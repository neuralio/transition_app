from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
import logging
import json

from authz_keycloak import require_user
from redis_conn import redis_client

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------- Models ----------
class SessionUpsert(BaseModel):
    session_id: str
    title: Optional[str] = None
    messages: List[Dict[str, Any]]

class SessionSummary(BaseModel):
    id: str
    title: str
    updated_at: float
    message_count: int

class SessionTitleUpdate(BaseModel):
    title: str
    touch: bool = False  # if True, bump updated_at and ordering; default False


# ---------- Time & bytes helpers ----------
def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _b2s(b):
    return b.decode("utf-8") if isinstance(b, (bytes, bytearray)) else b


# ---------- Redis key helpers ----------
def _k_doc(sub: str, sid: str) -> str:
    """Per-user document key."""
    return f"user:{sub}:session:{sid}"

def _k_doc_global(sid: str) -> str:
    """Global document key (back-compat / safety)."""
    return f"session:{sid}"

def _k_idx(sub: str) -> str:
    """Per-user index of sessions (ZSET newest-first)."""
    return f"sessidx:{sub}"

def _owner_key(sid: str) -> str:
    return f"session:{sid}:owner"


# ---------- Expiry (TTL) ----------
SESSION_TTL_SEC = 14 * 24 * 60 * 60  # 14 days

def _touch_session_ttl(sid: str, sub: Optional[str] = None) -> None:
    """
    Refresh TTL for all keys related to this session.
    Safe to call even if some keys don't exist.
    """
    keys = [
        f"chat:{sid}",
        f"chat:{sid}:history",
        f"state:{sid}",
        _k_doc_global(sid),
        _owner_key(sid),
    ]
    if sub:
        keys.append(_k_doc(sub, sid))

    pipe = redis_client.pipeline()
    for k in keys:
        pipe.expire(k, SESSION_TTL_SEC)
    pipe.execute()


# ---------- Owner helpers ----------
def _set_session_owner(session_id: str, sub: str):
    """Record owner once; harmless if it already exists."""
    if not sub:
        return
    try:
        if redis_client.setnx(_owner_key(session_id), sub):
            redis_client.expire(_owner_key(session_id), SESSION_TTL_SEC)
        else:
            # refresh on any write path
            redis_client.expire(_owner_key(session_id), SESSION_TTL_SEC)
    except Exception as e:
        logger.exception("set_session_owner failed for %s: %s", session_id, e)
        # print("set_session_owner failed for %s: %s", session_id, e)

def _get_session_owner(session_id: str) -> Optional[str]:
    try:
        v = redis_client.get(_owner_key(session_id))
        return _b2s(v) if v else None
    except Exception:
        logger.exception("get_session_owner failed | sess=%s", session_id)
        return None
    

# ---------- Core doc helpers ----------
def _get_doc_for_user_or_global(sub: str, sid: str) -> Optional[dict]:
    """Prefer per-user doc; fall back to global (caller must enforce ownership)."""
    raw = redis_client.get(_k_doc(sub, sid))
    if raw:
        return json.loads(_b2s(raw))
    raw = redis_client.get(_k_doc_global(sid))
    return json.loads(_b2s(raw)) if raw else None

def _save_doc_both(sub: str, sid: str, doc: dict, touch_index: bool = True) -> None:
    """
    Save the doc to both per-user and global keys.
    Update the user's ZSET index with numeric score for newest-first.
    """
    doc.setdefault("id", sid)
    doc.setdefault("title", "Untitled Chat")
    doc.setdefault("messages", [])
    doc.setdefault("created_at", _now_iso())
    # numeric updated_at for sorting & index score
    doc["updated_at"] = _now_ts()

    k_user = _k_doc(sub, sid)
    k_glob = _k_doc_global(sid)

    pipe = redis_client.pipeline()
    pipe.set(k_user, json.dumps(doc))
    pipe.set(k_glob, json.dumps(doc))
    pipe.expire(k_user, SESSION_TTL_SEC)
    pipe.expire(k_glob, SESSION_TTL_SEC) 
    if touch_index:
        pipe.zadd(_k_idx(sub), {k_user: float(doc["updated_at"])})
    pipe.execute()

    # ensure owner recorded
    _set_session_owner(sid, sub)
    # make sure owner + other session keys are kept alive
    _touch_session_ttl(sid, sub=sub)


# ---------- High-level helpers used by routes ----------
def _list_docs(sub: str) -> List[SessionSummary]:
    # Newest-first by score
    keys = redis_client.zrevrange(_k_idx(sub), 0, -1, withscores=True)
    out: List[SessionSummary] = []
    for k, score in keys:
        k = _b2s(k)
        raw = redis_client.get(k)
        if not raw:
            continue
        doc = json.loads(_b2s(raw))
        out.append(SessionSummary(
            id=doc["id"],
            title=(doc.get("title") or "Untitled Chat"),
            updated_at=float(score),
            message_count=len(doc.get("messages", [])),
        ))
    return out

def _get_doc_owned(sub: str, sid: str) -> Optional[dict]:
    """
    Return the session only if caller is the owner.
    We accept per-user or global storage, but enforce owner check.
    """
    owner = _get_session_owner(sid)
    if owner and owner != sub:
        return None
    return _get_doc_for_user_or_global(sub, sid)

def _save_user_session(sub: str, sid: str, title: str, messages: list) -> None:
    existing = _get_doc_for_user_or_global(sub, sid)
    created_at = existing.get("created_at") if existing else _now_iso()

    merged_messages = _merge_messages(existing.get("messages", []) if existing else [], messages)

    doc = {
        "id": sid,
        "title": (title or "Untitled Chat").strip() or "Untitled Chat",
        "messages": merged_messages,
        "created_at": created_at,
        # updated_at set inside _save_doc_both
    }
    _save_doc_both(sub, sid, doc, touch_index=True)

def _delete_doc(sub: str, sid: str) -> None:
    k_user = _k_doc(sub, sid)
    pipe = redis_client.pipeline()
    pipe.delete(k_user)
    pipe.zrem(_k_idx(sub), k_user)
    # Keep or remove global? Safer to remove only if caller is owner.
    owner = _get_session_owner(sid)
    if owner == sub:
        pipe.delete(_k_doc_global(sid))
        pipe.delete(_owner_key(sid))
    pipe.execute()

def _update_title(sub: str, sid: str, title: str, touch: bool = False):
    doc = _get_doc_for_user_or_global(sub, sid)
    if not doc:
        raise HTTPException(status_code=404, detail="session_not_found")
    doc["title"] = (title or "Untitled Chat").strip() or "Untitled Chat"
    _save_doc_both(sub, sid, doc, touch_index=touch)

def _seed_history_from_messages(session_id: str, messages: list) -> None:
    """Rebuild chat:{sid}:history for the LLM using stored messages."""
    history_key = f"chat:{session_id}:history"
    redis_client.delete(history_key)

    system_prompt = {
        "role": "system",
        "content": (
            "You are a smart assistant helping users evaluate Crop, PV suitability or basic "
            "Agent-Base Modelling. Avoid unnecessary elaboration."
        ),
    }

    pipe = redis_client.pipeline()
    pipe.rpush(history_key, json.dumps(system_prompt))

    # Only the role/content matter for the agent call; ignore other fields safely.
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            pipe.rpush(history_key, json.dumps({"role": role, "content": content}))
    pipe.expire(history_key, SESSION_TTL_SEC)
    pipe.execute()

    _touch_session_ttl(session_id)

def _parse_ts_for_sort(m: dict) -> float:
    """Best-effort to turn message['timestamp'] into a float epoch; fallback to 0."""
    t = m.get("timestamp")
    if t is None:
        return 0.0
    if isinstance(t, (int, float)):
        return float(t)
    if isinstance(t, str):
        s = t.replace("Z", "+00:00") if t.endswith("Z") else t
        try:
            return datetime.fromisoformat(s).timestamp()
        except Exception:
            logger.exception("Invalid timestamp: %s", s)
            return 0.0
    return 0.0

def _merge_messages(existing: list, incoming: list) -> list:
    """
    Merge client-sent 'incoming' with 'existing' stored on the server.
    Keep uniques from both; prefer incoming order for overlapping items,
    then append any existing items not present in incoming.
    """
    if not existing:
        return list(incoming or [])
    if not incoming:
        return list(existing or [])

    # Use (role, content, timestamp) to detect duplicates.
    def key(m):
        return (m.get("role"), m.get("content"), m.get("timestamp"))

    incoming_keys = {key(m) for m in incoming}
    merged = list(incoming)  # keep client order first

    for m in existing:
        if key(m) not in incoming_keys:
            merged.append(m)

    # Optional: sort strictly by timestamp to keep chronological view
    merged.sort(key=_parse_ts_for_sort)
    return merged

    
# ---------- Async result append ----------
def persist_async_result_to_session(sub: Optional[str], email: Optional[str], session_id: str, result: dict):
    """
    Append an 'assistant' message that matches the SPA's shape,
    then bump updated_at + index ordering.
    """
    # Fallback to mapped owner if we didn't get sub now
    if not sub:
        sub = _get_session_owner(session_id)

    # Load existing (prefer user's doc; fallback to global)
    doc = _get_doc_for_user_or_global(sub or "", session_id) or {
        "id": session_id,
        "title": result.get("title") or "#abm",
        "messages": [],
        "created_at": _now_iso(),
    }

    # --- 1) Carry forward the last known GeoJSON from previous messages ---
    last_geojson = None
    try:
        for m in reversed(doc.get("messages", [])):
            md = m.get("mapData") or {}
            gj = md.get("geoJsonData")
            if gj:
                last_geojson = gj
                break
    except Exception:
        logger.exception("Failed to carry forward last geojson | sess=%s", session_id)
        last_geojson = None

    # Build message in the same structure your SPA already returns from chat
    assistant_msg = {
        "role": "assistant",
        "content": result.get("text", "") or "Results are ready.",
        "timestamp": _now_iso(),
        "activeComponents": {
            "map": bool(result.get("map_layers")),
            "graph": bool(result.get("map_layers")),
            "simple_map": False,
            "bar_chart": bool(result.get("chart_data")),
            "slider": bool(result.get("map_layers"))
        },
        "mapData": {
            "pilotArea": result.get("pilot"),
            "geoJsonData": last_geojson,
            "wmsLayers": result.get("map_layers", []),
            "mapExplanation": result.get("map_explanation")
        },
        "graphData": [],
        "barChartData": result.get("chart_data", []),
        "serviceCalled": result.get("action").capitalize()
    }

    doc.setdefault("messages", []).append(assistant_msg)

    if sub:
        # We know the owner → write per-user + global & bump index
        _save_doc_both(sub, session_id, doc, touch_index=True)
    else:
        # Owner not known yet → write ONLY the global copy (no index, no owner set)
        doc["updated_at"] = _now_ts()
        redis_client.set(_k_doc_global(session_id), json.dumps(doc))
        redis_client.expire(_k_doc_global(session_id), SESSION_TTL_SEC)

    # Seed chat history so continuing this session keeps context
    history_key = f"chat:{session_id}:history"
    redis_client.rpush(history_key, json.dumps({"role": "assistant", "content": assistant_msg["content"]}))
    redis_client.expire(history_key, SESSION_TTL_SEC) 

    _touch_session_ttl(session_id, sub=sub)
    

# ---------- Routes ----------
@router.get("/sessions", response_model=List[SessionSummary])
def list_sessions(user=Depends(require_user)):
    sub = user.get("sub")
    return _list_docs(sub)

@router.get("/sessions/{session_id}")
def get_session(session_id: str, user=Depends(require_user)):
    sub = user.get("sub")
    # Enforce ownership, and read per-user doc with global fallback
    doc = _get_doc_owned(sub, session_id)
    if not doc:
        raise HTTPException(status_code=404, detail="session_not_found")
    return doc

@router.post("/sessions")
def upsert_session(body: SessionUpsert, user=Depends(require_user)):
    sub = user.get("sub")
    # Save both per-user and global docs; bump index
    _save_user_session(sub, body.session_id, body.title or "", body.messages)
    return {"ok": True}

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, user=Depends(require_user)):
    sub = user.get("sub")
    _delete_doc(sub, session_id)
    return {"ok": True}

@router.patch("/sessions/{session_id}/title")
def rename_session(session_id: str, body: SessionTitleUpdate, user=Depends(require_user)):
    sub = user.get("sub")
    _update_title(sub, session_id, body.title, touch=body.touch)
    return {"ok": True}

@router.post("/sessions/{session_id}/seed")
def seed_session_history(session_id: str, user=Depends(require_user)):
    sub = user.get("sub")
    doc = _get_doc_owned(sub, session_id)
    if not doc:
        raise HTTPException(status_code=404, detail="session_not_found")
    _seed_history_from_messages(session_id, doc.get("messages", []))
    return {"ok": True}