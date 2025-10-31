"""
GCP PolicymakerAgent - Green Credit Policy Authority
===================================================

Policy Level agent for GCP use case representing government policymakers
who design and adjust green credit policies to promote PV adoption.

Implements the feedback loop (GCP-16):
Policy → Financial Institutions → PV Adoption → Policy Adjustment
"""

import mesa
from typing import Dict, List


class GCPPolicymakerAgent(mesa.Agent):
    """
    Policy Level agent for Green Credit Policy simulation.

    Responsibilities:
    - Set green credit policy parameters (subsidies, loan rates, tax incentives)
    - Receive feedback from Financial Institutions (portfolio performance)
    - Receive adoption statistics from landowners (upward flow)
    - Adjust policies to meet PV adoption targets
    - Coordinate with other policymakers (lateral flow)
    """

    def __init__(
        self,
        model,
        policy_name: str,
        policy_goals: Dict
    ):
        """
        Initialize GCP policymaker agent.

        Parameters
        ----------
        model : GCPModel
            Mesa model instance
        policy_name : str
            Name/ID of policy authority (e.g., "National Green Policy")
        policy_goals : dict
            Policy objectives, e.g.:
            {
                'target_pv_adoption_rate': 0.30,  # 30% adoption target
                'financial_stability': 0.95,       # 95% loan non-default rate
                'budget_constraint': 1000000.0     # Max subsidy budget (euros)
            }
        """
        super().__init__(model)
        self.policy_name = policy_name
        self.policy_goals = policy_goals

        # Green credit policy instruments
        self.pv_subsidy_rate = 0.20  # Default: 20% subsidy on installation cost
        self.low_interest_loan_rate = 0.02  # Default: 2% interest rate for green loans
        self.tax_incentive_rate = 0.10  # Default: 10% tax break
        self.loan_guarantee_rate = 0.0  # Loan guarantees to reduce bank risk

        # Policy adjustment parameters
        self.adjustment_rate = 0.05  # Maximum 5% change per evaluation
        self.evaluation_period = 2  # Evaluate every 2 years
        self.last_evaluation_year = 0

        # Feedback from lower levels
        self.financial_institution_reports = []  # From Market Level
        self.adoption_statistics = {}  # From Individual Level (aggregated)

        # Performance tracking
        self.policy_effectiveness = {
            'pv_adoption_rate': 0.0,
            'financial_default_rate': 0.0,
            'total_subsidy_spending': 0.0
        }

        # Policy history (for monitoring feedback loop)
        self.policy_history = []

    def receive_financial_institution_reports(self, reports: List[Dict]):
        """
        Receive reports from Financial Institutions (upward flow from Market Level).

        Parameters
        ----------
        reports : list of dict
            Portfolio statistics from each FinancialInstitutionAgent:
            - total_loan_volume
            - approval_rate
            - default_rate
            - portfolio_risk_score
            - active_loans
        """
        self.financial_institution_reports = reports

    def receive_adoption_statistics(self, stats: Dict):
        """
        Receive PV adoption statistics (upward flow from Individual Level).

        Parameters
        ----------
        stats : dict
            Aggregated statistics:
            - total_landowners: Total number of landowners
            - landowners_with_pv: Number with PV installed
            - pv_adoption_rate: Percentage with PV
            - total_pv_capacity_kw: Total installed capacity
            - average_roi: Average ROI across all PV installations
        """
        self.adoption_statistics = stats

    def evaluate_policy_effectiveness(self, year: int):
        """
        Evaluate policy effectiveness based on feedback from all levels.

        Parameters
        ----------
        year : int
            Current simulation year
        """
        # 1. Evaluate PV adoption rate
        self.policy_effectiveness['pv_adoption_rate'] = self.adoption_statistics.get(
            'pv_adoption_rate',
            0.0
        )

        # 2. Evaluate financial institution health
        if self.financial_institution_reports:
            avg_default_rate = sum(
                report.get('default_rate', 0.0)
                for report in self.financial_institution_reports
            ) / len(self.financial_institution_reports)

            self.policy_effectiveness['financial_default_rate'] = avg_default_rate

        # 3. Calculate total subsidy spending
        total_subsidies = 0.0
        if hasattr(self.model, 'total_subsidy_spending'):
            total_subsidies = self.model.total_subsidy_spending

        self.policy_effectiveness['total_subsidy_spending'] = total_subsidies

        # Record policy state in history
        self.policy_history.append({
            'year': year,
            'pv_subsidy_rate': self.pv_subsidy_rate,
            'loan_rate': self.low_interest_loan_rate,
            'tax_incentive_rate': self.tax_incentive_rate,
            'adoption_rate': self.policy_effectiveness['pv_adoption_rate'],
            'default_rate': self.policy_effectiveness['financial_default_rate'],
            'subsidy_spending': total_subsidies
        })

    def adjust_policies(self, year: int):
        """
        Adjust green credit policies based on effectiveness evaluation.

        Implements adaptive policy feedback loop (GCP-16):
        - If adoption is below target: increase incentives
        - If default rate is high: adjust risk mitigation (loan guarantees)
        - If budget is exceeded: reduce subsidies

        Parameters
        ----------
        year : int
            Current simulation year
        """
        # Only adjust periodically
        if year - self.last_evaluation_year < self.evaluation_period:
            return

        self.last_evaluation_year = year

        # Get policy goals
        target_adoption = self.policy_goals.get('target_pv_adoption_rate', 0.30)
        target_financial_stability = self.policy_goals.get('financial_stability', 0.95)
        budget_limit = self.policy_goals.get('budget_constraint', 1000000.0)

        # Get current performance
        current_adoption = self.policy_effectiveness['pv_adoption_rate']
        current_default_rate = self.policy_effectiveness['financial_default_rate']
        current_spending = self.policy_effectiveness['total_subsidy_spending']

        # ===== ADJUSTMENT LOGIC =====

        # 1. Adjust PV subsidy rate based on adoption gap
        adoption_gap = target_adoption - current_adoption

        if abs(adoption_gap) > 0.05:  # Significant gap (>5%)
            if adoption_gap > 0:
                # Adoption below target: increase subsidies
                adjustment = min(self.adjustment_rate, adoption_gap * 0.2)
                self.pv_subsidy_rate = min(
                    0.40,  # Max 40% subsidy
                    self.pv_subsidy_rate + adjustment
                )
            else:
                # Adoption above target: can reduce subsidies
                adjustment = min(self.adjustment_rate, abs(adoption_gap) * 0.1)
                self.pv_subsidy_rate = max(
                    0.10,  # Min 10% subsidy
                    self.pv_subsidy_rate - adjustment
                )

        # 2. Adjust loan interest rate based on adoption and financial health
        if current_adoption < target_adoption * 0.8:  # Less than 80% of target
            # Significantly below target: reduce interest rate
            self.low_interest_loan_rate = max(
                0.01,  # Min 1% rate
                self.low_interest_loan_rate - 0.005
            )

        # 3. Adjust loan guarantees based on financial institution default rate
        target_default_rate = 1.0 - target_financial_stability  # e.g., 5% max default
        if current_default_rate > target_default_rate:
            # Default rate too high: increase loan guarantees
            self.loan_guarantee_rate = min(
                0.50,  # Max 50% guarantee
                self.loan_guarantee_rate + 0.10
            )
        elif current_default_rate < target_default_rate * 0.5:
            # Very low defaults: can reduce guarantees
            self.loan_guarantee_rate = max(
                0.0,
                self.loan_guarantee_rate - 0.05
            )

        # 4. Budget constraint check
        if current_spending > budget_limit:
            # Over budget: reduce subsidies
            reduction = min(0.05, (current_spending - budget_limit) / budget_limit * 0.1)
            self.pv_subsidy_rate = max(
                0.05,
                self.pv_subsidy_rate - reduction
            )

        # 5. Adjust tax incentives based on overall effectiveness
        if current_adoption < target_adoption * 0.7:  # Very low adoption
            # Boost tax incentives as additional stimulus
            self.tax_incentive_rate = min(
                0.20,  # Max 20% tax break
                self.tax_incentive_rate + 0.02
            )

    def get_policy_signals(self) -> Dict:
        """
        Generate policy signals for lower levels (downward flow).

        Returns
        -------
        dict
            Policy parameters for Financial Institutions and LandOwners:
            {
                'pv_subsidy_rate': float,
                'low_interest_loan_rate': float,
                'tax_incentive_rate': float,
                'loan_guarantee_rate': float,
                'policy_name': str
            }
        """
        return {
            'pv_subsidy_rate': self.pv_subsidy_rate,
            'low_interest_loan_rate': self.low_interest_loan_rate,
            'tax_incentive_rate': self.tax_incentive_rate,
            'loan_guarantee_rate': self.loan_guarantee_rate,
            'policy_name': self.policy_name,
            'target_adoption_rate': self.policy_goals.get('target_pv_adoption_rate', 0.30)
        }

    def lateral_coordination(self, other_policymakers: List['GCPPolicymakerAgent']):
        """
        Coordinate with other policy authorities (lateral flow within Policy Level).

        Policymakers can align their strategies or learn from each other.

        Parameters
        ----------
        other_policymakers : list of GCPPolicymakerAgent
            Other policy authorities
        """
        if not other_policymakers:
            return

        for other in other_policymakers:
            if other.unique_id != self.unique_id:
                # Learn from more successful policies
                if other.policy_effectiveness['pv_adoption_rate'] > self.policy_effectiveness['pv_adoption_rate']:
                    # Partially adopt their strategy
                    alignment_weight = 0.2  # 20% alignment

                    self.pv_subsidy_rate = (
                        (1 - alignment_weight) * self.pv_subsidy_rate +
                        alignment_weight * other.pv_subsidy_rate
                    )

                    self.low_interest_loan_rate = (
                        (1 - alignment_weight) * self.low_interest_loan_rate +
                        alignment_weight * other.low_interest_loan_rate
                    )

    def step(self):
        """
        Execute one policy-level timestep.

        Steps:
        1. Evaluate policy effectiveness (analyze upward feedback)
        2. Adjust policies based on evaluation
        """
        year = self.model.current_year

        # 1. Evaluate policy effectiveness
        self.evaluate_policy_effectiveness(year)

        # 2. Adjust policies if needed
        self.adjust_policies(year)

    def get_feedback_loop_data(self) -> Dict:
        """
        Get data for GCP-16 feedback loop visualization.

        Returns
        -------
        dict
            Historical data showing policy → adoption → financial → policy cycle
        """
        return {
            'policy_name': self.policy_name,
            'policy_history': self.policy_history,
            'current_effectiveness': self.policy_effectiveness,
            'policy_goals': self.policy_goals
        }

    def __repr__(self):
        return f"GCPPolicymaker({self.unique_id}, {self.policy_name}, adoption={self.policy_effectiveness['pv_adoption_rate']:.1%})"
