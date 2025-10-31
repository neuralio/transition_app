"""
Phenology Metrics Module

Calculates temporal phenology metrics from NDVI/NDWI time-series.
Implements IRR-US-01 temporal pattern analysis requirements.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
from datetime import datetime


@dataclass
class PhenologyMetrics:
    """
    Temporal phenology metrics for a single parcel.

    Attributes:
        parcel_id: Unique parcel identifier
        max_ndvi: Maximum NDVI during season
        max_ndvi_date: Date when max NDVI occurred
        start_ndvi: NDVI at season start (first observation)
        end_ndvi: NDVI at season end (last observation)
        mean_ndvi: Mean NDVI across all observations
        ndvi_drop_rate: Rate of NDVI decline (slope of senescence)
        max_ndwi: Maximum NDWI during season
        sustained_flooding_days: Number of consecutive days with NDWI > 0
        n_observations: Total number of valid observations
    """
    parcel_id: int
    max_ndvi: float
    max_ndvi_date: str
    start_ndvi: float
    end_ndvi: float
    mean_ndvi: float
    ndvi_drop_rate: float
    max_ndwi: Optional[float]
    sustained_flooding_days: int
    n_observations: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'parcel_id': self.parcel_id,
            'max_ndvi': self.max_ndvi,
            'max_ndvi_date': self.max_ndvi_date,
            'start_ndvi': self.start_ndvi,
            'end_ndvi': self.end_ndvi,
            'mean_ndvi': self.mean_ndvi,
            'ndvi_drop_rate': self.ndvi_drop_rate,
            'max_ndwi': self.max_ndwi,
            'sustained_flooding_days': self.sustained_flooding_days,
            'n_observations': self.n_observations
        }


class PhenologyCalculator:
    """
    Calculates phenology metrics from NDVI/NDWI time-series data.

    Usage:
        calculator = PhenologyCalculator()
        metrics = calculator.compute_metrics(parcel_id, ndvi_series, ndwi_series, dates)
    """

    def __init__(self, ndwi_flood_threshold: float = 0.0):
        """
        Initialize calculator.

        Args:
            ndwi_flood_threshold: NDWI threshold for flooding detection (default: 0.0)
        """
        self.ndwi_flood_threshold = ndwi_flood_threshold

    def compute_metrics(
        self,
        parcel_id: int,
        ndvi_series: List[float],
        ndwi_series: Optional[List[float]],
        dates: List[str]
    ) -> PhenologyMetrics:
        """
        Compute phenology metrics from time-series data.

        Args:
            parcel_id: Parcel identifier
            ndvi_series: List of NDVI values (chronological order)
            ndwi_series: List of NDWI values (same length as ndvi_series, or None)
            dates: List of date strings (ISO format: YYYY-MM-DD)

        Returns:
            PhenologyMetrics object with calculated metrics
        """
        # Input validation
        if not ndvi_series or len(ndvi_series) == 0:
            raise ValueError(f"Empty NDVI series for parcel {parcel_id}")

        if len(ndvi_series) != len(dates):
            raise ValueError(f"NDVI series and dates must have same length")

        # Convert to numpy arrays
        ndvi_arr = np.array(ndvi_series)

        # Find max NDVI and its date
        max_idx = np.argmax(ndvi_arr)
        max_ndvi = float(ndvi_arr[max_idx])
        max_ndvi_date = dates[max_idx]

        # Start and end NDVI
        start_ndvi = float(ndvi_arr[0])
        end_ndvi = float(ndvi_arr[-1])

        # Mean NDVI
        mean_ndvi = float(np.mean(ndvi_arr))

        # Calculate NDVI drop rate (senescence slope)
        # Use linear regression from max NDVI to end of season
        if max_idx < len(ndvi_arr) - 1:
            # Post-peak period (senescence)
            post_peak_ndvi = ndvi_arr[max_idx:]
            n_post = len(post_peak_ndvi)

            if n_post > 1:
                # Simple linear slope: (end - max) / n_days
                # Positive value = decline, negative = increase
                ndvi_drop_rate = float((max_ndvi - end_ndvi) / n_post)
            else:
                ndvi_drop_rate = 0.0
        else:
            # Max NDVI at end of season (no senescence)
            ndvi_drop_rate = 0.0

        # Process NDWI if available
        if ndwi_series and len(ndwi_series) == len(ndvi_series):
            ndwi_arr = np.array(ndwi_series)
            max_ndwi = float(np.max(ndwi_arr))

            # Calculate sustained flooding days (consecutive days with NDWI > threshold)
            sustained_flooding_days = self._calculate_sustained_flooding(ndwi_arr)
        else:
            max_ndwi = None
            sustained_flooding_days = 0

        return PhenologyMetrics(
            parcel_id=parcel_id,
            max_ndvi=max_ndvi,
            max_ndvi_date=max_ndvi_date,
            start_ndvi=start_ndvi,
            end_ndvi=end_ndvi,
            mean_ndvi=mean_ndvi,
            ndvi_drop_rate=ndvi_drop_rate,
            max_ndwi=max_ndwi,
            sustained_flooding_days=sustained_flooding_days,
            n_observations=len(ndvi_series)
        )

    def _calculate_sustained_flooding(self, ndwi_arr: np.ndarray) -> int:
        """
        Calculate maximum consecutive days with NDWI above flooding threshold.

        Args:
            ndwi_arr: Array of NDWI values

        Returns:
            Maximum consecutive days with NDWI > threshold
        """
        # Find consecutive sequences above threshold
        above_threshold = ndwi_arr > self.ndwi_flood_threshold

        if not np.any(above_threshold):
            return 0

        # Find runs of consecutive True values
        max_consecutive = 0
        current_consecutive = 0

        for is_above in above_threshold:
            if is_above:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive
