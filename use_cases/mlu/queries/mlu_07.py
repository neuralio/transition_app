"""
MLU-07: Integrate Historical EO Data for Benchmarking

This query provides historical baseline comparison functionality:
- Loads historical LUSA predictions (PAST_LUSA_PREDICTIONS.nc, 1990-2020)
- Loads future LUSA predictions (LUSA_PREDICTIONS_RCP{26,45,85}.nc, 2021-2100)
- Directly compares past vs future crop suitability
- Creates benchmark visualizations showing how suitability changes over time
"""

import sys
from pathlib import Path
import xarray as xr
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from use_cases.mlu.utils.scenario_utils import get_scenario_display_name


def _generate_benchmark_insights(crop, stats, future_scenarios):
    """Generate AI insights for historical vs future comparison."""
    try:
        client = OpenAI()

        # Calculate changes
        changes = {}
        if 'historical' in stats and crop in stats['historical']:
            hist_val = stats['historical'][crop]
            for scenario in future_scenarios:
                if scenario in stats and crop in stats[scenario]:
                    future_val = stats[scenario][crop]
                    change = future_val - hist_val
                    change_pct = (change / hist_val) * 100 if hist_val != 0 else 0
                    changes[scenario] = {'absolute': change, 'percent': change_pct, 'future': future_val}

        data_summary = f"""
Historical Benchmark Comparison for {crop}:
- Historical Baseline (1990-2020): {stats.get('historical', {}).get(crop, 0):.3f}
"""
        for scenario, change_data in changes.items():
            scenario_display = get_scenario_display_name(scenario)
            data_summary += f"- {scenario_display}: {change_data['future']:.3f} (Δ{change_data['absolute']:+.3f}, {change_data['percent']:+.1f}%)\n"

        insights = {}

        # Temporal Trend Analysis (matches Evolution Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a climate scientist analyzing long-term agricultural trends. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the temporal evolution shown in the LUSA Suitability Evolution chart. What does the trajectory from historical baseline (1990-2020) to future projections tell us about climate change impacts on {crop}?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Temporal Trend Analysis (Evolution Chart)"] = response.choices[0].message.content.strip()

        # Spatial Variability Insight (matches Heatmap)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a geospatial analyst studying agricultural landscapes. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Suitability Change Heatmap. What does the spatial distribution of changes tell us about which areas in Thessaloniki will be most/least affected? What should land-use planners focus on?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Spatial Distribution Insight (Heatmap)"] = response.choices[0].message.content.strip()

        # Scenario Comparison (matches Statistics Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a climate policy analyst comparing emission scenarios. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Statistical Comparison chart showing suitability differences across scenarios. What is the range of uncertainty? How should policymakers interpret these different climate pathways?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Scenario Uncertainty Analysis (Statistics)"] = response.choices[0].message.content.strip()

        # Adaptation Planning (matches Benchmark Report)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an agricultural adaptation specialist advising farmers and policymakers. Provide detailed, actionable recommendations in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nBased on the benchmark report data, what specific adaptation strategies should stakeholders implement? Consider both farm-level practices and regional policy interventions."}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Adaptation Strategy Recommendations (Report)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate AI insights: {e}")
        avg_change = np.mean([c['percent'] for c in changes.values()]) if changes else 0
        return {
            "Temporal Trend Analysis (Evolution Chart)": f"{crop} suitability shows {avg_change:+.1f}% average change across future scenarios compared to historical baseline (1990-2020), indicating {'declining' if avg_change < 0 else 'improving'} conditions over time",
            "Spatial Distribution Insight (Heatmap)": f"Spatial analysis reveals heterogeneous climate impacts across Thessaloniki region, with some areas experiencing more pronounced suitability changes than others",
            "Scenario Uncertainty Analysis (Statistics)": f"Statistical comparison across {len(changes)} climate scenarios shows range of possible futures, emphasizing need for robust adaptation planning under uncertainty",
            "Adaptation Strategy Recommendations (Report)": "Implement climate-smart agriculture practices including crop diversification, water management optimization, and soil health enhancement to maintain productivity under changing conditions"
        }


def load_lusa_data(data_path: str, crop: str, scenario: str, geojson=None):
    """
    Load LUSA suitability data from NetCDF files.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        crop: Crop name (WHEAT or MAIZE)
        scenario: Scenario name ('historical', 'rcp26', 'rcp45', 'rcp85')
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with LUSA predictions
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    data_path = Path(data_path)
    crop_dir = data_path / crop

    if scenario == 'historical':
        lusa_file = crop_dir / 'PAST_LUSA_PREDICTIONS.nc'
    else:
        lusa_file = crop_dir / f'{scenario.upper()}_LUSA_PREDICTIONS.nc'

    if not lusa_file.exists():
        raise FileNotFoundError(f"LUSA file not found: {lusa_file}")

    ds = xr.open_dataset(lusa_file)

    # Apply spatial filtering if geojson provided
    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


def query_mlu_07(
    data_path: str,
    scenarios: list = None,
    crops: list = None,
    output_dir: str = None,
    config = None,
    geojson: dict = None,
    farmer_locations: list = None  # NEW (2025-10-21): User-specified farmer locations
):
    """
    Run MLU-07: Historical vs Future LUSA Suitability Comparison.

    This query DIRECTLY loads and compares LUSA NetCDF files without running simulations.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        scenarios: List of scenarios to compare (default: ['historical', 'rcp26', 'rcp45', 'rcp85'])
        crops: List of crops to analyze (default: ['WHEAT', 'MAIZE'])
        output_dir: Output directory for results
        config: MLUConfig object (optional, will load from default if None)
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        dict: Result dictionary with status, outputs, and metrics
    """
    try:
        # Load config if not provided
        if config is None:
            from use_cases.mlu.config_loader import load_config
            config = load_config()

        if scenarios is None:
            scenarios = ['historical', 'rcp26', 'rcp45', 'rcp85']

        if crops is None:
            crops = ['WHEAT', 'MAIZE']

        # Set output path with timestamp to prevent overwriting
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_dir:
            output_path = Path(output_dir) / 'mlu_07' / timestamp
        else:
            # Default: use_cases/mlu/results/mlu_07/{timestamp}
            mlu_dir = Path(__file__).parent.parent
            output_path = mlu_dir / 'results' / 'mlu_07' / timestamp
        output_path.mkdir(parents=True, exist_ok=True)

        # Create visualizations subfolder (to match CCA/GCP/MLU-04/MLU-05 pattern)
        viz_output = output_path / "visualizations"
        viz_output.mkdir(parents=True, exist_ok=True)

        # Get Thessaloniki coordinates from config
        THESS_LAT_MIN = config.lat_min
        THESS_LAT_MAX = config.lat_max
        THESS_LON_MIN = config.lon_min
        THESS_LON_MAX = config.lon_max

        print(f"\n{'='*80}")
        print(f"🔍 MLU-07: Historical vs Future LUSA Benchmarking")
        print(f"{'='*80}")
        print(f"Crops: {', '.join(crops)}")
        print(f"Scenarios: {', '.join([s.upper() for s in scenarios])}")
        print(f"Region: Thessaloniki ({THESS_LAT_MIN}-{THESS_LAT_MAX}°N, {THESS_LON_MIN}-{THESS_LON_MAX}°E)")
        print(f"{'='*80}\n")

        # Load all LUSA data
        print(f"📁 Loading LUSA NetCDF files and filtering to Thessaloniki region...")
        lusa_data = {}

        for scenario in scenarios:
            lusa_data[scenario] = {}
            for crop in crops:
                print(f"   Loading {crop} - {scenario.upper()}...")
                ds = load_lusa_data(data_path, crop, scenario, geojson=geojson)

                # Filter to Thessaloniki region using config coordinates
                # LUSA files have ascending latitude
                lat_slice = config.get_lat_slice(for_lusa=True)
                lon_slice = config.get_lon_slice()
                ds_thessaloniki = ds.sel(
                    lat=slice(*lat_slice),
                    lon=slice(*lon_slice)
                )

                lusa_data[scenario][crop] = ds_thessaloniki

        print(f"\n📊 Creating visualizations...")
        viz_files = []

        # Check if single scenario mode (historical + one future scenario)
        is_single_scenario = len(scenarios) == 2 and 'historical' in scenarios
        single_scenario_name = None
        if is_single_scenario:
            from use_cases.mlu.utils.scenario_utils import get_scenario_short_name
            future_scenarios = [s for s in scenarios if s != 'historical']
            if future_scenarios:
                single_scenario_name = get_scenario_short_name(future_scenarios[0])
                print(f"   📌 Single scenario mode detected: {single_scenario_name}")

        # VISUALIZATION 1: LUSA Scores Over Time (Historical vs Future)
        print(f"   Creating LUSA suitability evolution comparison...")

        fig1 = make_subplots(
            rows=len(crops), cols=1,
            subplot_titles=[f'{crop} Suitability: Historical vs Future' for crop in crops],
            vertical_spacing=0.15
        )

        colors = {
            'historical': '#64748b',  # Gray (baseline)
            'rcp26': '#22c55e',       # Green (low emissions)
            'rcp45': '#f59e0b',       # Orange (medium)
            'rcp85': '#ef4444'        # Red (high emissions)
        }

        for idx, crop in enumerate(crops, 1):
            for scenario in scenarios:
                ds = lusa_data[scenario][crop]

                # Get suitability variable name (LUSA files use 'score')
                suitability_var = 'score'

                # Extract years and mean suitability across space
                if 'time' in ds.dims:
                    years = ds['time'].values
                    mean_suitability = ds[suitability_var].mean(dim=['lat', 'lon']).values
                else:
                    # Single time point
                    years = [2000] if scenario == 'historical' else [2050]
                    mean_suitability = [float(ds[suitability_var].mean().values)]

                label = "Historical (Baseline)" if scenario == 'historical' else get_scenario_display_name(scenario)
                line_width = 4 if scenario == 'historical' else 2
                line_dash = 'solid' if scenario == 'historical' else 'dash'

                fig1.add_trace(go.Scatter(
                    x=years,
                    y=mean_suitability,
                    mode='lines+markers',
                    name=label,
                    line=dict(color=colors[scenario], width=line_width, dash=line_dash),
                    marker=dict(size=4),
                    legendgroup=scenario,
                    showlegend=(idx == 1),  # Only show legend on first subplot
                    hovertemplate=f'<b>{label}</b><br>Year: %{{x}}<br>Suitability: %{{y:.3f}}<extra></extra>'
                ), row=idx, col=1)

        # Add scenario prefix if single scenario mode
        title_text = 'Land Suitability Evolution: Historical Baseline vs Future Projections<br><sub>AI-predicted crop suitability from LUSA model (0-100 scale, Thessaloniki region)</sub>'
        if is_single_scenario and single_scenario_name:
            title_text = f'{single_scenario_name} - {title_text.split("<br>")[0]}<br><sub>AI-predicted crop suitability from LUSA model (0-100 scale, Thessaloniki region)</sub>'

        fig1.update_layout(
            title=dict(
                text=title_text,
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            hovermode='x unified',
            height=400 * len(crops),
            width=1200,
            margin=dict(l=60, r=60, t=120, b=60),
            legend=dict(
                x=0.01,
                y=0.99,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#e2e8f0',
                borderwidth=1
            )
        )

        for idx in range(1, len(crops) + 1):
            fig1.update_xaxes(title_text="Year", row=idx, col=1, gridcolor='#e2e8f0')
            fig1.update_yaxes(title_text="LUSA Suitability Score (0-100)", row=idx, col=1, gridcolor='#e2e8f0', range=[0, 100])

        # Add scenario prefix to filename if single scenario mode
        filename_prefix = f'{single_scenario_name}_' if is_single_scenario and single_scenario_name else ''
        evolution_file = viz_output / f'{filename_prefix}lusa_suitability_evolution.html'
        fig1.write_html(str(evolution_file))
        viz_files.append(evolution_file)
        print(f"      ✅ {evolution_file.name}")

        # VISUALIZATION 2: Suitability Change Heatmap (Historical vs Future)
        print(f"   Creating suitability change heatmap...")

        # Determine number of columns based on actual scenarios (excluding historical)
        future_scenarios = [s for s in scenarios if s != 'historical']
        n_cols = len(future_scenarios)

        # Create shorter scenario names for subplot titles
        scenario_short_names = {
            'rcp26': 'Optimistic',
            'rcp45': 'Moderate',
            'rcp85': 'Pessimistic'
        }

        fig2 = make_subplots(
            rows=len(crops), cols=n_cols,
            subplot_titles=[
                f'{crop} - {scenario_short_names.get(scen, scen.upper())}'
                for crop in crops
                for scen in future_scenarios
            ],
            horizontal_spacing=0.12,
            vertical_spacing=0.15
        )

        for crop_idx, crop in enumerate(crops, 1):
            hist_ds = lusa_data['historical'][crop]
            # LUSA files use 'score' as the variable name
            hist_suitability_var = 'score'

            # Get historical mean
            if 'time' in hist_ds.dims:
                hist_mean = hist_ds[hist_suitability_var].mean(dim='time')
            else:
                hist_mean = hist_ds[hist_suitability_var]

            # Iterate through future scenarios
            for scen_idx, scenario in enumerate(future_scenarios, 1):
                if scenario not in lusa_data or crop not in lusa_data[scenario]:
                    continue  # Skip if data not available
                future_ds = lusa_data[scenario][crop]
                future_suitability_var = 'score'

                # Get future mean
                if 'time' in future_ds.dims:
                    future_mean = future_ds[future_suitability_var].mean(dim='time')
                else:
                    future_mean = future_ds[future_suitability_var]

                # Calculate change
                change = future_mean - hist_mean

                fig2.add_trace(go.Heatmap(
                    z=change.values,
                    x=change.lon.values,
                    y=change.lat.values,
                    colorscale='RdYlGn',
                    zmid=0,
                    zmin=-0.3,
                    zmax=0.3,
                    colorbar=dict(
                        title="Δ Suitability",
                        len=0.3,
                        y=1 - (crop_idx - 1) * 0.5 - 0.15,
                        x=1.02
                    ) if scen_idx == 3 else None,
                    showscale=(scen_idx == 3),
                    hovertemplate='Lat: %{y:.2f}<br>Lon: %{x:.2f}<br>Change: %{z:.3f}<extra></extra>'
                ), row=crop_idx, col=scen_idx)

        # Add scenario prefix if single scenario mode
        title_text2 = 'Suitability Changes from Historical Baseline<br><sub>Green = improved, Red = degraded, Yellow = stable</sub>'
        if is_single_scenario and single_scenario_name:
            title_text2 = f'{single_scenario_name} - {title_text2.split("<br>")[0]}<br><sub>Green = improved, Red = degraded, Yellow = stable</sub>'

        fig2.update_layout(
            title=dict(
                text=title_text2,
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            height=400 * len(crops),
            width=1400,
            margin=dict(l=60, r=120, t=140, b=60)  # Increased top margin for longer subplot titles
        )

        for crop_idx in range(1, len(crops) + 1):
            for scen_idx in range(1, 4):
                fig2.update_xaxes(title_text="Longitude", row=crop_idx, col=scen_idx)
                fig2.update_yaxes(title_text="Latitude", row=crop_idx, col=scen_idx)

        # Add scenario prefix to filename if single scenario mode
        heatmap_file = viz_output / f'{filename_prefix}suitability_change_heatmap.html'
        fig2.write_html(str(heatmap_file))
        viz_files.append(heatmap_file)
        print(f"      ✅ {heatmap_file.name}")

        # VISUALIZATION 3: Benchmark Summary Statistics
        print(f"   Creating benchmark statistics...")

        # Calculate statistics
        stats = {}
        for scenario in scenarios:
            stats[scenario] = {}
            for crop in crops:
                ds = lusa_data[scenario][crop]
                suitability_var = 'score'  # LUSA files use 'score'

                if 'time' in ds.dims:
                    mean_val = float(ds[suitability_var].mean().values)
                else:
                    mean_val = float(ds[suitability_var].mean().values)

                stats[scenario][crop] = mean_val

        fig3 = go.Figure()

        for crop in crops:
            scenario_labels = []
            values = []
            for scenario in scenarios:
                label = "Historical" if scenario == 'historical' else get_scenario_display_name(scenario)
                scenario_labels.append(label)
                values.append(stats[scenario][crop])

            fig3.add_trace(go.Bar(
                name=crop,
                x=scenario_labels,
                y=values,
                text=[f'{v:.3f}' for v in values],
                textposition='outside',
                marker=dict(color='#3b82f6' if crop == 'WHEAT' else '#f97316'),
                hovertemplate=f'<b>{crop}</b><br>Suitability: %{{y:.3f}}<extra></extra>'
            ))

        # Add scenario prefix if single scenario mode
        title_text3 = 'Average Suitability: Historical vs Future Scenarios<br><sub>Spatial and temporal mean LUSA scores</sub>'
        if is_single_scenario and single_scenario_name:
            title_text3 = f'{single_scenario_name} - {title_text3.split("<br>")[0]}<br><sub>Spatial and temporal mean LUSA scores</sub>'

        fig3.update_layout(
            title=dict(
                text=title_text3,
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            xaxis=dict(
                title=dict(text='Scenario', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b')
            ),
            yaxis=dict(
                title=dict(text='Mean LUSA Suitability (0-100)', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b'),
                gridcolor='#e2e8f0',
                range=[0, 100]
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

        # Add scenario prefix to filename if single scenario mode
        stats_file = viz_output / f'{filename_prefix}suitability_statistics.html'
        fig3.write_html(str(stats_file))
        viz_files.append(stats_file)
        print(f"      ✅ {stats_file.name}")

        # BENCHMARK REPORT (Text)
        print(f"   Creating benchmark report...")

        report_lines = []
        report_lines.append("="*80)
        report_lines.append("MLU-07: Historical LUSA Benchmark Report")
        report_lines.append("="*80)
        report_lines.append("")
        report_lines.append("HISTORICAL BASELINE")
        report_lines.append("-" * 80)
        for crop in crops:
            hist_val = stats['historical'][crop]
            report_lines.append(f"  {crop:12s}: {hist_val:.3f}")
        report_lines.append("")

        # Report for future scenarios
        future_scenarios = [s for s in scenarios if s != 'historical']
        for scenario in future_scenarios:
            if scenario not in stats:
                continue  # Skip if no data for this scenario
            scenario_display = get_scenario_display_name(scenario)
            report_lines.append(f"\n{scenario_display} - FUTURE PROJECTION")
            report_lines.append("-" * 80)
            report_lines.append(f"Suitability Changes from Historical:")
            for crop in crops:
                if crop not in stats['historical'] or crop not in stats[scenario]:
                    continue  # Skip if crop data not available
                hist_val = stats['historical'][crop]
                future_val = stats[scenario][crop]
                change = future_val - hist_val
                pct_change = (change / hist_val * 100) if hist_val > 0 else 0
                report_lines.append(f"  {crop:12s}: {future_val:.3f} ({change:+.3f}, {pct_change:+6.1f}%)")

        report_lines.append("\n" + "="*80)
        report_lines.append("End of Report")
        report_lines.append("="*80)

        report_file = output_path / 'benchmark_report.txt'
        report_file.write_text('\n'.join(report_lines))
        viz_files.append(report_file)
        print(f"      ✅ {report_file.name}")

        # Print summary
        print(f"\n{'='*80}")
        print(f"✅ MLU-07 COMPLETE")
        print(f"{'='*80}")
        print(f"Output: {output_path}")
        print(f"\nVisualizations:")
        for f in viz_files:
            print(f"  - {f.name}")
        print(f"\nKey Findings:")
        # Show comparison for available scenarios
        future_scenarios = [s for s in scenarios if s != 'historical']
        for crop in crops:
            if crop not in stats['historical']:
                continue
            hist_val = stats['historical'][crop]
            print(f"  {crop}:")
            print(f"    Historical: {hist_val:.3f}")
            for scenario in future_scenarios:
                if scenario in stats and crop in stats[scenario]:
                    future_val = stats[scenario][crop]
                    change = future_val - hist_val
                    scen_display = get_scenario_display_name(scenario)
                    print(f"    {scen_display}: {future_val:.3f} (Δ{change:+.3f})")

        # Generate AI insights for each crop
        all_insights = {}
        try:
            if 'historical' in stats and any(crop in stats['historical'] for crop in crops):
                # Print unified insights header (for backend extraction)
                print(f"\n📊 AI-Generated Insights:")

                for crop in crops:
                    if crop in stats['historical']:
                        print(f"\n{crop}:")
                        crop_insights = _generate_benchmark_insights(crop, stats, future_scenarios)
                        all_insights[crop] = crop_insights
                        for viz_name, insight in crop_insights.items():
                            print(f"\n  {viz_name}:")
                            print(f"    {insight}")
            else:
                print(f"\n⚠️  AI insights require historical baseline data")
                print(f"   Run MLU-07 with 'historical' scenario included for AI-generated insights")
        except Exception as e:
            print(f"\n⚠️  Could not generate AI insights: {e}")
            import traceback
            traceback.print_exc()

        print(f"{'='*80}\n")

        return {
            'status': 'success',
            'output_dir': str(output_path.absolute()),
            'visualizations': [str(f.absolute()) for f in viz_files],
            'statistics': stats,
            'ai_insights': all_insights
        }

    except ValueError as e:
        # Clean error message for validation errors (user-friendly)
        # Print with red box styling to stderr
        error_msg = str(e)
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"{error_msg}", file=sys.stderr)
        print(f"{'='*80}\n", file=sys.stderr)
        return {
            'status': 'error',
            'message': error_msg
        }
    except Exception as e:
        # Full traceback for unexpected errors (debugging)
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'message': str(e)
        }
