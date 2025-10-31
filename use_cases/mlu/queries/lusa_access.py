"""
MLU-01: Access LUSA Module

User Story: As a Policymaker, I want to access the LUSA module to retrieve
land-use suitability predictions for specific crops and climate scenarios.

This query provides QUICK ACCESS to LUSA predictions without running full ABM simulation.
"""

import sys
from pathlib import Path
import xarray as xr
import numpy as np
from typing import Dict, Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.data.loaders.data_loader import load_crop_suitability


def query_lusa_access(
    data_path: str,
    crop: str,
    scenario: str,
    year: Optional[int] = None,
    location: Optional[tuple] = None,
    output_format: str = "summary"
) -> Dict:
    """
    Access LUSA predictions for a specific crop and scenario.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA directory
        crop: Crop type (WHEAT, MAIZE)
        scenario: Climate scenario (rcp26, rcp45, rcp85, historical)
        year: Optional specific year (default: all years)
        location: Optional (lat, lon) tuple for specific location
        output_format: 'summary' (stats) or 'full' (complete dataset)

    Returns:
        Dictionary with LUSA prediction data:
        {
            'crop': str,
            'scenario': str,
            'year_range': tuple,
            'spatial_extent': dict,
            'statistics': dict,  # mean, std, min, max suitability
            'data': xarray.Dataset (if output_format='full')
        }
    """
    print(f"\n{'='*60}")
    print(f"MLU-01: Access LUSA Module")
    print(f"{'='*60}")
    print(f"Crop: {crop.upper()}")
    print(f"Scenario: {scenario.upper()}")
    print(f"Data Path: {data_path}")

    # Load LUSA predictions (already ML-predicted future suitability)
    print(f"\nLoading LUSA predictions...")

    try:
        lusa_data = load_crop_suitability(data_path, crop, scenario)
    except Exception as e:
        return {
            'status': 'error',
            'message': f"Failed to load LUSA data: {str(e)}",
            'crop': crop,
            'scenario': scenario
        }

    # Extract time range
    time_coords = lusa_data.time.values if 'time' in lusa_data.coords else []
    if len(time_coords) > 0:
        # Convert numpy datetime64 to years
        years = [int(str(t)[:4]) for t in time_coords]
        year_range = (min(years), max(years))
    else:
        year_range = None

    # Extract spatial extent
    spatial_extent = {
        'lat_min': float(lusa_data.lat.min().values),
        'lat_max': float(lusa_data.lat.max().values),
        'lon_min': float(lusa_data.lon.min().values),
        'lon_max': float(lusa_data.lon.max().values),
    }

    # Filter by year if specified
    if year is not None and year_range is not None:
        if year < year_range[0] or year > year_range[1]:
            return {
                'status': 'error',
                'message': f"Year {year} out of range {year_range}",
                'crop': crop,
                'scenario': scenario,
                'available_years': year_range
            }

        # Select specific year
        print(f"Filtering for year {year}...")
        # Find closest time index
        time_idx = years.index(year)
        lusa_data = lusa_data.isel(time=time_idx)

    # Filter by location if specified
    if location is not None:
        lat, lon = location
        print(f"Filtering for location ({lat:.2f}, {lon:.2f})...")
        lusa_data = lusa_data.sel(lat=lat, lon=lon, method='nearest')

    # Get suitability variable name (could be crop-specific)
    # Common names: 'suitability', 'WHEAT', 'MAIZE', etc.
    suitability_var = None
    for var_name in lusa_data.data_vars:
        if 'suitability' in var_name.lower() or crop.upper() in var_name.upper():
            suitability_var = var_name
            break

    if suitability_var is None:
        # Try first variable
        suitability_var = list(lusa_data.data_vars)[0]

    print(f"Suitability variable: {suitability_var}")

    # Calculate statistics
    suitability_values = lusa_data[suitability_var].values
    statistics = {
        'mean': float(np.nanmean(suitability_values)),
        'std': float(np.nanstd(suitability_values)),
        'min': float(np.nanmin(suitability_values)),
        'max': float(np.nanmax(suitability_values)),
        'median': float(np.nanmedian(suitability_values)),
    }

    # Count valid pixels
    valid_pixels = np.sum(~np.isnan(suitability_values))
    total_pixels = suitability_values.size
    statistics['valid_pixels'] = int(valid_pixels)
    statistics['total_pixels'] = int(total_pixels)
    statistics['coverage'] = float(valid_pixels / total_pixels * 100)

    print(f"\n{'='*60}")
    print(f"LUSA PREDICTIONS SUMMARY")
    print(f"{'='*60}")
    print(f"Mean Suitability: {statistics['mean']:.3f}")
    print(f"Std Deviation: {statistics['std']:.3f}")
    print(f"Range: [{statistics['min']:.3f}, {statistics['max']:.3f}]")
    print(f"Coverage: {statistics['coverage']:.1f}% ({statistics['valid_pixels']}/{statistics['total_pixels']} pixels)")
    print(f"{'='*60}\n")

    # Build result
    result = {
        'status': 'success',
        'crop': crop.upper(),
        'scenario': scenario.upper(),
        'year_range': year_range,
        'selected_year': year,
        'location': location,
        'spatial_extent': spatial_extent,
        'statistics': statistics,
        'variable_name': suitability_var,
    }

    # Include full dataset if requested
    if output_format == 'full':
        result['data'] = lusa_data

    # Generate visualizations (GIS map + Plotly heatmap)
    print(f"\n📊 Generating visualizations...")
    visualizations = _generate_lusa_visualizations(
        lusa_data=lusa_data,
        crop=crop,
        scenario=scenario,
        year=year,
        suitability_var=suitability_var,
        spatial_extent=spatial_extent,
        statistics=statistics
    )

    result['visualizations'] = visualizations

    # Print visualization paths
    if visualizations:
        print(f"\n{'='*60}")
        print(f"VISUALIZATIONS GENERATED")
        print(f"{'='*60}")
        for viz_type, viz_path in visualizations.items():
            print(f"  {viz_type}: {viz_path}")
        print(f"{'='*60}\n")

    return result


def _generate_lusa_visualizations(
    lusa_data: xr.Dataset,
    crop: str,
    scenario: str,
    year: Optional[int],
    suitability_var: str,
    spatial_extent: dict,
    statistics: dict
) -> dict:
    """
    Generate visualizations for LUSA data.

    Returns:
        Dict with paths to generated HTML files
    """
    visualizations = {}
    output_dir = Path(f"results/mlu01_{crop.lower()}_{scenario.lower()}")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Generate Plotly heatmap
        print(f"   Creating suitability heatmap...")

        import plotly.graph_objects as go

        suitability_values = lusa_data[suitability_var].values

        # If 3D (time, lat, lon), take first time slice for visualization
        if len(suitability_values.shape) == 3:
            suitability_values = suitability_values[0, :, :]

        fig = go.Figure(data=go.Heatmap(
            z=suitability_values,
            x=lusa_data.lon.values,
            y=lusa_data.lat.values,
            colorscale='Viridis',
            colorbar=dict(title='Suitability Score')
        ))

        fig.update_layout(
            title=f'{crop.upper()} Suitability - {scenario.upper()}',
            xaxis_title='Longitude',
            yaxis_title='Latitude',
            width=900,
            height=700
        )

        heatmap_file = output_dir / 'suitability_heatmap.html'
        fig.write_html(str(heatmap_file))
        visualizations['heatmap'] = str(heatmap_file.absolute())
        print(f"      ✅ Heatmap saved: {heatmap_file}")

    except Exception as e:
        print(f"      ⚠️  Heatmap generation failed: {e}")

    try:
        # 2. Generate GIS map with Folium
        print(f"   Creating interactive GIS map...")

        import folium

        # Create folium map centered on region
        center_lat = (spatial_extent['lat_min'] + spatial_extent['lat_max']) / 2
        center_lon = (spatial_extent['lon_min'] + spatial_extent['lon_max']) / 2

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10,
            tiles='OpenStreetMap',
            control_scale=True
        )

        # Add title
        title_html = f'''
        <div style="position: fixed; top: 10px; left: 50px; width: 500px; height: 80px;
                    background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
                    padding: 10px">
        <b>MLU-01: {crop.upper()} Suitability - {scenario.upper()}</b><br>
        {year if year else "All years"}<br>
        Mean: {statistics['mean']:.2f} | Std: {statistics['std']:.2f} | Coverage: {statistics['coverage']:.1f}%
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))

        # Add bounds rectangle
        folium.Rectangle(
            bounds=[[spatial_extent['lat_min'], spatial_extent['lon_min']],
                   [spatial_extent['lat_max'], spatial_extent['lon_max']]],
            color='blue',
            fill=False,
            weight=2,
            popup=f'Region Extent<br>Coverage: {statistics["coverage"]:.1f}%'
        ).add_to(m)

        # Add layer control
        folium.LayerControl().add_to(m)

        gis_file = output_dir / 'gis_map.html'
        m.save(str(gis_file))
        visualizations['gis_map'] = str(gis_file.absolute())
        print(f"      ✅ GIS map saved: {gis_file}")

    except ImportError:
        print(f"      ⚠️  Folium not installed. Install with: pip install folium")
    except Exception as e:
        print(f"      ⚠️  GIS map generation failed: {e}")

    return visualizations


def main():
    """Example usage of MLU-01 query."""
    import argparse

    parser = argparse.ArgumentParser(description="MLU-01: Access LUSA Module")
    parser.add_argument("--data-path", required=True, help="Path to PILOT_THESSALONIKI_DATA")
    parser.add_argument("--crop", required=True, choices=["WHEAT", "MAIZE"], help="Crop type")
    parser.add_argument("--scenario", required=True,
                       choices=["rcp26", "rcp45", "rcp85", "historical"],
                       help="Climate scenario")
    parser.add_argument("--year", type=int, help="Specific year (optional)")
    parser.add_argument("--lat", type=float, help="Latitude for location query")
    parser.add_argument("--lon", type=float, help="Longitude for location query")
    parser.add_argument("--full", action="store_true", help="Return full dataset")

    args = parser.parse_args()

    location = (args.lat, args.lon) if args.lat and args.lon else None
    output_format = "full" if args.full else "summary"

    result = query_lusa_access(
        data_path=args.data_path,
        crop=args.crop,
        scenario=args.scenario,
        year=args.year,
        location=location,
        output_format=output_format
    )

    if result['status'] == 'error':
        print(f"\n❌ Error: {result['message']}")
        sys.exit(1)

    print(f"\n✅ Query completed successfully!")

    # Print result summary
    print(f"\nResult:")
    for key, value in result.items():
        if key != 'data':  # Skip full dataset
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
