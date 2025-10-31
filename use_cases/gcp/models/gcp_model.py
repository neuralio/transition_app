"""
GCP Model - Green Credit Policy Multi-Level Agent-Based Model
=============================================================

Mesa model orchestrating 3-level ML-ABM for green credit policy simulation:
- Level 1: LandOwnerAgent (Individual PV adoption decisions)
- Level 2: FinancialInstitutionAgent (Loan decisions and risk management)
- Level 3: GCPPolicymakerAgent (Green credit policies and feedback loops)
"""

import mesa
import numpy as np
import xarray as xr
from typing import Dict, List, Optional
from scipy.spatial import cKDTree

from use_cases.gcp.agents.landowner_agent import LandOwnerAgent
from use_cases.gcp.agents.financial_institution_agent import FinancialInstitutionAgent
from use_cases.gcp.agents.policymaker_agent_gcp import GCPPolicymakerAgent
from use_cases.gcp.data.gcp_data_loader import GCPDataLoader


class GCPModel(mesa.Model):
    """
    Multi-Level ABM for Green Credit Policy simulation.

    Simulates PV adoption by landowners under various green credit policy scenarios.
    """

    def __init__(
        self,
        n_landowners: int = 20,
        n_financial_institutions: int = 2,
        n_policymakers: int = 1,
        n_years: int = 10,
        scenario: str = 'rcp45',
        policy_scenario: str = 'moderate_support',
        config: Dict = None,
        geojson: dict = None,
        farmer_locations: list = None  # NEW (2025-10-21): User-specified landowner locations with crops
    ):
        """
        Initialize GCP model.

        Parameters
        ----------
        n_landowners : int
            Number of landowner agents
        n_financial_institutions : int
            Number of financial institution agents
        n_policymakers : int
            Number of policymaker agents
        n_years : int
            Simulation duration (years)
        scenario : str
            Climate scenario (rcp26, rcp45, rcp85)
        policy_scenario : str
            Green credit policy scenario (low_support, moderate_support, high_support)
        config : dict
            Configuration dictionary from config.yaml
        geojson : dict
            GeoJSON dict/string for polygon-based spatial filtering (optional)
        """
        super().__init__()

        print("=" * 80)
        print("🚨 GCPModel __init__ CALLED")
        print(f"   farmer_locations: {farmer_locations}")
        print(f"   geojson: {geojson is not None}")
        print("=" * 80)

        self.n_landowners = n_landowners
        self.n_financial_institutions = n_financial_institutions
        self.n_policymakers = n_policymakers
        self.n_years = n_years
        self.scenario = scenario
        self.policy_scenario = policy_scenario
        self.config = config
        self.geojson = geojson
        print("   ✅ Model parameters set")

        # Time tracking
        self.current_year = 0
        self.start_year = 2021  # Starting year

        # Data loader
        print("   - Creating GCPDataLoader...")
        import sys
        sys.stdout.flush()
        self.data_loader = GCPDataLoader(geojson=geojson)
        print("   ✅ GCPDataLoader created")
        sys.stdout.flush()

        # Load environmental data
        self._load_environmental_data()

        # Agent collections (by level)
        self.landowner_agents = []  # Level 1: Individual
        self.financial_institution_agents = []  # Level 2: Market
        self.policymaker_agents = []  # Level 3: Policy

        # Spatial index for neighbor finding
        self.spatial_tree = None

        # PV installation tracking (for GCP-07 visualization)
        self.pv_installations = []  # List of dicts: {year, agent_id, lat, lon, capacity_kw}

        # Budget tracking
        self.total_subsidy_spending = 0.0

        # Initialize agents
        self._initialize_agents(farmer_locations)

        # Capture initial characteristics BEFORE any steps (policy adjustments happen during steps)
        self._capture_initial_characteristics()

        # Data collector for metrics
        self.datacollector = mesa.DataCollector(
            model_reporters={
                'year': lambda m: m.current_year + m.start_year,
                'pv_adoption_rate': self._compute_pv_adoption_rate,
                'total_pv_capacity_kw': self._compute_total_pv_capacity,
                'avg_loan_approval_rate': self._compute_avg_loan_approval_rate,
                'avg_default_rate': self._compute_avg_default_rate,
                'avg_pv_subsidy_rate': self._compute_avg_pv_subsidy_rate,
                'total_subsidy_spending': lambda m: m.total_subsidy_spending,
                'avg_roi': self._compute_avg_roi,
                'landowners_with_pv': lambda m: sum(1 for a in m.landowner_agents if a.has_pv),
                'landowners_without_pv': lambda m: sum(1 for a in m.landowner_agents if not a.has_pv),
                # Energy savings metrics (GCP-03 compliance)
                'total_annual_energy_savings': self._compute_total_annual_energy_savings,
                'avg_annual_energy_savings': self._compute_avg_annual_energy_savings,
                'total_annual_feed_in_revenue': self._compute_total_annual_feed_in_revenue,
                # Demographic breakdown metrics (GCP-03 compliance - demographic variations)
                'adoption_by_financial_situation': self._compute_adoption_by_financial_situation,
                'adoption_by_risk_tolerance': self._compute_adoption_by_risk_tolerance,
                'avg_roi_by_financial_situation': self._compute_avg_roi_by_financial_situation,
                'avg_payback_by_risk_tolerance': self._compute_avg_payback_by_risk_tolerance,
                'financial_situation_distribution': self._compute_financial_situation_distribution,
                'risk_tolerance_distribution': self._compute_risk_tolerance_distribution,
            }
        )

    def _load_environmental_data(self):
        """Load environmental data (solar potential, DEM, meteorological data)."""
        print("📊 Loading environmental data...", flush=True)

        # Load DEM
        print("   - Loading DEM data...", flush=True)
        self.dem_data = self.data_loader.load_dem_data()
        print("   ✅ DEM loaded", flush=True)

        # Load solar radiation data for scenario (used for PV energy production calculation)
        # Climate scenario (rcp26/rcp45/rcp85) affects solar radiation availability
        # which directly impacts PV financial attractiveness and adoption decisions
        print(f"   - Loading solar radiation data (scenario: {self.scenario})...", flush=True)
        self.solar_data = self.data_loader.load_meteorological_data(
            scenario=self.scenario,
            variable='solar_radiation'
        )
        print("   ✅ Solar radiation loaded", flush=True)

        # Solar potential used for PV energy production calculations
        # Different climate scenarios have different solar radiation levels
        # This creates realistic climate-economy coupling in PV adoption
        self.solar_potential_data = self.solar_data  # kWh/m²/day

        # Load population density (for urban/rural classification - GCP-07 compliance)
        print("   - Loading population density data...", flush=True)
        try:
            self.population_density_data = self.data_loader.load_population_density()
            print("   ✅ Population density loaded", flush=True)
        except Exception as e:
            print(f"   ⚠️  Could not load population density: {e}", flush=True)
            self.population_density_data = None  # Fallback to distance-based classification

        print("✅ Environmental data loaded successfully", flush=True)

    def _initialize_agents(self, farmer_locations=None):
        """Initialize all agent levels."""
        # Level 3: Policy Level - Initialize first (top-down)
        self._initialize_policymakers()

        # Level 2: Market Level - Financial Institutions
        self._initialize_financial_institutions()

        # Level 1: Individual Level - Landowners
        self._initialize_landowners(farmer_locations)

        # Build spatial index for neighbor finding
        self._build_spatial_index()

    def _initialize_policymakers(self):
        """Initialize policymaker agents (Level 3)."""
        import numpy as np
        np.random.seed(42 + self.n_policymakers)  # Deterministic but varied

        for i in range(self.n_policymakers):
            # Vary policy goals slightly (different policy authorities may have different targets)
            base_target = self.config['green_credit_policy']['policy_adjustment']['target_adoption_rate']
            target_adoption = max(0.20, min(0.50, base_target + np.random.uniform(-0.05, 0.05)))

            # Vary budget constraints (some regions/authorities have more funding)
            base_budget = 1000000.0  # 1M euro base
            budget_variation = np.random.uniform(0.8, 1.5)  # ±20-50%
            budget = base_budget * budget_variation

            policy_goals = {
                'target_pv_adoption_rate': target_adoption,
                'financial_stability': 0.95,  # 95% non-default rate (fixed)
                'budget_constraint': budget
            }

            policymaker = GCPPolicymakerAgent(
                model=self,
                policy_name=f"GreenPolicy_{i+1}",
                policy_goals=policy_goals
            )

            # Initialize with policy scenario (base rates)
            policy_params = self.config['green_credit_policy']['scenarios'][self.policy_scenario]
            base_pv_subsidy = policy_params['pv_subsidy_rate']

            # Add realistic variation to policy instruments (±3-5%)
            # Different policymakers may interpret the same "scenario" slightly differently
            variation = np.random.uniform(-0.03, 0.05)
            policymaker.pv_subsidy_rate = max(0.05, min(0.40, base_pv_subsidy + variation))

            policymaker.low_interest_loan_rate = max(0.01, min(0.05,
                policy_params['low_interest_loan_rate'] + np.random.uniform(-0.01, 0.01)))
            policymaker.tax_incentive_rate = max(0.05, min(0.20,
                policy_params['tax_incentive_rate'] + np.random.uniform(-0.03, 0.05)))

            self.policymaker_agents.append(policymaker)

    def _initialize_financial_institutions(self):
        """Initialize financial institution agents (Level 2)."""
        import numpy as np
        np.random.seed(42 + self.n_financial_institutions)  # Deterministic but varied

        for i in range(self.n_financial_institutions):
            institution = FinancialInstitutionAgent(
                model=self,
                institution_name=f"GreenBank_{i+1}"
            )

            # Add realistic variation to risk thresholds (±5-10%)
            # More conservative banks have higher credit score requirements
            base_credit_threshold = self.config['financial_institutions']['risk_assessment']['credit_score_threshold']
            institution.credit_score_threshold = base_credit_threshold + np.random.randint(-20, 30)

            # Vary green loan targets (some banks more ambitious than others)
            base_green_target = self.config['financial_institutions']['portfolio']['target_green_loan_percentage']
            institution.target_green_loan_percentage = max(0.10, min(0.30, base_green_target + np.random.uniform(-0.05, 0.05)))

            # Vary debt-to-income threshold slightly (±5%)
            base_dti = self.config['financial_institutions']['risk_assessment']['debt_to_income_threshold']
            institution.debt_to_income_threshold = base_dti + np.random.uniform(-0.05, 0.05)

            # Vary loan-to-value threshold slightly (±5%)
            base_ltv = self.config['financial_institutions']['risk_assessment']['loan_to_value_threshold']
            institution.loan_to_value_threshold = base_ltv + np.random.uniform(-0.05, 0.05)

            # Vary reserve ratio (regulatory requirement, but some banks hold more reserves)
            base_reserve = self.config['financial_institutions']['portfolio']['reserve_ratio']
            institution.reserve_ratio = max(0.08, min(0.15, base_reserve + np.random.uniform(-0.02, 0.03)))

            # Vary total capital (bank size diversity: small regional banks vs large national banks)
            base_capital = 10000000.0  # 10M euros base
            capital_variation = np.random.uniform(0.7, 1.5)  # ±30-50% variation
            institution.total_capital = base_capital * capital_variation

            self.financial_institution_agents.append(institution)

    def _initialize_landowners(self, farmer_locations=None):
        """Initialize landowner agents (Level 1)."""
        # Get region bounds
        lat_min = self.config['region']['lat_min']
        lat_max = self.config['region']['lat_max']
        lon_min = self.config['region']['lon_min']
        lon_max = self.config['region']['lon_max']

        # Validate user-specified locations if provided
        if farmer_locations is not None:
            print(f"📍 Using {len(farmer_locations)} user-specified locations")
            print(f"🔥 ABOUT TO CALL VALIDATION FUNCTION")
            print(f"   self.geojson is not None: {self.geojson is not None}")
            # Validation will use polygon bounds if geojson exists, otherwise data bounds
            self._validate_user_locations(farmer_locations, self.geojson)
            print(f"🔥 VALIDATION FUNCTION RETURNED (no error raised)")
            self.n_landowners = len(farmer_locations)

        # Generate random locations within region (or use user-specified)
        if farmer_locations is None:
            np.random.seed(42)  # For reproducibility
            lats = np.random.uniform(lat_min, lat_max, self.n_landowners)
            lons = np.random.uniform(lon_min, lon_max, self.n_landowners)
        else:
            lats = [loc['lat'] for loc in farmer_locations]
            lons = [loc['lon'] for loc in farmer_locations]

        # Sample financial situations and risk tolerance
        financial_dist = self.config['landowners']['financial_situation_distribution']
        financial_situations = np.random.choice(
            ['poor', 'moderate', 'wealthy'],
            size=self.n_landowners,
            p=[financial_dist['poor'], financial_dist['moderate'], financial_dist['wealthy']]
        )

        risk_dist = self.config['landowners']['risk_tolerance_distribution']
        risk_tolerances = np.random.choice(
            ['low', 'moderate', 'high'],
            size=self.n_landowners,
            p=[risk_dist['low'], risk_dist['moderate'], risk_dist['high']]
        )

        # Sample land sizes from FADN data (if available)
        land_sizes = np.random.lognormal(mean=2.3, sigma=0.6, size=self.n_landowners)  # Lognormal distribution
        land_sizes = np.clip(land_sizes, 5.0, 50.0)  # 5-50 hectares

        for i in range(self.n_landowners):
            # Get initial crop if user-specified
            initial_crop = None
            if farmer_locations is not None:
                initial_crop = farmer_locations[i].get('crop')
                if i < 5:  # Show first 5
                    print(f"   📌 Landowner {i+1}: {initial_crop} at ({lats[i]:.3f},{lons[i]:.3f})")

            landowner = LandOwnerAgent(
                model=self,
                lat=lats[i],
                lon=lons[i],
                financial_situation=financial_situations[i],
                risk_tolerance=risk_tolerances[i],
                land_hectares=land_sizes[i],
                initial_crop=initial_crop  # NEW (2025-10-21)
            )

            # Assign to a financial institution
            institution_idx = i % self.n_financial_institutions
            landowner.financial_institution = self.financial_institution_agents[institution_idx]

            self.landowner_agents.append(landowner)

    def _capture_initial_characteristics(self):
        """Capture initial agent characteristics before simulation starts."""
        self.initial_characteristics = {}

        # Capture policymaker initial state
        if self.policymaker_agents:
            self.initial_characteristics['policymakers'] = []
            for pm in self.policymaker_agents:
                self.initial_characteristics['policymakers'].append({
                    'policy_name': pm.policy_name,
                    'pv_subsidy_rate': pm.pv_subsidy_rate,
                    'low_interest_loan_rate': pm.low_interest_loan_rate,
                    'tax_incentive_rate': pm.tax_incentive_rate,
                    'loan_guarantee_rate': pm.loan_guarantee_rate,
                    'budget_constraint': pm.policy_goals.get('budget_constraint', 0),
                    'target_pv_adoption_rate': pm.policy_goals.get('target_pv_adoption_rate', 0)
                })

        # Capture financial institution initial state
        if self.financial_institution_agents:
            self.initial_characteristics['financial_institutions'] = []
            for fi in self.financial_institution_agents:
                self.initial_characteristics['financial_institutions'].append({
                    'institution_name': fi.institution_name,
                    'available_capital': fi._get_available_capital(),
                    'green_loan_target': fi.target_green_loan_percentage,
                    'credit_score_threshold': fi.credit_score_threshold,
                    'debt_to_income_threshold': fi.debt_to_income_threshold,
                    'loan_to_value_threshold': fi.loan_to_value_threshold,
                    'reserve_ratio': fi.reserve_ratio
                })

    def _build_spatial_index(self):
        """Build spatial index for efficient neighbor finding."""
        if not self.landowner_agents:
            return

        # Extract coordinates
        coords = np.array([[a.lat, a.lon] for a in self.landowner_agents])

        # Build KD-tree
        self.spatial_tree = cKDTree(coords)

    def get_spatial_neighbors(self, agent, radius_km: float = 50.0) -> List:
        """
        Find spatial neighbors within radius.

        Parameters
        ----------
        agent : LandOwnerAgent
            Query agent
        radius_km : float
            Search radius in kilometers

        Returns
        -------
        list
            List of neighboring agents
        """
        if self.spatial_tree is None:
            return []

        # Convert km to degrees (approximate)
        # At 40° latitude: 1° lat ≈ 111 km, 1° lon ≈ 85 km
        radius_deg = radius_km / 100.0  # Rough approximation

        # Query tree
        indices = self.spatial_tree.query_ball_point(
            [agent.lat, agent.lon],
            r=radius_deg
        )

        # Return agents (excluding self)
        neighbors = [self.landowner_agents[i] for i in indices if self.landowner_agents[i].unique_id != agent.unique_id]

        return neighbors

    def get_solar_potential(self, lat: float, lon: float) -> float:
        """
        Get solar potential at location.

        Parameters
        ----------
        lat : float
            Latitude
        lon : float
            Longitude

        Returns
        -------
        float
            Solar potential (kWh/m²/year)
        """
        if self.solar_potential_data is None:
            raise ValueError("❌ Solar potential data not loaded! Check config.yaml data path: //app/data")

        # If Dataset, get the first data variable (assumes single-variable meteorological files)
        data = self.solar_potential_data
        if isinstance(data, xr.Dataset):
            # Get the first data variable (skip coordinate variables)
            data_vars = [v for v in data.data_vars]
            if not data_vars:
                raise ValueError(f"❌ Solar potential Dataset has no data variables! Available variables: {list(data.variables)}")
            data = data[data_vars[0]]

        # Get closest point - NO FALLBACKS, ONLY REAL DATA
        solar_value = data.sel(
            lat=lat,
            lon=lon,
            method='nearest'
        )

        # Get time-averaged value if time dimension exists
        if 'time' in solar_value.dims:
            mean_val = solar_value.mean(dim='time')
            solar_value = float(mean_val.item())
        else:
            # Handle both scalar and array values
            solar_value = float(solar_value.item())

        # Convert from kWh/m²/day to kWh/m²/year
        return solar_value * 365

    def get_elevation(self, lat: float, lon: float) -> float:
        """
        Get elevation at location.

        IMPORTANT: Only uses real DEM data from config.yaml.
        No fallbacks - fails if data not loaded.
        """
        if self.dem_data is None:
            raise ValueError("❌ DEM data not loaded! Check config.yaml data path: //app/data")

        # If Dataset, get the first data variable
        data = self.dem_data
        if isinstance(data, xr.Dataset):
            data_vars = [v for v in data.data_vars]
            if not data_vars:
                raise ValueError(f"❌ DEM Dataset has no data variables! Available variables: {list(data.variables)}")
            data = data[data_vars[0]]

        # Get elevation from real DEM data - NO FALLBACKS
        elev = data.sel(lat=lat, lon=lon, method='nearest')
        return float(elev.item())

    def get_population_density(self, lat: float, lon: float) -> float:
        """
        Get population density at location (people/km²).

        Used for urban/rural classification (GCP-07 compliance).
        EU standard: >300 people/km² = urban, ≤300 = rural

        IMPORTANT: Only uses real EUROSTAT population density data.
        No distance-based fallbacks - fails if data not loaded.

        Parameters
        ----------
        lat : float
            Latitude
        lon : float
            Longitude

        Returns
        -------
        float
            Population density in people/km² from EUROSTAT data
        """
        if self.population_density_data is None:
            raise ValueError("❌ Population density data not loaded! Check config.yaml data path: //app/data")

        # If Dataset, get the first data variable
        data = self.population_density_data
        if isinstance(data, xr.Dataset):
            data_vars = [v for v in data.data_vars]
            if not data_vars:
                raise ValueError(f"❌ Population density Dataset has no data variables! Available variables: {list(data.variables)}")
            data = data[data_vars[0]]

        # Query population density data (EUROSTAT data is by NUTS region)
        # Get closest point from real data - NO FALLBACKS
        density = data.sel(lat=lat, lon=lon, method='nearest')
        return float(density.item())

    def record_pv_installation(
        self,
        agent_id: int,
        year: int,
        capacity_kw: float,
        lat: float,
        lon: float,
        subsidy_amount: float = 0.0
    ):
        """
        Record PV installation and subsidy disbursement (for GCP-07 visualization).

        Parameters
        ----------
        agent_id : int
            Agent unique ID
        year : int
            Installation year
        capacity_kw : float
            PV capacity (kW)
        lat, lon : float
            Location
        subsidy_amount : float
            Subsidy amount paid (euros)
        """
        self.pv_installations.append({
            'agent_id': agent_id,
            'year': year,
            'capacity_kw': capacity_kw,
            'lat': lat,
            'lon': lon,
            'subsidy_amount': subsidy_amount
        })

        # ✅ FIX: Track total subsidy spending
        self.total_subsidy_spending += subsidy_amount

    def step(self):
        """Execute one model step (one year)."""
        year = self.current_year + self.start_year

        # === STEP 1: Policy Level (Top-Down) ===
        # Policymakers evaluate effectiveness and adjust policies
        for policymaker in self.policymaker_agents:
            policymaker.step()

        # Get policy signals (downward flow)
        policy_signals = {}
        if self.policymaker_agents:
            policy_signals = self.policymaker_agents[0].get_policy_signals()

        # === STEP 2: Market Level ===
        # Financial institutions receive policy signals
        for institution in self.financial_institution_agents:
            institution.receive_policy_signals(policy_signals)
            institution.step()

        # === STEP 3: Individual Level ===
        # Landowners receive policy signals and make decisions
        for landowner in self.landowner_agents:
            landowner.receive_policy_signals(policy_signals)
            landowner.step()

        # === STEP 4: Upward Information Flow ===
        # Aggregate individual-level data for higher levels
        self._aggregate_upward_flow()

        # === STEP 5: Lateral Coordination ===
        # Within-level interactions
        if len(self.policymaker_agents) > 1:
            for policymaker in self.policymaker_agents:
                policymaker.lateral_coordination(
                    [p for p in self.policymaker_agents if p.unique_id != policymaker.unique_id]
                )

        # Collect data
        self.datacollector.collect(self)

        # Advance time
        self.current_year += 1

    def _aggregate_upward_flow(self):
        """Aggregate data from lower levels to higher levels (upward flow)."""
        # === Individual → Market Level ===
        # Landowners report adoption statistics to Financial Institutions
        # (Already handled through loan applications)

        # === Individual → Policy Level ===
        # Aggregate PV adoption statistics
        total_landowners = len(self.landowner_agents)
        landowners_with_pv = sum(1 for a in self.landowner_agents if a.has_pv)
        pv_adoption_rate = landowners_with_pv / total_landowners if total_landowners > 0 else 0.0

        total_pv_capacity = sum(a.pv_capacity_kw for a in self.landowner_agents if a.has_pv)

        avg_roi = 0.0
        if landowners_with_pv > 0:
            avg_roi = sum(a.roi for a in self.landowner_agents if a.has_pv) / landowners_with_pv

        adoption_stats = {
            'total_landowners': total_landowners,
            'landowners_with_pv': landowners_with_pv,
            'pv_adoption_rate': pv_adoption_rate,
            'total_pv_capacity_kw': total_pv_capacity,
            'average_roi': avg_roi
        }

        # Send to policymakers
        for policymaker in self.policymaker_agents:
            policymaker.receive_adoption_statistics(adoption_stats)

        # === Market → Policy Level ===
        # Financial institutions report portfolio performance
        financial_reports = []
        for institution in self.financial_institution_agents:
            financial_reports.append(institution.get_portfolio_state())

        # Send to policymakers
        for policymaker in self.policymaker_agents:
            policymaker.receive_financial_institution_reports(financial_reports)

    # === Data Collector Reporters ===

    def _compute_pv_adoption_rate(self) -> float:
        """Compute PV adoption rate."""
        total = len(self.landowner_agents)
        with_pv = sum(1 for a in self.landowner_agents if a.has_pv)
        return with_pv / total if total > 0 else 0.0

    def _compute_total_pv_capacity(self) -> float:
        """Compute total installed PV capacity."""
        return sum(a.pv_capacity_kw for a in self.landowner_agents if a.has_pv)

    def _compute_avg_loan_approval_rate(self) -> float:
        """Compute average loan approval rate across financial institutions."""
        if not self.financial_institution_agents:
            return 0.0

        rates = [inst.get_portfolio_state()['approval_rate'] for inst in self.financial_institution_agents]
        return sum(rates) / len(rates) if rates else 0.0

    def _compute_avg_default_rate(self) -> float:
        """Compute average default rate across financial institutions."""
        if not self.financial_institution_agents:
            return 0.0

        rates = [inst.get_portfolio_state()['default_rate'] for inst in self.financial_institution_agents]
        return sum(rates) / len(rates) if rates else 0.0

    def _compute_avg_pv_subsidy_rate(self) -> float:
        """Compute average PV subsidy rate across policymakers."""
        if not self.policymaker_agents:
            return 0.0

        rates = [p.pv_subsidy_rate for p in self.policymaker_agents]
        return sum(rates) / len(rates) if rates else 0.0

    def _compute_avg_roi(self) -> float:
        """Compute average ROI across all PV installations."""
        landowners_with_pv = [a for a in self.landowner_agents if a.has_pv]

        if not landowners_with_pv:
            return 0.0

        total_roi = sum(a.roi for a in landowners_with_pv)
        return total_roi / len(landowners_with_pv)

    def _compute_total_annual_energy_savings(self) -> float:
        """
        Compute total annual energy savings across all PV installations.

        Energy savings = electricity costs avoided through self-consumption.
        This is a key benefit factor in PV adoption decisions (GCP-03 compliance).

        Returns
        -------
        float
            Total annual energy savings in euros
        """
        landowners_with_pv = [a for a in self.landowner_agents if a.has_pv]

        if not landowners_with_pv:
            return 0.0

        total_savings = sum(a.annual_energy_savings for a in landowners_with_pv)
        return total_savings

    def _compute_avg_annual_energy_savings(self) -> float:
        """
        Compute average annual energy savings per PV installation.

        Returns
        -------
        float
            Average annual energy savings in euros
        """
        landowners_with_pv = [a for a in self.landowner_agents if a.has_pv]

        if not landowners_with_pv:
            return 0.0

        total_savings = sum(a.annual_energy_savings for a in landowners_with_pv)
        return total_savings / len(landowners_with_pv)

    def _compute_total_annual_feed_in_revenue(self) -> float:
        """
        Compute total annual feed-in revenue from grid electricity sales.

        Returns
        -------
        float
            Total annual feed-in revenue in euros
        """
        landowners_with_pv = [a for a in self.landowner_agents if a.has_pv]

        if not landowners_with_pv:
            return 0.0

        total_revenue = sum(a.annual_feed_in_revenue for a in landowners_with_pv)
        return total_revenue

    # === Demographic Breakdown Reporters (GCP-03 Compliance) ===

    def _compute_adoption_by_financial_situation(self) -> Dict[str, float]:
        """
        Compute PV adoption rate by financial situation.

        Returns
        -------
        dict
            Adoption rates: {'poor': 0.1, 'moderate': 0.3, 'wealthy': 0.6}
        """
        adoption_by_fs = {}

        for fs in ['poor', 'moderate', 'wealthy']:
            landowners_with_fs = [a for a in self.landowner_agents if a.financial_situation == fs]
            if landowners_with_fs:
                adopters = sum(1 for a in landowners_with_fs if a.has_pv)
                adoption_by_fs[fs] = adopters / len(landowners_with_fs)
            else:
                adoption_by_fs[fs] = 0.0

        return adoption_by_fs

    def _compute_adoption_by_risk_tolerance(self) -> Dict[str, float]:
        """
        Compute PV adoption rate by risk tolerance.

        Returns
        -------
        dict
            Adoption rates: {'low': 0.2, 'moderate': 0.4, 'high': 0.5}
        """
        adoption_by_rt = {}

        for rt in ['low', 'moderate', 'high']:
            landowners_with_rt = [a for a in self.landowner_agents if a.risk_tolerance == rt]
            if landowners_with_rt:
                adopters = sum(1 for a in landowners_with_rt if a.has_pv)
                adoption_by_rt[rt] = adopters / len(landowners_with_rt)
            else:
                adoption_by_rt[rt] = 0.0

        return adoption_by_rt

    def _compute_avg_roi_by_financial_situation(self) -> Dict[str, float]:
        """
        Compute average ROI by financial situation (for PV adopters only).

        Returns
        -------
        dict
            Average ROI: {'poor': 5.2, 'moderate': 7.8, 'wealthy': 9.1}
        """
        roi_by_fs = {}

        for fs in ['poor', 'moderate', 'wealthy']:
            adopters_with_fs = [a for a in self.landowner_agents
                               if a.financial_situation == fs and a.has_pv]
            if adopters_with_fs:
                avg_roi = sum(a.roi for a in adopters_with_fs) / len(adopters_with_fs)
                roi_by_fs[fs] = avg_roi
            else:
                roi_by_fs[fs] = 0.0

        return roi_by_fs

    def _compute_avg_payback_by_risk_tolerance(self) -> Dict[str, float]:
        """
        Compute average payback period by risk tolerance (for PV adopters only).

        Returns
        -------
        dict
            Average payback: {'low': 12.5, 'moderate': 11.2, 'high': 10.8} years
        """
        payback_by_rt = {}

        for rt in ['low', 'moderate', 'high']:
            adopters_with_rt = [a for a in self.landowner_agents
                               if a.risk_tolerance == rt and a.has_pv]
            if adopters_with_rt:
                avg_payback = sum(a.payback_period for a in adopters_with_rt) / len(adopters_with_rt)
                payback_by_rt[rt] = avg_payback
            else:
                payback_by_rt[rt] = 0.0

        return payback_by_rt

    def _compute_financial_situation_distribution(self) -> Dict[str, int]:
        """
        Compute distribution of financial situations among PV adopters.

        Returns
        -------
        dict
            Count of adopters: {'poor': 2, 'moderate': 5, 'wealthy': 8}
        """
        distribution = {'poor': 0, 'moderate': 0, 'wealthy': 0}

        adopters = [a for a in self.landowner_agents if a.has_pv]

        for adopter in adopters:
            distribution[adopter.financial_situation] += 1

        return distribution

    def _compute_risk_tolerance_distribution(self) -> Dict[str, int]:
        """
        Compute distribution of risk tolerances among PV adopters.

        Returns
        -------
        dict
            Count of adopters: {'low': 3, 'moderate': 7, 'high': 5}
        """
        distribution = {'low': 0, 'moderate': 0, 'high': 0}

        adopters = [a for a in self.landowner_agents if a.has_pv]

        for adopter in adopters:
            distribution[adopter.risk_tolerance] += 1

        return distribution

    def run_model(self, n_steps: Optional[int] = None):
        """
        Run the model for n_steps.

        Parameters
        ----------
        n_steps : int, optional
            Number of steps. If None, uses self.n_years.
        """
        if n_steps is None:
            n_steps = self.n_years

        for _ in range(n_steps):
            self.step()

    def get_results_dataframe(self):
        """Get results as pandas DataFrame."""
        return self.datacollector.get_model_vars_dataframe()

    def _validate_user_locations(self, farmer_locations: list, geojson=None):
        """
        Validate and snap user-specified landowner locations to meteo grid.

        Strategy:
        1. Validate coordinates are within bounds (polygon or Thessaloniki)
        2. Snap to nearest meteo grid point (data alignment for PV suitability)
        3. Add small random offset (±0.01°) for visual variety
        4. Ensure snap distance is reasonable (<0.1°)

        Args:
            farmer_locations: List of {"lat": float, "lon": float, "crop": str}
            geojson: Optional GeoJSON for polygon validation

        Returns:
            List of (lat, lon) tuples - SNAPPED to meteo grid with offsets
        """
        from backend.data.loaders.spatial_filter import get_polygon_bounds
        import sys

        # Terminal logging
        sys.stderr.write(f"\n{'='*80}\n")
        sys.stderr.write(f"📍 VALIDATING & SNAPPING USER COORDINATES TO METEO GRID (GCP)\n")
        sys.stderr.write(f"{'='*80}\n")
        sys.stderr.flush()

        # Determine validation bounds based on polygon availability
        if geojson:
            # User drew polygon - use polygon bounds for validation
            polygon_bounds = get_polygon_bounds(geojson)
            lat_min, lat_max = polygon_bounds['lat_min'], polygon_bounds['lat_max']
            lon_min, lon_max = polygon_bounds['lon_min'], polygon_bounds['lon_max']
            bounds_desc = f"drawn polygon [{lat_min:.2f}, {lat_max:.2f}]°N, [{lon_min:.2f}, {lon_max:.2f}]°E"
            use_polygon = True
        else:
            # No polygon - use model's data bounds
            lat_min, lat_max = self.config['region']['lat_min'], self.config['region']['lat_max']
            lon_min, lon_max = self.config['region']['lon_min'], self.config['region']['lon_max']
            bounds_desc = f"data bounds [{lat_min:.1f}, {lat_max:.1f}]°N, [{lon_min:.1f}, {lon_max:.1f}]°E"
            use_polygon = False

        sys.stderr.write(f"Validation bounds: {bounds_desc}\n")
        sys.stderr.flush()

        errors = []
        validated_locs = []

        # Import centralized epsilon configuration
        from backend.config.validation_config import get_coordinate_epsilon
        epsilon = get_coordinate_epsilon()

        # Max distance for snapping to solar grid (0.1° ≈ 11km - one grid pixel spacing)
        MAX_SNAP_DISTANCE = 0.1

        # Get solar data for snapping (GCP uses solar radiation, not full meteo)
        solar_data = self.solar_data

        sys.stderr.write(f"\n📍 Processing {len(farmer_locations)} user-specified locations:\n")
        sys.stderr.write(f"{'-'*80}\n")
        sys.stderr.flush()

        for i, loc in enumerate(farmer_locations, 1):
            user_lat, user_lon = loc['lat'], loc['lon']
            crop = loc.get('crop', 'PV')  # GCP is about PV installations
            location_errors = []

            sys.stderr.write(f"\nLocation {i}: User requested ({user_lat}, {user_lon}) for {crop}\n")
            sys.stderr.flush()

            # Check latitude bounds (with epsilon tolerance for boundary points)
            if not (lat_min - epsilon <= user_lat <= lat_max + epsilon):
                location_errors.append(f"latitude {user_lat}° outside range [{lat_min:.4f}°, {lat_max:.4f}°]")

            # Check longitude bounds (with epsilon tolerance for boundary points)
            if not (lon_min - epsilon <= user_lon <= lon_max + epsilon):
                location_errors.append(f"longitude {user_lon}° outside range [{lon_min:.4f}°, {lon_max:.4f}°]")

            # If basic validation failed, skip snapping
            if location_errors:
                errors.append(f"Location {i}: {'; '.join(location_errors)}")
                sys.stderr.write(f"  ❌ Validation failed: {'; '.join(location_errors)}\n")
                sys.stderr.flush()
                continue

            # ========== SNAP TO NEAREST SOLAR GRID POINT ==========
            # Find nearest solar grid point
            solar_lat_nearest = float(solar_data.lat.sel(lat=user_lat, method='nearest').values)
            solar_lon_nearest = float(solar_data.lon.sel(lon=user_lon, method='nearest').values)

            # Calculate snap distance
            snap_distance = ((solar_lat_nearest - user_lat)**2 + (solar_lon_nearest - user_lon)**2)**0.5

            # Validate snap distance
            if snap_distance > MAX_SNAP_DISTANCE:
                location_errors.append(
                    f"too far from solar grid - nearest point at ({solar_lat_nearest}, {solar_lon_nearest}) "
                    f"is {snap_distance:.4f}° away (max: {MAX_SNAP_DISTANCE}°)"
                )
                errors.append(f"Location {i}: {'; '.join(location_errors)}")
                sys.stderr.write(f"  ❌ Snap distance too large: {snap_distance:.4f}° > {MAX_SNAP_DISTANCE}°\n")
                sys.stderr.flush()
                continue

            # Add small random offset for visual variety (±0.001° ≈ ±110m)
            import random
            offset_lat = random.uniform(-0.001, 0.001)
            offset_lon = random.uniform(-0.001, 0.001)

            final_lat = solar_lat_nearest + offset_lat
            final_lon = solar_lon_nearest + offset_lon

            # Clamp to bounds to ensure we don't go outside
            final_lat = max(lat_min, min(lat_max, final_lat))
            final_lon = max(lon_min, min(lon_max, final_lon))

            # Round to 4 decimal places
            final_lat = round(final_lat, 4)
            final_lon = round(final_lon, 4)

            # Add to validated list
            validated_locs.append((final_lat, final_lon))

            # Terminal logging
            sys.stderr.write(f"  ✅ {crop.upper():<6} → Snapped to solar grid:\n")
            sys.stderr.write(f"     User requested:  ({user_lat:.4f}, {user_lon:.4f})\n")
            sys.stderr.write(f"     Solar grid:      ({solar_lat_nearest:.4f}, {solar_lon_nearest:.4f})\n")
            sys.stderr.write(f"     Final location:  ({final_lat:.4f}, {final_lon:.4f}) [with ±0.001° offset]\n")
            sys.stderr.write(f"     Snap distance:   {snap_distance:.6f}°\n")
            sys.stderr.flush()

        # Terminal summary
        sys.stderr.write(f"\n{'-'*80}\n")
        sys.stderr.write(f"📊 SUMMARY:\n")
        sys.stderr.write(f"   Total requested: {len(farmer_locations)}\n")
        sys.stderr.write(f"   Successfully validated & snapped: {len(validated_locs)}\n")
        sys.stderr.write(f"   Errors: {len(errors)}\n")
        sys.stderr.write(f"{'='*80}\n\n")
        sys.stderr.flush()

        # Raise error with ALL violations (single-line format for frontend)
        if errors:
            error_msg = f"❌ COORDINATE VALIDATION FAILED! {' | '.join(errors)}"
            if use_polygon:
                error_msg += " | ⚠️ Coordinates must be inside your drawn polygon!"
            raise ValueError(error_msg)

        return validated_locs
