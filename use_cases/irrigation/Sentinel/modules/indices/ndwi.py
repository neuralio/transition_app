"""
NDWI (Normalized Difference Water Index) implementation
"""

from typing import List
import xarray as xr
import numpy as np
from .base_index import BaseIndex


class NDWIIndex(BaseIndex):
    """
    Normalized Difference Water Index (NDWI)

    Formula: (Green - NIR) / (Green + NIR)
    Range: -1 to +1

    NDWI is used to monitor water content in vegetation and water bodies:
    - Water body delineation
    - Irrigation monitoring
    - Vegetation water stress detection
    - Flood mapping

    Values:
    - > 0.3: Water bodies (lakes, rivers, wetlands)
    - 0.0-0.3: Moist soil, wetlands, high water content vegetation
    - -0.3-0.0: Moderate moisture vegetation
    - < -0.3: Dry vegetation, bare soil, built-up areas
    """

    def __init__(self):
        super().__init__(
            name="NDWI",
            long_name="Normalized Difference Water Index",
            units="dimensionless"
        )

    @property
    def required_bands(self) -> List[str]:
        """NDWI requires Green (B03) and NIR (B08) bands"""
        return ["B03", "B08"]

    def calculate(self, ds: xr.Dataset) -> xr.DataArray:
        """
        Calculate NDWI with proper masking and nodata handling.

        Args:
            ds: xarray Dataset containing B03 (Green) and B08 (NIR) bands

        Returns:
            xarray DataArray with NDWI values
        """
        # Get original spatial reference from source band
        source_band = ds["B08"]

        print(f"      Original CRS: {source_band.rio.crs}")
        print(f"      Original Transform: {source_band.rio.transform()}")

        # Scale bands to reflectance
        scaled_bands = self.scale_and_validate_bands(ds)
        green = scaled_bands["B03"]
        nir = scaled_bands["B08"]

        # Calculate denominator and preserve spatial info
        denom = green + nir
        denom = self.preserve_spatial_reference(denom, source_band)

        print(f"      Denominator range: [{float(denom.min()):.3f}, {float(denom.max()):.3f}]")

        # Check for zero denominators
        zero_denom_count = (denom == 0).sum().values
        total_pixels = denom.size
        print(f"      Zero denominators: {zero_denom_count}/{total_pixels} pixels")

        # Create NDWI with proper masking - use small threshold for division
        ndwi = xr.where(denom > 0.0001, (green - nir) / denom, np.nan)

        # Preserve spatial reference and set attributes
        ndwi = self.preserve_spatial_reference(ndwi, source_band)
        ndwi = self.set_attributes(ndwi, source_band)

        # Debug NDWI before clipping
        valid_ndwi = ndwi.where(~np.isnan(ndwi))
        if not valid_ndwi.isnull().all():
            print(f"      NDWI before clipping: [{float(valid_ndwi.min()):.3f}, {float(valid_ndwi.max()):.3f}]")
        else:
            print(f"      NDWI: All values are NaN!")

        # Clip to valid NDWI range
        ndwi = self.clip_to_valid_range(ndwi, -1, 1)

        # Verify spatial reference is still intact
        print(f"      Final NDWI CRS: {ndwi.rio.crs}")

        return ndwi
