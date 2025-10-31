"""
GCP Agents Module
=================

Multi-Level Agent-Based Modeling (ML-ABM) agents for Green Credit Policy simulation.

Complete 4-Level Architecture:
------------------------------
- **Individual Level**: LandOwnerAgent - PV adoption decisions
- **Community Level**: CollectiveAgent (TODO: reuse from backend or create GCP-specific)
- **Market Level**: FinancialInstitutionAgent - Loan decisions and portfolio management
- **Policy Level**: GCPPolicymakerAgent - Green credit policies and feedback loops

Cross-Scale Interactions:
------------------------
- Downward: Policy → Market (loan guarantees) → Community (signals) → Individual (incentives)
- Upward: Individual (adoption) → Community (aggregation) → Market (portfolio) → Policy (effectiveness)
- Lateral: Within-level coordination (policy alignment, market competition, peer influence)
"""

from .landowner_agent import LandOwnerAgent
from .financial_institution_agent import FinancialInstitutionAgent
from .policymaker_agent_gcp import GCPPolicymakerAgent

__all__ = [
    'LandOwnerAgent',
    'FinancialInstitutionAgent',
    'GCPPolicymakerAgent'
]
