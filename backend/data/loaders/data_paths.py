"""
Data path builder using configuration.

Centralizes all data file path construction to use config.yaml instead of hardcoded paths.
"""

from pathlib import Path
from typing import Optional


class DataPathBuilder:
    """Build data file paths from configuration."""

    def __init__(self, base_path: str, subdirs: dict, files: dict):
        """
        Initialize path builder.

        Args:
            base_path: Base data directory path
            subdirs: Dictionary of subdirectory names from config
            files: Dictionary of file patterns from config
        """
        self.base_path = Path(base_path)
        self.subdirs = subdirs
        self.files = files

    def get_meteo_file(self, variable: str, scenario: str) -> Path:
        """
        Get meteorological data file path.

        Args:
            variable: Meteo variable (temperature, precipitation, solar_radiation, evapotranspiration)
            scenario: Scenario name (rcp26, rcp45, rcp85, historical)

        Returns:
            Path to NetCDF file
        """
        if scenario.lower() == 'historical':
            # Historical data: ERA5_LAND_* files in Historical/ folder
            filename = self.files.get(f'historical_{variable}')
            return self.base_path / self.subdirs['historical'] / filename
        else:
            # Future data: {variable}_{scenario}.nc in meteo/ folder
            filename_template = self.files.get(variable)
            filename = filename_template.replace('{scenario}', scenario.lower())
            return self.base_path / self.subdirs['meteo'] / filename

    def get_crop_suitability_file(self, crop: str, scenario: str) -> Path:
        """
        Get crop suitability (LUSA) file path.

        Args:
            crop: Crop name (WHEAT, MAIZE)
            scenario: Scenario name (rcp26, rcp45, rcp85, historical)

        Returns:
            Path to NetCDF file
        """
        crop_upper = crop.upper()
        crop_folder = self.subdirs['crops'].get(crop.lower(), crop_upper)

        if scenario.lower() == 'historical':
            # Historical: PAST_LUSA_PREDICTIONS.nc
            filename = self.files['lusa_historical']
        else:
            # Future: LUSA_PREDICTIONS_{SCENARIO}.nc
            scenario_upper = scenario.upper()
            filename = self.files['lusa_predictions'].replace('{scenario}', scenario_upper)

        return self.base_path / crop_folder / filename

    def get_yield_file(self, scenario: str) -> Path:
        """
        Get yield data (AquaCrop) file path.

        Args:
            scenario: Scenario name (rcp26, rcp45, rcp85, historical)

        Returns:
            Path to CSV file
        """
        if scenario.lower() == 'historical':
            # Historical: Historical/AquaCrop_Results_PAST.csv
            filename = self.files['yield_historical']
            return self.base_path / self.subdirs['historical'] / filename
        else:
            # Future: yield/AquaCrop_Results_{SCENARIO}_PILOT_THESSALONIKI.csv
            filename_key = f'yield_{scenario.lower()}'
            filename = self.files[filename_key]
            return self.base_path / self.subdirs['yield'] / filename

    def get_soil_file(self, variable: str) -> Path:
        """
        Get soil data file path.

        Args:
            variable: Soil variable (soil_type, cec, ph, organic_carbon)

        Returns:
            Path to NetCDF file
        """
        filename_key = f'soil_{variable}' if not variable.startswith('soil_') else variable
        filename = self.files[filename_key]
        return self.base_path / self.subdirs['soil'] / filename

    def get_dem_file(self) -> Path:
        """Get DEM (elevation) file path."""
        filename = self.files['dem']
        return self.base_path / self.subdirs['dem'] / filename
