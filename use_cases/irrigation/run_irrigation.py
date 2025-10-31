#!/usr/bin/env python3
"""
Irrigation Use Case - Main CLI Entry Point

Usage:
    python use_cases/irrigation/run_irrigation.py --query irr_01 --geojson '{"type":"Polygon",...}' --start-date 2024-06-01 --end-date 2024-08-31
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.irrigation.queries import (
    query_irr_01_bare_soil_classification,
)
from use_cases.irrigation.queries_phenology import (
    query_irr_01_with_phenology,
)


def main():
    parser = argparse.ArgumentParser(
        description="EO-Informed Irrigation Simulation - Thessaloniki Region"
    )

    # Required arguments
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        choices=["irr_01"],  # Start with just one query for testing
        help="Query ID (e.g., irr_01 for bare soil classification)"
    )

    # EO data arguments (REQUIRED for irrigation)
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date for EO data (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date for EO data (YYYY-MM-DD)"
    )

    # Spatial arguments (polygon REQUIRED)
    parser.add_argument(
        "--geojson",
        type=str,
        help="GeoJSON polygon string (inline)"
    )
    parser.add_argument(
        "--geojson-file",
        type=str,
        help="Path to GeoJSON file"
    )

    # Simulation parameters
    parser.add_argument(
        "--parcels",
        type=int,
        default=20,
        help="Number of land parcels to simulate (default: 20, ignored if --parcel-locations provided)"
    )
    parser.add_argument(
        "--parcel-locations",
        type=str,
        default=None,
        help="JSON string with parcel coordinates: '[{\"lat\":40.5,\"lon\":22.7}]' (overrides random sampling)"
    )
    parser.add_argument(
        "--use-polygons",
        action="store_true",
        help="Use full polygon geometries for analysis (analyzes all pixels within each polygon)"
    )
    parser.add_argument(
        "--extract-centroids",
        action="store_true",
        help="Extract centroids from GeoJSON polygons as point locations (single point per polygon)"
    )

    # Multi-level ABM parameters
    parser.add_argument(
        "--collectives",
        type=int,
        default=1,
        help="Number of water cooperatives (default: 1)"
    )
    parser.add_argument(
        "--disable-multilevel",
        action="store_true",
        help="Disable multi-level ABM (individual farmers only)"
    )

    # Temporal phenology parameters (IRR-US-01 enhancement)
    parser.add_argument(
        "--enable-phenology",
        action="store_true",
        help="Enable temporal phenology analysis (time-series NDVI/NDWI to distinguish harvested from fallow)"
    )
    parser.add_argument(
        "--temporal-window-days",
        type=int,
        default=10,
        help="Temporal window size in days for phenology analysis (default: 10)"
    )

    args = parser.parse_args()

    # Validate date format
    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
        datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError:
        print("❌ Error: Dates must be in YYYY-MM-DD format")
        sys.exit(1)

    # Load GeoJSON or create from parcel locations
    geojson = None
    if args.geojson:
        try:
            geojson = json.loads(args.geojson)
        except json.JSONDecodeError:
            print("❌ Error: Invalid GeoJSON string")
            sys.exit(1)
    elif args.geojson_file:
        try:
            with open(args.geojson_file, 'r') as f:
                geojson = json.load(f)

            # Show spatial filter bounds like MLU/CCA/GCP
            from backend.data.loaders.spatial_filter import get_polygon_bounds
            bounds = get_polygon_bounds(geojson)
            print(f"   Spatial filter bounds: lat=[{bounds['lat_min']:.2f}, {bounds['lat_max']:.2f}], "
                  f"lon=[{bounds['lon_min']:.2f}, {bounds['lon_max']:.2f}]")
        except Exception as e:
            print(f"❌ Error loading GeoJSON file: {e}")
            sys.exit(1)
    elif args.parcel_locations:
        # Create bounding box polygon from coordinates (for NDVI download)
        try:
            coords = json.loads(args.parcel_locations)
            lats = [c['lat'] for c in coords]
            lons = [c['lon'] for c in coords]

            # Add 0.01 degree buffer (~1km) around points
            lat_min, lat_max = min(lats) - 0.01, max(lats) + 0.01
            lon_min, lon_max = min(lons) - 0.01, max(lons) + 0.01

            # Create bounding box polygon
            geojson = {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [lon_min, lat_min],
                            [lon_max, lat_min],
                            [lon_max, lat_max],
                            [lon_min, lat_max],
                            [lon_min, lat_min]
                        ]]
                    },
                    "properties": {"auto_generated": True}
                }]
            }
            print(f"📍 Auto-generated bounding box from coordinates: [{lat_min:.2f}, {lon_min:.2f}] to [{lat_max:.2f}, {lon_max:.2f}]")
            # Show spatial filter bounds like MLU/CCA/GCP
            print(f"   Spatial filter bounds: lat=[{lat_min:.2f}, {lat_max:.2f}], lon=[{lon_min:.2f}, {lon_max:.2f}]")
        except Exception as e:
            print(f"❌ Error creating bounding box from coordinates: {e}")
            sys.exit(1)
    else:
        print("❌ Error: Must provide --geojson, --geojson-file, or --parcel-locations")
        sys.exit(1)

    # Handle parcel locations and polygon mode
    parcel_locations = None
    use_polygon_geometries = args.use_polygons

    if args.parcel_locations:
        # User provided explicit coordinates
        try:
            parcel_locations = json.loads(args.parcel_locations)
            print(f"📍 Using {len(parcel_locations)} user-specified parcel location(s)")
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing --parcel-locations: {e}")
            sys.exit(1)
    elif args.use_polygons:
        # Use full polygon geometries from GeoJSON
        from backend.data.loaders.geojson_utils import extract_features
        features = extract_features(geojson)
        print(f"📍 Using {len(features)} polygon geometr(y/ies) for full-field analysis")
        # We'll pass the geojson directly and let queries.py handle multiple polygons
    elif args.extract_centroids:
        # Extract centroids from GeoJSON polygons
        from backend.data.loaders.geojson_utils import extract_polygon_metadata
        metadata = extract_polygon_metadata(geojson)
        parcel_locations = [
            {'lat': poly['centroid']['lat'], 'lon': poly['centroid']['lon']}
            for poly in metadata
        ]
        print(f"📍 Extracted {len(parcel_locations)} centroid(s) from polygon(s)")

    # Route to query function
    if args.query == "irr_01":
        # Check if phenology mode is enabled
        if args.enable_phenology:
            print("=" * 80)
            print("🌾 IRRIGATION USE CASE: Bare Soil Classification WITH TEMPORAL PHENOLOGY (IRR-US-01 Enhanced)")
            print("=" * 80)
            print(f"📅 Season Range: {args.start_date} to {args.end_date}")
            print(f"⏱️  Temporal Window: {args.temporal_window_days} days per observation")
            if use_polygon_geometries:
                from backend.data.loaders.geojson_utils import extract_features
                num_polygons = len(extract_features(geojson))
                print(f"📍 Mode: Full polygon analysis ({num_polygons} field(s))")
            elif parcel_locations:
                print(f"📍 Mode: User-specified coordinates ({len(parcel_locations)} parcels)")
            else:
                print(f"📍 Mode: Random sampling within polygon")
                print(f"🔢 Parcels: {args.parcels}")
            print("=" * 80)

            results = query_irr_01_with_phenology(
                geojson=geojson,
                start_date=args.start_date,
                end_date=args.end_date,
                n_parcels=args.parcels,
                parcel_locations=parcel_locations,
                use_polygon_geometries=use_polygon_geometries,
                temporal_window_days=args.temporal_window_days
            )

            if results.get("success"):
                print("\n✅ Temporal phenology analysis completed successfully!")
                print(f"\n📊 Phenology Results:")
                print(f"   - Total parcels analyzed: {len(results['parcels'])}")
                print(f"   - Temporal observations: {results['n_observations']}")
                print(f"   - Sentinel-2 scenes processed: {results['scenes_found']}")
                print(f"\n📁 Output Directory: {results['output_dir']}")
                print(f"   - Classification GeoJSON")
                print(f"   - Phenology report (text)")
                print(f"   - Time-series charts (HTML)")
                print(f"   - Pattern distribution chart (HTML)")
            else:
                print(f"\n❌ Error: {results.get('message')}")
                sys.exit(1)

        else:
            # Standard single-date classification
            print("=" * 80)
            print("🌾 IRRIGATION USE CASE: Bare Soil Classification (IRR-US-01)")
            print("=" * 80)
            print(f"📅 Date Range: {args.start_date} to {args.end_date}")
            if use_polygon_geometries:
                from backend.data.loaders.geojson_utils import extract_features
                num_polygons = len(extract_features(geojson))
                print(f"📍 Mode: Full polygon analysis ({num_polygons} field(s))")
            elif parcel_locations:
                print(f"📍 Mode: User-specified coordinates ({len(parcel_locations)} parcels)")
            else:
                print(f"📍 Mode: Random sampling within polygon")
                print(f"🔢 Parcels: {args.parcels}")
            print("=" * 80)

            results = query_irr_01_bare_soil_classification(
                geojson=geojson,
                start_date=args.start_date,
                end_date=args.end_date,
                n_parcels=args.parcels,
                parcel_locations=parcel_locations,
                use_polygon_geometries=use_polygon_geometries
            )

        if results.get("success"):
            print("\n✅ Classification completed successfully!")
            print(f"\n📊 Results (NDVI/NDWI Multi-Index Classification):")
            print(f"   - Total parcels analyzed: {results['total_parcels']}")
            print(f"   - Vegetated parcels: {results['vegetated_count']} ({results['vegetated_pct']:.1f}%)")
            print(f"   - Bare soil parcels: {results['bare_soil_count']} ({results['bare_soil_pct']:.1f}%)")
            print(f"   - Flooded parcels: {results['flooded_count']} ({results['flooded_pct']:.1f}%)")
            if results.get('no_data_count', 0) > 0:
                print(f"   - No data parcels: {results['no_data_count']}")

            # Mean index values
            print(f"\n📊 Mean Index Values:")
            if results['vegetated_count'] > 0:
                print(f"   - Vegetated: NDVI={results['mean_ndvi_vegetated']:.3f}", end="")
                if results.get('mean_ndwi_vegetated') is not None:
                    print(f", NDWI={results['mean_ndwi_vegetated']:.3f}")
                else:
                    print()

            if results['bare_soil_count'] > 0:
                print(f"   - Bare Soil: NDVI={results['mean_ndvi_bare_soil']:.3f}", end="")
                if results.get('mean_ndwi_bare_soil') is not None:
                    print(f", NDWI={results['mean_ndwi_bare_soil']:.3f}")
                else:
                    print()

            if results['flooded_count'] > 0:
                print(f"   - Flooded: NDVI={results['mean_ndvi_flooded']:.3f}", end="")
                if results.get('mean_ndwi_flooded') is not None:
                    print(f", NDWI={results['mean_ndwi_flooded']:.3f}")
                else:
                    print()

            print(f"\n📁 Output Directory: {results['output_dir']}")
            print(f"\n📁 Output files:")
            print(f"   - Classification map (GeoJSON): {results['output_map']}")
            print(f"   - Summary report (TXT): {results['output_report']}")
            print(f"   - Pie chart (HTML): {results['output_pie_chart']}")
            if results.get('output_histogram'):
                print(f"   - NDVI histogram (HTML): {results['output_histogram']}")
            print(f"   - Interactive map (HTML): {results['output_interactive_map']}")
        else:
            print(f"\n❌ Error: {results.get('message', 'Unknown error')}")
            sys.exit(1)

    else:
        print(f"❌ Query {args.query} not yet implemented")
        sys.exit(1)


if __name__ == "__main__":
    main()
