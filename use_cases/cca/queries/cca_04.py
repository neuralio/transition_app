"""
CCA-04: Evaluate Land Suitability for PV Installations

User Story: "As a Farmer or Energy Company Representative
I want to evaluate land suitability for photovoltaic (PV) installations based on climate conditions
So that I can assess the potential for renewable energy production on agricultural land."

This query runs a multi-level ABM simulation with PV developers focusing on:
- Solar irradiance and land characteristics assessment
- PV installation suitability scoring
- Energy company investment decisions
- Farmer land lease agreements
- ROI and capacity factor analysis
"""

import sys
from pathlib import Path
from openai import OpenAI

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.cca.scripts.run_cca_simulation import run_simulation_with_results
from use_cases.cca.utils.scenario_utils import get_scenario_display_name


def _generate_pv_suitability_insights(scenario_display, adoption_rate, avg_roi, avg_capacity_factor, total_capacity_kw):
    """Generate AI insights for PV suitability analysis."""
    try:
        client = OpenAI()

        data_summary = f"""
PV Suitability Analysis Results:
- Climate Scenario: {scenario_display}
- PV Adoption Rate: {adoption_rate:.1f}%
- Average ROI: {avg_roi:.1%}
- Average Capacity Factor: {avg_capacity_factor:.1%}
- Total Installed Capacity: {total_capacity_kw:,.0f} kW
"""

        insights = {}

        # Financial Viability Assessment (ROI Heatmap)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a renewable energy investment analyst evaluating solar project economics. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the ROI Suitability Heatmap showing average returns of {avg_roi:.1%} under {scenario_display}. Is this investment attractive for farmers, developers, and financial institutions? What ROI thresholds drive adoption decisions?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Financial Viability Assessment (ROI Heatmap)"] = response.choices[0].message.content.strip()

        # Technical Performance Analysis (Capacity Factor Maps)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a solar energy engineer analyzing system performance. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Capacity Factor spatial distribution showing average {avg_capacity_factor:.1%} performance. How do local solar irradiance patterns affect PV viability? Which geographic zones offer highest energy yields?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Technical Performance Analysis (Capacity Factor Maps)"] = response.choices[0].message.content.strip()

        # Adoption Dynamics (Time-Series & Geographic Spread)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a renewable energy transition analyst studying adoption patterns. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the PV Adoption Evolution charts showing {adoption_rate:.1f}% uptake with {total_capacity_kw:,.0f} kW installed. What prevents higher adoption? Are there diffusion barriers, financing gaps, or policy constraints limiting growth?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Adoption Dynamics (Time-Series & Geographic Spread)"] = response.choices[0].message.content.strip()

        # Policy Recommendations (Investment Acceleration)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a renewable energy policy strategist designing incentive programs. Provide detailed, actionable recommendations in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nBased on the suitability analysis and current {adoption_rate:.1f}% adoption rate, what specific policy interventions would accelerate PV deployment? Consider feed-in tariffs, subsidies, low-interest loans, and grid connection support."}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Policy Recommendations (Investment Acceleration)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate AI insights: {e}")
        return {
            "Financial Viability Assessment (ROI Heatmap)": f"Average ROI of {avg_roi:.1%} under {scenario_display} indicates {'strong' if avg_roi > 0.15 else 'moderate' if avg_roi > 0.10 else 'marginal'} solar investment attractiveness for farmers and energy companies",
            "Technical Performance Analysis (Capacity Factor Maps)": f"Capacity factor of {avg_capacity_factor:.1%} reveals spatial heterogeneity in solar resource quality, with high-irradiance zones offering superior energy yields and faster payback periods",
            "Adoption Dynamics (Time-Series & Geographic Spread)": f"Current adoption rate of {adoption_rate:.1f}% with {total_capacity_kw:,.0f} kW capacity suggests {'early-stage' if adoption_rate < 15 else 'growing' if adoption_rate < 35 else 'mature'} market requiring {'aggressive incentives' if adoption_rate < 15 else 'supportive policies' if adoption_rate < 35 else 'grid integration focus'}",
            "Policy Recommendations (Investment Acceleration)": f"Boost adoption from {adoption_rate:.1f}% through enhanced subsidies (targeting ROI > 15%), streamlined permitting, and green financing mechanisms tailored to risk profiles of farmers and developers"
        }


def query_cca_04(
    data_path: str,
    scenario: str = None,
    n_farmers: int = 3,  # Consistent default across all CCA cases
    n_collectives: int = 2,  # Multi-level ABM: community level
    n_markets: int = 1,  # Multi-level ABM: market level
    n_policies: int = 1,  # Multi-level ABM: policy level
    n_pv_developers: int = 2,
    n_years: int = 10,
    output_dir: str = None,
    geojson: dict = None,
    print_insights: bool = True,  # NEW: Control whether to print insights
    farmer_locations: list = None  # NEW (2025-10-21)
):
    """
    CCA-04: Evaluate PV installation suitability on agricultural land.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        scenario: Climate scenario (rcp26, rcp45, rcp85) - Optional: if None, run all scenarios
        n_farmers: Number of farmer agents (land parcels to evaluate)
        n_collectives: Number of farmer collectives (community level)
        n_markets: Number of commodity markets (market level)
        n_policies: Number of policymaker agents (policy level)
        n_pv_developers: Number of PV developer agents (energy companies)
        n_years: Number of years to simulate
        output_dir: Output directory (default: results/cca_04)

    Returns:
        Dict with simulation results and PV suitability analysis
    """
    # If no scenario specified, run ALL scenarios for comparison (matches acceptance criteria)
    if scenario is None:
        print(f"\nℹ️  No scenario specified - running ALL scenarios for comparison!")
        return query_cca_04_all_scenarios(
            data_path=data_path,
            n_farmers=n_farmers,
            n_pv_developers=n_pv_developers,
            n_years=n_years,
            output_dir=output_dir,
            geojson=geojson,
            farmer_locations=farmer_locations
        )

    print(f"\n{'='*80}")
    print(f"CCA-04: PV Installation Suitability Evaluation")
    print(f"{'='*80}")
    print(f"Scenario: {scenario.upper()}")
    print(f"Duration: {n_years} years")
    print(f"Farmers: {n_farmers} (land parcels)")
    print(f"PV Developers: {n_pv_developers} (energy companies)")
    print(f"{'='*80}\n")

    # Set default output directory (absolute path to avoid nesting)
    if output_dir is None:
        # Use absolute path relative to project root
        cca_dir = Path(__file__).parent.parent  # Go up to use_cases/cca/
        output_dir = str(cca_dir / "results" / "cca_04")

    # Run simulation with PV developers enabled
    print("🔄 Running PV suitability evaluation with energy company agents...")
    results = run_simulation_with_results(
        scenario=scenario,
        n_years=n_years,
        n_farmers=n_farmers,
        n_collectives=n_collectives,
        n_markets=n_markets,
        n_policies=n_policies,
        n_pv_developers=n_pv_developers,  # Enable PV developers
        output_dir=output_dir,
        data_path=data_path,
        include_historical=False,
        skip_crop_stats=True,  # CCA-04 is PV-focused, skip crop statistics
        geojson=geojson,
        farmer_locations=farmer_locations  # NEW (2025-10-21)
    )

    # Extract PV installation insights
    model = results.get('model')

    if model and hasattr(model, 'pv_developer_agents') and model.pv_developer_agents:
        print(f"\n{'='*80}")
        print(f"CCA-04 RESULTS: PV SUITABILITY ANALYSIS")
        print(f"{'='*80}\n")

        # Show farmer initial characteristics (ALL)
        if hasattr(model, 'farmer_agents') and model.farmer_agents:
            print(f"👨‍🌾 Farmer Initial Characteristics (All {len(model.farmer_agents)} Farmers):")
            print("-" * 80)
            for farmer in model.farmer_agents:
                print(f"\nFarmer {farmer.unique_id}:")
                print(f"   • Location: ({farmer.lat:.4f}, {farmer.lon:.4f})")
                print(f"   • Farm Size: {farmer.land_hectares:.1f} hectares")
                print(f"   • Soil pH: {farmer.soil_ph:.2f}")
                print(f"   • Soil Organic Carbon: {farmer.soil_organic_carbon:.2f}%")
                print(f"   • Elevation: {farmer.elevation:.0f}m")
                print(f"   • Adaptation Capacity: {farmer.adaptation_capacity:.2f}")
                print(f"   • Initial Crop: {farmer.current_crop if farmer.current_crop else 'None (will decide)'}")

        # Show initial company characteristics
        print("\n" + "=" * 80)
        print("🏢 Energy Company Initial Characteristics:")
        print("-" * 80)
        for pv_dev in model.pv_developer_agents:
            # Determine company size category
            initial_capacity = pv_dev.initial_investment_capacity
            if initial_capacity <= 3500000:
                size_category = "Small"
            elif initial_capacity <= 6500000:
                size_category = "Medium"
            else:
                size_category = "Large"

            print(f"\n🏢 {pv_dev.company_name} ({size_category}):")
            print(f"   • Initial Investment Capacity: €{initial_capacity:,.0f}")
            print(f"   • PV Installation Cost: €{pv_dev.pv_cost_per_kw:.2f}/kW")
            print(f"   • System Lifetime: {pv_dev.pv_lifetime_years} years")
            print(f"   • Maintenance: {pv_dev.maintenance_cost_rate:.2%}/year")
            print(f"   • Farmer Lease Payment: €{pv_dev.land_lease_rate:.2f}/ha/year")

        print(f"\n{'='*80}")
        print("📊 Energy Company Simulation Results:")
        print("=" * 80)

        total_installations = 0
        total_capacity_kw = 0.0
        total_investment = 0.0
        all_installations = []

        for pv_dev in model.pv_developer_agents:
            n_installations = len(pv_dev.pv_installations)
            total_installations += n_installations
            total_capacity_kw += pv_dev.total_capacity_installed
            capital_deployed = pv_dev.initial_investment_capacity - pv_dev.investment_capacity

            print(f"\n🏢 {pv_dev.company_name}:")
            print(f"   Installations Made: {n_installations}")
            print(f"   Total Capacity: {pv_dev.total_capacity_installed:,.0f} kW")
            print(f"   Capital Deployed: €{capital_deployed:,.0f}")
            print(f"   Investment Remaining: €{pv_dev.investment_capacity:,.0f}")
            print(f"   Annual Revenue: €{pv_dev.annual_revenue:,.0f}")

            if n_installations > 0:
                avg_roi = sum(inst['roi'] for inst in pv_dev.pv_installations) / n_installations
                avg_capacity_factor = sum(inst['capacity_factor'] for inst in pv_dev.pv_installations) / n_installations
                avg_solar = sum(inst['solar_radiation'] for inst in pv_dev.pv_installations) / n_installations

                print(f"   Average ROI: {avg_roi:.1%} over {pv_dev.pv_lifetime_years} years")
                print(f"   Average Capacity Factor: {avg_capacity_factor:.1%}")
                print(f"   Average Solar Radiation: {avg_solar:.2f} kWh/m²/day")

                # Collect all installations for ranking
                all_installations.extend(pv_dev.pv_installations)
            print()

        # Summary statistics with 3-way status breakdown
        print(f"🌞 Overall PV Adoption Summary:")
        print(f"   Total Installations: {total_installations} / {n_farmers} parcels")
        print(f"   Adoption Rate: {(total_installations / n_farmers) * 100:.1f}%")
        print(f"   Total Capacity: {total_capacity_kw:,.0f} kW")
        print(f"   Farmers with PV: {len(model.farmers_with_pv)}")
        print(f"   Farmers still farming: {n_farmers - len(model.farmers_with_pv)}")

        # Calculate 3-way status breakdown
        installed_count = total_installations
        not_installed_count = n_farmers - total_installations

        # Evaluate non-installed parcels to determine budget constrained vs infeasible
        budget_constrained_count = 0
        infeasible_count = 0

        if model.pv_developer_agents and not_installed_count > 0:
            pv_dev = model.pv_developer_agents[0]
            for farmer in model.farmer_agents:
                if not farmer.has_pv_installation:
                    suitability = pv_dev.evaluate_location_suitability(
                        farmer.lat, farmer.lon, model.start_year
                    )
                    roi_analysis = pv_dev.calculate_roi(
                        land_hectares=farmer.land_hectares * 0.2,
                        suitability_metrics=suitability,
                        farmer_id=farmer.unique_id,
                        skip_budget_check=True
                    )
                    if roi_analysis['feasible']:
                        budget_constrained_count += 1
                    else:
                        infeasible_count += 1

        print(f"\n📊 Parcel Status Breakdown:")
        print(f"   🟢 Installed: {installed_count} ({installed_count/n_farmers*100:.1f}%)")
        print(f"   🟡 Budget Constrained: {budget_constrained_count} ({budget_constrained_count/n_farmers*100:.1f}%)")
        print(f"   🔴 Infeasible: {infeasible_count} ({infeasible_count/n_farmers*100:.1f}%)")

        # Top 5 most suitable locations
        if all_installations:
            print(f"\n⭐ Top 5 Most Suitable Locations for PV:")
            sorted_installations = sorted(all_installations, key=lambda x: x['roi'], reverse=True)
            for i, inst in enumerate(sorted_installations[:5], 1):
                lat, lon = inst['location']
                print(f"   {i}. Farmer {inst['farmer_id']}: {inst['capacity_kw']:.0f} kW, "
                      f"ROI={inst['roi']:.1%}, CF={inst['capacity_factor']:.1%}, "
                      f"Solar={inst['solar_radiation']:.2f} kWh/m²/day")

        # Climate scenario impact
        scenario_display = get_scenario_display_name(scenario, use_case="cca")
        print(f"\n🌡️  Climate Scenario Impact ({scenario_display}):")
        if scenario.lower() == 'rcp85':
            print(f"   - Higher solar radiation → Better PV performance")
            print(f"   - Increased heat may slightly reduce panel efficiency")
            print(f"   - Overall: Favorable for PV adoption")
        elif scenario.lower() == 'rcp26':
            print(f"   - Stable solar radiation → Predictable PV performance")
            print(f"   - Lower climate risk → Stable long-term investment")
        else:
            print(f"   - Moderate solar radiation changes")
            print(f"   - Balanced risk profile")

        # Generate AI insights
        if all_installations:
            adoption_rate_val = (total_installations / n_farmers) * 100
            avg_roi_val = sum(inst['roi'] for inst in all_installations) / len(all_installations)
            avg_cf_val = sum(inst['capacity_factor'] for inst in all_installations) / len(all_installations)

            # Generate AI insights (only if print_insights=True)
            insights = _generate_pv_suitability_insights(
                scenario_display=scenario_display,
                adoption_rate=adoption_rate_val,
                avg_roi=avg_roi_val,
                avg_capacity_factor=avg_cf_val,
                total_capacity_kw=total_capacity_kw
            )

            if print_insights:
                print(f"\n📊 AI-Generated Insights:")
                for viz_name, insight in insights.items():
                    print(f"\n  {viz_name}:")
                    print(f"    {insight}")

        print(f"\n💡 Policy Recommendation:")
        print(f"   To increase PV adoption from {(total_installations / n_farmers) * 100:.1f}%:")
        print(f"   - Increase green credit rate (currently €{model.pv_developer_agents[0].green_credit_rate:.3f}/kWh)")
        print(f"   - Provide installation subsidies for marginal agricultural land")
        print(f"   - Streamline grid connection permitting")

    else:
        print(f"\n⚠️  No PV developer agents found. Ensure --pv-developers flag is set.")

    # Generate PV suitability visualizations (per acceptance criteria)
    print(f"\n{'='*80}")
    print(f"GENERATING PV SUITABILITY VISUALIZATIONS")
    print(f"{'='*80}\n")

    try:
        from use_cases.cca.scripts.pv_suitability_viz import generate_pv_suitability_visualizations

        # Use timestamped output path from results
        timestamped_output = results.get('output_path', output_dir)
        viz_files = generate_pv_suitability_visualizations(
            model=model,
            scenario=scenario,
            output_dir=f"{timestamped_output}/visualizations"
        )

        if viz_files:
            print(f"\n📊 Generated PV Suitability Visualizations:")
            for viz_type, file_path in viz_files.items():
                print(f"   - {viz_type}: {file_path}")
    except Exception as e:
        print(f"\n⚠️  Warning: Could not generate PV suitability visualizations: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"✅ Results saved to: {output_dir}/")
    print(f"   - Text summary: {output_dir}/{scenario}/{scenario}_results.txt")
    print(f"{'='*80}\n")

    # Add insights to results if they were generated
    if 'insights' in locals():
        results['ai_insights'] = insights

    return results


def query_cca_04_all_scenarios(
    data_path: str,
    n_farmers: int = 3,  # Consistent default across all CCA cases
    n_collectives: int = 2,  # Multi-level ABM: community level
    n_markets: int = 1,  # Multi-level ABM: market level
    n_policies: int = 1,  # Multi-level ABM: policy level
    n_pv_developers: int = 2,
    n_years: int = 10,
    output_dir: str = None,
    geojson: dict = None,
    farmer_locations: list = None  # NEW (2025-10-21)
):
    """
    Run CCA-04 for ALL climate scenarios and create comparative analysis.

    This matches the CCA-04 acceptance criteria:
    "evaluate land suitability for photovoltaic (PV) installations based on
    current and future climate conditions" (plural scenarios)
    """
    from pathlib import Path

    scenarios = ['rcp26', 'rcp45', 'rcp85']
    results_by_scenario = {}

    if output_dir is None:
        cca_dir = Path(__file__).parent.parent
        output_dir = str(cca_dir / "results" / "cca_04")

    print(f"\n{'='*80}")
    print(f"CCA-04: PV SUITABILITY - MULTI-SCENARIO COMPARISON")
    print(f"{'='*80}")
    print(f"Running {len(scenarios)} climate scenarios: {', '.join([s.upper() for s in scenarios])}")
    print(f"Duration: {n_years} years per scenario")
    print(f"Farmers: {n_farmers} (land parcels)")
    print(f"PV Developers: {n_pv_developers} (energy companies)")
    print(f"{'='*80}\n")

    # Run each scenario
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] Running {scenario.upper()}...\n")
        result = query_cca_04(
            data_path=data_path,
            scenario=scenario,
            n_farmers=n_farmers,
            n_collectives=n_collectives,
            n_markets=n_markets,
            n_policies=n_policies,
            n_pv_developers=n_pv_developers,
            n_years=n_years,
            output_dir=output_dir,
            geojson=geojson,
            print_insights=False,  # Don't print individual insights - only comparison insights
            farmer_locations=farmer_locations  # NEW (2025-10-21)
        )
        results_by_scenario[scenario] = result

    # Comparative analysis
    print(f"\n{'='*80}")
    print(f"MULTI-SCENARIO PV SUITABILITY COMPARISON")
    print(f"{'='*80}\n")

    for scenario in scenarios:
        result = results_by_scenario[scenario]
        model = result.get('model')

        if model and hasattr(model, 'pv_developer_agents') and model.pv_developer_agents:
            total_installations = sum(len(dev.pv_installations) for dev in model.pv_developer_agents)
            total_capacity = sum(dev.total_capacity_installed for dev in model.pv_developer_agents)
            adoption_rate = (total_installations / n_farmers) * 100 if n_farmers > 0 else 0

            print(f"📊 {scenario.upper()}:")
            print(f"   Installations: {total_installations} / {n_farmers} parcels ({adoption_rate:.1f}%)")
            print(f"   Total Capacity: {total_capacity:,.0f} kW")
            print(f"   Farmers with PV: {len(model.farmers_with_pv)}")
            print()

    # Climate impact summary
    print(f"\n🌡️  Climate Scenario Impact on PV Adoption:")
    print(f"   RCP 2.6: Stable solar radiation → Predictable long-term PV performance")
    print(f"   RCP 4.5: Moderate changes → Balanced risk-reward profile")
    print(f"   RCP 8.5: Higher solar radiation → Best PV performance but climate risks")

    # Generate multi-scenario visualizations
    print(f"\n{'='*80}")
    print(f"GENERATING MULTI-SCENARIO VISUALIZATIONS")
    print(f"{'='*80}\n")

    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        from pathlib import Path
        import sys

        # Import scenario utilities for display names
        sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
        from scenario_utils import get_scenario_display_name

        # Use timestamped output from first scenario for comparison visualizations
        first_scenario_result = results_by_scenario[scenarios[0]]
        timestamped_output = first_scenario_result.get('output_path', output_dir)
        viz_dir = Path(timestamped_output) / "visualizations"
        viz_dir.mkdir(parents=True, exist_ok=True)

        # Collect data across scenarios with display names
        scenario_data = {}
        for scenario in scenarios:
            result = results_by_scenario[scenario]
            model = result.get('model')

            if model and hasattr(model, 'pv_developer_agents') and model.pv_developer_agents:
                total_installations = sum(len(dev.pv_installations) for dev in model.pv_developer_agents)
                total_capacity = sum(dev.total_capacity_installed for dev in model.pv_developer_agents)
                total_revenue = sum(dev.annual_revenue for dev in model.pv_developer_agents)

                # Use user-friendly display name
                display_name = get_scenario_display_name(scenario, use_case="cca")
                scenario_data[display_name] = {
                    'installations': total_installations,
                    'capacity_kw': total_capacity,
                    'revenue': total_revenue,
                    'adoption_rate': (total_installations / n_farmers) * 100 if n_farmers > 0 else 0
                }

        if scenario_data:
            # Create multi-scenario comparison plot
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    'PV Installations by Scenario',
                    'Total Capacity (kW) by Scenario',
                    'Adoption Rate (%) by Scenario',
                    'Annual Revenue (€) by Scenario'
                ),
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "bar"}, {"type": "bar"}]]
            )

            scenarios_upper = list(scenario_data.keys())

            # Plot 1: Installations
            fig.add_trace(
                go.Bar(
                    x=scenarios_upper,
                    y=[scenario_data[s]['installations'] for s in scenarios_upper],
                    name='Installations',
                    marker_color='#2ecc71',
                    text=[f"{scenario_data[s]['installations']}" for s in scenarios_upper],
                    textposition='auto'
                ),
                row=1, col=1
            )

            # Plot 2: Capacity
            fig.add_trace(
                go.Bar(
                    x=scenarios_upper,
                    y=[scenario_data[s]['capacity_kw'] for s in scenarios_upper],
                    name='Capacity (kW)',
                    marker_color='#f39c12',
                    text=[f"{scenario_data[s]['capacity_kw']:,.0f} kW" for s in scenarios_upper],
                    textposition='auto'
                ),
                row=1, col=2
            )

            # Plot 3: Adoption Rate
            fig.add_trace(
                go.Bar(
                    x=scenarios_upper,
                    y=[scenario_data[s]['adoption_rate'] for s in scenarios_upper],
                    name='Adoption Rate (%)',
                    marker_color='#3498db',
                    text=[f"{scenario_data[s]['adoption_rate']:.1f}%" for s in scenarios_upper],
                    textposition='auto'
                ),
                row=2, col=1
            )

            # Plot 4: Revenue
            fig.add_trace(
                go.Bar(
                    x=scenarios_upper,
                    y=[scenario_data[s]['revenue'] for s in scenarios_upper],
                    name='Revenue (€)',
                    marker_color='#9b59b6',
                    text=[f"€{scenario_data[s]['revenue']:,.0f}" for s in scenarios_upper],
                    textposition='auto'
                ),
                row=2, col=2
            )

            fig.update_layout(
                title_text="Multi-Scenario PV Suitability Comparison (CCA-04)",
                showlegend=False,
                height=800
            )

            output_file = viz_dir / "multi_scenario_pv_comparison.html"
            fig.write_html(str(output_file))
            print(f"✅ Generated: {output_file}")

    except Exception as e:
        print(f"⚠️  Warning: Could not generate multi-scenario visualizations: {e}")

    # Generate AI insights for comparison mode
    print(f"\n📊 AI-Generated Insights:")
    comparison_insights = _generate_comparison_insights_cca04(results_by_scenario, n_farmers)
    for viz_name, insight in comparison_insights.items():
        print(f"\n  {viz_name}:")
        print(f"    {insight}")

    print(f"\n{'='*80}")
    print(f"✅ Multi-scenario results saved to: {output_dir}/")
    print(f"{'='*80}\n")

    return results_by_scenario


def _generate_comparison_insights_cca04(results_by_scenario: dict, n_farmers: int):
    """
    Generate LLM-powered insights for CCA-04 COMPARISON MODE visualizations.

    Args:
        results_by_scenario: Dict mapping scenario name -> result dict
        n_farmers: Number of farmers/parcels

    Returns:
        Dict of insights for each comparison visualization
    """
    try:
        from openai import OpenAI
        client = OpenAI()

        # Extract comparison data
        scenario_names = []
        installations = []
        capacities = []
        adoption_rates = []
        avg_rois = []

        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in results_by_scenario:
                scenario_names.append(get_scenario_display_name(scenario, use_case="cca"))
                result = results_by_scenario[scenario]
                model = result.get('model')

                if model and hasattr(model, 'pv_developer_agents') and model.pv_developer_agents:
                    total_inst = sum(len(dev.pv_installations) for dev in model.pv_developer_agents)
                    total_cap = sum(dev.total_capacity_installed for dev in model.pv_developer_agents)

                    all_inst = []
                    for dev in model.pv_developer_agents:
                        all_inst.extend(dev.pv_installations)

                    avg_roi = sum(inst['roi'] for inst in all_inst) / len(all_inst) if all_inst else 0

                    installations.append(total_inst)
                    capacities.append(total_cap)
                    adoption_rates.append((total_inst / n_farmers) * 100)
                    avg_rois.append(avg_roi)

        # Prepare summary
        data_summary = f"""
Multi-Scenario PV Suitability Comparison (CCA-04):
- Scenarios: {', '.join(scenario_names)}
- Installations: {dict(zip(scenario_names, installations))}
- Total Capacity: {dict(zip(scenario_names, [f'{c:,.0f} kW' for c in capacities]))}
- Adoption Rates: {dict(zip(scenario_names, [f'{r:.1f}%' for r in adoption_rates]))}
- Average ROI: {dict(zip(scenario_names, [f'{r:.1%}' for r in avg_rois]))}
"""

        insights = {}

        # 1. Financial Viability Comparison (ROI Heatmap)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a renewable energy financial analyst evaluating PV investment viability under different climate scenarios. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Financial Viability ROI Heatmap showing PV investment returns across {', '.join(scenario_names)}: {dict(zip(scenario_names, [f'{r:.1%}' for r in avg_rois]))}. How do climate pathways affect long-term PV profitability? Which scenario offers the most attractive risk-adjusted returns for investors?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Financial Viability Comparison (ROI Heatmap)"] = response.choices[0].message.content.strip()

        # 2. Technical Performance Comparison (Capacity Factor Maps)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a solar energy engineer analyzing PV system performance under climate change. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Technical Performance (Capacity Factor Maps) showing total installed capacity: {dict(zip(scenario_names, [f'{c:,.0f} kW' for c in capacities]))}. How do solar radiation patterns evolve under different climate scenarios? What technical specifications should PV systems adopt to maximize performance across scenarios?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Technical Performance Comparison (Capacity Factor Maps)"] = response.choices[0].message.content.strip()

        # 3. Adoption Dynamics Comparison (Time-Series)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a clean energy policy advisor analyzing PV adoption trajectories under climate scenarios. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Adoption Dynamics Time-Series showing adoption rates: {dict(zip(scenario_names, [f'{r:.1f}%' for r in adoption_rates]))}. What market barriers prevent higher adoption even under favorable climate conditions? What policy interventions should Thessaloniki prioritize to accelerate PV deployment across all scenarios?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Adoption Dynamics Comparison (Time-Series)"] = response.choices[0].message.content.strip()

        # 4. Policy Recommendations Comparison (Investment Acceleration)
        max_adoption = max(adoption_rates) if adoption_rates else 0
        min_adoption = min(adoption_rates) if adoption_rates else 0
        adoption_gap = max_adoption - min_adoption

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a regional energy transition strategist developing robust PV deployment policies. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Policy Recommendations Dashboard for PV deployment. Adoption rates vary from {min_adoption:.1f}% to {max_adoption:.1f}% (gap: {adoption_gap:.1f}%). What scenario-agnostic policies should Thessaloniki implement to ensure robust PV adoption across all climate pathways?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Policy Recommendations Comparison (Investment Acceleration)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate LLM insights: {e}")
        # Fallback generic insights
        return {
            "Financial Viability Comparison (ROI Heatmap)": f"PV investment returns vary across scenarios: {dict(zip(scenario_names, [f'{r:.1%}' for r in avg_rois]))}, revealing differential climate sensitivity in long-term profitability",
            "Technical Performance Comparison (Capacity Factor Maps)": f"Installed capacity differs by scenario: {dict(zip(scenario_names, [f'{c:,.0f} kW' for c in capacities]))}, indicating climate-dependent technical performance",
            "Adoption Dynamics Comparison (Time-Series)": f"Adoption rates span {dict(zip(scenario_names, [f'{r:.1f}%' for r in adoption_rates]))}, showing market barriers persist across scenarios",
            "Policy Recommendations Comparison (Investment Acceleration)": f"Robust policies needed to close adoption gap from {min(adoption_rates):.1f}% to {max(adoption_rates):.1f}% across all climate pathways"
        }


if __name__ == "__main__":
    # Example usage
    query_cca_04(
        data_path="/app/data",
        scenario="rcp45",
        n_farmers=3,  # Consistent default across all CCA cases
        n_collectives=2,
        n_markets=1,
        n_policies=1,
        n_pv_developers=2,
        n_years=10
    )
