# Use Case 1: Climate Change Adaptation (CCA)

**Status**: ✅ **Option A (Quick Start)** IMPLEMENTED | ⏳ **Option B (Full Implementation)** IN PROGRESS

**Deliverable**: TRANSITION D1.1 - Use Case UC-CCA-01

---

## 🎯 **Overview**

The Climate Change Adaptation (CCA) use case simulates how farmers, agricultural collectives, energy companies, and policymakers adapt to changing climate conditions through Multi-Level Agent-Based Modeling (ML-ABM).

### **Primary Goals**
- Simulate crop yield under climate change scenarios (RCP 2.6, 4.5, 8.5)
- Evaluate land suitability for PV (photovoltaic) installations
- Model farmer adaptation decisions (crop selection, irrigation, PV adoption)
- Simulate agricultural collective strategies (shared resources, knowledge transfer)
- Assess policy effectiveness (green credits, subsidies, regulations)
- Historical validation against 2000-2020 land-use patterns

---

## 📊 **Data Source**

**Location**: `backend/data/CCA/`

### **Available Data**
```
backend/data/CCA/
├── land_suitability/
│   ├── WHEAT/
│   │   ├── PAST_LUSA_PREDICTIONS.nc    ⭐ Historical data (2000-2020)
│   │   ├── RCP26_LUSA_PREDICTIONS.nc   (2021-2100)
│   │   ├── RCP45_LUSA_PREDICTIONS.nc
│   │   └── RCP85_LUSA_PREDICTIONS.nc
│   └── MAIZE/ [same structure]
├── meteo/
│   ├── tas_rcp[26|45|85].nc           (temperature)
│   ├── pr_rcp[26|45|85].nc            (precipitation)
│   ├── rsds_rcp[26|45|85].nc          (solar radiation)
│   └── evptsp_rcp[26|45|85].nc        (evapotranspiration)
├── soil/
│   ├── phh2o_0-5cm_mean.nc            (pH)
│   ├── soc_0-5cm_mean.nc              (organic carbon)
│   ├── cec_0-5cm_mean.nc              (CEC)
│   └── SoilType_0-5cm_mean.nc
├── dem/
│   └── DEM.nc                          (elevation)
└── yield/
    ├── AquaCrop_Results_RCP26.csv      (3653 daily records, 2021-2031)
    ├── AquaCrop_Results_RCP45.csv
    └── AquaCrop_Results_RCP85.csv
```

**Key Difference from MLU**: Historical LUSA data (`PAST_LUSA_PREDICTIONS.nc`) enables validation against 2000-2020 observations.

---

## 🚀 **Quick Start (Option A)**

### **Installation**
```bash
# No additional installation required if you have the base TRANSITION project
cd use_cases/cca/
```

### **Run Basic Simulation**
```bash
# Run single scenario (quick test)
python run_cca.py --scenario rcp26 --years 5 --farmers 3

# Run all scenarios (RCP 2.6, 4.5, 8.5)
python run_cca.py --years 10 --farmers 10

# Run with historical validation
python run_cca.py --historical --years 10 --farmers 20
```

### **Command-Line Options**
```
--scenario [rcp26|rcp45|rcp85]  # Single scenario (default: run all)
--years N                       # Number of years to simulate (default: 10)
--farmers N                     # Number of farmer agents (default: 3)
--output DIR                    # Output directory (default: results)
--historical                    # Include historical validation (2000-2020)
--data-path PATH                # Path to CCA data (default: backend/data/CCA)
```

### **Expected Output**
```
use_cases/cca/results/
├── rcp26/
│   └── rcp26_basic_results.txt
├── rcp45/
│   └── rcp45_basic_results.txt
└── rcp85/
    └── rcp85_basic_results.txt
```

---

## 📈 **Current Implementation (Option A)**

### **✅ Implemented**
- [x] Multi-level ABM framework (Individual, Community, Market, Policy)
- [x] Real data loading from `backend/data/CCA/`
- [x] Crop selection decisions (WHEAT, MAIZE)
- [x] RCP scenario simulations (RCP 2.6, 4.5, 8.5)
- [x] Basic income and production tracking
- [x] Multi-scenario comparative analysis
- [x] Climate change impact assessment (RCP85 vs RCP26)

### **⏳ Not Yet Implemented (Option B - In Progress)**
- [ ] PV Developer Agent (energy company decisions)
- [ ] Climate resilience assessment
- [ ] Water resource management (irrigation optimization)
- [ ] PV adoption decision logic
- [ ] Extreme weather event modeling (droughts, floods)
- [ ] Historical validation (RMSE < 15% target)
- [ ] Interactive visualizations (Plotly, Folium)
- [ ] Climate insurance modeling

---

## 🎯 **Use Case Requirements (D1.1)**

### **Primary Actors**
1. **Individual Farmers** - Crop selection, irrigation, PV installations
2. **Agricultural Collectives** - Shared infrastructure, resource coordination
3. **Energy Companies** - PV investment decisions on agricultural land
4. **Policymakers** - Climate-resilient policies, green credits, subsidies

### **User Stories** (29 total: CCA-01 to CCA-29)

**Must-Have (Option A)**:
- ✅ CCA-01: Access Climate Change Adaptation Module
- ✅ CCA-02: Input climate scenario parameters
- ✅ CCA-03: Simulate crop yield under climate change
- ✅ CCA-05: Simulate farmer decisions on crop selection
- ✅ CCA-10: Simulate cross-scale interactions (multi-level ABM)

**Should-Have (Option B)**:
- ⏳ CCA-04: Evaluate land suitability for PV installations
- ⏳ CCA-06: Simulate agricultural collective adaptation strategies
- ⏳ CCA-07: Simulate market-level PV investment decisions
- ⏳ CCA-08: Introduce climate-resilient policies
- ⏳ CCA-14: Evaluate feedback loops in climate adaptation
- ⏳ CCA-19: Simulate water resource management

**Could-Have (Option B/C)**:
- ⏳ CCA-12: Perform long-term projections (10-50 years)
- ⏳ CCA-22: Adjust climate parameters in real-time
- ⏳ CCA-25: Explore climate change's impact on food security
- ⏳ CCA-29: Simulate climate insurance adoption

---

## 📝 **Example Output**

```
TRANSITION CCA Multi-Scenario Analysis
================================================================================
Use Case:  Climate Change Adaptation (UC-CCA-01)
Scenarios: RCP 2.6, RCP 4.5, RCP 8.5
Duration:  10 years
Farmers:   10
================================================================================

[1/3] Running RCP26...

TRANSITION CCA SIMULATION: RCP26
================================================================================
1. Initializing model...
   - Scenario: rcp26
   - Farmers: 10
   - Duration: 10 years
   Multi-Level ABM Enabled:
   - Individual Level: 10 farmers
   - Community Level: 1 collective(s)
   - Market Level: 1 commodity market
   - Policy Level: 1 policymaker agent

2. Running simulation (10 years)...
   Year 2021: 8 WHEAT, 2 MAIZE | Income: €28,500 | Production: 250.3 t
   Year 2022: 9 WHEAT, 1 MAIZE | Income: €29,100 | Production: 255.8 t
   ...

💡 Climate Change Impact (RCP85 vs RCP26):
   Income Loss: €3,450/year (12.1%)

   Policy Recommendation:
   To maintain farmer income under RCP85, consider:
   - Increasing climate adaptation subsidies by ~12%
   - Promoting drought-resistant crop varieties
   - Supporting PV installation on marginal agricultural land
```

---

## 🔬 **Validation Requirements**

### **Historical Validation (Option B)**
- **Requirement**: RMSE < 15% against 2000-2020 land-use observations
- **Data**: `PAST_LUSA_PREDICTIONS.nc` files
- **Method**: Compare simulated vs historical land-use patterns
- **Status**: ⏳ Not yet implemented

---

## 🛠️ **Next Steps**

### **Option B: Full Implementation**

1. **Implement PVDeveloperAgent**
   - Energy company decision-making
   - Land lease evaluation
   - ROI calculation with green credits

2. **Climate Resilience Features**
   - Vulnerability assessment
   - Adaptation capacity scoring
   - Extreme weather event modeling

3. **Water Resource Management**
   - Irrigation optimization
   - Collective water sharing agreements
   - Drought response strategies

4. **Historical Validation**
   - Load `PAST_LUSA_PREDICTIONS.nc`
   - Run 2000-2020 simulation
   - Calculate RMSE/MAE vs historical
   - Generate validation report

5. **Interactive Visualizations**
   - Adaptation pathway maps (land-use transitions)
   - Climate risk heatmaps (vulnerability)
   - Policy effectiveness dashboards
   - Water stress analysis charts

---

## 📚 **References**

- **Deliverable**: TRANSITION_D1.1_User_Stories_and_Use_Cases_Documentation_M04_v1.1.docx
- **Use Case ID**: UC-CCA-01
- **User Stories**: CCA-01 to CCA-29
- **Data Source**: `backend/data/CCA/`
- **Related Documentation**:
  - [MULTILEVEL-ABM.md](../../MULTILEVEL-ABM.md)
  - [RL-IMPLEMENTATION.md](../../RL-IMPLEMENTATION.md)
  - [CLAUDE.md](../../CLAUDE.md)

---

## 🤝 **Contributing**

Follow the TRANSITION project guidelines in [CLAUDE.md](../../CLAUDE.md):
- Max 500 lines per file
- PEP 8 for Python code
- Type hints required
- Real data only (no mocks)
- Document all agent classes

---

**Last Updated**: 2025-10-10
**Status**: Option A Complete ✅ | Option B In Progress ⏳
