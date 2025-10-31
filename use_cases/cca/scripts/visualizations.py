"""
Interactive Visualizations for CCA Simulation

Creates interactive charts (Plotly) and GIS maps (Folium) to visualize:
- Temporal dynamics (crop choices, income, production over time)
- Spatial patterns (farmer locations, PV installations, climate vulnerability)
- Scenario comparisons (RCP26 vs RCP45 vs RCP85)
- Policy impacts (green credits, subsidies, adaptation strategies)
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import folium
from folium import plugins
import numpy as np
from pathlib import Path
from typing import Dict, List
import sys
import rasterio
import xarray as xr
from global_land_mask import globe

# Import scenario utilities for display names
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from scenario_utils import get_scenario_display_name, get_scenario_short_name


class CCAVisualizer:
    """
    Creates interactive visualizations for CCA simulation results.

    Generates:
    - Plotly charts (time series, comparisons, distributions)
    - Folium GIS maps (farmer locations, PV installations, vulnerability)
    """

    def __init__(self, output_dir: str = "results/visualizations", data_path: str = None):
        """
        Initialize visualizer.

        Args:
            output_dir: Directory to save visualization files
            data_path: Path to PILOT_THESSALONIKI_DATA (optional, for suitability layers)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_path = Path(data_path) if data_path else None

        # Thessaloniki bounds
        self.lat_min, self.lat_max = 40.4, 40.9
        self.lon_min, self.lon_max = 22.5, 22.9
        self.center_lat = (self.lat_min + self.lat_max) / 2
        self.center_lon = (self.lon_min + self.lon_max) / 2

    def create_time_series_charts(self,
                                  yearly_stats: List[Dict],
                                  scenario: str,
                                  scenario_display: str = None,
                                  focus_crop: str = None) -> str:
        """
        Create time series charts for crop choices, income, and production.

        Args:
            yearly_stats: List of yearly statistics dicts
            scenario: RCP scenario name (internal code)
            scenario_display: User-friendly display name (optional)
            focus_crop: Optional crop to focus on (WHEAT, MAIZE, or None for all)

        Returns:
            Path to saved HTML file
        """
        # Use display name if provided, otherwise use scenario code
        display_name = scenario_display if scenario_display else scenario.upper()
        # Use short name for subplot titles to avoid overlap
        short_name = get_scenario_short_name(scenario)

        years = [s['year'] for s in yearly_stats]
        wheat_farmers = [s['wheat_farmers'] for s in yearly_stats]
        maize_farmers = [s['maize_farmers'] for s in yearly_stats]
        total_income = [s['total_income'] for s in yearly_stats]
        total_production = [s['total_production'] for s in yearly_stats]

        # Create subplots with short names in titles
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                f'Crop Choices Over Time - {short_name}',
                f'Total Farmer Income - {short_name}',
                f'Total Crop Production - {short_name}'
            ),
            vertical_spacing=0.12,
            specs=[[{"secondary_y": False}],
                   [{"secondary_y": False}],
                   [{"secondary_y": False}]]
        )

        # Row 1: Crop choices (filtered by focus_crop if specified)
        if not focus_crop or focus_crop.upper() == 'WHEAT':
            fig.add_trace(
                go.Scatter(
                    x=years, y=wheat_farmers,
                    mode='lines+markers',
                    name='Wheat Farmers',
                    line=dict(color='#DAA520', width=3),
                    marker=dict(size=8)
                ),
                row=1, col=1
            )

        if not focus_crop or focus_crop.upper() == 'MAIZE':
            fig.add_trace(
                go.Scatter(
                    x=years, y=maize_farmers,
                    mode='lines+markers',
                    name='Maize Farmers',
                    line=dict(color='#FFD700', width=3),
                    marker=dict(size=8)
                ),
            row=1, col=1
        )

        # Row 2: Income
        fig.add_trace(
            go.Scatter(
                x=years, y=total_income,
                mode='lines+markers',
                name='Total Income',
                line=dict(color='#2E8B57', width=3),
                marker=dict(size=8),
                fill='tozeroy'
            ),
            row=2, col=1
        )

        # Row 3: Production
        fig.add_trace(
            go.Scatter(
                x=years, y=total_production,
                mode='lines+markers',
                name='Total Production',
                line=dict(color='#4169E1', width=3),
                marker=dict(size=8),
                fill='tozeroy'
            ),
            row=3, col=1
        )

        # Update layout
        fig.update_xaxes(title_text="Year", row=3, col=1)
        fig.update_yaxes(title_text="Number of Farmers", row=1, col=1)
        fig.update_yaxes(title_text="Income (€)", row=2, col=1)
        fig.update_yaxes(title_text="Production (tons)", row=3, col=1)

        fig.update_layout(
            height=900,
            showlegend=True,
            title_text=f"CCA Simulation Results - {display_name}",
            title_x=0.5,
            hovermode='x unified',
            template='plotly_white'
        )

        # Save as HTML (primary output for frontend)
        output_html = self.output_dir / f"{scenario}_time_series.html"
        fig.write_html(str(output_html))

        return str(output_html)

    def create_scenario_comparison_charts(self,
                                          results_by_scenario: Dict) -> str:
        """
        Create comparison charts across RCP scenarios.

        Args:
            results_by_scenario: Dict mapping scenario -> results

        Returns:
            Path to saved HTML file
        """
        scenarios = list(results_by_scenario.keys())

        # Calculate averages for each scenario
        avg_income = []
        avg_production = []
        initial_wheat = []
        initial_maize = []
        final_wheat = []
        final_maize = []

        for scenario in scenarios:
            stats = results_by_scenario[scenario]['yearly_stats']
            if stats:
                avg_income.append(sum(s['total_income'] for s in stats) / len(stats))
                avg_production.append(sum(s['total_production'] for s in stats) / len(stats))
                initial_wheat.append(stats[0]['wheat_farmers'])
                initial_maize.append(stats[0]['maize_farmers'])
                final_wheat.append(stats[-1]['wheat_farmers'])
                final_maize.append(stats[-1]['maize_farmers'])

        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Average Total Income by Scenario',
                'Average Total Production by Scenario',
                'Crop Distribution: Initial vs Final Year',
                'Crop Evolution (Wheat vs Maize)'
            ),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )

        colors = ['#3498db', '#e74c3c', '#f39c12']  # Blue, Red, Orange

        # Get display names for scenarios
        scenario_labels = [get_scenario_display_name(s, use_case="cca") for s in scenarios]

        # Income comparison
        fig.add_trace(
            go.Bar(
                x=scenario_labels,
                y=avg_income,
                name='Avg Income',
                marker_color=colors[:len(scenarios)],
                text=[f'€{v:,.0f}' for v in avg_income],
                textposition='outside'
            ),
            row=1, col=1
        )

        # Production comparison
        fig.add_trace(
            go.Bar(
                x=scenario_labels,
                y=avg_production,
                name='Avg Production',
                marker_color=colors[:len(scenarios)],
                text=[f'{v:.1f}t' for v in avg_production],
                textposition='outside'
            ),
            row=1, col=2
        )

        # Chart 3: Initial vs Final crop distribution (stacked bar)
        for i, scenario_label in enumerate(scenario_labels):
            # Initial year (lighter colors)
            fig.add_trace(
                go.Bar(
                    x=[f"{scenario_label}<br>(Year 1)"],
                    y=[initial_wheat[i]],
                    name='Initial Wheat' if i == 0 else None,
                    marker_color='#DAA520',
                    showlegend=(i == 0),
                    text=[initial_wheat[i]],
                    textposition='inside',
                    legendgroup='initial'
                ),
                row=2, col=1
            )
            fig.add_trace(
                go.Bar(
                    x=[f"{scenario_label}<br>(Year 1)"],
                    y=[initial_maize[i]],
                    name='Initial Maize' if i == 0 else None,
                    marker_color='#FFD700',
                    showlegend=(i == 0),
                    text=[initial_maize[i]],
                    textposition='inside',
                    legendgroup='initial'
                ),
                row=2, col=1
            )

            # Final year (darker colors)
            fig.add_trace(
                go.Bar(
                    x=[f"{scenario_label}<br>(Final)"],
                    y=[final_wheat[i]],
                    name='Final Wheat' if i == 0 else None,
                    marker_color='#8B6914',  # Darker gold
                    showlegend=(i == 0),
                    text=[final_wheat[i]],
                    textposition='inside',
                    legendgroup='final'
                ),
                row=2, col=1
            )
            fig.add_trace(
                go.Bar(
                    x=[f"{scenario_label}<br>(Final)"],
                    y=[final_maize[i]],
                    name='Final Maize' if i == 0 else None,
                    marker_color='#B8860B',  # Darker yellow
                    showlegend=(i == 0),
                    text=[final_maize[i]],
                    textposition='inside',
                    legendgroup='final'
                ),
                row=2, col=1
            )

        # Chart 4: Crop change (wheat gain, maize loss)
        wheat_change = [final_wheat[i] - initial_wheat[i] for i in range(len(scenarios))]
        maize_change = [final_maize[i] - initial_maize[i] for i in range(len(scenarios))]

        fig.add_trace(
            go.Bar(
                x=scenario_labels,
                y=wheat_change,
                name='Wheat Change',
                marker_color='#2E8B57',  # Green for positive
                text=[f'{v:+d}' for v in wheat_change],
                textposition='outside'
            ),
            row=2, col=2
        )

        fig.add_trace(
            go.Bar(
                x=scenario_labels,
                y=maize_change,
                name='Maize Change',
                marker_color='#DC143C',  # Red for negative
                text=[f'{v:+d}' for v in maize_change],
                textposition='outside'
            ),
            row=2, col=2
        )

        # Update layout
        fig.update_yaxes(title_text="Income (€)", row=1, col=1)
        fig.update_yaxes(title_text="Production (tons)", row=1, col=2)
        fig.update_yaxes(title_text="Farmers", row=2, col=1)
        fig.update_yaxes(title_text="Change in Farmers", row=2, col=2)

        # Update barmode for stacked chart
        fig.update_layout(barmode='stack')

        fig.update_layout(
            height=800,
            showlegend=True,  # Enable legend to show crop types
            title_text="Multi-Scenario Comparison (Climate Change Adaptation)",
            title_x=0.5,
            template='plotly_white'
        )

        # Save as HTML (primary output for frontend)
        output_html = self.output_dir / "scenario_comparison.html"
        fig.write_html(str(output_html))

        return str(output_html)

    def create_pv_installation_charts(self,
                                      results_by_scenario: Dict) -> str:
        """
        Create PV installation comparison charts.

        Args:
            results_by_scenario: Dict mapping scenario -> results

        Returns:
            Path to saved HTML file
        """
        scenarios = []
        total_capacity = []
        num_installations = []
        total_revenue = []

        for scenario, results in results_by_scenario.items():
            model = results.get('model')
            if model and hasattr(model, 'pv_developer_agents') and model.pv_developer_agents:
                # Get user-friendly display name
                scenario_display = get_scenario_display_name(scenario, use_case="cca")
                for pv_dev in model.pv_developer_agents:
                    scenarios.append(scenario_display)
                    total_capacity.append(pv_dev.total_capacity_installed)
                    num_installations.append(len(pv_dev.pv_installations))
                    total_revenue.append(pv_dev.annual_revenue)

        if not scenarios:
            return None

        # Create subplots
        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=(
                'Total PV Capacity (kW)',
                'Number of Installations',
                'Annual Revenue (€/year)'
            ),
            vertical_spacing=0.15
        )

        # Capacity
        fig.add_trace(
            go.Bar(
                x=scenarios,
                y=total_capacity,
                name='Capacity (kW)',
                marker_color='#FF6B35'
            ),
            row=1, col=1
        )

        # Installations
        fig.add_trace(
            go.Bar(
                x=scenarios,
                y=num_installations,
                name='Installations',
                marker_color='#F7931E'
            ),
            row=1, col=2
        )

        # Revenue
        fig.add_trace(
            go.Bar(
                x=scenarios,
                y=total_revenue,
                name='Revenue (€)',
                marker_color='#FDC830'
            ),
            row=1, col=3
        )

        # Update layout
        fig.update_yaxes(title_text="Capacity (kW)", row=1, col=1)
        fig.update_yaxes(title_text="Count", row=1, col=2)
        fig.update_yaxes(title_text="Revenue (€/year)", row=1, col=3)

        fig.update_layout(
            height=500,
            showlegend=False,
            title_text="PV Installation Analysis - Cumulative Results by Company<br><sub>Total installations made during simulation (all happen in year 2021)</sub>",
            title_x=0.5,
            template='plotly_white',
            margin=dict(t=120, b=50, l=50, r=50)
        )

        # Save as JSON for react-plotly.js (responsive)
        output_json = self.output_dir / "pv_installations_plotly.json"
        import json
        layout = fig.to_dict()['layout']
        # Remove width to allow responsive sizing
        layout.pop('width', None)
        with open(output_json, 'w') as f:
            json.dump({
                'data': fig.to_dict()['data'],
                'layout': layout
            }, f)

        return str(output_json)

    def _add_suitability_layer(self, m: folium.Map, crop: str, year: int, scenario: str):
        """
        Add LUSA suitability raster layer to the map (similar to MLU CleanGISVisualizer).

        Args:
            m: Folium map object
            crop: Crop name (WHEAT or MAIZE)
            year: Year to visualize
            scenario: RCP scenario (rcp26, rcp45, rcp85)
        """
        if not self.data_path:
            print(f"   ⚠️  data_path not provided - skipping suitability layer for {crop}")
            return

        try:
            # Map scenario to RCP code
            scenario_map = {'rcp26': 'RCP26', 'rcp45': 'RCP45', 'rcp85': 'RCP85',
                            'optimistic': 'RCP26', 'moderate': 'RCP45', 'pessimistic': 'RCP85'}
            rcp_code = scenario_map.get(scenario.lower(), scenario.upper())

            # Path to LUSA crop suitability
            crop_path = self.data_path / f'LUSA/Predictions/{crop}/{rcp_code}/{crop}_{rcp_code}.nc'
            if not crop_path.exists():
                print(f"   ⚠️  LUSA file not found: {crop_path}")
                return

            # Load LUSA data
            ds = xr.open_dataset(crop_path)
            crop_data = ds['suitability_score'].sel(time=str(year), method='nearest')

            # Ensure lat/lon are in correct order (descending lat)
            if crop_data.lat[0] < crop_data.lat[-1]:
                crop_data = crop_data.isel(lat=slice(None, None, -1))

            # Subset to Thessaloniki region
            crop_subset = crop_data.sel(
                lat=slice(self.lat_max, self.lat_min),
                lon=slice(self.lon_min, self.lon_max)
            )

            # Color schemes (from MLU CleanGISVisualizer)
            colors = {
                'WHEAT': ['#dc2626', '#f59e0b', '#fbbf24', '#a3e635', '#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#3b82f6', '#2563eb'],
                'MAIZE': ['#7c3aed', '#a78bfa', '#c4b5fd', '#fbbf24', '#f59e0b', '#f97316', '#ea580c', '#dc2626', '#b91c1c', '#991b1b']
            }

            # Create raster layer
            folium.raster_layers.ImageOverlay(
                name=f'{crop} Suitability',
                image=crop_subset.values,
                bounds=[[self.lat_min, self.lon_min], [self.lat_max, self.lon_max]],
                opacity=0.6,
                interactive=True,
                cross_origin=False,
                zindex=1,
                colormap=lambda x: colors[crop][min(int(x / 10), 9)] if not np.isnan(x) else '#00000000'
            ).add_to(m)

            print(f"   ✅ Added {crop} suitability layer for year {year}")
        except Exception as e:
            print(f"   ⚠️  Could not add {crop} suitability layer: {e}")

    def create_farmer_location_map(self,
                                   yearly_snapshots: List[Dict],
                                   scenario: str,
                                   model=None,
                                   scenario_display: str = None,
                                   focus_crop: str = None) -> str:
        """
        Create Folium map showing farmer locations and crop choices with year selector.

        Args:
            yearly_snapshots: List of dicts with 'year' and 'farmers' keys
            scenario: RCP scenario name (internal code)
            model: Optional LandUseModel instance for PV installations (final state)
            scenario_display: User-friendly display name (optional)
            focus_crop: Optional crop to focus on (WHEAT, MAIZE, or None for all)

        Returns:
            Path to saved HTML file
        """
        # Use display name if provided, otherwise use scenario code
        display_name = scenario_display if scenario_display else scenario.upper()
        if not yearly_snapshots:
            return None

        # Calculate map center from first year (all farmers - no filtering needed)
        first_year_farmers = yearly_snapshots[0]['farmers']
        if not first_year_farmers:
            return None

        # Use all farmers (spatial bounds already validated during model initialization)
        land_farmers = first_year_farmers

        if not land_farmers:
            return None

        lats = [f['lat'] for f in land_farmers]
        lons = [f['lon'] for f in land_farmers]
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=9,
            tiles='OpenStreetMap',
            control_scale=True
        )

        # Add basemap options (like MLU)
        folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
        folium.TileLayer('Esri WorldImagery', name='Satellite').add_to(m)

        # NOTE: Suitability layers removed - CCA map focuses on temporal farmer decisions
        # Use MLU maps for spatial suitability visualization

        # Add title
        title_html = f'''
        <div id="map-title" style="position: fixed;
                    top: 10px; left: 50px; width: 450px; height: 80px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:16px; padding: 10px">
        <b>CCA Simulation - {display_name}</b><br>
        Farmer Locations & Crop Choices<br>
        <span id="year-display" style="color: #2E8B57; font-weight: bold;">Year: {yearly_snapshots[0]['year']}</span>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))

        # Create a FeatureGroup for each year - track the Folium object IDs
        year_groups = {}
        year_group_ids = {}  # Map year to the Folium-generated variable name
        years = [s['year'] for s in yearly_snapshots]

        for snapshot in yearly_snapshots:
            year = snapshot['year']
            is_first_year = (year == years[0])

            # Use all farmers (no filtering - bounds already validated)
            farmers_year = snapshot['farmers']

            # Create FeatureGroup - always show=True so Folium adds it to map
            year_group = folium.FeatureGroup(
                name=f"year_{year}",
                show=True,
                overlay=True
            )

            # Add farmer markers for this year (filtered by focus_crop if specified)
            for farmer in farmers_year:
                # Skip if location is in the sea
                if not globe.is_land(farmer['lat'], farmer['lon']):
                    continue

                crop = farmer['crop']
                has_pv = farmer.get('has_pv_installation', False)

                # Skip this farmer if focus_crop is set and doesn't match
                if focus_crop and not has_pv and crop != focus_crop.upper():
                    continue  # Filter out non-matching crops

                # Check if farmer has PV installation
                if has_pv:
                    # Farmer has PV installation - show as PV
                    marker_color = 'red'
                    icon_name = 'bolt'  # Lightning bolt for solar/electric
                    display_type = "PV Installation"
                    pv_lease_income = farmer.get('pv_lease_income', 0)
                    pv_year = farmer.get('pv_installation_year', 'Unknown')

                    popup_html = f"""
                    <div style="font-family: Arial; font-size: 12px;">
                        <b>Farmer {farmer['id']}</b><br>
                        Year: {year}<br>
                        Status: <b>PV Installation</b><br>
                        PV Since: {pv_year}<br>
                        Land: {farmer['land_hectares']:.1f} ha<br>
                        Lease Income: €{pv_lease_income:,.0f}/year<br>
                        Vulnerability: {farmer['vulnerability_score']:.2f}
                    </div>
                    """
                    tooltip_text = f"Farmer {farmer['id']}: PV Installation (€{pv_lease_income:,.0f}/yr)"

                else:
                    # Farmer is actively farming crops
                    if crop == "WHEAT":
                        marker_color = 'orange'
                        icon_name = 'leaf'
                    elif crop == "MAIZE":
                        marker_color = 'lightgreen'
                        icon_name = 'leaf'
                    else:
                        marker_color = 'gray'
                        icon_name = 'question'

                    display_type = "Farming"
                    popup_html = f"""
                    <div style="font-family: Arial; font-size: 12px;">
                        <b>Farmer {farmer['id']}</b><br>
                        Year: {year}<br>
                        Status: <b>Farming</b><br>
                        Crop: {crop}<br>
                        Land: {farmer['land_hectares']:.1f} ha<br>
                        Income: €{farmer['annual_income']:,.0f}<br>
                        Yield: {farmer['actual_yield']:.2f} t/ha<br>
                        Vulnerability: {farmer['vulnerability_score']:.2f}
                    </div>
                    """
                    tooltip_text = f"Farmer {farmer['id']}: {crop}"

                folium.Marker(
                    location=[farmer['lat'], farmer['lon']],
                    popup=folium.Popup(popup_html, max_width=250),
                    icon=folium.Icon(color=marker_color, icon=icon_name, prefix='fa'),
                    tooltip=tooltip_text
                ).add_to(year_group)

            year_groups[year] = year_group
            # Store the Folium internal ID (this will be the JavaScript variable name)
            year_group_ids[year] = year_group.get_name()
            year_group.add_to(m)

        # Detect which crops/types are actually present (filtered by focus_crop if specified)
        crops_present = set()
        has_pv = False
        for snapshot in yearly_snapshots:
            for farmer in snapshot['farmers']:
                if farmer.get('has_pv_installation', False):
                    has_pv = True
                elif farmer.get('crop'):
                    crops_present.add(farmer['crop'])

        # Build dynamic legend based on what's present AND focus_crop filter
        legend_items = []
        if 'WHEAT' in crops_present and (not focus_crop or focus_crop.upper() == 'WHEAT'):
            legend_items.append('<i class="fa fa-leaf" style="color:orange"></i> Wheat Farmer')
        if 'MAIZE' in crops_present and (not focus_crop or focus_crop.upper() == 'MAIZE'):
            legend_items.append('<i class="fa fa-leaf" style="color:lightgreen"></i> Maize Farmer')
        if has_pv and not focus_crop:  # PV only shown when no crop focus (full view)
            legend_items.append('<i class="fa fa-bolt" style="color:red"></i> PV Installation')

        # Calculate legend height based on number of items
        legend_height = 60 + (len(legend_items) * 20)  # Base 60px + 20px per item

        legend_html = f'''
        <div style="position: fixed;
                    bottom: 50px; right: 50px; width: 220px; height: {legend_height}px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:13px; padding: 10px">
        <b>Legend</b><br>
        {('<br>'.join(legend_items))}
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # Build JavaScript that directly references the Folium-generated FeatureGroup variables
        # Create navigation with slider bar and Previous/Next buttons
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
                <button id="prev-year"
                        style="background-color: #3b82f6; color: white; border: none;
                               padding: 6px 12px; cursor: pointer; border-radius: 4px;
                               font-size: 12px; font-weight: bold; transition: all 0.2s; flex-shrink: 0;">
                    ◀
                </button>
                <input type="range"
                       id="year-slider"
                       min="0"
                       max="{len(years) - 1}"
                       value="0"
                       step="1"
                       style="flex: 1; cursor: pointer; height: 8px; -webkit-appearance: none; appearance: none;
                              background: linear-gradient(to right, #3b82f6 0%, #3b82f6 0%, #e5e7eb 0%, #e5e7eb 100%);
                              border-radius: 5px; outline: none;">
                <button id="next-year"
                        style="background-color: #3b82f6; color: white; border: none;
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
        <style>
            #year-slider::-webkit-slider-thumb {{
                -webkit-appearance: none;
                appearance: none;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: #3b82f6;
                cursor: pointer;
                border: 3px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            #year-slider::-moz-range-thumb {{
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: #3b82f6;
                cursor: pointer;
                border: 3px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            #year-slider::-webkit-slider-thumb:hover {{
                background: #2563eb;
                transform: scale(1.1);
            }}
            #year-slider::-moz-range-thumb:hover {{
                background: #2563eb;
                transform: scale(1.1);
            }}
        </style>
        </div>
        '''

        year_selector_html += '''
        <script>
        setTimeout(function() {
            var mapElement = document.querySelector('.folium-map');
            if (mapElement) {
                var mapId = mapElement.id;
                var mapObj = window[mapId];

                if (mapObj) {
                    var yearLayers = {};
        '''

        # Map years to their actual Folium-generated FeatureGroup variable names
        for year in years:
            fg_var_name = year_group_ids[year]
            year_selector_html += f'''
                    yearLayers['{year}'] = {fg_var_name};
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

                        // Update slider value
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

                        // Hide all year layers
        '''

        for year in years:
            year_selector_html += f'''
                        if (yearLayers['{year}'] && mapObj.hasLayer(yearLayers['{year}'])) {{
                            mapObj.removeLayer(yearLayers['{year}']);
                        }}
            '''

        year_selector_html += '''

                        // Show selected year layer
                        if (yearLayers[selectedYear] && !mapObj.hasLayer(yearLayers[selectedYear])) {
                            mapObj.addLayer(yearLayers[selectedYear]);
                        }
                    }

                    // Hide all layers except first year initially
        '''

        for i, year in enumerate(years):
            if i > 0:  # Skip first year
                year_selector_html += f'''
                    if (yearLayers['{year}']) {{
                        mapObj.removeLayer(yearLayers['{year}']);
                    }}
            '''

        year_selector_html += '''

                    // Add event listener for slider
                    slider.addEventListener('input', function() {
                        var yearIndex = parseInt(this.value);
                        updateYearDisplay(yearIndex);
                    });

                    // Add event listeners for buttons
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

                    // Add hover effects to buttons
                    prevBtn.addEventListener('mouseenter', function() {
                        if (!this.disabled) this.style.backgroundColor = '#2563eb';
                    });
                    prevBtn.addEventListener('mouseleave', function() {
                        if (!this.disabled) this.style.backgroundColor = '#3b82f6';
                    });

                    nextBtn.addEventListener('mouseenter', function() {
                        if (!this.disabled) this.style.backgroundColor = '#2563eb';
                    });
                    nextBtn.addEventListener('mouseleave', function() {
                        if (!this.disabled) this.style.backgroundColor = '#3b82f6';
                    });

                    // Initialize
                    updateYearDisplay(0);
                }
            }

        }, 1000);
        </script>
        '''

        m.get_root().html.add_child(folium.Element(year_selector_html))

        # Add layer control for basemaps (no suitability layers)
        folium.LayerControl(
            position='topright',
            collapsed=True,
            autoZIndex=True
        ).add_to(m)

        # NOTE: Suitability legend removed - CCA map shows farmer decisions only
        # For suitability visualization, use MLU maps

        # Save
        output_file = self.output_dir / f"{scenario}_farmer_map.html"
        m.save(str(output_file))

        return str(output_file)

    def create_climate_vulnerability_map(self,
                                         yearly_snapshots: List[Dict],
                                         scenario: str,
                                         scenario_display: str = None) -> str:
        """
        Create heatmap showing climate vulnerability across farmer locations with year selector.

        Args:
            yearly_snapshots: List of dicts with 'year' and 'farmers' keys
            scenario: RCP scenario name (internal code)
            scenario_display: User-friendly display name (optional)

        Returns:
            Path to saved HTML file
        """
        # Use display name if provided, otherwise use scenario code
        display_name = scenario_display if scenario_display else scenario.upper()
        if not yearly_snapshots:
            return None

        # Calculate map center from first year (all farmers - no filtering needed)
        first_year_farmers = yearly_snapshots[0]['farmers']
        if not first_year_farmers:
            return None

        # Use all farmers (spatial bounds already validated during model initialization)
        land_farmers = first_year_farmers

        if not land_farmers:
            return None

        lats = [f['lat'] for f in land_farmers]
        lons = [f['lon'] for f in land_farmers]
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=9,
            tiles='OpenStreetMap'
        )

        # Add title with year display
        title_html = f'''
        <div id="map-title" style="position: fixed;
                    top: 10px; left: 50px; width: 400px; height: 80px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:16px; padding: 10px">
        <b>Climate Vulnerability - {display_name}</b><br>
        Farmer Climate Risk Assessment<br>
        <span id="year-display" style="color: #2E8B57; font-weight: bold;">Year: {yearly_snapshots[0]['year']}</span>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))

        # Create a FeatureGroup for each year
        year_groups = {}
        year_group_ids = {}
        years = [s['year'] for s in yearly_snapshots]

        for snapshot in yearly_snapshots:
            year = snapshot['year']

            # Use all farmers (no filtering - bounds already validated)
            farmers_year = snapshot['farmers']

            if not farmers_year:
                continue

            year_group = folium.FeatureGroup(
                name=f"vulnerability_{year}",
                show=True,
                overlay=True
            )

            # Prepare heatmap data for this year
            heat_data = []
            for farmer in farmers_year:
                # Skip if location is in the sea
                if not globe.is_land(farmer['lat'], farmer['lon']):
                    continue

                vulnerability = farmer.get('vulnerability_score', 0.5)
                heat_data.append([farmer['lat'], farmer['lon'], vulnerability])

            # Add heatmap layer for this year
            plugins.HeatMap(
                heat_data,
                min_opacity=0.3,
                radius=25,
                blur=35,
                gradient={'0.0': 'green', '0.5': 'yellow', '0.75': 'orange', '1.0': 'red'}
            ).add_to(year_group)

            # Add farmer markers for this year
            for farmer in farmers_year:
                # Skip if location is in the sea
                if not globe.is_land(farmer['lat'], farmer['lon']):
                    continue

                vulnerability = farmer.get('vulnerability_score', 0.5)

                # Color by vulnerability
                if vulnerability < 0.3:
                    color = 'green'
                elif vulnerability < 0.6:
                    color = 'orange'
                else:
                    color = 'red'

                popup_html = f"""
                <div style="font-family: Arial; font-size: 12px;">
                    <b>Farmer {farmer['id']}</b><br>
                    Year: {year}<br>
                    Vulnerability: {vulnerability:.2f}<br>
                    Adaptation Capacity: {farmer.get('adaptation_capacity', 0):.2f}<br>
                    Crop: {farmer['crop']}<br>
                    Income: €{farmer.get('annual_income', 0):,.0f}
                </div>
                """

                folium.CircleMarker(
                    location=[farmer['lat'], farmer['lon']],
                    radius=8,
                    popup=folium.Popup(popup_html, max_width=200),
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    tooltip=f"Vulnerability: {vulnerability:.2f}"
                ).add_to(year_group)

            year_groups[year] = year_group
            year_group_ids[year] = year_group.get_name()
            year_group.add_to(m)

        # Add legend
        legend_html = '''
        <div style="position: fixed;
                    bottom: 50px; right: 50px; width: 200px; height: 140px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:14px; padding: 10px">
        <b>Vulnerability Level</b><br>
        <i class="fa fa-circle" style="color:green"></i> Low (< 0.3)<br>
        <i class="fa fa-circle" style="color:orange"></i> Medium (0.3-0.6)<br>
        <i class="fa fa-circle" style="color:red"></i> High (> 0.6)<br>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # Build JavaScript for year selector - slider bar with Previous/Next buttons
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
                <button id="prev-year"
                        style="background-color: #3b82f6; color: white; border: none;
                               padding: 6px 12px; cursor: pointer; border-radius: 4px;
                               font-size: 12px; font-weight: bold; transition: all 0.2s; flex-shrink: 0;">
                    ◀
                </button>
                <input type="range"
                       id="year-slider"
                       min="0"
                       max="{len(years) - 1}"
                       value="0"
                       step="1"
                       style="flex: 1; cursor: pointer; height: 8px; -webkit-appearance: none; appearance: none;
                              background: linear-gradient(to right, #3b82f6 0%, #3b82f6 0%, #e5e7eb 0%, #e5e7eb 100%);
                              border-radius: 5px; outline: none;">
                <button id="next-year"
                        style="background-color: #3b82f6; color: white; border: none;
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
        <style>
            #year-slider::-webkit-slider-thumb {{
                -webkit-appearance: none;
                appearance: none;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: #3b82f6;
                cursor: pointer;
                border: 3px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            #year-slider::-moz-range-thumb {{
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: #3b82f6;
                cursor: pointer;
                border: 3px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            #year-slider::-webkit-slider-thumb:hover {{
                background: #2563eb;
                transform: scale(1.1);
            }}
            #year-slider::-moz-range-thumb:hover {{
                background: #2563eb;
                transform: scale(1.1);
            }}
        </style>
        </div>
        '''

        year_selector_html += '''
        <script>
        setTimeout(function() {
            var mapElement = document.querySelector('.folium-map');
            if (mapElement) {
                var mapId = mapElement.id;
                var mapObj = window[mapId];

                if (mapObj) {
                    var yearLayers = {};
        '''

        # Map years to their actual Folium-generated FeatureGroup variable names
        for year in years:
            if year in year_group_ids:
                fg_var_name = year_group_ids[year]
                year_selector_html += f'''
                    yearLayers['{year}'] = {fg_var_name};
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

                        // Update slider value
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

                        // Hide all year layers
        '''

        for year in years:
            if year in year_group_ids:
                year_selector_html += f'''
                        if (yearLayers['{year}'] && mapObj.hasLayer(yearLayers['{year}'])) {{
                            mapObj.removeLayer(yearLayers['{year}']);
                        }}
            '''

        year_selector_html += '''

                        // Show selected year layer
                        if (yearLayers[selectedYear] && !mapObj.hasLayer(yearLayers[selectedYear])) {
                            mapObj.addLayer(yearLayers[selectedYear]);
                        }
                    }

                    // Hide all layers except first year initially
        '''

        for i, year in enumerate(years):
            if i > 0 and year in year_group_ids:  # Skip first year
                year_selector_html += f'''
                    if (yearLayers['{year}']) {{
                        mapObj.removeLayer(yearLayers['{year}']);
                    }}
            '''

        year_selector_html += '''

                    // Add event listener for slider
                    slider.addEventListener('input', function() {
                        var yearIndex = parseInt(this.value);
                        updateYearDisplay(yearIndex);
                    });

                    // Add event listeners for buttons
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

                    // Add hover effects to buttons
                    prevBtn.addEventListener('mouseenter', function() {
                        if (!this.disabled) this.style.backgroundColor = '#2563eb';
                    });
                    prevBtn.addEventListener('mouseleave', function() {
                        if (!this.disabled) this.style.backgroundColor = '#3b82f6';
                    });

                    nextBtn.addEventListener('mouseenter', function() {
                        if (!this.disabled) this.style.backgroundColor = '#2563eb';
                    });
                    nextBtn.addEventListener('mouseleave', function() {
                        if (!this.disabled) this.style.backgroundColor = '#3b82f6';
                    });

                    // Initialize
                    updateYearDisplay(0);
                }
            }

        }, 1000);
        </script>
        '''

        m.get_root().html.add_child(folium.Element(year_selector_html))

        # Save
        output_file = self.output_dir / f"{scenario}_vulnerability_map.html"
        m.save(str(output_file))

        return str(output_file)


def generate_all_visualizations(results_by_scenario: Dict,
                                output_dir: str = "results/visualizations",
                                data_path: str = None,
                                focus_crop: str = None) -> Dict[str, str]:
    """
    Generate all visualizations for CCA simulation results.

    Args:
        results_by_scenario: Dict mapping scenario -> results
        output_dir: Directory to save visualizations
        data_path: Path to PILOT_THESSALONIKI_DATA (optional, for suitability layers)
        focus_crop: Optional crop to focus visualizations on (WHEAT, MAIZE, or None for all)

    Returns:
        Dict mapping visualization type -> file path
    """
    visualizer = CCAVisualizer(output_dir=output_dir, data_path=data_path)

    generated_files = {}

    print(f"\n{'='*80}")
    print("GENERATING INTERACTIVE VISUALIZATIONS")
    print("="*80)

    # Time series for each scenario
    print("\n1. Creating time series charts...")
    for scenario, results in results_by_scenario.items():
        # Get user-friendly display name
        scenario_display = get_scenario_display_name(scenario, use_case="cca")
        file_path = visualizer.create_time_series_charts(
            results['yearly_stats'],
            scenario,
            scenario_display,
            focus_crop=focus_crop  # Pass focus_crop filter
        )
        generated_files[f'{scenario}_time_series'] = file_path
        print(f"   ✅ {scenario_display}: {file_path}")

    # Scenario comparison (only if multiple scenarios)
    if len(results_by_scenario) > 1:
        print("\n2. Creating scenario comparison charts...")
        file_path = visualizer.create_scenario_comparison_charts(results_by_scenario)
        generated_files['scenario_comparison'] = file_path
        print(f"   ✅ Comparison: {file_path}")
    else:
        print("\n2. Skipping scenario comparison (only one scenario)")

    # PV installations (if any)
    print("\n3. Creating PV installation charts...")
    file_path = visualizer.create_pv_installation_charts(results_by_scenario)
    if file_path:
        generated_files['pv_installations'] = file_path
        print(f"   ✅ PV Analysis: {file_path}")
    else:
        print(f"   ⚠️  No PV installations to visualize")

    # GIS maps for each scenario
    print("\n4. Creating GIS maps...")
    for scenario, results in results_by_scenario.items():
        # Get user-friendly display name
        scenario_display = get_scenario_display_name(scenario, use_case="cca")
        model = results.get('model')
        yearly_snapshots = results.get('yearly_farmer_snapshots', [])

        if model:
            # Farmer location map (multi-year interactive)
            try:
                if yearly_snapshots:
                    file_path = visualizer.create_farmer_location_map(
                        yearly_snapshots,
                        scenario,
                        model=model,
                        scenario_display=scenario_display,
                        focus_crop=focus_crop  # Pass focus_crop filter
                    )
                    if file_path:
                        generated_files[f'{scenario}_farmer_map'] = file_path
                        print(f"   ✅ {scenario_display} Farmer Map (Multi-Year): {file_path}")
                else:
                    print(f"   ⚠️  No yearly snapshots available for {scenario_display} farmer map")
            except Exception as e:
                print(f"   ⚠️  Could not create {scenario_display} farmer map: {e}")

            # Vulnerability map (multi-year interactive)
            try:
                if yearly_snapshots:
                    file_path = visualizer.create_climate_vulnerability_map(yearly_snapshots, scenario, scenario_display)
                    if file_path:
                        generated_files[f'{scenario}_vulnerability_map'] = file_path
                        print(f"   ✅ {scenario_display} Vulnerability Map (Multi-Year): {file_path}")
                else:
                    print(f"   ⚠️  No yearly snapshots available for {scenario_display} vulnerability map")
            except Exception as e:
                print(f"   ⚠️  Could not create {scenario_display} vulnerability map: {e}")

    print(f"\n{'='*80}")
    print(f"✅ All visualizations saved to: {Path(output_dir).absolute()}")
    print("="*80)

    return generated_files
