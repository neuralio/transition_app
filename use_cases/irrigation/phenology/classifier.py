"""
Temporal Pattern Classifier Module

Classifies parcels based on temporal phenology patterns.
Implements IRR-US-01 temporal pattern recognition requirements.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from .metrics import PhenologyMetrics


class TemporalPattern(Enum):
    """Temporal phenology patterns."""
    HARVESTED_CROP = "harvested_crop"
    TRULY_FALLOW = "truly_fallow"
    IRRIGATED_FLOODED = "irrigated_flooded"
    VEGETATED = "vegetated"
    UNKNOWN = "unknown"


@dataclass
class TemporalClassification:
    """
    Temporal classification result for a parcel.

    Attributes:
        parcel_id: Unique parcel identifier
        pattern: Detected temporal pattern
        confidence: Classification confidence (0-1)
        reason: Human-readable explanation
        metrics: Associated phenology metrics
    """
    parcel_id: int
    pattern: TemporalPattern
    confidence: float
    reason: str
    metrics: PhenologyMetrics

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'parcel_id': self.parcel_id,
            'pattern': self.pattern.value,
            'confidence': self.confidence,
            'reason': self.reason,
            'metrics': self.metrics.to_dict()
        }


class TemporalClassifier:
    """
    Classifies parcels based on NDVI/NDWI temporal patterns.

    Implements classification rules from IRR-US-01:
    - Harvested crop: max NDVI > 0.6, end NDVI < 0.2 (NDVI drop indicates harvest)
    - Truly fallow: max NDVI < 0.3 all season (consistently bare)
    - Irrigated/Flooded: NDWI > 0 sustained for ≥7 days
    """

    def __init__(
        self,
        harvested_max_ndvi_threshold: float = 0.6,
        harvested_end_ndvi_threshold: float = 0.2,
        fallow_max_ndvi_threshold: float = 0.3,
        flooding_min_days: int = 7,
        vegetated_ndvi_threshold: float = 0.4
    ):
        """
        Initialize classifier with configurable thresholds.

        Args:
            harvested_max_ndvi_threshold: Min max NDVI for harvested crop (default: 0.6)
            harvested_end_ndvi_threshold: Max end NDVI for harvested crop (default: 0.2)
            fallow_max_ndvi_threshold: Max NDVI for fallow classification (default: 0.3)
            flooding_min_days: Min consecutive days for flooding detection (default: 7)
            vegetated_ndvi_threshold: Min mean NDVI for vegetated (default: 0.4)
        """
        self.harvested_max_ndvi_threshold = harvested_max_ndvi_threshold
        self.harvested_end_ndvi_threshold = harvested_end_ndvi_threshold
        self.fallow_max_ndvi_threshold = fallow_max_ndvi_threshold
        self.flooding_min_days = flooding_min_days
        self.vegetated_ndvi_threshold = vegetated_ndvi_threshold

    def classify(self, metrics: PhenologyMetrics) -> TemporalClassification:
        """
        Classify parcel based on phenology metrics.

        Args:
            metrics: Calculated phenology metrics

        Returns:
            TemporalClassification with detected pattern
        """
        # Rule 1: Check for irrigated/flooded pattern (highest priority)
        if metrics.sustained_flooding_days >= self.flooding_min_days:
            return TemporalClassification(
                parcel_id=metrics.parcel_id,
                pattern=TemporalPattern.IRRIGATED_FLOODED,
                confidence=0.9,
                reason=f"NDWI > 0 sustained for {metrics.sustained_flooding_days} days (≥{self.flooding_min_days} days threshold)",
                metrics=metrics
            )

        # Rule 2: Check for harvested crop pattern
        # High NDVI mid-season → low NDVI end-season = harvest event
        if (metrics.max_ndvi > self.harvested_max_ndvi_threshold and
            metrics.end_ndvi < self.harvested_end_ndvi_threshold):

            # Check for significant NDVI drop (senescence)
            if metrics.ndvi_drop_rate > 0.01:  # Positive = decline
                confidence = min(0.95, 0.7 + (metrics.ndvi_drop_rate * 10))
                return TemporalClassification(
                    parcel_id=metrics.parcel_id,
                    pattern=TemporalPattern.HARVESTED_CROP,
                    confidence=confidence,
                    reason=f"Max NDVI={metrics.max_ndvi:.2f} (>{self.harvested_max_ndvi_threshold}), End NDVI={metrics.end_ndvi:.2f} (<{self.harvested_end_ndvi_threshold}), Drop rate={metrics.ndvi_drop_rate:.3f}",
                    metrics=metrics
                )

        # Rule 3: Check for truly fallow pattern
        # Low NDVI throughout entire season = consistently bare
        if metrics.max_ndvi < self.fallow_max_ndvi_threshold:
            confidence = 1.0 - (metrics.max_ndvi / self.fallow_max_ndvi_threshold) * 0.2
            return TemporalClassification(
                parcel_id=metrics.parcel_id,
                pattern=TemporalPattern.TRULY_FALLOW,
                confidence=confidence,
                reason=f"Max NDVI={metrics.max_ndvi:.2f} (<{self.fallow_max_ndvi_threshold}) all season - consistently bare",
                metrics=metrics
            )

        # Rule 4: Check for vegetated pattern
        # Moderate to high NDVI maintained throughout season
        if metrics.mean_ndvi >= self.vegetated_ndvi_threshold:
            confidence = min(0.9, metrics.mean_ndvi / self.vegetated_ndvi_threshold * 0.7)
            return TemporalClassification(
                parcel_id=metrics.parcel_id,
                pattern=TemporalPattern.VEGETATED,
                confidence=confidence,
                reason=f"Mean NDVI={metrics.mean_ndvi:.2f} (≥{self.vegetated_ndvi_threshold}) - sustained vegetation",
                metrics=metrics
            )

        # Default: Unknown pattern
        return TemporalClassification(
            parcel_id=metrics.parcel_id,
            pattern=TemporalPattern.UNKNOWN,
            confidence=0.5,
            reason=f"No clear pattern detected (Max NDVI={metrics.max_ndvi:.2f}, Mean NDVI={metrics.mean_ndvi:.2f})",
            metrics=metrics
        )
