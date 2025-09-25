from fastapi import FastAPI, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from mistralai import Mistral
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional, Dict
import logging
import json
import os
import gc
from redis_conn import redis_client
import json
import requests
import copy
import time
from shapely.geometry import shape
from pyproj import Geod
from requests.exceptions import ReadTimeout, ConnectTimeout, ConnectionError

from state_manager import init_state, load_state, save_state, touch_session_ttl
from validators import validate_crop_type, validate_pilot, validate_geojson, validate_time_period, \
    validate_validation, validate_zero_one
from authz_keycloak import require_user, require_role, verify_jwt_token
from sessions import router as sessions_router, persist_async_result_to_session, _set_session_owner
from emailer import send_email, build_results_email_html
from logging_config import configure_logging

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router, prefix="/api", tags=["sessions"])

# Logging
configure_logging()
logger = logging.getLogger(__name__)


# Load env vars
load_dotenv()
api_key = os.getenv('API_KEY')
ag_id = os.getenv('AGENT_ID')  # Fill with actual agent ID
client = Mistral(api_key=api_key)

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://161.35.213.220")
RETRYABLE_STATUS = { 502, 503, 504 }


def retry_backoff(attempt: int) -> int:
    """Backoff schedule in seconds: 5m, 15m, 30m, max."""
    schedule = [300, 900, 1800]  # 5min, 15min, 30min
    return schedule[min(attempt, len(schedule)-1)]

def parse_number(value):
    try:
        # Δοκίμασε πρώτα αν είναι ακέραιος
        int_value = int(value)
        return int_value
    except (ValueError, TypeError):
        try:
            # Αν δεν είναι ακέραιος, δοκίμασε δεκαδικό
            float_value = float(value)
            return float_value
        except (ValueError, TypeError):
            return None


def call_llm(session_id: str, user_message: str) -> str:
    history_key = f"chat:{session_id}:history"

    # 🔸 System prompt ως μεταβλητή
    system_prompt = {
        "role": "system",
        "content": (
            "You are a smart assistant helping users evaluate Crop, PV suitability, basic Agent-Based Modelling, enhanced Agent-Based Modelling or full Agent-Based Modelling. Avoid unnecessary elaboration.\n\n"
        )
    }

    # ➕ Αν δεν υπάρχει ιστορικό, ξεκινάμε με system prompt
    if redis_client.llen(history_key) == 0:
        redis_client.rpush(history_key, json.dumps(system_prompt))

    # ➕ Πρόσθεσε το user μήνυμα
    redis_client.rpush(history_key, json.dumps({"role": "user", "content": user_message}))
    touch_session_ttl(session_id)

    # 🔄 Πάρε όλο το ιστορικό
    chat_history = [json.loads(m) for m in redis_client.lrange(history_key, 0, -1)]

    # 📡 Κάλεσε το LLM μέσω agent
    response = client.agents.complete(
        agent_id=ag_id,
        messages=chat_history
    )

    # ✅ Απόσπαση απάντησης
    answer = response.choices[0].message.content.strip()

    # 💾 Αποθήκευση απάντησης στο ιστορικό
    redis_client.rpush(history_key, json.dumps({"role": "assistant", "content": answer}))
    touch_session_ttl(session_id)

    return answer


def calculate_area_sq_meters(geojson_data):
    geod = Geod(ellps="WGS84")  # Use WGS84 ellipsoid
    total_area = 0.0

    # Parse string input if needed
    if isinstance(geojson_data, str):
        geojson_data = json.loads(geojson_data)

    # GeoJSON can have FeatureCollection or a single Feature
    features = geojson_data.get('features', [geojson_data])

    for feature in features:
        geom = shape(feature['geometry'])

        if geom.geom_type == 'Polygon':
            lon, lat = zip(*geom.exterior.coords)
            area, _ = geod.polygon_area_perimeter(lon, lat)
            total_area += abs(area)

        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                lon, lat = zip(*poly.exterior.coords)
                area, _ = geod.polygon_area_perimeter(lon, lat)
                total_area += abs(area)

    return total_area  # in square meters


def extract_identity(http_req: Optional[Request]) -> Dict[str, Optional[str]]:
    """
    Return {'sub': <keycloak sub or None>, 'email': <email or preferred_username or None>}
    Does not raise; returns None fields if anything fails.
    """
    sub = email = None
    if not http_req:
        return {"sub": None, "email": None}

    auth = http_req.headers.get("authorization") or http_req.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return {"sub": None, "email": None}

    token = auth.split(" ", 1)[1]
    try:
        claims = verify_jwt_token(token)
        sub = claims.get("sub")
        email = claims.get("email") or claims.get("preferred_username")
    except Exception as e:
        # swallow any decode/verification error to avoid breaking the flow
        logger.warning("Could not decode token: %s", e)
        pass

    return {"sub": sub, "email": email}


def handle_llm_response(response_text: str, session_id: str , model: str, sub: str | None):
    state = load_state(session_id)
    collected = state.get("collected_inputs", {})

    print("HANDLE STARTED")
    print(state)
    print(response_text)
    result = {
        "action": None,
        "pilot": None,
        "chart_data": [],
        "map_layers": [],
        "profit_layers": [],
        "profit_chart_data": [],
        "map_explanation": None,
        "text": response_text.strip()
    }

    print("IFMODEL")
    # --- Για μοντέλο crop ---
    if model == "crop_suitability":
        print("CROP VARIABLES")
        print(collected)
        crop_type = collected["crop_type"]
        time_period = collected["time_period"]
        pilot = collected["area"]

        payload = {
            "crop_type": crop_type.upper(),
            "area": pilot.upper()
        }

        if time_period == "future":
            url = "https://transitionapi.neuralio.ai/crop_future"
            payload["display_profits"] = collected["show_profit"]
        else:
            url = "https://transitionapi.neuralio.ai/crop_past"

        result["action"] = "crop_suitability"
        result["pilot"] = pilot.upper()

    # --- Για μοντέλο pv ---
    elif model == "pv_suitability":
        print("PV VARIABLES")
        print(collected)
        time_period = collected["time_period"]
        pilot = collected["area"]
        geojson_clean = json.loads(collected['geojson'])
        pretty_geojson = json.dumps(geojson_clean, indent=2)

        if time_period == "future":
            url = "https://transitionapi.neuralio.ai/pv_future"
        else:
            url = "https://transitionapi.neuralio.ai/pv_past"

        payload = {
            "task_id": session_id,
            "user_id": sub,
            "geojson" : pretty_geojson,
            "area": pilot.upper(),
            "proximity_to_powerlines": float(collected["proximity_to_powerlines"]),
            "road_network_accessibility": float(collected["road_network_accessibility"]),
            "PV_area": float(collected["PV_area"]),
            "electricity_rate": float(collected["electricity_rate"]),
            "efficiency": float(collected["efficiency"])
        }
        result["action"] = "pv_suitability"
        result["pilot"] = pilot.upper()

    # --- Για μοντέλο base-abm ---
    elif model == "base-abm":
        print("BASE-ABM VARIABLES")
        print(collected)
        time_period = collected["time_period"]
        pilot = collected["area"]
        validation = collected["validation"]

        if time_period == "future":
            url = "https://transitionapi.neuralio.ai/base_future"
        else:
            url = "https://transitionapi.neuralio.ai/base_past"

        payload = {
            "task_id": session_id,
            "user_id": sub,
            "area": pilot.upper(),
            "validation": validation.lower()
        }

        result["action"] = "base-abm"
        result["pilot"] = pilot.upper()

    # --- Για μοντέλο pecs-abm ---
    elif model == "pecs-abm":
        print("PECS-ABM VARIABLES")
        print(collected)
        time_period = collected["time_period"]
        pilot = collected["area"]
        validation = collected["validation"]

        if time_period == "future":
            url = "https://transitionapi.neuralio.ai/pecs_future"
        else:
            url = "https://transitionapi.neuralio.ai/pecs_past"

        payload = {
            "task_id": session_id,
            "user_id": sub, 
            "area": pilot.upper(),
            "health_status": float(collected["health_status"]),
            "labor_availability": float(collected["labor_availability"]),
            "stress_level": float(collected["stress_level"]),
            "satisfaction": float(collected["satisfaction"]),
            "policy_incentives": float(collected["policy_incentives"]),
            "information_access": float(collected["information_access"]),
            "social_influence": float(collected["social_influence"]),
            "community_participation": float(collected["community_participation"]),
            "validation": validation.lower()
        }

        result["action"] = "pecs-abm"
        result["pilot"] = pilot.upper()

    # --- Για μοντέλο full-abm ---
    elif model == "full-abm":
        print("FULL-ABM VARIABLES")
        print(collected)
        time_period = collected["time_period"]
        pilot = collected["area"]
        validation = collected["validation"]

        if time_period == "future":
            url = "https://transitionapi.neuralio.ai/full_future"
        else:
            url = "https://transitionapi.neuralio.ai/full_past"

        payload = {
            "task_id": session_id,
            "user_id": sub, 
            "area": pilot.upper(),
            "health_status": float(collected["health_status"]),
            "labor_availability": float(collected["labor_availability"]),
            "stress_level": float(collected["stress_level"]),
            "satisfaction": float(collected["satisfaction"]),
            "policy_incentives": float(collected["policy_incentives"]),
            "information_access": float(collected["information_access"]),
            "social_influence": float(collected["social_influence"]),
            "community_participation": float(collected["community_participation"]),
            "total_budget": float(collected["total_budget"]),
            "pv_installation_cost": float(collected["pv_installation_cost"]),
            "adoption_weight": float(collected["adoption_weight"]),
            "resilience_weight": float(collected["resilience_weight"]),
            "budget_overshoot_weight": float(collected["budget_overshoot_weight"]),
            "validation": validation.lower()
        }

        result["action"] = "full-abm"
        result["pilot"] = pilot.upper()

    else:
        result["text"] += f"\n❌ Unsupported model type: {model}"
        return result

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)

        if not response.ok:
            logger.error("API call failed: %s - %s", response.status_code, response.text)
            # print(f"❌ API call failed: {response.status_code} - {response.text}")
            result["text"] += "\n⚠️ Something went wrong when calling the model API."
            return result

        api_data = response.json()

        geoserver_data = api_data.get("geoserver_data", {})
        for layer in geoserver_data.get("layers", []):
            result["map_layers"].append(layer)

        for profit_layer in geoserver_data.get("layers_profits", []):
            result["profit_layers"].append(profit_layer)

        result["map_explanation"] = api_data.get("User Explanation", None)

        if api_data.get("Validation Statistics"):
            stats = api_data["Validation Statistics"]
            result["chart_data"] = [
                {
                    "data": stats.get("Explainability Plot Data", []),
                    "offset": stats.get("Explainability Plot Offset", 0),
                    "explanation": stats.get("Explainability User Message", None),
                    "validation_explanation": stats.get("Ensemble Statistics User Message", None),
                    "scenario": None
                }
            ]
        elif any(k.startswith("Validation Statistics - RCP") for k in api_data.keys()):
            for rcp in ["RCP26", "RCP45", "RCP85"]:
                stats_key = f"Validation Statistics - {rcp}"
                if stats_key in api_data:
                    stats = api_data[stats_key]
                    result["chart_data"].append({
                        "data": stats.get("Explainability Plot Data", []),
                        "offset": stats.get("Explainability Plot Offset", 0),
                        "explanation": stats.get("Explainability User Message", None),
                        "validation_explanation": stats.get("Ensemble Statistics User Message", None),
                        "scenario": rcp
                    })

        result["text"] += "✅ Model execution completed."
        return result

    except Exception as e:
        logger.exception("Exception during API call: %s", e)
        # print("❌ Exception during API call:", str(e))
        result["text"] += "\n❌ Failed to contact model API."
        return result


def run_abm_validation_job_async(session_id: str, model: str, collected_inputs: dict, sub: str | None, email: str | None):
    """
    Background thread: call the long-running ABM validation endpoint.
    Retries on gateway timeouts and network issues. On success, append results;
    on final failure, append a failure message to the session.
    """
    # Gather inputs
    time_period = collected_inputs["time_period"]
    pilot = collected_inputs["area"]
    validation = collected_inputs["validation"]
    model_name = None
    
    if model == "base-abm":
        if time_period == "future":
            url = "https://transitionapi.neuralio.ai/base_future"
        else:
            url = "https://transitionapi.neuralio.ai/base_past"

        payload = {
            "task_id": session_id,
            "user_id": sub,
            "area": pilot.upper(),
            "validation": validation.lower()
        }

        model_name = "ABM"
    
    elif model == "pecs-abm":
        if time_period == "future":
            url = "https://transitionapi.neuralio.ai/pecs_future"
        else:
            url = "https://transitionapi.neuralio.ai/pecs_past"
       
        payload = {
            "task_id": session_id,
            "user_id": sub, 
            "area": pilot.upper(),
            "health_status": float(collected_inputs["health_status"]),
            "labor_availability": float(collected_inputs["labor_availability"]),
            "stress_level": float(collected_inputs["stress_level"]),
            "satisfaction": float(collected_inputs["satisfaction"]),
            "policy_incentives": float(collected_inputs["policy_incentives"]),
            "information_access": float(collected_inputs["information_access"]),
            "social_influence": float(collected_inputs["social_influence"]),
            "community_participation": float(collected_inputs["community_participation"]),
            "validation": validation.lower()
        }

        model_name = "PECS-ABM"

    elif model == "full-abm":
        if time_period == "future":
            url = "https://transitionapi.neuralio.ai/full_future"
        else:
            url = "https://transitionapi.neuralio.ai/full_past"

        payload = {
            "task_id": session_id,
            "user_id": sub, 
            "area": pilot.upper(),
            "health_status": float(collected_inputs["health_status"]),
            "labor_availability": float(collected_inputs["labor_availability"]),
            "stress_level": float(collected_inputs["stress_level"]),
            "satisfaction": float(collected_inputs["satisfaction"]),
            "policy_incentives": float(collected_inputs["policy_incentives"]),
            "information_access": float(collected_inputs["information_access"]),
            "social_influence": float(collected_inputs["social_influence"]),
            "community_participation": float(collected_inputs["community_participation"]),
            "total_budget": float(collected_inputs["total_budget"]),
            "pv_installation_cost": float(collected_inputs["pv_installation_cost"]),
            "adoption_weight": float(collected_inputs["adoption_weight"]),
            "resilience_weight": float(collected_inputs["resilience_weight"]),
            "budget_overshoot_weight": float(collected_inputs["budget_overshoot_weight"]),
            "validation": validation.lower()
        }

        model_name = "FULL-ABM"

    headers = {"Content-Type": "application/json"}

    max_attempts = 4  # 1 initial + 3 retries
    last_error_text = None
    api_data = None

    for attempt in range(max_attempts):
        try:
            # connect timeout 10s; read timeout generously high (e.g. 3 * 3600s = 3h)
            resp = requests.post(url, headers=headers, json=payload, verify=False, timeout=(10, 5 * 3600))
            if resp.status_code == 200:
                api_data = resp.json()
                break  # success
            elif resp.status_code in RETRYABLE_STATUS:
                last_error_text = f"{resp.status_code} - {resp.text[:300]}"
            else:
                # Non-retryable (4xx etc.). Fail fast.
                last_error_text = f"{resp.status_code} - {resp.text[:300]}"
                logger.error("%s async: non-retryable response; %s", model_name, last_error_text)
                break
        except (ReadTimeout, ConnectTimeout, ConnectionError) as e:
            last_error_text = f"{type(e).__name__}: {str(e)[:300]}"

        # Retry if we have attempts left
        if attempt < max_attempts - 1:
            delay = retry_backoff(attempt)
            logger.warning("%s async: attempt %s failed; retrying in %ss; last_error=%s", model_name, attempt + 1, delay, last_error_text)
            time.sleep(delay)


    # Build result dict for persisting to session
    if api_data is not None:
        if sub:
            _set_session_owner(session_id, sub)

        result = {
            "action": model,
            "pilot": pilot.upper(),
            "chart_data": [],
            "map_layers": [],
            "profit_layers": [],
            "profit_chart_data": [],
            "map_explanation": None,
            "text": ""
        }

        # Map layers
        geoserver_data = api_data.get("geoserver_data", {})
        for layer in geoserver_data.get("layers", []):
            result["map_layers"].append(layer)

        result["map_explanation"] = api_data.get("User Explanation", None)

        # Chart / explainability blocks (both single and per-RCP variants supported)
        if api_data.get("Validation Statistics"):
            stats = api_data["Validation Statistics"]
            result["chart_data"] = [{
                "data": stats.get("Explainability Plot Data", []),
                "offset": stats.get("Explainability Plot Offset", 0),
                "explanation": stats.get("Explainability User Message", None),
                "validation_explanation": stats.get("Ensemble Statistics User Message", None),
                "scenario": None
            }]
        elif any(k.startswith("Validation Statistics - RCP") for k in api_data.keys()):
            for rcp in ["RCP26", "RCP45", "RCP85"]:
                stats_key = f"Validation Statistics - {rcp}"
                if stats_key in api_data:
                    stats = api_data[stats_key]
                    result["chart_data"].append({
                        "data": stats.get("Explainability Plot Data", []),
                        "offset": stats.get("Explainability Plot Offset", 0),
                        "explanation": stats.get("Explainability User Message", None),
                        "validation_explanation": stats.get("Ensemble Statistics User Message", None),
                        "scenario": rcp
                    })

        result["text"] = "✅ ABM validation results are ready."

        # Persist + “email”
        persist_async_result_to_session(sub, email, session_id, result)
        subject = f"{model_name} validation results are ready"
        deep_link = f"{FRONTEND_BASE_URL}/?sessionId={session_id}"

        if email:
            html = build_results_email_html(deep_link, session_id)
            send_email(email, subject, html)
        else:
            logger.info("[EMAIL/SKIPPED] No email present for sub=%s link=%s", sub, deep_link)

    else:
        # FAILURE PATH — clearly notify user; no map/graph payload
        logger.error("%s async: final failure; last_error=%s", model_name, last_error_text)
        msg = (
            f"⚠️ We couldn’t complete your **{model_name}** run with validation.\n\n"
            "The upstream service responded with an error"
            f"{f' ({last_error_text})' if last_error_text else ''}. "
            "Please try again later or contact support."
        )

        result = {
            "text": msg,
            "map_layers": [],
            "profit_layers": [],
            "map_explanation": None,
            "chart_data": [],
            "profit_chart_data": [],
            "action": "base-abm",
            "pilot": payload.get("area")
        }

        # Persist + “email”
        persist_async_result_to_session(sub, email, session_id, result)
        subject = f"{model_name} validation failed"
        deep_link = f"{FRONTEND_BASE_URL}/?sessionId={session_id}"

        if email:
            html = f"""
            <html><body>
            <p>Hi,</p>
            <p>We couldn’t complete your <strong>{model_name} validation</strong> run.</p>
            <p>Details have been added to your session. You may try again later.</p>
            <p><a href="{deep_link}">Open session</a></p>
            </body></html>
            """
            send_email(email, subject, html)
        else:
            logger.info("[EMAIL/SKIPPED] No email present for sub=%s link=%s", sub, deep_link)
    

# Pydantic input model
class ChatRequest(BaseModel):
    message: str
    session_id: str


class SessionResetRequest(BaseModel):
    session_id: str


# Main chat route
@app.post("/api/chat")
def chat_with_mistral(request: ChatRequest, bg: BackgroundTasks, http_req: Request = None):
    session_id = request.session_id
    user_input = request.message.strip()

    # extract user identity
    ident = extract_identity(http_req)
    sub = ident.get("sub")
    email = ident.get("email")

    # Load or init state
    state = load_state(session_id)
    if state is None:
        state = init_state(session_id)

    current_step = state["current_step"]
    service = state["service"]
    collected = state["collected_inputs"]

    chart_data = []
    map_layers = []
    profit_layers = []
    profit_chart_data = []
    map_explanation = None
    action = None
    pilot = None

    if user_input.lower() == "#exit":
        state = init_state(session_id)
        save_state(session_id, state)
        redis_client.delete(f"chat:{session_id}:history")
        llm_response = call_llm(session_id, "Tell very quickly 'If you’d like to start a service, type its name with a hashtag (e.g., #crop, #pv, #abm, #pecs or #full). You can also ask me anything to learn more about how the services work.'")
        return {
            "response": llm_response,
            "chart_data": [],
            "map_layers": [],
            "profit_layers": [],
            "profit_chart_data": [],
            "map_explanation": None,
            "action": None,
            "pilot": pilot
        }


    # Step 1: Επιλογή υπηρεσίας
    if current_step == "select_service":
        reply = user_input.lower()

        if "#crop" in reply:
            state["service"] = "crop_suitability"
            state["current_step"] = "crop_type"

            save_state(session_id, state)
            redis_client.delete(f"chat:{session_id}:history")

            return {
                "response": "Which crop would you like to evaluate?  Currently, we support the following crop types: **wheat** and **maize**. You can type #exit at any time if you want to change parameters or service.",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif "#pv" in reply:
            state["service"] = "pv_suitability"

            if state.get("collected_inputs") is not None and state["collected_inputs"].get("area") is not None:
                pv_area = calculate_area_sq_meters(state["collected_inputs"]["geojson"])
                state["collected_inputs"]["PV_area"] = parse_number(pv_area)

                state["current_step"] = "proximity_to_powerlines"
                response = "Please enter the distance from powerlines in kilometers (e.g., 1.5):"
            else:
                state["current_step"] = "pilot"
                response = "For which pilot area would you like to evaluate ? Currently, we support the following pilot areas:\n **PILOT_THESSALONIKI**, **PILOT_PILSEN**, **PILOT_OLOMOUC**. You can type #exit at any time if you want to change parameters or service."  # , **GREECE**, **CZECHIA** 


            save_state(session_id, state)
            redis_client.delete(f"chat:{session_id}:history")

            return {
                "response": response,
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif "#abm" in reply:
            state["service"] = "base-abm"

            if state.get("collected_inputs") is not None and state["collected_inputs"].get("area") is not None:
                state["current_step"] = "validation"
                response = "Would you like validation to be performed ? Please type **yes** or **no** ."
            else:
                state["current_step"] = "pilot"
                response = "For which pilot area would you like to evaluate ? Currently, we support the following pilot areas:\n **PILOT_THESSALONIKI**, **PILOT_PILSEN**, **PILOT_OLOMOUC** . You can type #exit at any time if you want to change parameters or service."  #, **GREECE**, **CZECHIA**
            
            save_state(session_id, state)
            redis_client.delete(f"chat:{session_id}:history")

            return {
                "response": response,
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }
        
        elif "#pecs" in reply:
            state["service"] = "pecs-abm"

            if state.get("collected_inputs") is not None and state["collected_inputs"].get("area") is not None:
                state["current_step"] = "health_status"
                response = "Please enter a positive number between 0 and 1 for health status (e.g., 0.78):"
            else:
                state["current_step"] = "pilot"
                response = "For which pilot area would you like to evaluate ? Currently, we support the following pilot areas:\n **PILOT_THESSALONIKI**, **PILOT_PILSEN**, **PILOT_OLOMOUC** . You can type #exit at any time if you want to change parameters or service."     #, **GREECE**, **CZECHIA**
            
            save_state(session_id, state)
            redis_client.delete(f"chat:{session_id}:history")

            return {
                "response": response,
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif "#full" in reply:
            state["service"] = "full-abm"

            if state.get("collected_inputs") is not None and state["collected_inputs"].get("area") is not None:
                state["current_step"] = "health_status"
                response = "Please enter a positive number between 0 and 1 for health status (e.g., 0.2):"
            else:
                state["current_step"] = "pilot"
                response = "For which pilot area would you like to evaluate ? Currently, we support the following pilot areas:\n **PILOT_THESSALONIKI**, **PILOT_PILSEN**, **PILOT_OLOMOUC** . You can type #exit at any time if you want to change parameters or service."    #, **GREECE**, **CZECHIA**
            
            save_state(session_id, state)
            redis_client.delete(f"chat:{session_id}:history")

            return {
                "response": response,
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }
                
        else:
            llm_response = call_llm(session_id, user_input)
            return {
                "response": llm_response,
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

    # Step 2: Crop Suitability flow
    if service == "crop_suitability":
        if current_step == "crop_type":
            crop = validate_crop_type(user_input)
            if not crop:
                return {
                    "response": "Please enter a valid crop: 'wheat' or 'maize'. You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["crop_type"] = crop
            
            if state.get("collected_inputs") is not None and state["collected_inputs"].get("area") is not None:
                state["current_step"] = "time_period"
                response = "Thanks! For which time period would you like to evaluate ? \n **Past** — based on historical Earth Observation data \n **Future** — using climate projections under RCP scenarios?"
            else:
                state["current_step"] = "pilot"
                response = "Thanks! For which pilot area would you like to evaluate ? Currently, we support the following pilot areas:\n **PILOT_THESSALONIKI**, **PILOT_PILSEN**, **PILOT_OLOMOUC** ."   # , **GREECE**, **CZECHIA**

            save_state(session_id, state)

            return {
                "response": response,
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": None
            }

        elif current_step == "pilot":
            pilot = validate_pilot(user_input)
            if not pilot:
                return {
                    "response": "Please provide a valid pilot: 'PILOT_THESSALONIKI', 'PILOT_PILSEN', 'PILOT_OLOMOUC'. You can type #exit at any time if you want to change parameters or service.",   # , 'GREECE', 'CZECHIA'
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["area"] = pilot
            state["current_step"] = "geojson"
            save_state(session_id, state)
            return {
                "response": "Please define your area of interest by drawing a polygon on the map shown below. "
                "Once you complete the drawing, the GeoJSON format will be automatically generated and submitted.",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": "open_map",
                "pilot": pilot
            }

        elif current_step == "geojson":
            geo = validate_geojson(user_input)
            if not geo:
                return {
                    "response": "Please provide a valid area (GeoJSON format). You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["geojson"] = geo
            state["current_step"] = "time_period"
            save_state(session_id, state)
            return {
                "response": "Thanks! For which time period would you like to evaluate ? \n **Past** — based on historical Earth Observation data \n **Future** — using climate projections under RCP scenarios?",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "time_period":
            period = validate_time_period(user_input)
            if not period:
                return {
                    "response": "Please enter 'past' or 'future'. You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }

            state["collected_inputs"]["time_period"] = period

            if period == "future":
                state["current_step"] = "profit"
            
                save_state(session_id, state)
                return {
                    "response": "Thanks! Would you like profit estimation to be also performed ? Please type **yes** or **no** ",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            else:
                save_state(session_id, state)

                # ✅ Τώρα που όλα τα inputs υπάρχουν, κάνε handle
                # response_text = "Thanks! Executing the Crop Suitability model now."
                # llm_result = handle_llm_response(response_text, session_id, service)
                llm_result = handle_llm_response("", session_id, service, sub)

                # redis_client.delete(f"state:{session_id}")
                print("******$$$$******")
                print(state)

                print("CLEARING INPUTS")
                state["service"] = None
                state["resuming"] = True
                state["current_step"] = "select_service"

                if "collected_inputs" in state and state["collected_inputs"]["time_period"] == "future": 
                    del state["collected_inputs"]["show_profit"]

                if "collected_inputs" in state:
                    del state["collected_inputs"]["crop_type"]
                    del state["collected_inputs"]["time_period"]

                save_state(session_id, state)
                print(state)

                return {
                    "response": llm_result["text"],
                    "chart_data": llm_result["chart_data"],
                    "map_layers": llm_result["map_layers"],
                    "profit_layers": llm_result["profit_layers"],
                    "profit_chart_data": llm_result["profit_chart_data"],
                    "map_explanation": llm_result["map_explanation"],
                    "action": llm_result["action"],
                    "pilot": llm_result["pilot"]
                }

        elif current_step == "profit":
            profit = validate_validation(user_input)
            if not profit:
                return {
                    "response": "Please enter 'yes' or 'no'. You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }

            state["collected_inputs"]["show_profit"] = profit
            save_state(session_id, state)

            # ✅ Τώρα που όλα τα inputs υπάρχουν, κάνε handle
            llm_result = handle_llm_response("", session_id, service, sub)

            # redis_client.delete(f"state:{session_id}")
            print("******$$$$******")
            print(state["collected_inputs"])

            print("CLEARING INPUTS")
            state["service"] = None
            state["resuming"] = True
            state["current_step"] = "select_service"

            if "collected_inputs" in state:
                del state["collected_inputs"]["crop_type"]
                del state["collected_inputs"]["time_period"]
                del state["collected_inputs"]["show_profit"]

            save_state(session_id, state)
            print(state)

            return {
                "response": llm_result["text"],
                "chart_data": llm_result["chart_data"],
                "map_layers": llm_result["map_layers"],
                "profit_layers": llm_result["profit_layers"],
                "profit_chart_data": llm_result["profit_chart_data"],
                "map_explanation": llm_result["map_explanation"],
                "action": llm_result["action"],
                "pilot": llm_result["pilot"]
            }

    elif service == "pv_suitability":
        if current_step == "pilot":
            pilot = validate_pilot(user_input)
            if not pilot:
                return {
                    "response": "Please provide a valid pilot: 'PILOT_THESSALONIKI', 'PILOT_PILSEN', 'PILOT_OLOMOUC'. You can type #exit at any time if you want to change parameters or service.",    #  , 'GREECE', 'CZECHIA'
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["area"] = pilot
            state["current_step"] = "geojson"
            save_state(session_id, state)
            return {
                "response": "Please define your area of interest by drawing a polygon on the map shown below. "
                "Once you complete the drawing, the GeoJSON format will be automatically generated and submitted.",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": "open_map",
                "pilot": pilot
            }

        elif current_step == "geojson":
            geo = validate_geojson(user_input)
            if not geo:
                return {
                    "response": "Please provide a valid area (GeoJSON format). You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": "open_map",
                    "pilot": pilot
            }
            state["collected_inputs"]["geojson"] = geo
            state["current_step"] = "proximity_to_powerlines"

            pv_area = calculate_area_sq_meters(geo)
            state["collected_inputs"]["PV_area"] = parse_number(pv_area)

            save_state(session_id, state)
            return {
                "response": "Please enter the distance from powerlines in kilometers (e.g., 1.5):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "proximity_to_powerlines":
            distance = parse_number(user_input)
            if distance is None:
                return {
                    "response": "Please enter a valid positive number for the distance from powerlines in km.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["proximity_to_powerlines"] = distance
            state["current_step"] = "road_network_accessibility"
            save_state(session_id, state)
            return {
                "response": "Please enter the distance from roads in kilometers (e.g., 2.0):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "road_network_accessibility":
            road_access = parse_number(user_input)
            if road_access is None:
                return {
                    "response": "Please enter a valid positive number for road network accessibility in km.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["road_network_accessibility"] = road_access
            state["current_step"] = "electricity_rate"
            save_state(session_id, state)
            return {
                "response": "Please enter the electricity rate in $/kWh (e.g., 0.15):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "electricity_rate":
            rate = parse_number(user_input)
            if rate is None:
                return {
                    "response": "Please enter a valid positive number for electricity rate in $/kWh.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["electricity_rate"] = rate
            state["current_step"] = "efficiency"
            save_state(session_id, state)
            return {
                "response": "Please enter the efficiency of the PV installation in % (e.g., 18.5):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "efficiency":
            eff = parse_number(user_input)
            if eff is None:
                return {
                    "response": "Please enter a valid positive number for efficiency percentage (e.g., 18.5).",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }

            state["collected_inputs"]["efficiency"] = eff
            state["current_step"] = "time_period"
            save_state(session_id, state)
            return {
                "response": "Thanks! For which time period would you like to evaluate ? \n **Past** — based on historical Earth Observation data \n **Future** — using climate projections under RCP scenarios?",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": "show_pv_indicator",
                "pilot": pilot
            }

        elif current_step == "time_period":
            period = validate_time_period(user_input)
            if not period:
                return {
                    "response": "Please enter 'past' or 'future'.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }

            state["collected_inputs"]["time_period"] = period
            save_state(session_id, state)
            print("CURRENT SERVICE")
            print(service)
            print(state)
            # ✅ Τώρα που όλα τα inputs υπάρχουν, κάνε handle
            llm_result = handle_llm_response("", session_id, service, sub)

            # redis_client.delete(f"state:{session_id}")
            print("******$$$$******")
            print(state)

            print("CLEARING INPUTS")
            state["service"] = None
            state["resuming"] = True
            state["current_step"] = "select_service"

            if "collected_inputs" in state:
                del state["collected_inputs"]["PV_area"]
                del state["collected_inputs"]["proximity_to_powerlines"]
                del state["collected_inputs"]["road_network_accessibility"]
                del state["collected_inputs"]["electricity_rate"]
                del state["collected_inputs"]["efficiency"]
                del state["collected_inputs"]["time_period"]

            save_state(session_id, state)
            print(state)

            return {
                "response": llm_result["text"],
                "chart_data": llm_result["chart_data"],
                "map_layers": llm_result["map_layers"],
                "profit_layers": llm_result["profit_layers"],
                "profit_chart_data": llm_result["profit_chart_data"],
                "map_explanation": llm_result["map_explanation"],
                "action": llm_result["action"],
                "pilot": llm_result["pilot"]
            }
        
    elif service == "base-abm":
        if current_step == "pilot":
            pilot = validate_pilot(user_input)
            if not pilot:
                return {
                    "response": "Please provide a valid pilot: 'PILOT_THESSALONIKI', 'PILOT_PILSEN', 'PILOT_OLOMOUC'. You can type #exit at any time if you want to change parameters or service.",   # , 'GREECE', 'CZECHIA'
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["area"] = pilot
            state["current_step"] = "geojson"
            save_state(session_id, state)
            return {
                "response": "Please define your area of interest by drawing a polygon on the map shown below. "
                "Once you complete the drawing, the GeoJSON format will be automatically generated and submitted.",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": "open_map",
                "pilot": pilot
            }

        elif current_step == "geojson":
            geo = validate_geojson(user_input)
            if not geo:
                return {
                    "response": "Please provide a valid area (GeoJSON format). You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["geojson"] = geo
            state["current_step"] = "validation"
            save_state(session_id, state)
            return {
                "response": "Thanks! Would you like validation to be performed ? Please type **yes** or **no** ",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }
        
        elif current_step == "validation":
            validation = validate_validation(user_input)
            if not validation:
                return {
                    "response": "Please enter 'yes' or 'no'. You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["validation"] = validation
            state["current_step"] = "time_period"
            save_state(session_id, state)
            return {
                "response": "Thanks! For which time period would you like to evaluate ? \n **Past** — based on historical Earth Observation data \n **Future** — using climate projections under RCP scenarios?",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "time_period":
            period = validate_time_period(user_input)
            if not period:
                return {
                    "response": "Please enter 'past' or 'future'. You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }

            state["collected_inputs"]["time_period"] = period
            save_state(session_id, state)

            # ✅ SPECIAL CASE: ABM + validation = yes -> async
            validation = state["collected_inputs"].get("validation", "").lower()
            if validation == "yes":
                # Copy inputs for background job *before* we clear state
                collected_copy = copy.deepcopy(state["collected_inputs"])
                collected_service = state["service"]

                # Record owner now (if we have sub)
                if sub:
                    _set_session_owner(session_id, sub)

                # Queue background job
                bg.add_task(run_abm_validation_job_async, session_id, collected_service, collected_copy, sub, email)

                # Clear inputs and reset wizard as usual
                state["service"] = None
                state["resuming"] = True
                state["current_step"] = "select_service"

                if "collected_inputs" in state:
                    # leave geojson/area in state if you need them later, or clean them too
                    del state["collected_inputs"]["validation"]
                    del state["collected_inputs"]["time_period"]
                save_state(session_id, state)

                # Immediate response to the SPA
                notify_email = email or "your account email"
                link = f"{FRONTEND_BASE_URL}/?sessionId={session_id}"
                immediate_msg = (
                    "⏳ Your **Base-ABM** run with validation may take a while.\n\n"
                    f"I’ll email you at **{notify_email}** when the results are ready. "
                    f"You can also open this link later to view the session directly: {link}"
                )
                return {
                    "response": immediate_msg,
                    "chart_data": [],
                    "map_layers": [],
                    "profit_layers": [],
                    "profit_chart_data": [],
                    "map_explanation": None,
                    "action": None,
                    "pilot": pilot     # collected_copy.get("area", None)
                }

            # ✅ Τώρα που όλα τα inputs υπάρχουν, κάνε handle
            llm_result = handle_llm_response("", session_id, service, sub)

            # redis_client.delete(f"state:{session_id}")
            print("******$$$$******")
            print(state)

            print("CLEARING INPUTS")
            state["service"] = None
            state["resuming"] = True
            state["current_step"] = "select_service"

            if "collected_inputs" in state:
                del state["collected_inputs"]["validation"]
                del state["collected_inputs"]["time_period"]

            save_state(session_id, state)
            print(state)

            return {
                "response": llm_result["text"],
                "chart_data": llm_result["chart_data"],
                "map_layers": llm_result["map_layers"],
                "profit_layers": llm_result["profit_layers"],
                "profit_chart_data": llm_result["profit_chart_data"],
                "map_explanation": llm_result["map_explanation"],
                "action": llm_result["action"],
                "pilot": llm_result["pilot"]
            }

    elif service == "pecs-abm":
        if current_step == "pilot":
            pilot = validate_pilot(user_input)
            if not pilot:
                return {
                    "response": "Please provide a valid pilot: 'PILOT_THESSALONIKI', 'PILOT_PILSEN', 'PILOT_OLOMOUC'. You can type #exit at any time if you want to change parameters or service.",      # , 'GREECE', 'CZECHIA'
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["area"] = pilot
            state["current_step"] = "geojson"
            save_state(session_id, state)
            return {
                "response": "Please define your area of interest by drawing a polygon on the map shown below. "
                "Once you complete the drawing, the GeoJSON format will be automatically generated and submitted.",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": "open_map",
                "pilot": pilot
            }

        elif current_step == "geojson":
            geo = validate_geojson(user_input)
            if not geo:
                return {
                    "response": "Please provide a valid area (GeoJSON format). You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["geojson"] = geo
            state["current_step"] = "health_status"
            save_state(session_id, state)
            return {
                "response": "Thanks! Please enter a positive number between 0 and 1 for health status (e.g., 0.78):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }
        
        elif current_step == "health_status":
            health = validate_zero_one(parse_number(user_input))
            if health is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for health status.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["health_status"] = health
            state["current_step"] = "labor_availability"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for labor availability (e.g., 0.25):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }
        
        elif current_step == "labor_availability":
            labor = validate_zero_one(parse_number(user_input))
            if labor is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for labor availability.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["labor_availability"] = labor
            state["current_step"] = "stress_level"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for stress level (e.g., 0.45):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "stress_level":
            stress = validate_zero_one(parse_number(user_input))
            if stress is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for stress level.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["stress_level"] = stress
            state["current_step"] = "satisfaction"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for satisfaction (e.g., 0.89):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "satisfaction":
            satisfaction = validate_zero_one(parse_number(user_input))
            if satisfaction is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for satisfaction.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["satisfaction"] = satisfaction
            state["current_step"] = "policy_incentives"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for policy incentives (e.g., 0.33):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "policy_incentives":
            incntvs = validate_zero_one(parse_number(user_input))
            if incntvs is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for policy incentives.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["policy_incentives"] = incntvs
            state["current_step"] = "information_access"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for information access (e.g., 0.45):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "information_access":
            access = validate_zero_one(parse_number(user_input))
            if access is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for information access.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["information_access"] = access
            state["current_step"] = "social_influence"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for social influence (e.g., 0.2):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "social_influence":
            infl = validate_zero_one(parse_number(user_input))
            if infl is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for social influence.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["social_influence"] = infl
            state["current_step"] = "community_participation"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for community participation (e.g., 0.8):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "community_participation":
            prtcptn = validate_zero_one(parse_number(user_input))
            if prtcptn is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for community participation.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["community_participation"] = prtcptn
            state["current_step"] = "validation"
            save_state(session_id, state)
            return {
                "response": "Would you like validation to be performed ? Please type **yes** or **no** ",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }
                                                        
        elif current_step == "validation":
            validation = validate_validation(user_input)
            if not validation:
                return {
                    "response": "Please enter 'yes' or 'no'. You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["validation"] = validation
            state["current_step"] = "time_period"
            save_state(session_id, state)
            return {
                "response": "Thanks! For which time period would you like to evaluate ? \n **Past** — based on historical Earth Observation data \n **Future** — using climate projections under RCP scenarios?",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": "show_pv_indicator",
                "pilot": pilot
            }

        elif current_step == "time_period":
            period = validate_time_period(user_input)
            if not period:
                return {
                    "response": "Please enter 'past' or 'future'. You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }

            state["collected_inputs"]["time_period"] = period
            save_state(session_id, state)

            # ✅ SPECIAL CASE: ABM + validation = yes -> async
            validation = state["collected_inputs"].get("validation", "").lower()
            if validation == "yes":
                # Copy inputs for background job *before* we clear state
                collected_copy = copy.deepcopy(state["collected_inputs"])
                collected_service = state["service"]

                # Record owner now (if we have sub)
                if sub:
                    _set_session_owner(session_id, sub)

                # Queue background job
                bg.add_task(run_abm_validation_job_async, session_id, collected_service, collected_copy, sub, email)

                # Clear inputs and reset wizard as usual
                state["service"] = None
                state["resuming"] = True
                state["current_step"] = "select_service"

                if "collected_inputs" in state:
                    # leave geojson/area in state if you need them later, or clean them too
                    del state["collected_inputs"]["health_status"]
                    del state["collected_inputs"]["labor_availability"]
                    del state["collected_inputs"]["stress_level"]
                    del state["collected_inputs"]["satisfaction"]
                    del state["collected_inputs"]["policy_incentives"]
                    del state["collected_inputs"]["information_access"]
                    del state["collected_inputs"]["social_influence"]
                    del state["collected_inputs"]["community_participation"]
                    del state["collected_inputs"]["validation"]
                    del state["collected_inputs"]["time_period"]

                save_state(session_id, state)

                # Immediate response to the SPA
                notify_email = email or "your account email"
                link = f"{FRONTEND_BASE_URL}/?sessionId={session_id}"
                immediate_msg = (
                    "⏳ Your **PECS-ABM** run with validation may take a while.\n\n"
                    f"I’ll email you at **{notify_email}** when the results are ready. "
                    f"You can also open this link later to view the session directly: {link}"
                )
                return {
                    "response": immediate_msg,
                    "chart_data": [],
                    "map_layers": [],
                    "profit_layers": [],
                    "profit_chart_data": [],
                    "map_explanation": None,
                    "action": None,
                    "pilot": pilot     # collected_copy.get("area", None)
                }
            
            # ✅ Normal (non-validation) ABM path – run synchronously like before
            # ✅ Τώρα που όλα τα inputs υπάρχουν, κάνε handle
            llm_result = handle_llm_response("", session_id, service, sub)

            # redis_client.delete(f"state:{session_id}")
            print("******$$$$******")
            print(state)

            print("CLEARING INPUTS")
            state["service"] = None
            state["resuming"] = True
            state["current_step"] = "select_service"

            if "collected_inputs" in state:
                del state["collected_inputs"]["health_status"]
                del state["collected_inputs"]["labor_availability"]
                del state["collected_inputs"]["stress_level"]
                del state["collected_inputs"]["satisfaction"]
                del state["collected_inputs"]["policy_incentives"]
                del state["collected_inputs"]["information_access"]
                del state["collected_inputs"]["social_influence"]
                del state["collected_inputs"]["community_participation"]
                del state["collected_inputs"]["validation"]
                del state["collected_inputs"]["time_period"]

            save_state(session_id, state)
            print(state)

            return {
                "response": llm_result["text"],
                "chart_data": llm_result["chart_data"],
                "map_layers": llm_result["map_layers"],
                "profit_layers": llm_result["profit_layers"],
                "profit_chart_data": llm_result["profit_chart_data"],
                "map_explanation": llm_result["map_explanation"],
                "action": llm_result["action"],
                "pilot": llm_result["pilot"]
            }
        
    elif service == "full-abm":
        if current_step == "pilot":
            pilot = validate_pilot(user_input)
            if not pilot:
                return {
                    "response": "Please provide a valid pilot: 'PILOT_THESSALONIKI', 'PILOT_PILSEN', 'PILOT_OLOMOUC'. You can type #exit at any time if you want to change parameters or service.",      #, 'GREECE', 'CZECHIA'
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["area"] = pilot
            state["current_step"] = "geojson"
            save_state(session_id, state)
            return {
                "response": "Please define your area of interest by drawing a polygon on the map shown below. "
                "Once you complete the drawing, the GeoJSON format will be automatically generated and submitted.",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": "open_map",
                "pilot": pilot
            }

        elif current_step == "geojson":
            geo = validate_geojson(user_input)
            if not geo:
                return {
                    "response": "Please provide a valid area (GeoJSON format). You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["geojson"] = geo
            state["current_step"] = "health_status"
            save_state(session_id, state)
            return {
                "response": "Thanks! Please enter a positive number between 0 and 1 for health status (e.g., 0.2):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }
        
        elif current_step == "health_status":
            health = validate_zero_one(parse_number(user_input))
            if health is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for health status.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["health_status"] = health
            state["current_step"] = "labor_availability"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for labor availability (e.g., 0.3):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }
        
        elif current_step == "labor_availability":
            labor = validate_zero_one(parse_number(user_input))
            if labor is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for labor availability.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["labor_availability"] = labor
            state["current_step"] = "stress_level"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for stress level (e.g., 0.6):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "stress_level":
            stress = validate_zero_one(parse_number(user_input))
            if stress is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for stress level.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["stress_level"] = stress
            state["current_step"] = "satisfaction"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for satisfaction (e.g., 0.5):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "satisfaction":
            satisfaction = validate_zero_one(parse_number(user_input))
            if satisfaction is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for satisfaction.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["satisfaction"] = satisfaction
            state["current_step"] = "policy_incentives"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for policy incentives (e.g., 0.7):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "policy_incentives":
            incntvs = validate_zero_one(parse_number(user_input))
            if incntvs is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for policy incentives.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["policy_incentives"] = incntvs
            state["current_step"] = "information_access"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for information access (e.g., 0.1):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "information_access":
            access = validate_zero_one(parse_number(user_input))
            if access is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for information access.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["information_access"] = access
            state["current_step"] = "social_influence"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for social influence (e.g., 0.5):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "social_influence":
            infl = validate_zero_one(parse_number(user_input))
            if infl is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for social influence.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["social_influence"] = infl
            state["current_step"] = "community_participation"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for community participation (e.g., 0.9):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "community_participation":
            prtcptn = validate_zero_one(parse_number(user_input))
            if prtcptn is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for community participation.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["community_participation"] = prtcptn
            state["current_step"] = "total_budget"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number for the total budget in euros (e.g., 800000)",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "total_budget":
            budget = parse_number(user_input)
            if budget is None:
                return {
                    "response": "Please enter a valid positive number for the total budget in euros (€).",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["total_budget"] = budget
            state["current_step"] = "pv_installation_cost"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number for the photovoltaic installation cost in euros (e.g., 3000)",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "pv_installation_cost":
            cost = parse_number(user_input)
            if cost is None:
                return {
                    "response": "Please enter a valid positive number for the photovoltaic installation cost in euros (€).",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["pv_installation_cost"] = cost
            state["current_step"] = "adoption_weight"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for adoption weight (e.g., 0.9)",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "adoption_weight":
            adpt_weight = validate_zero_one(parse_number(user_input))
            if adpt_weight is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for adoption weight.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["adoption_weight"] = adpt_weight
            state["current_step"] = "resilience_weight"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for resilience weight (e.g., 0.1):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }

        elif current_step == "resilience_weight":
            resil_weight = validate_zero_one(parse_number(user_input))
            if resil_weight is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for resilience weight.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["resilience_weight"] = resil_weight
            state["current_step"] = "budget_overshoot_weight"
            save_state(session_id, state)
            return {
                "response": "Please enter a positive number between 0 and 1 for budget overshoot weight (e.g., 0.5):",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }
                                
        elif current_step == "budget_overshoot_weight":
            budget_wght = validate_zero_one(parse_number(user_input))
            if budget_wght is None:
                return {
                    "response": "Please enter a valid positive number between 0 and 1 for budget overshoot weight.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["budget_overshoot_weight"] = budget_wght
            state["current_step"] = "validation"
            save_state(session_id, state)
            return {
                "response": "Would you like validation to be performed ? Please type **yes** or **no** ",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                "action": None,
                "pilot": pilot
            }
                                                                
        elif current_step == "validation":
            validation = validate_validation(user_input)
            if not validation:
                return {
                    "response": "Please enter 'yes' or 'no'. You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }
            state["collected_inputs"]["validation"] = validation
            state["current_step"] = "time_period"
            save_state(session_id, state)
            return {
                "response": "Thanks! For which time period would you like to evaluate ? \n **Past** — based on historical Earth Observation data \n **Future** — using climate projections under RCP scenarios?",
                "chart_data": chart_data,
                "map_layers": map_layers,
                "profit_layers": profit_layers,
                "profit_chart_data": profit_chart_data,
                "map_explanation": map_explanation,
                # "action": None,
                "action": "show_pv_indicator",
                "pilot": pilot
            }

        elif current_step == "time_period":
            period = validate_time_period(user_input)
            if not period:
                return {
                    "response": "Please enter 'past' or 'future'. You can type #exit at any time if you want to change parameters or service.",
                    "chart_data": chart_data,
                    "map_layers": map_layers,
                    "profit_layers": profit_layers,
                    "profit_chart_data": profit_chart_data,
                    "map_explanation": map_explanation,
                    "action": None,
                    "pilot": pilot
                }

            state["collected_inputs"]["time_period"] = period
            save_state(session_id, state)

            # ✅ SPECIAL CASE: ABM + validation = yes -> async
            validation = state["collected_inputs"].get("validation", "").lower()
            if validation == "yes":
                # Copy inputs for background job *before* we clear state
                collected_copy = copy.deepcopy(state["collected_inputs"])
                collected_service = state["service"]

                # Record owner now (if we have sub)
                if sub:
                    _set_session_owner(session_id, sub)

                # Queue background job
                bg.add_task(run_abm_validation_job_async, session_id, collected_service, collected_copy, sub, email)

                # Clear inputs and reset wizard as usual
                state["service"] = None
                state["resuming"] = True
                state["current_step"] = "select_service"

                if "collected_inputs" in state:
                    # leave geojson/area in state if you need them later, or clean them too
                    del state["collected_inputs"]["health_status"]
                    del state["collected_inputs"]["labor_availability"]
                    del state["collected_inputs"]["stress_level"]
                    del state["collected_inputs"]["satisfaction"]
                    del state["collected_inputs"]["policy_incentives"]
                    del state["collected_inputs"]["information_access"]
                    del state["collected_inputs"]["social_influence"]
                    del state["collected_inputs"]["community_participation"]
                    del state["collected_inputs"]["total_budget"]
                    del state["collected_inputs"]["pv_installation_cost"]
                    del state["collected_inputs"]["adoption_weight"]
                    del state["collected_inputs"]["resilience_weight"]
                    del state["collected_inputs"]["budget_overshoot_weight"]
                    del state["collected_inputs"]["validation"]
                    del state["collected_inputs"]["time_period"]

                save_state(session_id, state)

                # Immediate response to the SPA
                notify_email = email or "your account email"
                link = f"{FRONTEND_BASE_URL}/?sessionId={session_id}"
                immediate_msg = (
                    "⏳ Your **FULL-ABM** run with validation may take a while.\n\n"
                    f"I’ll email you at **{notify_email}** when the results are ready. "
                    f"You can also open this link later to view the session directly: {link}"
                )
                return {
                    "response": immediate_msg,
                    "chart_data": [],
                    "map_layers": [],
                    "profit_layers": [],
                    "profit_chart_data": [],
                    "map_explanation": None,
                    "action": None,
                    "pilot": pilot     # collected_copy.get("area", None)
                }
            
            # ✅ Normal (non-validation) ABM path – run synchronously like before
            # ✅ Τώρα που όλα τα inputs υπάρχουν, κάνε handle
            llm_result = handle_llm_response("", session_id, service, sub)

            # redis_client.delete(f"state:{session_id}")
            print("******$$$$******")
            print(state)

            print("CLEARING INPUTS")
            state["service"] = None
            state["resuming"] = True
            state["current_step"] = "select_service"

            if "collected_inputs" in state:
                del state["collected_inputs"]["health_status"]
                del state["collected_inputs"]["labor_availability"]
                del state["collected_inputs"]["stress_level"]
                del state["collected_inputs"]["satisfaction"]
                del state["collected_inputs"]["policy_incentives"]
                del state["collected_inputs"]["information_access"]
                del state["collected_inputs"]["social_influence"]
                del state["collected_inputs"]["community_participation"]
                del state["collected_inputs"]["total_budget"]
                del state["collected_inputs"]["pv_installation_cost"]
                del state["collected_inputs"]["adoption_weight"]
                del state["collected_inputs"]["resilience_weight"]
                del state["collected_inputs"]["budget_overshoot_weight"]
                del state["collected_inputs"]["validation"]
                del state["collected_inputs"]["time_period"]

            save_state(session_id, state)
            print(state)

            return {
                "response": llm_result["text"],
                "chart_data": llm_result["chart_data"],
                "map_layers": llm_result["map_layers"],
                "profit_layers": llm_result["profit_layers"],
                "profit_chart_data": llm_result["profit_chart_data"],
                "map_explanation": llm_result["map_explanation"],
                "action": llm_result["action"],
                "pilot": llm_result["pilot"]
            }

    # Αν για κάποιο λόγο δεν ταιριάζει τίποτα
    return {
        "response": "Something went wrong. Let's start over. Please choose a service: 'Crop Suitability', 'PV Suitability', 'Basic Agent-Based Modelling', 'Enhanced Agent-Based Modelling' or 'Full Agent-Based Modelling'.",
        "chart_data": chart_data,
        "map_layers": map_layers,
        "profit_layers": profit_layers,
        "profit_chart_data": profit_chart_data,
        "map_explanation": map_explanation,
        "action": None,
        "pilot": None
    }


@app.post("/api/clear-session")
def clear_session(request: SessionResetRequest):
    session_id = request.session_id

    # 🚫 First: Delete everything from Redis
    redis_client.delete(f"chat:{session_id}")
    redis_client.delete(f"chat:{session_id}:history")
    redis_client.delete(f"state:{session_id}")    

    # Force a clean break: remove references from memory too
    gc.collect()
    print("All cleared from Redis and memory (via GC).")

    return {"message": f"Session {session_id} cleared", "status": "ok"}



# protect an endpoint (requires any authenticated user)
@app.get("/api/secure/ping")
async def secure_ping(user=Depends(require_user)):
    # user is the decoded token payload
    return {"ok": True, "sub": user.get("sub")}

# protect an endpoint needing a realm role "admin"
@app.get("/api/admin/only")
async def admin_only(user=Depends(require_role("admin"))):
    return {"ok": True, "sub": user.get("sub"), "roles": user.get("realm_access", {})}

# whoami for debugging
@app.get("/api/secure/whoami")
async def whoami(user=Depends(require_user)):
    # return a minimal, safe subset
    return {
        "sub": user.get("sub"),
        "preferred_username": user.get("preferred_username"),
        "realm_roles": user.get("realm_access", {}).get("roles", [])
    }