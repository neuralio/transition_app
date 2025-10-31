"""
MLU-07: Integrate Historical EO Data for Benchmarking

This query provides historical baseline comparison functionality:
- Loads historical EO data (ERA5 reanalysis, 1990-2020)
- Compares past vs future climate scenarios (RCP26/45/85)
- Generates benchmark reports showing percentage changes
- Creates interactive comparison visualizations
"""

import sys
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from use_cases.mlu.scripts.run_mlu_simulation import run_simulation_with_results


def query_mlu_07(
    data_path: str,
    scenario: str,
    n_years: int = 10,
    n_parcels: int = 15,
    output_dir: str = None,
    enable_multi_level: bool = True,
    n_collectives: int = 2,
    n_markets: int = 1,
    n_policies: int = 1
):
    """
    Run MLU-07: Historical EO Data Integration and Benchmarking.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        scenario: Climate scenario ('historical', 'rcp26', 'rcp45', 'rcp85')
        n_years: Number of years to simulate
        n_parcels: Number of land parcels to simulate
        output_dir: Output directory for results
        enable_multi_level: Enable multi-level ABM (collectives, markets, policies)
        n_collectives: Number of farmer collectives
        n_markets: Number of commodity markets
        n_policies: Number of policymaker agents

    Returns:
        dict: Result dictionary with status, outputs, and metrics
    """
    try:
        output_path = Path(output_dir if output_dir else f'results/mlu_07_{scenario}')
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*80}")
        print(f"🔍 MLU-07: Historical EO Data Benchmarking - {scenario.upper()}")
        print(f"{'='*80}")
        print(f"Scenario: {scenario.upper()}")
        print(f"Years: {n_years}")
        print(f"Parcels: {n_parcels}")
        print(f"Multi-level: {'Enabled' if enable_multi_level else 'Disabled'}")
        if enable_multi_level:
            print(f"  - Collectives: {n_collectives}")
            print(f"  - Markets: {n_markets}")
            print(f"  - Policymakers: {n_policies}")
        print(f"{'='*80}\n")

        # Run simulation
        print(f"🚀 Running simulation for {scenario.upper()}...")
        collector = run_simulation_with_results(
            data_path=data_path,
            scenario=scenario,
            n_years=n_years,
            n_parcels=n_parcels,
            enable_multi_level=enable_multi_level,
            n_collectives=n_collectives if enable_multi_level else 0,
            n_markets=n_markets if enable_multi_level else 0,
            n_policies=n_policies if enable_multi_level else 0
        )

        print(f"📊 Creating visualizations...")
        viz_files = []

        # Extract time-series data
        years_data = []
        land_use_counts = {'WHEAT': [], 'MAIZE': [], 'SOLAR': []}
        avg_temperatures = []
        avg_precipitation = []
        avg_lusa_scores = {'WHEAT': [], 'MAIZE': []}  # NEW: Track LUSA suitability scores

        for snapshot in collector.spatial_snapshots:
            year = snapshot['year']
            years_data.append(year)

            # Count land use by crop
            parcels = snapshot['parcels']
            wheat_count = sum(1 for p in parcels if p.get('current_crop') == 'WHEAT')
            maize_count = sum(1 for p in parcels if p.get('current_crop') == 'MAIZE')
            solar_count = sum(1 for p in parcels if p.get('land_use') == 'solar_pv')

            land_use_counts['WHEAT'].append(wheat_count)
            land_use_counts['MAIZE'].append(maize_count)
            land_use_counts['SOLAR'].append(solar_count)

            # Collect environmental data
            temps = [p.get('temperature', 0) for p in parcels if p.get('temperature')]
            precip = [p.get('precipitation', 0) for p in parcels if p.get('precipitation')]

            avg_temperatures.append(sum(temps) / len(temps) if temps else 0)
            avg_precipitation.append(sum(precip) / len(precip) if precip else 0)

            # NEW: Collect LUSA suitability scores (from suitability_scores dict)
            wheat_lusa = [p['suitability_scores']['WHEAT'] for p in parcels if 'suitability_scores' in p and 'WHEAT' in p['suitability_scores']]
            maize_lusa = [p['suitability_scores']['MAIZE'] for p in parcels if 'suitability_scores' in p and 'MAIZE' in p['suitability_scores']]

            avg_lusa_scores['WHEAT'].append(sum(wheat_lusa) / len(wheat_lusa) if wheat_lusa else 0)
            avg_lusa_scores['MAIZE'].append(sum(maize_lusa) / len(maize_lusa) if maize_lusa else 0)

        # VISUALIZATION 1: Land Use Evolution with Climate Context
        print(f"   Creating land use evolution with climate context...")

        fig1 = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Land Use Evolution', 'Climate Variables'),
            vertical_spacing=0.12,
            row_heights=[0.6, 0.4]
        )

        # Top: Land use stacked area
        colors = {
            'WHEAT': '#3b82f6',   # Blue
            'MAIZE': '#f97316',   # Orange
            'SOLAR': '#eab308'    # Yellow
        }

        fig1.add_trace(go.Scatter(
            x=years_data,
            y=land_use_counts['WHEAT'],
            mode='lines',
            name='WHEAT',
            line=dict(width=0),
            stackgroup='one',
            fillcolor=colors['WHEAT'],
            hovertemplate='<b>WHEAT</b><br>Year: %{x}<br>Parcels: %{y}<extra></extra>'
        ), row=1, col=1)

        fig1.add_trace(go.Scatter(
            x=years_data,
            y=land_use_counts['MAIZE'],
            mode='lines',
            name='MAIZE',
            line=dict(width=0),
            stackgroup='one',
            fillcolor=colors['MAIZE'],
            hovertemplate='<b>MAIZE</b><br>Year: %{x}<br>Parcels: %{y}<extra></extra>'
        ), row=1, col=1)

        fig1.add_trace(go.Scatter(
            x=years_data,
            y=land_use_counts['SOLAR'],
            mode='lines',
            name='SOLAR PV',
            line=dict(width=0),
            stackgroup='one',
            fillcolor=colors['SOLAR'],
            hovertemplate='<b>SOLAR PV</b><br>Year: %{x}<br>Parcels: %{y}<extra></extra>'
        ), row=1, col=1)

        # Bottom: Climate variables
        fig1.add_trace(go.Scatter(
            x=years_data,
            y=avg_temperatures,
            mode='lines',
            name='Temperature (°C)',
            line=dict(color='#ef4444', width=2),
            hovertemplate='<b>Temperature</b><br>Year: %{x}<br>Temp: %{y:.1f}°C<extra></extra>'
        ), row=2, col=1)

        fig1.add_trace(go.Scatter(
            x=years_data,
            y=avg_precipitation,
            mode='lines',
            name='Precipitation (mm)',
            line=dict(color='#3b82f6', width=2),
            yaxis='y2',
            hovertemplate='<b>Precipitation</b><br>Year: %{x}<br>Precip: %{y:.0f}mm<extra></extra>'
        ), row=2, col=1)

        scenario_label = "Historical Baseline (1990-2020)" if scenario == 'historical' else f"Future Projection ({scenario.upper()})"

        fig1.update_layout(
            title=dict(
                text=f'Land Use Evolution with Climate Context - {scenario_label}<br><sub>How environmental conditions influence land use decisions</sub>',
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            hovermode='x unified',
            width=1200,
            height=800,
            margin=dict(l=60, r=60, t=120, b=60),
            legend=dict(
                x=0.01,
                y=0.99,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#e2e8f0',
                borderwidth=1
            )
        )

        fig1.update_xaxes(title_text="Year", row=2, col=1, gridcolor='#e2e8f0')
        fig1.update_yaxes(title_text="Number of Parcels", row=1, col=1, gridcolor='#e2e8f0')
        fig1.update_yaxes(title_text="Temperature (°C)", row=2, col=1, gridcolor='#e2e8f0')

        evolution_file = output_path / 'land_use_climate_evolution.html'
        fig1.write_html(str(evolution_file))
        viz_files.append(evolution_file)
        print(f"      ✅ {evolution_file.name}")

        # VISUALIZATION 2: Historical Summary Statistics
        print(f"   Creating summary statistics...")

        fig2 = go.Figure()

        categories = ['WHEAT', 'MAIZE', 'SOLAR']
        final_counts = [
            land_use_counts['WHEAT'][-1],
            land_use_counts['MAIZE'][-1],
            land_use_counts['SOLAR'][-1]
        ]

        fig2.add_trace(go.Bar(
            x=categories,
            y=final_counts,
            marker=dict(
                color=[colors[cat] for cat in categories],
                line=dict(color='#ffffff', width=2)
            ),
            text=final_counts,
            textposition='outside',
            textfont=dict(size=16, color='#0f172a', family='Inter, sans-serif'),
            hovertemplate='<b>%{x}</b><br>Final Parcels: %{y}<extra></extra>'
        ))

        fig2.update_layout(
            title=dict(
                text=f'Final Land Use Distribution - {scenario_label}<br><sub>Year {years_data[-1]}</sub>',
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            xaxis=dict(
                title=dict(text='Land Use Type', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b')
            ),
            yaxis=dict(
                title=dict(text='Number of Parcels', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b'),
                gridcolor='#e2e8f0'
            ),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            width=800,
            height=600,
            margin=dict(l=60, r=40, t=100, b=60)
        )

        summary_file = output_path / 'final_distribution.html'
        fig2.write_html(str(summary_file))
        viz_files.append(summary_file)
        print(f"      ✅ {summary_file.name}")

        # VISUALIZATION 3: LUSA Suitability Scores Evolution (KEY REQUIREMENT!)
        print(f"   Creating LUSA suitability scores evolution...")

        fig3 = go.Figure()

        # WHEAT suitability
        fig3.add_trace(go.Scatter(
            x=years_data,
            y=avg_lusa_scores['WHEAT'],
            mode='lines+markers',
            name='WHEAT Suitability',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=6, color='#3b82f6'),
            hovertemplate='<b>WHEAT</b><br>Year: %{x}<br>Suitability: %{y:.2f}<extra></extra>'
        ))

        # MAIZE suitability
        fig3.add_trace(go.Scatter(
            x=years_data,
            y=avg_lusa_scores['MAIZE'],
            mode='lines+markers',
            name='MAIZE Suitability',
            line=dict(color='#f97316', width=3),
            marker=dict(size=6, color='#f97316'),
            hovertemplate='<b>MAIZE</b><br>Year: %{x}<br>Suitability: %{y:.2f}<extra></extra>'
        ))

        fig3.update_layout(
            title=dict(
                text=f'Land Suitability Scores Evolution - {scenario_label}<br><sub>AI-predicted suitability from LUSA model (higher = more suitable)</sub>',
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            xaxis=dict(
                title=dict(text='Year', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b'),
                gridcolor='#e2e8f0'
            ),
            yaxis=dict(
                title=dict(text='LUSA Suitability Score (0-1)', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b'),
                gridcolor='#e2e8f0',
                range=[0, 1]
            ),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            hovermode='x unified',
            width=1000,
            height=600,
            margin=dict(l=60, r=40, t=100, b=60),
            legend=dict(
                x=0.01,
                y=0.99,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#e2e8f0',
                borderwidth=1
            )
        )

        lusa_file = output_path / 'lusa_suitability_evolution.html'
        fig3.write_html(str(lusa_file))
        viz_files.append(lusa_file)
        print(f"      ✅ {lusa_file.name}")

        # Print summary
        print(f"\n{'='*80}")
        print(f"✅ MLU-07 COMPLETE - {scenario.upper()}")
        print(f"{'='*80}")
        print(f"Output: {output_path}")
        print(f"\nVisualizations:")
        for f in viz_files:
            print(f"  - {f.name}")
        print(f"\nKey Metrics:")
        print(f"  - Total parcels: {n_parcels}")
        print(f"  - Simulation period: {years_data[0]}-{years_data[-1]}")
        print(f"  - Final land use: {final_counts[0]} WHEAT, {final_counts[1]} MAIZE, {final_counts[2]} SOLAR")
        print(f"  - Avg temperature: {sum(avg_temperatures)/len(avg_temperatures):.1f}°C")
        print(f"  - Avg precipitation: {sum(avg_precipitation)/len(avg_precipitation):.0f}mm")
        print(f"{'='*80}\n")

        return {
            'status': 'success',
            'scenario': scenario.upper(),
            'n_years': n_years,
            'n_parcels': n_parcels,
            'output_dir': str(output_path.absolute()),
            'visualizations': [str(f.absolute()) for f in viz_files],
            'final_land_use': {
                'WHEAT': final_counts[0],
                'MAIZE': final_counts[1],
                'SOLAR': final_counts[2]
            },
            'climate_metrics': {
                'avg_temperature': sum(avg_temperatures) / len(avg_temperatures),
                'avg_precipitation': sum(avg_precipitation) / len(avg_precipitation),
                'temp_trend': avg_temperatures[-1] - avg_temperatures[0],
                'precip_trend': avg_precipitation[-1] - avg_precipitation[0]
            },
            'lusa_metrics': {
                'avg_wheat_suitability': sum(avg_lusa_scores['WHEAT']) / len(avg_lusa_scores['WHEAT']) if avg_lusa_scores['WHEAT'] else 0,
                'avg_maize_suitability': sum(avg_lusa_scores['MAIZE']) / len(avg_lusa_scores['MAIZE']) if avg_lusa_scores['MAIZE'] else 0,
                'wheat_trend': avg_lusa_scores['WHEAT'][-1] - avg_lusa_scores['WHEAT'][0] if avg_lusa_scores['WHEAT'] else 0,
                'maize_trend': avg_lusa_scores['MAIZE'][-1] - avg_lusa_scores['MAIZE'][0] if avg_lusa_scores['MAIZE'] else 0
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'message': str(e),
            'scenario': scenario
        }


def create_historical_comparison(results_by_scenario: dict, output_dir: str = None):
    """
    Create comparison visualizations between historical and future scenarios.

    Args:
        results_by_scenario: Dict mapping scenario name -> result dict
        output_dir: Output directory for comparison charts

    Returns:
        List of generated visualization files
    """
    if not results_by_scenario:
        return []

    output_path = Path(output_dir if output_dir else 'results/mlu_07_comparison')
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"📊 Creating Historical vs Future Comparison Charts")
    print(f"{'='*80}")

    viz_files = []
    colors = {
        'historical': '#64748b',  # Gray (baseline)
        'rcp26': '#22c55e',       # Green (low emissions)
        'rcp45': '#f59e0b',       # Orange (medium)
        'rcp85': '#ef4444'        # Red (high emissions)
    }

    # Extract data from all scenarios
    scenarios_data = {}
    for scenario, result in results_by_scenario.items():
        if result.get('status') == 'success':
            scenarios_data[scenario] = result

    if not scenarios_data:
        print("   ⚠️  No successful scenarios to compare")
        return []

    # COMPARISON 1: Final Land Use - Historical vs Future
    print(f"   Creating land use comparison (historical vs future)...")

    fig1 = go.Figure()

    categories = ['WHEAT', 'MAIZE', 'SOLAR']
    cat_colors = {
        'WHEAT': '#3b82f6',
        'MAIZE': '#f97316',
        'SOLAR': '#eab308'
    }

    for category in categories:
        counts = []
        scenario_labels = []
        for scenario in ['historical', 'rcp26', 'rcp45', 'rcp85']:
            if scenario in scenarios_data:
                count = scenarios_data[scenario]['final_land_use'].get(category, 0)
                counts.append(count)
                label = "Historical (Baseline)" if scenario == 'historical' else scenario.upper()
                scenario_labels.append(label)

        fig1.add_trace(go.Bar(
            name=category,
            x=scenario_labels,
            y=counts,
            marker=dict(color=cat_colors[category]),
            text=counts,
            textposition='outside',
            hovertemplate=f'<b>{category}</b><br>Count: %{{y}}<extra></extra>'
        ))

    fig1.update_layout(
        title=dict(
            text='Land Use Comparison: Historical Baseline vs Future Scenarios<br><sub>How climate change affects land allocation</sub>',
            font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
        ),
        xaxis=dict(
            title=dict(text='Scenario', font=dict(size=14, color='#475569')),
            tickfont=dict(size=12, color='#64748b')
        ),
        yaxis=dict(
            title=dict(text='Number of Parcels', font=dict(size=14, color='#475569')),
            tickfont=dict(size=12, color='#64748b'),
            gridcolor='#e2e8f0'
        ),
        barmode='group',
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        width=1000,
        height=600,
        margin=dict(l=60, r=40, t=100, b=60),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#e2e8f0',
            borderwidth=1
        )
    )

    land_use_comparison_file = output_path / 'historical_vs_future_land_use.html'
    fig1.write_html(str(land_use_comparison_file))
    viz_files.append(land_use_comparison_file)
    print(f"      ✅ {land_use_comparison_file.name}")

    # COMPARISON 2: Climate Metrics - Historical vs Future
    if 'historical' in scenarios_data:
        print(f"   Creating climate metrics comparison...")

        fig2 = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Temperature Change', 'Precipitation Change'),
            horizontal_spacing=0.15
        )

        # Temperature comparison
        historical_temp = scenarios_data['historical']['climate_metrics']['avg_temperature']
        temp_changes = []
        temp_labels = []

        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in scenarios_data:
                future_temp = scenarios_data[scenario]['climate_metrics']['avg_temperature']
                temp_change = future_temp - historical_temp
                temp_changes.append(temp_change)
                temp_labels.append(scenario.upper())

        fig2.add_trace(go.Bar(
            x=temp_labels,
            y=temp_changes,
            marker=dict(
                color=[colors[s.lower()] for s in temp_labels],
                line=dict(color='#ffffff', width=2)
            ),
            text=[f"+{t:.1f}°C" if t >= 0 else f"{t:.1f}°C" for t in temp_changes],
            textposition='outside',
            textfont=dict(size=14, color='#0f172a', family='Inter, sans-serif'),
            hovertemplate='<b>%{x}</b><br>Change: %{y:.1f}°C<extra></extra>',
            showlegend=False
        ), row=1, col=1)

        # Precipitation comparison
        historical_precip = scenarios_data['historical']['climate_metrics']['avg_precipitation']
        precip_changes = []

        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in scenarios_data:
                future_precip = scenarios_data[scenario]['climate_metrics']['avg_precipitation']
                precip_change = future_precip - historical_precip
                precip_changes.append(precip_change)

        fig2.add_trace(go.Bar(
            x=temp_labels,
            y=precip_changes,
            marker=dict(
                color=[colors[s.lower()] for s in temp_labels],
                line=dict(color='#ffffff', width=2)
            ),
            text=[f"+{p:.0f}mm" if p >= 0 else f"{p:.0f}mm" for p in precip_changes],
            textposition='outside',
            textfont=dict(size=14, color='#0f172a', family='Inter, sans-serif'),
            hovertemplate='<b>%{x}</b><br>Change: %{y:.0f}mm<extra></extra>',
            showlegend=False
        ), row=1, col=2)

        fig2.update_layout(
            title=dict(
                text='Climate Change from Historical Baseline<br><sub>Average temperature and precipitation shifts</sub>',
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            width=1200,
            height=600,
            margin=dict(l=60, r=60, t=120, b=60)
        )

        fig2.update_xaxes(title_text="Scenario", row=1, col=1, tickfont=dict(size=12, color='#64748b'))
        fig2.update_xaxes(title_text="Scenario", row=1, col=2, tickfont=dict(size=12, color='#64748b'))
        fig2.update_yaxes(title_text="Temperature Change (°C)", row=1, col=1, gridcolor='#e2e8f0')
        fig2.update_yaxes(title_text="Precipitation Change (mm)", row=1, col=2, gridcolor='#e2e8f0')

        climate_comparison_file = output_path / 'historical_vs_future_climate.html'
        fig2.write_html(str(climate_comparison_file))
        viz_files.append(climate_comparison_file)
        print(f"      ✅ {climate_comparison_file.name}")

    # COMPARISON 3: LUSA Suitability Changes (KEY REQUIREMENT!)
    if 'historical' in scenarios_data:
        print(f"   Creating LUSA suitability comparison...")

        fig3 = make_subplots(
            rows=1, cols=2,
            subplot_titles=('WHEAT Suitability Change', 'MAIZE Suitability Change'),
            horizontal_spacing=0.15
        )

        # WHEAT suitability comparison
        historical_wheat = scenarios_data['historical']['lusa_metrics']['avg_wheat_suitability']
        wheat_changes = []
        wheat_labels = []

        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in scenarios_data:
                future_wheat = scenarios_data[scenario]['lusa_metrics']['avg_wheat_suitability']
                wheat_change = future_wheat - historical_wheat
                wheat_changes.append(wheat_change)
                wheat_labels.append(scenario.upper())

        fig3.add_trace(go.Bar(
            x=wheat_labels,
            y=wheat_changes,
            marker=dict(
                color=[colors[s.lower()] for s in wheat_labels],
                line=dict(color='#ffffff', width=2)
            ),
            text=[f"{w:+.3f}" for w in wheat_changes],
            textposition='outside',
            textfont=dict(size=14, color='#0f172a', family='Inter, sans-serif'),
            hovertemplate='<b>%{x}</b><br>Change: %{y:.3f}<extra></extra>',
            showlegend=False
        ), row=1, col=1)

        # MAIZE suitability comparison
        historical_maize = scenarios_data['historical']['lusa_metrics']['avg_maize_suitability']
        maize_changes = []

        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in scenarios_data:
                future_maize = scenarios_data[scenario]['lusa_metrics']['avg_maize_suitability']
                maize_change = future_maize - historical_maize
                maize_changes.append(maize_change)

        fig3.add_trace(go.Bar(
            x=wheat_labels,
            y=maize_changes,
            marker=dict(
                color=[colors[s.lower()] for s in wheat_labels],
                line=dict(color='#ffffff', width=2)
            ),
            text=[f"{m:+.3f}" for m in maize_changes],
            textposition='outside',
            textfont=dict(size=14, color='#0f172a', family='Inter, sans-serif'),
            hovertemplate='<b>%{x}</b><br>Change: %{y:.3f}<extra></extra>',
            showlegend=False
        ), row=1, col=2)

        fig3.update_layout(
            title=dict(
                text='Land Suitability Changes from Historical Baseline<br><sub>How climate change affects crop suitability (LUSA predictions)</sub>',
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            width=1200,
            height=600,
            margin=dict(l=60, r=60, t=120, b=60)
        )

        fig3.update_xaxes(title_text="Scenario", row=1, col=1, tickfont=dict(size=12, color='#64748b'))
        fig3.update_xaxes(title_text="Scenario", row=1, col=2, tickfont=dict(size=12, color='#64748b'))
        fig3.update_yaxes(title_text="Suitability Change (Δ)", row=1, col=1, gridcolor='#e2e8f0')
        fig3.update_yaxes(title_text="Suitability Change (Δ)", row=1, col=2, gridcolor='#e2e8f0')

        lusa_comparison_file = output_path / 'historical_vs_future_lusa.html'
        fig3.write_html(str(lusa_comparison_file))
        viz_files.append(lusa_comparison_file)
        print(f"      ✅ {lusa_comparison_file.name}")

    # COMPARISON 4: Benchmark Report (Text Summary)
    print(f"   Creating benchmark report...")

    report_lines = []
    report_lines.append("="*80)
    report_lines.append("MLU-07: Historical Benchmark Report")
    report_lines.append("="*80)
    report_lines.append("")

    if 'historical' in scenarios_data:
        hist_data = scenarios_data['historical']
        report_lines.append("HISTORICAL BASELINE (Reference Period)")
        report_lines.append("-" * 80)
        report_lines.append(f"Land Use Distribution:")
        for crop in ['WHEAT', 'MAIZE', 'SOLAR']:
            count = hist_data['final_land_use'][crop]
            pct = (count / hist_data['n_parcels']) * 100
            report_lines.append(f"  {crop:12s}: {count:3d} parcels ({pct:5.1f}%)")
        report_lines.append(f"\nClimate Metrics:")
        report_lines.append(f"  Temperature:   {hist_data['climate_metrics']['avg_temperature']:.1f}°C")
        report_lines.append(f"  Precipitation: {hist_data['climate_metrics']['avg_precipitation']:.0f}mm")
        report_lines.append(f"\nLUSA Suitability Scores:")
        report_lines.append(f"  WHEAT:         {hist_data['lusa_metrics']['avg_wheat_suitability']:.3f}")
        report_lines.append(f"  MAIZE:         {hist_data['lusa_metrics']['avg_maize_suitability']:.3f}")
        report_lines.append("")

        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in scenarios_data:
                future_data = scenarios_data[scenario]
                report_lines.append(f"\n{scenario.upper()} - FUTURE PROJECTION")
                report_lines.append("-" * 80)

                report_lines.append(f"Land Use Changes from Historical:")
                for crop in ['WHEAT', 'MAIZE', 'SOLAR']:
                    hist_count = hist_data['final_land_use'][crop]
                    future_count = future_data['final_land_use'][crop]
                    change = future_count - hist_count
                    pct_change = ((future_count - hist_count) / hist_count * 100) if hist_count > 0 else 0
                    sign = "+" if change >= 0 else ""
                    report_lines.append(f"  {crop:12s}: {future_count:3d} parcels ({sign}{change:+3d}, {pct_change:+6.1f}%)")

                report_lines.append(f"\nClimate Changes from Historical:")
                temp_change = future_data['climate_metrics']['avg_temperature'] - hist_data['climate_metrics']['avg_temperature']
                precip_change = future_data['climate_metrics']['avg_precipitation'] - hist_data['climate_metrics']['avg_precipitation']
                report_lines.append(f"  Temperature:   {future_data['climate_metrics']['avg_temperature']:.1f}°C ({temp_change:+.1f}°C)")
                report_lines.append(f"  Precipitation: {future_data['climate_metrics']['avg_precipitation']:.0f}mm ({precip_change:+.0f}mm)")

                report_lines.append(f"\nLUSA Suitability Changes from Historical:")
                wheat_change = future_data['lusa_metrics']['avg_wheat_suitability'] - hist_data['lusa_metrics']['avg_wheat_suitability']
                maize_change = future_data['lusa_metrics']['avg_maize_suitability'] - hist_data['lusa_metrics']['avg_maize_suitability']
                report_lines.append(f"  WHEAT:         {future_data['lusa_metrics']['avg_wheat_suitability']:.3f} ({wheat_change:+.3f})")
                report_lines.append(f"  MAIZE:         {future_data['lusa_metrics']['avg_maize_suitability']:.3f} ({maize_change:+.3f})")

    report_lines.append("\n" + "="*80)
    report_lines.append("End of Report")
    report_lines.append("="*80)

    report_file = output_path / 'benchmark_report.txt'
    report_file.write_text('\n'.join(report_lines))
    viz_files.append(report_file)
    print(f"      ✅ {report_file.name}")

    print(f"\n{'='*80}")
    print(f"✅ HISTORICAL COMPARISON COMPLETE")
    print(f"{'='*80}")
    print(f"Output: {output_path}")
    print(f"Comparison visualizations:")
    for f in viz_files:
        print(f"  - {f.name}")
    print(f"{'='*80}\n")

    return viz_files
