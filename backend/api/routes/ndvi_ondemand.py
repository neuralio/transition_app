"""On-Demand NDVI Download for Irrigation Queries

Downloads Sentinel-2 NDVI/NDWI data on-demand for irrigation simulations.
Data is saved to temporary directory and automatically cleaned up after use.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import subprocess
import tempfile
import yaml
import json
import logging
import re

logger = logging.getLogger(__name__)


def download_ndvi_for_query(
    geojson: Dict[str, Any],
    start_date: str,
    end_date: str,
    indices: List[str] = ["NDVI", "NDWI"]
) -> Tuple[Optional[str], Optional[str], str, int]:
    """
    Download NDVI/NDWI data on-demand for an irrigation query.

    Data is saved to a temporary directory that should be cleaned up by caller.

    Args:
        geojson: GeoJSON FeatureCollection with user-drawn polygons
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        indices: List of indices to compute (default: ["NDVI", "NDWI"])

    Returns:
        Tuple of (ndvi_raster_path, ndwi_raster_path, user_message, scenes_found)
        - ndvi_raster_path: Path to NDVI GeoTIFF or None if not found
        - ndwi_raster_path: Path to NDWI GeoTIFF or None if not found
        - user_message: User-friendly message about data availability
        - scenes_found: Number of Sentinel-2 scenes found (for alerting)

    Raises:
        RuntimeError: If download script fails
    """
    from shapely.geometry import shape

    logger.info(f"📡 On-demand NDVI download requested: {start_date} → {end_date}")

    # Extract bounding box from GeoJSON
    bbox = extract_bbox_from_geojson(geojson)
    logger.info(f"📍 Extracted bbox: {bbox}")

    # Create cache key from bbox + dates (for reusing NDVI across queries)
    import hashlib
    import time
    cache_key = f"{bbox}_{start_date}_{end_date}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]

    # Cleanup old cache entries BEFORE checking cache (age > 24 hours)
    cache_root = Path("/tmp/ndvi_cache")
    if cache_root.exists():
        current_time = time.time()
        age_limit_hours = 24  # Keep cache for 24 hours
        for cache_entry in cache_root.iterdir():
            if cache_entry.is_dir():
                try:
                    # Check age of cache directory
                    mtime = cache_entry.stat().st_mtime
                    age_hours = (current_time - mtime) / 3600
                    if age_hours > age_limit_hours:
                        logger.info(f"🗑️  Deleting old cache ({age_hours:.1f}h old): {cache_entry.name}")
                        import shutil
                        shutil.rmtree(cache_entry, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Could not cleanup cache entry {cache_entry}: {e}")

    # Check if cached NDVI exists
    cache_dir = cache_root / cache_hash
    if cache_dir.exists():
        # Check if NDVI file exists in cache
        ndvi_cached = cache_dir / "products/ndvi/daily"
        if ndvi_cached.exists():
            ndvi_files = list(ndvi_cached.glob("NDVI_*.tif"))
            if ndvi_files:
                logger.info(f"✅ Using cached NDVI from: {cache_dir}")
                ndvi_path = str(ndvi_files[-1])  # Most recent
                ndwi_cached = cache_dir / "products/ndwi/daily"
                ndwi_files = list(ndwi_cached.glob("NDWI_*.tif")) if ndwi_cached.exists() else []
                ndwi_path = str(ndwi_files[-1]) if ndwi_files else None
                return ndvi_path, ndwi_path, "Using cached NDVI data", len(ndvi_files)

    # No cache hit - create persistent cache directory
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_dir = cache_dir
    logger.info(f"📁 Using cache directory: {output_dir}")

    # Load template config and fill placeholders
    project_root = Path(__file__).parent.parent.parent.parent
    template_config_path = project_root / "use_cases/irrigation/Sentinel/config_modular.yaml"

    if not template_config_path.exists():
        raise FileNotFoundError(f"Template config not found: {template_config_path}")

    # Read template and replace placeholders
    with open(template_config_path, 'r') as f:
        config_template = f.read()

    config_filled = config_template.replace(
        '{{BBOX_PLACEHOLDER}}', str(bbox)
    ).replace(
        '{{START_DATE_PLACEHOLDER}}', start_date
    ).replace(
        '{{END_DATE_PLACEHOLDER}}', end_date
    ).replace(
        '{{OUTPUT_DIR_PLACEHOLDER}}', str(output_dir)
    )

    # Write filled config to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_filled)
        config_path = f.name

    logger.info(f"⚙️ Created config from template: {template_config_path}")
    logger.info("=" * 80)
    logger.info("📄 FILLED CONFIG CONTENT (sent to download script):")
    logger.info("=" * 80)
    logger.info(config_filled)
    logger.info("=" * 80)

    # Run Sentinel-2 download script
    script_path = project_root / "use_cases/irrigation/Sentinel/dowmload_process_sentinel2_data.py"

    if not script_path.exists():
        raise FileNotFoundError(f"Download script not found: {script_path}")

    logger.info(f"🚀 Executing Sentinel-2 download script...")
    logger.info(f"📝 Command: python3 {script_path} --config {config_path}")

    try:
        result = subprocess.run(
            ["python3", str(script_path), "--config", config_path],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max
            cwd=str(project_root)
        )

        # Clean up temp config
        Path(config_path).unlink()

        if result.returncode != 0:
            logger.error(f"❌ Download failed: {result.stderr}")
            raise RuntimeError(f"Sentinel-2 download failed: {result.stderr[:500]}")

        logger.info(f"✅ Download completed successfully")

    except subprocess.TimeoutExpired:
        logger.error("⏱️ Download timeout (>10 minutes)")
        Path(config_path).unlink()
        raise RuntimeError("Sentinel-2 download timeout (>10 minutes)")

    # Check script logs to determine if scenes were found
    log_files = list(output_dir.glob("logs/*.log"))
    scenes_found = None
    if log_files:
        try:
            with open(log_files[0], 'r') as f:
                log_content = f.read()
                match = re.search(r'Found (\d+) matching scenes', log_content)
                if match:
                    scenes_found = int(match.group(1))
                    logger.info(f"📡 Script found {scenes_found} Sentinel-2 scenes")
        except Exception as e:
            logger.debug(f"Could not parse log file: {e}")

    # Find NDVI and NDWI raster files
    ndvi_files = list(output_dir.glob("**/NDVI_*.tif"))
    ndwi_files = list(output_dir.glob("**/NDWI_*.tif"))

    ndvi_raster_path = str(sorted(ndvi_files)[-1]) if ndvi_files else None
    ndwi_raster_path = str(sorted(ndwi_files)[-1]) if ndwi_files else None

    # Generate user message
    user_message = ""
    if not ndvi_files:
        if scenes_found == 0:
            logger.warning(f"⚠️ No Sentinel-2 scenes available for {start_date} to {end_date}")
            logger.warning(f"   Sentinel-2 revisit time: 2-5 days. Try extending date range.")
            user_message = f"No satellite data available for {start_date} to {end_date}. Sentinel-2 revisit time is 2-5 days. Try selecting a wider date range (e.g., 7-10 days)."
        else:
            logger.error(f"❌ Script found {scenes_found} scenes but produced no NDVI rasters!")
            user_message = f"Processing error: Found {scenes_found} scenes but failed to generate NDVI."
    else:
        logger.info(f"📊 Found {len(ndvi_files)} NDVI raster(s)")
        logger.info(f"📊 NDVI raster: {ndvi_raster_path}")
        logger.info(f"📊 NDWI raster: {ndwi_raster_path}")
        user_message = f"Successfully processed {scenes_found or 'unknown'} Sentinel-2 scene(s)."

    return ndvi_raster_path, ndwi_raster_path, user_message, scenes_found or 0


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
