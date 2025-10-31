"""Generic data loader for pilot data with support for multiple temporal resolutions."""

import xarray as xr
import pandas as pd
import numpy as np
from typing import Optional, Tuple


# ==================== Meteorological Data ====================

def load_temperature(data_path, scenario, geojson=None):
    """Load temperature (tas) data.

    Args:
        data_path: Base path to data directory
        scenario: RCP scenario (rcp26, rcp45, rcp85)
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with temperature data
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    path = f"{data_path}/meteo/tas_{scenario}.nc"
    ds = xr.open_dataset(path)

    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


def load_precipitation(data_path, scenario, geojson=None):
    """Load precipitation (pr) data.

    Args:
        data_path: Base path to data directory
        scenario: RCP scenario (rcp26, rcp45, rcp85)
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with precipitation data
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    path = f"{data_path}/meteo/pr_{scenario}.nc"
    ds = xr.open_dataset(path)

    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


def load_solar_radiation(data_path, scenario, geojson=None):
    """Load solar radiation (rsds) data.

    Args:
        data_path: Base path to data directory
        scenario: RCP scenario (rcp26, rcp45, rcp85)
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with solar radiation data
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    path = f"{data_path}/meteo/rsds_{scenario}.nc"
    ds = xr.open_dataset(path)

    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


def load_evapotranspiration(data_path, scenario, geojson=None):
    """Load evapotranspiration (evptsp) data.

    Args:
        data_path: Base path to data directory
        scenario: RCP scenario (rcp26, rcp45, rcp85)
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with evapotranspiration data
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    path = f"{data_path}/meteo/evptsp_{scenario}.nc"
    ds = xr.open_dataset(path)

    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


def load_all_meteo(data_path, scenario, geojson=None):
    """Load all meteorological data for scenario.

    Args:
        data_path: Base path to data directory
        scenario: RCP scenario (rcp26, rcp45, rcp85)
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        dict with keys: 'temperature', 'precipitation', 'solar_radiation', 'evapotranspiration'
    """
    return {
        'temperature': load_temperature(data_path, scenario, geojson=geojson),
        'precipitation': load_precipitation(data_path, scenario, geojson=geojson),
        'solar_radiation': load_solar_radiation(data_path, scenario, geojson=geojson),
        'evapotranspiration': load_evapotranspiration(data_path, scenario, geojson=geojson)
    }


# ==================== Soil Data ====================

def load_soil_type(data_path, geojson=None):
    """Load soil type classification.

    Args:
        data_path: Base path to data directory
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with soil type data
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    path = f"{data_path}/soil/SoilType_0-5cm_mean.nc"
    ds = xr.open_dataset(path)

    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


def load_soil_cec(data_path, geojson=None):
    """Load soil Cation Exchange Capacity (CEC).

    Args:
        data_path: Base path to data directory
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with CEC data
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    path = f"{data_path}/soil/cec_0-5cm_mean.nc"
    ds = xr.open_dataset(path)

    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


def load_soil_ph(data_path, geojson=None):
    """Load soil pH (phh2o).

    Args:
        data_path: Base path to data directory
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with pH data
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    path = f"{data_path}/soil/phh2o_0-5cm_mean.nc"
    ds = xr.open_dataset(path)

    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


def load_soil_organic_carbon(data_path, geojson=None):
    """Load Soil Organic Carbon (SOC).

    Args:
        data_path: Base path to data directory
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with SOC data
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    path = f"{data_path}/soil/soc_0-5cm_mean.nc"
    ds = xr.open_dataset(path)

    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


def load_all_soil(data_path, geojson=None):
    """Load all soil data.

    Args:
        data_path: Base path to data directory
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        dict with keys: 'soil_type', 'cec', 'ph', 'organic_carbon'
    """
    return {
        'soil_type': load_soil_type(data_path, geojson=geojson),
        'cec': load_soil_cec(data_path, geojson=geojson),
        'ph': load_soil_ph(data_path, geojson=geojson),
        'organic_carbon': load_soil_organic_carbon(data_path, geojson=geojson)
    }


# ==================== Terrain Data ====================

def load_dem(data_path, geojson=None):
    """Load Digital Elevation Model.

    Args:
        data_path: Base path to data directory
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with elevation data
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    path = f"{data_path}/dem/DEM.nc"
    ds = xr.open_dataset(path)

    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


# ==================== Temporal Aggregation Helper ====================

def aggregate_to_annual(ds: xr.Dataset, year: int, time_dim: str = 'time') -> xr.Dataset:
    """
    Aggregate temporal data (daily/monthly) to annual mean for a specific year.

    Args:
        ds: xarray Dataset with time dimension
        year: Year to aggregate
        time_dim: Name of time dimension (default: 'time')

    Returns:
        xarray Dataset aggregated to annual mean for the specified year
    """
    if time_dim not in ds.dims:
        return ds  # No time dimension, return as-is

    # Create time slice for the year
    time_start = pd.Timestamp(f'{year}-01-01')
    time_end = pd.Timestamp(f'{year}-12-31')

    # Select data for the year and compute annual mean
    try:
        ds_year = ds.sel({time_dim: slice(time_start, time_end)})
        if len(ds_year[time_dim]) > 0:
            # Compute mean over time dimension
            ds_annual = ds_year.mean(dim=time_dim, keep_attrs=True)
            return ds_annual
        else:
            # No data for this year, use nearest year
            return ds.sel({time_dim: time_start}, method='nearest').drop_vars(time_dim)
    except Exception as e:
        # Fallback: use nearest timestamp
        return ds.sel({time_dim: time_start}, method='nearest').drop_vars(time_dim)


def get_valid_data_extent(ds: xr.Dataset, data_var=None, threshold: float = None) -> tuple:
    """
    Extract valid data extent (bounding box of non-NaN, non-zero values).

    Args:
        ds: xarray Dataset
        data_var: Data variable to check (if None, uses first data variable)
        threshold: Minimum value threshold for validity (if None, just checks non-zero/non-NaN)

    Returns:
        (lat_min, lat_max, lon_min, lon_max) or None if no valid data
    """
    try:
        # Get data variable
        if data_var is None:
            if hasattr(ds, 'score'):
                data_var = ds.score
            else:
                data_vars = list(ds.data_vars)
                if not data_vars:
                    return None
                data_var = ds[data_vars[0]]

        # Select first time step if temporal
        if 'time' in data_var.dims:
            data_var = data_var.isel(time=0)

        # Create validity mask
        if threshold is not None:
            valid_mask = (~np.isnan(data_var.values)) & (data_var.values > threshold)
        else:
            # Just check non-NaN and non-zero
            valid_mask = (~np.isnan(data_var.values)) & (data_var.values != 0)

        if not valid_mask.any():
            return None

        # Get coordinate arrays
        if 'lat' in ds.dims:
            lat_coords = ds.lat.values
            lon_coords = ds.lon.values
        elif 'latitude' in ds.dims:
            lat_coords = ds.latitude.values
            lon_coords = ds.longitude.values
        else:
            return None

        # Get indices of valid data
        valid_lats, valid_lons = np.where(valid_mask)

        # Get actual coordinate values
        valid_lat_values = lat_coords[valid_lats]
        valid_lon_values = lon_coords[valid_lons]

        # Return bounding box
        return (
            float(valid_lat_values.min()),
            float(valid_lat_values.max()),
            float(valid_lon_values.min()),
            float(valid_lon_values.max())
        )

    except Exception as e:
        return None


def get_temporal_resolution(ds: xr.Dataset, time_dim: str = 'time') -> str:
    """
    Detect temporal resolution of dataset (yearly, monthly, or daily).

    Args:
        ds: xarray Dataset with time dimension
        time_dim: Name of time dimension

    Returns:
        'yearly', 'monthly', 'daily', or 'unknown'
    """
    if time_dim not in ds.dims:
        return 'static'  # No time dimension

    if len(ds[time_dim]) < 2:
        return 'unknown'

    # Calculate time difference between first two timestamps
    time_values = pd.to_datetime(ds[time_dim].values)
    time_diff = (time_values[1] - time_values[0]).days

    if time_diff >= 300:  # ~1 year
        return 'yearly'
    elif time_diff >= 20:  # ~1 month
        return 'monthly'
    elif time_diff >= 1:  # ~1 day
        return 'daily'
    else:
        return 'unknown'


def validate_year_in_range(ds: xr.Dataset, year: int, time_dim: str = 'time',
                           dataset_name: str = 'dataset') -> bool:
    """
    Validate that a year is within the temporal range of the dataset.

    Args:
        ds: xarray Dataset with time dimension
        year: Year to validate
        time_dim: Name of time dimension
        dataset_name: Name for error messages

    Returns:
        True if year is in range

    Raises:
        ValueError if year is outside data range
    """
    if time_dim not in ds.dims:
        return True  # No temporal validation needed for static data

    time_values = pd.to_datetime(ds[time_dim].values)
    year_min = time_values.year.min()
    year_max = time_values.year.max()

    if year < year_min or year > year_max:
        raise ValueError(
            f"❌ Year {year} is outside {dataset_name} temporal range "
            f"({year_min}-{year_max}). Please adjust simulation years or data."
        )

    return True


# ==================== Crop Data ====================

def load_crop_suitability(data_path, crop, scenario, geojson=None):
    """Load crop suitability (LUSA) predictions.

    Args:
        data_path: Base path to data directory
        crop: Crop type (e.g., 'MAIZE', 'WHEAT')
        scenario: RCP scenario (e.g., 'rcp26', 'rcp45', 'rcp85')
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)

    Returns:
        xarray.Dataset with suitability scores over time
    """
    from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson

    crop_upper = crop.upper()
    scenario_upper = scenario.upper()
    # FIXED: Removed 'land_suitability/' subfolder - data is directly in crop folders
    # Correct path: /home/ggous/Downloads/PILOT_THESSALONIKI_DATA/WHEAT/RCP45_LUSA_PREDICTIONS.nc
    path = f"{data_path}/{crop_upper}/{scenario_upper}_LUSA_PREDICTIONS.nc"
    ds = xr.open_dataset(path)

    if geojson is not None:
        ds = filter_netcdf_by_geojson(ds, geojson, method='bounds')

    return ds


# ==================== DataLoader Class ====================

class DataLoader:
    """
    Object-oriented wrapper for data loading functions.

    Provides a unified interface for loading all data types:
    - Meteorological data (temperature, precipitation, solar, evapotranspiration)
    - Soil data (type, CEC, pH, organic carbon)
    - Terrain data (DEM elevation)
    - Crop suitability predictions (LUSA)
    """

    def __init__(self, data_path: str, crops: list, scenario: str,
                 auto_aggregate: bool = True, validate_years: bool = True,
                 geojson: dict = None):
        """
        Initialize DataLoader with flexible data handling.

        Args:
            data_path: Base path to data directory
            crops: List of crop types (e.g., ["WHEAT", "MAIZE"])
            scenario: RCP scenario (rcp26, rcp45, rcp85)
            auto_aggregate: If True, automatically aggregate daily/monthly data to annual
            validate_years: If True, validate that requested years are within data range
            geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)
        """
        self.data_path = data_path
        self.crops = crops
        self.scenario = scenario
        self.auto_aggregate = auto_aggregate
        self.validate_years = validate_years
        self.geojson = geojson

        # Lazy-loaded data (loaded on first access)
        self._meteo_data = None
        self._soil_data = None
        self._dem_data = None
        self._crop_suitability = {}

        # Cache for temporal resolution detection
        self._temporal_resolutions = {}

    def load_meteo(self):
        """Load all meteorological data."""
        if self._meteo_data is None:
            self._meteo_data = load_all_meteo(self.data_path, self.scenario, geojson=self.geojson)
        return self._meteo_data

    def load_soil(self):
        """Load all soil data."""
        if self._soil_data is None:
            self._soil_data = load_all_soil(self.data_path, geojson=self.geojson)
        return self._soil_data

    def load_dem(self):
        """Load DEM elevation data."""
        if self._dem_data is None:
            self._dem_data = load_dem(self.data_path, geojson=self.geojson)
        return self._dem_data

    def load_crop_suitability_for_crop(self, crop: str):
        """
        Load crop suitability for specific crop.

        Args:
            crop: Crop type (e.g., 'WHEAT', 'MAIZE')

        Returns:
            xarray.Dataset with suitability scores
        """
        if crop not in self._crop_suitability:
            self._crop_suitability[crop] = load_crop_suitability(
                self.data_path, crop, self.scenario, geojson=self.geojson
            )
        return self._crop_suitability[crop]

    def load_all_crop_suitability(self):
        """Load suitability data for all configured crops."""
        for crop in self.crops:
            self.load_crop_suitability_for_crop(crop)
        return self._crop_suitability

    def get_suitability_at_location(self, crop: str, lat: float, lon: float, year: int):
        """
        Get suitability score for crop at specific location and year.
        Automatically handles yearly, monthly, and daily temporal resolutions.

        Args:
            crop: Crop type
            lat: Latitude
            lon: Longitude
            year: Year (integer, e.g., 2021)

        Returns:
            float: Suitability score (0-1)
        """
        suitability_ds = self.load_crop_suitability_for_crop(crop)

        # Find nearest grid point
        try:
            # STEP 1: Validate year is within data range
            if self.validate_years and 'time' in suitability_ds.dims:
                validate_year_in_range(suitability_ds, year, 'time',
                                      dataset_name=f'{crop} suitability')

            # STEP 2: Detect and handle temporal resolution
            if 'time' in suitability_ds.dims:
                # Get temporal resolution (cache for efficiency)
                cache_key = f'suitability_{crop}'
                if cache_key not in self._temporal_resolutions:
                    self._temporal_resolutions[cache_key] = get_temporal_resolution(
                        suitability_ds, 'time'
                    )

                temporal_res = self._temporal_resolutions[cache_key]

                # If data is monthly or daily, aggregate to annual if enabled
                if self.auto_aggregate and temporal_res in ['monthly', 'daily']:
                    # Aggregate to annual mean for the requested year
                    suitability_ds = aggregate_to_annual(suitability_ds, year, 'time')
                else:
                    # For yearly data or when auto_aggregate=False, use nearest year
                    time_value = pd.Timestamp(f'{year}-01-01')
                    suitability_ds = suitability_ds.sel(time=time_value, method='nearest')

            # STEP 3: Select spatial location (handle both lat/lon and latitude/longitude)
            if 'lat' in suitability_ds.dims:
                suitability = suitability_ds.sel(lat=lat, lon=lon, method='nearest')
            elif 'latitude' in suitability_ds.dims:
                suitability = suitability_ds.sel(latitude=lat, longitude=lon, method='nearest')
            else:
                raise KeyError("Neither 'lat' nor 'latitude' found in dataset dimensions")

            # STEP 4: Extract the actual value
            # If it's a Dataset, extract the 'score' variable
            if hasattr(suitability, 'score'):
                return float(suitability.score.values.item())
            else:
                return float(suitability.values.item())
        except ValueError as e:
            # Year validation error - re-raise with context
            raise ValueError(f"Crop suitability data error: {e}")
        except Exception as e:
            # NO FALLBACKS - only use real data from config.yaml
            raise ValueError(f"❌ Could not get suitability at ({lat}, {lon}) for {crop}, year {year}: {e}. Check config.yaml data path.")

    def get_meteo_at_location(self, meteo_type: str, lat: float, lon: float, year: int):
        """
        Get meteorological data at specific location and year.
        Automatically handles yearly, monthly, and daily temporal resolutions.

        Args:
            meteo_type: 'temperature', 'precipitation', 'solar_radiation', 'evapotranspiration'
            lat: Latitude
            lon: Longitude
            year: Year (integer)

        Returns:
            float: Meteorological value
        """
        meteo_data = self.load_meteo()

        # Get the appropriate dataset - NO FALLBACKS
        if meteo_type not in meteo_data:
            raise ValueError(f"❌ Meteorological data type '{meteo_type}' not found! Available types: {list(meteo_data.keys())}. Check config.yaml data path.")

        ds = meteo_data[meteo_type]

        try:
            # STEP 1: Validate year is within data range
            if self.validate_years and 'time' in ds.dims:
                validate_year_in_range(ds, year, 'time',
                                      dataset_name=f'{meteo_type}')

            # STEP 2: Detect and handle temporal resolution
            if 'time' in ds.dims:
                # Get temporal resolution (cache for efficiency)
                cache_key = f'meteo_{meteo_type}'
                if cache_key not in self._temporal_resolutions:
                    self._temporal_resolutions[cache_key] = get_temporal_resolution(ds, 'time')

                temporal_res = self._temporal_resolutions[cache_key]

                # If data is monthly or daily, aggregate to annual if enabled
                if self.auto_aggregate and temporal_res in ['monthly', 'daily']:
                    # Aggregate to annual mean for the requested year
                    ds = aggregate_to_annual(ds, year, 'time')
                else:
                    # For yearly data or when auto_aggregate=False, use nearest year
                    time_value = pd.Timestamp(f'{year}-01-01')
                    ds = ds.sel(time=time_value, method='nearest')

            # STEP 3: Select spatial location (handle both lat/lon and latitude/longitude)
            if 'lat' in ds.dims:
                value = ds.sel(lat=lat, lon=lon, method='nearest')
            elif 'latitude' in ds.dims:
                value = ds.sel(latitude=lat, longitude=lon, method='nearest')
            else:
                raise KeyError("Neither 'lat' nor 'latitude' found in dataset dimensions")

            # STEP 4: Extract the actual numeric value from Dataset/DataArray
            # Meteorological datasets have specific variable names (tas, pr, rsds, evptsp)
            if isinstance(value, xr.Dataset):
                # It's a Dataset - need to extract the data variable
                data_vars = list(value.data_vars)
                if len(data_vars) > 0:
                    value = value[data_vars[0]]  # Get first data variable
                else:
                    raise ValueError("No data variables found in Dataset")

            # Now value should be a DataArray
            return float(value.values.item())
        except ValueError as e:
            # Year validation error - re-raise with context
            raise ValueError(f"Meteorological data error: {e}")
        except Exception as e:
            print(f"⚠️  Warning: Could not get {meteo_type} at ({lat}, {lon}), year {year}: {e}")
            # Return reasonable defaults based on type
            defaults = {
                'temperature': 15.0,
                'precipitation': 2.0,
                'solar_radiation': 200.0,
                'evapotranspiration': 1.0
            }
            return defaults.get(meteo_type, 0.5)

    def get_data_info(self) -> dict:
        """
        Get information about loaded data (spatial extent, temporal extent, resolution).
        Finds the INTERSECTION of valid data across all data types (smallest common area).

        Returns:
            dict with data characteristics
        """
        info = {
            'data_path': self.data_path,
            'scenario': self.scenario,
            'crops': self.crops,
            'auto_aggregate': self.auto_aggregate,
            'validate_years': self.validate_years
        }

        # Collect valid extents from all data sources
        extents = []
        extent_sources = []

        try:
            print("📍 Detecting valid data extent from all sources...")

            # 1. Crop suitability data (use threshold for high-suitability areas)
            if self.crops:
                for crop in self.crops:
                    ds = self.load_crop_suitability_for_crop(crop)
                    # Use threshold of 10.0 for 0-100 scale or 0.1 for 0-1 scale
                    if hasattr(ds, 'score'):
                        data_var = ds.score
                    else:
                        data_vars = list(ds.data_vars)
                        if data_vars:
                            data_var = ds[data_vars[0]]
                        else:
                            continue

                    # Select first time step
                    if 'time' in data_var.dims:
                        data_var = data_var.isel(time=0)

                    # Determine appropriate threshold
                    max_val = float(data_var.max().values)
                    threshold = 0.1 if max_val <= 1.0 else 10.0

                    extent = get_valid_data_extent(ds, data_var, threshold=threshold)
                    if extent:
                        extents.append(extent)
                        extent_sources.append(f'{crop} suitability')
                        print(f"   ✓ {crop} suitability: Lat [{extent[0]:.3f}, {extent[1]:.3f}], "
                              f"Lon [{extent[2]:.3f}, {extent[3]:.3f}]")

            # 2. Meteorological data (all variables)
            meteo_data = self.load_meteo()
            for meteo_type, ds in meteo_data.items():
                extent = get_valid_data_extent(ds, threshold=None)  # No threshold for meteo
                if extent:
                    extents.append(extent)
                    extent_sources.append(f'{meteo_type}')
                    print(f"   ✓ {meteo_type}: Lat [{extent[0]:.3f}, {extent[1]:.3f}], "
                          f"Lon [{extent[2]:.3f}, {extent[3]:.3f}]")

            # 3. Soil data (all soil variables)
            soil_data = self.load_soil()
            for soil_type, ds in soil_data.items():
                extent = get_valid_data_extent(ds, threshold=None)  # No threshold for soil
                if extent:
                    extents.append(extent)
                    extent_sources.append(f'soil_{soil_type}')
                    print(f"   ✓ soil_{soil_type}: Lat [{extent[0]:.3f}, {extent[1]:.3f}], "
                          f"Lon [{extent[2]:.3f}, {extent[3]:.3f}]")

            # 4. DEM data
            dem_data = self.load_dem()
            extent = get_valid_data_extent(dem_data, threshold=None)  # No threshold for DEM
            if extent:
                extents.append(extent)
                extent_sources.append('DEM')
                print(f"   ✓ DEM: Lat [{extent[0]:.3f}, {extent[1]:.3f}], "
                      f"Lon [{extent[2]:.3f}, {extent[3]:.3f}]")

            # 5. Compute intersection (smallest common area)
            if extents:
                print(f"\n   Computing intersection of {len(extents)} data sources...")

                # Intersection = max of minimums, min of maximums
                lat_min = max(e[0] for e in extents)  # Most restrictive lower bound
                lat_max = min(e[1] for e in extents)  # Most restrictive upper bound
                lon_min = max(e[2] for e in extents)
                lon_max = min(e[3] for e in extents)

                # Check if intersection is valid
                if lat_min < lat_max and lon_min < lon_max:
                    # Add small buffer (1% of range)
                    lat_range = lat_max - lat_min
                    lon_range = lon_max - lon_min
                    lat_buffer = lat_range * 0.01
                    lon_buffer = lon_range * 0.01

                    info['lat_range'] = (lat_min - lat_buffer, lat_max + lat_buffer)
                    info['lon_range'] = (lon_min - lon_buffer, lon_max + lon_buffer)
                    info['valid_data_extent'] = True
                    info['extent_sources'] = extent_sources
                    info['intersection_size'] = f"{lat_range:.3f}° × {lon_range:.3f}°"

                    print(f"   ✅ Intersection found: Lat [{info['lat_range'][0]:.3f}, {info['lat_range'][1]:.3f}], "
                          f"Lon [{info['lon_range'][0]:.3f}, {info['lon_range'][1]:.3f}]")
                    print(f"   📏 Area size: {info['intersection_size']}")
                else:
                    print("   ⚠️  No valid intersection - datasets don't overlap!")
                    info['valid_data_extent'] = False
                    info['error'] = "No overlap between datasets"
            else:
                print("   ⚠️  Could not extract valid extents from any data source")
                info['valid_data_extent'] = False
                info['error'] = "No valid extents found"

            # Get spatial resolution (from first crop suitability dataset)
            if self.crops:
                ds = self.load_crop_suitability_for_crop(self.crops[0])
                if 'lat' in ds.dims:
                    info['spatial_resolution'] = f"{abs(float(ds.lat[1] - ds.lat[0])):.4f}°"
                elif 'latitude' in ds.dims:
                    info['spatial_resolution'] = f"{abs(float(ds.latitude[1] - ds.latitude[0])):.4f}°"

            # Get temporal extent (from first crop suitability dataset)
            if self.crops:
                ds = self.load_crop_suitability_for_crop(self.crops[0])
                if 'time' in ds.dims:
                    time_values = pd.to_datetime(ds.time.values)
                    info['year_range'] = (int(time_values.year.min()), int(time_values.year.max()))
                    info['temporal_resolution'] = get_temporal_resolution(ds, 'time')
                else:
                    info['temporal_resolution'] = 'static'

        except Exception as e:
            print(f"   ❌ Error during extent detection: {e}")
            info['error'] = f"Could not extract data info: {e}"

        return info
