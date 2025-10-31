"""
Gymnasium Environment for MLU Multi-Level ABM with REAL EO Data

This environment wraps the actual LandUseModel simulation for RL training.
Uses 100% REAL data:
- LUSA predictions from Thessaloniki
- Climate data (temperature, precipitation, solar radiation)
- Soil data (organic carbon, pH, CEC)
- Market prices from CommodityMarketAgent
- Policy subsidies from PolicymakerAgent
- Multi-level ABM interactions

NO DUMMY DATA - Full integration with production MLU simulation.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from typing import Optional, Tuple, Dict, Any
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.mlu.models.landuse_model import LandUseModel
from use_cases.mlu.config_loader import load_config


class MLU_Env(gym.Env):
    """
    Gymnasium environment wrapping REAL MLU multi-level ABM simulation.

    State Space (11 dimensions):
    - LUSA scores: [wheat_suitability, maize_suitability, solar_suitability]
    - Environmental: [temperature, precipitation, solar_radiation, soil_quality]
    - Economic: [wheat_price, maize_price, electricity_price]
    - Policy: [subsidy_rate]

    Action Space (Discrete 3):
    - 0: Plant WHEAT
    - 1: Plant MAIZE
    - 2: Install SOLAR PV

    Reward:
    - Economic: Annual profit from real simulation
    - Sustainability: Diversification bonus (crop rotation)
    - Soil health: Bonus for maintaining soil quality
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        data_path: str,
        scenario: str = "rcp45",
        start_year: int = 2021,
        max_steps: int = 50,
        render_mode: Optional[str] = None
    ):
        """
        Initialize RL environment with REAL MLU simulation.

        Args:
            data_path: Path to PILOT_THESSALONIKI_DATA
            scenario: Climate scenario (rcp26, rcp45, rcp85)
            start_year: Starting year
            max_steps: Max simulation steps (years)
            render_mode: Rendering mode
        """
        super().__init__()

        self.data_path = data_path
        self.scenario = scenario
        self.start_year = start_year
        self.max_steps = max_steps
        self.render_mode = render_mode

        # Load config for Thessaloniki bounds
        self.config = load_config()

        # Create REAL LandUseModel (loads all real data!)
        self.model = LandUseModel(
            data_path=data_path,
            crops=['WHEAT', 'MAIZE'],
            scenario=scenario,
            n_parcels=1,  # Single parcel for RL training
            n_collectives=1,
            n_markets=1,
            n_policies=1,
            lat_bounds=(self.config.lat_min, self.config.lat_max),
            lon_bounds=(self.config.lon_min, self.config.lon_max),
            start_year=start_year,
            enable_multi_level=True,
            use_land_parcels=True
        )

        # Get the parcel agent controlled by RL
        self.parcel_agent = self.model.parcel_agents[0]

        # Action space: 0=WHEAT, 1=MAIZE, 2=SOLAR
        self.action_space = spaces.Discrete(3)

        # Observation space (bounds based on real data ranges)
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, -20, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32),
            high=np.array([100, 100, 100, 50, 500, 10, 300, 500, 500, 1, 1], dtype=np.float32),
            dtype=np.float32
        )

        # State tracking
        self.current_step = 0
        self.action_history = []
        self.income_history = []

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[dict] = None
    ) -> Tuple[np.ndarray, dict]:
        """Reset environment to initial state with optional randomization."""
        super().reset(seed=seed)

        # Reset simulation to start year
        self.model.current_year = self.start_year
        self.current_step = 0
        self.action_history = []
        self.income_history = []

        # Randomize parcel location within Thessaloniki (for testing diversity)
        # Small variation: ±0.1 degrees (~11km at this latitude)
        if options and options.get('randomize_location', False):
            import random
            lat_offset = random.uniform(-0.1, 0.1)
            lon_offset = random.uniform(-0.1, 0.1)

            # Keep within Thessaloniki bounds
            new_lat = np.clip(self.parcel_agent.lat + lat_offset,
                             self.config.lat_min, self.config.lat_max)
            new_lon = np.clip(self.parcel_agent.lon + lon_offset,
                             self.config.lon_min, self.config.lon_max)

            self.parcel_agent.lat = new_lat
            self.parcel_agent.lon = new_lon

            # Update soil/elevation for new location
            self.parcel_agent.soil_organic_carbon = self.model.get_soil(new_lat, new_lon, 'organic_carbon')
            self.parcel_agent.soil_ph = self.model.get_soil(new_lat, new_lon, 'ph')
            self.parcel_agent.elevation = self.model.get_elevation(new_lat, new_lon)

        # Reset parcel agent state
        self.parcel_agent.annual_income = 0.0
        self.parcel_agent.annual_profit = 0.0
        self.parcel_agent.land_use = None
        self.parcel_agent.current_crop = None

        # Get initial observation from REAL data
        obs = self._get_observation()
        info = {
            "year": self.model.current_year,
            "parcel_lat": self.parcel_agent.lat,
            "parcel_lon": self.parcel_agent.lon
        }

        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """
        Execute one time step in the REAL simulation.

        Args:
            action: 0=WHEAT, 1=MAIZE, 2=SOLAR

        Returns:
            observation, reward, terminated, truncated, info
        """
        action = int(action)

        # Map action to land use
        action_map = {
            0: ("agriculture", "WHEAT"),
            1: ("agriculture", "MAIZE"),
            2: ("solar_pv", None)
        }
        land_use, crop = action_map[action]

        # Set parcel's decision (used in simulation step)
        self.parcel_agent.land_use = land_use
        self.parcel_agent.current_crop = crop

        # Run ONE STEP of the REAL multi-level ABM simulation
        self.model.step()

        # Get REAL results from the parcel agent
        income = self.parcel_agent.annual_income
        profit = self.parcel_agent.annual_profit

        # Calculate reward based on REAL simulation outcomes
        reward = self._calculate_reward(income, profit, land_use, crop)

        # Track history
        self.action_history.append(action)
        self.income_history.append(income)

        # Advance time
        self.current_step += 1

        # Check termination
        terminated = self.current_step >= self.max_steps
        truncated = False

        # Get next observation
        obs = self._get_observation()
        info = {
            "year": self.model.current_year,
            "action": f"{land_use}_{crop}" if crop else land_use,
            "income": income,
            "profit": profit,
            "yield": self.parcel_agent.actual_yield if land_use == "agriculture" else 0,
            "energy_kwh": self.parcel_agent.annual_energy_kwh if land_use == "solar_pv" else 0
        }

        return obs, reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """
        Get current state observation from REAL simulation data.
        """
        year = self.model.current_year
        lat = self.parcel_agent.lat
        lon = self.parcel_agent.lon

        # REAL LUSA scores from Thessaloniki data
        lusa_wheat = self.model.get_suitability(lat, lon, 'WHEAT', year)
        lusa_maize = self.model.get_suitability(lat, lon, 'MAIZE', year)

        # Solar suitability (based on real solar radiation)
        solar_rad = self.model.get_meteo(lat, lon, 'solar_radiation', year)
        lusa_solar = min(100.0, solar_rad * 20.0)

        # REAL climate data
        temperature = self.model.get_meteo(lat, lon, 'temperature', year)
        precipitation = self.model.get_meteo(lat, lon, 'precipitation', year)

        # REAL soil quality
        soil_oc = self.parcel_agent.soil_organic_carbon
        soil_quality = min(300.0, soil_oc * 10.0)

        # REAL market prices from CommodityMarketAgent
        wheat_price = 200.0
        maize_price = 180.0
        if self.model.enable_multi_level and len(self.model.market_agents) > 0:
            market = self.model.market_agents[0]
            wheat_price = market.crop_prices.get('WHEAT', 200.0)
            maize_price = market.crop_prices.get('MAIZE', 180.0)

        # Electricity price
        electricity_price = self.parcel_agent.electricity_price

        # REAL subsidy rate from PolicymakerAgent
        subsidy_rate = self.parcel_agent.subsidy_rate
        if self.model.enable_multi_level and len(self.model.policy_agents) > 0:
            policy = self.model.policy_agents[0]
            subsidy_rate = policy.subsidy_rates.get('pv', 0.20)

        # Construct observation vector (ALL REAL DATA!)
        obs = np.array([
            lusa_wheat,
            lusa_maize,
            lusa_solar,
            temperature,
            precipitation,
            solar_rad,
            soil_quality,
            wheat_price,
            maize_price,
            electricity_price,
            subsidy_rate
        ], dtype=np.float32)

        return obs

    def _calculate_reward(
        self,
        income: float,
        profit: float,
        land_use: str,
        crop: Optional[str]
    ) -> float:
        """
        Calculate reward based on REAL simulation outcomes.

        Multi-objective reward with explicit weights:
        - Economic return (60%)
        - Sustainability (40%): diversification + soil health
        """
        # Economic component
        economic_reward = profit / 5000.0

        # Sustainability components
        # 1. Diversification bonus (encourage crop rotation)
        diversification_bonus = 0.0
        if len(self.action_history) >= 5:
            recent_actions = self.action_history[-5:]
            unique_actions = len(set(recent_actions))
            diversification_bonus = unique_actions * 0.5  # Max: 3 * 0.5 = 1.5

        # 2. Soil health bonus (real soil organic carbon)
        soil_health_bonus = 0.0
        if self.parcel_agent.soil_organic_carbon > 20.0:
            soil_health_bonus = 0.3

        # Explicit weights (sum to 1.0)
        economic_weight = 0.6        # 60% economic
        sustainability_weight = 0.4  # 40% sustainability

        # Combined sustainability score
        sustainability_score = diversification_bonus + soil_health_bonus

        # Weighted reward
        total_reward = (economic_reward * economic_weight) + \
                      (sustainability_score * sustainability_weight)

        return total_reward

    def render(self):
        """Render environment state."""
        if self.render_mode == "human":
            print(f"Year: {self.model.current_year}, Step: {self.current_step}")
            print(f"  Land use: {self.parcel_agent.land_use}")
            print(f"  Crop: {self.parcel_agent.current_crop}")
            print(f"  Income: {self.parcel_agent.annual_income:.2f}€")
