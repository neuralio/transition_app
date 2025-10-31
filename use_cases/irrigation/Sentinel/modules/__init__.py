"""
Sentinel-2 Processing Pipeline Modules

Modular architecture for Sentinel-2 satellite data processing including:
- Vegetation indices (NDVI, EVI, SAVI)
- Cloud masking using SCL
- RGB composite generation
- Temporal compositing
- Utility functions for file I/O and spatial processing
"""

__version__ = "1.0.0"
__author__ = "Sentinel-2 Processing Pipeline"

# Import main components for easy access
from .indices import index_registry, NDVIIndex, EVIIndex, SAVIIndex
from .processing import CloudMasker, RGBComposer, TemporalCompositor
from .utils import ConfigManager, PipelineLogger, setup_pipeline_logging
from .constants import BAND_MAPPINGS, SCL_CLASSES, SCL_CLOUD_MASK, SCL_CLEAR_CLASSES

__all__ = [
    # Indices
    'index_registry', 'NDVIIndex', 'EVIIndex', 'SAVIIndex',
    # Processing
    'CloudMasker', 'RGBComposer', 'TemporalCompositor', 
    # Utilities
    'ConfigManager', 'PipelineLogger', 'setup_pipeline_logging',
    # Constants
    'BAND_MAPPINGS', 'SCL_CLASSES', 'SCL_CLOUD_MASK', 'SCL_CLEAR_CLASSES'
]