"""
Base class for all vegetation indices
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import xarray as xr
import numpy as np


class BaseIndex(ABC):
    """
    Abstract base class for all vegetation indices.
    
    Provides common functionality for spatial reference handling,
    attribute management, and cloud masking integration.
    """
    
    def __init__(self, name: str, long_name: str, units: str = "dimensionless"):
        """
        Initialize base index.
        
        Args:
            name: Short name for the index (e.g., 'NDVI')
            long_name: Descriptive name (e.g., 'Normalized Difference Vegetation Index')
            units: Units of measurement (default: 'dimensionless')
        """
        self.name = name
        self.long_name = long_name
        self.units = units
    
    @property
    @abstractmethod
    def required_bands(self) -> List[str]:
        """List of required Sentinel-2 bands for this index"""
        pass
    
    @abstractmethod
    def calculate(self, ds: xr.Dataset) -> xr.DataArray:
        """
        Calculate the vegetation index.
        
        Args:
            ds: xarray Dataset containing Sentinel-2 bands
            
        Returns:
            xarray DataArray with calculated index values
        """
        pass
    
    def validate_inputs(self, ds: xr.Dataset) -> bool:
        """
        Validate that required bands are present in the dataset.
        
        Args:
            ds: xarray Dataset to validate
            
        Returns:
            True if all required bands are present
            
        Raises:
            ValueError: If required bands are missing
        """
        missing_bands = [band for band in self.required_bands if band not in ds]
        if missing_bands:
            raise ValueError(f"{self.name} requires bands {self.required_bands}, missing: {missing_bands}")
        return True
    
    def preserve_spatial_reference(self, data_array: xr.DataArray, source_band: xr.DataArray) -> xr.DataArray:
        """
        Preserve spatial reference information from source band.
        
        Args:
            data_array: Target array to update
            source_band: Source array with spatial reference
            
        Returns:
            Updated data array with spatial reference
        """
        if hasattr(source_band, 'rio'):
            original_crs = source_band.rio.crs
            original_transform = source_band.rio.transform()
            
            data_array.rio.write_crs(original_crs, inplace=True)
            data_array.rio.write_transform(original_transform, inplace=True)
        
        return data_array
    
    def set_attributes(self, data_array: xr.DataArray, source_band: xr.DataArray) -> xr.DataArray:
        """
        Set proper attributes for the calculated index.
        
        Args:
            data_array: Index data array
            source_band: Source band for copying attributes
            
        Returns:
            Data array with updated attributes
        """
        data_array.name = self.name
        data_array.attrs = source_band.attrs.copy()
        data_array.attrs.update({
            'long_name': self.long_name,
            'units': self.units,
            'index_type': 'vegetation_index'
        })
        
        return data_array
    
    def scale_and_validate_bands(self, ds: xr.Dataset) -> dict:
        """
        Scale Sentinel-2 bands from DN (0-10000) to reflectance (0.0-1.0) and validate.
        
        Args:
            ds: Dataset containing Sentinel-2 bands
            
        Returns:
            Dictionary of scaled band arrays
        """
        scaled_bands = {}
        
        for band in self.required_bands:
            if band == 'SCL':  # Skip SCL band - no scaling needed
                scaled_bands[band] = ds[band]
                continue
                
            # Scale from DN to reflectance
            scaled = ds[band].astype('float32') / 10000.0
            
            # Preserve spatial reference
            scaled = self.preserve_spatial_reference(scaled, ds[band])
            
            scaled_bands[band] = scaled
            
            # Print debug info
            print(f"      {band} scaled range: [{float(scaled.min()):.3f}, {float(scaled.max()):.3f}]")
        
        return scaled_bands
    
    def clip_to_valid_range(self, result: xr.DataArray, min_val: float = -1, max_val: float = 1) -> xr.DataArray:
        """
        Clip index values to valid range.
        
        Args:
            result: Index values to clip
            min_val: Minimum valid value
            max_val: Maximum valid value
            
        Returns:
            Clipped index values
        """
        return result.clip(min_val, max_val)
    
    def __call__(self, ds: xr.Dataset) -> xr.DataArray:
        """
        Convenience method to calculate index.
        
        Args:
            ds: xarray Dataset containing required bands
            
        Returns:
            Calculated index as xarray DataArray
        """
        self.validate_inputs(ds)
        return self.calculate(ds)