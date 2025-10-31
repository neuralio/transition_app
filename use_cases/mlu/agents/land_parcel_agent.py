"""Land Parcel Agent - Decides between agricultural use and solar PV installation.

Each parcel evaluates:
1. Agricultural suitability (LUSA crop scores + expected yields)
2. Solar PV suitability (solar radiation + economic viability)
3. Makes decision: CROP (with specific crop choice) or SOLAR PV

This implements the requirement: "processes ensemble climate projections to
predict the likelihood of land being suitable for particular crops or solar
installations under each scenario"
"""

import mesa


class LandParcelAgent(mesa.Agent):
    """Agent representing a land parcel that chooses between agriculture and solar PV.

    Decision factors:
    - LUSA crop suitability scores
    - Expected crop yields and market prices
    - Solar radiation levels
    - PV installation economics (costs, feed-in tariffs)
    - Neighbor influence (what are nearby parcels doing?)
    """

    def __init__(self, model, lat, lon, rl_policy=None, initial_crop=None):
        """Initialize land parcel agent.

        Args:
            model: LandUseModel instance
            lat: Latitude
            lon: Longitude
            rl_policy: Optional RLPolicy instance for RL-based decisions
        """
        super().__init__(model)

        # Location
        self.lat = lat
        self.lon = lon

        # Current land use decision
        self.land_use = None  # Will be 'agriculture' or 'solar_pv'
        self.current_crop = initial_crop  # If agriculture, which crop?

        # Land characteristics (varied farm sizes for realistic heterogeneity)
        import random
        rng = random.Random(42 + lat * 1000 + lon * 1000)  # Deterministic based on location
        self.land_hectares = rng.uniform(5.0, 15.0)  # Varied parcel sizes: 5-15 hectares

        # RL policy (optional)
        self.rl_policy = rl_policy
        self.use_rl = rl_policy is not None

        # Economic metrics
        self.annual_income = 0.0
        self.annual_profit = 0.0
        self.expected_yield = 0.0  # Expected yield (tons/ha)
        self.actual_yield = 0.0  # Actual yield (tons/ha) - for agriculture
        self.annual_energy_kwh = 0.0  # For solar PV

        # Get static environmental attributes
        self.soil_organic_carbon = model.get_soil(lat, lon, 'organic_carbon')
        self.soil_ph = model.get_soil(lat, lon, 'ph')
        self.elevation = model.get_elevation(lat, lon)

        # Solar PV parameters (if parcel chooses solar)
        self.pv_capacity_kw = 100.0
        self.pv_efficiency = 0.18
        self.pv_degradation_rate = 0.005
        self.pv_age_years = 0
        self.pv_installation_cost_per_kw = 1000.0  # €/kW
        self.pv_maintenance_cost_annual = 500.0  # €/year
        self.electricity_price = 0.15  # €/kWh
        self.subsidy_rate = 0.20  # 20% subsidy

        # Spatial influence
        self.spatial_neighbors = []
        self.neighbor_influence_radius = 50.0  # km

        # Multi-level ABM: Community signals (downward flow)
        self.community_signals = {}  # Signals from community level

    def receive_community_signals(self, signals):
        """
        Receive signals from Community Level (downward flow).

        Args:
            signals: Dict with market/policy signals and social norms
        """
        self.community_signals = signals

    def get_economic_state(self):
        """
        Get parcel's economic state for upward information flow (multi-level ABM).

        Returns:
            Dict with economic indicators
        """
        return {
            'land_use': self.land_use,  # 'agriculture' or 'solar_pv'
            'crop': self.current_crop,  # Crop name if agriculture, else None
            'expected_yield': self.expected_yield,  # Expected yield (tons/ha)
            'actual_yield': self.actual_yield,  # Actual yield (tons/ha)
            'land_hectares': self.land_hectares,
            'annual_income': self.annual_income,  # Total income
            'annual_profit': self.annual_profit,  # Net profit
            'total_production': self.actual_yield * self.land_hectares if self.land_use == 'agriculture' else 0.0,  # tons
            'annual_energy_kwh': self.annual_energy_kwh if self.land_use == 'solar_pv' else 0.0  # kWh
        }

    def step(self):
        """Execute one time step (one year).

        1. Update spatial neighbors
        2. Make land-use decision (RL or rule-based)
        3. Execute chosen land use
        """
        year = self.model.current_year

        # Update spatial neighbors
        self.spatial_neighbors = self.model.get_spatial_neighbors(
            self,
            radius_km=self.neighbor_influence_radius
        )

        # Make decision using RL or rule-based logic
        if self.use_rl:
            self._decide_with_rl(year)
        else:
            self._decide_rule_based(year)

    def _decide_rule_based(self, year):
        """Rule-based decision logic (original implementation)."""
        # NEW: If first year and agent has user-specified initial crop, start with it
        if year == self.model.current_year and self.current_crop is not None:
            self.land_use = 'agriculture'
            self._execute_agriculture(year)
            if self.unique_id % 5 == 0:
                print(f"   📌 Parcel ({self.lat:.3f},{self.lon:.3f}): Starting with {self.current_crop} (user-specified)")
            return

        # Evaluate both options
        ag_score, best_crop = self._evaluate_agriculture(year)
        pv_score = self._evaluate_solar_pv(year)

        # DEBUG: Print decision for first year
        if year == 2021 and self.unique_id % 5 == 0:
            decision = "🌾 AG" if ag_score > pv_score else "☀️ SOLAR"
            print(f"   Parcel ({self.lat:.3f},{self.lon:.3f}): Ag={ag_score:.1f}, Solar={pv_score:.1f} → {decision}")

        # Make decision
        if ag_score > pv_score:
            self.land_use = 'agriculture'
            self.current_crop = best_crop
            self._execute_agriculture(year)
        else:
            self.land_use = 'solar_pv'
            self.current_crop = None
            self._execute_solar_pv(year)

    def _decide_with_rl(self, year):
        """RL-based decision logic."""
        # Create observation vector
        observation = self._create_rl_observation(year)

        # Get action from RL policy (enable debug for first 3 parcels in first year)
        debug_mode = (year == 2021 and self.unique_id <= 3)
        action = self.rl_policy.predict_action(observation, deterministic=True, debug=debug_mode)

        # Map action to land use: 0=WHEAT, 1=MAIZE, 2=SOLAR
        action_map = {0: "WHEAT", 1: "MAIZE", 2: "SOLAR"}
        chosen_action = action_map[action]

        # DEBUG: Print decision for first year
        if year == 2021 and self.unique_id % 5 == 0:
            print(f"   🤖 RL Parcel ({self.lat:.3f},{self.lon:.3f}): {chosen_action}")

        # Execute decision
        if action in [0, 1]:  # Agriculture
            self.land_use = 'agriculture'
            self.current_crop = chosen_action
            self._execute_agriculture(year)
        else:  # Solar
            self.land_use = 'solar_pv'
            self.current_crop = None
            self._execute_solar_pv(year)

    def _create_rl_observation(self, year):
        """
        Create observation vector for RL policy.

        Returns:
            np.ndarray: 11D observation [lusa_wheat, lusa_maize, lusa_solar,
                        temp, precip, solar_rad, soil, wheat_price, maize_price,
                        elec_price, subsidy]
        """
        import numpy as np

        # Get LUSA scores
        lusa_wheat = self.model.get_suitability(self.lat, self.lon, "WHEAT", year)
        lusa_maize = self.model.get_suitability(self.lat, self.lon, "MAIZE", year)
        lusa_solar = self._get_solar_suitability(year)

        # Get environmental data
        temp = self.model.get_meteo(self.lat, self.lon, 'temperature', year)
        precip = self.model.get_meteo(self.lat, self.lon, 'precipitation', year)
        solar_rad = self.model.get_meteo(self.lat, self.lon, 'solar_radiation', year)
        soil_quality = self.soil_organic_carbon

        # Get market prices (from community signals if available)
        wheat_price = 200.0
        maize_price = 180.0
        if self.community_signals:
            market_signals = self.community_signals.get('market_signals', {})
            crop_prices = market_signals.get('crop_prices', {})
            wheat_price = crop_prices.get('wheat', 200.0)
            maize_price = crop_prices.get('maize', 180.0)

        # Get policy data
        elec_price = self.electricity_price
        subsidy = self.subsidy_rate
        if self.community_signals:
            policy_signals = self.community_signals.get('policy_signals', {})
            subsidies = policy_signals.get('subsidies', {})
            subsidy = subsidies.get('solar', 0.20)

        # Construct observation
        observation = np.array([
            lusa_wheat,
            lusa_maize,
            lusa_solar,
            temp,
            precip,
            solar_rad,
            soil_quality,
            wheat_price,
            maize_price,
            elec_price,
            subsidy
        ], dtype=np.float32)

        return observation

    def _evaluate_agriculture(self, year):
        """Evaluate agricultural suitability for all crops.

        Returns:
            (best_score, best_crop): Highest score and corresponding crop
        """
        best_score = 0.0
        best_crop = None

        for crop in self.model.crops:
            # Get LUSA base suitability
            base_suitability = self.model.get_suitability(
                self.lat, self.lon, crop, year
            )

            # Get expected yield
            expected_yield = self.model.get_expected_yield(crop, year)

            # Get market price
            market_price = self._get_crop_price(crop)

            # Calculate expected revenue
            parcel_size_ha = 10.0  # Assume 10 hectares
            expected_revenue = expected_yield * parcel_size_ha * market_price

            # Environmental adjustments (temperature, precipitation, etc.)
            env_multiplier = self._get_environmental_multiplier(crop, year)

            # Combine into overall agriculture score
            ag_score = base_suitability * env_multiplier * (expected_revenue / 10000.0)

            # Apply multi-level signals (market, policy, social)
            ag_score = self._apply_multilevel_signals(ag_score, crop, expected_yield)

            if ag_score > best_score:
                best_score = ag_score
                best_crop = crop

        return best_score, best_crop

    def _apply_multilevel_signals(self, score, crop, expected_yield):
        """
        Apply multi-level ABM signals (market, policy, social) to crop score.

        Args:
            score: Base suitability score
            crop: Crop name
            expected_yield: Expected yield (tons/ha)

        Returns:
            Score adjusted for market/policy/social signals
        """
        if not self.community_signals:
            return score

        # Market influence: crop prices from CommodityMarketAgent
        market_signals = self.community_signals.get('market_signals', {})
        crop_prices = market_signals.get('crop_prices', {})
        if crop in crop_prices:
            price = crop_prices[crop]  # Euros per ton
            expected_revenue = price * expected_yield * self.land_hectares  # Total revenue

            # Higher revenue = more attractive
            # Base revenue: 100 (price) × 2.5 (avg yield) × 10 (land) = 2500 euros
            baseline_revenue = 100.0 * 2.5 * 10.0
            revenue_multiplier = expected_revenue / baseline_revenue
            score *= revenue_multiplier

        # Policy influence: subsidies from PolicymakerAgent
        policy_signals = self.community_signals.get('policy_signals', {})
        subsidies = policy_signals.get('subsidies', {})
        if crop in subsidies:
            subsidy_rate = subsidies[crop]
            # Subsidy increases attractiveness
            score *= (1.0 + subsidy_rate)

        # Social influence: collective preference from CollectiveAgent
        collective_preference = self.community_signals.get('collective_preference')
        social_norms = self.community_signals.get('social_norms', {})
        risk_aversion = social_norms.get('risk_aversion', 0.5)

        if collective_preference == crop:
            # If community prefers this crop, it becomes more attractive
            # Effect modulated by social norms
            social_multiplier = 1.0 + (0.2 * risk_aversion)  # Higher risk aversion = stronger conformity
            score *= social_multiplier

        return max(0, score)

    def _get_solar_suitability(self, year):
        """
        Calculate solar PV suitability score (simplified for RL observation).

        Returns:
            float: Solar suitability score (0-100)
        """
        # Get solar radiation
        solar_radiation = self.model.get_meteo(
            self.lat, self.lon, 'solar_radiation', year
        )

        # Normalize solar radiation to 0-100 scale
        # Typical Greece: 2-4 kWh/m²/day, excellent sites: 4-5 kWh/m²/day
        solar_score = min(100.0, (solar_radiation / 5.0) * 100.0)

        return solar_score

    def _evaluate_solar_pv(self, year):
        """Evaluate solar PV suitability.

        Factors:
        - Solar radiation quality
        - Installation and grid connection costs
        - Distance to roads (access costs)
        - Distance to power grid (connection costs)
        - ROI and profitability

        Returns:
            PV suitability score
        """
        # Get solar radiation
        solar_radiation = self.model.get_meteo(
            self.lat, self.lon, 'solar_radiation', year
        )

        # Calculate expected energy production
        expected_energy = self._calculate_pv_energy(solar_radiation)

        # Calculate expected revenue
        expected_revenue = expected_energy * self.electricity_price

        # Get subsidy rate from policy signals (multi-level ABM) or use default
        subsidy_rate = self.subsidy_rate
        if self.community_signals:
            policy_signals = self.community_signals.get('policy_signals', {})
            pv_subsidy = policy_signals.get('pv_subsidy_rate')
            if pv_subsidy is not None:
                subsidy_rate = pv_subsidy

        # Calculate infrastructure costs
        # 1. Base installation cost
        base_installation = self.pv_capacity_kw * self.pv_installation_cost_per_kw * (1.0 - subsidy_rate)

        # 2. Distance to road network (assume random 0-10km, TODO: load real GIS data)
        import random
        random.seed(int(self.lat * 10000 + self.lon * 10000))  # Deterministic per location
        distance_to_road_km = random.uniform(0.5, 10.0)
        road_access_cost = distance_to_road_km * 5000  # €5000/km for temporary access roads

        # 3. Distance to power grid (assume random 1-20km, TODO: load real grid data)
        distance_to_grid_km = random.uniform(1.0, 20.0)
        # Grid connection is EXPENSIVE: €20,000-50,000/km for medium voltage lines
        grid_connection_cost = distance_to_grid_km * 30000  # €30,000/km
        grid_connection_fee = 5000  # One-time utility connection fee

        # Total investment
        total_investment = base_installation + road_access_cost + grid_connection_cost + grid_connection_fee

        # Annual costs
        annual_cost = self.pv_maintenance_cost_annual
        annual_grid_fee = 500  # Annual grid access/transmission fee

        # Calculate ROI
        annual_profit = expected_revenue - annual_cost - annual_grid_fee
        roi_years = total_investment / max(1.0, annual_profit)

        # Solar score: Use revenue-based score with infrastructure penalties
        # NOTE: solar_radiation is in kWh/m²/day (typical Greece: 2-4 kWh/m²/day)
        radiation_factor = min(1.5, solar_radiation / 3.0)  # Normalize: 3 kWh/m²/day = 1.0

        # ROI factor: Don't penalize too harshly for long ROI if profit is still positive
        # Focus on annual profit rather than payback period
        if annual_profit > 0:
            roi_factor = min(2.0, (annual_profit / 5000.0))  # €5k/year profit = 1.0x
        else:
            roi_factor = 0.1  # Unprofitable

        # Infrastructure factor: Grid distance is critical
        # Close to grid (<5km) = good, far from grid (>15km) = poor
        if distance_to_grid_km < 5:
            infrastructure_factor = 1.0
        elif distance_to_grid_km < 10:
            infrastructure_factor = 0.7
        else:
            infrastructure_factor = 0.3

        # Balance solar vs agriculture scores to get realistic mix
        # Agriculture scores: ~15-35 (LUSA * env * revenue/10000)
        # Make solar competitive for parcels with: high radiation + close to grid
        solar_score = (expected_revenue / 30000.0) * radiation_factor * roi_factor * infrastructure_factor * 100.0

        # Store for debugging
        self._last_grid_distance = distance_to_grid_km
        self._last_solar_profit = annual_profit

        return solar_score

    def _execute_agriculture(self, year):
        """Execute agricultural land use."""
        from use_cases.mlu.agents.farmer_agent import FarmerAgent

        # Use FarmerAgent logic for crop production
        # Get expected yield
        expected_yield = self.model.get_expected_yield(self.current_crop, year)
        self.expected_yield = expected_yield  # Store for multi-level ABM

        # Environmental variability
        import random
        variability = random.gauss(0, 0.15)
        self.actual_yield = expected_yield * (1.0 + variability)
        self.actual_yield = max(0, self.actual_yield)

        # Calculate income
        parcel_size_ha = 10.0
        crop_price = self._get_crop_price(self.current_crop)
        total_production = self.actual_yield * parcel_size_ha
        revenue = total_production * crop_price

        # Costs (simplified)
        production_cost = parcel_size_ha * 500.0  # €500/ha
        self.annual_income = revenue
        self.annual_profit = revenue - production_cost

        # No PV production
        self.annual_energy_kwh = 0.0

    def _execute_solar_pv(self, year):
        """Execute solar PV land use."""
        # Get solar radiation
        solar_radiation = self.model.get_meteo(
            self.lat, self.lon, 'solar_radiation', year
        )

        # Calculate energy production
        self.annual_energy_kwh = self._calculate_pv_energy(solar_radiation)

        # No agriculture production
        self.expected_yield = 0.0
        self.actual_yield = 0.0

        # Calculate economics
        revenue = self.annual_energy_kwh * self.electricity_price
        maintenance_cost = self.pv_maintenance_cost_annual
        annual_grid_fee = 500.0  # Annual grid access/transmission fee (same as in evaluation)

        self.annual_income = revenue
        self.annual_profit = revenue - maintenance_cost - annual_grid_fee  # Include grid fee

        # Age and degrade
        self.pv_age_years += 1
        self.pv_efficiency *= (1.0 - self.pv_degradation_rate)

        # No crop production
        self.actual_yield = 0.0

    def _calculate_pv_energy(self, solar_radiation_kwh_m2_day):
        """Calculate annual PV energy production.

        Args:
            solar_radiation_kwh_m2_day: Solar radiation in kWh/m²/day (from NetCDF data)

        Returns:
            Annual energy in kWh
        """
        # Convert daily solar radiation to annual
        # NetCDF data is in kWh/m²/day (e.g., 2.2 kWh/m²/day for Greece)
        solar_energy_kwh_m2_year = solar_radiation_kwh_m2_day * 365

        # Panel area (7 m² per kW is typical for modern panels)
        panel_area_m2 = self.pv_capacity_kw * 7.0

        # Energy = solar energy × area × efficiency × performance ratio
        # Performance ratio accounts for: inverter losses, temperature losses, shading, etc.
        performance_ratio = 0.75  # Typical value: 0.75-0.80

        energy_kwh = solar_energy_kwh_m2_year * panel_area_m2 * self.pv_efficiency * performance_ratio

        return energy_kwh

    def _get_environmental_multiplier(self, crop, year):
        """Get environmental multiplier for crop (temperature, precipitation, etc.)."""
        # Simplified version - could be expanded
        temperature = self.model.get_meteo(self.lat, self.lon, 'temperature', year)
        precipitation = self.model.get_meteo(self.lat, self.lon, 'precipitation', year)

        # Temperature adjustment
        temp_multiplier = 1.0
        if crop == "MAIZE" and temperature > 25:
            temp_multiplier = 1.1  # Heat-loving
        elif crop == "WHEAT" and 15 < temperature < 20:
            temp_multiplier = 1.1  # Cool-season

        # Precipitation adjustment
        precip_multiplier = 1.0
        if precipitation > 500:
            precip_multiplier = 1.05

        return temp_multiplier * precip_multiplier

    def _get_crop_price(self, crop):
        """
        Get crop price from market agents.

        IMPORTANT: Only uses real market prices - no fallbacks.
        If multi-level mode disabled, raises error.
        """
        if not self.model.market_agents:
            raise ValueError(f"❌ No market agents available! Enable multi-level mode (--collectives, --markets, --policies) or check model initialization.")

        market = self.model.market_agents[0]
        if crop not in market.crop_prices:
            raise ValueError(f"❌ Crop '{crop}' not found in market prices! Available crops: {list(market.crop_prices.keys())}")

        return market.crop_prices[crop]

    def __repr__(self):
        return f"LandParcel({self.unique_id}, use={self.land_use}, crop={self.current_crop}, lat={self.lat:.2f}, lon={self.lon:.2f})"
