"""Policy Level Agent - Government Policies and Regulations."""

import mesa


class PolicymakerAgent(mesa.Agent):
    """
    Policy Level agent representing government policymakers.

    Sets regulations, subsidies, and incentives that cascade down through
    Market and Community levels to affect Individual farmer decisions.
    """

    def __init__(self,
                 model,
                 policy_name,
                 policy_goals):
        """Initialize policymaker agent.

        Args:
            model: Mesa model instance
            policy_name: Name/ID of the policy authority
            policy_goals: Dict of policy objectives (e.g., {'food_security': 0.8, 'sustainability': 0.6})
        """
        super().__init__(model)
        self.policy_name = policy_name
        self.policy_goals = policy_goals  # Target metrics

        # Policy instruments
        self.subsidy_rates = {}  # Crop subsidies (e.g., {'WHEAT': 0.1})
        self.price_floors = {}  # Minimum prices (e.g., {'MAIZE': 50.0})
        self.price_ceilings = {}  # Maximum prices
        self.regulations = {}  # Other regulations

        # Interaction buffers
        self.market_reports = []  # Reports from market level

        # Performance tracking
        self.policy_effectiveness = {}  # Metric: actual vs. goal

    def perceive_from_markets(self, market_reports):
        """
        Receive upward signals from Market Level.

        Args:
            market_reports: List of dicts from CommodityMarketAgent.report_to_policy()
        """
        self.market_reports = market_reports

    def evaluate_policy_effectiveness(self):
        """
        Evaluate policy effectiveness based on market outcomes.

        Compares current state against policy goals.
        """
        if not self.market_reports:
            return

        # Aggregate market data
        total_supply = sum(report.get('total_supply', 0) for report in self.market_reports)
        avg_prices = {}
        for report in self.market_reports:
            for crop, price in report.get('crop_prices', {}).items():
                if crop not in avg_prices:
                    avg_prices[crop] = []
                avg_prices[crop].append(price)

        # Compute average prices
        avg_prices = {crop: sum(prices) / len(prices) for crop, prices in avg_prices.items()}

        # Evaluate against goals
        # Example: Food security = total supply > threshold
        food_security_threshold = 5000.0
        self.policy_effectiveness['food_security'] = min(1.0, total_supply / food_security_threshold)

        # Example: Price stability = prices within reasonable range
        target_price_range = (50.0, 150.0)
        price_stability = sum(
            1 for price in avg_prices.values()
            if target_price_range[0] <= price <= target_price_range[1]
        ) / max(1, len(avg_prices))
        self.policy_effectiveness['price_stability'] = price_stability

    def adjust_policies(self):
        """
        Adjust policy instruments based on effectiveness evaluation.

        Uses rule-based logic (can be replaced with RL later).
        """
        # Goal: Increase food security
        food_security_goal = self.policy_goals.get('food_security', 0.8)
        current_food_security = self.policy_effectiveness.get('food_security', 0.5)

        if current_food_security < food_security_goal:
            # Increase subsidies to boost production
            for crop in self.subsidy_rates:
                self.subsidy_rates[crop] = min(0.5, self.subsidy_rates[crop] + 0.05)
        else:
            # Reduce subsidies if goal met
            for crop in self.subsidy_rates:
                self.subsidy_rates[crop] = max(0.0, self.subsidy_rates[crop] - 0.02)

        # Goal: Price stability
        price_stability_goal = self.policy_goals.get('price_stability', 0.7)
        current_price_stability = self.policy_effectiveness.get('price_stability', 0.5)

        if current_price_stability < price_stability_goal:
            # Implement price floors/ceilings
            if self.market_reports:
                for report in self.market_reports:
                    for crop, price in report.get('crop_prices', {}).items():
                        if price < 50.0:
                            self.price_floors[crop] = 50.0
                        if price > 150.0:
                            self.price_ceilings[crop] = 150.0

    def get_policy_regulations(self):
        """
        Generate policy regulations for Market Level (downward flow).

        Returns:
            Dict with regulations, subsidies, price controls
        """
        regulations = {
            'subsidies': self.subsidy_rates.copy(),
            'regulations': self.regulations.copy()
        }

        # Add price floors/ceilings
        for crop, floor in self.price_floors.items():
            regulations[f'{crop}_price_floor'] = floor
        for crop, ceiling in self.price_ceilings.items():
            regulations[f'{crop}_price_ceiling'] = ceiling

        return regulations

    def lateral_influence(self, other_policies):
        """
        Lateral interaction with other policy authorities (within Policy Level).

        Args:
            other_policies: List of PolicymakerAgent instances
        """
        # Policy coordination (e.g., regional vs. national)
        for other in other_policies:
            if other.unique_id != self.unique_id:
                # Align subsidy rates slightly
                for crop in self.subsidy_rates:
                    if crop in other.subsidy_rates:
                        avg_rate = (self.subsidy_rates[crop] + other.subsidy_rates[crop]) / 2
                        self.subsidy_rates[crop] = 0.8 * self.subsidy_rates[crop] + 0.2 * avg_rate

    def step(self):
        """Execute one policy-level timestep."""
        # 1. Evaluate policy effectiveness (upward flow analysis)
        self.evaluate_policy_effectiveness()

        # 2. Adjust policies based on evaluation
        self.adjust_policies()

    def initialize_default_policies(self, crops):
        """
        Initialize default policy instruments.

        Args:
            crops: List of crop names
        """
        # Set default subsidies
        for crop in crops:
            self.subsidy_rates[crop] = 0.1  # 10% subsidy

        # Set default price floors
        for crop in crops:
            self.price_floors[crop] = 50.0

    def __repr__(self):
        return f"Policymaker({self.unique_id}, name={self.policy_name})"
