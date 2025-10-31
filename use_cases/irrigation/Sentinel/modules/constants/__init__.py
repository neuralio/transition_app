"""Constants and mappings for Sentinel-2 processing"""

from .band_mappings import BAND_MAPPINGS
from .scl_classes import SCL_CLASSES, SCL_CLOUD_MASK, SCL_CLEAR_CLASSES

__all__ = ['BAND_MAPPINGS', 'SCL_CLASSES', 'SCL_CLOUD_MASK', 'SCL_CLEAR_CLASSES']