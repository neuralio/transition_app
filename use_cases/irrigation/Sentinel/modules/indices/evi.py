"""
EVI (Enhanced Vegetation Index) implementation
"""

from typing import List
import xarray as xr
import numpy as np
from .base_index import BaseIndex


class EVIIndex(BaseIndex):
    """
    Enhanced Vegetation Index (EVI)
    
    Formula: 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
    Range: -1 to +1
    
    EVI is designed to:
    - Reduce atmospheric influences
    - Minimize soil background effects
    - Improve sensitivity in high biomass regions
    - Provide better linearity with vegetation parameters
    
    Advantages over NDVI:
    - Less saturated in dense vegetation
    - Better atmospheric correction
    - Improved soil background handling
    
    Values:
    - < 0.2: Non-vegetated or stressed vegetation
    - 0.2-0.4: Moderate vegetation vigor
    - 0.4-0.6: High vegetation vigor
    - > 0.6: Very dense, healthy vegetation
    """
    
    def __init__(self):
        super().__init__(
            name="EVI",
            long_name="Enhanced Vegetation Index",
            units="dimensionless"
        )
    
    @property
    def required_bands(self) -> List[str]:
        """EVI requires NIR (B08), Red (B04), and Blue (B02) bands"""
        return ["B08", "B04", "B02"]
    
    def calculate(self, ds: xr.Dataset) -> xr.DataArray:
        """
        Calculate EVI with proper masking and nodata handling.
        
        Args:
            ds: xarray Dataset containing B08 (NIR), B04 (Red), and B02 (Blue) bands
            
        Returns:
            xarray DataArray with EVI values
        """
        # Get original spatial reference from source band
        source_band = ds["B08"]
        
        # Scale bands to reflectance
        scaled_bands = self.scale_and_validate_bands(ds)
        nir = scaled_bands["B08"]
        red = scaled_bands["B04"]
        blue = scaled_bands["B02"]
        
        print(f"      EVI bands - NIR: [{float(nir.min()):.3f}, {float(nir.max()):.3f}], "
              f"Red: [{float(red.min()):.3f}, {float(red.max()):.3f}], "
              f"Blue: [{float(blue.min()):.3f}, {float(blue.max()):.3f}]")
        
        # Calculate denominator: NIR + 6*Red - 7.5*Blue + 1
        denom = nir + 6*red - 7.5*blue + 1
        denom = self.preserve_spatial_reference(denom, source_band)
        
        print(f"      EVI denominator range: [{float(denom.min()):.3f}, {float(denom.max()):.3f}]")
        
        # Create EVI with proper masking
        evi = xr.where(denom > 0.0001, 2.5 * (nir - red) / denom, np.nan)
        
        # Preserve spatial reference and set attributes
        evi = self.preserve_spatial_reference(evi, source_band)
        evi = self.set_attributes(evi, source_band)
        
        # Debug EVI values
        valid_evi = evi.where(~np.isnan(evi))
        if not valid_evi.isnull().all():
            print(f"      EVI range: [{float(valid_evi.min()):.3f}, {float(valid_evi.max()):.3f}]")
        else:
            print(f"      EVI: All values are NaN!")
        
        # Clip to reasonable EVI range
        evi = self.clip_to_valid_range(evi, -1, 1)
        
        # Verify spatial reference is still intact
        print(f"      Final EVI CRS: {evi.rio.crs}")
        
        return evi