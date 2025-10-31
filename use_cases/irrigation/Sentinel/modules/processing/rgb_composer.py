"""
RGB composite creation for Sentinel-2 data
"""

from typing import Optional, Tuple
import xarray as xr
import numpy as np
from .cloud_masking import CloudMasker


class RGBComposer:
    """
    Creates RGB composites from Sentinel-2 bands with proper NoData handling
    and optional cloud masking.
    """
    
    def __init__(self, cloud_masker: Optional[CloudMasker] = None):
        """
        Initialize RGB composer.
        
        Args:
            cloud_masker: Optional CloudMasker for creating cloud-free RGB
        """
        self.cloud_masker = cloud_masker
    
    def create_rgb(self, ds: xr.Dataset, apply_cloud_mask: bool = False) -> xr.DataArray:
        """
        Create RGB composite with proper NoData handling.
        
        Args:
            ds: Dataset containing B02 (Blue), B03 (Green), B04 (Red) bands
            apply_cloud_mask: Whether to apply cloud masking (requires SCL band)
            
        Returns:
            RGB composite as xarray DataArray with 3 bands (R, G, B)
        """
        # Validate required bands
        required_bands = ['B02', 'B03', 'B04']
        missing_bands = [band for band in required_bands if band not in ds]
        if missing_bands:
            raise ValueError(f"Missing required bands for RGB: {missing_bands}")
        
        # Get original spatial reference from source band
        source_band = ds["B04"]
        original_crs = getattr(source_band.rio, 'crs', None) if hasattr(source_band, 'rio') else None
        original_transform = getattr(source_band.rio, 'transform', lambda: None)() if hasattr(source_band, 'rio') else None
        
        # Get individual bands and handle NoData values
        red = ds["B04"].astype('float32')
        green = ds["B03"].astype('float32') 
        blue = ds["B02"].astype('float32')
        
        # Print data ranges for debugging
        print(f"      Raw band ranges - Red: [{float(red.min()):.0f}, {float(red.max()):.0f}], "
              f"Green: [{float(green.min()):.0f}, {float(green.max()):.0f}], "
              f"Blue: [{float(blue.min()):.0f}, {float(blue.max()):.0f}]")
        
        # Handle NoData values and scale to 0-1 range
        red_scaled, green_scaled, blue_scaled = self._scale_and_validate_bands(red, green, blue)
        
        # Preserve spatial reference during scaling
        if hasattr(red_scaled, 'rio') and original_crs is not None:
            for band_data in [red_scaled, green_scaled, blue_scaled]:
                band_data.rio.write_crs(original_crs, inplace=True)
                if original_transform is not None:
                    band_data.rio.write_transform(original_transform, inplace=True)
        
        # Apply cloud masking if requested and SCL is available
        if apply_cloud_mask and self.cloud_masker and 'SCL' in ds:
            print(f"      Applying cloud masking to RGB bands...")
            red_scaled = self.cloud_masker.apply_mask(red_scaled, ds['SCL'])
            green_scaled = self.cloud_masker.apply_mask(green_scaled, ds['SCL'])
            blue_scaled = self.cloud_masker.apply_mask(blue_scaled, ds['SCL'])
        elif apply_cloud_mask and 'SCL' not in ds:
            print(f"      Warning: Cloud masking requested but SCL band not available")
        
        # Create RGB stack (R, G, B order)
        rgb = xr.concat([red_scaled, green_scaled, blue_scaled], dim="band")
        
        # Restore spatial reference
        if hasattr(rgb, 'rio') and original_crs is not None:
            rgb.rio.write_crs(original_crs, inplace=True)
            if original_transform is not None:
                rgb.rio.write_transform(original_transform, inplace=True)
        
        # Set attributes
        rgb_name = "RGB_cloud_masked" if apply_cloud_mask else "RGB"
        rgb.name = rgb_name
        rgb.attrs = source_band.attrs.copy()
        rgb.attrs.update({
            'long_name': 'RGB Composite' + (' (Cloud Masked)' if apply_cloud_mask else ''),
            'units': 'reflectance',
            'band_order': 'Red, Green, Blue',
            'cloud_masked': apply_cloud_mask
        })
        
        # Print final statistics
        valid_pixels = (~np.isnan(rgb.isel(band=0))).sum().values
        total_pixels = rgb.isel(band=0).size
        print(f"      RGB: {valid_pixels}/{total_pixels} valid pixels ({100*valid_pixels/total_pixels:.1f}%)")
        
        return rgb
    
    def _scale_and_validate_bands(self, red: xr.DataArray, green: xr.DataArray, 
                                 blue: xr.DataArray) -> Tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
        """
        Scale and validate RGB bands with proper NoData handling.
        
        Args:
            red, green, blue: Raw band data arrays
            
        Returns:
            Tuple of scaled and validated band arrays
        """
        # Handle NoData values (commonly 0 or very large values in Sentinel-2)
        for band_name, band_data in [("Red", red), ("Green", green), ("Blue", blue)]:
            # Mask out clearly invalid values
            invalid_mask = (band_data <= 0) | (band_data > 10000)
            invalid_count = invalid_mask.sum().values
            if invalid_count > 0:
                print(f"      {band_name}: Found {invalid_count} invalid pixels (<=0 or >10000), setting to NaN")
        
        # Apply masks and scale to 0-1 range (Sentinel-2 L2A values are 0-10000)
        red_scaled = xr.where((red > 0) & (red <= 10000), red / 10000.0, np.nan)
        green_scaled = xr.where((green > 0) & (green <= 10000), green / 10000.0, np.nan)
        blue_scaled = xr.where((blue > 0) & (blue <= 10000), blue / 10000.0, np.nan)
        
        return red_scaled, green_scaled, blue_scaled
    
    def create_both_versions(self, ds: xr.Dataset) -> dict:
        """
        Create both regular and cloud-masked RGB composites.
        
        Args:
            ds: Dataset containing required bands (B02, B03, B04, optionally SCL)
            
        Returns:
            Dictionary with 'rgb' and optionally 'rgb_cloud_masked' keys
        """
        results = {}
        
        # Create regular RGB
        try:
            rgb = self.create_rgb(ds, apply_cloud_mask=False)
            results['rgb'] = rgb
            print(f"      ✓ Created regular RGB composite")
        except Exception as e:
            print(f"      ✗ Failed to create RGB composite: {e}")
            results['rgb'] = None
        
        # Create cloud-masked RGB if SCL is available and cloud masker is configured
        if self.cloud_masker and 'SCL' in ds:
            try:
                rgb_masked = self.create_rgb(ds, apply_cloud_mask=True)
                results['rgb_cloud_masked'] = rgb_masked
                print(f"      ✓ Created cloud-masked RGB composite")
            except Exception as e:
                print(f"      ✗ Failed to create cloud-masked RGB: {e}")
                results['rgb_cloud_masked'] = None
        else:
            if not self.cloud_masker:
                print(f"      - No cloud masker configured, skipping cloud-masked RGB")
            elif 'SCL' not in ds:
                print(f"      - No SCL band available, skipping cloud-masked RGB")
        
        return results