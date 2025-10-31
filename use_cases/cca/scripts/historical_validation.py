"""
Historical Validation for CCA Simulation

Validates the CCA simulation model against historical observations (2000-2020).
Target: RMSE < 15% for key agricultural metrics.

This module compares simulated results with actual historical data to assess
model accuracy and reliability before using it for future climate projections.
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import json


class HistoricalValidator:
    """
    Validates CCA simulation results against historical observations.

    Calculates RMSE (Root Mean Square Error) and other accuracy metrics
    to ensure model reliability before future projections.
    """

    def __init__(self, historical_data_path: str = None):
        """
        Initialize historical validator.

        Args:
            historical_data_path: Path to historical reference data
                                 If None, uses placeholder data for testing
        """
        self.historical_data_path = historical_data_path
        self.historical_data = None

        if historical_data_path and Path(historical_data_path).exists():
            self.load_historical_data()
        else:
            # Use placeholder data for testing
            # TODO: Replace with real historical data from:
            #   - Eurostat agricultural statistics (2000-2020)
            #   - FAOSTAT crop production data
            #   - National agricultural surveys
            self.historical_data = self._generate_placeholder_data()

    def load_historical_data(self):
        """
        Load historical reference data from file.

        Expected format: JSON with yearly observations
        {
            "2010": {"wheat_yield": 5.2, "maize_yield": 8.1, ...},
            "2011": {...},
            ...
        }
        """
        with open(self.historical_data_path, 'r') as f:
            self.historical_data = json.load(f)

    def _generate_placeholder_data(self) -> Dict:
        """
        Generate placeholder historical data for testing.

        TODO: Replace with real data from Eurostat/FAOSTAT

        Returns:
            Dict mapping years to agricultural metrics
        """
        # Placeholder based on typical Thessaloniki region yields
        # Real data should come from agricultural surveys
        placeholder = {}

        for year in range(2010, 2021):  # 2010-2020
            # Typical wheat yields in Thessaloniki: 3-6 t/ha
            # Typical maize yields: 7-12 t/ha
            # Add some year-to-year variation
            np.random.seed(year)

            placeholder[str(year)] = {
                'wheat_yield_t_per_ha': 4.0 + np.random.uniform(-0.5, 0.5),
                'maize_yield_t_per_ha': 9.0 + np.random.uniform(-1.0, 1.0),
                'wheat_fraction': 0.6 + np.random.uniform(-0.1, 0.1),  # % farmers growing wheat
                'maize_fraction': 0.4 + np.random.uniform(-0.1, 0.1),  # % farmers growing maize
                'avg_income_per_farmer': 5000 + np.random.uniform(-1000, 1000),  # €/farmer/year
            }

        return placeholder

    def calculate_rmse(self,
                      observed: List[float],
                      simulated: List[float]) -> float:
        """
        Calculate Root Mean Square Error.

        Args:
            observed: List of observed values
            simulated: List of simulated values

        Returns:
            RMSE value
        """
        observed = np.array(observed)
        simulated = np.array(simulated)

        mse = np.mean((observed - simulated) ** 2)
        rmse = np.sqrt(mse)

        return rmse

    def calculate_rmse_percentage(self,
                                   observed: List[float],
                                   simulated: List[float]) -> float:
        """
        Calculate RMSE as percentage of mean observed value.

        Args:
            observed: List of observed values
            simulated: List of simulated values

        Returns:
            RMSE percentage
        """
        observed = np.array(observed)
        simulated = np.array(simulated)

        rmse = self.calculate_rmse(observed, simulated)
        mean_observed = np.mean(observed)

        if mean_observed == 0:
            return float('inf')

        rmse_percentage = (rmse / abs(mean_observed)) * 100

        return rmse_percentage

    def calculate_mae(self,
                     observed: List[float],
                     simulated: List[float]) -> float:
        """
        Calculate Mean Absolute Error.

        Args:
            observed: List of observed values
            simulated: List of simulated values

        Returns:
            MAE value
        """
        observed = np.array(observed)
        simulated = np.array(simulated)

        mae = np.mean(np.abs(observed - simulated))

        return mae

    def calculate_r_squared(self,
                           observed: List[float],
                           simulated: List[float]) -> float:
        """
        Calculate R² (coefficient of determination).

        Args:
            observed: List of observed values
            simulated: List of simulated values

        Returns:
            R² value (0-1, where 1 is perfect fit)
        """
        observed = np.array(observed)
        simulated = np.array(simulated)

        ss_res = np.sum((observed - simulated) ** 2)
        ss_tot = np.sum((observed - np.mean(observed)) ** 2)

        if ss_tot == 0:
            return 0.0

        r_squared = 1 - (ss_res / ss_tot)

        return r_squared

    def validate_simulation_results(self,
                                   simulation_results: Dict,
                                   validation_years: List[int] = None) -> Dict:
        """
        Validate simulation results against historical observations.

        Args:
            simulation_results: Dict with simulation outputs
                              {year: {'wheat_yield': ..., 'maize_yield': ..., ...}}
            validation_years: Years to validate (default: all available)

        Returns:
            Dict with validation metrics and pass/fail status
        """
        if validation_years is None:
            validation_years = sorted([int(y) for y in self.historical_data.keys()])

        # Extract metrics for comparison
        metrics_to_validate = [
            'wheat_yield_t_per_ha',
            'maize_yield_t_per_ha',
            'wheat_fraction',
            'maize_fraction',
            'avg_income_per_farmer'
        ]

        validation_results = {}

        for metric in metrics_to_validate:
            observed = []
            simulated = []

            for year in validation_years:
                year_str = str(year)

                # Skip if data not available
                if year_str not in self.historical_data:
                    continue
                if year not in simulation_results:
                    continue

                # Get observed value
                if metric in self.historical_data[year_str]:
                    observed.append(self.historical_data[year_str][metric])

                    # Get simulated value
                    if metric in simulation_results[year]:
                        simulated.append(simulation_results[year][metric])

            # Calculate validation metrics
            if len(observed) > 0 and len(simulated) > 0 and len(observed) == len(simulated):
                rmse = self.calculate_rmse(observed, simulated)
                rmse_pct = self.calculate_rmse_percentage(observed, simulated)
                mae = self.calculate_mae(observed, simulated)
                r2 = self.calculate_r_squared(observed, simulated)

                # Check if passes target (RMSE < 15%)
                passes_target = rmse_pct < 15.0

                validation_results[metric] = {
                    'rmse': rmse,
                    'rmse_percentage': rmse_pct,
                    'mae': mae,
                    'r_squared': r2,
                    'passes_target': passes_target,
                    'n_samples': len(observed),
                    'observed_mean': np.mean(observed),
                    'simulated_mean': np.mean(simulated)
                }

        # Overall validation status
        all_metrics = [v for v in validation_results.values()]
        overall_pass = all(m['passes_target'] for m in all_metrics) if all_metrics else False
        avg_rmse_pct = np.mean([m['rmse_percentage'] for m in all_metrics]) if all_metrics else float('inf')

        validation_results['_summary'] = {
            'overall_pass': overall_pass,
            'avg_rmse_percentage': avg_rmse_pct,
            'n_metrics_validated': len(all_metrics),
            'n_metrics_passed': sum(1 for m in all_metrics if m['passes_target']),
            'validation_years': validation_years
        }

        return validation_results

    def generate_validation_report(self,
                                   validation_results: Dict,
                                   output_file: str = None) -> str:
        """
        Generate human-readable validation report.

        Args:
            validation_results: Output from validate_simulation_results()
            output_file: Path to save report (optional)

        Returns:
            Report text
        """
        report_lines = []

        report_lines.append("=" * 80)
        report_lines.append("HISTORICAL VALIDATION REPORT")
        report_lines.append("CCA Simulation - Climate Change Adaptation")
        report_lines.append("=" * 80)
        report_lines.append("")

        # Summary
        summary = validation_results.get('_summary', {})
        report_lines.append("VALIDATION SUMMARY:")
        report_lines.append(f"  Validation Period: {min(summary.get('validation_years', []))}-"
                          f"{max(summary.get('validation_years', []))}")
        report_lines.append(f"  Metrics Validated: {summary.get('n_metrics_validated', 0)}")
        report_lines.append(f"  Metrics Passed (RMSE < 15%): {summary.get('n_metrics_passed', 0)}")
        report_lines.append(f"  Average RMSE: {summary.get('avg_rmse_percentage', 0):.2f}%")
        report_lines.append(f"  Overall Status: {'✅ PASSED' if summary.get('overall_pass') else '❌ FAILED'}")
        report_lines.append("")

        # Detailed metrics
        report_lines.append("=" * 80)
        report_lines.append("DETAILED VALIDATION METRICS")
        report_lines.append("=" * 80)
        report_lines.append("")

        for metric_name, metric_data in validation_results.items():
            if metric_name == '_summary':
                continue

            status = "✅ PASS" if metric_data['passes_target'] else "❌ FAIL"

            report_lines.append(f"{metric_name}:")
            report_lines.append(f"  Status: {status}")
            report_lines.append(f"  RMSE: {metric_data['rmse']:.4f}")
            report_lines.append(f"  RMSE %: {metric_data['rmse_percentage']:.2f}% "
                              f"(target: < 15%)")
            report_lines.append(f"  MAE: {metric_data['mae']:.4f}")
            report_lines.append(f"  R²: {metric_data['r_squared']:.4f}")
            report_lines.append(f"  Observed Mean: {metric_data['observed_mean']:.4f}")
            report_lines.append(f"  Simulated Mean: {metric_data['simulated_mean']:.4f}")
            report_lines.append(f"  Samples: {metric_data['n_samples']}")
            report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("NOTES:")
        report_lines.append("- Target: RMSE < 15% for all metrics")
        report_lines.append("- Historical period: 2010-2020 (placeholder data)")
        report_lines.append("- TODO: Replace with real data from Eurostat/FAOSTAT")
        report_lines.append("=" * 80)

        report_text = "\n".join(report_lines)

        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)

        return report_text


def run_historical_validation(model_results: Dict,
                              output_dir: str = "results/validation") -> Dict:
    """
    Convenience function to run historical validation.

    Args:
        model_results: Simulation results to validate
        output_dir: Directory to save validation report

    Returns:
        Validation results dict
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Initialize validator
    validator = HistoricalValidator()

    # Run validation
    validation_results = validator.validate_simulation_results(model_results)

    # Generate report
    report_file = Path(output_dir) / "historical_validation_report.txt"
    validator.generate_validation_report(validation_results, str(report_file))

    print(f"\n✅ Historical validation complete!")
    print(f"   Report saved to: {report_file}")
    print(f"   Overall Status: {'PASSED' if validation_results['_summary']['overall_pass'] else 'FAILED'}")
    print(f"   Average RMSE: {validation_results['_summary']['avg_rmse_percentage']:.2f}%")

    return validation_results
