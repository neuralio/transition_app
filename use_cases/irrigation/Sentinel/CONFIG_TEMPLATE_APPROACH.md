# Configuration Template Approach

## Overview

The Sentinel-2 processing uses a **template-based configuration** pattern where `config_modular.yaml` serves as a single source of truth with placeholders filled from user interactions.

## Benefits

1. **Single Source of Truth** - All settings (cloud threshold, STAC URL, output format) in one file
2. **Easy Maintenance** - Update processing parameters without touching backend code
3. **User-Driven** - Bbox and dates filled dynamically from UI
4. **No Hardcoding** - Template approach prevents configuration drift

## How It Works

### 1. Template Config ([config_modular.yaml](config_modular.yaml))

```yaml
# Spatial parameters (filled from user-drawn polygons)
bbox: {{BBOX_PLACEHOLDER}}  # Will be replaced with [lon_min, lat_min, lon_max, lat_max] from UI

# Temporal parameters (filled from calendar selection)
start_date: "{{START_DATE_PLACEHOLDER}}"  # User-selected start date (YYYY-MM-DD)
end_date: "{{END_DATE_PLACEHOLDER}}"      # User-selected end date (YYYY-MM-DD)

# Static configuration (maintained by developers)
cloud_cover_threshold: 100.0
stac_url: "https://earth-search.aws.element84.com/v1"
indices_to_calculate: ["NDVI", "NDWI"]
# ... other settings
```

### 2. Backend Processing ([backend/api/routes/sentinel.py](../../../backend/api/routes/sentinel.py))

```python
# Load template
template_config_path = project_root / "use_cases/irrigation/Sentinel/config_modular.yaml"
with open(template_config_path, 'r') as f:
    config_template = f.read()

# Fill placeholders from user input
config_filled = config_template.replace(
    '{{BBOX_PLACEHOLDER}}', str(bbox)  # [22.583, 40.724, 22.742, 40.796]
).replace(
    '{{START_DATE_PLACEHOLDER}}', request.start_date  # "2025-10-19"
).replace(
    '{{END_DATE_PLACEHOLDER}}', request.end_date  # "2025-10-20"
)

# Write to temp file for subprocess
with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
    f.write(config_filled)
    config_path = f.name
```

### 3. Data Flow

```
User Draws Polygon → Frontend Extracts GeoJSON → Backend Extracts Bbox
                                                          ↓
User Selects Dates → Frontend Sends to API → Backend Fills Template
                                                          ↓
                                              Temp Config with User Values
                                                          ↓
                                       dowmload_process_sentinel2_data.py
                                                          ↓
                                         Raw NDVI/NDWI Rasters Saved
```

## Example Filled Config

**User draws polygon in Thessaloniki and selects Oct 19-20, 2025:**

```yaml
bbox: [22.58315323053064, 40.72426941012475, 22.741705905875463, 40.79613759875096]
start_date: "2025-10-19"
end_date: "2025-10-20"
cloud_cover_threshold: 100.0  # From template (unchanged)
stac_url: "https://earth-search.aws.element84.com/v1"  # From template
indices_to_calculate: ["NDVI", "NDWI"]  # From template
```

## Why Not Hardcode?

❌ **BAD (Old Approach):**
```python
config = {
    "bbox": [22.0, 40.65, 22.4, 40.9],  # Hardcoded Greece bounds
    "start_date": "2025-10-19",  # Hardcoded date
    "cloud_cover_threshold": 100.0  # Hardcoded in Python
}
```

✅ **GOOD (Template Approach):**
```yaml
# config_modular.yaml - ONE place to update
bbox: {{BBOX_PLACEHOLDER}}  # Filled from user polygon
start_date: "{{START_DATE_PLACEHOLDER}}"  # Filled from calendar
cloud_cover_threshold: 100.0  # Easy to change in YAML
```

## Placeholder Conventions

- **Format**: `{{PARAMETER_NAME_PLACEHOLDER}}`
- **Case**: UPPERCASE with underscores
- **Suffix**: Always end with `_PLACEHOLDER` for clarity

### Current Placeholders

| Placeholder | Type | Filled From | Example |
|-------------|------|-------------|---------|
| `{{BBOX_PLACEHOLDER}}` | List[float] | User-drawn polygons | `[22.583, 40.724, 22.742, 40.796]` |
| `{{START_DATE_PLACEHOLDER}}` | String | Calendar date picker | `"2025-10-19"` |
| `{{END_DATE_PLACEHOLDER}}` | String | Calendar date picker | `"2025-10-20"` |

## Future Extensions

If you need to make more parameters user-configurable:

1. Add placeholder to `config_modular.yaml`:
   ```yaml
   max_scenes: {{MAX_SCENES_PLACEHOLDER}}  # Default 0 = all scenes
   ```

2. Add UI control in frontend (e.g., number input)

3. Add replacement in `backend/api/routes/sentinel.py`:
   ```python
   config_filled = config_template.replace(
       '{{MAX_SCENES_PLACEHOLDER}}', str(request.max_scenes)
   )
   ```

## Benefits Summary

✅ **Maintainability** - Change cloud threshold once in YAML, not in Python
✅ **Flexibility** - Add new placeholders without backend refactoring
✅ **Transparency** - Developers see full config structure in one file
✅ **User-Driven** - Spatial/temporal parameters come from UI
✅ **No Code Drift** - Template ensures consistency across all requests

---

**Last Updated**: 2025-10-24
**Related Files**:
- [config_modular.yaml](config_modular.yaml) - Template configuration
- [backend/api/routes/sentinel.py](../../../backend/api/routes/sentinel.py) - Placeholder filling logic
- [frontend/components/app-sidebar.tsx](../../../frontend/components/app-sidebar.tsx) - User interaction handlers
