# IRR-US-01: Paper Methodology Implementation

## Overview

IRR-US-01 implements the **NDVI/NDWI multi-index classification methodology** described in the TRANSITION project paper for automated bare soil detection using Sentinel-2 imagery.

## Paper Requirements

The paper specifies a multi-step classification approach:

1. **NDVI Thresholding for Vegetation Absence**
   - NDVI < 0.2–0.3 indicates bare soil or fallow land
   - Parcels with consistently low NDVI are classified as having little to no green vegetation

2. **NDWI for Surface Water Check**
   - NDWI is used to distinguish bare dry soil from water-covered areas
   - NDWI > 0 indicates flooding or paddy water
   - NDWI ≤ 0 indicates dry bare soil

3. **Time-Series and Phenology Context** (Implemented - IRR-US-01)
   - Temporal pattern analysis to distinguish harvested fields from fallow
   - Track NDVI/NDWI evolution throughout the season
   - Improves robustness by analyzing phenology metrics (max NDVI, senescence rate)

## Implementation Status

### ✅ Implemented Features

#### 1. Dual-Index Classification
- **NDVI download and extraction** (Sentinel-2 vegetation index)
- **NDWI download and extraction** (Normalized Difference Water Index)
- Both indices extracted per parcel using 50m buffer (point mode) or full polygon geometry

#### 2. Three-Class Classification System
| Class | Criteria | Description |
|-------|----------|-------------|
| **Vegetated** | NDVI ≥ 0.25 | Crops present, active vegetation |
| **Bare Soil** | NDVI < 0.25 AND NDWI ≤ 0 | Dry bare soil (fallow, harvested, uncultivated) |
| **Flooded** | NDVI < 0.25 AND NDWI > 0 | Water surface (flooded fields, paddy, wetland) |

#### 3. Thresholds (from paper)
- **NDVI Threshold**: 0.25 (within paper's recommended range of 0.2-0.3)
- **NDWI Threshold**: 0.0 (paper specifies NDWI > 0 for water presence)

#### 4. Cloud Gap Handling
- Temporal compositing using max/median/mean reduction
- Multi-date composites (user-specified date range: start_date → end_date)
- SCL (Scene Classification Layer) cloud masking
- Automatic retry with reduced cloud cover threshold

#### 5. Standardized Outputs
- **GeoJSON**: Classification results with geometry (for GIS integration)
- **Text Report**: Detailed parcel-by-parcel classification with statistics
- **Visualizations**:
  - Pie chart: Class distribution
  - Histogram: NDVI distribution with threshold line
  - Interactive map: Folium map with color-coded parcels (green/brown/blue)

#### 6. Time-Series Phenology Analysis (Implemented - IRR-US-01)
**Robustness Enhancement** - Improves classification accuracy by leveraging temporal patterns

- **Multi-Date NDVI/NDWI Loading**: System processes NDVI/NDWI time-series for entire season (e.g., May–September: 10+ images)
- **Phenology Metrics Computed per Parcel**:
  - Max NDVI during season (peak greenness)
  - Date of max NDVI (timing of peak)
  - NDVI at season start and end
  - Rate of NDVI decline (senescence slope)
  - NDWI temporal evolution (for flooding detection)

- **Temporal Pattern Classification**:
  - **Harvested Crop**: max NDVI > 0.6, end NDVI < 0.2 (NDVI drop indicates harvest)
  - **Truly Fallow**: max NDVI < 0.3 all season (consistently low vegetation)
  - **Irrigated/Flooded**: NDWI > 0 sustained for ≥7 days (indicates flooding events)

- **Benefits**:
  - Reduces false positives (fields classified as bare when actually harvested)
  - Distinguishes harvested fields from long-term fallow
  - Improves rice flood detection accuracy (IRR-US-03)

- **Implementation**: Integrated into IRR-US-01 as core feature (not separate query)
  - Cloud gap handling via temporal compositing
  - Seasonal time windows (configurable: e.g., May–Sep for summer, Nov–Feb for winter)
  - **CLI flag**: `--enable-phenology` activates temporal analysis mode
  - **Module structure**: Modular OOP design (metrics.py, classifier.py, downloader.py, visualizer.py)
  - **Output**: Time-series charts, pattern distribution, phenology metrics per parcel

### ⏳ Future Enhancements (from paper)

#### Advanced Phenology Features
**Planned for Phase 2** - Additional temporal analysis capabilities

- **Sub-seasonal Dynamics**: Weekly NDVI/NDWI tracking for crop growth stage identification
- **Anomaly Detection**: Flag parcels with unusual phenology patterns (e.g., sudden NDVI drop mid-season = crop failure)
- **Machine Learning Integration**: Replace rule-based phenology classification with CNN/LSTM models trained on historical data
- **Cross-Sensor Validation**: Integrate Sentinel-1 SAR for all-weather monitoring (cloud-independent)

## Usage

### Basic Classification (Single-Date Mode)

```bash
# CLI (standard mode)
python use_cases/irrigation/run_irrigation.py \
  --query irr_01 \
  --geojson-file my_field.geojson \
  --start-date 2024-06-01 \
  --end-date 2024-06-30 \
  --parcels 20

# Natural language (via LLM)
python llm_interface/transition_agent.py "Classify bare soil for 20 parcels from 2024-06-01 to 2024-06-30"
```

### Temporal Phenology Analysis (Time-Series Mode) ✅ NEW

```bash
# CLI (phenology mode)
python use_cases/irrigation/run_irrigation.py \
  --query irr_01 \
  --geojson-file my_field.geojson \
  --start-date 2024-05-01 \
  --end-date 2024-09-30 \
  --parcels 10 \
  --enable-phenology \
  --temporal-window-days 10

# Natural language (via LLM) - coming soon
python llm_interface/transition_agent.py "Analyze temporal phenology for wheat from 2024-05-01 to 2024-09-30"
```

### User-Specified Coordinates

```bash
python use_cases/irrigation/run_irrigation.py \
  --query irr_01 \
  --parcel-locations '[{"lat":40.6,"lon":22.8}]' \
  --start-date 2024-06-01 \
  --end-date 2024-06-30
```

### Full Polygon Analysis

```bash
python use_cases/irrigation/run_irrigation.py \
  --query irr_01 \
  --geojson-file my_fields.geojson \
  --use-polygons \
  --start-date 2024-06-01 \
  --end-date 2024-06-30
```

## Classification Algorithm

```python
for each parcel:
    if NDVI >= 0.25:
        classification = 'vegetated'  # Crops present
    elif NDVI < 0.25:
        if NDWI > 0:
            classification = 'flooded'  # Water surface
        else:
            classification = 'bare_soil'  # Dry bare soil
```

## Validation

### User Story KPI
> Achieve a bare soil detection accuracy >90%, i.e. correctly identify at least 90% of truly uncultivated parcels in each season.

**Validation Method** (not yet implemented):
- Compare against ground truth data (farmer reports, field surveys)
- Calculate precision/recall for bare soil class
- Assess confusion between flooded and bare soil classes

## Technical Details

### Data Sources
- **Sentinel-2**: Level-2A surface reflectance (STAC API)
- **Indices**: NDVI (Band 8 - Band 4), NDWI (Band 3 - Band 8)
- **Cloud Masking**: SCL layer (Scene Classification Layer)

### Processing Pipeline
1. **Download**: On-demand Sentinel-2 download via STAC
2. **Composite**: Temporal reduction (max/median/mean)
3. **Extract**: Rasterio mask extraction per parcel
4. **Classify**: NDVI/NDWI thresholds applied
5. **Visualize**: Plotly charts + Folium interactive maps

### Performance
- **Cache**: 24-hour NDVI/NDWI cache (reuses data for same bbox+dates)
- **Parallel**: Independent parcels processed in single raster read
- **Speed**: ~2-5 seconds per parcel (including download)

## References

- **Paper Section**: "Automated EO Classification" (Section X.X in D2.3)
- **NDVI**: Normalized Difference Vegetation Index [2]
- **NDWI**: Normalized Difference Water Index [3]
- **Sentinel-2**: Copernicus STAC catalog

## Change Log

### 2025-10-24: Full Paper Methodology Implementation
- ✅ Added NDWI download and extraction
- ✅ Implemented 3-class system (vegetated, bare_soil, flooded)
- ✅ Updated visualizations for all classes
- ✅ Enhanced reports with NDVI/NDWI statistics
- ✅ Added paper methodology documentation

### Original Implementation
- ✅ NDVI-only classification (2-class: bare_soil, vegetated)
- ✅ Basic visualization and reporting
- ✅ Cloud gap handling via compositing
