"""
GCP-16: Monitor Feedback Loop Between Policy and Financial Institutions

User Story: "As a Policymaker
I want to monitor the feedback loop between policy changes and financial institution behavior
So that I can understand how green credit policies affect lending patterns and adjust policies accordingly."

This query focuses on:
- Policy → Financial Institutions → PV Adoption → Policy cycle
- Policy effectiveness evaluation over time
- Adaptive policy adjustment mechanisms
- Financial institution response to policy signals
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


def _generate_feedback_loop_insights(policy_scenario, adoption_improvement, default_change, subsidy_change, approval_rate):
    """Generate AI insights for feedback loop analysis."""
    try:
        client = OpenAI()

        effectiveness = "HIGHLY EFFECTIVE" if (adoption_improvement > 0.05 and default_change < 0.05) else (
            "EFFECTIVE" if adoption_improvement > 0.02 else (
            "INEFFECTIVE" if adoption_improvement < -0.02 else "STABLE"
        ))

        data_summary = f"""
Policy Feedback Loop Analysis ({policy_scenario}):
- Feedback Effectiveness: {effectiveness}
- Adoption Improvement: {adoption_improvement:+.1%}
- Default Rate Change: {default_change:+.1%}
- Subsidy Rate Change: {subsidy_change:+.1%}
- Financial Approval Rate: {approval_rate:.1%}
"""

        insights = {}

        # Feedback Loop Dashboard (12-Panel Grid: 4 rows x 3 cols)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a policy evaluation expert analyzing adaptive green credit policy feedback mechanisms. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Feedback Loop Dashboard with 12 subplots (4x3 grid): Row 1 (Policy Adjustments): Subsidy Rate ({subsidy_change:+.1%}), Loan Interest Rate, PV Adoption ({adoption_improvement:+.1%}); Row 2 (FI Response): Loan Approval ({approval_rate:.1%}), Portfolio Risk, Credit Threshold; Row 3 (Loan Dynamics): Active Loans, Loan Volume, Default Rate ({default_change:+.1%}); Row 4 (Effectiveness): Subsidy Spending, Subsidy-Adoption Correlation, Risk-Default Correlation. How effectively do policy adjustments cascade through financial institutions to drive adoption?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Feedback Loop Dashboard (12-Panel: Policy → FI → Loans → Outcomes)"] = response.choices[0].message.content.strip()

        # Adaptive Policy Mechanisms (Downward & Upward Flows)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a systems analyst studying policy-market feedback dynamics. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nEvaluate the downward flow (Policy sets subsidies → FI adjusts approval thresholds → Adoption changes) and upward flow (Adoption results → FI reports defaults → Policy evaluates effectiveness) shown in the 12-panel dashboard. Is the {effectiveness} feedback loop creating virtuous cycles or facing friction? What does {subsidy_change:+.1%} subsidy change yielding {adoption_improvement:+.1%} adoption improvement tell us?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Adaptive Policy Mechanisms (Downward & Upward Flow Analysis)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate AI insights: {e}")
        return {
            "Feedback Loop Dashboard (12-Panel: Policy → FI → Loans → Outcomes)": f"{effectiveness} feedback loop with {adoption_improvement:+.1%} adoption improvement from {subsidy_change:+.1%} subsidy change, showing {'strong' if adoption_improvement > 0.02 else 'weak'} policy-market coupling across 12 interconnected metrics",
            "Adaptive Policy Mechanisms (Downward & Upward Flow Analysis)": f"Downward cascade (subsidy {subsidy_change:+.1%} → approval {approval_rate:.1%}) and upward aggregation (adoption → default {default_change:+.1%} → evaluation) demonstrate {'efficient' if default_change < 0.05 else 'stressed'} multi-level coordination"
        }


def query_gcp_16(
    data_path: str,
    scenario: str = 'rcp45',
    policy_scenario: str = None,  # IGNORED - GCP-16 always runs all policy scenarios
    n_years: int = 10,
    n_landowners: int = 20,
    n_financial_institutions: int = 2,
    n_policymakers: int = 1,
    output_dir: str = None,
    geojson: dict = None,
    farmer_locations: list = None
):
    """
    GCP-16: Monitor feedback loop between policy and financial institutions.

    NOTE: This query ALWAYS runs ALL THREE policy scenarios (low_support, moderate_support, high_support)
    to enable comprehensive policy comparison. The policy_scenario parameter is IGNORED.

    Args:
        data_path: Path to GCP data directory
        scenario: Climate scenario (rcp26, rcp45, rcp85)
        policy_scenario: IGNORED (GCP-16 runs all policies automatically)
        n_years: Number of years to simulate (longer periods show feedback better)
        n_landowners: Number of landowner agents
        n_financial_institutions: Number of financial institution agents
        n_policymakers: Number of policymaker agents
        output_dir: Output directory (default: results/gcp_16)
        geojson: GeoJSON polygon for spatial filtering
        farmer_locations: User-specified landowner locations with crops

    Returns:
        Dict mapping policy_scenario -> results
    """
    # GCP-16 ALWAYS runs all policy scenarios for comparison
    policy_scenarios = ['low_support', 'moderate_support', 'high_support']

    print(f"\n{'='*80}")
    print(f"GCP-16: Policy Feedback Loop Monitoring - MULTI-POLICY COMPARISON")
    print(f"{'='*80}")
    print(f"Climate Scenario: {get_scenario_display_name(scenario)}")
    print(f"Policy Scenarios: {', '.join(policy_scenarios)} (ALL)")
    print(f"Duration: {n_years} years")
    print(f"Landowners: {n_landowners}")
    print(f"{'='*80}\n")

    print(f"   Feedback Loop Components:")
    print(f"   1. Policy Level: Sets green credit policies (subsidies, loan rates)")
    print(f"   2. Market Level: Financial institutions respond (loan approvals, risk assessment)")
    print(f"   3. Individual Level: Landowners adopt PV (or not)")
    print(f"   4. Upward Flow: Adoption statistics → Policy evaluation")
    print(f"   5. Policy Adjustment: Policies adapt based on effectiveness\n")

    if policy_scenario is not None:
        print(f"   ⚠️  NOTE: --policy flag is IGNORED for GCP-16")
        print(f"   GCP-16 automatically runs ALL policy scenarios for comprehensive comparison\n")

    # Set default output directory
    if output_dir is None:
        gcp_dir = Path(__file__).parent.parent
        output_dir = str(gcp_dir / "results" / "gcp_16")

    results_by_policy = {}

    # Run each policy scenario
    for i, policy in enumerate(policy_scenarios, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(policy_scenarios)}] Running {policy.replace('_', ' ').title()} policy...")
        print(f"{'='*80}\n")

        results = run_simulation_with_results(
            scenario=scenario,
            policy_scenario=policy,
            n_years=n_years,
            n_landowners=n_landowners,
            n_financial_institutions=n_financial_institutions,
            n_policymakers=n_policymakers,
            output_dir=output_dir,
            data_path=data_path,
            geojson=geojson,
            farmer_locations=farmer_locations
        )

        results_by_policy[policy] = results

    # Analyze feedback loops for all policy scenarios
    print(f"\n{'='*80}")
    print(f"GCP-16 RESULTS: MULTI-POLICY FEEDBACK LOOP ANALYSIS")
    print(f"{'='*80}\n")

    for policy in policy_scenarios:
        results = results_by_policy[policy]
        model = results.get('model')
        yearly_stats = results.get('yearly_stats', [])

        if not (model and yearly_stats):
            continue

        print(f"\n{'─'*80}")
        print(f"POLICY: {policy.replace('_', ' ').title()}")
        print(f"{'─'*80}\n")

        # === 1. POLICY LEVEL ===
        print(f"🏛️  POLICY LEVEL - Adaptive Policy Adjustment:")
        if model.policymaker_agents:
            for pm in model.policymaker_agents:
                print(f"\n   {pm.policy_name}:")
                print(f"   Policy Goals:")
                print(f"     - Target PV Adoption Rate: {pm.policy_goals.get('target_pv_adoption_rate', 0.0):.1%}")
                print(f"     - Financial Stability: {pm.policy_goals.get('financial_stability', 0.0):.1%}")
                print(f"     - Budget Constraint: €{pm.policy_goals.get('budget_constraint', 0.0):,.0f}")

                print(f"\n   Current Policy Effectiveness:")
                print(f"     - Actual PV Adoption Rate: {pm.policy_effectiveness['pv_adoption_rate']:.1%}")
                print(f"     - Financial Default Rate: {pm.policy_effectiveness['financial_default_rate']:.1%}")
                print(f"     - Total Subsidy Spending: €{pm.policy_effectiveness['total_subsidy_spending']:,.0f}")

                # Policy adjustment history
                if len(pm.policy_history) > 0:
                    print(f"\n   Policy Adjustment Timeline:")
                    print(f"     {'Year':<8} {'Subsidy Rate':<15} {'Loan Rate':<12} {'Adoption':<12} {'Default Rate':<15}")
                    print(f"     " + "-" * 70)

                    for hist in pm.policy_history:
                        print(f"     {hist['year']:<8} "
                              f"{hist['pv_subsidy_rate']:>13.1%}  "
                              f"{hist['loan_rate']:>10.2%}  "
                              f"{hist['adoption_rate']:>10.1%}  "
                              f"{hist['default_rate']:>13.1%}")

                    # Analyze policy changes
                    initial = pm.policy_history[0]
                    final = pm.policy_history[-1]

                    subsidy_change = final['pv_subsidy_rate'] - initial['pv_subsidy_rate']
                    adoption_change = final['adoption_rate'] - initial['adoption_rate']

                    print(f"\n   Policy Adjustment Summary:")
                    print(f"     Subsidy Rate Change: {subsidy_change:+.1%} (from {initial['pv_subsidy_rate']:.1%} to {final['pv_subsidy_rate']:.1%})")
                    print(f"     Adoption Change: {adoption_change:+.1%} (from {initial['adoption_rate']:.1%} to {final['adoption_rate']:.1%})")

                    if subsidy_change > 0 and adoption_change > 0:
                        print(f"\n     ✓ Policy adjustment was EFFECTIVE")
                        print(f"       → Increased subsidies led to higher adoption")
                    elif subsidy_change > 0 and adoption_change <= 0:
                        print(f"\n     ⚠️  Policy adjustment had LIMITED EFFECT")
                        print(f"       → Increased subsidies did not boost adoption")
                        print(f"       → Consider other policy mechanisms (loan guarantees, outreach)")
                    elif subsidy_change < 0 and adoption_change > 0:
                        print(f"\n     ✓ Policy was EFFICIENTLY OPTIMIZED")
                        print(f"       → Reduced subsidies while maintaining/growing adoption")
                    else:
                        print(f"\n     → Policy remained STABLE")

        # === 2. MARKET LEVEL ===
        print(f"\n💰 MARKET LEVEL - Financial Institution Response:")
        if model.financial_institution_agents:
            for fi in model.financial_institution_agents:
                portfolio_state = fi.get_portfolio_state()

                print(f"\n   {portfolio_state['institution_name']}:")
                print(f"     Lending Performance:")
                print(f"       - Total Loan Volume: €{portfolio_state['total_loan_volume']:,.0f}")
                print(f"       - Approval Rate: {portfolio_state['approval_rate']:.1%}")
                print(f"       - Default Rate: {portfolio_state['default_rate']:.1%}")
                print(f"       - Portfolio Risk Score: {portfolio_state['portfolio_risk_score']:.2f}")

                print(f"\n     Risk Management:")
                print(f"       - Credit Score Threshold: {portfolio_state['credit_score_threshold']:.0f}")
                print(f"       - Active Loans: {portfolio_state['active_loans']}")
                print(f"       - Defaulted Loans: {portfolio_state['defaulted_loans']}")

                # Analyze lending pattern changes
                if portfolio_state['default_rate'] > 0.10:
                    print(f"\n     ⚠️  HIGH DEFAULT RATE ({portfolio_state['default_rate']:.1%})")
                    print(f"       → Financial institution has tightened credit standards")
                    print(f"       → Policy should consider loan guarantees to reduce risk")
                elif portfolio_state['approval_rate'] < 0.5:
                    print(f"\n     ⚠️  LOW APPROVAL RATE ({portfolio_state['approval_rate']:.1%})")
                    print(f"       → Many landowners being denied loans")
                    print(f"       → Policy should increase loan guarantees or subsidies")
                else:
                    print(f"\n     ✓ Healthy lending environment")
                    print(f"       → Financial institution is supporting PV adoption")

        # === 3. INDIVIDUAL LEVEL ===
        print(f"\n🧑 INDIVIDUAL LEVEL - Landowner Adoption Behavior:")
        final_year = yearly_stats[-1]
        print(f"   Final Year ({final_year['year']}):")
        print(f"     PV Adopters: {final_year['pv_adopters']} ({final_year['pv_adoption_rate']:.1%})")
        print(f"     Total PV Capacity: {final_year['total_pv_capacity_kw']:,.0f} kW")

        # === 4. FEEDBACK LOOP DYNAMICS ===
        print(f"\n🔄 FEEDBACK LOOP DYNAMICS:")

        print(f"\n   1. DOWNWARD FLOW (Policy → Market → Individual):")
        if model.policymaker_agents and model.financial_institution_agents:
            pm = model.policymaker_agents[0]
            fi = model.financial_institution_agents[0]
            portfolio_state = fi.get_portfolio_state()

            print(f"      a) Policy sets subsidy rate: {pm.pv_subsidy_rate:.1%}")
            print(f"      b) Policy sets low-interest loan rate: {pm.low_interest_loan_rate:.2%}")
            print(f"      c) Financial institution responds with approval rate: {portfolio_state['approval_rate']:.1%}")
            print(f"      d) Landowners adopt PV: {final_year['pv_adoption_rate']:.1%}")

        print(f"\n   2. UPWARD FLOW (Individual → Market → Policy):")
        print(f"      a) Landowners submit {final_year['total_loans_approved'] + final_year['total_loans_denied']} loan applications")
        print(f"      b) Financial institutions approve {final_year['total_loans_approved']} loans")
        print(f"      c) {final_year['pv_adopters']} landowners adopt PV")
        print(f"      d) Policy evaluates effectiveness: {final_year['pv_adoption_rate']:.1%} adoption vs target")
        if model.policymaker_agents:
            target = model.policymaker_agents[0].policy_goals.get('target_pv_adoption_rate', 0.3)
            gap = target - final_year['pv_adoption_rate']
            print(f"      e) Adoption gap: {gap:+.1%} → Policy adjusts subsidies")

        # === 5. FEEDBACK EFFECTIVENESS ===
        print(f"\n📊 FEEDBACK LOOP EFFECTIVENESS:")

        if len(yearly_stats) >= 5:
            # Compare early vs late years
            early_stats = yearly_stats[:len(yearly_stats)//3]
            late_stats = yearly_stats[-len(yearly_stats)//3:]

            early_avg_adoption = sum(s['pv_adoption_rate'] for s in early_stats) / len(early_stats)
            late_avg_adoption = sum(s['pv_adoption_rate'] for s in late_stats) / len(late_stats)

            early_avg_default = sum(s['avg_default_rate'] for s in early_stats) / len(early_stats)
            late_avg_default = sum(s['avg_default_rate'] for s in late_stats) / len(late_stats)

            adoption_improvement = late_avg_adoption - early_avg_adoption
            default_change = late_avg_default - early_avg_default

            print(f"   Early Years (Avg):")
            print(f"     - PV Adoption: {early_avg_adoption:.1%}")
            print(f"     - Default Rate: {early_avg_default:.1%}")

            print(f"\n   Late Years (Avg):")
            print(f"     - PV Adoption: {late_avg_adoption:.1%}")
            print(f"     - Default Rate: {late_avg_default:.1%}")

            print(f"\n   System Evolution:")
            print(f"     - Adoption Improvement: {adoption_improvement:+.1%}")
            print(f"     - Default Rate Change: {default_change:+.1%}")

            # Overall feedback assessment
            print(f"\n   💡 Feedback Loop Assessment:")
            if adoption_improvement > 0.05 and default_change < 0.05:
                print(f"      ✓✓ HIGHLY EFFECTIVE feedback loop")
                print(f"         → Adoption increased while maintaining financial stability")
            elif adoption_improvement > 0.02:
                print(f"      ✓ EFFECTIVE feedback loop")
                print(f"         → Policy adjustments are driving adoption growth")
            elif adoption_improvement < -0.02:
                print(f"      ⚠️  INEFFECTIVE feedback loop")
                print(f"         → Policy adjustments not improving outcomes")
                print(f"         → Consider alternative policy mechanisms")
            else:
                print(f"      → STABLE feedback loop")
                print(f"         → System reached equilibrium")

            # Generate AI insights for this policy scenario
            print(f"\n📊 AI-Generated Insights:")

            # Get subsidy change and approval rate from model
            subsidy_change = 0.0
            approval_rate = 0.0
            if model.policymaker_agents and len(model.policymaker_agents[0].policy_history) > 0:
                pm = model.policymaker_agents[0]
                initial = pm.policy_history[0]
                final = pm.policy_history[-1]
                subsidy_change = final['pv_subsidy_rate'] - initial['pv_subsidy_rate']

            if model.financial_institution_agents:
                fi = model.financial_institution_agents[0]
                portfolio_state = fi.get_portfolio_state()
                approval_rate = portfolio_state['approval_rate']

            insights = _generate_feedback_loop_insights(
                policy_scenario=policy,
                adoption_improvement=adoption_improvement,
                default_change=default_change,
                subsidy_change=subsidy_change,
                approval_rate=approval_rate
            )
            for viz_name, insight in insights.items():
                print(f"\n  {viz_name}:")
                print(f"    {insight}")

            # Store insights for this policy
            results_by_policy[policy]['ai_insights'] = insights

    # Generate feedback loop visualizations
    print(f"\n{'='*80}")
    print(f"GENERATING FEEDBACK LOOP VISUALIZATIONS")
    print(f"{'='*80}\n")

    try:
        from use_cases.gcp.scripts.gcp_visualizations import generate_gcp_16_visualizations

        visualization_files = generate_gcp_16_visualizations(
            results_by_policy,
            scenario=scenario,
            output_dir=f"{results.get('output_path', output_dir)}/visualizations",
            data_path=data_path
        )

        if visualization_files:
            print(f"\n📊 Generated Visualizations:")
            for viz_type, file_path in visualization_files.items():
                print(f"   - {viz_type}: {file_path}")

    except Exception as e:
        print(f"\n⚠️  Warning: Could not generate feedback loop visualizations: {e}")
        print("   Install dependencies: pip install plotly")

    print(f"\n{'='*80}")
    print(f"✅ GCP-16 Multi-Policy Analysis Complete!")
    print(f"   - Results: {output_dir}/")
    print(f"   - Policy scenarios analyzed: {', '.join(policy_scenarios)}")
    print(f"   - Feedback loop visualizations generated for comprehensive comparison")
    print(f"{'='*80}\n")

    return results_by_policy


if __name__ == "__main__":
    # Example usage - GCP-16 automatically runs ALL policy scenarios
    # NOTE: policy_scenario parameter is IGNORED
    query_gcp_16(
        data_path="/Users/theanomamouka/Desktop/TRANSITION/transition/backend/data/GCP",
        scenario="rcp45",
        n_years=15,  # Longer period to see policy adjustments
        n_landowners=20,
        n_financial_institutions=2,
        n_policymakers=1
    )
