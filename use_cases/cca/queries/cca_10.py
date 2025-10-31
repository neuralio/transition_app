"""
CCA-10: Simulate Cross-Scale Interactions

User Story: "As a System User (Farmer, Collective, Energy Company, or Policymaker)
I want to simulate how decisions at one level (e.g., individual farmer decisions) affect other levels (e.g., market and policy)
So that I can understand how climate adaptation strategies impact different scales of the system."

This query runs a full multi-level ABM simulation focusing on:
- Individual → Community → Market → Policy interactions
- Downward flow (top-down influence)
- Upward flow (bottom-up aggregation)
- Lateral flow (peer interactions)
- Feedback loops (policy effectiveness evaluation)
"""

import sys
from pathlib import Path
from openai import OpenAI

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.cca.scripts.run_cca_simulation import run_simulation_with_results
from use_cases.cca.utils.scenario_utils import get_scenario_display_name


def _generate_cross_scale_insights(scenario_display, income_change, wheat_farmers, policy_effectiveness, n_farmers):
    """Generate AI insights for cross-scale interaction analysis."""
    try:
        client = OpenAI()

        data_summary = f"""
Cross-Scale Interaction Analysis:
- Climate Scenario: {scenario_display}
- Income trend: {income_change:+.1f}% change over simulation period
- Final wheat farmers: {wheat_farmers} / {n_farmers} total
- Policy effectiveness: {policy_effectiveness:.1%}
- Multi-level interactions: Individual ↔ Community ↔ Market ↔ Policy
"""

        insights = {}

        # Multi-Level Interaction Network (System Diagram)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a complex systems analyst studying multi-level agent-based models. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Multi-Level Interaction Network showing flows between Individual ({n_farmers} farmers) ↔ Community ↔ Market ↔ Policy levels. How do bottom-up signals (farmer decisions) interact with top-down influences (policy interventions)? What emergent patterns arise from these cross-scale dynamics?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Multi-Level Interaction Network (System Diagram)"] = response.choices[0].message.content.strip()

        # Economic Cascade Effects (Income Evolution Across Levels)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an agricultural economist studying income propagation through market systems. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Income Evolution charts showing {income_change:+.1f}% change under {scenario_display}. How do market price signals propagate from Market → Community → Individual levels? Are feedback effects amplifying or dampening income volatility?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Economic Cascade Effects (Income Evolution Charts)"] = response.choices[0].message.content.strip()

        # Policy Effectiveness Across Scales (Subsidy Impact Analysis)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a policy evaluation specialist analyzing intervention effectiveness in multi-level systems. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAssess the Policy Effectiveness Dashboard showing {policy_effectiveness:.1%} success rate. How effectively do Policy-level subsidies cascade through Community collectives to reach Individual farmers? Are intermediary levels creating friction or amplifying impact?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Policy Effectiveness Across Scales (Impact Dashboard)"] = response.choices[0].message.content.strip()

        # Agent Specialization Dynamics (Crop Distribution Evolution)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an agricultural land-use specialist studying farmer specialization patterns. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Agent Specialization charts showing {wheat_farmers}/{n_farmers} farmers converging to wheat production. What multi-level forces drive this specialization? Do Community peer effects or Market price signals dominate individual crop choices?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Agent Specialization Dynamics (Crop Distribution Charts)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate AI insights: {e}")
        return {
            "Multi-Level Interaction Network (System Diagram)": f"Cross-scale dynamics show bottom-up aggregation ({n_farmers} individual decisions → community → market) and top-down policy influence cascading through system, creating complex feedback loops under {scenario_display}",
            "Economic Cascade Effects (Income Evolution Charts)": f"Income trend of {income_change:+.1f}% reflects market price propagation through multi-level network, with community collectives and market clearing mechanisms mediating volatility transmission",
            "Policy Effectiveness Across Scales (Impact Dashboard)": f"Policy effectiveness at {policy_effectiveness:.1%} indicates {'strong' if policy_effectiveness > 0.7 else 'moderate' if policy_effectiveness > 0.4 else 'weak'} multi-level coordination, with {'efficient' if policy_effectiveness > 0.7 else 'partial'} cascade from policy → market → community → individual levels",
            "Agent Specialization Dynamics (Crop Distribution Charts)": f"Convergence to {wheat_farmers}/{n_farmers} wheat farmers reveals emergent specialization driven by multi-level signals: LUSA suitability (individual), collective norms (community), price incentives (market), and subsidies (policy)"
        }


def query_cca_10(
    data_path: str,
    scenario: str,
    n_years: int = 10,
    n_farmers: int = 3,  # Consistent with CCA-03 and CCA-04
    n_collectives: int = 2,
    n_markets: int = 1,
    n_policies: int = 1,
    n_pv_developers: int = 0,  # Optional: enable for PV feedback loops
    output_dir: str = None,
    geojson: dict = None,
    farmer_locations: list = None  # NEW (2025-10-21)
):
    """
    CCA-10: Simulate cross-scale interactions in multi-level ABM.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        scenario: Climate scenario (rcp26, rcp45, rcp85)
        n_years: Number of years to simulate
        n_farmers: Number of farmer agents (individual level)
        n_collectives: Number of collective agents (community level)
        n_markets: Number of market agents (market level)
        n_policies: Number of policymaker agents (policy level)
        n_pv_developers: Number of PV developer agents (optional, market level)
        output_dir: Output directory (default: results/cca_10)

    Returns:
        Dict with simulation results and cross-scale interaction analysis
    """
    # Get user-friendly display name
    scenario_display = get_scenario_display_name(scenario, use_case="cca")

    print(f"\n{'='*80}")
    print(f"CCA-10: Cross-Scale Interaction Simulation")
    print(f"{'='*80}")
    print(f"Scenario: {scenario_display}")
    print(f"Duration: {n_years} years")
    print(f"{'='*80}")
    print(f"Multi-Level ABM Architecture:")
    print(f"  🧑 Individual Level: {n_farmers} farmers")
    print(f"  👥 Community Level: {n_collectives} collective(s)")
    print(f"  📊 Market Level: {n_markets} commodity market(s)", end="")
    if n_pv_developers > 0:
        print(f" + {n_pv_developers} PV developer(s)")
    else:
        print()
    print(f"  🏛️  Policy Level: {n_policies} policymaker(s)")
    print(f"{'='*80}\n")

    # Set default output directory (absolute path to avoid nesting)
    if output_dir is None:
        # Use absolute path relative to project root
        cca_dir = Path(__file__).parent.parent  # Go up to use_cases/cca/
        output_dir = str(cca_dir / "results" / "cca_10")

    # Run simulation with full multi-level ABM enabled
    print("🔄 Running multi-level ABM with cross-scale interactions...")
    print("\n   Interaction Flows:")
    print("   ⬇️  Downward: Policy → Market → Community → Individual")
    print("   ⬆️  Upward: Individual → Community → Market → Policy")
    print("   ↔️  Lateral: Within-level peer interactions\n")

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
        include_historical=False,
        geojson=geojson,
        farmer_locations=farmer_locations  # NEW (2025-10-21)
    )

    # Analyze cross-scale interactions
    model = results.get('model')
    yearly_stats = results.get('yearly_stats', [])

    if model and yearly_stats:
        print(f"\n{'='*80}")
        print(f"CCA-10 RESULTS: CROSS-SCALE INTERACTION ANALYSIS")
        print(f"{'='*80}\n")

        # 1. INDIVIDUAL LEVEL OUTCOMES
        print(f"🧑 Individual Level (Farmers):")
        final_year = yearly_stats[-1]
        print(f"   Final Year ({final_year['year']}):")
        print(f"   - WHEAT farmers: {final_year['wheat_farmers']}")
        print(f"   - MAIZE farmers: {final_year['maize_farmers']}")
        print(f"   - Total income: €{final_year['total_income']:,.0f}")
        print(f"   - Total production: {final_year['total_production']:.1f} tons")

        # 2. COMMUNITY LEVEL OUTCOMES
        print(f"\n👥 Community Level (Collectives):")
        if model.collective_agents:
            for collective in model.collective_agents:
                n_members = len(collective.members)
                avg_income = (sum(getattr(f, 'annual_income', 0) for f in collective.members) / n_members
                             if n_members > 0 else 0)
                print(f"   {collective.region_name}:")
                print(f"   - Members: {n_members} farmers")
                print(f"   - Average income: €{avg_income:,.2f}/farmer")
                print(f"   - Risk aversion: {collective.social_norms.get('risk_aversion', 0.5):.2f}")

        # 3. MARKET LEVEL OUTCOMES
        print(f"\n📊 Market Level:")
        if model.market_agents:
            for market in model.market_agents:
                print(f"   {market.unique_id}:")
                print(f"   - Wheat price: €{market.crop_prices.get('WHEAT', 0):.2f}/ton")
                print(f"   - Maize price: €{market.crop_prices.get('MAIZE', 0):.2f}/ton")
                print(f"   - Wheat supply: {market.supply.get('WHEAT', 0):.1f} tons")
                print(f"   - Maize supply: {market.supply.get('MAIZE', 0):.1f} tons")

        # 3b. PV DEVELOPER OUTCOMES (if enabled)
        if n_pv_developers > 0 and model.pv_developer_agents:
            print(f"\n   PV Developers (Market Level):")
            for pv_dev in model.pv_developer_agents:
                print(f"   - {pv_dev.company_name}: {len(pv_dev.pv_installations)} installations, "
                      f"{pv_dev.total_capacity_installed:,.0f} kW")

        # 4. POLICY LEVEL OUTCOMES
        print(f"\n🏛️  Policy Level:")
        if model.policy_agents:
            for policy in model.policy_agents:
                print(f"   {policy.unique_id}:")
                print(f"   - Wheat subsidy: {policy.subsidy_rates.get('WHEAT', 0):.1%}")
                print(f"   - Maize subsidy: {policy.subsidy_rates.get('MAIZE', 0):.1%}")
                print(f"   - Food security goal: {policy.policy_goals.get('food_security', 0):.1%}")
                print(f"   - Sustainability goal: {policy.policy_goals.get('sustainability', 0):.1%}")
                print(f"   - Policy effectiveness:")
                for goal, effectiveness in policy.policy_effectiveness.items():
                    print(f"     • {goal}: {effectiveness:.1%}")

        # 5. FEEDBACK LOOPS
        print(f"\n🔄 Feedback Loop Examples:")
        print(f"   Downward (Top-Down):")
        if model.policy_agents and model.market_agents:
            wheat_subsidy = model.policy_agents[0].subsidy_rates.get('WHEAT', 0)
            wheat_price = model.market_agents[0].crop_prices.get('WHEAT', 0)
            print(f"   1. Policy sets wheat subsidy ({wheat_subsidy:.1%}) →")
            print(f"      Market adjusts wheat price (€{wheat_price:.2f}/ton) →")
            print(f"      Farmers plant more wheat ({final_year['wheat_farmers']} farmers)")

        print(f"\n   Upward (Bottom-Up):")
        if yearly_stats:
            wheat_production = final_year['total_production'] * (final_year['wheat_farmers'] / n_farmers)
            print(f"   1. Farmers produce wheat ({wheat_production:.1f} tons) →")
            print(f"      Market updates supply/demand →")
            print(f"      Policy evaluates food security effectiveness")

        print(f"\n   Lateral (Peer-to-Peer):")
        if model.collective_agents and len(model.collective_agents) > 1:
            print(f"   1. Collective agents share knowledge →")
            print(f"      Social norms converge (risk aversion, cooperation)")
        if model.market_agents and len(model.market_agents) > 1:
            print(f"   2. Markets exchange price information →")
            print(f"      Price arbitrage across regions")

        # 6. TEMPORAL DYNAMICS
        print(f"\n📈 Temporal Evolution:")
        if len(yearly_stats) >= 3:
            early_income = sum(s['total_income'] for s in yearly_stats[:3]) / 3
            late_income = sum(s['total_income'] for s in yearly_stats[-3:]) / 3
            income_change = ((late_income - early_income) / early_income) * 100 if early_income > 0 else 0

            print(f"   Income trend: {income_change:+.1f}% (early vs late years)")

            early_wheat = sum(s['wheat_farmers'] for s in yearly_stats[:3]) / 3
            late_wheat = sum(s['wheat_farmers'] for s in yearly_stats[-3:]) / 3
            wheat_change = late_wheat - early_wheat

            print(f"   Wheat adoption: {wheat_change:+.1f} farmers (early vs late)")

        # 7. SCENARIO-SPECIFIC INSIGHTS
        print(f"\n🌡️  Climate Scenario Impact ({scenario_display}):")
        if scenario.lower() == 'rcp85':
            print(f"   - High climate stress → Increased vulnerability")
            print(f"   - Policy response: Higher subsidies needed")
            print(f"   - Market response: Price volatility")
            print(f"   - Community response: Stronger risk aversion")
        elif scenario.lower() == 'rcp26':
            print(f"   - Low climate stress → Stable conditions")
            print(f"   - Policy response: Maintenance mode")
            print(f"   - Market response: Stable prices")
            print(f"   - Community response: Moderate risk tolerance")
        else:
            print(f"   - Moderate climate stress → Gradual adaptation")
            print(f"   - Policy response: Proactive adjustments")
            print(f"   - Market response: Price adjustments")

        print(f"\n💡 Cross-Scale Insights:")
        print(f"   ✓ Individual decisions aggregate to market trends")
        print(f"   ✓ Policy effectiveness depends on farmer response")
        print(f"   ✓ Community norms influence individual behavior")
        print(f"   ✓ Market signals propagate through all levels")

        # Generate AI insights
        if 'income_change' in locals() and model.policy_agents:
            avg_policy_effectiveness = sum(
                policy.policy_effectiveness.get('food_security', 0)
                for policy in model.policy_agents
            ) / len(model.policy_agents)

            print(f"\n📊 AI-Generated Insights:")
            insights = _generate_cross_scale_insights(
                scenario_display=scenario_display,
                income_change=income_change,
                wheat_farmers=final_year['wheat_farmers'],
                policy_effectiveness=avg_policy_effectiveness,
                n_farmers=n_farmers
            )
            for viz_name, insight in insights.items():
                print(f"\n  {viz_name}:")
                print(f"    {insight}")

    # Generate visualizations (including cross-scale interactions)
    print(f"\n{'='*80}")
    print(f"GENERATING VISUALIZATIONS")
    print(f"{'='*80}\n")

    try:
        from use_cases.cca.scripts.visualizations import generate_all_visualizations
        from use_cases.cca.scripts.cross_scale_viz import generate_cross_scale_visualizations

        # Add simulation parameters to results for use in visualizations
        results['simulation_params'] = {
            'n_farmers': n_farmers,
            'n_years': n_years,
            'n_collectives': n_collectives,
            'n_markets': n_markets,
            'n_policies': n_policies,
            'n_pv_developers': n_pv_developers
        }

        # Format results for visualization function
        results_by_scenario = {
            scenario: results
        }

        # Use timestamped output path from results
        timestamped_output = results.get('output_path', output_dir)

        # Generate standard visualizations
        visualization_files = generate_all_visualizations(
            results_by_scenario,
            output_dir=f"{timestamped_output}/visualizations",
            data_path=data_path
        )

        # Generate cross-scale interaction visualizations (CCA-10 specific)
        print(f"\n{'='*80}")
        print(f"GENERATING CROSS-SCALE VISUALIZATIONS (CCA-10)")
        print(f"{'='*80}\n")
        cross_scale_files = generate_cross_scale_visualizations(
            results_by_scenario,
            output_dir=f"{timestamped_output}/visualizations"
        )
        visualization_files.update(cross_scale_files)

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
    print(f"   - Cross-scale diagrams: See information flow, feedback, and network charts")
    print(f"{'='*80}\n")

    # Add insights to results if they were generated
    if 'insights' in locals():
        results['ai_insights'] = insights

    return results


if __name__ == "__main__":
    # Example usage
    query_cca_10(
        data_path="/app/data",
        scenario="rcp45",
        n_years=10,
        n_farmers=3,  # Consistent default across all CCA cases
        n_collectives=2,
        n_markets=1,
        n_policies=1
    )
