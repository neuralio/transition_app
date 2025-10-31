"""Irrigation Use Case - Agent-Based Models

This module provides irrigation-specific agents that extend the base MLU agents.
All agents inherit from existing TRANSITION agents to avoid code duplication.
"""

from .land_parcel_agent_irrigation import LandParcelAgentIrrigation
from .water_cooperative_agent import WaterCooperativeAgent
from .water_authority_agent import WaterAuthorityAgent

__all__ = [
    "LandParcelAgentIrrigation",
    "WaterCooperativeAgent",
    "WaterAuthorityAgent"
]
