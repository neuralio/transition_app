"""
MLU-04: Categorize Land Parcels Using AI

User Story: As a Developer, I want to use AI to categorize land parcels
based on their suitability for different land uses (agriculture vs solar PV).

This query provides QUICK CATEGORIZATION without running full ABM simulation.
Uses LUSA predictions + environmental factors to assign categories.
"""

import sys
from pathlib import Path
import xarray as xr
import numpy as np
from typing import Dict, List, Optional
import random

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.data.loaders.data_loader import (
    load_crop_suitability,
    load_temperature,
    load_solar_radiation,
    load_soil_type
)


def categorize_parcel(
    lusa_score: float,
    temperature: float,
    solar_radiation: float,
    soil_quality: float,
    elevation: float = None
) -> str:
    """
    Categorize a single parcel based on environmental factors.

    Categories:
    - 'HIGH_AGRICULTURE': High crop suitability
    - 'MODERATE_AGRICULTURE': Moderate crop suitability
    - 'HIGH_SOLAR': High solar PV potential
    - 'MIXED_USE': Both agriculture and solar viable
    - 'LOW_SUITABILITY': Neither highly suitable

    Args:
        lusa_score: LUSA crop suitability (0-1)
        temperature: Mean annual temperature (Celsius)
        solar_radiation: Mean annual solar radiation (W/m²)
        soil_quality: Soil quality index (0-1)
        elevation: Elevation (meters) - optional

    Returns:
        Category string
    """
    # Thresholds (tuned for real data ranges)
    HIGH_LUSA_THRESHOLD = 0.7
    MODERATE_LUSA_THRESHOLD = 0.5
    HIGH_SOLAR_THRESHOLD = 200.0  # W/m² (typical threshold for solar viability)
    GOOD_SOIL_THRESHOLD = 0.6

    # Decision logic
    high_agriculture = (lusa_score >= HIGH_LUSA_THRESHOLD and
                       soil_quality >= GOOD_SOIL_THRESHOLD)
    moderate_agriculture = lusa_score >= MODERATE_LUSA_THRESHOLD
    high_solar = solar_radiation >= HIGH_SOLAR_THRESHOLD

    if high_agriculture and high_solar:
        return 'MIXED_USE'
    elif high_agriculture:
        return 'HIGH_AGRICULTURE'
    elif moderate_agriculture:
        return 'MODERATE_AGRICULTURE'
    elif high_solar:
        return 'HIGH_SOLAR'
    else:
        return 'LOW_SUITABILITY'


def query_parcel_categorize(
    data_path: str,
    crop: str,
    scenario: str,
    n_parcels: int = 15,
    year: Optional[int] = None,
    seed: Optional[int] = None
) -> Dict:
    """
    Categorize land parcels using AI-based classification.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA directory
        crop: Crop type (WHEAT, MAIZE)
        scenario: Climate scenario (rcp26, rcp45, rcp85, historical)
        n_parcels: Number of parcels to categorize
        year: Specific year (default: first year in dataset)
        seed: Random seed for reproducibility

    Returns:
        Dictionary with categorization results:
        {
            'parcels': List of parcel data with categories,
            'summary': Category distribution,
            'statistics': Overall statistics
        }
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    print(f"\n{'='*60}")
    print(f"MLU-04: Categorize Land Parcels Using AI")
    print(f"{'='*60}")
    print(f"Crop: {crop.upper()}")
    print(f"Scenario: {scenario.upper()}")
    print(f"Number of Parcels: {n_parcels}")
    print(f"Data Path: {data_path}")

    # Load data
    print(f"\nLoading environmental data...")

    try:
        # LUSA predictions (already ML-predicted crop suitability)
        lusa_data = load_crop_suitability(data_path, crop, scenario)

        # Meteorological data (future projections or historical observations)
        temp_data = load_temperature(data_path, scenario)
        solar_data = load_solar_radiation(data_path, scenario)

        # Soil data (static)
        try:
            soil_data = load_soil_type(data_path)
        except:
            print("   Warning: Soil data not available, using default values")
            soil_data = None

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Failed to load data: {str(e)}",
            'crop': crop,
            'scenario': scenario
        }

    # Select year
    if 'time' in lusa_data.coords:
        time_coords = lusa_data.time.values
        years = [int(str(t)[:4]) for t in time_coords]

        if year is None:
            year = years[0]
            print(f"Using first year: {year}")
        elif year not in years:
            return {
                'status': 'error',
                'message': f"Year {year} not in dataset",
                'available_years': (min(years), max(years))
            }

        # Select year index
        year_idx = years.index(year)
        lusa_data = lusa_data.isel(time=year_idx)
        temp_data = temp_data.isel(time=year_idx) if 'time' in temp_data.coords else temp_data
        solar_data = solar_data.isel(time=year_idx) if 'time' in solar_data.coords else solar_data

    # Get suitability variable name
    suitability_var = None
    for var_name in lusa_data.data_vars:
        if 'suitability' in var_name.lower() or crop.upper() in var_name.upper():
            suitability_var = var_name
            break
    if suitability_var is None:
        suitability_var = list(lusa_data.data_vars)[0]

    # Temperature variable (tas = temperature at surface)
    temp_var = 'tas' if 'tas' in temp_data.data_vars else list(temp_data.data_vars)[0]

    # Solar radiation variable (rsds = surface downwelling shortwave radiation)
    solar_var = 'rsds' if 'rsds' in solar_data.data_vars else list(solar_data.data_vars)[0]

    # USE REAL COORDINATES FROM THE ACTUAL DATA (NOT RANDOM!)
    # Sample actual grid points from the NetCDF data
    print(f"\nSampling {n_parcels} REAL parcels from NetCDF grid...")

    # Get all valid (non-NaN) grid points from LUSA data
    lusa_values = lusa_data[suitability_var].values
    if len(lusa_values.shape) == 3:  # (time, lat, lon)
        lusa_values = lusa_values[0, :, :]  # Take first time slice

    lat_coords = lusa_data.lat.values
    lon_coords = lusa_data.lon.values

    # Find all valid (non-NaN) grid points
    valid_indices = []
    for i, lat in enumerate(lat_coords):
        for j, lon in enumerate(lon_coords):
            if not np.isnan(lusa_values[i, j]):
                valid_indices.append((i, j, lat, lon))

    print(f"Found {len(valid_indices)} valid grid points in Thessaloniki region")

    if len(valid_indices) == 0:
        return {
            'status': 'error',
            'message': 'No valid grid points found in LUSA data',
            'crop': crop,
            'scenario': scenario
        }

    # Sample n_parcels from the valid grid points
    if n_parcels > len(valid_indices):
        print(f"⚠️  Requested {n_parcels} parcels, but only {len(valid_indices)} valid points available")
        n_parcels = len(valid_indices)

    # Randomly sample from valid indices (but using REAL coordinates!)
    sampled_indices = np.random.choice(len(valid_indices), size=n_parcels, replace=False)

    parcels = []
    category_counts = {
        'HIGH_AGRICULTURE': 0,
        'MODERATE_AGRICULTURE': 0,
        'HIGH_SOLAR': 0,
        'MIXED_USE': 0,
        'LOW_SUITABILITY': 0
    }

    for idx, sample_idx in enumerate(sampled_indices):
        i, j, lat, lon = valid_indices[sample_idx]

        # Extract values at location (nearest neighbor)
        try:
            lusa_score = float(lusa_data[suitability_var].sel(lat=lat, lon=lon, method='nearest').values)
            temperature = float(temp_data[temp_var].sel(lat=lat, lon=lon, method='nearest').values)
            solar_radiation = float(solar_data[solar_var].sel(lat=lat, lon=lon, method='nearest').values)

            # Soil quality (if available)
            if soil_data is not None:
                soil_var = list(soil_data.data_vars)[0]
                soil_value = float(soil_data[soil_var].sel(lat=lat, lon=lon, method='nearest').values)
                # Normalize soil quality to 0-1 range (adjust based on actual data)
                soil_quality = np.clip(soil_value / 10.0, 0.0, 1.0)
            else:
                soil_quality = 0.7  # Default moderate soil quality

            # Categorize parcel
            category = categorize_parcel(
                lusa_score=lusa_score,
                temperature=temperature,
                solar_radiation=solar_radiation,
                soil_quality=soil_quality
            )

            category_counts[category] += 1

            parcels.append({
                'parcel_id': idx + 1,
                'lat': lat,
                'lon': lon,
                'category': category,
                'lusa_score': lusa_score,
                'temperature': temperature,
                'solar_radiation': solar_radiation,
                'soil_quality': soil_quality
            })

        except Exception as e:
            print(f"   Warning: Could not process parcel {i+1}: {e}")
            continue

    # Calculate summary statistics
    total_categorized = sum(category_counts.values())

    print(f"\n{'='*60}")
    print(f"CATEGORIZATION RESULTS")
    print(f"{'='*60}")
    print(f"Total Parcels Categorized: {total_categorized}")
    print(f"\nCategory Distribution:")
    for category, count in category_counts.items():
        percentage = (count / total_categorized * 100) if total_categorized > 0 else 0
        print(f"  {category:25s}: {count:3d} ({percentage:5.1f}%)")
    print(f"{'='*60}\n")

    # Generate visualizations
    print(f"\n📊 Generating visualizations...")
    from use_cases.mlu.queries.visualization_utils import create_parcel_map, create_category_pie_chart

    output_dir = Path(f"results/mlu04_{crop.lower()}_{scenario.lower()}")
    output_dir.mkdir(parents=True, exist_ok=True)

    visualizations = {}

    try:
        # GIS map with categorized parcels
        gis_file = str(output_dir / 'parcel_categories_map.html')
        viz_path = create_parcel_map(
            parcels=parcels,
            title=f'MLU-04: Parcel Categories - {crop.upper()} {scenario.upper()}',
            output_file=gis_file
        )
        if viz_path:
            visualizations['gis_map'] = viz_path
            print(f"   ✅ GIS map saved: {gis_file}")
    except Exception as e:
        print(f"   ⚠️  GIS map generation failed: {e}")

    try:
        # Pie chart
        pie_file = str(output_dir / 'category_distribution.html')
        viz_path = create_category_pie_chart(
            category_counts=category_counts,
            title=f'Land Use Category Distribution - {crop.upper()} {scenario.upper()}',
            output_file=pie_file
        )
        if viz_path:
            visualizations['pie_chart'] = viz_path
            print(f"   ✅ Pie chart saved: {pie_file}")
    except Exception as e:
        print(f"   ⚠️  Pie chart generation failed: {e}")

    # Print visualization paths
    if visualizations:
        print(f"\n{'='*60}")
        print(f"VISUALIZATIONS GENERATED")
        print(f"{'='*60}")
        for viz_type, viz_path in visualizations.items():
            print(f"  {viz_type}: {viz_path}")
        print(f"{'='*60}\n")

    return {
        'status': 'success',
        'crop': crop.upper(),
        'scenario': scenario.upper(),
        'year': year,
        'n_parcels': total_categorized,
        'parcels': parcels,
        'category_distribution': category_counts,
        'statistics': {
            'mean_lusa_score': np.mean([p['lusa_score'] for p in parcels]),
            'mean_temperature': np.mean([p['temperature'] for p in parcels]),
            'mean_solar_radiation': np.mean([p['solar_radiation'] for p in parcels]),
            'mean_soil_quality': np.mean([p['soil_quality'] for p in parcels])
        },
        'visualizations': visualizations
    }


def main():
    """Example usage of MLU-04 query."""
    import argparse

    parser = argparse.ArgumentParser(description="MLU-04: Categorize Land Parcels Using AI")
    parser.add_argument("--data-path", required=True, help="Path to PILOT_THESSALONIKI_DATA")
    parser.add_argument("--crop", required=True, choices=["WHEAT", "MAIZE"], help="Crop type")
    parser.add_argument("--scenario", required=True,
                       choices=["rcp26", "rcp45", "rcp85", "historical"],
                       help="Climate scenario")
    parser.add_argument("--parcels", type=int, default=15, help="Number of parcels to categorize")
    parser.add_argument("--year", type=int, help="Specific year (optional)")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")

    args = parser.parse_args()

    result = query_parcel_categorize(
        data_path=args.data_path,
        crop=args.crop,
        scenario=args.scenario,
        n_parcels=args.parcels,
        year=args.year,
        seed=args.seed
    )

    if result['status'] == 'error':
        print(f"\n❌ Error: {result['message']}")
        sys.exit(1)

    print(f"\n✅ Query completed successfully!")

    # Optionally save results to JSON
    import json
    output_file = f"parcel_categorization_{args.crop}_{args.scenario}.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"📄 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
