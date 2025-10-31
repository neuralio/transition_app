#!/usr/bin/env python3
"""
Test script for spatial filtering with real Thessaloniki data.

This script tests the GeoJSON polygon filtering on actual NetCDF files.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.data.loaders.data_loader import (
    load_temperature,
    load_crop_suitability,
    load_soil_type
)
from backend.data.loaders.spatial_filter import get_polygon_bounds


def test_spatial_filtering():
    """Test spatial filtering with sample polygon."""

    print("="*80)
    print("SPATIAL FILTERING TEST")
    print("="*80)

    # Data path
    data_path = "/app/data"

    # Sample GeoJSON polygon (smaller area within Thessaloniki)
    sample_geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [22.6, 40.5],  # Southwest
                    [22.8, 40.5],  # Southeast
                    [22.8, 40.7],  # Northeast
                    [22.6, 40.7],  # Northwest
                    [22.6, 40.5]   # Close polygon
                ]]
            },
            "properties": {"name": "Test Area"}
        }]
    }

    print(f"\n📍 Test Polygon:")
    bounds = get_polygon_bounds(sample_geojson)
    print(f"   Lat: {bounds['lat_min']:.2f} to {bounds['lat_max']:.2f}")
    print(f"   Lon: {bounds['lon_min']:.2f} to {bounds['lon_max']:.2f}")

    # Test 1: Load temperature data WITH filtering
    print(f"\n{'='*80}")
    print("TEST 1: Temperature Data (RCP45) with Spatial Filtering")
    print(f"{'='*80}")

    try:
        # Load WITHOUT filtering
        print("\nLoading temperature WITHOUT filtering...")
        ds_full = load_temperature(data_path, 'rcp45', geojson=None)
        print(f"   Full dataset: {len(ds_full.lat)} lat × {len(ds_full.lon)} lon = {len(ds_full.lat) * len(ds_full.lon)} points")

        # Load WITH filtering
        print("\nLoading temperature WITH GeoJSON filtering...")
        ds_filtered = load_temperature(data_path, 'rcp45', geojson=sample_geojson)
        print(f"   Filtered dataset: {len(ds_filtered.lat)} lat × {len(ds_filtered.lon)} lon = {len(ds_filtered.lat) * len(ds_filtered.lon)} points")

        reduction = (1 - (len(ds_filtered.lat) * len(ds_filtered.lon)) / (len(ds_full.lat) * len(ds_full.lon))) * 100
        print(f"\n   ✅ Data reduction: {reduction:.1f}%")

    except Exception as e:
        print(f"\n   ❌ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Load crop suitability WITH filtering
    print(f"\n{'='*80}")
    print("TEST 2: Crop Suitability (WHEAT, RCP45) with Spatial Filtering")
    print(f"{'='*80}")

    try:
        # Load WITHOUT filtering
        print("\nLoading WHEAT suitability WITHOUT filtering...")
        ds_full = load_crop_suitability(data_path, 'WHEAT', 'rcp45', filter_to_thessaloniki=False, geojson=None)
        print(f"   Full dataset: {len(ds_full.lat)} lat × {len(ds_full.lon)} lon = {len(ds_full.lat) * len(ds_full.lon)} points")

        # Load WITH filtering
        print("\nLoading WHEAT suitability WITH GeoJSON filtering...")
        ds_filtered = load_crop_suitability(data_path, 'WHEAT', 'rcp45', filter_to_thessaloniki=False, geojson=sample_geojson)
        print(f"   Filtered dataset: {len(ds_filtered.lat)} lat × {len(ds_filtered.lon)} lon = {len(ds_filtered.lat) * len(ds_filtered.lon)} points")

        reduction = (1 - (len(ds_filtered.lat) * len(ds_filtered.lon)) / (len(ds_full.lat) * len(ds_full.lon))) * 100
        print(f"\n   ✅ Data reduction: {reduction:.1f}%")

        # Show sample suitability score
        if 'suitability' in ds_filtered.data_vars:
            sample_score = float(ds_filtered['suitability'].isel(time=0, lat=0, lon=0).values)
            print(f"   Sample suitability score (first point, first time): {sample_score:.2f}")

    except Exception as e:
        print(f"\n   ❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Load soil data WITH filtering
    print(f"\n{'='*80}")
    print("TEST 3: Soil Type with Spatial Filtering")
    print(f"{'='*80}")

    try:
        # Load WITHOUT filtering
        print("\nLoading soil type WITHOUT filtering...")
        ds_full = load_soil_type(data_path, geojson=None)
        print(f"   Full dataset: {len(ds_full.lat)} lat × {len(ds_full.lon)} lon = {len(ds_full.lat) * len(ds_full.lon)} points")

        # Load WITH filtering
        print("\nLoading soil type WITH GeoJSON filtering...")
        ds_filtered = load_soil_type(data_path, geojson=sample_geojson)
        print(f"   Filtered dataset: {len(ds_filtered.lat)} lat × {len(ds_filtered.lon)} lon = {len(ds_filtered.lat) * len(ds_filtered.lon)} points")

        reduction = (1 - (len(ds_filtered.lat) * len(ds_filtered.lon)) / (len(ds_full.lat) * len(ds_full.lon))) * 100
        print(f"\n   ✅ Data reduction: {reduction:.1f}%")

    except Exception as e:
        print(f"\n   ❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*80}")
    print("✅ SPATIAL FILTERING TESTS COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    test_spatial_filtering()
