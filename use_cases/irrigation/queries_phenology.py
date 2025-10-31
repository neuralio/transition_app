"""
Phenology-Enhanced Query Functions

Implements IRR-US-01 with temporal phenology analysis.
"""

import sys
from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.mask import mask as rasterio_mask
from shapely.geometry import shape, Point
import geopandas as gpd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from phenology import (
    PhenologyCalculator,
    TemporalClassifier,
    TimeSeriesDownloader
)
from phenology.visualizer import PhenologyVisualizer


def query_irr_01_with_phenology(
    geojson: dict,
    start_date: str,
    end_date: str,
    n_parcels: int = 20,
    parcel_locations: list[dict] | None = None,
    use_polygon_geometries: bool = False,
    temporal_window_days: int = 10
) -> dict:
    """
    IRR-US-01: Automated EO Classification WITH Temporal Phenology Analysis.

    Enhanced version that downloads NDVI/NDWI time-series and analyzes
    temporal patterns to distinguish:
    - Harvested crops (high NDVI → low NDVI)
    - Truly fallow (low NDVI all season)
    - Irrigated/flooded (sustained NDWI > 0)

    Args:
        geojson: User-drawn polygon (region of interest)
        start_date: Season start date (YYYY-MM-DD)
        end_date: Season end date (YYYY-MM-DD)
        n_parcels: Number of parcels if using random sampling
        parcel_locations: User-specified coordinates
        use_polygon_geometries: Use full polygon geometries
        temporal_window_days: Size of each temporal window in days (default: 10)

    Returns:
        dict: Phenology classification results
    """
    print("=" * 80)
    print("🌾 IRR-US-01: Automated EO Classification (TEMPORAL PHENOLOGY MODE)")
    print("=" * 80)
    print(f"📅 Season Range: {start_date} to {end_date}")
    print(f"⏱️  Temporal Window: {temporal_window_days} days per observation")

    if use_polygon_geometries:
        from backend.data.loaders.geojson_utils import extract_features
        num_polygons = len(extract_features(geojson))
        print(f"📍 Mode: Full Polygon Analysis ({num_polygons} field(s))")
    elif parcel_locations:
        print(f"📍 Mode: User-Specified Coordinates ({len(parcel_locations)} parcels)")
    else:
        print(f"🔢 Mode: Random Sampling ({n_parcels} parcels)")
    print("=" * 80)

    # Step 1: Download time-series data
    print("\n🔄 Step 1: Downloading NDVI/NDWI time-series...")

    downloader = TimeSeriesDownloader(temporal_window_days=temporal_window_days)

    try:
        time_series_data, date_labels, total_scenes = downloader.download_time_series(
            geojson=geojson,
            start_date=start_date,
            end_date=end_date
        )
    except ValueError as e:
        return {
            "success": False,
            "message": str(e),
            "scenes_found": 0
        }

    # Step 2: Get or generate parcels
    parcels = _generate_parcels(
        geojson,
        n_parcels,
        parcel_locations,
        use_polygon_geometries
    )

    # Step 3: Extract time-series for each parcel
    print(f"\n🔄 Step 3: Extracting time-series for {len(parcels)} parcel(s)...")

    for parcel in parcels:
        parcel['ndvi_series'] = []
        parcel['ndwi_series'] = []

    # Extract from each time point
    for i, (ndvi_path, ndwi_path, date_label) in enumerate(time_series_data, 1):
        print(f"   Processing date {i}/{len(time_series_data)}: {date_label}")

        _extract_indices_for_date(
            parcels,
            ndvi_path,
            ndwi_path,
            date_label
        )

    # Step 4: Calculate phenology metrics
    print(f"\n🔄 Step 4: Calculating phenology metrics...")

    calculator = PhenologyCalculator()
    classifier = TemporalClassifier()

    for parcel in parcels:
        if len(parcel['ndvi_series']) >= 3:
            # Compute metrics
            metrics = calculator.compute_metrics(
                parcel_id=parcel['parcel_id'],
                ndvi_series=parcel['ndvi_series'],
                ndwi_series=parcel['ndwi_series'] if parcel['ndwi_series'] else None,
                dates=date_labels
            )

            # Classify pattern
            classification = classifier.classify(metrics)

            # Store results
            parcel['phenology_metrics'] = metrics.to_dict()
            parcel['temporal_pattern'] = classification.pattern.value
            parcel['pattern_confidence'] = classification.confidence
            parcel['pattern_reason'] = classification.reason
        else:
            parcel['phenology_metrics'] = None
            parcel['temporal_pattern'] = 'insufficient_data'
            parcel['pattern_confidence'] = 0.0
            parcel['pattern_reason'] = f"Only {len(parcel['ndvi_series'])} observations (need ≥3)"

    # Step 5: Generate outputs
    print(f"\n🔄 Step 5: Generating phenology analysis outputs...")

    from datetime import datetime as dt
    timestamp_dir = dt.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"use_cases/irrigation/results/irr_01_phenology/{timestamp_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save results
    output_geojson = output_dir / "phenology_classification.geojson"
    output_report = output_dir / "phenology_report.txt"
    output_timeseries = output_dir / "phenology_timeseries.html"
    output_pattern_chart = output_dir / "pattern_distribution.html"

    _save_phenology_outputs(
        parcels,
        output_geojson,
        output_report,
        start_date,
        end_date,
        total_scenes,
        len(time_series_data)
    )

    # Create visualizations
    print(f"\n🔄 Step 6: Creating phenology visualizations...")
    visualizer = PhenologyVisualizer()

    visualizer.create_time_series_chart(
        parcels=parcels,
        dates=date_labels,
        output_path=output_timeseries,
        max_parcels_to_plot=10
    )

    visualizer.create_pattern_summary_chart(
        parcels=parcels,
        output_path=output_pattern_chart
    )

    print(f"   ✅ Time-series chart: {output_timeseries}")
    print(f"   ✅ Pattern summary: {output_pattern_chart}")

    print(f"\n✅ Phenology analysis complete!")
    print(f"   📁 Results: {output_dir}")
    print(f"=" * 80)

    return {
        "success": True,
        "message": f"Phenology analysis completed with {len(time_series_data)} temporal observations",
        "scenes_found": total_scenes,
        "n_observations": len(time_series_data),
        "output_dir": str(output_dir),
        "parcels": parcels
    }


def _generate_parcels(
    geojson: dict,
    n_parcels: int,
    parcel_locations: list[dict] | None,
    use_polygon_geometries: bool
) -> list[dict]:
    """Generate parcels based on mode."""
    print(f"\n🔄 Step 2: Generating parcels...")

    if use_polygon_geometries:
        from backend.data.loaders.geojson_utils import extract_features
        features = extract_features(geojson)
        parcels = []
        for idx, feature in enumerate(features):
            geometry = feature.get('geometry', feature)
            poly_geom = shape(geometry)
            centroid = poly_geom.centroid
            parcels.append({
                'parcel_id': idx + 1,
                'lat': centroid.y,
                'lon': centroid.x,
                'geometry': poly_geom,
                'is_polygon': True
            })
    elif parcel_locations:
        parcels = []
        for idx, loc in enumerate(parcel_locations):
            point = Point(loc['lon'], loc['lat'])
            parcels.append({
                'parcel_id': idx + 1,
                'lat': loc['lat'],
                'lon': loc['lon'],
                'geometry': point,
                'is_polygon': False
            })
    else:
        # Random sampling
        if geojson.get('type') == 'FeatureCollection':
            polygon_geom = shape(geojson['features'][0]['geometry'])
        else:
            polygon_geom = shape(geojson)

        bounds = polygon_geom.bounds
        parcels = []
        attempts = 0

        while len(parcels) < n_parcels and attempts < n_parcels * 100:
            random_lon = np.random.uniform(bounds[0], bounds[2])
            random_lat = np.random.uniform(bounds[1], bounds[3])
            point = Point(random_lon, random_lat)

            if polygon_geom.contains(point):
                parcels.append({
                    'parcel_id': len(parcels) + 1,
                    'lat': random_lat,
                    'lon': random_lon,
                    'geometry': point,
                    'is_polygon': False
                })

            attempts += 1

    print(f"✅ Generated {len(parcels)} parcels")
    return parcels


def _extract_indices_for_date(
    parcels: list[dict],
    ndvi_path: str,
    ndwi_path: str | None,
    date_label: str
):
    """Extract NDVI/NDWI values for all parcels at a single date."""
    # Extract NDVI
    with rasterio.open(ndvi_path) as src:
        raster_crs = src.crs
        from pyproj import Transformer

        if raster_crs and str(raster_crs) != 'EPSG:4326':
            transformer = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
        else:
            transformer = None

        for parcel in parcels:
            geom = _get_extraction_geometry(parcel, transformer)

            try:
                masked_data, _ = rasterio_mask(src, [geom], crop=True, all_touched=True)
                valid_pixels = masked_data[masked_data != src.nodata]

                if len(valid_pixels) > 0:
                    ndvi_val = float(np.mean(valid_pixels))
                    parcel['ndvi_series'].append(ndvi_val)
                else:
                    parcel['ndvi_series'].append(None)
            except Exception:
                parcel['ndvi_series'].append(None)

    # Extract NDWI if available
    if ndwi_path:
        with rasterio.open(ndwi_path) as src_ndwi:
            raster_crs_ndwi = src_ndwi.crs

            if raster_crs_ndwi and str(raster_crs_ndwi) != 'EPSG:4326':
                transformer_ndwi = Transformer.from_crs("EPSG:4326", raster_crs_ndwi, always_xy=True)
            else:
                transformer_ndwi = None

            for parcel in parcels:
                geom = _get_extraction_geometry(parcel, transformer_ndwi)

                try:
                    masked_data_ndwi, _ = rasterio_mask(src_ndwi, [geom], crop=True, all_touched=True)
                    valid_pixels_ndwi = masked_data_ndwi[masked_data_ndwi != src_ndwi.nodata]

                    if len(valid_pixels_ndwi) > 0:
                        ndwi_val = float(np.mean(valid_pixels_ndwi))
                        parcel['ndwi_series'].append(ndwi_val)
                    else:
                        parcel['ndwi_series'].append(None)
                except Exception:
                    parcel['ndwi_series'].append(None)


def _get_extraction_geometry(parcel: dict, transformer):
    """Get geometry for extraction (with projection if needed)."""
    if parcel.get('is_polygon', False):
        if transformer:
            from shapely.ops import transform as shapely_transform
            return shapely_transform(
                lambda x, y: transformer.transform(x, y),
                parcel['geometry']
            )
        return parcel['geometry']
    else:
        if transformer:
            x_proj, y_proj = transformer.transform(parcel['lon'], parcel['lat'])
            return Point(x_proj, y_proj).buffer(50)
        return parcel['geometry'].buffer(0.0005)


def _save_phenology_outputs(
    parcels: list[dict],
    output_geojson: Path,
    output_report: Path,
    start_date: str,
    end_date: str,
    total_scenes: int,
    n_observations: int
):
    """Save phenology analysis outputs."""
    # GeoJSON
    parcels_gdf = gpd.GeoDataFrame(parcels, crs="EPSG:4326")
    parcels_gdf.to_file(output_geojson, driver="GeoJSON")

    # Text report
    with open(output_report, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("IRR-US-01: TEMPORAL PHENOLOGY ANALYSIS REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write("TEMPORAL ANALYSIS SUMMARY:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Season Range: {start_date} to {end_date}\n")
        f.write(f"Temporal Observations: {n_observations}\n")
        f.write(f"Total Sentinel-2 Scenes: {total_scenes}\n")
        f.write(f"Total Parcels: {len(parcels)}\n\n")

        # Pattern distribution
        pattern_counts = {}
        for parcel in parcels:
            pattern = parcel.get('temporal_pattern', 'unknown')
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        f.write("TEMPORAL PATTERN DISTRIBUTION:\n")
        f.write("-" * 80 + "\n")
        for pattern, count in sorted(pattern_counts.items()):
            pct = 100 * count / len(parcels)
            f.write(f"  {pattern:20s}: {count:3d} ({pct:5.1f}%)\n")
        f.write("\n")

        # Parcel details
        f.write("PARCEL PHENOLOGY DETAILS:\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'ID':<6} {'Pattern':<20} {'Conf':<6} {'MaxNDVI':<8} {'EndNDVI':<8} {'Flood':<6}\n")
        f.write("-" * 80 + "\n")

        for parcel in parcels:
            metrics = parcel.get('phenology_metrics')
            if metrics:
                f.write(
                    f"{parcel['parcel_id']:<6} "
                    f"{parcel['temporal_pattern']:<20} "
                    f"{parcel['pattern_confidence']:<6.2f} "
                    f"{metrics['max_ndvi']:<8.3f} "
                    f"{metrics['end_ndvi']:<8.3f} "
                    f"{metrics['sustained_flooding_days']:<6}\n"
                )
            else:
                f.write(f"{parcel['parcel_id']:<6} {'insufficient_data':<20} {0.0:<6.2f} N/A\n")

    print(f"   ✅ GeoJSON: {output_geojson}")
    print(f"   ✅ Report: {output_report}")
