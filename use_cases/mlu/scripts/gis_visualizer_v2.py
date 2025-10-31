"""
Clean GIS Visualization with Shadcn-inspired Design

Features:
- Single crop selection (mutually exclusive)
- Clean, non-overlapping legends
- Shadcn color palette
- Better layer organization
"""

import folium
from folium import plugins
import numpy as np
import xarray as xr
from pathlib import Path
from typing import Optional
import branca.colormap as cm
import sys

# Import scenario utilities for display names
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from scenario_utils import get_scenario_display_name


class CleanGISVisualizer:
    """Clean GIS visualizer with shadcn design principles."""

    def __init__(self, result_collector, data_path: str):
        self.collector = result_collector
        self.scenario = result_collector.scenario
        self.scenario_display = get_scenario_display_name(self.scenario)
        self.data_path = Path(data_path)

        # Thessaloniki bounds
        self.lat_min, self.lat_max = 40.2, 40.9
        self.lon_min, self.lon_max = 22.4, 23.4
        self.center_lat = (self.lat_min + self.lat_max) / 2
        self.center_lon = (self.lon_min + self.lon_max) / 2

        # Shadcn color palettes
        self.color_schemes = {
            'WHEAT': {
                'name': 'Wheat Suitability',
                'colors': ['#dc2626', '#f59e0b', '#fbbf24', '#a3e635', '#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#3b82f6', '#2563eb'],
                'icon': '🌾',
                'description': 'Blue gradient: Red (low) → Green → Blue (high)'
            },
            'MAIZE': {
                'name': 'Maize Suitability',
                'colors': ['#7c3aed', '#a78bfa', '#c4b5fd', '#fbbf24', '#f59e0b', '#f97316', '#ea580c', '#dc2626', '#b91c1c', '#991b1b'],
                'icon': '🌽',
                'description': 'Amber gradient: Purple (low) → Yellow → Amber (high)'
            }
        }

    def create_clean_map(
        self,
        year: int,
        crops: list = ['WHEAT'],
        show_soil: bool = False,
        show_elevation: bool = False,
        show_temperature: bool = False,
        show_farmers: bool = True,
        output_file: str = 'gis_clean_map.html'
    ):
        """
        Create clean GIS map with selected crops.

        Args:
            year: Year to visualize
            crops: List of crops to show ['WHEAT'] or ['MAIZE'] or ['WHEAT', 'MAIZE']
            show_soil: Include soil pH layer
            show_elevation: Include elevation layer
            show_temperature: Include temperature layer
            show_farmers: Include farmer parcels
            output_file: Output HTML file
        """
        print(f"\n📍 Creating Clean GIS Map")
        print(f"   Crops: {', '.join([self.color_schemes[c]['icon'] + ' ' + c for c in crops])}")
        print(f"   Year: {year}")
        print(f"   Region: Thessaloniki")

        # Create base map with OpenStreetMap (as before)
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=10,
            tiles='OpenStreetMap',  # Default OpenStreetMap
            control_scale=True,
            prefer_canvas=True
        )

        # Add basemap options (as requested)
        folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
        folium.TileLayer('Esri WorldImagery', name='Satellite').add_to(m)

        # Add suitability layers for each selected crop
        for crop in crops:
            self._add_clean_suitability(m, crop, year)

        # Optional layers (hidden by default)
        if show_elevation:
            self._add_clean_elevation(m)

        if show_temperature:
            self._add_clean_temperature(m, year)

        if show_farmers:
            self._add_clean_farmers(m, year, crops)
            # Add spatial neighbor connections (NEW!)
            self._add_spatial_network(m, year, crops)

        # Add custom legend for all selected crops (bottom right, no overlap)
        self._add_custom_legend(m, crops)

        # Add layer control (top right)
        folium.LayerControl(
            position='topright',
            collapsed=True,  # Collapsed by default
            autoZIndex=True
        ).add_to(m)

        # Add mouse coordinates (bottom left)
        plugins.MousePosition(
            position='bottomleft',
            separator=' | ',
            prefix='Coordinates: '
        ).add_to(m)

        # Add fullscreen button
        plugins.Fullscreen(position='topleft').add_to(m)

        # Save
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(output_path))
        print(f"\n✅ Clean GIS Map saved: {output_path.absolute()}")

        return m

    def _add_clean_suitability(self, m: folium.Map, crop: str, year: int):
        """Add clean crop suitability layer."""
        print(f"   {self.color_schemes[crop]['icon']} Adding {crop} suitability layer")

        # Load data
        rcp_label = self.scenario.upper()
        lusa_file = self.data_path / crop.upper() / f"{rcp_label}_LUSA_PREDICTIONS.nc"

        if not lusa_file.exists():
            print(f"      ⚠️  File not found: {lusa_file}")
            return

        ds = xr.open_dataset(lusa_file)
        scores = ds.sel(time=f"{year}-01-01", method="nearest").score

        # Filter to region
        scores_region = scores.sel(
            lat=slice(self.lat_min, self.lat_max),
            lon=slice(self.lon_min, self.lon_max)
        )

        # Create clean tile layer using Folium's built-in choropleth
        # Convert to grid cells
        lats = scores_region.lat.values
        lons = scores_region.lon.values
        values = scores_region.values

        # Get color scheme
        colors = self.color_schemes[crop]['colors']

        # Create feature group
        fg = folium.FeatureGroup(name=f"{crop} Suitability", show=True)

        # Add each grid cell as a rectangle
        for i in range(len(lats) - 1):
            for j in range(len(lons) - 1):
                val = values[i, j]
                if np.isnan(val) or val <= 0:
                    continue

                # Normalize value to color index
                color_idx = int((val / 100) * (len(colors) - 1))
                color_idx = min(color_idx, len(colors) - 1)
                color = colors[color_idx]

                # Create rectangle
                bounds = [
                    [lats[i + 1], lons[j]],
                    [lats[i], lons[j + 1]]
                ]

                folium.Rectangle(
                    bounds=bounds,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.6,
                    weight=0,  # No border
                    popup=f"<b>{crop}</b><br>Suitability: {val:.1f}/100",
                    tooltip=f"{val:.1f}"
                ).add_to(fg)

        fg.add_to(m)

    def _add_clean_elevation(self, m: folium.Map):
        """Add elevation layer (subtle, gray scale)."""
        print(f"   ⛰️  Adding elevation layer")
        # Implementation similar but with grayscale palette
        pass

    def _add_clean_temperature(self, m: folium.Map, year: int):
        """Add temperature layer (red-blue scale)."""
        print(f"   🌡️  Adding temperature layer")
        # Implementation with red-blue palette
        pass

    def _add_clean_farmers(self, m: folium.Map, year: int, crops: list):
        """Add farmer and solar PV parcel markers (clean, minimal style)."""
        print(f"   👨‍🌾 Adding land parcels (agriculture + solar PV)")

        spatial_data = self.collector.get_spatial_data(year)
        if not spatial_data or 'parcels' not in spatial_data:
            return

        parcels = spatial_data['parcels']

        # Create feature groups for agriculture and solar PV
        fg_farm = folium.FeatureGroup(name='Agricultural Parcels', show=True)
        fg_solar = folium.FeatureGroup(name='Solar PV Parcels', show=True)

        for parcel in parcels:
            land_use = parcel.get('land_use', 'agriculture')
            crop = parcel['current_crop']

            # Skip agricultural parcels that don't match selected crops
            if land_use == 'agriculture' and crop not in crops:
                continue

            # Validate coordinates are within Thessaloniki bounds (fix "in sea" issue!)
            lat, lon = parcel['lat'], parcel['lon']
            if not (self.lat_min <= lat <= self.lat_max and self.lon_min <= lon <= self.lon_max):
                print(f"      ⚠️  Skipping parcel outside bounds: ({lat:.4f}, {lon:.4f})")
                continue

            # Different popup/marker for solar PV vs agriculture
            if land_use == 'solar_pv':
                # Solar PV popup
                energy_kwh = parcel.get('annual_energy_kwh', 0)
                popup_html = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                            padding: 12px; min-width: 200px;">
                    <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;
                               color: #0f172a; border-bottom: 2px solid #eab308; padding-bottom: 8px;">
                        ☀️ SOLAR PV
                    </div>
                    <div style="font-size: 14px; color: #475569; line-height: 1.6;">
                        <div style="margin: 4px 0;">
                            <span style="color: #64748b;">📍 Location:</span>
                            <span style="font-weight: 500;">{lat:.4f}, {lon:.4f}</span>
                        </div>
                        <div style="margin: 4px 0;">
                            <span style="color: #64748b;">⚡ Energy:</span>
                            <span style="font-weight: 500; color: #eab308;">{energy_kwh:,.0f} kWh/year</span>
                        </div>
                        <div style="margin: 4px 0;">
                            <span style="color: #64748b;">💰 Income:</span>
                            <span style="font-weight: 500; color: #3b82f6;">€{parcel['annual_income']:,.0f}/year</span>
                        </div>
                    </div>
                </div>
                """
                marker_color = '#eab308'  # Yellow for solar
                icon = '☀️'
                tooltip_text = f"Solar PV: {energy_kwh:,.0f} kWh/year"
                target_fg = fg_solar
            else:
                # Agricultural popup
                popup_html = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                            padding: 12px; min-width: 200px;">
                    <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;
                               color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px;">
                        {self.color_schemes[crop]['icon']} {crop}
                    </div>
                    <div style="font-size: 14px; color: #475569; line-height: 1.6;">
                        <div style="margin: 4px 0;">
                            <span style="color: #64748b;">📍 Location:</span>
                            <span style="font-weight: 500;">{lat:.4f}, {lon:.4f}</span>
                        </div>
                        <div style="margin: 4px 0;">
                            <span style="color: #64748b;">🌾 Yield:</span>
                            <span style="font-weight: 500; color: #22c55e;">{parcel['actual_yield']:.2f} t/ha</span>
                        </div>
                        <div style="margin: 4px 0;">
                            <span style="color: #64748b;">💰 Income:</span>
                            <span style="font-weight: 500; color: #3b82f6;">€{parcel['annual_income']:,.0f}/year</span>
                        </div>
                        <div style="margin: 4px 0;">
                            <span style="color: #64748b;">📊 Suitability:</span>
                            <span style="font-weight: 500;">{parcel['suitability_scores'].get(crop, 0):.0f}/100</span>
                        </div>
                    </div>
                </div>
                """
                marker_color = '#3b82f6' if crop == 'WHEAT' else '#f97316'
                tooltip_text = f"{crop}: {parcel['actual_yield']:.1f} t/ha"
                target_fg = fg_farm

            folium.CircleMarker(
                location=[lat, lon],
                radius=7,
                color='#ffffff',  # White border
                weight=2,
                fillColor=marker_color,
                fillOpacity=0.9,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=tooltip_text
            ).add_to(target_fg)

        fg_farm.add_to(m)
        fg_solar.add_to(m)

    def _add_custom_legend(self, m: folium.Map, crops: list):
        """Add custom legend with shadcn styling (bottom right, no overlap)."""

        # Build legend HTML for all selected crops
        legend_items = []
        for crop in crops:
            scheme = self.color_schemes[crop]
            colors = scheme['colors']

            legend_items.append(f"""
                <div style="margin-bottom: 16px;">
                    <div style="font-size: 14px; font-weight: 600; color: #0f172a; margin-bottom: 8px;">
                        {scheme['icon']} {scheme['name']}
                    </div>
                    <div style="height: 20px;
                               background: linear-gradient(to right, {', '.join(colors)});
                               border-radius: 6px;
                               margin-bottom: 6px;">
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 10px; color: #64748b;">
                        <span>0 (Low)</span>
                        <span>100 (High)</span>
                    </div>
                </div>
            """)

        # Create gradient legend HTML with shadcn design
        legend_html = f"""
        <div style="position: fixed;
                    bottom: 30px; right: 30px;
                    width: 260px;
                    max-height: 400px;
                    overflow-y: auto;
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 16px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    z-index: 9999;">
            <div style="font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 16px;
                       border-bottom: 2px solid #e2e8f0; padding-bottom: 12px;">
                Land Suitability
            </div>
            {''.join(legend_items)}
        </div>
        """

        m.get_root().html.add_child(folium.Element(legend_html))

    def _add_spatial_network(self, m: folium.Map, year: int, crops: list):
        """Add spatial neighbor connections (visualize proximity interactions).

        Draws lines between farmers and their spatial neighbors (farmers + PV) to show
        the geographic proximity network that influences decisions.
        """
        print(f"   🔗 Adding spatial neighbor network and PV installations")

        spatial_data = self.collector.get_spatial_data(year)
        if not spatial_data or 'parcels' not in spatial_data:
            return

        parcels = spatial_data['parcels']
        pv_installations = spatial_data.get('pv_installations', [])

        # Create lookup by agent_id (both farmers and PV)
        agent_by_id = {}

        # Add farmers
        for parcel in parcels:
            crop = parcel['current_crop']
            if crop not in crops:
                continue

            lat, lon = parcel['lat'], parcel['lon']
            if not (self.lat_min <= lat <= self.lat_max and
                    self.lon_min <= lon <= self.lon_max):
                continue

            farmer_id = parcel.get('farmer_id')
            if farmer_id is not None:
                agent_by_id[farmer_id] = {'type': 'farmer', 'data': parcel}

        # Add PV installations
        for pv in pv_installations:
            lat, lon = pv['lat'], pv['lon']
            if not (self.lat_min <= lat <= self.lat_max and
                    self.lon_min <= lon <= self.lon_max):
                continue

            pv_id = pv.get('pv_id')
            if pv_id is not None:
                agent_by_id[pv_id] = {'type': 'pv', 'data': pv}

        if len(agent_by_id) < 2:
            print(f"      ⚠️  Not enough agents for network (need 2+, have {len(agent_by_id)})")
            return

        # Create feature group for spatial network (hidden by default)
        fg_network = folium.FeatureGroup(name='Spatial Network (50km)', show=False)

        # Draw connections using saved neighbor data
        import math

        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate distance in km."""
            R = 6371
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                 math.sin(dlon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        # Draw network connections
        connections_drawn = set()
        connection_count = 0

        for agent_id, agent_info in agent_by_id.items():
            # Get neighbors for this agent
            neighbor_ids = agent_info['data'].get('spatial_neighbors', [])

            for neighbor_id in neighbor_ids:
                # Check if neighbor exists in our agent set
                if neighbor_id not in agent_by_id:
                    continue

                # Avoid drawing same connection twice
                connection_key = tuple(sorted([agent_id, neighbor_id]))
                if connection_key in connections_drawn:
                    continue

                connections_drawn.add(connection_key)

                # Get agent and neighbor data
                agent_data = agent_info['data']
                neighbor_info = agent_by_id[neighbor_id]
                neighbor_data = neighbor_info['data']

                lat1, lon1 = agent_data['lat'], agent_data['lon']
                lat2, lon2 = neighbor_data['lat'], neighbor_data['lon']

                dist = haversine_distance(lat1, lon1, lat2, lon2)

                # Determine line color based on agent types
                if agent_info['type'] == 'farmer' and neighbor_info['type'] == 'farmer':
                    # Farmer-Farmer: color by crop similarity
                    crop1 = agent_data['current_crop']
                    crop2 = neighbor_data['current_crop']
                    if crop1 == crop2:
                        color = '#22c55e'  # Green = same crop
                        weight = 2
                        opacity = 0.6
                        label = f"{crop1} ↔ {crop2}"
                    else:
                        color = '#3b82f6'  # Blue = different crops
                        weight = 1
                        opacity = 0.3
                        label = f"{crop1} ↔ {crop2}"
                elif agent_info['type'] == 'pv' or neighbor_info['type'] == 'pv':
                    # Farmer-PV connection
                    color = '#f59e0b'  # Orange = PV interaction
                    weight = 2
                    opacity = 0.5
                    label = "Farmer ↔ PV"
                else:
                    # PV-PV (unlikely but handle it)
                    color = '#9ca3af'  # Gray
                    weight = 1
                    opacity = 0.3
                    label = "PV ↔ PV"

                folium.PolyLine(
                    locations=[[lat1, lon1], [lat2, lon2]],
                    color=color,
                    weight=weight,
                    opacity=opacity,
                    popup=f"{label}<br>Distance: {dist:.1f}km"
                ).add_to(fg_network)

                connection_count += 1

        fg_network.add_to(m)

        # Count solar PV parcels from the parcels list
        solar_pv_count = sum(1 for p in parcels if p.get('land_use') == 'solar_pv')

        print(f"      ✓ {connection_count} network connections added")
        print(f"      ✓ {solar_pv_count} solar PV parcels (shown as yellow markers in 'Solar PV Parcels' layer)")
