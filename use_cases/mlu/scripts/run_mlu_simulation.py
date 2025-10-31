"""
Run TRANSITION ML-ABM Simulation with Full Results Generation

Generates comprehensive interactive report including:
1. Map-based land suitability visualization
2. Suitability scores (past, current, projected)
3. Trade-off analysis (economic vs environmental)
4. Confidence measures from ensemble projections
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.mlu.models.landuse_model import LandUseModel
from use_cases.mlu.scripts.result_collector import ResultCollector
from use_cases.mlu.scripts.visualizer import ResultVisualizer
from use_cases.mlu.scripts.gis_visualizer_v2 import CleanGISVisualizer
from use_cases.mlu.scripts.ensemble_runner import EnsembleRunner
import time
from datetime import datetime


def run_simulation_with_results(
    scenario: str,
    n_years: int = 10,
    n_parcels: int = 15,  # Consistent default across all MLU cases
    n_farmers: int = None,  # DEPRECATED
    n_pv_installations: int = None,  # DEPRECATED
    output_dir: str = "results",
    data_path: str = None,  # REQUIRED: Must be passed from config
    n_collectives: int = 2,  # Multi-level ABM: community level
    n_markets: int = 1,  # Multi-level ABM: market level
    n_policies: int = 1,  # Multi-level ABM: policy level
    enable_multi_level: bool = True,  # Multi-level ABM enabled by default
    rl_policy = None,  # Optional RL policy for RL-02
    config = None,  # MLUConfig object (will load if None)
    skip_scenario_subdir: bool = False,  # If True, don't create scenario subdirectory
    geojson: dict = None,  # Optional GeoJSON polygon for spatial filtering
    farmer_locations: list = None  # NEW (2025-10-21): User-specified farmer locations
):
    """
    Run simulation and generate comprehensive results.

    Args:
        scenario: RCP scenario (rcp26, rcp45, rcp85)
        n_years: Number of years to simulate
        n_parcels: Number of land parcels (each decides: farm OR solar)
        n_farmers: DEPRECATED - for backward compatibility
        n_pv_installations: DEPRECATED - for backward compatibility
        output_dir: Directory for output files
        data_path: Path to PILOT_THESSALONIKI_DATA directory

    Returns:
        ResultCollector instance with all data
    """
    if data_path is None:
        raise ValueError("data_path is required! Pass it from config.yaml")

    print("=" * 80)
    # Load config if not provided
    if config is None:
        from use_cases.mlu.config_loader import load_config
        config = load_config()

    print(f"TRANSITION ML-ABM SIMULATION: {scenario.upper()}")
    print("=" * 80)

    # Initialize model
    print(f"\n1. Initializing model...")
    print(f"   - Data Path: {data_path}")
    print(f"   - Scenario: {scenario}")
    print(f"   - Land Parcels: {n_parcels} (each decides: farm OR solar)")
    print(f"   - Duration: {n_years} years")

    if enable_multi_level:
        print(f"\n   Multi-Level ABM Enabled:")
        print(f"   - Individual Level: {n_parcels} land parcels")
        print(f"   - Community Level: {n_collectives} collective(s)")
        print(f"   - Market Level: {n_markets} commodity market(s)")
        print(f"   - Policy Level: {n_policies} policymaker(s)")

    # Set start year based on scenario
    # Historical: 1990-2020 (ERA5 reanalysis past data)
    # Future RCP: 2021-2100 (climate projections)
    start_year = 1990 if scenario.lower() == "historical" else 2021

    # Set seed based on scenario for reproducibility
    # Historical: fixed seed (42) for reproducible baseline comparison
    # Future: random seed for stochastic variation
    seed = 42 if scenario.lower() == "historical" else None

    model = LandUseModel(
        data_path=data_path,
        crops=["WHEAT", "MAIZE"],
        scenario=scenario,
        n_parcels=n_parcels,
        n_farmers=n_farmers,  # Backward compatibility
        n_pv_installations=n_pv_installations,  # Backward compatibility
        n_collectives=n_collectives,  # Community level (farmer collectives)
        n_markets=n_markets,  # Market level (commodity pricing dynamics)
        n_policies=n_policies,  # Policy level (government interventions)
        lat_bounds=(config.lat_min, config.lat_max),  # Thessaloniki region (from config.yaml)
        lon_bounds=(config.lon_min, config.lon_max),  # Thessaloniki region (from config.yaml)
        start_year=start_year,
        seed=seed,  # Fixed seed for historical (reproducible), random for future
        use_land_parcels=True,  # NEW MODE: parcels decide farm vs solar
        enable_multi_level=enable_multi_level,  # Multi-Level ABM (controlled by CLI args)
        geojson=geojson,  # Optional GeoJSON polygon for spatial filtering
        rl_policy=rl_policy,  # RL-02: Optional RL policy for land-use decisions
        farmer_locations=farmer_locations  # NEW (2025-10-21): User-specified farmer locations
    )

    # Initialize result collector
    collector = ResultCollector(scenario=scenario, start_year=start_year)

    # Run simulation
    print(f"\n2. Running simulation...")
    start_time = time.time()

    for year_idx in range(n_years):
        year = start_year + year_idx
        print(f"   Year {year}...", end=" ", flush=True)

        # Step the model
        model.step()

        # Collect results
        collector.collect_step(model)

        print("✓")

    elapsed = time.time() - start_time
    print(f"\n   Simulation complete in {elapsed:.2f} seconds")

    # Export raw data
    print(f"\n3. Exporting raw data...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if skip_scenario_subdir:
        # output_dir already contains query-specific path (e.g., mlu_05_rcp26)
        output_path = Path(output_dir) / timestamp
    else:
        # Legacy behavior: add scenario subdirectory
        output_path = Path(output_dir) / scenario / timestamp
    output_path.mkdir(parents=True, exist_ok=True)

    collector.export_to_json(str(output_path / f"{scenario}_results.json"))
    collector.export_to_csv(str(output_path))

    # Generate comprehensive text report with initial characteristics (BEFORE summary stats)
    _generate_text_report(
        model=model,
        collector=collector,
        output_path=output_path,
        scenario=scenario,
        n_years=n_years,
        n_parcels=n_parcels,
        n_collectives=n_collectives,
        n_markets=n_markets,
        n_policies=n_policies
    )

    # Generate summary statistics
    print(f"\n5. Summary Statistics:")
    trade_offs = collector.calculate_trade_offs()

    print(f"\n   Economic Metrics:")
    print(f"     Total Income: €{trade_offs['economic']['total_income']:,.2f}")
    print(f"     Avg Farmer Income: €{trade_offs['economic']['avg_income']:,.2f}/year")
    print(f"     Total Production: {trade_offs['economic']['total_production']:,.2f} tons")
    print(f"     Avg Yield: {trade_offs['economic']['avg_yield']:.2f} tons/ha")

    print(f"\n   Environmental Metrics:")
    print(f"     Avg Soil Quality: {trade_offs['environmental']['avg_soil_quality']:.2f}")
    print(f"     Crop Diversity: {trade_offs['environmental']['crop_diversity']:.3f}")

    print(f"\n   Trade-off Score: {trade_offs['trade_off_score']:,.2f}")

    # Store model reference for agent characteristics display
    collector.model = model

    # Store timestamped output path for visualizations
    collector.output_path = str(output_path)

    return collector


def run_multi_scenario_analysis(
    scenarios: list = ['rcp26', 'rcp45', 'rcp85'],
    n_years: int = 10,
    n_parcels: int = 15,  # Consistent default across all MLU cases
    n_farmers: int = None,  # DEPRECATED
    n_pv_installations: int = None,  # DEPRECATED
    output_dir: str = "results",
    data_path: str = None,  # REQUIRED: Must be passed from config
    enable_ensemble: bool = False,  # NEW: Enable Monte Carlo ensemble
    ensemble_size: int = 30,  # NEW: Number of ensemble runs
    confidence_level: float = 0.95,  # NEW: Confidence level for uncertainty
    n_collectives: int = 2,  # Multi-level ABM: community level
    n_markets: int = 1,  # Multi-level ABM: market level
    n_policies: int = 1,  # Multi-level ABM: policy level
    enable_multi_level: bool = True,  # Multi-level ABM enabled by default
    rl_policy = None,  # Optional RL policy for RL-02
    config = None,  # MLUConfig object (will load if None)
    geojson: dict = None,  # GeoJSON for spatial filtering
    farmer_locations: list = None  # NEW (2025-10-21): User-specified farmer locations
):
    """
    Run simulations for multiple scenarios and generate comparative analysis.

    Args:
        scenarios: List of RCP scenarios
        n_years: Number of years to simulate
        n_parcels: Number of land parcels (each decides: farm OR solar)
        n_farmers: DEPRECATED - for backward compatibility
        n_pv_installations: DEPRECATED - for backward compatibility
        output_dir: Directory for output files
        enable_ensemble: Enable probabilistic Monte Carlo ensemble runs
        ensemble_size: Number of stochastic realizations per scenario
        confidence_level: Confidence level for uncertainty bands (e.g., 0.95)
        data_path: Path to PILOT_THESSALONIKI_DATA

    Returns:
        Dict mapping scenario -> ResultCollector
    """
    # Load config if not provided
    if config is None:
        from use_cases.mlu.config_loader import load_config
        config = load_config()

    print("\n" + "=" * 80)
    print("MULTI-SCENARIO ANALYSIS")
    print("=" * 80)

    results_by_scenario = {}
    data_path_used = data_path  # Store for GIS visualizer

    # Run each scenario (with or without ensemble)
    if enable_ensemble:
        # Monte Carlo ensemble mode
        print(f"\n🎲 Monte Carlo Ensemble Mode:")
        print(f"   - Ensemble Size: {ensemble_size} runs per scenario")
        print(f"   - Confidence Level: {confidence_level*100:.0f}%")

        ensemble_runner = EnsembleRunner(ensemble_size, confidence_level)

        for scenario in scenarios:
            print(f"\n{'='*80}")
            print(f"Running ensemble for {scenario.upper()} ({ensemble_size} realizations)")
            print(f"{'='*80}")

            ensemble_stats = ensemble_runner.run_ensemble(
                simulation_func=run_simulation_with_results,
                scenario=scenario,
                n_years=n_years,
                n_parcels=n_parcels,
                output_dir=output_dir,
                data_path=data_path,
                n_collectives=n_collectives,
                n_markets=n_markets,
                n_policies=n_policies,
                enable_multi_level=enable_multi_level,
                config=config,
                geojson=geojson,
                farmer_locations=farmer_locations
            )
            results_by_scenario[scenario] = ensemble_stats

            # Print probabilistic summary
            print(f"\n📊 Probabilistic Results for {scenario.upper()}:")
            print(f"   Solar PV Adoption: {ensemble_stats['probabilistic_statements']['solar_pv_adoption']}")
            print(f"   Total Income: {ensemble_stats['probabilistic_statements']['total_income']}")
    else:
        # Single run mode (existing behavior)
        for scenario in scenarios:
            collector = run_simulation_with_results(
                scenario=scenario,
                n_years=n_years,
                n_parcels=n_parcels,
                n_pv_installations=n_pv_installations,
                output_dir=output_dir,
                data_path=data_path,
                n_collectives=n_collectives,
                n_markets=n_markets,
                n_policies=n_policies,
                enable_multi_level=enable_multi_level,
                rl_policy=rl_policy,
                config=config,
                geojson=geojson,
                farmer_locations=farmer_locations
            )
            results_by_scenario[scenario] = collector

    # Generate visualizations for each scenario (only in single-run mode)
    if not enable_ensemble:
        print("\n" + "=" * 80)
        print("GENERATING VISUALIZATIONS")
        print("=" * 80)

        viz_output = Path(output_dir) / "visualizations"
        viz_output.mkdir(parents=True, exist_ok=True)

        for scenario, collector in results_by_scenario.items():
            print(f"\n{scenario.upper()}:")

            # Generate Plotly visualizations
            visualizer = ResultVisualizer(collector)
            visualizer.save_all_visualizations(
                output_dir=str(viz_output),
                results_by_scenario=results_by_scenario
            )

            # Generate clean GIS maps with Folium (shadcn design)
            print(f"   🗺️  Generating GIS map (WHEAT + MAIZE)...")
            try:
                gis_viz = CleanGISVisualizer(collector, data_path_used)
                gis_viz.create_clean_map(
                    year=2021,  # First year
                    crops=['WHEAT', 'MAIZE'],
                    show_farmers=True,
                    output_file=str(viz_output / f'{scenario}_gis_map.html')
                )
                print(f"      ✅ GIS map saved: {scenario}_gis_map.html")
            except ImportError as e:
                print(f"      ⚠️  Folium not installed. Install with: uv pip install folium")
                print(f"      Skipping GIS map generation...")
            except Exception as e:
                print(f"      ⚠️  GIS map generation failed: {e}")
                import traceback
                traceback.print_exc()
    else:
        # Generate ensemble visualizations
        print("\n" + "=" * 80)
        print("GENERATING ENSEMBLE VISUALIZATIONS")
        print("=" * 80)

        from use_cases.mlu.scripts.ensemble_visualizer import EnsembleVisualizer

        # Generate policy recommendations FIRST (before visualizations need them)
        from use_cases.mlu.scripts.policy_recommender import PolicyRecommender

        recommender = PolicyRecommender(results_by_scenario)
        recommendations = recommender.generate_recommendations()
        recommender.print_recommendations(recommendations)

        # Save recommendations to JSON for use in visualizations
        import json
        recommendations_file = Path(output_dir) / 'policy_recommendations.json'
        with open(recommendations_file, 'w') as f:
            json.dump(recommendations, f, indent=2)
        print(f"\n   Policy recommendations saved to: {recommendations_file.absolute()}")

        # Generate ensemble visualizations (now with recommendations available)
        viz_output = Path(output_dir) / "ensemble_visualizations"
        viz_output.mkdir(parents=True, exist_ok=True)

        for scenario, ensemble_stats in results_by_scenario.items():
            visualizer = EnsembleVisualizer(ensemble_stats)
            visualizer.save_all_visualizations(
                str(viz_output),
                recommendations_file=str(recommendations_file)
            )

        print("\n" + "=" * 80)
        print("ENSEMBLE STATISTICS SAVED")
        print("=" * 80)
        print(f"\n   Ensemble statistics saved to: {Path(output_dir).absolute()}")
        print(f"   Files: *_ensemble_stats.json for each scenario")
        print(f"   Visualizations: {viz_output.absolute()}")

    # Generate comparative report (skip in ensemble mode - already printed)
    if not enable_ensemble:
        print("\n" + "=" * 80)
        print("COMPARATIVE ANALYSIS")
        print("=" * 80)

        print("\nScenario Comparison:")
        print(f"{'Scenario':<10} {'Avg Income':<15} {'Total Prod':<15} {'Diversity':<15}")
        print("-" * 60)

        for scenario, collector in results_by_scenario.items():
            trade_offs = collector.calculate_trade_offs()
            print(
                f"{scenario.upper():<10} "
                f"€{trade_offs['economic']['avg_income']:>12,.2f}  "
                f"{trade_offs['economic']['total_production']:>12,.2f}t  "
                f"{trade_offs['environmental']['crop_diversity']:>12.3f}"
            )

        # Calculate differences
        print("\nImpact of Climate Change (RCP85 vs RCP26):")
        if 'rcp26' in results_by_scenario and 'rcp85' in results_by_scenario:
            rcp26_trade = results_by_scenario['rcp26'].calculate_trade_offs()
            rcp85_trade = results_by_scenario['rcp85'].calculate_trade_offs()

            income_loss = rcp26_trade['economic']['avg_income'] - rcp85_trade['economic']['avg_income']
            income_loss_pct = (income_loss / rcp26_trade['economic']['avg_income']) * 100

            prod_loss = rcp26_trade['economic']['total_production'] - rcp85_trade['economic']['total_production']
            prod_loss_pct = (prod_loss / rcp26_trade['economic']['total_production']) * 100

            print(f"  Income Loss: €{income_loss:,.2f}/farmer/year ({income_loss_pct:.1f}%)")
            print(f"  Production Loss: {prod_loss:,.2f} tons ({prod_loss_pct:.1f}%)")

            # Policy recommendation
            print(f"\n  💡 Policy Recommendation:")
            print(f"     To maintain farmer income under RCP85, subsidies should increase by ~{income_loss_pct:.0f}%")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {Path(output_dir).absolute()}")

    if not enable_ensemble:
        viz_output = Path(output_dir) / "visualizations"
        print(f"Visualizations: {viz_output.absolute()}")

        print("\n📊 Interactive Reports Generated:")
        print("   - Land suitability maps (per scenario)")
        print("   - Time-series analysis (suitability evolution)")
        print("   - Scenario comparison dashboard")
        print("   - Trade-off analysis (economic vs environmental)")

        print("\n🗺️  GIS Maps Generated (Shadcn Design):")
        print("   - rcp26_gis_map.html (WHEAT + MAIZE layers)")
        print("   - rcp45_gis_map.html (WHEAT + MAIZE layers)")
        print("   - rcp85_gis_map.html (WHEAT + MAIZE layers)")
        print("   Features: Clean colorbars, OpenStreetMap, farmer parcels, layer toggle")

        print("\n🌍 Open the HTML files in your browser to explore the results!")
    else:
        print("\n📊 Ensemble Visualizations Generated:")
        print("   - Time-series with confidence bands (uncertainty visualization)")
        print("   - Probabilistic summary with error bars")
        print("   - Uncertainty dashboard (mean, median, min, max)")
        print(f"   - All charts show {confidence_level*100:.0f}% confidence intervals")

        print("\n📈 HTML Files Generated:")
        print("   - *_ensemble_timeseries.html (trends with uncertainty bands)")
        print("   - *_ensemble_summary.html (final year with error bars)")
        print("   - *_ensemble_dashboard.html (comprehensive uncertainty view)")
        print("   - *_qualitative_summary.html (environmental benefits + community impact)")

        print("\n📁 JSON Statistics:")
        print("   - *_ensemble_stats.json (machine-readable data)")

        print("\n🎲 Probabilistic Features:")
        print("   - Monte Carlo simulations with multiple stochastic realizations")
        print("   - Uncertainty quantification for all key metrics")
        print("   - Visual confidence bands for future projections")
        print("   - Statistically robust decision support")

        print("\n🌍 Open the HTML files in your browser to explore uncertainty!")

    return results_by_scenario


def _generate_text_report(model, collector, output_path, scenario, n_years, n_parcels, n_collectives, n_markets, n_policies):
    """
    Generate comprehensive text report with multi-level ABM initial characteristics.
    Similar to CCA text reports.

    Args:
        model: LandUseModel instance
        collector: ResultCollector instance
        output_path: Path object for output directory
        scenario: Climate scenario (rcp26/rcp45/rcp85)
        n_years: Number of simulation years
        n_parcels: Number of land parcels
        n_collectives: Number of collectives
        n_markets: Number of markets
        n_policies: Number of policymakers
    """
    from use_cases.mlu.utils.scenario_utils import get_scenario_display_name

    results_file = output_path / f"{scenario}_results.txt"
    scenario_display = get_scenario_display_name(scenario)

    # Get yearly statistics
    agent_df = collector.get_farmer_dataframe()  # Changed from get_agent_dataframe()
    yearly_stats = []
    for year in range(2021, 2021 + n_years):
        year_data = agent_df[agent_df['year'] == year]
        if not year_data.empty:
            # MLU uses 'crop' column (not 'current_crop')
            wheat_count = len(year_data[year_data['crop'] == 'WHEAT'])
            maize_count = len(year_data[year_data['crop'] == 'MAIZE'])
            # Solar PV has land_use='solar_pv' and crop is null/empty
            solar_count = len(year_data[year_data['land_use'] == 'solar_pv'])
            total_income = year_data['annual_income'].sum()
            total_production = year_data['total_production'].sum()

            yearly_stats.append({
                'year': year,
                'wheat': wheat_count,
                'maize': maize_count,
                'solar': solar_count,
                'total_income': total_income,
                'total_production': total_production
            })

    with open(results_file, 'w') as f:
        f.write(f"MLU Simulation Results - {scenario_display}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Simulation Duration: {n_years} years (2021-{2021 + n_years - 1})\n")
        f.write(f"\nMulti-Level ABM Configuration:\n")
        f.write(f"  - Individual Level: {n_parcels} land parcels\n")
        f.write(f"  - Community Level: {n_collectives} collective(s)\n")
        f.write(f"  - Market Level: {n_markets} commodity market(s)\n")
        f.write(f"  - Policy Level: {n_policies} policymaker(s)\n")
        f.write("\n")

        # Yearly Statistics
        f.write("Yearly Statistics:\n")
        f.write("-" * 60 + "\n")
        for stats in yearly_stats:
            f.write(f"Year {stats['year']}: "
                   f"WHEAT={stats['wheat']}, "
                   f"MAIZE={stats['maize']}, "
                   f"SOLAR={stats['solar']}, "
                   f"Income=€{stats['total_income']:,.0f}, "
                   f"Production={stats['total_production']:.1f}t\n")

        # Summary Statistics
        f.write("\n")
        f.write("=" * 60 + "\n")
        f.write("SUMMARY STATISTICS\n")
        f.write("=" * 60 + "\n\n")

        if yearly_stats:
            avg_income = sum(s['total_income'] for s in yearly_stats) / len(yearly_stats)
            avg_production = sum(s['total_production'] for s in yearly_stats) / len(yearly_stats)

            f.write(f"Economic Metrics (Average over {n_years} years):\n")
            f.write(f"  - Avg Total Income: €{avg_income:,.2f}/year\n")
            f.write(f"  - Avg Total Production: {avg_production:,.2f} tons/year\n\n")

            # Final year crop distribution
            final_year = yearly_stats[-1]
            f.write(f"Final Year ({final_year['year']}) Land Use Distribution:\n")
            f.write(f"  - WHEAT: {final_year['wheat']} parcels\n")
            f.write(f"  - MAIZE: {final_year['maize']} parcels\n")
            f.write(f"  - SOLAR PV: {final_year['solar']} parcels\n")

        # ===== MULTI-LEVEL ABM: INITIAL AGENT CHARACTERISTICS =====

        # Land Parcel Initial Characteristics (INDIVIDUAL LEVEL)
        if hasattr(model, 'parcel_agents') and model.parcel_agents:
            f.write("\n")
            f.write("=" * 60 + "\n")
            f.write(f"INDIVIDUAL LEVEL: LAND PARCEL INITIAL CHARACTERISTICS (All {len(model.parcel_agents)} Parcels)\n")
            f.write("=" * 60 + "\n\n")

            for parcel in model.parcel_agents:
                f.write(f"Parcel {parcel.unique_id}:\n")
                f.write(f"  - Location: ({parcel.lat:.4f}, {parcel.lon:.4f})\n")
                f.write(f"  - Land Size: {parcel.land_hectares:.1f} hectares\n")
                f.write(f"  - Soil pH: {parcel.soil_ph:.2f}\n")
                f.write(f"  - Soil Organic Carbon: {parcel.soil_organic_carbon:.2f}%\n")
                f.write(f"  - Elevation: {parcel.elevation:.0f}m\n")
                f.write(f"  - Current Land Use: {parcel.land_use if parcel.land_use else 'agriculture'}\n")
                f.write(f"  - Current Crop: {parcel.current_crop if parcel.current_crop else 'None'}\n")
                f.write("\n")

        # Collective Initial Characteristics (COMMUNITY LEVEL) - use captured initial state
        if hasattr(model, 'initial_characteristics') and 'collectives' in model.initial_characteristics:
            collectives_initial = model.initial_characteristics['collectives']
            f.write("=" * 60 + "\n")
            f.write(f"COMMUNITY LEVEL: COLLECTIVE INITIAL CHARACTERISTICS (All {len(collectives_initial)} Collectives)\n")
            f.write("=" * 60 + "\n\n")

            for collective_data in collectives_initial:
                f.write(f"{collective_data['name']}:\n")
                f.write(f"  - Number of Members: {collective_data['members']} parcels\n")
                f.write(f"  - Initial Collective Wealth: €{collective_data['wealth']:,.2f}\n")
                f.write(f"  - Initial Social Norms: {collective_data['social_norms'] if collective_data['social_norms'] else 'None'}\n")
                f.write(f"  - Knowledge Pool: {collective_data['knowledge_pool']} shared practices\n")
                f.write("\n")

        # Market Initial Characteristics (MARKET LEVEL) - use captured initial state
        if hasattr(model, 'initial_characteristics') and 'markets' in model.initial_characteristics:
            markets_initial = model.initial_characteristics['markets']
            f.write("=" * 60 + "\n")
            f.write(f"MARKET LEVEL: COMMODITY MARKET INITIAL CHARACTERISTICS (All {len(markets_initial)} Markets)\n")
            f.write("=" * 60 + "\n\n")

            for market_data in markets_initial:
                f.write(f"{market_data['name']}:\n")
                f.write(f"  - Crops Traded: {', '.join(market_data['crops'])}\n")
                f.write(f"  - Initial Prices:\n")
                for crop, price in market_data['prices'].items():
                    f.write(f"      • {crop}: €{price:.2f}/ton\n")
                f.write(f"  - Initial Demand:\n")
                for crop, demand in market_data['demand'].items():
                    f.write(f"      • {crop}: {demand:.2f} tons\n")
                f.write("\n")

        # Policymaker Initial Characteristics (POLICY LEVEL)
        if hasattr(model, 'policy_agents') and model.policy_agents:
            f.write("=" * 60 + "\n")
            f.write(f"POLICY LEVEL: POLICYMAKER INITIAL CHARACTERISTICS (All {len(model.policy_agents)} Policymakers)\n")
            f.write("=" * 60 + "\n\n")

            for policymaker in model.policy_agents:
                f.write(f"{policymaker.policy_name}:\n")
                f.write(f"  - Policy Goals: {policymaker.policy_goals}\n")
                f.write(f"  - Subsidy Rates: {policymaker.subsidy_rates if policymaker.subsidy_rates else 'None'}\n")
                f.write(f"  - Price Floors: {policymaker.price_floors if policymaker.price_floors else 'None'}\n")
                f.write("\n")

    print(f"\n4. Text Report Generated:")
    print(f"   📄 {results_file}")


if __name__ == "__main__":
    # Example 1: Single scenario
    # collector = run_simulation_with_results(
    #     scenario='rcp85',
    #     n_years=10,
    #     n_farmers=50,
    #     output_dir='results'
    # )

    # Example 2: Multi-scenario analysis (RECOMMENDED)
    results = run_multi_scenario_analysis(
        scenarios=['rcp26', 'rcp45', 'rcp85'],
        n_years=10,
        n_farmers=15,  # Example value for MLU multi-scenario (MLU default is 15 parcels)
        output_dir='results'
    )
