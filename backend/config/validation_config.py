"""
Centralized validation configuration for coordinate validation.

This module provides a single source of truth for validation parameters
used across all use cases (MLU, CCA, GCP).
"""

# Coordinate validation epsilon tolerance
# Used for floating point comparison at polygon/data boundaries
# Value: 1e-5 degrees ≈ 1.1 meters (very tight tolerance for floating point precision only)
COORDINATE_EPSILON = 1e-5


def get_coordinate_epsilon() -> float:
    """
    Get the epsilon tolerance for coordinate validation.

    This tolerance is added to bounding box checks to handle:
    - Floating point precision issues
    - Exact boundary coordinates

    Returns:
        float: Epsilon value in degrees (~1.1m, essentially for floating point comparison only)
    """
    return COORDINATE_EPSILON
