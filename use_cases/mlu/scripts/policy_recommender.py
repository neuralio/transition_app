"""
Policy Recommendation Engine

Generates optimal land-use policy recommendations based on ML-ABM ensemble results.
Analyzes how different policies perform under different climate scenarios.
"""

from typing import Dict, List
import numpy as np
import sys
from pathlib import Path

# Import scenario utilities for display names
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from scenario_utils import get_scenario_display_name


class PolicyRecommender:
    """Generate policy recommendations from ensemble simulation results."""

    def __init__(self, ensemble_results: Dict[str, Dict]):
        """
        Initialize policy recommender.

        Args:
            ensemble_results: Dict with keys 'rcp26', 'rcp45', 'rcp85'
                             Each value is ensemble_stats dict
        """
        self.results = ensemble_results
        self.scenarios = sorted(ensemble_results.keys())

    def generate_recommendations(self) -> Dict:
        """
        Generate comprehensive policy recommendations.

        Returns:
            Dict with recommendations by scenario and overall strategy
        """
        recommendations = {
            'by_scenario': {},
            'overall_strategy': {},
            'key_insights': [],
        }

        # Analyze each scenario
        for scenario in self.scenarios:
            recommendations['by_scenario'][scenario] = self._analyze_scenario(scenario)

        # Cross-scenario analysis
        recommendations['overall_strategy'] = self._generate_overall_strategy()
        recommendations['key_insights'] = self._extract_key_insights()

        return recommendations

    def _analyze_scenario(self, scenario: str) -> Dict:
        """Analyze a single scenario and generate recommendations."""
        stats = self.results[scenario]
        stats_by_year = stats['stats_by_year']

        if not stats_by_year:
            return {}

        last_year = max(stats_by_year.keys())
        last_stats = stats_by_year[last_year]

        # Extract metrics
        solar_mean = last_stats['solar']['mean']
        solar_ci_lower = last_stats['solar']['ci_lower']
        solar_ci_upper = last_stats['solar']['ci_upper']

        wheat_mean = last_stats['wheat']['mean']
        maize_mean = last_stats['maize']['mean']

        income_mean = last_stats['income']['mean']
        income_ci_lower = last_stats['income']['ci_lower']
        income_ci_upper = last_stats['income']['ci_upper']

        # Generate scenario-specific recommendations
        recommendations = {
            'solar_adoption': self._recommend_solar_policy(scenario, solar_mean, solar_ci_lower, solar_ci_upper),
            'crop_diversification': self._recommend_crop_policy(scenario, wheat_mean, maize_mean),
            'income_support': self._recommend_income_policy(scenario, income_mean, income_ci_lower, income_ci_upper),
            'priority': self._determine_priority(scenario, last_stats),
        }

        return recommendations

    def _recommend_solar_policy(self, scenario: str, mean: float, ci_lower: float, ci_upper: float) -> Dict:
        """Recommend solar PV policy based on adoption rates."""
        adoption_pct = (mean / 15) * 100  # Assuming 15 total parcels (adjust based on config)
        uncertainty = ci_upper - ci_lower

        if adoption_pct < 20:
            policy = "Increase solar subsidies"
            action = f"Current adoption: {mean:.1f} parcels ({adoption_pct:.0f}%). Increase subsidies by 30-50% to reach 30% adoption target."
            priority = "HIGH"
        elif adoption_pct < 40:
            policy = "Maintain current solar subsidies"
            action = f"Adoption is moderate ({adoption_pct:.0f}%). Monitor and maintain current incentive levels."
            priority = "MEDIUM"
        else:
            policy = "Reduce solar subsidies"
            action = f"High adoption ({adoption_pct:.0f}%) achieved. Consider reducing subsidies to save budget."
            priority = "LOW"

        return {
            'policy': policy,
            'action': action,
            'priority': priority,
            'confidence': f"95% CI: {ci_lower:.0f}-{ci_upper:.0f} parcels (uncertainty: ±{uncertainty/2:.1f})"
        }

    def _recommend_crop_policy(self, scenario: str, wheat_mean: float, maize_mean: float) -> Dict:
        """Recommend crop diversification policy."""
        total_farming = wheat_mean + maize_mean
        if total_farming == 0:
            diversity = 0
        else:
            diversity = (min(wheat_mean, maize_mean) / total_farming) * 100

        if diversity < 20:
            policy = "Incentivize crop diversification"
            action = f"Low diversity ({diversity:.0f}%). Provide subsidies for alternative crops to reduce monoculture risk."
            priority = "HIGH"
        elif diversity < 40:
            policy = "Support balanced crop mix"
            action = f"Moderate diversity ({diversity:.0f}%). Maintain support for both wheat and maize."
            priority = "MEDIUM"
        else:
            policy = "Maintain current crop policies"
            action = f"Good diversity ({diversity:.0f}%). Current policies are working well."
            priority = "LOW"

        return {
            'policy': policy,
            'action': action,
            'priority': priority,
            'current_mix': f"Wheat: {wheat_mean:.1f}, Maize: {maize_mean:.1f}"
        }

    def _recommend_income_policy(self, scenario: str, mean: float, ci_lower: float, ci_upper: float) -> Dict:
        """Recommend income support policy based on economic outcomes."""
        # Assuming target income of €200,000 total (adjust based on goals)
        target_income = 200000
        income_gap = target_income - mean
        income_gap_pct = (income_gap / target_income) * 100

        if income_gap > 50000:
            policy = "Increase direct income support"
            action = f"Income below target by €{income_gap:,.0f} ({income_gap_pct:.0f}%). Increase subsidies or price supports."
            priority = "HIGH"
        elif income_gap > 0:
            policy = "Modest income support increase"
            action = f"Income slightly below target (€{income_gap:,.0f}). Small adjustments needed."
            priority = "MEDIUM"
        else:
            policy = "Maintain current income support"
            action = f"Income meets or exceeds target. Current policies are effective."
            priority = "LOW"

        return {
            'policy': policy,
            'action': action,
            'priority': priority,
            'current_income': f"€{mean:,.0f} (95% CI: €{ci_lower:,.0f}-€{ci_upper:,.0f})"
        }

    def _determine_priority(self, scenario: str, last_stats: Dict) -> str:
        """Determine overall policy priority for this scenario."""
        # RCP85 = highest priority (worst case)
        # RCP26 = lowest priority (best case)
        if scenario == 'rcp85':
            return "CRITICAL - Urgent action needed for worst-case climate scenario"
        elif scenario == 'rcp45':
            return "HIGH - Proactive measures recommended for moderate scenario"
        else:
            return "MEDIUM - Monitor and maintain for best-case scenario"

    def _generate_overall_strategy(self) -> Dict:
        """Generate overall strategy across all scenarios."""
        strategy = {
            'robust_policies': [],
            'scenario_specific': [],
            'investment_priorities': [],
        }

        # Compare solar adoption across scenarios
        solar_by_scenario = {}
        for scenario in self.scenarios:
            stats = self.results[scenario]['stats_by_year']
            if stats:
                last_year = max(stats.keys())
                solar_by_scenario[scenario] = stats[last_year]['solar']['mean']

        # Robust policies (work well across all scenarios)
        if all(v > 5 for v in solar_by_scenario.values()):
            strategy['robust_policies'].append(
                "Solar PV subsidies are effective across all scenarios - maintain as core policy"
            )
        else:
            strategy['robust_policies'].append(
                "Solar PV adoption varies by scenario - target subsidies based on climate trajectory"
            )

        # Scenario-specific strategies
        if 'rcp85' in solar_by_scenario and 'rcp26' in solar_by_scenario:
            diff = solar_by_scenario['rcp85'] - solar_by_scenario['rcp26']
            if abs(diff) > 2:
                strategy['scenario_specific'].append(
                    f"Solar adoption differs by {abs(diff):.1f} parcels between best/worst case - prepare flexible policies"
                )

        # Investment priorities
        strategy['investment_priorities'] = [
            "1. Solar infrastructure (grid connections, storage)",
            "2. Crop diversification programs (resilient varieties)",
            "3. Income insurance schemes (hedge against climate risk)",
            "4. Knowledge sharing networks (farmer cooperatives)",
        ]

        return strategy

    def _extract_key_insights(self) -> List[str]:
        """Extract key insights from cross-scenario analysis."""
        insights = []

        # Compare income across scenarios
        income_by_scenario = {}
        for scenario in self.scenarios:
            stats = self.results[scenario]['stats_by_year']
            if stats:
                last_year = max(stats.keys())
                income_by_scenario[scenario] = stats[last_year]['income']['mean']

        if 'rcp85' in income_by_scenario and 'rcp26' in income_by_scenario:
            income_loss = income_by_scenario['rcp26'] - income_by_scenario['rcp85']
            income_loss_pct = (income_loss / income_by_scenario['rcp26']) * 100

            if income_loss_pct > 10:
                pessimistic_display = get_scenario_display_name('rcp85')
                insights.append(
                    f"⚠️  Climate impact: Income drops by {income_loss_pct:.0f}% in worst-case scenario ({pessimistic_display})"
                )
                insights.append(
                    f"💰 To maintain income under {pessimistic_display}, subsidies should increase by ~{income_loss_pct:.0f}%"
                )

        # Solar vs farming trade-off
        insights.append(
            "🌱 Diversification is key: Mix of farming and solar PV reduces risk across all scenarios"
        )

        # Uncertainty insight
        insights.append(
            "📊 Uncertainty quantified: All recommendations include 95% confidence intervals for robust decision-making"
        )

        return insights

    def print_recommendations(self, recommendations: Dict):
        """Print recommendations in human-readable format."""
        print("\n" + "=" * 80)
        print("POLICY RECOMMENDATIONS")
        print("=" * 80)

        # By scenario
        for scenario in self.scenarios:
            scenario_display = get_scenario_display_name(scenario)
            print(f"\n📍 {scenario_display} Scenario:")
            print(f"   Priority: {recommendations['by_scenario'][scenario].get('priority', 'N/A')}")

            rec = recommendations['by_scenario'][scenario]

            print(f"\n   🔆 Solar PV Policy:")
            solar = rec.get('solar_adoption', {})
            print(f"      → {solar.get('policy', 'N/A')}")
            print(f"      → {solar.get('action', 'N/A')}")
            print(f"      → {solar.get('confidence', 'N/A')}")

            print(f"\n   🌾 Crop Policy:")
            crop = rec.get('crop_diversification', {})
            print(f"      → {crop.get('policy', 'N/A')}")
            print(f"      → {crop.get('action', 'N/A')}")

            print(f"\n   💶 Income Support:")
            income = rec.get('income_support', {})
            print(f"      → {income.get('policy', 'N/A')}")
            print(f"      → {income.get('action', 'N/A')}")

        # Overall strategy
        print(f"\n" + "=" * 80)
        print("OVERALL STRATEGY")
        print("=" * 80)

        strategy = recommendations['overall_strategy']

        print(f"\n✅ Robust Policies (work across all scenarios):")
        for policy in strategy.get('robust_policies', []):
            print(f"   • {policy}")

        print(f"\n⚙️  Scenario-Specific Adjustments:")
        for adj in strategy.get('scenario_specific', []):
            print(f"   • {adj}")

        print(f"\n💼 Investment Priorities:")
        for priority in strategy.get('investment_priorities', []):
            print(f"   {priority}")

        # Key insights
        print(f"\n" + "=" * 80)
        print("KEY INSIGHTS")
        print("=" * 80)
        for insight in recommendations.get('key_insights', []):
            print(f"   {insight}")

        print("\n" + "=" * 80)
