"""Vegetation indices for Sentinel-2 data"""

from .ndvi import NDVIIndex
from .evi import EVIIndex
from .savi import SAVIIndex
from .ndwi import NDWIIndex
from .registry import IndexRegistry

# Create the global registry
index_registry = IndexRegistry()

# Register available indices
index_registry.register('NDVI', NDVIIndex)
index_registry.register('EVI', EVIIndex)
index_registry.register('SAVI', SAVIIndex)
index_registry.register('NDWI', NDWIIndex)

__all__ = ['NDVIIndex', 'EVIIndex', 'SAVIIndex', 'NDWIIndex', 'index_registry']