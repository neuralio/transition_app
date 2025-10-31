"""
Run TRANSITION CCA (Climate Change Adaptation) Simulation

This script implements Use Case 1 (UC-CCA-01) from the TRANSITION deliverable D1.1.

Key Features:
- Multi-level ABM simulation (Individual, Community, Market, Policy)
- Climate change adaptation strategies
- Crop yield simulation under RCP scenarios
- PV installation decision modeling (Option B)
- Historical validation support (2000-2020)

Data Source: backend/data/CCA/
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.cca.models.landuse_model_cca import LandUseModel
from use_cases.cca.scripts.historical_validation import HistoricalValidator
from use_cases.cca.scripts.visualizations import generate_all_visualizations
from use_cases.cca.scripts.cross_scale_viz import generate_cross_scale_visualizations
from use_cases.cca.utils.scenario_utils import get_scenario_display_name


def run_simulation_with_results(
    scenario: str,
    n_years: int = 10,
    n_farmers: int = 3,
    n_collectives: int = 2,  # Multi-level ABM: community level
    n_markets: int = 1,  # Multi-level ABM: market level
    n_policies: int = 1,  # Multi-level ABM: policy level
    n_pv_developers: int = 0,
    output_dir: str = None,
    data_path: str = "backend/data/CCA",
    include_historical: bool = False,
    focus_crop: str = None,  # Optional crop to focus results on (WHEAT, MAIZE, or None for all)
    skip_crop_stats: bool = False,  # NEW: Skip crop statistics (for PV-focused simulations like CCA-04)
    geojson: dict = None,
    farmer_locations: list = None  # NEW (2025-10-21): User-specified farmer locations with crops
):
    """
    Run CCA simulation with comprehensive results tracking.

    Args:
        scenario: RCP scenario (rcp26, rcp45, rcp85)
        n_years: Number of years to simulate (default: 10, CCA typically uses 30-50)
        n_farmers: Number of farmer agents
        output_dir: Directory for output files (default: use_cases/cca/results)
        data_path: Path to CCA data directory
        include_historical: Include historical period (2000-2020) for validation
        focus_crop: Optional crop to focus results display on (WHEAT, MAIZE, or None for all crops)
        skip_crop_stats: Skip crop statistics section (for PV-focused simulations like CCA-04)

    Returns:
        Dict with simulation results
    """
    print("=" * 80)
    print(f"TRANSITION CCA SIMULATION: {scenario.upper()}")
    print("=" * 80)
    print(f"Use Case: Climate Change Adaptation (UC-CCA-01)")

    # Set default output directory (use_cases/cca/results)
    if output_dir is None:
        cca_dir = Path(__file__).parent.parent  # Go up to use_cases/cca/
        output_dir = str(cca_dir / "results")

    # If focus_crop specified but no farmer_locations, create farmer_locations with that crop
    # This ensures all farmers start with the requested crop (e.g., "simulate maize yield" → all farmers grow MAIZE)
    if focus_crop and farmer_locations is None:
        print(f"\n⚠️  Focus crop '{focus_crop}' specified - all farmers will start with {focus_crop}")
        print(f"   (Farmers will be assigned {focus_crop} as initial crop)\n")
        # We'll set farmer_locations=None and pass focus_crop to model instead
        # Model will handle this by setting initial_crop when creating farmers

    # Initialize model
    print(f"\n1. Initializing model...")
    print(f"   - Scenario: {scenario}")
    print(f"   - Farmers: {n_farmers}")
    print(f"   - Duration: {n_years} years")
    print(f"   - Data Path: {data_path}")
    if focus_crop:
        print(f"   - Focus Crop: {focus_crop} (all farmers start with this crop)")
    if include_historical:
        print(f"   - Historical Validation: ENABLED")

    # Convert relative path to absolute
    data_path_abs = str((Path(project_root) / data_path).resolve())

    # Auto-detect spatial bounds from data
    # Finds the intersection (smallest common area) across all data sources
    # (meteo, soil, DEM, crop suitability) where all datasets have valid data

    model = LandUseModel(
        data_path=data_path_abs,
        crops=["WHEAT", "MAIZE"],
        scenario=scenario,
        n_farmers=n_farmers,
        n_collectives=n_collectives,  # User-specified or default
        n_markets=n_markets,  # User-specified or default
        n_policies=n_policies,  # User-specified or default
        n_pv_developers=n_pv_developers,  # CCA: Energy companies for PV adoption
        lat_bounds=None,  # Auto-detect from data
        lon_bounds=None,  # Auto-detect from data
        start_year=2021,
        seed=None,  # Random seed for different locations each run
        enable_multi_level=True,  # Enable multi-level ABM
        auto_detect_bounds=True,  # Auto-detect spatial bounds (intersection of all data)
        auto_aggregate_temporal=True,  # Aggregate daily/monthly data to annual
        validate_temporal_range=True,  # Validate simulation years are in data range
        geojson=geojson,
        farmer_locations=farmer_locations,  # NEW (2025-10-21): User-specified coordinates
        focus_crop=focus_crop  # NEW: Pass focus_crop to model for initial crop assignment
    )

    print(f"\n   Multi-Level ABM Enabled:")
    print(f"   - Individual Level: {n_farmers} farmers")
    print(f"   - Community Level: {n_collectives} collective(s)")
    print(f"   - Market Level: {n_markets} commodity market(s)")
    if n_pv_developers > 0:
        print(f"   - Market Level (Energy): {n_pv_developers} PV developer(s)")
    print(f"   - Policy Level: {n_policies} policymaker agent(s)")

    # Run simulation
    print(f"\n2. Running simulation ({n_years} years)...")
    start_time = time.time()

    # Store results for basic reporting
    yearly_stats = []
    yearly_farmer_snapshots = []  # NEW: Store farmer state for all years

    for year_idx in range(n_years):
        year = 2021 + year_idx

        # Step the model
        model.step()

        # Collect basic stats
        farmer_agents = model.farmer_agents

        if farmer_agents:
            wheat_count = sum(1 for f in farmer_agents if f.current_crop == "WHEAT")
            maize_count = sum(1 for f in farmer_agents if f.current_crop == "MAIZE")

            # Calculate total income and production
            total_income = sum(getattr(f, 'annual_income', 0.0) for f in farmer_agents)
            total_production = sum(
                getattr(f, 'actual_yield', 0.0) * getattr(f, 'land_hectares', 10.0)
                for f in farmer_agents
            )

            yearly_stats.append({
                'year': year,
                'wheat_farmers': wheat_count,
                'maize_farmers': maize_count,
                'total_income': total_income,
                'total_production': total_production
            })

            # NEW: Capture farmer snapshot for visualization
            farmer_snapshot = []
            for f in farmer_agents:
                farmer_snapshot.append({
                    'id': f.unique_id,
                    'lat': f.lat,
                    'lon': f.lon,
                    'crop': f.current_crop,
                    'land_hectares': f.land_hectares,
                    'annual_income': getattr(f, 'annual_income', 0.0),
                    'actual_yield': getattr(f, 'actual_yield', 0.0),
                    'vulnerability_score': getattr(f, 'vulnerability_score', 0.5),
                    'adaptation_capacity': getattr(f, 'adaptation_capacity', 0.5),
                    # PV installation state (CCA Option B)
                    'has_pv_installation': getattr(f, 'has_pv_installation', False),
                    'pv_lease_income': getattr(f, 'pv_lease_income', 0.0),
                    'pv_installation_year': getattr(f, 'pv_installation_year', None)
                })

            yearly_farmer_snapshots.append({
                'year': year,
                'farmers': farmer_snapshot
            })

            print(f"   Year {year}: {wheat_count} WHEAT, {maize_count} MAIZE | "
                  f"Income: €{total_income:,.0f} | Production: {total_production:.1f} t")
        else:
            print(f"   Year {year}: No farmer data available")

    elapsed = time.time() - start_time
    print(f"\n   ✅ Simulation complete in {elapsed:.2f} seconds")

    # Print summary
    print(f"\n3. Summary Statistics:")
    if yearly_stats:
        avg_income = sum(s['total_income'] for s in yearly_stats) / len(yearly_stats)
        avg_production = sum(s['total_production'] for s in yearly_stats) / len(yearly_stats)

        print(f"\n   Economic Metrics (Avg over {n_years} years):")
        print(f"     Avg Total Income: €{avg_income:,.2f}/year")
        print(f"     Avg Total Production: {avg_production:,.2f} tons/year")

        # Crop distribution
        final_year = yearly_stats[-1]
        print(f"\n   Final Year ({final_year['year']}) Crop Distribution:")
        print(f"     WHEAT: {final_year['wheat_farmers']} farmers")
        print(f"     MAIZE: {final_year['maize_farmers']} farmers")

    # CCA: PV installation summary (if enabled)
    if n_pv_developers > 0 and hasattr(model, 'pv_developer_agents') and model.pv_developer_agents:
        print(f"\n   PV Installation Summary (CCA Option B):")
        for pv_dev in model.pv_developer_agents:
            print(f"     {pv_dev.company_name}:")
            print(f"       - Installations: {len(pv_dev.pv_installations)}")
            print(f"       - Total Capacity: {pv_dev.total_capacity_installed:,.0f} kW")
            print(f"       - Annual Revenue: €{pv_dev.annual_revenue:,.0f}")
            print(f"       - Investment Remaining: €{pv_dev.investment_capacity:,.0f}")
            if len(pv_dev.pv_installations) > 0:
                avg_roi = sum(inst['roi'] for inst in pv_dev.pv_installations) / len(pv_dev.pv_installations)
                print(f"       - Average ROI: {avg_roi:.2%}")

    # Export comprehensive results with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir) / scenario / timestamp
    output_path.mkdir(parents=True, exist_ok=True)

    results_file = output_path / f"{scenario}_results.txt"

    # Get user-friendly scenario name for display
    scenario_display = get_scenario_display_name(scenario, use_case="cca")

    with open(results_file, 'w') as f:
        f.write(f"CCA Simulation Results - {scenario_display}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Simulation Duration: {n_years} years (2021-{2021 + n_years - 1})\n")
        f.write(f"\nMulti-Level ABM Configuration:\n")
        f.write(f"  - Individual Level: {n_farmers} farmers\n")
        f.write(f"  - Community Level: {n_collectives} collective(s)\n")
        f.write(f"  - Market Level: {n_markets} commodity market(s)\n")
        if n_pv_developers > 0:
            f.write(f"  - Market Level (Energy): {n_pv_developers} PV developer(s)\n")
        f.write(f"  - Policy Level: {n_policies} policymaker(s)\n")
        f.write("\n")

        # Yearly Statistics (skip for PV-focused simulations)
        if not skip_crop_stats:
            f.write("Yearly Statistics:\n")
            f.write("-" * 60 + "\n")
            for stats in yearly_stats:
                if focus_crop:
                    # Show only the requested crop
                    crop_key = f"{focus_crop.lower()}_farmers"
                    crop_count = stats.get(crop_key, 0)
                    f.write(f"Year {stats['year']}: "
                           f"{focus_crop.upper()}={crop_count}, "
                           f"Income=€{stats['total_income']:,.0f}, "
                           f"Production={stats['total_production']:.1f}t\n")
                else:
                    # Show all crops
                    f.write(f"Year {stats['year']}: "
                           f"WHEAT={stats['wheat_farmers']}, "
                           f"MAIZE={stats['maize_farmers']}, "
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

                # Final year crop distribution (filtered by focus_crop if specified)
                final_year = yearly_stats[-1]
                f.write(f"Final Year ({final_year['year']}) Crop Distribution:\n")
                if focus_crop:
                    # Show only the requested crop
                    crop_key = f"{focus_crop.lower()}_farmers"
                    crop_count = final_year.get(crop_key, 0)
                    f.write(f"  - {focus_crop.upper()}: {crop_count} farmers\n")
                else:
                    # Show all crops
                    f.write(f"  - WHEAT: {final_year['wheat_farmers']} farmers\n")
                    f.write(f"  - MAIZE: {final_year['maize_farmers']} farmers\n")

        # ===== MULTI-LEVEL ABM: INITIAL CHARACTERISTICS =====

        # Farmer Initial Characteristics (INDIVIDUAL LEVEL - show ALL farmers)
        if hasattr(model, 'farmer_agents') and model.farmer_agents:
            f.write("\n")
            f.write("=" * 60 + "\n")
            f.write(f"INDIVIDUAL LEVEL: FARMER INITIAL CHARACTERISTICS (All {len(model.farmer_agents)} Farmers)\n")
            f.write("=" * 60 + "\n\n")

            # Show ALL farmers
            for farmer in model.farmer_agents:
                f.write(f"Farmer {farmer.unique_id}:\n")
                f.write(f"  - Location: ({farmer.lat:.4f}, {farmer.lon:.4f})\n")
                f.write(f"  - Farm Size: {farmer.land_hectares:.1f} hectares\n")
                f.write(f"  - Soil pH: {farmer.soil_ph:.2f}\n")
                f.write(f"  - Soil Organic Carbon: {farmer.soil_organic_carbon:.2f}%\n")
                f.write(f"  - Elevation: {farmer.elevation:.0f}m\n")
                f.write(f"  - Adaptation Capacity: {farmer.adaptation_capacity:.2f}\n")
                f.write(f"  - Initial Crop: {farmer.current_crop if farmer.current_crop else 'None (will decide)'}\n")
                f.write("\n")

        # Collective Initial Characteristics (COMMUNITY LEVEL)
        if hasattr(model, 'collective_agents') and model.collective_agents:
            f.write("=" * 60 + "\n")
            f.write(f"COMMUNITY LEVEL: COLLECTIVE INITIAL CHARACTERISTICS (All {len(model.collective_agents)} Collectives)\n")
            f.write("=" * 60 + "\n\n")

            for collective in model.collective_agents:
                f.write(f"{collective.region_name}:\n")
                f.write(f"  - Number of Members: {len(collective.members)} farmers\n")
                f.write(f"  - Member IDs: {[f.unique_id for f in collective.members]}\n")
                f.write(f"  - Initial Collective Wealth: €{collective.collective_wealth:,.2f}\n")
                f.write(f"  - Social Norms: {collective.social_norms if collective.social_norms else 'None (will develop)'}\n")
                f.write(f"  - Knowledge Pool: {len(collective.knowledge_pool)} shared practices\n")
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
                f.write(f"  - Initial Subsidy Rates: {policymaker.subsidy_rates if policymaker.subsidy_rates else 'None (will set)'}\n")
                f.write(f"  - Initial Price Floors: {policymaker.price_floors if policymaker.price_floors else 'None (market-driven)'}\n")
                f.write(f"  - PV Green Credit Rate: €{policymaker.pv_green_credit:.3f}/kWh\n")
                f.write(f"  - PV Installation Subsidy: {policymaker.pv_installation_subsidy:.1%}\n")
                f.write(f"  - Renewable Energy Target: {policymaker.renewable_energy_target:.1%}\n")
                f.write("\n")

        # PV Installation Summary
        if n_pv_developers > 0 and hasattr(model, 'pv_developer_agents') and model.pv_developer_agents:
            # First show initial company characteristics
            f.write("=" * 60 + "\n")
            f.write("ENERGY COMPANY INITIAL CHARACTERISTICS\n")
            f.write("=" * 60 + "\n\n")

            for pv_dev in model.pv_developer_agents:
                # Determine company size category
                initial_capacity = pv_dev.initial_investment_capacity
                if initial_capacity <= 3500000:
                    size_category = "Small"
                elif initial_capacity <= 6500000:
                    size_category = "Medium"
                else:
                    size_category = "Large"

                f.write(f"{pv_dev.company_name} ({size_category}):\n")
                f.write(f"  - Initial Investment Capacity: €{initial_capacity:,.0f}\n")
                f.write(f"  - PV Installation Cost: €{pv_dev.pv_cost_per_kw:.2f}/kW\n")
                f.write(f"  - System Lifetime: {pv_dev.pv_lifetime_years} years\n")
                f.write(f"  - Maintenance Rate: {pv_dev.maintenance_cost_rate:.2%}/year\n")
                f.write(f"  - Farmer Lease Payment: €{pv_dev.land_lease_rate:.2f}/ha/year\n")
                f.write("\n")

            # Then show simulation results
            f.write("=" * 60 + "\n")
            f.write("PV INSTALLATION SIMULATION RESULTS\n")
            f.write("=" * 60 + "\n\n")

            for pv_dev in model.pv_developer_agents:
                capital_deployed = pv_dev.initial_investment_capacity - pv_dev.investment_capacity

                f.write(f"{pv_dev.company_name}:\n")
                f.write(f"  - Installations: {len(pv_dev.pv_installations)}\n")
                f.write(f"  - Total Capacity: {pv_dev.total_capacity_installed:,.0f} kW\n")
                f.write(f"  - Capital Deployed: €{capital_deployed:,.0f}\n")
                f.write(f"  - Investment Remaining: €{pv_dev.investment_capacity:,.0f}\n")
                f.write(f"  - Annual Revenue: €{pv_dev.annual_revenue:,.0f}\n")

                if len(pv_dev.pv_installations) > 0:
                    avg_roi = sum(inst['roi'] for inst in pv_dev.pv_installations) / len(pv_dev.pv_installations)
                    f.write(f"  - Average ROI: {avg_roi:.2%} over {pv_dev.pv_lifetime_years} years\n")

                    # Installation details (belongs to this company)
                    f.write(f"\n  Installation Details ({pv_dev.company_name}):\n")
                    for i, inst in enumerate(pv_dev.pv_installations, 1):
                        f.write(f"    {i}. Farmer {inst['farmer_id']}: {inst['capacity_kw']:.0f} kW, "
                               f"ROI={inst['roi']:.1%}, Annual Profit=€{inst['annual_profit']:,.0f}\n")
                else:
                    # No installations - clarify why no Average ROI
                    f.write(f"  - No installations made (insufficient ROI or budget constraints)\n")

                f.write("\n")

    print(f"\n4. Results saved to: {results_file}")
    print(f"\n{'=' * 80}")

    return {
        'scenario': scenario,
        'yearly_stats': yearly_stats,
        'yearly_farmer_snapshots': yearly_farmer_snapshots,  # NEW: Multi-year farmer data
        'model': model,
        'output_path': str(output_path)  # Return timestamped output path for visualizations
    }


def run_multi_scenario_analysis(
    scenarios: list = ['rcp26', 'rcp45', 'rcp85'],
    n_years: int = 10,
    n_farmers: int = 3,
    n_collectives: int = 2,  # Multi-level ABM: community level
    n_markets: int = 1,  # Multi-level ABM: market level
    n_policies: int = 1,  # Multi-level ABM: policy level
    n_pv_developers: int = 0,
    output_dir: str = None,
    data_path: str = "backend/data/CCA",
    include_historical: bool = False
):
    """
    Run simulations for multiple RCP scenarios and generate comparative analysis.

    Args:
        scenarios: List of RCP scenarios to simulate
        n_years: Number of years to simulate
        n_farmers: Number of farmer agents
        output_dir: Directory for output files (default: use_cases/cca/results)
        data_path: Path to CCA data directory
        include_historical: Include historical validation

    Returns:
        Dict mapping scenario -> results
    """
    print("\n" + "=" * 80)
    print("MULTI-SCENARIO ANALYSIS - CLIMATE CHANGE ADAPTATION")
    print("=" * 80)
    print(f"Use Case: UC-CCA-01")
    print("=" * 80)

    # Set default output directory (use_cases/cca/results)
    if output_dir is None:
        cca_dir = Path(__file__).parent.parent  # Go up to use_cases/cca/
        output_dir = str(cca_dir / "results")

    results_by_scenario = {}

    # Run each scenario
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] Running {scenario.upper()}...\n")

        results = run_simulation_with_results(
            scenario=scenario,
            n_years=n_years,
            n_farmers=n_farmers,
            n_collectives=n_collectives,
            n_markets=n_markets,
            n_policies=n_policies,
            n_pv_developers=n_pv_developers,
            output_dir=output_dir,
            data_path=data_path,
            include_historical=include_historical
        )
        results_by_scenario[scenario] = results

        # Small delay between scenarios
        if i < len(scenarios):
            time.sleep(1)

    # Generate comparative report
    print("\n" + "=" * 80)
    print("COMPARATIVE ANALYSIS")
    print("=" * 80)

    print("\nScenario Comparison (Average over simulation period):")
    print(f"{'Scenario':<10} {'Avg Income':<15} {'Avg Production':<15}")
    print("-" * 50)

    for scenario, results in results_by_scenario.items():
        stats = results['yearly_stats']
        if stats:
            avg_income = sum(s['total_income'] for s in stats) / len(stats)
            avg_production = sum(s['total_production'] for s in stats) / len(stats)

            print(f"{scenario.upper():<10} "
                  f"€{avg_income:>12,.2f}  "
                  f"{avg_production:>12,.2f}t")

    # Calculate climate change impact (RCP85 vs RCP26)
    if 'rcp26' in results_by_scenario and 'rcp85' in results_by_scenario:
        rcp26_stats = results_by_scenario['rcp26']['yearly_stats']
        rcp85_stats = results_by_scenario['rcp85']['yearly_stats']

        if rcp26_stats and rcp85_stats:
            rcp26_avg_income = sum(s['total_income'] for s in rcp26_stats) / len(rcp26_stats)
            rcp85_avg_income = sum(s['total_income'] for s in rcp85_stats) / len(rcp85_stats)

            income_loss = rcp26_avg_income - rcp85_avg_income
            income_loss_pct = (income_loss / rcp26_avg_income) * 100 if rcp26_avg_income > 0 else 0

            print(f"\n💡 Climate Change Impact (RCP85 vs RCP26):")
            print(f"   Income Loss: €{income_loss:,.2f}/year ({income_loss_pct:.1f}%)")
            print(f"\n   Policy Recommendation:")
            print(f"   To maintain farmer income under RCP85, consider:")
            print(f"   - Increasing climate adaptation subsidies by ~{abs(income_loss_pct):.0f}%")
            print(f"   - Promoting drought-resistant crop varieties")
            print(f"   - Supporting PV installation on marginal agricultural land")

    # Write comparative analysis to file
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    comparative_file = output_path / "comparative_analysis.txt"
    with open(comparative_file, 'w') as f:
        f.write("MULTI-SCENARIO COMPARATIVE ANALYSIS\n")
        f.write("Climate Change Adaptation (UC-CCA-01)\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Analysis Period: {n_years} years (2021-{2021 + n_years - 1})\n")
        f.write(f"Number of Farmers: {n_farmers}\n")
        if n_pv_developers > 0:
            f.write(f"Number of PV Developers: {n_pv_developers}\n")
        f.write(f"Scenarios: {', '.join([s.upper() for s in scenarios])}\n\n")

        # Scenario comparison table
        f.write("=" * 80 + "\n")
        f.write("SCENARIO COMPARISON (Average over simulation period)\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"{'Scenario':<12} {'Avg Income':<20} {'Avg Production':<20}\n")
        f.write("-" * 80 + "\n")

        scenario_metrics = {}
        for scenario, results in results_by_scenario.items():
            stats = results['yearly_stats']
            if stats:
                avg_income = sum(s['total_income'] for s in stats) / len(stats)
                avg_production = sum(s['total_production'] for s in stats) / len(stats)
                scenario_metrics[scenario] = {
                    'avg_income': avg_income,
                    'avg_production': avg_production
                }

                # Use friendly scenario name
                scenario_display = get_scenario_display_name(scenario, use_case="cca")
                f.write(f"{scenario_display:<30} "
                       f"€{avg_income:>18,.2f}  "
                       f"{avg_production:>18,.2f} tons\n")

        # Climate change impact analysis
        if 'rcp26' in results_by_scenario and 'rcp85' in results_by_scenario:
            rcp26_stats = results_by_scenario['rcp26']['yearly_stats']
            rcp85_stats = results_by_scenario['rcp85']['yearly_stats']

            if rcp26_stats and rcp85_stats:
                rcp26_avg_income = sum(s['total_income'] for s in rcp26_stats) / len(rcp26_stats)
                rcp85_avg_income = sum(s['total_income'] for s in rcp85_stats) / len(rcp85_stats)

                rcp26_avg_production = sum(s['total_production'] for s in rcp26_stats) / len(rcp26_stats)
                rcp85_avg_production = sum(s['total_production'] for s in rcp85_stats) / len(rcp85_stats)

                income_loss = rcp26_avg_income - rcp85_avg_income
                income_loss_pct = (income_loss / rcp26_avg_income) * 100 if rcp26_avg_income != 0 else 0

                production_loss = rcp26_avg_production - rcp85_avg_production
                production_loss_pct = (production_loss / rcp26_avg_production) * 100 if rcp26_avg_production != 0 else 0

                # Get friendly names for comparison
                optimistic_name = get_scenario_display_name('rcp26', use_case="cca")
                pessimistic_name = get_scenario_display_name('rcp85', use_case="cca")

                f.write("\n")
                f.write("=" * 80 + "\n")
                f.write(f"CLIMATE CHANGE IMPACT ANALYSIS ({pessimistic_name} vs {optimistic_name})\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Economic Impact:\n")
                f.write(f"  - Income Loss: €{income_loss:,.2f}/year ({income_loss_pct:.1f}%)\n")
                f.write(f"  - {optimistic_name} Avg Income: €{rcp26_avg_income:,.2f}/year\n")
                f.write(f"  - {pessimistic_name} Avg Income: €{rcp85_avg_income:,.2f}/year\n\n")

                f.write(f"Production Impact:\n")
                f.write(f"  - Production Loss: {production_loss:,.2f} tons/year ({production_loss_pct:.1f}%)\n")
                f.write(f"  - {optimistic_name} Avg Production: {rcp26_avg_production:,.2f} tons/year\n")
                f.write(f"  - {pessimistic_name} Avg Production: {rcp85_avg_production:,.2f} tons/year\n\n")

                f.write("=" * 80 + "\n")
                f.write("POLICY RECOMMENDATIONS\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"To maintain farmer income and production under {pessimistic_name}, consider:\n\n")
                f.write(f"1. Climate Adaptation Subsidies:\n")
                f.write(f"   - Increase subsidies by ~{abs(income_loss_pct):.0f}% to compensate income loss\n")
                f.write(f"   - Target: €{abs(income_loss):,.0f}/year in additional support\n\n")
                f.write(f"2. Crop Resilience:\n")
                f.write(f"   - Promote drought-resistant crop varieties\n")
                f.write(f"   - Improve irrigation infrastructure\n")
                f.write(f"   - Diversify crop portfolio to reduce climate risk\n\n")
                f.write(f"3. Renewable Energy Integration:\n")
                f.write(f"   - Support PV installation on marginal agricultural land\n")
                f.write(f"   - Provide green credits and installation subsidies\n")
                f.write(f"   - Create alternative income streams for farmers\n\n")

        # PV installation comparison (if enabled)
        if n_pv_developers > 0:
            f.write("=" * 80 + "\n")
            f.write("PV INSTALLATION COMPARISON ACROSS SCENARIOS\n")
            f.write("=" * 80 + "\n\n")

            for scenario, results in results_by_scenario.items():
                model = results.get('model')
                if model and hasattr(model, 'pv_developer_agents') and model.pv_developer_agents:
                    scenario_display = get_scenario_display_name(scenario, use_case="cca")
                    f.write(f"{scenario_display}:\n")
                    for pv_dev in model.pv_developer_agents:
                        f.write(f"  - {pv_dev.company_name}: {len(pv_dev.pv_installations)} installations, "
                               f"{pv_dev.total_capacity_installed:,.0f} kW, "
                               f"€{pv_dev.annual_revenue:,.0f} annual revenue\n")
                    f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("Individual scenario details available in:\n")
        for scenario in scenarios:
            f.write(f"  - {output_dir}/{scenario}/{scenario}_results.txt\n")
        f.write("=" * 80 + "\n")

    # Generate interactive visualizations
    try:
        visualization_files = generate_all_visualizations(
            results_by_scenario,
            output_dir=f"{output_dir}/visualizations"
        )

        # Generate cross-scale interaction visualizations (CCA-10 compliance)
        print("\n" + "=" * 80)
        print("GENERATING CROSS-SCALE VISUALIZATIONS (CCA-10)")
        print("=" * 80)
        cross_scale_files = generate_cross_scale_visualizations(
            results_by_scenario,
            output_dir=f"{output_dir}/visualizations"
        )
        # Merge into visualization_files dict
        visualization_files.update(cross_scale_files)

    except Exception as e:
        print(f"\n⚠️  Warning: Could not generate visualizations: {e}")
        print("   Install plotly and folium: pip install plotly folium")
        visualization_files = {}

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {Path(output_dir).absolute()}")
    print(f"  - Comparative analysis: {comparative_file}")
    for scenario in scenarios:
        print(f"  - {scenario.upper()} details: {output_dir}/{scenario}/{scenario}_results.txt")

    if visualization_files:
        print(f"\nInteractive Visualizations:")
        print(f"  - Scenario comparison: {visualization_files.get('scenario_comparison', 'N/A')}")
        for scenario in scenarios:
            ts_file = visualization_files.get(f'{scenario}_time_series')
            if ts_file:
                print(f"  - {scenario.upper()} time series: {ts_file}")

        print(f"\n  Cross-Scale Interaction Visualizations (CCA-10):")
        for scenario in scenarios:
            info_flow = visualization_files.get(f'{scenario}_information_flow')
            feedback = visualization_files.get(f'{scenario}_feedback_timeline')
            drivers = visualization_files.get(f'{scenario}_driver_analysis')
            network = visualization_files.get(f'{scenario}_interaction_network')

            if info_flow:
                print(f"  - {scenario.upper()} information flow: {info_flow}")
            if feedback:
                print(f"  - {scenario.upper()} feedback timeline: {feedback}")
            if drivers:
                print(f"  - {scenario.upper()} driver analysis: {drivers}")
            if network:
                print(f"  - {scenario.upper()} interaction network: {network}")

    print("\n📊 Next Steps:")
    print("   For Option B (Full Implementation):")
    print("   - ✅ PVDeveloperAgent implemented")
    print("   - ✅ Climate resilience assessment integrated")
    print("   - ✅ Historical validation framework ready")
    print("   - ✅ Interactive visualizations generated")
    print("   - Add water resource management")
    print("   - Calibrate model with real historical data")

    return results_by_scenario


def run_historical_validation(
    scenario: str = 'rcp26',
    n_farmers: int = 3,  # Consistent default across all CCA cases
    data_path: str = "backend/data/CCA",
    output_dir: str = None,
    geojson: dict = None
):
    """
    Run historical validation for CCA simulation (2010-2020).

    Compares simulated results against historical observations to validate
    model accuracy before using for future projections.

    Args:
        scenario: RCP scenario to use for validation (default: rcp26)
        n_farmers: Number of farmer agents
        data_path: Path to CCA data directory
        output_dir: Directory for validation output (default: use_cases/cca/results/validation)

    Returns:
        Dict with validation results
    """
    print("\n" + "=" * 80)
    print("HISTORICAL VALIDATION - CCA SIMULATION")
    print("=" * 80)
    print(f"Use Case: Climate Change Adaptation (UC-CCA-01)")
    print(f"Validation Period: 2010-2020")
    print(f"Scenario: {scenario.upper()}")
    print(f"Target: RMSE < 15% for all metrics")
    print("=" * 80)

    # Set default output directory (use_cases/cca/results/validation)
    if output_dir is None:
        cca_dir = Path(__file__).parent.parent  # Go up to use_cases/cca/
        output_dir = str(cca_dir / "results" / "validation")

    # Run simulation for historical period
    print("\n1. Running simulation for historical period (2010-2020)...")
    data_path_abs = str((Path(project_root) / data_path).resolve())

    model = LandUseModel(
        data_path=data_path_abs,
        crops=["WHEAT", "MAIZE"],
        scenario=scenario,
        n_farmers=n_farmers,
        n_collectives=max(1, n_farmers // 10),
        n_markets=1,
        n_policies=1,
        n_pv_developers=0,  # No PV for historical period
        lat_bounds=None,  # Auto-detect from data
        lon_bounds=None,  # Auto-detect from data
        start_year=2010,  # Historical period
        seed=42,  # Fixed seed for reproducibility
        enable_multi_level=True,
        auto_detect_bounds=True,  # Auto-detect spatial bounds from data
        auto_aggregate_temporal=True,  # Aggregate daily/monthly data to annual
        validate_temporal_range=True,  # Validate simulation years are in data range
        geojson=geojson
    )

    # Run simulation for historical years
    simulation_results = {}
    validation_years = list(range(2010, 2021))  # 2010-2020

    for year_idx, year in enumerate(validation_years):
        model.step()

        # Extract metrics for validation
        farmer_agents = model.farmer_agents

        if farmer_agents:
            # Calculate yields per hectare
            wheat_farmers = [f for f in farmer_agents if f.current_crop == "WHEAT"]
            maize_farmers = [f for f in farmer_agents if f.current_crop == "MAIZE"]

            wheat_yield = (
                sum(getattr(f, 'actual_yield', 0.0) for f in wheat_farmers) /
                len(wheat_farmers) if wheat_farmers else 0.0
            )

            maize_yield = (
                sum(getattr(f, 'actual_yield', 0.0) for f in maize_farmers) /
                len(maize_farmers) if maize_farmers else 0.0
            )

            # Crop fractions
            wheat_fraction = len(wheat_farmers) / len(farmer_agents)
            maize_fraction = len(maize_farmers) / len(farmer_agents)

            # Average income per farmer
            avg_income = (
                sum(getattr(f, 'annual_income', 0.0) for f in farmer_agents) /
                len(farmer_agents)
            )

            simulation_results[year] = {
                'wheat_yield_t_per_ha': wheat_yield,
                'maize_yield_t_per_ha': maize_yield,
                'wheat_fraction': wheat_fraction,
                'maize_fraction': maize_fraction,
                'avg_income_per_farmer': avg_income
            }

        print(f"   Year {year}: WHEAT={len(wheat_farmers)}, MAIZE={len(maize_farmers)}")

    print(f"\n   ✅ Historical simulation complete")

    # Run validation
    print("\n2. Validating against historical observations...")
    validator = HistoricalValidator()
    validation_results = validator.validate_simulation_results(
        simulation_results,
        validation_years=validation_years
    )

    # Generate validation report
    print("\n3. Generating validation report...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_file = Path(output_dir) / "historical_validation_report.txt"

    report = validator.generate_validation_report(
        validation_results,
        output_file=str(report_file)
    )

    # Print summary
    summary = validation_results.get('_summary', {})
    print(f"\n{'=' * 80}")
    print("VALIDATION RESULTS")
    print("=" * 80)
    print(f"  Period: 2010-2020")
    print(f"  Metrics Validated: {summary.get('n_metrics_validated', 0)}")
    print(f"  Metrics Passed (RMSE < 15%): {summary.get('n_metrics_passed', 0)}")
    print(f"  Average RMSE: {summary.get('avg_rmse_percentage', 0):.2f}%")
    print(f"  Overall Status: {'✅ PASSED' if summary.get('overall_pass') else '❌ FAILED'}")
    print(f"\n  Report saved to: {report_file}")
    print("=" * 80)

    # Detailed metric results
    print("\n  Metric Details:")
    for metric_name, metric_data in validation_results.items():
        if metric_name == '_summary':
            continue

        status = "✅" if metric_data['passes_target'] else "❌"
        print(f"    {status} {metric_name}: RMSE = {metric_data['rmse_percentage']:.2f}%")

    print(f"\n{'=' * 80}")
    print("NOTE: Using placeholder historical data for testing")
    print("TODO: Replace with real data from Eurostat/FAOSTAT")
    print("=" * 80)

    return validation_results


if __name__ == "__main__":
    # Example: Run multi-scenario analysis
    results = run_multi_scenario_analysis(
        scenarios=['rcp26', 'rcp45', 'rcp85'],
        n_years=10,
        n_farmers=3,  # Consistent default across all CCA cases
        n_pv_developers=5,  # Include PV developers
        # output_dir defaults to use_cases/cca/results
        data_path='backend/data/CCA'  # Explicit correct path
    )
