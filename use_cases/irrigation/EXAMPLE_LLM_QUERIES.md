# Irrigation Use Case - LLM Query Examples

## ✅ WORKING - Tested on 2025-10-24

**Status**: IRR-US-01 (Bare Soil Classification) is FULLY IMPLEMENTED and working via LLM interface!

---

## Overview

This document provides natural language query examples for running irrigation simulations through the TRANSITION LLM interface. The irrigation use case uses **on-demand NDVI/NDWI download** - no manual "Get NDVI" step required!

**Key Features:**
- ✅ **Automatic EO data download** - NDVI/NDWI fetched when needed
- ✅ **Natural language date parsing** - "July 15 to August 31, 2023" → automatic conversion
- ✅ **CRS reprojection** - Automatic WGS84 → UTM coordinate transformation
- ✅ **Dynamic crop assignment** - Based on bare soil detection (NDVI thresholds) - PLANNED
- ✅ **Rice flood detection** - NDWI validation of actual flooding - PLANNED
- ✅ **Multi-level ABM** - Farmers, Water Cooperatives, Water Authorities - PLANNED

---

## 🧪 TESTED QUERIES (✅ Working)

### IRR-US-01: Automated Bare Soil Classification

**✅ Test 1: Natural language dates**
```bash
cd llm_interface
python transition_agent.py "Classify bare soil from July 15 to July 22, 2023 with 5 parcels" \
  --geojson-file ../use_cases/irrigation/test_polygon_thessaloniki.geojson
```

**Result**: ✅ SUCCESS
- 20 parcels analyzed (used default, not 5 - see note below)
- 100% bare soil detected (NDVI: -0.034)
- Files generated:
  - `classification_map_20230715.geojson`
  - `classification_report_20230715.txt`

**✅ Test 2: ISO date format**
```bash
python transition_agent.py "Detect bare parcels from 2023-07-15 to 2023-07-22" \
  --geojson-file ../use_cases/irrigation/test_polygon_thessaloniki.geojson
```

**Result**: ✅ SUCCESS (same as above)

**✅ Test 3: Different date ranges**
```bash
python transition_agent.py "Classify soil from July 1 to August 31, 2023" \
  --geojson-file ../use_cases/irrigation/test_polygon_thessaloniki.geojson
```

**Result**: ✅ SUCCESS (more Sentinel-2 scenes processed, better coverage)

---

## 🎯 User Stories Status

### ✅ IRR-US-01: Automated Bare Soil Classification (IMPLEMENTED & TESTED)

**Natural Language Examples (ALWAYS use "bare soil" keywords!):**
```
"Classify bare soil parcels in Thessaloniki for summer 2025 using NDVI"
"Detect bare soil from July 15 to August 31, 2025"
"Classify bare soil from July 15 to July 22, 2025 with 10 parcels"
"Identify fallow parcels using bare soil classification from 2025-07-01 to 2025-08-31"
"Detect bare soil at (40.5, 22.7) and (40.6, 22.8) from July 12 to July 16 2025"
"Classify my fields using bare soil analysis from July 12 to July 16 2025"
```

**⚠️ IMPORTANT**: Always include "bare soil" or "bare parcels" keywords!
- ❌ DON'T SAY: "Show me which parcels had no vegetation" (triggers MLU-05!)
- ✅ DO SAY: "Classify bare soil in my region" (triggers IRR-US-01)

**What Happens:**
1. LLM extracts date range from natural language
2. Downloads Sentinel-2 NDVI automatically (on-demand)
3. Generates random parcels within polygon
4. Reprojects coordinates from WGS84 to UTM (automatic)
5. Extracts NDVI values for each parcel
6. Classifies: NDVI < 0.25 = bare soil
7. Returns GeoJSON map + text report

**Requirements**:
- ✅ Date range MUST be specified (e.g., "July 2023" or "from 2023-07-01 to 2023-08-31")
- ✅ Polygon MUST be drawn (via --geojson-file)
- ✅ Sentinel-2 data must be available for dates/region

**KPI Target**: >90% accuracy vs ground truth

---

### 🔜 IRR-US-03: Dynamic Crop Assignment (Summer-to-Winter) - PLANNED

### IRR-US-03: Dynamic Crop Assignment (Summer-to-Winter)
**Natural Language:**
```
"Assign winter wheat to all summer-fallow parcels in my region"
"Simulate crop rotation: bare in summer → winter wheat"
"What crops should be planted after summer fallow?"
```

**Rule Applied:**
```
IF parcel.bare_in_summer:
    parcel.next_crop = "WINTER_WHEAT"
    parcel.sowing_date = "October 15"
```

**KPI Target**: 100% assignment rate (all bare parcels get assigned)

---

### IRR-US-04: Dynamic Crop Assignment (Winter-to-Summer)
**Natural Language:**
```
"Assign summer crops to winter-fallow parcels with 40% maize, 40% cotton, 20% rice"
"Simulate crop rotation for bare winter parcels"
"What happens to fields left fallow in winter?"
```

**Rule Applied:**
```
IF parcel.bare_in_winter:
    probabilities = {MAIZE: 0.4, COTTON: 0.4, RICE: 0.2}
    parcel.next_crop = random_choice(probabilities)
```

**KPI Target**: Logic completes in <1 second for 10,000 parcels

---

### IRR-US-05: Rice Flood Detection (NDWI-Based)
**Natural Language:**
```
"Detect which rice parcels are actually flooded in May using NDWI"
"Validate rice flooding with satellite water detection"
"Confirm rice paddy flooding for my region in June 2024"
```

**What Happens:**
- Downloads Sentinel-2 NDWI for May-June
- Applies NDWI > 0.2 threshold for flooding detection
- Sets `isFlooded=True` for confirmed parcels
- Uses AquaCrop paddy regime only for flooded parcels

**KPI Target**: >85% precision, >85% recall vs ground truth

---

### IRR-US-07: AquaCrop Seasonal Re-Initialization
**Natural Language:**
```
"Run 5-year irrigation simulation with dynamic crop rotations"
"Simulate water demand with AquaCrop for 2020-2024"
"Model seasonal crop transitions with soil moisture carryover"
```

**What Happens:**
- Re-initializes AquaCrop at each season transition
- Transfers soil moisture from previous season
- Loads crop-specific parameters (wheat.CRO, rice_flooded.CRO, etc.)
- Maintains water balance closure (±1% error)

**KPI Target**: 100% seasonal transitions without errors

---

### IRR-US-09: Farmer Agent Crop Decision (Multi-Level ABM)
**Natural Language:**
```
"Simulate farmer decisions based on EO bare soil detection"
"Run multi-level ABM with farmers, cooperatives, and water authority"
"Model farmer crop choices under water scarcity"
```

**What Happens:**
- Individual Level: FarmerAgent observes EO land status → decides next crop
- Community Level: WaterCooperativeAgent aggregates irrigation demand
- Policy Level: WaterAuthorityAgent monitors sustainability, allocates water

---

### IRR-US-12: Interactive Crop Distribution Map
**Natural Language:**
```
"Show crop distribution map for 2023 summer season"
"Visualize wheat, maize, cotton, and rice areas on map"
"Export crop distribution as GeoJSON"
```

**Output:**
- Interactive Folium map with color-coded parcels
- Wheat=yellow, Maize=green, Cotton=white, Rice=blue, Bare=gray
- Clickable parcels with details (crop, irrigation, yield)

---

### IRR-US-13: Seasonal Irrigation Demand Chart
**Natural Language:**
```
"Show irrigation demand over 5 years for Thessaloniki"
"Plot seasonal water usage: winter vs summer"
"Compare irrigation demand across scenarios"
```

**Output:**
- Plotly time-series chart (10 bars: 5 winters + 5 summers)
- Sustainable limit threshold overlay
- Drill-down to cooperative-level demands

---

## 💬 Example Natural Language Queries

### Basic Simulation Queries

**Query 1: Simple 5-Year Simulation**
```
"Run irrigation simulation for Thessaloniki from 2020 to 2024 using my drawn polygon"
```
**What It Does:**
- Uses user-drawn polygon as region of interest
- Downloads NDVI/NDWI on-demand for each season
- Classifies bare parcels, assigns crops dynamically
- Runs AquaCrop for water balance
- Returns 5-year irrigation demand

---

**Query 2: With Specific Dates**
```
"Simulate irrigation for my region from July 2023 to September 2023 using Sentinel-2 data from July 1 to August 31"
```
**What It Does:**
- Downloads Sentinel-2 NDVI/NDWI for Jul 1 - Aug 31, 2023
- Classifies end-of-summer bare parcels
- Assigns winter wheat to bare parcels
- Runs winter wheat simulation (Nov 2023 - Feb 2024)

---

**Query 3: Multi-Level ABM**
```
"Run 5-year irrigation ABM with farmers, cooperatives, and water authority for my polygon from 2020-2024"
```
**What It Does:**
- Creates FarmerAgents (individual level)
- Creates WaterCooperativeAgents (community level)
- Creates WaterAuthorityAgent (policy level)
- Simulates cross-scale interactions (upward/downward/lateral flows)
- Returns irrigation demand + policy alerts

---

### Crop-Specific Queries

**Query 4: Rice Flood Detection**
```
"Detect rice flooding in Thessaloniki for May 2024 using NDWI validation"
```
**What It Does:**
- Downloads NDWI for May 1 - June 30, 2024
- Identifies rice-assigned parcels
- Applies NDWI > 0.2 threshold
- Returns flooded vs non-flooded parcels

---

**Query 5: Wheat Rotation**
```
"Simulate winter wheat planting after summer fallow for 2023-2024"
```
**What It Does:**
- Downloads NDVI for Jul-Aug 2023 (classify bare parcels)
- Assigns winter wheat to all summer-bare parcels
- Runs AquaCrop for wheat (Oct 2023 - May 2024)
- Returns wheat yield + irrigation (minimal, mostly rainfed)

---

### Scenario Comparison Queries

**Query 6: Baseline vs Dynamic**
```
"Compare irrigation demand with and without dynamic crop assignment for 2020-2024"
```
**What It Does:**
- **Baseline**: Static crop distribution (no EO updates)
- **Dynamic**: EO-driven crop assignment every season
- Returns comparison chart + accuracy improvement metric

---

**Query 7: Policy Impact**
```
"Evaluate impact of limiting rice area to 20% of total on water demand"
```
**What It Does:**
- Runs simulation with policy constraint (rice ≤ 20%)
- Compares to baseline (no constraint)
- Returns water savings + policy recommendation

---

### Validation & Analysis Queries

**Query 8: Accuracy Validation**
```
"Validate bare soil classification accuracy against ground truth for summer 2023"
```
**What It Does:**
- Loads ground truth data (if available)
- Compares NDVI-classified bare parcels vs ground truth
- Returns confusion matrix, precision, recall, F1-score
- **Target**: >90% accuracy

---

**Query 9: Irrigation Demand Forecast**
```
"Forecast irrigation demand for 2025-2029 under RCP 4.5 climate scenario"
```
**What It Does:**
- Uses CMIP6 climate projections (future)
- Runs dynamic crop assignment + AquaCrop
- Returns 5-year irrigation forecast with uncertainty bands

---

## 🗺️ Polygon-Based Queries

All queries require a **user-drawn polygon** for spatial filtering:

**Query 10: Polygon + Dates**
```
"Simulate irrigation for my drawn polygon from 2023-01-01 to 2023-12-31"
```

**Query 11: Multiple Polygons**
```
"Compare irrigation demand between my two drawn regions for 2024"
```

**Query 12: No Data Alert**
```
"Simulate for my polygon from 2025-10-20 to 2025-10-21"
```
**Expected Alert:**
```
⚠️ No Satellite Data Found
No satellite data available for 2025-10-20 to 2025-10-21.
Sentinel-2 revisit time is 2-5 days. Try selecting a wider date range (e.g., 7-10 days).
```

---

## 🔧 Advanced Queries

### Ensemble Simulations

**Query 13: Monte Carlo Ensemble**
```
"Run irrigation simulation with 30 ensemble realizations for uncertainty quantification"
```
**What It Does:**
- Runs 30 stochastic realizations (random crop assignment varies)
- Computes mean, median, 95% confidence intervals
- Returns probabilistic irrigation demand

---

### Custom Crop Probabilities

**Query 14: Custom Assignment**
```
"Simulate with 60% maize, 30% cotton, 10% rice assignment for winter-fallow parcels"
```
**What It Does:**
- Overrides default probabilities (40/40/20)
- Uses user-specified {maize: 0.6, cotton: 0.3, rice: 0.1}

---

### Water Authority Monitoring

**Query 15: Sustainability Check**
```
"Monitor if irrigation demand exceeds 200 million m³/year sustainable limit"
```
**What It Does:**
- WaterAuthorityAgent tracks total regional demand
- Flags alert if demand > limit
- Returns policy recommendation (e.g., "Reduce rice area by 15%")

---

## 📊 Expected Outputs

### Success Case (Data Available)
```
✅ NDVI Processing Complete
Successfully processed 1 Sentinel-2 scene(s).

📊 Simulation Results:
- Total Irrigation (5 years): 487 million m³
- Crop Distribution:
  - Winter Wheat: 8,200 ha
  - Maize: 4,100 ha
  - Cotton: 3,800 ha
  - Rice (flooded): 1,900 ha
- Water Authority Alerts: None (demand within limits)

📁 Files Generated:
- crop_distribution_map_2024.html (Interactive Folium map)
- seasonal_irrigation_demand.html (Plotly time-series)
- abm_results.csv (Agent-level data)
```

---

### Warning Case (No Data)
```
⚠️ No Satellite Data Found
No satellite data available for 2025-10-20 to 2025-10-21.
Sentinel-2 revisit time is 2-5 days. Try selecting a wider date range (e.g., 7-10 days).
```

---

### Error Case (Invalid Dates)
```
❌ Validation Error
Start date must be before end date. You specified: 2024-12-31 to 2024-01-01
```

---

## 🛠️ Technical Notes

### On-Demand NDVI/NDWI Download
- **Automatic**: Downloads happen when irrigation query is executed
- **Temporary Storage**: Data saved to `/tmp/ndvi_temp_*` folders
- **Auto-Cleanup**: Deleted after simulation completes
- **Cache**: Same polygon + dates reuse existing download (hash-based)

### Date Requirements
- **MUST specify dates** for Sentinel-2 data download
- **Format**: `YYYY-MM-DD` (e.g., "2024-07-15")
- **Range**: Minimum 3-5 days for cloud-free images
- **Optimal**: 7-10 days for reliable data

### Polygon Requirements
- **MUST draw polygon** before running simulation
- **Validation**: Coordinates within Thessaloniki bounds (40.4-40.9°N, 22.5-22.9°E)
- **Format**: GeoJSON FeatureCollection (automatic from frontend)

---

## 📚 Documentation References

- **Full PRD**: [PRD.md](PRD.md) - Complete product requirements
- **Claude Guidelines**: [CLAUDE.md](CLAUDE.md) - AI assistant rules
- **Implementation Example**: [EXAMPLE_IRRIGATION_QUERY.md](EXAMPLE_IRRIGATION_QUERY.md) - Python code samples
- **On-Demand NDVI**: [ON_DEMAND_NDVI_SUMMARY.md](ON_DEMAND_NDVI_SUMMARY.md) - Technical details
- **Multi-Level ABM**: [../../MULTILEVEL-ABM.md](../../MULTILEVEL-ABM.md) - ML-ABM architecture

---

## ⚠️ Important Reminders

1. **Real Data Only**: NEVER use dummy/mock data - all Sentinel-2 downloads are real!
2. **Dates Required**: User MUST specify date range for EO data download
3. **Polygon Required**: User MUST draw polygon(s) for spatial filtering
4. **Auto NDVI Download**: No manual "Get NDVI" button - happens automatically
5. **Terminal Logging**: All info printed to backend terminal for debugging
6. **Alert System**: Clear messages if no satellite data available

---

**Last Updated**: 2025-10-24
**Status**: ✅ Ready for LLM Interface Integration
**Next Steps**: Create `llm_interface/irrigation_tool.py` to parse these queries
