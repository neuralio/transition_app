"""
Green Credit Policy (GCP) Module
=================================

This module simulates the impact of green credit policies on photovoltaic (PV) adoption
by farmers and landowners, and the feedback loops with financial institutions.

User Stories:
- GCP-03: Simulate PV Adoption by Farmers and Landowners
- GCP-07: View Geographic Distribution of PV Adoption
- GCP-16: Monitor the Feedback Loop between Policy and Financial Institutions

Architecture:
- Multi-Level Agent-Based Modeling (ML-ABM) with 4 levels:
  - Individual: LandOwnerAgent (PV adoption decisions)
  - Community: CollectiveAgent (cooperative decision-making)
  - Market: FinancialInstitutionAgent (loan decisions and risk assessment)
  - Policy: PolicymakerAgent (green credit policies and incentives)

Data Sources:
- EUROSTAT: Socioeconomic data (income, employment, demographics)
- ECB: Balance Sheet Items and interest rates
- FADN: Farm Accountancy Data Network
- ENSPRESO: Solar potential data
- DEM, meteorological, and soil data
"""

__version__ = "1.0.0"
__author__ = "TRANSITION Team"
