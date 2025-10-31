"""
Configuration loader for MLU use case.

Loads configuration from config.yaml in the use_cases/mlu directory.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


class MLUConfig:
    """Configuration holder for MLU use case."""

    def __init__(self, config_path: str = None):
        """Load configuration from YAML file.

        Args:
            config_path: Path to config.yaml file. If None, uses default location.
        """
        if config_path is None:
            # Default: config.yaml in same directory as this file
            config_path = Path(__file__).parent / "config.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)

    @property
    def data_path(self) -> str:
        """Get base data path."""
        return self._config['data']['base_path']

    @property
    def data_subdirs(self) -> Dict[str, Any]:
        """Get data subdirectories configuration."""
        return self._config['data'].get('subdirs', {})

    @property
    def data_files(self) -> Dict[str, str]:
        """Get data filenames configuration."""
        return self._config['data'].get('files', {})

    @property
    def n_parcels(self) -> int:
        """Get number of land parcels."""
        return self._config['simulation']['n_parcels']

    @property
    def n_years(self) -> int:
        """Get simulation duration in years."""
        return self._config['simulation']['n_years']

    @property
    def scenarios(self) -> list:
        """Get list of RCP scenarios."""
        return self._config['simulation']['scenarios']

    @property
    def ensemble_size(self) -> int:
        """Get number of Monte Carlo ensemble runs."""
        return self._config['simulation'].get('ensemble_size', 30)

    @property
    def confidence_level(self) -> float:
        """Get confidence level for uncertainty bands."""
        return self._config['simulation'].get('confidence_level', 0.95)

    @property
    def crops(self) -> list:
        """Get list of crops to model."""
        return self._config['crops']

    @property
    def results_dir(self) -> str:
        """Get results directory."""
        return self._config['output']['results_dir']

    @property
    def region(self) -> Dict[str, Any]:
        """Get region configuration."""
        return self._config['region']

    @property
    def lat_min(self) -> float:
        """Get minimum latitude (Thessaloniki region)."""
        return self._config['region']['lat_min']

    @property
    def lat_max(self) -> float:
        """Get maximum latitude (Thessaloniki region)."""
        return self._config['region']['lat_max']

    @property
    def lon_min(self) -> float:
        """Get minimum longitude (Thessaloniki region)."""
        return self._config['region']['lon_min']

    @property
    def lon_max(self) -> float:
        """Get maximum longitude (Thessaloniki region)."""
        return self._config['region']['lon_max']

    @property
    def lat_descending(self) -> bool:
        """Check if latitude coordinates are in descending order (for meteorological files)."""
        return self._config['region'].get('lat_descending', True)

    def get_lat_slice(self, for_lusa: bool = False):
        """Get latitude slice tuple for xarray.sel().

        Args:
            for_lusa: If True, returns slice for LUSA files (ascending lat).
                     If False, returns slice for meteorological files (descending lat).

        Returns:
            tuple: (start, end) for slice(start, end)
        """
        if for_lusa:
            # LUSA files have ascending latitude
            return (self.lat_min, self.lat_max)
        else:
            # Meteorological files have descending latitude
            return (self.lat_max, self.lat_min) if self.lat_descending else (self.lat_min, self.lat_max)

    def get_lon_slice(self):
        """Get longitude slice tuple for xarray.sel().

        Returns:
            tuple: (start, end) for slice(start, end)
        """
        return (self.lon_min, self.lon_max)

    @property
    def solar_pv(self) -> Dict[str, Any]:
        """Get solar PV parameters."""
        return self._config['solar_pv']

    @property
    def agriculture(self) -> Dict[str, Any]:
        """Get agriculture parameters."""
        return self._config['agriculture']

    @property
    def multilevel(self) -> Dict[str, Any]:
        """Get multi-level ABM settings."""
        return self._config['multilevel']

    def get(self, key: str, default=None):
        """Get configuration value by key (dot notation supported).

        Examples:
            config.get('data.base_path')
            config.get('solar_pv.capacity_kw')
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value


# Convenience function
def load_config(config_path: str = None) -> MLUConfig:
    """Load MLU configuration.

    Args:
        config_path: Optional path to config file

    Returns:
        MLUConfig instance
    """
    return MLUConfig(config_path)


if __name__ == "__main__":
    # Test the config loader
    config = load_config()
    print(f"Data path: {config.data_path}")
    print(f"Parcels: {config.n_parcels}")
    print(f"Years: {config.n_years}")
    print(f"Scenarios: {config.scenarios}")
    print(f"Crops: {config.crops}")
    print(f"Solar PV capacity: {config.solar_pv['capacity_kw']} kW")
    print(f"Electricity price: €{config.solar_pv['electricity_price']}/kWh")
