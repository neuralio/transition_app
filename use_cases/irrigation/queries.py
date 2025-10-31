"""
Irrigation Use Case Query Functions

Implements IRR-US-01 through IRR-US-17 from PRD.md
"""

import sys
from pathlib import Path
import json
import tempfile
import shutil
import numpy as np
import rasterio
from rasterio.mask import mask as rasterio_mask
from shapely.geometry import shape, Point
import geopandas as gpd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def query_irr_01_bare_soil_classification(
    geojson: dict,
    start_date: str,
    end_date: str,
    n_parcels: int = 20,
    parcel_locations: list[dict] | None = None,
    use_polygon_geometries: bool = False
) -> dict:
    """
    IRR-US-01: Automated Bare Soil Classification

    Uses Sentinel-2 NDVI to classify parcels as bare soil or vegetated.

    Args:
        geojson: User-drawn polygon (region of interest)
        start_date: Start date for EO data (YYYY-MM-DD)
        end_date: End date for EO data (YYYY-MM-DD)
        n_parcels: Number of parcels to generate within polygon (ignored if other modes used)
        parcel_locations: Optional list of user-specified coordinates [{"lat": 40.5, "lon": 22.7}, ...]
                         If provided, uses these exact locations instead of random sampling
        use_polygon_geometries: If True, analyzes ALL pixels within each polygon boundary (most accurate)

    Returns:
        dict: Classification results with success status
    """
    print("=" * 80)
    print("🌾 IRR-US-01: Automated Bare Soil Classification")
    print("=" * 80)
    print(f"📅 Date Range: {start_date} to {end_date}")
    if use_polygon_geometries:
        from backend.data.loaders.geojson_utils import extract_features
        num_polygons = len(extract_features(geojson))
        print(f"📍 Mode: Full Polygon Analysis ({num_polygons} field(s) - analyzes ALL pixels)")
    elif parcel_locations:
        print(f"📍 Mode: User-Specified Coordinates ({len(parcel_locations)} parcels - buffered points)")
    else:
        print(f"🔢 Mode: Random Sampling ({n_parcels} parcels - buffered points)")
    print("=" * 80)

    # Print GeoJSON details
    print("\n📍 INPUT GEOJSON:")
    print(f"   Type: {geojson.get('type', 'Unknown')}")
    if geojson.get('type') == 'FeatureCollection':
        print(f"   Features: {len(geojson.get('features', []))}")
        if geojson['features']:
            first_feat = geojson['features'][0]
            geom = first_feat.get('geometry', {})
            print(f"   Geometry Type: {geom.get('type', 'Unknown')}")
            if geom.get('coordinates'):
                coords = geom['coordinates'][0]  # First ring of polygon
                print(f"   Vertices: {len(coords)}")
                # Calculate bbox
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                bbox = [min(lons), min(lats), max(lons), max(lats)]
                print(f"   Bounding Box: {bbox}")
                print(f"   Lon Range: {min(lons):.4f} to {max(lons):.4f}")
                print(f"   Lat Range: {min(lats):.4f} to {max(lats):.4f}")
    print("=" * 80)

    # ========================================================================
    # STEP 1: Check for pre-downloaded NDVI data (SAME AS IRR-US-02)
    # ========================================================================
    print("\n🔄 Step 1: Loading pre-downloaded NDVI data...")

    from datetime import datetime
    import yaml
    import os

    # Load config to get NDVI data path
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Get NDVI repository path (expand ~ to home directory)
    ndvi_repo_path = Path(os.path.expanduser(config.get('ndvi', {}).get('data_path', '~/ndvi_data/thessaloniki')))

    # Check if NDVI data directory exists at all
    if not ndvi_repo_path.exists():
        raise RuntimeError(
            f"❌ NDVI data not found.\n\n"
            f"Please download NDVI data first using the download script:\n"
            f"   ./use_cases/irrigation/Sentinel/download_thessaloniki_ndvi_parallel.sh OUTPUT_DIR START_DATE END_DATE\n\n"
            f"Example:\n"
            f"   ./use_cases/irrigation/Sentinel/download_thessaloniki_ndvi_parallel.sh ~/ndvi_data/thessaloniki 20250701 20250731\n\n"
            f"See DEPLOY.md for detailed instructions."
        )

    year = datetime.strptime(start_date, "%Y-%m-%d").year
    year_dir = ndvi_repo_path / str(year)

    # Check if year directory exists
    if not year_dir.exists():
        # Get available years for helpful error message
        available_years = [d.name for d in ndvi_repo_path.iterdir() if d.is_dir() and d.name.isdigit()]
        available_str = ', '.join(sorted(available_years)) if available_years else "None"

        # Raise exception (Python will add "RuntimeError:" prefix automatically)
        raise RuntimeError(
            f"❌ No NDVI data found for year {year}\n\n"
            f"Available years in {ndvi_repo_path}:\n"
            f"{available_str}\n\n"
            f"Please use one of the available years."
        )

    # Find NDVI files in daily directory
    ndvi_daily_dir = year_dir / "products" / "ndvi" / "daily"

    if not ndvi_daily_dir.exists():
        raise RuntimeError(
            f"❌ NDVI daily directory not found: {ndvi_daily_dir}\n\n"
            f"Expected structure: {year}/products/ndvi/daily/NDVI_*.tif"
        )

    # List all available NDVI files
    all_ndvi_files = sorted(ndvi_daily_dir.glob("NDVI_*.tif"))
    if not all_ndvi_files:
        raise RuntimeError(
            f"❌ No NDVI files found in {ndvi_daily_dir}\n\n"
            f"Expected files: NDVI_YYYYMMDD.tif"
        )

    # Filter NDVI files to match requested date range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    ndvi_files = []
    for ndvi_file in all_ndvi_files:
        # Extract date from filename: NDVI_YYYYMMDD.tif
        date_str = ndvi_file.stem.split('_')[1]  # Get YYYYMMDD
        try:
            file_date = datetime.strptime(date_str, "%Y%m%d")
            if start_dt <= file_date <= end_dt:
                ndvi_files.append(ndvi_file)
        except ValueError:
            continue  # Skip files with invalid date format

    if not ndvi_files:
        # Show what dates ARE available
        available_dates = []
        for f in all_ndvi_files[:5]:  # Show first 5 as examples
            date_str = f.stem.split('_')[1]
            try:
                file_date = datetime.strptime(date_str, "%Y%m%d")
                available_dates.append(file_date.strftime("%Y-%m-%d"))
            except:
                pass

        raise RuntimeError(
            f"❌ No NDVI data found for requested date range: {start_date} to {end_date}\n\n"
            f"Available NDVI files in {year}: {len(all_ndvi_files)} files\n"
            f"Example dates: {', '.join(available_dates)}\n\n"
            f"Please adjust your date range to match available data."
        )

    print(f"✅ Found {len(ndvi_files)} NDVI files for date range {start_date} to {end_date}")
    print(f"   📁 NDVI directory: {ndvi_daily_dir}")

    # Set scenes_found for report (number of NDVI files in date range)
    scenes_found = len(ndvi_files)

    # Use the first available NDVI file as primary (will iterate through all later)
    ndvi_path = str(ndvi_files[0])

    # Check for NDWI files (optional)
    ndwi_daily_dir = year_dir / "products" / "ndwi" / "daily"
    ndwi_path = None
    if ndwi_daily_dir.exists():
        ndwi_files = sorted(ndwi_daily_dir.glob("NDWI_*.tif"))
        if ndwi_files:
            ndwi_path = str(ndwi_files[0])
            print(f"   📁 NDWI directory: {ndwi_daily_dir} ({len(ndwi_files)} files)")
        else:
            print(f"   ⚠️  NDWI data not available (will skip water detection)")
    else:
        print(f"   ⚠️  NDWI data not available (will skip water detection)")

    print("=" * 80)

    try:
        # Step 2: Get or generate parcels
        if use_polygon_geometries:
            # Use full polygon geometries for analysis
            print(f"\n🔄 Step 2: Extracting polygon geometries for full-field analysis...")
            from backend.data.loaders.geojson_utils import extract_features
            features = extract_features(geojson)

            parcels = []
            for idx, feature in enumerate(features):
                geometry = feature.get('geometry', feature)
                poly_geom = shape(geometry)

                # Calculate centroid for display purposes
                centroid = poly_geom.centroid

                parcels.append({
                    'parcel_id': idx + 1,
                    'lat': centroid.y,  # For display
                    'lon': centroid.x,  # For display
                    'geometry': poly_geom,  # Full polygon geometry for NDVI extraction
                    'is_polygon': True  # Flag to indicate polygon mode
                })
            print(f"✅ Loaded {len(parcels)} polygon geometr(y/ies)")
        elif parcel_locations:
            # Use user-specified coordinates
            print(f"\n🔄 Step 2: Using {len(parcel_locations)} user-specified parcel location(s)...")
            parcels = []
            for idx, loc in enumerate(parcel_locations):
                lat = loc['lat']
                lon = loc['lon']
                point = Point(lon, lat)  # shapely uses (lon, lat) order
                parcels.append({
                    'parcel_id': idx + 1,
                    'lat': lat,
                    'lon': lon,
                    'geometry': point,
                    'is_polygon': False  # Point mode
                })
            print(f"✅ Loaded {len(parcels)} user-specified parcels")
        else:
            # Generate random parcels within polygon
            print(f"\n🔄 Step 2: Generating {n_parcels} random parcels within polygon...")
            print(f"   🎲 Using random sampling (different parcels each run)")

            # Extract geometry from GeoJSON (handle both direct geometry and FeatureCollection)
            if geojson.get('type') == 'FeatureCollection':
                # Extract first feature's geometry
                polygon_geom = shape(geojson['features'][0]['geometry'])
            elif geojson.get('type') in ['Polygon', 'MultiPolygon']:
                # Direct geometry
                polygon_geom = shape(geojson)
            else:
                raise ValueError(f"Unsupported GeoJSON type: {geojson.get('type')}")

            bounds = polygon_geom.bounds  # (minx, miny, maxx, maxy)

            parcels = []
            attempts = 0
            max_attempts = n_parcels * 100

            while len(parcels) < n_parcels and attempts < max_attempts:
                # Generate random point within bounding box
                random_lon = np.random.uniform(bounds[0], bounds[2])
                random_lat = np.random.uniform(bounds[1], bounds[3])
                point = Point(random_lon, random_lat)

                # Check if point is inside polygon
                if polygon_geom.contains(point):
                    parcels.append({
                        'parcel_id': len(parcels) + 1,
                        'lat': random_lat,
                        'lon': random_lon,
                        'geometry': point,
                        'is_polygon': False  # Point mode
                    })

                attempts += 1

            if len(parcels) < n_parcels:
                print(f"⚠️  Warning: Only generated {len(parcels)} parcels (requested {n_parcels})")

            print(f"✅ Generated {len(parcels)} parcels")

        # Step 3: Extract NDVI and NDWI for each parcel
        print(f"\n🔄 Step 3: Extracting NDVI and NDWI values for each parcel...")

        # Extract NDVI
        with rasterio.open(ndvi_path) as src:
            # Get raster CRS
            raster_crs = src.crs
            print(f"   📍 Raster CRS: {raster_crs}, Parcels CRS: EPSG:4326")

            # Reproject parcels to raster CRS if needed
            from pyproj import Transformer
            if raster_crs is not None and str(raster_crs) != 'EPSG:4326':
                transformer = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
                print(f"   🔄 Reprojecting parcels from EPSG:4326 to {raster_crs}")

            for parcel in parcels:
                # Choose extraction geometry based on mode
                if parcel.get('is_polygon', False):
                    # Use full polygon geometry (reproject if needed)
                    if raster_crs is not None and str(raster_crs) != 'EPSG:4326':
                        # Reproject polygon
                        from shapely.ops import transform as shapely_transform
                        geom_to_mask = shapely_transform(
                            lambda x, y: transformer.transform(x, y),
                            parcel['geometry']
                        )
                    else:
                        geom_to_mask = parcel['geometry']
                else:
                    # Use buffered point (existing behavior)
                    if raster_crs is not None and str(raster_crs) != 'EPSG:4326':
                        x_proj, y_proj = transformer.transform(parcel['lon'], parcel['lat'])
                        point_proj = Point(x_proj, y_proj)
                        # Buffer in meters (50m) since we're in projected CRS
                        geom_to_mask = point_proj.buffer(50)
                    else:
                        # Use original point with degree buffer
                        geom_to_mask = parcel['geometry'].buffer(0.0005)

                # Extract NDVI within geometry
                try:
                    masked_data, _ = rasterio_mask(
                        src,
                        [geom_to_mask],
                        crop=True,
                        all_touched=True
                    )
                    # Calculate mean NDVI
                    valid_pixels = masked_data[masked_data != src.nodata]
                    if len(valid_pixels) > 0:
                        parcel['ndvi'] = float(np.mean(valid_pixels))
                        parcel['ndvi_pixels'] = len(valid_pixels)  # Track number of pixels analyzed
                    else:
                        parcel['ndvi'] = None
                        parcel['ndvi_pixels'] = 0
                except Exception as e:
                    print(f"⚠️  Warning: Could not extract NDVI for parcel {parcel['parcel_id']}: {e}")
                    parcel['ndvi'] = None
                    parcel['ndvi_pixels'] = 0

        # Extract NDWI if available (paper methodology: distinguish water from bare soil)
        if ndwi_path:
            print(f"   🌊 Extracting NDWI values for water detection...")
            with rasterio.open(ndwi_path) as src_ndwi:
                raster_crs_ndwi = src_ndwi.crs
                # Reproject parcels if needed
                from pyproj import Transformer
                if raster_crs_ndwi is not None and str(raster_crs_ndwi) != 'EPSG:4326':
                    transformer_ndwi = Transformer.from_crs("EPSG:4326", raster_crs_ndwi, always_xy=True)

                for parcel in parcels:
                    # Choose extraction geometry (same logic as NDVI)
                    if parcel.get('is_polygon', False):
                        if raster_crs_ndwi is not None and str(raster_crs_ndwi) != 'EPSG:4326':
                            from shapely.ops import transform as shapely_transform
                            geom_to_mask = shapely_transform(
                                lambda x, y: transformer_ndwi.transform(x, y),
                                parcel['geometry']
                            )
                        else:
                            geom_to_mask = parcel['geometry']
                    else:
                        if raster_crs_ndwi is not None and str(raster_crs_ndwi) != 'EPSG:4326':
                            x_proj, y_proj = transformer_ndwi.transform(parcel['lon'], parcel['lat'])
                            point_proj = Point(x_proj, y_proj)
                            geom_to_mask = point_proj.buffer(50)
                        else:
                            geom_to_mask = parcel['geometry'].buffer(0.0005)

                    # Extract NDWI
                    try:
                        masked_data_ndwi, _ = rasterio_mask(
                            src_ndwi,
                            [geom_to_mask],
                            crop=True,
                            all_touched=True
                        )
                        valid_pixels_ndwi = masked_data_ndwi[masked_data_ndwi != src_ndwi.nodata]
                        if len(valid_pixels_ndwi) > 0:
                            parcel['ndwi'] = float(np.mean(valid_pixels_ndwi))
                        else:
                            parcel['ndwi'] = None
                    except Exception as e:
                        print(f"⚠️  Warning: Could not extract NDWI for parcel {parcel['parcel_id']}: {e}")
                        parcel['ndwi'] = None
        else:
            # No NDWI available - set to None for all parcels
            for parcel in parcels:
                parcel['ndwi'] = None

        # Step 4: Classify parcels using NDVI/NDWI (paper methodology)
        print(f"\n🔄 Step 4: Classifying parcels using NDVI/NDWI methodology...")
        print(f"   📋 Classification Rules (from paper):")
        print(f"      - NDVI < 0.25: Bare soil or water (check NDWI)")
        print(f"      - NDVI >= 0.25: Vegetated")
        print(f"      - NDWI > 0 (when NDVI < 0.25): Flooded/water surface")
        print(f"      - NDWI <= 0 (when NDVI < 0.25): Dry bare soil")

        ndvi_threshold = 0.25  # Paper: NDVI < 0.2-0.3 indicates bare soil
        ndwi_threshold = 0.0   # Paper: NDWI > 0 indicates water presence

        # Classification counters
        class_counts = {
            'vegetated': 0,
            'bare_soil': 0,
            'flooded': 0,
            'no_data': 0
        }

        # Store values for statistics
        ndvi_by_class = {
            'vegetated': [],
            'bare_soil': [],
            'flooded': []
        }
        ndwi_by_class = {
            'vegetated': [],
            'bare_soil': [],
            'flooded': []
        }

        for parcel in parcels:
            if parcel['ndvi'] is not None:
                if parcel['ndvi'] < ndvi_threshold:
                    # Low NDVI - could be bare soil OR water
                    if parcel['ndwi'] is not None and parcel['ndwi'] > ndwi_threshold:
                        # High NDWI = water present (flooded field, paddy, wetland)
                        parcel['classification'] = 'flooded'
                        class_counts['flooded'] += 1
                        ndvi_by_class['flooded'].append(parcel['ndvi'])
                        if parcel['ndwi'] is not None:
                            ndwi_by_class['flooded'].append(parcel['ndwi'])
                    else:
                        # Low/no NDWI = dry bare soil (fallow, harvested, uncultivated)
                        parcel['classification'] = 'bare_soil'
                        class_counts['bare_soil'] += 1
                        ndvi_by_class['bare_soil'].append(parcel['ndvi'])
                        if parcel['ndwi'] is not None:
                            ndwi_by_class['bare_soil'].append(parcel['ndwi'])
                else:
                    # High NDVI = vegetated (crops present)
                    parcel['classification'] = 'vegetated'
                    class_counts['vegetated'] += 1
                    ndvi_by_class['vegetated'].append(parcel['ndvi'])
                    if parcel['ndwi'] is not None:
                        ndwi_by_class['vegetated'].append(parcel['ndwi'])
            else:
                parcel['classification'] = 'no_data'
                class_counts['no_data'] += 1

        # Step 5: Create output files with timestamp
        print(f"\n🔄 Step 5: Generating output files with timestamp...")

        # Create timestamped directory (like MLU-08 pattern)
        from datetime import datetime as dt
        timestamp_dir = dt.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"use_cases/irrigation/results/irr_01/{timestamp_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"   📁 Output Directory: {output_dir}")

        # File paths
        date_str = start_date.replace("-", "")
        output_map = output_dir / f"classification_map_{date_str}.geojson"
        output_report = output_dir / f"classification_report_{date_str}.txt"

        # GeoJSON output
        parcels_gdf = gpd.GeoDataFrame(parcels, crs="EPSG:4326")
        parcels_gdf.to_file(output_map, driver="GeoJSON")

        # Text report
        with open(output_report, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("IRRIGATION USE CASE: Bare Soil Classification Report\n")
            f.write("=" * 80 + "\n\n")

            # Initial Setup Summary (like MLU/CCA/GCP)
            f.write("INITIAL SETUP:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Date Range: {start_date} to {end_date}\n")
            f.write(f"Total Parcels: {len(parcels)}\n")

            # Analysis mode
            if use_polygon_geometries:
                f.write(f"Analysis Mode: Full Polygon Analysis (all pixels within boundaries)\n")
                from backend.data.loaders.geojson_utils import extract_features
                num_fields = len(extract_features(geojson))
                f.write(f"  - Number of Fields: {num_fields}\n")
                # Calculate average pixels per polygon
                avg_pixels = sum(p.get('ndvi_pixels', 0) for p in parcels) / len(parcels)
                f.write(f"  - Average Pixels per Field: {avg_pixels:.0f}\n")
            elif parcel_locations:
                f.write(f"Analysis Mode: Point Coordinates (50m buffered points)\n")
                f.write(f"  - Coordinates Provided: {len(parcel_locations)}\n")
            else:
                f.write(f"Analysis Mode: Random Sampling (within polygon)\n")
                f.write(f"  - Random Points Generated: {n_parcels}\n")

            f.write(f"Classification Method: NDVI/NDWI Multi-Index (Paper Methodology)\n")
            f.write(f"  - NDVI Threshold: 0.25 (values below = bare/water)\n")
            f.write(f"  - NDWI Threshold: 0.0 (values above = water present)\n")
            f.write(f"Sentinel-2 Scenes Processed: {scenes_found}\n")
            f.write("\n")

            f.write("CLASSIFICATION RESULTS:\n")
            f.write("=" * 80 + "\n")
            total_valid = len(parcels) - class_counts['no_data']
            if total_valid > 0:
                f.write(f"  - Vegetated:  {class_counts['vegetated']:3d} ({100*class_counts['vegetated']/total_valid:.1f}%) - Crops present (NDVI >= 0.25)\n")
                f.write(f"  - Bare Soil:  {class_counts['bare_soil']:3d} ({100*class_counts['bare_soil']/total_valid:.1f}%) - Dry bare soil (NDVI < 0.25, NDWI <= 0)\n")
                f.write(f"  - Flooded:    {class_counts['flooded']:3d} ({100*class_counts['flooded']/total_valid:.1f}%) - Water surface (NDVI < 0.25, NDWI > 0)\n")
                if class_counts['no_data'] > 0:
                    f.write(f"  - No Data:    {class_counts['no_data']:3d} ({100*class_counts['no_data']/len(parcels):.1f}%) - Missing observations\n")
            f.write("\n")

            f.write("MEAN INDEX VALUES BY CLASS:\n")
            f.write("-" * 80 + "\n")
            for cls in ['vegetated', 'bare_soil', 'flooded']:
                if len(ndvi_by_class[cls]) > 0:
                    mean_ndvi = np.mean(ndvi_by_class[cls])
                    mean_ndwi = np.mean(ndwi_by_class[cls]) if len(ndwi_by_class[cls]) > 0 else None
                    f.write(f"  {cls.capitalize():12s}: NDVI={mean_ndvi:.3f}")
                    if mean_ndwi is not None:
                        f.write(f", NDWI={mean_ndwi:.3f}")
                    f.write(f" (n={len(ndvi_by_class[cls])})\n")
            f.write("\n")

            f.write("PARCEL DETAILS:\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'ID':<6} {'Lat':<10} {'Lon':<10} {'NDVI':<8} {'NDWI':<8} {'Classification':<15}\n")
            f.write("-" * 80 + "\n")
            for parcel in parcels:
                ndvi_str = f"{parcel['ndvi']:.3f}" if parcel['ndvi'] is not None else "N/A"
                ndwi_str = f"{parcel['ndwi']:.3f}" if parcel.get('ndwi') is not None else "N/A"
                f.write(
                    f"{parcel['parcel_id']:<6} "
                    f"{parcel['lat']:<10.5f} "
                    f"{parcel['lon']:<10.5f} "
                    f"{ndvi_str:<8} "
                    f"{ndwi_str:<8} "
                    f"{parcel['classification']:<15}\n"
                )

        print(f"✅ Classification map saved to: {output_map}")
        print(f"✅ Text report saved to: {output_report}")

        # Step 6: Create visualizations
        print(f"\n🔄 Step 6: Creating visualization plots...")

        import plotly.graph_objects as go
        import plotly.express as px
        from plotly.subplots import make_subplots
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        # Plot 1: Pie Chart - Classification Distribution (3-class system)
        pie_labels = []
        pie_values = []
        pie_colors = []

        if class_counts['vegetated'] > 0:
            pie_labels.append('Vegetated')
            pie_values.append(class_counts['vegetated'])
            pie_colors.append('#5cb85c')  # Green

        if class_counts['bare_soil'] > 0:
            pie_labels.append('Bare Soil')
            pie_values.append(class_counts['bare_soil'])
            pie_colors.append('#d4a373')  # Brown

        if class_counts['flooded'] > 0:
            pie_labels.append('Flooded')
            pie_values.append(class_counts['flooded'])
            pie_colors.append('#4A90E2')  # Blue

        if class_counts['no_data'] > 0:
            pie_labels.append('No Data')
            pie_values.append(class_counts['no_data'])
            pie_colors.append('#999999')  # Gray

        pie_fig = go.Figure(data=[go.Pie(
            labels=pie_labels,
            values=pie_values,
            marker=dict(colors=pie_colors),
            textinfo='label+percent+value',
            hole=0.3
        )])
        pie_fig.update_layout(
            title=f"Land Cover Classification (NDVI/NDWI)<br><sub>{start_date} to {end_date}</sub>",
            font=dict(size=14),
            showlegend=True,
            height=500
        )
        pie_chart_path = output_dir / f"classification_pie_{date_str}.html"
        pie_fig.write_html(pie_chart_path, include_plotlyjs='cdn')  # Use CDN to reduce file size
        print(f"   ✅ Pie chart: {pie_chart_path} (using CDN for fast loading)")

        # Plot 2: NDVI Histogram
        all_ndvi = [p['ndvi'] for p in parcels if p['ndvi'] is not None]
        if all_ndvi:
            hist_fig = go.Figure()
            hist_fig.add_trace(go.Histogram(
                x=all_ndvi,
                nbinsx=20,
                marker_color='#5cb85c',
                name='NDVI Distribution',
                opacity=0.7
            ))
            # Add threshold line
            hist_fig.add_vline(
                x=ndvi_threshold,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Threshold: {ndvi_threshold}",
                annotation_position="top right"
            )
            hist_fig.update_layout(
                title=f"NDVI Distribution<br><sub>Bare Soil: NDVI < {ndvi_threshold}</sub>",
                xaxis_title="NDVI Value",
                yaxis_title="Number of Parcels",
                font=dict(size=14),
                height=500,
                bargap=0.1
            )
            hist_chart_path = output_dir / f"ndvi_histogram_{date_str}.html"
            hist_fig.write_html(hist_chart_path, include_plotlyjs='cdn')  # Use CDN to reduce file size
            print(f"   ✅ Histogram: {hist_chart_path} (using CDN for fast loading)")

        # Plot 3: Beautiful Interactive Spatial Map (Folium)
        import folium
        from folium.plugins import MarkerCluster, MiniMap

        # Calculate center and bounds
        center_lat = sum([p['lat'] for p in parcels]) / len(parcels)
        center_lon = sum([p['lon'] for p in parcels]) / len(parcels)

        # Create map with satellite imagery option
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles=None,  # No default tile
            control_scale=True
        )

        # Add multiple tile layers for user choice
        folium.TileLayer('OpenStreetMap', name='Street Map', show=True).add_to(m)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)

        # Add original polygon boundary with styling
        if geojson.get('type') == 'FeatureCollection':
            folium.GeoJson(
                geojson,
                name='Study Area',
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': '#FF4444',
                    'weight': 3,
                    'dashArray': '10, 5',
                    'fillOpacity': 0.1
                },
                tooltip='Study Area Boundary'
            ).add_to(m)

        # Add parcels with enhanced styling (3-class system)
        for parcel in parcels:
            if parcel['ndvi'] is not None:
                # Enhanced colors for 3 classes
                if parcel['classification'] == 'bare_soil':
                    color = '#CD853F'  # Peru brown
                    fill_color = '#DEB887'  # Burlywood
                    icon_symbol = '🏜️'
                elif parcel['classification'] == 'flooded':
                    color = '#4A90E2'  # Blue
                    fill_color = '#A4C8E1'  # Light blue
                    icon_symbol = '💧'
                else:  # vegetated
                    color = '#228B22'  # Forest green
                    fill_color = '#90EE90'  # Light green
                    icon_symbol = '🌿'

                # Enhanced popup with NDVI and NDWI
                ndwi_row = ""
                if parcel.get('ndwi') is not None:
                    ndwi_row = f"""
                        <tr>
                            <td style="padding: 3px; font-weight: bold;">NDWI Value:</td>
                            <td style="padding: 3px;">{parcel['ndwi']:.4f}</td>
                        </tr>
                    """

                popup_html = f"""
                <div style="font-family: Arial, sans-serif; min-width: 200px;">
                    <h4 style="margin: 0 0 10px 0; color: #333; border-bottom: 2px solid {color}; padding-bottom: 5px;">
                        {icon_symbol} Parcel #{parcel['parcel_id']}
                    </h4>
                    <table style="width: 100%; font-size: 13px;">
                        <tr>
                            <td style="padding: 3px; font-weight: bold;">Classification:</td>
                            <td style="padding: 3px; color: {color};">{parcel['classification'].replace('_', ' ').title()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 3px; font-weight: bold;">NDVI Value:</td>
                            <td style="padding: 3px;">{parcel['ndvi']:.4f}</td>
                        </tr>
                        {ndwi_row}
                        <tr>
                            <td style="padding: 3px; font-weight: bold;">Coordinates:</td>
                            <td style="padding: 3px; font-size: 11px;">{parcel['lat']:.5f}°N<br>{parcel['lon']:.5f}°E</td>
                        </tr>
                        <tr>
                            <td style="padding: 3px; font-weight: bold;">Date Range:</td>
                            <td style="padding: 3px; font-size: 11px;">{start_date}<br>to {end_date}</td>
                        </tr>
                    </table>
                </div>
                """

                tooltip_text = f"Parcel {parcel['parcel_id']}: {parcel['classification'].replace('_', ' ').title()} (NDVI: {parcel['ndvi']:.3f}"
                if parcel.get('ndwi') is not None:
                    tooltip_text += f", NDWI: {parcel['ndwi']:.3f}"
                tooltip_text += ")"

                folium.CircleMarker(
                    location=[parcel['lat'], parcel['lon']],
                    radius=10,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=tooltip_text,
                    color=color,
                    fill=True,
                    fillColor=fill_color,
                    fillOpacity=0.8,
                    weight=2,
                    opacity=1.0
                ).add_to(m)

        # Enhanced legend with summary statistics
        legend_html = f'''
        <div style="position: fixed; top: 10px; right: 10px; width: 280px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none; border-radius: 10px; z-index:9999;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                    color: white; font-family: Arial, sans-serif;">
            <div style="padding: 15px;">
                <h3 style="margin: 0 0 15px 0; font-size: 18px; border-bottom: 2px solid rgba(255,255,255,0.3); padding-bottom: 10px;">
                    🌾 Bare Soil Classification
                </h3>

                <div style="background: rgba(255,255,255,0.15); padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                    <p style="margin: 5px 0; font-size: 13px;">
                        <strong>📅 Period:</strong><br>
                        <span style="font-size: 12px;">{start_date} to {end_date}</span>
                    </p>
                </div>

                <div style="background: rgba(255,255,255,0.15); padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                    <p style="margin: 5px 0; font-size: 13px;">
                        <strong>📊 Summary Statistics:</strong>
                    </p>
                    <p style="margin: 5px 0; font-size: 12px;">
                        • Total Parcels: <strong>{len(parcels)}</strong><br>
                        • Vegetated: <strong>{class_counts['vegetated']}</strong> ({100*class_counts['vegetated']/len(parcels):.1f}%)<br>
                        • Bare Soil: <strong>{class_counts['bare_soil']}</strong> ({100*class_counts['bare_soil']/len(parcels):.1f}%)<br>
                        • Flooded: <strong>{class_counts['flooded']}</strong> ({100*class_counts['flooded']/len(parcels):.1f}%)
                    </p>
                </div>

                <div style="background: rgba(255,255,255,0.15); padding: 10px; border-radius: 5px;">
                    <p style="margin: 5px 0; font-size: 13px;">
                        <strong>🗺️ Legend (NDVI/NDWI Method):</strong>
                    </p>
                    <p style="margin: 8px 0; font-size: 12px;">
                        <span style="display: inline-block; width: 15px; height: 15px; background: #90EE90;
                               border: 2px solid #228B22; border-radius: 50%; vertical-align: middle;"></span>
                        <strong> Vegetated</strong> (NDVI ≥ 0.25)
                    </p>
                    <p style="margin: 8px 0; font-size: 12px;">
                        <span style="display: inline-block; width: 15px; height: 15px; background: #DEB887;
                               border: 2px solid #CD853F; border-radius: 50%; vertical-align: middle;"></span>
                        <strong> Bare Soil</strong> (NDVI < 0.25, NDWI ≤ 0)
                    </p>
                    <p style="margin: 8px 0; font-size: 12px;">
                        <span style="display: inline-block; width: 15px; height: 15px; background: #A4C8E1;
                               border: 2px solid #4A90E2; border-radius: 50%; vertical-align: middle;"></span>
                        <strong> Flooded</strong> (NDVI < 0.25, NDWI > 0)
                    </p>
                    <p style="margin: 8px 0; font-size: 12px;">
                        <span style="display: inline-block; width: 30px; height: 2px; background: transparent;
                               border: 2px dashed #FF4444; vertical-align: middle;"></span>
                        <strong> Study Boundary</strong>
                    </p>
                </div>

                <p style="margin: 10px 0 0 0; font-size: 10px; opacity: 0.8; text-align: center;">
                    Click markers for details | Switch basemaps in layer control
                </p>
            </div>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # Add layer control
        folium.LayerControl(position='topleft').add_to(m)

        # Add minimap for context
        minimap = MiniMap(toggle_display=True, position='bottomright')
        m.add_child(minimap)

        # Add fullscreen button
        from folium.plugins import Fullscreen
        Fullscreen(position='topleft').add_to(m)

        map_path = output_dir / f"classification_map_{date_str}.html"
        m.save(map_path)
        print(f"   ✅ Interactive map: {map_path}")

        print("=" * 80)
        print(f"📊 All outputs saved to: {output_dir}")
        print("=" * 80)

        # Generate NDVI/NDWI Time-Series Map with Slider
        print(f"\n🔄 Generating NDVI/NDWI time-series map with slider...")
        from use_cases.irrigation.visualizations.ndvi_timeseries_map import create_ndvi_timeseries_map

        timeseries_map_path = output_dir / f"ndvi_timeseries_map_{date_str}.html"
        try:
            # Prepare NDWI file list (matching NDVI files)
            ndwi_files_list = []
            if ndwi_daily_dir and ndwi_daily_dir.exists():
                for ndvi_file in ndvi_files:
                    date_str_file = ndvi_file.stem.split('_')[1]
                    ndwi_file = ndwi_daily_dir / f"NDWI_{date_str_file}.tif"
                    ndwi_files_list.append(ndwi_file)
            else:
                ndwi_files_list = [None] * len(ndvi_files)

            create_ndvi_timeseries_map(
                geojson=geojson,
                ndvi_files=ndvi_files,
                ndwi_files=ndwi_files_list,
                output_path=str(timeseries_map_path),
                parcel_data=parcels
            )
            print(f"   ✅ Time-series map: {timeseries_map_path}")
        except Exception as e:
            print(f"   ⚠️  Could not generate time-series map: {e}")
            timeseries_map_path = None

        # Console summary of classification results
        print("\n" + "=" * 80)
        print("📋 CLASSIFICATION SUMMARY (NDVI/NDWI Paper Methodology)")
        print("=" * 80)
        total_valid = len(parcels) - class_counts['no_data']
        if total_valid > 0:
            print(f"  Total Parcels Analyzed: {total_valid}")
            print(f"  • Vegetated:  {class_counts['vegetated']:3d} parcels ({100*class_counts['vegetated']/total_valid:5.1f}%) - Crops present")
            print(f"  • Bare Soil:  {class_counts['bare_soil']:3d} parcels ({100*class_counts['bare_soil']/total_valid:5.1f}%) - Dry bare soil")
            print(f"  • Flooded:    {class_counts['flooded']:3d} parcels ({100*class_counts['flooded']/total_valid:5.1f}%) - Water/flooded fields")
            if class_counts['no_data'] > 0:
                print(f"  • No Data:    {class_counts['no_data']:3d} parcels (missing observations)")
        print("=" * 80)

        # Return results (updated for 3-class system)
        return {
            "success": True,
            "total_parcels": len(parcels),
            "vegetated_count": class_counts['vegetated'],
            "bare_soil_count": class_counts['bare_soil'],
            "flooded_count": class_counts['flooded'],
            "no_data_count": class_counts['no_data'],
            "vegetated_pct": 100 * class_counts['vegetated'] / total_valid if total_valid > 0 else 0.0,
            "bare_soil_pct": 100 * class_counts['bare_soil'] / total_valid if total_valid > 0 else 0.0,
            "flooded_pct": 100 * class_counts['flooded'] / total_valid if total_valid > 0 else 0.0,
            "mean_ndvi_vegetated": float(np.mean(ndvi_by_class['vegetated'])) if ndvi_by_class['vegetated'] else 0.0,
            "mean_ndvi_bare_soil": float(np.mean(ndvi_by_class['bare_soil'])) if ndvi_by_class['bare_soil'] else 0.0,
            "mean_ndvi_flooded": float(np.mean(ndvi_by_class['flooded'])) if ndvi_by_class['flooded'] else 0.0,
            "mean_ndwi_vegetated": float(np.mean(ndwi_by_class['vegetated'])) if ndwi_by_class['vegetated'] else None,
            "mean_ndwi_bare_soil": float(np.mean(ndwi_by_class['bare_soil'])) if ndwi_by_class['bare_soil'] else None,
            "mean_ndwi_flooded": float(np.mean(ndwi_by_class['flooded'])) if ndwi_by_class['flooded'] else None,
            "output_map": str(output_map),
            "output_report": str(output_report),
            "output_pie_chart": str(pie_chart_path),
            "output_histogram": str(hist_chart_path) if all_ndvi else None,
            "output_interactive_map": str(map_path),
            "output_timeseries_map": str(timeseries_map_path) if timeseries_map_path else None,
            "output_dir": str(output_dir),
            "parcels": parcels  # Full data for further processing
        }

    finally:
        # NDVI files are now cached for reuse - no cleanup needed
        # Cache location: /tmp/ndvi_cache/{hash}/
        # Files will be reused if same bbox+dates requested again
        pass
