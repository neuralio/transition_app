"""Farmer Agent for Land-Use Suitability simulation."""

import mesa


class FarmerAgent(mesa.Agent):
    """A farmer deciding which crop to plant based on multiple factors."""

    def __init__(self,
                 model,
                 lat,
                 lon):
        """Initialize farmer agent.

        Args:
            model: Mesa model instance
            lat: Latitude of farmer's land
            lon: Longitude of farmer's land
        """
        super().__init__(model)
        self.lat = lat
        self.lon = lon
        self.current_crop = None

        # Get static data for this location
        self.soil_ph = model.get_soil(lat, lon, 'ph')
        self.soil_organic_carbon = model.get_soil(lat, lon, 'organic_carbon')
        self.elevation = model.get_elevation(lat, lon)

        # Economic state
        self.land_hectares = 10.0  # ❌ FAKE - TODO: Use real FADN farm size distribution
        self.expected_yield = 0.0  # tons/hectare (from real AquaCrop data)
        self.actual_yield = 0.0  # Realized yield after environmental factors
        self.annual_income = 0.0  # Euros (price × yield × land_size)

        # Multi-level interaction
        self.collective = None  # Link to CollectiveAgent
        self.community_signals = {}  # Signals from community level

        # Spatial interaction
        self.spatial_neighbors = []  # List of nearby FarmerAgents (updated each step)
        self.neighbor_influence_radius = 50.0  # km (increased for sparse farmer distribution)

    def receive_community_signals(self, signals):
        """
        Receive signals from Community Level (downward flow).

        Args:
            signals: Dict with market/policy signals and social norms
        """
        self.community_signals = signals

    def step(self):
        """One decision step - choose crop based on all factors."""
        year = self.model.current_year

        # Update spatial neighbors (geographic proximity)
        self.spatial_neighbors = self.model.get_spatial_neighbors(
            self,
            radius_km=self.neighbor_influence_radius
        )

        # Get dynamic data for current year
        temperature = self.model.get_meteo(self.lat, self.lon, 'temperature', year)
        precipitation = self.model.get_meteo(self.lat, self.lon, 'precipitation', year)
        solar_radiation = self.model.get_meteo(self.lat, self.lon, 'solar_radiation', year)

        # Get crop suitability scores (including expected yield)
        crop_scores = {}
        crop_expected_yields = {}  # Store expected yields for each crop

        for crop in self.model.crops:
            base_score = self.model.get_suitability(self.lat, self.lon, crop, year)

            # Get expected yield from REAL AquaCrop data
            expected_yield = self.model.get_expected_yield(crop, year)
            crop_expected_yields[crop] = expected_yield

            # Adjust score based on environmental factors
            adjusted_score = self._adjust_score(
                base_score=base_score,
                crop=crop,
                temperature=temperature,
                precipitation=precipitation,
                solar_radiation=solar_radiation
            )

            # Apply market/policy influences from community signals
            if self.community_signals:
                adjusted_score = self._apply_market_policy_influence(
                    score=adjusted_score,
                    crop=crop,
                    expected_yield=expected_yield
                )

            # Apply spatial neighbor influence (geographic proximity effects)
            adjusted_score = self._apply_spatial_neighbor_influence(
                score=adjusted_score,
                crop=crop
            )

            crop_scores[crop] = adjusted_score

        # Choose crop with highest adjusted score
        self.current_crop = max(crop_scores, key=crop_scores.get)
        self.expected_yield = crop_expected_yields[self.current_crop]

        # Calculate actual yield (expected yield adjusted by local conditions)
        self.actual_yield = self._calculate_actual_yield(
            expected_yield=self.expected_yield,
            temperature=temperature,
            precipitation=precipitation,
            solar_radiation=solar_radiation
        )

        # Calculate income
        self._calculate_income()

    def _adjust_score(self,
                      base_score,
                      crop,
                      temperature,
                      precipitation,
                      solar_radiation):
        """Adjust crop suitability score based on conditions.

        Args:
            base_score: Base LUSA suitability score
            crop: Crop name
            temperature: Temperature (K)
            precipitation: Precipitation (mm)
            solar_radiation: Solar radiation (W/m²)

        Returns:
            Adjusted score
        """
        score = base_score

        # Temperature adjustment (data is in Celsius)
        if crop == "WHEAT":
            # Wheat prefers cooler temps
            if temperature > 20:  # Too hot for wheat
                score *= 0.85
            elif temperature < 5:  # Too cold
                score *= 0.9
        elif crop == "MAIZE":
            # Maize needs warmer temps
            if temperature > 25:  # Ideal warmth
                score *= 1.05
            elif temperature < 10:  # Too cold for maize
                score *= 0.85

        # Precipitation adjustment
        if precipitation < 1.0:  # Low precipitation
            score *= 0.8  # General penalty for drought

        # Solar radiation adjustment
        if solar_radiation > 200:  # High solar radiation
            if crop == "MAIZE":
                score *= 1.1  # Maize benefits from sun

        # Soil pH adjustment
        if self.soil_ph < 60 or self.soil_ph > 80:
            score *= 0.9  # Penalty for extreme pH

        # Elevation adjustment
        if self.elevation > 500:
            if crop == "WHEAT":
                score *= 1.05  # Wheat does better at altitude
            elif crop == "MAIZE":
                score *= 0.95  # Maize prefers lower altitude

        return max(0, score)  # Ensure non-negative

    def _apply_market_policy_influence(self,
                                       score,
                                       crop,
                                       expected_yield):
        """Apply market and policy influences to crop score.

        Args:
            score: Current adjusted score
            crop: Crop name
            expected_yield: Expected yield (tons/ha) from real AquaCrop data

        Returns:
            Score adjusted for market/policy signals
        """
        if not self.community_signals:
            return score

        # Market influence: expected revenue (price × yield)
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

        # Policy influence: subsidies
        policy_signals = self.community_signals.get('policy_signals', {})
        subsidies = policy_signals.get('subsidies', {})
        if crop in subsidies:
            subsidy_rate = subsidies[crop]
            # Subsidy increases attractiveness
            score *= (1.0 + subsidy_rate)

        # Social influence: collective preference
        collective_preference = self.community_signals.get('collective_preference')
        social_norms = self.community_signals.get('social_norms', {})
        risk_aversion = social_norms.get('risk_aversion', 0.5)

        if collective_preference == crop:
            # If community prefers this crop, it becomes more attractive
            # Effect modulated by social norms
            social_multiplier = 1.0 + (0.2 * risk_aversion)  # Higher risk aversion = stronger conformity
            score *= social_multiplier

        return max(0, score)

    def _calculate_actual_yield(self,
                                expected_yield,
                                temperature,
                                precipitation,
                                solar_radiation):
        """
        Calculate actual yield based on expected yield and local conditions.

        The expected_yield comes from REAL AquaCrop simulations.
        We adjust it based on local micro-conditions.

        Args:
            expected_yield: Expected yield (tons/ha) from AquaCrop data
            temperature: Temperature (Celsius)
            precipitation: Precipitation (mm)
            solar_radiation: Solar radiation (W/m²)

        Returns:
            Actual yield (tons/ha)
        """
        actual_yield = expected_yield

        # Temperature stress
        if self.current_crop == "WHEAT":
            if temperature > 25:  # Heat stress for wheat
                actual_yield *= 0.85
            elif temperature < 0:  # Frost damage
                actual_yield *= 0.70
        elif self.current_crop == "MAIZE":
            if temperature > 35:  # Heat stress for maize
                actual_yield *= 0.80
            elif temperature < 8:  # Cold stress
                actual_yield *= 0.75

        # Water stress (low precipitation)
        if precipitation < 0.5:  # Severe drought
            actual_yield *= 0.60
        elif precipitation < 1.5:  # Moderate drought
            actual_yield *= 0.85

        # Solar radiation bonus
        if solar_radiation > 250:
            if self.current_crop == "MAIZE":
                actual_yield *= 1.05  # Maize benefits from high radiation

        # Soil quality adjustment
        if self.soil_organic_carbon > 15:  # High quality soil
            actual_yield *= 1.10
        elif self.soil_organic_carbon < 5:  # Poor soil
            actual_yield *= 0.90

        return max(0, actual_yield)

    def _calculate_income(self):
        """
        Calculate farmer's annual income.

        Income = (Price × Actual Yield × Land Size) + Subsidies - Costs

        Currently uses FAKE costs/subsidies - TODO: Use real FADN data
        """
        # Get market price
        market_signals = self.community_signals.get('market_signals', {})
        crop_prices = market_signals.get('crop_prices', {})
        price = crop_prices.get(self.current_crop, 100.0)  # Euros per ton

        # Revenue from crop sale
        revenue = price * self.actual_yield * self.land_hectares

        # Get subsidies
        policy_signals = self.community_signals.get('policy_signals', {})
        subsidies = policy_signals.get('subsidies', {})
        subsidy_rate = subsidies.get(self.current_crop, 0.0)
        subsidy_amount = revenue * subsidy_rate

        # Costs (❌ FAKE - TODO: Use real FADN cost data)
        cost_per_hectare = 500.0  # ❌ FAKE base cost
        if self.current_crop == "MAIZE":
            cost_per_hectare = 600.0  # ❌ FAKE maize costs more
        total_costs = cost_per_hectare * self.land_hectares

        # Net income
        self.annual_income = revenue + subsidy_amount - total_costs

    def get_economic_state(self):
        """
        Get farmer's economic state for upward information flow.

        Returns:
            Dict with economic indicators
        """
        return {
            'crop': self.current_crop,
            'expected_yield': self.expected_yield,
            'actual_yield': self.actual_yield,
            'land_hectares': self.land_hectares,
            'annual_income': self.annual_income,
            'total_production': self.actual_yield * self.land_hectares  # tons
        }

    def _apply_spatial_neighbor_influence(self, score, crop):
        """Apply influence from neighboring farmers (geographic proximity).

        Implements spatial feedback loops:
        1. Crop adoption diffusion: Neighbors growing same crop = social proof
        2. Knowledge spillovers: Successful neighbors increase confidence
        3. Local externalities: Diverse crops reduce pest risk

        Args:
            score: Current adjusted score
            crop: Crop being evaluated

        Returns:
            Score adjusted for spatial neighbor influence
        """
        if not self.spatial_neighbors:
            return score  # No neighbors within radius

        # Separate farmer neighbors from PV neighbors
        from use_cases.mlu.agents.pv_agent import PVInstallationAgent

        farmer_neighbors = []
        pv_neighbors = []

        for neighbor in self.spatial_neighbors:
            if isinstance(neighbor, PVInstallationAgent):
                pv_neighbors.append(neighbor)
            else:
                farmer_neighbors.append(neighbor)

        # Count neighbors growing each crop
        neighbor_crops = {}
        neighbor_incomes = {}  # Track neighbor success

        for neighbor in farmer_neighbors:
            if neighbor.current_crop:
                neighbor_crop = neighbor.current_crop
                neighbor_crops[neighbor_crop] = neighbor_crops.get(neighbor_crop, 0) + 1

                # Track income for knowledge spillovers
                if neighbor_crop not in neighbor_incomes:
                    neighbor_incomes[neighbor_crop] = []
                neighbor_incomes[neighbor_crop].append(neighbor.annual_income)

        total_neighbors = len(farmer_neighbors)

        # 1. CROP ADOPTION DIFFUSION: Social proof from neighbors
        if crop in neighbor_crops:
            adoption_rate = neighbor_crops[crop] / total_neighbors
            # Bandwagon effect: More neighbors growing it = more attractive
            diffusion_multiplier = 1.0 + (0.15 * adoption_rate)  # Up to +15% if all neighbors grow it
            score *= diffusion_multiplier

        # 2. KNOWLEDGE SPILLOVERS: Learn from successful neighbors
        if crop in neighbor_incomes:
            avg_neighbor_income = sum(neighbor_incomes[crop]) / len(neighbor_incomes[crop])
            # If neighbors are successful with this crop, boost confidence
            baseline_income = 25000.0  # Baseline annual income
            if avg_neighbor_income > baseline_income:
                success_multiplier = 1.0 + min(0.10, (avg_neighbor_income / baseline_income - 1.0) * 0.1)
                score *= success_multiplier

        # 3. LOCAL EXTERNALITIES: Diversity reduces pest/disease risk
        unique_crops = len(neighbor_crops)
        if unique_crops > 1:
            # Diverse neighborhood = lower monoculture risk
            diversity_bonus = 1.0 + (0.05 * (unique_crops - 1) / len(self.model.crops))
            score *= diversity_bonus

        # 4. PV NEIGHBOR INFLUENCE: Nearby solar installations affect decisions
        if pv_neighbors:
            # Count profitable PV installations
            profitable_pv = sum(1 for pv in pv_neighbors if pv.annual_profit > 0)

            if profitable_pv > 0:
                # Successful PV nearby makes agriculture less attractive
                # Farmers might consider: "Maybe I should switch to PV?"
                # This represents opportunity cost awareness
                pv_competition_factor = 0.95  # -5% penalty per profitable PV neighbor
                score *= (pv_competition_factor ** profitable_pv)

        return score

    def __repr__(self):
        return f"Farmer({self.unique_id}, crop={self.current_crop}, lat={self.lat:.2f}, lon={self.lon:.2f})"
