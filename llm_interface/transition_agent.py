#!/usr/bin/env python3
"""
TRANSITION LLM Agent - Ask questions, get results!

Usage:
    python transition_agent.py "Simulate wheat land use for 20 years under RCP 4.5"
    python transition_agent.py "Compare RL vs rule-based for 50 years"
    python transition_agent.py "Show me LUSA data for maize"
"""
import os
import sys
import instructor
from openai import OpenAI
from atomic_agents import AtomicAgent, AgentConfig, BaseIOSchema
from atomic_agents.context import SystemPromptGenerator
from pydantic import Field

# Import tools
from mlu_tool import MLUTool, MLUQueryInput
from cca_tool import CCATool, CCAQueryInput
from gcp_tool import GCPTool, GCPQueryInput
from rl_tool import RLTool, RLQueryInput
from irrigation_tool import IrrigationTool, IrrigationQueryInput


class QueryParserInput(BaseIOSchema):
    """Input for query parser"""
    query: str = Field(..., description="User's natural language query")


class QueryParserOutput(BaseIOSchema):
    """Output from query parser - structured parameters"""
    tool: str = Field(..., description="Which tool to use: 'mlu', 'cca', 'gcp', 'rl', 'irrigation', or 'chat' (for casual conversation)")
    user_story: str | None = Field(None, description="Identified user story (e.g., MLU-05, CCA-03, CCA-10, GCP-03, GCP-07, GCP-16)")
    scenario: str | None = Field(None, description="Climate scenario: rcp26, rcp45, rcp85")
    crop: str | None = Field(None, description="Crop type: WHEAT or MAIZE")
    policy: str | None = Field(None, description="Policy scenario: low_support, moderate_support, high_support (GCP only)")
    years: int | None = Field(None, description="Number of simulation years")
    parcels: int | None = Field(None, description="Number of land parcels (MLU only)")
    farmers: int | None = Field(None, description="Number of farmer agents (CCA only)")
    landowners: int | None = Field(None, description="Number of landowner agents (GCP only)")
    pv_developers: int | None = Field(None, description="Number of PV developer agents (CCA only)")
    ensemble_size: int | None = Field(None, description="Ensemble size for uncertainty quantification (MLU only)")
    enable_ensemble: bool | None = Field(None, description="Enable/disable ensemble mode (True/False/None for default, MLU only)")
    timesteps: int | None = Field(None, description="RL training timesteps")
    operation: str | None = Field(None, description="RL operation: 'train' or 'compare'")
    # Multi-level ABM parameters (all use cases)
    collectives: int | None = Field(None, description="Number of farmer collectives/cooperatives (Community Level - MLU/CCA only)")
    markets: int | None = Field(None, description="Number of commodity markets (Market Level - MLU/CCA only)")
    financial_institutions: int | None = Field(None, description="Number of financial institutions/banks (Market Level - GCP only)")
    policymakers: int | None = Field(None, description="Number of policymaker agents (Policy Level)")
    # Spatial filtering
    geojson_file: str | None = Field(None, description="Path to GeoJSON file for polygon-based spatial filtering")
    # User-specified farmer/parcel locations with initial crops
    farmer_locations: list[dict] | None = Field(None, description="List of farmer/parcel locations with initial crops. Each dict: {lat: float, lon: float, crop: str}")
    # Irrigation-specific parameters
    start_date: str | None = Field(None, description="Start date for EO data download (YYYY-MM-DD format, irrigation only)")
    end_date: str | None = Field(None, description="End date for EO data download (YYYY-MM-DD format, irrigation only)")


def create_query_parser():
    """Create LLM-powered query parser using GPT-4"""

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: Set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY='your-key'")
        sys.exit(1)

    # Setup OpenAI client with instructor
    client = instructor.from_openai(OpenAI(api_key=api_key))

    # System prompt for query parsing
    system_prompt = SystemPromptGenerator(
        background=[
            "You are an intelligent assistant for the TRANSITION ML-ABM system.",
            "TRANSITION models climate-resilient agriculture using multi-level agent-based simulations.",
            "You can handle BOTH casual conversation AND simulation requests.",
            "TRANSITION has four main use cases:",
            "  - MLU (Multi-Land Use): Agricultural vs Solar PV land use decisions",
            "  - CCA (Climate Change Adaptation): Farmer adaptation strategies, PV adoption, climate resilience",
            "  - GCP (Green Credit Policy): Green loans and subsidies for PV installations by landowners",
            "  - Irrigation: EO-informed irrigation water management with NDVI/NDWI-based crop classification",
        ],
        steps=[
            "STEP 0 (CRITICAL - MUST DO FIRST): Determine query type:",
            "   - If query is casual conversational (greetings, thanks, general questions, small talk) → Set tool='chat' and STOP HERE",
            "   - If query requests a simulation, analysis, or data operation → Continue to step 1",
            "   - IMPORTANT: Only casual/conversational queries should use tool='chat'. Simulation requests go to 'mlu', 'cca', 'gcp', 'rl', or 'irrigation'",
            "1. Identify which tool is needed: 'mlu', 'cca', 'gcp', 'rl', 'irrigation', or 'chat'",
            "   Tool detection logic (CHECK IN ORDER - PRIORITY MATTERS!):",
            "   a) IRRIGATION (HIGHEST PRIORITY): If query mentions 'irrigation' OR 'bare soil' OR 'ndvi classification' OR 'ndwi' OR 'water management' OR 'crop classification' OR 'fallow detection' OR 'phenology' OR 'temporal analysis' OR 'time-series' OR 'seasonal evolution' → 'irrigation' (MUST include date range!)",
            "   b) If query mentions 'pv installation' OR 'pv suitability' OR 'solar installation' OR 'solar suitability' OR 'energy company' OR 'best for solar' OR 'parcels for pv' → 'cca' (CCA-04: PV Suitability)",
            "   c) If query mentions 'cross-scale' OR 'feedback' OR 'farmer to policy' OR 'multi-level interaction' → 'cca' (CCA-10: Cross-Scale)",
            "   d) If query mentions 'training' OR 'RL' OR 'reinforcement learning' OR 'compare rl' → 'rl'",
            "   e) If query mentions 'green credit' OR 'green loan' OR 'subsidy' OR 'financial institution' OR 'landowner' OR 'pv adoption' OR 'loan approval' OR 'geographic distribution of pv' → 'gcp' (Green Credit Policy)",
            "   IMPORTANT: 'policy impact' OR 'analyze policy' → 'cca' (CCA-10 for climate policy analysis), NOT 'gcp' (GCP is about green credit financial policy)!",
            "   e) If query mentions 'land use' OR 'solar vs agriculture' OR 'parcel decision' OR 'LUSA' OR 'categorization' OR 'land allocation' OR 'farm or solar' OR 'crop suitability map' → 'mlu' (Multi-Land Use)",
            "   f) If query mentions 'yield' OR 'productivity' OR 'harvest' OR 'crop performance' OR 'farmer income' OR 'adaptation strategy' → 'cca' (CCA-03: Crop Yield)",
            "   g) If query mentions 'climate adaptation' OR 'farmer adaptation' OR 'resilience' OR 'vulnerability' → 'cca' (CCA-03)",
            "   h) DEFAULT: If query mentions 'simulate' OR 'wheat' OR 'maize' OR 'farmer' OR ANY crop-related simulation → 'cca' (CCA is default for crop simulations)",
            "   CRITICAL RULES:",
            "   - 'solar installation' OR 'pv suitability' OR 'best for solar' → ALWAYS CCA-04! (NOT MLU!)",
            "   - 'crop yield' OR 'simulate farmers' (without 'markets' or 'parcels') → ALWAYS CCA-03!",
            "   - 'land use decision' OR 'parcel allocation' OR 'LUSA data' → ALWAYS MLU!",
            "   - 'markets' OR 'parcels' keyword → ALWAYS MLU! (even if 'wheat' or 'farmers' mentioned)",
            "   - MLU is about land-use DECISIONS (farm wheat OR farm maize OR install solar PV)",
            "   - CCA-04 is about PV SUITABILITY EVALUATION (which parcels are best for solar installations)",
            "   - CCA-03 is about CROP SIMULATION (farmer crop yield performance and adaptation)",
            "   - 'farmer groups', 'collectives', 'cooperatives' are multi-level PARAMETERS, not use case indicators!",
            "   - When in doubt between MLU and CCA: If query asks 'which parcels are best for X' → CCA (evaluation), if query asks 'simulate land use' → MLU (decision simulation)!",
            "   CRITICAL KEYWORDS FOR TOOL SELECTION (PRIORITY ORDER - check in this order!):",
            "   - HIGHEST PRIORITY: If 'RL' OR 'reinforcement learning' OR 'compare rl' OR 'train rl' mentioned → tool='rl' (RL overrides ALL other keywords!)",
            "   - If 'crop yield' OR 'crop yields' OR 'yield' (and NOT RL query) → tool='cca' (crop yield analysis is CCA-03)",
            "   - If query has CROP NAME + COORDINATES (e.g., 'wheat at (40.5, 22.7)' OR 'maize at (40.6, 22.8)') → tool='cca' (CCA-03: crop simulation at specific locations)",
            "   - If 'pv suitability' OR 'cross-scale interactions' → tool='cca'",
            "   - If 'parcels' mentioned (and NOT RL or yield query, and NOT crop+coordinates) → tool='mlu' (parcels are MLU-only)",
            "   - If 'markets' mentioned (and NOT RL or yield query, and NOT crop+coordinates) → tool='mlu' (markets in MLU context)",
            "   - If 'farmers' mentioned (without 'parcels' or 'markets', and NOT RL query) → tool='cca' (farmers are CCA-only)",
            "   CRITICAL: Coordinates + crop names → CCA (crop simulation), Coordinates WITHOUT crop context → MLU (land use)",
            "   EXAMPLES:",
            "   - 'show crop yields with 2 markets' → tool='cca' (yield keyword takes priority!)",
            "   - 'simulate maize at (40.7, 22.8), wheat at (40.6, 22.7)' → tool='cca' (crop+coordinates = CCA-03!)",
            "   - 'simulate land use with 5 collectives and 2 markets' → tool='mlu' (no yield, has markets → MLU)",
            "   - 'categorize parcels at (40.5, 22.7), (40.6, 22.8)' → tool='mlu' (no crop context, categorization task → MLU-04)",
            "   - 'compare RL versus rule-based with 10 parcels' → tool='rl' (RL keyword overrides parcels!)",
            "2. Detect the user story - CRITICAL DECISION TREE:",
            "   FOR MLU QUERIES:",
            "   a) If query contains 'historical' OR 'land suitability' OR 'benchmark' → MLU-07",
            "   b) If query contains 'climate evolution' OR 'temperature change' OR 'precipitation' OR 'future climate scenarios' → MLU-08",
            "   c) If query contains 'categorize' OR 'classify' → MLU-04",
            "   d) If query contains 'LUSA data' OR 'view data' OR 'access data' → MLU-01",
            "   e) Otherwise (generic 'simulate') → MLU-05",
            "   FOR CCA QUERIES:",
            "   a) If query contains 'cross-scale' OR 'multi-level' OR 'feedback loop' OR 'interactions' OR 'policy impact' OR 'policy effect' OR 'analyze policy' OR 'policy influence' → CCA-10",
            "   b) If query contains 'pv' OR 'solar' OR 'photovoltaic' OR 'renewable energy' OR 'energy company' → CCA-04",
            "   c) If query contains 'crop yield' OR 'climate adaptation' OR 'farmer' OR 'resilience' OR 'vulnerability' → CCA-03",
            "   d) Default → CCA-03 (most common)",
            "   FOR GCP QUERIES (PRIORITY ORDER - check in this exact order! MUST check BEFORE moving to next!):",
            "   a) If query contains 'feedback loop' OR 'policy feedback' OR 'financial feedback' OR 'policy adjustment' OR 'monitor feedback' → GCP-16 (STOP HERE)",
            "   b) If query contains 'geographic' OR 'geographic distribution' OR 'map' OR 'spatial' OR 'where' OR 'location' OR 'view geographic' OR 'show map' OR 'distribution of pv' OR 'distribution of solar' → GCP-07 (STOP HERE)",
            "   c) If query contains 'pv adoption' OR 'green credit' OR 'subsidy' OR 'landowner' OR 'loan' (and NO map/geographic keywords) → GCP-03 (STOP HERE)",
            "   d) Default → GCP-03 (most common)",
            "   CRITICAL: 'map' OR 'geographic' takes ABSOLUTE PRIORITY over 'pv adoption'!",
            "   EXAMPLE: 'map pv adoption' → GCP-07 (NOT GCP-03) because 'map' keyword present!",
            "   EXAMPLE: 'view geographic distribution of solar installations' → GCP-07 (NOT GCP-03) because 'view geographic' present!",
            "   CRITICAL: 'historical' OR 'benchmark' = MLU-07 (static data comparison)",
            "   CRITICAL: 'land suitability' = MLU-07, NOT MLU-05!",
            "3. Extract climate scenario (accepts user-friendly names OR RCP codes):",
            "   User-friendly: 'optimistic'→'rcp26', 'moderate'→'rcp45', 'pessimistic'→'rcp85'",
            "   RCP codes: 'RCP 2.6'→'rcp26', 'RCP 4.5'→'rcp45', 'RCP 8.5'→'rcp85'",
            "   CRITICAL: If user specifies a scenario, return ONLY that scenario (not all scenarios!)",
            "4. Extract crop type: WHEAT or MAIZE (always extract if user mentions it)",
            "   - 'wheat' → WHEAT, 'maize' → MAIZE, 'corn' → MAIZE",
            "5. Extract numeric parameters (CRITICAL: ONLY extract what user EXPLICITLY mentions - do NOT fill in defaults!):",
            "   IMPORTANT: Look for numbers followed by keywords, including 'using', 'with', 'for' prefixes!",
            "   CRITICAL: Scan the ENTIRE query for ALL numbers - extract EVERY parameter mentioned!",
            "   - years: 'X years', 'for X years', 'over X years', 'simulate X years', '5 years' → years=X",
            "   - parcels: 'X parcels', 'with X parcels', 'simulate X parcels', 'for 10 parcels' → parcels=X (MLU/RL ONLY)",
            "   - farmers: 'X farmers', 'with X farmers', 'simulate X farmers' → farmers=X (CCA/IRRIGATION)",
            "   SPECIAL CASE: If routing to 'cca' but query says 'parcels', interpret it as 'farmers' (users may use parcels/farmers interchangeably)!",
            "   - landowners: 'X landowners', 'with X landowners', 'simulate X landowners' → landowners=X (GCP ONLY)",
            "   SPECIAL CASE: If routing to 'gcp' but query says 'farmers', interpret it as 'landowners' (users may use farmers/landowners interchangeably)!",
            "   SPECIAL CASE: If routing to 'irrigation' but query says 'parcels', interpret it as 'farmers' (users may use parcels/farmers interchangeably)!",
            "   - pv_developers: 'X energy companies', 'X pv developers', 'X developers' → pv_developers=X (CCA-04)",
            "   - ensemble_size: 'X realizations', 'ensemble size X', 'X runs', 'ensemble size 3' → ensemble_size=X (MLU-08)",
            "   - timesteps: 'X timesteps', 'X steps' → timesteps=X (RL only)",
            "   - collectives: 'X collectives', 'X cooperatives', 'using X collectives', 'with X collectives' → collectives=X (MLU/CCA/IRRIGATION)",
            "   - markets: 'X markets', 'using X markets', 'with X markets' → markets=X (MLU/CCA ONLY)",
            "   - financial_institutions: 'X financial institutions', 'X banks', 'X financial instructors', 'using X banks', 'with X financial institutions' → financial_institutions=X (GCP ONLY)",
            "   - policymakers: 'X policymakers', 'X policies', 'X water authorities', 'using X policymakers', 'with X policymakers', 'with X water authorities' → policymakers=X",
            "   CRITICAL: Extract ALL numbers mentioned! 'using 5 policymakers and 6 financial institutions' MUST extract policymakers=5 AND financial_institutions=6!",
            "   EXAMPLE: 'for 10 parcels for 5 years with ensemble size 3' → parcels=10, years=5, ensemble_size=3 (extract ALL THREE numbers!)",
            "6. Extract policy scenario (GCP ONLY):",
            "   - 'low support', 'low_support' → policy='low_support'",
            "   - 'moderate support', 'moderate_support' → policy='moderate_support'",
            "   - 'high support', 'high_support' → policy='high_support'",
            "7. Extract geojson file path (if mentioned):",
            "   - Look for file paths like '/path/to/file.geojson', 'polygon.json', or 'geojson file at X'",
            "   - If user mentions 'draw', 'polygon', 'area', 'geojson' WITHOUT a file path → geojson_file=None (user will draw interactively)",
            "   - If no geojson mentioned → geojson_file=None",
            "8. Extract farmer/parcel locations with initial crops (CRITICAL - HIGH PRIORITY!):",
            "   - PATTERNS TO DETECT (check for these EXACT patterns in query!):",
            "     • 'wheat at (40.5, 22.7)' → EXTRACT coordinates!",
            "     • 'wheat at 40.5, 22.7' → EXTRACT coordinates!",
            "     • 'maize at (40.6, 22.8)' → EXTRACT coordinates!",
            "     • 'crop at lat, lon' or 'crop at (lat, lon)' → EXTRACT!",
            "   - HOW TO PARSE:",
            "     • Extract latitude (first number) and longitude (second number)",
            "     • Extract crop name before 'at' keyword",
            "     • Normalize crop to uppercase: 'wheat'→'WHEAT', 'maize'→'MAIZE'",
            "     • Build list of dicts: [{'lat': float, 'lon': float, 'crop': str}]",
            "   - EXAMPLES (MUST MATCH THESE EXACTLY!):",
            "     • Input: 'wheat at (40.5, 22.7)' → Output: farmer_locations=[{'lat': 40.5, 'lon': 22.7, 'crop': 'WHEAT'}]",
            "     • Input: 'wheat at 40.5, 22.7 and maize at 40.6, 22.8' → Output: farmer_locations=[{'lat': 40.5, 'lon': 22.7, 'crop': 'WHEAT'}, {'lat': 40.6, 'lon': 22.8, 'crop': 'MAIZE'}]",
            "     • Input: 'simulate for 10 years' → Output: farmer_locations=None (no coordinates mentioned)",
            "   - CRITICAL: If you see 'at' followed by numbers with decimals → EXTRACT AS COORDINATES!",
            "   - If no coordinates mentioned → farmer_locations=None",
            "9. Detect ensemble mode:",
            "   - 'with uncertainty', 'probabilistic', 'ensemble', 'Monte Carlo' → enable_ensemble=True",
            "   - 'no uncertainty', 'single run', 'deterministic' → enable_ensemble=False",
            "   - Not mentioned → enable_ensemble=None (use default)",
            "10. For RL queries, identify operation: 'train' or 'compare'",
        ],
        output_instructions=[
            "Return ONLY the extracted parameters",
            "DEFAULT VALUES POLICY:",
            "  - CRITICAL: DO NOT fill in default values! Only extract what the user EXPLICITLY mentions!",
            "  - If a parameter is not mentioned by the user → return None (Python code will handle defaults and notify user)",
            "  - ONLY set a parameter if the user EXPLICITLY specified it in their query",
            "Tool detection: 'rl' if query mentions training/comparison/RL, otherwise 'mlu'",
            "Scenario parsing (accept both user-friendly and RCP codes - CRITICAL: Always extract scenario!):",
            "  - User-friendly: 'optimistic'→'rcp26', 'moderate'→'rcp45', 'pessimistic'→'rcp85'",
            "  - Phrase variations: 'under moderate scenario'→'rcp45', 'for moderate climate'→'rcp45', 'moderate warming'→'rcp45'",
            "  - RCP codes: 'RCP 2.6'→'rcp26', 'RCP 4.5'→'rcp45', 'RCP 8.5'→'rcp85'",
            "  - CRITICAL: If user says 'moderate', 'optimistic', or 'pessimistic' ANYWHERE in query → extract the scenario!",
            "Crop parsing: case-insensitive, return uppercase (WHEAT, MAIZE)",
            "Parameter extraction (CRITICAL: Extract ALL numbers from query!):",
            "  - Years: 'for 20 years' → years=20, 'for 5 years' → years=5, 'over 10 years' → years=10",
            "  - Parcels: 'with 30 parcels' → parcels=30, 'for 10 parcels' → parcels=10, '15 parcels' → parcels=15",
            "  - Ensemble: '50 realizations' → ensemble_size=50, 'ensemble size 3' → ensemble_size=3, 'ensemble size 30' → ensemble_size=30",
            "  - EXAMPLE QUERY: 'for 10 parcels for 5 years with ensemble size 3' → parcels=10, years=5, ensemble_size=3",
            "  - Ensemble mode: 'with uncertainty' → enable_ensemble=True, 'no uncertainty' → enable_ensemble=False",
            "  - Collectives: '5 collectives' → collectives=5, '3 cooperatives' → collectives=3, 'using 4 collectives' → collectives=4",
            "  - Markets: '2 markets' → markets=2, '1 commodity market' → markets=1, 'with 3 markets' → markets=3",
            "  - Policymakers: '3 policymakers' → policymakers=3, '1 policy agent' → policymakers=1, 'using 5 policymakers' → policymakers=5",
            "  - Farmers/Landowners (INTERCHANGEABLE): '20 farmers' in GCP query → landowners=20, '30 landowners' in GCP query → landowners=30",
            "  - If not specified → None (DO NOT assume defaults)",
            "User story detection - PRIORITY ORDER (check in this order!):",
            "  1. If 'historical' OR 'land suitability' OR 'benchmark' → MLU-07",
            "  2. If 'climate evolution' OR 'temperature' OR 'precipitation' OR 'future climate scenarios' → MLU-08",
            "  3. If 'categorize' OR 'classify' → MLU-04",
            "  4. If 'LUSA data' OR 'view data' → MLU-01",
            "  5. Otherwise → MLU-05 (default agent simulation)",
            "CRITICAL EXAMPLES (IMPORTANT: Only show parameters EXPLICITLY mentioned - omit unmentioned params!):",
            "  MLU Examples:",
            "  - 'benchmark historical vs future' → tool='mlu', user_story='MLU-07', crop=None, scenario=None, years=None, parcels=None",
            "  - 'simulate wheat under moderate scenario for 20 years' → tool='mlu', user_story='MLU-05', crop='WHEAT', scenario='rcp45', years=20, parcels=None",
            "  - 'pessimistic scenario for maize with ensemble' → tool='mlu', user_story='MLU-08', crop='MAIZE', scenario='rcp85', years=None, parcels=None",
            "  - 'simulate 20 parcels with 5 collectives and 2 markets' → tool='mlu', parcels=20, collectives=5, markets=2, years=None",
            "  - 'simulate wheat with 5 collectives and 2 markets under moderate scenario' → tool='mlu', crop='WHEAT', scenario='rcp45', collectives=5, markets=2, years=None, parcels=None",
            "  - 'show land use decisions with 15 parcels, 3 farmer groups, 2 markets' → tool='mlu', parcels=15, collectives=3, markets=2, years=None",
            "  - 'simulate for 20 years with 3 farmer groups and 2 markets' → tool='mlu', years=20, collectives=3, markets=2, parcels=None [markets keyword → MLU]",
            "  CCA Examples:",
            "  - 'wheat yield under optimistic scenario' → tool='cca', user_story='CCA-03', crop='WHEAT', scenario='rcp26', years=None, farmers=None",
            "  - 'simulate wheat yield under moderate climate' → tool='cca', user_story='CCA-03', crop='WHEAT', scenario='rcp45', years=None, farmers=None",
            "  - 'evaluate pv suitability pessimistic scenario with 2 energy companies' → tool='cca', user_story='CCA-04', scenario='rcp85', pv_developers=2, farmers=None",
            "  - 'show cross-scale interactions under rcp 4.5' → tool='cca', user_story='CCA-10', scenario='rcp45', years=None, farmers=None",
            "  - 'simulate 20 farmers with 3 cooperatives and 2 policymakers' → tool='cca', farmers=20, collectives=3, policymakers=2, years=None",
            "  - 'show crop yields with 20 parcels under pessimistic scenario' → tool='cca', user_story='CCA-03', farmers=20, scenario='rcp85', years=None [parcels→farmers mapping for CCA!]",
            "  - 'simulate wheat under moderate scenario for 10 years with 25 parcels using 5 policymakers' → tool='mlu', user_story='MLU-05', crop='WHEAT', scenario='rcp45', years=10, parcels=25, policymakers=5",
            "  RL Examples:",
            "  - 'compare RL versus rule-based decisions under moderate scenario for 5 years with 10 parcels' → tool='rl', scenario='rcp45', years=5, parcels=10",
            "  - 'compare RL vs rules for 50 years under pessimistic scenario' → tool='rl', scenario='rcp85', years=50, parcels=None",
            "  - 'train RL model under optimistic scenario for 100000 timesteps' → tool='rl', scenario='rcp26', timesteps=100000",
            "  GCP Examples:",
            "  - 'simulate pv adoption with moderate support under optimistic scenario' → tool='gcp', user_story='GCP-03', scenario='rcp26', policy='moderate_support', landowners=None, years=None",
            "  - 'simulate pv adoption with 22 farmers under moderate support policy' → tool='gcp', user_story='GCP-03', policy='moderate_support', landowners=22, scenario=None, years=None [farmers→landowners mapping for GCP!]",
            "  - 'view geographic distribution of solar installations with 50 landowners' → tool='gcp', user_story='GCP-07', landowners=50, policy=None, scenario=None [CRITICAL: 'view geographic' triggers GCP-07!]",
            "  - 'map pv adoption under low support policy' → tool='gcp', user_story='GCP-07', policy='low_support', scenario=None, landowners=None [CRITICAL: 'map' triggers GCP-07!]",
            "  - 'geographic distribution of pv with high support under pessimistic scenario' → tool='gcp', user_story='GCP-07', scenario='rcp85', policy='high_support', landowners=None",
            "  - 'show map of solar installations under moderate support' → tool='gcp', user_story='GCP-07', policy='moderate_support', scenario=None, landowners=None",
            "  - 'monitor policy feedback loop under moderate scenario for 15 years with 30 landowners' → tool='gcp', user_story='GCP-16', scenario='rcp45', years=15, landowners=30, policy=None",
            "  - 'simulate pv adoption with 20 landowners using 5 financial institutions and 3 policymakers' → tool='gcp', landowners=20, financial_institutions=5, policymakers=3, scenario=None, policy=None",
            "  - 'map pv adoption under low support with 6 banks and 2 policymakers' → tool='gcp', user_story='GCP-07', policy='low_support', financial_institutions=6, policymakers=2, scenario=None",
            "  Custom Farmer/Parcel Locations Examples (NEW - ADVANCED FEATURE - MUST EXTRACT COORDINATES!):",
            "  CRITICAL DISTINCTION:",
            "  - MLU: Land use allocation (agriculture vs solar PV) - Use tool='mlu' for land use simulation with coordinates",
            "  - CCA: Crop performance (wheat vs maize yield) - Use tool='cca' ONLY if query explicitly mentions 'yield', 'adaptation', 'resilience'",
            "  - DEFAULT: Coordinates without explicit yield/adaptation keywords → tool='mlu' (land use simulation)",
            "  EXAMPLES:",
            "  - 'simulate wheat at (40.5, 22.7) under moderate scenario for 10 years' → tool='mlu', user_story='MLU-05', farmer_locations=[{'lat': 40.5, 'lon': 22.7, 'crop': 'WHEAT'}], scenario='rcp45', years=10, parcels=None",
            "  - 'simulate maize at (40.7, 22.8), wheat at (40.6, 22.7) for 15 years' → tool='mlu', user_story='MLU-05', farmer_locations=[{'lat': 40.7, 'lon': 22.8, 'crop': 'MAIZE'}, {'lat': 40.6, 'lon': 22.7, 'crop': 'WHEAT'}], years=15, parcels=None",
            "  - 'simulate wheat YIELD at (40.5, 22.7) for 10 years' → tool='cca', user_story='CCA-03', farmer_locations=[{'lat': 40.5, 'lon': 22.7, 'crop': 'WHEAT'}], years=10, farmers=None",
            "  - 'categorize parcels at (40.5, 22.7), (40.6, 22.8) under moderate scenario' → tool='mlu', user_story='MLU-04', farmer_locations=[{'lat': 40.5, 'lon': 22.7, 'crop': 'WHEAT'}, {'lat': 40.6, 'lon': 22.8, 'crop': 'WHEAT'}], scenario='rcp45', parcels=None",
            "  - 'simulate 10 years: wheat at (40.6, 22.7), maize at (40.7, 22.8) with 5 collectives and 2 markets' → tool='mlu', user_story='MLU-05', farmer_locations=[...], collectives=5, markets=2, parcels=None",
            "  CRITICAL: Coordinates → DEFAULT tool='mlu' (land use), UNLESS query has 'yield'/'adaptation' keywords → tool='cca'!",
            "  CRITICAL: If farmer_locations extracted, parcels/farmers MUST be None!",
            "  Backward compatibility (RCP codes still work):",
            "  - 'wheat under rcp 45' → scenario='rcp45'",
            "  - 'rcp 8.5 scenario' → scenario='rcp85'",
            "  - 'compare RL under rcp45' → tool='rl', scenario='rcp45'",
        ]
    )

    # Create agent with custom schemas as type parameters
    agent = AtomicAgent[QueryParserInput, QueryParserOutput](
        config=AgentConfig(
            client=client,
            model="gpt-4o-mini",  # Fast and cost-effective
            #model="gpt-4o",
            system_prompt_generator=system_prompt
            # Note: schemas NOT in config - they're type parameters above!
        )
    )

    return agent


def main():
    """Main CLI interface"""
    import argparse

    # Parse arguments
    parser_args = argparse.ArgumentParser(description="TRANSITION LLM Agent", add_help=False)
    parser_args.add_argument("query", nargs="*", help="Natural language query")
    parser_args.add_argument("--geojson-file", type=str, default=None,
                           help="Path to GeoJSON file for spatial filtering")

    # If no arguments, show help
    if len(sys.argv) < 2:
        print("Usage: python transition_agent.py \"Your question here\" [--geojson-file PATH]")
        print("\n📊 MLU Examples (Multi-Land Use):")
        print("  python transition_agent.py \"Show LUSA data for wheat under moderate scenario\"")
        print("  python transition_agent.py \"Simulate land use under moderate scenario for 10 years with 15 parcels\"")
        print("  python transition_agent.py \"Show future climate scenarios for wheat under pessimistic scenario with ensemble size 10\"")
        print("\n🌱 CCA Examples (Climate Change Adaptation):")
        print("  python transition_agent.py \"Simulate wheat yield under moderate scenario for 10 years with 20 farmers\"")
        print("  python transition_agent.py \"Evaluate PV suitability under optimistic scenario with 2 energy companies\"")
        print("  python transition_agent.py \"Show cross-scale interactions under moderate scenario for 10 years\"")
        print("\n💰 GCP Examples (Green Credit Policy):")
        print("  python transition_agent.py \"Simulate PV adoption under moderate support with optimistic scenario and 20 farmers\"")
        print("  python transition_agent.py \"Map PV adoption under low support policy with pessimistic scenario\"")
        print("  python transition_agent.py \"Monitor feedback loops under moderate scenario for 15 years with 30 landowners\"")
        print("\n🤖 RL Examples (Reinforcement Learning):")
        print("  python transition_agent.py \"Compare RL vs rule-based decisions under moderate scenario for 50 years with 30 parcels\"")
        print("\n💧 Irrigation Examples (EO-Informed Water Management - IRR-US-01: Bare Soil Classification):")
        print("  \n  📍 With user-drawn polygon (random sampling):")
        print("    python transition_agent.py \"Classify bare soil from July 15 to August 31, 2023\" --geojson-file polygon.geojson")
        print("    python transition_agent.py \"Detect bare soil in my polygon from 2023-07-01 to 2023-08-31 with 10 parcels\" --geojson-file polygon.geojson")
        print("  \n  📌 With GPS coordinates (NO polygon needed!):")
        print("    python transition_agent.py \"Analyze bare soil at (40.5, 22.7) from July 15 to July 22, 2023\"")
        print("    python transition_agent.py \"Detect bare soil at (40.5, 22.7) and (40.6, 22.8) from summer 2023\"")
        print("  \n  🗺️  With drawn field polygons (full polygon analysis - most accurate!):")
        print("    python transition_agent.py \"Classify my 3 fields using bare soil analysis from July to August 2023\" --geojson-file fields.geojson")
        print("  \n  ⚠️  IMPORTANT: Always use 'bare soil' or 'bare parcels' keywords (NOT 'no vegetation' - triggers MLU!)")
        print("\n🗺️ With Spatial Filtering:")
        print("  python transition_agent.py \"Simulate wheat under moderate scenario\" --geojson-file /path/to/polygon.geojson")
        sys.exit(1)

    args = parser_args.parse_args()
    user_query = " ".join(args.query)
    geojson_file_path = args.geojson_file

    # Load GeoJSON if provided
    geojson_data = None
    if geojson_file_path:
        try:
            with open(geojson_file_path, 'r') as f:
                import json
                geojson_data = json.load(f)
            print(f"📍 Loaded GeoJSON from: {geojson_file_path}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Warning: Could not load GeoJSON file: {e}", file=sys.stderr)
            geojson_data = None

    parser = create_query_parser()

    try:
        # DETERMINISTIC PRE-CHECK: CCA vs MLU routing
        # KEY DISTINCTION:
        # - MLU: Land allocation (agriculture vs solar PV) - "land use", "parcels", "markets", "categorize"
        # - CCA: Crop performance (wheat vs maize yield) - "yield", "climate adaptation", "resilience"
        # COORDINATES ALONE don't determine use case - context matters!

        import re
        query_lower = user_query.lower()

        # Irrigation keywords: EO-informed water management (HIGHEST PRIORITY FOR IRRIGATION QUERIES)
        has_irrigation = any(kw in query_lower for kw in [
            'irrigation', 'bare soil', 'ndvi classification', 'ndwi', 'water management',
            'crop classification', 'fallow detection', 'classify soil', 'detect bare'
        ])

        # RL keywords: Reinforcement learning (HIGH PRIORITY - overrides all other keywords except irrigation)
        # Must check for "rl" in context of comparison/training, not just any "rl" substring
        has_rl = any(kw in query_lower for kw in [' rl ', 'reinforcement learning', 'compare rl', 'train rl', 'rl vs', 'rl versus', 'benchmark rl', 'rl against']) or query_lower.startswith('rl ') or query_lower.endswith(' rl')

        # GCP keywords: Green credit policy, PV adoption, feedback loops (HIGH PRIORITY - before CCA-04 and CCA-10)
        has_gcp = any(kw in query_lower for kw in [
            'green credit', 'green loan', 'subsidy', 'financial institution', 'bank', 'loan approval',
            'pv adoption', 'solar adoption', 'support policy', 'low support', 'moderate support', 'high support',
            'feedback loop', 'policy feedback', 'monitor feedback', 'track subsidy', 'subsidy effectiveness',
            'loan portfolio', 'financial risk', 'default rate'
        ])

        # MLU-08 keywords: Future climate scenarios with ensemble (HIGH PRIORITY)
        has_mlu_08 = any(kw in query_lower for kw in ['future climate', 'climate scenario', 'climate evolution', 'temperature change', 'precipitation', 'ensemble', 'uncertainty'])

        # MLU-07 keywords: Historical/future land suitability comparison (HIGH PRIORITY)
        # "benchmark" without "rl" context
        has_mlu_07_benchmark = 'benchmark' in query_lower and not has_rl
        has_mlu_07 = has_mlu_07_benchmark or any(kw in query_lower for kw in ['suitability evolution', 'suitability changes', 'historical vs future', 'compare historical', 'land suitability'])

        # CCA-10 keywords: Cross-scale interactions (MEDIUM PRIORITY)
        has_cca_crossscale = any(kw in query_lower for kw in ['cross-scale', 'cross scale', 'policy impact', 'policy effect', 'analyze policy', 'feedback loop', 'interaction'])

        # CCA-04 keywords: PV suitability EVALUATION (MEDIUM PRIORITY - must be specific to evaluation)
        # Only match if query asks "which parcels are BEST" or "evaluate suitability"
        has_cca_pv_suitability = any(kw in query_lower for kw in ['pv suitability', 'solar suitability', 'evaluate pv', 'best for solar', 'pv potential', 'energy company'])

        # CCA-03 keywords: yield, adaptation, resilience (crop performance focus)
        has_cca_yield = any(kw in query_lower for kw in ['yield', 'crop performance', 'climate adaptation', 'resilience', 'vulnerability'])

        # MLU keywords: land use decision, parcels, markets, categorization
        has_mlu_landuse = any(kw in query_lower for kw in ['land use', 'parcel', 'categorize', 'classify', 'lusa data'])

        # Markets keyword: If query has "markets" → MLU (commodity markets are MLU-specific)
        # BUT: "markets" with cross-scale/policy keywords → CCA-10 (markets as infrastructure parameter)
        has_markets = 'market' in query_lower

        # Default: If no explicit keywords, coordinates+crops → MLU (land use simulation is default for coordinates)
        coord_pattern = r'\(?\s*\d+\.?\d*\s*,\s*\d+\.?\d*\s*\)?'
        has_coordinates = bool(re.search(coord_pattern, query_lower))

        # Decision logic (PRIORITY ORDER)
        force_tool = None
        if has_irrigation:
            # Irrigation: EO-informed water management (HIGHEST PRIORITY FOR IRRIGATION)
            force_tool = 'irrigation'
            print(f"🎯 Detected Irrigation keywords (bare soil/NDVI classification) → Forcing tool='irrigation'", file=sys.stderr)
        elif has_rl:
            # RL: Reinforcement learning (HIGH PRIORITY - overrides all keywords except irrigation)
            force_tool = 'rl'
            print(f"🎯 Detected RL keywords (reinforcement learning/compare RL) → Forcing tool='rl'", file=sys.stderr)
        elif has_gcp:
            # GCP: Green credit policy, PV adoption
            force_tool = 'gcp'
            print(f"🎯 Detected GCP keywords (green credit/PV adoption/support policy) → Forcing tool='gcp'", file=sys.stderr)
        elif has_mlu_08:
            # MLU-08: Future climate scenarios with ensemble
            force_tool = 'mlu'
            print(f"🎯 Detected MLU-08 keywords (future climate scenarios) → Forcing tool='mlu'", file=sys.stderr)
        elif has_mlu_07:
            # MLU-07: Historical/future land suitability comparison
            force_tool = 'mlu'
            print(f"🎯 Detected MLU-07 keywords (land suitability evolution) → Forcing tool='mlu'", file=sys.stderr)
        elif has_cca_crossscale:
            # CCA-10: Cross-scale interactions
            force_tool = 'cca'
            print(f"🎯 Detected CCA-10 keywords (cross-scale/policy) → Forcing tool='cca'", file=sys.stderr)
        elif has_cca_pv_suitability:
            # CCA-04: PV suitability evaluation (must be specific to evaluation)
            force_tool = 'cca'
            print(f"🎯 Detected CCA-04 keywords (PV suitability evaluation) → Forcing tool='cca'", file=sys.stderr)
        elif has_cca_yield:
            # CCA-03: Crop yield/adaptation
            force_tool = 'cca'
            print(f"🎯 Detected CCA-03 keywords (yield/adaptation) → Forcing tool='cca'", file=sys.stderr)
        elif has_mlu_landuse or has_markets:
            # MLU: Land use decision
            force_tool = 'mlu'
            print(f"🎯 Detected MLU keywords (land use/parcels/markets) → Forcing tool='mlu'", file=sys.stderr)
        elif has_coordinates:
            # Coordinates without explicit keywords → MLU (default for land-use simulation with coordinates)
            force_tool = 'mlu'
            print(f"🎯 Detected coordinates without explicit keywords → Defaulting to tool='mlu' (land use simulation)", file=sys.stderr)

        # Call GPT-4o-mini API (silently)
        parsed = parser.run(QueryParserInput(query=user_query))

        # DEBUG: Show what LLM extracted
        print(f"\n🔍 LLM EXTRACTION DEBUG:", file=sys.stderr)
        print(f"   tool={parsed.tool}, user_story={parsed.user_story}", file=sys.stderr)
        print(f"   scenario={parsed.scenario}, crop={parsed.crop}, policy={parsed.policy}", file=sys.stderr)
        print(f"   years={parsed.years}, parcels={parsed.parcels}, farmers={parsed.farmers}, landowners={parsed.landowners}", file=sys.stderr)
        print(f"   collectives={parsed.collectives}, markets={parsed.markets}, policymakers={parsed.policymakers}", file=sys.stderr)

        # FALLBACK: If LLM failed to extract scenario, try regex (user-friendly names + RCP codes)
        if not parsed.scenario:
            query_lower = user_query.lower()
            # User-friendly scenario names (PRIMARY)
            if 'optimistic' in query_lower:
                parsed.scenario = 'rcp26'
                print(f"🔧 FALLBACK: Extracted scenario='rcp26' from 'optimistic' keyword", file=sys.stderr)
            elif 'moderate' in query_lower:
                parsed.scenario = 'rcp45'
                print(f"🔧 FALLBACK: Extracted scenario='rcp45' from 'moderate' keyword", file=sys.stderr)
            elif 'pessimistic' in query_lower:
                parsed.scenario = 'rcp85'
                print(f"🔧 FALLBACK: Extracted scenario='rcp85' from 'pessimistic' keyword", file=sys.stderr)
            # RCP codes (FALLBACK)
            elif 'rcp 2.6' in query_lower or 'rcp2.6' in query_lower or 'rcp26' in query_lower:
                parsed.scenario = 'rcp26'
                print(f"🔧 FALLBACK: Extracted scenario='rcp26' from RCP code", file=sys.stderr)
            elif 'rcp 4.5' in query_lower or 'rcp4.5' in query_lower or 'rcp45' in query_lower:
                parsed.scenario = 'rcp45'
                print(f"🔧 FALLBACK: Extracted scenario='rcp45' from RCP code", file=sys.stderr)
            elif 'rcp 8.5' in query_lower or 'rcp8.5' in query_lower or 'rcp85' in query_lower:
                parsed.scenario = 'rcp85'
                print(f"🔧 FALLBACK: Extracted scenario='rcp85' from RCP code", file=sys.stderr)

        # FALLBACK: If LLM failed to extract crop, try regex
        if not parsed.crop:
            query_lower = user_query.lower()
            if 'maize' in query_lower or 'corn' in query_lower:
                parsed.crop = 'MAIZE'
                print(f"🔧 FALLBACK: Extracted crop='MAIZE' from query keywords", file=sys.stderr)
            elif 'wheat' in query_lower:
                parsed.crop = 'WHEAT'
                print(f"🔧 FALLBACK: Extracted crop='WHEAT' from query keywords", file=sys.stderr)

        # FALLBACK: If LLM failed to extract numeric parameters, try regex
        import re
        query_lower = user_query.lower()

        # Extract markets (e.g., "3 markets", "with 2 markets")
        if parsed.markets is None:
            markets_match = re.search(r'(\d+)\s*markets?', query_lower)
            if markets_match:
                parsed.markets = int(markets_match.group(1))
                print(f"🔧 FALLBACK: Extracted markets={parsed.markets} from query", file=sys.stderr)

        # Extract collectives (e.g., "5 collectives", "3 cooperatives")
        if parsed.collectives is None:
            collectives_match = re.search(r'(\d+)\s*(collectives?|cooperatives?)', query_lower)
            if collectives_match:
                parsed.collectives = int(collectives_match.group(1))
                print(f"🔧 FALLBACK: Extracted collectives={parsed.collectives} from query", file=sys.stderr)

        # Extract policymakers (e.g., "3 policymakers", "2 policies")
        if parsed.policymakers is None:
            policymakers_match = re.search(r'(\d+)\s*(policymakers?|policies)', query_lower)
            if policymakers_match:
                parsed.policymakers = int(policymakers_match.group(1))
                print(f"🔧 FALLBACK: Extracted policymakers={parsed.policymakers} from query", file=sys.stderr)

        # Extract financial institutions (e.g., "3 financial institutions", "5 banks", "2 markets" for GCP)
        # NOTE: In GCP context, "markets" = financial institutions (banks providing loans)
        if parsed.financial_institutions is None:
            # Try "financial institutions", "banks", "financial instructors" (common typo)
            fi_match = re.search(r'(\d+)\s*(financial\s+institutions?|financial\s+instructors?|banks?)', query_lower)
            if fi_match:
                parsed.financial_institutions = int(fi_match.group(1))
                print(f"🔧 FALLBACK: Extracted financial_institutions={parsed.financial_institutions} from query", file=sys.stderr)
            elif any(keyword in query_lower for keyword in ['gcp', 'pv', 'solar', 'adoption', 'subsidy', 'feedback', 'loan', 'credit', 'green']):
                # In GCP context, "markets" might mean financial institutions (banks)
                markets_for_gcp = re.search(r'(\d+)\s*markets?', query_lower)
                if markets_for_gcp:
                    parsed.financial_institutions = int(markets_for_gcp.group(1))
                    print(f"🔧 FALLBACK: Extracted financial_institutions={parsed.financial_institutions} from 'markets' (GCP context)", file=sys.stderr)

        # OVERRIDE based on keyword detection
        if force_tool and parsed.tool != force_tool:
            print(f"⚠️  OVERRIDE: LLM said tool='{parsed.tool}', but keywords/context indicate tool='{force_tool}'", file=sys.stderr)
            parsed.tool = force_tool
            # Clear user_story so the individual tool (MLU/CCA/GCP) can identify correct user story
            # using its own keyword matcher
            parsed.user_story = None
            print(f"🔄 Cleared user_story - letting {force_tool.upper()} tool identify correct user story", file=sys.stderr)

        # Validate query specificity - detect vague queries
        if parsed.tool in ["mlu", "cca", "gcp"]:
            query_lower = user_query.lower()
            has_simulate = "simulate" in query_lower
            has_suitability = "suitability" in query_lower or "lusa" in query_lower
            has_crop = any(crop in query_lower for crop in ["wheat", "maize", "corn"])
            has_use_case = any(keyword in query_lower for keyword in [
                "land use", "parcel", "crop yield", "pv", "solar",
                "cross-scale", "farmer", "adaptation", "landowner", "green credit", "loan"
            ])

            # If user says "simulate" but doesn't specify WHAT, reject it
            if has_simulate and not has_crop and not has_use_case:
                print("❌ ERROR: Please specify what to simulate")
                print("❌ Your query is too vague. Please be more specific about what you want to simulate.")
                print("❌ Examples:")
                print("❌    - 'Simulate wheat yield under moderate scenario for 10 years with 20 farmers' (CCA-03: Crop Yield)")
                print("❌    - 'Simulate land use under moderate scenario for 10 years with 15 parcels' (MLU-05: Land Use)")
                print("❌    - 'Show cross-scale interactions under moderate scenario for 10 years' (CCA-10: Multi-level)")
                print("❌    - 'Simulate PV adoption under moderate support with optimistic scenario' (GCP-03: PV Adoption)")
                sys.exit(1)


        # Execute tool
        if parsed.tool == "chat":
            # Handle casual conversation with ChatGPT
            from openai import OpenAI
            chat_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = chat_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for the TRANSITION project - a Multi-Level Agent-Based Modeling system for climate change adaptation, land use simulations, and crop yield predictions. Be friendly, concise, and informative. If users ask what you can do, mention examples like 'Simulate wheat yield under moderate scenario for 10 years with 20 farmers' (CCA), 'Show LUSA data for wheat under moderate scenario' (MLU), or 'Map PV adoption under low support policy with pessimistic scenario' (GCP)."},
                    {"role": "user", "content": user_query}
                ]
            )

            print("="*80)
            print("RESPONSE")
            print("="*80)
            print(f"\n{response.choices[0].message.content}\n")
            return

        elif parsed.tool == "mlu":
            tool = MLUTool()
            result = tool.run(MLUQueryInput(
                query=user_query,
                user_story=parsed.user_story,  # Pass GPT-4 identified user story
                scenario=parsed.scenario,
                crop=parsed.crop,
                years=parsed.years,
                parcels=parsed.parcels,
                ensemble_size=parsed.ensemble_size,
                enable_ensemble=parsed.enable_ensemble,
                collectives=parsed.collectives,
                markets=parsed.markets,
                policymakers=parsed.policymakers,
                geojson_file=geojson_file_path or parsed.geojson_file,  # CLI arg overrides LLM extraction
                farmer_locations=parsed.farmer_locations  # NEW - 2025-10-21: User-specified coordinates
            ))
        elif parsed.tool == "cca":
            tool = CCATool()
            result = tool.run(CCAQueryInput(
                query=user_query,
                user_story=parsed.user_story,  # Pass GPT-4 identified user story
                scenario=parsed.scenario,
                crop=parsed.crop,
                years=parsed.years,
                farmers=parsed.farmers,
                pv_developers=parsed.pv_developers,
                collectives=parsed.collectives,
                markets=parsed.markets,
                policymakers=parsed.policymakers,
                geojson_file=geojson_file_path or parsed.geojson_file,  # CLI arg overrides LLM extraction
                farmer_locations=parsed.farmer_locations  # NEW - 2025-10-21: User-specified coordinates
            ))
        elif parsed.tool == "gcp":
            tool = GCPTool()
            result = tool.run(GCPQueryInput(
                query=user_query,
                user_story=parsed.user_story,
                scenario=parsed.scenario,
                policy=parsed.policy,
                years=parsed.years,
                landowners=parsed.landowners,
                financial_institutions=parsed.financial_institutions,
                policymakers=parsed.policymakers,
                geojson_file=geojson_file_path or parsed.geojson_file,  # CLI arg overrides LLM extraction
                farmer_locations=parsed.farmer_locations  # NEW - 2025-10-21: User-specified coordinates
            ))
        elif parsed.tool == "rl":
            tool = RLTool()
            result = tool.run(RLQueryInput(
                query=user_query,
                scenario=parsed.scenario,
                years=parsed.years,
                parcels=parsed.parcels,
                collectives=parsed.collectives,
                markets=parsed.markets,
                policymakers=parsed.policymakers,
                timesteps=parsed.timesteps,
                geojson_file=geojson_file_path or parsed.geojson_file  # CLI arg overrides LLM extraction
            ))
        elif parsed.tool == "irrigation":
            from irrigation_tool import IrrigationToolConfig
            tool = IrrigationTool(IrrigationToolConfig(geojson_state=geojson_data))

            # SPECIAL CASE: Irrigation uses 'parcels' field but LLM extracts 'farmers'
            # Convert farmers → parcels for irrigation tool
            irrigation_parcels = parsed.parcels
            if irrigation_parcels is None and parsed.farmers is not None:
                irrigation_parcels = parsed.farmers
                print(f"🔄 Converted farmers={parsed.farmers} → parcels={irrigation_parcels} for irrigation", file=sys.stderr)

            result = tool.run(IrrigationQueryInput(
                query=user_query,
                user_story=parsed.user_story,
                start_date=parsed.start_date,
                end_date=parsed.end_date,
                parcels=irrigation_parcels,
                parcel_locations=None,  # Will be extracted from query if coordinates present
                use_polygons=False,  # Default to point mode, will auto-detect if user draws multiple polygons
                collectives=parsed.collectives,
                policymakers=parsed.policymakers,  # Pass policymakers to irrigation tool
                geojson_file=parsed.geojson_file
            ))
        else:
            print(f"❌ ERROR: Unknown tool: {parsed.tool}")
            sys.exit(1)

        # Print result (especially important for errors)
        if result.status == "error":
            # Print error result to stdout for backend to capture
            print(result.result, flush=True)
            sys.exit(1)

        # Print detailed result output (for terminal debugging)
        if result.result:
            print(result.result, flush=True)

        # Print files for backend to parse
        print(f"\n[DEBUG] Found {len(result.output_files)} output files", flush=True)
        if result.output_files:
            for f in result.output_files:
                print(f"FILE: {f}", flush=True)
        else:
            # If no files, print a success message so backend has something to parse
            user_story = getattr(result, 'user_story', parsed.tool.upper())
            print(f"✅ {user_story} simulation completed successfully", flush=True)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
