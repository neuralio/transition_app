"""
Run TRANSITION GCP (Green Credit Policy) Simulation

This script implements Use Case 2 (UC-GCP) from the TRANSITION deliverable D1.1.

Key Features:
- Multi-level ABM simulation (Individual, Market, Policy)
- PV adoption by landowners under green credit policies
- Loan evaluation by financial institutions
- Policy feedback loops (policy effectiveness → policy adjustment)

Data Source: backend/data/GCP/
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Add GCP utils for scenario display names
gcp_utils_path = Path(__file__).parent.parent / "utils"
sys.path.insert(0, str(gcp_utils_path))

from use_cases.gcp.models.gcp_model import GCPModel
from scenario_utils import get_scenario_display_name


def run_simulation_with_results(
    scenario: str,
    policy_scenario: str = 'moderate_support',
    n_years: int = 10,
    n_landowners: int = 20,
    n_financial_institutions: int = 2,
    n_policymakers: int = 1,
    output_dir: str = "results",
    data_path: str = "backend/data/GCP",
    config_path: str = None,
    geojson: dict = None,
    farmer_locations: list = None  # NEW (2025-10-21)
):
    """
    Run GCP simulation with comprehensive results tracking.

    Args:
        scenario: Climate scenario (rcp26, rcp45, rcp85)
        policy_scenario: Green credit policy scenario (low_support, moderate_support, high_support)
        n_years: Number of years to simulate (default: 10)
        n_landowners: Number of landowner agents (individual level)
        n_financial_institutions: Number of financial institution agents (market level)
        n_policymakers: Number of policymaker agents (policy level)
        output_dir: Directory for output files
        data_path: Path to GCP data directory
        config_path: Path to config.yaml (optional, will auto-detect if None)

    Returns:
        Dict with simulation results
    """
    # Get user-friendly display names
    scenario_display = get_scenario_display_name(scenario) if scenario else "All Scenarios"
    policy_display = policy_scenario.replace('_', ' ').title() if policy_scenario else "All Policies"

    print("=" * 80)
    print(f"TRANSITION GCP SIMULATION: {scenario_display} | Policy: {policy_display}")
    print("=" * 80)
    print(f"Use Case: Green Credit Policy (UC-GCP)")

    # Initialize model
    print(f"\n1. Initializing model...")
    print(f"   - Climate Scenario: {scenario_display}")
    print(f"   - Policy Scenario: {policy_display}")
    print(f"   - Landowners: {n_landowners}")
    print(f"   - Financial Institutions: {n_financial_institutions}")
    print(f"   - Policymakers: {n_policymakers}")
    print(f"   - Duration: {n_years} years")
    print(f"   - Data Path: {data_path}")

    # Load config
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config.yaml'

    import yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Convert relative path to absolute
    data_path_abs = str((Path(project_root) / data_path).resolve())

    print("🔥 ABOUT TO CREATE GCPModel", flush=True)
    print(f"   n_landowners={n_landowners}", flush=True)
    print(f"   farmer_locations={farmer_locations}", flush=True)
    print(f"   geojson={'provided' if geojson else 'None'}", flush=True)

    model = GCPModel(
        n_landowners=n_landowners,
        n_financial_institutions=n_financial_institutions,
        n_policymakers=n_policymakers,
        n_years=n_years,
        scenario=scenario,
        policy_scenario=policy_scenario,
        config=config,
        geojson=geojson,
        farmer_locations=farmer_locations  # NEW (2025-10-21)
    )

    print(f"\n   Multi-Level ABM Enabled:")
    print(f"   - Individual Level: {n_landowners} landowner(s)")
    print(f"   - Market Level: {n_financial_institutions} financial institution(s)")
    print(f"   - Policy Level: {n_policymakers} policymaker(s)")

    # Run simulation
    print(f"\n2. Running simulation ({n_years} years)...")
    start_time = time.time()

    # Store results for basic reporting
    yearly_stats = []
    yearly_landowner_snapshots = []  # Store landowner state for all years

    for year_idx in range(n_years):
        year = model.start_year + year_idx

        # Step the model
        model.step()

        # Collect basic stats
        landowner_agents = model.landowner_agents

        if landowner_agents:
            pv_adopters = sum(1 for lo in landowner_agents if lo.has_pv)
            non_adopters = len(landowner_agents) - pv_adopters
            pv_adoption_rate = pv_adopters / len(landowner_agents) if landowner_agents else 0.0

            # Calculate total PV capacity
            total_pv_capacity = sum(lo.pv_capacity_kw for lo in landowner_agents if lo.has_pv)

            # Financial institution metrics
            total_loans_approved = 0
            total_loans_denied = 0
            total_defaults = 0
            avg_default_rate = 0.0

            # GCP-16 Compliance: Financial institution temporal metrics
            avg_approval_rate = 0.0
            avg_portfolio_risk_score = 0.0
            avg_credit_score_threshold = 0.0
            total_active_loans = 0
            total_loan_volume = 0.0

            if model.financial_institution_agents:
                for fi in model.financial_institution_agents:
                    total_loans_approved += len(fi.approved_loans)
                    total_loans_denied += len(fi.denied_loans)
                    total_defaults += len(fi.defaulted_loans)

                total_loans = sum(len(fi.approved_loans) for fi in model.financial_institution_agents)
                total_defaulted = sum(len(fi.defaulted_loans) for fi in model.financial_institution_agents)
                avg_default_rate = total_defaulted / total_loans if total_loans > 0 else 0.0

                # GCP-16 Compliance: Collect FI temporal metrics
                for fi in model.financial_institution_agents:
                    portfolio_state = fi.get_portfolio_state()
                    avg_approval_rate += portfolio_state['approval_rate']
                    avg_portfolio_risk_score += portfolio_state['portfolio_risk_score']
                    avg_credit_score_threshold += portfolio_state['credit_score_threshold']
                    total_active_loans += portfolio_state['active_loans']
                    total_loan_volume += portfolio_state['total_loan_volume']

                n_fi = len(model.financial_institution_agents)
                avg_approval_rate /= n_fi
                avg_portfolio_risk_score /= n_fi
                avg_credit_score_threshold /= n_fi

            # Policy metrics
            avg_subsidy_rate = 0.0
            total_subsidy_spending = model.total_subsidy_spending

            if model.policymaker_agents:
                avg_subsidy_rate = sum(p.pv_subsidy_rate for p in model.policymaker_agents) / len(model.policymaker_agents)

            # Energy savings metrics (GCP-03 compliance)
            total_annual_energy_savings = sum(lo.annual_energy_savings for lo in landowner_agents if lo.has_pv)
            avg_annual_energy_savings = total_annual_energy_savings / pv_adopters if pv_adopters > 0 else 0.0
            total_annual_feed_in_revenue = sum(lo.annual_feed_in_revenue for lo in landowner_agents if lo.has_pv)

            # ✅ FIX: Get demographic data from model's DataCollector
            adoption_by_fs = model._compute_adoption_by_financial_situation()
            adoption_by_rt = model._compute_adoption_by_risk_tolerance()
            avg_roi_by_fs = model._compute_avg_roi_by_financial_situation()
            avg_payback_by_rt = model._compute_avg_payback_by_risk_tolerance()

            yearly_stats.append({
                'year': year,
                'pv_adopters': pv_adopters,
                'non_adopters': non_adopters,
                'pv_adoption_rate': pv_adoption_rate,
                'total_pv_capacity_kw': total_pv_capacity,
                'total_loans_approved': total_loans_approved,
                'total_loans_denied': total_loans_denied,
                'total_defaults': total_defaults,
                'avg_default_rate': avg_default_rate,
                'avg_subsidy_rate': avg_subsidy_rate,
                'total_subsidy_spending': total_subsidy_spending,
                # Energy savings metrics (GCP-03 compliance)
                'total_annual_energy_savings': total_annual_energy_savings,
                'avg_annual_energy_savings': avg_annual_energy_savings,
                'total_annual_feed_in_revenue': total_annual_feed_in_revenue,
                # ✅ FIX: Demographic breakdown metrics (GCP-03 compliance)
                'adoption_by_financial_situation': adoption_by_fs,
                'adoption_by_risk_tolerance': adoption_by_rt,
                'avg_roi_by_financial_situation': avg_roi_by_fs,
                'avg_payback_by_risk_tolerance': avg_payback_by_rt,
                # GCP-16 Compliance: Financial institution temporal metrics
                'avg_approval_rate': avg_approval_rate,
                'avg_portfolio_risk_score': avg_portfolio_risk_score,
                'avg_credit_score_threshold': avg_credit_score_threshold,
                'total_active_loans': total_active_loans,
                'total_loan_volume': total_loan_volume
            })

            # Capture landowner snapshot for visualization
            landowner_snapshot = []
            for lo in landowner_agents:
                landowner_snapshot.append({
                    'id': lo.unique_id,
                    'lat': lo.lat,
                    'lon': lo.lon,
                    'has_pv': lo.has_pv,
                    'pv_capacity_kw': lo.pv_capacity_kw,
                    'loan_approved': lo.loan_approved,
                    'financial_situation': lo.financial_situation,
                    'risk_tolerance': lo.risk_tolerance,
                    'area_type': lo.area_type,  # GCP-07 compliance: urban/rural filtering
                    'roi': lo.roi,
                    'payback_period': lo.payback_period,
                    'annual_profit': lo.annual_profit,
                    'installation_cost': lo.installation_cost,
                    'annual_loan_payment': lo.annual_loan_payment
                })

            yearly_landowner_snapshots.append({
                'year': year,
                'landowners': landowner_snapshot
            })

            print(f"   Year {year}: {pv_adopters} PV adopters ({pv_adoption_rate:.1%}) | "
                  f"Capacity: {total_pv_capacity:.0f} kW | "
                  f"Loans: {total_loans_approved} approved, {total_loans_denied} denied | "
                  f"Default rate: {avg_default_rate:.1%}")
        else:
            print(f"   Year {year}: No landowner data available")

    elapsed = time.time() - start_time
    print(f"\n   ✅ Simulation complete in {elapsed:.2f} seconds")

    # Print summary
    print(f"\n3. Summary Statistics:")
    if yearly_stats:
        final_year = yearly_stats[-1]

        print(f"\n   Final Year ({final_year['year']}) PV Adoption:")
        print(f"     PV Adopters: {final_year['pv_adopters']}")
        print(f"     Non-Adopters: {final_year['non_adopters']}")
        print(f"     Adoption Rate: {final_year['pv_adoption_rate']:.1%}")
        print(f"     Total PV Capacity: {final_year['total_pv_capacity_kw']:,.0f} kW")

        print(f"\n   Loan Statistics:")
        print(f"     Total Loans Approved: {final_year['total_loans_approved']}")
        print(f"     Total Loans Denied: {final_year['total_loans_denied']}")
        print(f"     Total Defaults: {final_year['total_defaults']}")
        print(f"     Average Default Rate: {final_year['avg_default_rate']:.1%}")

        print(f"\n   Policy Metrics:")
        print(f"     Average Subsidy Rate: {final_year['avg_subsidy_rate']:.1%}")
        print(f"     Total Subsidy Spending: €{final_year['total_subsidy_spending']:,.2f}")

        # Calculate average adoption rate over simulation
        avg_adoption_rate = sum(s['pv_adoption_rate'] for s in yearly_stats) / len(yearly_stats)
        print(f"\n   Average Adoption Rate (over {n_years} years): {avg_adoption_rate:.1%}")

    # Financial institution portfolio summary
    if model.financial_institution_agents:
        print(f"\n   Financial Institution Portfolio Summary:")
        for fi in model.financial_institution_agents:
            portfolio_state = fi.get_portfolio_state()
            print(f"     {portfolio_state['institution_name']}:")
            print(f"       - Total Loan Volume: €{portfolio_state['total_loan_volume']:,.0f}")
            print(f"       - Active Loans: {portfolio_state['active_loans']}")
            print(f"       - Approval Rate: {portfolio_state['approval_rate']:.1%}")
            print(f"       - Default Rate: {portfolio_state['default_rate']:.1%}")
            print(f"       - Portfolio Risk Score: {portfolio_state['portfolio_risk_score']:.2f}")

    # Policy effectiveness summary
    if model.policymaker_agents:
        print(f"\n   Policy Effectiveness:")
        for pm in model.policymaker_agents:
            print(f"     {pm.policy_name}:")
            print(f"       - PV Adoption Rate: {pm.policy_effectiveness['pv_adoption_rate']:.1%}")
            print(f"       - Financial Default Rate: {pm.policy_effectiveness['financial_default_rate']:.1%}")
            print(f"       - Total Subsidy Spending: €{pm.policy_effectiveness['total_subsidy_spending']:,.0f}")
            print(f"       - Target Adoption Rate: {pm.policy_goals.get('target_pv_adoption_rate', 0.0):.1%}")

            # Policy adjustment insights
            if pm.policy_history:
                initial_subsidy = pm.policy_history[0]['pv_subsidy_rate']
                final_subsidy = pm.policy_history[-1]['pv_subsidy_rate']
                subsidy_change = final_subsidy - initial_subsidy
                print(f"       - Subsidy Rate Change: {subsidy_change:+.1%} (from {initial_subsidy:.1%} to {final_subsidy:.1%})")

    # Export comprehensive results with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scenario_safe = scenario if scenario else "all_scenarios"
    policy_safe = policy_scenario if policy_scenario else "all_policies"
    output_path = Path(output_dir) / scenario_safe / policy_safe / timestamp
    output_path.mkdir(parents=True, exist_ok=True)

    results_file = output_path / f"{scenario_safe}_{policy_safe}_results.txt"
    with open(results_file, 'w') as f:
        f.write(f"GCP Simulation Results - {scenario_display} | Policy: {policy_display}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Simulation Duration: {n_years} years ({model.start_year}-{model.start_year + n_years - 1})\n")
        f.write(f"Number of Landowners: {n_landowners}\n")
        f.write(f"Number of Financial Institutions: {n_financial_institutions}\n")
        f.write(f"Number of Policymakers: {n_policymakers}\n")
        f.write("\n")

        # ===== MULTI-LEVEL ABM: INITIAL CHARACTERISTICS =====

        # Landowner Initial Characteristics (INDIVIDUAL LEVEL - show ALL landowners)
        if hasattr(model, 'landowner_agents') and model.landowner_agents:
            f.write("=" * 80 + "\n")
            f.write(f"INDIVIDUAL LEVEL: LANDOWNER INITIAL CHARACTERISTICS (All {len(model.landowner_agents)} Landowners)\n")
            f.write("=" * 80 + "\n\n")

            # Show ALL landowners (use simple 1-based indexing for clarity)
            for idx, landowner in enumerate(model.landowner_agents, start=1):
                f.write(f"Landowner {idx}:\n")
                f.write(f"  - Location: ({landowner.lat:.4f}, {landowner.lon:.4f})\n")
                f.write(f"  - Land Size: {landowner.land_hectares:.1f} hectares\n")
                f.write(f"  - Financial Situation: {landowner.financial_situation}\n")
                f.write(f"  - Risk Tolerance: {landowner.risk_tolerance}\n")
                initial_crop_display = landowner.initial_crop if landowner.initial_crop else "None (considering PV)"
                f.write(f"  - Initial Land Use: {initial_crop_display}\n")
                f.write(f"  - Area Type: {landowner.area_type}\n")
                f.write("\n")

        # Financial Institution Initial Characteristics (MARKET LEVEL) - use captured initial state
        if hasattr(model, 'initial_characteristics') and 'financial_institutions' in model.initial_characteristics:
            fi_initial = model.initial_characteristics['financial_institutions']
            f.write("=" * 80 + "\n")
            f.write(f"MARKET LEVEL: FINANCIAL INSTITUTION INITIAL CHARACTERISTICS (All {len(fi_initial)} Institutions)\n")
            f.write("=" * 80 + "\n\n")

            for fi_data in fi_initial:
                f.write(f"{fi_data['institution_name']}:\n")
                f.write(f"  - Available Capital: €{fi_data['available_capital']:,.0f}\n")
                f.write(f"  - Green Loan Target: {fi_data['green_loan_target']:.1%}\n")
                f.write(f"  - Credit Score Threshold: {fi_data['credit_score_threshold']:.0f}\n")
                f.write(f"  - Debt-to-Income Threshold: {fi_data['debt_to_income_threshold']:.1%}\n")
                f.write(f"  - Loan-to-Value Threshold: {fi_data['loan_to_value_threshold']:.1%}\n")
                f.write(f"  - Reserve Ratio: {fi_data['reserve_ratio']:.1%}\n")
                f.write("\n")

        # Policymaker Initial Characteristics (POLICY LEVEL) - use captured initial state
        if hasattr(model, 'initial_characteristics') and 'policymakers' in model.initial_characteristics:
            policymakers_initial = model.initial_characteristics['policymakers']
            f.write("=" * 80 + "\n")
            f.write(f"POLICY LEVEL: POLICYMAKER INITIAL CHARACTERISTICS (All {len(policymakers_initial)} Policymakers)\n")
            f.write("=" * 80 + "\n\n")

            for pm_data in policymakers_initial:
                f.write(f"{pm_data['policy_name']}:\n")
                f.write(f"  - PV Subsidy Rate: {pm_data['pv_subsidy_rate']:.1%}\n")
                f.write(f"  - Low-Interest Loan Rate: {pm_data['low_interest_loan_rate']:.2%}\n")
                f.write(f"  - Tax Incentive Rate: {pm_data['tax_incentive_rate']:.1%}\n")
                f.write(f"  - Loan Guarantee Rate: {pm_data['loan_guarantee_rate']:.1%}\n")
                f.write(f"  - Budget Constraint: €{pm_data['budget_constraint']:,.0f}\n")
                f.write(f"  - Target PV Adoption Rate: {pm_data['target_pv_adoption_rate']:.1%}\n")
                f.write("\n")

        # Yearly Statistics
        f.write("=" * 80 + "\n")
        f.write("YEARLY STATISTICS\n")
        f.write("=" * 80 + "\n")
        f.write("-" * 80 + "\n")
        for stats in yearly_stats:
            f.write(f"Year {stats['year']}: "
                   f"PV Adopters={stats['pv_adopters']} ({stats['pv_adoption_rate']:.1%}), "
                   f"Capacity={stats['total_pv_capacity_kw']:.0f}kW, "
                   f"Loans Approved={stats['total_loans_approved']}, "
                   f"Default Rate={stats['avg_default_rate']:.1%}\n")

        # Summary Statistics
        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write("SUMMARY STATISTICS\n")
        f.write("=" * 80 + "\n\n")

        if yearly_stats:
            final_year = yearly_stats[-1]
            avg_adoption_rate = sum(s['pv_adoption_rate'] for s in yearly_stats) / len(yearly_stats)

            f.write(f"Final Year ({final_year['year']}) PV Adoption:\n")
            f.write(f"  - PV Adopters: {final_year['pv_adopters']}\n")
            f.write(f"  - Non-Adopters: {final_year['non_adopters']}\n")
            f.write(f"  - Adoption Rate: {final_year['pv_adoption_rate']:.1%}\n")
            f.write(f"  - Total PV Capacity: {final_year['total_pv_capacity_kw']:,.0f} kW\n\n")

            f.write(f"Average Adoption Rate (over {n_years} years): {avg_adoption_rate:.1%}\n\n")

            f.write(f"Loan Statistics:\n")
            f.write(f"  - Total Loans Approved: {final_year['total_loans_approved']}\n")
            f.write(f"  - Total Loans Denied: {final_year['total_loans_denied']}\n")
            f.write(f"  - Total Defaults: {final_year['total_defaults']}\n")
            f.write(f"  - Average Default Rate: {final_year['avg_default_rate']:.1%}\n\n")

            f.write(f"Policy Metrics:\n")
            f.write(f"  - Average Subsidy Rate: {final_year['avg_subsidy_rate']:.1%}\n")
            f.write(f"  - Total Subsidy Spending: €{final_year['total_subsidy_spending']:,.2f}\n")

        # Financial Institution Portfolio
        if model.financial_institution_agents:
            f.write("\n")
            f.write("=" * 80 + "\n")
            f.write("FINANCIAL INSTITUTION PORTFOLIO SUMMARY\n")
            f.write("=" * 80 + "\n\n")

            for fi in model.financial_institution_agents:
                portfolio_state = fi.get_portfolio_state()
                f.write(f"{portfolio_state['institution_name']}:\n")
                f.write(f"  - Total Loan Volume: €{portfolio_state['total_loan_volume']:,.0f}\n")
                f.write(f"  - Active Loans: {portfolio_state['active_loans']}\n")
                f.write(f"  - Approval Rate: {portfolio_state['approval_rate']:.1%}\n")
                f.write(f"  - Default Rate: {portfolio_state['default_rate']:.1%}\n")
                f.write(f"  - Portfolio Risk Score: {portfolio_state['portfolio_risk_score']:.2f}\n")
                f.write(f"  - Total Interest Income: €{portfolio_state['total_interest_income']:,.0f}\n")
                f.write(f"  - Total Defaults: €{portfolio_state['total_defaults']:,.0f}\n\n")

        # Policy Effectiveness
        if model.policymaker_agents:
            f.write("=" * 80 + "\n")
            f.write("POLICY EFFECTIVENESS ANALYSIS\n")
            f.write("=" * 80 + "\n\n")

            for pm in model.policymaker_agents:
                f.write(f"{pm.policy_name}:\n")
                f.write(f"  - PV Adoption Rate: {pm.policy_effectiveness['pv_adoption_rate']:.1%}\n")
                f.write(f"  - Target Adoption Rate: {pm.policy_goals.get('target_pv_adoption_rate', 0.0):.1%}\n")
                f.write(f"  - Financial Default Rate: {pm.policy_effectiveness['financial_default_rate']:.1%}\n")
                f.write(f"  - Total Subsidy Spending: €{pm.policy_effectiveness['total_subsidy_spending']:,.0f}\n")
                f.write(f"  - Budget Constraint: €{pm.policy_goals.get('budget_constraint', 0.0):,.0f}\n\n")

                # Policy history
                if pm.policy_history:
                    f.write(f"  Policy Adjustment History:\n")
                    for i, hist in enumerate(pm.policy_history):
                        f.write(f"    Year {hist['year']}: "
                               f"Subsidy={hist['pv_subsidy_rate']:.1%}, "
                               f"Loan Rate={hist['loan_rate']:.1%}, "
                               f"Adoption={hist['adoption_rate']:.1%}\n")
                    f.write("\n")

    print(f"\n4. Results saved to: {results_file}")
    print(f"\n{'=' * 80}")

    return {
        'scenario': scenario,
        'policy_scenario': policy_scenario,
        'yearly_stats': yearly_stats,
        'yearly_landowner_snapshots': yearly_landowner_snapshots,
        'model': model,
        'output_path': str(output_path)  # Return timestamped output path for visualizations
    }


def run_multi_policy_analysis(
    scenario: str = 'rcp45',
    policy_scenarios: list = ['low_support', 'moderate_support', 'high_support'],
    n_years: int = 10,
    n_landowners: int = 20,
    n_financial_institutions: int = 2,
    n_policymakers: int = 1,
    output_dir: str = "results",
    data_path: str = "backend/data/GCP",
    config_path: str = None
):
    """
    Run simulations for multiple policy scenarios and generate comparative analysis.

    Args:
        scenario: Climate scenario (rcp26, rcp45, rcp85)
        policy_scenarios: List of policy scenarios to simulate
        n_years: Number of years to simulate
        n_landowners: Number of landowner agents
        n_financial_institutions: Number of financial institution agents
        n_policymakers: Number of policymaker agents
        output_dir: Directory for output files
        data_path: Path to GCP data directory
        config_path: Path to config.yaml

    Returns:
        Dict mapping policy_scenario -> results
    """
    # Get user-friendly display name
    scenario_display = get_scenario_display_name(scenario) if scenario else "All Scenarios"
    policy_displays = [p.replace('_', ' ').title() for p in policy_scenarios]

    print("\n" + "=" * 80)
    print("MULTI-POLICY ANALYSIS - GREEN CREDIT POLICY")
    print("=" * 80)
    print(f"Use Case: UC-GCP")
    print(f"Climate Scenario: {scenario_display}")
    print(f"Policy Scenarios: {', '.join(policy_displays)}")
    print("=" * 80)

    results_by_policy = {}

    # Run each policy scenario
    for i, policy_scenario in enumerate(policy_scenarios, 1):
        print(f"\n[{i}/{len(policy_scenarios)}] Running {policy_scenario}...\n")

        results = run_simulation_with_results(
            scenario=scenario,
            policy_scenario=policy_scenario,
            n_years=n_years,
            n_landowners=n_landowners,
            n_financial_institutions=n_financial_institutions,
            n_policymakers=n_policymakers,
            output_dir=output_dir,
            data_path=data_path,
            config_path=config_path
        )
        results_by_policy[policy_scenario] = results

        # Small delay between scenarios
        if i < len(policy_scenarios):
            time.sleep(1)

    # Generate comparative report
    print("\n" + "=" * 80)
    print("COMPARATIVE ANALYSIS")
    print("=" * 80)

    print("\nPolicy Scenario Comparison (Final Year):")
    print(f"{'Policy Scenario':<20} {'PV Adoption':<15} {'Capacity (kW)':<15} {'Subsidy €':<15}")
    print("-" * 70)

    for policy_scenario, results in results_by_policy.items():
        stats = results['yearly_stats']
        if stats:
            final_stats = stats[-1]
            print(f"{policy_scenario:<20} "
                  f"{final_stats['pv_adoption_rate']:>13.1%}  "
                  f"{final_stats['total_pv_capacity_kw']:>13,.0f}  "
                  f"€{final_stats['total_subsidy_spending']:>12,.0f}")

    # Policy effectiveness analysis
    if 'low_support' in results_by_policy and 'high_support' in results_by_policy:
        low_stats = results_by_policy['low_support']['yearly_stats'][-1]
        high_stats = results_by_policy['high_support']['yearly_stats'][-1]

        adoption_increase = high_stats['pv_adoption_rate'] - low_stats['pv_adoption_rate']
        subsidy_increase = high_stats['total_subsidy_spending'] - low_stats['total_subsidy_spending']

        print(f"\n💡 Policy Impact (High Support vs Low Support):")
        print(f"   Adoption Increase: {adoption_increase:+.1%}")
        print(f"   Additional Subsidy Cost: €{subsidy_increase:+,.0f}")
        if subsidy_increase > 0:
            cost_per_adoption = subsidy_increase / (adoption_increase * n_landowners) if adoption_increase > 0 else 0
            print(f"   Cost per Additional Adoption: €{cost_per_adoption:,.0f}")

    # Write comparative analysis to file
    output_path = Path(output_dir) / scenario
    output_path.mkdir(parents=True, exist_ok=True)

    comparative_file = output_path / "comparative_policy_analysis.txt"
    with open(comparative_file, 'w') as f:
        f.write("MULTI-POLICY COMPARATIVE ANALYSIS\n")
        f.write("Green Credit Policy (UC-GCP)\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Climate Scenario: {scenario_display}\n")
        f.write(f"Policy Scenarios: {', '.join(policy_displays)}\n")
        f.write(f"Simulation Duration: {n_years} years\n")
        f.write(f"Number of Landowners: {n_landowners}\n\n")

        # Policy comparison table
        f.write("=" * 80 + "\n")
        f.write("POLICY SCENARIO COMPARISON (Final Year)\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"{'Policy Scenario':<20} {'PV Adoption':<15} {'Capacity (kW)':<18} {'Subsidy €':<15}\n")
        f.write("-" * 80 + "\n")

        for policy_scenario, results in results_by_policy.items():
            stats = results['yearly_stats']
            if stats:
                final_stats = stats[-1]
                f.write(f"{policy_scenario:<20} "
                       f"{final_stats['pv_adoption_rate']:>13.1%}  "
                       f"{final_stats['total_pv_capacity_kw']:>16,.0f}  "
                       f"€{final_stats['total_subsidy_spending']:>13,.0f}\n")

        # Policy effectiveness analysis
        if 'low_support' in results_by_policy and 'high_support' in results_by_policy:
            low_stats = results_by_policy['low_support']['yearly_stats'][-1]
            high_stats = results_by_policy['high_support']['yearly_stats'][-1]

            adoption_increase = high_stats['pv_adoption_rate'] - low_stats['pv_adoption_rate']
            subsidy_increase = high_stats['total_subsidy_spending'] - low_stats['total_subsidy_spending']

            f.write("\n")
            f.write("=" * 80 + "\n")
            f.write("POLICY IMPACT ANALYSIS (High Support vs Low Support)\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"PV Adoption:\n")
            f.write(f"  - Low Support: {low_stats['pv_adoption_rate']:.1%}\n")
            f.write(f"  - High Support: {high_stats['pv_adoption_rate']:.1%}\n")
            f.write(f"  - Increase: {adoption_increase:+.1%}\n\n")

            f.write(f"Subsidy Spending:\n")
            f.write(f"  - Low Support: €{low_stats['total_subsidy_spending']:,.0f}\n")
            f.write(f"  - High Support: €{high_stats['total_subsidy_spending']:,.0f}\n")
            f.write(f"  - Increase: €{subsidy_increase:+,.0f}\n\n")

            if subsidy_increase > 0 and adoption_increase > 0:
                cost_per_adoption = subsidy_increase / (adoption_increase * n_landowners)
                f.write(f"Efficiency:\n")
                f.write(f"  - Cost per Additional Adoption: €{cost_per_adoption:,.0f}\n\n")

            f.write("=" * 80 + "\n")
            f.write("POLICY RECOMMENDATIONS\n")
            f.write("=" * 80 + "\n\n")
            f.write("Based on the multi-policy analysis, consider:\n\n")
            f.write("1. Cost-Effectiveness:\n")
            if adoption_increase > 0.1:
                f.write(f"   - High support policies drive significant adoption (+{adoption_increase:.1%})\n")
            else:
                f.write(f"   - Policy impact is moderate - consider targeted interventions\n")
            f.write("\n")
            f.write("2. Budget Allocation:\n")
            f.write(f"   - Optimize subsidy rates to balance adoption and budget constraints\n")
            f.write("\n")
            f.write("3. Risk Management:\n")
            f.write(f"   - Monitor financial institution default rates\n")
            f.write(f"   - Adjust loan guarantees to maintain portfolio health\n")

        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write("Individual policy scenario details available in:\n")
        for policy_scenario in policy_scenarios:
            f.write(f"  - {output_dir}/{scenario}/{policy_scenario}/{scenario}_{policy_scenario}_results.txt\n")
        f.write("=" * 80 + "\n")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {Path(output_dir).absolute()}")
    print(f"  - Comparative analysis: {comparative_file}")
    scenario_safe = scenario if scenario else "all_scenarios"
    for i, policy_scenario in enumerate(policy_scenarios):
        policy_display = policy_displays[i]
        print(f"  - {policy_display}: {output_dir}/{scenario_safe}/{policy_scenario}/{scenario_safe}_{policy_scenario}_results.txt")

    print("\n📊 Next Steps:")
    print("   - GCP-03: PV adoption simulation complete ✅")
    print("   - GCP-07: Generate geographic distribution visualization")
    print("   - GCP-16: Monitor policy feedback loops")

    return results_by_policy


if __name__ == "__main__":
    # Example: Run multi-policy analysis
    results = run_multi_policy_analysis(
        scenario='rcp45',
        policy_scenarios=['low_support', 'moderate_support', 'high_support'],
        n_years=10,
        n_landowners=20,
        n_financial_institutions=2,
        n_policymakers=1,
        output_dir='results',
        data_path='backend/data/GCP'
    )
