"""
MLU-08: Simulate Future Climate Scenarios

User Story: As a Policymaker, I want to simulate different future climate
scenarios (RCP 2.6, 4.5, 8.5) to assess land-use suitability under varying
climate conditions.

This query provides QUICK SCENARIO COMPARISON without running full ABM.
For full ABM simulation, use MLU-05 (full_abm.py).
"""

import sys
from pathlib import Path
import xarray as xr
import numpy as np
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.data.loaders.data_loader import (
    load_crop_suitability,
    load_temperature,
    load_precipitation,
    load_solar_radiation
)


def query_climate_scenario(
    data_path: str,
    scenarios: List[str] = ["rcp26", "rcp45", "rcp85"],
    crop: str = "WHEAT",
    comparison_variable: str = "suitability",  # 'suitability', 'temperature', 'precipitation', 'all'
    year: Optional[int] = None,
    run_full_simulation: bool = False,
    n_years: int = 10,
    n_parcels: int = 15,
    output_dir: str = "results"
) -> Dict:
    """
    Compare future climate scenarios.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA directory
        scenarios: List of RCP scenarios to compare (rcp26, rcp45, rcp85)
        crop: Crop type (WHEAT, MAIZE)
        comparison_variable: What to compare across scenarios
        year: Specific year (if None, averages over all years)
        run_full_simulation: If True, run full ABM for all scenarios
        n_years: Number of years (if running full simulation)
        n_parcels: Number of parcels (if running full simulation)
        output_dir: Output directory (if running full simulation)

    Returns:
        Dictionary with scenario comparison results
    """
    print(f"\n{'='*60}")
    print(f"MLU-08: Simulate Future Climate Scenarios")
    print(f"{'='*60}")
    print(f"Scenarios: {', '.join([s.upper() for s in scenarios])}")
    print(f"Crop: {crop.upper()}")
    print(f"Comparison Variable: {comparison_variable.upper()}")

    # If user wants full ABM simulation
    if run_full_simulation:
        print(f"\nRunning full ABM simulation for all scenarios...")

        from use_cases.mlu.scripts.run_mlu_simulation import run_multi_scenario_analysis

        try:
            run_multi_scenario_analysis(
                scenarios=scenarios,
                n_years=n_years,
                n_parcels=n_parcels,
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

            return {
                'status': 'success',
                'mode': 'full_simulation',
                'scenarios': [s.upper() for s in scenarios],
                'message': f"Multi-scenario simulation completed",
                'output_dir': output_dir
            }

        except Exception as e:
            return {
                'status': 'error',
                'mode': 'full_simulation',
                'message': f"Simulation failed: {str(e)}"
            }

    # Otherwise, do quick data-level comparison (no simulation)
    print(f"\nLoading data for quick scenario comparison (no simulation)...")

    results = {
        'status': 'success',
        'mode': 'quick_comparison',
        'scenarios': [s.upper() for s in scenarios],
        'crop': crop.upper(),
        'comparison_variable': comparison_variable,
        'year': year,
        'scenario_data': {}
    }

    try:
        # Load data for each scenario
        for scenario in scenarios:
            print(f"\n  Loading {scenario.upper()} data...")

            scenario_results = {}

            # Crop suitability
            if comparison_variable in ['suitability', 'all']:
                try:
                    lusa_data = load_crop_suitability(data_path, crop, scenario)

                    # Get variable name
                    suitability_var = None
                    for var_name in lusa_data.data_vars:
                        if 'suitability' in var_name.lower() or crop.upper() in var_name.upper():
                            suitability_var = var_name
                            break
                    if suitability_var is None:
                        suitability_var = list(lusa_data.data_vars)[0]

                    # Select year if specified
                    if year is not None and 'time' in lusa_data.coords:
                        time_coords = lusa_data.time.values
                        years = [int(str(t)[:4]) for t in time_coords]
                        if year in years:
                            year_idx = years.index(year)
                            lusa_data = lusa_data.isel(time=year_idx)

                    values = lusa_data[suitability_var].values
                    scenario_results['suitability'] = {
                        'mean': float(np.nanmean(values)),
                        'std': float(np.nanstd(values)),
                        'min': float(np.nanmin(values)),
                        'max': float(np.nanmax(values)),
                        'median': float(np.nanmedian(values))
                    }

                except Exception as e:
                    print(f"    Warning: Could not load suitability for {scenario}: {e}")

            # Temperature
            if comparison_variable in ['temperature', 'all']:
                try:
                    temp_data = load_temperature(data_path, scenario)
                    temp_var = 'tas' if 'tas' in temp_data.data_vars else list(temp_data.data_vars)[0]

                    # Select year if specified
                    if year is not None and 'time' in temp_data.coords:
                        time_coords = temp_data.time.values
                        years = [int(str(t)[:4]) for t in time_coords]
                        if year in years:
                            year_idx = years.index(year)
                            temp_data = temp_data.isel(time=year_idx)

                    values = temp_data[temp_var].values
                    scenario_results['temperature'] = {
                        'mean': float(np.nanmean(values)),
                        'std': float(np.nanstd(values)),
                        'min': float(np.nanmin(values)),
                        'max': float(np.nanmax(values)),
                        'median': float(np.nanmedian(values))
                    }

                except Exception as e:
                    print(f"    Warning: Could not load temperature for {scenario}: {e}")

            # Precipitation
            if comparison_variable in ['precipitation', 'all']:
                try:
                    precip_data = load_precipitation(data_path, scenario)
                    precip_var = 'pr' if 'pr' in precip_data.data_vars else list(precip_data.data_vars)[0]

                    # Select year if specified
                    if year is not None and 'time' in precip_data.coords:
                        time_coords = precip_data.time.values
                        years = [int(str(t)[:4]) for t in time_coords]
                        if year in years:
                            year_idx = years.index(year)
                            precip_data = precip_data.isel(time=year_idx)

                    values = precip_data[precip_var].values
                    scenario_results['precipitation'] = {
                        'mean': float(np.nanmean(values)),
                        'std': float(np.nanstd(values)),
                        'min': float(np.nanmin(values)),
                        'max': float(np.nanmax(values)),
                        'median': float(np.nanmedian(values))
                    }

                except Exception as e:
                    print(f"    Warning: Could not load precipitation for {scenario}: {e}")

            results['scenario_data'][scenario.upper()] = scenario_results

        # Print comparison summary
        print(f"\n{'='*60}")
        print(f"SCENARIO COMPARISON SUMMARY")
        print(f"{'='*60}")

        for var_name in ['suitability', 'temperature', 'precipitation']:
            if any(var_name in results['scenario_data'][s] for s in results['scenario_data']):
                print(f"\n{var_name.upper()}:")
                print(f"  {'Scenario':<10} {'Mean':>12} {'Std':>12} {'Min':>12} {'Max':>12}")
                print(f"  {'-'*60}")
                for scenario in scenarios:
                    scenario_key = scenario.upper()
                    if var_name in results['scenario_data'][scenario_key]:
                        stats = results['scenario_data'][scenario_key][var_name]
                        print(f"  {scenario_key:<10} "
                              f"{stats['mean']:>12.3f} "
                              f"{stats['std']:>12.3f} "
                              f"{stats['min']:>12.3f} "
                              f"{stats['max']:>12.3f}")

        print(f"\n{'='*60}\n")

        # Calculate relative differences
        if len(scenarios) > 1:
            print(f"RELATIVE CHANGES (vs {scenarios[0].upper()}):")
            baseline_scenario = scenarios[0].upper()

            for var_name in ['suitability', 'temperature', 'precipitation']:
                if var_name in results['scenario_data'][baseline_scenario]:
                    baseline_mean = results['scenario_data'][baseline_scenario][var_name]['mean']

                    print(f"\n{var_name.upper()}:")
                    for i, scenario in enumerate(scenarios[1:], 1):
                        scenario_key = scenario.upper()
                        if var_name in results['scenario_data'][scenario_key]:
                            scenario_mean = results['scenario_data'][scenario_key][var_name]['mean']
                            change = scenario_mean - baseline_mean
                            change_pct = (change / baseline_mean * 100) if baseline_mean != 0 else 0.0
                            print(f"  {scenario_key:10s}: {change:+.3f} ({change_pct:+.1f}%)")

        print(f"\n{'='*60}\n")

        # Generate visualizations
        print(f"\n📊 Generating visualizations...")
        from use_cases.mlu.queries.visualization_utils import create_scenario_comparison_chart

        output_dir = Path(f"results/mlu08_{crop.lower()}")
        output_dir.mkdir(parents=True, exist_ok=True)

        visualizations = {}

        # Create comparison charts for each variable
        for var_name in ['suitability', 'temperature', 'precipitation']:
            if any(var_name in results['scenario_data'][s] for s in results['scenario_data']):
                try:
                    chart_file = str(output_dir / f'{var_name}_comparison.html')
                    viz_path = create_scenario_comparison_chart(
                        scenario_data=results['scenario_data'],
                        variable_name=var_name,
                        title=f'{var_name.title()} Comparison Across RCP Scenarios - {crop.upper()}',
                        output_file=chart_file
                    )
                    if viz_path:
                        visualizations[f'{var_name}_chart'] = viz_path
                        print(f"   ✅ {var_name.title()} chart saved: {chart_file}")
                except Exception as e:
                    print(f"   ⚠️  {var_name.title()} chart generation failed: {e}")

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
            'message': f"Scenario comparison failed: {str(e)}"
        }


def main():
    """Example usage of MLU-08 query."""
    import argparse

    parser = argparse.ArgumentParser(description="MLU-08: Simulate Future Climate Scenarios")
    parser.add_argument("--data-path", required=True, help="Path to PILOT_THESSALONIKI_DATA")
    parser.add_argument("--scenarios", nargs="+", default=["rcp26", "rcp45", "rcp85"],
                       choices=["rcp26", "rcp45", "rcp85"],
                       help="Scenarios to compare (default: all)")
    parser.add_argument("--crop", default="WHEAT", choices=["WHEAT", "MAIZE"], help="Crop type")
    parser.add_argument("--compare", default="all",
                       choices=["suitability", "temperature", "precipitation", "all"],
                       help="What to compare")
    parser.add_argument("--year", type=int, help="Specific year (optional)")
    parser.add_argument("--full-simulation", action="store_true",
                       help="Run full ABM simulation for all scenarios")
    parser.add_argument("--years", type=int, default=10, help="Number of years (if running full simulation)")
    parser.add_argument("--parcels", type=int, default=15, help="Number of parcels (if running full simulation)")
    parser.add_argument("--output", default="results", help="Output directory")

    args = parser.parse_args()

    result = query_climate_scenario(
        data_path=args.data_path,
        scenarios=args.scenarios,
        crop=args.crop,
        comparison_variable=args.compare,
        year=args.year,
        run_full_simulation=args.full_simulation,
        n_years=args.years,
        n_parcels=args.parcels,
        output_dir=args.output
    )

    if result['status'] == 'error':
        print(f"\n❌ Error: {result['message']}")
        sys.exit(1)

    print(f"\n✅ Scenario comparison completed successfully!")

    if result['mode'] == 'full_simulation':
        print(f"📊 View results: {result['output_dir']}/")


if __name__ == "__main__":
    main()
