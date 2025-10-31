# MLU User Stories - Implementation Status

## ✅ Implemented User Stories

### MLU-04: Categorize Land Parcels Using AI Models
- **Status**: ✅ Fully Complete
- **What it does**:
  - Uses AI techniques (LUSA predictions) to analyze EO and socioeconomic data
  - Categorizes land parcels based on suitability for agriculture (WHEAT/MAIZE) or solar PV
  - Considers: soil quality, crop resilience, solar potential, environmental constraints
  - Provides visualizations with clear labeling (blue=WHEAT, orange=MAIZE, yellow=SOLAR)
  - **NEW**: Automatic comparison across ALL future climate scenarios (Optimistic, Moderate, Pessimistic)
- **Climate Scenarios**:
  - **optimistic** (Low Warming ~2°C) - Ambitious mitigation
  - **moderate** (Medium Warming ~3°C) - Moderate mitigation
  - **pessimistic** (High Warming ~4-5°C) - High emissions
- **How to run**:
  - **All scenarios (recommended)**: `python run_mlu.py --query mlu_04 --parcels 15` (runs all scenarios + creates comparison charts)
  - User-friendly: `python run_mlu.py --query mlu_04 --scenario moderate --parcels 15`
  - Traditional RCP codes: `python run_mlu.py --query mlu_04 --scenario rcp45 --parcels 15` (still supported)
- **Outputs**:
  - **Per scenario**:
    - `results/mlu_04_{scenario}/gis_map.html` - Interactive GIS map with toggleable layers (WHEAT/MAIZE suitability heatmaps + categorized parcels)
    - `results/mlu_04_{scenario}/category_distribution.html` - Bar chart showing parcel category distribution
  - **Comparison (all scenarios mode)**:
    - `results/mlu_04_comparison/scenario_comparison_bar.html` - Grouped bar chart comparing categories across scenarios
    - `results/mlu_04_comparison/scenario_comparison_percentage.html` - Stacked percentage chart showing distribution shifts under different climate pathways

### MLU-05: Analyze Land Suitability Using Multi-Level ABM
- **Status**: ✅ Fully Complete
- **What it does**:
  - Simulates agent-based interactions between land parcels, community agents (collectives), market agents, and policymakers
  - Incorporates real-time feedback loops (environmental: climate/soil + socioeconomic: prices/subsidies)
  - **"Dynamic" outputs**: Interactive time-series showing how agents adjust behaviors over time (e.g., parcels switch from solar to agriculture when wheat prices rise)
  - **4-Level Multi-Level ABM**: Individual → Community → Market → Policy (enabled by default)
  - **Switch tracking**: Monitors both total switches AND switch types (WHEAT→SOLAR, MAIZE→WHEAT, etc.)
- **Climate Scenarios**:
  - **optimistic** (Low Warming ~2°C), **moderate** (Medium Warming ~3°C), **pessimistic** (High Warming ~4-5°C)
- **Multi-Level Configuration** (NEW):
  - **Default**: 2 collectives, 1 market, 1 policymaker (config.yaml)
  - **Custom**: Specify via `--collectives N --markets N --policies N` flags
  - **Disable**: Use `--disable-multilevel` for individual agents only
  - **LLM Interface**: Natural language support (e.g., "simulate with 5 collectives and 2 markets")
- **How to run**:
  - **All scenarios (recommended)**: `python run_mlu.py --query mlu_05 --years 10 --parcels 15` (runs all scenarios + creates comparison)
  - User-friendly: `python run_mlu.py --query mlu_05 --scenario moderate --years 10 --parcels 15`
  - **Custom multi-level**: `python run_mlu.py --query mlu_05 --scenario moderate --years 10 --parcels 15 --collectives 5 --markets 2 --policies 3`
  - Traditional RCP codes: `python run_mlu.py --query mlu_05 --scenario rcp45 --years 10 --parcels 15` (still supported)
  - Disable multi-level: `python run_mlu.py --query mlu_05 --scenario moderate --years 10 --disable-multilevel` (individual level only)
  - **LLM Interface**: `python llm_interface/transition_agent.py "Simulate wheat with 5 collectives and 2 markets under moderate scenario"`
- **Advanced: User-Specified Farmer Locations** (NEW - 2025-10-21):
  - Specify exact GPS coordinates with initial crops instead of random selection
  - Coordinates must be within Thessaloniki bounds (40.4-40.9°N, 22.5-22.9°E)
  - Coordinates must be within user-drawn polygon (if provided)
  - Valid crops: WHEAT, MAIZE
  - Agents can still switch crops dynamically in subsequent years based on market conditions
  - **CLI Example**:
    ```bash
    python run_mlu.py --query mlu_05 --scenario moderate --years 10 \
      --farmer-locations '[{"lat":40.5,"lon":22.7,"crop":"WHEAT"},{"lat":40.6,"lon":22.8,"crop":"MAIZE"}]'
    ```
  - **LLM Interface Examples**:
    ```bash
    # Single location
    python llm_interface/transition_agent.py "Simulate wheat at (40.5, 22.7) under moderate scenario for 10 years"

    # Multiple locations
    python llm_interface/transition_agent.py "Simulate 10 years: wheat at (40.5, 22.7), maize at (40.6, 22.8) under moderate scenario"

    # With multi-level agents
    python llm_interface/transition_agent.py "Simulate wheat at (40.5, 22.7) with 3 collectives and 2 markets under pessimistic scenario for 15 years"
    ```
  - **Validation**:
    - ✅ Coordinates checked against data bounds (Thessaloniki region)
    - ✅ Coordinates validated against drawn polygon (if provided)
    - ✅ Crop names validated (must be WHEAT or MAIZE)
    - ✅ Agent initialized with user-specified crop in first year
    - ✅ Agent retains dynamic decision-making in subsequent years
  - **Backward Compatibility**: Existing `--parcels N` parameter still works (random selection)
- **Outputs** (Simplified, focused on dynamic behavior):
  - **Per scenario**:
    - `results/mlu_05_{scenario}/land_use_evolution.html` - **Stacked area chart** showing land use changes over time (WHEAT/MAIZE/SOLAR)
    - `results/mlu_05_{scenario}/price_dynamics.html` - **Line chart** showing wheat/maize prices over time (what drives decisions)
    - `results/mlu_05_{scenario}/decision_switches.html` - **Bar chart** showing how many parcels changed crops each year
  - **Comparison (when running all scenarios)**:
    - `results/mlu_05_comparison/final_land_use_comparison.html` - Final land allocation across scenarios (grouped bar)
    - `results/mlu_05_comparison/decision_switches_comparison.html` - Total switches across scenarios (bar chart)
    - `results/mlu_05_comparison/switch_types_breakdown.html` - **Switch types breakdown** showing WHAT switches happened (e.g., WHEAT→SOLAR: 5, MAIZE→WHEAT: 3) - stacked bar chart
- **Key feature**: All charts are interactive (hover for details, zoom, pan) showing the **"dynamic"** evolution of the system
- **Recent fixes**:
  - ✅ Unified land use tracking (crops + solar PV)
  - ✅ Filtered out UNASSIGNED states (no more "None→WHEAT" switches)
  - ✅ Proper solar PV detection in switch tracking

### MLU-07: Integrate Historical EO Data for Benchmarking
- **Status**: ✅ Fully Complete
- **What it does**:
  - **Directly loads and compares LUSA NetCDF files** (no simulation needed!)
  - Compares historical LUSA predictions (1990-2020) vs future LUSA predictions (2021-2100)
  - **Filters to Thessaloniki region only** (40.4-40.9°N, 22.5-22.9°E (EXACT meteorological bounds))
  - Shows how crop suitability changes under different climate scenarios
  - Creates geographic heatmaps showing where suitability improves/degrades
  - Generates benchmark report with percentage changes
- **Climate Scenarios**:
  - **optimistic** (Low Warming ~2°C), **moderate** (Medium Warming ~3°C), **pessimistic** (High Warming ~4-5°C)
- **Data sources** (configurable in `config.yaml`):
  - **Historical LUSA**: `WHEAT/PAST_LUSA_PREDICTIONS.nc`, `MAIZE/PAST_LUSA_PREDICTIONS.nc`
  - **Future LUSA**: `WHEAT/RCP26_LUSA_PREDICTIONS.nc`, `MAIZE/RCP26_LUSA_PREDICTIONS.nc` (same for RCP45, RCP85)
  - **Note**: LUSA files use 0-100 scale (not 0-1) and cover all of Greece (filtered to Thessaloniki in code)
- **How to run**:
  - **All scenarios (default)**: `python run_mlu.py --query mlu_07` (compares historical + all future scenarios)
  - User-friendly: `python run_mlu.py --query mlu_07 --scenario moderate` (compares historical vs moderate only)
  - Traditional RCP codes: `python run_mlu.py --query mlu_07 --scenario rcp45` (compares historical vs RCP45 only)
- **Outputs** (4 visualizations):
  - `results/mlu_07/lusa_suitability_evolution.html` - **Line chart** showing WHEAT and MAIZE suitability over time (0-100 scale, Thessaloniki region mean)
  - `results/mlu_07/suitability_change_heatmap.html` - **Geographic heatmap** showing where suitability increased (green) or decreased (red) for each crop × scenario
  - `results/mlu_07/suitability_statistics.html` - **Bar chart** comparing mean suitability across historical and future scenarios
  - `results/mlu_07/benchmark_report.txt` - **Text report** with percentage changes and statistics
- **Key features**:
  - ✅ Direct NetCDF comparison (fast, no simulation overhead)
  - ✅ Regional filtering to Thessaloniki (not all Greece)
  - ✅ Correct 0-100 LUSA score scale
  - ✅ Historical baseline (1990-2020) vs future projections (2021-2100)
  - ✅ **LUSA suitability scores** visualization (fulfills "view land-use suitability scores" requirement)
  - ✅ Geographic change heatmaps (identifies improvement/degradation zones)
  - ✅ Percentage change calculations for all scenarios
  - ✅ Interactive Plotly charts with shadcn styling
- **Utility script**: `use_cases/mlu/scripts/inspect_netcdf.py` - Inspect any NetCDF file structure and data

### MLU-08: Simulate Future Climate Scenarios
- **Status**: ✅ **FULLY COMPLETE** - All requirements fulfilled
- **What it does**:
  - ✅ **Simulates future climate scenarios** with different emissions pathways
  - ✅ **Shows climate evolution** (temperature, precipitation) for different time horizons (2021-2030, extendable to 2100)
  - ✅ **Dynamically updates suitability scores** - LUSA predictions are climate-dependent (AI-computed responses to temperature/precipitation)
  - ✅ **Visual feedback on uncertainties** - Ensemble bands showing range of possible outcomes (±1.5°C temp, ±10 points suitability)
  - ✅ **Demonstrates climate-suitability relationships** - Side-by-side visualization showing how suitability responds to climate changes
- **Climate scenarios** (configured in `config.yaml`):
  - **optimistic** (Low Warming ~2°C): Aggressive mitigation, +1.5-2°C by 2100
  - **moderate** (Medium Warming ~3°C): Moderate mitigation, +2-3°C by 2100
  - **pessimistic** (High Warming ~4-5°C): Business-as-usual, +4-5°C by 2100
- **Data sources**:
  - Climate data: `meteo/tas_{scenario}.nc`, `pr_{scenario}.nc`
  - LUSA data: `WHEAT/RCP{26,45,85}_LUSA_PREDICTIONS.nc`, `MAIZE/RCP{26,45,85}_LUSA_PREDICTIONS.nc`
- **How to run**:
  - **All scenarios (default)**: `python run_mlu.py --query mlu_08` (runs all scenarios)
  - User-friendly: `python run_mlu.py --query mlu_08 --scenario moderate`
  - Traditional RCP codes: `python run_mlu.py --query mlu_08 --scenario rcp45` (still supported)
- **Outputs**:
  - `results/mlu_08/climate_scenarios.html` - **Climate evolution** showing temperature and precipitation divergence across scenarios
  - `results/mlu_08/suitability_response.html` - **Suitability response** showing how WHEAT/MAIZE suitability dynamically responds to climate
  - `results/mlu_08/uncertainty_ensemble.html` - **Uncertainty bands** showing ensemble spread (temperature ±1.5°C, suitability ±10 points)
- **Key features**:
  - ✅ Multi-scenario comparison (RCP26/45/85)
  - ✅ Climate evolution visualization (temperature + precipitation over time)
  - ✅ Dynamic suitability response - LUSA AI model computes suitability based on climate inputs
  - ✅ Uncertainty quantification with ensemble bands (±1.5°C, ±10 points)
  - ✅ Regional filtering to Thessaloniki (40.4-40.9°N, 22.5-22.9°E - EXACT meteorological bounds)
  - ✅ Interactive Plotly charts with shadcn styling
  - ✅ Clear visual feedback on climate-suitability relationships
- **How it fulfills requirements**:
  - ✅ "Simulate future climate conditions for different time horizons" → Shows 2021-2030 (data available), LUSA extends to 2100
  - ✅ "Dynamically update suitability scores based on climate inputs" → LUSA predictions ARE climate-dependent (AI model trained on climate data)
  - ✅ "Visual feedback on uncertainties with ensemble projections" → Uncertainty bands with ±1.5°C and ±10 points showing range of outcomes
- **Data source**: Uses real LUSA AI predictions that incorporate climate variables (temperature, precipitation, solar radiation) in their suitability computations

---

## 🔧 Configuration System

### Config-Based Data Paths & Coordinates
- **Status**: ✅ Implemented
- **What it does**:
  - All data file paths and filenames centralized in `config.yaml`
  - **Thessaloniki coordinates** centralized in config (single source of truth)
  - Easy to change data locations or region without editing code
  - Smart fallback to hardcoded paths if config unavailable
  - **Automatic handling** of descending latitude in meteorological files
- **Configuration file**: `use_cases/mlu/config.yaml`
- **Key sections**:
  - `data.base_path` - Base directory for all data files
  - `data.subdirs` - Subdirectory names (meteo, soil, Historical, etc.)
  - `data.files` - All filename patterns with {scenario} placeholders
  - `region` - **Thessaloniki coordinates** (lat_min, lat_max, lon_min, lon_max)
  - `region.lat_descending` - Handles descending latitude in meteorological files
- **Example**:
  ```yaml
  data:
    base_path: "/home/ggous/Downloads/PILOT_THESSALONIKI_DATA"
    files:
      historical_temperature: "ERA5_LAND_TMP_MEAN.nc"
      temperature: "tas_{scenario}.nc"
  region:
    lat_min: 40.4  # Exact bounds from evptsp_rcp85.nc
    lat_max: 40.9
    lon_min: 22.5
    lon_max: 22.9
    lat_descending: true  # Meteorological files have descending lat
  ```
- **How to use**:
  ```python
  from use_cases.mlu.config_loader import load_config
  config = load_config()

  # Automatic slice direction based on file type
  lat_slice = config.get_lat_slice(for_lusa=False)  # Meteorological files
  lon_slice = config.get_lon_slice()
  ds.sel(lat=slice(*lat_slice), lon=slice(*lon_slice))
  ```
- **How to change**: Edit `config.yaml` - no code changes needed!
- **Benefits**:
  - ✅ Single source of truth for coordinates
  - ✅ Automatic handling of descending/ascending latitude
  - ✅ All MLU scripts load from same config
  - ✅ Easy to change region or data paths

---

**Summary**: 4 user stories fully implemented (MLU-04, MLU-05, MLU-07, MLU-08)

**Last Updated**: 2025-10-20 (MLU-01 removed - not needed)
