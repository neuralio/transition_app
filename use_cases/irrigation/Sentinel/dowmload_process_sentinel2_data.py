#!/usr/bin/env python3
"""
Modularized Sentinel-2 Processing Pipeline

Enhanced version using the refactored modular architecture with separate
modules for indices, processing, and utilities.
"""

import argparse
import json
import yaml
import time
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
from pystac_client import Client
import rioxarray as rxr
import xarray as xr
import rasterio
from rasterio.enums import Resampling
import numpy as np
from tqdm import tqdm
import dask
from dask.distributed import Client as DaskClient
from dask import delayed
import dask.array as da
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import modular components
from modules.indices import index_registry
from modules.processing import CloudMasker, RGBComposer, TemporalCompositor
from modules.constants import BAND_MAPPINGS, SCL_CLASSES, SCL_CLOUD_MASK
from modules.utils import ConfigManager, PipelineLogger, setup_pipeline_logging, TimeEstimator, ProcessingTracker

# Register all available indices
from modules.indices import NDVIIndex, EVIIndex, SAVIIndex, NDWIIndex

# Initialize global components
logger = None
config_manager = None
time_estimator = None
processing_tracker = None


def initialize_pipeline(log_dir=None, config_file=None):
    """Initialize pipeline components"""
    global logger, config_manager, time_estimator, processing_tracker, index_registry
    
    # Setup basic logging (will be updated later with proper directory)
    if log_dir:
        logger = setup_pipeline_logging(log_dir, level="INFO")
    else:
        logger = setup_pipeline_logging(None, level="INFO")  # Use default/console logging
    
    logger.info("Initializing modular Sentinel-2 pipeline...")
    
    # Setup configuration
    config_manager = ConfigManager(config_file)
    
    # Setup time estimator
    time_estimator = TimeEstimator()
    
    # Setup processing tracker (will be properly initialized later with output paths)
    processing_tracker = None  # Will be created in main() after output paths are set
    
    # Register indices
    index_registry.register("NDVI", NDVIIndex)
    index_registry.register("EVI", EVIIndex)
    index_registry.register("SAVI", SAVIIndex)
    index_registry.register("NDWI", NDWIIndex)
    
    logger.info(f"Registered indices: {index_registry.list_indices()}")
    
    return logger, config_manager, time_estimator


def read_aoi(aoi_path):
    """Read AOI from geojson/shapefile and return geometry in WGS84"""
    gdf = gpd.read_file(aoi_path)
    gdf = gdf.to_crs(4326)
    union_geom = gdf.union_all() if hasattr(gdf, 'union_all') else gdf.unary_union
    geom = json.loads(gpd.GeoSeries([union_geom]).to_json())
    # Extract the geometry from the GeoJSON FeatureCollection
    if geom['type'] == 'FeatureCollection':
        geom = geom['features'][0]['geometry']
    return geom


def search_s2(aoi_geom, start, end, max_cloud, stac_url, ignore_cloud_filter=False):
    """Search for Sentinel-2 L2A scenes matching criteria"""
    client = Client.open(stac_url)
    
    logger.info(f"Searching STAC catalog: {stac_url}")
    logger.info(f"Date range: {start} to {end}")
    logger.info(f"Ignore cloud filter: {ignore_cloud_filter}")
    
    # Handle different STAC API implementations
    if "dataspace.copernicus.eu" in stac_url:
        # CDSE uses different parameter format
        search = client.search(
            collections=["sentinel-2-l2a"],
            bbox=[aoi_geom['coordinates'][0][0][0], aoi_geom['coordinates'][0][0][1], 
                  aoi_geom['coordinates'][0][2][0], aoi_geom['coordinates'][0][2][1]],
            datetime=f"{start}/{end}",
        )
    else:
        # Standard STAC API format (AWS, Microsoft PC)
        if ignore_cloud_filter:
            # Download ALL scenes regardless of cloud cover
            search = client.search(
                collections=["sentinel-2-l2a"],
                intersects=aoi_geom,
                datetime=f"{start}/{end}"
            )
        else:
            # Use cloud filter as before
            search = client.search(
                collections=["sentinel-2-l2a"],
                intersects=aoi_geom,
                datetime=f"{start}/{end}",
                query={"eo:cloud_cover": {"lt": max_cloud}}
            )
    
    items = list(search.items())
    
    # Filter by cloud cover if not done server-side (CDSE case) and cloud filter is enabled
    if "dataspace.copernicus.eu" in stac_url and not ignore_cloud_filter:
        items = [item for item in items if item.properties.get("eo:cloud_cover", 100) < max_cloud]
    
    logger.info(f"Found {len(items)} matching scenes")
    return items


def get_band_mapping(stac_url):
    """Get the appropriate band mapping based on STAC provider"""
    if "earth-search.aws" in stac_url:
        return BAND_MAPPINGS["aws"]
    else:
        return BAND_MAPPINGS["standard"]


@delayed
def download_band_delayed(asset_href, bandname, scene_id, aoi_geom, outdir):
    """Delayed version of band download for Dask parallelization"""
    return download_and_save_band(asset_href, bandname, scene_id, aoi_geom, outdir)


def download_and_save_band(asset_href, bandname, scene_id, aoi_geom, outdir, max_retries=2):
    """Download, clip and save band to local file, then return as xarray"""
    global processing_tracker
    
    # Create scene-specific directory
    scene_dir = Path(outdir) / "raw" / scene_id
    scene_dir.mkdir(parents=True, exist_ok=True)
    
    # Define output path
    band_file = scene_dir / f"{scene_id}_{bandname}.tif"
    
    # Check if already downloaded using processing tracker
    if processing_tracker and processing_tracker.is_scene_downloaded(scene_id, bandname):
        try:
            da = rxr.open_rasterio(band_file, masked=True).squeeze("band", drop=True)
            da = da.chunk({'x': 1024, 'y': 1024})
            da.name = bandname
            logger.debug(f"Using cached download: {scene_id}/{bandname}")
            return da
        except Exception as e:
            logger.warning(f"Cached file {band_file} is corrupted, re-downloading: {e}")
            if processing_tracker:
                processing_tracker.mark_download_failed(scene_id, bandname, f"Cached file corrupted: {e}")
    
    # Skip if already exists and is valid (fallback for non-tracked files)
    if band_file.exists():
        try:
            da = rxr.open_rasterio(band_file, masked=True).squeeze("band", drop=True)
            existing_resolution = abs(da.rio.resolution()[0])
            
            # If existing file has wrong resolution, reprocess it
            if existing_resolution > 15:  # Need to resample
                logger.debug(f"{bandname} exists but wrong resolution ({existing_resolution:.1f}m), reprocessing...")
                band_file.unlink()  # Remove corrupted file
            else:
                # Use dask arrays to chunk large data
                da = da.chunk({'x': 1024, 'y': 1024})
                da.name = bandname
                # Mark as complete in tracker if not already tracked
                if processing_tracker:
                    processing_tracker.mark_download_complete(scene_id, bandname, band_file)
                return da
        except Exception as e:
            logger.warning(f"Existing file {band_file} is corrupted, re-downloading: {e}")
            band_file.unlink()  # Remove corrupted file
    
    # Retry download with error handling
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Download attempt {attempt + 1}/{max_retries + 1}: {bandname} from {asset_href[:50]}...")
            
            # Download and clip with dask chunking for large files
            da = rxr.open_rasterio(asset_href, masked=True, chunks={'x': 1024, 'y': 1024}).squeeze("band", drop=True)
            da = da.rio.clip([aoi_geom], crs="EPSG:4326")
            da.name = bandname
            
            # Check and report resolution
            resolution = abs(da.rio.resolution()[0])
            
            # Resample to 10m if needed (ensures all bands are same resolution)
            if resolution > 15:  # If resolution is worse than 15m, resample to 10m
                from rasterio.enums import Resampling
                da = da.rio.reproject(
                    da.rio.crs,
                    resolution=10.0,
                    resampling=Resampling.bilinear
                )
            
            # Save to disk with dask computation
            da.rio.to_raster(band_file, compress="deflate", dtype="float32", tiled=True)
            
            # Verify file was saved correctly
            if band_file.exists() and band_file.stat().st_size > 1000:
                logger.debug(f"Successfully downloaded {bandname} for {scene_id}")
                # Mark download as complete in tracker
                if processing_tracker:
                    processing_tracker.mark_download_complete(scene_id, bandname, band_file)
                return da
            else:
                raise Exception("Downloaded file is empty or corrupted")
                
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Download attempt {attempt + 1} failed for {bandname}: {e}. Retrying...")
                # Clean up partial file if it exists
                if band_file.exists():
                    band_file.unlink()
                time.sleep(2)  # Wait before retry
                continue
            else:
                logger.error(f"Failed to download {bandname} for {scene_id} after {max_retries + 1} attempts: {e}")
                # Mark download as failed in tracker
                if processing_tracker:
                    processing_tracker.mark_download_failed(scene_id, bandname, str(e))
                # Clean up partial file if it exists
                if band_file.exists():
                    band_file.unlink()
                return None


def download_scene_parallel(item, bands, aoi_geom, band_mapping, outdir):
    """Download all bands for a scene in parallel"""
    scene_tasks = []
    
    for band in bands:
        asset_name = band_mapping.get(band, band)
        if asset_name in item.assets:
            href = item.assets[asset_name].href
            # Create delayed task for each band
            task = download_band_delayed(href, band, item.id, aoi_geom, outdir)
            scene_tasks.append((band, task))
    
    return scene_tasks


def group_items_by_date(items):
    """Group STAC items by acquisition date"""
    from collections import defaultdict
    date_groups = defaultdict(list)
    
    for item in items:
        # Extract date from item datetime
        date_str = item.datetime.date().strftime('%Y%m%d')
        date_groups[date_str].append(item)
    
    return dict(date_groups)


def create_spatial_mosaic(input_files, output_path):
    """Create a proper spatial mosaic from multiple raster files"""
    import rasterio
    from rasterio.merge import merge
    
    try:
        # Open all input files
        src_files = []
        for file_path in input_files:
            if Path(file_path).exists():
                src_files.append(rasterio.open(file_path))
        
        if not src_files:
            return None
        
        logger.debug(f"Mosaicking {len(src_files)} tiles...")
        
        # Merge the rasters using rasterio.merge
        # This handles overlaps, nodata, and creates a seamless mosaic
        mosaic, out_trans = merge(
            src_files, 
            method='max',  # Use maximum value for overlaps
            nodata=0,      # Set nodata value
            dtype='float32'
        )
        
        # Get metadata from first source
        out_meta = src_files[0].meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2], 
            "transform": out_trans,
            "dtype": 'float32',
            "compress": "deflate",
            "nodata": 0
        })
        
        # Write mosaic
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(mosaic)
        
        # Close source files
        for src in src_files:
            src.close()
        
        # Return as xarray
        mosaiced_data = rxr.open_rasterio(output_path, masked=True).squeeze("band", drop=True)
        resolution = abs(mosaiced_data.rio.resolution()[0])
        logger.debug(f"Mosaic size: {mosaiced_data.sizes}, Resolution: {resolution:.1f}m")
        return mosaiced_data
        
    except Exception as e:
        logger.error(f"Mosaicking failed: {e}")
        # Close any open files
        for src in src_files:
            try:
                src.close()
            except:
                pass
        return None


def process_single_date(items_for_date, bands, aoi_geom, band_mapping, outdir, date_str):
    """Process all scenes for a single date using parallel processing with progress tracking"""
    scene_start_time = time.time()
    logger.info(f"Processing date {date_str} ({len(items_for_date)} scenes) - PARALLEL MODE")
    
    # Create and display download summary
    scene_info = []
    for item in items_for_date:
        scene_parts = item.id.split('_')
        if len(scene_parts) >= 2:
            tile_id = scene_parts[1]  # Extract tile (e.g., 34TEK)
            sensor = scene_parts[0]   # Extract sensor (e.g., S2A)
            scene_info.append(f"{sensor}_{tile_id}")
        else:
            scene_info.append(item.id[:20])
    
    # Create parallel download tasks for all scenes and bands
    all_tasks = []
    task_mapping = {}  # Track which task belongs to which scene/band
    
    for item in items_for_date:
        scene_tasks = download_scene_parallel(item, bands, aoi_geom, band_mapping, outdir)
        for band, task in scene_tasks:
            all_tasks.append(task)
            task_mapping[task] = (item.id, band)
    
    if not all_tasks:
        logger.warning(f"No download tasks created for {date_str}")
        return None
    
    # Display download summary
    print(f"📡 Downloading {len(all_tasks)} files for {date_str}")
    print(f"🗺️  Scenes: {', '.join(scene_info)} ({len(items_for_date)} scenes × {len(bands)} bands)")
    print(f"⏳ Processing downloads in parallel...")
    
    # Create download status mapping for later use
    download_status = {}
    for task in all_tasks:
        scene_id, band = task_mapping[task]
        scene_parts = scene_id.split('_')
        tile_name = f"{scene_parts[0]}_{scene_parts[1]}_{band}" if len(scene_parts) >= 2 else f"{scene_id[:15]}_{band}"
        download_status[task] = tile_name
    
    logger.info(f"Executing {len(all_tasks)} download tasks in parallel...")
    
    # Execute all downloads in parallel using Dask (simplified, single-threaded for debugging)
    try:
        with dask.config.set(scheduler='synchronous'):  # Use synchronous scheduler for debugging
            results = dask.compute(*all_tasks)
    except Exception as e:
        logger.error(f"Parallel processing failed: {e}")
        return None
    
    # Process results and show final status
    print()  # Space before results
    band_files = {b: [] for b in bands}
    processed_scenes = set()
    successful_downloads = 0
    failed_downloads = 0
    
    print("📊 Download Results:")
    
    # Show final download status
    for task, result in zip(all_tasks, results):
        scene_id, band = task_mapping[task]
        tile_name = download_status[task]
        
        if result is not None:
            scene_dir = Path(outdir) / "raw" / scene_id
            band_file = scene_dir / f"{scene_id}_{band}.tif"
            band_files[band].append(str(band_file))
            processed_scenes.add(scene_id)
            successful_downloads += 1
            
            # Show success with file size
            try:
                file_size_mb = band_file.stat().st_size / (1024 * 1024)
                print(f"  ✅ {tile_name} ({file_size_mb:.1f}MB)")
                time_estimator.record_download(file_size_mb, 5.0, success=True)
            except:
                print(f"  ✅ {tile_name} (Downloaded)")
                time_estimator.record_download(30.0, 5.0, success=True)
        else:
            failed_downloads += 1
            print(f"  ❌ {tile_name} (Failed)")
            time_estimator.record_download(0, 0, success=False)
    
    # Show final progress summary
    progress_pct = (successful_downloads / len(all_tasks) * 100) if all_tasks else 0
    if failed_downloads == 0:
        print(f"\n✅ All downloads complete: {successful_downloads}/{len(all_tasks)} successful ({progress_pct:.1f}%)")
    else:
        print(f"\n⚠️  Downloads finished: {successful_downloads}/{len(all_tasks)} successful, {failed_downloads} failed ({progress_pct:.1f}%)")
    
    print()  # Add spacing after downloads
    
    successful_items = len(processed_scenes)
    logger.info(f"Parallel processing completed: {successful_items}/{len(items_for_date)} scenes successful")
    
    # Update time estimator progress
    time_estimator.print_progress()
    
    if successful_items == 0:
        logger.warning(f"No successful scenes for date {date_str}")
        return None
    
    # Create proper spatial mosaics using rasterio
    logger.info(f"Creating spatial mosaics for {date_str}...")
    mosaiced_bands = {}
    # Use products/mosaics directory instead of intermediate
    mosaic_dir = Path(outdir) / "products" / "mosaics" / "daily" / date_str
    mosaic_dir.mkdir(parents=True, exist_ok=True)
    
    for band in bands:
        if band_files[band]:
            mosaic_path = mosaic_dir / f"mosaic_{date_str}_{band}.tif"
            
            if len(band_files[band]) > 1:
                # Multiple files need mosaicking
                mosaiced_data = create_spatial_mosaic(band_files[band], mosaic_path)
            else:
                # Single file, just copy
                import shutil
                shutil.copy2(band_files[band][0], mosaic_path)
                mosaiced_data = rxr.open_rasterio(mosaic_path, masked=True).squeeze("band", drop=True)
            
            if mosaiced_data is not None:
                mosaiced_data.name = band
                mosaiced_bands[band] = mosaiced_data
    
    if mosaiced_bands:
        # Create dataset from mosaiced bands
        ds = xr.Dataset(mosaiced_bands)
        logger.info(f"Created unified mosaic for {date_str} ({successful_items} scenes)")
        first_band = list(ds.data_vars)[0]
        resolution = abs(ds[first_band].rio.resolution()[0])
        logger.info(f"Resolution: {resolution:.1f}m")
        return ds, date_str
    
    return None


def generate_per_date_products(ds, date_str, outdir, indices_to_calculate):
    """Generate products for a specific date using modular components"""
    global processing_tracker
    
    logger.info(f"Generating products for {date_str}...")
    
    # Create output directories
    output_paths = config_manager.create_output_directories()
    
    products_created = 0
    products_skipped = 0
    
    # Check data quality first
    for band in ["B02", "B03", "B04", "B08", "SCL"]:
        if band in ds:
            band_data = ds[band]
            valid_pixels = (~band_data.isnull()).sum().values
            total_pixels = band_data.size
            logger.debug(f"{band}: {valid_pixels}/{total_pixels} valid pixels ({100*valid_pixels/total_pixels:.1f}%)")
        else:
            logger.debug(f"{band}: Missing!")
    
    # Initialize processing components
    cloud_masker = CloudMasker() if 'SCL' in ds else None
    rgb_composer = RGBComposer(cloud_masker)
    
    # Generate RGB products
    if all(b in ds for b in ["B02", "B03", "B04"]):
        try:
            # Check if regular RGB already exists
            rgb_exists = processing_tracker and processing_tracker.is_product_complete(date_str, "rgb")
            rgb_cloud_exists = processing_tracker and processing_tracker.is_product_complete(date_str, "rgb_cloud_masked")
            
            if rgb_exists and rgb_cloud_exists:
                products_skipped += 2
                logger.debug(f"Skipping RGB products for {date_str} - already complete")
            else:
                rgb_results = rgb_composer.create_both_versions(ds)
                
                # Save regular RGB to rgb/daily/
                if rgb_results.get('rgb') is not None and not rgb_exists:
                    rgb_path = output_paths['rgb_daily'] / f"RGB_{date_str}.tif"
                    if save_geotiff_modular(rgb_results['rgb'], rgb_path):
                        products_created += 1
                        if processing_tracker:
                            processing_tracker.mark_product_complete(date_str, "rgb", rgb_path)
                        logger.info(f"Saved RGB for {date_str}")
                elif rgb_exists:
                    products_skipped += 1
                    logger.debug(f"Skipped RGB for {date_str} - already exists")
                
                # Save cloud-masked RGB to cloud_free/daily/
                if rgb_results.get('rgb_cloud_masked') is not None and not rgb_cloud_exists:
                    rgb_cloud_path = output_paths['cloud_free_daily'] / f"RGB_cloud_masked_{date_str}.tif"
                    if save_geotiff_modular(rgb_results['rgb_cloud_masked'], rgb_cloud_path):
                        products_created += 1
                        if processing_tracker:
                            processing_tracker.mark_product_complete(date_str, "rgb_cloud_masked", rgb_cloud_path)
                        logger.info(f"Saved cloud-masked RGB for {date_str}")
                elif rgb_cloud_exists:
                    products_skipped += 1
                    logger.debug(f"Skipped cloud-masked RGB for {date_str} - already exists")
                    
        except Exception as e:
            logger.error(f"RGB generation failed for {date_str}: {e}")
    
    # Save individual bands if requested
    if config_manager.config.save_individual_bands and output_paths['bands']:
        try:
            # Save each band as individual GeoTIFF to bands/daily/
            for band_name, band_data in ds.data_vars.items():
                if band_data is not None:
                    band_path = output_paths['bands'] / f"{band_name}_{date_str}.tif"
                    if save_geotiff_modular(band_data, band_path):
                        products_created += 1
                        logger.info(f"Saved individual band {band_name} for {date_str}")
        except Exception as e:
            logger.error(f"Individual band saving failed for {date_str}: {e}")
    
    # Generate vegetation indices
    try:
        # Calculate all requested indices
        indices_dict = index_registry.calculate_indices(ds, indices_to_calculate)
        
        # Save indices to their own separate directories
        for index_name, index_data in indices_dict.items():
            if index_data is not None:
                # Check if index already exists
                if processing_tracker and processing_tracker.is_product_complete(date_str, "indices", index_name):
                    products_skipped += 1
                    logger.debug(f"Skipped {index_name} for {date_str} - already exists")
                    continue
                
                # Each index gets its own directory
                if index_name == "NDVI":
                    index_path = output_paths['ndvi_daily'] / f"NDVI_{date_str}.tif"
                elif index_name == "EVI":
                    index_path = output_paths['evi_daily'] / f"EVI_{date_str}.tif"
                elif index_name == "SAVI":
                    index_path = output_paths['savi_daily'] / f"SAVI_{date_str}.tif"
                elif index_name == "NDWI":
                    index_path = output_paths['ndwi_daily'] / f"NDWI_{date_str}.tif"
                else:
                    # Fallback for any other indices
                    logger.warning(f"Unknown index {index_name}, saving to NDVI directory")
                    index_path = output_paths['ndvi_daily'] / f"{index_name}_{date_str}.tif"
                
                if save_geotiff_modular(index_data, index_path):
                    products_created += 1
                    if processing_tracker:
                        processing_tracker.mark_product_complete(date_str, "indices", index_path, index_name)
                    logger.info(f"Saved {index_name} for {date_str}")
        
        # Generate cloud-free versions if SCL is available
        if cloud_masker and 'SCL' in ds:
            cloud_free_indices = cloud_masker.apply_to_indices(indices_dict, ds['SCL'])
            
            # Save cloud-free indices to cloud_free/daily/
            for index_name, index_data in cloud_free_indices.items():
                if index_data is not None:
                    # Check if cloud-free index already exists
                    if processing_tracker and processing_tracker.is_product_complete(date_str, "cloud_free", index_name):
                        products_skipped += 1
                        logger.debug(f"Skipped cloud-free {index_name} for {date_str} - already exists")
                        continue
                    
                    # index_name already contains '_cloud_free' suffix from cloud masking module
                    cloud_free_path = output_paths['cloud_free_daily'] / f"{index_name}_{date_str}.tif"
                    if save_geotiff_modular(index_data, cloud_free_path):
                        products_created += 1
                        if processing_tracker:
                            processing_tracker.mark_product_complete(date_str, "cloud_free", cloud_free_path, index_name)
                        logger.info(f"Saved cloud-free {index_name} for {date_str}")
                            
    except Exception as e:
        logger.error(f"Index calculation failed for {date_str}: {e}")
    
    logger.info(f"Generated {products_created} products for {date_str} (skipped {products_skipped} existing)")
    return products_created


def save_geotiff_modular(data_array, output_path, nodata=-9999):
    """Save xarray DataArray using modular utilities"""
    from modules.utils import save_geotiff
    return save_geotiff(data_array, output_path, dtype='float32')


def process_per_date_products(items, bands, aoi_geom, band_mapping, outdir, max_items=50):
    """Process items by date and generate per-date products"""
    
    # Limit items and group by date
    items_to_process = items[:max_items]
    logger.info(f"Processing {len(items_to_process)} out of {len(items)} available scenes")
    logger.debug(f"Band mapping: {band_mapping}")
    
    date_groups = group_items_by_date(items_to_process)
    logger.info(f"Found {len(date_groups)} unique dates")
    
    per_date_datasets = []
    processed_dates = []
    
    # Get indices to calculate from config
    indices_to_calculate = config_manager.config.indices_to_calculate
    
    # Process each date
    for i, (date_str, items_for_date) in enumerate(sorted(date_groups.items())):
        logger.info(f"🔄 Processing date {i+1}/{len(date_groups)}: {date_str}")
        result = process_single_date(items_for_date, bands, aoi_geom, band_mapping, outdir, date_str)
        if result is not None:
            ds, processed_date = result
            per_date_datasets.append((ds, processed_date))
            processed_dates.append(processed_date)
            
            # Generate per-date products using modular components
            scene_start_time = time.time()
            products_created = generate_per_date_products(ds, processed_date, outdir, indices_to_calculate)
            scene_processing_time = time.time() - scene_start_time
            
            # Record scene completion
            time_estimator.record_scene_completion(scene_processing_time, products_created, success=True)
            
            print(f"✅ Completed {processed_date}: {products_created} products in {scene_processing_time:.1f}s", flush=True)
            
            # Print progress more frequently - every scene or every few scenes for large datasets
            progress_interval = max(1, min(3, len(date_groups) // 3))  # Show progress every 1-3 scenes max
            if (i + 1) % progress_interval == 0 or i == len(date_groups) - 1:
                print(f"🔄 Scene {i+1}/{len(date_groups)} complete", flush=True)
                time_estimator.print_progress()
    
    if not per_date_datasets:
        raise RuntimeError("No data could be processed for any date.")
    
    logger.info(f"Successfully processed {len(per_date_datasets)} dates: {processed_dates}")
    return per_date_datasets


def process_temporal_composites(per_date_datasets, outdir):
    """Process temporal composites using modular components"""
    global processing_tracker
    
    if not config_manager.config.temporal_compositing:
        logger.info("Temporal compositing disabled, skipping...")
        return
    
    logger.info("Processing temporal composites...")
    
    # Initialize temporal compositor
    compositor = TemporalCompositor(
        rule=config_manager.config.temporal_rule,
        reducer=config_manager.config.temporal_reducer,
        outdir=outdir
    )
    
    # Process each requested index
    total_created = 0
    total_skipped = 0
    
    for index_name in config_manager.config.indices_to_calculate:
        try:
            # Generate composites (the compositor will handle the actual file generation)
            result = compositor.process_temporal_composites(per_date_datasets, index_name)
            
            if result['status'] == 'success':
                created_count = result['composites_created']
                total_created += created_count
                
                # Mark composite files as complete in tracker
                if processing_tracker and 'composite_files' in result:
                    for file_path in result['composite_files']:
                        # Extract period info from filename
                        # Expected format: INDEX_dekadal_REDUCER_STARTDATE_ENDDATE.tif
                        file_name = Path(file_path).stem
                        parts = file_name.split('_')
                        if len(parts) >= 5:
                            start_date = parts[-2]
                            end_date = parts[-1] 
                            processing_tracker.mark_temporal_composite_complete(
                                index_name, 
                                config_manager.config.temporal_rule,
                                config_manager.config.temporal_reducer,
                                start_date, 
                                end_date,
                                file_path
                            )
                
                logger.info(f"Created {created_count} temporal composites for {index_name}")
            else:
                logger.error(f"Temporal compositing failed for {index_name}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Temporal compositing error for {index_name}: {e}")
    
    if total_created > 0:
        logger.info(f"📊 Total temporal composites created: {total_created}")
    if total_skipped > 0:
        logger.info(f"📊 Total temporal composites skipped: {total_skipped}")


def main(args):
    """Main pipeline execution"""
    global logger, config_manager, time_estimator, processing_tracker
    
    # Setup Dask for parallel processing
    print("🚀 Setting up parallel processing with Dask...")
    dask.config.set({
        'array.chunk-size': '128MB',  # Chunk size for arrays
        'distributed.worker.memory.target': 0.8,  # Memory management
        'distributed.worker.memory.spill': 0.9,
        'distributed.worker.memory.pause': 0.95,
        # Disable Dask progress bars that might interfere
        'distributed.dashboard.link': False,
        'distributed.diagnostics.progress.enabled': False,
    })
    
    # Disable Dask logging to avoid output capture
    import logging
    logging.getLogger('distributed').setLevel(logging.WARNING)
    logging.getLogger('dask').setLevel(logging.WARNING)
    
    # Initialize pipeline without creating directories yet
    print("DEBUG: About to initialize pipeline...")
    logger, config_manager, time_estimator = initialize_pipeline(log_dir=None, config_file=args.config)
    print(f"DEBUG: Pipeline initialized, config output_dir: {config_manager.config.output_dir}")
    
    try:
        # Update configuration with command line arguments
        cli_updates = {}
        if args.start:
            cli_updates['start_date'] = args.start
        if args.end:
            cli_updates['end_date'] = args.end
        # Note: If end_date is None in config and no --end provided,
        # the ProcessingConfig.__post_init__ will set it to today's date automatically
        
        if args.cloud is not None:
            cli_updates['cloud_cover_threshold'] = args.cloud
        if args.outdir:
            cli_updates['output_dir'] = args.outdir
        if args.indices:
            cli_updates['indices_to_calculate'] = args.indices
        if args.temporal:
            cli_updates['temporal_compositing'] = True
        
        print(f"DEBUG: CLI updates: {cli_updates}")
        config_manager.update_config(cli_updates)
        
        # Use the final output directory from configuration (after CLI overrides)
        outdir = config_manager.config.output_dir
        print(f"DEBUG: Final output directory: {outdir}")
        
        # Setup proper logging with final output directory
        final_log_dir = Path(outdir) / 'logs'
        print(f"DEBUG: Creating log directory: {final_log_dir}")
        final_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Reinitialize logger with proper directory
        logger = setup_pipeline_logging(final_log_dir, level="INFO")
        logger.info(f"📁 Using output directory from configuration: {outdir}")
        logger.info("Logger reinitialized with proper output directory")
        
        # Validate configuration
        validation_errors = config_manager.validate_config()
        if validation_errors:
            for error in validation_errors:
                logger.error(f"Configuration error: {error}")
            raise ValueError("Invalid configuration")
        
        # Print configuration
        config_manager.print_config()
        
        # Initialize processing tracker
        metadata_dir = Path(outdir) / 'metadata'
        processing_tracker = ProcessingTracker(metadata_dir, logger)
        logger.info("📊 Processing tracker initialized")
        
        # Start processing session
        config_dict = {
            'start_date': config_manager.config.start_date,
            'end_date': config_manager.config.end_date, 
            'indices_to_calculate': config_manager.config.indices_to_calculate,
            'temporal_rule': config_manager.config.temporal_rule,
            'temporal_reducer': config_manager.config.temporal_reducer,
            'create_rgb': config_manager.config.create_rgb,
            'create_cloud_masked_products': config_manager.config.create_cloud_masked_products,
            'output_dir': outdir,
            'cloud_cover_threshold': config_manager.config.cloud_cover_threshold
        }
        session_id = processing_tracker.start_processing_session(config_dict)
        logger.info(f"🚀 Started processing session: {session_id}")
        
        # Generate resume summary
        resume_summary = processing_tracker.get_resume_summary(config_dict)
        logger.info("📋 Processing Resume Summary:")
        logger.info(f"  • Downloads: {resume_summary['downloads']['complete_scenes']}/{resume_summary['downloads']['total_scenes']} scenes complete")
        logger.info(f"  • Products: {resume_summary['products']['complete_products']}/{resume_summary['products']['total_products']} products complete")
        logger.info(f"  • Temporal composites: {resume_summary['temporal_composites']['complete_composites']}/{resume_summary['temporal_composites']['total_composites']} complete")
        if resume_summary.get('estimated_time_savings') != 'Unknown':
            logger.info(f"  • Estimated time savings: {resume_summary['estimated_time_savings']}")
        if resume_summary.get('config_drift'):
            logger.warning("  ⚠️  Configuration drift detected - some products may need regeneration")
        
        # Confirm final output directory
        logger.info(f"📁 Final output directory: {outdir}")
        
        # Read AOI - prioritize command line, then config file, then bbox
        if args.aoi:
            aoi_geom = read_aoi(args.aoi)
        elif config_manager.config.aoi:
            aoi_geom = read_aoi(config_manager.config.aoi)
        else:
            # Use bbox from config as polygon
            bbox = config_manager.config.bbox
            aoi_geom = {
                "type": "Polygon",
                "coordinates": [[
                    [bbox[0], bbox[1]],  # min_x, min_y
                    [bbox[2], bbox[1]],  # max_x, min_y
                    [bbox[2], bbox[3]],  # max_x, max_y
                    [bbox[0], bbox[3]],  # min_x, max_y
                    [bbox[0], bbox[1]]   # close polygon
                ]]
            }
        
        # Search for scenes - prioritize command line, then config, then default
        stac_url = args.stac or config_manager.config.stac_url
        items = search_s2(
            aoi_geom, 
            config_manager.config.start_date, 
            config_manager.config.end_date,
            config_manager.config.cloud_cover_threshold, 
            stac_url, 
            ignore_cloud_filter=config_manager.config.ignore_cloud_filter
        )
        
        if not items:
            logger.error("No scenes found. Check dates and AOI.")
            return
        
        # Initialize time estimator with scene count
        max_scenes = config_manager.config.max_scenes
        scenes_to_process = len(items) if max_scenes == 0 else min(max_scenes, len(items))
        estimated_downloads = scenes_to_process * 5  # Estimate 5 bands per scene
        
        print(f"DEBUG: About to start time estimator with {scenes_to_process} scenes")
        time_estimator.start_pipeline(scenes_to_process, estimated_downloads)
        
        print("DEBUG: Time estimator started, calling print_progress()")
        # Show initial progress state
        time_estimator.print_progress()
        print("DEBUG: print_progress() called")
        
        # Print cloud cover statistics
        cloud_covers = [item.properties.get('eo:cloud_cover', 0) for item in items]
        if cloud_covers:
            logger.info(f"Cloud cover range: {min(cloud_covers):.1f}% - {max(cloud_covers):.1f}%")
            high_cloud_count = sum(1 for cc in cloud_covers if cc > 50)
            logger.info(f"High cloud scenes (>50%): {high_cloud_count}/{len(items)} ({100*high_cloud_count/len(items):.1f}%)")
        
        # Get band mapping for the STAC provider
        band_mapping = get_band_mapping(stac_url)
        
        # Determine required bands including SCL for cloud masking
        required_bands = set(["B02", "B03", "B04", "B08", "SCL"])
        
        # Add any additional bands required by indices
        for index_name in config_manager.config.indices_to_calculate:
            index_bands = index_registry.get_required_bands([index_name])
            required_bands.update(index_bands)
        
        logger.info(f"Required bands: {sorted(required_bands)}")
        
        # Clean up any corrupted files from previous runs
        print("🧹 Cleaning up any corrupted files from previous runs...")
        raw_dir = Path(outdir) / "raw"
        if raw_dir.exists():
            for scene_dir in raw_dir.iterdir():
                if scene_dir.is_dir():
                    for tif_file in scene_dir.glob("*.tif"):
                        try:
                            # Try to open each TIFF file to check if it's valid
                            rxr.open_rasterio(tif_file, masked=True).squeeze("band", drop=True).close()
                        except Exception:
                            logger.warning(f"Removing corrupted file: {tif_file}")
                            tif_file.unlink()
        
        # Process per-date products
        time_estimator.start_phase("processing")
        max_scenes = config_manager.config.max_scenes
        if max_scenes == 0:
            logger.info(f"Processing ALL {len(items)} available scenes")
            per_date_datasets = process_per_date_products(
                items, sorted(required_bands), aoi_geom, band_mapping, outdir, max_items=len(items)
            )
        else:
            logger.info(f"Processing {min(max_scenes, len(items))} out of {len(items)} available scenes")
            per_date_datasets = process_per_date_products(
                items, sorted(required_bands), aoi_geom, band_mapping, outdir, max_items=max_scenes
            )
        
        # Process temporal composites if requested
        if config_manager.config.temporal_compositing:
            time_estimator.start_phase("temporal_compositing")
            process_temporal_composites(per_date_datasets, outdir)
        
        # Log processing summary
        successful_scenes = len(per_date_datasets)
        total_scenes = len(items)
        logger.log_processing_summary(
            total_scenes, successful_scenes, 
            config_manager.config.indices_to_calculate, 
            successful_scenes if config_manager.config.temporal_compositing else 0
        )
        
        # Print final completion summary
        time_estimator.print_final_summary()
        logger.info(f"Pipeline complete! Outputs saved to {outdir}")
        
        # End processing session successfully
        if processing_tracker:
            processing_tracker.end_processing_session(session_id, success=True)
            # Print final statistics
            stats = processing_tracker.get_statistics()
            logger.info("📊 Final Processing Statistics:")
            logger.info(f"  • Total scenes: {stats['downloads']['total_scenes']}")
            logger.info(f"  • Successful downloads: {stats['downloads']['successful_downloads']}")
            logger.info(f"  • Total products: {stats['products']['total_products']}")
        
    except Exception as e:
        logger.critical(f"Pipeline failed: {e}")
        
        # End processing session with failure
        if processing_tracker:
            processing_tracker.end_processing_session(session_id, success=False, error=str(e))
            
        if time_estimator:
            time_estimator.print_final_summary()
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Modular Sentinel-2 processing pipeline")
    p.add_argument("--config", help="Configuration file path (JSON or YAML)")
    p.add_argument("--aoi", help="GeoJSON/SHAPEFILE path (in any CRS)")
    p.add_argument("--start", help="Start date YYYY-MM-DD")
    p.add_argument("--end", help="End date YYYY-MM-DD")
    p.add_argument("--cloud", type=int, help="Max cloud cover percentage")
    p.add_argument("--stac", help="STAC endpoint URL")
    p.add_argument("--outdir", help="Output directory")
    p.add_argument("--indices", nargs="+", help="Vegetation indices to compute",
                  choices=["NDVI", "EVI", "SAVI", "NDWI"])
    p.add_argument("--temporal", action="store_true", help="Build temporal composites")
    
    args = p.parse_args()
    main(args)
