"""
Monte Carlo Ensemble Runner for Probabilistic Uncertainty Analysis.

Runs multiple stochastic realizations of the same scenario to:
1. Calculate mean/median outcomes
2. Compute confidence intervals
3. Quantify probability distributions
4. Provide probabilistic statements ("X% chance of Y")
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from pathlib import Path
import json


class EnsembleRunner:
    """Run Monte Carlo ensemble simulations and compute statistics."""

    def __init__(self, ensemble_size: int = 30, confidence_level: float = 0.95):
        """
        Initialize ensemble runner.

        Args:
            ensemble_size: Number of stochastic realizations per scenario
            confidence_level: Confidence level for intervals (e.g., 0.95 = 95%)
        """
        self.ensemble_size = ensemble_size
        self.confidence_level = confidence_level
        self.alpha = 1.0 - confidence_level  # Significance level

    def run_ensemble(self, simulation_func, scenario: str, n_years: int,
                    n_parcels: int, output_dir: str, data_path: str, **kwargs) -> Dict:
        """
        Run ensemble simulations for a scenario.

        Args:
            simulation_func: Function to run single simulation (returns ResultCollector)
            scenario: RCP scenario
            n_years: Number of years
            n_parcels: Number of parcels
            output_dir: Output directory
            data_path: Data path
            **kwargs: Additional arguments to pass to simulation_func (e.g., n_collectives, n_markets, n_policies, enable_multi_level)

        Returns:
            Dictionary with ensemble statistics
        """
        print(f"\n🔬 MONTE CARLO ENSEMBLE: {scenario.upper()}")
        print(f"   Running {self.ensemble_size} stochastic realizations...")
        print(f"   Confidence level: {self.confidence_level*100:.0f}%")

        ensemble_results = []

        # Run multiple realizations with different random seeds
        for run_id in range(self.ensemble_size):
            print(f"      Run {run_id+1}/{self.ensemble_size}...", end=" ")

            # Set unique random seed for this realization
            np.random.seed(run_id * 1000 + hash(scenario) % 1000)

            # Run simulation
            collector = simulation_func(
                scenario=scenario,
                n_years=n_years,
                n_parcels=n_parcels,
                output_dir=f"{output_dir}/ensemble_{run_id}",
                data_path=data_path,
                **kwargs  # Pass through multi-level ABM settings and other parameters
            )

            # Extract key metrics
            run_data = self._extract_metrics(collector, run_id)
            ensemble_results.append(run_data)

            print("✓")

        # Compute ensemble statistics
        print(f"\n   📊 Computing ensemble statistics...")
        ensemble_stats = self._compute_statistics(ensemble_results, scenario)

        # Save ensemble results
        self._save_ensemble(ensemble_stats, scenario, output_dir)

        return ensemble_stats

    def _extract_metrics(self, collector, run_id: int) -> Dict:
        """Extract key metrics from a simulation run."""
        df = collector.get_farmer_dataframe()

        if df.empty:
            return {'run_id': run_id, 'data': {}}

        metrics = {}

        # Time-series metrics
        for year in df['year'].unique():
            year_data = df[df['year'] == year]

            # Count crops
            wheat_count = int((year_data['crop'] == 'WHEAT').sum())
            maize_count = int((year_data['crop'] == 'MAIZE').sum())

            # Count solar PV parcels (check both 'land_use' and 'crop' columns)
            if 'land_use' in year_data.columns:
                solar_count = int((year_data['land_use'] == 'solar_pv').sum())
            else:
                solar_count = int((year_data['crop'] == 'solar_pv').sum())

            # Calculate income
            total_income = float(year_data['annual_income'].sum())

            # Calculate average yield (only for farming parcels)
            crop_data = year_data[year_data['crop'].notna() & (year_data['crop'] != 'solar_pv')]
            avg_yield = float(crop_data['actual_yield'].mean()) if len(crop_data) > 0 else 0.0

            # Calculate solar energy
            solar_energy = float(year_data['annual_energy_kwh'].sum()) if 'annual_energy_kwh' in year_data.columns else 0.0

            metrics[int(year)] = {
                'wheat_count': wheat_count,
                'maize_count': maize_count,
                'solar_count': solar_count,
                'total_income': total_income,
                'avg_yield': avg_yield,
                'solar_energy': solar_energy,
            }

        return {'run_id': run_id, 'data': metrics}

    def _compute_statistics(self, ensemble_results: List[Dict], scenario: str) -> Dict:
        """Compute statistics across ensemble runs."""

        # Organize data by year
        years = set()
        for result in ensemble_results:
            years.update(result['data'].keys())

        years = sorted(years)

        stats_by_year = {}

        for year in years:
            # Extract all values for this year across runs
            wheat_counts = []
            maize_counts = []
            solar_counts = []
            total_incomes = []
            avg_yields = []
            solar_energies = []

            for result in ensemble_results:
                if year in result['data']:
                    year_data = result['data'][year]
                    wheat_counts.append(year_data.get('wheat_count', 0))
                    maize_counts.append(year_data.get('maize_count', 0))
                    solar_counts.append(year_data.get('solar_count', 0))
                    total_incomes.append(year_data.get('total_income', 0))
                    avg_yields.append(year_data.get('avg_yield', 0))
                    solar_energies.append(year_data.get('solar_energy', 0))

            # Compute statistics
            stats_by_year[year] = {
                'wheat': self._compute_metric_stats(wheat_counts),
                'maize': self._compute_metric_stats(maize_counts),
                'solar': self._compute_metric_stats(solar_counts),
                'income': self._compute_metric_stats(total_incomes),
                'yield': self._compute_metric_stats(avg_yields),
                'energy': self._compute_metric_stats(solar_energies),
            }

        # Generate probabilistic statements for the last year
        last_year = max(years) if years else None
        probabilistic_statements = {}

        if last_year and last_year in stats_by_year:
            last_stats = stats_by_year[last_year]

            # Solar PV adoption
            solar_stats = last_stats['solar']
            probabilistic_statements['solar_pv_adoption'] = (
                f"{self.confidence_level*100:.0f}% confidence: "
                f"{solar_stats['ci_lower']:.0f}-{solar_stats['ci_upper']:.0f} parcels adopt solar PV "
                f"(mean: {solar_stats['mean']:.1f})"
            )

            # Total income
            income_stats = last_stats['income']
            probabilistic_statements['total_income'] = (
                f"{self.confidence_level*100:.0f}% confidence: "
                f"€{income_stats['ci_lower']:,.0f}-€{income_stats['ci_upper']:,.0f} "
                f"(mean: €{income_stats['mean']:,.0f})"
            )

            # Wheat adoption
            wheat_stats = last_stats['wheat']
            probabilistic_statements['wheat_adoption'] = (
                f"{self.confidence_level*100:.0f}% confidence: "
                f"{wheat_stats['ci_lower']:.0f}-{wheat_stats['ci_upper']:.0f} parcels choose wheat "
                f"(mean: {wheat_stats['mean']:.1f})"
            )

            # Maize adoption
            maize_stats = last_stats['maize']
            probabilistic_statements['maize_adoption'] = (
                f"{self.confidence_level*100:.0f}% confidence: "
                f"{maize_stats['ci_lower']:.0f}-{maize_stats['ci_upper']:.0f} parcels choose maize "
                f"(mean: {maize_stats['mean']:.1f})"
            )

            # NEW: Probability-based statements (% likelihood)
            solar_values = [result['data'][last_year]['solar_count'] for result in ensemble_results if last_year in result['data']]
            wheat_values = [result['data'][last_year]['wheat_count'] for result in ensemble_results if last_year in result['data']]

            # Calculate probabilities for different thresholds
            prob_high_solar = (sum(1 for v in solar_values if v >= 8) / len(solar_values)) * 100 if solar_values else 0
            prob_wheat_dominant = (sum(1 for v in wheat_values if v >= 8) / len(wheat_values)) * 100 if wheat_values else 0

            # Add probability statements
            probabilistic_statements['solar_probability'] = (
                f"{prob_high_solar:.0f}% probability of high solar adoption (≥8 parcels) by {last_year}"
            )
            probabilistic_statements['wheat_probability'] = (
                f"{prob_wheat_dominant:.0f}% probability of wheat dominance (≥8 parcels) by {last_year}"
            )

        return {
            'scenario': scenario,
            'ensemble_size': self.ensemble_size,
            'confidence_level': self.confidence_level,
            'stats_by_year': stats_by_year,
            'probabilistic_statements': probabilistic_statements,
        }

    def _compute_metric_stats(self, values: List[float]) -> Dict:
        """Compute statistics for a metric."""
        if not values:
            return {'mean': 0, 'median': 0, 'std': 0, 'ci_lower': 0, 'ci_upper': 0}

        values = np.array(values)
        mean = float(np.mean(values))
        median = float(np.median(values))
        std = float(np.std(values))

        # Confidence interval (percentile method)
        ci_lower_pct = (self.alpha / 2) * 100
        ci_upper_pct = (1 - self.alpha / 2) * 100
        ci_lower = float(np.percentile(values, ci_lower_pct))
        ci_upper = float(np.percentile(values, ci_upper_pct))

        return {
            'mean': mean,
            'median': median,
            'std': std,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'min': float(np.min(values)),
            'max': float(np.max(values)),
        }

    def _save_ensemble(self, ensemble_stats: Dict, scenario: str, output_dir: str):
        """Save ensemble statistics to file."""
        output_path = Path(output_dir) / f"{scenario}_ensemble_stats.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(ensemble_stats, f, indent=2)

        print(f"   ✅ Ensemble statistics saved: {output_path}")

    def generate_probabilistic_statements(self, ensemble_stats: Dict) -> List[str]:
        """
        Generate human-readable probabilistic statements.

        Examples:
        - "95% confidence: 8-12 parcels will adopt solar PV by 2030"
        - "Mean income: €450k ± €50k (95% CI)"
        """
        statements = []
        scenario = ensemble_stats['scenario'].upper()
        conf_pct = self.confidence_level * 100

        # Get final year stats
        final_year = max(ensemble_stats['stats_by_year'].keys())
        final_stats = ensemble_stats['stats_by_year'][final_year]

        # Solar PV adoption
        solar = final_stats['solar']
        statements.append(
            f"Under {scenario}, by {final_year}: "
            f"{solar['mean']:.1f} parcels adopt solar PV "
            f"({conf_pct:.0f}% CI: {solar['ci_lower']:.1f}-{solar['ci_upper']:.1f})"
        )

        # Income
        income = final_stats['income']
        statements.append(
            f"Total income: €{income['mean']:.0f}/year "
            f"(±€{income['std']:.0f}, {conf_pct:.0f}% CI: €{income['ci_lower']:.0f}-€{income['ci_upper']:.0f})"
        )

        # Wheat vs Maize
        wheat = final_stats['wheat']
        maize = final_stats['maize']
        statements.append(
            f"Wheat: {wheat['mean']:.1f} parcels ({conf_pct:.0f}% CI: {wheat['ci_lower']:.1f}-{wheat['ci_upper']:.1f}), "
            f"Maize: {maize['mean']:.1f} parcels ({conf_pct:.0f}% CI: {maize['ci_lower']:.1f}-{maize['ci_upper']:.1f})"
        )

        return statements
