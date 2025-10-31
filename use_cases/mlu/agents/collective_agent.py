"""Community Level Agent - Farmer Collectives/Cooperatives."""

import mesa


class CollectiveAgent(mesa.Agent):
    """
    Community Level agent representing farmer collectives/cooperatives.

    Aggregates individual farmer decisions, facilitates resource sharing,
    and mediates between individuals and market/policy levels.
    """

    def __init__(self,
                 model,
                 region_name,
                 member_farmers):
        """Initialize collective agent.

        Args:
            model: Mesa model instance
            region_name: Name/ID of the region
            member_farmers: List of FarmerAgent instances in this collective
        """
        super().__init__(model)
        self.region_name = region_name
        self.members = member_farmers  # List of FarmerAgent instances

        # Community state
        self.collective_crop_preference = None  # Dominant crop in community
        self.knowledge_pool = set()  # Shared knowledge/practices
        self.collective_wealth = 0.0  # Pooled resources
        self.social_norms = {}  # Shared norms (e.g., {'risk_aversion': 0.6})

        # Interaction buffers
        self.market_signals = {}  # Signals received from market level
        self.policy_signals = {}  # Signals received from policy level

        # Register members
        for farmer in self.members:
            farmer.collective = self  # Bidirectional link

    def perceive_from_market(self, market_signals):
        """
        Receive downward signals from Market Level.

        Args:
            market_signals: Dict with price signals, demand forecasts
        """
        self.market_signals = market_signals

    def perceive_from_policy(self, policy_signals):
        """
        Receive downward signals from Policy Level.

        Args:
            policy_signals: Dict with regulations, subsidies, incentives
        """
        self.policy_signals = policy_signals

    def aggregate_member_decisions(self):
        """
        Aggregate upward from Individual Level.

        Collects individual farmer decisions and computes community statistics.
        Uses REAL production and income data from farmers.
        """
        if not self.members:
            return

        # Count crop choices
        crop_counts = {}
        for farmer in self.members:
            if farmer.current_crop:
                crop_counts[farmer.current_crop] = crop_counts.get(farmer.current_crop, 0) + 1

        # Dominant crop becomes collective preference
        if crop_counts:
            self.collective_crop_preference = max(crop_counts, key=crop_counts.get)

        # Aggregate wealth using REAL farmer income data
        self.collective_wealth = sum(farmer.annual_income for farmer in self.members)

        # Aggregate production by crop (tons)
        self.crop_production = {}  # Total production by crop
        for farmer in self.members:
            if farmer.current_crop:
                econ_state = farmer.get_economic_state()
                crop = econ_state['crop']
                production = econ_state['total_production']  # tons
                self.crop_production[crop] = self.crop_production.get(crop, 0.0) + production

    def broadcast_to_members(self):
        """
        Broadcast downward to Individual Level members.

        Shares market/policy signals and social norms with member farmers.
        """
        for farmer in self.members:
            # Share collective knowledge
            farmer.receive_community_signals({
                'market_signals': self.market_signals,
                'policy_signals': self.policy_signals,
                'social_norms': self.social_norms,
                'collective_preference': self.collective_crop_preference
            })

    def lateral_influence(self, other_collectives):
        """
        Lateral interaction with neighboring collectives (within Community Level).

        Args:
            other_collectives: List of CollectiveAgent instances
        """
        # Share knowledge with neighboring collectives
        for other in other_collectives:
            if other.unique_id != self.unique_id:
                # Knowledge diffusion
                self.knowledge_pool.update(other.knowledge_pool)

    def report_to_market(self):
        """
        Report upward to Market Level.

        Returns:
            Dict with aggregate production, demand, etc. (REAL data from farmers)
        """
        return {
            'collective_id': self.unique_id,
            'region': self.region_name,
            'num_farmers': len(self.members),
            'dominant_crop': self.collective_crop_preference,
            'collective_wealth': self.collective_wealth,  # Real aggregated income
            'crop_production': getattr(self, 'crop_production', {})  # Real production (tons)
        }

    def step(self):
        """Execute one community-level timestep."""
        # 1. Aggregate member decisions (upward flow)
        self.aggregate_member_decisions()

        # 2. Update social norms based on collective behavior
        self._update_social_norms()

        # 3. Broadcast signals to members (downward flow)
        self.broadcast_to_members()

    def _update_social_norms(self):
        """Update community social norms based on member behaviors."""
        if not self.members:
            return

        # Example: Risk aversion norm based on crop diversity
        crop_types = len(set(f.current_crop for f in self.members if f.current_crop))
        # High diversity = lower risk aversion
        self.social_norms['risk_aversion'] = max(0.2, 1.0 - (crop_types / 10.0))

    def __repr__(self):
        return f"Collective({self.unique_id}, region={self.region_name}, members={len(self.members)})"
