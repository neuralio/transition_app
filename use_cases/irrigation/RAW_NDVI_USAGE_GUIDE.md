# Raw NDVI Values Usage Guide

## ✅ What Changed - RAW Values Instead of Statistics!

### Before ❌ (WRONG - Statistics)
```json
{
  "geojson": {
    "features": [{
      "properties": {
        "ndvi_mean": 0.65,    ← Statistics (averaged)
        "ndvi_std": 0.12,
        "ndvi_min": 0.35,
        "ndvi_max": 0.85
      }
    }]
  }
}
```

### After ✅ (CORRECT - Raw Raster)
```json
{
  "geojson": {...},
  "ndvi_raster_path": "/path/to/NDVI_20241024.tif",  ← RAW values (-1 to 1)
  "ndwi_raster_path": "/path/to/NDWI_20241024.tif",  ← RAW values
  "output_dir": "./ndvi_data/20241024_143022"
}
```

---

## 🎯 Why Raw Values?

According to **EO_Irrigation.pdf**:

> **Bare Soil Detection**: NDVI < 0.2–0.3
> **Rice Flood Detection**: NDWI > 0.2

You need the **actual pixel values** to apply these thresholds, NOT averaged statistics!

**Example**:
- Parcel has 1000 pixels
- 800 pixels: NDVI = 0.65 (vegetation)
- 200 pixels: NDVI = 0.15 (bare soil)
- **Statistics would show**: ndvi_mean = 0.55 ❌ (masks the bare soil!)
- **Raw values show**: 20% bare soil pixels detected ✅

---

## 📊 NDVI Raster File Format

### File Structure
```
ndvi_data/
└── 20241024_143022/
    ├── NDVI_20241024.tif    ← GeoTIFF raster with raw NDVI values
    ├── NDWI_20241024.tif    ← GeoTIFF raster with raw NDWI values
    └── RGB_20241024.tif      ← Optional RGB composite
```

### Raster Properties
| Property | Value |
|----------|-------|
| **Format** | GeoTIFF (.tif) |
| **Data Type** | Float32 |
| **Value Range** | -1.0 to +1.0 |
| **CRS** | EPSG:4326 (WGS84) |
| **NoData** | Typically -9999 or NaN |

### NDVI Value Interpretation
| Range | Meaning | Use Case |
|-------|---------|----------|
| **-1 to 0** | Water, bare soil, urban | Identify non-vegetated areas |
| **0 to 0.2** | Sparse vegetation, bare soil | **Bare soil detection threshold** |
| **0.2 to 0.4** | Grassland, early crop growth | Crop emergence |
| **0.4 to 0.6** | Active vegetation, crops | Vegetative stage |
| **0.6 to 0.8** | Dense crops, forests | Peak growth |
| **0.8 to 1** | Very dense vegetation | Mature crops/forests |

### NDWI Value Interpretation
| Range | Meaning | Use Case |
|-------|---------|----------|
| **< 0** | Dry soil, vegetation | No water detected |
| **0 to 0.2** | Moist soil | Irrigated fields |
| **> 0.2** | Standing water | **Rice flood detection threshold** |
| **> 0.3** | Open water | Lakes, rivers, flooded paddies |

---

## 🐍 How to Use Raw NDVI Raster in Python

### Example 1: Bare Soil Detection (NDVI < 0.25)

```python
import rasterio
from shapely.geometry import shape
from rasterio.mask import mask
import numpy as np

# Response from API
ndvi_raster_path = "/path/to/NDVI_20241024.tif"
polygon_geojson = {...}  # Your drawn polygon

# Open NDVI raster
with rasterio.open(ndvi_raster_path) as src:
    # Extract polygon geometry
    geom = shape(polygon_geojson["geometry"])

    # Mask raster with polygon
    ndvi_masked, transform = mask(src, [geom], crop=True)

    # Get valid NDVI values (exclude nodata)
    ndvi_values = ndvi_masked[0]  # First band
    valid_mask = (ndvi_values != src.nodata) & np.isfinite(ndvi_values)
    valid_ndvi = ndvi_values[valid_mask]

    # Apply bare soil threshold (NDVI < 0.25)
    bare_soil_threshold = 0.25
    bare_soil_pixels = valid_ndvi < bare_soil_threshold

    # Calculate bare soil percentage
    bare_soil_pct = (bare_soil_pixels.sum() / len(valid_ndvi)) * 100

    print(f"Bare soil detected: {bare_soil_pct:.1f}% of parcel")

    # Decision logic
    if bare_soil_pct > 80:
        print("→ Parcel is BARE - assign new crop")
        # Trigger crop rotation logic
    else:
        print("→ Parcel has vegetation - continue current crop")
```

### Example 2: Rice Flood Detection (NDWI > 0.2)

```python
import rasterio
from shapely.geometry import shape
from rasterio.mask import mask
import numpy as np

# Response from API
ndwi_raster_path = "/path/to/NDWI_20241024.tif"
rice_parcel_geojson = {...}  # Parcel assigned to rice

# Open NDWI raster
with rasterio.open(ndwi_raster_path) as src:
    geom = shape(rice_parcel_geojson["geometry"])

    # Mask raster with polygon
    ndwi_masked, transform = mask(src, [geom], crop=True)

    # Get valid NDWI values
    ndwi_values = ndwi_masked[0]
    valid_mask = (ndwi_values != src.nodata) & np.isfinite(ndwi_values)
    valid_ndwi = ndwi_values[valid_mask]

    # Apply flood detection threshold (NDWI > 0.2)
    flood_threshold = 0.2
    flooded_pixels = valid_ndwi > flood_threshold

    # Calculate flooded area percentage
    flooded_pct = (flooded_pixels.sum() / len(valid_ndwi)) * 100

    print(f"Flooded area: {flooded_pct:.1f}% of rice parcel")

    # Decision logic
    if flooded_pct > 60:
        print("→ Rice flooding CONFIRMED - use flooded rice AquaCrop")
        is_flooded = True
    else:
        print("→ Rice NOT flooded - reassign to alternate crop")
        is_flooded = False
        # Reassign to MAIZE or COTTON
```

---

## 🔧 Integration with Irrigation Agents

### LandParcelAgentIrrigation

Update the agent to use raw NDVI values:

```python
# In land_parcel_agent_irrigation.py

def detect_bare_soil_from_ndvi_raster(self, ndvi_raster_path, polygon_geojson):
    """
    Detect bare soil using raw NDVI raster values.

    Args:
        ndvi_raster_path: Path to NDVI GeoTIFF
        polygon_geojson: GeoJSON of this parcel's geometry

    Returns:
        bool: True if bare soil detected (NDVI < threshold)
    """
    import rasterio
    from rasterio.mask import mask
    from shapely.geometry import shape
    import numpy as np

    threshold = self.eo_thresholds['bare_soil_detection']['ndvi_threshold']  # 0.25
    confidence = self.eo_thresholds['bare_soil_detection']['confidence_level']  # 0.8

    with rasterio.open(ndvi_raster_path) as src:
        geom = shape(polygon_geojson)

        # Extract NDVI for this parcel
        ndvi_masked, _ = mask(src, [geom], crop=True)
        ndvi_values = ndvi_masked[0]
        valid_mask = (ndvi_values != src.nodata) & np.isfinite(ndvi_values)
        valid_ndvi = ndvi_values[valid_mask]

        if len(valid_ndvi) == 0:
            return False  # No data

        # Count pixels below threshold
        bare_pixels = valid_ndvi < threshold
        bare_pct = bare_pixels.sum() / len(valid_ndvi)

        # Require confidence_level percentage of pixels below threshold
        self.is_bare_soil = bare_pct >= confidence

        # Store actual NDVI mean for reference
        self.ndvi_value = float(np.mean(valid_ndvi))

        return self.is_bare_soil


def detect_rice_flooding_from_ndwi_raster(self, ndwi_raster_path, polygon_geojson):
    """
    Detect rice flooding using raw NDWI raster values.

    Args:
        ndwi_raster_path: Path to NDWI GeoTIFF
        polygon_geojson: GeoJSON of this parcel's geometry

    Returns:
        bool: True if flooding detected (NDWI > 0.2)
    """
    import rasterio
    from rasterio.mask import mask
    from shapely.geometry import shape
    import numpy as np

    if self.current_crop != "RICE":
        return False

    threshold = self.eo_thresholds['rice_flood_detection']['ndwi_threshold']  # 0.2
    min_flooded_pct = self.eo_thresholds['rice_flood_detection']['min_flooded_area_pct']  # 60%

    with rasterio.open(ndwi_raster_path) as src:
        geom = shape(polygon_geojson)

        # Extract NDWI for this parcel
        ndwi_masked, _ = mask(src, [geom], crop=True)
        ndwi_values = ndwi_masked[0]
        valid_mask = (ndwi_values != src.nodata) & np.isfinite(ndwi_values)
        valid_ndwi = ndwi_values[valid_mask]

        if len(valid_ndwi) == 0:
            return False

        # Count flooded pixels (NDWI > threshold)
        flooded_pixels = valid_ndwi > threshold
        flooded_pct = (flooded_pixels.sum() / len(valid_ndwi)) * 100

        # Require min_flooded_area_pct of parcel to be flooded
        self.is_flooded = flooded_pct >= min_flooded_pct

        # Store actual NDWI mean for reference
        self.ndwi_value = float(np.mean(valid_ndwi))

        return self.is_flooded
```

---

## 📋 API Response Example

```json
{
  "success": true,
  "geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Polygon",
          "coordinates": [[[22.5, 40.5], [22.6, 40.5], [22.6, 40.6], [22.5, 40.6], [22.5, 40.5]]]
        },
        "properties": {}
      }
    ]
  },
  "output_dir": "./ndvi_data/20241024_143022",
  "ndvi_raster_path": "./ndvi_data/20241024_143022/NDVI_20241024.tif",
  "ndwi_raster_path": "./ndvi_data/20241024_143022/NDWI_20241024.tif",
  "message": "Successfully computed NDVI, NDWI. Use raw raster files for thresholding."
}
```

---

## ✅ Summary

**What You Get**:
- ✅ Path to raw NDVI raster file (GeoTIFF)
- ✅ Path to raw NDWI raster file (GeoTIFF)
- ✅ Values range from -1 to +1 (NOT statistics!)
- ✅ Can apply thresholds pixel-by-pixel

**How to Use**:
1. API returns `ndvi_raster_path` and `ndwi_raster_path`
2. Open raster with `rasterio`
3. Mask raster with polygon geometry
4. Apply thresholds:
   - `NDVI < 0.25` → Bare soil detection
   - `NDWI > 0.2` → Rice flood detection
5. Make crop assignment decisions based on pixel percentages

**NO MORE STATISTICS** - Use the raw values as specified in EO_Irrigation.pdf! ✅
