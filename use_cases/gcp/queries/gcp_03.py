"""
GCP-03: Simulate PV Adoption by Farmers/Landowners

User Story: "As a Policymaker or Energy Company
I want to simulate the effects of green credit policies on PV adoption by landowners
So that I can evaluate policy effectiveness and optimize green credit schemes."

This query runs a multi-level ABM simulation focusing on:
- PV adoption decisions under various green credit policy scenarios
- Loan approval rates by financial institutions
- Policy effectiveness evaluation
- Financial institution portfolio performance
"""

import sys
from pathlib import Path
from openai import OpenAI

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Add GCP utils for scenario display names
gcp_utils_path = Path(__file__).parent.parent / "utils"
sys.path.insert(0, str(gcp_utils_path))

from use_cases.gcp.scripts.run_gcp_simulation import run_simulation_with_results
from scenario_utils import get_scenario_display_name


def _generate_pv_adoption_insights(policy_scenario, adoption_rate, approval_rate, default_rate, subsidy_spending):
    """Generate AI insights for PV adoption under green credit policies."""
    try:
        client = OpenAI()

        data_summary = f"""
Green Credit Policy Impact on PV Adoption:
- Policy Scenario: {policy_scenario}
- PV Adoption Rate: {adoption_rate:.1%}
- Loan Approval Rate: {approval_rate:.1%}
- Default Rate: {default_rate:.1%}
- Total Subsidy Spending: €{subsidy_spending:,.0f}
"""

        insights = {}

        # Comprehensive Time-Series Dashboard (10-Panel Grid: 5 rows x 2 cols)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a green energy transition analyst evaluating policy-driven adoption across multiple metrics. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Time-Series Dashboard with 10 subplots (5x2 grid): (1) PV Adoption reaching {adoption_rate:.1%}, (2) Total Capacity growth, (3) Loan Applications (approved/denied), (4) Default Rate evolution, (5) Policy Subsidy Rate trajectory, (6) Total Subsidy Spending €{subsidy_spending:,.0f}, (7) Adopters vs Non-Adopters split, (8) Loan Approval Rate {approval_rate:.1%}, (9) Energy Savings & Feed-in Revenue, (10) Avg Savings per Installation. What do these 10 interconnected time-series reveal about policy-market-adoption dynamics?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Comprehensive Time-Series Dashboard (10-Panel: Adoption, Capacity, Loans, Defaults, Policy, Energy)"] = response.choices[0].message.content.strip()

        # Financial Institution Lending Behavior (Approval/Default Dynamics)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a green finance risk manager analyzing institutional lending patterns. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Loan Performance Dashboard showing {approval_rate:.1%} approval rate and {default_rate:.1%} default rate. Are financial institutions balancing growth with risk management? What does this signal about loan product design and credit assessment quality?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Financial Institution Lending Behavior (Performance Dashboard)"] = response.choices[0].message.content.strip()

        # Policy Cost-Effectiveness (Subsidy Spending vs Adoption)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a public finance analyst evaluating green subsidy efficiency. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAssess the Policy Cost Dashboard showing €{subsidy_spending:,.0f} total spending for {adoption_rate:.1%} adoption under {policy_scenario}. What is the cost per adopter? Is this subsidy level delivering value for money, or should policymakers adjust incentive structures?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Policy Cost-Effectiveness (Subsidy ROI Analysis)"] = response.choices[0].message.content.strip()

        # Multi-Policy Comparison (Cross-Scenario Strategic Insights)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a policy strategist comparing green credit interventions. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nBased on the Multi-Policy Comparison visualizations, how does {policy_scenario} (adoption: {adoption_rate:.1%}, cost: €{subsidy_spending:,.0f}) perform against alternative support levels? Should policymakers increase, maintain, or reduce incentive intensity?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Multi-Policy Strategic Comparison (Optimization Insights)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate AI insights: {e}")
        return {
            "PV Adoption Trajectory (Time-Series Chart)": f"{policy_scenario} policy achieves {adoption_rate:.1%} adoption, indicating {'strong' if adoption_rate > 0.4 else 'moderate' if adoption_rate > 0.2 else 'weak'} policy effectiveness with {'accelerating' if adoption_rate > 0.4 else 'steady'} growth trajectory",
            "Financial Institution Lending Behavior (Performance Dashboard)": f"Loan approval rate of {approval_rate:.1%} with {default_rate:.1%} defaults indicates {'aggressive' if approval_rate > 0.7 else 'balanced' if approval_rate > 0.5 else 'conservative'} risk appetite, with {'healthy' if default_rate < 0.08 else 'elevated'} portfolio risk levels",
            "Policy Cost-Effectiveness (Subsidy ROI Analysis)": f"Subsidy spending of €{subsidy_spending:,.0f} for {adoption_rate:.1%} adoption yields {'excellent' if (subsidy_spending / max(0.01, adoption_rate)) < 100000 else 'moderate' if (subsidy_spending / max(0.01, adoption_rate)) < 200000 else 'costly'} cost-efficiency ratio",
            "Multi-Policy Strategic Comparison (Optimization Insights)": f"Comparative analysis suggests {policy_scenario} represents {'optimal' if policy_scenario == 'moderate_support' else 'aggressive' if policy_scenario == 'high_support' else 'conservative'} intervention level, with room for {'increased intensity' if policy_scenario == 'low_support' else 'efficiency gains' if policy_scenario == 'high_support' else 'fine-tuning'}"
        }


def query_gcp_03(
    data_path: str,
    scenario: str = 'rcp45',
    policy_scenario: str = 'moderate_support',
    n_years: int = 10,
    n_landowners: int = 20,
    n_financial_institutions: int = 2,
    n_policymakers: int = 1,
    output_dir: str = None,
    geojson: dict = None,
    farmer_locations: list = None  # NEW (2025-10-21)
):
    """
    GCP-03: Simulate PV adoption by farmers/landowners under green credit policies.

    Args:
        data_path: Path to GCP data directory (backend/data/GCP)
        scenario: Climate scenario (rcp26, rcp45, rcp85)
        policy_scenario: Green credit policy scenario (low_support, moderate_support, high_support)
        n_years: Number of years to simulate
        n_landowners: Number of landowner agents
        n_financial_institutions: Number of financial institution agents
        n_policymakers: Number of policymaker agents
        output_dir: Output directory (default: results/gcp_03)

    Returns:
        Dict with simulation results
    """
    print(f"\n{'='*80}")
    print(f"GCP-03: PV Adoption Simulation Under Green Credit Policies")
    print(f"{'='*80}")
    print(f"Climate Scenario: {get_scenario_display_name(scenario)}")
    print(f"Policy Scenario: {policy_scenario}")
    print(f"Duration: {n_years} years")
    print(f"Landowners: {n_landowners}")
    print(f"Financial Institutions: {n_financial_institutions}")
    print(f"{'='*80}\n")

    # Set default output directory (absolute path to avoid nesting)
    if output_dir is None:
        # Use absolute path relative to project root
        gcp_dir = Path(__file__).parent.parent  # Go up to use_cases/gcp/
        output_dir = str(gcp_dir / "results" / "gcp_03")

    # Run simulation with focus on PV adoption
    print("🔄 Running PV adoption simulation with green credit policies...")
    results = run_simulation_with_results(
        scenario=scenario,
        policy_scenario=policy_scenario,
        n_years=n_years,
        n_landowners=n_landowners,
        n_financial_institutions=n_financial_institutions,
        n_policymakers=n_policymakers,
        output_dir=output_dir,
        data_path=data_path,
        geojson=geojson,
        farmer_locations=farmer_locations  # NEW (2025-10-21)
    )

    # Extract key insights
    yearly_stats = results.get('yearly_stats', [])
    model = results.get('model')

    # Display multi-level ABM initial characteristics
    if model:
        print(f"\n{'='*80}")
        print(f"MULTI-LEVEL ABM: INITIAL AGENT CHARACTERISTICS")
        print(f"{'='*80}\n")

        # Individual Level: Landowners
        if hasattr(model, 'landowner_agents') and model.landowner_agents and n_landowners <= 10:
            # Only show all landowners if there are 10 or fewer (to avoid console spam)
            print(f"🏠 Individual Level: Landowners (All {len(model.landowner_agents)}):")
            print("-" * 80)
            for landowner in model.landowner_agents:
                print(f"\nLandowner {landowner.unique_id}:")
                print(f"   • Location: ({landowner.lat:.4f}, {landowner.lon:.4f})")
                print(f"   • Land Size: {landowner.land_hectares:.1f} ha")
                print(f"   • Financial Situation: {landowner.financial_situation}")
                print(f"   • Risk Tolerance: {landowner.risk_tolerance}")
                initial_crop_display = landowner.initial_crop if landowner.initial_crop else "None (considering PV)"
                print(f"   • Initial Land Use: {initial_crop_display}")
        elif hasattr(model, 'landowner_agents') and model.landowner_agents:
            print(f"🏠 Individual Level: {len(model.landowner_agents)} Landowners (see results file for full details)")

        # Market Level: Financial Institutions
        if hasattr(model, 'financial_institution_agents') and model.financial_institution_agents:
            print(f"\n🏦 Market Level: Financial Institutions ({len(model.financial_institution_agents)}):")
            print("-" * 80)
            for institution in model.financial_institution_agents:
                print(f"\n{institution.institution_name}:")
                print(f"   • Available Capital: €{institution._get_available_capital():,.0f}")
                print(f"   • Green Loan Target: {institution.target_green_loan_percentage:.1%}")
                print(f"   • Credit Score Threshold: {institution.credit_score_threshold:.0f}")
                print(f"   • Debt-to-Income Threshold: {institution.debt_to_income_threshold:.1%}")
                print(f"   • Loan-to-Value Threshold: {institution.loan_to_value_threshold:.1%}")

        # Policy Level: Policymakers
        if hasattr(model, 'policymaker_agents') and model.policymaker_agents:
            print(f"\n🏛️  Policy Level: Policymakers ({len(model.policymaker_agents)}):")
            print("-" * 80)
            for policymaker in model.policymaker_agents:
                print(f"\n{policymaker.policy_name}:")
                print(f"   • PV Subsidy Rate: {policymaker.pv_subsidy_rate:.1%}")
                print(f"   • Low-Interest Loan Rate: {policymaker.low_interest_loan_rate:.2%}")
                print(f"   • Tax Incentive Rate: {policymaker.tax_incentive_rate:.1%}")
                budget = policymaker.policy_goals.get('budget_constraint', 0)
                print(f"   • Budget Constraint: €{budget:,.0f}")

    if yearly_stats:
        print(f"\n{'='*80}")
        print(f"GCP-03 RESULTS: PV ADOPTION ANALYSIS")
        print(f"{'='*80}\n")

        # Calculate average adoption metrics
        avg_adoption_rate = sum(s['pv_adoption_rate'] for s in yearly_stats) / len(yearly_stats)
        final_year = yearly_stats[-1]

        print(f"📊 PV Adoption Performance ({n_years} years under {policy_scenario}):")
        print(f"   Average Adoption Rate: {avg_adoption_rate:.1%}")
        print(f"   Final Year Adoption: {final_year['pv_adoption_rate']:.1%} ({final_year['pv_adopters']} landowners)")
        print(f"   Total PV Capacity: {final_year['total_pv_capacity_kw']:,.0f} kW")

        # Energy savings (GCP-03 compliance: key benefit factor)
        print(f"\n⚡ Energy Savings & Revenue (Key Adoption Benefits):")
        print(f"   Total Annual Energy Savings: €{final_year['total_annual_energy_savings']:,.0f}")
        print(f"   Average per Installation: €{final_year['avg_annual_energy_savings']:,.0f}")
        print(f"   Total Feed-in Revenue: €{final_year['total_annual_feed_in_revenue']:,.0f}")
        print(f"   Combined Economic Benefit: €{final_year['total_annual_energy_savings'] + final_year['total_annual_feed_in_revenue']:,.0f}/year")

        # Loan statistics
        approval_rate = (
            final_year['total_loans_approved'] /
            (final_year['total_loans_approved'] + final_year['total_loans_denied'])
            if (final_year['total_loans_approved'] + final_year['total_loans_denied']) > 0
            else 0.0
        )

        print(f"\n💰 Financial Institution Performance:")
        print(f"   Loan Approval Rate: {approval_rate:.1%}")
        print(f"   Total Loans Approved: {final_year['total_loans_approved']}")
        print(f"   Total Loans Denied: {final_year['total_loans_denied']}")
        print(f"   Default Rate: {final_year['avg_default_rate']:.1%}")

        # Policy effectiveness
        print(f"\n🏛️  Policy Effectiveness:")
        print(f"   Average Subsidy Rate: {final_year['avg_subsidy_rate']:.1%}")
        print(f"   Total Subsidy Spending: €{final_year['total_subsidy_spending']:,.0f}")

        # Recommendations based on policy scenario
        print(f"\n💡 Policy Recommendations:")
        if policy_scenario == 'low_support':
            print(f"   Under {policy_scenario}:")
            print(f"   - Adoption is limited ({final_year['pv_adoption_rate']:.1%})")
            print(f"   - Consider increasing subsidies to boost adoption")
            print(f"   - Evaluate loan guarantee programs")
        elif policy_scenario == 'moderate_support':
            print(f"   Under {policy_scenario}:")
            print(f"   - Adoption is moderate ({final_year['pv_adoption_rate']:.1%})")
            print(f"   - Balance cost-effectiveness with adoption goals")
            print(f"   - Monitor financial institution risk")
        elif policy_scenario == 'high_support':
            print(f"   Under {policy_scenario}:")
            print(f"   - Adoption is high ({final_year['pv_adoption_rate']:.1%})")
            print(f"   - Evaluate budget sustainability")
            print(f"   - Consider phasing out incentives as market matures")

        # Temporal trends
        if len(yearly_stats) >= 3:
            early_adoption = sum(s['pv_adoption_rate'] for s in yearly_stats[:3]) / 3
            late_adoption = sum(s['pv_adoption_rate'] for s in yearly_stats[-3:]) / 3
            adoption_growth = late_adoption - early_adoption

            print(f"\n📈 Temporal Dynamics:")
            print(f"   Adoption Growth: {adoption_growth:+.1%} (early vs late years)")
            if adoption_growth > 0.1:
                print(f"   ✓ Strong growth trend - policies are effective")
            elif adoption_growth < 0:
                print(f"   ⚠️  Declining trend - review policy effectiveness")
            else:
                print(f"   → Stable trend - market saturation or policy equilibrium")

        # Generate AI insights
        print(f"\n📊 AI-Generated Insights:")
        insights = _generate_pv_adoption_insights(
            policy_scenario=policy_scenario,
            adoption_rate=final_year['pv_adoption_rate'],
            approval_rate=approval_rate,
            default_rate=final_year['avg_default_rate'],
            subsidy_spending=final_year['total_subsidy_spending']
        )
        for viz_name, insight in insights.items():
            print(f"\n  {viz_name}:")
            print(f"    {insight}")

    # Generate visualizations
    print(f"\n{'='*80}")
    print(f"GENERATING VISUALIZATIONS")
    print(f"{'='*80}\n")

    try:
        from use_cases.gcp.scripts.gcp_visualizations import generate_gcp_03_visualizations

        # Format results for visualization function
        results_by_policy = {
            policy_scenario: results
        }

        # Use timestamped output path from results
        timestamped_output = results.get('output_path', output_dir)
        visualization_files = generate_gcp_03_visualizations(
            results_by_policy,
            scenario=scenario,
            output_dir=f"{timestamped_output}/visualizations",
            data_path=data_path
        )

        if visualization_files:
            print(f"\n📊 Generated Visualizations:")
            for viz_type, file_path in visualization_files.items():
                print(f"   - {viz_type}: {file_path}")

            # Highlight demographic breakdown (GCP-03 compliance)
            print(f"\n🎯 GCP-03 COMPLIANCE: Demographic & Geographic Variations")
            print(f"   ✅ Geographic Distribution: {policy_scenario}_pv_map.html")
            print(f"   ✅ Demographic Breakdown: {policy_scenario}_demographic_breakdown.html")
            print(f"      - Adoption rates by financial situation (poor/moderate/wealthy)")
            print(f"      - Adoption rates by risk tolerance (low/moderate/high)")
            print(f"      - ROI analysis by financial situation")
            print(f"      - Payback period by risk tolerance")
            print(f"      - Distribution of adopters by demographics")
    except Exception as e:
        print(f"\n⚠️  Warning: Could not generate visualizations: {e}")
        print("   Install dependencies: pip install plotly folium")

    print(f"\n{'='*80}")
    print(f"✅ Results saved to: {output_dir}/")
    print(f"   - Text summary: {output_dir}/{scenario}/{policy_scenario}/{scenario}_{policy_scenario}_results.txt")
    print(f"{'='*80}\n")

    # Add insights to results if they were generated
    if 'insights' in locals():
        results['ai_insights'] = insights

    return results


def query_gcp_03_all_policies(
    data_path: str,
    scenario: str = 'rcp45',
    n_years: int = 10,
    n_landowners: int = 20,
    n_financial_institutions: int = 2,
    n_policymakers: int = 1,
    output_dir: str = None,
    farmer_locations: list = None  # NEW (2025-10-21)
):
    """
    Run GCP-03 for ALL policy scenarios and create comparative analysis.

    This matches the GCP-03 acceptance criteria:
    "Users should be able to compare PV adoption under different green credit policy scenarios."

    Args:
        data_path: Path to GCP data directory
        scenario: Climate scenario (rcp26, rcp45, rcp85)
        n_years: Number of years to simulate
        n_landowners: Number of landowner agents
        n_financial_institutions: Number of financial institution agents
        n_policymakers: Number of policymaker agents
        output_dir: Output directory (default: results/gcp_03)

    Returns:
        Dict mapping policy_scenario -> results
    """
    policy_scenarios = ['low_support', 'moderate_support', 'high_support']

    print(f"\n{'='*80}")
    print(f"GCP-03: Multi-Policy PV Adoption Comparison")
    print(f"{'='*80}")
    print(f"Climate Scenario: {get_scenario_display_name(scenario)}")
    print(f"Policy Scenarios: {', '.join(policy_scenarios)}")
    print(f"Duration: {n_years} years")
    print(f"Landowners: {n_landowners}")
    print(f"{'='*80}\n")

    # Set default output directory
    if output_dir is None:
        gcp_dir = Path(__file__).parent.parent
        output_dir = str(gcp_dir / "results" / "gcp_03")

    results_by_policy = {}

    # Run each policy scenario
    for i, policy_scenario in enumerate(policy_scenarios, 1):
        print(f"\n[{i}/{len(policy_scenarios)}] Running {policy_scenario}...\n")

        result = query_gcp_03(
            data_path=data_path,
            scenario=scenario,
            policy_scenario=policy_scenario,
            n_years=n_years,
            n_landowners=n_landowners,
            n_financial_institutions=n_financial_institutions,
            n_policymakers=n_policymakers,
            output_dir=output_dir,
            farmer_locations=farmer_locations
        )
        results_by_policy[policy_scenario] = result

    # Create comparative analysis
    print(f"\n{'='*80}")
    print(f"COMPARATIVE ANALYSIS: PV ADOPTION ACROSS POLICY SCENARIOS")
    print(f"{'='*80}\n")

    # Compare adoption rates
    print(f"📊 Final Year Adoption Rate Comparison:")
    print(f"{'Policy Scenario':<20} {'Adoption Rate':<15} {'PV Capacity (kW)':<20} {'Subsidy €':<15}")
    print("-" * 75)

    for policy_scenario in policy_scenarios:
        yearly_stats = results_by_policy[policy_scenario].get('yearly_stats', [])

        if yearly_stats:
            final_stats = yearly_stats[-1]
            print(f"{policy_scenario:<20} "
                  f"{final_stats['pv_adoption_rate']:>13.1%}  "
                  f"{final_stats['total_pv_capacity_kw']:>18,.0f}  "
                  f"€{final_stats['total_subsidy_spending']:>13,.0f}")

    # Policy impact analysis
    if 'low_support' in results_by_policy and 'high_support' in results_by_policy:
        low_stats = results_by_policy['low_support']['yearly_stats'][-1]
        high_stats = results_by_policy['high_support']['yearly_stats'][-1]

        adoption_increase = high_stats['pv_adoption_rate'] - low_stats['pv_adoption_rate']
        subsidy_increase = high_stats['total_subsidy_spending'] - low_stats['total_subsidy_spending']

        print(f"\n💡 Policy Impact (High Support vs Low Support):")
        print(f"   Adoption Increase: {adoption_increase:+.1%}")
        print(f"   Additional Subsidy Cost: €{subsidy_increase:+,.0f}")

        cost_per_adoption = None
        if subsidy_increase > 0 and adoption_increase > 0:
            cost_per_adoption = subsidy_increase / (adoption_increase * n_landowners)
            print(f"   Cost per Additional Adoption: €{cost_per_adoption:,.0f}")

        print(f"\n   Recommendation:")
        if cost_per_adoption and cost_per_adoption < 5000:
            print(f"   ✓ High support is cost-effective (€{cost_per_adoption:,.0f} per adoption)")
            print(f"   → Consider implementing high_support policy")
        elif cost_per_adoption and cost_per_adoption < 10000:
            print(f"   → Moderate support balances cost and effectiveness")
            print(f"   → Consider moderate_support or targeted high_support")
        elif cost_per_adoption:
            print(f"   ⚠️  High support is expensive (€{cost_per_adoption:,.0f} per adoption)")
            print(f"   → Evaluate alternative policy mechanisms")
        else:
            print(f"   → Unable to calculate cost-effectiveness (no adoption increase or negative subsidy change)")

    # Generate comparative visualizations
    print(f"\n{'='*80}")
    print(f"GENERATING COMPARATIVE VISUALIZATIONS")
    print(f"{'='*80}\n")

    try:
        from use_cases.gcp.scripts.gcp_visualizations import generate_gcp_03_visualizations

        # Use timestamped output path from results
        timestamped_output = results.get('output_path', output_dir)
        visualization_files = generate_gcp_03_visualizations(
            results_by_policy,
            scenario=scenario,
            output_dir=f"{timestamped_output}/visualizations",
            data_path=data_path
        )

        if visualization_files:
            print(f"\n📊 Generated Comparative Visualizations:")
            for viz_type, file_path in visualization_files.items():
                print(f"   - {viz_type}: {file_path}")
    except Exception as e:
        print(f"\n⚠️  Warning: Could not generate visualizations: {e}")

    print(f"\n{'='*80}")
    print(f"✅ Multi-Policy Analysis Complete!")
    print(f"   - Results: {output_dir}/")
    print(f"   - Policy scenarios compared: {', '.join(policy_scenarios)}")
    print(f"{'='*80}\n")

    return results_by_policy


def query_gcp_03_all_scenarios(
    data_path: str,
    policy_scenario: str = 'moderate_support',
    n_years: int = 10,
    n_landowners: int = 20,
    n_financial_institutions: int = 2,
    n_policymakers: int = 1,
    output_dir: str = None,
    farmer_locations: list = None  # NEW (2025-10-21)
):
    """
    Run GCP-03 for ALL climate scenarios and create comparative analysis.

    This provides comprehensive climate-policy analysis:
    "How does this policy perform across different climate futures?"

    Args:
        data_path: Path to GCP data directory
        policy_scenario: Green credit policy scenario (low_support, moderate_support, high_support)
        n_years: Number of years to simulate
        n_landowners: Number of landowner agents
        n_financial_institutions: Number of financial institution agents
        n_policymakers: Number of policymaker agents
        output_dir: Output directory (default: results/gcp_03)

    Returns:
        Dict mapping scenario -> results
    """
    climate_scenarios = ['rcp26', 'rcp45', 'rcp85']

    print(f"\n{'='*80}")
    print(f"GCP-03: Multi-Scenario Climate Comparison")
    print(f"{'='*80}")
    print(f"Policy Scenario: {policy_scenario}")
    print(f"Climate Scenarios: {', '.join(climate_scenarios)}")
    print(f"Duration: {n_years} years")
    print(f"Landowners: {n_landowners}")
    print(f"{'='*80}\n")

    # Set default output directory
    if output_dir is None:
        gcp_dir = Path(__file__).parent.parent
        output_dir = str(gcp_dir / "results" / "gcp_03")

    results_by_scenario = {}

    # Run each climate scenario
    for i, scenario in enumerate(climate_scenarios, 1):
        print(f"\n[{i}/{len(climate_scenarios)}] Running {get_scenario_display_name(scenario)}...\n")

        result = query_gcp_03(
            data_path=data_path,
            scenario=scenario,
            policy_scenario=policy_scenario,
            n_years=n_years,
            n_landowners=n_landowners,
            n_financial_institutions=n_financial_institutions,
            n_policymakers=n_policymakers,
            output_dir=output_dir,
            farmer_locations=farmer_locations
        )
        results_by_scenario[scenario] = result

    # Create comparative analysis
    print(f"\n{'='*80}")
    print(f"COMPARATIVE ANALYSIS: {policy_scenario.replace('_', ' ').title()} ACROSS CLIMATE SCENARIOS")
    print(f"{'='*80}\n")

    # Compare adoption rates across climate scenarios
    print(f"📊 Final Year Adoption Rate Comparison:")
    print(f"{'Climate Scenario':<40} {'Adoption Rate':<15} {'PV Capacity (kW)':<20} {'Solar Impact':<15}")
    print("-" * 75)

    for scenario in climate_scenarios:
        yearly_stats = results_by_scenario[scenario].get('yearly_stats', [])

        if yearly_stats:
            final_stats = yearly_stats[-1]
            scenario_name = get_scenario_display_name(scenario)
            print(f"{scenario_name:<40} "
                  f"{final_stats['pv_adoption_rate']:>13.1%}  "
                  f"{final_stats['total_pv_capacity_kw']:>18,.0f}  "
                  f"{'Varies' if scenario != 'rcp45' else 'Baseline':>13}")

    # Climate impact analysis
    if 'rcp26' in results_by_scenario and 'rcp85' in results_by_scenario:
        rcp26_stats = results_by_scenario['rcp26']['yearly_stats'][-1]
        rcp85_stats = results_by_scenario['rcp85']['yearly_stats'][-1]

        adoption_diff = rcp85_stats['pv_adoption_rate'] - rcp26_stats['pv_adoption_rate']
        capacity_diff = rcp85_stats['total_pv_capacity_kw'] - rcp26_stats['total_pv_capacity_kw']

        print(f"\n💡 Climate Impact ({get_scenario_display_name('rcp85')} vs {get_scenario_display_name('rcp26')}):")
        print(f"   Adoption Difference: {adoption_diff:+.1%}")
        print(f"   Capacity Difference: {capacity_diff:+,.0f} kW")

        print(f"\n   Interpretation:")
        if abs(adoption_diff) < 0.05:
            print(f"   → Climate scenario has MINIMAL impact on PV adoption")
            print(f"   → Policy effectiveness is climate-robust")
        else:
            print(f"   → Climate scenario SIGNIFICANTLY affects PV adoption")
            print(f"   → Solar radiation variability influences financial attractiveness")

    print(f"\n{'='*80}")
    print(f"✅ Multi-Scenario Analysis Complete!")
    print(f"   - Results: {output_dir}/")
    print(f"   - Climate scenarios compared: {', '.join(climate_scenarios)}")
    print(f"{'='*80}\n")

    return results_by_scenario


if __name__ == "__main__":
    # Example usage
    query_gcp_03(
        data_path="/Users/theanomamouka/Desktop/TRANSITION/transition/backend/data/GCP",
        scenario="rcp45",
        policy_scenario="moderate_support",
        n_years=10,
        n_landowners=20,
        n_financial_institutions=2,
        n_policymakers=1
    )
