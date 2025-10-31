"""
NDVI (Normalized Difference Vegetation Index) implementation
"""

from typing import List
import xarray as xr
import numpy as np
from .base_index import BaseIndex


class NDVIIndex(BaseIndex):
    """
    Normalized Difference Vegetation Index (NDVI)
    
    Formula: (NIR - Red) / (NIR + Red)
    Range: -1 to +1
    
    NDVI is the most widely used vegetation index, indicating:
    - Vegetation presence and vigor
    - Biomass estimation
    - Photosynthetic activity
    
    Values:
    - < 0.1: Non-vegetated (water, snow, clouds, bare soil)
    - 0.1-0.3: Sparse vegetation (grasslands, crops in early growth)
    - 0.3-0.6: Moderate vegetation (agricultural crops, mixed vegetation)
    - > 0.6: Dense vegetation (forests, mature crops)
    """
    
    def __init__(self):
        super().__init__(
            name="NDVI",
            long_name="Normalized Difference Vegetation Index",
            units="dimensionless"
        )
    
    @property
    def required_bands(self) -> List[str]:
        """NDVI requires NIR (B08) and Red (B04) bands"""
        return ["B08", "B04"]
    
    def calculate(self, ds: xr.Dataset) -> xr.DataArray:
        """
        Calculate NDVI with proper masking and nodata handling.
        
        Args:
            ds: xarray Dataset containing B08 (NIR) and B04 (Red) bands
            
        Returns:
            xarray DataArray with NDVI values
        """
        # Get original spatial reference from source band
        source_band = ds["B08"]
        
        print(f"      Original CRS: {source_band.rio.crs}")
        print(f"      Original Transform: {source_band.rio.transform()}")
        
        # Scale bands to reflectance
        scaled_bands = self.scale_and_validate_bands(ds)
        nir = scaled_bands["B08"]
        red = scaled_bands["B04"]
        
        # Calculate denominator and preserve spatial info
        denom = nir + red
        denom = self.preserve_spatial_reference(denom, source_band)
        
        print(f"      Denominator range: [{float(denom.min()):.3f}, {float(denom.max()):.3f}]")
        
        # Check for zero denominators
        zero_denom_count = (denom == 0).sum().values
        total_pixels = denom.size
        print(f"      Zero denominators: {zero_denom_count}/{total_pixels} pixels")
        
        # Create NDVI with proper masking - use small threshold for division
        ndvi = xr.where(denom > 0.0001, (nir - red) / denom, np.nan)
        
        # Preserve spatial reference and set attributes
        ndvi = self.preserve_spatial_reference(ndvi, source_band)
        ndvi = self.set_attributes(ndvi, source_band)
        
        # Debug NDVI before clipping
        valid_ndvi = ndvi.where(~np.isnan(ndvi))
        if not valid_ndvi.isnull().all():
            print(f"      NDVI before clipping: [{float(valid_ndvi.min()):.3f}, {float(valid_ndvi.max()):.3f}]")
        else:
            print(f"      NDVI: All values are NaN!")
        
        # Clip to valid NDVI range
        ndvi = self.clip_to_valid_range(ndvi, -1, 1)
        
        # Verify spatial reference is still intact
        print(f"      Final NDVI CRS: {ndvi.rio.crs}")
        
        return ndvi