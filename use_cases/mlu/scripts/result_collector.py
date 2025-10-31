"""
Results Collection System for TRANSITION ML-ABM

Collects simulation data for generating interactive reports with:
- Map-based land suitability visualization
- Suitability scores (past, current, projected)
- Trade-off analysis (economic vs environmental)
- Confidence measures from ensemble projections
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import json


class ResultCollector:
    """
    Collects and stores simulation results for visualization and reporting.
    """

    def __init__(self, scenario: str, start_year: int):
        """
        Initialize result collector.

        Args:
            scenario: RCP scenario (rcp26, rcp45, rcp85)
            start_year: Starting year of simulation
        """
        self.scenario = scenario
        self.start_year = start_year
        self.current_step = 0

        # Time-series data
        self.timesteps = []
        self.farmer_data = []  # Individual farmer states
        self.collective_data = []  # Community aggregates
        self.market_data = []  # Market states
        self.policy_data = []  # Policy states

        # Spatial data (for mapping)
        self.spatial_snapshots = []  # Land suitability maps over time

        # Summary statistics
        self.summary_stats = {
            'total_production_by_crop': {},
            'avg_farmer_income': [],
            'crop_diversity': [],
            'land_use_change': [],
        }

    def collect_step(self, model):
        """
        Collect data from one simulation step.

        Args:
            model: LandUseModel instance
        """
        year = model.current_year
        self.timesteps.append(year)
        self.current_step += 1

        # Collect individual farmer/parcel data
        from use_cases.mlu.agents.farmer_agent import FarmerAgent
        from use_cases.mlu.agents.land_parcel_agent import LandParcelAgent

        # Collect from both FarmerAgent (legacy) and LandParcelAgent (new)
        farmers = [a for a in model.agents if isinstance(a, FarmerAgent)]
        farmers.extend(model.parcel_agents)  # Add land parcels

        step_farmer_data = []
        for farmer in farmers:
            # LandParcelAgent doesn't have get_economic_state(), so handle both cases
            if hasattr(farmer, 'get_economic_state'):
                econ = farmer.get_economic_state()
            else:
                # LandParcelAgent: construct economic state manually
                econ = {
                    'crop': farmer.current_crop,
                    'expected_yield': 0.0,  # Not tracked separately in LandParcelAgent
                    'actual_yield': farmer.actual_yield,
                    'total_production': farmer.actual_yield * 10.0,  # 10 ha assumed
                    'annual_income': farmer.annual_income,
                    'land_hectares': 10.0,
                }

            step_farmer_data.append({
                'year': year,
                'farmer_id': farmer.unique_id,
                'lat': farmer.lat,
                'lon': farmer.lon,
                'land_use': getattr(farmer, 'land_use', 'agriculture'),  # NEW
                'crop': econ['crop'],
                'expected_yield': econ['expected_yield'],
                'actual_yield': econ['actual_yield'],
                'total_production': econ['total_production'],
                'annual_income': econ['annual_income'],
                'land_hectares': econ['land_hectares'],
                'annual_energy_kwh': getattr(farmer, 'annual_energy_kwh', 0.0),  # NEW: for solar parcels
                # Environmental data
                'soil_ph': getattr(farmer, 'soil_ph', 0.0),
                'soil_organic_carbon': farmer.soil_organic_carbon,
                'elevation': farmer.elevation,
            })

        self.farmer_data.extend(step_farmer_data)

        # Collect collective data
        step_collective_data = []
        for collective in model.collective_agents:
            step_collective_data.append({
                'year': year,
                'collective_id': collective.unique_id,
                'region': collective.region_name,
                'num_farmers': len(collective.members),
                'dominant_crop': collective.collective_crop_preference,
                'collective_wealth': collective.collective_wealth,
                'crop_production': collective.crop_production.copy() if hasattr(collective, 'crop_production') else {},
            })

        self.collective_data.extend(step_collective_data)

        # Collect market data
        step_market_data = []
        for market in model.market_agents:
            step_market_data.append({
                'year': year,
                'market_id': market.unique_id,
                'crop_prices': market.crop_prices.copy(),
                'supply': market.supply.copy(),
                'demand': market.demand.copy(),
            })

        self.market_data.extend(step_market_data)

        # Collect policy data
        step_policy_data = []
        for policy in model.policy_agents:
            step_policy_data.append({
                'year': year,
                'policy_id': policy.unique_id,
                'subsidy_rates': policy.subsidy_rates.copy(),
                'price_floors': policy.price_floors.copy(),
                'price_ceilings': policy.price_ceilings.copy(),
            })

        self.policy_data.extend(step_policy_data)

        # Collect spatial snapshot for mapping
        spatial_snapshot = self._create_spatial_snapshot(model, year, farmers)
        self.spatial_snapshots.append(spatial_snapshot)

        # Update summary statistics
        self._update_summary_stats(model, farmers)

    def _create_spatial_snapshot(self, model, year, farmers):
        """
        Create spatial snapshot for land suitability mapping.

        Args:
            model: LandUseModel
            year: Current year
            farmers: List of FarmerAgent

        Returns:
            Dict with spatial data for visualization
        """
        snapshot = {
            'year': year,
            'parcels': []
        }

        for farmer in farmers:
            # Get current suitability scores for all crops
            suitability_scores = {}
            for crop in model.crops:
                score = model.get_suitability(farmer.lat, farmer.lon, crop, year)
                suitability_scores[crop] = float(score)

            # Get expected yields
            expected_yields = {}
            for crop in model.crops:
                yield_val = model.get_expected_yield(crop, year)
                expected_yields[crop] = float(yield_val)

            # Check if this is a LandParcelAgent
            land_use = getattr(farmer, 'land_use', 'agriculture')

            parcel = {
                'farmer_id': farmer.unique_id,  # Add ID for tracking
                'lat': float(farmer.lat),
                'lon': float(farmer.lon),
                'land_use': land_use,  # NEW: 'agriculture' or 'solar_pv'
                'current_crop': farmer.current_crop if land_use == 'agriculture' else None,
                'suitability_scores': suitability_scores,
                'expected_yields': expected_yields,
                'actual_yield': float(farmer.actual_yield),
                'annual_income': float(farmer.annual_income),
                'annual_energy_kwh': float(getattr(farmer, 'annual_energy_kwh', 0.0)),  # For solar parcels
                'soil_quality': float(farmer.soil_organic_carbon),
                'elevation': float(farmer.elevation),
                'spatial_neighbors': [n.unique_id for n in farmer.spatial_neighbors] if hasattr(farmer, 'spatial_neighbors') else [],
            }

            snapshot['parcels'].append(parcel)

        # Add PV installations
        snapshot['pv_installations'] = []
        if hasattr(model, 'pv_agents'):
            from use_cases.mlu.agents.pv_agent import PVInstallationAgent
            for pv in model.pv_agents:
                pv_data = {
                    'pv_id': pv.unique_id,
                    'lat': float(pv.lat),
                    'lon': float(pv.lon),
                    'capacity_kw': float(pv.capacity_kw),
                    'annual_energy_kwh': float(pv.annual_energy_kwh),
                    'annual_revenue': float(pv.annual_revenue),
                    'annual_profit': float(pv.annual_profit),
                    'age_years': int(pv.age_years),
                    'is_operational': bool(pv.is_operational),
                    'spatial_neighbors': [n.unique_id for n in pv.spatial_neighbors] if hasattr(pv, 'spatial_neighbors') else [],
                }
                snapshot['pv_installations'].append(pv_data)

        return snapshot

    def _update_summary_stats(self, model, farmers):
        """Update summary statistics."""

        # Total production by crop
        crop_production = {}
        for farmer in farmers:
            if farmer.current_crop:
                crop_production[farmer.current_crop] = crop_production.get(
                    farmer.current_crop, 0.0
                ) + farmer.actual_yield * farmer.land_hectares

        self.summary_stats['total_production_by_crop'][model.current_year] = crop_production

        # Average farmer income
        if farmers:
            avg_income = np.mean([f.annual_income for f in farmers])
            self.summary_stats['avg_farmer_income'].append(avg_income)

        # Crop diversity (Shannon entropy)
        crop_counts = {}
        for farmer in farmers:
            if farmer.current_crop:
                crop_counts[farmer.current_crop] = crop_counts.get(farmer.current_crop, 0) + 1

        if crop_counts:
            total = sum(crop_counts.values())
            proportions = [count / total for count in crop_counts.values()]
            shannon_entropy = -sum(p * np.log(p) for p in proportions if p > 0)
            self.summary_stats['crop_diversity'].append(shannon_entropy)
        else:
            self.summary_stats['crop_diversity'].append(0.0)

    def get_farmer_dataframe(self) -> pd.DataFrame:
        """Get farmer data as pandas DataFrame."""
        return pd.DataFrame(self.farmer_data)

    def get_collective_dataframe(self) -> pd.DataFrame:
        """Get collective data as pandas DataFrame."""
        return pd.DataFrame(self.collective_data)

    def get_market_dataframe(self) -> pd.DataFrame:
        """Get market data as pandas DataFrame."""
        # Flatten nested dicts
        flattened = []
        for record in self.market_data:
            flat_record = {
                'year': record['year'],
                'market_id': record['market_id'],
            }
            # Add crop prices
            for crop, price in record['crop_prices'].items():
                flat_record[f'{crop}_price'] = price
            # Add supply
            for crop, supply in record['supply'].items():
                flat_record[f'{crop}_supply'] = supply
            # Add demand
            for crop, demand in record['demand'].items():
                flat_record[f'{crop}_demand'] = demand

            flattened.append(flat_record)

        return pd.DataFrame(flattened)

    def get_policy_dataframe(self) -> pd.DataFrame:
        """Get policy data as pandas DataFrame."""
        # Flatten nested dicts
        flattened = []
        for record in self.policy_data:
            flat_record = {
                'year': record['year'],
                'policy_id': record['policy_id'],
            }
            # Add subsidy rates
            for crop, subsidy in record.get('subsidy_rates', {}).items():
                flat_record[f'{crop}_subsidy_rate'] = subsidy
            # Add price floors
            for crop, floor in record.get('price_floors', {}).items():
                flat_record[f'{crop}_price_floor'] = floor
            # Add price ceilings
            for crop, ceiling in record.get('price_ceilings', {}).items():
                flat_record[f'{crop}_price_ceiling'] = ceiling

            flattened.append(flat_record)

        return pd.DataFrame(flattened)

    def get_spatial_data(self, year: Optional[int] = None) -> Dict:
        """
        Get spatial data for mapping.

        Args:
            year: Specific year to get (None = latest)

        Returns:
            Spatial snapshot dict
        """
        if not self.spatial_snapshots:
            return {}

        if year is None:
            return self.spatial_snapshots[-1]

        # Find snapshot for specific year
        for snapshot in self.spatial_snapshots:
            if snapshot['year'] == year:
                return snapshot

        # If year not found, return closest
        return min(self.spatial_snapshots, key=lambda s: abs(s['year'] - year))

    def get_time_series_comparison(self, metric: str) -> Dict:
        """
        Get time-series data for a specific metric.

        Args:
            metric: 'income', 'production', 'diversity', 'prices'

        Returns:
            Dict with years and values
        """
        if metric == 'income':
            return {
                'years': self.timesteps,
                'values': self.summary_stats['avg_farmer_income'],
                'unit': '€/year',
                'label': 'Average Farmer Income'
            }
        elif metric == 'diversity':
            return {
                'years': self.timesteps,
                'values': self.summary_stats['crop_diversity'],
                'unit': 'Shannon Entropy',
                'label': 'Crop Diversity'
            }
        elif metric == 'production':
            # Sum total production across all crops
            total_production = []
            for year in self.timesteps:
                prod_dict = self.summary_stats['total_production_by_crop'].get(year, {})
                total_production.append(sum(prod_dict.values()))

            return {
                'years': self.timesteps,
                'values': total_production,
                'unit': 'tons',
                'label': 'Total Production'
            }

        return {}

    def calculate_trade_offs(self) -> Dict:
        """
        Calculate trade-offs between economic and environmental objectives.

        Returns:
            Dict with trade-off metrics
        """
        df = self.get_farmer_dataframe()

        if df.empty:
            return {}

        # Economic metrics
        total_income = df['annual_income'].sum()
        avg_income = df['annual_income'].mean()

        # Environmental metrics
        avg_soil_quality = df['soil_organic_carbon'].mean()
        crop_diversity = self.summary_stats['crop_diversity'][-1] if self.summary_stats['crop_diversity'] else 0

        # Production efficiency
        total_production = df['total_production'].sum()
        avg_yield = df['actual_yield'].mean()

        return {
            'economic': {
                'total_income': float(total_income),
                'avg_income': float(avg_income),
                'total_production': float(total_production),
                'avg_yield': float(avg_yield),
            },
            'environmental': {
                'avg_soil_quality': float(avg_soil_quality),
                'crop_diversity': float(crop_diversity),
            },
            'trade_off_score': float(avg_income * crop_diversity),  # Combined score
        }

    def export_to_json(self, output_path: str):
        """
        Export all results to JSON file.

        Args:
            output_path: Path to output JSON file
        """
        output = {
            'scenario': self.scenario,
            'start_year': self.start_year,
            'timesteps': self.timesteps,
            'farmer_data': self.farmer_data,
            'collective_data': self.collective_data,
            'market_data': self.market_data,
            'policy_data': self.policy_data,
            'spatial_snapshots': self.spatial_snapshots,
            'summary_stats': self.summary_stats,
            'trade_offs': self.calculate_trade_offs(),
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Results exported to: {output_path}")

    def export_to_csv(self, output_dir: str):
        """
        Export results as CSV files.

        Args:
            output_dir: Directory to save CSV files
        """
        from use_cases.mlu.utils.scenario_utils import get_scenario_short_name

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Use user-friendly scenario name for CSV filenames
        scenario_short = get_scenario_short_name(self.scenario).lower().replace(" ", "_")

        # Export each dataframe
        self.get_farmer_dataframe().to_csv(output_dir / f'{scenario_short}_farmers.csv', index=False)
        self.get_collective_dataframe().to_csv(output_dir / f'{scenario_short}_collectives.csv', index=False)
        self.get_market_dataframe().to_csv(output_dir / f'{scenario_short}_markets.csv', index=False)
        self.get_policy_dataframe().to_csv(output_dir / f'{scenario_short}_policies.csv', index=False)

        print(f"Results exported to: {output_dir}")

    def get_timeseries_summary(self) -> Dict:
        """
        Generate timeseries summary for RL comparison.

        Returns:
            Dict with 'timeseries' and 'summary' keys
        """
        df = self.get_farmer_dataframe()

        # Group by year
        timeseries = []
        for year in self.timesteps:
            year_data = df[df['year'] == year]

            # Count land use types
            n_wheat = len(year_data[year_data['crop'] == 'WHEAT'])
            n_maize = len(year_data[year_data['crop'] == 'MAIZE'])
            n_solar = len(year_data[year_data['land_use'] == 'solar_pv'])
            total = len(year_data)

            timeseries.append({
                'year': year,
                'pct_wheat': (n_wheat / total * 100) if total > 0 else 0,
                'pct_maize': (n_maize / total * 100) if total > 0 else 0,
                'pct_solar': (n_solar / total * 100) if total > 0 else 0,
                'total_income': year_data['annual_income'].sum(),
                'total_profit': year_data['annual_income'].sum() * 0.7,  # Approx profit = 70% income
                'total_production': year_data['total_production'].sum(),
                'total_energy': year_data['annual_energy_kwh'].sum()
            })

        # Summary statistics
        summary = {
            'scenario': self.scenario,
            'n_parcels': len(set(df['farmer_id'])),
            'n_years': len(self.timesteps),
            'start_year': self.start_year,
            'end_year': self.timesteps[-1] if self.timesteps else self.start_year
        }

        return {
            'timeseries': timeseries,
            'summary': summary
        }

    def __repr__(self):
        return f"ResultCollector(scenario={self.scenario}, steps={self.current_step}, farmers={len(set(f['farmer_id'] for f in self.farmer_data))})"


if __name__ == "__main__":
    print("ResultCollector - Ready for simulation data collection")
