"""Multi-Level Orchestrator for ML-ABM cross-scale interactions.

=== IMPORTANT: WHAT IS THE ORCHESTRATOR? ===

The orchestrator is a COORDINATION MANAGER (NOT a decision-maker).

PURPOSE:
    - Executes agent steps in a SPECIFIC ORDER to ensure proper information flows
    - Does NOT make decisions (agents make their own decisions)
    - Simply CALLS agent methods in the correct sequence

WHY WE NEED IT:
    - Mesa's built-in self.agents.shuffle_do("step") activates ALL agents RANDOMLY
    - But Multi-Level ABM requires ORDERED execution for cascading effects
    - Example: Policies MUST set subsidies BEFORE markets update prices
              Markets MUST update prices BEFORE farmers make decisions

WHAT IT DOES (in step_all_levels):
    1. Calls policy agents → generate regulations (subsidies, price controls)
    2. Passes regulations DOWN to market agents
    3. Market agents update prices, pass signals DOWN to communities
    4. Communities broadcast signals DOWN to farmers
    5. Farmers make decisions using all received signals
    6. Results flow UPWARD: Farmers → Communities → Markets → Policies
    7. Agents interact LATERALLY with peers at same level

MESA COMPATIBILITY:
    - Mesa does NOT have built-in orchestrator support
    - This is a CUSTOM pattern for managing multi-level complexity
    - Without it, we'd need complex conditional logic in model.step()
    - The orchestrator encapsulates execution order in one reusable class
"""


class MultiLevelOrchestrator:
    """
    Orchestrates cross-level interactions in Multi-Level ABM.

    This is a COORDINATION MANAGER that ensures agents execute in the correct
    order for proper information cascading. IT DOES NOT MAKE DECISIONS.

    Manages three types of flows:
    1. Downward: Policy → Market → Community → Individual (top-down influence)
    2. Upward: Individual → Community → Market → Policy (bottom-up aggregation)
    3. Lateral: Within-level peer interactions (knowledge sharing, arbitrage)
    """

    def __init__(self, model):
        """Initialize orchestrator.

        Args:
            model: LandUseModel instance containing all agent levels
        """
        self.model = model

    def step_all_levels(self):
        """
        Execute one complete multi-level timestep.

        Order:
        1. Policy agents step and generate regulations
        2. Market agents receive policy signals and step
        3. Community agents receive market signals and step
        4. Individual farmers receive community signals and step
        5. Upward aggregation flows back through levels
        6. Lateral interactions within each level
        """
        # === DOWNWARD FLOW (Top-Down) ===

        # 1. Policy Level: Generate regulations
        for policy_agent in self.model.policy_agents:
            policy_agent.step()

        # 2. Market Level: Receive policy signals
        policy_regulations = {}
        if self.model.policy_agents:
            # Aggregate all policy regulations
            for policy_agent in self.model.policy_agents:
                policy_regulations.update(policy_agent.get_policy_regulations())

        for market_agent in self.model.market_agents:
            market_agent.perceive_from_policy(policy_regulations)
            market_agent.step()

        # 2b. PV Developer Level (Market-level): Receive policy incentives
        if hasattr(self.model, 'pv_developer_agents') and self.model.pv_developer_agents:
            for pv_dev in self.model.pv_developer_agents:
                pv_dev.perceive_from_policy(policy_regulations)
                pv_dev.step()

        # 3. Community Level: Receive market signals
        market_signals = {}
        if self.model.market_agents:
            # Use first market's signals (can be extended for multiple markets)
            market_signals = self.model.market_agents[0].get_market_signals()

        for collective_agent in self.model.collective_agents:
            collective_agent.perceive_from_market(market_signals)
            collective_agent.perceive_from_policy(policy_regulations)

        # 4. Individual Level: Receive community signals (via collectives)
        # Broadcast happens in collective.step()

        # Step community agents
        for collective_agent in self.model.collective_agents:
            collective_agent.step()

        # Step individual farmers (already receive signals from collectives)
        self.model.agents.shuffle_do("step")

        # === UPWARD FLOW (Bottom-Up Aggregation) ===

        # 1. Community → Market: Report aggregate outcomes
        community_reports = []
        for collective_agent in self.model.collective_agents:
            report = collective_agent.report_to_market()
            community_reports.append(report)

        # Markets aggregate community reports
        for market_agent in self.model.market_agents:
            market_agent.aggregate_from_communities(community_reports)

        # 2. Market → Policy: Report market outcomes
        market_reports = []
        for market_agent in self.model.market_agents:
            report = market_agent.report_to_policy()
            market_reports.append(report)

        # 2b. PV Developers → Policy: Report PV installations
        pv_reports = []
        if hasattr(self.model, 'pv_developer_agents') and self.model.pv_developer_agents:
            for pv_dev in self.model.pv_developer_agents:
                pv_reports.append(pv_dev.get_pv_report())

        # Policies evaluate effectiveness (including PV adoption)
        for policy_agent in self.model.policy_agents:
            policy_agent.perceive_from_markets(market_reports)
            if pv_reports and hasattr(policy_agent, 'perceive_pv_reports'):
                policy_agent.perceive_pv_reports(pv_reports)

        # === LATERAL FLOW (Within-Level Interactions) ===

        # Individual level: Peer influence (via PECS.social in full implementation)
        # Currently handled implicitly through collective membership

        # Community level: Knowledge sharing between collectives
        if len(self.model.collective_agents) > 1:
            for collective_agent in self.model.collective_agents:
                other_collectives = [
                    c for c in self.model.collective_agents
                    if c.unique_id != collective_agent.unique_id
                ]
                collective_agent.lateral_influence(other_collectives)

        # Market level: Price arbitrage between markets
        if len(self.model.market_agents) > 1:
            for market_agent in self.model.market_agents:
                other_markets = [
                    m for m in self.model.market_agents
                    if m.unique_id != market_agent.unique_id
                ]
                market_agent.lateral_influence(other_markets)

        # PV Developer level: Knowledge sharing about best locations
        if hasattr(self.model, 'pv_developer_agents') and len(self.model.pv_developer_agents) > 1:
            for pv_dev in self.model.pv_developer_agents:
                other_pvs = [
                    p for p in self.model.pv_developer_agents
                    if p.unique_id != pv_dev.unique_id
                ]
                # PV developers share information about successful locations
                # (lateral_influence could be added to PVDeveloperAgent if needed)

        # Policy level: Policy coordination
        if len(self.model.policy_agents) > 1:
            for policy_agent in self.model.policy_agents:
                other_policies = [
                    p for p in self.model.policy_agents
                    if p.unique_id != policy_agent.unique_id
                ]
                policy_agent.lateral_influence(other_policies)

    def get_interaction_summary(self):
        """
        Get summary of cross-level interactions.

        Returns:
            Dict with interaction statistics
        """
        summary = {
            'num_individuals': len(self.model.agents),
            'num_communities': len(self.model.collective_agents),
            'num_markets': len(self.model.market_agents),
            'num_policies': len(self.model.policy_agents),
            'year': self.model.current_year
        }

        if hasattr(self.model, 'pv_developer_agents'):
            summary['num_pv_developers'] = len(self.model.pv_developer_agents)

        return summary
