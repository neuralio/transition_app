"""
Time-Series EO Data Downloader

Downloads NDVI/NDWI for multiple dates to support temporal phenology analysis.
Implements IRR-US-01 cloud gap handling and multi-date compositing.
"""

from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import sys

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.api.routes.ndvi_ondemand import download_ndvi_for_query


class TimeSeriesDownloader:
    """
    Downloads NDVI/NDWI time-series for phenology analysis.

    Splits date range into temporal windows and downloads composite for each window.
    """

    def __init__(self, temporal_window_days: int = 10):
        """
        Initialize downloader.

        Args:
            temporal_window_days: Size of each temporal window in days (default: 10)
                                 Each window produces one NDVI/NDWI observation
        """
        self.temporal_window_days = temporal_window_days

    def download_time_series(
        self,
        geojson: dict,
        start_date: str,
        end_date: str
    ) -> Tuple[List[Tuple[str, str, str]], List[str], int]:
        """
        Download NDVI/NDWI time-series for date range.

        Args:
            geojson: Region of interest (GeoJSON)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Tuple of:
            - List of (ndvi_path, ndwi_path, date_label) tuples
            - List of date labels (for time axis)
            - Total scenes processed

        Raises:
            ValueError: If date range is too short or downloads fail
        """
        # Split date range into temporal windows
        date_windows = self._create_date_windows(start_date, end_date)

        if len(date_windows) < 3:
            raise ValueError(
                f"Date range too short for temporal analysis. "
                f"Need at least 3 observations (30 days), got {len(date_windows)} windows. "
                f"Increase date range or reduce temporal_window_days."
            )

        print(f"\n📅 Temporal Analysis: {len(date_windows)} time windows")
        print(f"   Window size: {self.temporal_window_days} days")
        print(f"   Date range: {start_date} → {end_date}")

        # Download data for each window
        time_series_data = []
        total_scenes = 0

        for i, (window_start, window_end) in enumerate(date_windows, 1):
            date_label = window_start  # Use window start as label

            print(f"\n   [{i}/{len(date_windows)}] Downloading {window_start} → {window_end}...")

            ndvi_path, ndwi_path, message, scenes = download_ndvi_for_query(
                geojson=geojson,
                start_date=window_start,
                end_date=window_end,
                indices=["NDVI", "NDWI"]
            )

            if not ndvi_path:
                print(f"      ⚠️  Warning: {message} (skipping window)")
                continue

            print(f"      ✅ Downloaded (scenes: {scenes})")
            time_series_data.append((ndvi_path, ndwi_path, date_label))
            total_scenes += scenes

        if len(time_series_data) < 3:
            raise ValueError(
                f"Insufficient data for temporal analysis. "
                f"Got {len(time_series_data)}/{len(date_windows)} valid windows. "
                f"Need at least 3 observations."
            )

        # Extract date labels
        date_labels = [data[2] for data in time_series_data]

        print(f"\n✅ Time-series download complete:")
        print(f"   Valid observations: {len(time_series_data)}/{len(date_windows)}")
        print(f"   Total scenes: {total_scenes}")

        return time_series_data, date_labels, total_scenes

    def _create_date_windows(
        self,
        start_date: str,
        end_date: str
    ) -> List[Tuple[str, str]]:
        """
        Create temporal windows for date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of (window_start, window_end) date string tuples
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        windows = []
        current_start = start_dt

        while current_start < end_dt:
            current_end = min(
                current_start + timedelta(days=self.temporal_window_days),
                end_dt
            )

            windows.append((
                current_start.strftime("%Y-%m-%d"),
                current_end.strftime("%Y-%m-%d")
            ))

            current_start = current_end

        return windows
