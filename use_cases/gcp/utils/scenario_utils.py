"""
Scenario mapping utilities for GCP use case.

Direct implementation to avoid slow dynamic imports.
"""

def normalize_scenario(scenario: str) -> str:
    """Normalize scenario name to RCP code for GCP."""
    scenario_lower = scenario.lower()
    # User-friendly names
    mapping = {
        'optimistic': 'rcp26',
        'moderate': 'rcp45',
        'pessimistic': 'rcp85'
    }
    return mapping.get(scenario_lower, scenario_lower)


def get_scenario_display_name(rcp_code: str) -> str:
    """Get display name for RCP code in GCP."""
    descriptions = {
        'rcp26': 'Optimistic (Low Warming ~2°C)',
        'rcp45': 'Moderate (Medium Warming ~3°C)',
        'rcp85': 'Pessimistic (High Warming ~4-5°C)',
        'optimistic': 'Optimistic (Low Warming ~2°C)',
        'moderate': 'Moderate (Medium Warming ~3°C)',
        'pessimistic': 'Pessimistic (High Warming ~4-5°C)'
    }
    return descriptions.get(rcp_code.lower(), rcp_code.upper())


def get_scenario_short_name(rcp_code: str) -> str:
    """Get SHORT display name for RCP code (for plot titles to avoid overlap)."""
    short_names = {
        'rcp26': 'Optimistic',
        'rcp45': 'Moderate',
        'rcp85': 'Pessimistic',
        'optimistic': 'Optimistic',
        'moderate': 'Moderate',
        'pessimistic': 'Pessimistic'
    }
    return short_names.get(rcp_code.lower(), rcp_code.upper())


def get_all_scenarios() -> list:
    """Get list of all valid RCP scenarios."""
    return ['rcp26', 'rcp45', 'rcp85']


def get_user_friendly_scenarios() -> dict:
    """Get mapping of user-friendly names to descriptions."""
    return {
        'optimistic': 'Optimistic (Low Warming ~2°C)',
        'moderate': 'Moderate (Medium Warming ~3°C)',
        'pessimistic': 'Pessimistic (High Warming ~4-5°C)'
    }
