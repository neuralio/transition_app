"""Farmer Agent for Land-Use Suitability simulation."""

import mesa


class FarmerAgent(mesa.Agent):
    """A farmer deciding which crop to plant based on multiple factors."""

    def __init__(self,
                 model,
                 lat,
                 lon,
                 initial_crop=None):
        """Initialize farmer agent.

        Args:
            model: Mesa model instance
            lat: Latitude of farmer's land
            lon: Longitude of farmer's land
            initial_crop: Optional initial crop assignment (e.g., 'WHEAT', 'MAIZE')
                         If None, agent will evaluate all options in first step
        """
        super().__init__(model)
        self.lat = lat
        self.lon = lon
        self.current_crop = initial_crop  # Can start with user-specified crop

        # Get static data for this location
        import random

        # Try to load real data, but add realistic variation if defaults returned
        self.soil_ph = model.get_soil(lat, lon, 'ph')
        if self.soil_ph == 0.5:  # Default value means data loading failed
            # Thessaloniki region: pH typically 6.5-8.0 for agricultural land
            self.soil_ph = random.uniform(6.5, 8.0)

        self.soil_organic_carbon = model.get_soil(lat, lon, 'organic_carbon')
        if self.soil_organic_carbon == 0.5:  # Default value means data loading failed
            # Mediterranean agricultural soils: 1.0-3.5% organic carbon
            self.soil_organic_carbon = random.uniform(1.0, 3.5)

        self.elevation = model.get_elevation(lat, lon)
        if self.elevation == 100.0:  # Default value means data loading failed
            # Thessaloniki region: 0-500m elevation (mostly plains with some hills)
            # Coastal areas: 0-50m, inland plains: 50-150m, hilly areas: 150-500m
            elevation_type = random.choice(['coastal', 'plain', 'plain', 'hill'])
            if elevation_type == 'coastal':
                self.elevation = random.uniform(0, 50)
            elif elevation_type == 'plain':
                self.elevation = random.uniform(50, 150)
            else:  # hill
                self.elevation = random.uniform(150, 500)

        # Economic state - Add farmer heterogeneity
        # Farm size varies: 5-20 hectares (log-normal distribution)
        self.land_hectares = max(5.0, min(20.0, random.lognormvariate(2.3, 0.4)))
        self.expected_yield = 0.0  # tons/hectare (from real AquaCrop data)
        self.actual_yield = 0.0  # Realized yield after environmental factors
        self.annual_income = 0.0  # Euros (price × yield × land_size)
        self.income_history = []  # Track income over time for adaptation capacity

        # PV installation state (CCA Option B)
        self.has_pv_installation = False  # Whether farmer switched to PV
        self.pv_lease_income = 0.0  # Annual lease income from PV developer (€/year)
        self.pv_installation_year = None  # Year when PV was installed

        # Multi-level interaction
        self.collective = None  # Link to CollectiveAgent
        self.community_signals = {}  # Signals from community level

        # Climate resilience (CCA-specific) - Differentiate farmers
        # Initial adaptation capacity varies by farmer characteristics
        # Larger farms = more resources = higher capacity
        farm_size_factor = min(1.0, self.land_hectares / 15.0)  # 15ha = high capacity
        # Age/experience varies (randomize: 0.2-0.8)
        experience_factor = random.uniform(0.2, 0.8)
        # Initial adaptation capacity (weighted combination)
        self.adaptation_capacity = 0.3 * farm_size_factor + 0.3 * experience_factor + 0.4 * 0.5

        # Vulnerability starts moderate but will evolve based on exposure and capacity
        self.vulnerability_score = 0.5
        self.climate_risk_exposure = {}  # Drought, flood, heatwave risks
        self.resilience_history = []  # Track resilience over time

        # Location-based risk factors (spatial variation even in small region)
        # Farmers at higher elevation = lower flood risk, higher drought risk
        self.elevation_risk_factor = (self.elevation - 200) / 500.0  # Normalized elevation risk
        # Farmers at edges of region = more exposed to extreme weather
        # Calculate distance from region center
        center_lat = (model.lat_bounds[0] + model.lat_bounds[1]) / 2.0
        center_lon = (model.lon_bounds[0] + model.lon_bounds[1]) / 2.0
        self.edge_distance = ((lat - center_lat)**2 + (lon - center_lon)**2)**0.5
        self.edge_exposure_factor = min(1.0, self.edge_distance * 10.0)  # 0 (center) to 1 (edge)

    def receive_community_signals(self, signals):
        """
        Receive signals from Community Level (downward flow).

        Args:
            signals: Dict with market/policy signals and social norms
        """
        self.community_signals = signals

    def step(self):
        """One decision step - choose crop OR continue PV leasing."""
        year = self.model.current_year

        # If farmer has switched to PV, they don't farm anymore
        if self.has_pv_installation:
            # Just receive lease income, no farming
            self.current_crop = None
            self.expected_yield = 0.0
            self.actual_yield = 0.0
            self.annual_income = self.pv_lease_income

            # Track PV income in history (for adaptation capacity)
            self.income_history.append(self.pv_lease_income)

            # Still track resilience (economic resilience through PV income)
            self.track_resilience_over_time()
            return

        # Otherwise, continue with normal farming decisions
        # Get dynamic data for current year
        temperature = self.model.get_meteo(self.lat, self.lon, 'temperature', year)
        precipitation = self.model.get_meteo(self.lat, self.lon, 'precipitation', year)
        solar_radiation = self.model.get_meteo(self.lat, self.lon, 'solar_radiation', year)

        # CCA: Assess climate vulnerability
        vulnerability = self.assess_climate_vulnerability(temperature, precipitation)

        # CCA: Update adaptation capacity based on economic/social factors
        self.update_adaptation_capacity()

        # Get crop suitability scores (including expected yield)
        crop_scores = {}
        crop_expected_yields = {}  # Store expected yields for each crop

        # If focus_crop is set (e.g., "simulate maize yield"), lock farmers to that crop
        # This ensures we track the SPECIFIC crop's performance under climate change
        crops_to_evaluate = [self.model.focus_crop] if hasattr(self.model, 'focus_crop') and self.model.focus_crop else self.model.crops

        for crop in crops_to_evaluate:
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

            crop_scores[crop] = adjusted_score

        # CCA: Make resilient crop decision (incorporates vulnerability & adaptation capacity)
        # If focus_crop set, this will only have one option (the focus crop)
        self.current_crop = self.make_resilient_crop_decision(crop_scores, vulnerability)
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

        # CCA: Track resilience over time for analysis
        self.track_resilience_over_time()

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

        # Costs vary by farm size (economies of scale)
        # Smaller farms have higher per-hectare costs
        size_efficiency = min(1.0, self.land_hectares / 12.0)  # 12ha = full efficiency
        base_cost_per_ha = 100.0 if self.current_crop == "WHEAT" else 150.0  # Maize costs more
        cost_per_hectare = base_cost_per_ha * (1.3 - 0.3 * size_efficiency)  # 30% cost reduction at scale
        total_costs = cost_per_hectare * self.land_hectares

        # Net income
        self.annual_income = revenue + subsidy_amount - total_costs

        # Track income history for adaptation capacity calculation
        self.income_history.append(self.annual_income)

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

    # ==================== CLIMATE RESILIENCE FEATURES (CCA) ====================

    def assess_climate_vulnerability(self, temperature: float, precipitation: float):
        """
        Assess farmer's vulnerability to climate risks.

        Vulnerability = f(exposure, sensitivity, lack of adaptive capacity)
        Now includes: spatial variation, temporal trends, farmer-specific factors

        Args:
            temperature: Current temperature (Celsius)
            precipitation: Current precipitation (mm)

        Returns:
            Dict with vulnerability metrics
        """
        # TEMPORAL TREND: Climate change increases hazard exposure over time
        # RCP scenarios show increasing extremes
        years_elapsed = self.model.current_year - 2020  # Years since baseline
        scenario = self.model.scenario.lower()

        # Climate change amplification factor (increases over time)
        if 'rcp26' in scenario:
            temporal_amplification = 1.0 + (years_elapsed * 0.01)  # +1% per year
        elif 'rcp45' in scenario:
            temporal_amplification = 1.0 + (years_elapsed * 0.02)  # +2% per year
        elif 'rcp85' in scenario:
            temporal_amplification = 1.0 + (years_elapsed * 0.035)  # +3.5% per year
        else:
            temporal_amplification = 1.0

        # EXPOSURE to climate hazards (amplified by climate change over time)
        # Drought exposure (low precipitation)
        base_drought = 1.0 if precipitation < 1.0 else max(0, 1.0 - (precipitation / 3.0))
        drought_exposure = min(1.0, base_drought * temporal_amplification)

        # Add spatial variation: Higher elevation = more drought risk
        if self.elevation_risk_factor > 0:
            drought_exposure = min(1.0, drought_exposure * (1.0 + self.elevation_risk_factor * 0.3))

        # Heatwave exposure (high temperature)
        base_heatwave = 1.0 if temperature > 30 else max(0, (temperature - 20) / 10.0)
        heatwave_exposure = min(1.0, base_heatwave * temporal_amplification)

        # Edge farmers more exposed to extreme heat
        heatwave_exposure = min(1.0, heatwave_exposure * (1.0 + self.edge_exposure_factor * 0.2))

        # Flood exposure (excessive precipitation)
        flood_exposure = 1.0 if precipitation > 10.0 else max(0, (precipitation - 5.0) / 5.0)

        # Lower elevation = higher flood risk
        if self.elevation_risk_factor < 0:
            flood_exposure = min(1.0, flood_exposure * (1.0 - self.elevation_risk_factor * 0.4))

        # SENSITIVITY (depends on crop choice, soil, farm size)
        # Crop sensitivity to climate stress
        if self.current_crop == "WHEAT":
            crop_sensitivity = 0.8  # Wheat more drought-sensitive
        elif self.current_crop == "MAIZE":
            crop_sensitivity = 0.6  # Maize more heat-resistant
        else:
            crop_sensitivity = 0.7  # Default if no crop yet

        # Soil quality sensitivity (poor soil = high sensitivity)
        soil_sensitivity = max(0, 1.0 - (self.soil_organic_carbon / 20.0))

        # Farm size sensitivity (smaller farms = more vulnerable)
        # Small farms (5ha) = high sensitivity (0.8), Large farms (20ha) = low sensitivity (0.3)
        farm_size_sensitivity = max(0.3, 1.0 - (self.land_hectares - 5.0) / 15.0)

        # Economic sensitivity (poor economic performance = high sensitivity)
        if len(self.income_history) > 0:
            avg_income = sum(self.income_history) / len(self.income_history)
            income_stability = 1.0 - min(1.0, avg_income / 5000.0)  # Normalize by 5k euros
        else:
            income_stability = 0.5  # No history yet

        # Calculate overall scores
        exposure_score = (drought_exposure * 0.4 + heatwave_exposure * 0.4 + flood_exposure * 0.2)
        sensitivity_score = (
            crop_sensitivity * 0.3 +
            soil_sensitivity * 0.2 +
            farm_size_sensitivity * 0.3 +
            income_stability * 0.2
        )
        adaptive_capacity_deficit = 1.0 - self.adaptation_capacity

        # FINAL VULNERABILITY (weighted combination)
        # Exposure matters most (climate hazards), then adaptive capacity, then sensitivity
        vulnerability = (
            exposure_score * 0.45 +           # Climate hazards
            adaptive_capacity_deficit * 0.35 + # Ability to respond
            sensitivity_score * 0.20           # Intrinsic sensitivity
        )

        self.vulnerability_score = min(1.0, max(0.0, vulnerability))

        # Store detailed risk exposure
        self.climate_risk_exposure = {
            'drought': drought_exposure,
            'heatwave': heatwave_exposure,
            'flood': flood_exposure,
            'temporal_amplification': temporal_amplification
        }

        return {
            'vulnerability': self.vulnerability_score,
            'exposure': exposure_score,
            'sensitivity': sensitivity_score,
            'adaptive_capacity': self.adaptation_capacity,
            'risk_exposure': self.climate_risk_exposure
        }

    def update_adaptation_capacity(self):
        """
        Update farmer's adaptation capacity based on economic and social factors.

        Adaptation capacity = f(economic resources, social capital, knowledge/experience, farm assets)
        Now uses actual income history and farm characteristics.
        """
        # Economic dimension (income stability and level)
        if len(self.income_history) >= 3:
            # Use 3-year average for stability
            recent_income = sum(self.income_history[-3:]) / 3.0
            # Income variability (coefficient of variation)
            avg_income = sum(self.income_history) / len(self.income_history)
            if avg_income > 0:
                income_std = (sum((x - avg_income)**2 for x in self.income_history) / len(self.income_history))**0.5
                income_stability = 1.0 - min(1.0, income_std / avg_income)  # Lower CV = higher stability
            else:
                income_stability = 0.0
            # Combine level and stability
            economic_capacity = 0.6 * min(1.0, recent_income / 8000.0) + 0.4 * income_stability
        elif len(self.income_history) > 0:
            # Early years: just use income level
            recent_income = self.income_history[-1]
            economic_capacity = min(1.0, max(0.0, recent_income / 8000.0))
        else:
            # No history: use current income
            economic_capacity = min(1.0, max(0.0, self.annual_income / 8000.0))

        # Asset dimension (farm size = productive capacity)
        # Larger farms have more buffer capacity
        asset_capacity = min(1.0, self.land_hectares / 15.0)  # 15ha = full asset capacity

        # Social dimension (collective membership strength)
        social_capacity = 0.7 if self.collective else 0.3

        # Knowledge dimension (experience = years farmed)
        years_experience = self.model.current_year - 2020
        knowledge_capacity = min(1.0, years_experience / 20.0)  # 20 years to full experience

        # Overall adaptation capacity (weighted average)
        # Economic resources matter most, then assets, then social/knowledge
        self.adaptation_capacity = (
            economic_capacity * 0.35 +
            asset_capacity * 0.25 +
            social_capacity * 0.20 +
            knowledge_capacity * 0.20
        )

        return self.adaptation_capacity

    def make_resilient_crop_decision(self, crop_scores: dict, vulnerability_assessment: dict) -> str:
        """
        Make crop decision incorporating climate resilience.

        Adjusts crop scores based on vulnerability and adaptation capacity.

        Args:
            crop_scores: Dict of crop -> base suitability score
            vulnerability_assessment: From assess_climate_vulnerability()

        Returns:
            Selected crop (string)
        """
        adjusted_scores = crop_scores.copy()

        # Risk aversion factor (higher vulnerability = more conservative)
        risk_aversion = self.vulnerability_score * 0.5

        # If highly vulnerable, prefer more resilient crops
        if self.vulnerability_score > 0.7:
            # Maize slightly more drought-resistant than wheat
            if "MAIZE" in adjusted_scores:
                adjusted_scores["MAIZE"] *= (1.0 + risk_aversion * 0.2)

        # If good adaptation capacity, willing to take more risks
        if self.adaptation_capacity > 0.7:
            # Can afford to optimize for economic return
            pass  # Keep original scores

        # If poor adaptation capacity, strongly prefer safe options
        elif self.adaptation_capacity < 0.3:
            # Penalize risky crops
            max_score = max(adjusted_scores.values())
            for crop in adjusted_scores:
                if adjusted_scores[crop] < max_score * 0.8:
                    adjusted_scores[crop] *= 0.5  # Strong penalty for lower-ranked crops

        return max(adjusted_scores, key=adjusted_scores.get)

    def track_resilience_over_time(self):
        """Track resilience metrics over time for analysis."""
        self.resilience_history.append({
            'year': self.model.current_year,
            'vulnerability': self.vulnerability_score,
            'adaptation_capacity': self.adaptation_capacity,
            'income': self.annual_income,
            'crop': self.current_crop,
            'risks': self.climate_risk_exposure.copy()
        })

    def _estimate_potential_farming_income(self) -> float:
        """
        Estimate potential farming income if farmer continues farming.

        Used for comparing against PV offers when farmer hasn't farmed yet.

        Returns:
            Estimated annual farming income (€/year)
        """
        year = self.model.current_year

        # Get environmental data
        temperature = self.model.get_meteo(self.lat, self.lon, 'temperature', year)
        precipitation = self.model.get_meteo(self.lat, self.lon, 'precipitation', year)

        # Evaluate all crops and find best expected income
        best_income = 0.0

        for crop in self.model.crops:
            # Get expected yield
            expected_yield = self.model.get_expected_yield(crop, year)

            # Apply simple environmental adjustment
            adjusted_yield = expected_yield
            if precipitation < 1.5:  # Drought
                adjusted_yield *= 0.85
            if temperature > 25 and crop == "WHEAT":  # Heat stress for wheat
                adjusted_yield *= 0.85

            # Get market price
            market_signals = self.community_signals.get('market_signals', {})
            crop_prices = market_signals.get('crop_prices', {})
            price = crop_prices.get(crop, 100.0)

            # Calculate revenue
            revenue = price * adjusted_yield * self.land_hectares

            # Get subsidy
            policy_signals = self.community_signals.get('policy_signals', {})
            subsidies = policy_signals.get('subsidies', {})
            subsidy_rate = subsidies.get(crop, 0.0)
            subsidy_amount = revenue * subsidy_rate

            # Calculate costs (lowered to make farming viable)
            cost_per_hectare = 150.0 if crop == "MAIZE" else 100.0
            total_costs = cost_per_hectare * self.land_hectares

            # Net income
            net_income = revenue + subsidy_amount - total_costs

            if net_income > best_income:
                best_income = net_income

        return best_income

    def evaluate_pv_offer(self, pv_offer: dict) -> bool:
        """
        Evaluate PV installation offer from developer.

        Farmer decides: continue farming OR accept PV installation
        Decision based on:
        - Projected farming income vs PV lease income
        - Climate vulnerability (high vulnerability = more likely to accept)
        - Risk aversion (from community signals)

        Args:
            pv_offer: Dict with:
                - 'annual_lease_payment': Annual lease payment (€/year)
                - 'capacity_kw': PV installation capacity (kW)
                - 'installation_cost': Total installation cost (€)
                - 'roi': Expected ROI for developer (%)
                - 'pv_developer_id': ID of PV developer making offer

        Returns:
            True if farmer accepts offer (accepts PV installation), False otherwise
        """
        annual_lease_payment = pv_offer['annual_lease_payment']

        # Estimate potential farming income (what farmer WOULD earn if they farm)
        # Use actual income if already farming, otherwise project it
        if self.annual_income > 0:
            projected_farming_income = self.annual_income
        else:
            projected_farming_income = self._estimate_potential_farming_income()

        # Base decision: Compare PV lease income vs farming income
        # PV must be significantly better to justify switching
        if projected_farming_income <= 0:
            # If farming would lose money, PV is very attractive
            income_ratio = 10.0
        else:
            income_ratio = annual_lease_payment / projected_farming_income

        # Farmers value farming lifestyle/tradition - PV must offer competitive income
        # Base threshold: PV must pay equal or better income than farming
        base_threshold = 1.0  # PV must pay 100% of farming income

        # Vulnerability factor: High vulnerability makes PV more attractive
        # Reduces threshold by up to 30%
        vulnerability_reduction = self.vulnerability_score * 0.3

        # Risk aversion: Higher risk aversion = prefer stable PV income
        # Reduces threshold by up to 20%
        social_norms = self.community_signals.get('social_norms', {})
        risk_aversion = social_norms.get('risk_aversion', 0.5)
        risk_aversion_reduction = risk_aversion * 0.2

        # Calculate acceptance threshold (0.5 to 1.0 range)
        # Base 1.0, reduced by up to 0.5 total → range [0.5, 1.0]
        acceptance_threshold = base_threshold - vulnerability_reduction - risk_aversion_reduction

        # Add randomness (farmer heterogeneity in preferences)
        import random
        random_factor = random.uniform(0.85, 1.15)  # ±15% variation

        return income_ratio * random_factor >= acceptance_threshold

    def accept_pv_installation(self, pv_offer: dict):
        """
        Accept PV installation offer - switch from farming to PV leasing.

        Args:
            pv_offer: Dict with PV offer details
        """
        self.has_pv_installation = True
        self.pv_lease_income = pv_offer['annual_lease_payment']
        self.pv_installation_year = self.model.current_year

        # Stop farming
        self.current_crop = None
        self.expected_yield = 0.0
        self.actual_yield = 0.0
        self.annual_income = self.pv_lease_income

    def get_resilience_report(self) -> dict:
        """
        Generate resilience report for analysis.

        Returns:
            Dict with resilience metrics
        """
        return {
            'farmer_id': self.unique_id,
            'vulnerability': self.vulnerability_score,
            'adaptation_capacity': self.adaptation_capacity,
            'risk_exposure': self.climate_risk_exposure,
            'current_crop': self.current_crop,
            'income': self.annual_income,
            'resilience_trend': len(self.resilience_history)
        }

    def __repr__(self):
        return f"Farmer({self.unique_id}, crop={self.current_crop}, lat={self.lat:.2f}, lon={self.lon:.2f})"
