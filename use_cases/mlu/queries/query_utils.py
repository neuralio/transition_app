"""
Utility functions for query mode.

Creates minimal simulations to populate ResultCollector,
then uses EXISTING visualization code for consistency.
"""

import sys
from pathlib import Path
import numpy as np
import xarray as xr

# Add project root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.mlu.scripts.result_collector import ResultCollector
from use_cases.mlu.scripts.visualizer import ResultVisualizer
from use_cases.mlu.scripts.gis_visualizer_v2 import CleanGISVisualizer


def create_lusa_result_collector(
    data_path: str,
    crop: str,
    scenario: str,
    n_parcels: int = 15,
    start_year: int = 2021
) -> ResultCollector:
    """
    Create a ResultCollector populated with LUSA data and sampled parcels.

    This creates a minimal "simulation" result that can be visualized
    using the existing ResultVisualizer and CleanGISVisualizer classes.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        crop: Crop type (WHEAT, MAIZE)
        scenario: Climate scenario (rcp26, rcp45, rcp85, historical)
        n_parcels: Number of parcels to sample from NetCDF grid
        start_year: Start year for time series

    Returns:
        ResultCollector with sampled parcel data
    """
    from backend.data.loaders.data_loader import (
        load_crop_suitability,
        load_temperature,
        load_solar_radiation
    )

    # Load LUSA data
    lusa_data = load_crop_suitability(data_path, crop, scenario)

    # Load meteorological data
    try:
        temp_data = load_temperature(data_path, scenario)
        solar_data = load_solar_radiation(data_path, scenario)
    except:
        temp_data = None
        solar_data = None

    # Initialize collector
    collector = ResultCollector(scenario=scenario, start_year=start_year)

    # Sample REAL grid points from LUSA data
    parcels = _sample_real_grid_points(lusa_data, temp_data, solar_data, crop, n_parcels)

    # Populate collector with sampled parcels for each time step
    time_coords = lusa_data.time.values if 'time' in lusa_data.coords else []
    years = [int(str(t)[:4]) for t in time_coords] if len(time_coords) > 0 else [start_year]

    # Create minimal "model" object for collection
    class MinimalModel:
        def __init__(self, parcels_data, year):
            self.parcels = parcels_data
            self.year = year
            self.current_year = year  # ResultCollector expects this!
            self.agents = []  # Empty list (no FarmerAgent instances)
            self.parcel_agents = parcels_data  # Our parcels act as LandParcelAgents
            self.schedule = type('Schedule', (), {'agents': parcels_data})()

    # Collect data for first few years (for time series)
    for year_idx in range(min(10, len(years))):
        year = years[year_idx]

        # Update parcel data for this year (use setattr for object attributes)
        for p in parcels:
            setattr(p, 'year', year)
            setattr(p, 'current_crop', crop)

        model = MinimalModel(parcels, year)
        collector.collect_step(model)

    return collector


def _sample_real_grid_points(lusa_data, temp_data, solar_data, crop, n_parcels):
    """
    Sample REAL grid points from NetCDF data (NOT random coordinates!).

    Returns:
        List of parcel dicts with real Thessaloniki coordinates
    """
    # Get suitability variable
    suitability_var = 'score' if 'score' in lusa_data.data_vars else list(lusa_data.data_vars)[0]

    # Get first time slice
    lusa_values = lusa_data[suitability_var].values
    if len(lusa_values.shape) == 3:  # (time, lat, lon)
        lusa_values = lusa_values[0, :, :]

    lat_coords = lusa_data.lat.values
    lon_coords = lusa_data.lon.values

    # Find all valid (non-NaN) grid points
    valid_indices = []
    for i, lat in enumerate(lat_coords):
        for j, lon in enumerate(lon_coords):
            if not np.isnan(lusa_values[i, j]):
                valid_indices.append((i, j, lat, lon, lusa_values[i, j]))

    print(f"   Found {len(valid_indices)} valid grid points in region")

    if len(valid_indices) == 0:
        raise ValueError("No valid grid points found in LUSA data")

    # Sample n_parcels
    n_sample = min(n_parcels, len(valid_indices))
    sampled_indices = np.random.choice(len(valid_indices), size=n_sample, replace=False)

    # Create parcel objects
    parcels = []
    for idx in sampled_indices:
        i, j, lat, lon, lusa_score = valid_indices[idx]

        # Get temperature and solar if available
        temperature = None
        solar_radiation = None

        if temp_data is not None:
            try:
                temp_var = 'tas' if 'tas' in temp_data.data_vars else list(temp_data.data_vars)[0]
                temp_vals = temp_data[temp_var].values
                if len(temp_vals.shape) == 3:
                    temp_vals = temp_vals[0, :, :]
                temperature = float(temp_data[temp_var].sel(lat=lat, lon=lon, method='nearest').values)
            except:
                pass

        if solar_data is not None:
            try:
                solar_var = 'rsds' if 'rsds' in solar_data.data_vars else list(solar_data.data_vars)[0]
                solar_vals = solar_data[solar_var].values
                if len(solar_vals.shape) == 3:
                    solar_vals = solar_vals[0, :, :]
                solar_radiation = float(solar_data[solar_var].sel(lat=lat, lon=lon, method='nearest').values)
            except:
                pass

        # Create parcel-like object
        parcel = type('Parcel', (), {
            'unique_id': len(parcels),
            'lat': lat,
            'lon': lon,
            'suitability_scores': {crop: lusa_score},
            'current_crop': crop,
            'land_hectares': 10.0,
            'actual_yield': lusa_score * 5.0,  # Rough estimate
            'annual_income': lusa_score * 1000.0,  # Rough estimate
            'soil_quality': 50.0,
            'temperature': temperature,
            'solar_radiation': solar_radiation
        })()

        parcels.append(parcel)

    return parcels


def generate_visualizations(collector, data_path, output_dir, crops=['WHEAT', 'MAIZE']):
    """
    Generate visualizations using EXISTING visualization classes.

    This ensures query mode produces THE SAME visualizations as full simulation!

    Args:
        collector: ResultCollector with simulation data
        data_path: Path to PILOT_THESSALONIKI_DATA
        output_dir: Output directory for HTML files
        crops: List of crops to visualize
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n📊 Generating visualizations (using SAME code as full simulation)...")

    # 1. Use ResultVisualizer for Plotly charts
    visualizer = ResultVisualizer(collector, data_path)
    visualizer.save_all_visualizations(str(output_path))

    # 2. Use CleanGISVisualizer for GIS maps
    try:
        gis_viz = CleanGISVisualizer(collector, data_path)
        gis_viz.create_clean_map(
            year=2021,
            crops=crops,
            show_farmers=True,
            output_file=str(output_path / f'{collector.scenario}_gis_map.html')
        )
        print(f"   ✅ GIS map saved: {collector.scenario}_gis_map.html")
    except Exception as e:
        print(f"   ⚠️  GIS map generation failed: {e}")

    print(f"\n✅ All visualizations saved to: {output_path}")

    return {
        'output_dir': str(output_path.absolute()),
        'files_generated': list(output_path.glob('*.html'))
    }
