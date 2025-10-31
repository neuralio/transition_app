"""
Scenario mapping utilities for TRANSITION project.

Maps user-friendly scenario names to RCP codes:
- optimistic → rcp26 (Low Warming ~2°C)
- moderate → rcp45 (Medium Warming ~3°C)
- pessimistic → rcp85 (High Warming ~4-5°C)

This allows users to use intuitive names while maintaining backward compatibility.
"""

import yaml
from pathlib import Path
from typing import Optional, Dict


def load_scenario_config(use_case: str = "cca") -> Dict:
    """
    Load scenario configuration from config.yaml.

    Args:
        use_case: Either 'cca' or 'mlu'

    Returns:
        Dict with scenario_mapping and scenario_descriptions
    """
    if use_case == "cca":
        config_path = Path(__file__).parent.parent / "config.yaml"
    elif use_case == "mlu":
        config_path = Path(__file__).parent.parent.parent / "mlu" / "config.yaml"
    else:
        raise ValueError(f"Unknown use case: {use_case}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return {
        'scenario_mapping': config['simulation']['scenario_mapping'],
        'scenario_descriptions': config['simulation']['scenario_descriptions']
    }


def normalize_scenario(scenario: str, use_case: str = "cca") -> str:
    """
    Normalize scenario name to RCP code.

    Accepts both user-friendly names and RCP codes:
    - optimistic / rcp26 → rcp26
    - moderate / rcp45 → rcp45
    - pessimistic / rcp85 → rcp85

    Args:
        scenario: User-provided scenario (e.g., "optimistic", "RCP26", "rcp45")
        use_case: Either 'cca' or 'mlu'

    Returns:
        Normalized RCP code (rcp26, rcp45, or rcp85)

    Raises:
        ValueError: If scenario is not recognized
    """
    if not scenario:
        return None

    # Normalize to lowercase
    scenario_lower = scenario.lower().strip()

    # Load mapping from config
    config = load_scenario_config(use_case)
    scenario_mapping = config['scenario_mapping']

    # Check if already an RCP code
    if scenario_lower in ['rcp26', 'rcp45', 'rcp85']:
        return scenario_lower

    # Check if user-friendly name
    if scenario_lower in scenario_mapping:
        return scenario_mapping[scenario_lower]

    # Try to extract RCP code from variations (e.g., "RCP 2.6", "rcp_26")
    rcp_map = {
        '26': 'rcp26', '2.6': 'rcp26',
        '45': 'rcp45', '4.5': 'rcp45',
        '85': 'rcp85', '8.5': 'rcp85'
    }

    for key, value in rcp_map.items():
        if key in scenario_lower:
            return value

    # Invalid scenario
    valid_options = list(scenario_mapping.keys()) + ['rcp26', 'rcp45', 'rcp85']
    raise ValueError(
        f"Invalid scenario: '{scenario}'. "
        f"Valid options: {', '.join(valid_options)}"
    )


def get_scenario_display_name(rcp_code: str, use_case: str = "cca") -> str:
    """
    Get user-friendly display name for RCP code.

    Args:
        rcp_code: RCP code (rcp26, rcp45, rcp85) or None
        use_case: Either 'cca' or 'mlu'

    Returns:
        Display name (e.g., "Optimistic (Low Warming ~2°C)") or "All Scenarios" if None
    """
    if rcp_code is None:
        return "All Scenarios"

    config = load_scenario_config(use_case)
    scenario_descriptions = config['scenario_descriptions']

    rcp_code_lower = rcp_code.lower()
    return scenario_descriptions.get(rcp_code_lower, rcp_code.upper())


def get_scenario_short_name(rcp_code: str) -> str:
    """
    Get SHORT display name for RCP code (for plot titles to avoid overlap).

    Args:
        rcp_code: RCP code (rcp26, rcp45, rcp85)

    Returns:
        Short name (e.g., "Optimistic", "Moderate", "Pessimistic")
    """
    scenario_short_names = {
        'rcp26': 'Optimistic',
        'rcp45': 'Moderate',
        'rcp85': 'Pessimistic'
    }
    rcp_code_lower = rcp_code.lower()
    return scenario_short_names.get(rcp_code_lower, rcp_code.upper())


def get_all_scenarios(use_case: str = "cca") -> list:
    """
    Get list of all valid RCP scenarios.

    Args:
        use_case: Either 'cca' or 'mlu'

    Returns:
        List of RCP codes ['rcp26', 'rcp45', 'rcp85']
    """
    return ['rcp26', 'rcp45', 'rcp85']


def get_user_friendly_scenarios() -> dict:
    """
    Get mapping of user-friendly names to descriptions.

    Returns:
        Dict mapping user names to full descriptions
    """
    return {
        'optimistic': 'Low Warming (~2°C) - Ambitious climate mitigation',
        'moderate': 'Medium Warming (~3°C) - Moderate mitigation efforts',
        'pessimistic': 'High Warming (~4-5°C) - High emissions scenario'
    }
