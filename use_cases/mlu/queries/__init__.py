"""
Query module for MLU user stories.

Each query represents a specific user story from USER_STORIES.md:
- MLU-04: Categorize Land Parcels Using AI (mlu_04.py)
- MLU-05: Analyze Land Suitability Using Multi-Level ABM (full_abm.py)
- MLU-07: Integrate Historical EO Data for Benchmarking (historical_benchmark.py)
- MLU-08: Simulate Future Climate Scenarios (climate_scenario.py)
"""

from .mlu_04 import query_mlu_04 as query_parcel_categorize
from .full_abm import query_full_abm
from .historical_benchmark import query_historical_benchmark
from .climate_scenario import query_climate_scenario

__all__ = [
    "query_parcel_categorize",
    "query_full_abm",
    "query_historical_benchmark",
    "query_climate_scenario",
]
