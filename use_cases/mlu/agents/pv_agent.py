"""PV Installation Agent for Multi-Land Use simulation.

Represents photovoltaic (solar panel) installations that compete with
agricultural land use. Makes decisions based on solar radiation, electricity
prices, and installation costs.
"""

from mesa import Agent


class PVInstallationAgent(Agent):
    """Agent representing a solar PV installation.

    Decisions based on:
    - Solar radiation (from meteo data)
    - Electricity price and feed-in tariffs
    - Installation and maintenance costs
    - Land opportunity cost (foregone agricultural revenue)
    """

    def __init__(self, model, lat, lon):
        """Initialize PV installation agent.

        Args:
            model: LandUseModel instance
            lat: Latitude of installation
            lon: Longitude of installation
        """
        super().__init__(model)

        # Location
        self.lat = lat
        self.lon = lon

        # PV characteristics
        self.capacity_kw = 100.0  # Installation capacity (kW)
        self.efficiency = 0.18  # Panel efficiency (18%)
        self.degradation_rate = 0.005  # Annual degradation (0.5%/year)
        self.age_years = 0  # Installation age

        # Economic parameters
        self.installation_cost_per_kw = 1000.0  # €/kW
        self.maintenance_cost_annual = 500.0  # €/year
        self.electricity_price = 0.15  # €/kWh (feed-in tariff)
        self.subsidy_rate = 0.20  # 20% government subsidy

        # Operational state
        self.is_operational = True
        self.annual_energy_kwh = 0.0  # Energy produced this year
        self.annual_revenue = 0.0
        self.annual_profit = 0.0
        self.lifetime_revenue = 0.0

        # Spatial influence
        self.spatial_neighbors = []  # Nearby farmers/PV installations
        self.neighbor_influence_radius = 50.0  # km

    def step(self):
        """Execute one time step (one year).

        1. Get solar radiation for current year
        2. Calculate energy production
        3. Calculate revenue and profit
        4. Update age and efficiency (degradation)
        5. Update spatial neighbors
        """
        if not self.is_operational:
            return

        year = self.model.current_year

        # Update spatial neighbors (for influence calculations)
        self.spatial_neighbors = self.model.get_spatial_neighbors(
            self,
            radius_km=self.neighbor_influence_radius
        )

        # Get solar radiation (W/m²) for this location and year
        solar_radiation = self.model.get_meteo(
            self.lat, self.lon, 'solar_radiation', year
        )

        # Calculate energy production
        self.annual_energy_kwh = self._calculate_energy_production(solar_radiation)

        # Calculate economics
        self.annual_revenue = self.annual_energy_kwh * self.electricity_price
        maintenance_cost = self.maintenance_cost_annual
        self.annual_profit = self.annual_revenue - maintenance_cost

        self.lifetime_revenue += self.annual_revenue

        # Age and degrade
        self.age_years += 1
        self.efficiency *= (1.0 - self.degradation_rate)

        # Decommission after 25 years
        if self.age_years >= 25:
            self.is_operational = False

    def _calculate_energy_production(self, solar_radiation_w_m2):
        """Calculate annual energy production based on solar radiation.

        Args:
            solar_radiation_w_m2: Average solar radiation (W/m²)

        Returns:
            Annual energy production (kWh)
        """
        # Convert W/m² to kWh/m²/year
        # Assume 365 days, average 6 hours of useful sunlight per day
        hours_per_year = 365 * 6
        solar_energy_kwh_m2 = (solar_radiation_w_m2 / 1000.0) * hours_per_year

        # Panel area for capacity (typical: 6-8 m² per kW)
        panel_area_m2 = self.capacity_kw * 7.0  # m²

        # Energy production = solar energy × area × efficiency
        energy_kwh = solar_energy_kwh_m2 * panel_area_m2 * self.efficiency

        return energy_kwh

    def get_suitability_score(self, year):
        """Calculate PV suitability score for this location.

        Based on:
        - Solar radiation (higher = better)
        - Economic viability (ROI)
        - Land opportunity cost

        Returns:
            Suitability score (0-100)
        """
        # Get solar radiation
        solar_radiation = self.model.get_meteo(
            self.lat, self.lon, 'solar_radiation', year
        )

        # Solar suitability (normalize: 150-250 W/m² typical range)
        solar_score = min(100.0, max(0.0, (solar_radiation - 150.0) / 100.0 * 100.0))

        # Economic suitability (simple ROI check)
        estimated_annual_energy = self._calculate_energy_production(solar_radiation)
        estimated_annual_revenue = estimated_annual_energy * self.electricity_price
        estimated_annual_profit = estimated_annual_revenue - self.maintenance_cost_annual

        total_investment = self.capacity_kw * self.installation_cost_per_kw * (1.0 - self.subsidy_rate)

        if total_investment > 0:
            roi_years = total_investment / max(1.0, estimated_annual_profit)
            # Good ROI: < 10 years = 100 points, 20 years = 50 points, > 30 years = 0 points
            economic_score = max(0.0, 100.0 - (roi_years - 10.0) * 5.0)
        else:
            economic_score = 0.0

        # Weighted combination
        suitability = 0.6 * solar_score + 0.4 * economic_score

        return suitability

    def get_influence_on_neighbors(self):
        """Calculate influence of this PV installation on nearby farmers.

        Returns:
            dict with influence metrics
        """
        return {
            'type': 'pv_installation',
            'energy_output': self.annual_energy_kwh,
            'profitability': self.annual_profit,
            'age': self.age_years,
            'capacity': self.capacity_kw
        }
