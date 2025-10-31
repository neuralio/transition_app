"""Generic data loader for pilot data."""

import xarray as xr
from pathlib import Path
from typing import Optional, Union, Dict
import logging

# Import config and path builder
try:
    from use_cases.mlu.config_loader import load_config
    from backend.data.loaders.data_paths import DataPathBuilder
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False

# Import spatial filtering functions
try:
    from backend.data.loaders.spatial_filter import (
        filter_netcdf_by_geojson,
        get_polygon_bounds
    )
    _SPATIAL_FILTER_AVAILABLE = True
except ImportError:
    _SPATIAL_FILTER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Global config instance (lazy loaded)
_global_config = None
_global_path_builder = None


def _get_path_builder(data_path: str):
    """Get or create DataPathBuilder instance."""
    global _global_config, _global_path_builder

    if not _CONFIG_AVAILABLE:
        # Fallback: config not available, return None
        return None

    if _global_path_builder is None:
        try:
            _global_config = load_config()
            _global_path_builder = DataPathBuilder(
                base_path=_global_config.data_path,
                subdirs=_global_config.data_subdirs,
                files=_global_config.data_files
            )
        except Exception:
            # Config loading failed, use fallback mode
            return None

    return _global_path_builder


def _apply_spatial_filter(
    ds: xr.Dataset,
    geojson: Optional[Union[str, dict]] = None,
    method: str = 'bounds'
) -> xr.Dataset:
    """
    Apply spatial filtering to xarray Dataset using GeoJSON polygon.

    Args:
        ds: xarray Dataset to filter
        geojson: Optional GeoJSON polygon (string or dict)
        method: 'bounds' (fast) or 'mask' (precise) - default: 'bounds'

    Returns:
        Filtered xarray Dataset (or original if no geojson provided)
    """
    if geojson is None:
        return ds

    if not _SPATIAL_FILTER_AVAILABLE:
        logger.warning("Spatial filtering not available (shapely not installed). Returning unfiltered data.")
        return ds

    try:
        # Apply spatial filtering
        # NOTE: Validation should be done in run scripts BEFORE calling loaders
        logger.info(f"Applying spatial filter (method={method})...")
        filtered_ds = filter_netcdf_by_geojson(ds, geojson, method=method)

        # Log the filtering results
        orig_lat_size = ds.sizes.get('lat', ds.sizes.get('latitude', 0))
        orig_lon_size = ds.sizes.get('lon', ds.sizes.get('longitude', 0))
        filt_lat_size = filtered_ds.sizes.get('lat', filtered_ds.sizes.get('latitude', 0))
        filt_lon_size = filtered_ds.sizes.get('lon', filtered_ds.sizes.get('longitude', 0))

        # Print to terminal AND log
        filter_msg = f"✅ Spatial filtering applied: {orig_lat_size}x{orig_lon_size} → {filt_lat_size}x{filt_lon_size} grid points"
        print(filter_msg)
        logger.info(filter_msg)

        # Print actual coordinate ranges for verification
        lat_coords = filtered_ds.coords.get('lat', filtered_ds.coords.get('latitude', None))
        lon_coords = filtered_ds.coords.get('lon', filtered_ds.coords.get('longitude', None))
        if lat_coords is not None and lon_coords is not None:
            lat_range = f"[{float(lat_coords.min()):.2f}, {float(lat_coords.max()):.2f}]"
            lon_range = f"[{float(lon_coords.min()):.2f}, {float(lon_coords.max()):.2f}]"
            coord_msg = f"   📍 Filtered data coordinates: lat={lat_range}, lon={lon_range}"
            print(coord_msg)
            logger.info(coord_msg)

        return filtered_ds

    except Exception as e:
        logger.error(f"❌ Failed to apply spatial filtering: {e}")
        return ds


# ==================== Meteorological Data ====================

def load_temperature(data_path, scenario, geojson=None):
    """Load temperature (tas) data.

    Args:
        data_path: Base path to data directory
        scenario: RCP scenario (rcp26, rcp45, rcp85) or 'historical'
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        xarray.Dataset with temperature data (spatially filtered if geojson provided)
    """
    # Try to use config-based paths
    path_builder = _get_path_builder(data_path)
    if path_builder:
        path = path_builder.get_meteo_file('temperature', scenario)
    else:
        # Fallback to hardcoded paths
        if scenario.lower() == 'historical':
            path = f"{data_path}/Historical/ERA5_LAND_TMP_MEAN.nc"
        else:
            path = f"{data_path}/meteo/tas_{scenario}.nc"

    ds = xr.open_dataset(str(path))
    return _apply_spatial_filter(ds, geojson)


def load_precipitation(data_path, scenario, geojson=None):
    """Load precipitation (pr) data.

    Args:
        data_path: Base path to data directory
        scenario: RCP scenario (rcp26, rcp45, rcp85) or 'historical'
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        xarray.Dataset with precipitation data (spatially filtered if geojson provided)
    """
    # Try to use config-based paths
    path_builder = _get_path_builder(data_path)
    if path_builder:
        path = path_builder.get_meteo_file('precipitation', scenario)
    else:
        # Fallback to hardcoded paths
        if scenario.lower() == 'historical':
            path = f"{data_path}/Historical/ERA5_LAND_RAIN.nc"
        else:
            path = f"{data_path}/meteo/pr_{scenario}.nc"

    ds = xr.open_dataset(str(path))
    return _apply_spatial_filter(ds, geojson)


def load_solar_radiation(data_path, scenario, geojson=None):
    """Load solar radiation (rsds) data.

    Args:
        data_path: Base path to data directory
        scenario: RCP scenario (rcp26, rcp45, rcp85) or 'historical'
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        xarray.Dataset with solar radiation data (spatially filtered if geojson provided)

    Note:
        - Future data (RCP): kWh/m²/day
        - Historical data (ERA5): kWh/m²/year → converted to kWh/m²/day
    """
    # Try to use config-based paths
    path_builder = _get_path_builder(data_path)
    if path_builder:
        path = path_builder.get_meteo_file('solar_radiation', scenario)
    else:
        # Fallback to hardcoded paths
        if scenario.lower() == 'historical':
            path = f"{data_path}/Historical/ERA5_LAND_SOLAR.nc"
        else:
            path = f"{data_path}/meteo/rsds_{scenario}.nc"

    ds = xr.open_dataset(str(path))

    # Convert historical from annual to daily units
    if scenario.lower() == 'historical':
        var_name = list(ds.data_vars.keys())[0]
        ds[var_name] = ds[var_name] / 365.0
        ds[var_name].attrs['units'] = 'kWh/m2/day'
        ds[var_name].attrs['note'] = 'Converted from annual to daily (original: kWh/m2/year)'

    return _apply_spatial_filter(ds, geojson)


def load_evapotranspiration(data_path, scenario, geojson=None):
    """Load evapotranspiration (evptsp) data.

    Args:
        data_path: Base path to data directory
        scenario: RCP scenario (rcp26, rcp45, rcp85) or 'historical'
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        xarray.Dataset with evapotranspiration data (spatially filtered if geojson provided)
    """
    if scenario.lower() == 'historical':
        path = f"{data_path}/Historical/ERA5_LAND_EVPT.nc"
    else:
        path = f"{data_path}/meteo/evptsp_{scenario}.nc"

    ds = xr.open_dataset(path)
    return _apply_spatial_filter(ds, geojson)


def load_all_meteo(data_path, scenario, geojson=None):
    """Load all meteorological data for scenario.

    Args:
        data_path: Base path to data directory
        scenario: RCP scenario (rcp26, rcp45, rcp85)
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        dict with keys: 'temperature', 'precipitation', 'solar_radiation', 'evapotranspiration'
        (all spatially filtered if geojson provided)
    """
    return {
        'temperature': load_temperature(data_path, scenario, geojson),
        'precipitation': load_precipitation(data_path, scenario, geojson),
        'solar_radiation': load_solar_radiation(data_path, scenario, geojson),
        'evapotranspiration': load_evapotranspiration(data_path, scenario, geojson)
    }


# ==================== Soil Data ====================

def load_soil_type(data_path, geojson=None):
    """Load soil type classification.

    Args:
        data_path: Base path to data directory
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        xarray.Dataset with soil type data (spatially filtered if geojson provided)
    """
    path = f"{data_path}/soil/SoilType_0-5cm_mean.nc"
    ds = xr.open_dataset(path)
    return _apply_spatial_filter(ds, geojson)


def load_soil_cec(data_path, geojson=None):
    """Load soil Cation Exchange Capacity (CEC).

    Args:
        data_path: Base path to data directory
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        xarray.Dataset with CEC data (spatially filtered if geojson provided)
    """
    path = f"{data_path}/soil/cec_0-5cm_mean.nc"
    ds = xr.open_dataset(path)
    return _apply_spatial_filter(ds, geojson)


def load_soil_ph(data_path, geojson=None):
    """Load soil pH (phh2o).

    Args:
        data_path: Base path to data directory
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        xarray.Dataset with pH data (spatially filtered if geojson provided)
    """
    path = f"{data_path}/soil/phh2o_0-5cm_mean.nc"
    ds = xr.open_dataset(path)
    return _apply_spatial_filter(ds, geojson)


def load_soil_organic_carbon(data_path, geojson=None):
    """Load Soil Organic Carbon (SOC).

    Args:
        data_path: Base path to data directory
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        xarray.Dataset with SOC data (spatially filtered if geojson provided)
    """
    path = f"{data_path}/soil/soc_0-5cm_mean.nc"
    ds = xr.open_dataset(path)
    return _apply_spatial_filter(ds, geojson)


def load_all_soil(data_path, geojson=None):
    """Load all soil data.

    Args:
        data_path: Base path to data directory
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        dict with keys: 'soil_type', 'cec', 'ph', 'organic_carbon'
        (all spatially filtered if geojson provided)
    """
    return {
        'soil_type': load_soil_type(data_path, geojson),
        'cec': load_soil_cec(data_path, geojson),
        'ph': load_soil_ph(data_path, geojson),
        'organic_carbon': load_soil_organic_carbon(data_path, geojson)
    }


# ==================== Terrain Data ====================

def load_dem(data_path, geojson=None):
    """Load Digital Elevation Model.

    Args:
        data_path: Base path to data directory
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        xarray.Dataset with elevation data (spatially filtered if geojson provided)
    """
    path = f"{data_path}/dem/DEM.nc"
    ds = xr.open_dataset(path)
    return _apply_spatial_filter(ds, geojson)


# ==================== Crop Data ====================

def load_crop_suitability(data_path, crop, scenario, filter_to_thessaloniki=True, geojson=None):
    """Load crop suitability (LUSA) predictions.

    Args:
        data_path: Base path to data directory
        crop: Crop type (e.g., 'MAIZE', 'WHEAT')
        scenario: RCP scenario (e.g., 'rcp26', 'rcp45', 'rcp85') or 'historical'
        filter_to_thessaloniki: If True, filter to Thessaloniki coords (matches meteo grid)
        geojson: Optional GeoJSON polygon for spatial filtering (overrides filter_to_thessaloniki)

    Returns:
        xarray.Dataset with suitability scores over time (spatially filtered if geojson provided)

    Note:
        If geojson is provided, it takes precedence over filter_to_thessaloniki.
        Use geojson for user-drawn polygon filtering, or filter_to_thessaloniki for fixed bounds.
    """
    crop_upper = crop.upper()
    if scenario.lower() == 'historical':
        path = f"{data_path}/{crop_upper}/PAST_LUSA_PREDICTIONS.nc"
    else:
        scenario_upper = scenario.upper()
        path = f"{data_path}/{crop_upper}/{scenario_upper}_LUSA_PREDICTIONS.nc"

    ds = xr.open_dataset(path)

    # Priority 1: Apply GeoJSON filtering if provided (user-drawn polygon)
    if geojson is not None:
        logger.info(f"Applying GeoJSON spatial filter to {crop} suitability data...")
        return _apply_spatial_filter(ds, geojson)

    # Priority 2: Apply default Thessaloniki filtering (fixed bounds from config)
    if filter_to_thessaloniki and _CONFIG_AVAILABLE:
        try:
            config = load_config() if _global_config is None else _global_config
            # Use config helper to get correct lat slice
            lat_slice = config.get_lat_slice(for_lusa=True)  # LUSA has ascending lat
            lon_slice = config.get_lon_slice()

            ds = ds.sel(
                lat=slice(*lat_slice),
                lon=slice(*lon_slice)
            )
        except Exception:
            pass  # If filtering fails, return full dataset

    return ds
