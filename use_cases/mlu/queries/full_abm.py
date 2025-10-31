"""
MLU-05: Analyze Land Suitability Using Multi-Level ABM

User Story: As a Policymaker, I want to simulate land-use dynamics using
a multi-level ABM that models interactions between individuals, communities,
markets, and policies.

This query runs the FULL MULTI-LEVEL ABM SIMULATION (what exists now).
"""

import sys
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.mlu.scripts.run_mlu_simulation import (
    run_simulation_with_results,
    run_multi_scenario_analysis
)


def query_full_abm(
    data_path: str,
    scenario: str,
    n_years: int = 10,
    n_parcels: int = 15,
    output_dir: str = "results",
    enable_multi_level: bool = True,
    n_collectives: int = 2,
    n_markets: int = 1,
    n_policies: int = 1,
    enable_ensemble: bool = False,
    ensemble_size: int = 30,
    confidence_level: float = 0.95,
    rl_policy = None
) -> Dict:
    """
    Run full multi-level ABM simulation.

    This is a WRAPPER around the existing simulation code.
    It runs the complete 4-level ML-ABM with all interactions.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA directory
        scenario: Climate scenario (rcp26, rcp45, rcp85, historical)
        n_years: Number of years to simulate
        n_parcels: Number of land parcels
        output_dir: Output directory for results
        enable_multi_level: Enable multi-level ABM (4 levels)
        n_collectives: Number of farmer collectives (community level)
        n_markets: Number of commodity markets (market level)
        n_policies: Number of policymakers (policy level)
        enable_ensemble: Enable Monte Carlo ensemble mode
        ensemble_size: Number of ensemble runs
        confidence_level: Confidence level for uncertainty bands
        rl_policy: Optional RL policy for RL-02

    Returns:
        Dictionary with simulation results and status
    """
    print(f"\n{'='*60}")
    print(f"MLU-05: Analyze Land Suitability Using Multi-Level ABM")
    print(f"{'='*60}")
    print(f"Scenario: {scenario.upper()}")
    print(f"Duration: {n_years} years")
    print(f"Land Parcels: {n_parcels}")
    print(f"Multi-Level ABM: {'✅ ENABLED' if enable_multi_level else '❌ DISABLED'}")
    if enable_multi_level:
        print(f"  - Individual Level: {n_parcels} land parcels")
        print(f"  - Community Level: {n_collectives} farmer collectives")
        print(f"  - Market Level: {n_markets} commodity markets")
        print(f"  - Policy Level: {n_policies} policymakers")
    if enable_ensemble:
        print(f"Mode: 🎲 Monte Carlo Ensemble ({ensemble_size} runs, {confidence_level*100:.0f}% CI)")
    else:
        print(f"Mode: Single simulation run")
    print(f"Output: {output_dir}/")
    print(f"{'='*60}\n")

    try:
        # Run the existing simulation code (NO CHANGES TO EXISTING CODE)
        collector = run_simulation_with_results(
            scenario=scenario,
            n_years=n_years,
            n_parcels=n_parcels,
            n_farmers=None,  # Backward compatibility
            n_pv_installations=None,  # Backward compatibility
            output_dir=output_dir,
            data_path=data_path,
            n_collectives=n_collectives,
            n_markets=n_markets,
            n_policies=n_policies,
            enable_multi_level=enable_multi_level,
            rl_policy=rl_policy
        )

        return {
            'status': 'success',
            'scenario': scenario.upper(),
            'n_years': n_years,
            'n_parcels': n_parcels,
            'multi_level_enabled': enable_multi_level,
            'output_dir': output_dir,
            'message': f"Simulation completed successfully. Results saved to {output_dir}/{scenario}/",
            'collector': collector  # ResultCollector instance with all data
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Simulation failed: {str(e)}",
            'scenario': scenario,
            'n_years': n_years,
            'n_parcels': n_parcels
        }


def query_full_abm_multi_scenario(
    data_path: str,
    scenarios: list = ['rcp26', 'rcp45', 'rcp85'],
    n_years: int = 10,
    n_parcels: int = 15,
    output_dir: str = "results",
    enable_multi_level: bool = True,
    n_collectives: int = 2,
    n_markets: int = 1,
    n_policies: int = 1,
    enable_ensemble: bool = False,
    ensemble_size: int = 30,
    confidence_level: float = 0.95,
    rl_policy = None
) -> Dict:
    """
    Run full multi-level ABM for multiple scenarios with comparison visualizations.

    This is a WRAPPER around the existing multi-scenario analysis code.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA directory
        scenarios: List of scenarios to run
        n_years: Number of years to simulate
        n_parcels: Number of land parcels
        output_dir: Output directory for results
        enable_multi_level: Enable multi-level ABM
        n_collectives: Number of farmer collectives
        n_markets: Number of commodity markets
        n_policies: Number of policymakers
        enable_ensemble: Enable Monte Carlo ensemble mode
        ensemble_size: Number of ensemble runs
        confidence_level: Confidence level for uncertainty bands
        rl_policy: Optional RL policy

    Returns:
        Dictionary with simulation results
    """
    print(f"\n{'='*60}")
    print(f"MLU-05: Multi-Scenario Analysis with Multi-Level ABM")
    print(f"{'='*60}")
    print(f"Scenarios: {', '.join([s.upper() for s in scenarios])}")
    print(f"Duration: {n_years} years")
    print(f"Land Parcels: {n_parcels}")
    print(f"Multi-Level ABM: {'✅ ENABLED' if enable_multi_level else '❌ DISABLED'}")
    if enable_ensemble:
        print(f"Mode: 🎲 Monte Carlo Ensemble ({ensemble_size} runs, {confidence_level*100:.0f}% CI)")
    print(f"Output: {output_dir}/")
    print(f"{'='*60}\n")

    try:
        # Run the existing multi-scenario analysis (NO CHANGES TO EXISTING CODE)
        run_multi_scenario_analysis(
            scenarios=scenarios,
            n_years=n_years,
            n_parcels=n_parcels,
            n_farmers=None,
            n_pv_installations=None,
            output_dir=output_dir,
            data_path=data_path,
            enable_ensemble=enable_ensemble,
            ensemble_size=ensemble_size,
            confidence_level=confidence_level,
            n_collectives=n_collectives,
            n_markets=n_markets,
            n_policies=n_policies,
            enable_multi_level=enable_multi_level,
            rl_policy=rl_policy
        )

        return {
            'status': 'success',
            'scenarios': [s.upper() for s in scenarios],
            'n_years': n_years,
            'n_parcels': n_parcels,
            'multi_level_enabled': enable_multi_level,
            'ensemble_enabled': enable_ensemble,
            'output_dir': output_dir,
            'message': f"Multi-scenario analysis completed. Results saved to {output_dir}/"
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Multi-scenario analysis failed: {str(e)}",
            'scenarios': scenarios
        }


def main():
    """Example usage of MLU-05 query."""
    import argparse

    parser = argparse.ArgumentParser(description="MLU-05: Full Multi-Level ABM Simulation")
    parser.add_argument("--data-path", required=True, help="Path to PILOT_THESSALONIKI_DATA")
    parser.add_argument("--scenario", default=None,
                       choices=["rcp26", "rcp45", "rcp85", "historical"],
                       help="Single scenario (default: run all scenarios)")
    parser.add_argument("--years", type=int, default=None, help="Number of years")
    parser.add_argument("--parcels", type=int, default=None, help="Number of parcels")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--disable-multilevel", action="store_true",
                       help="Disable multi-level ABM")
    parser.add_argument("--collectives", type=int, default=None, help="Number of collectives")
    parser.add_argument("--markets", type=int, default=None, help="Number of markets")
    parser.add_argument("--policies", type=int, default=None, help="Number of policymakers")
    parser.add_argument("--ensemble", action="store_true", help="Enable ensemble mode")
    parser.add_argument("--ensemble-size", type=int, default=None, help="Ensemble size")

    args = parser.parse_args()

    if args.scenario is None:
        # Multi-scenario analysis
        result = query_full_abm_multi_scenario(
            data_path=args.data_path,
            scenarios=['rcp26', 'rcp45', 'rcp85'],
            n_years=args.years,
            n_parcels=args.parcels,
            output_dir=args.output,
            enable_multi_level=not args.disable_multilevel,
            n_collectives=args.collectives,
            n_markets=args.markets,
            n_policies=args.policies,
            enable_ensemble=args.ensemble,
            ensemble_size=args.ensemble_size
        )
    else:
        # Single scenario
        result = query_full_abm(
            data_path=args.data_path,
            scenario=args.scenario,
            n_years=args.years,
            n_parcels=args.parcels,
            output_dir=args.output,
            enable_multi_level=not args.disable_multilevel,
            n_collectives=args.collectives,
            n_markets=args.markets,
            n_policies=args.policies,
            enable_ensemble=args.ensemble,
            ensemble_size=args.ensemble_size
        )

    if result['status'] == 'error':
        print(f"\n❌ Error: {result['message']}")
        sys.exit(1)

    print(f"\n✅ {result['message']}")


if __name__ == "__main__":
    main()
