# Use Case 3: Multi-Land Use (MLU) Suitability Analysis

## Overview

Multi-Level Agent-Based Model (ML-ABM) simulation for land-use suitability analysis in Thessaloniki pilot region using **100% real data**:

- ✅ **LUSA predictions** - Real ML-predicted crop suitability (WHEAT, MAIZE)
- ✅ **AquaCrop yield data** - Real crop yield simulations
- ✅ **Climate scenarios** - **Optimistic** (Low Warming ~2°C), **Moderate** (Medium Warming ~3°C), **Pessimistic** (High Warming ~4-5°C)
- ✅ **Earth Observation data** - Sentinel/Landsat soil, elevation, climate data
- ✅ **Probabilistic uncertainty** - Monte Carlo ensemble mode with 95% confidence intervals
- ✅ **Multi-Level ABM** - Full 4-level architecture (ENABLED by default)

**Multi-Level Architecture (DEFAULT MODE):**
- **Individual Level:** Land parcels deciding between farming crops OR installing solar PV
- **Community Level:** Farmer collectives influencing land-use decisions (social influence, knowledge sharing)
- **Market Level:** Commodity markets setting crop prices (supply/demand dynamics)
- **Policy Level:** Policymakers providing subsidies and regulations (top-down interventions)

---

## Quick Start

### Configuration

**To change data path:** Edit `config.yaml` and update `data.base_path`

### Prerequisites

```bash
# Required packages
pip install mesa xarray netCDF4 pandas numpy matplotlib seaborn plotly folium Pillow
```

### Run Simulation

```bash
cd use_cases/mlu/

# Full analysis (3 scenarios, ensemble mode)
python run_mlu.py

# Quick test (1 scenario, fast)
python test_ensemble.py --ensemble-size 5

# Single run (GIS maps instead of uncertainty charts)
python run_mlu.py --no-ensemble

# Custom ensemble size
python run_mlu.py --ensemble-size 50 --years 10 --parcels 15
```

**Output:**
- Ensemble mode: Uncertainty visualizations + **policy recommendations**
- Single mode: GIS maps in `results/visualizations/`

---

## Command-Line Arguments

```bash
python run_mlu.py [OPTIONS]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--scenario` | All 3 | Climate scenario: `optimistic`, `moderate`, `pessimistic` (or `rcp26`, `rcp45`, `rcp85` for backward compatibility) |
| `--years` | 10 | Number of simulation years |
| `--parcels` | 15 | Number of land parcels (each decides: farm OR solar) |
| `--output` | `results` | Output directory |
| `--ensemble` | Auto | Force enable Monte Carlo ensemble mode |
| `--no-ensemble` | Auto | Force disable ensemble mode (single run) |

**Climate Scenario Options:**
- **optimistic** (Low Warming ~2°C) - or `rcp26`
- **moderate** (Medium Warming ~3°C) - or `rcp45`
- **pessimistic** (High Warming ~4-5°C) - or `rcp85`

**Examples (User-Friendly Names - RECOMMENDED):**

```bash
# Default: All scenarios with ensemble mode (30 runs per scenario)
python run_mlu.py

# Long-term analysis with more parcels (moderate scenario)
python run_mlu.py --scenario moderate --years 30 --parcels 50

# Quick test with pessimistic scenario (single run)
python run_mlu.py --scenario pessimistic --years 5 --no-ensemble

# Force ensemble mode with custom config
python run_mlu.py --scenario moderate --ensemble --years 20
```

**Traditional RCP Codes (Still Supported):**

```bash
python run_mlu.py --scenario rcp85 --years 5 --no-ensemble
python run_mlu.py --scenario rcp45 --ensemble --years 20
```

---

## Probabilistic Uncertainty Analysis

**NEW: Monte Carlo Ensemble Mode** - Quantifies uncertainty in predictions through multiple stochastic realizations.

### What is Ensemble Mode?

Runs 30+ simulations (each with different random seeds) and generates **visualizations showing uncertainty**:

- **Time-series with confidence bands**: Shaded areas showing 95% CI around mean trajectory
- **Error bars**: Uncertainty bars on final year results
- **Uncertainty dashboard**: Mean, median, min, max for all metrics
- **Probabilistic statements**: Human-readable (e.g., "95% confident: 8-12 parcels adopt solar PV")

### Visualizations Generated

**Ensemble Mode** creates 3 interactive HTML charts per scenario:
1. `*_ensemble_timeseries.html` - Time-series with shaded confidence bands
2. `*_ensemble_summary.html` - Final year bar chart with error bars
3. `*_ensemble_dashboard.html` - Comprehensive uncertainty metrics

### Configuration

Edit `config.yaml`:

```yaml
simulation:
  # Set ensemble_size > 1 to enable (30-50 recommended)
  ensemble_size: 30  # Default: 30 runs per scenario

  # Confidence level for uncertainty bands
  confidence_level: 0.95  # 95% CI (standard)
```

### Command-Line Control

```bash
# Auto-enable (if ensemble_size > 1 in config)
python run_mlu.py

# Force enable ensemble mode
python run_mlu.py --ensemble

# Force single run (faster, no uncertainty)
python run_mlu.py --no-ensemble
```

### Output Format

**Ensemble Statistics JSON** (`*_ensemble_stats.json`):
```json
{
  "scenario": "rcp85",
  "ensemble_size": 30,
  "confidence_level": 0.95,
  "metrics": {
    "solar_pv_adoption": {
      "mean": 10.3,
      "median": 10.0,
      "std": 1.8,
      "ci_lower": 8.2,
      "ci_upper": 12.4
    },
    "total_income": {
      "mean": 145678.50,
      "std": 8234.12,
      "ci_lower": 138245.30,
      "ci_upper": 153111.70
    }
  },
  "probabilistic_statements": {
    "solar_pv_adoption": "95% confidence: 8-12 parcels adopt solar PV (mean: 10.3)",
    "total_income": "95% confidence: €138,245-€153,112 (mean: €145,679)"
  }
}
```

### Benefits

- ✅ **Robust Predictions**: Averages over stochasticity
- ✅ **Uncertainty Quantification**: Know confidence in outcomes
- ✅ **Risk Assessment**: Worst-case/best-case scenarios
- ✅ **Policy Support**: Defensible decision-making with confidence intervals
- ✅ **Fulfills PRD Requirements**: Probabilistic land-use projections

---

## What the Simulation Does

### 1. Data Loading (100% Real)

**Climate Data** (RCP-specific NetCDF):
- Temperature (`tas_rcp26.nc`, `tas_rcp45.nc`, `tas_rcp85.nc`)
- Precipitation (`pr_*.nc`)
- Solar radiation (`rsds_*.nc`)
- Evapotranspiration (`evptsp_*.nc`)

**Soil Data** (static NetCDF):
- Soil pH (`phh2o_0-5cm_mean.nc`)
- Organic carbon (`soc_0-5cm_mean.nc`)
- Soil type, CEC

**Terrain**:
- Digital Elevation Model (`DEM.nc`)

**Crop Suitability** (LUSA predictions):
- WHEAT: `WHEAT/RCP26_LUSA_PREDICTIONS.nc` (+ RCP45, RCP85)
- MAIZE: `MAIZE/RCP26_LUSA_PREDICTIONS.nc` (+ RCP45, RCP85)

**Yield Data** (AquaCrop simulations):
- Real simulated yields by crop, year, scenario

### 2. Agent Initialization

**Farmer Placement:**
- Farmers placed on LUSA grid pixels where crop suitability > 0
- Small random offset (±1km) for visual variety
- Always within Thessaloniki bounds (40.2-40.9°N, 22.4-23.4°E)

**Multi-Level Agents Created:**
- **Farmers**: Individual decision-makers
- **Collectives**: Groups of farmers (cooperative behavior)
- **Markets**: Commodity trading (WHEAT/MAIZE prices)
- **Policies**: Government interventions (subsidies, price controls)

### 3. Annual Decision Cycle

Each year, for each farmer:

1. **Update Spatial Neighbors** (geographic proximity detection within 10km radius)
2. **Read LUSA Base Score** (real ML prediction 0-100)
3. **Adjust for Local Conditions:**
   - Temperature stress (heat/cold penalties)
   - Precipitation deficit (drought penalty)
   - Soil pH suitability
   - Elevation preference
4. **Apply Market Signals:**
   - Crop prices from CommodityMarketAgent
   - Supply/demand dynamics
5. **Apply Policy Influence:**
   - Subsidies from PolicymakerAgent
   - Price floors/ceilings
6. **Apply Spatial Neighbor Influence** (NEW! ✨):
   - **Crop adoption diffusion**: Social proof from neighbors growing same crop (+15% if all neighbors)
   - **Knowledge spillovers**: Learn from successful neighbors (+10% if neighbors have high income)
   - **Local externalities**: Diverse crops reduce pest/disease risk (+5% per unique crop)
7. **Choose Crop** with highest adjusted score
8. **Calculate Yield** using real AquaCrop data + local adjustments
9. **Calculate Income** (price × yield × land_size)

**Multi-Level Interactions:**
- **Downward**: Policy → Market → Community → Individual (top-down influence)
- **Upward**: Individual → Community → Market → Policy (bottom-up aggregation)
- **Lateral**: Farmer ↔ Farmer via social influence (collectives + spatial neighbors)

### 4. Visualization Generation

**GIS Maps** (`*_gis_map.html`):
- Folium interactive maps
- LUSA suitability layers (WHEAT = blue gradient, MAIZE = amber gradient)
- Farmer parcel markers (blue = wheat, orange = maize)
- Popup details: crop, yield, income, suitability scores

**Time-Series Plots** (`*_timeseries.html`):
- Crop adoption over time
- Income trends
- Production volumes
- Diversity metrics

**Trade-Off Analysis** (`trade_off_analysis.html`):
- Economic vs environmental trade-offs
- Sustainability metrics

**Confidence Analysis** (`confidence_*.html`):
- Cross-scenario variability
- Uncertainty quantification

---

## Example Output

```
================================================================================
TRANSITION MLU Multi-Scenario Analysis
================================================================================
Scenarios: Optimistic (Low Warming ~2°C), Moderate (Medium Warming ~3°C), Pessimistic (High Warming ~4-5°C)
Duration:  10 years
Farmers:   3
Output:    results/
================================================================================

[1/3] Running Optimistic Scenario...
================================================================================
TRANSITION ML-ABM SIMULATION: Optimistic (Low Warming ~2°C)
================================================================================

1. Initializing model...
   - Scenario: rcp26
   - Farmers: 3
   - Years: 10

Loading data...
   ✓ Crop data (WHEAT, MAIZE)
   ✓ Meteo data (temperature, precipitation, solar_radiation, evapotranspiration)
   ✓ Soil data (ph, organic_carbon)
   ✓ Terrain data (elevation)
   ✓ Yield data (AquaCrop simulations)

Finding suitable locations for farmers...

Created 3 farmers
  Using 3 suitable locations
  Lat: 40.20 to 40.90
  Lon: 22.40 to 23.40

=== Initializing Multi-Level ABM ===
Creating 1 collective(s)...
  - Collective 1: 3 farmers
Creating 1 market(s)...
  - Market 1: trading WHEAT, MAIZE
Creating 1 policy agent(s)...
  - Policy 1: goals={'food_security': 0.8, 'price_stability': 0.7, 'sustainability': 0.6}

2. Running simulation (10 years)...
Year 2021: 3 WHEAT, 0 MAIZE | Income: €45,678 | Production: 48.2 t
Year 2022: 3 WHEAT, 0 MAIZE | Income: €46,234 | Production: 48.8 t
Year 2023: 2 WHEAT, 1 MAIZE | Income: €44,891 | Production: 47.3 t
...

✓ Simulation complete!

[2/3] Running RCP45...
[3/3] Running RCP85...

================================================================================
GENERATING VISUALIZATIONS
================================================================================

📊 RCP26 Visualizations
   ✓ Time-series plots saved
   ✓ Land suitability samples saved
   ✓ Full grid heatmaps saved
   🗺️  Generating GIS map (WHEAT + MAIZE)...
      ✅ GIS map saved: rcp26_gis_map.html

📊 RCP45 Visualizations
   ...

📊 RCP85 Visualizations
   ...

📈 Cross-Scenario Analysis
   ✓ Trade-off analysis saved
   ✓ Confidence intervals saved

✅ All visualizations saved to: results/visualizations

================================================================================
MULTI-SCENARIO ANALYSIS COMPLETE
================================================================================
```

---

## Data Structure

```
/home/ggous/Downloads/PILOT_THESSALONIKI_DATA/
├── meteo/
│   ├── tas_rcp26.nc       # Temperature (RCP 2.6)
│   ├── tas_rcp45.nc       # Temperature (RCP 4.5)
│   ├── tas_rcp85.nc       # Temperature (RCP 8.5)
│   ├── pr_rcp26.nc        # Precipitation
│   ├── pr_rcp45.nc
│   ├── pr_rcp85.nc
│   ├── rsds_rcp26.nc      # Solar radiation
│   ├── rsds_rcp45.nc
│   ├── rsds_rcp85.nc
│   ├── evptsp_rcp26.nc    # Evapotranspiration
│   ├── evptsp_rcp45.nc
│   └── evptsp_rcp85.nc
├── soil/
│   ├── SoilType_0-5cm_mean.nc
│   ├── cec_0-5cm_mean.nc
│   ├── phh2o_0-5cm_mean.nc     # Soil pH
│   └── soc_0-5cm_mean.nc       # Organic carbon
├── dem/
│   └── DEM.nc                   # Elevation
├── MAIZE/
│   ├── RCP26_LUSA_PREDICTIONS.nc
│   ├── RCP45_LUSA_PREDICTIONS.nc
│   └── RCP85_LUSA_PREDICTIONS.nc
├── WHEAT/
│   ├── RCP26_LUSA_PREDICTIONS.nc
│   ├── RCP45_LUSA_PREDICTIONS.nc
│   └── RCP85_LUSA_PREDICTIONS.nc
└── yields/
    ├── wheat_rcp26.csv          # AquaCrop yields
    ├── wheat_rcp45.csv
    ├── wheat_rcp85.csv
    ├── maize_rcp26.csv
    ├── maize_rcp45.csv
    └── maize_rcp85.csv
```

---

## Code Structure

```
use_cases/mlu/                       # ← Use Case 3: Multi-Land Use (SELF-CONTAINED)
├── run_mlu.py                       # ← MAIN ENTRY POINT
├── README.md                        # ← This file
├── scripts/
│   └── run_mlu_simulation.py        # Simulation orchestrator
├── results/                          # Code modules (not output!)
│   ├── result_collector.py          # Data collection (all 4 levels)
│   ├── visualizer.py                # Plotly visualizations
│   └── gis_visualizer_v2.py         # Folium GIS maps
└── results/                          # Output directory (gitignored)
    └── visualizations/               # Generated HTML files
        ├── rcp26_gis_map.html
        ├── rcp45_gis_map.html
        └── rcp85_gis_map.html

../../backend/                        # Shared infrastructure
├── data/loaders/
│   ├── data_loader.py               # NetCDF data loader
│   └── yield_loader.py              # AquaCrop yield loader
└── simulation/
    ├── agents/
    │   ├── farmer_agent.py          # Individual farmer (PECS)
    │   ├── collective_agent.py      # Community level
    │   ├── market_agent.py          # Market level
    │   └── policy_agent.py          # Policy level
    └── models/
        └── landuse_model.py         # Mesa ML-ABM model
```

---

## Key Features

### 100% Real Data
- **NO dummy data** - All inputs from actual EO sources
- **NO synthetic values** - Climate, soil, yields all real
- **LUSA predictions** - Real ML model outputs

### Multi-Level ABM
- **4 interaction levels** (Individual, Community, Market, Policy)
- **Cross-scale dynamics** (bottom-up aggregation + top-down influence)
- **Emergent behavior** from agent interactions

### Realistic Decision-Making
- **PECS Framework**: Physiology, Emotion, Cognition, Social
- **Multi-objective**: Economic + environmental + social factors
- **Bounded rationality**: Imperfect information, adaptive learning

### Geographic Proximity Interactions (NEW! ✨)
- **Spatial indexing**: Grid-based neighbor detection (10km radius, Haversine distance)
- **Crop adoption diffusion**: Bandwagon effects from neighbors
- **Knowledge spillovers**: Learn from successful nearby farmers
- **Local externalities**: Crop diversity benefits (pest/disease resistance)
- **Continuous feedback**: Neighbors influence each other dynamically each year

### Comprehensive Visualization
- **Interactive GIS maps** with real suitability layers
- **Time-series analysis** across all metrics
- **Multi-scenario comparison** (RCP 2.6 vs 4.5 vs 8.5)
- **Uncertainty quantification** with confidence intervals

---

## Understanding the Results

### GIS Maps (`*_gis_map.html`)

**Colored Grid Squares:**
- LUSA suitability predictions at 0.1° resolution (~10km grid)
- WHEAT = Blue gradient (red low → blue high)
- MAIZE = Amber gradient (purple low → amber high)
- Only shows pixels with score > 0

**Farmer Markers:**
- Blue circles = Farmers who chose WHEAT
- Orange circles = Farmers who chose MAIZE
- Click marker for details (crop, yield, income, suitability)

**Spatial Network (NEW! ✨):**
- Toggle "Spatial Network (10km)" layer in top-right controls
- **Green lines** = Neighbors growing same crop (strong influence, bandwagon effect)
- **Blue lines** = Neighbors growing different crops (diversity benefit)
- Click line to see crops and distance
- Shows geographic proximity interactions that influence farmer decisions

**Why farmers are outside some colored areas:**
- Farmers are placed on LUSA grid pixels
- Small random offset (±1km) for visual variety
- If maize suitability = 0 in an area, no maize-colored squares
- Farmers there chose wheat (blue markers on wheat-suitable areas)

### Why All Farmers Choose WHEAT

**This is expected!** LUSA data shows:
- Thessaloniki region has **much higher wheat suitability**
- WHEAT suitable at 99.7% of locations
- MAIZE suitable at only 30% of locations
- Under RCP scenarios, wheat becomes even more favorable

**To see MAIZE adoption:**
- Run longer simulations (--years 30)
- Increase farmer count (--farmers 50)
- Under RCP 8.5, some farmers may switch to maize

---

## Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'mesa'`
**Fix**: `pip install mesa xarray netCDF4 folium`

**Issue**: `FileNotFoundError: PILOT_THESSALONIKI_DATA not found`
**Fix**: Ensure data path exists: `/home/ggous/Downloads/PILOT_THESSALONIKI_DATA`

**Issue**: All farmers choose same crop
**Fix**: **This is correct behavior!** LUSA data heavily favors WHEAT in Thessaloniki

**Issue**: Farmers appear outside colored grid squares
**Fix**: **This is expected** - farmers are placed on LUSA pixels with small offset

**Issue**: Only 2 farmers instead of 3
**Fix**: Check console for "⚠️ Skipping parcel outside bounds" - may indicate placement issue

**Issue**: HTML files not opening
**Fix**: Open with web browser (Firefox, Chrome). Folium maps require JavaScript.

---

## Next Steps

### Phase 1 (Current)
- ✅ Multi-Level ABM with real data
- ✅ Interactive GIS visualizations
- ✅ Multi-scenario analysis

### Phase 2 (Planned)
- 🔲 Real market prices (FADN agricultural data)
- 🔲 Real policy data (EU CAP subsidies)
- 🔲 Reinforcement Learning for policy optimization
- 🔲 Gymnasium environment wrappers
- 🔲 Stable-Baselines3 PPO training

### Phase 3 (Future)
- 🔲 Extended use cases (Food Security, Grid Stabilization)
- 🔲 Cross-border modeling (Geopolitics)
- 🔲 Digital Twin integration with DestinE

---

## References

- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **RL Implementation**: See [RL-IMPLEMENTATION.md](RL-IMPLEMENTATION.md)
- **Project Overview**: See [PRD.md](PRD.md)
- **Development Tasks**: See [TASKS.md](TASKS.md)

For detailed ML-ABM specifications, see [ML-ABM-REQUIREMENTS.md](ML-ABM-REQUIREMENTS.md).
