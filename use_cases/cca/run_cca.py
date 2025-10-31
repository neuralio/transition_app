#!/usr/bin/env python3
"""
Convenience wrapper to run CCA (Use Case 1: Climate Change Adaptation) simulation.

Usage Examples:
    # Query-based interface (aligned with MLU pattern)
    python run_cca.py --query cca_03 --crop WHEAT --scenario rcp45      # CCA-03: Crop yield
    python run_cca.py --query cca_04 --scenario rcp45 --pv-developers 2 # CCA-04: PV suitability
    python run_cca.py --query cca_10 --scenario rcp45 --farmers 20      # CCA-10: Cross-scale

    # Legacy interface (backward compatible)
    python run_cca.py                    # Run ALL scenarios + visualizations (default)
    python run_cca.py --scenario rcp85   # Run single scenario only
    python run_cca.py --years 30         # Run 30-year simulation (CCA focuses on long-term)
    python run_cca.py --validate         # Run historical validation (2010-2020, RMSE < 15% target)
    python run_cca.py --pv-developers 2  # Enable PV installation modeling (Option B)
"""

import sys
from pathlib import Path
import yaml

# Add project root to Python path (go up 2 levels: cca -> use_cases -> root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import scenario utilities
from use_cases.cca.utils.scenario_utils import normalize_scenario, get_scenario_display_name

# Import legacy functions
from use_cases.cca.scripts.run_cca_simulation import (
    run_simulation_with_results,
    run_multi_scenario_analysis,
    run_historical_validation
)

# Import query functions
from use_cases.cca.queries import query_cca_03, query_cca_04, query_cca_10


def load_config():
    """Load CCA configuration file."""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run CCA simulation")

    # Query-based interface (NEW - aligned with MLU)
    parser.add_argument("--query", default=None,
                       choices=["cca_03", "cca_04", "cca_10"],
                       help="User story query (CCA-03: crop yield, CCA-04: PV suitability, CCA-10: cross-scale)")
    parser.add_argument("--crop", default=None,
                       choices=["WHEAT", "MAIZE"],
                       help="Crop to focus on (for CCA-03, default: all crops)")

    # Common arguments
    parser.add_argument("--scenario", default=None,
                       help="Climate scenario: optimistic/moderate/pessimistic OR rcp26/rcp45/rcp85 (default: run all)")
    parser.add_argument("--years", type=int, default=10,
                       help="Number of years to simulate (default: 10)")
    parser.add_argument("--farmers", type=int, default=3,
                       help="Number of farmer agents (default: 3)")
    parser.add_argument("--pv-developers", type=int, default=0,
                       help="Number of PV developer agents (default: 0, set to 1+ to enable PV adoption)")
    parser.add_argument("--output", default=None,
                       help="Output directory (default: use_cases/cca/results/)")

    # Legacy arguments
    parser.add_argument("--validate", action="store_true",
                       help="Run historical validation (2010-2020) - RMSE < 15% target")
    parser.add_argument("--historical", action="store_true",
                       help="Include historical period (2000-2020) for validation")
    parser.add_argument("--data-path", default=None,
                       help="Path to data directory (default: from config.yaml)")

    # Multi-level ABM arguments
    parser.add_argument("--collectives", type=int, default=None,
                       help="Number of collectives (default: from config)")
    parser.add_argument("--markets", type=int, default=None,
                       help="Number of markets (default: from config)")
    parser.add_argument("--policies", type=int, default=None,
                       help="Number of policymakers (default: from config)")

    # Polygon spatial filtering arguments
    parser.add_argument("--geojson", type=str, default=None,
                       help="Path to GeoJSON file or GeoJSON string for spatial filtering")
    parser.add_argument("--geojson-file", type=str, default=None,
                       help="Path to GeoJSON file for spatial filtering (alternative)")

    # User-specified farmer locations with initial crops (NEW - 2025-10-21)
    parser.add_argument("--farmer-locations", type=str, default=None,
                       help="JSON string with farmer coordinates and crops: '[{\"lat\":40.5,\"lon\":22.7,\"crop\":\"WHEAT\"}]'")

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    # Get data path from config if not provided
    if args.data_path is None:
        args.data_path = config.get('data', {}).get('base_path', '/app/data')

    # Normalize scenario name (convert optimistic/moderate/pessimistic to rcp26/45/85)
    if args.scenario:
        try:
            original_scenario = args.scenario
            args.scenario = normalize_scenario(args.scenario, use_case="cca")
            if original_scenario.lower() != args.scenario:
                display_name = get_scenario_display_name(args.scenario, use_case="cca")
                print(f"ℹ️  '{original_scenario}' → {display_name}")
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    # Parse farmer locations FIRST (NEW - 2025-10-21)
    farmer_locations = None
    if args.farmer_locations:
        import json
        try:
            farmer_locations = json.loads(args.farmer_locations)
            print(f"📍 Loaded {len(farmer_locations)} user-specified farmer locations")
            for i, loc in enumerate(farmer_locations, 1):
                print(f"   {i}. {loc['crop']} at ({loc['lat']:.4f}, {loc['lon']:.4f})")

            # CRITICAL: Override farmers argument with number of user-specified locations
            if args.farmers is not None and args.farmers != len(farmer_locations):
                print(f"⚠️  WARNING: Ignoring --farmers={args.farmers} (using {len(farmer_locations)} user-specified locations)")
            args.farmers = len(farmer_locations)  # Override farmers

        except Exception as e:
            print(f"❌ ERROR: Invalid farmer locations JSON: {e}")
            sys.exit(1)

    # Load GeoJSON - REQUIRED (unless user specifies exact coordinates)
    geojson_data = None

    # Check if GeoJSON is provided (allow bypass if farmer_locations specified)
    if not (args.geojson or args.geojson_file or farmer_locations):
        print(f"❌ ERROR: No spatial filter polygon provided!", file=sys.stderr)
        print(f"   Please draw a polygon on the map before running simulations.", file=sys.stderr)
        print(f"   Click 'Draw Polygon for Spatial Filtering' to select your area of interest.", file=sys.stderr)
        print(f"   OR specify exact coordinates with --farmer-locations", file=sys.stderr)
        sys.exit(1)

    # Auto-generate bounding box from farmer coordinates (like irrigation/MLU)
    if farmer_locations and not (args.geojson or args.geojson_file):
        import json
        print(f"📍 No polygon provided - auto-generating bounding box from coordinates...")

        lats = [loc['lat'] for loc in farmer_locations]
        lons = [loc['lon'] for loc in farmer_locations]

        # Add 0.01 degree buffer (~1km) around points
        lat_min, lat_max = min(lats) - 0.01, max(lats) + 0.01
        lon_min, lon_max = min(lons) - 0.01, max(lons) + 0.01

        # Create bounding box polygon
        geojson_data = {
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
        print(f"   Auto-generated bounding box: [{lat_min:.2f}, {lon_min:.2f}] to [{lat_max:.2f}, {lon_max:.2f}]")
        print(f"   Spatial filter bounds: lat=[{lat_min:.2f}, {lat_max:.2f}], lon=[{lon_min:.2f}, {lon_max:.2f}]")

    elif args.geojson or args.geojson_file:
        import json
        try:
            geojson_source = args.geojson or args.geojson_file
            if Path(geojson_source).exists():
                print(f"📍 Loading GeoJSON from file: {geojson_source}")
                with open(geojson_source, 'r') as f:
                    geojson_data = json.load(f)
            else:
                print(f"📍 Parsing GeoJSON string...")
                geojson_data = json.loads(geojson_source)

            # Validate GeoJSON against actual data bounds
            from backend.data.loaders.spatial_filter import validate_geojson_bounds, get_polygon_bounds

            # Get data bounds from config
            data_bounds = {
                'lat_min': config['region']['lat_min'],
                'lat_max': config['region']['lat_max'],
                'lon_min': config['region']['lon_min'],
                'lon_max': config['region']['lon_max']
            }

            is_valid, msg = validate_geojson_bounds(geojson_data, data_bounds)
            if not is_valid:
                print(f"❌ GeoJSON validation failed: {msg}", file=sys.stderr)
                print(f"❌ ERROR: Polygon is outside available data bounds!", file=sys.stderr)
                print(f"   Please draw a polygon inside the orange rectangle on the map.", file=sys.stderr)
                print(f"🛑 EXITING WITH ERROR CODE 1", file=sys.stderr)
                sys.exit(1)  # Exit immediately with error code

            print(f"✅ GeoJSON validated: {msg}")
            # Show bounds
            bounds = get_polygon_bounds(geojson_data)
            print(f"   Polygon bounds: Lat [{bounds['lat_min']:.2f}, {bounds['lat_max']:.2f}], Lon [{bounds['lon_min']:.2f}, {bounds['lon_max']:.2f}]")
        except Exception as e:
            print(f"❌ Error loading GeoJSON: {e}")
            print(f"   Falling back to full Thessaloniki region")
            geojson_data = None

    # Get multi-level params from config if not provided
    multilevel_config = config.get('multilevel', {})
    n_collectives = args.collectives if args.collectives is not None else multilevel_config.get('n_collectives', 2)
    n_markets = args.markets if args.markets is not None else multilevel_config.get('n_markets', 1)
    n_policies = args.policies if args.policies is not None else multilevel_config.get('n_policymakers', 1)

    # Query-based routing (NEW)
    if args.query:
        # CCA-03 and CCA-04 can run without scenario (run all scenarios for comparison)
        # CCA-10 requires scenario (cross-scale interactions need climate context)
        if args.query == "cca_10" and args.scenario is None:
            print(f"❌ ERROR: CCA-10 requires --scenario parameter (optimistic, moderate, or pessimistic)")
            print(f"❌ Cross-scale interactions need climate context. Please specify: optimistic, moderate, or pessimistic")
            print(f"❌ Example: Run cross-scale interactions with 20 farmers under moderate scenario")
            sys.exit(1)

        if args.query == "cca_03":
            # CCA-03: Crop Yield Under Climate Change
            # If no scenario specified, runs ALL scenarios for comparison (matches acceptance criteria)
            if args.scenario is None:
                print("ℹ️  No scenario specified - will run ALL scenarios for comparison")
            result = query_cca_03(
                data_path=args.data_path,
                scenario=args.scenario,  # Can be None (runs all scenarios)
                crop=args.crop,
                n_years=args.years,
                n_farmers=args.farmers,
                n_collectives=n_collectives,
                n_markets=n_markets,
                n_policies=n_policies,
                output_dir=None,  # Let it use default: use_cases/cca/results/cca_03
                geojson=geojson_data,
                farmer_locations=farmer_locations  # NEW (2025-10-21)
            )
            if result.get('status') == 'error':
                # Error already printed by query function
                sys.exit(1)

        elif args.query == "cca_04":
            # CCA-04: PV Suitability Evaluation
            # If no scenario specified, runs ALL scenarios for comparison (matches acceptance criteria)
            if args.scenario is None:
                print("ℹ️  No scenario specified - will run ALL scenarios for comparison")
            query_cca_04(
                data_path=args.data_path,
                scenario=args.scenario,  # Can be None (runs all scenarios)
                n_farmers=args.farmers,
                n_collectives=n_collectives,
                n_markets=n_markets,
                n_policies=n_policies,
                n_pv_developers=args.pv_developers,
                n_years=args.years,
                output_dir=None,  # Let it use default: use_cases/cca/results/cca_04
                geojson=geojson_data,
                farmer_locations=farmer_locations  # NEW (2025-10-21)
            )

        elif args.query == "cca_10":
            # CCA-10: Cross-Scale Interactions (scenario required - checked above)
            query_cca_10(
                data_path=args.data_path,
                scenario=args.scenario,
                n_years=args.years,
                n_farmers=args.farmers,
                n_collectives=n_collectives,
                n_markets=n_markets,
                n_policies=n_policies,
                n_pv_developers=args.pv_developers,
                output_dir=None,  # Let it use default: use_cases/cca/results/cca_10
                geojson=geojson_data,
                farmer_locations=farmer_locations  # NEW (2025-10-21)
            )

    # Historical validation mode
    elif args.validate:
        run_historical_validation(
            scenario=args.scenario if args.scenario else "rcp26",
            n_farmers=args.farmers,
            data_path=args.data_path,
            output_dir=f"{args.output}/validation"
        )
    # Default: run all scenarios with visualizations
    elif args.scenario is None:
        print(f"\n{'='*80}")
        print(f"TRANSITION CCA Multi-Scenario Analysis")
        print(f"{'='*80}")
        print(f"Use Case:  Climate Change Adaptation (UC-CCA-01)")
        print(f"Scenarios: RCP 2.6, RCP 4.5, RCP 8.5")
        print(f"Duration:  {args.years} years")
        print(f"Farmers:   {args.farmers}")
        if args.pv_developers > 0:
            print(f"PV Developers: {args.pv_developers} (energy companies)")
        print(f"Data:      {args.data_path}")
        print(f"Output:    {args.output}/")
        if args.historical:
            print(f"Historical Validation: ENABLED (2000-2020)")
        print(f"{'='*80}\n")

        run_multi_scenario_analysis(
            scenarios=['rcp26', 'rcp45', 'rcp85'],
            n_years=args.years,
            n_farmers=args.farmers,
            n_pv_developers=args.pv_developers,
            output_dir=args.output,
            data_path=args.data_path,
            include_historical=args.historical
        )
    else:
        # Single scenario
        print(f"\n{'='*80}")
        print(f"TRANSITION CCA Single Scenario")
        print(f"{'='*80}")
        print(f"Use Case:  Climate Change Adaptation (UC-CCA-01)")
        print(f"Scenario:  {args.scenario.upper()}")
        print(f"Duration:  {args.years} years")
        print(f"Farmers:   {args.farmers}")
        if args.pv_developers > 0:
            print(f"PV Developers: {args.pv_developers} (energy companies)")
        print(f"Data:      {args.data_path}")
        print(f"Output:    {args.output}/")
        if args.historical:
            print(f"Historical Validation: ENABLED (2000-2020)")
        print(f"⚠️  Note: Use no --scenario flag to run all scenarios with visualizations")
        print(f"{'='*80}\n")

        run_simulation_with_results(
            scenario=args.scenario,
            n_years=args.years,
            n_farmers=args.farmers,
            n_collectives=n_collectives,
            n_markets=n_markets,
            n_policies=n_policies,
            n_pv_developers=args.pv_developers,
            output_dir=args.output,
            data_path=args.data_path,
            include_historical=args.historical
        )
