"""Water Cooperative Agent for Irrigation Use Case

Extends MLU CollectiveAgent with:
- Aggregation of irrigation water demand from farmers
- Distribution of available water resources
- Coordination with Water Authority for allocation
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from use_cases.mlu.agents.collective_agent import CollectiveAgent


class WaterCooperativeAgent(CollectiveAgent):
    """
    Water cooperative agent (Community Level).

    Inherits from MLU CollectiveAgent and adds:
    - Aggregation of irrigation water demand
    - Water distribution logic
    - Drought response strategies
    """

    def __init__(self, model, region_name, member_farmers):
        """Initialize water cooperative agent.

        Args:
            model: Mesa model instance
            region_name: Name/ID of the water cooperative region
            member_farmers: List of LandParcelAgentIrrigation instances
        """
        # Call parent constructor
        super().__init__(model, region_name, member_farmers)

        # Irrigation-specific attributes
        self.total_water_demand_m3 = 0.0  # Aggregated water demand (cubic meters)
        self.total_water_allocated_m3 = 0.0  # Water allocated by authority
        self.total_water_distributed_m3 = 0.0  # Water actually distributed to farmers
        self.water_allocation_efficiency = 1.0  # Distribution efficiency (0-1)

        # Drought management
        self.is_drought = False  # Set by Water Authority
        self.drought_reduction_factor = 1.0  # Reduce allocation during drought (e.g., 0.7 = 70%)

    def aggregate_water_demand(self):
        """
        Aggregate irrigation water demand from member farmers (upward flow).

        Computes total water needs for the cooperative region.
        """
        if not self.members:
            return

        total_demand_mm = 0.0  # millimeters
        total_area_ha = 0.0    # hectares

        for farmer in self.members:
            economic_state = farmer.get_economic_state()
            water_demand_mm = economic_state.get('annual_water_demand_mm', 0.0)
            area_ha = economic_state.get('land_hectares', 10.0)

            total_demand_mm += water_demand_mm
            total_area_ha += area_ha

        # Convert to cubic meters: (mm * ha * 10) = m³
        # 1 mm over 1 ha = 10 m³
        self.total_water_demand_m3 = total_demand_mm * total_area_ha * 10.0

    def distribute_water_to_farmers(self):
        """
        Distribute allocated water to member farmers (downward flow).

        Distributes water based on:
        - Farmer's individual demand
        - Available allocation from Water Authority
        - Drought reduction factor
        """
        if not self.members or self.total_water_demand_m3 == 0:
            return

        # Calculate distribution ratio
        if self.total_water_allocated_m3 >= self.total_water_demand_m3:
            # Sufficient water: full allocation
            distribution_ratio = 1.0
        else:
            # Water scarcity: proportional reduction
            distribution_ratio = self.total_water_allocated_m3 / self.total_water_demand_m3

        # Apply drought reduction if active
        distribution_ratio *= self.drought_reduction_factor

        total_distributed = 0.0

        for farmer in self.members:
            economic_state = farmer.get_economic_state()
            demand_mm = economic_state.get('annual_water_demand_mm', 0.0)
            area_ha = economic_state.get('land_hectares', 10.0)

            # Calculate allocated water for this farmer
            farmer_demand_m3 = demand_mm * area_ha * 10.0
            allocated_m3 = farmer_demand_m3 * distribution_ratio

            # Convert back to mm
            allocated_mm = allocated_m3 / (area_ha * 10.0) if area_ha > 0 else 0.0

            # Update farmer's water supply
            farmer.actual_water_supplied_mm = allocated_mm
            total_distributed += allocated_m3

        self.total_water_distributed_m3 = total_distributed

    def receive_water_allocation(self, allocated_m3, is_drought=False, drought_factor=1.0):
        """
        Receive water allocation from Water Authority (downward flow).

        Args:
            allocated_m3: Water allocation in cubic meters
            is_drought: Whether drought conditions are active
            drought_factor: Drought reduction factor (0-1)
        """
        self.total_water_allocated_m3 = allocated_m3
        self.is_drought = is_drought
        self.drought_reduction_factor = drought_factor

    def report_to_authority(self):
        """
        Report to Water Authority (upward flow).

        Returns:
            Dict with water demand and usage statistics
        """
        return {
            'cooperative_id': self.unique_id,
            'region': self.region_name,
            'num_farmers': len(self.members),
            'total_water_demand_m3': self.total_water_demand_m3,
            'total_water_allocated_m3': self.total_water_allocated_m3,
            'total_water_distributed_m3': self.total_water_distributed_m3,
            'allocation_efficiency': self.water_allocation_efficiency,
            'dominant_crop': self.collective_crop_preference  # From parent class
        }

    def step(self):
        """Execute one community-level timestep with irrigation logic."""
        # 1. Aggregate water demand from farmers (upward flow)
        self.aggregate_water_demand()

        # 2. Call parent step() for standard collective behavior
        super().step()

        # 3. Distribute allocated water to farmers (downward flow)
        self.distribute_water_to_farmers()

    def __repr__(self):
        return f"WaterCooperative({self.unique_id}, region={self.region_name}, demand={self.total_water_demand_m3:.0f}m³)"
