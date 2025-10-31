"""
Spatial Filtering for NetCDF Data using GeoJSON Polygons

This module provides functions to filter xarray Datasets based on user-drawn polygons.
Used for dynamic area-of-interest selection in TRANSITION simulations.

Enhanced with multi-polygon support and coordinate extraction (2025-10-23).

Author: TRANSITION Team
Date: 2025-10-15 (Enhanced: 2025-10-23)
"""

import xarray as xr
import numpy as np
from shapely.geometry import shape, Point, box
from shapely.ops import unary_union
import json
from typing import Dict, Union, Tuple, List
import logging

# Import new utilities for polygon metadata extraction
from backend.data.loaders.geojson_utils import (
    extract_polygon_metadata,
    extract_centroids_for_farmer_locations,
    format_farmer_locations_json
)

logger = logging.getLogger(__name__)


def parse_geojson(geojson_data: Union[str, dict]) -> dict:
    """
    Parse GeoJSON from string or dict format.

    Args:
        geojson_data: GeoJSON as string or dict

    Returns:
        Parsed GeoJSON dict
    """
    if isinstance(geojson_data, str):
        try:
            return json.loads(geojson_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GeoJSON string: {e}")
            raise ValueError(f"Invalid GeoJSON string: {e}")
    return geojson_data


def get_polygon_bounds(geojson_data: Union[str, dict]) -> Dict[str, float]:
    """
    Extract bounding box (min/max lat/lon) from GeoJSON polygon.

    Supports:
    - Single Polygon
    - MultiPolygon
    - FeatureCollection with multiple polygons

    Args:
        geojson_data: GeoJSON polygon (string or dict)

    Returns:
        Dict with keys: lat_min, lat_max, lon_min, lon_max

    Example:
        >>> geojson = {
        ...     "type": "Feature",
        ...     "geometry": {
        ...         "type": "Polygon",
        ...         "coordinates": [[[22.5, 40.4], [22.9, 40.4], [22.9, 40.9], [22.5, 40.9], [22.5, 40.4]]]
        ...     }
        ... }
        >>> bounds = get_polygon_bounds(geojson)
        >>> bounds
        {'lat_min': 40.4, 'lat_max': 40.9, 'lon_min': 22.5, 'lon_max': 22.9}
    """
    geojson_data = parse_geojson(geojson_data)

    # Handle FeatureCollection or single Feature/Geometry
    if geojson_data.get('type') == 'FeatureCollection':
        features = geojson_data.get('features', [])
    elif geojson_data.get('type') == 'Feature':
        features = [geojson_data]
    else:
        # Assume it's a raw geometry
        features = [{'type': 'Feature', 'geometry': geojson_data}]

    if not features:
        raise ValueError("GeoJSON contains no features")

    # Extract all coordinates from all features
    all_coords = []
    for feature in features:
        try:
            geom = shape(feature.get('geometry', feature))

            # Handle different geometry types
            if geom.geom_type == 'Polygon':
                coords = list(geom.exterior.coords)
            elif geom.geom_type == 'MultiPolygon':
                coords = []
                for poly in geom.geoms:
                    coords.extend(list(poly.exterior.coords))
            else:
                logger.warning(f"Unsupported geometry type: {geom.geom_type}")
                continue

            all_coords.extend(coords)
        except Exception as e:
            logger.error(f"Failed to extract coordinates from feature: {e}")
            continue

    if not all_coords:
        raise ValueError("No valid coordinates found in GeoJSON")

    # Extract lons and lats (GeoJSON uses [lon, lat] order)
    lons = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]

    bounds = {
        'lat_min': min(lats),
        'lat_max': max(lats),
        'lon_min': min(lons),
        'lon_max': max(lons)
    }

    logger.info(f"📍 Extracted polygon bounds: "
                f"lat=[{bounds['lat_min']:.4f}, {bounds['lat_max']:.4f}], "
                f"lon=[{bounds['lon_min']:.4f}, {bounds['lon_max']:.4f}]")

    return bounds


def filter_netcdf_by_bounds(ds: xr.Dataset, bounds: Dict[str, float]) -> xr.Dataset:
    """
    Filter xarray Dataset by bounding box (FAST method).

    This method filters the NetCDF data to only include grid points within
    the bounding box of the polygon. It's fast but includes all points in
    the rectangular bounding box (not just inside the polygon).

    Args:
        ds: xarray Dataset with 'lat' and 'lon' coordinates
        bounds: Dict with lat_min, lat_max, lon_min, lon_max

    Returns:
        Filtered xarray Dataset

    Example:
        >>> bounds = {'lat_min': 40.5, 'lat_max': 40.8, 'lon_min': 22.6, 'lon_max': 22.8}
        >>> filtered_ds = filter_netcdf_by_bounds(ds, bounds)
    """
    try:
        # Determine if lat/lon are ascending or descending
        lat_ascending = ds.lat.values[0] < ds.lat.values[-1]
        lon_ascending = ds.lon.values[0] < ds.lon.values[-1]

        # Handle different coordinate orderings
        if lat_ascending:
            lat_slice = ds.sel(lat=slice(bounds['lat_min'], bounds['lat_max']))
        else:
            # Descending coordinates (max to min)
            lat_slice = ds.sel(lat=slice(bounds['lat_max'], bounds['lat_min']))

        if lon_ascending:
            filtered_ds = lat_slice.sel(lon=slice(bounds['lon_min'], bounds['lon_max']))
        else:
            # Descending coordinates
            filtered_ds = lat_slice.sel(lon=slice(bounds['lon_max'], bounds['lon_min']))

        # Calculate reduction stats
        orig_lat_size = len(ds.lat)
        orig_lon_size = len(ds.lon)
        new_lat_size = len(filtered_ds.lat)
        new_lon_size = len(filtered_ds.lon)

        reduction_pct = (1 - (new_lat_size * new_lon_size) / (orig_lat_size * orig_lon_size)) * 100

        logger.info(f"📊 Spatial filtering applied:")
        logger.info(f"   Bounds: lat=[{bounds['lat_min']:.2f}, {bounds['lat_max']:.2f}], "
                   f"lon=[{bounds['lon_min']:.2f}, {bounds['lon_max']:.2f}]")
        logger.info(f"   Original grid: {orig_lat_size} lat × {orig_lon_size} lon = "
                   f"{orig_lat_size * orig_lon_size:,} points")
        logger.info(f"   Filtered grid: {new_lat_size} lat × {new_lon_size} lon = "
                   f"{new_lat_size * new_lon_size:,} points")
        logger.info(f"   Data reduction: {reduction_pct:.1f}%")

        return filtered_ds

    except Exception as e:
        logger.error(f"Failed to filter NetCDF by bounds: {e}")
        logger.warning("Returning original dataset without filtering")
        return ds


def filter_netcdf_by_polygon_mask(ds: xr.Dataset, geojson_data: Union[str, dict]) -> xr.Dataset:
    """
    Filter xarray Dataset by polygon mask (PRECISE method - slower).

    This method creates a boolean mask for each grid point and only keeps
    points that are actually inside the polygon. More accurate than bounding
    box filtering but significantly slower for large datasets.

    Args:
        ds: xarray Dataset with 'lat' and 'lon' coordinates
        geojson_data: GeoJSON polygon (string or dict)

    Returns:
        Filtered xarray Dataset (with NaN values outside polygon)

    Example:
        >>> geojson = {"type": "Feature", "geometry": {...}}
        >>> filtered_ds = filter_netcdf_by_polygon_mask(ds, geojson)
    """
    geojson_data = parse_geojson(geojson_data)

    try:
        # Handle FeatureCollection or single Feature
        if geojson_data.get('type') == 'FeatureCollection':
            features = geojson_data.get('features', [])
        elif geojson_data.get('type') == 'Feature':
            features = [geojson_data]
        else:
            features = [{'type': 'Feature', 'geometry': geojson_data}]

        # Combine all polygons into one geometry
        polygons = [shape(f.get('geometry', f)) for f in features]
        combined_polygon = unary_union(polygons)

        # Get lat/lon arrays
        lats = ds.lat.values
        lons = ds.lon.values

        # Create 2D coordinate meshgrid
        lon_grid, lat_grid = np.meshgrid(lons, lats)

        # Create mask (True for points inside polygon)
        logger.info("Creating polygon mask (this may take a moment)...")
        mask = np.zeros(lat_grid.shape, dtype=bool)

        total_points = lat_grid.size
        points_checked = 0

        for i in range(len(lats)):
            for j in range(len(lons)):
                point = Point(lon_grid[i, j], lat_grid[i, j])
                mask[i, j] = combined_polygon.contains(point)
                points_checked += 1

                # Progress logging for large datasets
                if points_checked % 1000 == 0:
                    progress = (points_checked / total_points) * 100
                    logger.debug(f"   Progress: {progress:.1f}% ({points_checked}/{total_points} points)")

        points_inside = mask.sum()
        points_outside = (~mask).sum()

        logger.info(f"📊 Polygon mask created:")
        logger.info(f"   Total grid points: {total_points:,}")
        logger.info(f"   Points inside polygon: {points_inside:,} ({points_inside/total_points*100:.1f}%)")
        logger.info(f"   Points outside polygon: {points_outside:,} ({points_outside/total_points*100:.1f}%)")

        # Apply mask to dataset (points outside become NaN)
        ds_masked = ds.where(mask, drop=False)  # drop=False keeps the grid structure

        # Optionally, drop all-NaN coordinates to reduce size
        # ds_masked = ds_masked.dropna(dim='lat', how='all').dropna(dim='lon', how='all')

        return ds_masked

    except Exception as e:
        logger.error(f"Failed to apply polygon mask: {e}")
        logger.warning("Returning original dataset without masking")
        return ds


def filter_netcdf_by_geojson(
    ds: xr.Dataset,
    geojson_data: Union[str, dict],
    method: str = 'bounds'
) -> xr.Dataset:
    """
    Filter xarray Dataset using GeoJSON polygon.

    Convenience function that wraps both filtering methods.

    Args:
        ds: xarray Dataset with 'lat' and 'lon' coordinates
        geojson_data: GeoJSON polygon (string or dict)
        method: 'bounds' (fast, bounding box) or 'mask' (slow, precise polygon)

    Returns:
        Filtered xarray Dataset

    Example:
        >>> # Fast bounding box filtering
        >>> filtered_ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')
        >>>
        >>> # Precise polygon masking
        >>> filtered_ds = filter_netcdf_by_geojson(ds, geojson, method='mask')
    """
    if method == 'bounds':
        bounds = get_polygon_bounds(geojson_data)
        return filter_netcdf_by_bounds(ds, bounds)
    elif method == 'mask':
        return filter_netcdf_by_polygon_mask(ds, geojson_data)
    else:
        raise ValueError(f"Unknown filtering method: {method}. Use 'bounds' or 'mask'")


def point_in_polygon(lat: float, lon: float, geojson_data: Union[str, dict]) -> bool:
    """
    Check if a point (lat, lon) is inside a GeoJSON polygon.

    Args:
        lat: Latitude of the point
        lon: Longitude of the point
        geojson_data: GeoJSON polygon (string or dict)

    Returns:
        True if point is inside polygon, False otherwise

    Example:
        >>> geojson = {"type": "Feature", "geometry": {...}}
        >>> is_inside = point_in_polygon(40.6, 22.7, geojson)
    """
    geojson_data = parse_geojson(geojson_data)

    try:
        # Handle FeatureCollection or single Feature
        if geojson_data.get('type') == 'FeatureCollection':
            features = geojson_data.get('features', [])
        elif geojson_data.get('type') == 'Feature':
            features = [geojson_data]
        else:
            features = [{'type': 'Feature', 'geometry': geojson_data}]

        # Combine all polygons into one geometry
        polygons = [shape(f.get('geometry', f)) for f in features]
        combined_polygon = unary_union(polygons)

        # Create point and check containment (use covers instead of contains to include boundary)
        point = Point(lon, lat)  # GeoJSON uses (lon, lat) order
        is_inside = combined_polygon.covers(point)
        return is_inside

    except Exception as e:
        logger.error(f"Failed to check point-in-polygon: {e}")
        return False


def validate_geojson_bounds(geojson_data: Union[str, dict], data_bounds: Dict[str, float]) -> Tuple[bool, str]:
    """
    Validate that GeoJSON polygon overlaps with available data bounds.

    NOTE: This function checks if the polygon has ANY overlap with data bounds.
    If polygon is completely outside data bounds, a warning is returned but
    filtering will still proceed (resulting in empty dataset).

    Args:
        geojson_data: GeoJSON polygon to validate
        data_bounds: Dict with lat_min, lat_max, lon_min, lon_max from actual data

    Returns:
        Tuple of (has_overlap: bool, message: str)

    Example:
        >>> data_bounds = {'lat_min': 40.4, 'lat_max': 40.9, 'lon_min': 22.5, 'lon_max': 22.9}
        >>> has_overlap, msg = validate_geojson_bounds(geojson, data_bounds)
        >>> if not has_overlap:
        ...     print(f"Warning: {msg}")
    """
    try:
        polygon_bounds = get_polygon_bounds(geojson_data)

        # Check if polygon completely outside data bounds (no overlap)
        no_overlap_lat = (polygon_bounds['lat_max'] < data_bounds['lat_min'] or
                          polygon_bounds['lat_min'] > data_bounds['lat_max'])
        no_overlap_lon = (polygon_bounds['lon_max'] < data_bounds['lon_min'] or
                          polygon_bounds['lon_min'] > data_bounds['lon_max'])

        if no_overlap_lat or no_overlap_lon:
            return False, (f"⚠️ Polygon is completely outside data bounds! "
                          f"Polygon: lat=[{polygon_bounds['lat_min']:.2f}, {polygon_bounds['lat_max']:.2f}], "
                          f"lon=[{polygon_bounds['lon_min']:.2f}, {polygon_bounds['lon_max']:.2f}] | "
                          f"Data: lat=[{data_bounds['lat_min']:.2f}, {data_bounds['lat_max']:.2f}], "
                          f"lon=[{data_bounds['lon_min']:.2f}, {data_bounds['lon_max']:.2f}]")

        # Check partial overlap (polygon extends beyond data bounds)
        partial_overlap = (polygon_bounds['lat_min'] < data_bounds['lat_min'] or
                          polygon_bounds['lat_max'] > data_bounds['lat_max'] or
                          polygon_bounds['lon_min'] < data_bounds['lon_min'] or
                          polygon_bounds['lon_max'] > data_bounds['lon_max'])

        if partial_overlap:
            return True, (f"ℹ️ Polygon partially outside data bounds - will be clipped to available data. "
                         f"Polygon: lat=[{polygon_bounds['lat_min']:.2f}, {polygon_bounds['lat_max']:.2f}], "
                         f"lon=[{polygon_bounds['lon_min']:.2f}, {polygon_bounds['lon_max']:.2f}]")

        return True, "✓ Polygon is within data bounds"

    except Exception as e:
        return False, f"Failed to validate polygon: {e}"


def process_geojson_complete(
    geojson_data: Union[str, dict],
    default_crop: str = "WHEAT"
) -> Dict:
    """
    Complete GeoJSON processing workflow for TRANSITION simulations.

    This convenience function extracts:
    1. Bounding box for spatial filtering
    2. Polygon metadata (centroids, areas, vertices)
    3. Farmer locations for --farmer-locations CLI argument

    Args:
        geojson_data: GeoJSON FeatureCollection from map drawing
        default_crop: Default crop type (WHEAT, MAIZE, SOLAR)

    Returns:
        Dict with:
        - bounds: Bounding box dict
        - metadata: List of polygon metadata
        - farmer_locations: List ready for CLI
        - farmer_locations_json: JSON string for CLI

    Example:
        >>> geojson = {"type": "FeatureCollection", "features": [...]}
        >>> result = process_geojson_complete(geojson, "WHEAT")
        >>> print(result['farmer_locations_json'])
        '[{"lat":40.5,"lon":22.7,"crop":"WHEAT"}]'
    """
    try:
        # Extract bounding box
        bounds = get_polygon_bounds(geojson_data)

        # Extract polygon metadata
        metadata = extract_polygon_metadata(geojson_data)

        # Extract farmer locations
        farmer_locations = extract_centroids_for_farmer_locations(geojson_data, default_crop)

        # Format for CLI
        farmer_locations_json = format_farmer_locations_json(farmer_locations)

        result = {
            'bounds': bounds,
            'metadata': metadata,
            'farmer_locations': farmer_locations,
            'farmer_locations_json': farmer_locations_json,
            'num_polygons': len(metadata)
        }

        logger.info(f"✅ Processed {len(metadata)} polygon(s) successfully")

        return result

    except Exception as e:
        logger.error(f"Failed to process GeoJSON: {e}")
        raise


# Example usage and testing
if __name__ == "__main__":
    # Example GeoJSON for Thessaloniki sub-region with MULTIPLE polygons
    example_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [22.6, 40.5],
                        [22.7, 40.5],
                        [22.7, 40.6],
                        [22.6, 40.6],
                        [22.6, 40.5]
                    ]]
                },
                "properties": {"name": "Field A"}
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [22.75, 40.55],
                        [22.85, 40.55],
                        [22.85, 40.65],
                        [22.75, 40.65],
                        [22.75, 40.55]
                    ]]
                },
                "properties": {"name": "Field B"}
            }
        ]
    }

    print("=" * 70)
    print("Testing Spatial Filter Module (Multi-Polygon Support)")
    print("=" * 70)

    print(f"\nExample GeoJSON with {len(example_geojson['features'])} polygons:")
    print(json.dumps(example_geojson, indent=2))

    # Test bounds extraction
    print("\n1. Extracting bounding box...")
    bounds = get_polygon_bounds(example_geojson)
    print(f"   Bounds: {bounds}")

    # Test validation
    print("\n2. Validating against data bounds...")
    thessaloniki_bounds = {'lat_min': 40.4, 'lat_max': 40.9, 'lon_min': 22.5, 'lon_max': 22.9}
    has_overlap, msg = validate_geojson_bounds(example_geojson, thessaloniki_bounds)
    print(f"   Valid: {has_overlap}")
    print(f"   Message: {msg}")

    # Test complete processing workflow
    print("\n3. Complete GeoJSON processing...")
    result = process_geojson_complete(example_geojson, "WHEAT")
    print(f"\n   Number of polygons: {result['num_polygons']}")
    print(f"\n   Polygon metadata:")
    for poly in result['metadata']:
        print(f"     - {poly['name']}: centroid at ({poly['centroid']['lat']}, {poly['centroid']['lon']}), area {poly['area_km2']} km²")

    print(f"\n   Farmer locations:")
    for loc in result['farmer_locations']:
        print(f"     - ({loc['lat']}, {loc['lon']}) - {loc['crop']}")

    print(f"\n   CLI format:")
    print(f"     --farmer-locations '{result['farmer_locations_json']}'")

    print("\n" + "=" * 70)
    print("✅ All tests completed successfully!")
    print("=" * 70)
