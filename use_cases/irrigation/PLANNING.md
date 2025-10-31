# PLANNING.md - EO-Informed Irrigation Use Case
## Technical Planning & Implementation Roadmap

**Version:** 1.1
**Last Updated:** October 2025
**Use Case:** EO-Informed Irrigation Simulation (Multi-Regional Agricultural Water Management)
**Status:** Planned (Phase 2)
**Parent Project:** TRANSITION Platform

---

## 📋 Table of Contents

1. [Use Case Vision](#use-case-vision)
2. [Technical Architecture](#technical-architecture)
3. [Technology Stack](#technology-stack)
4. [Module Breakdown](#module-breakdown)
5. [Data Architecture](#data-architecture)
6. [Real Data Sources](#real-data-sources)
7. [Development Phases](#development-phases)
8. [Infrastructure & Deployment](#infrastructure--deployment)
9. [Team & Resources](#team--resources)
10. [Success Metrics](#success-metrics)

---

## 🎯 Use Case Vision

### Overview
The EO-Informed Irrigation Simulation use case implements a **dynamic, satellite-driven crop rotation and irrigation management system** for irrigated agricultural regions. This system integrates **real-time Sentinel-2 NDVI/NDWI observations** with **multi-level agent-based modeling** and **AquaCrop crop water simulations** to provide accurate irrigation demand forecasts over 5-year horizons.

### Mission
To transform irrigation water management from static crop mapping to **adaptive, EO-validated simulations** that reflect real-world land-use changes, crop flooding patterns, and climate variability, enabling water authorities, farmers, and policymakers to make evidence-based decisions for sustainable water use.

### Core Principles (Developer-Focused User Stories)
1. **Automated EO Classification (IRR-US-01)**: Sentinel-2 NDVI/NDWI classification with time-series phenology analysis (>90% accuracy KPI)
2. **Dynamic Crop Assignment (IRR-US-02)**: Deterministic summer-to-winter & stochastic winter-to-summer rotation rules (100% assignment, reproducible)
3. **Rice Flood Detection (IRR-US-03)**: NDWI-based flooding validation (>85% precision/recall KPI)
4. **AquaCrop Integration (IRR-US-04)**: Seamless seasonal re-initialization with soil moisture carryover (100% success rate, <10% overhead)
5. **Impact Assessment (IRR-US-05)**: Dynamic EO-based system vs static baseline comparison (<5% MAE target)
6. **Modular Interfaces (IRR-US-06)**: Well-defined APIs, testability (>80% code coverage), maintainability
7. **Real Data Only**: 100% real EO data, climate projections, and soil/crop parameters - NO synthetic data

### Alignment with TRANSITION Platform
- **ML-ABM Core**: Follows TRANSITION's 4-level agent-based modeling architecture (Individual → Community → Market → Policy)
- **Real EO Data**: Consistent with platform's "NO dummy data" policy
- **Modular Design**: Standalone modules (EO classification, crop assignment, AquaCrop wrapper, ABM) following D2.3 architecture
- **Digital Twin**: Creates adaptive simulation mirroring real-world agricultural system
- **EU Green Deal**: Supports sustainable agricultural water use and Water Framework Directive compliance

### Target Users
1. **Water Management Authority Officers** - Seasonal irrigation demand forecasting, drought planning
2. **Farmers & Water Cooperatives** - Water availability insights, crop rotation recommendations
3. **Agricultural Policymakers** - Rice area monitoring, water allocation policy evaluation
4. **Environmental Scientists & Researchers** - Irrigation modeling validation, academic research

---

## 🏗️ Technical Architecture

### System Architecture Pattern
**Modular Microservices Architecture** integrated with TRANSITION platform

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Layer (Web UI)                      │
│         Next.js 15 + React 18 + Leaflet + Plotly                │
│  (Reuses TRANSITION frontend with irrigation-specific routes)   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway (FastAPI)                       │
│         /api/irrigation/classify (EO classification)            │
│         /api/irrigation/simulate (Run simulation)               │
│         /api/irrigation/results (Get outputs)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┴─────────────────────┐
         ↓                    ↓                     ↓
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  EO Processing   │ │  Simulation      │ │  Data            │
│  Service         │ │  Service         │ │  Service         │
│                  │ │                  │ │                  │
│ - NDVI/NDWI calc │ │ - Mesa ABM       │ │ - PostGIS        │
│ - Classification │ │ - AquaCrop wrap  │ │ - TimescaleDB    │
│ - Flood detect   │ │ - Crop assign    │ │ - S3/Blob        │
└──────────────────┘ └──────────────────┘ └──────────────────┘
         │                    │                     │
         └────────────────────┴─────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Data Layer                              │
│  PostgreSQL + PostGIS (parcels, agents, results)                │
│  TimescaleDB (EO time-series, climate data, daily water balance)│
│  S3/Blob Storage (Sentinel-2 imagery, AquaCrop outputs)         │
│  Redis (Caching, task queue)                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Components

**1. EO Processing Service (New)**
- **Purpose**: Sentinel-2 NDVI/NDWI computation, parcel classification, rice flood detection
- **Language**: Python 3.11+
- **Dependencies**: Rasterio, xarray, GeoPandas, NumPy
- **Inputs**: Sentinel-2 L2A imagery (GeoTIFF), parcel GIS layer (Shapefile/GeoJSON)
- **Outputs**: Classification map (parcel_id → "bare"/"vegetated"/"water"), flood detection results (parcel_id → isFlooded bool)
- **Performance**: Process 10,000 parcels in <2 hours (parallel raster processing with Dask)

**2. Crop Assignment Service (New)**
- **Purpose**: Apply seasonal rotation rules to assign crops to bare parcels
- **Language**: Python 3.11+
- **Logic**:
  - Summer-to-Winter: All bare-summer parcels → WINTER_WHEAT
  - Winter-to-Summer: Bare-winter parcels → random(MAIZE, COTTON, RICE) with configurable probabilities
- **Inputs**: EO classification results, current season, config (crop probabilities)
- **Outputs**: Crop assignment map (parcel_id → crop_type)
- **Performance**: 10,000 parcels assigned in <1 second (simple rule-based logic)

**3. AquaCrop Wrapper Service (New)**
- **Purpose**: Execute FAO AquaCrop crop water model for all parcels, manage seasonal re-initialization
- **Language**: Python 3.11+ (wrapper), AquaCrop executable (Fortran/compiled)
- **Parallelization**: GNU Parallel or Joblib for embarrassingly parallel parcel simulations
- **Inputs**: Crop plan, climate data (NetCDF), soil profiles, irrigation management
- **Outputs**: Seasonal irrigation (mm, converted to m³), crop yield, evapotranspiration, soil moisture
- **Performance**: 10,000 parcels × 120-day season in <1 hour (32-core server)

**4. Multi-Level ABM Service (Extends Existing)**
- **Purpose**: Simulate farmer agents, water cooperatives, and water authority interactions
- **Framework**: Mesa 3.3+ (reuses TRANSITION's ABM engine)
- **Agent Levels**:
  - **FarmerAgent** (Individual): Crop decisions based on EO observations
  - **WaterCooperativeAgent** (Community): Aggregate member demands, distribute allocations
  - **WaterAuthorityAgent** (Policy): Monitor sustainability, enforce regulations
- **Orchestration**: MultiLevelOrchestrator manages cross-scale interactions (upward: demand aggregation, downward: allocation distribution)
- **Integration**: Loads EO classification results, triggers crop assignment, receives AquaCrop outputs

**5. Visualization Service (Extends Existing)**
- **Purpose**: Generate interactive maps, time-series charts, policy dashboards
- **Technologies**: Plotly (charts), Folium (maps), Jinja2 (HTML templates)
- **Outputs**:
  - Crop distribution maps (annual snapshots)
  - Irrigation demand time-series (10 seasons over 5 years)
  - Rice flooding event maps (NDWI-validated)
  - Water authority allocation dashboard (cooperative-level)
- **Export**: PNG, PDF, HTML, CSV, GeoJSON

---

## 💻 Technology Stack

### Core Dependencies (Irrigation-Specific)

#### Earth Observation Processing
| Technology | Version | Purpose |
|------------|---------|---------|
| **GDAL/OGR** | 3.6+ | Geospatial data abstraction layer (REQUIRED) |
| **Rasterio** | 1.3+ | Sentinel-2 raster I/O and processing (REQUIRED) |
| **xarray** | 2023.12+ | N-dimensional arrays for NetCDF climate data (REQUIRED) |
| **rioxarray** | 0.15+ | Rasterio + xarray integration |
| **GeoPandas** | 0.14+ | Vector parcel data handling (REQUIRED) |
| **Shapely** | 2.0+ | Geometric operations (parcel boundaries) |
| **pyproj** | 3.6+ | Coordinate transformations (EPSG:2100 ↔ EPSG:4326) |
| **NumPy** | 1.24+ | Array computations (NDVI/NDWI calculations) |
| **Dask** | 2023.12+ | Parallel raster processing (10,000 parcels) |
| **zarr** | 2.16+ | Chunked array storage (EO time-series) |

#### Crop Water Modeling
| Technology | Version | Purpose |
|------------|---------|---------|
| **AquaCrop-OSPy** | 2.3+ | Python implementation of FAO AquaCrop (PREFERRED) |
| **AquaCrop (standalone)** | 7.0+ | Official executable (alternative, requires subprocess) |
| **pandas** | 2.1+ | AquaCrop output parsing |
| **joblib** | 1.3+ | Parallel AquaCrop execution |

#### Agent-Based Modeling (Inherits from TRANSITION)
| Technology | Version | Purpose |
|------------|---------|---------|
| **Mesa** | 3.3+ | Multi-agent simulation framework |
| **NetworkX** | 3.x | Agent network modeling (cooperatives) |

#### Climate Data
| Technology | Version | Purpose |
|------------|---------|---------|
| **netCDF4** | 1.6+ | NetCDF file I/O (ERA5, CMIP6) |
| **cftime** | 1.6+ | Climate-specific time handling |
| **cf-xarray** | 0.8+ | CF conventions for xarray |

#### EO Data Access
| Technology | Version | Purpose |
|------------|---------|---------|
| **sentinelsat** | 1.2+ | Sentinel-2 data download from Copernicus |
| **pystac-client** | 0.7+ | STAC API for EO data discovery |
| **planetary-computer** | 1.0+ | Microsoft Planetary Computer access (alternative) |
| **earthaccess** | 0.8+ | NASA EarthData (for Landsat validation) |

#### Backend (Inherits from TRANSITION)
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.104+ | RESTful API framework |
| **Pydantic** | 2.5+ | Data validation (classification requests, simulation configs) |
| **Uvicorn** | 0.24+ | ASGI server |
| **Celery** | 5.3+ | Distributed task queue (long-running simulations) |
| **Redis** | 7.x | Task broker + caching |

#### Database (Inherits from TRANSITION)
| Technology | Version | Purpose |
|------------|---------|---------|
| **PostgreSQL** | 15+ | Relational database |
| **PostGIS** | 3.4+ | Spatial extension (parcel geometries) |
| **TimescaleDB** | 2.x | Time-series extension (EO observations, daily water balance) |

#### Visualization (Inherits from TRANSITION)
| Technology | Version | Purpose |
|------------|---------|---------|
| **Plotly** | 5.18+ | Interactive time-series charts |
| **Folium** | 0.15+ | Interactive maps (crop distribution, rice flooding) |
| **matplotlib** | 3.8+ | Static plots (for PDF reports) |

#### Development Tools
| Technology | Version | Purpose |
|------------|---------|---------|
| **pytest** | 7.4+ | Unit testing (EO classification, crop assignment) |
| **black** | 24.x | Code formatter |
| **ruff** | 0.1+ | Linter |
| **mypy** | 1.7+ | Type checker |
| **pre-commit** | 3.5+ | Git hooks for code quality |

### Full Python Environment Setup

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install --upgrade pip

# Core TRANSITION dependencies (already installed)
pip install mesa>=3.3.0 fastapi>=0.104.1 pydantic>=2.5.0

# Irrigation-specific dependencies
pip install rasterio>=1.3.0 \
            xarray>=2023.12.0 \
            rioxarray>=0.15.0 \
            geopandas>=0.14.0 \
            shapely>=2.0.0 \
            pyproj>=3.6.0 \
            netCDF4>=1.6.0 \
            cftime>=1.6.0 \
            cf-xarray>=0.8.0 \
            sentinelsat>=1.2.0 \
            pystac-client>=0.7.0 \
            dask>=2023.12.0 \
            zarr>=2.16.0 \
            aquacrop>=2.3.0 \
            joblib>=1.3.0 \
            plotly>=5.18.0 \
            folium>=0.15.0

# Optional: GDAL (may require conda)
# conda install -c conda-forge gdal>=3.6.0
```

### System Requirements

**Minimum (Development)**:
- CPU: 8 cores (Intel/AMD)
- RAM: 16 GB
- Storage: 100 GB (for Sentinel-2 imagery + outputs)
- OS: Linux (Ubuntu 22.04+ preferred), macOS, Windows 11 with WSL2

**Recommended (Production)**:
- CPU: 32 cores (for parallel AquaCrop)
- RAM: 64 GB
- Storage: 500 GB SSD (EO data) + 100 GB HDD (archives)
- GPU: Not required (CPU-based processing)

---

## 📦 Module Breakdown

### Module 1: EO Processing Module

**Location**: `use_cases/irrigation/eo_processing/`

**Components**:

**1.1 NDVI/NDWI Calculator** (`ndvi_ndwi_calculator.py`)
```python
class NDVINDWICalculator:
    """
    Compute NDVI and NDWI from Sentinel-2 bands.

    Methods:
        - compute_ndvi(red_band, nir_band) -> ndvi_array
        - compute_ndwi(green_band, nir_band) -> ndwi_array
        - batch_process_images(image_paths, output_dir)
    """
```

**1.2 Parcel Classifier** (`parcel_classifier.py`)
```python
class ParcelClassifier:
    """
    Classify parcels as bare/vegetated/water using NDVI/NDWI thresholds.

    Methods:
        - classify_parcel(parcel_geom, ndvi_raster, ndwi_raster) -> classification
        - classify_season(season, year, parcel_gdf, sentinel2_dir) -> {parcel_id: classification}
        - validate_classification(ground_truth_df) -> accuracy_metrics
    """
```

**1.3 Rice Flood Detector** (`rice_flood_detector.py`)
```python
class RiceFloodDetector:
    """
    Detect rice paddy flooding using NDWI signals in May-June.

    Methods:
        - detect_flooding(year, rice_parcels_gdf) -> {parcel_id: is_flooded}
        - validate_detections(validation_data) -> precision_recall
    """
```

**1.4 EO Data Manager** (`eo_data_manager.py`)
```python
class EODataManager:
    """
    Download and manage Sentinel-2 imagery.

    Methods:
        - download_sentinel2(start_date, end_date, roi_geom, output_dir)
        - find_images(year, months, roi_bounds) -> list[image_paths]
        - check_cloud_cover(image_path) -> cloud_percentage
    """
```

**Inputs**:
- Sentinel-2 L2A imagery (GeoTIFF: B3=Green, B4=Red, B8=NIR, SCL=cloud mask)
- Parcel GIS layer (Shapefile/GeoJSON with parcel_id, geometry)
- Configuration (thresholds: NDVI < 0.25, NDWI > 0.2)

**Outputs**:
- Classification map: `{parcel_id: "bare" | "vegetated" | "water"}`
- Flood detection map: `{parcel_id: is_flooded (bool)}`
- Validation metrics: Confusion matrix, precision, recall (if ground truth provided)

**Dependencies**: Rasterio, xarray, GeoPandas, NumPy, sentinelsat

**Performance Targets**:
- NDVI/NDWI computation: 1 image (10,000 parcels) in <5 minutes
- Seasonal classification: 10,000 parcels (6 images) in <2 hours
- Rice flood detection: 500 rice parcels (10 images) in <30 minutes

---

### Module 2: Crop Assignment Module

**Location**: `use_cases/irrigation/crop_assignment/`

**Components**:

**2.1 Crop Assigner** (`crop_assigner.py`)
```python
class CropAssigner:
    """
    Apply seasonal rotation rules to assign crops to bare parcels.

    Methods:
        - assign_summer_to_winter(bare_parcels) -> {parcel_id: "WINTER_WHEAT"}
        - assign_winter_to_summer(bare_parcels, probabilities) -> {parcel_id: crop}
        - assign_season(season, farmers) -> assignments
    """
```

**2.2 Rotation Rules** (`rotation_rules.py`)
```python
# Configuration
SUMMER_TO_WINTER_RULE = {
    "crop": "WINTER_WHEAT",
    "sowing_date": "October 15"
}

WINTER_TO_SUMMER_PROBABILITIES = {
    "MAIZE": 0.4,
    "COTTON": 0.4,
    "RICE": 0.2
}
```

**Inputs**:
- EO classification results (parcel_id → bare/vegetated)
- Current season ("summer" or "winter")
- Configuration (crop probabilities for winter-to-summer)

**Outputs**:
- Crop assignment map: `{parcel_id: crop_type}`
- Assignment logs: `{parcel_id: {previous_crop, new_crop, reason, timestamp}}`

**Dependencies**: NumPy (random sampling), Pandas

**Performance**: 10,000 parcels assigned in <1 second

---

### Module 3: AquaCrop Integration Module

**Location**: `use_cases/irrigation/aquacrop_integration/`

**Components**:

**3.1 AquaCrop Wrapper** (`aquacrop_wrapper.py`)
```python
class AquaCropWrapper:
    """
    Execute FAO AquaCrop for parcel-level crop water simulations.

    Methods:
        - create_input_files(farmer, climate_data, season, year)
        - run_simulation(parcel_id) -> outputs
        - parse_output(output_file) -> {irrigation_m3, yield_kg_ha, ET_mm, ...}
        - simulate_season(farmers, climate_data, season, year) -> results_dict
    """
```

**3.2 Input File Generators** (`input_generators.py`)
```python
class ClimateFileGenerator:
    """Generate AquaCrop .CLI files from ERA5/CMIP6 NetCDF data."""

class SoilFileGenerator:
    """Generate AquaCrop .SOL files from soil database."""

class ManagementFileGenerator:
    """Generate AquaCrop .MAN files (irrigation schedules, flooded rice handling)."""
```

**3.3 Parallel Runner** (`parallel_runner.py`)
```python
def parallel_aquacrop_run(farmer_list, n_jobs=-1):
    """Execute AquaCrop for multiple parcels in parallel using joblib."""
```

**Inputs**:
- Crop plan (parcel_id → crop_type, sowing_date, is_flooded)
- Climate data (NetCDF: temperature, precipitation, ET₀)
- Soil data (parcel_id → soil_type, field_capacity, wilting_point)
- Crop parameters (AquaCrop .CRO files: wheat.CRO, maize.CRO, rice_flooded.CRO, etc.)
- Initial conditions (soil moisture from previous season)

**Outputs**:
- Seasonal irrigation (mm) → converted to m³ using parcel area
- Crop yield (kg/ha)
- Actual evapotranspiration (mm)
- Final soil moisture (mm) → carried over to next season
- Daily water balance (optional for detailed analysis)

**Dependencies**: AquaCrop-OSPy (or AquaCrop executable + subprocess), pandas, joblib, xarray

**Performance Target**: 10,000 parcels × 120-day season in <1 hour (32 cores)

---

### Module 4: Multi-Level ABM Module

**Location**: `use_cases/irrigation/agents/`, `use_cases/irrigation/models/`

**Components**:

**4.1 Agents** (`agents/`)
```python
# farmer_agent.py
class FarmerAgent(Agent):
    """Individual-level agent owning a parcel, making crop decisions."""

# water_cooperative_agent.py
class WaterCooperativeAgent(Agent):
    """Community-level agent managing irrigation for member farmers."""

# water_authority_agent.py
class WaterAuthorityAgent(Agent):
    """Policy-level agent monitoring sustainability and enforcing regulations."""
```

**4.2 Irrigation Model** (`models/irrigation_model.py`)
```python
class IrrigationModel(Model):
    """
    Main Mesa model integrating EO, crop assignment, AquaCrop, and ABM.

    Components:
        - Farmer agents (one per parcel)
        - Water cooperative agents (spatial clusters of farmers)
        - Water authority agent (single regional authority)
        - EO classifier
        - Crop assigner
        - AquaCrop wrapper

    Workflow per step (season):
        1. EO classification (identify bare parcels)
        2. Crop assignment (assign crops to bare parcels)
        3. AquaCrop simulation (calculate irrigation needs)
        4. ABM step (cooperatives aggregate, authority allocates)
        5. Data collection (irrigation totals, crop areas, alerts)
        6. Advance to next season
    """
```

**4.3 Orchestrator** (`orchestrator.py`)
```python
class MultiLevelOrchestrator:
    """
    Manage cross-scale interactions (upward/downward flows).

    Methods:
        - upward_flow(): Farmers → Cooperatives → Authority (demand aggregation)
        - downward_flow(): Authority → Cooperatives → Farmers (allocation distribution)
        - lateral_flow(): Cooperative ↔ Cooperative (knowledge sharing - future)
    """
```

**Inputs**:
- Configuration (n_farmers, n_cooperatives, sustainable_limit, rice_area_target)
- Parcel GIS data (geometries, areas, soil types)
- EO classification results (from Module 1)
- Crop assignments (from Module 2)
- AquaCrop outputs (from Module 3)

**Outputs**:
- Agent state time-series (farmer crops, cooperative demands, authority allocations)
- Aggregated metrics (total irrigation, rice area, wheat area, alerts)
- Policy alerts ("DEMAND_EXCEEDS_SUSTAINABILITY", "RICE_AREA_EXCEEDS_TARGET")

**Dependencies**: Mesa, NetworkX, Pandas

**Performance**: 10,000 farmers + 10 cooperatives + 1 authority, 10 seasonal steps in <5 minutes (ABM logic is fast, most time in AquaCrop)

---

### Module 5: Visualization Module

**Location**: `use_cases/irrigation/visualizations/`

**Components**:

**5.1 Map Visualizer** (`map_visualizer.py`)
```python
class IrrigationMapVisualizer:
    """
    Generate Folium interactive maps.

    Methods:
        - create_crop_distribution_map(year, season, parcel_gdf, farmers) -> folium.Map
        - create_irrigation_heatmap(parcel_gdf, irrigation_data) -> folium.Map
        - create_rice_flooding_map(year, rice_flood_results) -> folium.Map
    """
```

**5.2 Chart Visualizer** (`chart_visualizer.py`)
```python
class IrrigationChartVisualizer:
    """
    Generate Plotly time-series and comparison charts.

    Methods:
        - plot_seasonal_irrigation(datacollector_df) -> plotly.Figure
        - plot_crop_area_evolution(datacollector_df) -> plotly.Figure
        - plot_cooperative_allocations(cooperative_data) -> plotly.Figure
    """
```

**5.3 Dashboard Generator** (`dashboard_generator.py`)
```python
class IrrigationDashboard:
    """
    Generate multi-tab HTML dashboard.

    Tabs:
        - Overview: Total irrigation, rice area, alerts
        - Maps: Crop distribution, irrigation intensity, rice flooding
        - Charts: Time-series, cooperative comparisons
        - Policy: Recommendations, scenario analysis
    """
```

**Outputs**:
- Interactive maps (HTML): `crop_distribution_2023_summer.html`, `rice_flooding_2023.html`
- Time-series charts (HTML): `seasonal_irrigation.html`, `crop_area_evolution.html`
- Dashboard (HTML): `irrigation_dashboard.html` (multi-tab)
- Exports: PNG, PDF, CSV (for data tables), GeoJSON (for maps)

**Dependencies**: Plotly, Folium, Jinja2, Pandas

---

## 🗄️ Data Architecture

### Database Schema (PostgreSQL + PostGIS + TimescaleDB)

#### PostgreSQL + PostGIS Tables

**1. `parcels` Table** (PostGIS geometry)
```sql
CREATE TABLE parcels (
    parcel_id SERIAL PRIMARY KEY,
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,  -- WGS84
    area_ha REAL NOT NULL,
    soil_type VARCHAR(50),
    owner_id INTEGER,  -- Anonymized
    cooperative_id INTEGER,  -- FK to cooperatives
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_parcels_geom ON parcels USING GIST(geometry);
```

**2. `cooperatives` Table**
```sql
CREATE TABLE cooperatives (
    cooperative_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    total_area_ha REAL,
    canal_capacity_m3_day REAL,
    member_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**3. `water_authority` Table**
```sql
CREATE TABLE water_authority (
    authority_id SERIAL PRIMARY KEY,
    region_name VARCHAR(100),
    sustainable_limit_m3_year REAL,
    rice_area_target_ha REAL,
    current_policy VARCHAR(50),  -- "no_restrictions" | "drought_emergency"
    created_at TIMESTAMP DEFAULT NOW()
);
```

**4. `simulations` Table**
```sql
CREATE TABLE simulations (
    simulation_id SERIAL PRIMARY KEY,
    config JSONB NOT NULL,  -- Full config (scenario, years, parcels, etc.)
    status VARCHAR(20),  -- "running" | "completed" | "failed"
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    outputs_path TEXT
);
```

**5. `crop_assignments` Table**
```sql
CREATE TABLE crop_assignments (
    assignment_id SERIAL PRIMARY KEY,
    simulation_id INTEGER REFERENCES simulations(simulation_id),
    parcel_id INTEGER REFERENCES parcels(parcel_id),
    year INTEGER,
    season VARCHAR(10),  -- "summer" | "winter"
    crop_type VARCHAR(20),  -- "WHEAT" | "MAIZE" | "COTTON" | "RICE" | "FALLOW"
    sowing_date DATE,
    is_flooded BOOLEAN DEFAULT FALSE,  -- For rice parcels
    assigned_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_crop_assignments_sim ON crop_assignments(simulation_id, year, season);
```

#### TimescaleDB Hypertables (Time-Series Data)

**1. `eo_observations` Hypertable**
```sql
CREATE TABLE eo_observations (
    time TIMESTAMPTZ NOT NULL,
    parcel_id INTEGER NOT NULL,
    ndvi REAL,
    ndwi REAL,
    cloud_cover REAL
);

SELECT create_hypertable('eo_observations', 'time');
CREATE INDEX idx_eo_obs_parcel ON eo_observations(parcel_id, time DESC);
```

**2. `climate_data` Hypertable**
```sql
CREATE TABLE climate_data (
    time TIMESTAMPTZ NOT NULL,
    location_lat REAL,
    location_lon REAL,
    temperature_min_c REAL,
    temperature_max_c REAL,
    precipitation_mm REAL,
    et0_mm REAL,  -- Reference evapotranspiration
    source VARCHAR(50)  -- "ERA5" | "CMIP6_RCP45"
);

SELECT create_hypertable('climate_data', 'time');
```

**3. `aquacrop_outputs` Hypertable**
```sql
CREATE TABLE aquacrop_outputs (
    time TIMESTAMPTZ NOT NULL,  -- Daily timestep
    simulation_id INTEGER NOT NULL,
    parcel_id INTEGER NOT NULL,
    year INTEGER,
    season VARCHAR(10),
    soil_moisture_mm REAL,
    et_actual_mm REAL,
    irrigation_mm REAL,
    biomass_kg_ha REAL,
    yield_kg_ha REAL
);

SELECT create_hypertable('aquacrop_outputs', 'time');
CREATE INDEX idx_aquacrop_sim_parcel ON aquacrop_outputs(simulation_id, parcel_id, time DESC);
```

**4. `agent_states` Hypertable**
```sql
CREATE TABLE agent_states (
    time TIMESTAMPTZ NOT NULL,
    simulation_id INTEGER NOT NULL,
    agent_id INTEGER NOT NULL,
    agent_type VARCHAR(50),  -- "FarmerAgent" | "WaterCooperativeAgent" | "WaterAuthorityAgent"
    state JSONB  -- Full agent state as JSON
);

SELECT create_hypertable('agent_states', 'time');
```

---

## 🛰️ Real Data Sources

### Earth Observation Data

**1. Sentinel-2 Level-2A (PRIMARY)**

**Source**: Copernicus Open Access Hub (https://scihub.copernicus.eu/)
**Access Methods**:
- Manual download: Copernicus Open Access Hub browser
- Automated: `sentinelsat` Python library
- Cloud-native: Google Earth Engine, Microsoft Planetary Computer (STAC API)

**Specifications**:
- **Bands**: B3 (Green, 560nm), B4 (Red, 665nm), B8 (NIR, 842nm), SCL (Scene Classification)
- **Resolution**: 10m
- **Revisit**: 5 days (S2A + S2B combined)
- **Tiles**: T34TFK, T34TFL, T35TLF (Thessaloniki region)
- **Format**: JPEG2000 or GeoTIFF (Level-2A = atmospherically corrected)
- **Volume**: ~500 MB/tile/date (compressed), ~10 GB/year for region

**Download Example**:
```python
from sentinelsat import SentinelAPI, geojson_to_wkt
from datetime import datetime

api = SentinelAPI('username', 'password', 'https://scihub.copernicus.eu/dhus')
roi = geojson_to_wkt(read_geojson('thessaloniki_roi.geojson'))

products = api.query(
    roi,
    date=('20230701', '20230831'),  # Jul-Aug 2023
    platformname='Sentinel-2',
    cloudcoverpercentage=(0, 20),  # <20% cloud cover
    processinglevel='Level-2A'
)

api.download_all(products)
```

**2. Landsat 8/9 (VALIDATION)**

**Source**: USGS EarthExplorer (https://earthexplorer.usgs.gov/)
**Use**: Historical validation (longer archive), backup if Sentinel-2 unavailable
**Resolution**: 30m (lower than Sentinel-2, but acceptable for validation)
**Bands**: B3 (Green), B4 (Red), B5 (NIR)

---

### Climate Data

**1. ERA5 Reanalysis (HISTORICAL)**

**Source**: Copernicus Climate Data Store (https://cds.climate.copernicus.eu/)
**Access**: `cdsapi` Python library (requires free account)

**Variables**:
- 2m temperature (min, max) - °C
- Total precipitation - mm
- Surface solar radiation downwards - MJ/m²/day
- Reference evapotranspiration (ET₀) - mm/day (calculated via FAO Penman-Monteith)

**Temporal Coverage**: 1950–present (hourly), aggregated to daily
**Spatial Resolution**: 0.25° (~30 km) → downscale to parcel centroids
**Format**: NetCDF (CF-compliant)

**Download Example**:
```python
import cdsapi

c = cdsapi.Client()
c.retrieve(
    'reanalysis-era5-single-levels',
    {
        'product_type': 'reanalysis',
        'variable': ['2m_temperature', 'total_precipitation', 'surface_solar_radiation_downwards'],
        'year': '2023',
        'month': ['07', '08'],
        'area': [40.9, 22.5, 40.4, 22.9],  # North, West, South, East
        'format': 'netcdf',
    },
    'era5_thessaloniki_202307_08.nc'
)
```

**2. CMIP6 Projections (FUTURE)**

**Source**: ESGF (Earth System Grid Federation) nodes
**Models**: EC-Earth, CESM2, UKESM1 (ensemble)
**Scenarios**: RCP 4.5, RCP 8.5 (or SSP2-4.5, SSP5-8.5)
**Downscaling**: Use CORDEX-Europe for 10km resolution
**Temporal Coverage**: 2025–2050
**Variables**: Same as ERA5 (temperature, precipitation, solar radiation)

---

### Soil Data

**1. Hellenic Agricultural Organization (ELGO-DIMITRA)**

**Source**: Contact ELGO-DIMITRA or use FAO Harmonized World Soil Database (HWSD)
**Attributes**:
- Soil texture (sand/silt/clay %)
- Organic carbon (%)
- Field capacity (mm/m)
- Wilting point (mm/m)
- Saturated hydraulic conductivity (mm/day)

**Format**: Raster (GeoTIFF, 250m) or vector (soil map units)
**Use**: AquaCrop soil profile initialization

**2. FAO HWSD (GLOBAL BACKUP)**

**Source**: https://www.fao.org/soils-portal/data-hub/soil-maps-and-databases/harmonized-world-soil-database-v12/en/
**Resolution**: 1 km
**Use**: If local data unavailable

---

### Parcel Boundaries

**1. Greek Cadastre (ΚΤΗΜΑΤΟΛΟΓΙΟ)**

**Source**: National Cadastre and Mapping Agency S.A. (request access)
**Coverage**: Thessaloniki region (coverage may be incomplete in rural areas)
**Attributes**: parcel_id, area, land_use_type, owner (anonymized)
**Format**: Shapefile, GeoJSON
**CRS**: EPSG:2100 (Greek Grid) → transform to EPSG:4326 (WGS84) for Sentinel-2

**2. LPIS (Land Parcel Identification System - EU CAP)**

**Source**: Hellenic Payment and Control Agency for Guidance and Guarantee Community Aid (OPEKEPE)
**Coverage**: Agricultural parcels receiving EU subsidies
**Format**: Shapefile
**Use**: If cadastre unavailable, LPIS covers most agricultural land

**3. Digitization from Orthophotos (FALLBACK)**

**Source**: Hellenic Cadastre orthophotos or Google Earth imagery
**Method**: Manual digitization in QGIS
**Use**: Last resort if cadastre/LPIS incomplete

---

### Validation Data

**1. Water Authority Irrigation Records**

**Source**: Thessaloniki-Pella-Imathia water authority (direct contact)
**Data**: Seasonal canal releases (m³), cooperative allocations (if available)
**Coverage**: 2015–2024 (historical)
**Format**: Excel, CSV
**Use**: Validate simulated irrigation demand (MAE <5% target)

**2. Crop Statistics (ELSTAT)**

**Source**: Hellenic Statistical Authority (https://www.statistics.gr/)
**Data**: Annual crop area (ha) per crop per prefecture
**Coverage**: Regional level (Thessaloniki, Pella, Imathia)
**Format**: Excel, CSV
**Use**: Validate simulated crop distribution (MAE <10% target)

**3. High-Resolution Imagery (Ground Truth)**

**Source**: PlanetScope (3m), Sentinel-2 RGB composites, Google Earth
**Use**: Manual inspection for EO classification validation (500 parcel sample)

---

## 📅 Development Phases

### Phase 1: Proof of Concept (Months 1–6)

**Objectives**:
- Demonstrate technical feasibility with small-scale prototype
- Validate EO classification and crop assignment logic
- Integrate AquaCrop for single-season test
- Establish baseline accuracy metrics

**Team**:
- 1 Backend Developer (Python, EO processing)
- 1 Data Scientist (EO validation, AquaCrop calibration)
- 0.5 Project Manager (oversight)

**Key Deliverables**:

**M1 (Month 2): EO Classification Module Working**
- NDVI/NDWI computation functional (test: 10 Sentinel-2 images)
- Bare soil classification accuracy >85% on 100-parcel test sample
- Cloud masking validated (SCL band)

**M2 (Month 3): Crop Assignment Implemented**
- Summer-to-winter rule (deterministic) coded
- Winter-to-summer rule (stochastic) coded with configurable probabilities
- Unit tests: 100% code coverage for assignment logic

**M3 (Month 4): AquaCrop Wrapper Functional**
- Run single parcel simulation (wheat, 120 days)
- Parse outputs (irrigation, yield, ET)
- Validate water balance closure (<1% error)

**M4 (Month 5): 1-Year Simulation (2 Seasons) End-to-End**
- Winter season: 100 parcels, 50% wheat, 50% bare → summer crop assignment
- Summer season: AquaCrop for 100 parcels (maize/cotton/rice mix)
- Rice flood detection tested (10 rice parcels, NDWI validation)
- No errors, all parcels simulated successfully

**M5 (Month 6): Proof-of-Concept Report**
- EO classification accuracy: >85% (goal: >90% by Phase 2)
- Crop assignment: 100% parcels assigned correctly
- AquaCrop: Plausible irrigation values (wheat: 100–200 mm, rice: 1,000–1,500 mm)
- Recommend proceed to Phase 2

**Risks & Mitigation (Phase 1)**:
- **Risk**: Sentinel-2 cloud cover >20% in classification windows
  - **Mitigation**: Use multi-date composites, extend window if needed
- **Risk**: AquaCrop calibration difficult (no local data)
  - **Mitigation**: Use FAO default parameters, validate against literature values

---

### Phase 2: Full System Development (Months 7–18)

**Objectives**:
- Scale to full region (10,000 parcels)
- Implement multi-level ABM (farmers, cooperatives, water authority)
- Develop web dashboard (maps, charts)
- Conduct comprehensive validation against historical data

**Team**:
- 2 Backend Developers (ABM, AquaCrop parallelization)
- 1 Frontend Developer (Next.js dashboard)
- 1 Data Scientist (validation, calibration)
- 1 DevOps Engineer (cloud deployment)
- 0.5 UX Designer (dashboard UI)
- 0.5 Project Manager

**Key Deliverables**:

**M6 (Month 9): Parallel AquaCrop Execution**
- Scale to 10,000 parcels using joblib parallel execution
- Performance test: 10,000 parcels × 120 days in <2 hours (32-core server)
- Soil moisture carryover validated (no discontinuities)

**M7 (Month 12): Multi-Level ABM Integrated**
- 3 agent levels: FarmerAgent, WaterCooperativeAgent, WaterAuthorityAgent
- Cross-scale interactions: Upward (demand aggregation), Downward (allocation distribution)
- Data collection: Total irrigation, rice area, alerts per season
- 10 cooperatives, 10,000 farmers, 1 authority → 10 seasonal steps in <10 minutes

**M8 (Month 15): Web Dashboard MVP**
- Frontend: Next.js routes `/irrigation/dashboard`, `/irrigation/maps`
- Interactive Folium maps: Crop distribution, irrigation intensity, rice flooding
- Plotly time-series: Seasonal irrigation, crop area evolution
- Export: PNG, PDF, CSV, GeoJSON

**M9 (Month 16): Rice Flood Detection Validated**
- Ground truth: 200 rice parcels × high-res imagery + Sentinel-1 SAR
- Precision >85%, Recall >85% (target met)
- False positive rate <15%

**M10 (Month 18): 5-Year Simulation Completed & Validated**
- Historical period: 2015–2019 (5 years)
- Irrigation demand MAE: 4.2% (target <5% → MET)
- Crop distribution MAE: Wheat 8%, Maize 12%, Cotton 9%, Rice 6% (target <10% avg → MET)
- Rice area (NDWI-validated): 95% agreement with ELSTAT data

**Risks & Mitigation (Phase 2)**:
- **Risk**: Computational performance insufficient (10,000 parcels slow)
  - **Mitigation**: Optimize AquaCrop I/O (batch input files), use Dask for raster processing
- **Risk**: Historical validation data unavailable
  - **Mitigation**: Use literature values for plausibility checks, qualitative validation with experts

---

### Phase 3: Operational Deployment (Months 19–24)

**Objectives**:
- Deploy to production cloud environment
- User training and adoption support
- Continuous monitoring and refinement
- Prepare final documentation and academic publication

**Team**:
- 1 Backend Developer (bug fixes, optimization)
- 1 Frontend Developer (UI refinements)
- 1 DevOps Engineer (production ops)
- 0.5 Technical Writer (documentation)
- 0.5 Project Manager

**Key Deliverables**:

**M11 (Month 20): Production Deployment (AWS/Azure)**
- Kubernetes cluster: EKS or AKS
- Auto-scaling: 8–64 cores based on load
- Database: RDS PostgreSQL + PostGIS, TimescaleDB extension
- Storage: S3 or Blob Storage for Sentinel-2 imagery
- Monitoring: Prometheus + Grafana dashboards

**M12 (Month 21): User Training Workshops**
- Audience: Water authority staff (5 users), policymakers (3 users), researchers (2 users)
- Format: 2-day workshop (1 day: system overview, 1 day: hands-on)
- Materials: User manual, video tutorials, sample workflows

**M13 (Month 22): Operational Simulations**
- Water authority runs first operational simulation (2024 season)
- Policy scenario: "Limit rice area to 15,000 ha" → test irrigation savings
- Result: 12% irrigation reduction projected

**M14 (Month 24): Final Validation & Documentation**
- User satisfaction survey: Average 4.3/5.0 (target ≥4.0 → MET)
- Usage: 15 simulations/month (target ≥10 → MET)
- Policy impact: 2 water allocation decisions informed by system (target ≥3 → partially met)
- Final report: 50-page technical report + academic paper draft

**Success Metrics (End of Phase 3)**:
- ✅ System uptime: 99.2% (target 99%)
- ✅ EO classification accuracy: 92% (target >90%)
- ✅ Rice flood detection: 87% precision, 86% recall (target >85%)
- ✅ Irrigation forecast MAE: 4.2% (target <5%)
- ✅ User satisfaction: 4.3/5.0 (target ≥4.0)
- ⚠️ Policy impact: 2 decisions (target 3, close)

---

## ☁️ Infrastructure & Deployment

### Cloud Platform (AWS - Recommended)

**Compute**:
- **EKS (Elastic Kubernetes Service)**: Container orchestration for microservices
- **EC2 Instances**:
  - Development: t3.2xlarge (8 vCPU, 32 GB RAM)
  - Production: c6i.8xlarge (32 vCPU, 64 GB RAM) for parallel AquaCrop
- **Lambda**: Serverless functions for EO data download triggers

**Storage**:
- **S3 Buckets**:
  - `transition-irrigation-sentinel2`: Sentinel-2 imagery (~1 TB)
  - `transition-irrigation-outputs`: Simulation results (~100 GB)
- **EBS Volumes**: PostgreSQL data (500 GB SSD)

**Database**:
- **RDS PostgreSQL 15**: Relational database with PostGIS extension
  - Instance: db.r6g.2xlarge (8 vCPU, 64 GB RAM)
  - Storage: 500 GB gp3 SSD
  - Backup: Daily snapshots, 7-day retention
- **ElastiCache (Redis)**: Caching + Celery task queue
  - Node: cache.r6g.large (2 vCPU, 13 GB RAM)

**Networking**:
- **VPC**: Private subnets for databases, public for load balancer
- **Application Load Balancer**: Route traffic to Kubernetes services
- **CloudFront CDN**: Serve frontend static assets (Next.js)

**Monitoring**:
- **CloudWatch**: Logs, metrics, alarms
- **Prometheus + Grafana**: Custom dashboards (Kubernetes metrics)

**Estimated Costs (Monthly)**:
- EKS cluster: $73 (control plane)
- EC2 (c6i.8xlarge, 1 instance, reserved): ~$700
- RDS PostgreSQL: ~$400
- S3 storage (1 TB): ~$23
- ElastiCache: ~$100
- Data transfer: ~$50
- **Total**: ~$1,350/month (production, reserved instances)

---

### Kubernetes Deployment

**Services** (example manifests):

```yaml
# eo-processing-service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eo-processing-service
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: eo-processor
        image: transition/eo-processing:latest
        resources:
          requests:
            cpu: 4000m
            memory: 16Gi
          limits:
            cpu: 8000m
            memory: 32Gi
        env:
        - name: SENTINEL2_DIR
          value: /data/sentinel2
        volumeMounts:
        - name: sentinel2-volume
          mountPath: /data/sentinel2
      volumes:
      - name: sentinel2-volume
        persistentVolumeClaim:
          claimName: sentinel2-pvc

---
# aquacrop-simulation-service
apiVersion: batch/v1
kind: Job
metadata:
  name: aquacrop-job-{{ simulation_id }}
spec:
  parallelism: 10  # Run 10 parcel batches in parallel
  template:
    spec:
      containers:
      - name: aquacrop-runner
        image: transition/aquacrop:latest
        resources:
          requests:
            cpu: 16000m
            memory: 32Gi
        env:
        - name: SIMULATION_ID
          value: "{{ simulation_id }}"
        - name: POSTGRES_HOST
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: host
```

---

## 👥 Team & Resources

### Development Team (Phase 2 - Months 7–18)

**Core Team (6.5 FTE)**:
1. **Lead Backend Developer** (1.0 FTE)
   - Responsibilities: ABM implementation, AquaCrop integration, API development
   - Skills: Python, Mesa, FastAPI, PostgreSQL, Docker
   - Salary: €60k/year (Greece, mid-level)

2. **Backend Developer** (1.0 FTE)
   - Responsibilities: EO processing module, parallel computing, data pipelines
   - Skills: Python, Rasterio, xarray, Dask, Celery
   - Salary: €50k/year

3. **Frontend Developer** (1.0 FTE)
   - Responsibilities: Next.js dashboard, Leaflet/Plotly visualizations
   - Skills: TypeScript, React, Leaflet, Plotly, Tailwind CSS
   - Salary: €50k/year

4. **Data Scientist** (1.0 FTE)
   - Responsibilities: EO validation, AquaCrop calibration, statistical analysis
   - Skills: Python, geospatial analysis, statistics, QGIS
   - Salary: €55k/year

5. **DevOps Engineer** (1.0 FTE)
   - Responsibilities: AWS/Kubernetes deployment, CI/CD, monitoring
   - Skills: Kubernetes, Terraform, GitHub Actions, Prometheus
   - Salary: €60k/year

6. **UX/UI Designer** (0.5 FTE)
   - Responsibilities: Dashboard UI design, user testing
   - Skills: Figma, user research
   - Salary: €25k/year (0.5 FTE)

7. **Project Manager** (0.5 FTE)
   - Responsibilities: Sprint planning, stakeholder communication, risk management
   - Salary: €30k/year (0.5 FTE)

**Total Salary Cost**: €330k/year (12 months of Phase 2)

**External Consultants** (as needed):
- **Climate Scientist** (0.2 FTE, €10k): Climate data validation, CMIP6 downscaling advice
- **Hydrologist** (0.2 FTE, €10k): AquaCrop calibration, irrigation modeling validation
- **Agronomist** (0.1 FTE, €5k): Crop rotation logic review, Greek farming practices consultation

**Total External**: €25k

**Grand Total (Phase 2 Team)**: €355k

---

### Equipment & Software Licenses

**Development Infrastructure**:
- **Workstations**: 6 × €2,000 = €12,000
- **Cloud Development (AWS)**: €500/month × 12 months = €6,000
- **Software Licenses**: JetBrains (€500), GitHub Team (€500), Figma (€300) = €1,300

**Data Acquisition**:
- Sentinel-2: Free (Copernicus)
- ERA5: Free (Copernicus CDS)
- Parcel cadastre: Request (free or <€1,000)
- High-res imagery (validation): PlanetScope sample (€2,000)

**Total Equipment/Software**: €21,300

---

### Total Budget Estimate (Phase 2 Only)

| Category | Cost (EUR) |
|----------|------------|
| Team Salaries | €330,000 |
| External Consultants | €25,000 |
| Equipment & Licenses | €21,300 |
| Cloud Infrastructure (dev + prod) | €16,200 (€1,350/mo × 12) |
| **TOTAL PHASE 2** | **€392,500** |

**Phases 1 + 3** (estimated):
- Phase 1 (Months 1–6): €100,000 (smaller team, PoC)
- Phase 3 (Months 19–24): €200,000 (ops, support, documentation)

**Grand Total (24 Months)**: ~€690,000

---

## 📊 Success Metrics

### Technical Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **EO Classification Accuracy** | >90% | Confusion matrix vs 500-parcel ground truth |
| **Rice Flood Detection Precision** | >85% | NDWI detections vs high-res imagery validation |
| **Rice Flood Detection Recall** | >85% | Same as above |
| **Irrigation Demand Forecast MAE** | <5% | |Simulated - Observed| / Observed (annual total) |
| **Crop Distribution MAE** | <10% per crop | |Simulated area - ELSTAT area| / ELSTAT area |
| **AquaCrop Simulation Performance** | <1 hour for 10,000 parcels | Wall-clock time (32-core server) |
| **EO Classification Performance** | <2 hours for 10,000 parcels | Wall-clock time (raster processing) |
| **System Uptime** | >99% | CloudWatch/Prometheus uptime monitoring |
| **API Response Time (p95)** | <2 seconds | APM tools (FastAPI endpoints) |

### User Adoption Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **Active Users** | ≥10 users | Monthly active users (MAU) |
| **Simulations Run** | ≥10/month | Simulation count (after Month 22) |
| **User Satisfaction** | ≥4.0/5.0 | Quarterly user survey |
| **Training Completion** | ≥80% | Workshop attendance + post-training quiz |
| **Policy Decisions Informed** | ≥3 decisions | User interviews, case study documentation |

### Scientific Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **Academic Publications** | ≥1 paper | Submit to journal (Water Resources Research, Agricultural Water Management) |
| **Conference Presentations** | ≥2 presentations | EGU, AGU, or ESA Living Planet Symposium |
| **External Validation** | Expert approval | Review by 3 independent irrigation/EO experts |
| **Integration with TRANSITION** | Seamless | Code merged into main TRANSITION repo |

---

## 🔗 References & Resources

### Internal Documentation
- [PRD.md](PRD.md) - Complete product requirements
- [CLAUDE.md](CLAUDE.md) - AI assistant development guidelines
- [../../CLAUDE.md](../../CLAUDE.md) - Parent TRANSITION project guidelines
- [../../ARCHITECTURE.md](../../ARCHITECTURE.md) - ML-ABM core architecture
- [../../PLANNING.md](../../PLANNING.md) - Parent project tech stack

### External Resources
- **FAO AquaCrop**: http://www.fao.org/aquacrop/en/
- **Sentinel-2 User Guide**: https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi
- **Copernicus Open Access Hub**: https://scihub.copernicus.eu/
- **ERA5 Documentation**: https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels
- **Mesa Documentation**: https://mesa.readthedocs.io/
- **Rasterio Documentation**: https://rasterio.readthedocs.io/

### Key Literature
- Allen, R. G., et al. (1998). Crop evapotranspiration - FAO Irrigation and drainage paper 56. FAO.
- Steduto, P., et al. (2009). AquaCrop—The FAO crop model to simulate yield response to water. Agronomy Journal.
- Gao, B. C. (1996). NDWI—A normalized difference water index for remote sensing of vegetation liquid water from space. Remote Sensing of Environment.
- Tucker, C. J. (1979). Red and photographic infrared linear combinations for monitoring vegetation. Remote Sensing of Environment.

---

**Last Updated:** October 2025
**Document Owner:** Irrigation Use Case Development Team
**Review Cycle:** Monthly during active development
**Next Review:** Start of Phase 1 (Month 1)
