# NDVI Workflow Guide - User-Driven Date Selection

## ✅ What Changed (No More Hardcoded Values!)

**Before** ❌:
- Dates were hardcoded to "last 30 days"
- User had no control over date range
- Violated "no hardcoding" principle

**After** ✅:
- NO default dates - user MUST select manually
- Clear visual feedback when dates are missing
- Button only enables when user selects dates

---

## 🎯 Complete User Workflow

### Step 1: User Draws Polygon(s)

**Single Polygon**:
```
User draws 1 polygon → bbox computed from that polygon
Example: [22.5, 40.5, 22.7, 40.7]
```

**Multiple Polygons**:
```
User draws 3 polygons → bbox computed from ALL polygons
Example:
  Polygon 1: (22.5, 40.5) to (22.6, 40.6)
  Polygon 2: (22.7, 40.7) to (22.8, 40.8)
  Polygon 3: (22.9, 40.9) to (23.0, 41.0)

  Combined bbox: [22.5, 40.5, 23.0, 41.0]  ← Covers all polygons
```

**Important**: The bbox will include areas OUTSIDE the polygons (rectangular bounds), but the final NDVI statistics are computed ONLY for the drawn polygon areas (using raster masking).

---

### Step 2: User Selects Date Range

**Required Actions**:
1. Click on "Start Date" field
2. Select a start date from calendar
3. Click on "End Date" field
4. Select an end date from calendar

**Visual Feedback**:
- Before selection: ⚠️ "Required: Select both start and end dates to enable NDVI processing" (orange)
- After selection: ✓ "Date range selected (2024-01-01 to 2024-01-31)" (green)

**Validation**:
- End date must be >= start date
- If invalid: Red error message appears

---

### Step 3: User Clicks "Get NDVI"

**Button States**:

| Condition | Button State | Visual |
|-----------|--------------|--------|
| No polygons drawn | Disabled (gray) | "📊 Get NDVI" |
| Polygons drawn, no dates | Disabled (gray) | "📊 Get NDVI" |
| Polygons drawn + dates selected | **Enabled (green)** | "📊 Get NDVI" |
| Processing in progress | Disabled with spinner | "⏳ Processing..." |

---

### Step 4: Backend Processes Request

**What Happens**:

1. **Extract bbox from ALL polygons**:
   ```python
   # From sentinel.py extract_bbox_from_geojson()
   all_coords = []
   for feature in geojson["features"]:
       geom = shape(feature["geometry"])
       all_coords.extend(geom.exterior.coords)

   bbox = [min(lons), min(lats), max(lons), max(lats)]
   ```

2. **Create temporary config.yaml**:
   ```yaml
   bbox: [22.5, 40.5, 23.0, 41.0]  # From ALL polygons
   start_date: "2024-01-01"         # User-selected
   end_date: "2024-01-31"           # User-selected
   indices: ["NDVI", "NDWI"]
   output_dir: "./ndvi_data/20241024_143022"
   ```

3. **Execute Python script**:
   ```bash
   python3 dowmload_process_sentinel2_data.py --config /tmp/temp_config_xyz.yaml
   ```

4. **Script downloads Sentinel-2 data**:
   - Queries STAC catalog for scenes covering bbox
   - Downloads scenes for date range
   - Computes NDVI: `(NIR - Red) / (NIR + Red)`
   - Saves `NDVI_20240115.tif` (example date)

5. **Backend extracts NDVI per polygon**:
   ```python
   # For EACH polygon (not just bbox):
   for feature in geojson["features"]:
       geom = shape(feature["geometry"])

       # Mask NDVI raster with polygon geometry
       masked, transform = mask(src, [geom], crop=True)

       # Compute statistics ONLY for pixels inside polygon
       ndvi_values = masked[valid_mask]

       feature["properties"]["ndvi_mean"] = float(np.mean(ndvi_values))
       feature["properties"]["ndvi_std"] = float(np.std(ndvi_values))
       # ... etc
   ```

6. **Returns enriched GeoJSON**:
   ```json
   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "geometry": {...},
         "properties": {
           "ndvi_mean": 0.65,
           "ndvi_std": 0.12,
           "ndvi_min": 0.35,
           "ndvi_max": 0.85,
           "ndvi_count": 1250
         }
       },
       {
         "type": "Feature",
         "geometry": {...},
         "properties": {
           "ndvi_mean": 0.72,
           "ndvi_std": 0.09,
           "ndvi_min": 0.45,
           "ndvi_max": 0.88,
           "ndvi_count": 980
         }
       }
     ]
   }
   ```

---

## 🎨 User Interface Flow

```
┌─────────────────────────────────────────────────┐
│  Map Component                                  │
│                                                 │
│  [Draw polygon(s) on map]                       │
│                                                 │
│  ✓ 3 polygons selected                          │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  📅 Date Range (Sentinel-2 Data)                │
│                                                 │
│  📅 Select date range                           │
│                                                 │
│  Start Date: [  2024-01-01  ]  ← User clicks    │
│  End Date:   [  2024-01-31  ]  ← User clicks    │
│                                                 │
│  ✓ Date range selected (2024-01-01 to 2024-... │
└─────────────────────────────────────────────────┘

┌───────────┬────────────┬──────────────┬──────────┐
│ Clear Last│ Clear All  │ Copy GeoJSON │ 📊 Get   │
│           │            │              │   NDVI   │
└───────────┴────────────┴──────────────┴──────────┘
                                         ↑
                                    Enabled (green)
                                    when polygons + dates
```

---

## 🔄 Integration with Other Queries (CCA, MLU, GCP)

**Key Concept**:
- **Polygon selection** is universal → works for ALL queries (CCA, MLU, GCP)
- **Date selection + Get NDVI** is OPTIONAL → only if user wants NDVI values

### Workflow Options

#### Option A: Use Polygons Without NDVI
```
1. User draws polygon(s)
2. User runs CCA/MLU/GCP query
3. Query uses polygon bbox for spatial filtering
4. No NDVI data used (standard workflow)
```

#### Option B: Use Polygons WITH NDVI
```
1. User draws polygon(s)
2. User selects date range
3. User clicks "Get NDVI"
4. Backend computes NDVI → enriches polygons
5. User runs CCA/MLU/GCP query
6. Query uses polygon bbox + NDVI values
7. Agents can use NDVI for bare soil detection, crop classification, etc.
```

### Example: MLU with NDVI

**Without NDVI** (current):
```python
# LandParcelAgent decides crop based on LUSA scores only
best_crop = self._evaluate_agriculture(year)
```

**With NDVI** (enhanced):
```python
# LandParcelAgent uses NDVI to detect bare soil first
if self.ndvi_value < 0.25:  # Bare soil detected
    self.is_bare_soil = True
    # Assign crop based on seasonal rotation rules
    best_crop = self.assign_crop_from_rotation_rules(season)
else:
    # Continue with current crop (vegetation detected)
    best_crop = self.current_crop
```

---

## 📊 NDVI Statistics Explained

For each polygon, the backend returns:

| Metric | Description | Typical Range | Interpretation |
|--------|-------------|---------------|----------------|
| `ndvi_mean` | Average NDVI | -1 to +1 | Overall vegetation health |
| `ndvi_std` | Standard deviation | 0 to 1 | Spatial variability (uniformity) |
| `ndvi_min` | Minimum NDVI | -1 to +1 | Least vegetated area |
| `ndvi_max` | Maximum NDVI | -1 to +1 | Most vegetated area |
| `ndvi_count` | Number of pixels | Integer | Spatial coverage |

**NDVI Ranges**:
- **-1 to 0**: Water, bare soil, urban
- **0 to 0.2**: Sparse vegetation, bare soil
- **0.2 to 0.4**: Grassland, crops (early growth)
- **0.4 to 0.6**: Crops (vegetative stage)
- **0.6 to 0.8**: Dense crops, forests
- **0.8 to 1**: Very dense vegetation

---

## 🚨 Important Notes

### 1. NO Hardcoded Values
- ❌ NO default dates (removed "last 30 days")
- ❌ NO default bbox (derived from user polygons)
- ❌ NO default indices (user can specify in API request)
- ✅ User controls EVERYTHING

### 2. Multiple Polygons Handling
- Bbox computed from ALL polygons (rectangular bounds)
- Sentinel-2 download covers entire bbox (may include areas outside polygons)
- NDVI statistics computed ONLY for areas inside each polygon (raster masking)
- Result: Efficient download + precise statistics

### 3. Date Range Guidelines
- **Minimum**: 1 day (single Sentinel-2 pass)
- **Recommended**: 10-30 days (multiple passes, cloud filtering)
- **Maximum**: No limit (but processing time increases)
- **Sentinel-2 availability**: Data from 2015 onwards

### 4. Processing Time
- **Small area (< 10km²), 1 month**: ~2-5 minutes
- **Medium area (10-100km²), 1 month**: ~5-10 minutes
- **Large area (> 100km²), 1 month**: May timeout (>10 minutes)

---

## ✅ Summary

**User Workflow**:
1. ✅ Draw polygon(s) → bbox computed from ALL
2. ✅ Select date range → NO defaults, user MUST choose
3. ✅ Click "Get NDVI" → button only enabled when both above complete
4. ✅ Backend downloads Sentinel-2 → processes NDVI
5. ✅ Returns enriched GeoJSON → NDVI stats per polygon
6. ✅ Use polygons with/without NDVI for CCA/MLU/GCP queries

**Key Principles**:
- 🚫 NO hardcoded values anywhere
- ✅ User controls dates, polygons, and when to fetch NDVI
- ✅ Multiple polygons supported (bbox from all)
- ✅ NDVI computed only for drawn polygon areas (not entire bbox)
