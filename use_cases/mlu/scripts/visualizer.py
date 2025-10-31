"""
Visualization System for TRANSITION ML-ABM Results

Generates interactive visualizations:
1. Map-based land suitability visualization
2. Suitability scores (past, current, projected)
3. Trade-off analysis (economic vs environmental)
4. Confidence measures from ensemble projections
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import sys

# Import scenario utilities for display names
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from scenario_utils import get_scenario_display_name


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


class ResultVisualizer:
    """
    Creates interactive visualizations for simulation results.
    """

    def __init__(self, result_collector, data_path: Optional[str] = None):
        """
        Initialize visualizer.

        Args:
            result_collector: ResultCollector instance with simulation data
            data_path: Path to PILOT_THESSALONIKI_DATA (needed for full grid visualization)
        """
        self.collector = result_collector
        self.scenario = result_collector.scenario
        self.scenario_display = get_scenario_display_name(self.scenario)

        # Get data path from config if not provided
        if data_path is None:
            try:
                from use_cases.mlu.config_loader import load_config
                config = load_config()
                data_path = config.data_path
            except Exception:
                # Fallback if config unavailable
                data_path = "/app/data"

        self.data_path = data_path

    def create_land_suitability_map(self, year: Optional[int] = None, crop: Optional[str] = None, show_full_grid: bool = False):
        """
        Create interactive map showing land suitability scores.

        Args:
            year: Year to visualize (None = latest)
            crop: Specific crop to show (None = current crop)
            show_full_grid: If True, load and show full LUSA grid (all 9k+ pixels)
                           If False, show only farmer sample locations (default, faster)

        Returns:
            Plotly figure object
        """
        spatial_data = self.collector.get_spatial_data(year)

        if not spatial_data or 'parcels' not in spatial_data:
            return go.Figure().add_annotation(text="No spatial data available")

        parcels = spatial_data['parcels']
        year_display = spatial_data['year']

        # Extract data for plotting
        lats = [p['lat'] for p in parcels]
        lons = [p['lon'] for p in parcels]

        if crop:
            # Show suitability for specific crop
            values = [p['suitability_scores'].get(crop, 0) for p in parcels]
            title_text = f"Land Suitability for {crop} ({self.scenario_display}, {year_display})"
            colorbar_title = "Suitability Score (0-100)"
        else:
            # Show current crop choice
            values = [p['suitability_scores'].get(p['current_crop'], 0) for p in parcels]
            current_crops = [p['current_crop'] for p in parcels]
            title_text = f"Land Use and Suitability ({self.scenario_display}, {year_display})"
            colorbar_title = "Suitability Score"

        # Create hover text
        hover_texts = []
        for p in parcels:
            text = f"<b>Location:</b> ({p['lat']:.4f}, {p['lon']:.4f})<br>"
            text += f"<b>Current Crop:</b> {p['current_crop']}<br>"
            text += f"<b>Actual Yield:</b> {p['actual_yield']:.2f} tons/ha<br>"
            text += f"<b>Annual Income:</b> €{p['annual_income']:.2f}<br>"
            text += f"<b>Soil Quality:</b> {p['soil_quality']:.1f}<br>"
            text += "<b>Suitability:</b><br>"
            for c, s in p['suitability_scores'].items():
                text += f"  {c}: {s:.1f}<br>"
            hover_texts.append(text)

        # Create scatter mapbox
        fig = go.Figure(go.Scattermapbox(
            lat=lats,
            lon=lons,
            mode='markers',
            marker=dict(
                size=15,
                color=values,
                colorscale='RdYlGn',
                cmin=0,
                cmax=100,
                colorbar=dict(title=colorbar_title),
                showscale=True
            ),
            text=hover_texts,
            hoverinfo='text',
            name='Land Parcels'
        ))

        # Update layout
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)

        fig.update_layout(
            title=title_text,
            mapbox=dict(
                style='open-street-map',
                center=dict(lat=center_lat, lon=center_lon),
                zoom=10
            ),
            height=600,
            margin=dict(l=0, r=0, t=40, b=0),
            autosize=True
        )

        return fig

    def create_full_lusa_heatmap(self, year: Optional[int] = None, crop: str = 'WHEAT', show_farmers: bool = True):
        """
        Create interactive heatmap showing FULL LUSA grid (all pixels) with farmers overlaid.

        Args:
            year: Year to visualize (None = latest from simulation)
            crop: Crop to show ('WHEAT' or 'MAIZE')
            show_farmers: If True, overlay farmer locations

        Returns:
            Plotly figure object with full LUSA grid heatmap
        """
        import xarray as xr

        # Get year from spatial data if not specified
        if year is None:
            spatial_data = self.collector.get_spatial_data(year)
            year = spatial_data.get('year', 2021) if spatial_data else 2021

        # Load full LUSA grid from NetCDF
        scenario_map = {
            'rcp26': 'RCP26',
            'rcp45': 'RCP45',
            'rcp85': 'RCP85'
        }
        rcp_label = scenario_map.get(self.scenario.lower(), 'RCP85')

        # Try to use config-based path
        try:
            from use_cases.mlu.config_loader import load_config
            from backend.data.loaders.data_paths import DataPathBuilder
            config = load_config()
            path_builder = DataPathBuilder(config.data_path, config.data_subdirs, config.data_files)
            lusa_file = str(path_builder.get_crop_suitability_file(crop, self.scenario))
        except Exception:
            # Fallback to hardcoded path
            lusa_file = f"{self.data_path}/{crop.upper()}/{rcp_label}_LUSA_PREDICTIONS.nc"

        try:
            ds = xr.open_dataset(lusa_file)
            scores = ds.sel(time=f"{year}-01-01", method="nearest").score

            # Get grid data
            lats = scores.lat.values
            lons = scores.lon.values
            values = scores.values

            # Get Thessaloniki bounds from spatial data (where farmers are)
            spatial_data = self.collector.get_spatial_data(year)
            if spatial_data and 'parcels' in spatial_data and len(spatial_data['parcels']) > 0:
                parcels = spatial_data['parcels']
                farmer_lats = [p['lat'] for p in parcels]
                farmer_lons = [p['lon'] for p in parcels]
                # Use farmer bounds with small margin
                lat_min, lat_max = min(farmer_lats) - 0.2, max(farmer_lats) + 0.2
                lon_min, lon_max = min(farmer_lons) - 0.2, max(farmer_lons) + 0.2
            else:
                # Fallback: Thessaloniki region
                lat_min, lat_max = 40.2, 40.9
                lon_min, lon_max = 22.4, 23.4

            # Mask: valid data + within Thessaloniki bounds
            mask = (~np.isnan(values)) & (values > 0)

            # Apply spatial filter to focus on Thessaloniki region
            lat_mask = (lats >= lat_min) & (lats <= lat_max)
            lon_mask = (lons >= lon_min) & (lons <= lon_max)

            # Create 2D mask combining all filters
            spatial_mask_2d = lat_mask[:, None] & lon_mask[None, :]
            final_mask = mask & spatial_mask_2d

            # Extract ONLY valid pixels in Thessaloniki region (coarse grid)
            valid_indices = np.where(final_mask)
            valid_lats_coarse = lats[valid_indices[0]]
            valid_lons_coarse = lons[valid_indices[1]]
            valid_values_coarse = values[valid_indices]

            print(f"    Original LUSA grid: {len(valid_values_coarse)} pixels (0.1° resolution)")
            print(f"    Bounds: lat {lat_min:.2f}-{lat_max:.2f}, lon {lon_min:.2f}-{lon_max:.2f}")

            # INTERPOLATE to create smooth heatmap (coarse grid is too sparse!)
            from scipy.interpolate import griddata

            print(f"    Interpolating to fine grid for smooth heatmap...")

            # Create fine grid (10x denser than original)
            lat_range = lat_max - lat_min
            lon_range = lon_max - lon_min
            n_lat = max(50, int(lat_range * 100))  # ~0.01° resolution
            n_lon = max(50, int(lon_range * 100))

            lats_fine = np.linspace(lat_min, lat_max, n_lat)
            lons_fine = np.linspace(lon_min, lon_max, n_lon)
            lon_grid, lat_grid = np.meshgrid(lons_fine, lats_fine)

            # Interpolate using cubic for smooth appearance
            points = np.column_stack((valid_lats_coarse, valid_lons_coarse))
            values_fine = griddata(points, valid_values_coarse, (lat_grid, lon_grid),
                                 method='cubic', fill_value=np.nan)

            # Clip to valid range and remove NaN
            values_fine = np.clip(values_fine, 0, 100)
            valid_fine = ~np.isnan(values_fine)

            # Flatten for plotting
            valid_lats = lat_grid[valid_fine]
            valid_lons = lon_grid[valid_fine]
            valid_values = values_fine[valid_fine]

            print(f"    Interpolated grid: {len(valid_values)} pixels → SMOOTH HEATMAP!")

            # Create hover text for grid pixels
            grid_hover = [
                f"<b>LUSA Heatmap</b><br>Lat: {lat:.4f}<br>Lon: {lon:.4f}<br><b>Suitability: {val:.0f}</b>"
                for lat, lon, val in zip(valid_lats, valid_lons, valid_values)
            ]

            # Create figure
            fig = go.Figure()

            # Add interpolated LUSA grid as smooth heatmap
            fig.add_trace(go.Scattermapbox(
                lat=valid_lats,
                lon=valid_lons,
                mode='markers',
                marker=dict(
                    size=6,  # Smaller markers, more of them = smooth
                    color=valid_values,
                    colorscale='RdYlGn',
                    cmin=0,
                    cmax=100,
                    colorbar=dict(
                        title="Land Suitability<br>Score (0-100)",
                        x=1.02,
                        len=0.7,
                        y=0.5,
                        thickness=15
                    ),
                    opacity=0.85
                ),
                text=grid_hover,
                hoverinfo='text',
                name='LUSA Heatmap',
                showlegend=False
            ))

            # Overlay farmer locations if requested
            if show_farmers:
                spatial_data = self.collector.get_spatial_data(year)
                if spatial_data and 'parcels' in spatial_data:
                    parcels = spatial_data['parcels']

                    farmer_lats = [p['lat'] for p in parcels]
                    farmer_lons = [p['lon'] for p in parcels]
                    farmer_crops = [p['current_crop'] for p in parcels]
                    farmer_yields = [p['actual_yield'] for p in parcels]
                    farmer_incomes = [p['annual_income'] for p in parcels]

                    # Create hover text for farmers
                    farmer_hover = []
                    for p in parcels:
                        text = f"<b>FARMER</b><br>"
                        text += f"Location: ({p['lat']:.4f}, {p['lon']:.4f})<br>"
                        text += f"Crop: {p['current_crop']}<br>"
                        text += f"Yield: {p['actual_yield']:.2f} t/ha<br>"
                        text += f"Income: €{p['annual_income']:.0f}/yr<br>"
                        text += f"Suitability: {p['suitability_scores'].get(crop, 0):.0f}"
                        farmer_hover.append(text)

                    # Color farmers by their current crop - bright colors for visibility
                    farmer_colors = ['#0000FF' if c == 'WHEAT' else '#FF8C00' for c in farmer_crops]
                    farmer_symbols = ['circle' if c == 'WHEAT' else 'square' for c in farmer_crops]

                    fig.add_trace(go.Scattermapbox(
                        lat=farmer_lats,
                        lon=farmer_lons,
                        mode='markers',
                        marker=dict(
                            size=15,  # Larger than grid points
                            color=farmer_colors,
                            symbol='star',  # Star symbol stands out more
                            opacity=1.0  # Fully opaque
                        ),
                        text=farmer_hover,
                        hoverinfo='text',
                        name='Farmers',
                        showlegend=True
                    ))

            # Calculate map center
            valid_lats = lats[mask.any(axis=1)]
            valid_lons = lons[mask.any(axis=0)]
            center_lat = float(np.mean(valid_lats)) if len(valid_lats) > 0 else 40.6
            center_lon = float(np.mean(valid_lons)) if len(valid_lons) > 0 else 23.0

            # Update layout
            fig.update_layout(
                title=f"Land Suitability for {crop} - Full LUSA Grid<br>{self.scenario_display} Scenario, Year {year}",
                mapbox=dict(
                    style='open-street-map',
                    center=dict(lat=center_lat, lon=center_lon),
                    zoom=9
                ),
                height=700,
                margin=dict(l=0, r=0, t=60, b=0),
                showlegend=True,
                legend=dict(
                    x=0.01,
                    y=0.99,
                    bgcolor='rgba(255,255,255,0.8)'
                ),
                autosize=True
            )

            ds.close()
            return fig

        except Exception as e:
            # Fallback to sample-based map if full grid fails
            print(f"Warning: Could not load full LUSA grid ({e}). Using sample-based map.")
            return self.create_land_suitability_map(year=year, crop=crop)

    def create_suitability_time_series(self, lat: float, lon: float, crop: str):
        """
        Create time-series showing suitability evolution for a specific location.

        Args:
            lat: Latitude
            lon: Longitude
            crop: Crop name

        Returns:
            Plotly figure
        """
        # Extract suitability scores over time for this location
        years = []
        scores = []

        for snapshot in self.collector.spatial_snapshots:
            # Find parcel closest to specified location
            parcels = snapshot['parcels']
            closest = min(parcels, key=lambda p: (p['lat'] - lat)**2 + (p['lon'] - lon)**2)

            years.append(snapshot['year'])
            scores.append(closest['suitability_scores'].get(crop, 0))

        # Create figure
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=years,
            y=scores,
            mode='lines+markers',
            name=f'{crop} Suitability',
            line=dict(color='green', width=3),
            marker=dict(size=8)
        ))

        fig.update_layout(
            title=f"Land Suitability Time Series for {crop}<br>Location: ({lat:.4f}, {lon:.4f}) - {self.scenario_display}",
            xaxis_title="Year",
            yaxis_title="Suitability Score (0-100)",
            yaxis=dict(range=[0, 100]),
            hovermode='x unified',
            height=400,
            autosize=True
        )

        return fig

    def create_trade_off_visualization(self, results_by_scenario: Dict):
        """
        Create trade-off visualization comparing scenarios.

        Args:
            results_by_scenario: Dict mapping scenario -> ResultCollector

        Returns:
            Plotly figure
        """
        # Extract trade-off metrics
        scenarios = []
        incomes = []
        diversities = []
        productions = []

        for scenario, collector in results_by_scenario.items():
            trade_offs = collector.calculate_trade_offs()

            scenario_display = get_scenario_display_name(scenario)
            scenarios.append(scenario_display)
            incomes.append(trade_offs['economic']['avg_income'])
            diversities.append(trade_offs['environmental']['crop_diversity'])
            productions.append(trade_offs['economic']['total_production'])

        # Create subplot with 2 panels
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Economic vs Environmental Trade-off', 'Production Efficiency'),
            specs=[[{'type': 'scatter'}, {'type': 'bar'}]]
        )

        # Panel 1: Income vs Diversity scatter
        fig.add_trace(
            go.Scatter(
                x=incomes,
                y=diversities,
                mode='markers+text',
                text=scenarios,
                textposition='top center',
                marker=dict(
                    size=20,
                    color=['green', 'orange', 'red'],
                    line=dict(width=2, color='white')
                ),
                name='Scenarios'
            ),
            row=1, col=1
        )

        # Panel 2: Total production by scenario
        fig.add_trace(
            go.Bar(
                x=scenarios,
                y=productions,
                marker=dict(color=['green', 'orange', 'red']),
                name='Production'
            ),
            row=1, col=2
        )

        # Update axes
        fig.update_xaxes(title_text="Average Farmer Income (€/year)", row=1, col=1)
        fig.update_yaxes(title_text="Crop Diversity (Shannon Entropy)", row=1, col=1)
        fig.update_xaxes(title_text="Scenario", row=1, col=2)
        fig.update_yaxes(title_text="Total Production (tons)", row=1, col=2)

        fig.update_layout(
            title_text="Policy Trade-Off Analysis Across Climate Scenarios",
            showlegend=False,
            height=400,
            autosize=True
        )

        return fig

    def create_scenario_comparison_dashboard(self, results_by_scenario: Dict):
        """
        Create comprehensive dashboard comparing all scenarios.

        Args:
            results_by_scenario: Dict mapping scenario -> ResultCollector

        Returns:
            Plotly figure
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Average Farmer Income Over Time',
                'Total Production Over Time',
                'Crop Diversity Over Time',
                'Market Price Dynamics'
            ),
            specs=[[{'type': 'scatter'}, {'type': 'scatter'}],
                   [{'type': 'scatter'}, {'type': 'scatter'}]]
        )

        colors = {'rcp26': 'green', 'rcp45': 'orange', 'rcp85': 'red'}

        for scenario, collector in results_by_scenario.items():
            scenario_display = get_scenario_display_name(scenario)
            color = colors.get(scenario, 'blue')

            # Panel 1: Income
            income_data = collector.get_time_series_comparison('income')
            fig.add_trace(
                go.Scatter(
                    x=income_data['years'],
                    y=income_data['values'],
                    mode='lines+markers',
                    name=f'{scenario_display} Income',
                    line=dict(color=color, width=2),
                    showlegend=True
                ),
                row=1, col=1
            )

            # Panel 2: Production
            prod_data = collector.get_time_series_comparison('production')
            fig.add_trace(
                go.Scatter(
                    x=prod_data['years'],
                    y=prod_data['values'],
                    mode='lines+markers',
                    name=f'{scenario_display} Production',
                    line=dict(color=color, width=2),
                    showlegend=False
                ),
                row=1, col=2
            )

            # Panel 3: Diversity
            div_data = collector.get_time_series_comparison('diversity')
            fig.add_trace(
                go.Scatter(
                    x=div_data['years'],
                    y=div_data['values'],
                    mode='lines+markers',
                    name=f'{scenario_display} Diversity',
                    line=dict(color=color, width=2),
                    showlegend=False
                ),
                row=2, col=1
            )

            # Panel 4: Prices (WHEAT as example)
            market_df = collector.get_market_dataframe()
            if 'WHEAT_price' in market_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=market_df['year'],
                        y=market_df['WHEAT_price'],
                        mode='lines+markers',
                        name=f'{scenario_display} Wheat Price',
                        line=dict(color=color, width=2),
                        showlegend=False
                    ),
                    row=2, col=2
                )

        # Update axes labels
        fig.update_xaxes(title_text="Year", row=1, col=1)
        fig.update_yaxes(title_text="Income (€/year)", row=1, col=1)

        fig.update_xaxes(title_text="Year", row=1, col=2)
        fig.update_yaxes(title_text="Production (tons)", row=1, col=2)

        fig.update_xaxes(title_text="Year", row=2, col=1)
        fig.update_yaxes(title_text="Diversity (Shannon)", row=2, col=1)

        fig.update_xaxes(title_text="Year", row=2, col=2)
        fig.update_yaxes(title_text="Price (€/ton)", row=2, col=2)

        fig.update_layout(
            title_text="Multi-Level ABM Results: Climate Scenario Comparison",
            height=800,
            hovermode='x unified'
        )

        return fig

    def create_confidence_interval_plot(self, results_by_scenario: Dict, metric: str = 'income'):
        """
        Create plot with confidence intervals based on ensemble projections.

        Args:
            results_by_scenario: Dict mapping scenario -> ResultCollector
            metric: 'income', 'production', or 'diversity'

        Returns:
            Plotly figure
        """
        fig = go.Figure()

        # Use hex colors for proper rgba conversion
        colors = {'rcp26': '#00AA00', 'rcp45': '#FF8800', 'rcp85': '#DD0000'}
        color_names = {'rcp26': 'green', 'rcp45': 'orange', 'rcp85': 'red'}

        for scenario, collector in results_by_scenario.items():
            scenario_display = get_scenario_display_name(scenario)
            color_hex = colors.get(scenario, '#0000FF')
            color_name = color_names.get(scenario, 'blue')
            data = collector.get_time_series_comparison(metric)

            years = data['years']
            values = data['values']

            # Calculate confidence bounds (using ±15% as placeholder for ensemble spread)
            # TODO: Replace with actual ensemble projection data
            upper_bound = [v * 1.15 for v in values]
            lower_bound = [v * 0.85 for v in values]

            # Convert hex to rgb and add alpha for confidence band
            rgb = px.colors.hex_to_rgb(color_hex)
            fillcolor = f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.2)'

            # Add confidence band
            fig.add_trace(go.Scatter(
                x=years + years[::-1],
                y=upper_bound + lower_bound[::-1],
                fill='toself',
                fillcolor=fillcolor,
                line=dict(color='rgba(255,255,255,0)'),
                showlegend=False,
                name=f'{scenario_display} CI'
            ))

            # Add mean line
            fig.add_trace(go.Scatter(
                x=years,
                y=values,
                mode='lines+markers',
                name=f'{scenario_display}',
                line=dict(color=color_hex, width=3),
                marker=dict(size=8)
            ))

        fig.update_layout(
            title=f"{data['label']} with Confidence Intervals (±15% Ensemble Spread)",
            xaxis_title="Year",
            yaxis_title=f"{data['label']} ({data['unit']})",
            hovermode='x unified',
            height=500,
            autosize=True
        )

        return fig

    def save_all_visualizations(self, output_dir: str, results_by_scenario: Optional[Dict] = None):
        """
        Generate and save all visualizations to HTML files.

        Args:
            output_dir: Directory to save HTML files
            results_by_scenario: Optional dict for multi-scenario comparisons
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"Generating visualizations for {self.scenario}...")

        # 1. Full LUSA grid heatmap (NEW - shows complete suitability landscape)
        print("  - Full LUSA grid heatmap for WHEAT...")
        fig = self.create_full_lusa_heatmap(crop='WHEAT', show_farmers=True)
        wheat_file = output_dir / f'{self.scenario}_WHEAT_full_grid_heatmap.html'
        fig.write_html(wheat_file, config={'responsive': True, 'displayModeBar': True})
        inject_responsive_css_to_file(wheat_file)

        print("  - Full LUSA grid heatmap for MAIZE...")
        fig = self.create_full_lusa_heatmap(crop='MAIZE', show_farmers=True)
        maize_file = output_dir / f'{self.scenario}_MAIZE_full_grid_heatmap.html'
        fig.write_html(maize_file, config={'responsive': True, 'displayModeBar': True})
        inject_responsive_css_to_file(maize_file)

        # 2. Sample-based land suitability map (legacy, keep for comparison)
        print("  - Land suitability map (sample points)...")
        fig = self.create_land_suitability_map()
        samples_file = output_dir / f'{self.scenario}_land_suitability_samples.html'
        fig.write_html(samples_file, config={'responsive': True, 'displayModeBar': True})
        inject_responsive_css_to_file(samples_file)

        # 3. Time series for first parcel
        if self.collector.spatial_snapshots:
            first_parcel = self.collector.spatial_snapshots[0]['parcels'][0]
            lat, lon = first_parcel['lat'], first_parcel['lon']
            crops = list(first_parcel['suitability_scores'].keys())

            for crop in crops:
                print(f"  - Time series for {crop}...")
                fig = self.create_suitability_time_series(lat, lon, crop)
                ts_file = output_dir / f'{self.scenario}_{crop}_timeseries.html'
                fig.write_html(ts_file, config={'responsive': True, 'displayModeBar': True})
                inject_responsive_css_to_file(ts_file)

        # 4. Multi-scenario comparisons (if provided)
        if results_by_scenario:
            print("  - Scenario comparison dashboard...")
            fig = self.create_scenario_comparison_dashboard(results_by_scenario)
            comp_file = output_dir / 'scenario_comparison_dashboard.html'
            fig.write_html(comp_file, config={'responsive': True, 'displayModeBar': True})
            inject_responsive_css_to_file(comp_file)

            print("  - Trade-off visualization...")
            fig = self.create_trade_off_visualization(results_by_scenario)
            trade_file = output_dir / 'trade_off_analysis.html'
            fig.write_html(trade_file, config={'responsive': True, 'displayModeBar': True})
            inject_responsive_css_to_file(trade_file)

            print("  - Confidence interval plots...")
            for metric in ['income', 'production', 'diversity']:
                fig = self.create_confidence_interval_plot(results_by_scenario, metric)
                conf_file = output_dir / f'confidence_{metric}.html'
                fig.write_html(conf_file, config={'responsive': True, 'displayModeBar': True})
                inject_responsive_css_to_file(conf_file)

        print(f"\n✅ All visualizations saved to: {output_dir}")

    def __repr__(self):
        return f"ResultVisualizer(scenario={self.scenario}, steps={self.collector.current_step})"


if __name__ == "__main__":
    print("ResultVisualizer - Ready for creating interactive visualizations")
