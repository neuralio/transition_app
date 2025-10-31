# CLAUDE.md - EO-Informed Irrigation Use Case
## AI Assistant Guidelines for Irrigation Simulation Development

**Last Updated:** October 2025
**Use Case:** EO-Informed Irrigation Simulation (Multi-Regional Agricultural Water Management)
**Status:** Planned (Phase 2)

---

## 🎯 Essential Context (Read First)

### Priority Reading Order

1. **[PRD.md](PRD.md)** - Complete product requirements for irrigation use case
2. **[PLANNING.md](PLANNING.md)** - Technical stack and development roadmap
3. **[../../CLAUDE.md](../../CLAUDE.md)** - Parent project guidelines (TRANSITION platform)
4. **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - Multi-level ABM core architecture
5. **[../../PRD.md](../../PRD.md)** - Parent project requirements
6. **[../../ML-ABM-REQUIREMENTS.md](../../ML-ABM-REQUIREMENTS.md)** - ML-ABM specifications

---

## ⚠️ Critical Rules

### 1. Real Data ONLY
- **100% Real EO Data Required**: Sentinel-2 NDVI/NDWI time-series from Copernicus
- **NO Dummy Data**: Never use mock, synthetic, or placeholder data
- **Real Climate Data**: ERA5 reanalysis (historical), CMIP6 projections (future)
- **Real Soil/Crop Data**: FAO AquaCrop parameters, Hellenic Agricultural Organization soil data
- **Validation Required**: All outputs must align with historical irrigation records (within 5% error)

### 2. Multi-Level ABM Architecture
This is a **real Multi-Level Agent-Based Modeling (ML-ABM) implementation** following TRANSITION's core architecture:

**Four Levels (Mandatory)**:
- **Individual Level**: Farmer agents (one per parcel) making seasonal crop decisions
- **Community Level**: Water cooperative agents managing irrigation resources
- **Market Level**: (Optional for Phase 1) - Agricultural commodity markets
- **Policy Level**: Water authority agents setting regulations and monitoring sustainability

**Cross-Scale Interactions**:
- **Upward Flow**: Farmers → Cooperatives → Water Authority (demand aggregation)
- **Downward Flow**: Water Authority → Cooperatives → Farmers (allocation decisions)
- **Lateral Flow**: Cooperative ↔ Cooperative (knowledge sharing), Farmer ↔ Farmer (peer influence - future)

### 3. Developer User Stories (See PRD.md Section 7)
All implementation MUST follow the 6 developer-focused user stories with specific KPIs:

**IRR-US-01: Automated EO Classification**
- NDVI/NDWI classification with time-series phenology analysis
- Time-series robustness: Distinguish harvested (NDVI drops end-season) from fallow (low all season)
- **KPI: >90% bare soil detection accuracy** vs ground truth
- No manual intervention, cloud gap handling via multi-date composites
- Seasonal classification windows: End-of-summer (Jul–Aug), end-of-winter (Jan–Feb)

**IRR-US-02: Dynamic Crop Assignment Logic**
- **Summer-to-Winter (Deterministic)**: Bare summer → WINTER_WHEAT
- **Winter-to-Summer (Stochastic)**: Bare winter → random {MAIZE, COTTON, RICE} with configurable probabilities
- Agent-based: Farmer observes EO classification → decides next crop
- **KPI: 100% parcels assigned**, deterministic & reproducible (seeded RNG)

**IRR-US-03: Rice Flood Detection via NDWI**
- May–June NDWI monitoring for rice-assigned parcels
- Flooding criteria: NDWI > 0.2 (single date) OR NDWI > 0 sustained ≥7 days
- AquaCrop regime: isFlooded=True → rice_flooded.CRO, False → rice_rainfed.CRO or reassign
- **KPI: >85% precision, >85% recall** vs high-res imagery validation

**IRR-US-04: AquaCrop Integration & Seasonal Reset**
- Seamless re-initialization at winter→summer, summer→winter transitions
- Soil moisture carryover (no discontinuities >10 mm)
- **KPI: 100% seasonal transition success rate, <10% computational overhead**
- Water balance closure: ±1% error per season

**IRR-US-05: Irrigation Modeling Impact Assessment**
- Dynamic EO-based vs static baseline comparison
- **KPI: Dynamic achieves <5% MAE**, static typically ~15% MAE (3x improvement)
- Uncertainty quantification: 95% confidence intervals

**IRR-US-06: Data & Module Interfaces**
- Modular APIs: EO Classification, Crop Assignment, Rice Flood Detection, AquaCrop Wrapper
- Data formats: JSON/Parquet (inter-module), GeoJSON (spatial), NetCDF (time-series)
- **KPI: >80% code coverage, modularity (components replaceable without breaking others)**
- Testing: Unit tests (pytest), integration tests, API documentation (OpenAPI/Swagger)

---

## 📁 Code Standards

### File Limits & Naming
- **Max 500 lines per file**
- **Naming Conventions**:
  - Functions: `camelCase` (Python: `snake_case`)
  - Classes: `PascalCase`
  - Files: `snake_case.py` (Python), `kebab-case.ts` (TypeScript)
  - Constants: `UPPER_SNAKE_CASE`

### Code practices
- **Modular** Code must be modular
- **Object oriented** Code must be object-oriented
    
### Python Standards (PEP 8)
- **Type hints required** for all functions
- **Docstrings**: Google style for all classes and public functions
- **Function arguments**: If >3 args, place each on new line
- **Imports**: Group standard → third-party → local, sort alphabetically
- **Line length**: 88 characters (Black formatter)

### Module Structure (Follow Existing Pattern)
```
use_cases/irrigation/
├── agents/
│   ├── farmer_agent.py          # Individual level
│   ├── water_cooperative_agent.py  # Community level
│   └── water_authority_agent.py    # Policy level
├── models/
│   └── irrigation_model.py      # Mesa model with AquaCrop integration
├── scripts/
│   ├── eo_classification.py    # NDVI/NDWI processing
│   ├── crop_assignment.py      # Seasonal assignment logic
│   ├── rice_flood_detection.py # NDWI flood validation
│   └── ensemble_runner.py      # Monte Carlo simulations (optional)
├── visualizations/
│   └── irrigation_visualizer.py  # Maps, time-series charts
├── run_irrigation.py            # Main CLI entry point
├── config.yaml                  # Configuration (REQUIRED)
├── PRD.md                       # This file
├── PLANNING.md                  # Tech stack
└── CLAUDE.md                    # AI guidelines
```

---

## 🛠️ Technology Stack (Irrigation-Specific)

### Core Dependencies (MUST Use)
```python
# Agent-Based Modeling
mesa>=3.3.0

# Earth Observation Processing
rasterio>=1.3.0       # REQUIRED for Sentinel-2 raster data
xarray>=2023.12.0     # REQUIRED for NetCDF climate data
geopandas>=0.14.0     # REQUIRED for parcel GIS data
rioxarray>=0.15.0     # Rasterio + xarray integration

# Crop Water Modeling
# AquaCrop-OSPy (Python implementation of FAO AquaCrop)
# Install via: pip install aquacrop
aquacrop>=2.3.0  # OR use subprocess to call AquaCrop executable

# Climate Data
cftime>=1.6.0
cf-xarray>=0.8.0
netCDF4>=1.6.0

# Geospatial
shapely>=2.0.0
pyproj>=3.6.0
fiona>=1.9.0

# Data Access (Sentinel-2)
sentinelsat>=1.2.0  # Copernicus data download
pystac-client>=0.7.0  # STAC API for EO discovery

# Backend (API)
fastapi>=0.104.1
pydantic>=2.5.0

# Visualization
plotly>=5.18.0
folium>=0.15.0
matplotlib>=3.8.0

# Parallel Processing
dask>=2023.12.0  # For 10,000 parcel simulations
joblib>=1.3.0
```

### Data Sources (Real Only - Area-Agnostic)
**Sentinel-2 Level-2A** (Primary):
- **Access**: Copernicus Open Access Hub, Google Earth Engine, Microsoft Planetary Computer
- **Bands**: B3 (Green), B4 (Red), B8 (NIR), SCL (cloud mask)
- **Resolution**: 10m
- **Revisit**: 5 days (S2A+S2B combined)
- **Format**: GeoTIFF or JPEG2000
- **Volume**: ~10 GB/year compressed per region (varies by area)

**Climate Data**:
- **Historical**: ERA5 reanalysis (temperature, precipitation, ET₀)
- **Future**: CMIP6 downscaled projections (RCP 4.5, 8.5) or regional climate models
- **Format**: NetCDF (CF-compliant)
- **Spatial Resolution**: 0.25° (~30 km) → downscale to parcel centroids

**Soil Data**:
- **Source**: National agricultural agencies, FAO Harmonized World Soil Database (HWSD)
- **Attributes**: Texture, field capacity, wilting point, hydraulic conductivity
- **Format**: Raster (GeoTIFF) or vector (Shapefile)
- **Resolution**: 250m to 1km (varies by source)

**Parcel Boundaries**:
- **Source**: National cadastre systems, LPIS (EU Land Parcel Identification System), or digitized from orthophotos
- **Format**: Shapefile, GeoJSON
- **CRS**: Local coordinate system → transform to EPSG:4326 (WGS84) for Sentinel-2 alignment

---

## 🧬 Multi-Level ABM Implementation Guide

### Agent Hierarchy (Irrigation Context)

**1. FarmerAgent (Individual Level)**
```python
from mesa import Agent

class FarmerAgent(Agent):
    """
    Farmer agent owning a parcel, making seasonal crop decisions.

    Attributes:
        parcel_id (int): Unique parcel identifier
        location (tuple): (lat, lon) coordinates
        soil_type (str): Soil classification
        current_crop (str): "WHEAT" | "MAIZE" | "COTTON" | "RICE" | "FALLOW"
        land_status (str): "bare" | "vegetated" (from EO classification)
        irrigation_used_m3 (float): Last season irrigation volume
        water_cooperative_id (int): Membership in cooperative

    Decision Logic:
        - Observe EO-derived land_status at season end
        - Apply crop rotation rules (summer-to-winter, winter-to-summer)
        - (Future RL): Optimize crop choice based on water availability signals
    """

    def __init__(self, unique_id, model, parcel_id, location, soil_type):
        super().__init__(unique_id, model)
        self.parcel_id = parcel_id
        self.location = location
        self.soil_type = soil_type
        self.current_crop = "FALLOW"
        self.land_status = "bare"
        self.irrigation_used_m3 = 0.0
        self.water_cooperative_id = None

    def step(self):
        """Execute seasonal decision-making."""
        self.observe_land_status()  # Get EO classification result
        self.decide_next_crop()     # Apply rotation rules
        self.request_water()        # Submit demand to cooperative

    def observe_land_status(self):
        """Receive EO classification: 'bare' or 'vegetated'."""
        # In real implementation, get from model.eo_classification_results
        pass

    def decide_next_crop(self):
        """Apply dynamic crop assignment rules."""
        season = self.model.current_season
        if season == "summer" and self.land_status == "bare":
            # Summer-to-Winter: Bare in summer → winter wheat
            self.next_crop = "WINTER_WHEAT"
        elif season == "winter" and self.land_status == "bare":
            # Winter-to-Summer: Bare in winter → random summer crop
            probs = self.model.config['crop_probabilities']
            self.next_crop = random.choices(
                ["MAIZE", "COTTON", "RICE"],
                weights=[probs['maize'], probs['cotton'], probs['rice']]
            )[0]
```

**2. WaterCooperativeAgent (Community Level)**
```python
class WaterCooperativeAgent(Agent):
    """
    Water cooperative managing irrigation for member farmers.

    Attributes:
        cooperative_id (int): Unique ID
        member_parcels (list): List of farmer agent IDs
        total_irrigated_area_ha (float): Sum of member parcel areas
        canal_capacity_m3_day (float): Maximum delivery capacity
        seasonal_allocation_m3 (float): Water allocated by authority

    Behaviors:
        - Aggregate irrigation demand from members (upward flow)
        - Submit request to water authority
        - Distribute allocated water to members (downward flow)
        - (Future) Prioritize allocation if shortage
    """

    def step(self):
        """Aggregate member demands and request allocation."""
        self.aggregate_demand()
        self.request_allocation()
        self.distribute_water()

    def aggregate_demand(self):
        """Sum irrigation needs from all member farmers."""
        total_demand = 0.0
        for farmer_id in self.member_parcels:
            farmer = self.model.schedule.agents[farmer_id]
            # Demand from AquaCrop simulation output
            total_demand += farmer.irrigation_demand_m3
        self.total_demand_m3 = total_demand

    def request_allocation(self):
        """Submit allocation request to water authority."""
        authority = self.model.water_authority
        authority.receive_request(self.cooperative_id, self.total_demand_m3)

    def distribute_water(self):
        """Allocate water to members (pro-rata if shortage)."""
        if self.allocated_m3 < self.total_demand_m3:
            ratio = self.allocated_m3 / self.total_demand_m3
            for farmer_id in self.member_parcels:
                farmer = self.model.schedule.agents[farmer_id]
                farmer.allocated_water_m3 = farmer.irrigation_demand_m3 * ratio
        else:
            # Sufficient water, grant full requests
            pass
```

**3. WaterAuthorityAgent (Policy Level)**
```python
class WaterAuthorityAgent(Agent):
    """
    Regional water authority setting policies and monitoring sustainability.

    Attributes:
        sustainable_limit_m3_year (float): Annual irrigation cap
        rice_area_target_ha (float): Maximum rice cultivation area
        current_policy (str): "no_restrictions" | "drought_emergency"
        total_demand_m3 (float): Sum of all cooperative requests
        total_rice_area_ha (float): Detected rice area from EO + NDWI

    Behaviors:
        - Receive cooperative requests (upward flow)
        - Monitor total demand vs sustainable limit
        - Allocate water (may reduce if exceeds limit)
        - Flag alerts if rice area or demand exceeds targets
        - (Future) Adjust policies: quotas, rice area caps, subsidies
    """

    def step(self):
        """Process cooperative requests and enforce policies."""
        self.compute_total_demand()
        self.evaluate_sustainability()
        self.allocate_to_cooperatives()
        self.monitor_rice_area()

    def compute_total_demand(self):
        """Sum all cooperative requests."""
        self.total_demand_m3 = sum(
            coop.total_demand_m3 for coop in self.model.cooperatives
        )

    def evaluate_sustainability(self):
        """Check if demand exceeds sustainable limit."""
        if self.total_demand_m3 > self.sustainable_limit_m3_year:
            self.alerts.append("DEMAND_EXCEEDS_SUSTAINABILITY")
            self.current_policy = "drought_emergency"
        else:
            self.current_policy = "no_restrictions"

    def allocate_to_cooperatives(self):
        """Allocate water (pro-rata if shortage)."""
        if self.current_policy == "drought_emergency":
            # Reduce allocations proportionally
            ratio = self.sustainable_limit_m3_year / self.total_demand_m3
            for coop in self.model.cooperatives:
                coop.allocated_m3 = coop.total_demand_m3 * ratio
        else:
            # Grant full requests
            for coop in self.model.cooperatives:
                coop.allocated_m3 = coop.total_demand_m3

    def monitor_rice_area(self):
        """Count rice parcels confirmed flooded via NDWI."""
        rice_parcels = [
            farmer for farmer in self.model.farmers
            if farmer.current_crop == "RICE" and farmer.is_flooded
        ]
        self.total_rice_area_ha = sum(p.area_ha for p in rice_parcels)

        if self.total_rice_area_ha > self.rice_area_target_ha:
            self.alerts.append("RICE_AREA_EXCEEDS_TARGET")
```

### Mesa Model (IrrigationModel)
```python
from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector

class IrrigationModel(Model):
    """
    Main irrigation simulation model integrating EO, ABM, and AquaCrop.

    Components:
        - EO classification module (NDVI/NDWI processing)
        - Crop assignment module (seasonal rotation rules)
        - AquaCrop wrapper (crop water balance simulation)
        - Multi-level ABM (farmers, cooperatives, water authority)
    """

    def __init__(self, config, parcel_gdf, climate_data):
        super().__init__()
        self.config = config
        self.parcel_gdf = parcel_gdf
        self.climate_data = climate_data
        self.current_season = "winter"  # or "summer"
        self.current_year = 0

        # Initialize agents
        self.schedule = RandomActivation(self)
        self.create_farmer_agents()
        self.create_cooperative_agents()
        self.create_water_authority()

        # Initialize modules
        self.eo_classifier = EOClassifier(config)
        self.crop_assigner = CropAssigner(config)
        self.aquacrop_runner = AquaCropRunner(config)

        # Data collection
        self.datacollector = DataCollector(
            model_reporters={
                "total_irrigation_m3": lambda m: sum(f.irrigation_used_m3 for f in m.farmers),
                "rice_area_ha": lambda m: m.water_authority.total_rice_area_ha,
                "wheat_area_ha": lambda m: sum(1 for f in m.farmers if f.current_crop == "WHEAT"),
            },
            agent_reporters={
                "crop": "current_crop",
                "irrigation_m3": "irrigation_used_m3",
                "is_flooded": lambda a: getattr(a, 'is_flooded', False),
            }
        )

    def step(self):
        """Execute one seasonal step."""
        # 1. EO Classification (end of season)
        self.classify_parcels()

        # 2. Crop Assignment (for next season)
        self.assign_crops()

        # 3. AquaCrop Simulation (current season)
        self.run_aquacrop()

        # 4. ABM Step (agents make decisions, cooperatives aggregate)
        self.schedule.step()

        # 5. Data Collection
        self.datacollector.collect(self)

        # 6. Advance to next season
        self.advance_season()

    def classify_parcels(self):
        """Run EO classification to identify bare/vegetated parcels."""
        results = self.eo_classifier.classify_season(
            season=self.current_season,
            year=self.current_year
        )
        # Update farmer agents with classification results
        for farmer in self.farmers:
            farmer.land_status = results.get(farmer.parcel_id, "vegetated")

    def assign_crops(self):
        """Apply crop rotation rules to bare parcels."""
        assignments = self.crop_assigner.assign_season(
            season=self.current_season,
            farmers=self.farmers
        )
        # Update next_crop attribute
        for farmer in self.farmers:
            if farmer.land_status == "bare":
                farmer.next_crop = assignments[farmer.parcel_id]

    def run_aquacrop(self):
        """Execute AquaCrop for all parcels, update irrigation demands."""
        results = self.aquacrop_runner.simulate_season(
            farmers=self.farmers,
            climate_data=self.climate_data,
            season=self.current_season,
            year=self.current_year
        )
        # Update irrigation volumes
        for farmer in self.farmers:
            farmer.irrigation_used_m3 = results[farmer.parcel_id]['irrigation_m3']
```

---

## 📊 EO Classification Module

### NDVI/NDWI Processing
```python
import rasterio
import numpy as np
from rasterio.mask import mask
import geopandas as gpd

class EOClassifier:
    """
    Sentinel-2 based parcel classification using NDVI/NDWI.

    Methods:
        - compute_ndvi(): Calculate NDVI from Red and NIR bands
        - compute_ndwi(): Calculate NDWI from Green and NIR bands
        - classify_parcel(): Threshold NDVI/NDWI to determine bare/vegetated/water
        - classify_season(): Batch classify all parcels for a season
    """

    def __init__(self, config):
        self.ndvi_threshold = config['eo']['ndvi_threshold']  # e.g., 0.25
        self.ndwi_threshold = config['eo']['ndwi_threshold']  # e.g., 0.2
        self.sentinel2_dir = config['data']['sentinel2_path']

    def compute_ndvi(self, red_band, nir_band):
        """NDVI = (NIR - Red) / (NIR + Red)"""
        with np.errstate(divide='ignore', invalid='ignore'):
            ndvi = (nir_band - red_band) / (nir_band + red_band)
            ndvi[np.isnan(ndvi)] = 0  # Handle divide-by-zero
        return ndvi

    def compute_ndwi(self, green_band, nir_band):
        """NDWI = (Green - NIR) / (Green + NIR)"""
        with np.errstate(divide='ignore', invalid='ignore'):
            ndwi = (green_band - nir_band) / (green_band + nir_band)
            ndwi[np.isnan(ndwi)] = 0
        return ndwi

    def classify_parcel(self, parcel_geom, ndvi_raster_path, ndwi_raster_path):
        """
        Classify single parcel as bare/vegetated/water.

        Args:
            parcel_geom: Shapely geometry (polygon)
            ndvi_raster_path: Path to NDVI GeoTIFF
            ndwi_raster_path: Path to NDWI GeoTIFF

        Returns:
            str: "bare" | "vegetated" | "water"
        """
        # Extract NDVI within parcel
        with rasterio.open(ndvi_raster_path) as src:
            ndvi_vals, _ = mask(src, [parcel_geom], crop=True, all_touched=True)
            mean_ndvi = np.nanmean(ndvi_vals)

        # Extract NDWI within parcel
        with rasterio.open(ndwi_raster_path) as src:
            ndwi_vals, _ = mask(src, [parcel_geom], crop=True, all_touched=True)
            mean_ndwi = np.nanmean(ndwi_vals)

        # Classification logic
        if mean_ndwi > self.ndwi_threshold:
            return "water"  # Standing water (e.g., flooded rice paddy)
        elif mean_ndvi < self.ndvi_threshold:
            return "bare"   # Bare soil or fallow
        else:
            return "vegetated"  # Crop present

    def classify_season(self, season, year, parcel_gdf):
        """
        Classify all parcels for a season using time-series.

        Args:
            season (str): "summer" or "winter"
            year (int): Simulation year
            parcel_gdf (GeoDataFrame): Parcel geometries

        Returns:
            dict: {parcel_id: classification_result}
        """
        # Load Sentinel-2 imagery for classification window
        if season == "summer":
            months = [7, 8]  # Jul-Aug
        else:
            months = [1, 2]  # Jan-Feb

        classifications = {}
        for idx, row in parcel_gdf.iterrows():
            parcel_id = row['parcel_id']
            geom = row['geometry']

            # Get all clear images in window
            images = self.find_sentinel2_images(year, months, geom.bounds)

            # Compute NDVI/NDWI for each image
            ndvi_series = []
            ndwi_series = []
            for img in images:
                ndvi = self.load_and_compute_ndvi(img, geom)
                ndwi = self.load_and_compute_ndwi(img, geom)
                ndvi_series.append(ndvi)
                ndwi_series.append(ndwi)

            # Temporal consistency: bare if NDVI < threshold in >=80% of images
            bare_count = sum(1 for ndvi in ndvi_series if ndvi < self.ndvi_threshold)
            if bare_count / len(ndvi_series) >= 0.8:
                # Check if it's water-covered
                if max(ndwi_series) > self.ndwi_threshold:
                    classifications[parcel_id] = "water"
                else:
                    classifications[parcel_id] = "bare"
            else:
                classifications[parcel_id] = "vegetated"

        return classifications
```

### Rice Flood Detection
```python
class RiceFloodDetector:
    """
    NDWI-based rice paddy flooding detection.

    Monitors May-June NDWI for rice-assigned parcels to confirm flooding.
    """

    def __init__(self, config):
        self.ndwi_flood_threshold = config['rice']['ndwi_flood_threshold']  # e.g., 0.2
        self.monitoring_window = config['rice']['monitoring_window']  # (5, 1) to (6, 30): May-June

    def detect_flooding(self, year, rice_parcels_gdf):
        """
        Detect which rice parcels are actually flooded.

        Args:
            year (int): Current year
            rice_parcels_gdf (GeoDataFrame): Parcels assigned to rice

        Returns:
            dict: {parcel_id: is_flooded (bool)}
        """
        flooding_status = {}

        for idx, row in rice_parcels_gdf.iterrows():
            parcel_id = row['parcel_id']
            geom = row['geometry']

            # Load NDWI images for May-June
            images = self.find_sentinel2_images(
                year,
                months=[5, 6],
                bounds=geom.bounds
            )

            # Check if any image shows flooding
            is_flooded = False
            for img in images:
                ndwi = self.compute_ndwi_for_parcel(img, geom)
                if ndwi > self.ndwi_flood_threshold:
                    is_flooded = True
                    break  # Flooding detected

            flooding_status[parcel_id] = is_flooded

        return flooding_status
```

---

## 🌾 AquaCrop Integration

### AquaCrop Wrapper
```python
import subprocess
import pandas as pd
from pathlib import Path

class AquaCropRunner:
    """
    Wrapper for FAO AquaCrop crop water model.

    Manages seasonal re-initialization, soil moisture carryover, and parallel execution.
    """

    def __init__(self, config):
        self.aquacrop_exe = config['aquacrop']['executable_path']
        self.crop_files = config['aquacrop']['crop_files']  # {WHEAT: wheat.CRO, ...}
        self.soil_data = config['aquacrop']['soil_data']
        self.output_dir = Path(config['aquacrop']['output_dir'])

    def simulate_season(self, farmers, climate_data, season, year):
        """
        Run AquaCrop for all parcels in parallel.

        Args:
            farmers (list): FarmerAgent instances
            climate_data (xr.Dataset): Temperature, precipitation, ET0
            season (str): "summer" or "winter"
            year (int): Simulation year

        Returns:
            dict: {parcel_id: {irrigation_m3, yield_kg_ha, ET_mm, ...}}
        """
        results = {}

        # Prepare AquaCrop input files for each parcel
        for farmer in farmers:
            if farmer.current_crop == "FALLOW":
                results[farmer.parcel_id] = {'irrigation_m3': 0, 'yield_kg_ha': 0}
                continue

            # Create parcel-specific input files
            self.create_input_files(farmer, climate_data, season, year)

        # Run AquaCrop (parallel via joblib or dask)
        from joblib import Parallel, delayed

        aquacrop_results = Parallel(n_jobs=-1)(
            delayed(self.run_aquacrop_for_parcel)(farmer)
            for farmer in farmers if farmer.current_crop != "FALLOW"
        )

        # Parse outputs
        for farmer, output in zip(farmers, aquacrop_results):
            if output is not None:
                results[farmer.parcel_id] = output

        return results

    def create_input_files(self, farmer, climate_data, season, year):
        """
        Generate AquaCrop input files for a parcel.

        Files:
            - .CLI: Climate data (Tmin, Tmax, precip, ET0)
            - .CRO: Crop parameters (load from crop_files[farmer.current_crop])
            - .SOL: Soil profile (from soil_data based on farmer.soil_type)
            - .MAN: Irrigation management (depends on crop + is_flooded)
            - .PRO: Project file linking all inputs
        """
        parcel_id = farmer.parcel_id
        parcel_dir = self.output_dir / f"parcel_{parcel_id}" / f"{season}_{year}"
        parcel_dir.mkdir(parents=True, exist_ok=True)

        # 1. Climate file (.CLI)
        cli_path = parcel_dir / f"{parcel_id}.CLI"
        self.write_climate_file(climate_data, farmer.location, season, year, cli_path)

        # 2. Crop file (.CRO) - copy from templates
        crop = farmer.current_crop
        if crop == "RICE" and hasattr(farmer, 'is_flooded') and farmer.is_flooded:
            cro_template = self.crop_files['RICE_FLOODED']
        else:
            cro_template = self.crop_files[crop]

        cro_path = parcel_dir / f"{parcel_id}.CRO"
        shutil.copy(cro_template, cro_path)

        # 3. Soil file (.SOL)
        sol_path = parcel_dir / f"{parcel_id}.SOL"
        self.write_soil_file(farmer.soil_type, sol_path)

        # 4. Management file (.MAN)
        man_path = parcel_dir / f"{parcel_id}.MAN"
        if crop == "RICE" and farmer.is_flooded:
            self.write_flooded_rice_management(man_path)
        else:
            self.write_standard_management(crop, man_path)

        # 5. Project file (.PRO)
        pro_path = parcel_dir / f"{parcel_id}.PRO"
        self.write_project_file(parcel_id, cli_path, cro_path, sol_path, man_path, pro_path)

        # 6. Initial conditions (soil moisture from previous season)
        if hasattr(farmer, 'final_soil_moisture_mm'):
            self.set_initial_soil_moisture(pro_path, farmer.final_soil_moisture_mm)

    def run_aquacrop_for_parcel(self, farmer):
        """
        Execute AquaCrop for a single parcel.

        Returns:
            dict: Simulation outputs {irrigation_m3, yield_kg_ha, ET_mm, ...}
        """
        parcel_id = farmer.parcel_id
        pro_file = self.output_dir / f"parcel_{parcel_id}" / f"{farmer.parcel_id}.PRO"

        # Run AquaCrop executable
        cmd = [self.aquacrop_exe, str(pro_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f"AquaCrop failed for parcel {parcel_id}: {result.stderr}")
            return None

        # Parse output files
        output_file = pro_file.parent / f"{parcel_id}_SeasonOutput.txt"
        outputs = self.parse_aquacrop_output(output_file)

        # Store final soil moisture for carryover
        farmer.final_soil_moisture_mm = outputs['final_soil_moisture_mm']

        return outputs

    def parse_aquacrop_output(self, output_file):
        """
        Parse AquaCrop output text file.

        Returns:
            dict: {irrigation_m3, yield_kg_ha, ET_act_mm, biomass_kg_ha, ...}
        """
        # AquaCrop output format varies; adapt to your version
        # Typical structure: lines with seasonal totals
        with open(output_file, 'r') as f:
            lines = f.readlines()

        # Example parsing (adjust to actual format)
        outputs = {}
        for line in lines:
            if "Total irrigation" in line:
                outputs['irrigation_mm'] = float(line.split()[-1])
            elif "Yield (dry)" in line:
                outputs['yield_kg_ha'] = float(line.split()[-1])
            elif "Actual ET" in line:
                outputs['ET_act_mm'] = float(line.split()[-1])
            elif "Final soil moisture" in line:
                outputs['final_soil_moisture_mm'] = float(line.split()[-1])

        # Convert irrigation mm to m³ (requires parcel area)
        # Assuming farmer.area_ha is available
        # outputs['irrigation_m3'] = outputs['irrigation_mm'] * farmer.area_ha * 10  # mm → m³/ha → m³

        return outputs
```

---

## 🎨 Visualization Guidelines

### Interactive Maps (Folium)
- **Crop Distribution Map**: Color-coded parcels (wheat=yellow, maize=green, cotton=white, rice=blue, fallow=gray)
- **Irrigation Intensity Map**: Heatmap of total seasonal irrigation (m³/ha)
- **Rice Flooding Events**: Blue markers for NDWI-confirmed flooded parcels

### Time-Series Charts (Plotly)
- **Seasonal Irrigation Demand**: Bar chart (10 bars for 5 years: winter + summer)
- **Crop Area Evolution**: Line chart (4 lines: wheat, maize, cotton, rice hectares over time)
- **Water Authority Allocations**: Stacked bar (requested vs allocated per cooperative)

### Style Guide
- **Colors**: Earth tones (greens, browns, blues) + TRANSITION primary color (#3b82f6)
- **Fonts**: Inter (sans-serif), monospace for code
- **Chart Library**: Plotly with `plotly_white` theme
- **Maps**: Folium with OpenStreetMap tiles
- **Export**: All charts support PNG/PDF/HTML export

---

## 🧪 Validation Requirements

### EO Classification Validation
**Target**: >90% accuracy
**Method**:
1. Sample 500 parcels (stratified: 250 bare, 250 vegetated)
2. Ground truth: Field surveys OR high-res imagery (PlanetScope 3m, Google Earth)
3. Metrics: Confusion matrix, precision, recall, F1-score, kappa

### Rice Flood Detection Validation
**Target**: >85% precision, >85% recall
**Method**:
1. Sample 200 rice parcels
2. Ground truth: High-res optical imagery (confirm standing water visible) OR Sentinel-1 SAR (low backscatter = water)
3. Compare NDWI detections to ground truth

### Irrigation Demand Validation
**Target**: MAE <5% of annual total
**Method**:
1. Run 5-year simulation for historical period (e.g., 2015–2019)
2. Compare simulated total irrigation to water authority records (if available)
3. Calculate Mean Absolute Error: |Simulated - Observed| / Observed

### Crop Distribution Validation
**Target**: MAE <10% per crop
**Method**:
1. Compare simulated annual crop area to Hellenic Statistical Authority (ELSTAT) data
2. Per-crop MAE: |Simulated_ha - ELSTAT_ha| / ELSTAT_ha

---

## 📚 Documentation Requirements

### Mandatory Files (Create These)
1. **USER_STORIES.md** - All 17 user stories with acceptance criteria, usage examples, outputs
2. **EXAMPLE_CASES_PROMPTS.md** - Quick reference: CLI commands, natural language queries
3. **INSTRUCTIONS_IRRIGATION.md** - Step-by-step usage guide for new users
4. **config.yaml** - All configuration parameters with inline comments
5. **README.md** - Overview, installation, quick start

### Docstring Standard (Google Style)
```python
def classify_season(self, season: str, year: int, parcel_gdf: gpd.GeoDataFrame) -> Dict[int, str]:
    """
    Classify all parcels for a season using NDVI/NDWI time-series.

    This function loads Sentinel-2 imagery for the classification window (Jul-Aug for summer,
    Jan-Feb for winter), computes NDVI/NDWI for each parcel, and determines if parcels are
    bare, vegetated, or water-covered based on thresholds and temporal consistency.

    Args:
        season: Season identifier, either "summer" or "winter".
        year: Simulation year (e.g., 2023).
        parcel_gdf: GeoDataFrame with parcel geometries and parcel_id column.

    Returns:
        Dictionary mapping parcel_id to classification result:
            - "bare": NDVI < threshold in >=80% of images, NDWI low
            - "vegetated": NDVI >= threshold
            - "water": NDWI > threshold (flooded or wetland)

    Raises:
        ValueError: If season not in ["summer", "winter"].
        FileNotFoundError: If Sentinel-2 imagery not found for specified period.

    Examples:
        >>> classifier = EOClassifier(config)
        >>> parcels = gpd.read_file("parcels.shp")
        >>> results = classifier.classify_season("summer", 2023, parcels)
        >>> print(results[101])  # parcel_id=101
        'bare'

    Notes:
        - Requires cloud-free Sentinel-2 imagery (cloud cover <20% preferred).
        - Uses Scene Classification Layer (SCL) for cloud masking.
        - Temporal consistency check: parcel must be bare in >=80% of clear observations.
    """
```

---

## 🚀 Development Workflow

### Phase 1: Proof of Concept (Months 1–6)
- [ ] EO classification module (NDVI/NDWI) working for 100 parcels
- [ ] Crop assignment rules implemented (summer-to-winter, winter-to-summer)
- [ ] AquaCrop wrapper running single parcel simulation
- [ ] 1-year simulation (2 seasons) end-to-end test
- [ ] Validation: Bare soil accuracy >85% on test sample

### Phase 2: Full System (Months 7–18)
- [ ] Scale to 10,000 parcels with parallel AquaCrop
- [ ] Multi-level ABM: Farmers, Cooperatives, Water Authority
- [ ] Rice flood detection (NDWI) validated >85% precision/recall
- [ ] Web dashboard: Interactive maps, time-series charts
- [ ] 5-year simulation validated: irrigation MAE <5%

### Phase 3: Deployment (Months 19–24)
- [ ] Production deployment on cloud (AWS/Azure)
- [ ] User training: Water authority, policymakers
- [ ] Operational use: >=10 simulations/month
- [ ] User satisfaction: >=4.0/5.0
- [ ] Policy impact: >=3 decisions informed by system

---

## 🔗 Context7 MCP Usage

**ALWAYS use Context7 MCP for library documentation:**

### How to Use
1. **Resolve Library ID**: `mcp__context7__resolve-library-id` with library name
2. **Get Documentation**: `mcp__context7__get-library-docs` with resolved ID

### Key Libraries for Irrigation Use Case
- **Mesa**: `/projectmesa/mesa` - Agent-based modeling framework
- **Rasterio**: `/rasterio/rasterio` - EO raster data processing
- **xarray**: `/pydata/xarray` - NetCDF climate data handling
- **GeoPandas**: `/geopandas/geopandas` - Vector geospatial data
- **Dask**: `/dask/dask` - Parallel computing for large simulations

---

## ⚠️ Common Pitfalls to Avoid

1. **Using Dummy Data**: NEVER create synthetic EO data. Always use real Sentinel-2 imagery.
2. **Ignoring Soil Moisture Carryover**: AquaCrop re-initialization MUST transfer soil moisture from previous season.
3. **Assuming All Rice Floods**: MUST validate with NDWI. Not all assigned rice parcels are actually flooded.
4. **Missing Parameter Flow**: Ensure CLI args → query functions → simulation (test end-to-end).
5. **Hardcoding Coordinates**: Use config.yaml for all region bounds, don't hardcode lat/lon.
6. **Skipping Water Balance Validation**: Check daily Inputs = Outputs ± 1% in AquaCrop.
7. **Forgetting Cloud Masking**: Use Sentinel-2 SCL band to exclude cloudy pixels from NDVI/NDWI.
8. **Not Handling Missing Data**: If EO data gaps, use interpolation OR flag uncertainty (never fill with dummy).

---

## 📞 Questions & Support

**For Irrigation Use Case Questions:**
- Review [PRD.md](PRD.md) Section 6 (Detailed Use Case Description)
- Check [PLANNING.md](PLANNING.md) for tech stack details
- Study reference implementations: [use_cases/mlu/](../../mlu/) (4-level ABM template)

**For TRANSITION Platform Questions:**
- [../../CLAUDE.md](../../CLAUDE.md) - Parent project guidelines
- [../../ARCHITECTURE.md](../../ARCHITECTURE.md) - ML-ABM architecture
- [../../TASKS.md](../../TASKS.md) - Development tasks

**For Library Documentation:**
- Use Context7 MCP tools (resolve-library-id → get-library-docs)

---

**Last Updated:** October 2025
**Document Owner:** Irrigation Use Case Development Team
**Review Cycle:** Monthly during active development
