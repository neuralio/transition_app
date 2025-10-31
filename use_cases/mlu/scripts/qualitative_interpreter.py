"""
Qualitative Data Interpreter

Adds qualitative interpretations to quantitative simulation results:
- Environmental benefits descriptions
- Community impact narratives
- Human-readable interpretations of metrics
"""

from typing import Dict, List


class QualitativeInterpreter:
    """Generate qualitative interpretations of simulation results."""

    @staticmethod
    def interpret_solar_adoption(solar_count: float, total_parcels: int = 15) -> Dict[str, str]:
        """
        Generate qualitative interpretation of solar PV adoption.

        Returns:
            Dict with 'level', 'environmental_benefit', 'community_impact'
        """
        adoption_pct = (solar_count / total_parcels) * 100

        if adoption_pct < 15:
            level = "Low adoption"
            env_benefit = "Minimal renewable energy contribution. High carbon footprint remains. Limited climate mitigation."
            community_impact = "Few landowners benefit from energy independence. Community relies heavily on external energy sources."
        elif adoption_pct < 35:
            level = "Moderate adoption"
            env_benefit = "Growing renewable energy capacity. Reduced carbon emissions. Positive climate action visible."
            community_impact = "Increased energy independence for participating landowners. Community interest growing."
        elif adoption_pct < 60:
            level = "High adoption"
            env_benefit = "Significant renewable energy generation. Major carbon emission reductions. Strong climate resilience."
            community_impact = "Widespread energy independence. Community becoming energy self-sufficient. Economic benefits distributed."
        else:
            level = "Very high adoption"
            env_benefit = "Dominant renewable energy. Near-zero agricultural carbon footprint. Exemplary climate leadership."
            community_impact = "Community-wide energy independence. Strong local economy. Model for other regions."

        return {
            'level': level,
            'environmental_benefit': env_benefit,
            'community_impact': community_impact,
            'percentage': f"{adoption_pct:.0f}%"
        }

    @staticmethod
    def interpret_crop_diversity(wheat_count: float, maize_count: float) -> Dict[str, str]:
        """
        Generate qualitative interpretation of crop diversity.

        Returns:
            Dict with 'level', 'environmental_benefit', 'community_impact'
        """
        total_farming = wheat_count + maize_count
        if total_farming == 0:
            diversity_pct = 0
        else:
            diversity_pct = (min(wheat_count, maize_count) / total_farming) * 100

        if diversity_pct < 15:
            level = "Monoculture (low diversity)"
            env_benefit = "High pest/disease risk. Soil degradation concerns. Vulnerable to climate shocks."
            community_impact = "Community food security at risk. Economic fragility from single crop dependence."
        elif diversity_pct < 35:
            level = "Moderate diversity"
            env_benefit = "Improved pest resistance. Better soil health. Some climate resilience."
            community_impact = "Moderate food security. Reduced economic risk from crop failures."
        elif diversity_pct < 50:
            level = "High diversity"
            env_benefit = "Strong ecosystem health. Natural pest control. Climate-resilient agriculture."
            community_impact = "Good food security. Economic stability from diversified income streams."
        else:
            level = "Excellent diversity"
            env_benefit = "Optimal ecosystem services. Maximum soil health. Highly climate-resilient."
            community_impact = "Strong food security. Robust local economy. Model sustainable agriculture."

        return {
            'level': level,
            'environmental_benefit': env_benefit,
            'community_impact': community_impact,
            'percentage': f"{diversity_pct:.0f}%"
        }

    @staticmethod
    def interpret_income_level(avg_income: float) -> Dict[str, str]:
        """
        Generate qualitative interpretation of income levels.

        Returns:
            Dict with 'level', 'environmental_implication', 'community_impact'
        """
        # Income thresholds (adjust based on regional context)
        if avg_income < 5000:
            level = "Low income"
            env_implication = "Risk of unsustainable practices due to financial pressure. Short-term thinking prevails."
            community_impact = "Economic stress. Potential out-migration. Limited investment in sustainable practices."
        elif avg_income < 8000:
            level = "Moderate income"
            env_implication = "Some capacity for sustainable investments. Balance between profit and environment."
            community_impact = "Stable community. Moderate quality of life. Some capacity for innovation."
        elif avg_income < 12000:
            level = "Good income"
            env_implication = "Strong capacity for sustainable practices. Long-term environmental thinking."
            community_impact = "Thriving community. Good quality of life. Active investment in future."
        else:
            level = "High income"
            env_implication = "Excellent sustainability capacity. Environmental stewardship prioritized."
            community_impact = "Prosperous community. High quality of life. Leader in sustainable practices."

        return {
            'level': level,
            'environmental_implication': env_implication,
            'community_impact': community_impact,
            'value': f"€{avg_income:,.0f}/year"
        }

    @staticmethod
    def interpret_scenario_climate(scenario: str) -> Dict[str, str]:
        """
        Generate qualitative description of climate scenario.

        Returns:
            Dict with 'description', 'climate_reality', 'adaptation_need'
        """
        scenarios = {
            'rcp26': {
                'description': 'Best-case scenario (Strong climate action)',
                'climate_reality': 'Aggressive emission reductions. Paris Agreement targets met. Global temperature rise limited to <2°C. Moderate climate impacts.',
                'adaptation_need': 'Proactive adaptation. Focus on optimization rather than crisis response. Long-term planning viable.'
            },
            'rcp45': {
                'description': 'Moderate scenario (Partial climate action)',
                'climate_reality': 'Some emission reductions. Partial policy implementation. Temperature rise 2-3°C. Significant climate impacts.',
                'adaptation_need': 'Balanced adaptation strategy. Both mitigation and resilience needed. Medium-term uncertainty.'
            },
            'rcp85': {
                'description': 'Worst-case scenario (No climate action)',
                'climate_reality': 'Business-as-usual emissions. No meaningful policy. Temperature rise >4°C. Severe climate impacts.',
                'adaptation_need': 'Urgent, transformative adaptation. Crisis management required. High uncertainty in long-term planning.'
            }
        }

        return scenarios.get(scenario, {
            'description': 'Unknown scenario',
            'climate_reality': 'Not specified',
            'adaptation_need': 'Not specified'
        })

    @staticmethod
    def interpret_trade_offs(avg_income: float, crop_diversity: float) -> Dict[str, str]:
        """
        Generate qualitative interpretation of economic-environmental trade-offs.

        Returns:
            Dict with 'balance', 'sustainability_status', 'recommendation'
        """
        # Normalize diversity (0-1 scale assumed)
        income_normalized = min(avg_income / 12000, 1.0)  # 12000 as max reference
        diversity_normalized = crop_diversity  # Already 0-1

        balance_score = (income_normalized + diversity_normalized) / 2

        if balance_score < 0.3:
            balance = "Poor balance"
            sustainability = "Unsustainable. Both economic and environmental goals unmet."
            recommendation = "Urgent intervention needed. Increase subsidies and promote diversification."
        elif balance_score < 0.5:
            balance = "Moderate balance"
            sustainability = "Marginally sustainable. Either economic or environmental goal unmet."
            recommendation = "Targeted improvements needed. Focus on weaker dimension."
        elif balance_score < 0.7:
            balance = "Good balance"
            sustainability = "Sustainable. Both goals reasonably met. Room for optimization."
            recommendation = "Maintain current policies. Fine-tune for efficiency."
        else:
            balance = "Excellent balance"
            sustainability = "Highly sustainable. Exemplary performance on both dimensions."
            recommendation = "Showcase as best practice. Maintain and document for replication."

        return {
            'balance': balance,
            'sustainability_status': sustainability,
            'recommendation': recommendation
        }

    @staticmethod
    def generate_narrative_summary(results: Dict) -> str:
        """
        Generate a human-readable narrative summary of simulation results.

        Args:
            results: Dict with quantitative metrics

        Returns:
            Multi-paragraph narrative summary
        """
        # Extract quantitative data
        solar = results.get('solar_count', 0)
        wheat = results.get('wheat_count', 0)
        maize = results.get('maize_count', 0)
        income = results.get('avg_income', 0)
        scenario = results.get('scenario', 'unknown')

        # Generate qualitative interpretations
        solar_interp = QualitativeInterpreter.interpret_solar_adoption(solar)
        diversity_interp = QualitativeInterpreter.interpret_crop_diversity(wheat, maize)
        income_interp = QualitativeInterpreter.interpret_income_level(income)
        climate_interp = QualitativeInterpreter.interpret_scenario_climate(scenario)

        # Construct narrative
        narrative = f"""
**Climate Context:** {climate_interp['description']}
{climate_interp['climate_reality']}

**Land Use Pattern:**
The region shows {solar_interp['level']} of solar PV ({solar_interp['percentage']}), with {diversity_interp['level']} in agricultural areas ({diversity_interp['percentage']} balanced crop mix).

**Environmental Benefits:**
- **Renewable Energy:** {solar_interp['environmental_benefit']}
- **Agricultural Resilience:** {diversity_interp['environmental_benefit']}

**Community Impact:**
- **Energy Independence:** {solar_interp['community_impact']}
- **Food Security:** {diversity_interp['community_impact']}
- **Economic Status:** {income_interp['level']} ({income_interp['value']}). {income_interp['community_impact']}

**Environmental-Economic Implications:**
{income_interp['environmental_implication']}

**Adaptation Strategy:**
{climate_interp['adaptation_need']}
        """.strip()

        return narrative
