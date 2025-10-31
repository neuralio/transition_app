"""
Financial Institution Agent for Green Credit Policy (GCP) Simulation
====================================================================

Market-level agent representing a bank or financial institution that:
- Evaluates loan applications from landowners for PV installations
- Manages loan portfolio and risk assessment
- Responds to green credit policy changes
- Provides feedback to policymakers on portfolio performance
"""

import mesa
import numpy as np
from typing import Dict, List, Optional


class FinancialInstitutionAgent(mesa.Agent):
    """
    A financial institution that evaluates PV loan applications.

    Responsibilities:
    - Assess credit risk of loan applicants
    - Approve/deny loan applications
    - Manage loan portfolio (active loans, defaults, profitability)
    - Respond to policy changes (interest rate adjustments, guarantees)
    - Provide portfolio statistics for policy feedback loops
    """

    def __init__(
        self,
        model,
        institution_name: str = "GreenBank"
    ):
        """
        Initialize financial institution agent.

        Parameters
        ----------
        model : GCPModel
            Mesa model instance
        institution_name : str
            Name of the financial institution
        """
        super().__init__(model)
        self.institution_name = institution_name

        # Loan portfolio
        self.active_loans = []  # List of active loans
        self.approved_loans = []  # All approved loans (history)
        self.denied_loans = []  # All denied applications (history)
        self.defaulted_loans = []  # Loans that defaulted

        # Portfolio statistics
        self.total_loan_volume = 0.0  # Total euros loaned
        self.total_green_loans = 0  # Number of green (PV) loans
        self.total_interest_income = 0.0  # Cumulative interest earned
        self.total_defaults = 0.0  # Total losses from defaults
        self.portfolio_value = 0.0  # Current outstanding principal
        self.portfolio_risk_score = 0.0  # Portfolio risk (0-1, lower is better)

        # Risk assessment parameters
        self.credit_score_threshold = model.config['financial_institutions']['risk_assessment']['credit_score_threshold']
        self.debt_to_income_threshold = model.config['financial_institutions']['risk_assessment']['debt_to_income_threshold']
        self.loan_to_value_threshold = model.config['financial_institutions']['risk_assessment']['loan_to_value_threshold']

        # Portfolio management targets
        self.target_green_loan_percentage = model.config['financial_institutions']['portfolio']['target_green_loan_percentage']
        self.max_exposure_per_sector = model.config['financial_institutions']['portfolio']['max_exposure_per_sector']
        self.reserve_ratio = model.config['financial_institutions']['portfolio']['reserve_ratio']

        # Policy response parameters
        self.policy_response_lag = model.config['financial_institutions']['feedback']['policy_response_lag']
        self.market_adjustment_rate = model.config['financial_institutions']['feedback']['market_adjustment_rate']

        # Policy signals from government
        self.policy_signals = {}

    def receive_policy_signals(self, signals: Dict):
        """
        Receive signals from Policy Level (downward flow).

        Parameters
        ----------
        signals : dict
            Policy signals (interest rates, loan guarantees, etc.)
        """
        self.policy_signals = signals

    def evaluate_loan_application(
        self,
        agent,
        loan_amount: float,
        interest_rate: float,
        term: int,
        year: int
    ) -> bool:
        """
        Evaluate a loan application from a landowner.

        Decision based on:
        - Credit risk assessment (financial situation, debt-to-income ratio)
        - Loan-to-value ratio (loan amount vs PV system value)
        - Portfolio capacity (reserve requirements)
        - Policy incentives (loan guarantees from government)

        Parameters
        ----------
        agent : LandOwnerAgent
            Applicant
        loan_amount : float
            Requested loan amount (euros)
        interest_rate : float
            Proposed interest rate (0-1)
        term : int
            Loan term (years)
        year : int
            Application year

        Returns
        -------
        bool
            True if loan is approved, False otherwise
        """
        # 1. Credit risk assessment
        credit_score = self._assess_credit_risk(agent)

        if credit_score < self.credit_score_threshold:
            # Credit score too low
            self._record_denied_loan(agent, loan_amount, year, reason="Low credit score")
            return False

        # 2. Debt-to-income ratio
        # Estimate annual income based on financial situation
        income_map = {
            'poor': 20000.0,
            'moderate': 40000.0,
            'wealthy': 80000.0
        }
        estimated_annual_income = income_map[agent.financial_situation]

        annual_loan_payment = agent.annual_loan_payment
        debt_to_income = annual_loan_payment / estimated_annual_income

        if debt_to_income > self.debt_to_income_threshold:
            # Debt-to-income ratio too high
            self._record_denied_loan(agent, loan_amount, year, reason="High debt-to-income ratio")
            return False

        # 3. Loan-to-value ratio
        pv_system_value = agent.installation_cost
        loan_to_value = loan_amount / pv_system_value if pv_system_value > 0 else 1.0

        if loan_to_value > self.loan_to_value_threshold:
            # Loan-to-value too high
            self._record_denied_loan(agent, loan_amount, year, reason="High loan-to-value ratio")
            return False

        # 4. Portfolio capacity check
        available_capital = self._get_available_capital()
        if loan_amount > available_capital:
            # Insufficient capital
            self._record_denied_loan(agent, loan_amount, year, reason="Insufficient capital")
            return False

        # ✅ NEW: 5. Forward-looking cash flow analysis
        # Banks assess if the PV system will generate enough profit to service the loan
        # This is especially important for poor farmers with marginal credit
        if agent.financial_situation == 'poor':
            # Calculate expected annual profit from PV (simplified estimate)
            # This would normally be done by the landowner agent, but we approximate here
            pv_capacity = getattr(agent, 'pv_capacity_kw', 100.0)  # Default 100kW if not set yet

            # Estimate annual revenue (conservative estimate)
            electricity_price = self.model.config['solar_pv']['electricity_price']
            feed_in_tariff = self.model.config['solar_pv']['feed_in_tariff']
            solar_hours_per_year = 1800  # Conservative for Greece

            estimated_annual_generation = pv_capacity * solar_hours_per_year
            estimated_annual_revenue = estimated_annual_generation * (electricity_price * 0.3 + feed_in_tariff * 0.7)

            # Estimate annual costs
            maintenance_cost = self.model.config['solar_pv']['maintenance_cost_annual']
            grid_fee = self.model.config['solar_pv']['annual_grid_fee']
            estimated_annual_costs = maintenance_cost + grid_fee + annual_loan_payment

            estimated_annual_profit = estimated_annual_revenue - estimated_annual_costs

            # Reject if projected to be unprofitable (can't service loan)
            if estimated_annual_profit < 0:
                self._record_denied_loan(agent, loan_amount, year, reason="Negative projected cash flow")
                return False

        # 6. Policy incentives (loan guarantees reduce risk)
        loan_guarantee = self.policy_signals.get('loan_guarantee_rate', 0.0)
        risk_adjustment = 1.0 - (loan_guarantee * 0.5)  # Guarantees reduce perceived risk

        adjusted_credit_score = credit_score / risk_adjustment

        # Final decision
        if adjusted_credit_score >= self.credit_score_threshold:
            # Approve loan
            self._record_approved_loan(
                agent=agent,
                loan_amount=loan_amount,
                interest_rate=interest_rate,
                term=term,
                year=year
            )
            return True
        else:
            # Deny loan
            self._record_denied_loan(agent, loan_amount, year, reason="Adjusted risk too high")
            return False

    def _assess_credit_risk(self, agent) -> float:
        """
        Assess credit risk of loan applicant.

        Parameters
        ----------
        agent : LandOwnerAgent
            Loan applicant

        Returns
        -------
        float
            Credit score (0-1000)
        """
        # ✅ FIX: More realistic base credit scores (lower to create rejections)
        base_scores = {
            'poor': 480,      # Below default threshold - needs strong compensating factors
            'moderate': 620,  # Moderate credit - borderline
            'wealthy': 750    # Good credit
        }
        base_score = base_scores[agent.financial_situation]

        # Adjust for risk tolerance (risk-seeking might have lower scores)
        risk_adjustments = {
            'low': 40,      # Conservative = higher score
            'moderate': 0,  # No adjustment
            'high': -50     # Risk-seeking = penalty (more realistic)
        }
        risk_adjustment = risk_adjustments[agent.risk_tolerance]

        # Adjust for land assets (more land = more collateral)
        land_bonus = min(40, agent.land_hectares * 4)  # Up to +40 for large parcels (reduced)

        credit_score = base_score + risk_adjustment + land_bonus

        # Add some randomness (represent incomplete information)
        credit_score += np.random.normal(0, 25)

        return max(300, min(900, credit_score))  # Clamp to 300-900 range

    def _get_available_capital(self) -> float:
        """
        Calculate available capital for lending.

        Returns
        -------
        float
            Available capital (euros)
        """
        # Total capital (set during initialization, varies by institution)
        # Default to 10M if not set (for backward compatibility)
        total_capital = getattr(self, 'total_capital', 10000000.0)

        # Reserve requirement
        required_reserves = self.portfolio_value * self.reserve_ratio

        # Available capital
        available = total_capital - required_reserves - self.portfolio_value

        return max(0, available)

    def _record_approved_loan(
        self,
        agent,
        loan_amount: float,
        interest_rate: float,
        term: int,
        year: int
    ):
        """
        Record an approved loan.

        Parameters
        ----------
        agent : LandOwnerAgent
            Borrower
        loan_amount : float
            Loan amount (euros)
        interest_rate : float
            Interest rate (0-1)
        term : int
            Loan term (years)
        year : int
            Loan origination year
        """
        loan = {
            'agent_id': agent.unique_id,
            'agent': agent,
            'loan_amount': loan_amount,
            'interest_rate': interest_rate,
            'term': term,
            'origination_year': year,
            'remaining_balance': loan_amount,
            'status': 'active'
        }

        self.active_loans.append(loan)
        self.approved_loans.append(loan)

        # Update portfolio statistics
        self.total_loan_volume += loan_amount
        self.total_green_loans += 1
        self.portfolio_value += loan_amount

    def _record_denied_loan(
        self,
        agent,
        loan_amount: float,
        year: int,
        reason: str
    ):
        """
        Record a denied loan application.

        Parameters
        ----------
        agent : LandOwnerAgent
            Applicant
        loan_amount : float
            Requested amount (euros)
        year : int
            Application year
        reason : str
            Denial reason
        """
        denial = {
            'agent_id': agent.unique_id,
            'loan_amount': loan_amount,
            'year': year,
            'reason': reason
        }

        self.denied_loans.append(denial)

    def step(self):
        """
        One decision step - manage loan portfolio and respond to policies.
        """
        year = self.model.current_year

        # 1. Update existing loans
        self._update_loan_portfolio(year)

        # 2. Calculate portfolio risk
        self._calculate_portfolio_risk()

        # 3. Adjust lending strategy based on policy signals
        self._adjust_lending_strategy(year)

    def _update_loan_portfolio(self, year: int):
        """
        Update loan portfolio (collect payments, handle defaults).

        Parameters
        ----------
        year : int
            Current year
        """
        for loan in self.active_loans[:]:  # Copy list to allow modification
            agent = loan['agent']
            years_since_origination = year - loan['origination_year']

            # Check if loan term expired
            if years_since_origination >= loan['term']:
                # Loan paid off
                loan['status'] = 'paid_off'
                self.active_loans.remove(loan)
                self.portfolio_value -= loan['remaining_balance']
                continue

            # Collect annual payment
            annual_payment = agent.annual_loan_payment

            # ✅ FIX: Realistic default detection
            # Check for default - multiple conditions
            should_default = False

            # Condition 1: Agent decommissioned PV (lost collateral)
            if hasattr(agent, 'pv_decommissioned') and agent.pv_decommissioned:
                should_default = True

            # Condition 2: Agent no longer has PV but still has active loan
            elif not agent.has_pv:
                should_default = True

            # Condition 3: Persistent losses - can't afford payments
            # If negative profit for 3+ consecutive years, default becomes likely
            elif hasattr(agent, 'consecutive_loss_years') and agent.consecutive_loss_years >= 3:
                # Probability increases with consecutive loss years
                default_probability = min(0.8, agent.consecutive_loss_years * 0.15)  # 15% per year, max 80%
                if np.random.random() < default_probability:
                    should_default = True

            # Condition 4: Catastrophic losses - immediate default
            elif hasattr(agent, 'cumulative_profit') and agent.cumulative_profit < -loan['loan_amount']:
                should_default = True

            # ✅ NEW: Stochastic individual-level default risk
            # Even under good overall conditions, individual random shocks cause defaults
            # (equipment failures, personal crises, poor management, natural disasters)
            if not should_default:
                # Baseline default probability (annualized)
                baseline_default_prob = 0.02  # 2% per year baseline

                # Adjust by financial situation (poor farmers more vulnerable)
                financial_situation_multipliers = {
                    'poor': 2.0,      # 2x baseline (4% per year)
                    'moderate': 1.0,  # 1x baseline (2% per year)
                    'wealthy': 0.5    # 0.5x baseline (1% per year)
                }
                fs_multiplier = financial_situation_multipliers.get(agent.financial_situation, 1.0)

                # Adjust by loan age (early years riskier - installation issues)
                age_multipliers = {
                    0: 1.5,  # First year: installation issues, learning curve
                    1: 1.3,  # Second year: early equipment failures
                    2: 1.0,  # Years 3+: normal risk
                }
                age_multiplier = age_multipliers.get(years_since_origination, 1.0)

                # Adjust by profitability (negative profit increases risk even if not persistent)
                profit_multiplier = 1.0
                if hasattr(agent, 'annual_profit') and agent.annual_profit < 0:
                    profit_multiplier = 1.8  # 80% increase in default risk when unprofitable

                # Combined probability
                default_prob = baseline_default_prob * fs_multiplier * age_multiplier * profit_multiplier
                default_prob = min(0.15, default_prob)  # Cap at 15% per year

                if np.random.random() < default_prob:
                    should_default = True

            if should_default:
                # Default!
                self._handle_default(loan, year)
                continue

            # Calculate interest income
            interest_payment = loan['remaining_balance'] * loan['interest_rate']
            principal_payment = annual_payment - interest_payment

            self.total_interest_income += interest_payment

            # Update remaining balance
            loan['remaining_balance'] -= principal_payment
            loan['remaining_balance'] = max(0, loan['remaining_balance'])

    def _handle_default(self, loan: Dict, year: int):
        """
        Handle loan default.

        Parameters
        ----------
        loan : dict
            Loan that defaulted
        year : int
            Default year
        """
        # Record default
        loan['status'] = 'defaulted'
        loan['default_year'] = year
        self.defaulted_loans.append(loan)
        self.active_loans.remove(loan)

        # Record loss
        loss_amount = loan['remaining_balance']
        self.total_defaults += loss_amount
        self.portfolio_value -= loss_amount

    def _calculate_portfolio_risk(self):
        """
        Calculate portfolio risk score.

        Risk factors:
        - Concentration risk (too many loans in one sector)
        - Default rate
        - Average credit quality
        """
        if not self.approved_loans:
            self.portfolio_risk_score = 0.0
            return

        # Default rate
        total_loans = len(self.approved_loans)
        defaulted_loans = len(self.defaulted_loans)
        default_rate = defaulted_loans / total_loans if total_loans > 0 else 0.0

        # Concentration risk (all loans are green/PV)
        concentration_risk = 1.0  # High concentration in green loans

        # Portfolio risk score (0-1)
        self.portfolio_risk_score = (default_rate * 0.7) + (concentration_risk * 0.3)

    def _adjust_lending_strategy(self, year: int):
        """
        Adjust lending strategy based on policy signals and portfolio performance.

        Parameters
        ----------
        year : int
            Current year
        """
        # ✅ FIX: More aggressive threshold adjustment based on risk
        if self.portfolio_risk_score > 0.5:
            # Very high risk - aggressive tightening
            self.credit_score_threshold = min(
                750,
                self.credit_score_threshold + 30
            )
        elif self.portfolio_risk_score > 0.3:
            # High risk - moderate tightening
            self.credit_score_threshold = min(
                750,
                self.credit_score_threshold + 15
            )
        elif self.portfolio_risk_score > 0.15:
            # Moderate risk - slight tightening
            self.credit_score_threshold = min(
                700,
                self.credit_score_threshold + 5
            )
        elif self.portfolio_risk_score < 0.05:
            # Very low risk - can loosen standards
            self.credit_score_threshold = max(
                480,
                self.credit_score_threshold - 10
            )

        # Respond to policy changes (with lag)
        if self.policy_signals and year % self.policy_response_lag == 0:
            # Adjust rates based on policy incentives
            new_target = self.policy_signals.get('target_green_loan_percentage')
            if new_target:
                adjustment = (new_target - self.target_green_loan_percentage) * self.market_adjustment_rate
                self.target_green_loan_percentage += adjustment

    def get_portfolio_state(self) -> Dict:
        """
        Get financial institution's portfolio state for upward information flow.

        Returns
        -------
        dict
            Portfolio statistics for policymakers
        """
        # Calculate current metrics
        total_loans = len(self.approved_loans)
        active_loan_count = len(self.active_loans)
        defaulted_loan_count = len(self.defaulted_loans)
        denied_loan_count = len(self.denied_loans)

        approval_rate = (
            total_loans / (total_loans + denied_loan_count)
            if (total_loans + denied_loan_count) > 0
            else 0.0
        )

        default_rate = (
            defaulted_loan_count / total_loans
            if total_loans > 0
            else 0.0
        )

        return {
            'institution_name': self.institution_name,
            'total_loan_volume': self.total_loan_volume,
            'total_green_loans': self.total_green_loans,
            'active_loans': active_loan_count,
            'defaulted_loans': defaulted_loan_count,
            'denied_loans': denied_loan_count,
            'approval_rate': approval_rate,
            'default_rate': default_rate,
            'portfolio_value': self.portfolio_value,
            'portfolio_risk_score': self.portfolio_risk_score,
            'total_interest_income': self.total_interest_income,
            'total_defaults': self.total_defaults,
            'credit_score_threshold': self.credit_score_threshold
        }

    def __repr__(self):
        return f"FinancialInstitution({self.institution_name}, loans={len(self.active_loans)}, risk={self.portfolio_risk_score:.2f})"
