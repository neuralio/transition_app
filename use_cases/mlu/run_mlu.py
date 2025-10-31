#!/usr/bin/env python3
"""
Convenience wrapper to run MLU (Use Case 3) simulation.

TWO MODES:
1. Query Mode (NEW): Execute specific user stories (MLU-01 through MLU-08)
2. Simulation Mode (EXISTING): Run full multi-level ABM simulations

Query Mode Usage (NEW - User Story Queries):
    python run_mlu.py --query mlu_01 --crop WHEAT --scenario rcp45  # MLU-01: Access LUSA
    python run_mlu.py --query mlu_04 --parcels 15 --scenario rcp45  # MLU-04: Categorize parcels
    python run_mlu.py --query mlu_05 --years 10 --parcels 15 --scenario rcp45  # MLU-05: Multi-Level ABM
    python run_mlu.py --query mlu_07 --crop WHEAT --scenario rcp45  # MLU-07: Historical benchmark
    python run_mlu.py --query mlu_08 --crop WHEAT  # MLU-08: Future climate scenarios

Simulation Mode Usage (EXISTING - Full ABM):
    python run_mlu.py                    # Run ALL scenarios + visualizations (default)
    python run_mlu.py --scenario rcp85   # Run single scenario only (no visualizations)
    python run_mlu.py --years 20         # Run 20-year simulation
    python run_mlu.py --config custom.yaml  # Use custom config file
"""

import sys
from pathlib import Path

# Add project root to Python path (go up 2 levels: mlu -> use_cases -> root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import scenario utilities
from use_cases.mlu.utils.scenario_utils import normalize_scenario, get_scenario_display_name

# Import and run
from use_cases.mlu.scripts.run_mlu_simulation import (
    run_simulation_with_results,
    run_multi_scenario_analysis
)
from use_cases.mlu.config_loader import load_config

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run MLU simulation (Case 3) - Two modes: Query or Full Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

Query Mode (User Story Queries):
  python run_mlu.py --query mlu_01 --crop WHEAT --scenario rcp45
  python run_mlu.py --query mlu_04 --parcels 15 --scenario rcp45
  python run_mlu.py --query mlu_05 --years 10 --parcels 15 --scenario rcp45
  python run_mlu.py --query mlu_07 --crop WHEAT --scenario rcp45
  python run_mlu.py --query mlu_08 --crop WHEAT

Simulation Mode (Full ABM - uses default from config):
  python run_mlu.py                    # Run all scenarios
  python run_mlu.py --scenario rcp45   # Run single scenario
  python run_mlu.py --years 20 --parcels 30  # Custom parameters
"""
    )

    # NEW: Query Mode arguments
    parser.add_argument("--query", default=None,
                       choices=['mlu_04', 'mlu_05', 'mlu_07', 'mlu_08'],
                       help="Execute specific user story query (mlu_04, mlu_05, mlu_07, mlu_08). "
                            "If set, runs in Query Mode instead of Full Simulation Mode.")
    parser.add_argument("--config", default=None,
                       help="Path to config YAML file (default: use_cases/mlu/config.yaml)")
    parser.add_argument("--crop", default=None,
                       choices=["WHEAT", "MAIZE"],
                       help="Crop type for query mode")
    parser.add_argument("--scenario", default=None,
                       help="Climate scenario: optimistic/moderate/pessimistic OR rcp26/rcp45/rcp85 OR historical (default: run all)")
    parser.add_argument("--years", type=int, default=None,
                       help="Number of years to simulate (default: from config)")
    parser.add_argument("--parcels", type=int, default=None,
                       help="Number of land parcels (each decides: farm OR solar) (default: from config)")
    parser.add_argument("--farmers", type=int, default=None,
                       help="DEPRECATED: Use --parcels instead")
    parser.add_argument("--pv", type=int, default=None,
                       help="DEPRECATED: Use --parcels instead")
    parser.add_argument("--output", default=None,
                       help="Output directory (default: from config)")
    parser.add_argument("--farmer-locations", type=str, default=None,
                       help="JSON string with farmer coordinates and crops: '[{\"lat\":40.5,\"lon\":22.7,\"crop\":\"WHEAT\"}]'")
    parser.add_argument("--ensemble", action="store_true",
                       help="Enable Monte Carlo ensemble mode with probabilistic uncertainty (uses config ensemble_size)")
    parser.add_argument("--no-ensemble", action="store_true",
                       help="Disable ensemble mode (run single simulation per scenario)")
    parser.add_argument("--ensemble-size", type=int, default=None,
                       help="Number of ensemble runs (overrides config, e.g., --ensemble-size 50)")

    # Multi-level ABM arguments
    parser.add_argument("--collectives", type=int, default=None,
                       help="Number of farmer collectives/cooperatives (default: from config, usually 2)")
    parser.add_argument("--markets", type=int, default=None,
                       help="Number of commodity markets (default: from config, usually 1)")
    parser.add_argument("--policies", type=int, default=None,
                       help="Number of policymaker agents (default: from config, usually 1)")
    parser.add_argument("--disable-multilevel", action="store_true",
                       help="Disable multi-level ABM (only use individual land parcel agents)")

    # Spatial filtering arguments
    parser.add_argument("--geojson", type=str, default=None,
                       help="Path to GeoJSON file or GeoJSON string for spatial filtering (polygon area of interest)")
    parser.add_argument("--geojson-file", type=str, default=None,
                       help="Path to GeoJSON file for spatial filtering (alternative to --geojson)")

    # RL-02: Adaptive Agricultural Agents
    parser.add_argument("--use-rl", action="store_true",
                       help="Use trained RL policy for land-use decisions (RL-02)")
    parser.add_argument("--rl-model", type=str, default="models/rl02/rl02_rcp45_final.zip",
                       help="Path to trained RL model (.zip for Stable-Baselines3)")

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Parse farmer locations if provided
    farmer_locations = None
    if args.farmer_locations:
        import json
        try:
            farmer_locations = json.loads(args.farmer_locations)
            print(f"📍 Loaded {len(farmer_locations)} user-specified farmer locations")
            for i, loc in enumerate(farmer_locations, 1):
                print(f"   {i}. {loc['crop']} at ({loc['lat']:.4f}, {loc['lon']:.4f})")

            # CRITICAL: Override parcels argument with number of user-specified locations
            if args.parcels is not None and args.parcels != len(farmer_locations):
                print(f"⚠️  WARNING: Ignoring --parcels={args.parcels} (using {len(farmer_locations)} user-specified locations)")
            args.parcels = len(farmer_locations)  # Override parcels

        except Exception as e:
            print(f"❌ ERROR: Invalid farmer locations JSON: {e}")
            sys.exit(1)

    # Load GeoJSON for spatial filtering - REQUIRED (unless user specifies exact coordinates)
    geojson_data = None

    # Check if GeoJSON is provided (allow bypass if farmer_locations specified)
    if not (args.geojson or args.geojson_file or farmer_locations):
        print(f"❌ ERROR: No spatial filter polygon provided!", file=sys.stderr)
        print(f"   Please draw a polygon on the map before running simulations.", file=sys.stderr)
        print(f"   Click 'Draw Polygon for Spatial Filtering' to select your area of interest.", file=sys.stderr)
        print(f"   OR specify exact coordinates with --farmer-locations", file=sys.stderr)
        sys.exit(1)

    # Auto-generate bounding box from farmer coordinates (like irrigation does)
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
            # Check if it's a file path or raw JSON string
            geojson_source = args.geojson or args.geojson_file

            # Check if geojson_source is a file path or JSON string
            import sys
            sys.stderr.write(f"🔍 DEBUG run_mlu: Processing GeoJSON source...\n")
            sys.stderr.flush()

            # Try to check if it's a file path (without calling exists() on long strings)
            is_file = False
            try:
                if len(geojson_source) < 260 and not geojson_source.strip().startswith('{'):
                    is_file = Path(geojson_source).exists()
            except (OSError, ValueError):
                pass

            if is_file:
                # Load from file
                print(f"📍 Loading GeoJSON from file: {geojson_source}")
                with open(geojson_source, 'r') as f:
                    geojson_data = json.load(f)
            else:
                # Try to parse as JSON string
                print(f"📍 Parsing GeoJSON string...")
                geojson_data = json.loads(geojson_source)

            # Validate GeoJSON against actual data bounds
            from backend.data.loaders.spatial_filter import validate_geojson_bounds, get_polygon_bounds

            # Get data bounds from config (MLUConfig uses properties, not dict access)
            data_bounds = {
                'lat_min': config.lat_min,
                'lat_max': config.lat_max,
                'lon_min': config.lon_min,
                'lon_max': config.lon_max
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
            print(f"   Spatial filter bounds: lat=[{bounds['lat_min']:.2f}, {bounds['lat_max']:.2f}], "
                  f"lon=[{bounds['lon_min']:.2f}, {bounds['lon_max']:.2f}]")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid GeoJSON format: {e}")
            print(f"   Using full Thessaloniki bounds instead.")
            geojson_data = None
        except Exception as e:
            print(f"❌ Failed to load GeoJSON: {e}")
            print(f"   Using full Thessaloniki bounds instead.")
            geojson_data = None

    # Normalize scenario name (convert optimistic/moderate/pessimistic to rcp26/45/85)
    if args.scenario and args.scenario != 'historical':
        try:
            original_scenario = args.scenario
            args.scenario = normalize_scenario(args.scenario)
            if original_scenario.lower() != args.scenario:
                display_name = get_scenario_display_name(args.scenario)
                print(f"ℹ️  '{original_scenario}' → {display_name}")
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    # ============================================================================
    # QUERY MODE (NEW): Execute specific user story queries
    # ============================================================================
    if args.query is not None:
        # Fix output_dir for query mode - make it relative to use_cases/mlu/
        if args.output is None:
            mlu_dir = Path(__file__).parent
            # Set default output for query mode (will be appended with query-specific subdir)
            default_query_output = str(mlu_dir / config.results_dir)
        else:
            default_query_output = args.output

        print(f"\n{'='*60}")
        print(f"MLU QUERY MODE")
        print(f"{'='*60}")
        print(f"Executing User Story: {args.query.upper()}")
        print(f"Data Path: {config.data_path}")
        print(f"{'='*60}\n")

        # Handle each query type
        if args.query == 'mlu_04':
            # MLU-04: Categorize Land Parcels Using AI
            n_parcels = args.parcels if args.parcels is not None else config.n_parcels
            year = args.years if args.years is not None else 2050  # Default year: 2050

            # Warning: MLU-04 ignores --crop parameter (it categorizes ALL options)
            if args.crop:
                print(f"⚠️  WARNING: MLU-04 categorizes parcels as WHEAT/MAIZE/SOLAR (compares ALL options).")
                print(f"⚠️  The --crop parameter is IGNORED for this query (categorization requires comparing all crops).")
                print()

            # If no scenario specified, run ALL scenarios with comparison
            if args.scenario is None:
                from use_cases.mlu.queries.mlu_04 import query_mlu_04_all_scenarios
                print("ℹ️  No scenario specified - running ALL scenarios with comparison!")
                result = query_mlu_04_all_scenarios(
                    data_path=config.data_path,
                    n_parcels=n_parcels,
                    year=year,
                    output_dir=default_query_output,
                    geojson=geojson_data,
                    farmer_locations=farmer_locations
                )
                print(f"\n✅ MLU-04 Complete! Check {result.get('comparison_output', 'results/mlu_04_comparison')}")
                sys.exit(0)  # Exit successfully after all scenarios
            else:
                # Single scenario mode
                from use_cases.mlu.queries.mlu_04 import query_mlu_04
                result = query_mlu_04(
                    data_path=config.data_path,
                    scenario=args.scenario,
                    n_parcels=n_parcels,
                    year=year,
                    output_dir=None,  # Let it use default: use_cases/mlu/results/mlu_04_{scenario}
                    geojson=geojson_data,
                    farmer_locations=farmer_locations
                )
                if result['status'] == 'error':
                    # Error already printed by query function with red box styling
                    sys.exit(1)
                sys.exit(0)

        elif args.query == 'mlu_05':
            # MLU-05: Simplified Multi-Level ABM with Dynamic Visualizations
            from use_cases.mlu.queries.mlu_05 import query_mlu_05

            n_parcels = args.parcels if args.parcels is not None else config.n_parcels
            n_years = args.years if args.years is not None else config.n_years

            # Warning: MLU-05 simulates ALL crops (ABM agents decide dynamically)
            if args.crop:
                print(f"⚠️  WARNING: MLU-05 is an Agent-Based Model where agents dynamically choose between WHEAT/MAIZE/SOLAR.")
                print(f"⚠️  The --crop parameter is IGNORED for this query (agents make their own decisions).")
                print()

            # If no scenario specified, run ALL scenarios
            if args.scenario is None:
                print("ℹ️  No scenario specified - running ALL scenarios!")
                scenarios = ['rcp26', 'rcp45', 'rcp85']
                results = {}
                for scen in scenarios:
                    print(f"\n🔄 Running {scen.upper()}...")
                    result = query_mlu_05(
                        data_path=config.data_path,
                        scenario=scen,
                        n_years=n_years,
                        n_parcels=n_parcels,
                        output_dir=None,  # Let it use default: use_cases/mlu/results/mlu_05_{scenario}
                        enable_multi_level=not args.disable_multilevel,
                        n_collectives=args.collectives if args.collectives is not None else config.multilevel['n_collectives'],
                        n_markets=args.markets if args.markets is not None else config.multilevel['n_markets'],
                        n_policies=args.policies if args.policies is not None else config.multilevel['n_policymakers'],
                        print_insights=False,  # Don't print individual insights - only comparison insights
                        geojson=geojson_data,  # Pass geojson for validation
                        farmer_locations=farmer_locations
                    )
                    if result['status'] == 'success':
                        results[scen] = result

                # Create comparison visualizations
                if len(results) > 1:
                    from use_cases.mlu.queries.mlu_05 import create_scenario_comparison
                    print(f"\n🎨 Creating scenario comparison visualizations...")
                    create_scenario_comparison(results, args.output)

                print(f"\n{'='*80}")
                print(f"✅ MLU-05 ALL SCENARIOS COMPLETE")
                print(f"{'='*80}")
                for scen, res in results.items():
                    print(f"  {scen.upper()}: {res['output_dir']}")
                print(f"Comparison charts: {args.output or 'results'}/mlu_05_comparison/")
                print(f"{'='*80}\n")
                sys.exit(0)
            else:
                # Single scenario mode
                result = query_mlu_05(
                    data_path=config.data_path,
                    scenario=args.scenario,
                    n_years=n_years,
                    n_parcels=n_parcels,
                    output_dir=None,  # Let it use default: use_cases/mlu/results/mlu_05_{scenario}
                    enable_multi_level=not args.disable_multilevel,
                    n_collectives=args.collectives if args.collectives is not None else config.multilevel['n_collectives'],
                    n_markets=args.markets if args.markets is not None else config.multilevel['n_markets'],
                    n_policies=args.policies if args.policies is not None else config.multilevel['n_policymakers'],
                    geojson=geojson_data,  # Pass geojson for validation
                    farmer_locations=farmer_locations
                )
                if result['status'] == 'error':
                    # Error already printed by query function with red box styling
                    sys.exit(1)
                sys.exit(0)

        elif args.query == 'mlu_07':
            # MLU-07: Integrate Historical EO Data for Benchmarking
            # SIMPLE MODE: Directly loads and compares LUSA NetCDF files (no simulation)
            from use_cases.mlu.queries.mlu_07 import query_mlu_07

            # Determine which scenarios to run
            if args.scenario is None:
                # Default: all scenarios
                scenarios = ['historical', 'rcp26', 'rcp45', 'rcp85']
            else:
                # Single scenario: always include historical for comparison
                scenarios = ['historical', args.scenario] if args.scenario != 'historical' else ['historical']

            # Determine which crops to analyze
            if args.crop:
                crops = [args.crop]  # User specified crop
                print(f"ℹ️  Analyzing crop: {args.crop}")
            else:
                crops = ['WHEAT', 'MAIZE']  # Default: both crops
                print(f"ℹ️  No crop specified - analyzing both WHEAT and MAIZE")

            result = query_mlu_07(
                data_path=config.data_path,
                scenarios=scenarios,
                crops=crops,
                output_dir=None,  # Let it use default: use_cases/mlu/results/mlu_07
                geojson=geojson_data,
                farmer_locations=farmer_locations
            )

            if result['status'] == 'error':
                print(f"\n❌ Error: {result['message']}")
                sys.exit(1)
            sys.exit(0)

        elif args.query == 'mlu_08':
            # MLU-08: Simulate Future Climate Scenarios with Uncertainty
            from use_cases.mlu.queries.mlu_08 import query_mlu_08

            # Determine which scenarios to run
            if args.scenario is None:
                # Default: all future scenarios
                scenarios = ['rcp26', 'rcp45', 'rcp85']
            else:
                # Single scenario
                scenarios = [args.scenario] if args.scenario != 'historical' else ['rcp26', 'rcp45', 'rcp85']

            # Determine which crops to analyze
            if args.crop:
                crops = [args.crop]  # User specified crop
                print(f"ℹ️  Analyzing crop: {args.crop}")
            else:
                crops = ['WHEAT', 'MAIZE']  # Default: both crops
                print(f"ℹ️  No crop specified - analyzing both WHEAT and MAIZE")

            # Determine ensemble mode for MLU-08
            ensemble_size = args.ensemble_size if args.ensemble_size is not None else config.ensemble_size
            if args.ensemble:
                enable_ensemble = True
            elif args.no_ensemble:
                enable_ensemble = False
            else:
                # Default: use config (enable if ensemble_size > 1)
                enable_ensemble = ensemble_size > 1

            result = query_mlu_08(
                data_path=config.data_path,
                scenarios=scenarios,
                crops=crops,
                output_dir=None,  # Let it use default: use_cases/mlu/results/mlu_08
                enable_ensemble=enable_ensemble,
                ensemble_size=ensemble_size,
                config=config,
                n_years=args.years,  # Pass CLI argument
                n_parcels=args.parcels,  # Pass CLI argument
                n_collectives=args.collectives,  # Pass CLI argument
                n_markets=args.markets,  # Pass CLI argument
                n_policies=args.policies,  # Pass CLI argument
                geojson=geojson_data,
                farmer_locations=farmer_locations
            )

            if result['status'] == 'error':
                print(f"\n❌ Error: {result['message']}")
                sys.exit(1)
            sys.exit(0)

        # All queries should be handled above with direct execution
        # If we reach here, something went wrong
        print(f"❌ ERROR: Query {args.query} not properly handled")
        sys.exit(1)

        # Exit (don't run simulation mode)
        sys.exit(0)

    # ============================================================================
    # SIMULATION MODE (EXISTING): Full multi-level ABM simulations
    # ============================================================================

    # Override config with CLI arguments (if provided)
    n_years = args.years if args.years is not None else config.n_years
    n_parcels = args.parcels if args.parcels is not None else config.n_parcels

    # Fix output_dir to be relative to use_cases/mlu/ (not project root)
    if args.output is not None:
        output_dir = args.output
    else:
        # Make results_dir relative to use_cases/mlu/ directory
        mlu_dir = Path(__file__).parent
        output_dir = str(mlu_dir / config.results_dir)

    ensemble_size = args.ensemble_size if args.ensemble_size is not None else config.ensemble_size

    # Multi-level ABM settings
    if args.disable_multilevel:
        enable_multi_level = False
        n_collectives = 0
        n_markets = 0
        n_policies = 0
    else:
        enable_multi_level = config.multilevel['enabled']
        n_collectives = args.collectives if args.collectives is not None else config.multilevel['n_collectives']
        n_markets = args.markets if args.markets is not None else config.multilevel['n_markets']
        n_policies = args.policies if args.policies is not None else config.multilevel['n_policymakers']

    # Determine ensemble mode
    if args.ensemble:
        enable_ensemble = True
    elif args.no_ensemble:
        enable_ensemble = False
    else:
        # Default: use config (enable if ensemble_size > 1)
        enable_ensemble = ensemble_size > 1

    # Handle backward compatibility
    if args.farmers is not None or args.pv is not None:
        print("⚠️  WARNING: --farmers and --pv are deprecated. Use --parcels instead.")
        print("   Each parcel will decide between farming or solar PV.\n")

    # Load RL policy if requested
    rl_policy = None
    if args.use_rl:
        from use_cases.mlu.rl.rl_policy import RLPolicy
        from pathlib import Path

        # Try multiple path resolution strategies
        rl_model_path = Path(args.rl_model)

        # Strategy 1: Absolute path or relative to current directory
        if rl_model_path.exists():
            pass  # Found it!
        # Strategy 2: Relative to this script's directory (use_cases/mlu/)
        elif (Path(__file__).parent / rl_model_path).exists():
            rl_model_path = Path(__file__).parent / rl_model_path
        # Strategy 3: Relative to rl/ subdirectory
        elif (Path(__file__).parent / "rl" / rl_model_path).exists():
            rl_model_path = Path(__file__).parent / "rl" / rl_model_path
        else:
            print(f"❌ ERROR: RL model not found: {args.rl_model}")
            print(f"   Searched in:")
            print(f"   - {Path(args.rl_model).absolute()}")
            print(f"   - {(Path(__file__).parent / args.rl_model).absolute()}")
            print(f"   - {(Path(__file__).parent / 'rl' / args.rl_model).absolute()}")
            print(f"\n   Train a model first with: cd use_cases/mlu/rl && python train_rl02.py")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"🤖 RL MODE ENABLED (RL-02: Adaptive Agricultural Agents)")
        print(f"{'='*60}")
        print(f"Using trained policy: {rl_model_path}")
        print(f"{'='*60}\n")

        rl_policy = RLPolicy(str(rl_model_path), framework="sb3")

    # Default: run all scenarios with visualizations
    if args.scenario is None:
        print(f"\n{'='*60}")
        print(f"TRANSITION MLU Multi-Scenario Analysis")
        print(f"{'='*60}")
        print(f"Data Path: {config.data_path}")
        print(f"Scenarios: {', '.join([s.upper() for s in config.scenarios])}")
        print(f"Duration:  {n_years} years")
        print(f"Land Parcels: {n_parcels} (each decides: farm OR solar)")
        print(f"Multi-Level ABM: {'✅ ENABLED' if enable_multi_level else '❌ DISABLED'}")
        if enable_multi_level:
            print(f"  - Individual Level: {n_parcels} land parcels")
            print(f"  - Community Level: {n_collectives} farmer collectives")
            print(f"  - Market Level: {n_markets} commodity markets")
            print(f"  - Policy Level: {n_policies} policymakers")
        print(f"Output:    {output_dir}/")
        if enable_ensemble:
            print(f"Mode:      🎲 Monte Carlo Ensemble ({ensemble_size} runs, {config.confidence_level*100:.0f}% CI)")
        else:
            print(f"Mode:      Single run per scenario")
        print(f"{'='*60}\n")

        run_multi_scenario_analysis(
            scenarios=config.scenarios,
            n_years=n_years,
            n_parcels=n_parcels,
            n_farmers=args.farmers,  # For backward compatibility
            n_pv_installations=args.pv,  # For backward compatibility
            output_dir=output_dir,
            data_path=config.data_path,
            enable_ensemble=enable_ensemble,
            ensemble_size=ensemble_size,
            confidence_level=config.confidence_level,
            n_collectives=n_collectives,
            n_markets=n_markets,
            n_policies=n_policies,
            enable_multi_level=enable_multi_level,
            rl_policy=rl_policy,
            config=config
        )
    else:
        # Single scenario (no visualizations)
        print(f"\n{'='*60}")
        print(f"TRANSITION MLU Single Scenario")
        print(f"{'='*60}")
        print(f"Data Path: {config.data_path}")
        print(f"Scenario:  {args.scenario.upper()}")
        print(f"Duration:  {n_years} years")
        print(f"Land Parcels: {n_parcels} (each decides: farm OR solar)")
        print(f"Multi-Level ABM: {'✅ ENABLED' if enable_multi_level else '❌ DISABLED'}")
        if enable_multi_level:
            print(f"  - Individual Level: {n_parcels} land parcels")
            print(f"  - Community Level: {n_collectives} farmer collectives")
            print(f"  - Market Level: {n_markets} commodity markets")
            print(f"  - Policy Level: {n_policies} policymakers")
        print(f"Output:    {output_dir}/")
        print(f"⚠️  Note: Use no --scenario flag to run all scenarios with visualizations")
        print(f"{'='*60}\n")

        run_simulation_with_results(
            scenario=args.scenario,
            n_years=n_years,
            n_parcels=n_parcels,
            n_farmers=args.farmers,  # For backward compatibility
            n_pv_installations=args.pv,  # For backward compatibility
            output_dir=output_dir,
            data_path=config.data_path,
            n_collectives=n_collectives,
            n_markets=n_markets,
            n_policies=n_policies,
            enable_multi_level=enable_multi_level,
            rl_policy=rl_policy,
            config=config
        )
