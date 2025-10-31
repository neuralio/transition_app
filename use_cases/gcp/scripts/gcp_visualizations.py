"""
Interactive Visualizations for GCP Simulation

Creates interactive charts (Plotly) and GIS maps (Folium) to visualize:
- PV adoption dynamics (adoption rates, capacity over time)
- Financial institution metrics (loan approval/default rates)
- Policy effectiveness (subsidies, policy adjustments)
- Geographic distribution (PV installation locations)
- Policy feedback loops (GCP-16)
"""

import json
import sys
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import folium
from folium import plugins
import numpy as np
from pathlib import Path
from typing import Dict, List
from global_land_mask import globe

# Add GCP utils to path for scenario display names
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from scenario_utils import get_scenario_display_name


class GCPVisualizer:
    """
    Creates interactive visualizations for GCP simulation results.

    Generates:
    - Plotly charts (time series, comparisons, policy feedback)
    - Folium GIS maps (PV installation locations, financial patterns)
    """

    def __init__(self, output_dir: str = "results/visualizations", data_path: str = None):
        """
        Initialize visualizer.

        Args:
            output_dir: Directory to save visualization files
            data_path: Path to GCP data directory (optional, for overlay data)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_path = Path(data_path) if data_path else None

        # Default region bounds (can be updated from data)
        self.lat_min, self.lat_max = 40.4, 40.9
        self.lon_min, self.lon_max = 22.5, 22.9
        self.center_lat = (self.lat_min + self.lat_max) / 2
        self.center_lon = (self.lon_min + self.lon_max) / 2

    def create_time_series_charts(self,
                                  yearly_stats: List[Dict],
                                  scenario: str,
                                  policy_scenario: str) -> str:
        """
        Create time series charts for PV adoption, loans, and policy metrics.

        Args:
            yearly_stats: List of yearly statistics dicts
            scenario: Climate scenario (rcp26/rcp45/rcp85)
            policy_scenario: Policy scenario (low_support/moderate_support/high_support)

        Returns:
            Path to saved HTML file
        """
        years = [s['year'] for s in yearly_stats]
        pv_adopters = [s['pv_adopters'] for s in yearly_stats]
        pv_adoption_rate = [s['pv_adoption_rate'] * 100 for s in yearly_stats]  # Convert to percentage
        total_pv_capacity = [s['total_pv_capacity_kw'] for s in yearly_stats]
        loans_approved = [s['total_loans_approved'] for s in yearly_stats]
        loans_denied = [s['total_loans_denied'] for s in yearly_stats]
        default_rate = [s['avg_default_rate'] * 100 for s in yearly_stats]  # Convert to percentage
        subsidy_rate = [s['avg_subsidy_rate'] * 100 for s in yearly_stats]  # Convert to percentage
        subsidy_spending = [s['total_subsidy_spending'] for s in yearly_stats]
        # Energy savings metrics (GCP-03 compliance)
        energy_savings = [s.get('total_annual_energy_savings', 0.0) for s in yearly_stats]
        feed_in_revenue = [s.get('total_annual_feed_in_revenue', 0.0) for s in yearly_stats]
        avg_energy_savings = [s.get('avg_annual_energy_savings', 0.0) for s in yearly_stats]

        # Get user-friendly scenario name
        scenario_display = get_scenario_display_name(scenario)

        # Create subplots
        fig = make_subplots(
            rows=5, cols=2,
            subplot_titles=(
                f'PV Adoption Over Time ({scenario_display}, {policy_scenario})',
                f'Total PV Capacity (kW)',
                f'Loan Application Outcomes',
                f'Default Rate (%)',
                f'Policy Subsidy Rate (%)',
                f'Total Subsidy Spending (€)',
                f'PV Adopters vs Non-Adopters',
                f'Loan Approval Rate (%)',
                f'Annual Energy Savings & Revenue (€)',
                f'Avg Energy Savings per Installation (€)'
            ),
            vertical_spacing=0.06,
            horizontal_spacing=0.12,
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )

        # Row 1, Col 1: PV Adoption Rate
        fig.add_trace(
            go.Scatter(
                x=years, y=pv_adoption_rate,
                mode='lines+markers',
                name='PV Adoption Rate (%)',
                line=dict(color='#22c55e', width=3),
                marker=dict(size=8),
                fill='tozeroy'
            ),
            row=1, col=1
        )

        # Row 1, Col 2: Total PV Capacity
        fig.add_trace(
            go.Scatter(
                x=years, y=total_pv_capacity,
                mode='lines+markers',
                name='Total Capacity (kW)',
                line=dict(color='#f59e0b', width=3),
                marker=dict(size=8),
                fill='tozeroy'
            ),
            row=1, col=2
        )

        # Row 2, Col 1: Loan Approvals/Denials
        fig.add_trace(
            go.Bar(
                x=years, y=loans_approved,
                name='Loans Approved',
                marker_color='#3b82f6'
            ),
            row=2, col=1
        )
        fig.add_trace(
            go.Bar(
                x=years, y=loans_denied,
                name='Loans Denied',
                marker_color='#ef4444'
            ),
            row=2, col=1
        )

        # Row 2, Col 2: Default Rate
        fig.add_trace(
            go.Scatter(
                x=years, y=default_rate,
                mode='lines+markers',
                name='Default Rate (%)',
                line=dict(color='#dc2626', width=3),
                marker=dict(size=8)
            ),
            row=2, col=2
        )

        # Row 3, Col 1: Policy Subsidy Rate
        fig.add_trace(
            go.Scatter(
                x=years, y=subsidy_rate,
                mode='lines+markers',
                name='Subsidy Rate (%)',
                line=dict(color='#8b5cf6', width=3),
                marker=dict(size=8)
            ),
            row=3, col=1
        )

        # Row 3, Col 2: Subsidy Spending
        fig.add_trace(
            go.Scatter(
                x=years, y=subsidy_spending,
                mode='lines+markers',
                name='Subsidy Spending (€)',
                line=dict(color='#ec4899', width=3),
                marker=dict(size=8),
                fill='tozeroy'
            ),
            row=3, col=2
        )

        # Row 4, Col 1: Adopters vs Non-Adopters (Stacked Area)
        non_adopters = [s['non_adopters'] for s in yearly_stats]
        fig.add_trace(
            go.Scatter(
                x=years, y=pv_adopters,
                mode='lines',
                name='PV Adopters',
                fill='tonexty',
                line=dict(color='#10b981', width=2)
            ),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=years, y=non_adopters,
                mode='lines',
                name='Non-Adopters',
                fill='tozeroy',
                line=dict(color='#6b7280', width=2)
            ),
            row=4, col=1
        )

        # Row 4, Col 2: Loan Approval Rate
        approval_rate = [
            (s['total_loans_approved'] / (s['total_loans_approved'] + s['total_loans_denied']) * 100)
            if (s['total_loans_approved'] + s['total_loans_denied']) > 0 else 0
            for s in yearly_stats
        ]
        fig.add_trace(
            go.Scatter(
                x=years, y=approval_rate,
                mode='lines+markers',
                name='Approval Rate (%)',
                line=dict(color='#0ea5e9', width=3),
                marker=dict(size=8)
            ),
            row=4, col=2
        )

        # Row 5, Col 1: Energy Savings + Feed-in Revenue (Stacked)
        fig.add_trace(
            go.Scatter(
                x=years, y=energy_savings,
                mode='lines',
                name='Energy Savings',
                fill='tozeroy',
                line=dict(color='#fbbf24', width=2),
                stackgroup='one'
            ),
            row=5, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=years, y=feed_in_revenue,
                mode='lines',
                name='Feed-in Revenue',
                fill='tonexty',
                line=dict(color='#10b981', width=2),
                stackgroup='one'
            ),
            row=5, col=1
        )

        # Row 5, Col 2: Average Energy Savings per Installation
        fig.add_trace(
            go.Scatter(
                x=years, y=avg_energy_savings,
                mode='lines+markers',
                name='Avg Savings (€)',
                line=dict(color='#f59e0b', width=3),
                marker=dict(size=8),
                fill='tozeroy'
            ),
            row=5, col=2
        )

        # Update axes
        fig.update_xaxes(title_text="Year", row=5, col=1)
        fig.update_xaxes(title_text="Year", row=5, col=2)
        fig.update_yaxes(title_text="Adoption Rate (%)", row=1, col=1)
        fig.update_yaxes(title_text="Capacity (kW)", row=1, col=2)
        fig.update_yaxes(title_text="Count", row=2, col=1)
        fig.update_yaxes(title_text="Default Rate (%)", row=2, col=2)
        fig.update_yaxes(title_text="Subsidy Rate (%)", row=3, col=1)
        fig.update_yaxes(title_text="Spending (€)", row=3, col=2)
        fig.update_yaxes(title_text="Landowners", row=4, col=1)
        fig.update_yaxes(title_text="Approval Rate (%)", row=4, col=2)
        fig.update_yaxes(title_text="Annual Benefit (€)", row=5, col=1)
        fig.update_yaxes(title_text="Avg Savings (€)", row=5, col=2)

        # Update barmode for stacked
        fig.update_layout(barmode='group')

        fig.update_layout(
            height=1750,  # Increased from 1400 to accommodate 5th row
            showlegend=True,
            title_text=f"GCP Simulation Results - {scenario_display} | {policy_scenario.replace('_', ' ').title()}",
            title_x=0.5,
            hovermode='x unified',
            template='plotly_white'
        )

        # Save
        output_file = self.output_dir / f"{scenario}_{policy_scenario}_time_series.html"
        fig.write_html(str(output_file))

        return str(output_file)

    def create_policy_comparison_charts(self,
                                       results_by_policy: Dict,
                                       scenario: str) -> str:
        """
        Create comparison charts across policy scenarios.

        Args:
            results_by_policy: Dict mapping policy_scenario -> results
            scenario: Climate scenario (rcp26/rcp45/rcp85)

        Returns:
            Path to saved HTML file
        """
        # Get user-friendly scenario name
        scenario_display = get_scenario_display_name(scenario)

        policy_scenarios = list(results_by_policy.keys())
        policy_labels = [p.replace('_', ' ').title() for p in policy_scenarios]

        # Calculate final year metrics for each policy
        final_adoption_rates = []
        final_pv_capacities = []
        final_subsidy_spending = []
        final_default_rates = []
        avg_approval_rates = []

        for policy in policy_scenarios:
            stats = results_by_policy[policy]['yearly_stats']
            if stats:
                final_stats = stats[-1]
                final_adoption_rates.append(final_stats['pv_adoption_rate'] * 100)
                final_pv_capacities.append(final_stats['total_pv_capacity_kw'])
                final_subsidy_spending.append(final_stats['total_subsidy_spending'])
                final_default_rates.append(final_stats['avg_default_rate'] * 100)

                # Calculate average approval rate over all years
                avg_approval = sum([
                    (s['total_loans_approved'] / (s['total_loans_approved'] + s['total_loans_denied']))
                    if (s['total_loans_approved'] + s['total_loans_denied']) > 0 else 0
                    for s in stats
                ]) / len(stats) * 100
                avg_approval_rates.append(avg_approval)

        # Create subplots
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=(
                'Final PV Adoption Rate (%)',
                'Total PV Capacity (kW)',
                'Total Subsidy Spending (€)',
                'Final Default Rate (%)',
                'Avg Loan Approval Rate (%)',
                'Cost per Adoption (€)'
            ),
            vertical_spacing=0.25,
            horizontal_spacing=0.12
        )

        colors = ['#3b82f6', '#8b5cf6', '#ec4899']  # Blue, Purple, Pink

        # Chart 1: Final Adoption Rate
        fig.add_trace(
            go.Bar(
                x=policy_labels,
                y=final_adoption_rates,
                marker_color=colors,
                text=[f'{v:.1f}%' for v in final_adoption_rates],
                textposition='inside',
                textfont=dict(size=14, color='white', family='Arial'),
                name='Adoption Rate'
            ),
            row=1, col=1
        )

        # Chart 2: Total PV Capacity
        fig.add_trace(
            go.Bar(
                x=policy_labels,
                y=final_pv_capacities,
                marker_color=colors,
                text=[f'{v:,.0f} kW' for v in final_pv_capacities],
                textposition='inside',
                textfont=dict(size=14, color='white', family='Arial'),
                name='Capacity'
            ),
            row=1, col=2
        )

        # Chart 3: Subsidy Spending
        fig.add_trace(
            go.Bar(
                x=policy_labels,
                y=final_subsidy_spending,
                marker_color=colors,
                text=[f'€{v:,.0f}' for v in final_subsidy_spending],
                textposition='inside',
                textfont=dict(size=14, color='white', family='Arial'),
                name='Spending'
            ),
            row=1, col=3
        )

        # Chart 4: Default Rate
        fig.add_trace(
            go.Bar(
                x=policy_labels,
                y=final_default_rates,
                marker_color=colors,
                text=[f'{v:.1f}%' for v in final_default_rates],
                textposition='inside',
                textfont=dict(size=14, color='white', family='Arial'),
                name='Default Rate'
            ),
            row=2, col=1
        )

        # Chart 5: Approval Rate
        fig.add_trace(
            go.Bar(
                x=policy_labels,
                y=avg_approval_rates,
                marker_color=colors,
                text=[f'{v:.1f}%' for v in avg_approval_rates],
                textposition='inside',
                textfont=dict(size=14, color='white', family='Arial'),
                name='Approval Rate'
            ),
            row=2, col=2
        )

        # Chart 6: Cost per Adoption (Efficiency)
        n_landowners = results_by_policy[policy_scenarios[0]].get('model').n_landowners
        cost_per_adoption = []
        for i, policy in enumerate(policy_scenarios):
            adoption_rate = final_adoption_rates[i] / 100
            spending = final_subsidy_spending[i]
            n_adopters = adoption_rate * n_landowners
            cost = spending / n_adopters if n_adopters > 0 else 0
            cost_per_adoption.append(cost)

        fig.add_trace(
            go.Bar(
                x=policy_labels,
                y=cost_per_adoption,
                marker_color=colors,
                text=[f'€{v:,.0f}' for v in cost_per_adoption],
                textposition='inside',
                textfont=dict(size=14, color='white', family='Arial'),
                name='Cost/Adoption'
            ),
            row=2, col=3
        )

        # Update axes
        fig.update_yaxes(title_text="Adoption (%)", row=1, col=1)
        fig.update_yaxes(title_text="Capacity (kW)", row=1, col=2)
        fig.update_yaxes(title_text="Spending (€)", row=1, col=3)
        fig.update_yaxes(title_text="Default (%)", row=2, col=1)
        fig.update_yaxes(title_text="Approval (%)", row=2, col=2)
        fig.update_yaxes(title_text="Cost (€)", row=2, col=3)

        fig.update_layout(
            height=900,
            showlegend=False,
            title_text=f"Policy Scenario Comparison - {scenario_display}",
            title_x=0.5,
            template='plotly_white'
        )

        # Save
        output_file = self.output_dir / f"{scenario}_policy_comparison.html"
        fig.write_html(str(output_file))

        return str(output_file)

    def create_feedback_loop_chart(self,
                                   policy_history: List[Dict],
                                   yearly_stats: List[Dict],
                                   scenario: str,
                                   policy_scenario: str) -> str:
        """
        Create enhanced policy feedback loop visualization (GCP-16 Full Compliance).

        Shows bidirectional feedback:
        - Policy → Financial Institutions → PV Adoption (downward flow)
        - PV Adoption → Financial Institutions → Policy (upward flow)

        Args:
            policy_history: List of policy state dicts over time (from PolicymakerAgent)
            yearly_stats: List of yearly statistics (includes FI temporal metrics)
            scenario: Climate scenario
            policy_scenario: Policy scenario

        Returns:
            Path to saved HTML file
        """
        if not policy_history or not yearly_stats:
            return None

        # Get user-friendly scenario name
        scenario_display = get_scenario_display_name(scenario)

        # Extract policy metrics
        years = [h['year'] for h in policy_history]
        subsidy_rates = [h['pv_subsidy_rate'] * 100 for h in policy_history]
        loan_rates = [h['loan_rate'] * 100 for h in policy_history]
        adoption_rates = [h['adoption_rate'] * 100 for h in policy_history]
        default_rates = [h['default_rate'] * 100 for h in policy_history]
        subsidy_spending = [h['subsidy_spending'] for h in policy_history]

        # Extract financial institution metrics from yearly_stats (GCP-16 compliance)
        fi_approval_rates = [s.get('avg_approval_rate', 0.0) * 100 for s in yearly_stats]
        fi_portfolio_risk = [s.get('avg_portfolio_risk_score', 0.0) * 100 for s in yearly_stats]
        fi_credit_thresholds = [s.get('avg_credit_score_threshold', 0.0) for s in yearly_stats]
        fi_active_loans = [s.get('total_active_loans', 0) for s in yearly_stats]
        fi_loan_volume = [s.get('total_loan_volume', 0.0) for s in yearly_stats]

        # Create enhanced subplots (4 rows x 3 cols = 12 charts)
        fig = make_subplots(
            rows=4, cols=3,
            subplot_titles=(
                # Row 1: Policy Adjustments
                'Policy: Subsidy Rate (%)',
                'Policy: Loan Interest Rate (%)',
                'PV Adoption Rate (%)',
                # Row 2: Financial Institution Response
                'FI Response: Loan Approval Rate (%)',
                'FI Response: Portfolio Risk Score (%)',
                'FI Response: Credit Score Threshold',
                # Row 3: Loan Portfolio Dynamics
                'Active Loan Portfolio Count',
                'Total Loan Volume (€)',
                'Default Rate (%)',
                # Row 4: Feedback Effectiveness
                'Subsidy Spending (€)',
                'Subsidy vs Adoption Correlation',
                'Risk vs Default Correlation'
            ),
            vertical_spacing=0.08,
            horizontal_spacing=0.10,
            specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]]
        )

        # ===== ROW 1: POLICY ADJUSTMENTS =====

        # Chart 1: Subsidy Rate
        fig.add_trace(
            go.Scatter(
                x=years, y=subsidy_rates,
                mode='lines+markers',
                name='Subsidy Rate',
                line=dict(color='#8b5cf6', width=3),
                marker=dict(size=8),
                showlegend=False
            ),
            row=1, col=1
        )

        # Chart 2: Loan Interest Rate
        fig.add_trace(
            go.Scatter(
                x=years, y=loan_rates,
                mode='lines+markers',
                name='Loan Rate',
                line=dict(color='#ec4899', width=3),
                marker=dict(size=8),
                showlegend=False
            ),
            row=1, col=2
        )

        # Chart 3: PV Adoption Rate Response
        fig.add_trace(
            go.Scatter(
                x=years, y=adoption_rates,
                mode='lines+markers',
                name='Adoption Rate',
                line=dict(color='#22c55e', width=3),
                marker=dict(size=8),
                fill='tozeroy',
                showlegend=False
            ),
            row=1, col=3
        )

        # ===== ROW 2: FINANCIAL INSTITUTION RESPONSE (GCP-16 COMPLIANCE) =====

        # Chart 4: FI Loan Approval Rate
        fig.add_trace(
            go.Scatter(
                x=years, y=fi_approval_rates,
                mode='lines+markers',
                name='Approval Rate',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=8),
                showlegend=False
            ),
            row=2, col=1
        )

        # Chart 5: FI Portfolio Risk Score
        fig.add_trace(
            go.Scatter(
                x=years, y=fi_portfolio_risk,
                mode='lines+markers',
                name='Risk Score',
                line=dict(color='#f59e0b', width=3),
                marker=dict(size=8),
                showlegend=False
            ),
            row=2, col=2
        )

        # Chart 6: FI Credit Score Threshold
        fig.add_trace(
            go.Scatter(
                x=years, y=fi_credit_thresholds,
                mode='lines+markers',
                name='Credit Threshold',
                line=dict(color='#06b6d4', width=3),
                marker=dict(size=8),
                showlegend=False
            ),
            row=2, col=3
        )

        # ===== ROW 3: LOAN PORTFOLIO DYNAMICS (GCP-16 COMPLIANCE) =====

        # Chart 7: Active Loan Portfolio
        fig.add_trace(
            go.Scatter(
                x=years, y=fi_active_loans,
                mode='lines+markers',
                name='Active Loans',
                line=dict(color='#10b981', width=3),
                marker=dict(size=8),
                fill='tozeroy',
                showlegend=False
            ),
            row=3, col=1
        )

        # Chart 8: Total Loan Volume
        fig.add_trace(
            go.Scatter(
                x=years, y=fi_loan_volume,
                mode='lines+markers',
                name='Loan Volume',
                line=dict(color='#14b8a6', width=3),
                marker=dict(size=8),
                fill='tozeroy',
                showlegend=False
            ),
            row=3, col=2
        )

        # Chart 9: Default Rate
        fig.add_trace(
            go.Scatter(
                x=years, y=default_rates,
                mode='lines+markers',
                name='Default Rate',
                line=dict(color='#dc2626', width=3),
                marker=dict(size=8),
                showlegend=False
            ),
            row=3, col=3
        )

        # ===== ROW 4: FEEDBACK EFFECTIVENESS (GCP-16 COMPLIANCE) =====

        # Chart 10: Subsidy Spending
        fig.add_trace(
            go.Scatter(
                x=years, y=subsidy_spending,
                mode='lines+markers',
                name='Spending',
                line=dict(color='#f59e0b', width=3),
                marker=dict(size=8),
                fill='tozeroy',
                showlegend=False
            ),
            row=4, col=1
        )

        # Chart 11: Subsidy vs Adoption Correlation (bidirectional feedback)
        fig.add_trace(
            go.Scatter(
                x=subsidy_rates, y=adoption_rates,
                mode='markers+lines',
                name='Policy-Adoption Loop',
                marker=dict(size=10, color=years, colorscale='Viridis', showscale=True,
                           colorbar=dict(title="Year", x=1.02, len=0.3, y=0.15)),
                line=dict(color='gray', width=1, dash='dot'),
                showlegend=False
            ),
            row=4, col=2
        )

        # Chart 12: Risk vs Default Correlation (FI response feedback)
        fig.add_trace(
            go.Scatter(
                x=fi_portfolio_risk, y=default_rates,
                mode='markers+lines',
                name='Risk-Default Loop',
                marker=dict(size=10, color=years, colorscale='Plasma', showscale=True,
                           colorbar=dict(title="Year", x=1.15, len=0.3, y=0.15)),
                line=dict(color='gray', width=1, dash='dot'),
                showlegend=False
            ),
            row=4, col=3
        )

        # Update axes labels (show x-axis only on bottom row)
        for col in range(1, 4):
            fig.update_xaxes(title_text="Year", row=4, col=col)

        # Y-axis labels
        fig.update_yaxes(title_text="Subsidy (%)", row=1, col=1)
        fig.update_yaxes(title_text="Loan Rate (%)", row=1, col=2)
        fig.update_yaxes(title_text="Adoption (%)", row=1, col=3)

        fig.update_yaxes(title_text="Approval (%)", row=2, col=1)
        fig.update_yaxes(title_text="Risk (%)", row=2, col=2)
        fig.update_yaxes(title_text="Threshold", row=2, col=3)

        fig.update_yaxes(title_text="Count", row=3, col=1)
        fig.update_yaxes(title_text="Volume (€)", row=3, col=2)
        fig.update_yaxes(title_text="Default (%)", row=3, col=3)

        fig.update_yaxes(title_text="Spending (€)", row=4, col=1)
        fig.update_yaxes(title_text="Adoption (%)", row=4, col=2)
        fig.update_yaxes(title_text="Default (%)", row=4, col=3)

        # Update correlation chart x-axes
        fig.update_xaxes(title_text="Subsidy Rate (%)", row=4, col=2)
        fig.update_xaxes(title_text="Portfolio Risk (%)", row=4, col=3)

        fig.update_layout(
            height=1600,
            showlegend=False,
            title_text=f"GCP-16: Policy Feedback Loop Analysis - {scenario_display} | {policy_scenario.replace('_', ' ').title()}",
            title_x=0.5,
            hovermode='closest',
            template='plotly_white'
        )

        # Save
        output_file = self.output_dir / f"{scenario}_{policy_scenario}_feedback_loop.html"
        fig.write_html(str(output_file))

        return str(output_file)

    def create_pv_installation_map(self,
                                   yearly_landowner_snapshots: List[Dict],
                                   scenario: str,
                                   policy_scenario: str) -> str:
        """
        Create Folium map showing PV installations with year selector (GCP-07).

        GCP-07 Compliance:
        - Map-based visualization of geographic distribution
        - Interactive markers showing PV installations, loan approvals, and non-adopters
        - Temporal drill-down with year selector
        - Detailed popups with installation metrics
        - Color-coded markers by adoption status

        Args:
            yearly_landowner_snapshots: List of dicts with 'year' and 'landowners' keys
            scenario: Climate scenario
            policy_scenario: Policy scenario

        Returns:
            Path to saved HTML file for PV installation map
        """
        if not yearly_landowner_snapshots:
            return None

        # Calculate map center from first year
        first_year_landowners = yearly_landowner_snapshots[0]['landowners']
        if not first_year_landowners:
            return None

        lats = [lo['lat'] for lo in first_year_landowners]
        lons = [lo['lon'] for lo in first_year_landowners]
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)

        # Get user-friendly scenario name
        scenario_display = get_scenario_display_name(scenario)

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=9,
            tiles='OpenStreetMap',
            control_scale=True
        )

        # Add basemap options
        folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
        folium.TileLayer('Esri WorldImagery', name='Satellite').add_to(m)

        # Add title
        title_html = f'''
        <div id="map-title" style="position: fixed;
                    top: 10px; left: 50px; width: 500px; height: 80px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:16px; padding: 10px">
        <b>GCP Simulation - {scenario_display} | {policy_scenario.replace('_', ' ').title()}</b><br>
        PV Installation Geographic Distribution<br>
        <span id="year-display" style="color: #22c55e; font-weight: bold;">Year: {yearly_landowner_snapshots[0]['year']}</span>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))

        # Create a FeatureGroup for each year (for markers)
        year_groups = {}
        year_group_ids = {}
        years = [str(s['year']) for s in yearly_landowner_snapshots]  # ✅ FIX: Convert all years to strings

        # GCP-07 Compliance: Track marker metadata for filtering
        markers_metadata = {}  # Format: {year: {marker_var_name: {financial_situation, area_type}}}

        for snapshot in yearly_landowner_snapshots:
            year = str(snapshot['year'])  # ✅ FIX: Ensure year is string for Folium
            landowners_year = snapshot['landowners']

            year_group = folium.FeatureGroup(
                name=f"year_{year}",
                show=True,
                overlay=True
            )

            # Add landowner markers (filter out agents in the sea)
            for lo in landowners_year:
                # Skip if location is in the sea
                if not globe.is_land(lo['lat'], lo['lon']):
                    continue
                has_pv = lo['has_pv']
                loan_approved = lo['loan_approved']

                # Determine adoption status for display
                if has_pv:
                    adoption_status = 'has_pv'
                elif loan_approved:
                    adoption_status = 'loan_approved'
                else:
                    adoption_status = 'no_pv'

                if has_pv:
                    # PV Adopter - green with bolt icon
                    marker_color = 'green'
                    icon_name = 'bolt'
                    pv_capacity = lo['pv_capacity_kw']
                    roi = lo['roi']
                    payback = lo['payback_period']

                    popup_html = f"""
                    <div style="font-family: Arial; font-size: 12px;">
                        <b>Landowner {lo['id']}</b><br>
                        Year: {year}<br>
                        Status: <b>PV Installed</b><br>
                        Capacity: {pv_capacity:.0f} kW<br>
                        ROI: {roi:.1%}<br>
                        Payback: {payback:.1f} years<br>
                        Financial Situation: {lo['financial_situation']}<br>
                        Risk Tolerance: {lo['risk_tolerance']}<br>
                        Area Type: {lo['area_type'].capitalize()}<br>
                        Annual Profit: €{lo['annual_profit']:,.0f}
                    </div>
                    """
                    tooltip_text = f"Landowner {lo['id']}: PV {pv_capacity:.0f} kW"

                elif loan_approved:
                    # Loan approved but not yet installed - orange
                    marker_color = 'orange'
                    icon_name = 'clock'

                    popup_html = f"""
                    <div style="font-family: Arial; font-size: 12px;">
                        <b>Landowner {lo['id']}</b><br>
                        Year: {year}<br>
                        Status: <b>Loan Approved</b><br>
                        Financial Situation: {lo['financial_situation']}<br>
                        Risk Tolerance: {lo['risk_tolerance']}<br>
                        Area Type: {lo['area_type'].capitalize()}<br>
                        Annual Loan Payment: €{lo['annual_loan_payment']:,.0f}
                    </div>
                    """
                    tooltip_text = f"Landowner {lo['id']}: Loan Approved"

                else:
                    # No PV - gray
                    marker_color = 'gray'
                    icon_name = 'home'

                    popup_html = f"""
                    <div style="font-family: Arial; font-size: 12px;">
                        <b>Landowner {lo['id']}</b><br>
                        Year: {year}<br>
                        Status: <b>No PV</b><br>
                        Financial Situation: {lo['financial_situation']}<br>
                        Risk Tolerance: {lo['risk_tolerance']}<br>
                        Area Type: {lo['area_type'].capitalize()}
                    </div>
                    """
                    tooltip_text = f"Landowner {lo['id']}: No PV"

                # Create marker with simple data attributes in tooltip
                marker = folium.Marker(
                    location=[lo['lat'], lo['lon']],
                    popup=folium.Popup(popup_html, max_width=250),
                    icon=folium.Icon(color=marker_color, icon=icon_name, prefix='fa'),
                    tooltip=tooltip_text
                )
                marker.add_to(year_group)

                # GCP-07 Compliance: Store marker metadata for filtering
                if year not in markers_metadata:
                    markers_metadata[year] = {}
                marker_var_name = marker.get_name()  # Get Folium's JavaScript variable name
                markers_metadata[year][marker_var_name] = {
                    'financial_situation': lo['financial_situation'],
                    'area_type': lo['area_type']
                }

            year_groups[year] = year_group
            year_group_ids[year] = year_group.get_name()
            year_group.add_to(m)

        # Add legend
        legend_html = '''
        <div style="position: fixed;
                    bottom: 50px; right: 50px; width: 220px; height: 130px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:13px; padding: 10px">
        <b>Legend</b><br>
        <i class="fa fa-bolt" style="color:green"></i> PV Installed<br>
        <i class="fa fa-clock" style="color:orange"></i> Loan Approved<br>
        <i class="fa fa-home" style="color:gray"></i> No PV
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # GCP-07 Compliance: Add filter panel
        filter_panel_html = '''
        <div id="filter-panel" style="position: fixed;
                    top: 200px; left: 50px; width: 250px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:13px; padding: 10px">
        <b>Filter Landowners (GCP-07)</b><br>
        <div style="margin-top: 10px;">
            <b style="font-size: 12px;">Financial Situation:</b><br>
            <label style="margin: 2px 0; display: block;">
                <input type="checkbox" class="filter-fs" value="poor" checked> Poor
            </label>
            <label style="margin: 2px 0; display: block;">
                <input type="checkbox" class="filter-fs" value="moderate" checked> Moderate
            </label>
            <label style="margin: 2px 0; display: block;">
                <input type="checkbox" class="filter-fs" value="wealthy" checked> Wealthy
            </label>
        </div>
        <div style="margin-top: 10px;">
            <b style="font-size: 12px;">Area Type:</b><br>
            <label style="margin: 2px 0; display: block;">
                <input type="checkbox" class="filter-area" value="urban" checked> Urban
            </label>
            <label style="margin: 2px 0; display: block;">
                <input type="checkbox" class="filter-area" value="rural" checked> Rural
            </label>
        </div>
        <button id="apply-filters" style="margin-top: 10px; width: 100%; padding: 5px;
                background-color: #22c55e; color: white; border: none; cursor: pointer;
                border-radius: 3px; font-weight: bold;">
            Apply Filters
        </button>
        <button id="clear-filters" style="margin-top: 5px; width: 100%; padding: 5px;
                background-color: #6b7280; color: white; border: none; cursor: pointer;
                border-radius: 3px;">
            Clear Filters
        </button>
        <div id="filter-counter" style="margin-top: 10px; font-size: 11px; color: #6b7280;
                    font-style: italic;">
            Showing all landowners
        </div>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(filter_panel_html))

        # Year selector with slider + Previous/Next buttons (GCP-07 compliance)
        year_selector_html = f'''
        <div style="position: fixed;
                    top: 100px; left: 50px; width: 380px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    padding: 15px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1)">
        <div style="text-align: center; margin-bottom: 10px;">
            <label style="font-weight: bold; color: #1e40af; font-size: 14px; display: block; margin-bottom: 8px;">
                Year: <span id="current-year-display" style="font-size: 18px; color: #2563eb;">{years[0]}</span>
            </label>
            <div style="display: flex; align-items: center; gap: 10px;">
                <button id="prev-year" style="background-color: #3b82f6; color: white; border: none;
                           padding: 6px 12px; cursor: pointer; border-radius: 4px;
                           font-size: 12px; font-weight: bold; transition: all 0.2s; flex-shrink: 0;">
                    ◀
                </button>
                <input type="range" id="year-slider" min="0" max="{len(years) - 1}" value="0" step="1"
                       style="flex: 1; cursor: pointer; height: 8px; -webkit-appearance: none; appearance: none;
                              background: linear-gradient(to right, #3b82f6 0%, #3b82f6 0%, #e5e7eb 0%, #e5e7eb 100%);
                              border-radius: 5px; outline: none;">
                <button id="next-year" style="background-color: #3b82f6; color: white; border: none;
                           padding: 6px 12px; cursor: pointer; border-radius: 4px;
                           font-size: 12px; font-weight: bold; transition: all 0.2s; flex-shrink: 0;">
                    ▶
                </button>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 11px; color: #6b7280; padding: 0 40px;">
                <span>{years[0]}</span>
                <span>{years[-1]}</span>
            </div>
        </div>
        </div>
        '''

        year_selector_html += '''
        <style>
            #year-slider::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #2563eb;
                cursor: pointer;
                border: 2px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }

            #year-slider::-moz-range-thumb {
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #2563eb;
                cursor: pointer;
                border: 2px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }

            #prev-year:hover:not(:disabled), #next-year:hover:not(:disabled) {
                background-color: #2563eb;
                transform: scale(1.05);
            }

            #prev-year:active:not(:disabled), #next-year:active:not(:disabled) {
                transform: scale(0.95);
            }
        </style>

        <script>
        setTimeout(function() {
            var mapElement = document.querySelector('.folium-map');
            if (mapElement) {
                var mapId = mapElement.id;
                var mapObj = window[mapId];

                if (mapObj) {
                    var yearLayers = {};
        '''

        # Add marker layer references
        for year in years:
            fg_var_name = year_group_ids[year]
            year_selector_html += f'''
                    yearLayers['{year}'] = {fg_var_name};
            '''

        # Embed markers metadata as JSON for filtering (GCP-07 compliance)
        import json
        markers_metadata_json = json.dumps(markers_metadata)
        year_selector_html += f'''
                    // GCP-07 Compliance: Marker metadata for filtering
                    var markersMetadata = {markers_metadata_json};
        '''

        year_selector_html += f'''
                    var availableYears = [{', '.join([str(y) for y in years])}];
                    var slider = document.getElementById('year-slider');
                    var prevBtn = document.getElementById('prev-year');
                    var nextBtn = document.getElementById('next-year');

                    function updateYearDisplay(yearIndex) {{
                        var selectedYear = availableYears[yearIndex];
                        document.getElementById('year-display').textContent = 'Year: ' + selectedYear;
                        document.getElementById('current-year-display').textContent = selectedYear;

                        slider.value = yearIndex;

                        // Update slider background (progress bar effect)
                        var percentage = (yearIndex / (availableYears.length - 1)) * 100;
                        slider.style.background = 'linear-gradient(to right, #3b82f6 0%, #3b82f6 ' + percentage + '%, #e5e7eb ' + percentage + '%, #e5e7eb 100%)';

                        // Update button states
                        if (yearIndex === 0) {{
                            prevBtn.disabled = true;
                            prevBtn.style.backgroundColor = '#9ca3af';
                            prevBtn.style.cursor = 'not-allowed';
                            prevBtn.style.opacity = '0.5';
                        }} else {{
                            prevBtn.disabled = false;
                            prevBtn.style.backgroundColor = '#3b82f6';
                            prevBtn.style.cursor = 'pointer';
                            prevBtn.style.opacity = '1';
                        }}

                        if (yearIndex === availableYears.length - 1) {{
                            nextBtn.disabled = true;
                            nextBtn.style.backgroundColor = '#9ca3af';
                            nextBtn.style.cursor = 'not-allowed';
                            nextBtn.style.opacity = '0.5';
                        }} else {{
                            nextBtn.disabled = false;
                            nextBtn.style.backgroundColor = '#3b82f6';
                            nextBtn.style.cursor = 'pointer';
                            nextBtn.style.opacity = '1';
                        }}
        '''

        # Remove all marker layers
        for year in years:
            year_selector_html += f'''
                        if (yearLayers['{year}'] && mapObj.hasLayer(yearLayers['{year}'])) {{
                            mapObj.removeLayer(yearLayers['{year}']);
                        }}
            '''

        year_selector_html += '''

                        // Add selected year marker layer
                        var selectedYearStr = String(selectedYear);
                        if (yearLayers[selectedYearStr] && !mapObj.hasLayer(yearLayers[selectedYearStr])) {
                            mapObj.addLayer(yearLayers[selectedYearStr]);
                        }

                        // Reapply filters after year change
                        applyFilters();
                    }

                    // GCP-07 Compliance: Filter markers by financial situation and area type
                    function applyFilters() {
                        var selectedFS = [];
                        document.querySelectorAll('.filter-fs:checked').forEach(function(cb) {
                            selectedFS.push(cb.value);
                        });

                        var selectedArea = [];
                        document.querySelectorAll('.filter-area:checked').forEach(function(cb) {
                            selectedArea.push(cb.value);
                        });

                        // Get current year from slider (yearIndex to actual year)
                        var yearIndex = parseInt(slider.value);
                        var currentYear = String(availableYears[yearIndex]);
                        var metadata = markersMetadata[currentYear];

                        if (!metadata) {
                            document.getElementById('filter-counter').textContent = 'No data for selected year';
                            return;
                        }

                        var shownCount = 0;
                        var totalCount = Object.keys(metadata).length;

                        // Iterate through markers and show/hide based on filters
                        for (var markerVar in metadata) {
                            var markerObj = window[markerVar];  // Get marker object from global scope
                            if (markerObj && markerObj.setOpacity) {
                                var meta = metadata[markerVar];
                                var showMarker = selectedFS.includes(meta.financial_situation) &&
                                               selectedArea.includes(meta.area_type);

                                if (showMarker) {
                                    markerObj.setOpacity(1);
                                    shownCount++;
                                } else {
                                    markerObj.setOpacity(0);  // Hide marker
                                }
                            }
                        }

                        document.getElementById('filter-counter').textContent =
                            'Showing ' + shownCount + ' of ' + totalCount + ' landowners';
                    }

                    // GCP-07 Compliance: Clear all filters
                    function clearFilters() {
                        // Check all checkboxes
                        document.querySelectorAll('.filter-fs, .filter-area').forEach(function(cb) {
                            cb.checked = true;
                        });

                        // Reapply filters (will show all)
                        applyFilters();
                    }
        '''

        # Hide all years except first on initial load
        for i, year in enumerate(years):
            if i > 0:
                year_selector_html += f'''
                    if (yearLayers['{year}']) {{
                        mapObj.removeLayer(yearLayers['{year}']);
                    }}
            '''

        year_selector_html += '''

                    // Event listeners for slider and buttons
                    slider.addEventListener('input', function() {
                        var yearIndex = parseInt(this.value);
                        updateYearDisplay(yearIndex);
                    });

                    prevBtn.addEventListener('click', function() {
                        var currentIndex = parseInt(slider.value);
                        if (currentIndex > 0) {
                            updateYearDisplay(currentIndex - 1);
                        }
                    });

                    nextBtn.addEventListener('click', function() {
                        var currentIndex = parseInt(slider.value);
                        if (currentIndex < availableYears.length - 1) {
                            updateYearDisplay(currentIndex + 1);
                        }
                    });

                    // GCP-07 Compliance: Attach event listeners for filter buttons
                    document.getElementById('apply-filters').addEventListener('click', function() {
                        applyFilters();
                    });

                    document.getElementById('clear-filters').addEventListener('click', function() {
                        clearFilters();
                    });

                    // Initialize on first load
                    setTimeout(function() {
                        updateYearDisplay(0);  // Initialize to first year
                        applyFilters();
                    }, 500);
                }
            }
        }, 1000);
        </script>
        '''

        m.get_root().html.add_child(folium.Element(year_selector_html))

        # Add layer control
        folium.LayerControl(
            position='topright',
            collapsed=True,
            autoZIndex=True
        ).add_to(m)

        # Save
        output_file = self.output_dir / f"{scenario}_{policy_scenario}_pv_map.html"
        m.save(str(output_file))

        return str(output_file)

    def create_pv_adoption_heatmap(self,
                                   yearly_landowner_snapshots: List[Dict],
                                   scenario: str,
                                   policy_scenario: str) -> str:
        """
        Create standalone Folium heatmap showing PV adoption density (GCP-07).

        GCP-07 Compliance:
        - Heatmap visualization highlighting areas with high/low adoption rates
        - Temporal drill-down with year selector
        - Color gradient showing adoption density
        - Spatial clustering analysis

        Args:
            yearly_landowner_snapshots: List of dicts with 'year' and 'landowners' keys
            scenario: Climate scenario
            policy_scenario: Policy scenario

        Returns:
            Path to saved HTML file for heatmap
        """
        if not yearly_landowner_snapshots:
            return None

        # Calculate map center from first year
        first_year_landowners = yearly_landowner_snapshots[0]['landowners']
        if not first_year_landowners:
            return None

        lats = [lo['lat'] for lo in first_year_landowners]
        lons = [lo['lon'] for lo in first_year_landowners]
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)

        # Get user-friendly scenario name
        scenario_display = get_scenario_display_name(scenario)

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=9,
            tiles='OpenStreetMap',
            control_scale=True
        )

        # Add basemap options
        folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
        folium.TileLayer('Esri WorldImagery', name='Satellite').add_to(m)

        # Add title
        title_html = f'''
        <div id="map-title" style="position: fixed;
                    top: 10px; left: 50px; width: 500px; height: 80px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:16px; padding: 10px">
        <b>GCP Simulation - {scenario_display} | {policy_scenario.replace('_', ' ').title()}</b><br>
        PV Adoption Density Heatmap<br>
        <span id="year-display" style="color: #22c55e; font-weight: bold;">Year: {yearly_landowner_snapshots[0]['year']}</span>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))

        # Create heatmap FeatureGroups for each year
        heatmap_groups = {}
        heatmap_group_ids = {}
        years = [str(s['year']) for s in yearly_landowner_snapshots]

        for snapshot in yearly_landowner_snapshots:
            year = str(snapshot['year'])
            landowners_year = snapshot['landowners']

            # Collect PV installation coordinates for heatmap
            heatmap_data = []

            for lo in landowners_year:
                # Skip if location is in the sea
                if not globe.is_land(lo['lat'], lo['lon']):
                    continue

                if lo['has_pv']:
                    # Add to heatmap data with weight (can use capacity for intensity)
                    weight = 1.0  # Equal weight for all installations
                    heatmap_data.append([lo['lat'], lo['lon'], weight])

            # Create heatmap layer for this year
            if heatmap_data:
                heatmap_group = folium.FeatureGroup(
                    name=f"heatmap_{year}",
                    show=True,  # First year shown by default
                    overlay=True
                )

                plugins.HeatMap(
                    heatmap_data,
                    name=f'PV Adoption Heatmap {year}',
                    min_opacity=0.3,
                    max_opacity=0.8,
                    radius=15,
                    blur=20,
                    gradient={'0.4': 'blue', '0.65': 'lime', '0.85': 'orange', '1.0': 'red'}
                ).add_to(heatmap_group)

                heatmap_groups[year] = heatmap_group
                heatmap_group_ids[year] = heatmap_group.get_name()
                heatmap_group.add_to(m)

        # Add heatmap legend
        legend_html = '''
        <div style="position: fixed;
                    bottom: 50px; right: 50px; width: 250px; height: 120px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:13px; padding: 10px">
        <b>PV Adoption Density</b><br>
        <div style="background: linear-gradient(to right, blue, lime, orange, red);
                    width: 100%; height: 20px; margin-top: 5px; margin-bottom: 5px;"></div>
        <div style="display: flex; justify-content: space-between; font-size: 11px;">
            <span>Low</span>
            <span>Medium</span>
            <span>High</span>
        </div>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # Year selector with slider + Previous/Next buttons
        year_selector_html = f'''
        <div style="position: fixed;
                    top: 100px; left: 50px; width: 380px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    padding: 15px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1)">
        <div style="text-align: center; margin-bottom: 10px;">
            <label style="font-weight: bold; color: #1e40af; font-size: 14px; display: block; margin-bottom: 8px;">
                Year: <span id="current-year-display" style="font-size: 18px; color: #2563eb;">{years[0]}</span>
            </label>
            <div style="display: flex; align-items: center; gap: 10px;">
                <button id="prev-year" style="background-color: #3b82f6; color: white; border: none;
                           padding: 6px 12px; cursor: pointer; border-radius: 4px;
                           font-size: 12px; font-weight: bold; transition: all 0.2s; flex-shrink: 0;">
                    ◀
                </button>
                <input type="range" id="year-slider" min="0" max="{len(years) - 1}" value="0" step="1"
                       style="flex: 1; cursor: pointer; height: 8px; -webkit-appearance: none; appearance: none;
                              background: linear-gradient(to right, #3b82f6 0%, #3b82f6 0%, #e5e7eb 0%, #e5e7eb 100%);
                              border-radius: 5px; outline: none;">
                <button id="next-year" style="background-color: #3b82f6; color: white; border: none;
                           padding: 6px 12px; cursor: pointer; border-radius: 4px;
                           font-size: 12px; font-weight: bold; transition: all 0.2s; flex-shrink: 0;">
                    ▶
                </button>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 11px; color: #6b7280; padding: 0 40px;">
                <span>{years[0]}</span>
                <span>{years[-1]}</span>
            </div>
        </div>
        </div>
        '''

        year_selector_html += '''
        <style>
            #year-slider::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #2563eb;
                cursor: pointer;
                border: 2px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }

            #year-slider::-moz-range-thumb {
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #2563eb;
                cursor: pointer;
                border: 2px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }

            #prev-year:hover:not(:disabled), #next-year:hover:not(:disabled) {
                background-color: #2563eb;
                transform: scale(1.05);
            }

            #prev-year:active:not(:disabled), #next-year:active:not(:disabled) {
                transform: scale(0.95);
            }
        </style>

        <script>
        setTimeout(function() {
            var mapElement = document.querySelector('.folium-map');
            if (mapElement) {
                var mapId = mapElement.id;
                var mapObj = window[mapId];

                if (mapObj) {
                    var heatmapLayers = {};
        '''

        # Add heatmap layer references
        for year in years:
            if year in heatmap_group_ids:
                heatmap_var_name = heatmap_group_ids[year]
                year_selector_html += f'''
                    heatmapLayers['{year}'] = {heatmap_var_name};
                '''

        year_selector_html += f'''
                    var availableYears = [{', '.join([str(y) for y in years])}];
                    var slider = document.getElementById('year-slider');
                    var prevBtn = document.getElementById('prev-year');
                    var nextBtn = document.getElementById('next-year');

                    function updateYearDisplay(yearIndex) {{
                        var selectedYear = availableYears[yearIndex];
                        document.getElementById('year-display').textContent = 'Year: ' + selectedYear;
                        document.getElementById('current-year-display').textContent = selectedYear;

                        slider.value = yearIndex;

                        // Update slider background (progress bar effect)
                        var percentage = (yearIndex / (availableYears.length - 1)) * 100;
                        slider.style.background = 'linear-gradient(to right, #3b82f6 0%, #3b82f6 ' + percentage + '%, #e5e7eb ' + percentage + '%, #e5e7eb 100%)';

                        // Update button states
                        if (yearIndex === 0) {{
                            prevBtn.disabled = true;
                            prevBtn.style.backgroundColor = '#9ca3af';
                            prevBtn.style.cursor = 'not-allowed';
                            prevBtn.style.opacity = '0.5';
                        }} else {{
                            prevBtn.disabled = false;
                            prevBtn.style.backgroundColor = '#3b82f6';
                            prevBtn.style.cursor = 'pointer';
                            prevBtn.style.opacity = '1';
                        }}

                        if (yearIndex === availableYears.length - 1) {{
                            nextBtn.disabled = true;
                            nextBtn.style.backgroundColor = '#9ca3af';
                            nextBtn.style.cursor = 'not-allowed';
                            nextBtn.style.opacity = '0.5';
                        }} else {{
                            nextBtn.disabled = false;
                            nextBtn.style.backgroundColor = '#3b82f6';
                            nextBtn.style.cursor = 'pointer';
                            nextBtn.style.opacity = '1';
                        }}
        '''

        # Remove all heatmap layers
        for year in years:
            year_selector_html += f'''
                        if (heatmapLayers['{year}'] && mapObj.hasLayer(heatmapLayers['{year}'])) {{
                            mapObj.removeLayer(heatmapLayers['{year}']);
                        }}
            '''

        year_selector_html += '''

                        // Add selected year heatmap layer
                        var selectedYearStr = String(selectedYear);
                        if (heatmapLayers[selectedYearStr] && !mapObj.hasLayer(heatmapLayers[selectedYearStr])) {
                            mapObj.addLayer(heatmapLayers[selectedYearStr]);
                        }
                    }
        '''

        # Hide all years except first on initial load
        for i, year in enumerate(years):
            if i > 0:
                year_selector_html += f'''
                    if (heatmapLayers['{year}']) {{
                        mapObj.removeLayer(heatmapLayers['{year}']);
                    }}
            '''

        year_selector_html += '''

                    // Event listeners for slider and buttons
                    slider.addEventListener('input', function() {
                        var yearIndex = parseInt(this.value);
                        updateYearDisplay(yearIndex);
                    });

                    prevBtn.addEventListener('click', function() {
                        var currentIndex = parseInt(slider.value);
                        if (currentIndex > 0) {
                            updateYearDisplay(currentIndex - 1);
                        }
                    });

                    nextBtn.addEventListener('click', function() {
                        var currentIndex = parseInt(slider.value);
                        if (currentIndex < availableYears.length - 1) {
                            updateYearDisplay(currentIndex + 1);
                        }
                    });

                    // Initialize on first load
                    setTimeout(function() {
                        updateYearDisplay(0);  // Initialize to first year
                    }, 500);
                }
            }
        }, 1000);
        </script>
        '''

        m.get_root().html.add_child(folium.Element(year_selector_html))

        # Add layer control
        folium.LayerControl(
            position='topright',
            collapsed=True,
            autoZIndex=True
        ).add_to(m)

        # Save
        output_file = self.output_dir / f"{scenario}_{policy_scenario}_pv_heatmap.html"
        m.save(str(output_file))

        return str(output_file)

    def create_demographic_breakdown_charts(self,
                                            yearly_stats: List[Dict],
                                            scenario: str,
                                            policy_scenario: str) -> str:
        """
        Create demographic breakdown charts for GCP-03 compliance.

        Shows PV adoption patterns by financial situation and risk tolerance,
        demonstrating demographic variations in adoption behavior.

        Args:
            yearly_stats: List of yearly statistics dicts (with demographic data)
            scenario: Climate scenario (rcp26/rcp45/rcp85)
            policy_scenario: Policy scenario (low_support/moderate_support/high_support)

        Returns:
            Path to saved HTML file
        """
        years = [s['year'] for s in yearly_stats]

        # Get user-friendly scenario name
        scenario_display = get_scenario_display_name(scenario)

        # Extract demographic data from yearly_stats
        # Each stat contains dictionaries like {'poor': 0.1, 'moderate': 0.3, 'wealthy': 0.6}
        adoption_by_fs = [s.get('adoption_by_financial_situation', {}) for s in yearly_stats]
        adoption_by_rt = [s.get('adoption_by_risk_tolerance', {}) for s in yearly_stats]
        roi_by_fs = [s.get('avg_roi_by_financial_situation', {}) for s in yearly_stats]
        payback_by_rt = [s.get('avg_payback_by_risk_tolerance', {}) for s in yearly_stats]

        # Create subplots (2 rows x 2 cols = 4 charts) - removed final year pie charts
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                f'PV Adoption Rate by Financial Situation',
                f'PV Adoption Rate by Risk Tolerance',
                f'Average ROI by Financial Situation (%)',
                f'Average Payback Period by Risk Tolerance (years)'
            ),
            vertical_spacing=0.15,
            horizontal_spacing=0.12,
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )

        # Colors for financial situations and risk tolerances
        fs_colors = {'poor': '#ef4444', 'moderate': '#f59e0b', 'wealthy': '#10b981'}
        rt_colors = {'low': '#3b82f6', 'moderate': '#8b5cf6', 'high': '#ec4899'}

        # Chart 1: Adoption by Financial Situation (time series)
        for fs, color in fs_colors.items():
            adoption_values = [stat.get(fs, 0.0) * 100 for stat in adoption_by_fs]
            fig.add_trace(
                go.Scatter(
                    x=years, y=adoption_values,
                    mode='lines+markers',
                    name=fs.capitalize(),
                    line=dict(color=color, width=3),
                    marker=dict(size=6),
                    legendgroup='fs',
                    showlegend=True
                ),
                row=1, col=1
            )

        # Chart 2: Adoption by Risk Tolerance (time series)
        for rt, color in rt_colors.items():
            adoption_values = [stat.get(rt, 0.0) * 100 for stat in adoption_by_rt]
            fig.add_trace(
                go.Scatter(
                    x=years, y=adoption_values,
                    mode='lines+markers',
                    name=f'{rt.capitalize()} Risk',
                    line=dict(color=color, width=3),
                    marker=dict(size=6),
                    legendgroup='rt',
                    showlegend=True
                ),
                row=1, col=2
            )

        # Chart 3: Average ROI by Financial Situation (time series)
        for fs, color in fs_colors.items():
            roi_values = [stat.get(fs, 0.0) for stat in roi_by_fs]
            fig.add_trace(
                go.Scatter(
                    x=years, y=roi_values,
                    mode='lines+markers',
                    name=fs.capitalize(),
                    line=dict(color=color, width=3),
                    marker=dict(size=6),
                    legendgroup='fs',
                    showlegend=False
                ),
                row=2, col=1
            )

        # Chart 4: Average Payback Period by Risk Tolerance (time series)
        for rt, color in rt_colors.items():
            payback_values = [stat.get(rt, 0.0) for stat in payback_by_rt]
            fig.add_trace(
                go.Scatter(
                    x=years, y=payback_values,
                    mode='lines+markers',
                    name=f'{rt.capitalize()} Risk',
                    line=dict(color=color, width=3),
                    marker=dict(size=6),
                    legendgroup='rt',
                    showlegend=False
                ),
                row=2, col=2
            )

        # Update axes labels
        fig.update_xaxes(title_text="Year", row=1, col=1)
        fig.update_xaxes(title_text="Year", row=1, col=2)
        fig.update_xaxes(title_text="Year", row=2, col=1)
        fig.update_xaxes(title_text="Year", row=2, col=2)

        fig.update_yaxes(title_text="Adoption Rate (%)", row=1, col=1)
        fig.update_yaxes(title_text="Adoption Rate (%)", row=1, col=2)
        fig.update_yaxes(title_text="ROI (%)", row=2, col=1)
        fig.update_yaxes(title_text="Payback Period (years)", row=2, col=2)

        fig.update_layout(
            height=800,
            showlegend=True,
            title_text=f"GCP Demographic Analysis - {scenario_display} | {policy_scenario.replace('_', ' ').title()}",
            title_x=0.5,
            hovermode='x unified',
            template='plotly_white',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1.0,
                xanchor="right",
                x=1.15
            )
        )

        # Save
        output_file = self.output_dir / f"{scenario}_{policy_scenario}_demographic_breakdown.html"
        fig.write_html(str(output_file))

        return str(output_file)


def generate_all_visualizations(results_by_policy: Dict,
                                scenario: str,
                                output_dir: str = "results/visualizations",
                                data_path: str = None) -> Dict[str, str]:
    """
    Generate all visualizations for GCP simulation results.

    Args:
        results_by_policy: Dict mapping policy_scenario -> results
        scenario: Climate scenario (rcp26/rcp45/rcp85)
        output_dir: Directory to save visualizations
        data_path: Path to GCP data directory (optional)

    Returns:
        Dict mapping visualization type -> file path
    """
    visualizer = GCPVisualizer(output_dir=output_dir, data_path=data_path)

    generated_files = {}

    print(f"\n{'='*80}")
    print("GENERATING GCP INTERACTIVE VISUALIZATIONS")
    print("="*80)

    # Time series for each policy scenario
    print("\n1. Creating time series charts...")
    for policy_scenario, results in results_by_policy.items():
        file_path = visualizer.create_time_series_charts(
            results['yearly_stats'],
            scenario,
            policy_scenario
        )
        generated_files[f'{policy_scenario}_time_series'] = file_path
        print(f"   ✅ {policy_scenario}: {file_path}")

    # Policy comparison
    print("\n2. Creating policy comparison charts...")
    file_path = visualizer.create_policy_comparison_charts(results_by_policy, scenario)
    generated_files['policy_comparison'] = file_path
    print(f"   ✅ Comparison: {file_path}")

    # Policy feedback loop (GCP-16)
    print("\n3. Creating policy feedback loop charts...")
    for policy_scenario, results in results_by_policy.items():
        model = results.get('model')
        yearly_stats = results.get('yearly_stats', [])
        if model and model.policymaker_agents and yearly_stats:
            policy_history = model.policymaker_agents[0].policy_history
            if policy_history:
                file_path = visualizer.create_feedback_loop_chart(
                    policy_history,
                    yearly_stats,
                    scenario,
                    policy_scenario
                )
                if file_path:
                    generated_files[f'{policy_scenario}_feedback_loop'] = file_path
                    print(f"   ✅ {policy_scenario} Feedback Loop: {file_path}")

    # GIS maps for each policy scenario (GCP-07)
    print("\n4. Creating GIS maps...")
    for policy_scenario, results in results_by_policy.items():
        yearly_snapshots = results.get('yearly_landowner_snapshots', [])

        if yearly_snapshots:
            # Create PV installation map (markers)
            try:
                file_path = visualizer.create_pv_installation_map(
                    yearly_snapshots,
                    scenario,
                    policy_scenario
                )
                if file_path:
                    generated_files[f'{policy_scenario}_pv_map'] = file_path
                    print(f"   ✅ {policy_scenario} PV Map: {file_path}")
            except Exception as e:
                print(f"   ⚠️  Could not create {policy_scenario} PV map: {e}")

            # Create PV adoption heatmap (separate file)
            try:
                file_path = visualizer.create_pv_adoption_heatmap(
                    yearly_snapshots,
                    scenario,
                    policy_scenario
                )
                if file_path:
                    generated_files[f'{policy_scenario}_pv_heatmap'] = file_path
                    print(f"   ✅ {policy_scenario} PV Heatmap: {file_path}")
            except Exception as e:
                print(f"   ⚠️  Could not create {policy_scenario} PV heatmap: {e}")

    # Demographic breakdown charts (GCP-03 compliance)
    print("\n5. Creating demographic breakdown charts...")
    for policy_scenario, results in results_by_policy.items():
        yearly_stats = results.get('yearly_stats', [])

        if yearly_stats:
            try:
                file_path = visualizer.create_demographic_breakdown_charts(
                    yearly_stats,
                    scenario,
                    policy_scenario
                )
                if file_path:
                    generated_files[f'{policy_scenario}_demographic_breakdown'] = file_path
                    print(f"   ✅ {policy_scenario} Demographic Breakdown: {file_path}")
            except Exception as e:
                print(f"   ⚠️  Could not create {policy_scenario} demographic breakdown: {e}")

    print(f"\n{'='*80}")
    print(f"✅ All visualizations saved to: {Path(output_dir).absolute()}")
    print("="*80)

    return generated_files


def generate_gcp_03_visualizations(results_by_policy: Dict,
                                    scenario: str,
                                    output_dir: str = "results/visualizations",
                                    data_path: str = None) -> Dict[str, str]:
    """
    Generate visualizations specifically for GCP-03 query.

    GCP-03 outputs:
    - time_series.html (PV adoption dynamics)
    - demographic_breakdown.html (adoption by financial situation/risk tolerance)
    - pv_map.html (geographic distribution with filters)

    Args:
        results_by_policy: Dict mapping policy_scenario -> results
        scenario: Climate scenario (rcp26/rcp45/rcp85)
        output_dir: Directory to save visualizations
        data_path: Path to GCP data directory (optional)

    Returns:
        Dict mapping visualization type -> file path
    """
    visualizer = GCPVisualizer(output_dir=output_dir, data_path=data_path)
    generated_files = {}

    print(f"\n{'='*80}")
    print("GENERATING GCP-03 VISUALIZATIONS")
    print("="*80)

    # Time series for each policy scenario
    print("\n1. Creating time series charts...")
    for policy_scenario, results in results_by_policy.items():
        file_path = visualizer.create_time_series_charts(
            results['yearly_stats'],
            scenario,
            policy_scenario
        )
        generated_files[f'{policy_scenario}_time_series'] = file_path
        print(f"   ✅ {policy_scenario}: {file_path}")

    # Demographic breakdown charts (GCP-03 core requirement)
    print("\n2. Creating demographic breakdown charts...")
    for policy_scenario, results in results_by_policy.items():
        yearly_stats = results.get('yearly_stats', [])

        if yearly_stats:
            try:
                file_path = visualizer.create_demographic_breakdown_charts(
                    yearly_stats,
                    scenario,
                    policy_scenario
                )
                if file_path:
                    generated_files[f'{policy_scenario}_demographic_breakdown'] = file_path
                    print(f"   ✅ {policy_scenario} Demographic Breakdown: {file_path}")
            except Exception as e:
                print(f"   ⚠️  Could not create {policy_scenario} demographic breakdown: {e}")

    # PV installation map (geographic distribution)
    print("\n3. Creating PV installation maps...")
    for policy_scenario, results in results_by_policy.items():
        yearly_snapshots = results.get('yearly_landowner_snapshots', [])

        if yearly_snapshots:
            try:
                file_path = visualizer.create_pv_installation_map(
                    yearly_snapshots,
                    scenario,
                    policy_scenario
                )
                if file_path:
                    generated_files[f'{policy_scenario}_pv_map'] = file_path
                    print(f"   ✅ {policy_scenario} PV Map: {file_path}")
            except Exception as e:
                print(f"   ⚠️  Could not create {policy_scenario} PV map: {e}")

    print(f"\n{'='*80}")
    print(f"✅ GCP-03 Visualizations saved to: {Path(output_dir).absolute()}")
    print("="*80)

    return generated_files


def generate_gcp_07_visualizations(yearly_landowner_snapshots: List[Dict],
                                    scenario: str,
                                    policy_scenario: str,
                                    output_dir: str = "results/visualizations",
                                    data_path: str = None) -> Dict[str, str]:
    """
    Generate visualizations specifically for GCP-07 query.

    GCP-07 outputs:
    - pv_map.html (interactive map with filters for demographic drill-down)
    - pv_heatmap.html (density heatmap showing adoption clustering)

    Args:
        yearly_landowner_snapshots: List of dicts with 'year' and 'landowners' keys
        scenario: Climate scenario (rcp26/rcp45/rcp85)
        policy_scenario: Policy scenario (low_support/moderate_support/high_support)
        output_dir: Directory to save visualizations
        data_path: Path to GCP data directory (optional)

    Returns:
        Dict mapping visualization type -> file path
    """
    visualizer = GCPVisualizer(output_dir=output_dir, data_path=data_path)
    generated_files = {}

    print(f"\n{'='*80}")
    print("GENERATING GCP-07 VISUALIZATIONS")
    print("="*80)

    if not yearly_landowner_snapshots:
        print("   ⚠️  No landowner snapshot data available")
        return generated_files

    # PV installation map with filters (GCP-07 core requirement)
    print("\n1. Creating PV installation map with demographic filters...")
    try:
        file_path = visualizer.create_pv_installation_map(
            yearly_landowner_snapshots,
            scenario,
            policy_scenario
        )
        if file_path:
            generated_files['pv_map'] = file_path
            print(f"   ✅ PV Installation Map (with filters): {file_path}")
    except Exception as e:
        print(f"   ⚠️  Could not create PV installation map: {e}")

    # PV adoption heatmap (GCP-07 density visualization)
    print("\n2. Creating PV adoption density heatmap...")
    try:
        file_path = visualizer.create_pv_adoption_heatmap(
            yearly_landowner_snapshots,
            scenario,
            policy_scenario
        )
        if file_path:
            generated_files['pv_heatmap'] = file_path
            print(f"   ✅ PV Adoption Heatmap: {file_path}")
    except Exception as e:
        print(f"   ⚠️  Could not create PV adoption heatmap: {e}")

    print(f"\n{'='*80}")
    print(f"✅ GCP-07 Visualizations saved to: {Path(output_dir).absolute()}")
    print("="*80)

    return generated_files


def generate_gcp_16_visualizations(results_by_policy: Dict,
                                    scenario: str,
                                    output_dir: str = "results/visualizations",
                                    data_path: str = None) -> Dict[str, str]:
    """
    Generate visualizations specifically for GCP-16 query.

    GCP-16 outputs:
    - feedback_loop.html (policy adjustment dynamics over time)
    - policy_comparison.html (multi-policy comparison if multiple policies provided)

    Args:
        results_by_policy: Dict mapping policy_scenario -> results
        scenario: Climate scenario (rcp26/rcp45/rcp85)
        output_dir: Directory to save visualizations
        data_path: Path to GCP data directory (optional)

    Returns:
        Dict mapping visualization type -> file path
    """
    visualizer = GCPVisualizer(output_dir=output_dir, data_path=data_path)
    generated_files = {}

    print(f"\n{'='*80}")
    print("GENERATING GCP-16 VISUALIZATIONS")
    print("="*80)

    # Policy feedback loop (GCP-16 core requirement)
    print("\n1. Creating policy feedback loop charts...")
    for policy_scenario, results in results_by_policy.items():
        model = results.get('model')
        yearly_stats = results.get('yearly_stats', [])
        if model and model.policymaker_agents and yearly_stats:
            policy_history = model.policymaker_agents[0].policy_history
            if policy_history:
                file_path = visualizer.create_feedback_loop_chart(
                    policy_history,
                    yearly_stats,
                    scenario,
                    policy_scenario
                )
                if file_path:
                    generated_files[f'{policy_scenario}_feedback_loop'] = file_path
                    print(f"   ✅ {policy_scenario} Feedback Loop: {file_path}")
            else:
                print(f"   ⚠️  No policy history available for {policy_scenario}")
        else:
            print(f"   ⚠️  No policymaker agents or yearly stats found for {policy_scenario}")

    # Policy comparison (if multiple policies)
    if len(results_by_policy) > 1:
        print("\n2. Creating policy comparison charts...")
        file_path = visualizer.create_policy_comparison_charts(results_by_policy, scenario)
        generated_files['policy_comparison'] = file_path
        print(f"   ✅ Policy Comparison: {file_path}")
    else:
        print("\n2. Skipping policy comparison (only one policy scenario)")

    print(f"\n{'='*80}")
    print(f"✅ GCP-16 Visualizations saved to: {Path(output_dir).absolute()}")
    print("="*80)

    return generated_files
