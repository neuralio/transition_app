"""Sentinel-2 NDVI/NDWI Processing API Endpoint

Provides FastAPI routes for dynamic Sentinel-2 data download and NDVI computation.

Workflow:
1. Receive GeoJSON polygons + date range from frontend
2. Extract bounding box from polygons
3. Create temporary config_modular.yaml
4. Execute dowmload_process_sentinel2_data.py as subprocess
5. Extract NDVI values per polygon from output raster
6. Return enriched GeoJSON with NDVI statistics
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import subprocess
import json
import yaml
from pathlib import Path
import tempfile
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router (no prefix here - added in server.py)
router = APIRouter(tags=["sentinel"])


# ============================================================================
# Request/Response Models
# ============================================================================

class PolygonRequest(BaseModel):
    """Request model for NDVI computation"""
    geojson: Dict[str, Any] = Field(..., description="GeoJSON FeatureCollection from map")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)", example="2024-01-01")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)", example="2024-01-31")
    indices: List[str] = Field(default=["NDVI", "NDWI"], description="Indices to compute")

class PolygonResponse(BaseModel):
    """Response model for NDVI computation"""
    success: bool
    geojson: Dict[str, Any]
    output_dir: str
    ndvi_raster_path: str = Field(default="", description="Path to raw NDVI raster file (GeoTIFF)")
    ndwi_raster_path: str = Field(default="", description="Path to raw NDWI raster file (GeoTIFF)")
    message: str = ""


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/compute-indices", response_model=PolygonResponse)
async def compute_indices(request: PolygonRequest):
    """
    Compute NDVI/NDWI for user-drawn polygons within specified date range.

    Args:
        request: PolygonRequest with geojson, start_date, end_date

    Returns:
        PolygonResponse with enriched GeoJSON containing NDVI statistics

    Raises:
        HTTPException: If processing fails
    """
    try:
        logger.info(f"📥 Received NDVI request: {request.start_date} → {request.end_date}")
        logger.info(f"📊 Polygon count: {len(request.geojson.get('features', []))}")

        # Print full GeoJSON to terminal
        logger.info("=" * 80)
        logger.info("📍 POLYGON GEOJSON:")
        logger.info("=" * 80)
        logger.info(json.dumps(request.geojson, indent=2))
        logger.info("=" * 80)

        # Validate date range
        if request.start_date > request.end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before or equal to end date"
            )

        # Extract bounding box from GeoJSON
        bbox = extract_bbox_from_geojson(request.geojson)
        logger.info(f"📍 Extracted bbox: {bbox}")

        # Create deterministic output directory based on GEOJSON geometry and dates (for caching)
        # Hash the actual polygon coordinates to detect ANY change in shape
        import hashlib
        geojson_str = json.dumps(request.geojson, sort_keys=True)  # Sort keys for consistent hashing
        cache_key = f"{geojson_str}_{request.start_date}_{request.end_date}"
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:8]
        output_dir = Path(f"./ndvi_data/{request.start_date}_{request.end_date}_{cache_hash}")

        # DEBUG: Print cache key details
        logger.info("=" * 80)
        logger.info("🔑 CACHE KEY DETAILS:")
        logger.info(f"  Start Date: {request.start_date}")
        logger.info(f"  End Date: {request.end_date}")
        logger.info(f"  GeoJSON hash: {hashlib.md5(geojson_str.encode()).hexdigest()[:16]}")
        logger.info(f"  Full cache hash: {cache_hash}")
        logger.info(f"  Output directory: {output_dir}")
        logger.info("=" * 80)

        # Check if data already exists
        existing_ndvi = list(output_dir.glob("**/NDVI_*.tif")) if output_dir.exists() else []
        if existing_ndvi:
            logger.info(f"🔄 CACHE HIT! Found {len(existing_ndvi)} existing NDVI files in {output_dir}")
            logger.info(f"   Files: {[f.name for f in existing_ndvi[:3]]}...")
        else:
            logger.info(f"📁 CACHE MISS! Creating new output directory: {output_dir}")
            output_dir.mkdir(parents=True, exist_ok=True)

        # Load template config and fill placeholders
        project_root = Path(__file__).parent.parent.parent.parent
        template_config_path = project_root / "use_cases/irrigation/Sentinel/config_modular.yaml"

        if not template_config_path.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Template config not found: {template_config_path}"
            )

        # Read template and replace placeholders
        with open(template_config_path, 'r') as f:
            config_template = f.read()

        # Replace placeholders with user-provided values
        config_filled = config_template.replace(
            '{{BBOX_PLACEHOLDER}}', str(bbox)
        ).replace(
            '{{START_DATE_PLACEHOLDER}}', request.start_date
        ).replace(
            '{{END_DATE_PLACEHOLDER}}', request.end_date
        ).replace(
            '{{OUTPUT_DIR_PLACEHOLDER}}', str(output_dir)
        )

        # Write filled config to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_filled)
            config_path = f.name

        logger.info(f"⚙️ Created config from template: {template_config_path}")
        logger.info(f"📝 Filled config saved to: {config_path}")

        # DEBUG: Print the actual filled config being passed to script
        logger.info("=" * 80)
        logger.info("📄 FILLED CONFIG CONTENT (sent to download script):")
        logger.info("=" * 80)
        logger.info(config_filled)
        logger.info("=" * 80)

        # Run Sentinel-2 download script (note: filename has typo "dowmload")
        script_path = Path("use_cases/irrigation/Sentinel/dowmload_process_sentinel2_data.py")

        # Make path absolute from project root
        if not script_path.is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent
            script_path = project_root / script_path

        logger.info(f"📍 Script path: {script_path}")
        logger.info(f"📍 Script exists: {script_path.exists()}")

        if not script_path.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Sentinel-2 processing script not found: {script_path}"
            )

        logger.info(f"🚀 Executing Sentinel-2 download script...")
        logger.info(f"📝 Command: python {script_path} --config {config_path}")

        result = subprocess.run(
            ["python3", str(script_path), "--config", config_path],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max
            cwd=str(project_root)  # Run from project root
        )

        # Clean up temp config
        Path(config_path).unlink()

        if result.returncode != 0:
            logger.error(f"❌ Processing failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Sentinel-2 processing failed: {result.stderr[:500]}"
            )

        logger.info(f"✅ Processing completed successfully")

        # Check script logs to determine if scenes were found
        log_files = list(output_dir.glob("logs/*.log"))
        scenes_found = None
        if log_files:
            try:
                with open(log_files[0], 'r') as f:
                    log_content = f.read()
                    # Look for "Found X matching scenes" in log
                    import re
                    match = re.search(r'Found (\d+) matching scenes', log_content)
                    if match:
                        scenes_found = int(match.group(1))
                        logger.info(f"📡 Script found {scenes_found} Sentinel-2 scenes")
            except Exception as e:
                logger.debug(f"Could not parse log file: {e}")

        # Find NDVI and NDWI raster file paths (for raw values -1 to 1)
        ndvi_files = list(output_dir.glob("**/NDVI_*.tif"))
        ndwi_files = list(output_dir.glob("**/NDWI_*.tif"))

        ndvi_raster_path = str(sorted(ndvi_files)[-1]) if ndvi_files else ""
        ndwi_raster_path = str(sorted(ndwi_files)[-1]) if ndwi_files else ""

        # Provide clear user feedback based on actual script results
        user_message = ""
        if not ndvi_files:
            if scenes_found == 0:
                logger.warning(f"⚠️ No Sentinel-2 scenes available for {request.start_date} to {request.end_date}")
                logger.warning(f"   Sentinel-2 revisit time: 2-5 days. Try extending date range.")
                user_message = f"No satellite data available for {request.start_date} to {request.end_date}. Sentinel-2 revisit time is 2-5 days. Try selecting a wider date range (e.g., 7-10 days)."
            else:
                logger.error(f"❌ Script found {scenes_found} scenes but produced no NDVI rasters!")
                user_message = f"Processing error: Found {scenes_found} scenes but failed to generate NDVI."
        else:
            logger.info(f"📊 Found {len(ndvi_files)} NDVI raster(s)")
            logger.info(f"📊 NDVI raster available at: {ndvi_raster_path}")
            logger.info(f"📊 NDWI raster available at: {ndwi_raster_path}")
            user_message = f"Successfully processed {scenes_found or 'unknown'} Sentinel-2 scene(s)."

        # Return GeoJSON with raster paths (not statistics!)
        # The raw NDVI/NDWI values (-1 to 1) are in the raster files
        # Users can apply thresholds:
        #   - NDVI < 0.2-0.3 → bare soil detection
        #   - NDWI > 0.2 → water/flooding detection (for rice)
        result_geojson = request.geojson.copy()

        return PolygonResponse(
            success=True,
            geojson=result_geojson,
            output_dir=str(output_dir),
            ndvi_raster_path=ndvi_raster_path,
            ndwi_raster_path=ndwi_raster_path,
            message=user_message
        )

    except subprocess.TimeoutExpired:
        logger.error("⏱️ Processing timeout (>10 minutes)")
        raise HTTPException(
            status_code=504,
            detail="Processing timeout: Sentinel-2 download took too long (>10 minutes)"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helper Functions
# ============================================================================

def extract_bbox_from_geojson(geojson: Dict[str, Any]) -> List[float]:
    """
    Extract bounding box [lon_min, lat_min, lon_max, lat_max] from GeoJSON.

    Args:
        geojson: GeoJSON FeatureCollection

    Returns:
        List[float]: [lon_min, lat_min, lon_max, lat_max]
    """
    from shapely.geometry import shape

    all_coords = []

    for feature in geojson.get("features", []):
        geom = shape(feature["geometry"])

        # Handle both Polygon and MultiPolygon
        if geom.geom_type == "Polygon":
            all_coords.extend(geom.exterior.coords)
        elif geom.geom_type == "MultiPolygon":
            for poly in geom.geoms:
                all_coords.extend(poly.exterior.coords)

    if not all_coords:
        raise ValueError("No coordinates found in GeoJSON")

    lons = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]

    return [min(lons), min(lats), max(lons), max(lats)]


def enrich_geojson_with_ndvi(geojson: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
    """
    Add NDVI statistics to each polygon feature.

    Args:
        geojson: Original GeoJSON FeatureCollection
        output_dir: Directory containing NDVI raster files

    Returns:
        Enriched GeoJSON with NDVI properties

    Raises:
        ValueError: If no NDVI files found
    """
    import rasterio
    from rasterio.mask import mask
    from shapely.geometry import shape
    import numpy as np

    # Find NDVI raster file(s)
    ndvi_files = list(Path(output_dir).glob("**/NDVI_*.tif"))

    if not ndvi_files:
        raise ValueError(f"No NDVI files found in {output_dir}")

    # Use the most recent NDVI file (or could use temporal composite)
    ndvi_raster_path = sorted(ndvi_files)[-1]

    logger.info(f"📄 Using NDVI raster: {ndvi_raster_path}")

    # Open NDVI raster
    with rasterio.open(ndvi_raster_path) as src:
        for feature in geojson.get("features", []):
            geom = shape(feature["geometry"])

            try:
                # Mask NDVI raster with polygon
                masked, transform = mask(src, [geom], crop=True, all_touched=True)

                # Extract valid NDVI values (exclude nodata)
                ndvi_values = masked[0]  # First band
                valid_mask = (ndvi_values != src.nodata) & np.isfinite(ndvi_values)
                valid_ndvi = ndvi_values[valid_mask]

                if len(valid_ndvi) == 0:
                    # No valid NDVI values in this polygon
                    feature["properties"] = feature.get("properties", {})
                    feature["properties"].update({
                        "ndvi_mean": None,
                        "ndvi_std": None,
                        "ndvi_min": None,
                        "ndvi_max": None,
                        "ndvi_count": 0
                    })
                else:
                    # Add statistics to feature properties
                    feature["properties"] = feature.get("properties", {})
                    feature["properties"].update({
                        "ndvi_mean": float(np.mean(valid_ndvi)),
                        "ndvi_std": float(np.std(valid_ndvi)),
                        "ndvi_min": float(np.min(valid_ndvi)),
                        "ndvi_max": float(np.max(valid_ndvi)),
                        "ndvi_count": int(len(valid_ndvi))
                    })

            except Exception as e:
                logger.warning(f"⚠️ Failed to extract NDVI for polygon: {e}")
                feature["properties"] = feature.get("properties", {})
                feature["properties"]["ndvi_error"] = str(e)

    return geojson
