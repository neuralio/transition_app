"""PV Developer Agent - Energy Companies for Solar Installation Decisions."""

import mesa


class PVDeveloperAgent(mesa.Agent):
    """
    Market Level agent representing photovoltaic (PV) energy developers.

    Makes decisions about:
    - Which agricultural land to lease for PV installations
    - ROI calculation with green credits and policy incentives
    - Interaction with farmers for land lease agreements
    - Response to policy incentives and regulations
    """

    def __init__(self,
                 model,
                 company_name: str,
                 investment_capacity: float = 5000000.0):
        """Initialize PV developer agent.

        Args:
            model: Mesa model instance
            company_name: Name/ID of the energy company
            investment_capacity: Available capital for PV investments (euros)
        """
        super().__init__(model)
        self.company_name = company_name
        self.investment_capacity = investment_capacity
        self.initial_investment_capacity = investment_capacity  # Store original for reporting

        # Economic parameters
        self.pv_installations = []  # List of (farmer_id, location, capacity_kW, roi, year)
        self.total_capacity_installed = 0.0  # kW
        self.annual_revenue = 0.0  # From electricity sales + green credits
        self.green_credit_rate = 0.0  # Per kWh incentive from policy

        # Technical parameters - Add heterogeneity based on company characteristics
        import random

        # PV installation cost varies by company efficiency/scale
        # Large companies: economies of scale (€550-650/kW)
        # Medium companies: standard costs (€580-680/kW)
        # Small companies: higher costs (€620-720/kW)
        if investment_capacity >= 7000000:  # Large
            self.pv_cost_per_kw = random.uniform(550, 650)
        elif investment_capacity >= 4000000:  # Medium
            self.pv_cost_per_kw = random.uniform(580, 680)
        else:  # Small
            self.pv_cost_per_kw = random.uniform(620, 720)

        # System lifetime varies by technology/quality (20-30 years)
        # Better companies invest in higher quality panels
        if investment_capacity >= 7000000:  # Large
            self.pv_lifetime_years = random.randint(26, 30)
        elif investment_capacity >= 4000000:  # Medium
            self.pv_lifetime_years = random.randint(23, 27)
        else:  # Small
            self.pv_lifetime_years = random.randint(20, 25)

        # Maintenance cost rate varies (1.5%-3.0% per year)
        # Better maintenance = higher reliability but higher cost
        self.maintenance_cost_rate = random.uniform(0.015, 0.03)

        # Land lease payment varies by company strategy (€2,500-4,000/ha/year)
        # Aggressive companies pay more to secure best land
        if investment_capacity >= 7000000:  # Large - can afford premium
            self.land_lease_rate = random.uniform(3200, 4000)
        elif investment_capacity >= 4000000:  # Medium
            self.land_lease_rate = random.uniform(2800, 3500)
        else:  # Small - budget constrained
            self.land_lease_rate = random.uniform(2500, 3200)

        # Installation tracking
        self.farmers_with_pv = set()  # Track which farmers already have PV
        self.farmers_offered_pv = set()  # Track which farmers have been offered (accepted or rejected)
        self.installation_years = []  # Years when installations were made (typically year 1 only)

        # Interaction buffers
        self.policy_incentives = {}  # Green credit rates, subsidies
        self.available_land_offers = []  # From farmers willing to lease

    def evaluate_location_suitability(self, lat: float, lon: float, year: int) -> dict:
        """
        Evaluate PV installation suitability at a location.

        Args:
            lat: Latitude
            lon: Longitude
            year: Year

        Returns:
            Dict with suitability metrics
        """
        # Get solar radiation (key factor for PV)
        solar_radiation = self.model.get_meteo(lat, lon, 'solar_radiation', year)

        # Get elevation (affects installation costs)
        elevation = self.model.get_elevation(lat, lon)

        # Solar radiation is in kWh/m²/day
        # Convert to annual solar energy: kWh/m²/year
        annual_solar_energy = solar_radiation * 365  # kWh/m²/year

        # PV capacity factor calculation
        # Typical values for Greece: 15-22%
        # Formula: CF = (Annual Solar Energy / Peak Sun Hours) × System Efficiency
        # Peak sun hours reference: ~1000 kWh/m²/year at 1 kW/m² = 1000 hours
        # System efficiency including all losses: ~18%
        # CF = (annual_solar_energy / 1000) × 0.18
        # Simplified: CF ≈ annual_solar_energy / 5500

        # Uncapped CF for ROI ranking (to differentiate sites)
        capacity_factor_uncapped = annual_solar_energy / 5500.0

        # Capped CF for actual energy production (technical realism)
        capacity_factor_capped = min(0.25, capacity_factor_uncapped)

        # For Greece with 4-6 kWh/m²/day:
        #   4.0 × 365 = 1,460 kWh/m²/year → CF = 0.265 → capped at 0.25 (25%)
        #   5.0 × 365 = 1,825 kWh/m²/year → CF = 0.332 → capped at 0.25 (25%)

        # Installation difficulty (elevation penalty)
        installation_multiplier = 1.0
        if elevation > 500:
            installation_multiplier = 1.2  # 20% more expensive
        elif elevation > 1000:
            installation_multiplier = 1.5  # 50% more expensive

        return {
            'solar_radiation': solar_radiation,  # kWh/m²/day
            'annual_solar_energy': annual_solar_energy,  # kWh/m²/year
            'capacity_factor': capacity_factor_capped,  # Capped for production
            'capacity_factor_uncapped': capacity_factor_uncapped,  # Uncapped for ranking
            'installation_multiplier': installation_multiplier,
            'elevation': elevation,
            'suitability_score': capacity_factor_capped  # 0-0.25 range
        }

    def calculate_roi(self,
                      land_hectares: float,
                      suitability_metrics: dict,
                      farmer_id: str,
                      skip_budget_check: bool = False) -> dict:
        """
        Calculate Return on Investment for PV installation.

        Args:
            land_hectares: Land area available
            suitability_metrics: From evaluate_location_suitability()
            farmer_id: Farmer offering land

        Returns:
            Dict with ROI analysis
        """
        # PV installation parameters
        # Typical: 1 hectare = ~500-700 kW (assuming ground-mounted solar)
        capacity_kw = land_hectares * 600  # 600 kW per hectare

        # Capital cost
        installation_cost = (
            capacity_kw * self.pv_cost_per_kw *
            suitability_metrics['installation_multiplier']
        )

        # Check if within budget (skip for visualization purposes)
        if not skip_budget_check and installation_cost > self.investment_capacity:
            return {
                'roi': -1.0,
                'ranking_roi': -1.0,
                'feasible': False,
                'capacity_kw': capacity_kw,
                'installation_cost': installation_cost,
                'annual_revenue': 0,
                'annual_cost': 0,
                'net_annual_profit': 0,
                'payback_period': float('inf'),
                'farmer_id': farmer_id,
                'reason': 'insufficient_capital'
            }

        # Annual revenue calculation (using CAPPED CF for realistic production)
        # kWh/year = capacity_kW × capacity_factor × 8760 hours/year
        annual_kwh = capacity_kw * suitability_metrics['capacity_factor'] * 8760

        # Revenue sources
        electricity_price = 0.10  # €/kWh (wholesale)
        electricity_revenue = annual_kwh * electricity_price

        # Green credit revenue (from policy incentives)
        green_credit_revenue = annual_kwh * self.green_credit_rate

        total_annual_revenue = electricity_revenue + green_credit_revenue

        # Annual costs
        maintenance_cost = installation_cost * self.maintenance_cost_rate
        land_lease_cost = land_hectares * self.land_lease_rate
        total_annual_cost = maintenance_cost + land_lease_cost

        # Net annual profit
        net_annual_profit = total_annual_revenue - total_annual_cost

        # Simple payback period (years)
        if net_annual_profit > 0:
            payback_period = installation_cost / net_annual_profit
        else:
            payback_period = float('inf')

        # ROI over lifetime (using capped CF for realistic revenue)
        lifetime_profit = (net_annual_profit * self.pv_lifetime_years) - installation_cost
        roi = lifetime_profit / installation_cost if installation_cost > 0 else 0

        # RANKING ROI: Use uncapped CF to differentiate sites with high solar potential
        # This creates variation even when all sites hit the 25% cap
        if 'capacity_factor_uncapped' in suitability_metrics:
            annual_kwh_uncapped = capacity_kw * suitability_metrics['capacity_factor_uncapped'] * 8760
            revenue_uncapped = annual_kwh_uncapped * electricity_price + annual_kwh_uncapped * self.green_credit_rate
            profit_uncapped = revenue_uncapped - total_annual_cost
            lifetime_profit_uncapped = (profit_uncapped * self.pv_lifetime_years) - installation_cost
            ranking_roi = lifetime_profit_uncapped / installation_cost if installation_cost > 0 else 0
        else:
            ranking_roi = roi  # Fallback if uncapped not available

        # Decision threshold: ROI > 0.5 (50% return over lifetime)
        feasible = roi > 0.5 and payback_period < 10

        return {
            'roi': roi,  # Realistic ROI for reporting
            'ranking_roi': ranking_roi,  # ROI for site ranking (uses uncapped CF)
            'feasible': feasible,
            'capacity_kw': capacity_kw,
            'installation_cost': installation_cost,
            'annual_revenue': total_annual_revenue,
            'annual_cost': total_annual_cost,
            'net_annual_profit': net_annual_profit,
            'payback_period': payback_period,
            'farmer_id': farmer_id
        }

    def perceive_from_policy(self, policy_incentives: dict):
        """
        Receive policy signals (green credits, subsidies).

        Args:
            policy_incentives: Dict with incentive rates
        """
        self.policy_incentives = policy_incentives

        # Update green credit rate
        self.green_credit_rate = policy_incentives.get('pv_green_credit', 0.0)

    def evaluate_all_available_land(self):
        """
        Evaluate all land offers from farmers and make investment decisions.

        Realistic behavior:
        - Only installs in first 1-2 years (market entry period)
        - Evaluates multiple farmers, not just first viable one
        - Tracks which farmers already have installations
        - Responds to solar radiation differences across scenarios

        Returns:
            List of accepted installation proposals
        """
        accepted_proposals = []

        year = self.model.current_year
        start_year = self.model.start_year

        # Realistic constraint: Only install in first year (market entry period)
        # After that, focus on operating existing installations
        years_since_start = year - start_year
        if years_since_start > 0:  # Only install in year 0 (first year)
            return accepted_proposals

        # Track this as an installation year
        if year not in self.installation_years:
            self.installation_years.append(year)

        # Evaluate all farmers, installing on best ones until budget runs out
        # Create list of (farmer, suitability, roi) tuples
        candidates = []

        for farmer in self.model.farmer_agents:
            # Skip if farmer already has PV from this or another company
            # Check global tracker to prevent multiple companies from installing on same farmer
            if farmer.unique_id in self.model.farmers_with_pv:
                continue

            # Skip if this company already offered to this farmer (avoid re-offering after rejection)
            if farmer.unique_id in self.farmers_offered_pv:
                continue

            # Evaluate suitability using current year's solar data
            suitability = self.evaluate_location_suitability(
                farmer.lat, farmer.lon, year
            )

            # Only consider if suitability is good (15% capacity factor minimum)
            if suitability['suitability_score'] > 0.15:
                # Calculate ROI
                roi_analysis = self.calculate_roi(
                    land_hectares=farmer.land_hectares * 0.2,  # Offer 20% of land
                    suitability_metrics=suitability,
                    farmer_id=farmer.unique_id
                )

                if roi_analysis['feasible']:
                    candidates.append({
                        'farmer': farmer,
                        'suitability': suitability,
                        'roi_analysis': roi_analysis
                    })

        # Sort by ranking_roi (best first) to prioritize most profitable installations
        # Uses uncapped CF for differentiation even when all sites hit 25% cap
        candidates.sort(key=lambda x: x['roi_analysis']['ranking_roi'], reverse=True)

        # Make offers to best candidates until budget exhausted
        for candidate in candidates:
            farmer = candidate['farmer']
            roi_analysis = candidate['roi_analysis']
            suitability = candidate['suitability']

            # Check if still have budget
            if self.investment_capacity < roi_analysis['installation_cost']:
                break  # Out of money, stop offering

            # Calculate lease payment offer to farmer
            # Offer farmer a share of annual profit (e.g., 15-25% of revenue)
            # This makes PV attractive to farmer while maintaining developer profit
            land_hectares = farmer.land_hectares * 0.2  # PV uses 20% of land
            annual_lease_payment = land_hectares * self.land_lease_rate  # €500/hectare/year

            # Create PV offer
            pv_offer = {
                'annual_lease_payment': annual_lease_payment,
                'capacity_kw': roi_analysis['capacity_kw'],
                'installation_cost': roi_analysis['installation_cost'],
                'roi': roi_analysis['roi'],
                'pv_developer_id': self.unique_id
            }

            # Ask farmer to evaluate offer
            farmer_accepts = farmer.evaluate_pv_offer(pv_offer)

            # Track that we offered to this farmer (whether they accept or reject)
            # This prevents re-offering in future years
            self.farmers_offered_pv.add(farmer.unique_id)

            if farmer_accepts:
                # Farmer accepted - make the installation
                farmer.accept_pv_installation(pv_offer)

                accepted_proposals.append(roi_analysis)

                # Reduce available investment capacity
                self.investment_capacity -= roi_analysis['installation_cost']

                # Track installation with year
                self.pv_installations.append({
                    'farmer_id': farmer.unique_id,
                    'location': (farmer.lat, farmer.lon),
                    'capacity_kw': roi_analysis['capacity_kw'],
                    'roi': roi_analysis['roi'],
                    'annual_profit': roi_analysis['net_annual_profit'],
                    'year_installed': year,
                    'capacity_factor': suitability['capacity_factor'],
                    'solar_radiation': suitability['solar_radiation']
                })

                self.total_capacity_installed += roi_analysis['capacity_kw']

                # Mark farmer as having PV (both local and global tracking)
                self.farmers_with_pv.add(farmer.unique_id)
                self.model.farmers_with_pv.add(farmer.unique_id)  # Global tracker prevents multiple companies installing on same farmer

                # Stop if budget too low for another installation
                if self.investment_capacity < 100000:  # Minimum for another installation
                    break

        return accepted_proposals

    def calculate_annual_performance(self):
        """Calculate annual revenue from all installations."""
        self.annual_revenue = sum(
            install['annual_profit'] for install in self.pv_installations
        )

    def step(self):
        """Execute one PV developer timestep."""
        # 1. Evaluate available land opportunities
        proposals = self.evaluate_all_available_land()

        # 2. Calculate performance of existing installations
        self.calculate_annual_performance()

    def get_pv_report(self) -> dict:
        """
        Generate report for policy level (upward flow).

        Returns:
            Dict with PV installation metrics
        """
        return {
            'developer_id': self.unique_id,
            'company_name': self.company_name,
            'total_capacity_kw': self.total_capacity_installed,
            'num_installations': len(self.pv_installations),
            'annual_revenue': self.annual_revenue,
            'investment_capacity_remaining': self.investment_capacity
        }

    def __repr__(self):
        return (f"PVDeveloper({self.unique_id}, "
                f"capacity={self.total_capacity_installed:.0f}kW, "
                f"installations={len(self.pv_installations)})")
