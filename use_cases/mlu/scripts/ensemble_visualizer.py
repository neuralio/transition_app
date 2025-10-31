"""
Ensemble Visualization Module

Creates visualizations for Monte Carlo ensemble results:
- Time-series with confidence bands (uncertainty visualization)
- Parcel suitability ranking with uncertainty bars
- Scenario comparison with probabilistic projections
- Qualitative interpretations (environmental benefits, community impact)
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from typing import Dict, List
import numpy as np
import sys
from use_cases.mlu.scripts.qualitative_interpreter import QualitativeInterpreter

# Import scenario utilities for display names
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from scenario_utils import get_scenario_display_name, get_scenario_short_name


def inject_responsive_css_to_file(output_file):
    """Inject AGGRESSIVE responsive CSS into generated HTML file to make plots full-width."""
    with open(output_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    if 'plotly-responsive-styles' not in html_content:
        responsive_css = """
        <style id="plotly-responsive-styles">
            html, body {
                margin: 0 !important;
                padding: 0 !important;
                width: 100% !important;
                overflow-x: hidden !important;
            }
            body > div {
                width: 100% !important;
                max-width: 100% !important;
            }
            #plotly-div,
            .plotly-graph-div,
            .js-plotly-plot,
            .plot-container,
            .svg-container {
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
            }
            div[id^="plotly"] {
                width: 100% !important;
            }
        </style>
        """

        if '</head>' in html_content:
            html_content = html_content.replace('</head>', f'{responsive_css}</head>', 1)
        else:
            html_content = responsive_css + html_content

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)


class EnsembleVisualizer:
    """Generate visualizations for ensemble simulation results."""

    def __init__(self, ensemble_stats: Dict):
        """
        Initialize visualizer with ensemble statistics.

        Args:
            ensemble_stats: Dictionary from EnsembleRunner
        """
        self.stats = ensemble_stats
        self.scenario = ensemble_stats['scenario']
        self.scenario_display = get_scenario_display_name(self.scenario)
        self.scenario_short = get_scenario_short_name(self.scenario)  # For filenames
        self.confidence_level = ensemble_stats['confidence_level']

    def create_time_series_with_uncertainty(self, output_path: str):
        """
        Create time-series plots with confidence bands showing uncertainty.

        Shows mean trajectory with shaded confidence interval bands.
        """
        stats_by_year = self.stats['stats_by_year']
        years = sorted(stats_by_year.keys())

        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Land Use Adoption (with 95% CI)',
                'Total Income (with 95% CI)',
                'Average Yield (with 95% CI)',
                'Solar Energy Production (with 95% CI)'
            )
        )

        # 1. Land use adoption (wheat, maize, solar)
        for crop, color, row, col in [
            ('wheat', 'blue', 1, 1),
            ('maize', 'orange', 1, 1),
            ('solar', 'green', 1, 1)
        ]:
            means = [stats_by_year[y][crop]['mean'] for y in years]
            ci_lower = [stats_by_year[y][crop]['ci_lower'] for y in years]
            ci_upper = [stats_by_year[y][crop]['ci_upper'] for y in years]

            # Confidence band (shaded area)
            fig.add_trace(go.Scatter(
                x=years + years[::-1],
                y=ci_upper + ci_lower[::-1],
                fill='toself',
                fillcolor=f'rgba({self._hex_to_rgb(color)}, 0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                showlegend=False,
                name=f'{crop.upper()} CI'
            ), row=1, col=1)

            # Mean line
            fig.add_trace(go.Scatter(
                x=years,
                y=means,
                mode='lines+markers',
                name=crop.upper(),
                line=dict(color=color, width=2),
            ), row=1, col=1)

        # 2. Total income
        income_means = [stats_by_year[y]['income']['mean'] for y in years]
        income_lower = [stats_by_year[y]['income']['ci_lower'] for y in years]
        income_upper = [stats_by_year[y]['income']['ci_upper'] for y in years]

        fig.add_trace(go.Scatter(
            x=years + years[::-1],
            y=income_upper + income_lower[::-1],
            fill='toself',
            fillcolor='rgba(0, 100, 255, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            showlegend=False,
            name='Income CI'
        ), row=1, col=2)

        fig.add_trace(go.Scatter(
            x=years,
            y=income_means,
            mode='lines+markers',
            name='Total Income',
            line=dict(color='blue', width=2),
        ), row=1, col=2)

        # 3. Average yield
        yield_means = [stats_by_year[y]['yield']['mean'] for y in years]
        yield_lower = [stats_by_year[y]['yield']['ci_lower'] for y in years]
        yield_upper = [stats_by_year[y]['yield']['ci_upper'] for y in years]

        fig.add_trace(go.Scatter(
            x=years + years[::-1],
            y=yield_upper + yield_lower[::-1],
            fill='toself',
            fillcolor='rgba(255, 140, 0, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            showlegend=False,
            name='Yield CI'
        ), row=2, col=1)

        fig.add_trace(go.Scatter(
            x=years,
            y=yield_means,
            mode='lines+markers',
            name='Avg Yield',
            line=dict(color='orange', width=2),
        ), row=2, col=1)

        # 4. Solar energy
        energy_means = [stats_by_year[y]['energy']['mean'] for y in years]
        energy_lower = [stats_by_year[y]['energy']['ci_lower'] for y in years]
        energy_upper = [stats_by_year[y]['energy']['ci_upper'] for y in years]

        fig.add_trace(go.Scatter(
            x=years + years[::-1],
            y=energy_upper + energy_lower[::-1],
            fill='toself',
            fillcolor='rgba(0, 200, 0, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            showlegend=False,
            name='Energy CI'
        ), row=2, col=2)

        fig.add_trace(go.Scatter(
            x=years,
            y=energy_means,
            mode='lines+markers',
            name='Solar Energy',
            line=dict(color='green', width=2),
        ), row=2, col=2)

        # Update layout
        fig.update_xaxes(title_text="Year", row=2, col=1)
        fig.update_xaxes(title_text="Year", row=2, col=2)
        fig.update_yaxes(title_text="Number of Parcels", row=1, col=1)
        fig.update_yaxes(title_text="Income (€)", row=1, col=2)
        fig.update_yaxes(title_text="Yield (tons/ha)", row=2, col=1)
        fig.update_yaxes(title_text="Energy (kWh)", row=2, col=2)

        fig.update_layout(
            title=f"Ensemble Results: {self.scenario_display} (with {self.confidence_level*100:.0f}% Confidence Intervals)",
            height=800,
            showlegend=True,
            template='plotly_white'
        )

        fig.write_html(output_path, config={'responsive': True, 'displayModeBar': True})
        inject_responsive_css_to_file(output_path)
        print(f"      ✅ Time-series with uncertainty bands: {Path(output_path).name}")

    def create_probabilistic_summary(self, output_path: str):
        """
        Create bar chart showing final year results with error bars (uncertainty).
        """
        if not self.stats['stats_by_year']:
            return

        last_year = max(self.stats['stats_by_year'].keys())
        last_stats = self.stats['stats_by_year'][last_year]

        # Prepare data
        metrics = ['wheat', 'maize', 'solar']
        means = [last_stats[m]['mean'] for m in metrics]
        ci_lower = [last_stats[m]['ci_lower'] for m in metrics]
        ci_upper = [last_stats[m]['ci_upper'] for m in metrics]

        # Error bars (CI range)
        error_y = dict(
            type='data',
            symmetric=False,
            array=[u - m for u, m in zip(ci_upper, means)],
            arrayminus=[m - l for m, l in zip(means, ci_lower)]
        )

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=[m.upper() for m in metrics],
            y=means,
            error_y=error_y,
            marker_color=['blue', 'orange', 'green'],
            text=[f'{m:.1f}' for m in means],
            textposition='outside',
        ))

        fig.update_layout(
            title=f"Land Use Distribution in {last_year} ({self.scenario_display})<br>"
                  f"<sub>Error bars show {self.confidence_level*100:.0f}% confidence intervals</sub>",
            xaxis_title="Land Use Type",
            yaxis_title="Number of Parcels",
            template='plotly_white',
            height=500,
            autosize=True
        )

        fig.write_html(output_path, config={'responsive': True, 'displayModeBar': True})
        inject_responsive_css_to_file(output_path)
        print(f"      ✅ Probabilistic summary: {Path(output_path).name}")

    def create_uncertainty_dashboard(self, output_path: str):
        """
        Create comprehensive dashboard showing all uncertainty metrics.
        """
        if not self.stats['stats_by_year']:
            return

        last_year = max(self.stats['stats_by_year'].keys())
        last_stats = self.stats['stats_by_year'][last_year]

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Land Use Uncertainty',
                'Income Uncertainty',
                'Yield Uncertainty',
                'Energy Uncertainty'
            ),
            specs=[[{'type': 'bar'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'bar'}]]
        )

        # 1. Land use
        for i, (metric, color) in enumerate([('wheat', 'blue'), ('maize', 'orange'), ('solar', 'green')]):
            stats = last_stats[metric]
            fig.add_trace(go.Bar(
                name=metric.upper(),
                x=['Mean', 'Median', 'Min', 'Max'],
                y=[stats['mean'], stats['median'], stats['min'], stats['max']],
                marker_color=color
            ), row=1, col=1)

        # 2. Income
        income = last_stats['income']
        fig.add_trace(go.Bar(
            name='Income',
            x=['Mean', 'Median', 'CI Lower', 'CI Upper'],
            y=[income['mean'], income['median'], income['ci_lower'], income['ci_upper']],
            marker_color='blue'
        ), row=1, col=2)

        # 3. Yield
        yield_stats = last_stats['yield']
        fig.add_trace(go.Bar(
            name='Yield',
            x=['Mean', 'Median', 'CI Lower', 'CI Upper'],
            y=[yield_stats['mean'], yield_stats['median'], yield_stats['ci_lower'], yield_stats['ci_upper']],
            marker_color='orange'
        ), row=2, col=1)

        # 4. Energy
        energy = last_stats['energy']
        fig.add_trace(go.Bar(
            name='Energy',
            x=['Mean', 'Median', 'CI Lower', 'CI Upper'],
            y=[energy['mean'], energy['median'], energy['ci_lower'], energy['ci_upper']],
            marker_color='green'
        ), row=2, col=2)

        fig.update_layout(
            title=f"Uncertainty Dashboard: {self.scenario_display} (Year {last_year})",
            height=800,
            showlegend=True,
            template='plotly_white'
        )

        fig.write_html(output_path, config={'responsive': True, 'displayModeBar': True})
        inject_responsive_css_to_file(output_path)
        print(f"      ✅ Uncertainty dashboard: {Path(output_path).name}")

    def _hex_to_rgb(self, hex_color: str) -> str:
        """Convert hex color to RGB string for rgba()."""
        if hex_color == 'blue':
            return '0, 0, 255'
        elif hex_color == 'orange':
            return '255, 140, 0'
        elif hex_color == 'green':
            return '0, 200, 0'
        return '0, 0, 0'

    def create_insights_dashboard(self, output_path: str, recommendations_file: str = None):
        """
        Create multi-tab insights dashboard with:
        - Tab 1: Qualitative Insights (environmental/community impacts)
        - Tab 2: Policy Recommendations (actionable items for decision-makers)
        - Tab 3: Technical Details (ensemble statistics and confidence intervals)

        Args:
            output_path: Path to save dashboard HTML
            recommendations_file: Path to policy_recommendations.json (optional)
        """
        if not self.stats['stats_by_year']:
            return

        last_year = max(self.stats['stats_by_year'].keys())
        last_stats = self.stats['stats_by_year'][last_year]

        # Extract quantitative data for all tabs
        solar_mean = last_stats['solar']['mean']
        wheat_mean = last_stats['wheat']['mean']
        maize_mean = last_stats['maize']['mean']
        income_mean = last_stats['income']['mean']

        # Generate qualitative interpretations
        solar_interp = QualitativeInterpreter.interpret_solar_adoption(solar_mean)
        diversity_interp = QualitativeInterpreter.interpret_crop_diversity(wheat_mean, maize_mean)
        income_interp = QualitativeInterpreter.interpret_income_level(income_mean)
        climate_interp = QualitativeInterpreter.interpret_scenario_climate(self.scenario)

        # Load policy recommendations from JSON (if available)
        policy_recommendations = None
        if recommendations_file and Path(recommendations_file).exists():
            with open(recommendations_file, 'r') as f:
                policy_recommendations = json.load(f)

        # Start HTML with tab structure
        html_content = f"""
        <html>
        <head>
            <title>{self.scenario_short} - Insights Dashboard</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    margin: 0;
                    padding: 0;
                    background: #f8fafc;
                    color: #1e293b;
                }}

                /* Tab Navigation */
                .tab-container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}

                .tab-nav {{
                    display: flex;
                    background: #1e293b;
                    border-bottom: 3px solid #3b82f6;
                    position: sticky;
                    top: 0;
                    z-index: 100;
                }}

                .tab-button {{
                    flex: 1;
                    padding: 16px 24px;
                    background: #1e293b;
                    color: #94a3b8;
                    border: none;
                    cursor: pointer;
                    font-size: 15px;
                    font-weight: 600;
                    transition: all 0.3s ease;
                    border-bottom: 3px solid transparent;
                }}

                .tab-button:hover {{
                    background: #334155;
                    color: #e2e8f0;
                }}

                .tab-button.active {{
                    background: #f8fafc;
                    color: #0f172a;
                    border-bottom: 3px solid #3b82f6;
                }}

                .tab-content {{
                    display: none;
                    padding: 40px;
                    max-width: 900px;
                    margin: 0 auto;
                }}

                .tab-content.active {{
                    display: block;
                }}

                /* Existing styles */
                h1 {{ color: #0f172a; border-bottom: 3px solid #3b82f6; padding-bottom: 10px; margin-top: 0; }}
                h2 {{ color: #334155; margin-top: 30px; border-left: 4px solid #3b82f6; padding-left: 15px; }}
                h3 {{ color: #475569; margin-top: 20px; }}
                .section {{ background: white; padding: 25px; margin: 20px 0; border-radius: 8px;
                           box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .metric {{ display: inline-block; background: #eff6ff; padding: 8px 16px;
                          border-radius: 6px; margin: 5px; font-weight: 600; }}
                .benefit {{ color: #059669; font-weight: 500; }}
                .impact {{ color: #7c3aed; font-weight: 500; }}
                .warning {{ color: #dc2626; }}
                .success {{ color: #16a34a; }}
                .recommendation {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 10px 0; border-radius: 6px; }}
                .stat-box {{ background: #eff6ff; padding: 15px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #3b82f6; }}
            </style>
        </head>
        <body>
            <div class="tab-container">
                <!-- Tab Navigation -->
                <div class="tab-nav">
                    <button class="tab-button active" onclick="openTab(event, 'tab1')">
                        📊 Qualitative Insights
                    </button>
                    <button class="tab-button" onclick="openTab(event, 'tab2')">
                        📋 Policy Recommendations
                    </button>
                    <button class="tab-button" onclick="openTab(event, 'tab3')">
                        🔬 Technical Details
                    </button>
                </div>
"""

        # TAB 1: Qualitative Insights (existing content)
        html_content += self._generate_tab1_qualitative(
            solar_interp, diversity_interp, income_interp, climate_interp, last_year, income_mean
        )

        # TAB 2: Policy Recommendations
        html_content += self._generate_tab2_policy(policy_recommendations)

        # TAB 3: Technical Details
        html_content += self._generate_tab3_technical(last_year)

        # Close HTML with JavaScript
        html_content += """
            </div>

            <script>
                function openTab(evt, tabName) {
                    // Hide all tab content
                    var tabContents = document.getElementsByClassName("tab-content");
                    for (var i = 0; i < tabContents.length; i++) {
                        tabContents[i].classList.remove("active");
                    }

                    // Remove active class from all buttons
                    var tabButtons = document.getElementsByClassName("tab-button");
                    for (var i = 0; i < tabButtons.length; i++) {
                        tabButtons[i].classList.remove("active");
                    }

                    // Show current tab and mark button as active
                    document.getElementById(tabName).classList.add("active");
                    evt.currentTarget.classList.add("active");
                }
            </script>
        </body>
        </html>
        """

        # Write HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"      ✅ Insights dashboard: {Path(output_path).name}")

    def _generate_tab1_qualitative(self, solar_interp, diversity_interp, income_interp, climate_interp, last_year, income_mean):
        """Generate Tab 1: Qualitative Insights content."""
        prob_statements_html = ""
        if 'probabilistic_statements' in self.stats:
            prob_statements = self.stats['probabilistic_statements']
            for key, statement in prob_statements.items():
                prob_statements_html += f"""
                    <div style="margin: 8px 0; padding: 8px; background: #fefce8; border-left: 3px solid #f59e0b;">
                        📌 <strong>{statement}</strong>
                    </div>"""

        return f"""
                <!-- Tab 1: Qualitative Insights -->
                <div id="tab1" class="tab-content active">
                    <h1>📊 Qualitative Impact Assessment: {self.scenario_display}</h1>

                    <div class="section">
                        <h2>🌍 Climate Context</h2>
                        <p><strong>{climate_interp['description']}</strong></p>
                        <p>{climate_interp['climate_reality']}</p>
                        <p><em>{climate_interp['adaptation_need']}</em></p>
                    </div>

                    <div class="section">
                        <h2>☀️ Solar PV Adoption</h2>
                        <p class="metric">{solar_interp['level']} ({solar_interp['percentage']})</p>
                        <p><span class="benefit">Environmental Benefit:</span> {solar_interp['environmental_benefit']}</p>
                        <p><span class="impact">Community Impact:</span> {solar_interp['community_impact']}</p>
                    </div>

                    <div class="section">
                        <h2>🌾 Agricultural Diversity</h2>
                        <p class="metric">{diversity_interp['level']} ({diversity_interp['percentage']})</p>
                        <p><span class="benefit">Environmental Benefit:</span> {diversity_interp['environmental_benefit']}</p>
                        <p><span class="impact">Community Impact:</span> {diversity_interp['community_impact']}</p>
                    </div>

                    <div class="section">
                        <h2>💰 Economic Status</h2>
                        <p class="metric">{income_interp['level']} ({income_interp['value']})</p>
                        <p><span class="benefit">Environmental Implication:</span> {income_interp['environmental_implication']}</p>
                        <p><span class="impact">Community Impact:</span> {income_interp['community_impact']}</p>
                    </div>

                    <div class="section">
                        <h2>🎯 Key Takeaways</h2>
                        <ul>
                            <li>The region demonstrates <strong>{solar_interp['level']}</strong> with <strong>{diversity_interp['level']}</strong></li>
                            <li>Environmental sustainability: {'⚠️ Needs improvement' if float(solar_interp['percentage'].strip('%')) < 30 else '✅ On track'}</li>
                            <li>Community resilience: {'⚠️ Vulnerable' if income_mean < 6000 else '✅ Stable'}</li>
                            <li>Climate adaptation: {climate_interp['adaptation_need'].split('.')[0]}</li>
                        </ul>
                    </div>

                    <div class="section" style="background: #fef3c7; border-left: 4px solid #f59e0b;">
                        <h2>📊 Probabilistic Projections</h2>
                        <p style="font-size: 15px; color: #78350f; margin-bottom: 15px;">
                            <strong>Based on {self.stats['ensemble_size']} Monte Carlo simulations with {self.stats['confidence_level']*100:.0f}% confidence:</strong>
                        </p>
                        <div style="background: white; padding: 15px; border-radius: 6px; margin: 10px 0;">
                            {prob_statements_html}
                        </div>
                        <p style="font-size: 14px; color: #78350f; margin-top: 15px;">
                            <em>These probabilities indicate the likelihood of different outcomes occurring by {last_year},
                            helping decision-makers understand the most favorable land-use choices under uncertainty.</em>
                        </p>
                    </div>
                </div>
"""

    def _generate_tab2_policy(self, policy_recommendations):
        """
        Generate Tab 2: Policy Recommendations content.

        Uses policy recommendations from PolicyRecommender (loaded from JSON).

        Args:
            policy_recommendations: Dict from PolicyRecommender.generate_recommendations()
                                   Structure: {'by_scenario': {scenario: {...}}, 'overall_strategy': {...}, 'key_insights': [...]}
        """
        if not policy_recommendations:
            return """
                <!-- Tab 2: Policy Recommendations -->
                <div id="tab2" class="tab-content">
                    <h1>📋 Policy Recommendations: {self.scenario_display}</h1>
                    <div class="section" style="background: #fef3c7; border-left: 4px solid #f59e0b;">
                        <p style="color: #78350f;">Policy recommendations not available. Please ensure ensemble mode is enabled.</p>
                    </div>
                </div>
"""

        # Get recommendations for current scenario
        scenario_rec = policy_recommendations['by_scenario'].get(self.scenario, {})
        if not scenario_rec:
            return """
                <!-- Tab 2: Policy Recommendations -->
                <div id="tab2" class="tab-content">
                    <h1>📋 Policy Recommendations: {self.scenario_display}</h1>
                    <div class="section" style="background: #fef3c7; border-left: 4px solid #f59e0b;">
                        <p style="color: #78350f;">No recommendations found for {self.scenario_display}.</p>
                    </div>
                </div>
"""

        solar_rec = scenario_rec.get('solar_adoption', {})
        crop_rec = scenario_rec.get('crop_diversification', {})
        income_rec = scenario_rec.get('income_support', {})
        priority = scenario_rec.get('priority', 'N/A')

        overall_strategy = policy_recommendations.get('overall_strategy', {})
        key_insights = policy_recommendations.get('key_insights', [])

        # Build robust policies list
        robust_html = ""
        for policy in overall_strategy.get('robust_policies', []):
            robust_html += f"<li>{policy}</li>\n"

        # Build scenario-specific adjustments list
        scenario_specific_html = ""
        for adj in overall_strategy.get('scenario_specific', []):
            scenario_specific_html += f"<li>{adj}</li>\n"

        # Build investment priorities list
        investment_html = ""
        for inv_priority in overall_strategy.get('investment_priorities', []):
            investment_html += f"<li>{inv_priority}</li>\n"

        # Build key insights list
        insights_html = ""
        for insight in key_insights:
            insights_html += f"<li>{insight}</li>\n"

        return f"""
                <!-- Tab 2: Policy Recommendations -->
                <div id="tab2" class="tab-content">
                    <h1>📋 Policy Recommendations: {self.scenario_display}</h1>

                    <div class="section" style="background: #fef3c7; border-left: 4px solid #f59e0b;">
                        <p style="font-size: 16px; color: #78350f;">
                            <strong>Priority: {priority}</strong>
                        </p>
                    </div>

                    <div class="recommendation">
                        <h2>🔆 Solar PV Policy</h2>
                        <p><strong>→ {solar_rec.get('policy', 'N/A')}</strong></p>
                        <p style="font-weight: normal;">→ {solar_rec.get('action', 'N/A')}</p>
                        <p style="font-weight: normal;">→ {solar_rec.get('confidence', 'N/A')}</p>
                    </div>

                    <div class="recommendation">
                        <h2>🌾 Crop Policy</h2>
                        <p><strong>→ {crop_rec.get('policy', 'N/A')}</strong></p>
                        <p style="font-weight: normal;">→ {crop_rec.get('action', 'N/A')}</p>
                    </div>

                    <div class="recommendation">
                        <h2>💶 Income Support</h2>
                        <p><strong>→ {income_rec.get('policy', 'N/A')}</strong></p>
                        <p style="font-weight: normal;">→ {income_rec.get('action', 'N/A')}</p>
                    </div>

                    <div class="section" style="background: #eff6ff; border-left: 4px solid #3b82f6;">
                        <h2>⚙️ Overall Strategy</h2>
                        <p><strong>✅ Robust Policies (work across all scenarios):</strong></p>
                        <ul>
                            {robust_html}
                        </ul>

                        <p><strong>⚙️ Scenario-Specific Adjustments:</strong></p>
                        <ul>
                            {scenario_specific_html}
                        </ul>

                        <p><strong>💼 Investment Priorities:</strong></p>
                        <ol>
                            {investment_html}
                        </ol>
                    </div>

                    <div class="section" style="background: #f0fdf4; border-left: 4px solid #16a34a;">
                        <h2>🌱 Key Insights</h2>
                        <ul>
                            {insights_html}
                        </ul>
                    </div>
                </div>
"""

    def _generate_tab3_technical(self, last_year):
        """Generate Tab 3: Technical Details content."""
        # Get all statistics
        stats_by_year = self.stats['stats_by_year']
        last_stats = stats_by_year[last_year]

        # Format confidence intervals
        metrics = ['solar', 'wheat', 'maize', 'income']
        metrics_display = {'solar': 'Solar PV Adoption', 'wheat': 'Wheat Parcels', 'maize': 'Maize Parcels', 'income': 'Average Income (€)'}

        stats_html = ""
        for metric in metrics:
            if metric in last_stats:
                data = last_stats[metric]
                stats_html += f"""
                    <div class="stat-box">
                        <h3>{metrics_display[metric]}</h3>
                        <p><strong>Mean:</strong> {data['mean']:.2f}</p>
                        <p><strong>Median:</strong> {data['median']:.2f}</p>
                        <p><strong>Std Dev:</strong> {data['std']:.2f}</p>
                        <p><strong>95% CI:</strong> [{data['ci_lower']:.2f}, {data['ci_upper']:.2f}]</p>
                        <p><strong>Min:</strong> {data['min']:.2f} | <strong>Max:</strong> {data['max']:.2f}</p>
                    </div>
                """

        return f"""
                <!-- Tab 3: Technical Details -->
                <div id="tab3" class="tab-content">
                    <h1>🔬 Technical Details: {self.scenario_display}</h1>

                    <div class="section">
                        <h2>📊 Ensemble Configuration</h2>
                        <p><strong>Number of Simulations:</strong> {self.stats['ensemble_size']}</p>
                        <p><strong>Confidence Level:</strong> {self.stats['confidence_level']*100:.0f}%</p>
                        <p><strong>Scenario:</strong> {self.scenario_display}</p>
                        <p><strong>Final Year:</strong> {last_year}</p>
                    </div>

                    <div class="section">
                        <h2>📈 Final Year Statistics (Year {last_year})</h2>
                        {stats_html}
                    </div>

                    <div class="section" style="background: #fef3c7; border-left: 4px solid #f59e0b;">
                        <h2>ℹ️ Methodology Notes</h2>
                        <p><strong>Monte Carlo Ensemble:</strong> Multiple simulation runs with stochastic agent decisions to quantify uncertainty.</p>
                        <p><strong>Confidence Intervals:</strong> 95% CI represents the range where we expect the true value to fall 95% of the time.</p>
                        <p><strong>Agent-Based Model:</strong> Individual land parcels make autonomous decisions based on climate, prices, and policies.</p>
                        <p><strong>Multi-Level Dynamics:</strong> Interactions across individual, community, market, and policy levels.</p>
                    </div>

                    <div class="section" style="background: #e0f2fe; border-left: 4px solid #0284c7;">
                        <h2>💡 Understanding the Metrics</h2>
                        <p><strong>Average Income (€):</strong> Total revenue per parcel from farming activities and/or solar energy sales. Calculated as:</p>
                        <ul>
                            <li><strong>Farming income:</strong> Crop yield × market price per ton (for wheat/maize parcels)</li>
                            <li><strong>Solar income:</strong> Annual energy production (kWh) × feed-in tariff (for solar PV parcels)</li>
                            <li><strong>Total:</strong> Sum across all parcels ÷ number of parcels</li>
                        </ul>
                        <p><em>Note: If solar/maize adoption is 0, income comes entirely from wheat farming revenue.</em></p>

                        <p><strong>Solar PV Adoption:</strong> Number of parcels that switched from farming to solar PV installations.</p>
                        <p><strong>Wheat/Maize Parcels:</strong> Number of parcels growing each crop type.</p>
                        <p><strong>Energy Production:</strong> Total solar energy generated (kWh/year) - zero if no solar adoption.</p>
                    </div>
                </div>
"""

    def create_qualitative_summary(self, output_path: str):
        """
        DEPRECATED: Use create_insights_dashboard() instead.
        Create qualitative narrative summary with environmental/community impacts.
        """
        if not self.stats['stats_by_year']:
            return

        last_year = max(self.stats['stats_by_year'].keys())
        last_stats = self.stats['stats_by_year'][last_year]

        # Extract quantitative data
        solar_mean = last_stats['solar']['mean']
        wheat_mean = last_stats['wheat']['mean']
        maize_mean = last_stats['maize']['mean']
        income_mean = last_stats['income']['mean']

        # Generate qualitative interpretations
        solar_interp = QualitativeInterpreter.interpret_solar_adoption(solar_mean)
        diversity_interp = QualitativeInterpreter.interpret_crop_diversity(wheat_mean, maize_mean)
        income_interp = QualitativeInterpreter.interpret_income_level(income_mean)
        climate_interp = QualitativeInterpreter.interpret_scenario_climate(self.scenario)

        # Create HTML report with qualitative text
        html_content = f"""
        <html>
        <head>
            <title>{self.scenario_short} - Qualitative Summary</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                       padding: 40px; background: #f8fafc; color: #1e293b; max-width: 900px; margin: auto; }}
                h1 {{ color: #0f172a; border-bottom: 3px solid #3b82f6; padding-bottom: 10px; }}
                h2 {{ color: #334155; margin-top: 30px; border-left: 4px solid #3b82f6; padding-left: 15px; }}
                .section {{ background: white; padding: 25px; margin: 20px 0; border-radius: 8px;
                           box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .metric {{ display: inline-block; background: #eff6ff; padding: 8px 16px;
                          border-radius: 6px; margin: 5px; font-weight: 600; }}
                .benefit {{ color: #059669; font-weight: 500; }}
                .impact {{ color: #7c3aed; font-weight: 500; }}
                .warning {{ color: #dc2626; }}
                .success {{ color: #16a34a; }}
            </style>
        </head>
        <body>
            <h1>📊 Qualitative Impact Assessment: {self.scenario_display}</h1>

            <div class="section">
                <h2>🌍 Climate Context</h2>
                <p><strong>{climate_interp['description']}</strong></p>
                <p>{climate_interp['climate_reality']}</p>
                <p><em>{climate_interp['adaptation_need']}</em></p>
            </div>

            <div class="section">
                <h2>☀️ Solar PV Adoption</h2>
                <p class="metric">{solar_interp['level']} ({solar_interp['percentage']})</p>
                <p><span class="benefit">Environmental Benefit:</span> {solar_interp['environmental_benefit']}</p>
                <p><span class="impact">Community Impact:</span> {solar_interp['community_impact']}</p>
            </div>

            <div class="section">
                <h2>🌾 Agricultural Diversity</h2>
                <p class="metric">{diversity_interp['level']} ({diversity_interp['percentage']})</p>
                <p><span class="benefit">Environmental Benefit:</span> {diversity_interp['environmental_benefit']}</p>
                <p><span class="impact">Community Impact:</span> {diversity_interp['community_impact']}</p>
            </div>

            <div class="section">
                <h2>💰 Economic Status</h2>
                <p class="metric">{income_interp['level']} ({income_interp['value']})</p>
                <p><span class="benefit">Environmental Implication:</span> {income_interp['environmental_implication']}</p>
                <p><span class="impact">Community Impact:</span> {income_interp['community_impact']}</p>
            </div>

            <div class="section">
                <h2>🎯 Key Takeaways</h2>
                <ul>
                    <li>The region demonstrates <strong>{solar_interp['level']}</strong> with <strong>{diversity_interp['level']}</strong></li>
                    <li>Environmental sustainability: {('⚠️ Needs improvement' if float(solar_interp['percentage'].strip('%')) < 30 else '✅ On track')}</li>
                    <li>Community resilience: {('⚠️ Vulnerable' if income_mean < 6000 else '✅ Stable')}</li>
                    <li>Climate adaptation: {climate_interp['adaptation_need'].split('.')[0]}</li>
                </ul>
            </div>

            <div class="section" style="background: #fef3c7; border-left: 4px solid #f59e0b;">
                <h2>📊 Probabilistic Projections</h2>
                <p style="font-size: 15px; color: #78350f; margin-bottom: 15px;">
                    <strong>Based on {self.stats['ensemble_size']} Monte Carlo simulations with {self.stats['confidence_level']*100:.0f}% confidence:</strong>
                </p>
                <div style="background: white; padding: 15px; border-radius: 6px; margin: 10px 0;">"""

        # Add probabilistic statements
        if 'probabilistic_statements' in self.stats:
            prob_statements = self.stats['probabilistic_statements']
            for key, statement in prob_statements.items():
                html_content += f"""
                    <div style="margin: 8px 0; padding: 8px; background: #fefce8; border-left: 3px solid #f59e0b;">
                        📌 <strong>{statement}</strong>
                    </div>"""

        html_content += f"""
                </div>
                <p style="font-size: 14px; color: #78350f; margin-top: 15px;">
                    <em>These probabilities indicate the likelihood of different outcomes occurring by {last_year},
                    helping decision-makers understand the most favorable land-use choices under uncertainty.</em>
                </p>
            </div>

            <div class="section" style="background: #eff6ff; border-left: 4px solid #3b82f6;">
                <p><strong>💡 Complete Analysis:</strong> This report integrates three types of information:
                <ul style="margin-top: 10px;">
                    <li><strong>Quantitative:</strong> Numbers, scores, percentages (e.g., {solar_interp['percentage']} solar adoption)</li>
                    <li><strong>Qualitative:</strong> Environmental benefits and community impacts (e.g., "{solar_interp['environmental_benefit'][:50]}...")</li>
                    <li><strong>Probabilistic:</strong> Likelihood statements showing uncertainty (e.g., {self.stats['confidence_level']*100:.0f}% confidence intervals)</li>
                </ul>
                This comprehensive approach provides robust decision support for land-use planning under {self.scenario_display} climate conditions.</p>
            </div>
        </body>
        </html>
        """

        with open(output_path, 'w') as f:
            f.write(html_content)

        print(f"      ✅ Qualitative summary: {Path(output_path).name}")

    def save_all_visualizations(self, output_dir: str, recommendations_file: str = None):
        """
        Generate all ensemble visualizations.

        Args:
            output_dir: Directory to save HTML files
            recommendations_file: Path to policy_recommendations.json (optional)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Use short scenario name for filenames (Optimistic, Moderate, Pessimistic)
        scenario_name = self.scenario_short

        print(f"\n   📊 Generating ensemble visualizations for {self.scenario_display}...")

        # Time-series with confidence bands
        self.create_time_series_with_uncertainty(
            str(output_path / f"{scenario_name}_ensemble_timeseries.html")
        )

        # Probabilistic summary
        self.create_probabilistic_summary(
            str(output_path / f"{scenario_name}_ensemble_summary.html")
        )

        # Uncertainty dashboard
        self.create_uncertainty_dashboard(
            str(output_path / f"{scenario_name}_ensemble_dashboard.html")
        )

        # Multi-tab insights dashboard (NEW: combines qualitative + policy + technical)
        self.create_insights_dashboard(
            str(output_path / f"{scenario_name}_insights_dashboard.html"),
            recommendations_file=recommendations_file
        )
