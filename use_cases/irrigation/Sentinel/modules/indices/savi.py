"""
SAVI (Soil Adjusted Vegetation Index) implementation
"""

from typing import List
import xarray as xr
import numpy as np
from .base_index import BaseIndex


class SAVIIndex(BaseIndex):
    """
    Soil Adjusted Vegetation Index (SAVI)
    
    Formula: ((NIR - Red) / (NIR + Red + L)) * (1 + L)
    Range: -1 to +1
    
    Where L is the soil brightness correction factor:
    - L = 0: Dense vegetation (equivalent to NDVI)
    - L = 0.5: Intermediate vegetation density (default)
    - L = 1: Sparse vegetation or bare soil
    
    SAVI is designed to:
    - Minimize soil background influences
    - Improve vegetation detection in arid/semi-arid regions
    - Provide better accuracy in sparse vegetation areas
    - Reduce soil noise in vegetation assessments
    
    Applications:
    - Rangeland monitoring
    - Agricultural crop assessment in early growth stages
    - Vegetation monitoring in arid environments
    - Soil-vegetation discrimination
    
    Values:
    - < 0.1: Bare soil or non-vegetated
    - 0.1-0.3: Sparse vegetation
    - 0.3-0.6: Moderate vegetation
    - > 0.6: Dense vegetation
    """
    
    def __init__(self, L: float = 0.5):
        """
        Initialize SAVI with soil brightness correction factor.
        
        Args:
            L: Soil brightness correction factor (default: 0.5)
               - 0.0 for dense vegetation
               - 0.5 for intermediate vegetation (recommended default)
               - 1.0 for sparse vegetation
        """
        super().__init__(
            name="SAVI",
            long_name="Soil Adjusted Vegetation Index",
            units="dimensionless"
        )
        self.L = L
    
    @property
    def required_bands(self) -> List[str]:
        """SAVI requires NIR (B08) and Red (B04) bands"""
        return ["B08", "B04"]
    
    def calculate(self, ds: xr.Dataset) -> xr.DataArray:
        """
        Calculate SAVI with proper masking and nodata handling.
        
        Args:
            ds: xarray Dataset containing B08 (NIR) and B04 (Red) bands
            
        Returns:
            xarray DataArray with SAVI values
        """
        # Get original spatial reference from source band
        source_band = ds["B08"]
        
        # Scale bands to reflectance
        scaled_bands = self.scale_and_validate_bands(ds)
        nir = scaled_bands["B08"]
        red = scaled_bands["B04"]
        
        print(f"      SAVI bands - NIR: [{float(nir.min()):.3f}, {float(nir.max()):.3f}], "
              f"Red: [{float(red.min()):.3f}, {float(red.max()):.3f}]")
        print(f"      Using L factor: {self.L}")
        
        # Calculate denominator: NIR + Red + L
        denom = nir + red + self.L
        denom = self.preserve_spatial_reference(denom, source_band)
        
        print(f"      SAVI denominator range: [{float(denom.min()):.3f}, {float(denom.max()):.3f}]")
        
        # Create SAVI with proper masking: ((NIR - Red) / (NIR + Red + L)) * (1 + L)
        savi = xr.where(denom > 0.0001, ((nir - red) / denom) * (1 + self.L), np.nan)
        
        # Preserve spatial reference and set attributes
        savi = self.preserve_spatial_reference(savi, source_band)
        savi = self.set_attributes(savi, source_band)
        
        # Add L factor to attributes
        savi.attrs['soil_adjustment_factor'] = self.L
        
        # Debug SAVI values
        valid_savi = savi.where(~np.isnan(savi))
        if not valid_savi.isnull().all():
            print(f"      SAVI range: [{float(valid_savi.min()):.3f}, {float(valid_savi.max()):.3f}]")
        else:
            print(f"      SAVI: All values are NaN!")
        
        # Clip to reasonable SAVI range
        savi = self.clip_to_valid_range(savi, -1, 1)
        
        # Verify spatial reference is still intact
        print(f"      Final SAVI CRS: {savi.rio.crs}")
        
        return savi