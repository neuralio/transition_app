"""
Yield Data Loader - Real AquaCrop simulation results

Loads Y(fresh) values from AquaCrop CSV files for different RCP scenarios.
Data source: /home/ggous/Downloads/PILOT_THESSALONIKI_DATA/yield/

File format: AquaCrop_Results_RCP{26|45|85}_PILOT_THESSALONIKI.csv
Target column: Y(fresh) (column 42) - Fresh yield in tons/hectare

⚠️ IMPORTANT: This is REAL Earth Observation data (NO dummy/mock data)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional


class YieldDataLoader:
    """Loads and manages real crop yield data from AquaCrop simulations."""

    def __init__(self, data_path: str):
        """
        Initialize yield data loader.

        Args:
            data_path: Path to PILOT_THESSALONIKI_DATA directory
        """
        self.data_path = Path(data_path)
        self.yield_path = self.data_path / "yield"

        # Cache for loaded yield data
        self._cache: Dict[str, pd.DataFrame] = {}

        # Scenario mapping
        self.scenario_files = {
            "rcp26": "AquaCrop_Results_RCP26_PILOT_THESSALONIKI.csv",
            "rcp45": "AquaCrop_Results_RCP45_PILOT_THESSALONIKI.csv",
            "rcp85": "AquaCrop_Results_RCP85_PILOT_THESSALONIKI.csv",
            "historical": "AquaCrop_Results_PAST.csv",  # Real historical yield data (1990-2020)
        }

    def load_scenario_yields(self, scenario: str) -> pd.DataFrame:
        """
        Load yield data for a specific RCP scenario.

        Args:
            scenario: RCP scenario (rcp26, rcp45, rcp85)

        Returns:
            DataFrame with columns: Year, Month, Day, Y_fresh, Biomass, Rain, Irri
        """
        scenario = scenario.lower()

        # Check cache
        if scenario in self._cache:
            return self._cache[scenario]

        # Validate scenario
        if scenario not in self.scenario_files:
            raise ValueError(f"Unknown scenario: {scenario}. Must be one of {list(self.scenario_files.keys())}")

        # Load CSV - historical is in different folder
        if scenario == "historical":
            csv_path = self.data_path / "Historical" / self.scenario_files[scenario]
        else:
            csv_path = self.yield_path / self.scenario_files[scenario]

        if not csv_path.exists():
            raise FileNotFoundError(f"Yield data not found: {csv_path}")

        print(f"Loading yield data for {scenario.upper()}...")

        # Read CSV (skip first row which is empty, use second row as header)
        df = pd.read_csv(csv_path, skiprows=0)

        # Extract relevant columns
        # Y(fresh): Fresh yield (tons/hectare)
        # Biomass: Total biomass (tons/hectare)
        # Rain: Rainfall (mm)
        # Irri: Irrigation (mm)
        yield_data = df[['Year', 'Month', 'Day', 'Y(fresh)', 'Biomass', 'Rain', 'Irri']].copy()

        # Rename for convenience
        yield_data.columns = ['year', 'month', 'day', 'yield_fresh', 'biomass', 'rainfall', 'irrigation']

        # Convert to numeric (handle any string values)
        for col in ['yield_fresh', 'biomass', 'rainfall', 'irrigation']:
            yield_data[col] = pd.to_numeric(yield_data[col], errors='coerce')

        # Remove rows with NaN yields
        yield_data = yield_data.dropna(subset=['yield_fresh'])

        # Cache it
        self._cache[scenario] = yield_data

        print(f"  Loaded {len(yield_data)} daily records from {yield_data['year'].min()} to {yield_data['year'].max()}")
        print(f"  Yield range: {yield_data['yield_fresh'].min():.2f} - {yield_data['yield_fresh'].max():.2f} tons/ha")

        return yield_data

    def get_annual_yield(self, scenario: str, year: int, crop: str = "wheat") -> float:
        """
        Get annual average yield for a specific year and scenario.

        Args:
            scenario: RCP scenario (rcp26, rcp45, rcp85)
            year: Year to query
            crop: Crop type (currently all yield data is for wheat/generic crop)

        Returns:
            Annual yield in tons/hectare
        """
        df = self.load_scenario_yields(scenario)

        # Filter by year
        year_data = df[df['year'] == year]

        if len(year_data) == 0:
            # Year not in data - use nearest year or interpolate
            available_years = sorted(df['year'].unique())
            if year < available_years[0]:
                # Use first available year
                year_data = df[df['year'] == available_years[0]]
                # Suppress warning for historical scenario (expected to use proxy data)
                if scenario.lower() != "historical":
                    print(f"  Warning: Year {year} before data range, using {available_years[0]}")
            elif year > available_years[-1]:
                # Use last available year (silently, this is expected at simulation end)
                year_data = df[df['year'] == available_years[-1]]
                # Note: Warning suppressed - normal to use last year at simulation end
            else:
                # Interpolate between nearest years
                lower_year = max(y for y in available_years if y < year)
                upper_year = min(y for y in available_years if y > year)
                lower_yield = df[df['year'] == lower_year]['yield_fresh'].max()
                upper_yield = df[df['year'] == upper_year]['yield_fresh'].max()

                # Linear interpolation
                t = (year - lower_year) / (upper_year - lower_year)
                interpolated_yield = lower_yield + t * (upper_yield - lower_yield)
                return interpolated_yield

        # Get maximum yield in that year (peak harvest)
        annual_yield = year_data['yield_fresh'].max()

        return annual_yield

    def get_yield_statistics(self, scenario: str) -> Dict[str, float]:
        """
        Get statistical summary of yields for a scenario.

        Args:
            scenario: RCP scenario

        Returns:
            Dictionary with mean, std, min, max, q25, q75
        """
        df = self.load_scenario_yields(scenario)

        # Filter to only non-zero yields (harvest periods)
        harvest_yields = df[df['yield_fresh'] > 0]['yield_fresh']

        return {
            'mean': harvest_yields.mean(),
            'std': harvest_yields.std(),
            'min': harvest_yields.min(),
            'max': harvest_yields.max(),
            'q25': harvest_yields.quantile(0.25),
            'q75': harvest_yields.quantile(0.75),
        }

    def compare_scenarios(self, year: int, crop: str = "wheat") -> Dict[str, float]:
        """
        Compare yields across all scenarios for a given year.

        Args:
            year: Year to compare
            crop: Crop type

        Returns:
            Dictionary mapping scenario -> yield
        """
        results = {}
        for scenario in self.scenario_files.keys():
            results[scenario] = self.get_annual_yield(scenario, year, crop)
        return results


def load_yield_data(data_path: str, scenario: str, crop: str = "wheat") -> YieldDataLoader:
    """
    Convenience function to load yield data.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        scenario: RCP scenario
        crop: Crop type

    Returns:
        YieldDataLoader instance
    """
    loader = YieldDataLoader(data_path)
    # Preload the scenario
    loader.load_scenario_yields(scenario)
    return loader


if __name__ == "__main__":
    # Test the loader
    data_path = "/app/data"

    print("=" * 60)
    print("YIELD DATA LOADER TEST")
    print("=" * 60)

    loader = YieldDataLoader(data_path)

    # Test RCP85
    print("\n1. Loading RCP85 scenario...")
    df = loader.load_scenario_yields("rcp85")
    print(f"   Shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")

    # Test annual yield
    print("\n2. Testing annual yield queries...")
    for year in [2021, 2025, 2030]:
        yield_val = loader.get_annual_yield("rcp85", year)
        print(f"   {year}: {yield_val:.2f} tons/ha")

    # Test statistics
    print("\n3. Yield statistics for RCP85...")
    stats = loader.get_yield_statistics("rcp85")
    for key, val in stats.items():
        print(f"   {key}: {val:.2f} tons/ha")

    # Test scenario comparison
    print("\n4. Comparing scenarios for 2025...")
    comparison = loader.compare_scenarios(2025)
    for scenario, yield_val in comparison.items():
        print(f"   {scenario.upper()}: {yield_val:.2f} tons/ha")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
