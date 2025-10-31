# Product Requirements Document (PRD)
## EO-Informed Irrigation Simulation Use Case
### Multi-Regional Agricultural Water Management

**Version:** 1.1
**Date:** October 2025
**Use Case Status:** Planned (Phase 2)
**Parent Project:** TRANSITION - EO-Informed Agent Based Models for Digital Twins Applications
**Implementation:** Area-agnostic, globally applicable (all regional parameters configurable)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Use Case Background & Context](#use-case-background--context)
3. [Vision & Objectives](#vision--objectives)
4. [Stakeholders & User Personas](#stakeholders--user-personas)
5. [Scope & Boundaries](#scope--boundaries)
6. [Detailed Use Case Description](#detailed-use-case-description)
7. [User Stories](#user-stories)
8. [Functional Requirements](#functional-requirements)
9. [Technical Requirements](#technical-requirements)
10. [Data Requirements](#data-requirements)
11. [Success Metrics & KPIs](#success-metrics--kpis)
12. [Validation Strategy](#validation-strategy)
13. [Development Roadmap](#development-roadmap)
14. [Risks & Mitigation](#risks--mitigation)
15. [Glossary](#glossary)

---

## 1. Executive Summary

### 1.1 Use Case Overview

The EO-Informed Irrigation Simulation use case implements a **dynamic, satellite-driven crop rotation and irrigation management system** for irrigated agricultural regions globally. This use case integrates **Sentinel-2 NDVI/NDWI time-series data** with **agent-based modeling** and **crop water models (AquaCrop)** to create an adaptive 5-year simulation of irrigation needs based on real-world land-use changes.

**Area-Agnostic Design**: The system is designed to work in any agricultural region worldwide (Mediterranean, tropical, temperate, arid) with configurable seasonal windows, crop types, and climate data. All regional parameters (crop calendars, seasonal boundaries, irrigation practices) are specified via `config.yaml` or API parameters - **NO hardcoded geography**.

### 1.2 Key Innovation

Unlike static crop mapping approaches, this system:
- **Automatically detects bare soil** parcels using EO data (NDVI/NDWI thresholding)
- **Dynamically assigns crops** based on seasonal rotation rules (summer-to-winter, winter-to-summer)
- **Validates rice flooding** with NDWI water detection to ensure accurate water balance modeling
- **Creates adaptive simulations** that reflect actual farmer behavior and land-use changes

### 1.3 Value Proposition

**For Water Management Authorities:**
- Accurate irrigation demand forecasts based on real crop patterns
- Early detection of land-use changes affecting water needs
- Scenario testing for drought and policy interventions

**For Farmers & Cooperatives:**
- Data-driven crop rotation recommendations
- Water availability insights for planning
- Understanding of collective irrigation impacts

**For Policymakers:**
- Evidence-based water allocation policies
- Climate adaptation strategy evaluation
- Regional agricultural sustainability monitoring

### 1.4 Alignment with TRANSITION

This use case extends TRANSITION's **Multi-Level Agent-Based Modeling (ML-ABM)** framework with:
- **Individual Level**: Farmer agents making seasonal crop decisions based on EO observations
- **Community Level**: Water cooperatives managing shared irrigation resources
- **Policy Level**: Government water authorities observing regional patterns

It embodies TRANSITION's core principles:
- ✅ **100% Real EO Data**: Sentinel-2 NDVI/NDWI time-series (NO dummy data)
- ✅ **Multi-Level ABM**: Farmers → Cooperatives → Policy authorities
- ✅ **Digital Twin**: Adaptive simulation mirroring real-world land-use dynamics
- ✅ **Modular Architecture**: Standalone EO classification + crop assignment + AquaCrop modules

---

## 2. Use Case Background & Context

### 2.1 Geographic Context (Configurable Per Region)

**Region**: User-specified via geographic bounds, parcel file, or administrative boundaries
**Area**: Configurable (from 100s to 1000s km² of irrigated agricultural land)
**Climate**: Adaptable to any climate zone (Mediterranean, tropical, temperate, arid, semi-arid)

**Example Regions** (demonstrating configurability):
- **Mediterranean** (e.g., Thessaloniki plain, Greece): Hot dry summers, mild wet winters; summer crops (rice, maize, cotton), winter crops (wheat)
- **Tropical** (e.g., Southeast Asia): Monsoon-driven; rice paddies year-round with dry/wet season rotation
- **Temperate** (e.g., US Midwest): Cold winters, warm summers; corn-soybean rotations
- **Arid** (e.g., Middle East): Year-round irrigation-dependent; date palms, vegetables

### 2.2 Agricultural Characteristics (Region-Specific Configuration)

**Crop Types** (configurable via `config.yaml`):
- **Summer/Rainy Season Crops**: Examples include rice (flooded), maize, cotton, cassava, groundnut (region-dependent)
- **Winter/Dry Season Crops**: Examples include wheat, barley, vegetables, fallow (region-dependent)

**Irrigation Systems** (configurable per region):
- Canal networks, tube wells, drip irrigation, furrow irrigation, or combinations
- Flood-dependent crops (e.g., rice paddies) require NDWI-based flood detection
- Supplemental irrigation crops (e.g., maize, cotton) use deficit irrigation scheduling
- Rainfed crops (e.g., winter cereals in Mediterranean) with minimal/no irrigation

**Crop Rotation Patterns** (emergent from EO data, not hardcoded):
- **Double-cropping**: Common in regions with distinct seasons (e.g., winter cereal → summer cash crop)
- **Single-cropping**: Dominant in extreme climates (long fallow periods)
- Fallow periods: Some farmers skip summer or winter to save water or due to market conditions
- **Rotation benefits**: Soil health, pest control, economic diversification

### 2.3 Problem Statement

Current irrigation planning faces critical challenges:

1. **Static Crop Maps**: Traditional approaches assume fixed crop distributions, missing real-time changes
2. **Uncertain Rice Flooding**: Assumptions about rice paddies often overestimate water use (not all assigned rice fields are actually flooded)
3. **Delayed Detection**: Manual surveys take weeks/months to identify land-use changes
4. **Climate Stress**: Increasing drought frequency requires adaptive water management
5. **Policy Gaps**: Lack of evidence-based tools for water allocation under changing conditions

**This use case addresses these gaps** by creating a **continuously updated, EO-validated crop and irrigation model**.

### 2.4 Alignment with EU Policies

- **EU Green Deal**: Sustainable agricultural water use
- **Water Framework Directive**: Integrated river basin management
- **Common Agricultural Policy (CAP)**: Support for precision agriculture
- **DestinE Initiative**: High-fidelity environmental digital twins

---

## 3. Vision & Objectives

### 3.1 Vision Statement

To create an **adaptive irrigation planning tool** that uses real-time Earth Observation data to detect crop rotations, validate rice flooding, and simulate water demand over 5-year horizons, enabling water managers, farmers, and policymakers to make climate-resilient decisions for the Thessaloniki–Pella–Imathia plain.

### 3.2 Primary Objectives

**OBJ-1: EO-Driven Crop Detection**
Automatically classify land parcels as vegetated or bare soil using Sentinel-2 NDVI/NDWI indices with >90% accuracy.

**OBJ-2: Dynamic Crop Assignment**
Implement seasonal rotation rules to assign crops to bare parcels (summer-to-winter, winter-to-summer) reflecting realistic farmer behavior.

**OBJ-3: Rice Flood Validation**
Use NDWI signals to confirm rice paddy flooding (>85% precision/recall), preventing false water usage assumptions.

**OBJ-4: AquaCrop Integration**
Seamlessly reinitialize the AquaCrop crop water model each season with EO-derived crop plans, maintaining soil moisture continuity.

**OBJ-5: Multi-Level ABM**
Simulate interactions between farmer agents (parcel decisions), water cooperatives (resource allocation), and policy authorities (regulation).

**OBJ-6: Irrigation Demand Forecasting**
Produce 5-year irrigation demand projections with improved accuracy (<5% error vs historical data) compared to static models (15% error).

### 3.3 Success Criteria

- ✅ System processes Sentinel-2 imagery automatically each season
- ✅ Bare soil classification accuracy >90% (validated against ground truth)
- ✅ 100% of bare parcels assigned next-season crop within seconds
- ✅ Rice flood detection >85% precision and recall
- ✅ AquaCrop simulations run without seasonal transition errors
- ✅ Irrigation demand forecasts align within 5% of historical totals
- ✅ Policy recommendations generated for drought and climate scenarios

---

## 4. Stakeholders & User Personas

### 4.1 Primary User Personas

#### Persona 1: Water Management Authority Officer

**Profile:**
- Role: Regional water resource manager
- Manages canal systems and water allocation
- Plans seasonal releases from reservoirs
- Responds to drought emergencies

**Goals:**
- Forecast seasonal irrigation demand accurately
- Detect land-use changes affecting water needs early
- Optimize water allocation across competing uses
- Develop drought contingency plans

**Pain Points:**
- Delayed crop surveys (manual, seasonal lag)
- Overestimation of rice water use (assumed all rice fields flood)
- Difficulty projecting future demand under climate change
- Lack of scenario analysis tools

**Key Features Needed:**
- Real-time crop classification maps
- Seasonal irrigation demand forecasts
- Drought scenario simulations
- Historical vs projected comparisons

---

#### Persona 2: Farmer / Farm Cooperative Member

**Profile:**
- Owns 5–20 hectares in the plain
- Member of local irrigation cooperative
- Makes seasonal crop decisions (wheat, maize, cotton, rice)
- Concerned about water availability and costs

**Goals:**
- Understand water availability for upcoming season
- Plan crop rotations considering water constraints
- Coordinate with cooperative on irrigation schedules
- Maximize yield while conserving water

**Pain Points:**
- Uncertainty about summer water supply
- Rising irrigation costs
- Lack of information on neighbors' crop choices (collective impact)
- Climate variability affecting yield

**Key Features Needed:**
- Water availability forecasts per cooperative zone
- Crop rotation recommendations
- Cooperative-level water demand insights
- Historical water usage comparisons

---

#### Persona 3: Agricultural Policymaker

**Profile:**
- Works for regional/national agricultural ministry
- Develops water allocation policies
- Evaluates subsidy programs (e.g., rice cultivation support)
- Monitors compliance with EU directives

**Goals:**
- Ensure sustainable agricultural water use
- Balance farmer livelihoods with environmental limits
- Evaluate policy effectiveness (e.g., rice area limits)
- Adapt policies to climate change projections

**Pain Points:**
- Lack of real-time data on rice cultivation areas
- Difficulty quantifying policy impact on water use
- Need for long-term climate adaptation scenarios
- Political pressure during droughts

**Key Features Needed:**
- Annual rice area estimates (EO-validated)
- Policy scenario simulations (e.g., rice subsidy removal)
- Long-term climate impact projections
- Evidence-based policy recommendations

---

#### Persona 4: Environmental Scientist / Academic Researcher

**Profile:**
- Studies agricultural water use and climate adaptation
- Uses models for research publications
- Interested in model validation and uncertainty

**Goals:**
- Access high-quality irrigation and crop data
- Validate crop water models against EO observations
- Publish research on climate adaptation
- Contribute to improving modeling methods

**Pain Points:**
- Difficulty accessing integrated EO + model datasets
- Lack of open-source irrigation simulation tools
- Need for reproducible workflows
- Uncertainty quantification often missing

**Key Features Needed:**
- Data export (crop maps, irrigation estimates, EO time-series)
- Model documentation and validation reports
- API access for programmatic use
- Uncertainty estimates with all outputs

---

### 4.2 Secondary Stakeholders

- **ESA Technical Staff**: Monitor project alignment with DestinE and TRANSITION objectives
- **Irrigation Equipment Companies**: Use demand forecasts for market planning
- **Climate Services Providers**: Integrate irrigation data into broader climate services
- **EU Commission (DG AGRI, DG ENV)**: Assess tool for CAP and Water Framework Directive compliance

---

## 5. Scope & Boundaries

### 5.1 In Scope

**Core Capabilities:**

1. **EO-Based Parcel Classification Module**
   - Sentinel-2 NDVI time-series processing (10m resolution)
   - NDVI thresholding for bare soil detection (NDVI < 0.2–0.3)
   - NDWI processing for water/flooding detection
   - Time-series phenology analysis (distinguish harvested vs fallow)
   - Output: Binary land cover status map (vegetated/bare) per season

2. **Dynamic Crop Assignment Logic**
   - **Summer-to-Winter Rule**: Bare in summer → winter wheat
   - **Winter-to-Summer Rule**: Bare in winter → random(maize, cotton, rice)
   - Configurable crop probabilities (e.g., 40% maize, 40% cotton, 20% rice)
   - Agent-based implementation (farmer decision rules)

3. **Rice Flood Detection (NDWI-Based)**
   - May NDWI monitoring for rice-assigned parcels
   - Threshold-based flooding confirmation (NDWI > 0.2 or sustained > 0)
   - Conditional AquaCrop irrigation regime (flooded vs non-flooded)
   - Dynamic adjustment for non-confirmed rice (reassignment or fallow marking)

4. **AquaCrop Integration**
   - Seasonal re-initialization with updated crop plans
   - Crop-specific parameter files (wheat, maize, cotton, rice flooded/rainfed)
   - Soil moisture carryover between seasons
   - Irrigation schedule optimization per crop type
   - Water balance closure validation

5. **Multi-Level Agent-Based Modeling**
   - **Individual Level**: Farmer agents observe EO data, decide next-season crop
   - **Community Level**: Water cooperative agents aggregate demand, manage allocations
   - **Policy Level**: Water authority agents set regulations, monitor sustainability
   - Cross-scale feedback loops (individual → cooperative → policy)

6. **Five-Year Simulation Workflow**
   - Year 0 initialization (EO-derived starting conditions)
   - Iterative seasonal cycle: Classify → Assign → Simulate (winter/summer)
   - Automated AquaCrop runs per parcel per season
   - Aggregated irrigation demand outputs (seasonal, annual, 5-year total)

7. **Visualizations & Reporting**
   - Interactive maps: Crop distribution, irrigation demand, rice flooding events
   - Time-series charts: Seasonal irrigation, crop area evolution
   - Comparison views: Historical vs simulated, scenario comparisons
   - Policy recommendations: Water savings, crop diversification, drought resilience
   - Uncertainty bands: EO classification confidence, model ensemble spreads

8. **Data Sources**
   - Sentinel-2 Level-2A (NDVI, NDWI, 10m, 5-day revisit)
   - GIS parcel boundaries (vector layer of agricultural fields)
   - Climate data: Historical temperature, precipitation, solar radiation, ET₀
   - Soil data: Soil type, texture, water holding capacity (for AquaCrop)
   - Baseline irrigation infrastructure: Canal networks, pump capacity

### 5.2 Out of Scope (Phase 1)

**Excluded from Initial Implementation:**

- Real-time automated satellite data download (manual pre-processing for Phase 1)
- Groundwater modeling (focus on surface irrigation only)
- Economic optimization of crop choices (profit maximization not included)
- Social network analysis among farmers (peer influence simplified)
- Mobile app for farmers (web platform only)
- Automated policy enforcement (advisory outputs only)
- IoT sensor data integration (soil moisture sensors, smart meters)
- Blockchain for water rights tracking

### 5.3 Future Enhancements (Phase 2+)

**Potential Extensions:**

- **Automated EO Pipeline**: Sentinel Hub or Google Earth Engine integration for on-demand data
- **Groundwater Component**: Couple with MODFLOW for aquifer-surface water interactions
- **Economic Module**: Add crop price dynamics, profit optimization per agent
- **Social Networks**: Explicit modeling of farmer information sharing
- **Machine Learning**: Replace rule-based crop assignment with RL-trained policies
- **Climate Scenarios**: Integrate CMIP6 projections for long-term planning
- **Mobile Interface**: Farmer-facing app for water allocation notifications
- **IoT Integration**: Real-time soil moisture and flow meter data

---

## 6. Detailed Use Case Description

### 6.1 Use Case Name

**UC-IRR-01: EO-Informed Dynamic Irrigation Simulation (5-Year Multi-Seasonal)**

### 6.2 Primary Actors

- **Farmer Agents** (Individual Level): Land parcel owners making crop decisions
- **Water Cooperative Agents** (Community Level): Irrigation collectives managing shared resources
- **Water Authority Agents** (Policy Level): Government bodies regulating water use
- **EO Classification Module** (System): Automated bare soil/crop detection
- **Crop Assignment Module** (System): Rule-based seasonal crop allocation
- **AquaCrop Simulation Engine** (System): Crop water balance modeling

### 6.3 Preconditions

1. **EO Data Availability**: Sentinel-2 NDVI/NDWI time-series data for the region with sufficient temporal frequency and cloud-free observations covering simulation period (historical) or real-time access (operational)
2. **Parcel Boundaries**: Defined parcel boundaries (GIS layer of agricultural fields) with unique IDs
3. **Initial Crop Status**: Year 0 crop distribution from prior EO-derived land cover maps or agricultural survey
4. **Climate Data**: Climate data and soil information required for crop growth modeling (e.g., for AquaCrop): temperature, precipitation, solar radiation, reference ET
5. **Soil Data**: Soil type, texture, field capacity, wilting point for each parcel or region
6. **AquaCrop Configuration**: Crop parameter files calibrated for region (crop types configurable)
7. **Baseline Infrastructure Data**: Baseline irrigation infrastructure data (canal capacities, water authority allocation systems)
8. **TRANSITION Platform**: Modular services (EO data processing, crop growth simulation, ABM engine) deployed and configured for the region

### 6.3.1 Triggers

**Scheduled Seasonal Updates:**
- Automatic EO-based classification triggered at end-of-season intervals (configurable: e.g., end of winter and end of summer each year) to update crop assignments
- Ensures each simulated season's crops reflect the latest EO observations

**On-Demand Simulation Requests:**
- User or system requests for an annual land-use simulation (e.g., to evaluate a policy or climate scenario)
- Invokes this workflow, ensuring dynamic crop assignment based on EO data rather than static assumptions

### 6.4 Main Flow (5-Year Simulation)

**⚠️ CONFIGURATION NOTE**: All dates, months, seasons, crop types, and regional parameters mentioned in this workflow are **examples only** and **MUST be configurable** via `config.yaml` or API parameters. The system is designed to be **region-agnostic** and adaptable to any agricultural context globally (Mediterranean, tropical, temperate, etc.).

**Key Configurable Parameters:**
- **Seasonal windows**: Summer/winter classification periods (e.g., May–Sep for Mediterranean summer, Nov–Mar for tropical dry season)
- **Crop types**: Configurable crop lists per season (e.g., {maize, cotton, rice} for Mediterranean summer, {cassava, groundnut} for West African rainy season)
- **NDVI/NDWI thresholds**: Vegetation and water detection thresholds (region-specific)
- **Flooding monitoring**: Crop types requiring flood detection, monitoring windows, NDWI thresholds
- **Sowing dates**: Per-crop, per-region planting calendars
- **Climate scenarios**: Historical, RCP, SSP, or regional projections

---

#### **Step 1: System Initialization**

**User Actions:**
- Selects simulation period (e.g., 5-year horizon)
- Specifies region of interest (geographic bounds or parcel file)
- Chooses climate scenario (historical, RCP 4.5, RCP 8.5, or regional projections)
- Sets crop assignment probabilities (e.g., configurable crop mix for winter-to-summer transitions)
- Configures multi-level ABM parameters (number of cooperatives, water authority policies)
- Configures seasonal windows (summer/winter classification periods - region-specific)

**System Actions:**
- Loads Sentinel-2 imagery archive for selected period
- Ingests parcel GIS layer and assigns unique IDs
- Initializes farmer agents (one per parcel) with attributes (location, soil type, initial crop)
- Creates water cooperative agents (spatial clustering of parcels)
- Initializes water authority agent with policy parameters (water allocation limits, rice area targets)
- Loads AquaCrop configuration files and climate data

---

#### **Step 2: Year 0 Baseline Classification**

**EO Classification Module Actions:**
- Processes Sentinel-2 imagery from fall of Year 0 (configurable classification window)
- Computes NDVI for all parcels, identifies those with established vegetation (winter crops) vs bare
- Generates initial crop status map: {parcel_id: crop_type or "bare"}

**System Actions:**
- Initializes AquaCrop for Year 0 winter season (dates configurable per region)
- Sets sowing dates, crop parameters based on identified crops
- Establishes baseline soil moisture conditions

---

#### **Step 3: Winter Season Simulation (Year 1: Configurable Dates)**

**Farmer Agent Actions:**
- Agents with winter crops monitor growth (passive, model-driven)
- Agents with bare parcels remain fallow (no irrigation)

**AquaCrop Simulation:**
- Simulates winter crop growth for all assigned parcels
- Calculates water use (mostly rainfall, minimal irrigation typical for winter cereals)
- Updates soil moisture daily

**EO Classification Module (End of Winter):**
- Processes Sentinel-2 from end-of-winter window (configurable: e.g., Jan–Feb in Mediterranean, Dec–Jan in tropics)
- Identifies parcels that remained bare throughout winter
- Outputs: {bare_winter_parcels: [list of parcel IDs]}

**Crop Assignment Module:**
- Applies **Winter-to-Summer Rule**: For each bare-winter parcel, randomly assigns summer crops based on configured probabilities (e.g., maize, cotton, rice, or region-specific crops)
- Updates parcel crop plan: {parcel_id: assigned_crop}

---

#### **Step 4: Transition to Summer Season (Year 1: Configurable Dates)**

**System Actions:**
- Reads updated crop plan from assignment module
- For each parcel with a new summer crop:
  - Retrieves final soil moisture from winter simulation (carryover)
  - Initializes AquaCrop with new crop parameters (sowing dates configurable per crop and region)
  - Sets initial soil conditions (moisture, organic matter from previous season)

**Flood Detection Module (Configurable Monitoring Window):**
- For all parcels assigned flooded crops (e.g., "RICE" in paddy systems):
  - Monitors Sentinel-2 NDWI starting at expected flooding period (configurable: e.g., May for Mediterranean rice, other months for different regions/crops)
  - If NDWI exceeds flooding threshold (configurable, e.g., >0.2) during monitoring window → Flag as `isFlooded=True`
  - If NDWI remains low → Flag as `isFlooded=False` (potential failed planting or reassignment)

**AquaCrop Adjustment:**
- Flooded parcels: Use continuous shallow flooding regime (ponding depth configurable, percolation rate from soil data)
- Non-flooded parcels: Switch to supplemental irrigation or mark as alternate crop (if advanced logic enabled)

---

#### **Step 5: Summer Season Simulation (Year 1: Configurable Dates)**

**Farmer Agent Actions:**
- Agents with summer crops monitor crop growth
- Cooperatives aggregate irrigation demand across member parcels
- Water authority monitors total regional demand, enforces allocation limits if drought

**AquaCrop Simulation:**
- Simulates daily crop growth for all summer crops
- Calculates irrigation requirements based on soil moisture deficit
- For flooded crops: Maintains ponding, simulates percolation and evapotranspiration
- Outputs: Seasonal irrigation volume per parcel, crop yield

**Water Cooperative Agents:**
- Aggregate irrigation demand from member farmers
- Allocate water based on availability (canal capacity, reservoir releases, water rights)
- Notify farmers of any restrictions (configurable allocation ratios)

**Water Authority Agent:**
- Monitors total regional irrigation demand
- Compares against sustainable limits (configurable thresholds: e.g., river flow, aquifer levels)
- If limits exceeded, triggers policy intervention (configurable responses: e.g., crop area restrictions, water pricing)

---

#### **Step 6: End of Summer Analysis & Next Assignment (Configurable Window)**

**EO Classification Module:**
- Processes Sentinel-2 from end-of-summer window (configurable: e.g., Jul–Aug in Mediterranean, other months for different regions)
- Identifies parcels that remained bare throughout summer (NDVI below vegetation threshold all season)
- Outputs: {bare_summer_parcels: [list of parcel IDs]}

**Crop Assignment Module:**
- Applies **Summer-to-Winter Rule**: All bare-summer parcels assigned dominant winter crop (configurable: e.g., "WINTER_WHEAT" in Mediterranean, "BARLEY" elsewhere)
- Updates crop plan for Year 1→Year 2 winter transition

**Reporting Module:**
- Generates Year 1 summary:
  - Total irrigation used (volume units configurable)
  - Crop distribution (% by area for each crop type)
  - Flooding events: N parcels confirmed flooded (for flood-dependent crops)
  - Water cooperative allocations: List of shortfalls (if any)
  - Policy alerts: Configurable thresholds (e.g., crop area targets, water limits)

---

#### **Step 7: Repeat Cycle for Years 2–5**

**Iterative Process:**

For each subsequent year (all parameters configurable per region):
1. **Winter Simulation**: Grow winter crops, classify bare-winter parcels → assign summer crops
2. **Summer Simulation**: Grow summer crops, check flooding via NDWI (for flood-dependent crops), classify bare-summer → assign winter crops
3. **Aggregation**: Water cooperatives sum demands, water authority evaluates sustainability
4. **Adaptation**: Farmer agents may adjust behavior based on water scarcity signals (future RL enhancement)

**Dynamic Adjustments:**
- If a parcel assigned flood-dependent crop but flooding not confirmed by NDWI:
  - Mark as "not_planted" or "alternate_crop"
  - Feed back into agent learning (future enhancement)
- If drought year (low water availability):
  - Water authority reduces allocations → farmers may leave fields fallow → detected as bare next season → cycle continues

**Emergent Patterns:**
- Over 5 years, system captures realistic crop rotation sequences
- Example rotation (crops configurable per region): Parcel A: Year1 summer_crop_A → Year1 winter_crop_B → Year2 summer_crop_C → Year2 winter fallow → Year3 flood_crop (flooding confirmed) → ...
- Patterns emerge from EO-detected land use, not predetermined schedules

---

#### **Step 8: Final Outputs & Analysis**

**After 5-Year Simulation:**

**Spatial Outputs:**
- Annual crop distribution maps (GeoJSON/Shapefile)
- Rice flooding event maps (locations + timing)
- Irrigation intensity heatmaps (total water per parcel)

**Time-Series Outputs:**
- Seasonal irrigation demand (10 seasons: 5 winters + 5 summers)
- Crop area evolution (hectares of wheat, maize, cotton, rice over time)
- Water cooperative allocations (requested vs allocated)
- Policy intervention timeline (if drought policies triggered)

**Summary Metrics:**
- Total 5-year irrigation (units configurable: m³, acre-feet, etc.)
- Average annual area per crop type (EO-validated)
- Water savings from fallow detection (% vs assuming all parcels cultivated)
- Accuracy vs historical data: Mean Absolute Error <5% (target from IRR-US-05)

**Policy Recommendations (Region-Specific):**
- Drought resilience: Quantified fallow incentive impacts on demand reduction
- Crop area management: Evidence-based thresholds for sustainable water use
- Infrastructure: Data-driven capacity upgrade recommendations based on peak demand patterns

---

### 6.5 Postconditions

- ✅ 5-year crop rotation history stored in database
- ✅ Irrigation demand validated against historical records (if available)
- ✅ Rice flooding areas match EO observations (>85% agreement)
- ✅ Policy insights generated and reviewed by water authority
- ✅ System ready for next simulation cycle or scenario testing

---

### 6.6 Alternative Flows

**AF-1: Rice Flooding Not Confirmed**
- **Trigger**: NDWI remains low for rice-assigned parcel in May–June
- **Action**: System marks parcel as `rice_not_planted`, treats as fallow or reassigns to alternate crop (if NDVI rises later)
- **Impact**: Prevents overestimation of rice water use

**AF-2: Drought Emergency (Mid-Simulation)**
- **Trigger**: Water authority detects reservoir levels <30% in July
- **Action**: Emergency allocation cuts → some farmers cannot irrigate → fields dry out (NDVI drops) → detected as bare in next classification → assigned wheat in winter (normal flow resumes)
- **Impact**: Simulation adapts to real-world shocks

**AF-3: Manual Override (User Intervention)**
- **Trigger**: User knows a specific parcel will be rice (e.g., farmer pre-commitment)
- **Action**: User manually assigns crop to parcel, overriding EO classification
- **Impact**: System respects ground truth, improves accuracy

**AF-4: EO Data Gap (Cloud Cover)**
- **Trigger**: Sentinel-2 imagery unavailable for classification window (>80% cloud cover)
- **Action**: Use previous season's classification as proxy, flag uncertainty, or interpolate from neighboring parcels
- **Impact**: Graceful degradation, warns user of reduced confidence

---

## 7. User Stories

### 7.1 Developer User Stories

#### **IRR-US-01: Automated EO Classification**

**User Story:**
As a **developer of the EO data service**, I want to integrate an automated Sentinel-2 classification module that flags bare soil parcels using NDVI/NDWI indices, so that the simulation can dynamically update crop rotations.

**Requirements:**
The classification should operate without manual intervention each season, processing imagery and outputting results in a standardized format (e.g., a binary mask per parcel). It must handle cloud gaps by using the best available observations or multi-date composites.

**Acceptance Criteria:**

**Automated Processing:**
- ✅ System processes Sentinel-2 imagery for all parcels in region automatically each season
- ✅ NDVI computed for each parcel: (NIR - Red) / (NIR + Red)
- ✅ NDWI computed for water detection: (Green - NIR) / (Green + NIR)
- ✅ NDVI threshold approach (NDVI < 0.2–0.3) to identify bare soil parcels
- ✅ Output: Binary mask per parcel (bare/vegetated) in standardized format

**Cloud Gap Handling:**
- ✅ Cloud masking using SCL (Scene Classification Layer) to exclude unreliable pixels
- ✅ Multi-date compositing: Best available observation selection (max NDVI or median composite)
- ✅ Temporal window: Use multiple images within classification period (e.g., July–August for summer, Jan–Feb for winter)
- ✅ Graceful degradation: If <3 clear images available, flag uncertainty but still output result

**Time-Series Phenology Context (Robustness Enhancement):**
- ✅ Leverage NDVI/NDWI time-series throughout season to improve robustness
- ✅ Distinguish harvested fields (high NDVI mid-season, low end-season) from fallow fields (low NDVI all season)
- ✅ Temporal pattern recognition:
  - **Harvested crop**: max NDVI > 0.6, end NDVI < 0.2 (NDVI drop indicates harvest)
  - **Truly fallow**: max NDVI < 0.3 all season (consistently bare)
- ✅ Minimize false negatives (bare fields missed) by incorporating phenology patterns

**Performance & Accuracy KPIs:**
- 🎯 **KPI: >90% bare soil detection accuracy** - Correctly identify at least 90% of truly uncultivated parcels in each season (validated against ground truth or farmer reports)
- ✅ NDVI threshold approach minimizes false negatives (bare fields missed)
- ✅ Process completes within 2 hours for ~10,000 parcels
- ✅ No manual intervention required between seasons

**Priority:** Must Have

**Technical Implementation:**
- Module: `queries.py::query_irr_01_bare_soil_classification()`
- Data sources: Sentinel-2 Level-2A (STAC API), NDVI/NDWI extraction via rasterio
- Caching: 24-hour NDVI/NDWI cache for reuse
- Visualization: Pie charts (class distribution), histograms (NDVI distribution), interactive Folium maps

**Validation:**
- Confusion matrix vs ground truth (500-parcel sample)
- Validate against farmer reports or field surveys

---

#### **IRR-US-02: Dynamic Crop Assignment Logic**

**User Story:**
As a **developer of the ABM simulation**, I want the system to dynamically assign crops to bare soil parcels using seasonal rotation rules (summer-to-winter, winter-to-summer), so that the simulation reflects realistic farmer decision-making and crop rotation patterns.

**Requirements:**
Using the EO-derived classification from IRR-US-01, the system dynamically assigns crops to each parcel for the next season, following regional agricultural practices.

**Acceptance Criteria:**

**Summer-to-Winter Rule (Deterministic):**
- ✅ During summer growing season (May–September), any parcel identified as bare soil → automatically assigned **winter wheat** for next winter cycle
- ✅ Rationale: Farmers utilize fallow summer fields by planting winter wheat in autumn (common practice in Greece)
- ✅ Example: If July–August Sentinel-2 shows NDVI < 0.2 (no summer vegetation) → flag for winter wheat planting in October
- ✅ Agent-based implementation: Agent observes land status (bare summer) → decides to plant wheat in fall
- ✅ 100% assignment rate: All bare-summer parcels receive winter wheat assignment

**Winter-to-Summer Rule (Stochastic):**
- ✅ During winter season (November–February), any parcel classified as bare soil → randomly assigned to one of three summer crops: **maize**, **cotton**, or **rice**
- ✅ Random assignment: Uniform or weighted based on regional crop distribution (configurable probabilities)
- ✅ Example: Field not sown with winter wheat (NDVI low in Jan–Feb) → system assigns "maize" (or "cotton" or "rice") for April planting
- ✅ Stochastic element: Introduces crop diversity, models heterogeneous farmer behavior
- ✅ Agent-based implementation: Agent observes land status (bare winter) → randomly chooses summer crop from {maize, cotton, rice}
- ✅ 100% assignment rate: All bare-winter parcels receive summer crop assignment

**Justification & Context:**
- ✅ Mimics farmers' decision-making: Idle land in one season → utilized in next for suitable crop
- ✅ Reflects double-cropping patterns: Winter cereals (wheat) followed by summer cash crops (maize/cotton/rice)
- ✅ Crop rotation benefits: Soil health, pest control, economic diversification
- ✅ Adaptive land-use: System does NOT assume static crop map, adapts each year based on EO observations

**Agent-Based Implementation:**
- ✅ Parcel/farming agent applies rules as part of behavior
- ✅ Agent "observes" land status (via EO data) at season end
- ✅ Agent "decides" on next crop using rule-based policy:
  - IF bare summer → plant wheat in fall
  - IF bare winter → random choice {maize, cotton, rice} for spring
- ✅ Multi-level ABM integration: Satellite data drives individual agent actions → affects regional land-use patterns

**Performance & Reproducibility KPIs:**
- 🎯 **KPI: 100% parcels assigned** - All bare soil parcels receive crop assignment (no unassigned parcels)
- 🎯 **KPI: Deterministic & reproducible** - Same input → same output (seeded RNG for winter-to-summer randomization)
- ✅ Assignment logged for traceability: {parcel_id, season, previous_crop, new_crop, reason}
- ✅ Validation: Over 1000 bare-winter parcels, distribution matches configured probabilities ±2%

**Priority:** Must Have

**Technical Implementation:**
- Module: `queries.py::apply_crop_rotation_rules()`
- Rule engine: Deterministic summer→winter, stochastic winter→summer
- Configuration: `config.yaml` probabilities (e.g., `{maize: 0.4, cotton: 0.4, rice: 0.2}`)
- Agent integration: Farmer agent decision model in `agents/farmer_agent.py`

---

#### **IRR-US-03: Rice Flood Detection via NDWI**

**User Story:**
As a **developer of the water balance model**, I want the system to validate rice parcels by detecting actual flooding via NDWI (Normalized Difference Water Index) from Sentinel-2, so that only truly flooded fields use the paddy irrigation regime in AquaCrop.

**Requirements:**
Many parcels may be assigned "rice" in the crop rotation logic (IRR-US-02), but not all rice parcels are actually flooded (some farmers may fail to plant or choose rainfed rice). This user story ensures the irrigation model accurately reflects on-the-ground conditions.

**Acceptance Criteria:**

**NDWI Monitoring:**
- ✅ All parcels assigned `crop = "RICE"` monitored for NDWI in May–June flooding period
- ✅ NDWI calculation: (Green - NIR) / (Green + NIR) from Sentinel-2
- ✅ Flooding detection criteria (configurable):
  - **Option 1**: NDWI > 0.2 on any single date in May/early June → `isFlooded = True`
  - **Option 2**: NDWI > 0 sustained for ≥7 consecutive days → `isFlooded = True`
- ✅ Parcels not meeting criteria → `isFlooded = False`

**AquaCrop Regime Selection:**
- ✅ Flooded rice parcels (`isFlooded = True`):
  - Use AquaCrop continuous flooding regime (rice_flooded.CRO)
  - Ponding depth: 5–10 cm (configurable)
  - Percolation rate: Site-specific from soil data
  - Water table: At surface
- ✅ Non-flooded rice parcels (`isFlooded = False`):
  - Use rainfed or supplemental irrigation regime (rice_rainfed.CRO)
  - OR reassign to alternate crop if NDVI rises in June (see Dynamic Reassignment below)

**Dynamic Reassignment (Optional):**
- ✅ If `crop = "RICE"` and `isFlooded = False` by end of May:
  - Check June NDVI: If NDVI > 0.4 → reassign to "MAIZE_LATE_PLANTED"
  - If NDVI remains low → mark as "FALLOW" (no crop simulation)
- ✅ Reassignment logic configurable (user chooses behavior)
- ✅ All reassignments logged with reason code
- ✅ Final crop distribution report shows "rice_planned vs rice_actual"

**Performance & Accuracy KPIs:**
- 🎯 **KPI: >85% precision** - True flooded / (True flooded + False positives) - Minimize false flooding detections
- 🎯 **KPI: >85% recall** - True flooded / (True flooded + Missed flooded) - Minimize missed flooding events
- ✅ Validation: Compare NDWI detections to high-resolution imagery (PlanetScope 3m) or farmer reports
- ✅ Water balance closure: Inputs (irrigation + rain) = Outputs (ET + percolation + runoff + Δstorage) ±1%

**Priority:** Must Have

**Technical Implementation:**
- Module: `queries.py::validate_rice_flooding()`
- NDWI time-series extraction: STAC API, rasterio
- Temporal analysis: 5-day Sentinel-2 revisit, interpolation for cloud gaps
- AquaCrop integration: Conditional .CRO file selection based on `isFlooded` flag

**Validation:**
- Sample 200 rice parcels, visual inspection of Sentinel-2 imagery for standing water
- Cross-reference with SAR (Sentinel-1) flood maps (SAR not affected by clouds)

---

#### **IRR-US-04: AquaCrop Integration & Seasonal Reset**

**User Story:**
As a **developer of the crop water model**, I want AquaCrop to reinitialize at every season transition with the updated crop plan from IRR-US-02, carrying over soil moisture from the previous season, so that the 5-year multi-seasonal simulation runs seamlessly without manual intervention.

**Requirements:**
The system must handle winter→summer and summer→winter transitions, loading new crop parameters while maintaining soil moisture continuity.

**Acceptance Criteria:**

**Seamless Seasonal Re-Initialization:**
- ✅ System reads crop plan file: `{parcel_id, crop_type, sowing_date, isFlooded (for rice)}`
- ✅ For each parcel:
  - Loads appropriate crop parameter file: wheat.CRO, maize.CRO, cotton.CRO, rice_flooded.CRO, rice_rainfed.CRO
  - Sets sowing date from crop plan (configurable per crop)
  - Retrieves **final soil moisture** from previous season AquaCrop simulation
  - Initializes soil profile with **carryover moisture** (no discontinuity)
  - Loads climate file (temperature, precipitation, ET₀) for new season
  - Sets irrigation management file based on crop type

**Irrigation Management:**
- ✅ **Flooded rice**: Continuous flooding regime (maintain ponding, ponding depth 5–10 cm)
- ✅ **Maize/Cotton**: Deficit irrigation (irrigate when soil moisture < threshold)
- ✅ **Wheat**: Rainfed (no irrigation, or minimal supplemental)
- ✅ **Fallow**: No crop simulation (skip parcel)

**Performance & Reliability KPIs:**
- 🎯 **KPI: 100% seasonal transition success rate** - All parcels reinitialize without errors
- 🎯 **KPI: <10% computational overhead** - Re-initialization adds <10% to total runtime
- ✅ Re-initialization completes within 5 minutes for 10,000 parcels
- ✅ Soil moisture continuity validated: No discontinuities >10 mm between seasons
- ✅ Water balance closure maintained: ±1% error per season

**Error Handling:**
- ✅ If .CRO file missing → log error, skip parcel, notify user
- ✅ If soil moisture carryover fails → use default initial conditions, flag uncertainty
- ✅ All errors logged with parcel_id, season, error type

**Priority:** Must Have

**Technical Implementation:**
- Module: `queries.py::reinitialize_aquacrop_seasonal()`
- AquaCrop wrapper: Python subprocess calls or AquaCrop-OSPy integration
- Soil moisture carryover: Extract from previous season output, write to initial conditions file
- Parallelization: GNU Parallel or Dask for 10,000-parcel batch processing

**Validation:**
- End-to-end 5-year simulation test (10 seasons): Verify no crashes, plausible outputs
- Soil moisture time-series: Plot across season transitions, check continuity

---

#### **IRR-US-05: Irrigation Modeling Impact Assessment**

**User Story:**
As a **water resource manager**, I want to compare irrigation demand forecasts from the dynamic EO-based crop rotation system versus a static crop map baseline, so that I can quantify the value of real-time EO updates.

**Requirements:**
Demonstrate that the dynamic system (IRR-US-01 + IRR-US-02 + IRR-US-03 + IRR-US-04) improves forecast accuracy compared to traditional static approaches.

**Acceptance Criteria:**

**Baseline Comparison:**
- ✅ **Static Baseline**: Assumes fixed crop distribution (e.g., 30% wheat, 30% maize, 20% cotton, 20% rice every year)
- ✅ **Dynamic EO-Based**: Uses actual bare soil classification → dynamic crop assignment each season
- ✅ Run both scenarios for same 5-year period (e.g., 2020–2024 historical)
- ✅ Compute irrigation demand for both (total m³, seasonal breakdown)

**Accuracy Metrics:**
- ✅ **Mean Absolute Error (MAE)**: |Simulated - Observed| irrigation demand
- ✅ **Relative Error**: (Simulated - Observed) / Observed × 100%
- ✅ Compare against historical irrigation records (if available) or water authority allocation data

**Performance KPIs:**
- 🎯 **KPI: Dynamic system achieves <5% MAE** vs historical data
- 🎯 **KPI: Static baseline typically has ~15% MAE** (demonstrates 3x improvement)
- ✅ Document scenarios where dynamic excels: Drought years (more fallow detected), land-use changes
- ✅ Uncertainty quantification: Confidence intervals for irrigation forecasts

**Reporting:**
- ✅ Comparison dashboard: Side-by-side charts (static vs dynamic irrigation demand)
- ✅ Annual breakdown: Show which years dynamic performed best
- ✅ Spatial analysis: Map parcels where dynamic captured crop changes missed by static
- ✅ Policy recommendations: "Dynamic EO saves X% water allocation errors"

**Priority:** Should Have

**Technical Implementation:**
- Module: `queries.py::compare_static_vs_dynamic()`
- Baseline generator: Create static crop map from regional statistics
- Comparison metrics: MAE, RMSE, bias
- Visualization: Plotly side-by-side time-series, difference heatmaps

**Validation:**
- Use 2015–2019 as calibration, 2020–2024 as validation period
- If historical data unavailable: Qualitative validation via stakeholder workshops

---

#### **IRR-US-06: Data & Module Interfaces**

**User Story:**
As a **system integrator**, I want all components (EO classification, crop assignment, rice flood detection, AquaCrop wrapper) to communicate via well-defined data interfaces and modular APIs, so that the system is maintainable, testable, and extensible.

**Requirements:**
Enforce clean architecture with clear separation of concerns. Each module should be independently testable and replaceable.

**Acceptance Criteria:**

**Modular Architecture:**
- ✅ **EO Classification Module** (IRR-US-01):
  - Input: {region, season, date_range}
  - Output: `{parcel_id: classification_status (bare/vegetated/flooded), confidence, phenology_metrics}`
  - Interface: RESTful API endpoint or Python function call
- ✅ **Crop Assignment Module** (IRR-US-02):
  - Input: `{parcel_id: classification_status, season}`
  - Output: `{parcel_id: assigned_crop, sowing_date}`
  - Interface: Rule engine function, configurable via YAML
- ✅ **Rice Flood Detection Module** (IRR-US-03):
  - Input: `{parcel_id: crop (rice parcels only), date_range (May–June)}`
  - Output: `{parcel_id: isFlooded (boolean), NDWI_peak, flooding_dates}`
  - Interface: Separate validation function
- ✅ **AquaCrop Wrapper** (IRR-US-04):
  - Input: `{parcel_id, crop_type, sowing_date, initial_soil_moisture, climate_file, irrigation_regime}`
  - Output: `{parcel_id, daily_soil_moisture, ET, irrigation, yield}`
  - Interface: Subprocess wrapper or Python bindings (AquaCrop-OSPy)

**Data Formats:**
- ✅ All inter-module communication uses **JSON or Parquet** (standardized, versioned)
- ✅ Geospatial data: GeoJSON for parcel boundaries, COG (Cloud-Optimized GeoTIFF) for rasters
- ✅ Time-series: NetCDF or Parquet (columnar storage for efficient querying)

**API Design:**
- ✅ RESTful endpoints for all services (if microservices architecture)
- ✅ Synchronous APIs for real-time requests (<1s latency)
- ✅ Asynchronous task queue (RabbitMQ, Celery) for batch processing (10,000 parcels)

**Testing & Documentation:**
- ✅ **Unit tests**: Each module tested independently (>80% code coverage)
- ✅ **Integration tests**: End-to-end pipeline test (EO → Crop Assignment → AquaCrop)
- ✅ **API documentation**: OpenAPI/Swagger spec for all endpoints
- ✅ **Data schemas**: JSON Schema or Pydantic models for all interfaces

**Performance & Maintainability KPIs:**
- 🎯 **KPI: Modularity** - Each component replaceable without breaking others (e.g., swap AquaCrop for DSSAT)
- 🎯 **KPI: Testability** - >80% code coverage, all modules independently testable
- ✅ Version control: Semantic versioning for all module releases (v1.0.0, v1.1.0, etc.)
- ✅ Logging: Structured logs (JSON) with trace IDs for debugging

**Priority:** Must Have

**Technical Implementation:**
- Framework: FastAPI (Python) for RESTful services
- Data validation: Pydantic models for all request/response schemas
- Testing: pytest, unittest, CI/CD pipeline (GitHub Actions)
- Documentation: MkDocs or Sphinx for user/developer guides

**Validation:**
- Conduct code review: Check adherence to SOLID principles
- Perform load testing: Verify 10,000-parcel batch completes within SLA
- Developer survey: Assess ease of module extension/replacement

---

### 7.2 Multi-Level ABM User Stories (Future Enhancements)

#### **IRR-US-07: Farmer Agent Crop Decision**

**User Story:**
As a **Water Authority Agent**, I want to monitor total regional irrigation demand and rice cultivation area each season, and trigger policy alerts if sustainable limits are exceeded.

**Acceptance Criteria:**
- ✅ Authority agent receives aggregated demand from all cooperatives
- ✅ Computes total regional demand: Sum of all cooperative requests
- ✅ Computes total rice area: Count of parcels with `crop = "RICE"` and `isFlooded = True`
- ✅ Policy rules:
  - If total demand > sustainable limit (e.g., 200 million m³/year) → Alert: "Demand exceeds sustainability"
  - If rice area > target (e.g., 15,000 ha) → Alert: "Rice area exceeds CAP limits"
- ✅ Alerts logged and displayed to user in dashboard
- ✅ (Future) Authority can adjust policies: reduce subsidies, impose water quotas

**Priority:** Should Have

---

### 7.6 Visualization & Reporting User Stories

#### **IRR-US-12: Interactive Crop Distribution Map**

**User Story:**
As a **Policymaker**, I want to view an interactive map showing crop distribution for any year/season of the simulation, with color-coding by crop type, so that I can understand land-use patterns.

**Acceptance Criteria:**
- ✅ Map displays all parcels color-coded: wheat (yellow), maize (green), cotton (white), rice (blue), bare (gray)
- ✅ User can select year and season (e.g., "2022 Summer") from dropdown
- ✅ Clicking a parcel shows popup: crop type, irrigation used, yield, NDVI history
- ✅ Export options: PNG, PDF, GeoJSON
- ✅ Map loads in <3 seconds for 10,000 parcels

**Priority:** Must Have

---

#### **IRR-US-13: Seasonal Irrigation Demand Chart**

**User Story:**
As a **Water Management Officer**, I want to view a time-series chart of seasonal irrigation demand (winter and summer for each year) so that I can identify trends and plan reservoir releases.

**Acceptance Criteria:**
- ✅ Chart shows 10 bars (5 winters + 5 summers) with irrigation volume (million m³)
- ✅ Overlays: Sustainable limit threshold as horizontal line
- ✅ Tooltips: Hover to see breakdown by crop (e.g., "Summer 2023: 50 Mm³ rice, 30 Mm³ maize, 20 Mm³ cotton")
- ✅ Export as PNG, CSV (tabular data)
- ✅ Interactive: Click bar to drill down into cooperative-level demands

**Priority:** Must Have

---

#### **IRR-US-14: Rice Flooding Event Map**

**User Story:**
As an **Environmental Scientist**, I want to see a map of all rice flooding events detected by NDWI over the 5-year simulation, with timing information, so that I can validate model outputs against satellite observations.

**Acceptance Criteria:**
- ✅ Map layer: Points or polygons for all flooded rice parcels
- ✅ Color gradient: Flooding start date (early May = dark blue, late May = light blue)
- ✅ Popup: Parcel ID, flooding dates, peak NDWI value, total water used
- ✅ Toggle layer on/off per year
- ✅ Export: GeoJSON with flooding metadata

**Priority:** Should Have

---

#### **IRR-US-15: Policy Scenario Comparison**

**User Story:**
As a **Policymaker**, I want to compare irrigation demand between baseline and policy scenarios (e.g., "limit rice to 20% of area"), side-by-side, so that I can evaluate policy effectiveness.

**Acceptance Criteria:**
- ✅ Run multiple simulations: Baseline, Policy A, Policy B
- ✅ Dashboard shows side-by-side comparison:
  - Total 5-year irrigation (bar chart)
  - Rice area evolution (line chart)
  - Number of water shortage events (table)
- ✅ Difference highlighting: "Policy A reduces irrigation by 12% vs baseline"
- ✅ Export comparison report as PDF

**Priority:** Should Have

---

### 7.7 Data & Integration User Stories

#### **IRR-US-16: Sentinel-2 Data Ingestion**

**User Story:**
As a **System Administrator**, I want the system to ingest Sentinel-2 Level-2A imagery for the region of interest, extracting NDVI and NDWI bands, and storing them in a spatiotemporal database for use by the classification module.

**Acceptance Criteria:**
- ✅ Automated script downloads Sentinel-2 tiles covering Thessaloniki–Pella–Imathia
- ✅ Processes imagery: Cloud masking, NDVI = (NIR - Red)/(NIR + Red), NDWI = (Green - NIR)/(Green + NIR)
- ✅ Stores time-series in database (PostGIS or raster database): {date, parcel_id, NDVI, NDWI}
- ✅ Ingestion frequency: Weekly during growing season, monthly off-season
- ✅ Data validation: Flag images with >80% cloud cover over region

**Priority:** Must Have (for operational use; manual pre-processing acceptable for Phase 1)

---

#### **IRR-US-17: AquaCrop Output Export**

**User Story:**
As a **Researcher**, I want to export AquaCrop simulation outputs (daily soil moisture, ET, irrigation, yield) for all parcels as CSV or NetCDF files, so that I can perform custom analyses.

**Acceptance Criteria:**
- ✅ Export button in UI: "Export AquaCrop Outputs"
- ✅ User selects parcels (all, or filtered by crop/year), variables, format
- ✅ CSV: Columns = date, parcel_id, soil_moisture_mm, ET_mm, irrigation_mm, biomass_kg_ha, yield_kg_ha
- ✅ NetCDF: Multidimensional (time, parcel, variable)
- ✅ File size: Compressed if >100 MB
- ✅ Download completes in <30 seconds

**Priority:** Should Have

---

## 8. Functional Requirements

### 8.1 EO Data Processing

**FR-IRR-01: NDVI Computation**
**Priority:** Must Have
**Description:** System computes NDVI for each parcel from Sentinel-2 NIR and Red bands.

**Specifications:**
- Input: Sentinel-2 L2A imagery (10m resolution, bands B4=Red, B8=NIR)
- Formula: NDVI = (NIR - Red) / (NIR + Red)
- Output range: [-1, 1] (vegetated areas typically 0.2–0.9)
- Cloud masking: Use SCL (Scene Classification Layer) to exclude clouds
- Parcel aggregation: Mean NDVI within parcel boundary (zonal statistics)
- Storage: Time-series database {parcel_id, date, NDVI}

---

**FR-IRR-02: NDWI Computation**
**Priority:** Must Have
**Description:** System computes NDWI for water detection from Sentinel-2 Green and NIR bands.

**Specifications:**
- Input: Sentinel-2 L2A (B3=Green, B8=NIR)
- Formula: NDWI = (Green - NIR) / (Green + NIR)
- Output range: [-1, 1] (water typically >0, dry soil <0)
- Cloud masking: Same as NDVI
- Parcel aggregation: Mean NDWI within parcel
- Flooding threshold: Configurable (default NDWI > 0.2)

---

**FR-IRR-03: Bare Soil Classification**
**Priority:** Must Have
**Description:** Classify parcels as bare soil using NDVI threshold and temporal consistency.

**Specifications:**
- Threshold: NDVI < 0.2–0.3 (configurable)
- Temporal window: All images in classification period (e.g., Jul–Aug for summer)
- Consistency check: Parcel bare if NDVI < threshold in ≥80% of clear observations
- Water exclusion: If NDWI > 0, classify as "water" not "bare soil"
- Output: Binary map {parcel_id: "bare" | "vegetated" | "water"}
- Accuracy target: >90% vs ground truth

---

**FR-IRR-04: Phenology Time-Series Analysis**
**Priority:** Should Have
**Description:** Analyze NDVI time-series to distinguish crop phenology patterns.

**Specifications:**
- Metrics computed per parcel:
  - Max NDVI during season
  - Date of max NDVI (peak greenness)
  - NDVI at season start and end
  - Rate of NDVI decline (senescence slope)
- Classification:
  - Harvested crop: max NDVI > 0.6, end NDVI < 0.2
  - Fallow: max NDVI < 0.3 all season
  - Perennial/permanent: NDVI stable >0.5
- Output: Phenology category per parcel
- Use: Improve bare soil classification accuracy

---

### 8.2 Crop Assignment Logic

**FR-IRR-05: Summer-to-Winter Wheat Assignment**
**Priority:** Must Have
**Description:** Assign winter wheat to all bare-summer parcels at season transition.

**Specifications:**
- Input: List of bare-summer parcels {parcel_ids}
- Assignment: For each parcel, `crop = "WINTER_WHEAT"`, `sowing_date = "October 15"` (configurable)
- Deterministic: All bare-summer → wheat (no randomness)
- Agent update: Farmer agent state updated with new crop
- Logging: Record assignment {parcel_id, season, previous_crop, new_crop="WHEAT"}

---

**FR-IRR-06: Winter-to-Summer Random Assignment**
**Priority:** Must Have
**Description:** Randomly assign maize, cotton, or rice to bare-winter parcels based on probabilities.

**Specifications:**
- Input: List of bare-winter parcels {parcel_ids}
- Probabilities: Configurable {maize: p_m, cotton: p_c, rice: p_r}, sum=1.0
- Random number generator: Seeded for reproducibility (user-specified seed)
- Assignment: Draw from multinomial distribution per parcel
- Validation: Over N parcels, distribution = probabilities ±2%
- Output: {parcel_id: "MAIZE" | "COTTON" | "RICE"}

---

**FR-IRR-07: Crop Parameter Database**
**Priority:** Must Have
**Description:** Maintain database of crop parameters for AquaCrop (sowing dates, growing degree days, water requirements).

**Specifications:**
- Crops: Winter wheat, maize, cotton, rice (flooded), rice (rainfed)
- Parameters per crop:
  - AquaCrop .CRO file path
  - Default sowing date (month/day)
  - Growing season length (days)
  - Water requirement class (low/medium/high)
- User interface: View and edit crop parameters
- Validation: Check .CRO file exists, sowing dates valid for region

---

### 8.3 Rice Flood Detection

**FR-IRR-08: NDWI Monitoring for Rice Parcels**
**Priority:** Must Have
**Description:** Monitor NDWI time-series for rice-assigned parcels during May–June flooding period.

**Specifications:**
- Input: All parcels with `crop = "RICE"`
- Monitoring window: May 1 – June 30
- Data source: Sentinel-2 NDWI time-series (5-day revisit)
- Flooding criteria:
  - Option 1: NDWI > 0.2 on any single date
  - Option 2: NDWI > 0 sustained for ≥7 consecutive days (requires interpolation)
- Output: {parcel_id: isFlooded (boolean)}

---

**FR-IRR-09: Rice Flooding Confirmation**
**Priority:** Must Have
**Description:** Flag rice parcels as flooded or non-flooded based on NDWI thresholds.

**Specifications:**
- If NDWI criteria met → `isFlooded = True`
- If NDWI criteria not met → `isFlooded = False`
- AquaCrop regime selection:
  - isFlooded=True → Use rice_flooded.CRO (continuous ponding)
  - isFlooded=False → Use rice_rainfed.CRO or reassign (see FR-IRR-10)
- Precision target: >85% (few false positives)
- Recall target: >85% (few false negatives)

---

**FR-IRR-10: Rice Parcel Reassignment**
**Priority:** Should Have
**Description:** Reassign rice parcels that are not confirmed as flooded to alternate crop or fallow.

**Specifications:**
- Trigger: `crop = "RICE"` and `isFlooded = False` by end of May
- Reassignment options (user configurable):
  - Check June NDVI: If NDVI > 0.4 → reassign to "MAIZE_LATE_PLANTED"
  - If NDVI remains low → mark as "FALLOW" (no crop simulation)
- Logging: Record reassignment reason
- Impact: Final crop distribution shows "rice_planned" vs "rice_actual_flooded"

---

### 8.4 AquaCrop Integration

**FR-IRR-11: AquaCrop Initialization per Parcel**
**Priority:** Must Have
**Description:** Initialize AquaCrop simulation for each parcel each season with crop-specific parameters.

**Specifications:**
- Input: Crop plan {parcel_id, crop_type, sowing_date, isFlooded (for rice)}
- For each parcel:
  - Load .CRO file for crop_type
  - Load soil profile (from GIS soil data)
  - Load climate file (temperature, rainfall, ET₀ for simulation period)
  - Set sowing date, irrigation management file
- Irrigation management:
  - Flooded rice: Continuous flooding (maintain ponding)
  - Maize/cotton: Deficit irrigation (irrigate when soil moisture < threshold)
  - Wheat: Rainfed (no irrigation, or minimal supplemental)
- Initial conditions: Soil moisture from previous season (carryover)

---

**FR-IRR-12: Seasonal Re-initialization**
**Priority:** Must Have
**Description:** Re-initialize AquaCrop at winter→summer and summer→winter transitions with updated crop plans.

**Specifications:**
- Timing: Triggered after crop assignment module completes
- Process:
  - Finalize previous season simulation (extract final soil moisture)
  - Read new crop plan
  - Re-initialize AquaCrop with new crops
  - Transfer soil moisture (carryover)
- Validation: No simulation errors, soil moisture continuity (no jumps >10 mm)
- Performance: Complete re-init for 10,000 parcels in <5 minutes

---

**FR-IRR-13: Water Balance Output**
**Priority:** Must Have
**Description:** AquaCrop outputs daily water balance components for each parcel.

**Specifications:**
- Output variables:
  - Soil moisture (mm)
  - Evapotranspiration: ET_act, ET_pot (mm/day)
  - Irrigation applied (mm/day)
  - Precipitation (mm/day)
  - Deep percolation (mm/day)
  - Runoff (mm/day)
  - Change in storage (mm/day)
- Water balance closure: Input = Output ± 1% error
- Storage: Daily time-series per parcel in database
- Aggregation: Seasonal irrigation = sum(irrigation_daily)

---

**FR-IRR-14: Crop Yield Output**
**Priority:** Should Have
**Description:** AquaCrop simulates biomass and grain yield for each crop.

**Specifications:**
- Output per parcel per season:
  - Final biomass (kg/ha dry matter)
  - Grain yield (kg/ha at harvest moisture)
  - Harvest index
- Validation: Compare simulated yields to regional statistics (±15% acceptable)
- Use: Economic impact analysis (future enhancement)

---

### 8.5 Multi-Level ABM

**FR-IRR-15: Farmer Agent Initialization**
**Priority:** Must Have
**Description:** Create farmer agent for each parcel with attributes and decision rules.

**Specifications:**
- One agent per parcel
- Attributes:
  - parcel_id (unique)
  - location (lat/lon)
  - soil_type
  - current_crop
  - irrigation_used_last_season (m³)
- Decision rules:
  - Observe EO land_status at season end
  - Apply summer-to-winter or winter-to-summer rule
  - Update current_crop
- Future enhancement: Economic optimization, risk aversion

---

**FR-IRR-16: Water Cooperative Agent**
**Priority:** Should Have
**Description:** Create cooperative agents representing irrigation districts, aggregating demand from member parcels.

**Specifications:**
- Cooperative definition: Spatial cluster of parcels (e.g., within 5 km radius)
- Attributes:
  - cooperative_id
  - member_parcels (list)
  - total_irrigated_area (ha)
  - canal_capacity (m³/day)
- Behavior:
  - Each season: Sum irrigation demand from member parcels
  - Submit request to water authority
  - Receive allocation (may be <100% if shortage)
  - (Future) Allocate among members based on priority rules

---

**FR-IRR-17: Water Authority Agent**
**Priority:** Should Have
**Description:** Policy-level agent monitoring regional demand and enforcing sustainability limits.

**Specifications:**
- Single agent per simulation (regional scale)
- Attributes:
  - total_sustainable_limit (m³/year)
  - rice_area_target (ha)
  - current_policy (e.g., "no restrictions" or "rice area cap")
- Behavior:
  - Receive cooperative requests
  - Compute total demand
  - If demand > limit → flag alert
  - If rice area > target → flag alert
  - (Future) Adjust policies: reduce allocations, change subsidies

---

**FR-IRR-18: Cross-Scale Feedback Loops**
**Priority:** Could Have
**Description:** Implement feedback from policy/cooperative levels to farmer agents (e.g., water scarcity signals influence crop choice).

**Specifications:**
- Water scarcity signal: If allocation < 100%, cooperatives broadcast to members
- Farmer response (future RL): Agents learn to choose less water-intensive crops if scarcity frequent
- For Phase 1: One-way flow (farmers → cooperatives → authority)
- For Phase 2+: Two-way feedback (authority policies → farmer adaptation)

---

### 8.6 Visualization

**FR-IRR-19: Interactive Crop Map**
**Priority:** Must Have
**Description:** Web-based interactive map of crop distribution per season.

**Specifications:**
- Technology: Leaflet or Mapbox GL JS
- Layers: Parcel boundaries color-coded by crop
- Color scheme: Wheat=yellow, maize=green, cotton=white, rice=blue, bare=gray
- Controls: Year/season selector (dropdown)
- Interactivity: Click parcel for popup (crop, area, irrigation, yield)
- Performance: Render 10,000 parcels in <3 seconds
- Export: PNG, PDF, GeoJSON

---

**FR-IRR-20: Time-Series Charts**
**Priority:** Must Have
**Description:** Interactive charts for irrigation demand and crop area over time.

**Specifications:**
- Chart library: Plotly or D3.js
- Chart types:
  - Bar chart: Seasonal irrigation (10 bars for 5 years)
  - Line chart: Crop area evolution (4 lines: wheat, maize, cotton, rice)
  - Stacked area: Crop distribution over time
- Tooltips: Hover for exact values
- Export: PNG, SVG, CSV (data table)

---

**FR-IRR-21: Rice Flooding Event Visualization**
**Priority:** Should Have
**Description:** Map layer showing rice flooding events detected by NDWI.

**Specifications:**
- Geometry: Points or polygons for flooded parcels
- Symbology: Color by flooding start date (gradient)
- Popup: Flooding dates, peak NDWI, total water used
- Toggle: On/off per year
- Export: GeoJSON with metadata

---

**FR-IRR-22: Policy Scenario Dashboard**
**Priority:** Should Have
**Description:** Comparison dashboard for multiple simulation scenarios.

**Specifications:**
- Layout: Side-by-side panels for 2–3 scenarios
- Metrics compared:
  - Total 5-year irrigation (bar chart)
  - Rice area evolution (line chart)
  - Water shortage events (table)
- Difference highlighting: "Scenario A: -12% irrigation vs baseline"
- Export: PDF report with all charts

---

### 8.7 Data Management

**FR-IRR-23: Parcel GIS Database**
**Priority:** Must Have
**Description:** Store parcel boundaries and attributes in PostGIS database.

**Specifications:**
- Geometry: Polygon (multipolygon for complex parcels)
- Attributes: parcel_id, area_ha, soil_type, owner (anonymized)
- Spatial indexing: For fast queries
- API: RESTful endpoint for parcel CRUD operations
- Import: Shapefile, GeoJSON upload

---

**FR-IRR-24: EO Time-Series Database**
**Priority:** Must Have
**Description:** Store NDVI/NDWI time-series in spatiotemporal database.

**Specifications:**
- Schema: {parcel_id, date, NDVI, NDWI, cloud_cover}
- Database: PostGIS + TimescaleDB extension (for time-series optimization)
- Indexing: Composite index on (parcel_id, date)
- Retention: 10 years of data
- Query performance: Retrieve full time-series for 10,000 parcels in <10 seconds

---

**FR-IRR-25: AquaCrop Results Database**
**Priority:** Must Have
**Description:** Store AquaCrop simulation outputs (daily water balance, yields).

**Specifications:**
- Schema: {parcel_id, date, soil_moisture, ET, irrigation, yield}
- Database: TimescaleDB or InfluxDB (time-series optimized)
- Aggregation: Pre-compute seasonal totals (irrigation, yield) for fast dashboards
- Export API: CSV, NetCDF download endpoints
- Storage: ~1 TB for 10,000 parcels × 5 years × daily data

---

## 9. Technical Requirements

### 9.1 System Architecture

**TR-IRR-01: Modular Microservices**
**Priority:** Must Have
**Description:** Implement as microservices for scalability and maintainability.

**Specifications:**
- Services:
  - **EO Processing Service**: NDVI/NDWI computation, classification
  - **Crop Assignment Service**: Rule-based crop allocation
  - **AquaCrop Wrapper Service**: Manages AquaCrop runs, parses outputs
  - **ABM Engine**: Mesa-based agent simulation
  - **Data Service**: API for database access
  - **Visualization Service**: Web UI and map rendering
- Communication: RESTful APIs + message queue (RabbitMQ or Kafka) for async tasks
- Deployment: Docker containers, Kubernetes orchestration

---

**TR-IRR-02: High-Performance Computing**
**Priority:** Should Have
**Description:** Leverage HPC or cloud GPU instances for large-scale simulations.

**Specifications:**
- Parallel AquaCrop runs: GNU Parallel or Dask for 10,000 parcel simulations
- EO processing: Use cloud-optimized GeoTIFFs (COGs) for fast access
- ABM scalability: Mesa with parallel agent updates (if available) or custom parallelization
- Target: 5-year simulation for 10,000 parcels completes in <2 hours

---

**TR-IRR-03: Cloud Infrastructure**
**Priority:** Must Have
**Description:** Deploy on cloud platform (AWS, Azure, or Google Cloud).

**Specifications:**
- Compute: Auto-scaling EC2/VM instances (or Kubernetes nodes)
- Storage: S3/Blob Storage for EO imagery, RDS/Cloud SQL for databases
- Networking: Load balancer, VPC for secure communication
- Cost optimization: Spot instances for batch processing, reserved instances for databases

---

### 9.2 Performance Requirements

**TR-IRR-04: EO Classification Performance**
**Priority:** Must Have
**Description:** Bare soil classification completes within 2 hours for 10,000 parcels.

**Specifications:**
- Input: Sentinel-2 imagery for 1 classification window (e.g., Jul–Aug: ~6 images)
- Processing: NDVI computation, cloud masking, zonal statistics
- Output: Classification map
- Target: 2 hours on 16-core machine or 30 minutes on 64-core HPC

---

**TR-IRR-05: AquaCrop Simulation Performance**
**Priority:** Must Have
**Description:** Seasonal AquaCrop simulations complete within 1 hour for 10,000 parcels.

**Specifications:**
- Parallelization: Run parcels in parallel (batches of 100)
- Per-parcel runtime: <5 seconds (typical for 120-day season)
- Total runtime: 10,000 parcels / 100 parallel × 5 sec ≈ 8 minutes (ideal), <1 hour (conservative)
- Resource: 32-core server

---

**TR-IRR-06: Dashboard Responsiveness**
**Priority:** Must Have
**Description:** Web dashboard loads and renders visualizations within 3 seconds.

**Specifications:**
- Map rendering: <3 seconds for 10,000 parcels (use vector tiles or clustering)
- Chart rendering: <1 second for time-series (pre-aggregated data)
- Database queries: <500 ms for dashboard metrics (use indexed queries)

---

### 9.3 Data Requirements (See Section 10)

---

### 9.4 Scalability

**TR-IRR-07: Horizontal Scalability**
**Priority:** Should Have
**Description:** System scales to larger regions (e.g., 100,000 parcels) without redesign.

**Specifications:**
- Database sharding: Partition by parcel_id or spatial region
- Stateless services: All microservices horizontally scalable
- Load balancing: Distribute requests across service replicas
- Caching: Redis for frequently accessed data (crop parameters, recent classifications)

---

### 9.5 Security & Privacy

**TR-IRR-08: Data Anonymization**
**Priority:** Must Have
**Description:** Parcel ownership data anonymized to protect farmer privacy.

**Specifications:**
- Parcel owners replaced with hashed IDs
- No personally identifiable information (PII) stored
- GDPR compliance: Data minimization, right to be forgotten
- Access control: Role-based (water authority sees aggregates, farmers see own parcels)

---

**TR-IRR-09: Secure Data Transmission**
**Priority:** Must Have
**Description:** All data transmission encrypted (TLS 1.3).

**Specifications:**
- HTTPS for web UI and APIs
- Database connections encrypted (TLS/SSL)
- No sensitive data in logs (sanitize parcel IDs)

---

## 10. Data Requirements

### 10.1 Earth Observation Data

**DR-IRR-01: Sentinel-2 Level-2A Imagery**
**Source:** Copernicus Open Access Hub
**Frequency:** 5-day revisit (for single satellite), 2–3 days (combined S2A+S2B)
**Resolution:** 10m (visible/NIR bands: B2, B3, B4, B8)
**Bands Required:**
- B3 (Green, 560 nm) for NDWI
- B4 (Red, 665 nm) for NDVI
- B8 (NIR, 842 nm) for NDVI/NDWI
- SCL (Scene Classification Layer) for cloud masking

**Coverage:** Thessaloniki–Pella–Imathia plain (tiles T34TFK, T34TFL, T35TLF)
**Historical Archive:** 2017–present (for validation), 2020–2024 (for demo simulation)
**Format:** GeoTIFF or JPEG2000, cloud-optimized preferred
**Volume:** ~50 GB/year for region (uncompressed), ~10 GB compressed

---

### 10.2 GIS Data

**DR-IRR-02: Parcel Boundaries**
**Source:** Greek cadastre (ΚΤΗΜΑΤΟΛΟΓΙΟ) or digitized from orthophotos
**Geometry:** Polygons (multipolygons for split parcels)
**Attributes:** parcel_id, area_ha, owner_id (anonymized), land_use_type
**Format:** Shapefile or GeoJSON
**CRS:** EPSG:2100 (Greek Grid) or EPSG:4326 (WGS84)
**Coverage:** ~10,000–20,000 parcels in study area
**Update Frequency:** Annually (cadastre updates)

---

**DR-IRR-03: Soil Data**
**Source:** Hellenic Agricultural Organization (ELGO-DIMITRA), FAO Harmonized World Soil Database
**Attributes per soil type:**
- Texture (sand/silt/clay %)
- Organic matter (%)
- Field capacity (mm/m)
- Wilting point (mm/m)
- Saturated hydraulic conductivity (mm/day)

**Format:** Raster (GeoTIFF, 250m resolution) or vector (soil map units)
**Use:** AquaCrop soil profile initialization

---

**DR-IRR-04: Irrigation Infrastructure**
**Source:** Water management authority (e.g., Hellenic Ministry of Rural Development)
**Features:**
- Canal networks (polylines with capacity attributes)
- Pump stations (points with flow rate)
- Reservoirs (polygons with storage capacity)

**Format:** Shapefile
**Use:** Cooperative service area delineation, capacity constraints

---

### 10.3 Climate Data

**DR-IRR-05: Historical Climate Data**
**Source:** National Observatory of Athens, ERA5 reanalysis
**Variables:**
- Daily minimum/maximum temperature (°C)
- Daily precipitation (mm)
- Solar radiation (MJ/m²/day)
- Reference evapotranspiration ET₀ (mm/day, FAO Penman-Monteith)
- (Optional) Wind speed, humidity

**Spatial Resolution:** 10 km grid or station interpolation
**Temporal Coverage:** 2000–2024 (for calibration), 2020–2024 (for demo)
**Format:** NetCDF or CSV (per grid cell or parcel centroid)
**Volume:** ~500 MB for 25 years

---

**DR-IRR-06: Future Climate Projections**
**Source:** CMIP6 downscaled projections (e.g., CORDEX for Europe)
**Scenarios:** RCP 4.5, RCP 8.5 (or SSP2-4.5, SSP5-8.5)
**Variables:** Same as historical (temperature, precipitation, ET₀)
**Temporal Coverage:** 2025–2050
**Use:** Long-term scenario testing (Phase 2)

---

### 10.4 Crop Data

**DR-IRR-07: AquaCrop Crop Files**
**Source:** FAO AquaCrop database, calibrated for Greek conditions
**Crops:** Winter wheat, maize, cotton, rice
**Files:** .CRO (crop parameters), .MAN (irrigation management)
**Calibration:** Validate against regional yield statistics (Hellenic Statistical Authority)
**Updates:** Re-calibrate if regional data available (every 2–3 years)

---

**DR-IRR-08: Crop Statistics (Validation)**
**Source:** Hellenic Statistical Authority (ELSTAT), EU Crop Monitoring Service
**Data:**
- Annual crop area (ha) per crop per region
- Average yields (kg/ha)
- Irrigation water use estimates (if available)

**Use:** Validate simulation outputs (crop distribution, yields, irrigation)

---

### 10.5 Data Quality Requirements

**DQR-IRR-01: EO Data Completeness**
- Target: <20% cloud cover for classification windows (Jul–Aug, Jan–Feb)
- If >20% cloudy, use adjacent images or flag uncertainty
- Minimum 3 clear images per classification window

**DQR-IRR-02: GIS Accuracy**
- Parcel boundary positional accuracy: ±10 m (acceptable for 10m Sentinel-2 resolution)
- Topology: No gaps or overlaps between parcels

**DQR-IRR-03: Climate Data Validation**
- Cross-check station data with ERA5 (R² > 0.9 for temperature, >0.7 for precipitation)
- Fill missing data with interpolation or long-term averages (flag as estimated)

---

## 11. Success Metrics & KPIs

### 11.1 EO Classification Accuracy

**KPI-IRR-01: Bare Soil Detection Accuracy**
**Definition:** Percentage of parcels correctly classified as bare vs vegetated
**Target:** >90% overall accuracy
**Measurement:** Confusion matrix vs ground truth (field surveys or high-res imagery)
**Validation:** Sample 500 parcels, classify independently, compare

---

**KPI-IRR-02: Rice Flood Detection Precision/Recall**
**Definition:**
- Precision: True flooded / (True flooded + False flooded)
- Recall: True flooded / (True flooded + Missed flooded)

**Target:** >85% precision, >85% recall
**Measurement:** Compare NDWI-detected flooding to:
- High-resolution imagery (e.g., PlanetScope 3m) showing standing water
- Farmer reports (if available)

**Validation:** 200 rice parcels, visual inspection of imagery

---

### 11.2 Simulation Performance

**KPI-IRR-03: Irrigation Demand Forecast Accuracy**
**Definition:** Mean Absolute Error (MAE) between simulated and observed irrigation
**Target:** MAE <5% of total annual irrigation
**Measurement:** Compare 5-year simulated total vs historical records (if available)
**Example:** If historical total = 150 Mm³, simulated should be 142.5–157.5 Mm³

**Validation:** Use 2015–2019 as calibration, 2020–2024 as validation period

---

**KPI-IRR-04: Crop Distribution Agreement**
**Definition:** Agreement between simulated and observed crop areas
**Target:** MAE <10% per crop
**Measurement:** Compare simulated annual crop area (ha) to ELSTAT statistics
**Example:** If ELSTAT reports 12,000 ha rice, simulation should show 10,800–13,200 ha

---

**KPI-IRR-05: Simulation Runtime**
**Definition:** Wall-clock time to complete 5-year simulation
**Target:** <2 hours for 10,000 parcels on standard HPC node (32 cores)
**Measurement:** Time from initialization to final output generation

---

### 11.3 User Adoption & Satisfaction

**KPI-IRR-06: User Engagement**
**Definition:** Number of simulations run per month by water authority users
**Target:** ≥10 simulations/month within 6 months of deployment
**Measurement:** Usage analytics (log all simulation runs)

---

**KPI-IRR-07: User Satisfaction Score**
**Definition:** Average rating from user surveys (1–5 scale)
**Target:** ≥4.0/5.0
**Measurement:** Quarterly survey of water authority, policymaker, researcher users
**Questions:** Ease of use, accuracy of outputs, usefulness for decision-making

---

**KPI-IRR-08: Policy Impact**
**Definition:** Number of policy decisions informed by simulation outputs
**Target:** ≥3 policy adjustments within first year (e.g., rice area limits, drought allocations)
**Measurement:** User interviews, case study documentation

---

### 11.4 System Reliability

**KPI-IRR-09: System Uptime**
**Definition:** Percentage of time system is operational
**Target:** 99% uptime (excluding planned maintenance)
**Measurement:** Automated monitoring (Prometheus + Grafana)

---

**KPI-IRR-10: Data Freshness**
**Definition:** Lag between Sentinel-2 image availability and classification output
**Target:** <7 days (weekly update cycle)
**Measurement:** Timestamp difference (image date vs classification completion)

---

## 12. Validation Strategy

### 12.1 EO Classification Validation

**Method 1: Ground Truth Sampling**
- **Sample size:** 500 parcels (250 bare, 250 vegetated) per season
- **Selection:** Stratified random (cover different crop types, regions)
- **Ground truth:** Field surveys (if budget allows) or high-resolution imagery (PlanetScope 3m, Google Earth)
- **Metrics:** Confusion matrix, accuracy, precision, recall, F1-score
- **Threshold:** Overall accuracy >90%, kappa >0.8

**Method 2: Time-Series Consistency**
- Check temporal logic: A parcel classified "bare in summer" should have low NDVI all summer
- Flag inconsistencies (e.g., NDVI jumps mid-season but still classified bare)

**Method 3: Expert Review**
- Water authority staff review classification maps for obvious errors
- Iterative refinement of NDVI thresholds based on local knowledge

---

### 12.2 Rice Flood Detection Validation

**Method 1: High-Resolution Imagery**
- Acquire Planet or Sentinel-2 RGB composites for May (rice flooding start)
- Visually inspect 200 rice parcels: confirm standing water visible
- Compare to NDWI-detected flooding flags
- Metrics: Precision, recall (target >85%)

**Method 2: Water Authority Records**
- If available: Canal release schedules, flood irrigation dates
- Cross-reference NDWI flooding dates with canal operations
- Expect temporal correlation (flooding starts 1–3 days after canal release)

**Method 3: Synthetic Aperture Radar (SAR)**
- Use Sentinel-1 C-band SAR (not affected by clouds)
- Flooded paddies show low backscatter (smooth water surface)
- Confirm NDWI detections with SAR-based flood maps

---

### 12.3 AquaCrop Model Validation

**Method 1: Yield Validation**
- Compare simulated yields (kg/ha) to:
  - ELSTAT regional yield statistics
  - Farm surveys (if available)
- Metrics: R², RMSE, bias
- Threshold: R² >0.7, RMSE <15% of mean yield

**Method 2: Water Balance Validation**
- Compare simulated seasonal irrigation (mm or m³/ha) to:
  - Water authority allocation records
  - Literature values for Greece (e.g., rice: 1,200–1,500 mm/season)
- Check plausibility: Total 5-year irrigation aligns with regional water use reports

**Method 3: Sensitivity Analysis**
- Vary uncertain parameters (soil hydraulic conductivity, crop coefficients)
- Ensure outputs remain within realistic ranges (Monte Carlo or one-at-a-time)

---

### 12.4 Multi-Level ABM Validation

**Method 1: Pattern-Oriented Modeling**
- Identify emergent patterns in real data (e.g., "rice area decreases after drought years")
- Check if ABM reproduces same patterns (qualitative validation)

**Method 2: Stakeholder Workshops**
- Present simulation results to water authority, farmers, policymakers
- Discuss realism: "Does this match your experience?"
- Iteratively refine agent decision rules based on feedback

**Method 3: Historical Scenario Replay**
- Run simulation for historical period (e.g., 2018 drought)
- Compare simulated response (crop area changes, water shortages) to actual events
- Metrics: Qualitative agreement (yes/no), quantitative (if data available)

---

### 12.5 Integrated System Validation

**Method 1: End-to-End Test Case**
- Define test case: 2020–2024 simulation for 1,000-parcel subset
- Execute full pipeline: EO classification → Crop assignment → AquaCrop → ABM → Visualization
- Verify:
  - No errors/crashes
  - Outputs pass sanity checks (irrigation >0, yields realistic)
  - Runtime within targets

**Method 2: Comparison with Existing Tools**
- If available: Compare to static crop mapping + simple irrigation model
- Expected: Dynamic EO-based approach should have lower MAE for irrigation demand

**Method 3: User Acceptance Testing (UAT)**
- Water authority staff run 3 test scenarios (baseline, drought, policy change)
- Evaluate:
  - Ease of use (survey)
  - Output usefulness (can they make decisions based on results?)
  - Bug reports (track and fix)

---

## 13. Development Roadmap

### 13.1 Phase 1: Proof of Concept (Months 1–6)

**Objectives:**
- Demonstrate feasibility with small-scale prototype
- Validate EO classification and crop assignment logic
- Integrate AquaCrop for single-season test

**Key Deliverables:**
- **M1** (Month 2): EO classification module working (NDVI/NDWI computation, bare soil detection)
- **M2** (Month 3): Crop assignment rules implemented (summer-to-winter, winter-to-summer)
- **M3** (Month 4): AquaCrop wrapper functional (run single parcel, parse outputs)
- **M4** (Month 5): 1-year simulation for 100 parcels (end-to-end test)
- **M5** (Month 6): Proof-of-concept report with validation results

**Milestones:**
- ✅ EO data pipeline: Ingest Sentinel-2, compute indices, store time-series
- ✅ Bare soil classification accuracy >85% on test sample
- ✅ AquaCrop runs without errors, outputs plausible

---

### 13.2 Phase 2: Full System Development (Months 7–18)

**Objectives:**
- Scale to full region (10,000 parcels)
- Implement multi-level ABM (farmers, cooperatives, water authority)
- Develop web-based visualization dashboard
- Conduct comprehensive validation

**Key Deliverables:**
- **M6** (Month 9): Parallel AquaCrop execution (10,000 parcels in <2 hours)
- **M7** (Month 12): Multi-level ABM integrated (3 agent levels communicating)
- **M8** (Month 15): Web dashboard MVP (interactive maps, time-series charts)
- **M9** (Month 16): Rice flood detection (NDWI-based) validated (>85% precision/recall)
- **M10** (Month 18): Full 5-year simulation completed and validated

**Milestones:**
- ✅ System processes 10,000 parcels: EO classification → Crop assignment → AquaCrop
- ✅ Water cooperatives aggregate demand, water authority monitors sustainability
- ✅ Irrigation demand forecast MAE <5% vs historical data
- ✅ Dashboard deployed, accessible to test users

---

### 13.3 Phase 3: Operational Deployment (Months 19–24)

**Objectives:**
- Deploy to production environment (cloud)
- User training and adoption support
- Continuous monitoring and refinement
- Documentation and knowledge transfer

**Key Deliverables:**
- **M11** (Month 20): Production system deployed on cloud (AWS/Azure)
- **M12** (Month 21): User training workshops (water authority, policymakers)
- **M13** (Month 22): First operational simulations run by end users
- **M14** (Month 24): Final validation report, user guide, technical documentation

**Milestones:**
- ✅ System live at water authority (production use)
- ✅ ≥10 simulations/month usage rate
- ✅ User satisfaction score ≥4.0/5.0
- ✅ ≥3 policy decisions informed by system outputs

---

### 13.4 Phase 4: Enhancements & Scale-Up (Months 25+)

**Objectives:**
- Extend to neighboring regions (scale-up)
- Add advanced features (RL crop optimization, groundwater coupling)
- Long-term climate scenario integration

**Potential Deliverables:**
- Automated Sentinel-2 pipeline (Sentinel Hub API)
- Machine learning crop classification (replace rule-based with CNN/RF)
- Economic module (crop prices, profit optimization)
- Groundwater-surface water coupling (MODFLOW integration)
- Climate change scenarios (CMIP6 projections to 2050)
- Mobile app for farmers (water availability notifications)

---

### 13.5 Development Methodology

**Agile/Scrum:**
- 2-week sprints
- Daily standups, sprint planning, reviews, retrospectives
- Product backlog prioritized by MoSCoW (Must, Should, Could, Won't)

**Team Composition (Estimated):**
- 1 Product Owner (liaises with water authority)
- 1 Scrum Master
- 2 Backend Developers (Python: EO processing, AquaCrop wrapper, ABM)
- 1 Frontend Developer (React/Next.js dashboard)
- 1 DevOps Engineer (cloud deployment, CI/CD)
- 1 Data Scientist (EO validation, ML models for Phase 4)
- 1 Domain Expert (hydrologist/agronomist, part-time consulting)
- 1 QA Engineer (testing, validation)

**Tools:**
- Version control: Git (GitHub/GitLab)
- CI/CD: GitHub Actions or GitLab CI
- Project management: Jira or Trello
- Documentation: Markdown (in repo), Confluence or Notion

---

## 14. Risks & Mitigation

### 14.1 Technical Risks

**RISK-T-IRR-01: EO Data Quality (Cloud Cover)**
**Description:** Frequent cloud cover in classification windows (Jul–Aug, Jan–Feb) reduces usable imagery.
**Probability:** Medium (Mediterranean summers usually clear, but winters cloudy)
**Impact:** High (if <3 clear images, classification unreliable)
**Mitigation:**
- Use Sentinel-2A+2B combined (2–3 day revisit) to increase chances
- Extend classification window if needed (e.g., Jul–Sep instead of Jul–Aug)
- Fallback: Use previous season's classification + interpolation for missing parcels
- Validate with SAR (Sentinel-1) which penetrates clouds

**Contingency:**
- Flag low-confidence parcels (based on cloud cover), exclude from analysis or mark uncertainty
- For operational use: Combine optical + SAR for all-weather monitoring

---

**RISK-T-IRR-02: AquaCrop Calibration Challenges**
**Description:** AquaCrop parameters may not be well-calibrated for local conditions (soil, climate), leading to inaccurate irrigation estimates.
**Probability:** Medium
**Impact:** High (undermines forecast accuracy)
**Mitigation:**
- Allocate time for calibration: Compare simulated vs observed yields for 2–3 years
- Sensitivity analysis: Identify most influential parameters (soil hydraulic conductivity, crop coefficients)
- Use local trial data if available (experimental plots)
- Consult FAO AquaCrop database for Mediterranean crops

**Contingency:**
- Use ensemble of parameter sets (Monte Carlo) to quantify uncertainty
- If calibration fails: Fall back to simpler water balance model (e.g., FAO Crop Water Requirements)

---

**RISK-T-IRR-03: Computational Performance (Scalability)**
**Description:** Simulating 10,000 parcels × 5 years × 365 days may exceed computational budget or runtime targets.
**Probability:** Low (parallelization should handle it)
**Impact:** Medium (delays outputs, reduces operational usefulness)
**Mitigation:**
- Optimize AquaCrop runs: Pre-compute lookup tables for common scenarios
- Parallel processing: Use GNU Parallel or Dask for embarrassingly parallel parcel simulations
- Cloud burst: Auto-scale to 100+ cores during peak demand
- Profiling: Identify bottlenecks (e.g., I/O vs computation)

**Contingency:**
- Reduce simulation resolution: Group similar parcels (e.g., same soil+crop → single representative parcel)
- Use approximate methods (e.g., daily timestep → 10-day timestep for non-critical periods)

---

### 14.2 Data Risks

**RISK-D-IRR-01: Parcel Boundary Availability**
**Description:** Greek cadastre data may be incomplete or inaccessible for study area.
**Probability:** Medium (cadastre coverage incomplete in some regions)
**Impact:** High (can't run simulation without parcels)
**Mitigation:**
- Early engagement with cadastre authority (request data access Month 1)
- Backup: Digitize parcels from high-resolution imagery (time-consuming but feasible)
- Use LPIS (Land Parcel Identification System) from CAP if available

**Contingency:**
- Start with subset of region where cadastre is complete (proof-of-concept)
- Use coarser resolution (e.g., 100m grid cells instead of actual parcels)

---

**RISK-D-IRR-02: Historical Validation Data Scarcity**
**Description:** Lack of historical irrigation records or crop area statistics for validation.
**Probability:** Medium (water authority may not have detailed records)
**Impact:** Medium (reduces validation rigor, but system still operational)
**Mitigation:**
- Early stakeholder engagement: Request any available data (even partial)
- Use proxy data: EU Crop Monitoring reports, academic studies
- Invest in qualitative validation (expert workshops)

**Contingency:**
- Rely on literature values for plausibility checks (e.g., rice irrigation 1,200–1,500 mm/season)
- Validate indirectly: "Does simulated drought response match known 2018 drought impacts?"

---

### 14.3 User Adoption Risks

**RISK-UA-IRR-01: Low User Engagement**
**Description:** Water authority staff may not adopt tool due to complexity, lack of training, or preference for existing methods.
**Probability:** Medium
**Impact:** High (system unused, project impact limited)
**Mitigation:**
- User-centered design: Co-design UI with water authority staff (workshops, prototypes)
- Comprehensive training: Multi-day workshops, user manuals, video tutorials
- Champion identification: Find internal advocate at water authority
- Demonstrate value: Show how tool solves real problems (e.g., drought planning)
- Iterative feedback: Monthly check-ins, incorporate user requests

**Contingency:**
- Simplify UI: Hide advanced features, provide "wizard" workflows
- Provide decision support: Automated policy recommendations (reduce user effort)
- Hybrid approach: Tool provides inputs to existing decision processes (not full replacement)

---

**RISK-UA-IRR-02: Stakeholder Skepticism (Model Trust)**
**Description:** Policymakers may not trust model outputs, especially if they contradict intuition or existing practices.
**Probability:** Medium
**Impact:** Medium (limits policy impact)
**Mitigation:**
- Transparency: Explainable outputs (show why rice area decreased: low NDVI → no crop detected)
- Validation reporting: Clearly communicate accuracy metrics (>90% classification, <5% irrigation error)
- Sensitivity analysis: Show how results change with assumptions (build confidence)
- Case studies: Demonstrate successful use in other regions (if available)

**Contingency:**
- Use tool for scenario exploration (not prescriptive): "What if rice area limited to 15,000 ha?" (user decides)
- Incremental adoption: Start with low-stakes decisions, build trust over time

---

### 14.4 External Dependencies

**RISK-ED-IRR-01: Copernicus Sentinel-2 Data Continuity**
**Description:** Sentinel-2 mission could end or experience data gaps (satellite failure).
**Probability:** Low (Sentinel-2C scheduled for launch 2024, continuity planned)
**Impact:** High (system depends on Sentinel-2)
**Mitigation:**
- Monitor Copernicus announcements
- Plan for Sentinel-2 Next Generation (2030s)
- Backup: Landsat 8/9 (16-day revisit, coarser resolution but similar bands)

**Contingency:**
- Adapt to Landsat if Sentinel-2 unavailable (update NDVI/NDWI processing)
- Use commercial providers (Planet, Maxar) if budget allows

---

**RISK-ED-IRR-02: AquaCrop Software Maintenance**
**Description:** FAO AquaCrop may become unmaintained or incompatible with future OS.
**Probability:** Low (actively maintained as of 2024)
**Impact:** Medium (would require model replacement)
**Mitigation:**
- Use AquaCrop-OSPy (Python open-source implementation) for long-term flexibility
- Monitor FAO updates, contribute to open-source community
- Modular design: Easy to swap crop model (AquaCrop → DSSAT, APSIM)

**Contingency:**
- Implement simple FAO-56 crop water model as fallback (less accurate but robust)

---

## 15. Glossary

**AquaCrop**: FAO crop-water productivity model simulating yield response to water (Smith & Steduto, 2009).

**Agent-Based Model (ABM)**: Computational model simulating autonomous agents (farmers, cooperatives) and their interactions.

**Bare Soil**: Land with no vegetation cover (NDVI < threshold), indicating fallow or harvested field.

**CMIP6**: Coupled Model Intercomparison Project Phase 6, providing future climate scenarios.

**CORDEX**: Coordinated Regional Climate Downscaling Experiment, providing regional climate projections for Europe.

**Evapotranspiration (ET)**: Combined water loss from soil evaporation and plant transpiration (mm/day).

**NDVI (Normalized Difference Vegetation Index)**: (NIR - Red) / (NIR + Red), indicating vegetation greenness (-1 to 1).

**NDWI (Normalized Difference Water Index)**: (Green - NIR) / (Green + NIR), indicating surface water presence (-1 to 1).

**Phenology**: Study of periodic plant life cycle events (e.g., sowing, peak greenness, harvest).

**RCP (Representative Concentration Pathway)**: Climate scenarios (RCP 2.6, 4.5, 6.0, 8.5) representing different greenhouse gas trajectories.

**Sentinel-2**: EU Copernicus optical satellite constellation for land monitoring (10m resolution, 5-day revisit).

**Zonal Statistics**: Aggregating raster values (e.g., NDVI) within vector zones (e.g., parcels).

---

## Appendices

### Appendix A: Crop Rotation Rules (Detailed)

**Summer-to-Winter Rule:**
```
IF (parcel.status == "BARE_SUMMER"):
    parcel.next_crop = "WINTER_WHEAT"
    parcel.sowing_date = "October 15" (configurable)
    parcel.irrigation_regime = "RAINFED" (minimal irrigation)
```

**Winter-to-Summer Rule:**
```
IF (parcel.status == "BARE_WINTER"):
    probabilities = {MAIZE: 0.4, COTTON: 0.4, RICE: 0.2}  # configurable
    parcel.next_crop = random_choice(probabilities)
    IF parcel.next_crop == "RICE":
        parcel.monitor_ndwi = TRUE  # flag for flood detection
    ELSE:
        parcel.monitor_ndwi = FALSE
    parcel.sowing_date = "April 15" (rice: "April 25")
```

---

### Appendix B: NDWI Flood Detection Algorithm

**Pseudocode:**
```python
for parcel in rice_parcels:
    ndwi_time_series = get_ndwi(parcel, start="May 1", end="June 30")

    # Method 1: Single-date threshold
    if any(ndwi > 0.2 for ndwi in ndwi_time_series):
        parcel.isFlooded = True

    # Method 2: Sustained flooding (alternative)
    sustained_days = count_consecutive_days(ndwi_time_series > 0)
    if sustained_days >= 7:
        parcel.isFlooded = True
    else:
        parcel.isFlooded = False

    # Set AquaCrop regime
    if parcel.isFlooded:
        parcel.aquacrop_config = "rice_flooded.CRO"
    else:
        # Check if alternate crop grew (NDVI rises in June)
        june_ndvi = get_ndvi(parcel, "June 15")
        if june_ndvi > 0.4:
            parcel.crop = "MAIZE_LATE_PLANTED"
            parcel.aquacrop_config = "maize.CRO"
        else:
            parcel.crop = "FALLOW"
            parcel.aquacrop_config = None  # no simulation
```

---

### Appendix C: AquaCrop Water Balance Validation

**Closure Check:**
```
For each parcel, each day:
    Inputs = Irrigation + Precipitation
    Outputs = ET_actual + Deep_Percolation + Runoff
    Delta_Storage = Soil_Moisture[day] - Soil_Moisture[day-1]

    Water_Balance_Error = (Inputs - Outputs - Delta_Storage) / Inputs

    IF abs(Water_Balance_Error) > 0.01:
        LOG WARNING: "Parcel {id}, Day {date}: Water balance error {error}%"

Seasonal Check:
    Total_Inputs = sum(Irrigation + Precip)
    Total_Outputs = sum(ET + Percolation + Runoff)
    Final_Storage - Initial_Storage = Delta

    Seasonal_Error = (Total_Inputs - Total_Outputs - Delta) / Total_Inputs

    ASSERT Seasonal_Error < 0.01  # <1% error acceptable
```

---

### Appendix D: Multi-Level ABM Communication Flow

**Upward Flow (Aggregation):**
```
1. Farmer Agents → Water Cooperative:
   Each farmer agent reports: irrigation_demand_m3
   Cooperative sums: total_demand = sum(farmer.irrigation_demand)

2. Water Cooperative → Water Authority:
   Cooperative submits request: {cooperative_id, total_demand_m3, season}
   Authority aggregates: regional_demand = sum(cooperative.total_demand)

3. Water Authority Analysis:
   IF regional_demand > sustainable_limit:
       authority.alert = "DEMAND_EXCEEDS_SUSTAINABILITY"
   IF rice_area > target_area:
       authority.alert = "RICE_AREA_EXCEEDS_CAP"
```

**Downward Flow (Policy/Allocation):**
```
1. Water Authority → Water Cooperative:
   Authority allocates: {cooperative_id, allocated_m3, allocation_ratio}
   IF allocation_ratio < 1.0:
       cooperative.water_shortage = TRUE

2. Water Cooperative → Farmer Agents:
   Cooperative broadcasts: "Allocation at {ratio*100}% of request"
   Farmers adjust (future RL): reduce crop area or switch to less water-intensive crops
```

---

### Appendix E: Example Simulation Workflow (1 Year)

**Year 1 Winter (Nov–Feb):**
1. Load Year 0 classification: 8,000 parcels with winter wheat, 2,000 bare
2. Run AquaCrop for wheat parcels (rainfed, minimal irrigation)
3. End of winter: EO classification → identify 1,500 parcels bare in winter
4. Crop assignment: Randomly assign 600 maize, 600 cotton, 300 rice

**Year 1 Summer (Mar–Sep):**
1. AquaCrop initialization:
   - 8,000 wheat harvested, soil moisture carried over
   - 600 maize sowing April 15, 600 cotton sowing April 15, 300 rice sowing April 25
   - 2,000 bare parcels (no crop, fallow)
2. May: NDWI monitoring for 300 rice parcels → 250 confirmed flooded, 50 not flooded
   - 250 flooded: Use rice_flooded.CRO (continuous ponding)
   - 50 not flooded: Check June NDVI → 30 show late maize (reassign), 20 stay fallow
3. Run AquaCrop for all crops (May–Sep):
   - 600 maize: Deficit irrigation, total 400 mm
   - 600 cotton: Deficit irrigation, total 350 mm
   - 250 rice (flooded): 1,200 mm irrigation
   - 30 maize (late): 300 mm irrigation
4. End of summer: EO classification → 1,800 parcels bare in summer
5. Crop assignment: All 1,800 → winter wheat for Year 2 winter

**Year 1 Outputs:**
- Total irrigation: 600×400 + 600×350 + 250×1,200 + 30×300 = 759,000 m³ (simplified, actual per-parcel)
- Crop distribution: Wheat 8,000 ha (winter), Maize 630 ha (summer), Cotton 600 ha, Rice 250 ha
- Water authority alert: None (demand within limits)

**Repeat for Years 2–5...**

---

**End of PRD for EO-Informed Irrigation Use Case**

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | October 2025 | TRANSITION Team | Initial PRD creation for irrigation use case |

---

**For questions or feedback, contact:** TRANSITION Project Team
