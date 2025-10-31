"""
GCP Data Loader
===============

Loads socioeconomic, financial, geospatial, and environmental data for the
Green Credit Policy (GCP) use case.

Data Sources:
- EUROSTAT: Socioeconomic indicators (TSV format)
- ECB: Balance Sheet Items (CSV format)
- FADN: Farm Accountancy Data (CSV format)
- ENSPRESO: Solar and biomass potential (Excel format)
- Shapefiles: NUTS and LAU boundaries
- Environmental: DEM, meteorological, soil data (NetCDF)

This loader is designed to be flexible to handle different:
- Spatial extents
- Spatial resolutions
- Temporal extents
- Temporal aggregations (daily, monthly, yearly)
"""

import os
import pandas as pd
import geopandas as gpd
import xarray as xr
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


class GCPDataLoader:
    """
    Data loader for GCP use case.

    Handles multiple data formats and ensures spatial/temporal flexibility.
    """

    def __init__(self, config_path: str = None, geojson: dict = None):
        """
        Initialize the data loader.

        Parameters
        ----------
        config_path : str, optional
            Path to config.yaml. If None, uses default path.
        geojson : dict, optional
            GeoJSON dict/string for polygon-based spatial filtering
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.base_path = Path(self.config['data']['base_path'])
        self.subdirs = self.config['data']['subdirs']
        self.files = self.config['data']['files']
        self.region = self.config['region']
        self.geojson = geojson

        logger.info(f"Initialized GCPDataLoader with base_path: {self.base_path}")

    # ===== EUROSTAT Data Loaders =====

    def load_eurostat_tsv(self, filename: str, region_filter: Optional[str] = None) -> pd.DataFrame:
        """
        Load EUROSTAT TSV file.

        EUROSTAT TSV format:
        - First column: metadata (freq,unit,direct,na_item,geo)
        - Remaining columns: years (2014, 2015, ...)
        - Tab-separated values

        Parameters
        ----------
        filename : str
            Name of the EUROSTAT TSV file
        region_filter : str, optional
            NUTS code to filter (e.g., 'EL52' for Thessaloniki NUTS2)

        Returns
        -------
        pd.DataFrame
            Loaded and parsed EUROSTAT data
        """
        filepath = self.base_path / filename

        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return pd.DataFrame()

        try:
            # Read TSV file
            df = pd.read_csv(filepath, sep='\t', encoding='utf-8')

            # First column contains metadata and geo code
            # Format: freq,unit,direct,na_item,geo
            first_col = df.columns[0]

            # Split the first column into metadata fields
            metadata_parts = first_col.split(',')

            # Parse each row
            rows = []
            for idx, row in df.iterrows():
                # Get metadata from first column value
                first_val = str(row.iloc[0])
                parts = first_val.split(',')

                # Extract geo code (last part)
                if len(parts) >= 5:
                    geo_code = parts[4]

                    # Filter by region if specified
                    if region_filter and not geo_code.startswith(region_filter):
                        continue

                    # Extract year values
                    for col in df.columns[1:]:
                        year = col.strip()
                        value = row[col]

                        # Skip empty/invalid values
                        if pd.notna(value) and value not in [':', ' ']:
                            try:
                                value_float = float(str(value).strip().replace(',', ''))
                                rows.append({
                                    'geo': geo_code,
                                    'year': int(year),
                                    'value': value_float,
                                    'metadata': first_val
                                })
                            except (ValueError, TypeError):
                                continue

            result_df = pd.DataFrame(rows)
            logger.info(f"Loaded {len(result_df)} records from {filename}")
            return result_df

        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return pd.DataFrame()

    def load_household_income(self, region_filter: Optional[str] = None) -> pd.DataFrame:
        """Load household income by NUTS 2 regions."""
        return self.load_eurostat_tsv(
            self.files['household_income'],
            region_filter=region_filter
        )

    def load_gdp(self, region_filter: Optional[str] = None) -> pd.DataFrame:
        """Load GDP at NUTS 3 regions."""
        return self.load_eurostat_tsv(
            self.files['gdp'],
            region_filter=region_filter
        )

    def load_population_density(self, region_filter: Optional[str] = None) -> pd.DataFrame:
        """Load population density by NUTS 3 region."""
        return self.load_eurostat_tsv(
            self.files['population_density'],
            region_filter=region_filter
        )

    def load_employment(self, region_filter: Optional[str] = None) -> pd.DataFrame:
        """Load agricultural employment by NUTS 2 regions."""
        return self.load_eurostat_tsv(
            self.files['employment'],
            region_filter=region_filter
        )

    def load_electricity_prices(self) -> pd.DataFrame:
        """Load electricity prices for non-household consumers."""
        return self.load_eurostat_tsv(self.files['electricity_prices'])

    def load_farm_indicators(self, region_filter: Optional[str] = None) -> pd.DataFrame:
        """Load farm indicators by agricultural area."""
        return self.load_eurostat_tsv(
            self.files['farm_indicators'],
            region_filter=region_filter
        )

    def load_interest_rates(self) -> pd.DataFrame:
        """Load MFI interest rates (monthly)."""
        return self.load_eurostat_tsv(self.files['interest_rates'])

    # ===== FADN Data Loader =====

    def load_fadn(self) -> pd.DataFrame:
        """
        Load EU Farm Accountancy Data Network (FADN).

        Returns
        -------
        pd.DataFrame
            Farm-level economic data
        """
        filepath = self.base_path / self.files['fadn']

        if not filepath.exists():
            logger.warning(f"FADN file not found: {filepath}")
            return pd.DataFrame()

        try:
            # Try UTF-8 first, fall back to latin-1 if UTF-8 fails
            try:
                df = pd.read_csv(filepath, sep=';', encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, sep=';', encoding='latin-1')
            logger.info(f"Loaded FADN data: {len(df)} years")
            return df
        except Exception as e:
            logger.error(f"Error loading FADN: {e}")
            return pd.DataFrame()

    # ===== ECB Data Loader =====

    def load_ecb_balance_sheet(self, nrows: Optional[int] = None) -> pd.DataFrame:
        """
        Load ECB Balance Sheet Items.

        Note: This file is very large (4GB), so we provide an option to load
        only a subset of rows for testing/development.

        Parameters
        ----------
        nrows : int, optional
            Number of rows to load. If None, loads entire file.

        Returns
        -------
        pd.DataFrame
            ECB Balance Sheet data
        """
        filepath = self.base_path / self.files['balance_sheet']

        if not filepath.exists():
            logger.warning(f"ECB Balance Sheet file not found: {filepath}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(filepath, nrows=nrows, encoding='utf-8', low_memory=False)
            logger.info(f"Loaded ECB Balance Sheet: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error loading ECB Balance Sheet: {e}")
            return pd.DataFrame()

    # ===== Geospatial Data Loaders =====

    def load_nuts_boundaries(self, nuts_level: int = 2) -> gpd.GeoDataFrame:
        """
        Load NUTS boundaries shapefile.

        Parameters
        ----------
        nuts_level : int
            NUTS level (0, 1, 2, or 3)

        Returns
        -------
        gpd.GeoDataFrame
            NUTS boundaries
        """
        filepath = self.base_path / self.files['nuts_shapefile']

        if not filepath.exists():
            logger.warning(f"NUTS shapefile not found: {filepath}")
            return gpd.GeoDataFrame()

        try:
            gdf = gpd.read_file(filepath)
            # Filter by NUTS level
            gdf = gdf[gdf['LEVL_CODE'] == nuts_level]
            logger.info(f"Loaded NUTS{nuts_level} boundaries: {len(gdf)} regions")
            return gdf
        except Exception as e:
            logger.error(f"Error loading NUTS boundaries: {e}")
            return gpd.GeoDataFrame()

    def load_lau_boundaries(self) -> gpd.GeoDataFrame:
        """
        Load LAU (Local Administrative Units) boundaries.

        Returns
        -------
        gpd.GeoDataFrame
            LAU boundaries
        """
        filepath = self.base_path / self.files['lau_shapefile']

        if not filepath.exists():
            logger.warning(f"LAU shapefile not found: {filepath}")
            return gpd.GeoDataFrame()

        try:
            gdf = gpd.read_file(filepath)
            logger.info(f"Loaded LAU boundaries: {len(gdf)} units")
            return gdf
        except Exception as e:
            logger.error(f"Error loading LAU boundaries: {e}")
            return gpd.GeoDataFrame()

    # ===== Environmental Data Loaders =====
    # These methods handle flexible spatial/temporal extents

    def load_netcdf_data(
        self,
        filename: str,
        variable: Optional[str] = None,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None
    ) -> xr.Dataset:
        """
        Load NetCDF file with flexible spatial/temporal slicing.

        This method automatically detects:
        - Coordinate names (lat/latitude/y, lon/longitude/x)
        - Coordinate order (ascending/descending)
        - Temporal dimension names (time/t)

        Parameters
        ----------
        filename : str
            NetCDF filename
        variable : str, optional
            Specific variable to load
        lat_min, lat_max : float, optional
            Latitude bounds
        lon_min, lon_max : float, optional
            Longitude bounds
        time_min, time_max : str, optional
            Time bounds (ISO format)

        Returns
        -------
        xr.Dataset
            Loaded NetCDF data
        """
        try:
            # Open dataset
            ds = xr.open_dataset(filename)

            # Detect coordinate names
            lat_coord = None
            lon_coord = None
            time_coord = None

            for coord in ds.coords:
                coord_lower = coord.lower()
                if coord_lower in ['lat', 'latitude', 'y']:
                    lat_coord = coord
                elif coord_lower in ['lon', 'longitude', 'x']:
                    lon_coord = coord
                elif coord_lower in ['time', 't']:
                    time_coord = coord

            # Apply spatial slicing if coordinates found
            if lat_coord and lat_min is not None and lat_max is not None:
                # Check if latitude is descending
                lat_values = ds[lat_coord].values
                is_descending = lat_values[0] > lat_values[-1]

                if is_descending:
                    ds = ds.sel({lat_coord: slice(lat_max, lat_min)})
                else:
                    ds = ds.sel({lat_coord: slice(lat_min, lat_max)})

            if lon_coord and lon_min is not None and lon_max is not None:
                ds = ds.sel({lon_coord: slice(lon_min, lon_max)})

            # Apply temporal slicing if time coordinate found
            if time_coord and time_min is not None:
                ds = ds.sel({time_coord: slice(time_min, time_max)})

            # Select specific variable if requested
            if variable and variable in ds.data_vars:
                ds = ds[[variable]]

            # Apply geojson spatial filtering if provided
            if self.geojson is not None:
                from backend.data.loaders.spatial_filter import filter_netcdf_by_geojson
                ds = filter_netcdf_by_geojson(ds, self.geojson, method='bounds')

            logger.info(f"Loaded NetCDF: {filename}")
            return ds

        except Exception as e:
            logger.error(f"Error loading NetCDF {filename}: {e}")
            return xr.Dataset()

    def load_meteorological_data(
        self,
        scenario: str,
        variable: str = 'temperature',
        **kwargs
    ) -> xr.Dataset:
        """
        Load meteorological data for a given scenario and variable.

        Parameters
        ----------
        scenario : str
            Climate scenario (rcp26, rcp45, rcp85)
        variable : str
            Meteorological variable (temperature, precipitation, solar_radiation)
        **kwargs
            Additional arguments passed to load_netcdf_data
            (lat_min, lat_max, lon_min, lon_max, time_min, time_max)

        Returns
        -------
        xr.Dataset
            Meteorological data
        """
        # Get filename pattern
        if variable == 'temperature':
            filename_pattern = self.files['temperature']
        elif variable == 'precipitation':
            filename_pattern = self.files['precipitation']
        elif variable == 'solar_radiation':
            filename_pattern = self.files['solar_radiation']
        else:
            raise ValueError(f"Unknown variable: {variable}")

        # Substitute scenario
        filename = filename_pattern.format(scenario=scenario)
        filepath = self.base_path / self.subdirs['meteo'] / filename

        # Use region bounds if not specified
        if 'lat_min' not in kwargs:
            kwargs['lat_min'] = self.region['lat_min']
            kwargs['lat_max'] = self.region['lat_max']
            kwargs['lon_min'] = self.region['lon_min']
            kwargs['lon_max'] = self.region['lon_max']

        return self.load_netcdf_data(filepath, **kwargs)

    def load_soil_data(
        self,
        soil_property: str = 'type',
        **kwargs
    ) -> xr.Dataset:
        """
        Load soil data.

        Parameters
        ----------
        soil_property : str
            Soil property (type, cec, ph)
        **kwargs
            Additional arguments for spatial slicing

        Returns
        -------
        xr.Dataset
            Soil data
        """
        filename_map = {
            'type': self.files['soil_type'],
            'cec': self.files['soil_cec'],
            'ph': self.files['soil_ph']
        }

        if soil_property not in filename_map:
            raise ValueError(f"Unknown soil property: {soil_property}")

        filename = filename_map[soil_property]
        filepath = self.base_path / self.subdirs['soil'] / filename

        # Use region bounds if not specified
        if 'lat_min' not in kwargs:
            kwargs['lat_min'] = self.region['lat_min']
            kwargs['lat_max'] = self.region['lat_max']
            kwargs['lon_min'] = self.region['lon_min']
            kwargs['lon_max'] = self.region['lon_max']

        return self.load_netcdf_data(filepath, **kwargs)

    def load_dem_data(self, **kwargs) -> xr.Dataset:
        """
        Load Digital Elevation Model (DEM) data.

        Parameters
        ----------
        **kwargs
            Additional arguments for spatial slicing

        Returns
        -------
        xr.Dataset
            DEM data
        """
        filepath = self.base_path / self.subdirs['dem'] / self.files['dem']

        # Use region bounds if not specified
        if 'lat_min' not in kwargs:
            kwargs['lat_min'] = self.region['lat_min']
            kwargs['lat_max'] = self.region['lat_max']
            kwargs['lon_min'] = self.region['lon_min']
            kwargs['lon_max'] = self.region['lon_max']

        return self.load_netcdf_data(filepath, **kwargs)

    # ===== Solar Potential Data =====

    def load_solar_potential(self, region_filter: Optional[str] = None) -> pd.DataFrame:
        """
        Load ENSPRESO solar potential data.

        Parameters
        ----------
        region_filter : str, optional
            NUTS code to filter

        Returns
        -------
        pd.DataFrame
            Solar potential data
        """
        filepath = self.base_path / self.files['solar_potential']

        if not filepath.exists():
            logger.warning(f"Solar potential file not found: {filepath}")
            return pd.DataFrame()

        try:
            # Read Excel file
            df = pd.read_excel(filepath, engine='openpyxl')

            # Filter by region if specified
            if region_filter and 'NUTS' in df.columns:
                df = df[df['NUTS'].str.startswith(region_filter)]

            logger.info(f"Loaded solar potential data: {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"Error loading solar potential: {e}")
            return pd.DataFrame()

    # ===== Convenience Methods =====

    def get_region_socioeconomic_data(
        self,
        nuts_code: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Load all socioeconomic data for a region.

        Parameters
        ----------
        nuts_code : str, optional
            NUTS code (e.g., 'EL52'). If None, uses config default.

        Returns
        -------
        dict
            Dictionary of DataFrames with socioeconomic indicators
        """
        if nuts_code is None:
            nuts_code = self.region.get('nuts2_code', 'EL52')

        return {
            'household_income': self.load_household_income(nuts_code),
            'gdp': self.load_gdp(nuts_code),
            'population_density': self.load_population_density(nuts_code),
            'employment': self.load_employment(nuts_code),
            'farm_indicators': self.load_farm_indicators(nuts_code),
            'fadn': self.load_fadn()
        }

    def get_financial_data(self) -> Dict[str, pd.DataFrame]:
        """
        Load all financial data.

        Returns
        -------
        dict
            Dictionary of DataFrames with financial indicators
        """
        return {
            'interest_rates': self.load_interest_rates(),
            'electricity_prices': self.load_electricity_prices()
        }


# Convenience function
def load_gcp_data(config_path: Optional[str] = None) -> GCPDataLoader:
    """
    Create and return a GCPDataLoader instance.

    Parameters
    ----------
    config_path : str, optional
        Path to config.yaml

    Returns
    -------
    GCPDataLoader
        Configured data loader
    """
    return GCPDataLoader(config_path=config_path)
