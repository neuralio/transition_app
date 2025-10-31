"""
LandOwner Agent for Green Credit Policy (GCP) Simulation
========================================================

Individual-level agent representing a farmer or landowner who decides
whether to adopt solar PV installations based on:
- Financial incentives (green credit policies)
- Energy savings
- Social influences (peer adoption, community norms)
- Financial capacity and risk tolerance
- Loan availability from financial institutions
"""

import mesa
import numpy as np
from typing import Dict, Optional


class LandOwnerAgent(mesa.Agent):
    """
    A landowner deciding whether to adopt PV based on multiple factors.

    Decision factors:
    - Financial: Green credit subsidies, low-interest loans, tax incentives
    - Economic: Expected ROI, energy savings, electricity prices
    - Social: Peer adoption rates, collective norms
    - Personal: Financial situation, risk tolerance
    - Environmental: Solar potential, land characteristics
    """

    def __init__(
        self,
        model,
        lat: float,
        lon: float,
        financial_situation: str = 'moderate',
        risk_tolerance: str = 'moderate',
        land_hectares: float = 10.0,
        initial_crop: str = None  # NEW (2025-10-21): Initial land use before potential PV adoption
    ):
        """
        Initialize landowner agent.

        Parameters
        ----------
        model : GCPModel
            Mesa model instance
        lat : float
            Latitude of landowner's property
        lon : float
            Longitude of landowner's property
        financial_situation : str
            'poor', 'moderate', or 'wealthy'
        risk_tolerance : str
            'low', 'moderate', or 'high'
        land_hectares : float
            Size of land parcel in hectares
        initial_crop : str, optional
            Initial crop/land use (e.g., 'WHEAT', 'MAIZE') before PV adoption (NEW - 2025-10-21)
        """
        super().__init__(model)
        self.lat = lat
        self.lon = lon
        self.land_hectares = land_hectares

        # Personal characteristics
        self.financial_situation = financial_situation
        self.risk_tolerance = risk_tolerance

        # Land use state (NEW - 2025-10-21)
        self.initial_crop = initial_crop  # What was on the land before PV
        self.current_land_use = initial_crop if initial_crop else None  # Current use (crop or PV)

        # PV adoption state
        self.has_pv = False  # Whether PV is installed
        self.pv_capacity_kw = 0.0  # PV system size (kW)
        self.pv_installation_year = None  # Year PV was installed
        self.pv_age = 0  # Years since installation
        self.pv_decommissioned = False  # Whether PV was removed/abandoned
        self.decommission_year = None  # Year PV was decommissioned
        self.decommission_reason = None  # Reason for decommissioning
        self.consecutive_loss_years = 0  # Track consecutive years of losses

        # Financial state
        self.loan_approved = False  # Whether financial institution approved loan
        self.loan_amount = 0.0  # Loan amount (euros)
        self.loan_interest_rate = 0.0  # Interest rate
        self.loan_term = 0  # Loan duration (years)
        self.annual_loan_payment = 0.0  # Annual payment (euros)

        # Economic state
        self.installation_cost = 0.0  # Total PV installation cost
        self.subsidy_amount = 0.0  # Government subsidy received
        self.annual_energy_savings = 0.0  # Annual electricity savings
        self.annual_feed_in_revenue = 0.0  # Revenue from selling surplus electricity
        self.annual_profit = 0.0  # Net annual profit (savings + revenue - loan payment - maintenance)
        self.cumulative_profit = 0.0  # Cumulative profit since installation
        self.roi = 0.0  # Return on investment (%)
        self.payback_period = 0.0  # Years to break even

        # Multi-level interaction
        self.collective = None  # Link to CollectiveAgent
        self.financial_institution = None  # Link to FinancialInstitutionAgent
        self.community_signals = {}  # Signals from community level
        self.policy_signals = {}  # Signals from policy level

        # Spatial interaction
        self.spatial_neighbors = []  # Nearby landowners
        self.neighbor_influence_radius = 50.0  # km

        # Environmental data
        self.solar_potential = model.get_solar_potential(lat, lon)  # kWh/m²/year
        self.elevation = model.get_elevation(lat, lon)
        self.land_slope = self._estimate_slope()  # Derived from elevation

        # Geographic classification (GCP-07 compliance: rural vs urban filtering)
        self.area_type = self._classify_area_type()  # 'urban' or 'rural'

    def _estimate_slope(self) -> float:
        """
        Estimate land slope from elevation.

        Returns
        -------
        float
            Slope in degrees (0-90)
        """
        # TODO: Calculate actual slope from DEM data
        # For now, assume relatively flat land suitable for PV
        return np.random.uniform(0, 15)  # 0-15 degrees

    def _classify_area_type(self) -> str:
        """
        Classify landowner location as urban or rural based on population density.

        Uses EU classification: >300 people/km² = urban

        Returns
        -------
        str
            'urban' or 'rural'
        """
        try:
            # Get population density from model (people/km²)
            pop_density = self.model.get_population_density(self.lat, self.lon)

            # EU urban/rural classification threshold
            # >300 people/km² = urban
            # ≤300 people/km² = rural
            return 'urban' if pop_density > 300 else 'rural'
        except Exception:
            # If population density data unavailable, classify based on distance from center
            # Thessaloniki center: ~40.64°N, 22.94°E
            center_lat, center_lon = 40.64, 22.94
            distance_from_center = np.sqrt(
                (self.lat - center_lat)**2 + (self.lon - center_lon)**2
            ) * 111  # Convert degrees to km (approximate)

            # Within 15km of center = urban, beyond = rural
            return 'urban' if distance_from_center < 15 else 'rural'

    def receive_community_signals(self, signals: Dict):
        """
        Receive signals from Community Level (downward flow).

        Parameters
        ----------
        signals : dict
            Market/policy signals and social norms from collective
        """
        self.community_signals = signals

    def receive_policy_signals(self, signals: Dict):
        """
        Receive signals from Policy Level (downward flow).

        Parameters
        ----------
        signals : dict
            Green credit policy parameters (subsidies, loans, tax incentives)
        """
        self.policy_signals = signals

    def step(self):
        """
        One decision step - decide whether to adopt PV.

        Decision logic:
        1. If already has PV: calculate performance and profits
        2. If no PV: evaluate adoption decision based on all factors
        """
        year = self.model.current_year + self.model.start_year  # Actual calendar year

        # Update spatial neighbors
        self.spatial_neighbors = self.model.get_spatial_neighbors(
            self,
            radius_km=self.neighbor_influence_radius
        )

        if self.has_pv:
            # Already has PV: calculate ongoing performance
            self._update_pv_performance(year)

            # Evaluate if PV should be decommissioned
            self._evaluate_decommissioning(year)
        else:
            # No PV yet: evaluate adoption decision
            self._evaluate_pv_adoption(year)

    def _evaluate_pv_adoption(self, year: int):
        """
        Evaluate whether to adopt PV this year.

        Decision based on:
        - Financial attractiveness (ROI, payback period)
        - Green credit policy incentives
        - Social influence from neighbors/collective
        - Personal characteristics (financial situation, risk tolerance)
        - Loan availability from financial institution

        Parameters
        ----------
        year : int
            Current simulation year
        """
        # Calculate expected PV system size based on land area
        # Typical: 1 hectare can accommodate ~100 kW of PV
        max_pv_capacity = self.land_hectares * 10.0  # More conservative: 10 kW/hectare
        self.pv_capacity_kw = min(
            max_pv_capacity,
            self.model.config['solar_pv']['capacity_kw']
        )

        # Calculate installation cost
        cost_per_kw = self.model.config['solar_pv']['installation_cost_per_kw']
        self.installation_cost = self.pv_capacity_kw * cost_per_kw

        # Calculate subsidy amount
        subsidy_rate = self.policy_signals.get('pv_subsidy_rate', 0.0)
        self.subsidy_amount = self.installation_cost * subsidy_rate

        # Net cost after subsidy
        net_cost = self.installation_cost - self.subsidy_amount

        # ✅ FIX: Calculate attractiveness FIRST (before requesting loan)
        # This prevents "ghost loans" where loans are approved but never used

        # Calculate financial attractiveness (preliminary - assumes loan if needed)
        # Set loan parameters tentatively for financial calculations
        needs_loan = self._needs_loan(net_cost)
        if needs_loan:
            # Calculate tentative loan parameters for attractiveness calculation
            capacity_map = {'poor': 0.2, 'moderate': 0.5, 'wealthy': 1.0}
            capacity_ratio = capacity_map[self.financial_situation]
            available_capital = net_cost * capacity_ratio
            self.loan_amount = max(0, net_cost - available_capital)
            self.loan_interest_rate = self.policy_signals.get('low_interest_loan_rate', 0.05)
            self.loan_term = min(20, self.model.config['solar_pv']['project_lifetime'])
            self.annual_loan_payment = self._calculate_loan_payment(
                principal=self.loan_amount,
                rate=self.loan_interest_rate,
                term=self.loan_term
            )
        else:
            self.loan_amount = 0.0
            self.annual_loan_payment = 0.0

        # Calculate financial attractiveness
        financial_score = self._calculate_financial_attractiveness()

        # Calculate social influence
        social_score = self._calculate_social_influence()

        # Calculate risk-adjusted score
        risk_adjusted_score = self._calculate_risk_adjusted_score(
            financial_score,
            social_score
        )

        # Decision threshold - calibrated to create policy differentiation
        # In real-world scenarios, farmers adopt with moderate-to-high confidence
        # This threshold balances financial attractiveness vs social proof
        # Fine-tuned to achieve gradual S-curve adoption across full 10-year period
        adoption_threshold = 0.515  # Need 51.5% confidence (calibrated for steady 10-year growth)

        # ✅ FIX: Only request loan if decision passes
        if risk_adjusted_score >= adoption_threshold:
            # Decision is YES - now secure financing if needed
            if needs_loan:
                # Request loan from financial institution
                self._request_loan(net_cost, year)

                if not self.loan_approved:
                    # Loan denied - cannot proceed with PV installation
                    return

            # Financing secured (or not needed) - Adopt PV!
            self._install_pv(year)

    def _needs_loan(self, net_cost: float) -> bool:
        """
        Determine if landowner needs a loan.

        Parameters
        ----------
        net_cost : float
            Net installation cost after subsidies (euros)

        Returns
        -------
        bool
            True if loan is needed
        """
        # Financial capacity based on financial situation
        capacity_map = {
            'poor': 0.2,      # Can afford 20% upfront
            'moderate': 0.5,  # Can afford 50% upfront
            'wealthy': 1.0    # Can afford 100% upfront
        }
        capacity_ratio = capacity_map[self.financial_situation]

        available_capital = net_cost * capacity_ratio
        return available_capital < net_cost

    def _request_loan(self, net_cost: float, year: int):
        """
        Request loan from financial institution.

        Parameters
        ----------
        net_cost : float
            Net installation cost after subsidies (euros)
        year : int
            Current year
        """
        # Capacity to pay upfront
        capacity_map = {
            'poor': 0.2,
            'moderate': 0.5,
            'wealthy': 1.0
        }
        capacity_ratio = capacity_map[self.financial_situation]
        available_capital = net_cost * capacity_ratio

        # Loan amount needed
        self.loan_amount = max(0, net_cost - available_capital)

        # Get loan interest rate from policy
        self.loan_interest_rate = self.policy_signals.get(
            'low_interest_loan_rate',
            0.05  # Default 5%
        )

        # Loan term (years)
        self.loan_term = min(20, self.model.config['solar_pv']['project_lifetime'])

        # Request loan from financial institution
        if self.financial_institution:
            self.loan_approved = self.financial_institution.evaluate_loan_application(
                agent=self,
                loan_amount=self.loan_amount,
                interest_rate=self.loan_interest_rate,
                term=self.loan_term,
                year=year
            )

            if self.loan_approved:
                # Calculate annual loan payment (amortization)
                self.annual_loan_payment = self._calculate_loan_payment(
                    principal=self.loan_amount,
                    rate=self.loan_interest_rate,
                    term=self.loan_term
                )
        else:
            # No financial institution - assume loan is approved
            self.loan_approved = True
            self.annual_loan_payment = self._calculate_loan_payment(
                principal=self.loan_amount,
                rate=self.loan_interest_rate,
                term=self.loan_term
            )

    def _calculate_loan_payment(
        self,
        principal: float,
        rate: float,
        term: int
    ) -> float:
        """
        Calculate annual loan payment using amortization formula.

        Parameters
        ----------
        principal : float
            Loan principal (euros)
        rate : float
            Annual interest rate (0-1)
        term : int
            Loan term (years)

        Returns
        -------
        float
            Annual payment (euros)
        """
        if principal == 0 or term == 0:
            return 0.0

        if rate == 0:
            return principal / term

        # Amortization formula: PMT = P * (r(1+r)^n) / ((1+r)^n - 1)
        monthly_rate = rate / 12
        n_payments = term * 12
        monthly_payment = principal * (
            monthly_rate * (1 + monthly_rate) ** n_payments
        ) / (
            (1 + monthly_rate) ** n_payments - 1
        )

        return monthly_payment * 12  # Annual payment

    def _calculate_financial_attractiveness(self) -> float:
        """
        Calculate financial attractiveness of PV adoption.

        Returns
        -------
        float
            Financial score (0-1)
        """
        # Calculate expected annual energy production
        panel_efficiency = self.model.config['solar_pv']['efficiency']
        degradation_rate = self.model.config['solar_pv']['degradation_rate']

        # Realistic energy production calculation for Greece
        # Solar potential represents kWh/m²/year (e.g., 1800 for Greece)
        # Convert to full-load hours: solar_potential_kWh/m²/year ≈ annual equivalent hours
        # For Greece: ~1600-1800 full-load equivalent hours per year
        full_load_hours = self.solar_potential / 1.1  # Normalize (typical 1800/1.1 ≈ 1636 hours)

        # Annual energy production: capacity × full-load hours × panel efficiency adjustment
        annual_energy_kwh = self.pv_capacity_kw * full_load_hours

        # Annual energy savings (self-consumption)
        electricity_price = self.model.config['solar_pv']['electricity_price']
        self.annual_energy_savings = annual_energy_kwh * 0.7 * electricity_price  # 70% self-consumption

        # Annual feed-in revenue (surplus electricity)
        feed_in_tariff = self.model.config['solar_pv']['feed_in_tariff']
        self.annual_feed_in_revenue = annual_energy_kwh * 0.3 * feed_in_tariff  # 30% sold to grid

        # Annual maintenance cost
        maintenance_cost = self.model.config['solar_pv']['maintenance_cost_annual']

        # Annual profit
        self.annual_profit = (
            self.annual_energy_savings +
            self.annual_feed_in_revenue -
            self.annual_loan_payment -
            maintenance_cost
        )

        # Calculate ROI
        total_investment = self.installation_cost - self.subsidy_amount
        if total_investment > 0:
            self.roi = (self.annual_profit / total_investment) * 100  # Percentage

        # Calculate payback period
        if self.annual_profit > 0:
            self.payback_period = total_investment / self.annual_profit
        else:
            self.payback_period = 999  # Never pays back

        # Financial attractiveness score
        # Based on ROI and payback period
        roi_score = min(1.0, self.roi / 10.0)  # 10% ROI = full score
        payback_score = max(0.0, 1.0 - (self.payback_period / 25))  # < 25 years is good

        financial_score = (roi_score * 0.6) + (payback_score * 0.4)

        return max(0.0, min(1.0, financial_score))

    def _calculate_social_influence(self) -> float:
        """
        Calculate social influence from neighbors and collective.

        Returns
        -------
        float
            Social influence score (0-1)
        """
        if not self.spatial_neighbors:
            return 0.5  # Neutral if no neighbors

        # Count neighbors with PV
        neighbors_with_pv = sum(
            1 for neighbor in self.spatial_neighbors
            if isinstance(neighbor, LandOwnerAgent) and neighbor.has_pv
        )

        total_neighbors = len([
            n for n in self.spatial_neighbors
            if isinstance(n, LandOwnerAgent)
        ])

        if total_neighbors == 0:
            peer_adoption_rate = 0.3  # Conservative baseline (lack of proven success)
        else:
            # IMPORTANT: Start with conservative baseline (0.3) when no peers have adopted
            # Represents "lack of proven success" - need to see peers succeed first
            # As adoption grows, peer_adoption_rate increases gradually to allow late adoption
            # Formula: baseline + (adoption_rate × scale_factor)
            # Example: 0% adopted → 0.3, 50% adopted → 0.575, 70% adopted → 0.685, 100% adopted → 0.85
            # Scale factor 0.55 balances early restraint with late-adopter inclusion
            peer_adoption_rate = 0.3 + (neighbors_with_pv / total_neighbors) * 0.55

        # Social influence: bandwagon effect
        # Higher adoption rate = more pressure to adopt
        social_score = peer_adoption_rate

        # Collective influence
        if self.community_signals:
            collective_pressure = self.community_signals.get('collective_pressure', 0.0)
            social_score = (social_score * 0.7) + (collective_pressure * 0.3)

        return social_score

    def _calculate_risk_adjusted_score(
        self,
        financial_score: float,
        social_score: float
    ) -> float:
        """
        Calculate risk-adjusted adoption score.

        Parameters
        ----------
        financial_score : float
            Financial attractiveness (0-1)
        social_score : float
            Social influence (0-1)

        Returns
        -------
        float
            Risk-adjusted score (0-1)
        """
        # Weight financial and social factors
        financial_weight = self.model.config['landowners']['decision']['financial_weight']
        social_weight = self.model.config['landowners']['decision']['social_weight']

        base_score = (
            financial_score * financial_weight +
            social_score * social_weight
        )

        # Add direct subsidy signal effect (policy legitimacy/awareness)
        # Higher subsidies = government endorsement = increased confidence
        # This represents the "policy signal" beyond pure financial ROI
        subsidy_rate = self.policy_signals.get('pv_subsidy_rate', 0.0)
        subsidy_bonus = subsidy_rate * 0.35  # Up to 10.5% bonus at 30% subsidy
        base_score += subsidy_bonus

        # Add technology maturity bonus (proven technology over time)
        # As more years pass and PV installations succeed, perceived risk decreases
        # This represents learning effects and reduced uncertainty
        years_since_start = self.model.current_year
        maturity_bonus = min(0.025, years_since_start * 0.0025)  # Up to 2.5% bonus after 10 years
        base_score += maturity_bonus

        # Adjust for risk tolerance
        # Risk-averse farmers require significantly more confidence to adopt new technology
        # Risk-seeking farmers are more willing to adopt with lower confidence
        risk_adjustment_map = {
            'low': 0.85,     # Risk-averse: require 15% higher confidence (penalized significantly)
            'moderate': 1.0, # Moderate: no adjustment
            'high': 1.15     # Risk-seeking: willing to adopt with 15% lower confidence (encouraged)
        }
        risk_adjustment = risk_adjustment_map[self.risk_tolerance]

        risk_adjusted_score = base_score * risk_adjustment

        return max(0.0, min(1.0, risk_adjusted_score))

    def _install_pv(self, year: int):
        """
        Install PV system.

        Parameters
        ----------
        year : int
            Installation year
        """
        self.has_pv = True
        self.pv_installation_year = year
        self.pv_age = 0
        self.cumulative_profit = 0.0

        # Record installation and subsidy disbursement in model data collector
        self.model.record_pv_installation(
            agent_id=self.unique_id,
            year=year,
            capacity_kw=self.pv_capacity_kw,
            lat=self.lat,
            lon=self.lon,
            subsidy_amount=self.subsidy_amount  # ✅ FIX: Report subsidy spending
        )

    def _update_pv_performance(self, year: int):
        """
        Update PV performance for existing installation.

        Parameters
        ----------
        year : int
            Current year
        """
        self.pv_age = year - self.pv_installation_year

        # Apply degradation
        degradation_rate = self.model.config['solar_pv']['degradation_rate']
        performance_factor = (1 - degradation_rate) ** self.pv_age

        # Update annual performance (same calculation as initial)
        full_load_hours = self.solar_potential / 1.1  # Normalize to full-load equivalent hours
        annual_energy_kwh = self.pv_capacity_kw * full_load_hours * performance_factor

        # Update economics
        electricity_price = self.model.config['solar_pv']['electricity_price']
        feed_in_tariff = self.model.config['solar_pv']['feed_in_tariff']
        maintenance_cost = self.model.config['solar_pv']['maintenance_cost_annual']

        self.annual_energy_savings = annual_energy_kwh * 0.7 * electricity_price
        self.annual_feed_in_revenue = annual_energy_kwh * 0.3 * feed_in_tariff

        # Check if loan is still being paid
        years_since_installation = self.pv_age
        if years_since_installation < self.loan_term:
            annual_payment = self.annual_loan_payment
        else:
            annual_payment = 0.0  # Loan paid off

        self.annual_profit = (
            self.annual_energy_savings +
            self.annual_feed_in_revenue -
            annual_payment -
            maintenance_cost
        )

        self.cumulative_profit += self.annual_profit

        # Track consecutive loss years for decommissioning logic
        if self.annual_profit < 0:
            self.consecutive_loss_years += 1
        else:
            self.consecutive_loss_years = 0  # Reset counter

    def _evaluate_decommissioning(self, year: int):
        """
        Evaluate whether to decommission/abandon PV installation.

        Decommissioning conditions:
        1. Catastrophic financial failure: cumulative loss exceeds 1.5x installation cost
        2. End of life: PV age exceeds project lifetime AND never profitable
        3. Persistent losses: 5+ consecutive years of negative annual profit

        Parameters
        ----------
        year : int
            Current year
        """
        project_lifetime = self.model.config['solar_pv']['project_lifetime']

        # Condition 1: Catastrophic financial failure
        # If cumulative losses exceed 1.5× installation cost, abandon PV
        if self.cumulative_profit < -1.5 * self.installation_cost:
            self._decommission_pv(year, "catastrophic_financial_failure")
            return

        # Condition 2: End of life without profitability
        # If PV exceeds project lifetime AND never broke even, abandon
        if self.pv_age >= project_lifetime and self.cumulative_profit < 0:
            self._decommission_pv(year, "end_of_life_unprofitable")
            return

        # Condition 3: Persistent losses
        # If 5+ consecutive years of losses, financially struggling farmers abandon
        # Risk-averse farmers abandon earlier (4 years), wealthy farmers persist longer (6 years)
        loss_tolerance_map = {
            'poor': 4,      # Poor farmers abandon after 4 years of losses
            'moderate': 5,  # Moderate farmers abandon after 5 years
            'wealthy': 6    # Wealthy farmers can sustain 6 years of losses
        }
        loss_threshold = loss_tolerance_map.get(self.financial_situation, 5)

        if self.consecutive_loss_years >= loss_threshold:
            self._decommission_pv(year, "persistent_losses")
            return

    def _decommission_pv(self, year: int, reason: str):
        """
        Decommission/remove PV installation.

        Parameters
        ----------
        year : int
            Year of decommissioning
        reason : str
            Reason for decommissioning
        """
        self.has_pv = False
        self.pv_decommissioned = True
        self.decommission_year = year
        self.decommission_reason = reason

        # Reset PV-specific attributes
        self.pv_capacity_kw = 0.0
        self.annual_energy_savings = 0.0
        self.annual_feed_in_revenue = 0.0
        self.annual_profit = 0.0
        # Keep cumulative_profit for historical record of losses
        self.consecutive_loss_years = 0

        # Notify financial institution if loan was outstanding
        if self.financial_institution and self.loan_amount > 0:
            # This would trigger a default in the financial institution
            # The financial institution can track this as a loss
            pass

        # Record decommissioning in model data collector
        if hasattr(self.model, 'record_pv_decommission'):
            self.model.record_pv_decommission(
                agent_id=self.unique_id,
                year=year,
                reason=reason,
                cumulative_loss=abs(min(0, self.cumulative_profit)),
                lat=self.lat,
                lon=self.lon
            )

    def get_economic_state(self) -> Dict:
        """
        Get landowner's economic state for upward information flow.

        Returns
        -------
        dict
            Economic indicators
        """
        return {
            'agent_id': self.unique_id,
            'has_pv': self.has_pv,
            'pv_capacity_kw': self.pv_capacity_kw,
            'pv_age': self.pv_age,
            'annual_profit': self.annual_profit,
            'cumulative_profit': self.cumulative_profit,
            'roi': self.roi,
            'payback_period': self.payback_period,
            'loan_approved': self.loan_approved,
            'loan_amount': self.loan_amount,
            'financial_situation': self.financial_situation,
            'risk_tolerance': self.risk_tolerance,
            'area_type': self.area_type,  # GCP-07 compliance: urban/rural filtering
            'pv_decommissioned': self.pv_decommissioned,
            'decommission_year': self.decommission_year,
            'decommission_reason': self.decommission_reason,
            'consecutive_loss_years': self.consecutive_loss_years
        }

    def __repr__(self):
        pv_status = f"PV:{self.pv_capacity_kw:.1f}kW" if self.has_pv else "No PV"
        return f"LandOwner({self.unique_id}, {pv_status}, lat={self.lat:.2f}, lon={self.lon:.2f})"
