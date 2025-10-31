# Example: Irrigation Query with On-Demand NDVI Download

## Overview

This example shows how to run an irrigation query that automatically downloads NDVI data on-demand.

**Key Features:**
- ✅ NDVI downloaded automatically when needed
- ✅ Data saved to temporary directory
- ✅ Automatic cleanup after query completes
- ✅ Alert shown if no satellite data available
- ✅ Full terminal logging for debugging

## Python Example

```python
import tempfile
import shutil
from pathlib import Path
from backend.api.routes.ndvi_ondemand import download_ndvi_for_query

def run_irrigation_query(geojson: dict, start_date: str, end_date: str):
    """
    Run irrigation ABM simulation with automatic NDVI download.

    Args:
        geojson: User-drawn polygons
        start_date: Start date for NDVI data (YYYY-MM-DD)
        end_date: End date for NDVI data (YYYY-MM-DD)
    """
    print(f"🌾 Starting irrigation query: {start_date} to {end_date}")

    try:
        # Download NDVI on-demand
        print("📡 Downloading Sentinel-2 NDVI data...")
        ndvi_path, ndwi_path, message, scenes_found = download_ndvi_for_query(
            geojson=geojson,
            start_date=start_date,
            end_date=end_date
        )

        # Check if data is available
        if not ndvi_path:
            print(f"⚠️  {message}")
            return {
                "success": False,
                "message": message,
                "scenes_found": scenes_found
            }

        print(f"✅ {message}")
        print(f"📊 NDVI raster: {ndvi_path}")
        print(f"📊 NDWI raster: {ndwi_path}")

        # Initialize irrigation agents with NDVI data
        print("🚜 Initializing irrigation agents...")
        agents = create_irrigation_agents(
            geojson=geojson,
            ndvi_raster_path=ndvi_path,
            ndwi_raster_path=ndwi_path
        )

        # Run ABM simulation
        print("⚙️  Running ABM simulation...")
        results = run_irrigation_simulation(agents, n_years=5)

        print("✅ Simulation complete!")

        return {
            "success": True,
            "message": "Irrigation simulation completed successfully",
            "results": results,
            "scenes_found": scenes_found
        }

    finally:
        # Cleanup temporary NDVI files
        if ndvi_path:
            temp_dir = Path(ndvi_path).parent.parent.parent
            if temp_dir.exists() and "ndvi_temp_" in str(temp_dir):
                print(f"🗑️  Cleaning up temporary NDVI data: {temp_dir}")
                shutil.rmtree(temp_dir)


def create_irrigation_agents(geojson, ndvi_raster_path, ndwi_raster_path):
    """Create irrigation agents with NDVI data."""
    from use_cases.irrigation.agents.land_parcel_agent_irrigation import LandParcelAgentIrrigation

    agents = []

    # Extract parcels from polygons
    for feature in geojson['features']:
        # Create agent for each parcel
        agent = LandParcelAgentIrrigation(
            model=None,  # Set actual model
            lat=40.5,    # Extract from polygon
            lon=22.7,    # Extract from polygon
            ndvi_raster_path=ndvi_raster_path
        )
        agents.append(agent)

    return agents


def run_irrigation_simulation(agents, n_years=5):
    """Run irrigation ABM simulation."""
    # Placeholder - implement actual simulation logic
    results = {
        "n_agents": len(agents),
        "n_years": n_years,
        "water_demand": 1000.0,  # Example metric
        "crop_yield": 5000.0     # Example metric
    }
    return results


# Example usage
if __name__ == "__main__":
    # Example GeoJSON from user
    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [22.6, 40.7],
                    [22.7, 40.7],
                    [22.7, 40.8],
                    [22.6, 40.8],
                    [22.6, 40.7]
                ]]
            },
            "properties": {}
        }]
    }

    # Run query with date range
    results = run_irrigation_query(
        geojson=geojson,
        start_date="2025-10-12",
        end_date="2025-10-14"
    )

    print(results)
```

## Expected Output

### Success Case (Data Available):
```
🌾 Starting irrigation query: 2025-10-12 to 2025-10-14
📡 Downloading Sentinel-2 NDVI data...
📁 Using temporary directory: /tmp/ndvi_temp_abc123
⚙️ Created config from template: use_cases/irrigation/Sentinel/config_modular.yaml
================================================================================
📄 FILLED CONFIG CONTENT (sent to download script):
================================================================================
bbox: [22.6, 40.7, 22.7, 40.8]
start_date: "2025-10-12"
end_date: "2025-10-14"
...
================================================================================
🚀 Executing Sentinel-2 download script...
✅ Download completed successfully
📡 Script found 1 Sentinel-2 scenes
📊 Found 1 NDVI raster(s)
📊 NDVI raster: /tmp/ndvi_temp_abc123/products/ndvi/daily/NDVI_20251012.tif
📊 NDWI raster: /tmp/ndvi_temp_abc123/products/ndwi/daily/NDWI_20251012.tif
✅ Successfully processed 1 Sentinel-2 scene(s).
🚜 Initializing irrigation agents...
⚙️  Running ABM simulation...
✅ Simulation complete!
🗑️  Cleaning up temporary NDVI data: /tmp/ndvi_temp_abc123
```

### Failure Case (No Data Available):
```
🌾 Starting irrigation query: 2025-10-20 to 2025-10-21
📡 Downloading Sentinel-2 NDVI data...
📁 Using temporary directory: /tmp/ndvi_temp_xyz789
...
📡 Script found 0 Sentinel-2 scenes
⚠️ No Sentinel-2 scenes available for 2025-10-20 to 2025-10-21
   Sentinel-2 revisit time: 2-5 days. Try extending date range.
⚠️  No satellite data available for 2025-10-20 to 2025-10-21. Sentinel-2 revisit time is 2-5 days. Try selecting a wider date range (e.g., 7-10 days).
🗑️  Cleaning up temporary NDVI data: /tmp/ndvi_temp_xyz789

{'success': False, 'message': 'No satellite data available...', 'scenes_found': 0}
```

## Integration with FastAPI

```python
# backend/api/routes/irrigation.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.api.routes.ndvi_ondemand import download_ndvi_for_query
import tempfile
import shutil

router = APIRouter(prefix="/api/irrigation", tags=["irrigation"])

class IrrigationQueryRequest(BaseModel):
    geojson: dict
    start_date: str
    end_date: str
    n_years: int = 5

@router.post("/simulate")
async def simulate_irrigation(request: IrrigationQueryRequest):
    """Run irrigation simulation with automatic NDVI download."""

    try:
        # Download NDVI on-demand
        ndvi_path, ndwi_path, message, scenes_found = download_ndvi_for_query(
            geojson=request.geojson,
            start_date=request.start_date,
            end_date=request.end_date
        )

        if not ndvi_path:
            # No data available - return alert
            return {
                "success": False,
                "alert": {
                    "type": "warning",
                    "title": "No Satellite Data Found",
                    "message": message
                },
                "scenes_found": scenes_found
            }

        # Run simulation
        results = run_irrigation_query(
            geojson=request.geojson,
            ndvi_path=ndvi_path,
            ndwi_path=ndwi_path,
            n_years=request.n_years
        )

        return {
            "success": True,
            "alert": {
                "type": "success",
                "title": "Simulation Complete",
                "message": message
            },
            "results": results
        }

    finally:
        # Cleanup temp files
        if ndvi_path:
            temp_dir = Path(ndvi_path).parent.parent.parent
            if "ndvi_temp_" in str(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
```

## User Workflow

**Before (Manual NDVI Download):**
1. User draws polygon
2. User selects dates
3. User clicks "Get NDVI" button → waits
4. User runs irrigation query

**After (Automatic On-Demand):**
1. User draws polygon
2. User runs irrigation query with dates → NDVI downloads automatically!
3. Results returned

**Much simpler!** ✅

---

**Last Updated**: 2025-10-24
