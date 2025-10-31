#!/usr/bin/env python3
"""
Convenience wrapper to run GCP (Use Case 2: Green Credit Policy) simulation.

Usage Examples:
    # Query-based interface (aligned with CCA/MLU pattern)
    python run_gcp.py --query gcp_03 --scenario rcp45 --policy moderate_support  # GCP-03: PV adoption
    python run_gcp.py --query gcp_07 --scenario rcp45 --policy high_support      # GCP-07: Geographic distribution
    python run_gcp.py --query gcp_16 --scenario rcp45 --policy moderate_support  # GCP-16: Policy feedback loop

    # Multi-policy analysis
    python run_gcp.py --scenario rcp45                          # Run ALL policy scenarios for comparison
    python run_gcp.py --scenario rcp45 --policy low_support    # Run single policy scenario

    # Advanced parameters
    python run_gcp.py --query gcp_03 --scenario rcp45 --landowners 50 --years 15
    python run_gcp.py --query gcp_16 --scenario rcp85 --years 20  # Longer for feedback loop
"""

import sys
from pathlib import Path
import yaml

# Add project root to Python path (go up 2 levels: gcp -> use_cases -> root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import simulation functions
from use_cases.gcp.scripts.run_gcp_simulation import (
    run_simulation_with_results,
    run_multi_policy_analysis
)

# Import query functions
from use_cases.gcp.queries import query_gcp_03, query_gcp_03_all_policies, query_gcp_03_all_scenarios, query_gcp_07, query_gcp_16


def load_config():
    """Load GCP configuration file."""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run GCP simulation")

    # Query-based interface (aligned with CCA/MLU)
    parser.add_argument("--query", default=None,
                       choices=["gcp_03", "gcp_07", "gcp_16"],
                       help="User story query (GCP-03: PV adoption, GCP-07: geographic dist, GCP-16: feedback loop)")

    # Common arguments
    parser.add_argument("--scenario", default=None,
                       help="Climate scenario: rcp26/rcp45/rcp85 (default: run all scenarios)")
    parser.add_argument("--policy", "--policy-scenario", dest='policy_scenario', default=None,
                       help="Green credit policy: low_support/moderate_support/high_support (default: run all)")
    parser.add_argument("--years", type=int, default=10,
                       help="Number of years to simulate (default: 10, use 15+ for GCP-16)")
    parser.add_argument("--landowners", type=int, default=20,
                       help="Number of landowner agents (default: 20)")
    parser.add_argument("--financial-institutions", type=int, default=2,
                       help="Number of financial institution agents (default: 2)")
    parser.add_argument("--policymakers", type=int, default=1,
                       help="Number of policymaker agents (default: 1)")
    parser.add_argument("--output", default=None,
                       help="Output directory (default: use_cases/gcp/results/)")
    parser.add_argument("--data-path", default=None,
                       help="Path to data directory (default: from config.yaml)")

    # Polygon spatial filtering arguments
    parser.add_argument("--geojson", type=str, default=None,
                       help="Path to GeoJSON file or GeoJSON string for spatial filtering")
    parser.add_argument("--geojson-file", type=str, default=None,
                       help="Path to GeoJSON file for spatial filtering (alternative)")

    # User-specified landowner locations with initial crops (NEW - 2025-10-21)
    parser.add_argument("--farmer-locations", type=str, default=None,
                       help="JSON string with landowner coordinates and crops: '[{\"lat\":40.5,\"lon\":22.7,\"crop\":\"WHEAT\"}]'")

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    # Get data path from config if not provided
    if args.data_path is None:
        args.data_path = config.get('data', {}).get('base_path',
                                                     '/Users/theanomamouka/Desktop/TRANSITION/transition/backend/data/GCP')

    # Validate scenario (if provided)
    valid_scenarios = ['rcp26', 'rcp45', 'rcp85']
    if args.scenario and args.scenario.lower() not in valid_scenarios:
        print(f"❌ Error: Invalid scenario '{args.scenario}'")
        print(f"   Valid scenarios: {', '.join(valid_scenarios)}")
        sys.exit(1)

    # Validate policy scenario (if provided)
    valid_policies = ['low_support', 'moderate_support', 'high_support']
    if args.policy_scenario and args.policy_scenario.lower() not in valid_policies:
        print(f"❌ Error: Invalid policy scenario '{args.policy_scenario}'")
        print(f"   Valid policy scenarios: {', '.join(valid_policies)}")
        sys.exit(1)

    # Parse farmer locations (NEW - 2025-10-21)
    farmer_locations = None
    if args.farmer_locations:
        import json
        try:
            farmer_locations = json.loads(args.farmer_locations)
            print(f"📍 Loaded {len(farmer_locations)} user-specified landowner locations")
            for i, loc in enumerate(farmer_locations, 1):
                print(f"   {i}. {loc['crop']} at ({loc['lat']:.4f}, {loc['lon']:.4f})")

            # CRITICAL: Override landowners argument with number of user-specified locations
            if args.landowners is not None and args.landowners != len(farmer_locations):
                print(f"⚠️  WARNING: Ignoring --landowners={args.landowners} (using {len(farmer_locations)} user-specified locations)")
            args.landowners = len(farmer_locations)  # Override landowners

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

    # Auto-generate bounding box from landowner coordinates (like irrigation/MLU/CCA)
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

    # Query-based routing
    if args.query:
        # Handle missing parameters with defaults (scenarios/policies must be specified or default to "run all")
        if args.scenario is None:
            print(f"ℹ️  No climate scenario specified - will run ALL scenarios (rcp26, rcp45, rcp85)")
        if args.policy_scenario is None:
            print(f"ℹ️  No policy scenario specified - will run ALL policies (low_support, moderate_support, high_support)")

        if args.query == "gcp_03":
            # GCP-03: PV Adoption Simulation
            #  4 possible modes based on what user specifies:
            # 1. Both specified → Single combination
            # 2. Scenario only → All policies under that scenario
            # 3. Policy only → All scenarios under that policy
            # 4. Neither → All combinations (3 scenarios × 3 policies = 9)

            if args.scenario and args.policy_scenario:
                # Mode 1: Single combination
                print(f"\n{'='*80}")
                print(f"GCP-03: PV Adoption - Single Scenario/Policy")
                print(f"{'='*80}\n")
                result = query_gcp_03(
                    data_path=args.data_path,
                    scenario=args.scenario,
                    policy_scenario=args.policy_scenario,
                    n_years=args.years,
                    n_landowners=args.landowners,
                    n_financial_institutions=args.financial_institutions,
                    n_policymakers=args.policymakers,
                    output_dir=args.output,
                    geojson=geojson_data,
                    farmer_locations=farmer_locations
                )
                if result is None:
                    # Query crashed without returning anything
                    print(f"\n❌ ERROR: Simulation failed (missing data files or other error)")
                    sys.exit(1)
                elif result.get('status') == 'error':
                    # Error already printed by query function
                    sys.exit(1)

            elif args.scenario and not args.policy_scenario:
                # Mode 2: All policies under specified scenario
                print(f"\n{'='*80}")
                print(f"GCP-03: Policy Comparison under {args.scenario.upper()}")
                print(f"{'='*80}\n")
                query_gcp_03_all_policies(
                    data_path=args.data_path,
                    scenario=args.scenario,
                    n_years=args.years,
                    n_landowners=args.landowners,
                    n_financial_institutions=args.financial_institutions,
                    n_policymakers=args.policymakers,
                    output_dir=args.output,
                    farmer_locations=farmer_locations
                )

            elif not args.scenario and args.policy_scenario:
                # Mode 3: All scenarios under specified policy
                print(f"\n{'='*80}")
                print(f"GCP-03: Climate Comparison under {args.policy_scenario}")
                print(f"{'='*80}\n")
                query_gcp_03_all_scenarios(
                    data_path=args.data_path,
                    policy_scenario=args.policy_scenario,
                    n_years=args.years,
                    n_landowners=args.landowners,
                    n_financial_institutions=args.financial_institutions,
                    n_policymakers=args.policymakers,
                    output_dir=args.output
                )

            else:
                # Mode 4: All combinations (3 × 3 = 9 simulations)
                print(f"\n{'='*80}")
                print(f"GCP-03: Full Matrix (All Scenarios × All Policies)")
                print(f"⚠️  Warning: This will run 9 simulations (3 scenarios × 3 policies)")
                print(f"{'='*80}\n")

                for scenario in ['rcp26', 'rcp45', 'rcp85']:
                    query_gcp_03_all_policies(
                        data_path=args.data_path,
                        scenario=scenario,
                        n_years=args.years,
                        n_landowners=args.landowners,
                        n_financial_institutions=args.financial_institutions,
                        n_policymakers=args.policymakers,
                        output_dir=args.output
                    )

        elif args.query == "gcp_07":
            # GCP-07: Geographic Distribution Visualization
            # GCP-07 requires BOTH scenario and policy (cannot visualize "all" on a single map)
            if not args.scenario:
                print(f"❌ ERROR: GCP-07 requires --scenario parameter")
                print(f"   Geographic map visualization needs a specific climate scenario.")
                print(f"   Use: --scenario rcp26 (optimistic), --scenario rcp45 (moderate), or --scenario rcp85 (pessimistic)")
                sys.exit(1)

            if not args.policy_scenario:
                print(f"❌ ERROR: GCP-07 requires --policy parameter")
                print(f"   Geographic map visualization needs a specific policy scenario.")
                print(f"   Use: --policy low_support, --policy moderate_support, or --policy high_support")
                sys.exit(1)

            print(f"\n{'='*80}")
            print(f"GCP-07: View Geographic Distribution of PV Adoption")
            print(f"{'='*80}\n")
            result = query_gcp_07(
                data_path=args.data_path,
                scenario=args.scenario,
                policy_scenario=args.policy_scenario,
                n_years=args.years,
                n_landowners=args.landowners,
                n_financial_institutions=args.financial_institutions,
                n_policymakers=args.policymakers,
                output_dir=args.output,
                geojson=geojson_data,
                farmer_locations=farmer_locations
            )
            if result is None:
                # Query crashed without returning anything
                print(f"\n❌ ERROR: Simulation failed (missing data files or other error)")
                sys.exit(1)
            elif result.get('status') == 'error':
                # Error already printed by query function
                sys.exit(1)

        elif args.query == "gcp_16":
            # GCP-16: Policy Feedback Loop Monitoring
            # GCP-16 requires scenario (automatically runs ALL policies)
            if not args.scenario:
                print(f"❌ ERROR: GCP-16 requires --scenario parameter")
                print(f"   Feedback loop analysis needs a specific climate scenario.")
                print(f"   Use: --scenario rcp26 (optimistic), --scenario rcp45 (moderate), or --scenario rcp85 (pessimistic)")
                print(f"\n   Note: GCP-16 automatically runs ALL policy scenarios (low, moderate, high support)")
                print(f"   The --policy flag is IGNORED if provided.")
                sys.exit(1)

            print(f"\n{'='*80}")
            print(f"GCP-16: Monitor Feedback Loop Between Policy and Financial Institutions")
            print(f"{'='*80}\n")

            # Recommend longer simulation for feedback loop
            if args.years < 10:
                print(f"⚠️  Warning: GCP-16 feedback loop analysis works best with 15+ years")
                print(f"   Current: {args.years} years - consider using --years 15\n")

            # Inform user if they specified policy (it will be ignored)
            if args.policy_scenario:
                print(f"ℹ️  Note: --policy flag is ignored for GCP-16")
                print(f"   GCP-16 automatically runs ALL policy scenarios for comprehensive comparison\n")

            result = query_gcp_16(
                data_path=args.data_path,
                scenario=args.scenario,
                policy_scenario=args.policy_scenario,  # Passed but ignored by query function
                n_years=args.years,
                n_landowners=args.landowners,
                n_financial_institutions=args.financial_institutions,
                n_policymakers=args.policymakers,
                output_dir=args.output,
                geojson=geojson_data,
                farmer_locations=farmer_locations
            )
            if result is None:
                # Query crashed without returning anything
                print(f"\n❌ ERROR: Simulation failed (missing data files or other error)")
                sys.exit(1)
            elif result.get('status') == 'error':
                # Error already printed by query function
                sys.exit(1)

    # Multi-policy analysis (run all policy scenarios for comparison)
    elif args.policy_scenario is None:
        print(f"\n{'='*80}")
        print(f"TRANSITION GCP Multi-Policy Analysis")
        print(f"{'='*80}")
        print(f"Use Case:  Green Credit Policy (UC-GCP)")
        print(f"Climate Scenario: {args.scenario.upper()}")
        print(f"Policy Scenarios: low_support, moderate_support, high_support")
        print(f"Duration:  {args.years} years")
        print(f"Landowners: {args.landowners}")
        print(f"Financial Institutions: {args.financial_institutions}")
        print(f"Data:      {args.data_path}")
        print(f"Output:    {args.output if args.output else 'use_cases/gcp/results/'}")
        print(f"{'='*80}\n")

        run_multi_policy_analysis(
            scenario=args.scenario,
            policy_scenarios=['low_support', 'moderate_support', 'high_support'],
            n_years=args.years,
            n_landowners=args.landowners,
            n_financial_institutions=args.financial_institutions,
            n_policymakers=args.policymakers,
            output_dir=args.output if args.output else 'use_cases/gcp/results',
            data_path=args.data_path,
            config_path=None
        )

    # Single policy scenario
    else:
        print(f"\n{'='*80}")
        print(f"TRANSITION GCP Single Policy Scenario")
        print(f"{'='*80}")
        print(f"Use Case:  Green Credit Policy (UC-GCP)")
        print(f"Climate Scenario: {args.scenario.upper()}")
        print(f"Policy Scenario: {args.policy_scenario}")
        print(f"Duration:  {args.years} years")
        print(f"Landowners: {args.landowners}")
        print(f"Financial Institutions: {args.financial_institutions}")
        print(f"Data:      {args.data_path}")
        print(f"Output:    {args.output if args.output else 'use_cases/gcp/results/'}")
        print(f"⚠️  Note: Omit --policy flag to run all policy scenarios with comparative analysis")
        print(f"{'='*80}\n")

        run_simulation_with_results(
            scenario=args.scenario,
            policy_scenario=args.policy_scenario,
            n_years=args.years,
            n_landowners=args.landowners,
            n_financial_institutions=args.financial_institutions,
            n_policymakers=args.policymakers,
            output_dir=args.output if args.output else 'use_cases/gcp/results',
            data_path=args.data_path,
            config_path=None
        )
