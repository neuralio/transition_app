"""
GIS-based Visualization System using Folium

Provides REAL GIS raster layers:
- Land suitability (from LUSA NetCDF)
- Soil properties (pH, organic carbon)
- Elevation (DEM)
- Meteorological data (temperature, precipitation)
- Farmer locations with parcels
"""

import folium
from folium import plugins
import numpy as np
import xarray as xr
import rasterio
from rasterio.transform import from_bounds
from rasterio.io import MemoryFile
from pathlib import Path
import branca.colormap as cm
from typing import Optional, List, Dict
import tempfile
import base64
from io import BytesIO
from PIL import Image


class GISVisualizer:
    """
    Creates interactive GIS maps with real raster layers using Folium.
    """

    def __init__(self, result_collector, data_path: str):
        """
        Initialize GIS visualizer.

        Args:
            result_collector: ResultCollector instance with simulation data
            data_path: Path to PILOT_THESSALONIKI_DATA
        """
        self.collector = result_collector
        self.scenario = result_collector.scenario
        self.data_path = Path(data_path)

        # Map bounds (Thessaloniki region)
        self.lat_min, self.lat_max = 40.2, 40.9
        self.lon_min, self.lon_max = 22.4, 23.4
        self.center_lat = (self.lat_min + self.lat_max) / 2
        self.center_lon = (self.lon_min + self.lon_max) / 2

    def create_multi_layer_map(
        self,
        year: int,
        crops: List[str] = ['WHEAT', 'MAIZE'],
        include_layers: Optional[List[str]] = None,
        output_file: str = 'gis_multi_layer_map.html'
    ):
        """
        Create interactive GIS map with multiple raster layers.

        Args:
            year: Year to visualize
            crops: List of crops to show suitability for
            include_layers: Layers to include ['suitability', 'soil', 'elevation', 'temperature']
                           None = all layers
            output_file: Output HTML file path

        Returns:
            Folium map object
        """
        if include_layers is None:
            include_layers = ['suitability', 'soil', 'elevation', 'temperature', 'farmers']

        # Create base map
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=10,
            tiles='OpenStreetMap',
            control_scale=True
        )

        # Add different basemap options
        folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
        folium.TileLayer('Esri WorldImagery', name='Satellite').add_to(m)

        print(f"\n📍 Creating GIS Map for Year {year}")
        print(f"   Region: Thessaloniki ({self.lat_min:.2f}-{self.lat_max:.2f}°N, {self.lon_min:.2f}-{self.lon_max:.2f}°E)")

        # Layer 1: Land Suitability (per crop)
        if 'suitability' in include_layers:
            for crop in crops:
                self._add_suitability_layer(m, crop, year)

        # Layer 2: Soil Properties
        if 'soil' in include_layers:
            self._add_soil_layer(m, 'ph')
            self._add_soil_layer(m, 'organic_carbon')

        # Layer 3: Elevation
        if 'elevation' in include_layers:
            self._add_elevation_layer(m)

        # Layer 4: Temperature
        if 'temperature' in include_layers:
            self._add_temperature_layer(m, year)

        # Layer 5: Precipitation
        if 'precipitation' in include_layers:
            self._add_precipitation_layer(m, year)

        # Layer 6: Farmer Parcels (vector layer)
        if 'farmers' in include_layers:
            self._add_farmer_parcels(m, year)

        # Add layer control (toggle layers on/off)
        folium.LayerControl(position='topright', collapsed=False).add_to(m)

        # Add minimap
        plugins.MiniMap(toggle_display=True).add_to(m)

        # Add fullscreen option
        plugins.Fullscreen(position='topleft').add_to(m)

        # Add mouse position
        plugins.MousePosition().add_to(m)

        # Save map
        output_path = Path(output_file)
        m.save(str(output_path))
        print(f"\n✅ GIS Map saved to: {output_path.absolute()}")

        return m

    def _add_suitability_layer(self, m: folium.Map, crop: str, year: int):
        """Add land suitability raster layer."""
        print(f"   📊 Adding layer: {crop} Suitability")

        # Load LUSA data
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

        # Use different colormaps for different crops for better distinction
        if crop == 'WHEAT':
            colormap = 'wheat_blue'  # Blue theme for wheat
            opacity = 0.7
        elif crop == 'MAIZE':
            colormap = 'maize_orange'  # Orange theme for maize
            opacity = 0.7
        else:
            colormap = 'RdYlGn'
            opacity = 0.6

        # Convert to raster overlay
        self._add_raster_overlay(
            m=m,
            data=scores_region.values,
            lats=scores_region.lat.values,
            lons=scores_region.lon.values,
            name=f'{crop} Suitability ({year})',
            colormap=colormap,
            vmin=0,
            vmax=100,
            opacity=opacity
        )

    def _add_soil_layer(self, m: folium.Map, soil_var: str):
        """Add soil property raster layer."""
        print(f"   🌱 Adding layer: Soil {soil_var.replace('_', ' ').title()}")

        # Map variable names to actual file names
        soil_file_map = {
            'ph': 'phh2o_0-5cm_mean.nc',
            'organic_carbon': 'soc_0-5cm_mean.nc',
            'cec': 'cec_0-5cm_mean.nc',
            'soil_type': 'SoilType_0-5cm_mean.nc'
        }

        if soil_var not in soil_file_map:
            print(f"      ⚠️  Unknown soil variable: {soil_var}")
            return

        soil_file = self.data_path / 'soil' / soil_file_map[soil_var]

        if not soil_file.exists():
            print(f"      ⚠️  File not found: {soil_file}")
            return

        # Load NetCDF
        ds = xr.open_dataset(soil_file)
        var_name = list(ds.data_vars)[0]
        data_full = ds[var_name]

        # Filter to region
        data_region = data_full.sel(
            lat=slice(self.lat_min, self.lat_max),
            lon=slice(self.lon_min, self.lon_max)
        )

        # Add to map
        self._add_raster_overlay(
            m=m,
            data=data_region.values,
            lats=data_region.lat.values,
            lons=data_region.lon.values,
            name=f'Soil {soil_var.replace("_", " ").title()}',
            colormap='YlOrBr',
            vmin=np.nanpercentile(data_region.values, 2),
            vmax=np.nanpercentile(data_region.values, 98),
            opacity=0.5
        )

    def _add_elevation_layer(self, m: folium.Map):
        """Add elevation raster layer."""
        print(f"   ⛰️  Adding layer: Elevation (DEM)")

        dem_file = self.data_path / 'dem' / 'DEM.nc'

        if not dem_file.exists():
            print(f"      ⚠️  File not found: {dem_file}")
            return

        # Load NetCDF
        ds = xr.open_dataset(dem_file)
        var_name = list(ds.data_vars)[0]
        data_full = ds[var_name]

        # Filter to region
        data_region = data_full.sel(
            lat=slice(self.lat_min, self.lat_max),
            lon=slice(self.lon_min, self.lon_max)
        )

        self._add_raster_overlay(
            m=m,
            data=data_region.values,
            lats=data_region.lat.values,
            lons=data_region.lon.values,
            name='Elevation (m)',
            colormap='terrain',
            vmin=np.nanpercentile(data_region.values, 2),
            vmax=np.nanpercentile(data_region.values, 98),
            opacity=0.5
        )

    def _add_temperature_layer(self, m: folium.Map, year: int):
        """Add temperature raster layer."""
        print(f"   🌡️  Adding layer: Temperature")

        # File is tas_rcp26.nc (tas = temperature at surface)
        temp_file = self.data_path / 'meteo' / f'tas_{self.scenario}.nc'

        if not temp_file.exists():
            print(f"      ⚠️  File not found: {temp_file}")
            return

        ds = xr.open_dataset(temp_file)
        var_name = list(ds.data_vars)[0]
        temp_data = ds.sel(time=f"{year}-01-01", method="nearest")[var_name]

        temp_region = temp_data.sel(
            lat=slice(self.lat_min, self.lat_max),
            lon=slice(self.lon_min, self.lon_max)
        )

        self._add_raster_overlay(
            m=m,
            data=temp_region.values,
            lats=temp_region.lat.values,
            lons=temp_region.lon.values,
            name=f'Temperature (°C) - {year}',
            colormap='RdYlBu_r',
            vmin=np.nanpercentile(temp_region.values, 2),
            vmax=np.nanpercentile(temp_region.values, 98),
            opacity=0.5
        )

    def _add_precipitation_layer(self, m: folium.Map, year: int):
        """Add precipitation raster layer."""
        print(f"   💧 Adding layer: Precipitation")

        # File is pr_rcp26.nc (pr = precipitation)
        precip_file = self.data_path / 'meteo' / f'pr_{self.scenario}.nc'

        if not precip_file.exists():
            print(f"      ⚠️  File not found: {precip_file}")
            return

        ds = xr.open_dataset(precip_file)
        var_name = list(ds.data_vars)[0]
        precip_data = ds.sel(time=f"{year}-01-01", method="nearest")[var_name]

        precip_region = precip_data.sel(
            lat=slice(self.lat_min, self.lat_max),
            lon=slice(self.lon_min, self.lon_max)
        )

        self._add_raster_overlay(
            m=m,
            data=precip_region.values,
            lats=precip_region.lat.values,
            lons=precip_region.lon.values,
            name=f'Precipitation (mm) - {year}',
            colormap='Blues',
            vmin=0,
            vmax=np.nanpercentile(precip_region.values, 98),
            opacity=0.5
        )

    def _add_farmer_parcels(self, m: folium.Map, year: int):
        """Add farmer parcel points as vector layer."""
        print(f"   👨‍🌾 Adding layer: Farmer Parcels")

        spatial_data = self.collector.get_spatial_data(year)
        if not spatial_data or 'parcels' not in spatial_data:
            print(f"      ⚠️  No farmer data available")
            return

        parcels = spatial_data['parcels']

        # Create feature group for farmers
        farmer_group = folium.FeatureGroup(name=f'Farmer Parcels ({year})')

        for parcel in parcels:
            # Color by crop
            crop_colors = {'WHEAT': 'blue', 'MAIZE': 'orange'}
            color = crop_colors.get(parcel['current_crop'], 'gray')

            # Create popup with parcel info
            popup_html = f"""
            <div style="font-family: Arial; width: 200px;">
                <h4 style="margin: 0; color: {color};">🌾 Farmer Parcel</h4>
                <hr style="margin: 5px 0;">
                <b>Location:</b> ({parcel['lat']:.4f}, {parcel['lon']:.4f})<br>
                <b>Crop:</b> {parcel['current_crop']}<br>
                <b>Suitability:</b> {parcel['suitability_scores'].get(parcel['current_crop'], 0):.1f}/100<br>
                <b>Yield:</b> {parcel['actual_yield']:.2f} t/ha<br>
                <b>Income:</b> €{parcel['annual_income']:,.0f}/year
            </div>
            """

            # Add marker
            folium.CircleMarker(
                location=[parcel['lat'], parcel['lon']],
                radius=8,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{parcel['current_crop']} - {parcel['actual_yield']:.1f} t/ha"
            ).add_to(farmer_group)

        farmer_group.add_to(m)

    def _add_raster_overlay(
        self,
        m: folium.Map,
        data: np.ndarray,
        lats: np.ndarray,
        lons: np.ndarray,
        name: str,
        colormap: str,
        vmin: float,
        vmax: float,
        opacity: float = 0.6
    ):
        """
        Add a raster overlay to the map.

        Args:
            m: Folium map
            data: 2D array of values
            lats: Latitude coordinates
            lons: Longitude coordinates
            name: Layer name
            colormap: Colormap name
            vmin: Minimum value for colormap
            vmax: Maximum value for colormap
            opacity: Layer opacity
        """
        # Validate data
        if data.size == 0 or data.shape[0] == 0 or data.shape[1] == 0:
            print(f"      ⚠️  Empty data array, skipping layer")
            return

        # Handle NaN values
        data_clean = np.where(np.isnan(data), vmin, data)

        # Check if we have valid range
        if vmax <= vmin:
            vmax = vmin + 1

        # Normalize data to 0-1 for image
        data_norm = np.clip((data_clean - vmin) / (vmax - vmin), 0, 1)

        # Create colormap - shadcn-inspired color schemes
        if colormap == 'wheat_blue':
            # Blue gradient for WHEAT (cool tones) - shadcn blue palette
            # Low suitability (red) → Medium (neutral) → High (blue)
            colors = [
                (239, 68, 68),   # red-500 (low suitability)
                (251, 146, 60),  # orange-400
                (250, 204, 21),  # yellow-400
                (234, 179, 8),   # yellow-500
                (163, 230, 53),  # lime-400
                (134, 239, 172), # green-300
                (103, 232, 249), # cyan-300
                (56, 189, 248),  # sky-400
                (59, 130, 246),  # blue-500
                (37, 99, 235),   # blue-600
                (29, 78, 216)    # blue-700 (high suitability)
            ]
        elif colormap == 'maize_orange':
            # Orange/amber gradient for MAIZE (warm tones) - shadcn amber palette
            # Low suitability (purple) → Medium (neutral) → High (orange)
            colors = [
                (168, 85, 247),  # purple-500 (low suitability)
                (192, 132, 252), # purple-400
                (196, 181, 253), # purple-300
                (226, 232, 240), # slate-200
                (253, 224, 71),  # yellow-300
                (252, 211, 77),  # amber-300
                (251, 191, 36),  # amber-400
                (245, 158, 11),  # amber-500
                (217, 119, 6),   # amber-600
                (180, 83, 9),    # amber-700
                (146, 64, 14)    # amber-800 (high suitability)
            ]
        elif colormap == 'RdYlGn':
            colors = [(165, 0, 38), (215, 48, 39), (244, 109, 67), (253, 174, 97),
                     (254, 224, 139), (255, 255, 191), (217, 239, 139), (166, 217, 106),
                     (102, 189, 99), (26, 152, 80), (0, 104, 55)]
        elif colormap == 'RdYlBu_r':
            colors = [(165, 0, 38), (215, 48, 39), (244, 109, 67), (253, 174, 97),
                     (254, 224, 139), (255, 255, 191), (171, 217, 233), (116, 173, 209),
                     (69, 117, 180), (49, 54, 149)]
        elif colormap == 'Blues':
            # Shadcn blue palette
            colors = [(241, 245, 249), (226, 232, 240), (203, 213, 225), (148, 163, 184),
                     (100, 116, 139), (59, 130, 246), (37, 99, 235), (29, 78, 216), (30, 64, 175)]
        elif colormap == 'YlOrBr':
            # Shadcn earth tones
            colors = [(254, 252, 232), (254, 243, 199), (253, 224, 71), (250, 204, 21),
                     (234, 179, 8), (202, 138, 4), (161, 98, 7), (120, 53, 15), (87, 83, 78)]
        elif colormap == 'terrain':
            # Shadcn green/earth palette
            colors = [(20, 83, 45), (21, 128, 61), (34, 197, 94), (74, 222, 128),
                     (187, 247, 208), (254, 240, 138), (253, 224, 71), (161, 98, 7), (120, 53, 15)]
        else:
            colors = [(239, 68, 68), (250, 204, 21), (34, 197, 94)]  # Default shadcn red-yellow-green

        # Create RGB image
        height, width = data_norm.shape

        if height == 0 or width == 0:
            print(f"      ⚠️  Invalid dimensions ({height}x{width}), skipping layer")
            return

        img_array = np.zeros((height, width, 4), dtype=np.uint8)

        for i in range(height):
            for j in range(width):
                val = data_norm[i, j]
                if np.isnan(data[i, j]):
                    img_array[i, j] = [0, 0, 0, 0]  # Transparent for NaN
                else:
                    # Interpolate color
                    idx = val * (len(colors) - 1)
                    idx1 = int(np.floor(idx))
                    idx2 = min(idx1 + 1, len(colors) - 1)
                    alpha = idx - idx1

                    c1 = colors[idx1]
                    c2 = colors[idx2]

                    r = int(c1[0] * (1 - alpha) + c2[0] * alpha)
                    g = int(c1[1] * (1 - alpha) + c2[1] * alpha)
                    b = int(c1[2] * (1 - alpha) + c2[2] * alpha)

                    img_array[i, j] = [r, g, b, int(opacity * 255)]

        # Create PIL image
        try:
            img = Image.fromarray(img_array, mode='RGBA')

            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            buffered.seek(0)
            img_str = base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            print(f"      ⚠️  Could not create image: {e}")
            return

        # Add image overlay
        bounds = [[lats.min(), lons.min()], [lats.max(), lons.max()]]

        folium.raster_layers.ImageOverlay(
            image=f'data:image/png;base64,{img_str}',
            bounds=bounds,
            opacity=opacity,
            name=name,
            overlay=True,
            control=True
        ).add_to(m)

        # Add colorbar legend
        self._add_colorbar(m, name, colormap, vmin, vmax, colors)

    def _add_colorbar(self, m: folium.Map, name: str, colormap: str, vmin: float, vmax: float, colors: List):
        """Add colorbar legend to map."""
        # Convert RGB tuples to hex colors for branca
        try:
            hex_colors = []
            for c in colors:
                if c is not None and len(c) == 3:
                    # Ensure values are integers 0-255
                    r = int(max(0, min(255, c[0])))
                    g = int(max(0, min(255, c[1])))
                    b = int(max(0, min(255, c[2])))
                    hex_color = f'#{r:02x}{g:02x}{b:02x}'
                    hex_colors.append(hex_color)

            if not hex_colors:
                # Fallback
                hex_colors = ['#d73027', '#fee08b', '#1a9850']

            color_scale = cm.LinearColormap(
                colors=hex_colors,
                vmin=vmin,
                vmax=vmax,
                caption=name
            )
            m.add_child(color_scale)
        except Exception as e:
            print(f"      ⚠️  Could not add colorbar: {e}")
            # Skip colorbar if it fails

    def _crop_to_region(self, data: np.ndarray, bounds):
        """Crop raster data to Thessaloniki region."""
        # Calculate resolution
        height, width = data.shape
        lat_res = (bounds.top - bounds.bottom) / height
        lon_res = (bounds.right - bounds.left) / width

        # Find pixel indices for region
        lat_idx_min = int((bounds.top - self.lat_max) / lat_res)
        lat_idx_max = int((bounds.top - self.lat_min) / lat_res)
        lon_idx_min = int((self.lon_min - bounds.left) / lon_res)
        lon_idx_max = int((self.lon_max - bounds.left) / lon_res)

        # Clip to valid range
        lat_idx_min = max(0, lat_idx_min)
        lat_idx_max = min(height, lat_idx_max)
        lon_idx_min = max(0, lon_idx_min)
        lon_idx_max = min(width, lon_idx_max)

        if lat_idx_min >= lat_idx_max or lon_idx_min >= lon_idx_max:
            print(f"      ⚠️  Region outside data bounds")
            return None, None, None

        # Crop data
        data_region = data[lat_idx_min:lat_idx_max, lon_idx_min:lon_idx_max]

        # Create lat/lon arrays
        lats = np.linspace(self.lat_max, self.lat_min, lat_idx_max - lat_idx_min)
        lons = np.linspace(self.lon_min, self.lon_max, lon_idx_max - lon_idx_min)

        return data_region, lats, lons
