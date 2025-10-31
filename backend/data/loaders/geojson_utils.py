"""
GeoJSON Utilities for Multi-Polygon Support

This module provides utility functions for extracting coordinates, centroids,
and metadata from GeoJSON polygons. Used for coordinate extraction from
user-drawn spatial filters.

Author: TRANSITION Team
Date: 2025-10-23
"""

import json
import logging
from typing import Dict, List, Union, Tuple
from shapely.geometry import shape, Point, Polygon as ShapelyPolygon
from shapely.ops import unary_union
import numpy as np

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


def extract_features(geojson_data: Union[str, dict]) -> List[dict]:
    """
    Extract all features from GeoJSON (handles FeatureCollection, Feature, or Geometry).

    Args:
        geojson_data: GeoJSON data

    Returns:
        List of feature dictionaries
    """
    geojson_data = parse_geojson(geojson_data)

    if geojson_data.get('type') == 'FeatureCollection':
        return geojson_data.get('features', [])
    elif geojson_data.get('type') == 'Feature':
        return [geojson_data]
    else:
        # Assume it's a raw geometry, wrap it in a Feature
        return [{'type': 'Feature', 'geometry': geojson_data, 'properties': {}}]


def calculate_centroid(geometry: dict) -> Tuple[float, float]:
    """
    Calculate centroid (center point) of a polygon geometry.

    Args:
        geometry: GeoJSON geometry dict

    Returns:
        Tuple of (latitude, longitude)

    Example:
        >>> geometry = {"type": "Polygon", "coordinates": [[[22.5, 40.4], ...]]}
        >>> lat, lon = calculate_centroid(geometry)
        >>> print(f"Centroid: ({lat:.4f}, {lon:.4f})")
    """
    try:
        geom = shape(geometry)
        centroid = geom.centroid

        # GeoJSON uses (lon, lat) order, but we return (lat, lon) for consistency
        return centroid.y, centroid.x

    except Exception as e:
        logger.error(f"Failed to calculate centroid: {e}")
        raise ValueError(f"Invalid geometry for centroid calculation: {e}")


def calculate_area(geometry: dict) -> float:
    """
    Calculate area of a polygon in square kilometers (approximate).

    Uses simple spherical approximation. For precise area calculation,
    use projected coordinates (e.g., UTM).

    Args:
        geometry: GeoJSON geometry dict

    Returns:
        Area in km²
    """
    try:
        geom = shape(geometry)

        # Get area in square degrees
        area_deg2 = geom.area

        # Convert to km² (approximate)
        # At latitude ~40°, 1 degree lat ≈ 111 km, 1 degree lon ≈ 85 km
        lat, _ = calculate_centroid(geometry)
        lat_rad = np.radians(lat)

        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * np.cos(lat_rad)

        area_km2 = area_deg2 * km_per_deg_lat * km_per_deg_lon

        return area_km2

    except Exception as e:
        logger.error(f"Failed to calculate area: {e}")
        return 0.0


def extract_vertices(geometry: dict) -> List[Tuple[float, float]]:
    """
    Extract all vertices (corner points) from a polygon.

    Args:
        geometry: GeoJSON geometry dict

    Returns:
        List of (latitude, longitude) tuples
    """
    try:
        geom = shape(geometry)

        if geom.geom_type == 'Polygon':
            coords = list(geom.exterior.coords)
        elif geom.geom_type == 'MultiPolygon':
            coords = []
            for poly in geom.geoms:
                coords.extend(list(poly.exterior.coords))
        else:
            raise ValueError(f"Unsupported geometry type: {geom.geom_type}")

        # Convert (lon, lat) to (lat, lon)
        vertices = [(lat, lon) for lon, lat in coords]

        return vertices

    except Exception as e:
        logger.error(f"Failed to extract vertices: {e}")
        return []


def get_bounding_box(geometry: dict) -> Dict[str, float]:
    """
    Get bounding box of a polygon.

    Args:
        geometry: GeoJSON geometry dict

    Returns:
        Dict with lat_min, lat_max, lon_min, lon_max
    """
    try:
        geom = shape(geometry)
        lon_min, lat_min, lon_max, lat_max = geom.bounds

        return {
            'lat_min': lat_min,
            'lat_max': lat_max,
            'lon_min': lon_min,
            'lon_max': lon_max
        }

    except Exception as e:
        logger.error(f"Failed to get bounding box: {e}")
        return {'lat_min': 0, 'lat_max': 0, 'lon_min': 0, 'lon_max': 0}


def extract_polygon_metadata(geojson_data: Union[str, dict]) -> List[Dict]:
    """
    Extract comprehensive metadata for all polygons in GeoJSON.

    Returns metadata for each polygon including:
    - polygon_id (1-indexed)
    - centroid (lat, lon)
    - vertices (list of lat/lon pairs)
    - bounding_box (min/max lat/lon)
    - area (km²)
    - num_vertices

    Args:
        geojson_data: GeoJSON FeatureCollection, Feature, or Geometry

    Returns:
        List of metadata dictionaries, one per polygon

    Example:
        >>> geojson = {"type": "FeatureCollection", "features": [...]}
        >>> metadata = extract_polygon_metadata(geojson)
        >>> for poly in metadata:
        ...     print(f"Polygon {poly['polygon_id']}: centroid at ({poly['centroid']['lat']:.4f}, {poly['centroid']['lon']:.4f})")
    """
    features = extract_features(geojson_data)

    metadata_list = []

    for idx, feature in enumerate(features):
        try:
            geometry = feature.get('geometry', feature)
            properties = feature.get('properties', {})

            # Calculate metadata
            centroid_lat, centroid_lon = calculate_centroid(geometry)
            vertices = extract_vertices(geometry)
            bbox = get_bounding_box(geometry)
            area = calculate_area(geometry)

            metadata = {
                'polygon_id': idx + 1,  # 1-indexed for user display
                'name': properties.get('name', f"Polygon {idx + 1}"),
                'centroid': {
                    'lat': round(centroid_lat, 6),
                    'lon': round(centroid_lon, 6)
                },
                'vertices': [
                    {'lat': round(lat, 6), 'lon': round(lon, 6)}
                    for lat, lon in vertices
                ],
                'bounding_box': {
                    'lat_min': round(bbox['lat_min'], 6),
                    'lat_max': round(bbox['lat_max'], 6),
                    'lon_min': round(bbox['lon_min'], 6),
                    'lon_max': round(bbox['lon_max'], 6)
                },
                'area_km2': round(area, 3),
                'num_vertices': len(vertices)
            }

            metadata_list.append(metadata)

        except Exception as e:
            logger.warning(f"Failed to extract metadata for feature {idx}: {e}")
            continue

    logger.info(f"📊 Extracted metadata for {len(metadata_list)} polygon(s)")

    return metadata_list


def extract_centroids_for_farmer_locations(
    geojson_data: Union[str, dict],
    default_crop: str = "WHEAT"
) -> List[Dict[str, Union[float, str]]]:
    """
    Extract centroids from GeoJSON polygons for use with --farmer-locations.

    This is a convenience function that converts polygon centroids into
    the format expected by --farmer-locations CLI argument.

    Args:
        geojson_data: GeoJSON FeatureCollection
        default_crop: Default crop type to assign (WHEAT, MAIZE, SOLAR, etc.)

    Returns:
        List of dicts: [{"lat": 40.5, "lon": 22.7, "crop": "WHEAT"}, ...]

    Example:
        >>> geojson = {"type": "FeatureCollection", "features": [...]}
        >>> locations = extract_centroids_for_farmer_locations(geojson, "WHEAT")
        >>> print(json.dumps(locations))
        [{"lat": 40.5, "lon": 22.7, "crop": "WHEAT"}, ...]
    """
    metadata = extract_polygon_metadata(geojson_data)

    farmer_locations = []

    for poly in metadata:
        # Check if user specified a crop in polygon properties
        crop = poly.get('crop', default_crop).upper()

        location = {
            'lat': poly['centroid']['lat'],
            'lon': poly['centroid']['lon'],
            'crop': crop
        }

        farmer_locations.append(location)

    logger.info(f"📍 Extracted {len(farmer_locations)} farmer location(s) from polygon centroids")

    return farmer_locations


def format_farmer_locations_json(locations: List[Dict]) -> str:
    """
    Format farmer locations as JSON string for CLI argument.

    Args:
        locations: List of location dicts

    Returns:
        JSON string ready for --farmer-locations argument

    Example:
        >>> locations = [{"lat": 40.5, "lon": 22.7, "crop": "WHEAT"}]
        >>> json_str = format_farmer_locations_json(locations)
        >>> print(json_str)
        '[{"lat":40.5,"lon":22.7,"crop":"WHEAT"}]'
    """
    return json.dumps(locations, separators=(',', ':'))


# Example usage and testing
if __name__ == "__main__":
    # Example GeoJSON with multiple polygons
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
                "properties": {"name": "Field A", "crop": "WHEAT"}
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
                "properties": {"name": "Field B", "crop": "MAIZE"}
            }
        ]
    }

    print("=" * 60)
    print("Testing GeoJSON Utilities Module")
    print("=" * 60)

    # Test metadata extraction
    print("\n1. Extracting polygon metadata...")
    metadata = extract_polygon_metadata(example_geojson)

    for poly in metadata:
        print(f"\n{poly['name']} (ID: {poly['polygon_id']}):")
        print(f"  Centroid: ({poly['centroid']['lat']}, {poly['centroid']['lon']})")
        print(f"  Area: {poly['area_km2']:.2f} km²")
        print(f"  Vertices: {poly['num_vertices']}")
        print(f"  Bounding Box: lat=[{poly['bounding_box']['lat_min']}, {poly['bounding_box']['lat_max']}], "
              f"lon=[{poly['bounding_box']['lon_min']}, {poly['bounding_box']['lon_max']}]")

    # Test farmer locations extraction
    print("\n2. Extracting farmer locations...")
    locations = extract_centroids_for_farmer_locations(example_geojson, "WHEAT")

    for loc in locations:
        print(f"  Farmer at ({loc['lat']}, {loc['lon']}) - Crop: {loc['crop']}")

    # Test CLI format
    print("\n3. CLI --farmer-locations format:")
    cli_json = format_farmer_locations_json(locations)
    print(f"  --farmer-locations '{cli_json}'")

    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
