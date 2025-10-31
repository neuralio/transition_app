"""
Scenario mapping utilities for MLU use case.

This is a thin wrapper around CCA's scenario_utils to maintain consistency.
"""

import sys
from pathlib import Path

# Add CCA utils to path and import with explicit module name to avoid circular import
cca_utils_path = Path(__file__).parent.parent.parent / "cca" / "utils"
sys.path.insert(0, str(cca_utils_path))

import importlib.util
spec = importlib.util.spec_from_file_location("cca_scenario_utils", cca_utils_path / "scenario_utils.py")
cca_scenario_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cca_scenario_utils)


def normalize_scenario(scenario: str) -> str:
    """Normalize scenario name to RCP code for MLU."""
    return cca_scenario_utils.normalize_scenario(scenario, use_case="mlu")


def get_scenario_display_name(rcp_code: str) -> str:
    """Get display name for RCP code in MLU."""
    return cca_scenario_utils.get_scenario_display_name(rcp_code, use_case="mlu")


def get_scenario_short_name(rcp_code: str) -> str:
    """Get SHORT display name for RCP code (for plot titles to avoid overlap)."""
    return cca_scenario_utils.get_scenario_short_name(rcp_code)


def get_all_scenarios() -> list:
    """Get list of all valid RCP scenarios."""
    return cca_scenario_utils.get_all_scenarios(use_case="mlu")


def get_user_friendly_scenarios() -> dict:
    """Get mapping of user-friendly names to descriptions."""
    return cca_scenario_utils.get_user_friendly_scenarios()
