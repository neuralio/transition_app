"""
RL Policy Wrapper for RL-02: Adaptive Agricultural Agents

Loads trained RL models and provides decision-making interface for LandParcelAgent.
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any


class RLPolicy:
    """Wrapper for trained RL policy (PPO, DQN, etc.)."""

    def __init__(self, model_path: str, framework: str = "sb3"):
        """
        Initialize RL policy from trained model.

        Args:
            model_path: Path to saved model (.zip for SB3)
            framework: Framework used ("sb3" for Stable-Baselines3)
        """
        self.model_path = Path(model_path)
        self.framework = framework

        if not self.model_path.exists():
            raise FileNotFoundError(f"RL model not found: {model_path}")

        # Load model
        if framework == "sb3":
            from stable_baselines3 import PPO
            self.model = PPO.load(str(model_path))
            print(f"✅ Loaded RL policy from {model_path}")
        else:
            raise ValueError(f"Unsupported framework: {framework}")

    def predict_action(
        self,
        observation: np.ndarray,
        deterministic: bool = True,
        debug: bool = False
    ) -> int:
        """
        Predict action given observation.

        Args:
            observation: State observation (11D vector for RL-02)
            deterministic: If True, use deterministic policy (no exploration)
            debug: If True, print observation and action

        Returns:
            action: 0=WHEAT, 1=MAIZE, 2=SOLAR
        """
        action, _states = self.model.predict(observation, deterministic=deterministic)

        if debug:
            print(f"  OBS: LUSA(W={observation[0]:.1f}, M={observation[1]:.1f}, S={observation[2]:.1f}) "
                  f"Weather(T={observation[3]:.1f}, P={observation[4]:.1f}, SR={observation[5]:.2f}) "
                  f"Prices(W={observation[7]:.0f}, M={observation[8]:.0f}, E={observation[9]:.2f}) "
                  f"Sub={observation[10]:.2f} → Action={int(action)}")

        return int(action)

    def predict_batch(
        self,
        observations: np.ndarray,
        deterministic: bool = True
    ) -> np.ndarray:
        """
        Predict actions for batch of observations.

        Args:
            observations: Batch of state observations (N x 11)
            deterministic: If True, use deterministic policy

        Returns:
            actions: Array of actions (N,)
        """
        actions = []
        for obs in observations:
            action = self.predict_action(obs, deterministic=deterministic)
            actions.append(action)
        return np.array(actions)


def create_observation_from_agent(
    agent,
    model,
    year: int
) -> np.ndarray:
    """
    Create RL observation vector from LandParcelAgent state.

    Args:
        agent: LandParcelAgent instance
        model: LandUseModel instance
        year: Current simulation year

    Returns:
        observation: 11D vector for RL policy
        [lusa_wheat, lusa_maize, lusa_solar, temp, precip,
         solar_rad, soil_quality, wheat_price, maize_price,
         elec_price, subsidy]
    """
    # Get LUSA scores
    lusa_wheat = agent.wheat_suitability
    lusa_maize = agent.maize_suitability
    lusa_solar = agent.solar_suitability

    # Get environmental data
    temp = agent.temperature if hasattr(agent, 'temperature') else 15.0
    precip = agent.precipitation if hasattr(agent, 'precipitation') else 50.0
    solar_rad = agent.solar_radiation if hasattr(agent, 'solar_radiation') else 2.5
    soil_quality = agent.soil_quality

    # Get economic data (from market agent if available)
    wheat_price = 200.0  # Default
    maize_price = 180.0
    elec_price = 0.15

    if hasattr(model, 'market_agents') and len(model.market_agents) > 0:
        market = model.market_agents[0]
        wheat_price = market.prices.get('wheat', 200.0)
        maize_price = market.prices.get('maize', 180.0)

    # Get policy data (from policymaker agent if available)
    subsidy = 0.20  # Default

    if hasattr(model, 'policymaker_agents') and len(model.policymaker_agents) > 0:
        policy = model.policymaker_agents[0]
        subsidy = policy.subsidies.get('solar', 0.20)

    # Construct observation vector
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


if __name__ == "__main__":
    # Test RL policy loading
    import sys

    if len(sys.argv) < 2:
        print("Usage: python rl_policy.py <path_to_model.zip>")
        sys.exit(1)

    model_path = sys.argv[1]

    print("=" * 60)
    print("RL POLICY WRAPPER TEST")
    print("=" * 60)

    # Load policy
    policy = RLPolicy(model_path)

    # Test with dummy observation
    obs = np.array([
        50.0,  # wheat LUSA
        45.0,  # maize LUSA
        60.0,  # solar LUSA
        15.0,  # temp
        50.0,  # precip
        2.5,   # solar_rad
        250.0, # soil
        200.0, # wheat_price
        180.0, # maize_price
        0.15,  # elec_price
        0.20   # subsidy
    ], dtype=np.float32)

    print(f"\nTest observation: {obs}")
    action = policy.predict_action(obs)
    action_names = {0: "WHEAT", 1: "MAIZE", 2: "SOLAR"}
    print(f"Predicted action: {action} ({action_names[action]})")

    print("\n✅ Policy wrapper test complete!")
