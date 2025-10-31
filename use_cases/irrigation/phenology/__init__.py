"""
Temporal Phenology Analysis Module

Provides classes and functions for analyzing NDVI/NDWI time-series
and detecting temporal patterns (harvested crops, fallow fields, flooding).

Implements IRR-US-01 temporal phenology requirements.
"""

from .metrics import PhenologyMetrics, PhenologyCalculator
from .classifier import TemporalPattern, TemporalClassification, TemporalClassifier
from .downloader import TimeSeriesDownloader

__all__ = [
    'PhenologyMetrics',
    'PhenologyCalculator',
    'TemporalPattern',
    'TemporalClassification',
    'TemporalClassifier',
    'TimeSeriesDownloader'
]
