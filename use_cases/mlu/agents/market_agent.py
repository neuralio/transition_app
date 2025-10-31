"""Market Level Agent - Commodity Markets and Price Dynamics."""

import mesa


class CommodityMarketAgent(mesa.Agent):
    """
    Market Level agent representing agricultural commodity markets.

    Mediates between Community and Policy levels, handles price formation
    based on supply/demand from communities and regulations from policies.
    """

    def __init__(self,
                 model,
                 market_name,
                 crops,
                 initial_prices=None,
                 initial_demand=None):
        """Initialize market agent.

        Args:
            model: Mesa model instance
            market_name: Name/ID of the market
            crops: List of crop names traded in this market
            initial_prices: Optional dict of initial prices per crop (default: 100.0 for all)
            initial_demand: Optional dict of initial demand per crop (default: 1000.0 for all)
        """
        super().__init__(model)
        self.market_name = market_name
        self.crops = crops

        # Market state - use varied initial prices if provided
        if initial_prices:
            self.crop_prices = initial_prices.copy()
        else:
            self.crop_prices = {crop: 100.0 for crop in crops}  # Base prices
        self.supply = {crop: 0.0 for crop in crops}  # Aggregated supply
        # Use varied initial demand if provided
        if initial_demand:
            self.demand = initial_demand.copy()
        else:
            self.demand = {crop: 1000.0 for crop in crops}  # Market demand
        self.price_history = {crop: [] for crop in crops}

        # Interaction buffers
        self.policy_regulations = {}  # Regulations from policy level
        self.community_reports = []  # Reports from community level

    def perceive_from_policy(self, policy_regulations):
        """
        Receive downward signals from Policy Level.

        Args:
            policy_regulations: Dict with price floors, quotas, tariffs, etc.
        """
        self.policy_regulations = policy_regulations

    def aggregate_from_communities(self, community_reports):
        """
        Aggregate upward from Community Level.

        Args:
            community_reports: List of dicts from CollectiveAgent.report_to_market()
        """
        self.community_reports = community_reports

        # Aggregate supply from all communities (REAL production data)
        self.supply = {crop: 0.0 for crop in self.crops}
        for report in community_reports:
            # Get total production by crop from community
            crop_production = report.get('crop_production', {})  # tons
            for crop, production_tons in crop_production.items():
                if crop in self.supply:
                    self.supply[crop] += production_tons

    def update_prices(self):
        """
        Update crop prices based on supply/demand dynamics.

        Incorporates policy regulations (price floors, etc.).
        """
        for crop in self.crops:
            supply = self.supply.get(crop, 0.0)
            demand = self.demand.get(crop, 1000.0)

            # Simple supply/demand price adjustment
            if supply > 0:
                # Price inversely proportional to supply/demand ratio
                price_ratio = demand / (supply + 1e-6)  # Avoid division by zero
                new_price = self.crop_prices[crop] * (1 + 0.1 * (price_ratio - 1))
            else:
                # No supply = price increase
                new_price = self.crop_prices[crop] * 1.05

            # Apply policy regulations
            price_floor = self.policy_regulations.get(f'{crop}_price_floor', 0)
            price_ceiling = self.policy_regulations.get(f'{crop}_price_ceiling', float('inf'))
            new_price = max(price_floor, min(price_ceiling, new_price))

            # Clamp to reasonable bounds
            new_price = max(10.0, min(500.0, new_price))

            self.crop_prices[crop] = new_price
            self.price_history[crop].append(new_price)

    def get_market_signals(self):
        """
        Generate market signals for Community Level (downward flow).

        Returns:
            Dict with price signals and market conditions
        """
        return {
            'crop_prices': self.crop_prices.copy(),
            'supply': self.supply.copy(),
            'demand': self.demand.copy(),
            'price_trends': {
                crop: 'rising' if len(hist) < 2 else
                      ('rising' if hist[-1] > hist[-2] else 'falling')
                for crop, hist in self.price_history.items()
            }
        }

    def report_to_policy(self):
        """
        Report upward to Policy Level.

        Returns:
            Dict with market metrics for policy evaluation
        """
        return {
            'market_id': self.unique_id,
            'market_name': self.market_name,
            'crop_prices': self.crop_prices.copy(),
            'supply': self.supply.copy(),
            'demand': self.demand.copy(),
            'total_supply': sum(self.supply.values()),
            'num_communities': len(self.community_reports)
        }

    def lateral_influence(self, other_markets):
        """
        Lateral interaction with other markets (within Market Level).

        Args:
            other_markets: List of CommodityMarketAgent instances
        """
        # Price arbitrage across markets
        for other in other_markets:
            if other.unique_id != self.unique_id:
                for crop in self.crops:
                    if crop in other.crop_prices:
                        # Prices converge slightly across markets
                        avg_price = (self.crop_prices[crop] + other.crop_prices[crop]) / 2
                        self.crop_prices[crop] = 0.9 * self.crop_prices[crop] + 0.1 * avg_price

    def step(self):
        """Execute one market-level timestep."""
        # 1. Update prices based on supply/demand and policy
        self.update_prices()

        # 2. Update demand (simplified - could be dynamic)
        self._update_demand()

    def _update_demand(self):
        """Update market demand (simplified)."""
        # In full implementation, demand would be driven by population,
        # external markets, etc. Here we use simple dynamics.
        for crop in self.crops:
            # Demand inversely related to price
            price = self.crop_prices[crop]
            base_demand = 1000.0
            self.demand[crop] = base_demand * (100.0 / price)

    def __repr__(self):
        return f"Market({self.unique_id}, name={self.market_name}, crops={self.crops})"
