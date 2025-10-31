"""Water Authority Agent for Irrigation Use Case

Extends MLU PolicymakerAgent with:
- Water allocation policies (instead of crop subsidies)
- Drought monitoring and response
- Sustainable water management goals
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from use_cases.mlu.agents.policymaker_agent import PolicymakerAgent


class WaterAuthorityAgent(PolicymakerAgent):
    """
    Water authority agent (Policy Level).

    Inherits from MLU PolicymakerAgent and adapts it for water management:
    - Water allocation instead of crop subsidies
    - Drought monitoring and response
    - Sustainable water use goals
    """

    def __init__(self, model, authority_name, policy_goals):
        """Initialize water authority agent.

        Args:
            model: Mesa model instance
            authority_name: Name/ID of the water authority
            policy_goals: Dict of water management objectives
                         e.g., {'water_sustainability': 0.8, 'farmer_welfare': 0.7}
        """
        # Call parent constructor
        super().__init__(model, authority_name, policy_goals)

        # Water-specific attributes
        self.total_water_available_m3 = 0.0  # Available water resources
        self.total_water_allocated_m3 = 0.0  # Total allocation to cooperatives
        self.total_water_demand_m3 = 0.0     # Total demand from cooperatives

        # Drought management
        self.drought_threshold_deficit = 0.3  # Declare drought if demand > supply * 1.3
        self.is_drought_active = False
        self.drought_reduction_factor = 1.0  # Reduction during drought (e.g., 0.7 = 70% allocation)

        # Sustainability metrics
        self.water_use_efficiency = 0.0  # Allocated / Demand
        self.sustainability_score = 0.0  # Based on renewable water use

        # Reports from cooperatives
        self.cooperative_reports = []

    def perceive_from_cooperatives(self, cooperative_reports):
        """
        Receive upward signals from Water Cooperatives.

        Args:
            cooperative_reports: List of dicts from WaterCooperativeAgent.report_to_authority()
        """
        self.cooperative_reports = cooperative_reports

        # Aggregate total water demand
        self.total_water_demand_m3 = sum(
            report.get('total_water_demand_m3', 0.0)
            for report in cooperative_reports
        )

    def evaluate_drought_conditions(self):
        """
        Evaluate whether drought conditions exist.

        Drought declared if:
        - Total demand > Available water * drought_threshold_deficit
        """
        if self.total_water_available_m3 == 0:
            return

        demand_ratio = self.total_water_demand_m3 / self.total_water_available_m3

        if demand_ratio > (1.0 + self.drought_threshold_deficit):
            # Drought conditions
            self.is_drought_active = True
            # Implement proportional reduction
            self.drought_reduction_factor = min(0.7, self.total_water_available_m3 / self.total_water_demand_m3)
        else:
            # Normal conditions
            self.is_drought_active = False
            self.drought_reduction_factor = 1.0

    def allocate_water_to_cooperatives(self):
        """
        Allocate water to cooperatives based on demand and availability.

        Allocation strategies:
        - Normal: Meet full demand if possible
        - Drought: Proportional reduction across all cooperatives
        """
        if not self.cooperative_reports:
            return

        if self.total_water_demand_m3 == 0:
            return

        # Calculate allocation ratio
        if self.total_water_available_m3 >= self.total_water_demand_m3:
            # Sufficient water
            allocation_ratio = 1.0
        else:
            # Water scarcity
            allocation_ratio = self.total_water_available_m3 / self.total_water_demand_m3

        # Apply drought reduction
        allocation_ratio *= self.drought_reduction_factor

        total_allocated = 0.0

        # Allocate to each cooperative proportionally
        for report in self.cooperative_reports:
            cooperative_id = report['cooperative_id']
            demand_m3 = report['total_water_demand_m3']

            allocated_m3 = demand_m3 * allocation_ratio
            total_allocated += allocated_m3

            # Send allocation to cooperative (would be done via model in full implementation)
            # For now, store in policy regulations
            self.regulations[f'cooperative_{cooperative_id}_allocation'] = allocated_m3

        self.total_water_allocated_m3 = total_allocated

    def evaluate_policy_effectiveness(self):
        """
        Evaluate water management policy effectiveness.

        Overrides parent method to focus on water-specific metrics.
        """
        if not self.cooperative_reports:
            return

        # Water use efficiency: How much of demand was met
        if self.total_water_demand_m3 > 0:
            self.water_use_efficiency = min(1.0, self.total_water_allocated_m3 / self.total_water_demand_m3)
        else:
            self.water_use_efficiency = 1.0

        # Sustainability: Are we using water within renewable limits?
        # Simple metric: allocated <= available
        if self.total_water_available_m3 > 0:
            self.sustainability_score = min(1.0, 1.0 - (self.total_water_allocated_m3 / self.total_water_available_m3))
        else:
            self.sustainability_score = 0.0

        # Update policy effectiveness dict (for parent class compatibility)
        self.policy_effectiveness['water_sustainability'] = self.sustainability_score
        self.policy_effectiveness['farmer_welfare'] = self.water_use_efficiency

    def adjust_policies(self):
        """
        Adjust water allocation policies based on effectiveness.

        Could implement:
        - Adaptive drought thresholds
        - Seasonal allocation adjustments
        - Crop-specific water pricing
        """
        # Placeholder for policy adjustment logic
        # In full implementation, would adjust:
        # - drought_threshold_deficit
        # - water_available_m3 (based on reservoir levels, rainfall forecasts)
        # - drought_reduction_factor (more/less strict rationing)
        pass

    def get_water_allocation_regulations(self):
        """
        Generate water allocation regulations for Cooperatives (downward flow).

        Returns:
            Dict with water allocations and drought status
        """
        return {
            'is_drought': self.is_drought_active,
            'drought_reduction_factor': self.drought_reduction_factor,
            'cooperative_allocations': {
                report['cooperative_id']: self.regulations.get(f'cooperative_{report["cooperative_id"]}_allocation', 0.0)
                for report in self.cooperative_reports
            }
        }

    def step(self):
        """Execute one policy-level timestep with water management logic."""
        # 1. Evaluate drought conditions
        self.evaluate_drought_conditions()

        # 2. Allocate water to cooperatives
        self.allocate_water_to_cooperatives()

        # 3. Evaluate policy effectiveness (upward flow analysis)
        self.evaluate_policy_effectiveness()

        # 4. Adjust policies based on evaluation
        self.adjust_policies()

    def initialize_water_resources(self, total_available_m3):
        """
        Initialize available water resources for the authority.

        Args:
            total_available_m3: Total water available for irrigation (cubic meters)
        """
        self.total_water_available_m3 = total_available_m3

    def __repr__(self):
        return f"WaterAuthority({self.unique_id}, name={self.policy_name}, available={self.total_water_available_m3:.0f}m³)"
