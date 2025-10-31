"""
SCL-based cloud masking for Sentinel-2 data
"""

from typing import Union, List, Optional
import xarray as xr
import numpy as np
from ..constants import SCL_CLOUD_MASK, SCL_CLEAR_CLASSES


class CloudMasker:
    """
    Cloud masking using Sentinel-2 Scene Classification Layer (SCL).
    
    Provides functionality to create cloud masks and apply them to
    data arrays or indices for cloud-free product generation.
    """
    
    def __init__(self, mask_classes: Optional[List[int]] = None):
        """
        Initialize cloud masker.
        
        Args:
            mask_classes: List of SCL values to mask out. If None, uses default cloud mask.
        """
        self.mask_classes = mask_classes if mask_classes is not None else SCL_CLOUD_MASK
        print(f"CloudMasker initialized with mask classes: {self.mask_classes}")
    
    def create_cloud_mask(self, scl_data: xr.DataArray) -> xr.DataArray:
        """
        Create cloud mask from SCL data.
        
        Args:
            scl_data: Scene Classification Layer data
            
        Returns:
            Boolean mask where True = clear pixels, False = cloudy/bad pixels
        """
        # Create mask where True = clear pixels, False = clouds/shadows/bad data
        clear_mask = ~np.isin(scl_data, self.mask_classes)
        
        # Convert to xarray with same coordinates as input
        mask = xr.DataArray(
            clear_mask,
            coords=scl_data.coords,
            dims=scl_data.dims,
            attrs={
                'long_name': 'Cloud/Shadow Clear Mask',
                'description': f'True=clear, False=masked (classes {self.mask_classes})'
            }
        )
        
        return mask
    
    def apply_mask(self, data_array: xr.DataArray, scl_data: xr.DataArray, 
                   fill_value: Union[float, int] = np.nan) -> xr.DataArray:
        """
        Apply SCL-based cloud mask to data array.
        
        Args:
            data_array: Data to mask
            scl_data: Scene Classification Layer data
            fill_value: Value to use for masked pixels (default: NaN)
            
        Returns:
            Masked data array
        """
        # Get original spatial reference from source array
        original_crs = getattr(data_array.rio, 'crs', None) if hasattr(data_array, 'rio') else None
        original_transform = getattr(data_array.rio, 'transform', lambda: None)() if hasattr(data_array, 'rio') else None
        
        # Create cloud mask
        cloud_mask = self.create_cloud_mask(scl_data)
        
        # Apply mask - set cloudy pixels to fill_value
        masked_data = xr.where(cloud_mask, data_array, fill_value)
        
        # Restore spatial reference if available
        if hasattr(masked_data, 'rio') and original_crs is not None:
            masked_data.rio.write_crs(original_crs, inplace=True)
            if original_transform is not None:
                masked_data.rio.write_transform(original_transform, inplace=True)
        
        # Copy attributes and update name
        masked_data.attrs = data_array.attrs.copy()
        masked_data.attrs['cloud_masked'] = True
        masked_data.attrs['mask_classes'] = self.mask_classes
        
        if hasattr(data_array, 'name') and data_array.name:
            masked_data.name = f"{data_array.name}_cloud_free"
        else:
            masked_data.name = "cloud_free"
        
        return masked_data
    
    def get_mask_statistics(self, scl_data: xr.DataArray) -> dict:
        """
        Calculate statistics about cloud/clear pixels.
        
        Args:
            scl_data: Scene Classification Layer data
            
        Returns:
            Dictionary with mask statistics
        """
        cloud_mask = self.create_cloud_mask(scl_data)
        
        total_pixels = cloud_mask.size
        clear_pixels = cloud_mask.sum().values
        masked_pixels = total_pixels - clear_pixels
        
        # Get counts for each SCL class
        scl_values, scl_counts = np.unique(scl_data.values, return_counts=True)
        class_stats = dict(zip(scl_values.astype(int), scl_counts.astype(int)))
        
        return {
            'total_pixels': int(total_pixels),
            'clear_pixels': int(clear_pixels),
            'masked_pixels': int(masked_pixels),
            'clear_percentage': float(clear_pixels / total_pixels * 100),
            'masked_percentage': float(masked_pixels / total_pixels * 100),
            'scl_class_counts': class_stats
        }
    
    def apply_to_indices(self, indices_dict: dict, scl_data: xr.DataArray) -> dict:
        """
        Apply cloud masking to multiple indices.
        
        Args:
            indices_dict: Dictionary of index_name -> xarray.DataArray
            scl_data: Scene Classification Layer data
            
        Returns:
            Dictionary of cloud-free indices
        """
        cloud_free_indices = {}
        
        print(f"    Applying cloud masking to {len(indices_dict)} indices...")
        
        # Get mask statistics
        stats = self.get_mask_statistics(scl_data)
        print(f"    Mask statistics: {stats['clear_percentage']:.1f}% clear, "
              f"{stats['masked_percentage']:.1f}% masked")
        
        for name, index_data in indices_dict.items():
            if index_data is not None:
                try:
                    masked_index = self.apply_mask(index_data, scl_data)
                    cloud_free_indices[f"{name}_cloud_free"] = masked_index
                    print(f"      ✓ {name} -> {name}_cloud_free")
                except Exception as e:
                    print(f"      ✗ Failed to mask {name}: {e}")
                    cloud_free_indices[f"{name}_cloud_free"] = None
            else:
                cloud_free_indices[f"{name}_cloud_free"] = None
        
        return cloud_free_indices
    
    def validate_scl_data(self, scl_data: xr.DataArray) -> bool:
        """
        Validate SCL data for cloud masking.
        
        Args:
            scl_data: Scene Classification Layer data to validate
            
        Returns:
            True if SCL data is valid
            
        Raises:
            ValueError: If SCL data is invalid
        """
        if scl_data is None:
            raise ValueError("SCL data is None")
        
        # Check for expected SCL value range (0-11)
        min_val = float(scl_data.min())
        max_val = float(scl_data.max())
        
        if min_val < 0 or max_val > 11:
            print(f"Warning: SCL values outside expected range [0,11]: [{min_val}, {max_val}]")
        
        # Check for all-NoData SCL
        if min_val == max_val == 0:
            print("Warning: SCL data appears to be all NoData (value 0)")
            return False
        
        return True