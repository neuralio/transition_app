"""
MLU-07: Integrate Historical EO Data for Benchmarking

User Story: As a Policymaker, I want to integrate historical Earth Observation
data to benchmark model predictions against past observations.

This query provides QUICK COMPARISON between historical data and future projections
without running full ABM simulation (unless requested).
"""

import sys
from pathlib import Path
import xarray as xr
import numpy as np
from typing import Dict, Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.data.loaders.data_loader import (
    load_crop_suitability,
    load_temperature,
    load_precipitation,
    load_solar_radiation
)


def compare_historical_vs_future(
    historical_data: xr.Dataset,
    future_data: xr.Dataset,
    variable_name: str,
    metric: str = "mean"
) -> Dict:
    """
    Compare historical vs future data for a specific variable.

    Args:
        historical_data: Historical dataset
        future_data: Future projection dataset
        variable_name: Variable to compare
        metric: 'mean', 'min', 'max', 'std'

    Returns:
        Dictionary with comparison statistics
    """
    hist_values = historical_data[variable_name].values
    future_values = future_data[variable_name].values

    if metric == "mean":
        hist_stat = float(np.nanmean(hist_values))
        future_stat = float(np.nanmean(future_values))
    elif metric == "min":
        hist_stat = float(np.nanmin(hist_values))
        future_stat = float(np.nanmin(future_values))
    elif metric == "max":
        hist_stat = float(np.nanmax(hist_values))
        future_stat = float(np.nanmax(future_values))
    elif metric == "std":
        hist_stat = float(np.nanstd(hist_values))
        future_stat = float(np.nanstd(future_values))
    else:
        raise ValueError(f"Unknown metric: {metric}")

    change = future_stat - hist_stat
    change_pct = (change / hist_stat * 100) if hist_stat != 0 else 0.0

    return {
        'historical': hist_stat,
        'future': future_stat,
        'change': change,
        'change_percent': change_pct
    }


def query_historical_benchmark(
    data_path: str,
    crop: str = "WHEAT",
    future_scenario: str = "rcp45",
    comparison_type: str = "suitability",  # 'suitability', 'temperature', 'precipitation', 'all'
    historical_period: tuple = None,  # (start_year, end_year)
    future_period: tuple = None,  # (start_year, end_year)
    run_full_simulation: bool = False,  # If True, runs full ABM with historical comparison
    output_dir: str = "results"
) -> Dict:
    """
    Benchmark future projections against historical observations.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA directory
        crop: Crop type (WHEAT, MAIZE)
        future_scenario: Future scenario to compare (rcp26, rcp45, rcp85)
        comparison_type: What to compare ('suitability', 'temperature', 'precipitation', 'all')
        historical_period: Historical period (default: all available)
        future_period: Future period (default: all available)
        run_full_simulation: If True, run full ABM simulation with historical comparison
        output_dir: Output directory (if running full simulation)

    Returns:
        Dictionary with benchmarking results
    """
    print(f"\n{'='*60}")
    print(f"MLU-07: Historical Benchmarking")
    print(f"{'='*60}")
    print(f"Crop: {crop.upper()}")
    print(f"Future Scenario: {future_scenario.upper()}")
    print(f"Comparison Type: {comparison_type.upper()}")

    # If user wants full ABM simulation with historical comparison
    if run_full_simulation:
        print(f"\nRunning full ABM simulation with historical comparison...")
        print(f"This will run: historical + {future_scenario}")

        from use_cases.mlu.scripts.run_mlu_simulation import run_multi_scenario_analysis
        from use_cases.mlu.scripts.historical_comparison import create_historical_comparison

        # Run historical + future scenario
        scenarios = ["historical", future_scenario]

        try:
            run_multi_scenario_analysis(
                scenarios=scenarios,
                n_years=10,
                n_parcels=15,
                n_farmers=None,
                n_pv_installations=None,
                output_dir=output_dir,
                data_path=data_path,
                enable_ensemble=False,
                ensemble_size=1,
                confidence_level=0.95,
                n_collectives=2,
                n_markets=1,
                n_policies=1,
                enable_multi_level=True,
                rl_policy=None
            )

            # Generate comparison visualization
            create_historical_comparison(results_dir=output_dir)

            return {
                'status': 'success',
                'mode': 'full_simulation',
                'message': f"Historical benchmarking simulation completed",
                'output_dir': output_dir,
                'comparison_file': f"{output_dir}/historical_comparison.html",
                'report_file': f"{output_dir}/historical_benchmark_report.txt"
            }

        except Exception as e:
            return {
                'status': 'error',
                'mode': 'full_simulation',
                'message': f"Simulation failed: {str(e)}"
            }

    # Otherwise, do quick data-level comparison (no simulation)
    print(f"\nLoading data for quick comparison (no simulation)...")

    results = {
        'status': 'success',
        'mode': 'quick_comparison',
        'crop': crop.upper(),
        'future_scenario': future_scenario.upper(),
        'comparisons': {}
    }

    try:
        # Compare crop suitability
        if comparison_type in ['suitability', 'all']:
            print(f"\n  Loading crop suitability data...")
            try:
                hist_lusa = load_crop_suitability(data_path, crop, "historical")
                future_lusa = load_crop_suitability(data_path, crop, future_scenario)

                # Get variable name
                suitability_var = None
                for var_name in hist_lusa.data_vars:
                    if 'suitability' in var_name.lower() or crop.upper() in var_name.upper():
                        suitability_var = var_name
                        break
                if suitability_var is None:
                    suitability_var = list(hist_lusa.data_vars)[0]

                comparison = compare_historical_vs_future(
                    hist_lusa, future_lusa, suitability_var, metric="mean"
                )
                results['comparisons']['suitability'] = comparison

                print(f"    Historical Mean Suitability: {comparison['historical']:.3f}")
                print(f"    Future Mean Suitability:     {comparison['future']:.3f}")
                print(f"    Change: {comparison['change']:+.3f} ({comparison['change_percent']:+.1f}%)")

            except Exception as e:
                print(f"    Warning: Could not compare suitability: {e}")

        # Compare temperature
        if comparison_type in ['temperature', 'all']:
            print(f"\n  Loading temperature data...")
            try:
                hist_temp = load_temperature(data_path, "historical")
                future_temp = load_temperature(data_path, future_scenario)

                temp_var = 'tas' if 'tas' in hist_temp.data_vars else list(hist_temp.data_vars)[0]

                comparison = compare_historical_vs_future(
                    hist_temp, future_temp, temp_var, metric="mean"
                )
                results['comparisons']['temperature'] = comparison

                print(f"    Historical Mean Temperature: {comparison['historical']:.2f} K")
                print(f"    Future Mean Temperature:     {comparison['future']:.2f} K")
                print(f"    Change: {comparison['change']:+.2f} K ({comparison['change_percent']:+.1f}%)")

            except Exception as e:
                print(f"    Warning: Could not compare temperature: {e}")

        # Compare precipitation
        if comparison_type in ['precipitation', 'all']:
            print(f"\n  Loading precipitation data...")
            try:
                hist_precip = load_precipitation(data_path, "historical")
                future_precip = load_precipitation(data_path, future_scenario)

                precip_var = 'pr' if 'pr' in hist_precip.data_vars else list(hist_precip.data_vars)[0]

                comparison = compare_historical_vs_future(
                    hist_precip, future_precip, precip_var, metric="mean"
                )
                results['comparisons']['precipitation'] = comparison

                print(f"    Historical Mean Precipitation: {comparison['historical']:.6f}")
                print(f"    Future Mean Precipitation:     {comparison['future']:.6f}")
                print(f"    Change: {comparison['change']:+.6f} ({comparison['change_percent']:+.1f}%)")

            except Exception as e:
                print(f"    Warning: Could not compare precipitation: {e}")

        print(f"\n{'='*60}")
        print(f"BENCHMARKING SUMMARY")
        print(f"{'='*60}")
        print(f"Compared: {len(results['comparisons'])} variables")
        for var_name, comparison in results['comparisons'].items():
            print(f"  {var_name:20s}: {comparison['change_percent']:+6.1f}% change")
        print(f"{'='*60}\n")

        # Generate visualizations
        print(f"\n📊 Generating visualizations...")
        from use_cases.mlu.queries.visualization_utils import create_historical_comparison_chart

        output_dir = Path(f"results/mlu07_{crop.lower()}_{future_scenario.lower()}")
        output_dir.mkdir(parents=True, exist_ok=True)

        visualizations = {}

        try:
            # Historical vs Future comparison chart
            chart_file = str(output_dir / 'historical_vs_future.html')
            viz_path = create_historical_comparison_chart(
                historical_stats=results['comparisons'],
                future_stats=results['comparisons'],
                scenario=future_scenario,
                title=f'Historical vs Future Comparison - {crop.upper()} {future_scenario.upper()}',
                output_file=chart_file
            )
            if viz_path:
                visualizations['comparison_chart'] = viz_path
                print(f"   ✅ Comparison chart saved: {chart_file}")
        except Exception as e:
            print(f"   ⚠️  Comparison chart generation failed: {e}")

        # Print visualization paths
        if visualizations:
            print(f"\n{'='*60}")
            print(f"VISUALIZATIONS GENERATED")
            print(f"{'='*60}")
            for viz_type, viz_path in visualizations.items():
                print(f"  {viz_type}: {viz_path}")
            print(f"{'='*60}\n")

        results['visualizations'] = visualizations

        return results

    except Exception as e:
        return {
            'status': 'error',
            'mode': 'quick_comparison',
            'message': f"Data comparison failed: {str(e)}"
        }


def main():
    """Example usage of MLU-07 query."""
    import argparse

    parser = argparse.ArgumentParser(description="MLU-07: Historical Benchmarking")
    parser.add_argument("--data-path", required=True, help="Path to PILOT_THESSALONIKI_DATA")
    parser.add_argument("--crop", default="WHEAT", choices=["WHEAT", "MAIZE"], help="Crop type")
    parser.add_argument("--scenario", default="rcp45",
                       choices=["rcp26", "rcp45", "rcp85"],
                       help="Future scenario")
    parser.add_argument("--compare", default="all",
                       choices=["suitability", "temperature", "precipitation", "all"],
                       help="What to compare")
    parser.add_argument("--full-simulation", action="store_true",
                       help="Run full ABM simulation with historical comparison")
    parser.add_argument("--output", default="results", help="Output directory")

    args = parser.parse_args()

    result = query_historical_benchmark(
        data_path=args.data_path,
        crop=args.crop,
        future_scenario=args.scenario,
        comparison_type=args.compare,
        run_full_simulation=args.full_simulation,
        output_dir=args.output
    )

    if result['status'] == 'error':
        print(f"\n❌ Error: {result['message']}")
        sys.exit(1)

    print(f"\n✅ Benchmarking completed successfully!")

    if result['mode'] == 'full_simulation':
        print(f"📊 View comparison: {result['comparison_file']}")
        print(f"📄 View report: {result['report_file']}")


if __name__ == "__main__":
    main()
