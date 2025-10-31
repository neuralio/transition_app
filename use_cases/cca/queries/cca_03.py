"""
CCA-03: Simulate Crop Yield Under Climate Change

User Story: "As a Farmer or Agricultural Developer
I want to simulate the effects of future climate conditions on crop yields
So that I can make informed decisions about crop rotation, irrigation, and climate-resilient farming practices."

This query runs a multi-level ABM simulation focusing on:
- Crop yield evolution under climate change
- Farmer adaptation decisions (crop selection)
- Climate vulnerability assessment
- Yield tracking across RCP scenarios
"""

import sys
from pathlib import Path
from openai import OpenAI

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.cca.scripts.run_cca_simulation import run_simulation_with_results
from use_cases.cca.utils.scenario_utils import get_scenario_display_name


def _generate_crop_yield_insights(crop, scenario_display, avg_yield, avg_income, avg_vulnerability, avg_adaptation):
    """Generate AI insights for crop yield simulation."""
    try:
        client = OpenAI()

        data_summary = f"""
Crop Yield Simulation Results for {crop}:
- Climate Scenario: {scenario_display}
- Average Yield: {avg_yield:.2f} tons/hectare
- Average Farmer Income: €{avg_income:,.2f}/year
- Final Year Vulnerability Score: {avg_vulnerability:.1%}
- Final Year Adaptation Capacity: {avg_adaptation:.1%}
"""

        insights = {}

        # Yield Trajectory Analysis (Time-Series Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an agricultural economist analyzing multi-year crop performance trends. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Yield Evolution Time-Series chart showing {crop} performance under {scenario_display}. With average yields of {avg_yield:.2f} tons/hectare, is this economically viable? What trends should farmers monitor for early warning signs of climate impacts?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Yield Trajectory Analysis (Time-Series Chart)"] = response.choices[0].message.content.strip()

        # Economic Viability Assessment (Income Evolution)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a farm financial advisor analyzing profitability under climate change. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Farmer Income Evolution chart showing average earnings of €{avg_income:,.2f}/year under {scenario_display}. Is this income level sustainable for farm operations? What financial strategies should farmers adopt?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Economic Viability Assessment (Income Chart)"] = response.choices[0].message.content.strip()

        # Climate Vulnerability vs Adaptation (Dual Metrics)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a climate resilience specialist evaluating farmer adaptive capacity. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Vulnerability vs Adaptation charts showing final year vulnerability ({avg_vulnerability:.1%}) and adaptation capacity ({avg_adaptation:.1%}). Is the adaptation keeping pace with climate risks? What interventions are urgently needed?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Climate Vulnerability vs Adaptation (Risk Dashboard)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate AI insights: {e}")
        return {
            "Yield Trajectory Analysis (Time-Series Chart)": f"{crop} yields averaging {avg_yield:.2f} tons/hectare under {scenario_display}, indicating {'stable' if avg_yield > 3 else 'declining'} productivity trends requiring continuous monitoring",
            "Economic Viability Assessment (Income Chart)": f"Average farm income of €{avg_income:,.0f}/year under {scenario_display} suggests {'sustainable' if avg_income > 50000 else 'marginal'} economic viability, necessitating {'value-added diversification' if avg_income < 50000 else 'productivity optimization'} strategies",
            "Climate Vulnerability vs Adaptation (Risk Dashboard)": f"Vulnerability at {avg_vulnerability:.1%} with adaptation capacity {avg_adaptation:.1%} reveals {'concerning gap' if avg_vulnerability > avg_adaptation else 'adequate resilience'}, requiring {'urgent' if avg_vulnerability > 0.6 else 'gradual'} climate-smart interventions"
        }


def query_cca_03(
    data_path: str,
    scenario: str = None,  # Optional: if None, run all scenarios
    crop: str = "WHEAT",
    n_years: int = 10,
    n_farmers: int = 3,  # Consistent default across all CCA cases
    n_collectives: int = 2,  # Multi-level ABM: community level
    n_markets: int = 1,  # Multi-level ABM: market level
    n_policies: int = 1,  # Multi-level ABM: policy level
    output_dir: str = None,
    geojson: dict = None,
    print_insights: bool = True,  # NEW: Control whether to print insights
    farmer_locations: list = None  # NEW (2025-10-21): User-specified farmer locations with crops
):
    """
    CCA-03: Simulate crop yield under climate change.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        scenario: Climate scenario (rcp26, rcp45, rcp85, or None for all scenarios)
        crop: Crop to focus on (WHEAT, MAIZE)
        n_years: Number of years to simulate
        n_farmers: Number of farmer agents
        n_collectives: Number of farmer collectives (community level)
        n_markets: Number of commodity markets (market level)
        n_policies: Number of policymaker agents (policy level)
        output_dir: Output directory (default: results/cca_03)
        geojson: GeoJSON polygon for spatial filtering
        print_insights: Whether to print insights
        farmer_locations: List of dicts [{lat, lon, crop}, ...] (NEW - 2025-10-21)

    Returns:
        Dict with simulation results (or dict of results if multiple scenarios)
    """
    # If no scenario specified, run ALL scenarios for comparison
    if scenario is None:
        print(f"\nℹ️  No scenario specified - running ALL scenarios for comparison!")
        return query_cca_03_all_scenarios(
            data_path=data_path,
            crop=crop,
            n_years=n_years,
            n_farmers=n_farmers,
            output_dir=output_dir,
            geojson=geojson,
            farmer_locations=farmer_locations
        )

    # Get user-friendly display name
    scenario_display = get_scenario_display_name(scenario, use_case="cca")

    print(f"\n{'='*80}")
    print(f"CCA-03: Crop Yield Simulation Under Climate Change")
    print(f"{'='*80}")
    print(f"Crop: {crop.upper() if crop else 'ALL (WHEAT + MAIZE)'}")
    print(f"Scenario: {scenario_display}")
    print(f"Duration: {n_years} years")
    print(f"Farmers: {n_farmers}")
    print(f"{'='*80}\n")

    # Set default output directory (absolute path to avoid nesting)
    if output_dir is None:
        # Use absolute path relative to project root
        cca_dir = Path(__file__).parent.parent  # Go up to use_cases/cca/
        output_dir = str(cca_dir / "results" / "cca_03")

    # Run simulation with focus on crop yield
    print("🔄 Running crop yield simulation with climate adaptation...")
    results = run_simulation_with_results(
        scenario=scenario,
        n_years=n_years,
        n_farmers=n_farmers,
        n_collectives=n_collectives,
        n_markets=n_markets,
        n_policies=n_policies,
        n_pv_developers=0,  # No PV for CCA-03 (crop focus)
        output_dir=output_dir,
        data_path=data_path,
        include_historical=False,
        focus_crop=crop,  # NEW: Filter results display to requested crop only
        geojson=geojson,
        farmer_locations=farmer_locations  # NEW (2025-10-21)
    )

    # Display multi-level ABM initial characteristics
    model = results.get('model')
    if model:
        print(f"\n{'='*80}")
        print(f"MULTI-LEVEL ABM: INITIAL AGENT CHARACTERISTICS")
        print(f"{'='*80}\n")

        # Individual Level: Farmers
        if hasattr(model, 'farmer_agents') and model.farmer_agents and n_farmers <= 10:
            # Only show all farmers if there are 10 or fewer (to avoid console spam)
            print(f"👨‍🌾 Individual Level: Farmers (All {len(model.farmer_agents)}):")
            print("-" * 80)
            for farmer in model.farmer_agents:
                print(f"\nFarmer {farmer.unique_id}:")
                print(f"   • Location: ({farmer.lat:.4f}, {farmer.lon:.4f})")
                print(f"   • Farm Size: {farmer.land_hectares:.1f} ha")
                print(f"   • Initial Crop: {farmer.current_crop if farmer.current_crop else 'Will decide'}")
        elif hasattr(model, 'farmer_agents') and model.farmer_agents:
            print(f"👨‍🌾 Individual Level: {len(model.farmer_agents)} Farmers (see results file for full details)")

        # Community Level: Collectives
        if hasattr(model, 'collective_agents') and model.collective_agents:
            print(f"\n🏘️  Community Level: Collectives ({len(model.collective_agents)}):")
            print("-" * 80)
            for collective in model.collective_agents:
                print(f"\n{collective.region_name}:")
                print(f"   • Members: {len(collective.members)} farmers")
                print(f"   • Member IDs: {[f.unique_id for f in collective.members]}")

        # Market Level: Commodity Markets (use INITIAL characteristics)
        if hasattr(model, 'initial_characteristics') and 'markets' in model.initial_characteristics:
            markets_initial = model.initial_characteristics['markets']
            print(f"\n🏪 Market Level: Commodity Markets ({len(markets_initial)}):")
            print("-" * 80)
            for market_data in markets_initial:
                print(f"\n{market_data['name']}:")
                print(f"   • Crops Traded: {', '.join(market_data['crops'])}")
                print(f"   • Initial Prices: {', '.join([f'{crop}=€{price:.2f}/t' for crop, price in market_data['prices'].items()])}")
                print(f"   • Initial Demand: {', '.join([f'{crop}={demand:.2f}t' for crop, demand in market_data['demand'].items()])}")

        # Policy Level: Policymakers
        if hasattr(model, 'policy_agents') and model.policy_agents:
            print(f"\n🏛️  Policy Level: Policymakers ({len(model.policy_agents)}):")
            print("-" * 80)
            for policymaker in model.policy_agents:
                print(f"\n{policymaker.policy_name}:")
                print(f"   • Policy Goals: {policymaker.policy_goals}")
                print(f"   • PV Green Credit: €{policymaker.pv_green_credit:.3f}/kWh")
                print(f"   • PV Installation Subsidy: {policymaker.pv_installation_subsidy:.1%}")
                print(f"   • Renewable Energy Target: {policymaker.renewable_energy_target:.1%}")
                if policymaker.subsidy_rates:
                    print(f"   • Crop Subsidy Rates: {policymaker.subsidy_rates}")

    # Extract crop-specific insights (or all crops if crop=None)
    yearly_stats = results.get('yearly_stats', [])
    yearly_farmer_snapshots = results.get('yearly_farmer_snapshots', [])

    if yearly_stats and crop:
        # Crop-specific analysis (only when crop is specified)
        print(f"\n{'='*80}")
        print(f"CCA-03 RESULTS: {crop.upper()} YIELD ANALYSIS")
        print(f"{'='*80}\n")

        # Calculate average yield for target crop
        crop_key = f"{crop.lower()}_farmers"
        total_crop_years = 0
        total_yield = 0.0
        total_income = 0.0

        for year_data in yearly_farmer_snapshots:
            farmers = year_data.get('farmers', [])
            crop_farmers = [f for f in farmers if f.get('crop') == crop.upper()]

            if crop_farmers:
                total_crop_years += 1
                year_yield = sum(f.get('actual_yield', 0.0) for f in crop_farmers) / len(crop_farmers)
                year_income = sum(f.get('annual_income', 0.0) for f in crop_farmers) / len(crop_farmers)
                total_yield += year_yield
                total_income += year_income

        if total_crop_years > 0:
            avg_yield = total_yield / total_crop_years
            avg_income = total_income / total_crop_years

            print(f"📊 {crop.upper()} Performance ({n_years} years under {scenario_display}):")
            print(f"   Average Yield: {avg_yield:.2f} tons/hectare")
            print(f"   Average Income: €{avg_income:,.2f}/year per farmer")
            print(f"   Years with {crop.upper()}: {total_crop_years} / {n_years}")

        # Climate vulnerability insights
        print(f"\n🌡️  Climate Resilience Insights:")
        avg_vulnerability = 0.5
        avg_adaptation = 0.5
        if yearly_farmer_snapshots:
            last_year = yearly_farmer_snapshots[-1]
            farmers = last_year.get('farmers', [])
            if farmers:
                avg_vulnerability = sum(f.get('vulnerability_score', 0.5) for f in farmers) / len(farmers)
                avg_adaptation = sum(f.get('adaptation_capacity', 0.5) for f in farmers) / len(farmers)
                print(f"   Final Year Vulnerability: {avg_vulnerability:.2%}")
                print(f"   Final Year Adaptation Capacity: {avg_adaptation:.2%}")

        # Generate AI insights (only if print_insights=True)
        insights = _generate_crop_yield_insights(
            crop=crop,
            scenario_display=scenario_display,
            avg_yield=avg_yield if total_crop_years > 0 else 0,
            avg_income=avg_income if total_crop_years > 0 else 0,
            avg_vulnerability=avg_vulnerability,
            avg_adaptation=avg_adaptation
        )

        if print_insights:
            print(f"\n📊 AI-Generated Insights:")
            for viz_name, insight in insights.items():
                print(f"\n  {viz_name}:")
                print(f"    {insight}")

        print(f"\n💡 Recommendation:")
        print(f"   Under {scenario_display}, consider:")
        if scenario.lower() == 'rcp85':
            if crop:
                print(f"   - Switching to drought-resistant {crop.lower()} varieties")
            else:
                print(f"   - Switching to drought-resistant crop varieties")
            print(f"   - Investing in irrigation infrastructure")
            print(f"   - Diversifying with climate-resilient crops")
        else:
            if crop:
                print(f"   - Continue monitoring {crop.lower()} performance")
            else:
                print(f"   - Continue monitoring crop performance")
            print(f"   - Maintain current adaptation strategies")

    else:
        # When crop=None (showing all crops), still generate insights based on overall performance
        if yearly_farmer_snapshots and print_insights:
            # Calculate overall metrics across all crops
            total_farmers = 0
            total_yield = 0.0
            total_income = 0.0
            total_years = 0

            for year_data in yearly_farmer_snapshots:
                farmers = year_data.get('farmers', [])
                if farmers:
                    total_years += 1
                    total_yield += sum(f.get('actual_yield', 0.0) for f in farmers) / len(farmers)
                    total_income += sum(f.get('annual_income', 0.0) for f in farmers) / len(farmers)

            avg_yield = total_yield / total_years if total_years > 0 else 0
            avg_income = total_income / total_years if total_years > 0 else 0

            # Get final year metrics
            avg_vulnerability = 0.5
            avg_adaptation = 0.5
            if yearly_farmer_snapshots:
                last_year = yearly_farmer_snapshots[-1]
                farmers = last_year.get('farmers', [])
                if farmers:
                    avg_vulnerability = sum(f.get('vulnerability_score', 0.5) for f in farmers) / len(farmers)
                    avg_adaptation = sum(f.get('adaptation_capacity', 0.5) for f in farmers) / len(farmers)

            # Generate insights for all crops
            insights = _generate_crop_yield_insights(
                crop="ALL CROPS" if crop is None else crop,
                scenario_display=scenario_display,
                avg_yield=avg_yield,
                avg_income=avg_income,
                avg_vulnerability=avg_vulnerability,
                avg_adaptation=avg_adaptation
            )

            print(f"\n📊 AI-Generated Insights:")
            for viz_name, insight in insights.items():
                print(f"\n  {viz_name}:")
                print(f"    {insight}")

    # Generate visualizations
    print(f"\n{'='*80}")
    print(f"GENERATING VISUALIZATIONS")
    print(f"{'='*80}\n")

    try:
        from use_cases.cca.scripts.visualizations import generate_all_visualizations

        # Format results for visualization function
        results_by_scenario = {
            scenario: results
        }

        # Use timestamped output path from results
        timestamped_output = results.get('output_path', output_dir)
        visualization_files = generate_all_visualizations(
            results_by_scenario,
            output_dir=f"{timestamped_output}/visualizations",
            data_path=data_path,
            focus_crop=crop  # Pass crop filter to visualizations
        )

        if visualization_files:
            print(f"\n📊 Generated Visualizations:")
            for viz_type, file_path in visualization_files.items():
                print(f"   - {viz_type}: {file_path}")
    except Exception as e:
        print(f"\n⚠️  Warning: Could not generate visualizations: {e}")
        print("   Install dependencies: pip install plotly folium")

    print(f"\n{'='*80}")
    print(f"✅ Results saved to: {output_dir}/")
    print(f"   - Text summary: {output_dir}/{scenario}/{scenario}_results.txt")
    print(f"   - Visualizations: {output_dir}/visualizations/")
    print(f"{'='*80}\n")

    # Add insights to results if they were generated
    if 'insights' in locals():
        results['ai_insights'] = insights

    return results


def query_cca_03_all_scenarios(
    data_path: str,
    crop: str = "WHEAT",
    n_years: int = 10,
    n_farmers: int = 3,  # Consistent default across all CCA cases
    n_collectives: int = 2,  # Multi-level ABM: community level
    n_markets: int = 1,  # Multi-level ABM: market level
    n_policies: int = 1,  # Multi-level ABM: policy level
    output_dir: str = None,
    geojson: dict = None,
    farmer_locations: list = None  # NEW (2025-10-21)
):
    """
    Run CCA-03 for ALL climate scenarios and create comparative analysis.

    This matches the CCA-03 acceptance criteria:
    "Users should be able to select specific crops and see how yields vary
    under different climate scenarios."

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        crop: Crop to focus on (WHEAT, MAIZE)
        n_years: Number of years to simulate
        n_farmers: Number of farmer agents
        output_dir: Output directory (default: results/cca_03)
        geojson: GeoJSON polygon
        farmer_locations: User-specified farmer locations (NEW - 2025-10-21)

    Returns:
        Dict mapping scenario -> results
    """
    scenarios = ['rcp26', 'rcp45', 'rcp85']

    # Get user-friendly display names for all scenarios
    scenario_displays = [get_scenario_display_name(s, use_case="cca") for s in scenarios]

    print(f"\n{'='*80}")
    print(f"CCA-03: Multi-Scenario Crop Yield Comparison")
    print(f"{'='*80}")
    print(f"Crop: {crop.upper() if crop else 'ALL (WHEAT + MAIZE)'}")
    print(f"Scenarios: {', '.join(scenario_displays)}")
    print(f"Duration: {n_years} years")
    print(f"Farmers: {n_farmers}")
    print(f"{'='*80}\n")

    # Set default output directory
    if output_dir is None:
        cca_dir = Path(__file__).parent.parent
        output_dir = str(cca_dir / "results" / "cca_03")

    results_by_scenario = {}

    # Run each scenario
    for i, scenario in enumerate(scenarios, 1):
        scenario_display = get_scenario_display_name(scenario, use_case="cca")
        print(f"\n[{i}/{len(scenarios)}] Running {scenario_display}...\n")

        result = query_cca_03(
            data_path=data_path,
            scenario=scenario,
            crop=crop,  # Will be passed to focus_crop internally
            n_years=n_years,
            n_farmers=n_farmers,
            n_collectives=n_collectives,
            n_markets=n_markets,
            n_policies=n_policies,
            output_dir=output_dir,
            geojson=geojson,
            print_insights=False,  # Don't print individual insights - only comparison insights
            farmer_locations=farmer_locations  # NEW (2025-10-21)
        )
        results_by_scenario[scenario] = result

    # Create comparative analysis
    print(f"\n{'='*80}")
    if crop:
        print(f"COMPARATIVE ANALYSIS: {crop.upper()} YIELD ACROSS SCENARIOS")
    else:
        print(f"COMPARATIVE ANALYSIS: CROP YIELD ACROSS SCENARIOS")
    print(f"{'='*80}\n")

    # Compare average yields across scenarios
    if crop:
        print(f"📊 Average Yield Comparison ({n_years} years):")
        print(f"{'Scenario':<12} {'Avg Yield (t/ha)':<20} {'Avg Income (€/year)':<20}")
        print("-" * 60)

        for scenario in scenarios:
            yearly_snapshots = results_by_scenario[scenario].get('yearly_farmer_snapshots', [])

            if yearly_snapshots:
                total_yield = 0.0
                total_income = 0.0
                count = 0

                for year_data in yearly_snapshots:
                    farmers = year_data.get('farmers', [])
                    crop_farmers = [f for f in farmers if f.get('crop') == crop.upper()]

                if crop_farmers:
                    year_yield = sum(f.get('actual_yield', 0.0) for f in crop_farmers) / len(crop_farmers)
                    year_income = sum(f.get('annual_income', 0.0) for f in crop_farmers) / len(crop_farmers)
                    total_yield += year_yield
                    total_income += year_income
                    count += 1

            if count > 0:
                avg_yield = total_yield / count
                avg_income = total_income / count
                scenario_display = get_scenario_display_name(scenario, use_case="cca")
                print(f"{scenario_display:<30} {avg_yield:>17.2f}   €{avg_income:>17,.2f}")

    # Climate impact analysis (only when crop is specified)
    if crop and 'rcp26' in results_by_scenario and 'rcp85' in results_by_scenario:
        rcp26_snapshots = results_by_scenario['rcp26'].get('yearly_farmer_snapshots', [])
        rcp85_snapshots = results_by_scenario['rcp85'].get('yearly_farmer_snapshots', [])

        if rcp26_snapshots and rcp85_snapshots:
            # Calculate averages
            def get_avg_yield(snapshots):
                total = 0.0
                count = 0
                for year_data in snapshots:
                    farmers = year_data.get('farmers', [])
                    crop_farmers = [f for f in farmers if f.get('crop') == crop.upper()]
                    if crop_farmers:
                        total += sum(f.get('actual_yield', 0.0) for f in crop_farmers) / len(crop_farmers)
                        count += 1
                return total / count if count > 0 else 0

            rcp26_yield = get_avg_yield(rcp26_snapshots)
            rcp85_yield = get_avg_yield(rcp85_snapshots)

            if rcp26_yield > 0:
                yield_loss = rcp26_yield - rcp85_yield
                yield_loss_pct = (yield_loss / rcp26_yield) * 100

                optimistic_display = get_scenario_display_name('rcp26', use_case="cca")
                pessimistic_display = get_scenario_display_name('rcp85', use_case="cca")

                print(f"\n💡 Climate Change Impact ({pessimistic_display} vs {optimistic_display}):")
                print(f"   Yield Loss: {yield_loss:.2f} t/ha ({yield_loss_pct:.1f}%)")
                print(f"\n   Recommendation for {crop.upper()} under {pessimistic_display}:")
                print(f"   - Develop drought-resistant varieties")
                print(f"   - Invest in irrigation infrastructure")
                print(f"   - Consider crop diversification")

    # Generate comparative visualizations
    print(f"\n{'='*80}")
    print(f"GENERATING COMPARATIVE VISUALIZATIONS")
    print(f"{'='*80}\n")

    try:
        from use_cases.cca.scripts.visualizations import generate_all_visualizations

        visualization_files = generate_all_visualizations(
            results_by_scenario,
            output_dir=f"{output_dir}/visualizations",
            data_path=data_path,
            focus_crop=crop  # Pass crop filter to visualizations
        )

        if visualization_files:
            print(f"\n📊 Generated Comparative Visualizations:")
            for viz_type, file_path in visualization_files.items():
                print(f"   - {viz_type}: {file_path}")
    except Exception as e:
        print(f"\n⚠️  Warning: Could not generate visualizations: {e}")

    # Generate AI insights for comparison mode
    print(f"\n📊 AI-Generated Insights:")
    comparison_insights = _generate_comparison_insights_cca03(results_by_scenario, crop, n_years)
    for viz_name, insight in comparison_insights.items():
        print(f"\n  {viz_name}:")
        print(f"    {insight}")

    print(f"\n{'='*80}")
    print(f"✅ Multi-Scenario Analysis Complete!")
    print(f"   - Results: {output_dir}/")
    print(f"   - Visualizations: {output_dir}/visualizations/")
    print(f"   - Scenarios compared: {', '.join(scenario_displays)}")
    print(f"{'='*80}\n")

    return results_by_scenario


def _generate_comparison_insights_cca03(results_by_scenario: dict, crop: str, n_years: int):
    """
    Generate LLM-powered insights for CCA-03 COMPARISON MODE visualizations.

    Args:
        results_by_scenario: Dict mapping scenario name -> result dict
        crop: Crop being analyzed
        n_years: Number of years simulated

    Returns:
        Dict of insights for each comparison visualization
    """
    try:
        from openai import OpenAI
        client = OpenAI()

        # Extract comparison data
        scenario_names = []
        avg_yields = []
        avg_incomes = []

        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in results_by_scenario:
                scenario_names.append(get_scenario_display_name(scenario, use_case="cca"))

                yearly_snapshots = results_by_scenario[scenario].get('yearly_farmer_snapshots', [])
                total_yield = 0.0
                total_income = 0.0
                count = 0

                for year_data in yearly_snapshots:
                    farmers = year_data.get('farmers', [])
                    crop_farmers = [f for f in farmers if f.get('crop') == crop.upper()]
                    if crop_farmers:
                        total_yield += sum(f.get('actual_yield', 0.0) for f in crop_farmers) / len(crop_farmers)
                        total_income += sum(f.get('annual_income', 0.0) for f in crop_farmers) / len(crop_farmers)
                        count += 1

                avg_yield = total_yield / count if count > 0 else 0
                avg_income = total_income / count if count > 0 else 0
                avg_yields.append(avg_yield)
                avg_incomes.append(avg_income)

        # Calculate yield loss from optimistic to pessimistic
        yield_loss_pct = 0
        if len(avg_yields) >= 2 and avg_yields[0] > 0:
            yield_loss_pct = ((avg_yields[0] - avg_yields[-1]) / avg_yields[0]) * 100

        # Prepare summary
        data_summary = f"""
Multi-Scenario Comparison Results (CCA-03):
- Crop: {crop.upper()}
- Scenarios: {', '.join(scenario_names)}
- Duration: {n_years} years
- Average Yields: {dict(zip(scenario_names, [f'{y:.2f} t/ha' for y in avg_yields]))}
- Average Incomes: {dict(zip(scenario_names, [f'€{i:,.0f}' for i in avg_incomes]))}
- Yield Loss ({scenario_names[0]} → {scenario_names[-1]}): {yield_loss_pct:.1f}%
"""

        insights = {}

        # 1. Yield Trajectory Comparison (Time-Series Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an agricultural economist analyzing climate-driven yield trajectories. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Yield Trajectory Time-Series showing {crop.upper()} yields across {', '.join(scenario_names)}. The yield loss from optimistic to pessimistic scenario is {yield_loss_pct:.1f}%. What adaptation strategies should Thessaloniki farmers prioritize under different climate pathways?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Yield Trajectory Comparison (Time-Series Chart)"] = response.choices[0].message.content.strip()

        # 2. Economic Viability Comparison (Income Dashboard)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a farm economics expert analyzing climate change impacts on agricultural profitability. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Economic Viability Dashboard showing average farmer incomes: {dict(zip(scenario_names, [f'€{i:,.0f}' for i in avg_incomes]))}. How should financial institutions and policymakers adjust support mechanisms for {crop.upper()} farmers under severe climate scenarios?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Economic Viability Comparison (Income Dashboard)"] = response.choices[0].message.content.strip()

        # 3. Multi-Scenario Strategic Planning (Comparison Dashboard)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a regional agricultural planning expert developing climate-resilient strategies. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Multi-Scenario Comparison Dashboard for {crop.upper()} cultivation. Given the yield loss of {yield_loss_pct:.1f}% from best to worst case, what robust strategies should Thessaloniki's agricultural sector pursue that perform acceptably across all scenarios?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Multi-Scenario Strategic Planning (Comparison Dashboard)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate LLM insights: {e}")
        # Fallback generic insights
        return {
            "Yield Trajectory Comparison (Time-Series Chart)": f"{crop.upper()} yields diverge across climate scenarios: {dict(zip(scenario_names, [f'{y:.2f} t/ha' for y in avg_yields]))}, revealing differential climate sensitivity and adaptation needs",
            "Economic Viability Comparison (Income Dashboard)": f"Farmer incomes vary by scenario: {dict(zip(scenario_names, [f'€{i:,.0f}' for i in avg_incomes]))}, indicating need for scenario-dependent financial support mechanisms",
            "Multi-Scenario Strategic Planning (Comparison Dashboard)": f"Comparing across scenarios enables robust planning under uncertainty, with farmers needing flexible strategies for {crop.upper()} cultivation"
        }


if __name__ == "__main__":
    # Example usage
    query_cca_03(
        data_path="/app/data",
        scenario="rcp45",
        crop="WHEAT",
        n_years=10,
        n_farmers=3,  # Consistent default across all CCA cases
        n_collectives=2,
        n_markets=1,
        n_policies=1
    )
