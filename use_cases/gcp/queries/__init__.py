"""
GCP Query Handlers
==================

Query implementations for Green Credit Policy (GCP) use case.

Query Handlers:
- GCP-03: Simulate PV adoption by farmers/landowners under green credit policies
- GCP-07: View geographic distribution of PV adoption across the region
- GCP-16: Monitor feedback loop between policy and financial institutions

Each query handler provides a user-friendly interface to run specific
GCP simulation scenarios and generate appropriate visualizations.
"""

from .gcp_03 import query_gcp_03, query_gcp_03_all_policies, query_gcp_03_all_scenarios
from .gcp_07 import query_gcp_07
from .gcp_16 import query_gcp_16

__all__ = [
    'query_gcp_03',
    'query_gcp_03_all_policies',
    'query_gcp_03_all_scenarios',
    'query_gcp_07',
    'query_gcp_16'
]
