# Multi-Region Configuration Guide
## EO-Informed Irrigation Simulation for All European Countries

**Version:** 1.0
**Date:** October 2025
**Purpose:** Configure the irrigation simulation for ANY European agricultural region

---

## 🌍 Overview

The EO-Informed Irrigation Simulation is **region-agnostic** and can be configured for any European country or agricultural region. This guide explains how to set up the system for your specific region.

**Important**: All geographic references in PRD.md, CLAUDE.md, and PLANNING.md that mention "Thessaloniki", "Northern Greece", or specific coordinates are **EXAMPLES ONLY**. The system is fully configurable via YAML files.

---

## 📋 Quick Start

###  Step 1: Define Your Region

Edit `use_cases/irrigation/config.yaml`:

```yaml
region:
  name: "Your Region Name"
  bbox: [lon_min, lat_min, lon_max, lat_max]  # From user-drawn polygons or manual input
  climate_zone: "Mediterranean"  # Or Continental, Oceanic
  country: "Your Country"
```

### Step 2: Select Crop Calendar

Choose the appropriate crop calendar file based on your climate zone:

```yaml
# In config.yaml
crop_calendar_file: "crop_calendars/mediterranean.yaml"  # Greece, Italy, Spain
# OR
crop_calendar_file: "crop_calendars/continental.yaml"    # Poland, Germany, Czech Republic
# OR
crop_calendar_file: "crop_calendars/oceanic.yaml"        # France, UK, Ireland (create if needed)
```

### Step 3: Adjust EO Thresholds (Optional)

Most regions can use the default thresholds. If your region has unique characteristics (high altitude, arid climate), create a custom file:

```bash
cp use_cases/irrigation/eo_thresholds/default.yaml \\
   use_cases/irrigation/eo_thresholds/your_region.yaml
```

Then edit thresholds and reference in config.yaml:

```yaml
eo_thresholds_file: "eo_thresholds/your_region.yaml"
```

---

## 🗺️ Supported European Regions

### 1. Mediterranean Climate Zone

**Countries**: Greece, Southern Italy, Spain, Portugal, Southern France
**Crop Calendar**: `crop_calendars/mediterranean.yaml`
**Key Characteristics**:
- Hot, dry summers (irrigation critical)
- Mild, wet winters
- Crops: Rice, Maize, Cotton, Winter Wheat
- Growing seasons:
  - Summer: May-September
  - Winter: October-June

**Example Configurations**:

#### Thessaloniki-Pella-Imathia Plain, Greece
```yaml
region:
  name: "Thessaloniki-Pella-Imathia"
  bbox: [22.0, 40.4, 22.9, 40.9]
  climate_zone: "Mediterranean"
  country: "Greece"
crop_calendar_file: "crop_calendars/mediterranean.yaml"
```

#### Po Valley, Italy
```yaml
region:
  name: "Po Valley"
  bbox: [9.0, 44.5, 12.0, 45.5]
  climate_zone: "Mediterranean"
  country: "Italy"
crop_calendar_file: "crop_calendars/mediterranean.yaml"
```

#### Ebro Delta, Spain
```yaml
region:
  name: "Ebro Delta"
  bbox: [0.5, 40.5, 1.0, 40.8]
  climate_zone: "Mediterranean"
  country: "Spain"
crop_calendar_file: "crop_calendars/mediterranean.yaml"
```

---

### 2. Continental Climate Zone

**Countries**: Poland, Germany, Czech Republic, Austria, Hungary
**Crop Calendar**: `crop_calendars/continental.yaml`
**Key Characteristics**:
- Cold winters, warm summers
- Higher rainfall than Mediterranean (400-600mm vs 300-400mm)
- NO rice cultivation (too cold)
- Crops: Maize, Sugar Beet, Sunflower, Winter Wheat, Winter Barley, Rapeseed
- Growing seasons:
  - Summer: April-October
  - Winter: September-July

**Example Configurations**:

#### Wielkopolska Region, Poland
```yaml
region:
  name: "Wielkopolska"
  bbox: [16.0, 51.5, 18.0, 53.0]
  climate_zone: "Continental"
  country: "Poland"
crop_calendar_file: "crop_calendars/continental.yaml"
```

#### Bavarian Plains, Germany
```yaml
region:
  name: "Bavaria"
  bbox: [10.5, 48.0, 12.5, 49.0]
  climate_zone: "Continental"
  country: "Germany"
crop_calendar_file: "crop_calendars/continental.yaml"
```

---

### 3. Oceanic Climate Zone

**Countries**: France (western), UK, Ireland, Netherlands, Belgium
**Crop Calendar**: `crop_calendars/oceanic.yaml` **(to be created)**
**Key Characteristics**:
- Mild temperatures year-round
- High rainfall (600-800mm), evenly distributed
- Limited irrigation needs (mostly rainfed)
- Crops: Winter Wheat, Winter Barley, Rapeseed, Potatoes, Sugar Beet

**Example Configuration (Loire Valley, France)**:
```yaml
region:
  name: "Loire Valley"
  bbox: [-1.5, 47.0, 0.5, 48.0]
  climate_zone: "Oceanic"
  country: "France"
crop_calendar_file: "crop_calendars/oceanic.yaml"  # Create this file
```

**Note**: For oceanic regions, copy `continental.yaml` as a starting point and adjust:
- Reduce irrigation requirements (mostly rainfed)
- Adjust classification windows (earlier spring, later autumn)

---

## 📅 Creating Custom Crop Calendars

If none of the provided crop calendars match your region, create a custom one:

### Template Structure

```yaml
# Your custom crop calendar

summer_crops:
  - name: "CROP_NAME"
    description: "Crop description"
    sowing_window:
      start: 120  # Day of year (Jan 1 = 1)
      end: 150
    harvest_window:
      start: 240
      end: 270
    flooding_required: false  # true only for rice
    total_irrigation_mm: 400  # Annual irrigation water requirement
    irrigation_method: "deficit"  # Options: continuous_flooding, deficit, rainfed

winter_crops:
  # Same structure

classification_windows:
  end_of_summer:
    start: 210  # When to check for bare soil (end of summer)
    end: 240
  end_of_winter:
    start: 15   # When to check for bare soil (end of winter)
    end: 45

crop_rotation:
  summer_to_winter:
    crops:
      - name: "WINTER_WHEAT"
        probability: 0.6
      - name: "OTHER_CROP"
        probability: 0.4
  winter_to_summer:
    crops:
      - name: "MAIZE"
        probability: 0.5
      - name: "OTHER_CROP"
        probability: 0.5
```

### Key Parameters to Adjust

| Parameter | How to Determine | Example Values |
|-----------|------------------|----------------|
| **Sowing Window** | Local agricultural calendars, extension services | Mediterranean rice: 120-150 (May), Continental maize: 105-135 (Apr-May) |
| **Harvest Window** | Typical harvest dates for your region | Mediterranean wheat: 150-180 (Jun), Continental wheat: 180-210 (Jul) |
| **Irrigation Requirements** | FAO AquaCrop database, local irrigation studies | Rice: 1200mm, Maize: 250-400mm, Wheat: 50-100mm |
| **Crop Rotation Probabilities** | Regional crop statistics (Eurostat), farmer surveys | Adjust to reflect local farming practices |

---

## 🛠️ Calibrating EO Thresholds

The default EO thresholds work for most regions, but calibration improves accuracy.

### When to Calibrate

- **High-altitude regions** (Alps, Pyrenees): NDVI thresholds 0.05-0.1 lower
- **Arid regions** (Southern Spain, Sicily): Lower NDVI for water-stressed crops
- **Northern latitudes** (Scandinavia): Adjust peak growth windows (+15-30 days)

### Calibration Process

1. **Collect Ground Truth**:
   - Field visits or farmer surveys to identify known crop types
   - Minimum 30 parcels per crop type

2. **Extract NDVI/NDWI Time Series**:
   - Use Sentinel-2 data for ground-truthed parcels
   - Download full growing season (10-day composites)

3. **Analyze Thresholds**:
   - Plot NDVI distributions for bare soil vs. vegetated parcels
   - Adjust `ndvi_threshold` to minimize false positives/negatives
   - Target accuracy: >85%

4. **Update Configuration**:
   ```yaml
   # eo_thresholds/your_region.yaml
   bare_soil_detection:
     ndvi_threshold: 0.22  # Adjusted from default 0.25
   ```

### Common Adjustments

| Region Type | NDVI Threshold | NDWI Threshold | Notes |
|-------------|---------------|----------------|-------|
| **Mediterranean (standard)** | 0.25 | 0.2 | Default values work well |
| **Alpine/High-altitude** | 0.20 | 0.2 | Lower NDVI due to cooler temps |
| **Arid (Southern Spain)** | 0.20 | 0.15 | Water-stressed crops have lower NDVI |
| **Northern Europe** | 0.25 | 0.2 | Default OK, adjust peak growth windows |

---

## 🚀 Complete Setup Example: Poland (Continental)

### Step 1: Configure Region

```yaml
# use_cases/irrigation/config.yaml

region:
  name: "Wielkopolska Agricultural Region"
  bbox: [16.0, 51.5, 18.0, 53.0]  # From user-drawn polygons
  climate_zone: "Continental"
  country: "Poland"

sentinel:
  stac_url: "https://earth-search.aws.element84.com/v1"
  cloud_cover_threshold: 100.0
  indices: ["NDVI", "NDWI"]

crop_calendar_file: "crop_calendars/continental.yaml"
eo_thresholds_file: "eo_thresholds/default.yaml"

simulation:
  duration_years: 5
  n_parcels: 100
  start_year: 2021
```

### Step 2: Verify Crop Calendar

Open `use_cases/irrigation/crop_calendars/continental.yaml` and verify crops match Polish agriculture:

- ✅ Maize (50% of summer crops)
- ✅ Sugar Beet (30% of summer crops)
- ✅ Winter Wheat (50% of winter crops)
- ✅ Winter Rapeseed (20% of winter crops)

### Step 3: Run Simulation

```bash
# From TRANSITION root directory
python use_cases/irrigation/run_irrigation.py \\
  --config use_cases/irrigation/config.yaml \\
  --years 5 \\
  --parcels 100
```

### Step 4: Validate Results

- Compare simulated crop distribution with Eurostat statistics for Wielkopolska
- Validate irrigation water demand against Polish Ministry of Agriculture data
- Target accuracy: Crop distribution ±10%, water demand ±15%

---

## 📊 Data Sources for Configuration

### Crop Calendars
- **FAO Crop Calendar**: http://www.fao.org/agriculture/seed/cropcalendar
- **EU Joint Research Centre**: https://mars.jrc.ec.europa.eu/
- **National Agricultural Ministries**: Country-specific resources

### Irrigation Requirements
- **FAO AquaCrop Database**: http://www.fao.org/aquacrop/
- **EUROSTAT Agricultural Statistics**: https://ec.europa.eu/eurostat/

### EO Data
- **Copernicus Open Access Hub**: https://scihub.copernicus.eu/
- **AWS Earth Search (STAC)**: https://earth-search.aws.element84.com/v1

---

## ❓ FAQ

### Q: Can I use this for countries outside Europe?
**A**: Yes, but crop calendars and thresholds will need more extensive calibration. The system is designed for temperate/Mediterranean climates.

### Q: What if my region grows crops not in the default calendars?
**A**: Add new crop entries to your custom crop calendar YAML file with appropriate irrigation requirements from FAO AquaCrop or local studies.

### Q: How do I handle regions with multiple climate zones?
**A**: Create separate configurations for each sub-region, or use a weighted average approach for crop rotation probabilities.

### Q: Can I use this for irrigated vs. rainfed crops?
**A**: Yes. Set `total_irrigation_mm: 0` for fully rainfed crops (e.g., winter wheat in Continental Europe).

---

## 📚 Additional Resources

- **Parent Project Documentation**: See `/CLAUDE.md`, `/PRD.md`, `/PLANNING.md`
- **Agent Architecture**: See `/MULTILEVEL-ABM.md`
- **Example Simulations**: See `use_cases/irrigation/EXAMPLE_CASES_PROMPTS.md`

---

## 🤝 Contributing

To add support for a new region:

1. Create a new crop calendar YAML file in `crop_calendars/`
2. Test with at least 3 pilot regions
3. Document calibration results in this guide
4. Submit pull request with example configuration

---

**Note**: All references to "Thessaloniki", "Northern Greece", or specific Greek coordinates in other documentation files (PRD.md, CLAUDE.md, PLANNING.md) are **examples only**. Use this configuration guide as the authoritative source for setting up your region.
