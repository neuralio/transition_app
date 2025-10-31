"""
MLU-04: Categorize Land Parcels Using AI Models

User Story: "Uses AI techniques (LUSA predictions) to analyze EO and socioeconomic data.
Categorizes land parcels based on suitability for agriculture (WHEAT/MAIZE) or solar PV."

What to show:
- Categorize REAL parcels from NetCDF grid
- Categories: WHEAT (blue), MAIZE (orange), SOLAR (yellow)
- GIS map with color-coded markers
- Category distribution chart
"""

import sys
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
import folium
from folium import plugins
import xarray as xr
from datetime import datetime
from openai import OpenAI

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.data.loaders.data_loader import load_crop_suitability, load_solar_radiation
from use_cases.mlu.utils.scenario_utils import get_scenario_display_name, get_scenario_short_name


def _generate_parcel_insights(scenario, n_parcels, category_counts):
    """Generate AI insights for parcel categorization."""
    try:
        client = OpenAI()

        total = sum(category_counts.values())
        percentages = {k: (v/total)*100 for k, v in category_counts.items()}

        data_summary = f"""
Parcel Categorization Results:
- Climate Scenario: {scenario}
- Total Parcels: {n_parcels}
- High Crop Suitability: {category_counts.get('High Crop Suitability', 0)} ({percentages.get('High Crop Suitability', 0):.1f}%)
- Medium Crop Suitability: {category_counts.get('Medium Crop Suitability', 0)} ({percentages.get('Medium Crop Suitability', 0):.1f}%)
- Solar PV Priority: {category_counts.get('Solar PV Priority', 0)} ({percentages.get('Solar PV Priority', 0):.1f}%)
"""

        insights = {}

        # Category Distribution Analysis (Bar Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a land-use planning expert interpreting categorization results. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Category Distribution Bar Chart showing parcel breakdown. What does the distribution of High Crop ({percentages.get('High Crop Suitability', 0):.1f}%), Medium Crop ({percentages.get('Medium Crop Suitability', 0):.1f}%), and Solar PV ({percentages.get('Solar PV Priority', 0):.1f}%) tell us about optimal land allocation?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Category Distribution Analysis (Bar Chart)"] = response.choices[0].message.content.strip()

        # Geographic Pattern Insight (GIS Map)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a geospatial planner analyzing land use patterns. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Interactive GIS Map showing spatial distribution of the three categories. What geographic clustering or patterns should inform zoning decisions and infrastructure planning?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Geographic Pattern Insight (GIS Map)"] = response.choices[0].message.content.strip()

        # Economic Diversification Strategy
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an agricultural economist advising on portfolio diversification. Provide detailed, actionable recommendations in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAdvise farmers and investors on economic diversification. With {percentages.get('Solar PV Priority', 0):.1f}% suitable for solar PV, how should they balance crop production vs renewable energy investment for optimal income and risk management?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Economic Diversification Strategy"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate AI insights: {e}")
        solar_pct = percentages.get('Solar PV Priority', 0)
        high_crop_pct = percentages.get('High Crop Suitability', 0)
        return {
            "Category Distribution Analysis (Bar Chart)": f"Distribution shows {high_crop_pct:.1f}% high agricultural potential, {percentages.get('Medium Crop Suitability', 0):.1f}% medium potential, and {solar_pct:.1f}% solar PV priority, indicating balanced land-use opportunities under {scenario}",
            "Geographic Pattern Insight (GIS Map)": f"Spatial analysis of {n_parcels} parcels reveals clustering of similar categories, suggesting zone-based planning approaches could optimize infrastructure and policy implementation",
            "Economic Diversification Strategy": f"With {solar_pct:.1f}% suitable for solar PV, landowners should consider hybrid agrivoltaic systems or strategic portfolio allocation to diversify income streams and hedge against climate risks"
        }


def categorize_parcel(wheat_score, maize_score, solar_potential):
    """
    Categorize a parcel based on suitability scores.

    Returns: 'WHEAT', 'MAIZE', or 'SOLAR'
    """
    # Simple rule: highest score wins
    scores = {
        'WHEAT': wheat_score,
        'MAIZE': maize_score,
        'SOLAR': solar_potential
    }
    return max(scores, key=scores.get)


def query_mlu_04(
    data_path: str,
    scenario: str,
    n_parcels: int = 15,
    year: int = 2050,
    output_dir: str = None,
    geojson: dict = None,
    print_insights: bool = True,  # NEW: Control whether to print insights
    farmer_locations: list = None  # NEW (2025-10-21): User-specified farmer locations
):
    """
    MLU-04: Categorize Land Parcels

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        scenario: rcp26, rcp45, rcp85, or historical
        n_parcels: Number of parcels to sample
        year: Target year for categorization (default: 2050)
        output_dir: Where to save visualizations
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        Dict with status and results
    """
    print(f"\n{'='*60}")
    print(f"MLU-04: Categorize Land Parcels Using AI")
    print(f"{'='*60}")
    scenario_display = get_scenario_display_name(scenario)  # Full name for console output
    scenario_short = get_scenario_short_name(scenario)  # Short name for titles (like CCA)
    print(f"Scenario: {scenario_display}")
    print(f"Target Year: {year}")
    print(f"Parcels to categorize: {n_parcels}")
    print(f"{'='*60}\n")

    try:
        # Load LUSA data for both crops
        print(f"Loading LUSA predictions for scenario: {scenario.upper()}...")
        wheat_data = load_crop_suitability(data_path, 'WHEAT', scenario, filter_to_thessaloniki=True, geojson=geojson)
        maize_data = load_crop_suitability(data_path, 'MAIZE', scenario, filter_to_thessaloniki=True, geojson=geojson)
        print(f"✓ Loaded data shape: {wheat_data['score'].shape} (time × lat × lon)")

        # Load solar radiation (proxy for solar PV potential)
        try:
            solar_data = load_solar_radiation(data_path, scenario, geojson=geojson)
            solar_var = 'rsds' if 'rsds' in solar_data.data_vars else list(solar_data.data_vars)[0]
        except:
            solar_data = None

        # Extract data for the specified year
        wheat_values = wheat_data['score'].values
        maize_values = maize_data['score'].values

        if len(wheat_values.shape) == 3:
            # Find the year index (data starts from 2021)
            years = wheat_data.time.dt.year.values if 'time' in wheat_data.coords else range(2021, 2021 + wheat_values.shape[0])
            year_idx = None
            for idx, yr in enumerate(years):
                if yr == year:
                    year_idx = idx
                    break

            if year_idx is None:
                print(f"⚠️  WARNING: Year {year} not found in data. Using closest year.")
                # Find closest year
                year_idx = min(range(len(years)), key=lambda i: abs(years[i] - year))
                print(f"⚠️  Using year {years[year_idx]} instead")
            else:
                print(f"✓ Using data from year {year} (index {year_idx})")

            wheat_values = wheat_values[year_idx, :, :]
            maize_values = maize_values[year_idx, :, :]

            print(f"✓ Wheat suitability range: {wheat_values.min():.1f} - {wheat_values.max():.1f}")
            print(f"✓ Maize suitability range: {maize_values.min():.1f} - {maize_values.max():.1f}")

        lats = wheat_data.lat.values
        lons = wheat_data.lon.values

        # FILTER TO THESSALONIKI REGION (same bounds as working simulation!)
        lat_min, lat_max = 40.2, 40.9
        lon_min, lon_max = 22.4, 23.4

        # Extract solar radiation for the same year as crops
        solar_vals = solar_data[solar_var].values if solar_data is not None else None
        if solar_vals is not None and len(solar_vals.shape) == 3:
            # Use the same year index as wheat/maize
            if year_idx is not None:
                solar_vals = solar_vals[year_idx, :, :]
                print(f"✓ Solar radiation range: {np.nanmin(solar_vals):.1f} - {np.nanmax(solar_vals):.1f} kWh/m²/day")
            else:
                solar_vals = solar_vals[0, :, :]  # Fallback to first slice
        elif solar_vals is not None:
            # Already 2D
            print(f"✓ Solar radiation range: {np.nanmin(solar_vals):.1f} - {np.nanmax(solar_vals):.1f} kWh/m²/day")

        # Find all valid grid points IN THESSALONIKI ONLY
        print(f"Finding valid grid points in Thessaloniki region...")
        print(f"   Bounds: lat {lat_min}-{lat_max}, lon {lon_min}-{lon_max}")
        valid_points = []
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                # Check if point is in Thessaloniki region AND has valid data
                in_region = (lat >= lat_min and lat <= lat_max and lon >= lon_min and lon <= lon_max)
                has_data = not np.isnan(wheat_values[i, j]) and not np.isnan(maize_values[i, j])

                if in_region and has_data:
                    # Get solar potential (normalized to 0-100 scale)
                    if solar_vals is not None:
                        try:
                            solar_raw = solar_vals[i, j]
                            # Normalize: typical range 4-6 kWh/m²/day in Greece
                            # Scale to 0-100: 4 kWh/m²/day = 80, 6 kWh/m²/day = 100
                            solar_potential = min(100.0, max(0.0, (solar_raw - 2.0) * 25.0))
                        except:
                            solar_potential = 50.0
                    else:
                        solar_potential = 50.0

                    valid_points.append({
                        'lat': lat,
                        'lon': lon,
                        'wheat_score': wheat_values[i, j],
                        'maize_score': maize_values[i, j],
                        'solar_potential': solar_potential
                    })

        print(f"   Found {len(valid_points)} valid grid points")

        # First, categorize ALL parcels to see population-level distribution
        all_categories = {'WHEAT': 0, 'MAIZE': 0, 'SOLAR': 0}
        for p in valid_points:
            cat = categorize_parcel(p['wheat_score'], p['maize_score'], p['solar_potential'])
            all_categories[cat] += 1

        print(f"\n📊 Population-Level Distribution (all {len(valid_points)} parcels):")
        for cat, count in all_categories.items():
            pct = (count / len(valid_points) * 100) if len(valid_points) > 0 else 0
            print(f"   {cat:10s}: {count:3d} parcels ({pct:5.1f}%)")

        # NEW (2025-10-21): Validate user-specified coordinates if provided
        if farmer_locations:
            print(f"\n🔍 Validating {len(farmer_locations)} user-specified locations...")
            from backend.data.loaders.spatial_filter import get_polygon_bounds

            # Determine validation bounds
            if geojson:
                polygon_bounds = get_polygon_bounds(geojson)
                bounds_lat = (polygon_bounds['lat_min'], polygon_bounds['lat_max'])
                bounds_lon = (polygon_bounds['lon_min'], polygon_bounds['lon_max'])
                bounds_desc = f"polygon bounds"
            else:
                bounds_lat = (lat_min, lat_max)
                bounds_lon = (lon_min, lon_max)
                bounds_desc = f"data bounds"

            # Validate ALL coordinates
            errors = []
            # Import centralized epsilon configuration
            from backend.config.validation_config import get_coordinate_epsilon
            epsilon = get_coordinate_epsilon()

            for i, loc in enumerate(farmer_locations, 1):
                lat, lon = loc['lat'], loc['lon']
                location_errors = []

                # Check latitude bounds (with epsilon tolerance for boundary points)
                if not (bounds_lat[0] - epsilon <= lat <= bounds_lat[1] + epsilon):
                    location_errors.append(f"latitude {lat}° outside range [{bounds_lat[0]:.4f}°, {bounds_lat[1]:.4f}°]")
                # Check longitude bounds (with epsilon tolerance for boundary points)
                if not (bounds_lon[0] - epsilon <= lon <= bounds_lon[1] + epsilon):
                    location_errors.append(f"longitude {lon}° outside range [{bounds_lon[0]:.4f}°, {bounds_lon[1]:.4f}°]")

                if location_errors:
                    errors.append(f"Location {i}: {'; '.join(location_errors)}")

            if errors:
                error_msg = f"❌ COORDINATE VALIDATION FAILED! {' | '.join(errors)}"
                if geojson:
                    error_msg += " | ⚠️ Coordinates must be inside your drawn polygon!"
                raise ValueError(error_msg)

            print(f"   ✅ All coordinates valid within {bounds_desc}")

            # Use user-specified locations instead of random sampling
            n_sample = len(farmer_locations)
            sampled_indices = []
            for loc in farmer_locations:
                # Find closest valid point to user's coordinates
                min_dist = float('inf')
                closest_idx = None
                for idx, vp in enumerate(valid_points):
                    dist = np.sqrt((vp['lat'] - loc['lat'])**2 + (vp['lon'] - loc['lon'])**2)
                    if dist < min_dist:
                        min_dist = dist
                        closest_idx = idx
                if closest_idx is not None:
                    sampled_indices.append(closest_idx)
            print(f"   📍 Using {len(sampled_indices)} user-specified locations")
        else:
            # Sample n_parcels (with fixed seed for reproducibility)
            n_sample = min(n_parcels, len(valid_points))
            np.random.seed(42)  # Fixed seed for consistent results across runs
            sampled_indices = np.random.choice(len(valid_points), size=n_sample, replace=False)

        # Show score ranges for sampled parcels BEFORE categorization
        sampled_wheat = [valid_points[i]['wheat_score'] for i in sampled_indices]
        sampled_maize = [valid_points[i]['maize_score'] for i in sampled_indices]
        sampled_solar = [valid_points[i]['solar_potential'] for i in sampled_indices]
        print(f"\n📊 Sampled Parcel Scores (n={n_sample}):")
        print(f"   WHEAT:  {min(sampled_wheat):.1f} - {max(sampled_wheat):.1f} (avg: {np.mean(sampled_wheat):.1f})")
        print(f"   MAIZE:  {min(sampled_maize):.1f} - {max(sampled_maize):.1f} (avg: {np.mean(sampled_maize):.1f})")
        print(f"   SOLAR:  {min(sampled_solar):.1f} - {max(sampled_solar):.1f} (avg: {np.mean(sampled_solar):.1f})")

        # Categorize parcels
        parcels = []
        category_counts = {'WHEAT': 0, 'MAIZE': 0, 'SOLAR': 0}

        for idx in sampled_indices:
            p = valid_points[idx]
            category = categorize_parcel(p['wheat_score'], p['maize_score'], p['solar_potential'])
            category_counts[category] += 1

            parcels.append({
                'parcel_id': len(parcels) + 1,
                'lat': p['lat'],
                'lon': p['lon'],
                'category': category,
                'wheat_score': p['wheat_score'],
                'maize_score': p['maize_score'],
                'solar_potential': p['solar_potential']
            })

        # Print summary
        print(f"\n{'='*60}")
        print(f"CATEGORIZATION RESULTS")
        print(f"{'='*60}")
        for category, count in category_counts.items():
            pct = (count / n_sample * 100) if n_sample > 0 else 0
            print(f"{category:10s}: {count:3d} parcels ({pct:5.1f}%)")
        print(f"{'='*60}\n")

        # Create output directory - make it relative to use_cases/mlu/
        # Add timestamp to prevent overwriting
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_dir:
            output_path = Path(output_dir) / f'mlu_04_{scenario.lower()}' / timestamp
        else:
            # Default: use_cases/mlu/results/mlu_04_{scenario}/{timestamp}
            mlu_dir = Path(__file__).parent.parent
            output_path = mlu_dir / 'results' / f'mlu_04_{scenario.lower()}' / timestamp
        output_path.mkdir(parents=True, exist_ok=True)

        # Create visualizations subfolder (to match CCA/GCP/MLU-05 pattern)
        viz_output = output_path / "visualizations"
        viz_output.mkdir(parents=True, exist_ok=True)

        # Generate visualizations
        print(f"📊 Generating visualizations...")
        viz_files = []

        # 1. GIS Map with toggleable layers (SAME as working simulation!)
        print(f"   Creating interactive GIS map with layer controls...")

        # Calculate center from actual parcels
        center_lat = np.mean([p['lat'] for p in parcels])
        center_lon = np.mean([p['lon'] for p in parcels])

        # Create base map (SAME as CleanGISVisualizer!)
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10,
            tiles='OpenStreetMap',
            control_scale=True,
            prefer_canvas=True
        )

        # Add basemap options
        folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
        folium.TileLayer('Esri WorldImagery', name='Satellite').add_to(m)

        # Color schemes (from CleanGISVisualizer)
        suitability_colors = {
            'WHEAT': ['#dc2626', '#f59e0b', '#fbbf24', '#a3e635', '#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#3b82f6', '#2563eb'],
            'MAIZE': ['#7c3aed', '#a78bfa', '#c4b5fd', '#fbbf24', '#f59e0b', '#f97316', '#ea580c', '#dc2626', '#b91c1c', '#991b1b']
        }

        marker_colors = {
            'WHEAT': '#3b82f6',   # Blue
            'MAIZE': '#f97316',   # Orange
            'SOLAR': '#eab308'    # Yellow
        }

        # LAYER 1: WHEAT Suitability Heatmap (toggleable!)
        print(f"      🌾 Adding WHEAT suitability layer...")
        fg_wheat_suit = folium.FeatureGroup(name='🌾 WHEAT Suitability', show=True)

        # FILTER TO THESSALONIKI REGION using xarray .sel() (SAME as working code!)
        wheat_scores = wheat_data['score']
        if len(wheat_scores.shape) == 3:
            wheat_scores = wheat_scores[0, :, :]  # First time slice

        wheat_region = wheat_scores.sel(
            lat=slice(lat_min, lat_max),
            lon=slice(lon_min, lon_max)
        )

        wheat_lats = wheat_region.lat.values
        wheat_lons = wheat_region.lon.values
        wheat_vals = wheat_region.values

        for i in range(len(wheat_lats) - 1):
            for j in range(len(wheat_lons) - 1):
                val = wheat_vals[i, j]
                if np.isnan(val) or val <= 0:
                    continue

                # Color based on suitability
                color_idx = int((val / 100) * (len(suitability_colors['WHEAT']) - 1))
                color_idx = min(color_idx, len(suitability_colors['WHEAT']) - 1)
                color = suitability_colors['WHEAT'][color_idx]

                bounds = [[wheat_lats[i+1], wheat_lons[j]], [wheat_lats[i], wheat_lons[j+1]]]
                folium.Rectangle(
                    bounds=bounds,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.6,
                    weight=0,
                    popup=f"<b>WHEAT</b><br>Suitability: {val:.1f}/100"
                ).add_to(fg_wheat_suit)

        fg_wheat_suit.add_to(m)

        # LAYER 2: MAIZE Suitability Heatmap (toggleable!)
        print(f"      🌽 Adding MAIZE suitability layer...")
        fg_maize_suit = folium.FeatureGroup(name='🌽 MAIZE Suitability', show=True)

        # FILTER TO THESSALONIKI REGION using xarray .sel()
        maize_scores = maize_data['score']
        if len(maize_scores.shape) == 3:
            maize_scores = maize_scores[0, :, :]  # First time slice

        maize_region = maize_scores.sel(
            lat=slice(lat_min, lat_max),
            lon=slice(lon_min, lon_max)
        )

        maize_lats = maize_region.lat.values
        maize_lons = maize_region.lon.values
        maize_vals = maize_region.values

        for i in range(len(maize_lats) - 1):
            for j in range(len(maize_lons) - 1):
                val = maize_vals[i, j]
                if np.isnan(val) or val <= 0:
                    continue

                color_idx = int((val / 100) * (len(suitability_colors['MAIZE']) - 1))
                color_idx = min(color_idx, len(suitability_colors['MAIZE']) - 1)
                color = suitability_colors['MAIZE'][color_idx]

                bounds = [[maize_lats[i+1], maize_lons[j]], [maize_lats[i], maize_lons[j+1]]]
                folium.Rectangle(
                    bounds=bounds,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.6,
                    weight=0,
                    popup=f"<b>MAIZE</b><br>Suitability: {val:.1f}/100"
                ).add_to(fg_maize_suit)

        fg_maize_suit.add_to(m)

        # LAYER 3: WHEAT Parcels (toggleable!)
        fg_wheat = folium.FeatureGroup(name='WHEAT Parcels', show=True)
        for p in [p for p in parcels if p['category'] == 'WHEAT']:
            popup_html = f"""
            <div style="font-family: -apple-system, sans-serif; padding: 12px; min-width: 200px;">
                <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px; color: #0f172a;
                           border-bottom: 2px solid #3b82f6; padding-bottom: 8px;">
                    🌾 WHEAT Parcel
                </div>
                <div style="font-size: 14px; color: #475569; line-height: 1.6;">
                    <div><b>Location:</b> ({p['lat']:.4f}, {p['lon']:.4f})</div>
                    <div><b>Wheat Score:</b> {p['wheat_score']:.1f}/100</div>
                    <div><b>Maize Score:</b> {p['maize_score']:.1f}/100</div>
                    <div><b>Solar Potential:</b> {p['solar_potential']:.1f}/100</div>
                </div>
            </div>
            """
            folium.CircleMarker(
                location=[p['lat'], p['lon']],
                radius=8,
                color='#ffffff',
                weight=2,
                fillColor=marker_colors['WHEAT'],
                fillOpacity=0.9,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"WHEAT: {p['wheat_score']:.1f}"
            ).add_to(fg_wheat)
        fg_wheat.add_to(m)

        # LAYER 4: MAIZE Parcels (toggleable!)
        fg_maize = folium.FeatureGroup(name='MAIZE Parcels', show=True)
        for p in [p for p in parcels if p['category'] == 'MAIZE']:
            popup_html = f"""
            <div style="font-family: -apple-system, sans-serif; padding: 12px; min-width: 200px;">
                <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px; color: #0f172a;
                           border-bottom: 2px solid #f97316; padding-bottom: 8px;">
                    🌽 MAIZE Parcel
                </div>
                <div style="font-size: 14px; color: #475569; line-height: 1.6;">
                    <div><b>Location:</b> ({p['lat']:.4f}, {p['lon']:.4f})</div>
                    <div><b>Wheat Score:</b> {p['wheat_score']:.1f}/100</div>
                    <div><b>Maize Score:</b> {p['maize_score']:.1f}/100</div>
                    <div><b>Solar Potential:</b> {p['solar_potential']:.1f}/100</div>
                </div>
            </div>
            """
            folium.CircleMarker(
                location=[p['lat'], p['lon']],
                radius=8,
                color='#ffffff',
                weight=2,
                fillColor=marker_colors['MAIZE'],
                fillOpacity=0.9,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"MAIZE: {p['maize_score']:.1f}"
            ).add_to(fg_maize)
        fg_maize.add_to(m)

        # LAYER 5: SOLAR Parcels (toggleable!)
        fg_solar = folium.FeatureGroup(name='☀️ SOLAR Parcels', show=True)
        for p in [p for p in parcels if p['category'] == 'SOLAR']:
            popup_html = f"""
            <div style="font-family: -apple-system, sans-serif; padding: 12px; min-width: 200px;">
                <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px; color: #0f172a;
                           border-bottom: 2px solid #eab308; padding-bottom: 8px;">
                    ☀️ SOLAR Parcel
                </div>
                <div style="font-size: 14px; color: #475569; line-height: 1.6;">
                    <div><b>Location:</b> ({p['lat']:.4f}, {p['lon']:.4f})</div>
                    <div><b>Wheat Score:</b> {p['wheat_score']:.1f}/100</div>
                    <div><b>Maize Score:</b> {p['maize_score']:.1f}/100</div>
                    <div><b>Solar Potential:</b> {p['solar_potential']:.1f}/100</div>
                </div>
            </div>
            """
            folium.CircleMarker(
                location=[p['lat'], p['lon']],
                radius=8,
                color='#ffffff',
                weight=2,
                fillColor=marker_colors['SOLAR'],
                fillOpacity=0.9,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"SOLAR: {p['solar_potential']:.1f}"
            ).add_to(fg_solar)
        fg_solar.add_to(m)

        # Add custom legend (bottom right - SAME as working code!)
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
            <div style="margin-bottom: 16px;">
                <div style="font-size: 14px; font-weight: 600; color: #0f172a; margin-bottom: 8px;">
                    🌾 Wheat Suitability
                </div>
                <div style="height: 20px;
                           background: linear-gradient(to right, {', '.join(suitability_colors['WHEAT'])});
                           border-radius: 6px;
                           margin-bottom: 6px;">
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 10px; color: #64748b;">
                    <span>0 (Low)</span>
                    <span>100 (High)</span>
                </div>
            </div>
            <div style="margin-bottom: 16px;">
                <div style="font-size: 14px; font-weight: 600; color: #0f172a; margin-bottom: 8px;">
                    🌽 Maize Suitability
                </div>
                <div style="height: 20px;
                           background: linear-gradient(to right, {', '.join(suitability_colors['MAIZE'])});
                           border-radius: 6px;
                           margin-bottom: 6px;">
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 10px; color: #64748b;">
                    <span>0 (Low)</span>
                    <span>100 (High)</span>
                </div>
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        # Add LayerControl (creates the checkboxes!!!)
        folium.LayerControl(
            position='topright',
            collapsed=False,  # Show expanded for easy toggling
            autoZIndex=True
        ).add_to(m)

        # Add mouse coordinates
        plugins.MousePosition(
            position='bottomleft',
            separator=' | ',
            prefix='Coordinates: '
        ).add_to(m)

        # Add fullscreen button
        plugins.Fullscreen(position='topleft').add_to(m)

        gis_file = viz_output / 'gis_map.html'
        m.save(str(gis_file))

        # Add <title> tag for frontend display (use short name like CCA)
        gis_title = f'{scenario_short} - Land Parcel Categorization Map'
        with open(gis_file, 'r') as f:
            gis_content = f.read()
        gis_content = gis_content.replace('<head>', f'<head><title>{gis_title}</title>')
        with open(gis_file, 'w') as f:
            f.write(gis_content)

        viz_files.append(gis_file)
        print(f"      ✅ {gis_file.name}")

        # 2. BAR CHART (as requested!)
        print(f"   Creating category distribution bar chart...")

        # Prepare data
        categories = list(category_counts.keys())
        counts = list(category_counts.values())
        bar_colors = [marker_colors[cat] for cat in categories]

        fig = go.Figure(data=[go.Bar(
            x=categories,
            y=counts,
            marker=dict(
                color=bar_colors,
                line=dict(color='#ffffff', width=2)
            ),
            text=counts,
            textposition='outside',
            textfont=dict(size=14, color='#0f172a', family='Inter, sans-serif'),
            hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
        )])

        fig.update_layout(
            title=dict(
                text=f'{scenario_short} - Land Parcel Categories',
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            xaxis=dict(
                title=dict(text='Category', font=dict(size=14, color='#475569')),
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
            height=500,
            margin=dict(l=60, r=40, t=80, b=60)
        )

        bar_file = viz_output / 'category_distribution.html'
        # Write HTML with custom title tag for frontend display (use short name like CCA)
        html_title = f'{scenario_short} - Land Parcel Categories'
        fig.write_html(str(bar_file), include_plotlyjs='cdn', config={'displayModeBar': False})

        # Add <title> tag for backend extraction
        with open(bar_file, 'r') as f:
            html_content = f.read()
        html_content = html_content.replace('<head>', f'<head><title>{html_title}</title>')
        with open(bar_file, 'w') as f:
            f.write(html_content)

        viz_files.append(bar_file)
        print(f"      ✅ {bar_file.name}")

        # Generate AI insights (only if print_insights=True)
        insights = _generate_parcel_insights(scenario_display, n_sample, category_counts)

        if print_insights:
            print(f"\n📊 AI-Generated Insights:")
            for viz_name, insight in insights.items():
                print(f"\n  {viz_name}:")
                print(f"    {insight}")

        # Print summary
        print(f"\n{'='*60}")
        print(f"✅ MLU-04 COMPLETE")
        print(f"{'='*60}")
        print(f"Output: {output_path}")
        print(f"Visualizations:")
        for f in viz_files:
            print(f"  - Saved to {f}")
        print(f"{'='*60}\n")

        return {
            'status': 'success',
            'scenario': scenario_display,
            'n_parcels': n_sample,
            'category_counts': category_counts,
            'parcels': parcels,
            'output_dir': str(output_path.absolute()),
            'visualizations': [str(f.absolute()) for f in viz_files],
            'ai_insights': insights
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
            'message': error_msg,
            'scenario': scenario
        }
    except Exception as e:
        # Full traceback for unexpected errors (debugging)
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'message': str(e),
            'scenario': scenario
        }


def query_mlu_04_all_scenarios(
    data_path: str,
    n_parcels: int = 15,
    year: int = 2050,
    output_dir: str = None,
    geojson: dict = None,
    farmer_locations: list = None  # NEW (2025-10-21): User-specified farmer locations
):
    """
    Run MLU-04 for ALL scenarios and create comparison visualizations.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        n_parcels: Number of parcels to sample
        year: Target year for categorization (default: 2050)
        output_dir: Base output directory
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        Dict with status and all results
    """
    # MLU-04 is for FUTURE climate scenarios only (no historical)
    scenarios = ['rcp26', 'rcp45', 'rcp85']

    print(f"\n{'='*80}")
    print(f"MLU-04: Running ALL Future Climate Scenarios")
    print(f"{'='*80}")
    print(f"Scenarios: {', '.join([s.upper() for s in scenarios])}")
    print(f"Parcels per scenario: {n_parcels}")
    print(f"{'='*80}\n")

    results_by_scenario = {}

    # Run each scenario
    for scenario in scenarios:
        scenario_display = get_scenario_display_name(scenario)
        print(f"\n🔄 Running {scenario_display}...")
        result = query_mlu_04(
            data_path=data_path,
            scenario=scenario,
            n_parcels=n_parcels,
            year=year,
            output_dir=output_dir,
            geojson=geojson,
            print_insights=False,  # Don't print individual insights - only comparison insights
            farmer_locations=farmer_locations
        )

        if result['status'] == 'success':
            results_by_scenario[scenario] = result
        else:
            print(f"⚠️  {scenario_display} failed: {result.get('message', 'Unknown error')}")

    if not results_by_scenario:
        return {
            'status': 'error',
            'message': 'All scenarios failed'
        }

    # Create comparison visualizations
    print(f"\n{'='*80}")
    print(f"📊 Creating Scenario Comparison Charts")
    print(f"{'='*80}")

    # Create comparison output directory - make it relative to use_cases/mlu/
    if output_dir:
        comparison_output = Path(output_dir) / 'mlu_04_comparison'
    else:
        mlu_dir = Path(__file__).parent.parent
        comparison_output = mlu_dir / 'results' / 'mlu_04_comparison'
    comparison_output.mkdir(parents=True, exist_ok=True)

    # 1. Comparison Bar Chart (category distribution across scenarios)
    print(f"   Creating comparison bar chart...")

    fig = go.Figure()

    categories = ['WHEAT', 'MAIZE', 'SOLAR']
    colors_map = {
        'WHEAT': '#3b82f6',
        'MAIZE': '#f97316',
        'SOLAR': '#eab308'
    }

    for category in categories:
        counts = []
        scenario_labels = []
        for scenario in scenarios:
            if scenario in results_by_scenario:
                count = results_by_scenario[scenario]['category_counts'].get(category, 0)
                counts.append(count)
                scenario_display = get_scenario_display_name(scenario)
                scenario_labels.append(scenario_display)

        fig.add_trace(go.Bar(
            name=category,
            x=scenario_labels,
            y=counts,
            marker=dict(color=colors_map[category]),
            text=counts,
            textposition='outside',
            hovertemplate=f'<b>{category}</b><br>Count: %{{y}}<extra></extra>'
        ))

    fig.update_layout(
        title=dict(
            text='Land Parcel Categories Across Climate Scenarios',
            font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
        ),
        xaxis=dict(
            title=dict(text='Climate Scenario', font=dict(size=14, color='#475569')),
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
        margin=dict(l=60, r=40, t=80, b=60),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#e2e8f0',
            borderwidth=1
        )
    )

    comparison_file = comparison_output / 'scenario_comparison_bar.html'
    fig.write_html(str(comparison_file))
    print(f"      ✅ {comparison_file.name}")

    # 2. Percentage Stacked Bar Chart
    print(f"   Creating percentage distribution chart...")

    fig2 = go.Figure()

    for category in categories:
        percentages = []
        scenario_labels = []
        for scenario in scenarios:
            if scenario in results_by_scenario:
                count = results_by_scenario[scenario]['category_counts'].get(category, 0)
                total = results_by_scenario[scenario]['n_parcels']
                pct = (count / total * 100) if total > 0 else 0
                percentages.append(pct)
                scenario_display = get_scenario_display_name(scenario)
                scenario_labels.append(scenario_display)

        fig2.add_trace(go.Bar(
            name=category,
            x=scenario_labels,
            y=percentages,
            marker=dict(color=colors_map[category]),
            text=[f'{p:.1f}%' for p in percentages],
            textposition='inside',
            hovertemplate=f'<b>{category}</b><br>%{{y:.1f}}%<extra></extra>'
        ))

    fig2.update_layout(
        title=dict(
            text='Land Parcel Category Distribution (%) Across Climate Scenarios',
            font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
        ),
        xaxis=dict(
            title=dict(text='Climate Scenario', font=dict(size=14, color='#475569')),
            tickfont=dict(size=12, color='#64748b')
        ),
        yaxis=dict(
            title=dict(text='Percentage (%)', font=dict(size=14, color='#475569')),
            tickfont=dict(size=12, color='#64748b'),
            gridcolor='#e2e8f0',
            range=[0, 100]
        ),
        barmode='stack',
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        width=1000,
        height=600,
        margin=dict(l=60, r=40, t=80, b=60),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#e2e8f0',
            borderwidth=1
        )
    )

    pct_file = comparison_output / 'scenario_comparison_percentage.html'
    fig2.write_html(str(pct_file))
    print(f"      ✅ {pct_file.name}")

    # Generate AI insights for comparison mode
    print(f"\n📊 AI-Generated Insights:")
    comparison_insights = _generate_comparison_insights_mlu04(results_by_scenario)
    for viz_name, insight in comparison_insights.items():
        print(f"\n  {viz_name}:")
        print(f"    {insight}")

    # Print summary
    print(f"\n{'='*80}")
    print(f"✅ ALL SCENARIOS COMPLETE")
    print(f"{'='*80}")
    print(f"Comparison output: {comparison_output}")
    print(f"\nIndividual scenario results:")
    for scenario, result in results_by_scenario.items():
        scenario_display = get_scenario_display_name(scenario)
        print(f"  - {scenario_display}: {result['output_dir']}")
    print(f"\nComparison visualizations:")
    print(f"  - Saved to {comparison_file}")
    print(f"  - Saved to {pct_file}")
    print(f"{'='*80}\n")

    return {
        'status': 'success',
        'results_by_scenario': results_by_scenario,
        'comparison_output': str(comparison_output.absolute()),
        'scenarios_run': list(results_by_scenario.keys())
    }


def _generate_comparison_insights_mlu04(results_by_scenario: dict):
    """
    Generate LLM-powered insights for MLU-04 COMPARISON MODE visualizations.

    Args:
        results_by_scenario: Dict mapping scenario name -> result dict

    Returns:
        Dict of insights for each comparison visualization
    """
    try:
        from openai import OpenAI
        client = OpenAI()

        # Extract comparison data
        scenario_names = []
        wheat_counts = []
        maize_counts = []
        solar_counts = []

        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in results_by_scenario:
                scenario_names.append(get_scenario_display_name(scenario))
                wheat_counts.append(results_by_scenario[scenario]['category_counts'].get('WHEAT', 0))
                maize_counts.append(results_by_scenario[scenario]['category_counts'].get('MAIZE', 0))
                solar_counts.append(results_by_scenario[scenario]['category_counts'].get('SOLAR', 0))

        n_parcels = results_by_scenario[list(results_by_scenario.keys())[0]]['n_parcels']

        # Prepare summary
        data_summary = f"""
Multi-Scenario Comparison Results (MLU-04):
- Scenarios: {', '.join(scenario_names)}
- Parcels per scenario: {n_parcels}
- WHEAT optimal parcels: {dict(zip(scenario_names, wheat_counts))}
- MAIZE optimal parcels: {dict(zip(scenario_names, maize_counts))}
- SOLAR optimal parcels: {dict(zip(scenario_names, solar_counts))}
"""

        insights = {}

        # 1. Category Distribution Comparison (Grouped Bar Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an agricultural land-use expert analyzing climate-driven categorization shifts. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Category Distribution Comparison (Grouped Bar Chart) showing WHEAT, MAIZE, and SOLAR optimal parcels across {', '.join(scenario_names)}. How do climate pathways affect the number of parcels best-suited for each category? Which land-use type shows strongest climate sensitivity?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Category Distribution Comparison (Grouped Bar Chart)"] = response.choices[0].message.content.strip()

        # 2. Percentage Distribution (Stacked Bar Chart)
        wheat_pcts = [w/n_parcels*100 for w in wheat_counts]
        maize_pcts = [m/n_parcels*100 for m in maize_counts]
        solar_pcts = [s/n_parcels*100 for s in solar_counts]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a land-use planning specialist analyzing percentage shifts in optimal land allocation. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Percentage Distribution (Stacked Bar Chart) showing relative proportions: WHEAT {dict(zip(scenario_names, [f'{p:.1f}%' for p in wheat_pcts]))}, MAIZE {dict(zip(scenario_names, [f'{p:.1f}%' for p in maize_pcts]))}, SOLAR {dict(zip(scenario_names, [f'{p:.1f}%' for p in solar_pcts]))}. What strategic implications emerge for regional land-use planning? Should Thessaloniki pivot toward certain categories under different climate scenarios?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Percentage Distribution (Stacked Bar Chart)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate LLM insights: {e}")
        # Fallback generic insights
        return {
            "Category Distribution Comparison (Grouped Bar Chart)": f"Climate scenarios show divergent land categorization across WHEAT, MAIZE, and SOLAR, revealing differential climate sensitivity in optimal land use",
            "Percentage Distribution (Stacked Bar Chart)": f"Relative proportions shift across scenarios: WHEAT {dict(zip(scenario_names, wheat_counts))}, MAIZE {dict(zip(scenario_names, maize_counts))}, SOLAR {dict(zip(scenario_names, solar_counts))}, indicating strategic land-use planning implications"
        }


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(description="MLU-04: Categorize Land Parcels")
    parser.add_argument("--data-path", required=True, help="Path to PILOT_THESSALONIKI_DATA")
    parser.add_argument("--scenario", default=None,
                       choices=["rcp26", "rcp45", "rcp85"],
                       help="Future climate scenario (omit to run ALL scenarios)")
    parser.add_argument("--parcels", type=int, required=True, help="Number of parcels")
    parser.add_argument("--output", default=None, help="Output directory")

    args = parser.parse_args()

    # If no scenario specified, run ALL scenarios
    if args.scenario is None:
        print("ℹ️  No scenario specified - running ALL scenarios!")
        result = query_mlu_04_all_scenarios(
            data_path=args.data_path,
            n_parcels=args.parcels,
            output_dir=args.output
        )
    else:
        # Single scenario
        result = query_mlu_04(
            data_path=args.data_path,
            scenario=args.scenario,
            n_parcels=args.parcels,
            output_dir=args.output
        )

    if result['status'] == 'error':
        print(f"\n❌ Error: {result['message']}")
        sys.exit(1)

    print(f"✅ Success!")


if __name__ == "__main__":
    main()
