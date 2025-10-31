"""
Multi-Level Agent-Based Land-Use Model for TRANSITION Project.

This model implements the ML-ABM framework with 4 hierarchical levels:
- Individual Level: FarmerAgent
- Community Level: CollectiveAgent
- Market Level: CommodityMarketAgent
- Policy Level: PolicymakerAgent

Supports multiple use cases:
- MLU (Multi-Land Use): Land suitability optimization
- CCA (Climate Change Adaptation): Adaptation strategies under climate change
- GCP (Green Credit Policy): PV adoption with policy incentives
"""

import mesa
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from use_cases.cca.data.loaders.data_loader_cca import DataLoader
from use_cases.cca.agents.farmer_agent_cca import FarmerAgent
from use_cases.cca.agents.collective_agent_cca import CollectiveAgent
from use_cases.cca.agents.market_agent_cca import CommodityMarketAgent
from use_cases.cca.agents.policymaker_agent_cca import PolicymakerAgent
from use_cases.cca.agents.pv_developer_agent_cca import PVDeveloperAgent
from use_cases.cca.orchestrator import MultiLevelOrchestrator


class LandUseModel(mesa.Model):
    """
    Multi-Level ABM for land-use decision-making under climate change.

    This model simulates the complex interactions between:
    - Individual farmers making crop/PV installation decisions
    - Agricultural collectives coordinating resources
    - Commodity markets determining prices
    - Policy makers setting regulations and incentives

    Data Sources:
    - MLU: backend/data/MLU/ (PILOT_THESSALONIKI_DATA)
    - CCA: backend/data/CCA/
    - GCP: backend/data/GCP/ (future)
    """

    def __init__(
        self,
        data_path: str,
        crops: List[str],
        scenario: str,
        n_farmers: int = 3,  # Consistent default across all CCA cases
        n_collectives: int = 2,
        n_markets: int = 1,
        n_policies: int = 1,
        n_pv_developers: int = 0,  # CCA-specific: energy companies
        lat_bounds: Optional[Tuple[float, float]] = None,
        lon_bounds: Optional[Tuple[float, float]] = None,
        start_year: int = 2021,
        seed: Optional[int] = None,
        enable_multi_level: bool = True,
        auto_detect_bounds: bool = True,
        auto_aggregate_temporal: bool = True,
        validate_temporal_range: bool = True,
        geojson: dict = None,
        farmer_locations: list = None,  # NEW (2025-10-21): User-specified farmer locations with crops
        focus_crop: str = None  # NEW: Focus crop for CCA-03 (all farmers start with this crop if no farmer_locations)
    ):
        """
        Initialize the Land-Use Model with flexible data handling.

        Args:
            data_path: Path to data directory (MLU/CCA/GCP)
            crops: List of crop types (e.g., ["WHEAT", "MAIZE"])
            scenario: Climate scenario (rcp26, rcp45, rcp85)
            n_farmers: Number of farmer agents
            n_collectives: Number of collective agents (cooperatives)
            n_markets: Number of market agents
            n_policies: Number of policy agents
            n_pv_developers: Number of PV developer agents (CCA-specific)
            lat_bounds: (min_lat, max_lat) for region (None = auto-detect from data)
            lon_bounds: (min_lon, max_lon) for region (None = auto-detect from data)
            start_year: Starting year of simulation
            seed: Random seed for reproducibility
            enable_multi_level: Enable multi-level ABM (cross-scale interactions)
            auto_detect_bounds: Auto-detect spatial bounds from data if bounds not provided
            auto_aggregate_temporal: Automatically aggregate daily/monthly data to annual
            validate_temporal_range: Validate that simulation years are within data range
            geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)
            farmer_locations: List of dicts [{lat, lon, crop}, ...] (NEW - 2025-10-21)
        """
        super().__init__()

        # Set random seed
        if seed is not None:
            np.random.seed(seed)
            self.random = np.random.RandomState(seed)
        else:
            self.random = np.random.RandomState()

        # Store configuration
        self.data_path = data_path
        self.crops = crops
        self.scenario = scenario
        self.current_year = start_year
        self.enable_multi_level = enable_multi_level
        self.geojson = geojson  # Store geojson for validation
        self.focus_crop = focus_crop  # NEW: Store focus_crop for farmer creation

        # Initialize data loader with flexible options
        print(f"Loading data from: {data_path}")
        self.data_loader = DataLoader(
            data_path=data_path,
            crops=crops,
            scenario=scenario,
            auto_aggregate=auto_aggregate_temporal,
            validate_years=validate_temporal_range,
            geojson=geojson
        )

        # Auto-detect or use provided spatial bounds
        if lat_bounds is None or lon_bounds is None:
            if auto_detect_bounds:
                print("📍 Auto-detecting spatial bounds from data...")
                data_info = self.data_loader.get_data_info()
                if 'lat_range' in data_info and 'lon_range' in data_info:
                    self.lat_bounds = data_info['lat_range']
                    self.lon_bounds = data_info['lon_range']
                    print(f"   Detected bounds: Lat {self.lat_bounds}, Lon {self.lon_bounds}")
                else:
                    # Fallback to default Thessaloniki region
                    print("⚠️  Could not auto-detect bounds, using default Thessaloniki region")
                    self.lat_bounds = (40.5, 40.75)
                    self.lon_bounds = (22.8, 23.0)
            else:
                raise ValueError("lat_bounds and lon_bounds must be provided when auto_detect_bounds=False")
        else:
            self.lat_bounds = lat_bounds
            self.lon_bounds = lon_bounds

        # Display data information
        print("\n📊 Data Characteristics:")
        data_info = self.data_loader.get_data_info()
        if 'spatial_resolution' in data_info:
            print(f"   Spatial Resolution: {data_info['spatial_resolution']}")
        if 'temporal_resolution' in data_info:
            print(f"   Temporal Resolution: {data_info['temporal_resolution']}")
        if 'year_range' in data_info:
            print(f"   Year Range: {data_info['year_range'][0]}-{data_info['year_range'][1]}")
        print(f"   Spatial Extent: Lat {self.lat_bounds}, Lon {self.lon_bounds}")
        print()

        # Agent lists (for easier access by type)
        # Note: Mesa 3.0+ manages self.agents internally
        self.farmer_agents = []
        self.collective_agents = []
        self.market_agents = []
        self.pv_developer_agents = []  # CCA-specific
        self.policy_agents = []

        # Global tracker for PV installations (shared across all PV developers)
        self.farmers_with_pv = set()  # Set of farmer IDs that have PV installations
        self.start_year = start_year  # Store start year for PV developer logic

        # Initialize agents
        print(f"Creating {n_farmers} farmers...")
        self._create_farmer_agents(n_farmers, farmer_locations, geojson)

        if enable_multi_level:
            print(f"Creating {n_collectives} collectives...")
            self._create_collective_agents(n_collectives)

            print(f"Creating {n_markets} market(s)...")
            self._create_market_agents(n_markets)

            if n_pv_developers > 0:
                print(f"Creating {n_pv_developers} PV developer(s)...")
                self._create_pv_developer_agents(n_pv_developers)

            print(f"Creating {n_policies} policy agent(s)...")
            self._create_policy_agents(n_policies)

            # Initialize orchestrator for cross-scale interactions
            print("Initializing multi-level orchestrator...")
            self.orchestrator = MultiLevelOrchestrator(model=self)
        else:
            self.orchestrator = None

        # Initialize data collector
        self._setup_data_collector()

        # Capture initial agent characteristics before any simulation steps
        self._capture_initial_characteristics()

        print("Model initialization complete!")

    def _create_farmer_agents(self, n_farmers: int, farmer_locations: list = None, geojson: dict = None):
        """Create farmer agents at user-specified or random locations within bounds (land only)."""
        # Validate user-specified locations if provided
        if farmer_locations is not None:
            print(f"📍 Using {len(farmer_locations)} user-specified locations")
            validated_locs = self._validate_user_locations(farmer_locations, self.geojson)
            n_farmers = len(farmer_locations)

        for i in range(n_farmers):
            # Use user-specified location if provided
            if farmer_locations is not None:
                lat = farmer_locations[i]['lat']
                lon = farmer_locations[i]['lon']
                initial_crop = farmer_locations[i]['crop']
                valid_location = True
            else:
                # Find valid land location (not sea)
                max_retries = 100  # Increased retries for better land detection
                valid_location = False
                lat = None
                lon = None
                # Use focus_crop if specified (e.g., "simulate maize yield" → all farmers start with MAIZE)
                initial_crop = self.focus_crop if self.focus_crop else None

                for attempt in range(max_retries):
                    # Random location within bounds
                    test_lat = self.random.uniform(*self.lat_bounds)
                    test_lon = self.random.uniform(*self.lon_bounds)

                    # PRIMARY VALIDATION: Check crop suitability
                    # If any crop has suitability > 0.1, it's likely agricultural land
                    has_crop_suitability = False
                    for crop in self.crops:
                        try:
                            suitability = self.get_suitability(test_lat, test_lon, crop, self.current_year)
                            # Check for actual suitability data (not default 0.5)
                            # Real suitability data ranges from 0-100, we check for > 0.1 (scaled 0-1)
                            if suitability > 0.1 and suitability != 0.5:
                                has_crop_suitability = True
                                break
                        except:
                            continue

                    if has_crop_suitability:
                        # SECONDARY VALIDATION: Check elevation (avoid extreme elevations and sea)
                        try:
                            elevation = self.get_elevation(test_lat, test_lon)
                            # Valid agricultural land: elevation 0-1500m
                            # Reject default value (100.0) and check for reasonable range
                            if elevation != 100.0 and 0 < elevation < 1500:
                                valid_location = True
                                lat = test_lat
                                lon = test_lon
                                break
                            # If elevation check fails but we have good suitability, still accept
                            elif has_crop_suitability:
                                valid_location = True
                                lat = test_lat
                                lon = test_lon
                                break
                        except:
                            # If elevation fails but we have suitability, accept
                            valid_location = True
                            lat = test_lat
                            lon = test_lon
                            break

                if not valid_location:
                    # If we still can't find a valid location after many retries,
                    # use a safe fallback location (center of the region)
                    lat = (self.lat_bounds[0] + self.lat_bounds[1]) / 2
                    lon = (self.lon_bounds[0] + self.lon_bounds[1]) / 2
                    if i == 0:  # Only print warning once
                        print(f"⚠️  Warning: Could not validate {max_retries} random locations.")
                        print(f"   Placing farmers at safe central location ({lat:.4f}, {lon:.4f})")
                        print(f"   This may indicate bounds are too wide or include large sea areas.")

            # Create farmer with correct signature (model, lat, lon, initial_crop)
            farmer = FarmerAgent(
                model=self,
                lat=lat,
                lon=lon,
                initial_crop=initial_crop
            )

            # Print debug info for user-specified locations
            if farmer_locations is not None and i < 5:  # Show first 5
                print(f"   📌 Farmer {i+1}: {initial_crop} at ({lat:.3f},{lon:.3f})")

            # Vary land sizes (5-20 hectares) for installation diversity
            # Real EU farm sizes: small (5-10 ha), medium (10-20 ha), large (>20 ha)
            farmer.land_hectares = self.random.uniform(5.0, 20.0)

            # Mesa 3.0+ automatically adds agents to self.agents
            self.farmer_agents.append(farmer)

    def _create_collective_agents(self, n_collectives: int):
        """Create agricultural collective agents with heterogeneous characteristics."""
        import random

        # Skip if no collectives requested (e.g., CCA-04 doesn't use collectives)
        if n_collectives == 0 or not self.farmer_agents:
            return

        # Divide farmers among collectives
        farmers_per_collective = len(self.farmer_agents) // n_collectives

        # Region name varieties for diversity (location-agnostic)
        region_names = [
            "Farmers Cooperative North", "Farmers Cooperative Central", "Farmers Cooperative South",
            "Farmers Cooperative East", "Farmers Cooperative West", "Agricultural Collective Alpha",
            "Agricultural Collective Beta", "Rural Development Group", "Community Farm Alliance"
        ]

        for i in range(n_collectives):
            # Assign farmers to this collective
            start_idx = i * farmers_per_collective
            if i == n_collectives - 1:
                # Last collective gets remaining farmers
                member_farmers = self.farmer_agents[start_idx:]
            else:
                member_farmers = self.farmer_agents[start_idx:start_idx + farmers_per_collective]

            # Use descriptive region name (with fallback to numbered if > 9 collectives)
            region_name = region_names[i] if i < len(region_names) else f"Collective-{i+1}"

            # Create collective with correct signature (model, region_name, member_farmers)
            collective = CollectiveAgent(
                model=self,
                region_name=region_name,
                member_farmers=member_farmers
            )

            # Add heterogeneous initial characteristics
            # Collective wealth varies based on member count and average farmer wealth
            total_farmer_wealth = sum(
                getattr(f, 'land_hectares', 10.0) * random.uniform(1000, 5000)
                for f in member_farmers
            )
            collective.collective_wealth = total_farmer_wealth * random.uniform(0.05, 0.15)  # 5-15% pooled

            # Social norms vary by collective (risk aversion: 0.3-0.9)
            collective.social_norms = {
                'risk_aversion': random.uniform(0.3, 0.9),
                'innovation_openness': random.uniform(0.2, 0.8)
            }

            # Knowledge pool starts small but varies
            initial_knowledge = random.randint(0, 3)
            collective.knowledge_pool = set([f"practice_{j}" for j in range(initial_knowledge)])

            # Mesa 3.0+ automatically adds agents to self.agents
            self.collective_agents.append(collective)

    def _create_market_agents(self, n_markets: int):
        """Create commodity market agents with heterogeneous characteristics."""
        import random

        # Skip if no markets requested (e.g., CCA-04 doesn't use commodity markets)
        if n_markets == 0:
            return

        # Market name varieties for diversity (location-agnostic)
        market_names = [
            "Regional Commodity Market",
            "Agricultural Trading Exchange",
            "Farmers Market Cooperative",
            "Central Trading Hub",
            "Rural Commodity Exchange"
        ]

        for i in range(n_markets):
            # Use descriptive market name (with fallback to numbered if > 5 markets)
            market_name = market_names[i] if i < len(market_names) else f"Market-{i+1}"

            # Generate heterogeneous initial prices (±20% from base 100 €/ton)
            initial_prices = {crop: random.uniform(80.0, 120.0) for crop in self.crops}

            # Generate heterogeneous initial demand (500-1000 tons per crop)
            initial_demand = {crop: random.uniform(500.0, 1000.0) for crop in self.crops}

            # Create market with heterogeneous initial values
            market = CommodityMarketAgent(
                model=self,
                market_name=market_name,
                crops=self.crops,
                initial_prices=initial_prices,
                initial_demand=initial_demand
            )

            # Mesa 3.0+ automatically adds agents to self.agents
            self.market_agents.append(market)

    def _create_pv_developer_agents(self, n_pv_developers: int):
        """Create PV developer agents (energy companies) with heterogeneous characteristics."""
        import random

        # Different company sizes: small (3M), medium (5M), large (8M)
        investment_capacities = [3000000.0, 5000000.0, 8000000.0]

        for i in range(n_pv_developers):
            # Use generic numbered names (1-indexed for user clarity)
            company_name = f"Energy Company {i+1}"

            # Assign investment capacity based on company size distribution
            # Randomize to create heterogeneity
            if n_pv_developers == 1:
                # Single company gets medium size
                capacity = 5000000.0
            elif n_pv_developers == 2:
                # Two companies: one small, one large (for contrast)
                capacity = investment_capacities[0] if i == 0 else investment_capacities[2]
            else:
                # Multiple companies: mix of sizes
                capacity = random.choice(investment_capacities)

            # Create PV developer with heterogeneous investment capacity
            pv_developer = PVDeveloperAgent(
                model=self,
                company_name=company_name,
                investment_capacity=capacity
            )

            # Mesa 3.0+ automatically adds agents to self.agents
            self.pv_developer_agents.append(pv_developer)

    def _create_policy_agents(self, n_policies: int):
        """Create policymaker agents with heterogeneous characteristics."""
        import random

        # Skip if no policymakers requested
        if n_policies == 0:
            return

        # Policy authority name varieties for diversity
        policy_names = [
            "Agricultural Policy Authority",
            "Regional Development Authority",
            "Environmental Protection Agency",
            "Rural Economic Council",
            "Climate Adaptation Task Force"
        ]

        for i in range(n_policies):
            # Use descriptive policy name (with fallback to numbered if > 5 policymakers)
            policy_name = policy_names[i] if i < len(policy_names) else f"Policymaker-{i+1}"

            # Create policy with correct signature (model, policy_name, policy_goals)
            # Add heterogeneous policy goals (vary priorities between policymakers)
            policy_goals = {
                'food_security': random.uniform(0.6, 0.9),
                'sustainability': random.uniform(0.4, 0.8),
                'economic_growth': random.uniform(0.5, 0.8)
            }

            # CCA: Add renewable energy goal if PV developers present
            if hasattr(self, 'pv_developer_agents') and len(self.pv_developer_agents) > 0:
                policy_goals['renewable_energy'] = random.uniform(0.1, 0.4)  # 10-40% renewable target

            policy = PolicymakerAgent(
                model=self,
                policy_name=policy_name,
                policy_goals=policy_goals
            )

            # Initialize default policies for all crops
            policy.initialize_default_policies(self.crops)

            # Add heterogeneous policy parameters
            # PV green credit rate varies (€0.03-0.07/kWh)
            policy.pv_green_credit = random.uniform(0.03, 0.07)

            # PV installation subsidy varies (0-20%)
            policy.pv_installation_subsidy = random.uniform(0.0, 0.2)

            # Renewable energy target varies (0-50%)
            policy.renewable_energy_target = random.uniform(0.0, 0.5)

            # Mesa 3.0+ automatically adds agents to self.agents
            self.policy_agents.append(policy)

    def _setup_data_collector(self):
        """Setup Mesa DataCollector for tracking metrics over time."""

        # Model-level reporters
        model_reporters = {
            "Year": lambda m: m.current_year,
            "Avg_Income": lambda m: np.mean([
                getattr(f, 'annual_income', 0.0) for f in m.farmer_agents
            ]) if m.farmer_agents else 0.0,
            "Total_Production": lambda m: sum([
                getattr(f, 'actual_yield', 0.0) * getattr(f, 'land_hectares', 10.0)
                for f in m.farmer_agents
            ]) if m.farmer_agents else 0.0,
        }

        # Add crop-specific reporters
        for crop in self.crops:
            model_reporters[f"{crop}_Farmers"] = lambda m, c=crop: sum(
                1 for f in m.farmer_agents if getattr(f, 'current_crop', None) == c
            )

        # Add multi-level reporters if enabled
        if self.enable_multi_level:
            if self.market_agents:
                for crop in self.crops:
                    model_reporters[f"{crop}_Price"] = lambda m, c=crop: (
                        m.market_agents[0].crop_prices.get(c, 100.0)
                        if m.market_agents else 100.0
                    )

            if self.policy_agents:
                for crop in self.crops:
                    model_reporters[f"{crop}_Subsidy"] = lambda m, c=crop: (
                        m.policy_agents[0].subsidy_rates.get(c, 0.0)
                        if m.policy_agents else 0.0
                    )

        # Agent-level reporters
        agent_reporters = {
            "Crop": lambda a: getattr(a, 'current_crop', None),
            "Income": lambda a: getattr(a, 'annual_income', 0.0),
            "Yield": lambda a: getattr(a, 'actual_yield', 0.0),
        }

        self.datacollector = mesa.DataCollector(
            model_reporters=model_reporters,
            agent_reporters=agent_reporters
        )

    def step(self):
        """
        Execute one time step of the model.

        Steps:
        1. Multi-level orchestrator handles all cross-scale interactions
        2. Collect data
        3. Increment year
        """

        # Multi-level interactions (orchestrator manages all flows)
        if self.enable_multi_level and self.orchestrator:
            self.orchestrator.step_all_levels()
        else:
            # Simple mode: just step all agents randomly
            import random
            agents_shuffled = list(self.agents)
            random.shuffle(agents_shuffled)
            for agent in agents_shuffled:
                agent.step()

        # Collect data
        self.datacollector.collect(self)

        # Increment year
        self.current_year += 1

    def get_model_data(self):
        """Get model-level data collected during simulation."""
        return self.datacollector.get_model_vars_dataframe()

    def get_agent_data(self):
        """Get agent-level data collected during simulation."""
        return self.datacollector.get_agent_vars_dataframe()

    def _capture_initial_characteristics(self):
        """Capture initial agent characteristics before any simulation steps."""
        self.initial_characteristics = {}

        # Capture market initial states
        if self.market_agents:
            self.initial_characteristics['markets'] = []
            for market in self.market_agents:
                self.initial_characteristics['markets'].append({
                    'name': market.market_name,
                    'crops': market.crops.copy(),
                    'prices': market.crop_prices.copy(),
                    'demand': market.demand.copy()
                })

        # Capture collective initial states
        if self.collective_agents:
            self.initial_characteristics['collectives'] = []
            for collective in self.collective_agents:
                self.initial_characteristics['collectives'].append({
                    'name': collective.region_name,
                    'members': len(collective.members),
                    'wealth': collective.collective_wealth,
                    'social_norms': collective.social_norms.copy() if collective.social_norms else {},
                    'knowledge_pool': len(collective.knowledge_pool)
                })

        # Capture policymaker initial states
        if self.policy_agents:
            self.initial_characteristics['policymakers'] = []
            for policymaker in self.policy_agents:
                self.initial_characteristics['policymakers'].append({
                    'name': policymaker.policy_name,
                    'goals': policymaker.policy_goals.copy(),
                    'pv_green_credit': policymaker.pv_green_credit,
                    'pv_subsidy': policymaker.pv_installation_subsidy,
                    'renewable_target': policymaker.renewable_energy_target
                })

    def get_farmer_decisions(self) -> Dict[str, int]:
        """Get current crop decision distribution."""
        decisions = {crop: 0 for crop in self.crops}
        for farmer in self.farmer_agents:
            crop = getattr(farmer, 'current_crop', None)
            if crop in decisions:
                decisions[crop] += 1
        return decisions

    def get_market_state(self) -> Dict[str, Dict]:
        """Get current market state (prices, supply, demand)."""
        if not self.market_agents:
            return {}

        market_state = {}
        for market in self.market_agents:
            market_state[market.unique_id] = {
                'prices': market.crop_prices.copy(),
                'supply': market.supply.copy(),
                'demand': market.demand.copy()
            }

        return market_state

    def get_policy_state(self) -> Dict[str, Dict]:
        """Get current policy state (subsidies, regulations, effectiveness)."""
        if not self.policy_agents:
            return {}

        policy_state = {}
        for policy in self.policy_agents:
            policy_state[policy.unique_id] = {
                'subsidies': policy.subsidy_rates.copy(),
                'price_floors': getattr(policy, 'price_floors', {}).copy(),
                'price_ceilings': getattr(policy, 'price_ceilings', {}).copy(),
                'effectiveness': policy.policy_effectiveness.copy()
            }

        return policy_state

    def get_summary_stats(self) -> Dict:
        """Get summary statistics for current state."""
        stats = {
            'year': self.current_year,
            'n_farmers': len(self.farmer_agents),
            'n_collectives': len(self.collective_agents),
            'n_markets': len(self.market_agents),
            'n_policies': len(self.policy_agents),
            'farmer_decisions': self.get_farmer_decisions(),
        }

        if self.farmer_agents:
            stats['avg_income'] = np.mean([
                getattr(f, 'annual_income', 0.0) for f in self.farmer_agents
            ])
            stats['total_production'] = sum([
                getattr(f, 'actual_yield', 0.0) * getattr(f, 'land_hectares', 10.0)
                for f in self.farmer_agents
            ])

        if self.enable_multi_level:
            stats['market_state'] = self.get_market_state()
            stats['policy_state'] = self.get_policy_state()

        return stats

    def export_results(self, output_dir: str):
        """
        Export simulation results to files.

        Args:
            output_dir: Directory to save results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export model-level data
        model_data = self.get_model_data()
        model_data.to_csv(output_path / "model_data.csv")

        # Export agent-level data
        agent_data = self.get_agent_data()
        agent_data.to_csv(output_path / "agent_data.csv")

        print(f"Results exported to: {output_path}")

    # Helper methods for agents to access data

    def get_soil(self, lat: float, lon: float, soil_type: str) -> float:
        """Get soil data at location.

        Args:
            lat: Latitude
            lon: Longitude
            soil_type: 'ph', 'organic_carbon', 'cec', 'soil_type'

        Returns:
            Soil value (returns 0.5 default if data loading fails)
        """
        try:
            soil_data = self.data_loader.load_soil()
            if soil_type == 'ph':
                ds = soil_data['ph']
            elif soil_type == 'organic_carbon':
                ds = soil_data['organic_carbon']
            elif soil_type == 'cec':
                ds = soil_data['cec']
            elif soil_type == 'soil_type':
                ds = soil_data['soil_type']
            else:
                return 0.5

            # Select nearest location (handle both lat/lon and latitude/longitude)
            if 'lat' in ds.dims:
                value = ds.sel(lat=lat, lon=lon, method='nearest')
            else:
                value = ds.sel(latitude=lat, longitude=lon, method='nearest')
            return float(value.values.item())
        except Exception as e:
            # Return neutral default
            return 0.5

    def get_elevation(self, lat: float, lon: float) -> float:
        """Get elevation at location.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Elevation in meters (returns 100.0 default if data loading fails)
        """
        try:
            dem_data = self.data_loader.load_dem()
            # Handle both lat/lon and latitude/longitude
            if 'lat' in dem_data.dims:
                value = dem_data.sel(lat=lat, lon=lon, method='nearest')
            else:
                value = dem_data.sel(latitude=lat, longitude=lon, method='nearest')
            return float(value.values.item())
        except Exception as e:
            # Return neutral default
            return 100.0

    def get_meteo(self, lat: float, lon: float, meteo_type: str, year: int) -> float:
        """Get meteorological data at location and year.

        Automatically handles yearly, monthly, and daily temporal resolutions.

        Args:
            lat: Latitude
            lon: Longitude
            meteo_type: 'temperature', 'precipitation', 'solar_radiation', 'evapotranspiration'
            year: Year (integer, e.g., 2021)

        Returns:
            Meteorological value (returns neutral default if data loading fails)
        """
        return self.data_loader.get_meteo_at_location(meteo_type, lat, lon, year)

    def get_suitability(self, lat: float, lon: float, crop: str, year: int) -> float:
        """Get crop suitability at location and year.

        Args:
            lat: Latitude
            lon: Longitude
            crop: Crop name
            year: Year

        Returns:
            Suitability score (0-1)
        """
        return self.data_loader.get_suitability_at_location(crop, lat, lon, year)

    def get_expected_yield(self, crop: str, year: int) -> float:
        """Get expected yield for crop in year from AquaCrop data.

        Args:
            crop: Crop name
            year: Year

        Returns:
            Expected yield in tons/hectare (returns 2.5 default)
        """
        # TODO: Load from AquaCrop_Results CSV files
        # For now, return reasonable defaults
        if crop == "WHEAT":
            return 2.8  # tons/ha (typical wheat yield)
        elif crop == "MAIZE":
            return 3.5  # tons/ha (typical maize yield)
        else:
            return 2.5

    def _validate_user_locations(self, farmer_locations: list, geojson: dict = None) -> list:
        """
        Validate and snap user-specified farmer locations to LUSA grid.

        Strategy:
        1. Validate coordinates are within bounds (polygon or Thessaloniki)
        2. Snap to nearest LUSA pixel (data alignment)
        3. Add small random offset (±0.01°) for visual variety
        4. Ensure snap distance is reasonable (<0.1°)

        Args:
            farmer_locations: List of {"lat": float, "lon": float, "crop": str}
            geojson: Optional GeoJSON for polygon validation

        Returns:
            List of (lat, lon) tuples - SNAPPED to LUSA grid with offsets
        """
        from backend.data.loaders.spatial_filter import point_in_polygon, get_polygon_bounds
        import sys

        # Terminal logging
        sys.stderr.write(f"\n{'='*80}\n")
        sys.stderr.write(f"📍 VALIDATING & SNAPPING USER COORDINATES TO LUSA GRID (CCA)\n")
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
            # No polygon - use full data bounds
            lat_min, lat_max = self.lat_bounds
            lon_min, lon_max = self.lon_bounds
            bounds_desc = f"Thessaloniki data bounds [{lat_min:.1f}, {lat_max:.1f}]°N, [{lon_min:.1f}, {lon_max:.1f}]°E"
            use_polygon = False

        sys.stderr.write(f"Validation bounds: {bounds_desc}\n")
        sys.stderr.flush()

        errors = []
        validated_locs = []

        # Import centralized epsilon configuration
        from backend.config.validation_config import get_coordinate_epsilon
        epsilon = get_coordinate_epsilon()

        # Max distance for snapping to LUSA pixel (0.1° ≈ 11km - one LUSA pixel spacing)
        MAX_SNAP_DISTANCE = 0.1

        # Get first crop's LUSA data for snapping
        first_crop = self.crops[0]
        lusa_data = self.crop_data[first_crop]

        sys.stderr.write(f"\n📍 Processing {len(farmer_locations)} user-specified locations:\n")
        sys.stderr.write(f"{'-'*80}\n")
        sys.stderr.flush()

        for i, loc in enumerate(farmer_locations, 1):
            user_lat, user_lon, crop = loc['lat'], loc['lon'], loc['crop']
            location_errors = []

            sys.stderr.write(f"\nLocation {i}: User requested ({user_lat}, {user_lon}) for {crop}\n")
            sys.stderr.flush()

            # Check latitude bounds (with epsilon tolerance for boundary points)
            if not (lat_min - epsilon <= user_lat <= lat_max + epsilon):
                location_errors.append(f"latitude {user_lat}° outside range [{lat_min:.4f}°, {lat_max:.4f}°]")

            # Check longitude bounds (with epsilon tolerance for boundary points)
            if not (lon_min - epsilon <= user_lon <= lon_max + epsilon):
                location_errors.append(f"longitude {user_lon}° outside range [{lon_min:.4f}°, {lon_max:.4f}°]")

            # Check crop name
            if crop.upper() not in self.crops:
                location_errors.append(f"invalid crop '{crop}' (valid: {', '.join(self.crops)})")

            # If basic validation failed, skip snapping
            if location_errors:
                errors.append(f"Location {i}: {'; '.join(location_errors)}")
                sys.stderr.write(f"  ❌ Validation failed: {'; '.join(location_errors)}\n")
                sys.stderr.flush()
                continue

            # ========== SNAP TO NEAREST LUSA PIXEL ==========
            # Find nearest LUSA pixel
            lusa_lat_nearest = float(lusa_data.lat.sel(lat=user_lat, method='nearest').values)
            lusa_lon_nearest = float(lusa_data.lon.sel(lon=user_lon, method='nearest').values)

            # Calculate snap distance
            snap_distance = ((lusa_lat_nearest - user_lat)**2 + (lusa_lon_nearest - user_lon)**2)**0.5

            # Validate snap distance
            if snap_distance > MAX_SNAP_DISTANCE:
                location_errors.append(
                    f"too far from LUSA grid - nearest pixel at ({lusa_lat_nearest}, {lusa_lon_nearest}) "
                    f"is {snap_distance:.4f}° away (max: {MAX_SNAP_DISTANCE}°)"
                )
                errors.append(f"Location {i}: {'; '.join(location_errors)}")
                sys.stderr.write(f"  ❌ Snap distance too large: {snap_distance:.4f}° > {MAX_SNAP_DISTANCE}°\n")
                sys.stderr.flush()
                continue

            # Add small random offset for visual variety (±0.001° ≈ ±110m)
            offset_lat = self.random.uniform(-0.001, 0.001)
            offset_lon = self.random.uniform(-0.001, 0.001)

            final_lat = lusa_lat_nearest + offset_lat
            final_lon = lusa_lon_nearest + offset_lon

            # Clamp to bounds to ensure we don't go outside
            final_lat = max(lat_min, min(lat_max, final_lat))
            final_lon = max(lon_min, min(lon_max, final_lon))

            # Round to 4 decimal places
            final_lat = round(final_lat, 4)
            final_lon = round(final_lon, 4)

            # Add to validated list
            validated_locs.append((final_lat, final_lon))

            # Terminal logging
            sys.stderr.write(f"  ✅ {crop.upper():<6} → Snapped to LUSA grid:\n")
            sys.stderr.write(f"     User requested:  ({user_lat:.4f}, {user_lon:.4f})\n")
            sys.stderr.write(f"     LUSA pixel:      ({lusa_lat_nearest:.4f}, {lusa_lon_nearest:.4f})\n")
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

    def __repr__(self):
        return (
            f"LandUseModel(scenario={self.scenario}, "
            f"year={self.current_year}, "
            f"farmers={len(self.farmer_agents)}, "
            f"multi_level={self.enable_multi_level})"
        )
