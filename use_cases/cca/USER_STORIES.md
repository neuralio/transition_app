# CCA User Stories - Climate Change Adaptation

**Status**: ✅ **3 User Stories Implemented** (CCA-03, CCA-04, CCA-10)

**Use Case**: UC-CCA-01 - Climate Change Adaptation Using Multi-Level Agent-Based Modeling

**Deliverable**: TRANSITION D1.1 - Use Case Documentation

---

## 🔑 CCA vs MLU: Key Distinction

**When to use CCA**:
- Focus on **crop performance** and **climate resilience**
- Questions about **yield**, **adaptation**, **vulnerability**
- Farmer decision: **Which crop to plant?** (WHEAT vs MAIZE)
- Optional PV adoption as **adaptation strategy**
- Keywords: "yield", "productivity", "climate adaptation", "resilience"

**When to use MLU**:
- Focus on **land allocation** between competing uses
- Agent decision: **Farm crops OR install solar PV?**
- Multi-use trade-offs (agriculture vs energy production)
- Keywords: "land use", "parcels", "markets", "categorize"

**Examples**:
- ✅ CCA: "Simulate **wheat yield** under moderate scenario for 10 years"
- ✅ MLU: "Simulate wheat at (40.5, 22.7) under moderate scenario for 10 years" (coordinates without "yield" → land use)
- ✅ CCA: "Simulate **crop adaptation** strategies under pessimistic scenario"
- ✅ MLU: "Simulate land use with 5 collectives and 2 **markets**" (markets keyword)

---

## 📋 Implemented User Stories

### CCA-03: Simulate Crop Yield Under Climate Change ✅

**User Story**:
> As a **Farmer** or **Agricultural Developer**
> I want to **simulate the effects of future climate conditions on crop yields**
> So that I can **make informed decisions about crop rotation, irrigation, and climate-resilient farming practices**.

**Acceptance Criteria**:
- The system must allow users to simulate crop yields based on climate projections, including changes in temperature, precipitation, and soil quality.
- Users should be able to select specific crops and see how yields vary under different climate scenarios.
- The system must provide visualizations showing expected yield changes over time, highlighting impacts of different RCP scenarios.

**Implementation Details**:
- **Entry Point**: `python run_cca.py --query cca_03 --crop WHEAT --scenario rcp45 --years 10`
- **Module**: `use_cases/cca/queries/cca_03.py`
- **Output**: `results/cca_03/`
- **Features**:
  - Multi-level ABM simulation with farmer crop decisions
  - Real AquaCrop yield data integration
  - Climate vulnerability assessment
  - Yield tracking under temperature, precipitation, soil changes
  - Time-series visualizations of yield evolution
  - Comparative analysis across RCP scenarios (26, 45, 85)
- **Multi-Level Configuration** (OPTIONAL - not required for CCA-03):
  - **Focus**: CCA-03 simulates **individual farmer decisions** (no multi-level defaults)
  - **Custom (Optional)**: `--collectives N --markets N --policies N` flags if explicitly needed
  - **Note**: For cross-scale interactions, use **CCA-10** instead

**Natural Language Interface**:
```bash
python llm_interface/transition_agent.py "Simulate wheat yield under RCP 4.5 for 10 years"
python llm_interface/transition_agent.py "Show how maize yield changes under climate change"
# With custom multi-level agents
python llm_interface/transition_agent.py "Simulate wheat yield with 20 farmers and 3 cooperatives under moderate scenario"
```

---

### CCA-04: Evaluate Land Suitability for PV Installations ✅

**User Story**:
> As a **Farmer** or **Energy Company Representative**
> I want to **evaluate land suitability for photovoltaic (PV) installations based on climate conditions**
> So that I can **assess the potential for renewable energy production on agricultural land**.

**Acceptance Criteria**:
- The system must integrate solar irradiance data and land characteristics (e.g., terrain, soil quality) to assess the suitability of land for PV installations.
- Users should be able to visualize which land parcels are most suitable for solar energy production based on current and future climate conditions.
- The system should provide a suitability score for each parcel of land, indicating the potential for PV energy generation.

**Implementation Details**:
- **Entry Point**:
  - User-friendly: `python run_cca.py --query cca_04 --scenario moderate --farmers 10 --pv-developers 2`
  - OR with RCP codes: `python run_cca.py --query cca_04 --scenario rcp45 --farmers 10 --pv-developers 2`
  - Available scenarios: **optimistic** (Low Warming ~2°C), **moderate** (Medium Warming ~3°C), **pessimistic** (High Warming ~4-5°C)
- **Module**: `use_cases/cca/queries/cca_04.py`
- **Output**: `results/cca_04/`
- **Features**:
  - PV Developer Agent evaluates all farmer locations
  - Solar radiation data integration (kWh/m²/day)
  - Capacity factor calculation (realistic 15-25% for Greece)
  - ROI analysis with green credits and policy incentives
  - Installation cost and payback period estimation
  - Elevation-adjusted installation costs
  - Suitability scoring for each land parcel
  - Map visualization showing PV-suitable locations
  - Comparison of PV adoption across RCP scenarios

**Natural Language Interface**:
```bash
python llm_interface/transition_agent.py "Evaluate PV suitability with 2 energy companies"
python llm_interface/transition_agent.py "Show which parcels are best for solar installations"
```

---

### CCA-10: Simulate Cross-Scale Interactions ✅

**User Story**:
> As a **System User** (Farmer, Collective, Energy Company, or Policymaker)
> I want to **simulate how decisions at one level (e.g., individual farmer decisions) affect other levels (e.g., market and policy)**
> So that I can **understand how climate adaptation strategies impact different scales of the system**.

**Acceptance Criteria**:
- The system must simulate interactions between individual, community, market, and policy levels, showing how decisions at one level influence outcomes at another.
- Feedback loops must be modeled to show how individual behavior (e.g., a farmer adopting PV) affects market trends and future policy decisions.
- The system should visualize these cross-scale interactions and feedback loops.

**Implementation Details**:
- **Entry Point**: `python run_cca.py --query cca_10 --scenario [optimistic|moderate|pessimistic] --years 10 --farmers 20`
  - **Note**: Scenario parameter is REQUIRED (cross-scale interactions need climate context)
- **Module**: `use_cases/cca/queries/cca_10.py`
- **Output**: `results/cca_10/`
- **Features**:
  - **Multi-Level ABM Framework** (4 levels active):
    - **Individual Level**: FarmerAgent crop/PV decisions
    - **Community Level**: CollectiveAgent coordination
    - **Market Level**: CommodityMarketAgent + PVDeveloperAgent
    - **Policy Level**: PolicymakerAgent subsidies/regulations
  - **Downward Flow**: Policy → Market → Community → Individual
  - **Upward Flow**: Individual → Community → Market → Policy
  - **Lateral Flow**: Peer interactions within each level
  - **Feedback Loop Tracking**:
    - Policy effectiveness evaluation based on market outcomes
    - Market price adjustments based on farmer production
    - Collective influence on individual farmer decisions
    - PV adoption impact on energy policy goals
  - **Cross-Scale Visualizations**:
    - Information flow diagrams (Sankey-style)
    - Feedback timeline charts
    - Driver analysis (what influences what)
    - Interaction network graphs
- **Multi-Level Configuration** (NEW):
  - **Default**: 2 collectives, 1 market, 1 policymaker
  - **Custom**: `--collectives N --markets N --policies N` flags
  - **CLI Example**: `python run_cca.py --query cca_10 --scenario rcp45 --collectives 4 --markets 2 --policies 1`
  - **LLM Interface**: "Run cross-scale interactions with 20 farmers, 4 collectives, 2 markets"

**Natural Language Interface**:
```bash
python llm_interface/transition_agent.py "Simulate cross-scale interactions for 10 years"
python llm_interface/transition_agent.py "Show how farmer decisions affect policy"
# With custom multi-level agents
python llm_interface/transition_agent.py "Run cross-scale interactions with 20 farmers, 4 collectives, 2 markets under RCP 8.5"
```

---

## 🚀 Quick Start Examples

### Via Direct CLI
```bash
# CCA-03: Crop yield simulation
python use_cases/cca/run_cca.py --query cca_03 --crop WHEAT --scenario rcp45 --years 10

# CCA-04: PV suitability evaluation
python use_cases/cca/run_cca.py --query cca_04 --scenario rcp45 --farmers 10 --pv-developers 2

# CCA-10: Cross-scale interactions
python use_cases/cca/run_cca.py --query cca_10 --scenario rcp45 --years 10 --farmers 20
```

### Via Natural Language Interface
```bash
# CCA-03
python llm_interface/transition_agent.py "Simulate wheat yield under RCP 4.5 for 10 years"

# CCA-04
python llm_interface/transition_agent.py "Evaluate land for PV installations with 2 energy companies"

# CCA-10
python llm_interface/transition_agent.py "Show cross-scale interactions between farmers and policy"
```

---

## 📊 Data Requirements

**Data Source**: `/home/ggous/Downloads/PILOT_THESSALONIKI_DATA` (shared with MLU)

**Required Data**:
- **Meteorological**: Temperature, precipitation, solar radiation, evapotranspiration
- **Soil**: pH, organic carbon, CEC, soil type
- **Terrain**: DEM (elevation)
- **Crop Suitability**: LUSA predictions for WHEAT, MAIZE (RCP 26, 45, 85)
- **Yield**: AquaCrop simulation results (optional, uses defaults if unavailable)

**Climate Scenarios**: RCP 2.6, RCP 4.5, RCP 8.5

---

## 🎯 Key Features

### Climate Resilience (CCA-03)
- **Vulnerability Assessment**: Exposure, sensitivity, adaptive capacity
- **Temporal Trends**: Climate change amplification over time
- **Spatial Variation**: Elevation and edge effects
- **Adaptation Capacity**: Economic, social, asset, knowledge factors
- **Risk-Aware Decisions**: Vulnerability-adjusted crop selection

### PV Adoption (CCA-04)
- **ROI Calculation**: Installation costs, green credits, payback period
- **Farmer Decision**: Farming vs PV income comparison
- **Market-Level Agent**: PVDeveloperAgent evaluates all locations
- **Realistic Behavior**: Only installs in first year (market entry)
- **Policy Integration**: Green credit rates influence PV adoption

### Multi-Level Interactions (CCA-10)
- **4 Hierarchical Levels**: Individual, Community, Market, Policy
- **Cross-Scale Flows**: Downward, upward, lateral
- **Feedback Loops**: Policy effectiveness evaluation, market adjustments
- **Orchestrated Execution**: MultiLevelOrchestrator manages all interactions
- **Comprehensive Tracking**: All cross-level information flows recorded

---

## 📈 Validation

**Target**: RMSE < 15% for historical period (2010-2020)

**Historical Validation** (Optional):
```bash
python use_cases/cca/run_cca.py --validate --scenario rcp26 --farmers 20
```

**Validation Metrics**:
- Wheat yield (tons/hectare)
- Maize yield (tons/hectare)
- Crop distribution (wheat/maize fractions)
- Average farmer income

---

## 🔗 Related Documentation

- **Architecture**: [MULTILEVEL-ABM.md](../../MULTILEVEL-ABM.md)
- **Project Guidelines**: [CLAUDE.md](../../CLAUDE.md)
- **Use Case Details**: [README.md](README.md)
- **PRD**: [PRD.md](../../PRD.md)

---

**Last Updated**: 2025-10-12
**Implementation Status**: All 3 user stories complete ✅
**Integration Status**: CLI + LLM interface ready ✅
