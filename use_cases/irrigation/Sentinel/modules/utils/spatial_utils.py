"""
Spatial processing utilities for Sentinel-2 data
"""

from typing import Tuple, List, Optional, Union
import xarray as xr
import numpy as np
from shapely.geometry import box
import geopandas as gpd
from rasterio.warp import reproject, Resampling
from rasterio.enums import Resampling as RioResampling


def reproject_to_match(source_data: xr.DataArray, target_data: xr.DataArray, 
                      resampling: str = 'nearest') -> xr.DataArray:
    """
    Reproject source data to match target data's CRS and grid.
    
    Args:
        source_data: Source data to reproject
        target_data: Target data with desired CRS and grid
        resampling: Resampling method ('nearest', 'bilinear', 'cubic')
        
    Returns:
        Reprojected source data
    """
    # Map resampling method names to rasterio enums
    resampling_methods = {
        'nearest': RioResampling.nearest,
        'bilinear': RioResampling.bilinear,
        'cubic': RioResampling.cubic,
        'cubic_spline': RioResampling.cubic_spline,
        'lanczos': RioResampling.lanczos,
        'average': RioResampling.average,
        'mode': RioResampling.mode
    }
    
    if resampling not in resampling_methods:
        raise ValueError(f"Unsupported resampling method: {resampling}")
    
    try:
        # Use rioxarray's reproject_match method
        reprojected = source_data.rio.reproject_match(
            target_data,
            resampling=resampling_methods[resampling]
        )
        
        # Preserve original attributes
        reprojected.attrs = source_data.attrs.copy()
        reprojected.attrs['reprojected'] = True
        reprojected.attrs['resampling_method'] = resampling
        
        return reprojected
        
    except Exception as e:
        print(f"Error reprojecting data: {e}")
        return source_data  # Return original on error


def calculate_bbox_overlap(bbox1: Tuple[float, float, float, float], 
                          bbox2: Tuple[float, float, float, float]) -> float:
    """
    Calculate the overlap percentage between two bounding boxes.
    
    Args:
        bbox1: First bbox as (minx, miny, maxx, maxy)
        bbox2: Second bbox as (minx, miny, maxx, maxy)
        
    Returns:
        Overlap percentage (0-100)
    """
    # Create shapely box geometries
    box1 = box(*bbox1)
    box2 = box(*bbox2)
    
    # Calculate intersection
    intersection = box1.intersection(box2)
    
    if intersection.area == 0:
        return 0.0
    
    # Calculate overlap as percentage of smaller box
    smaller_area = min(box1.area, box2.area)
    overlap_percent = (intersection.area / smaller_area) * 100
    
    return overlap_percent


def clip_to_bbox(data_array: xr.DataArray, 
                bbox: Tuple[float, float, float, float]) -> xr.DataArray:
    """
    Clip data array to bounding box.
    
    Args:
        data_array: Data to clip
        bbox: Bounding box as (minx, miny, maxx, maxy)
        
    Returns:
        Clipped data array
    """
    minx, miny, maxx, maxy = bbox
    
    try:
        # Use rioxarray's clip_box method
        clipped = data_array.rio.clip_box(minx, miny, maxx, maxy)
        
        # Preserve attributes
        clipped.attrs = data_array.attrs.copy()
        clipped.attrs['clipped_to_bbox'] = bbox
        
        return clipped
        
    except Exception as e:
        print(f"Error clipping to bbox: {e}")
        return data_array


def calculate_pixel_area(data_array: xr.DataArray) -> float:
    """
    Calculate pixel area in square meters.
    
    Args:
        data_array: Data array with spatial coordinates
        
    Returns:
        Pixel area in square meters
    """
    try:
        # Get pixel size from transform if available
        if hasattr(data_array, 'rio') and hasattr(data_array.rio, 'transform'):
            transform = data_array.rio.transform()
            pixel_width = abs(transform[0])
            pixel_height = abs(transform[4])
            
            # Convert to meters if in degrees (rough approximation)
            if hasattr(data_array.rio, 'crs') and data_array.rio.crs:
                crs_string = str(data_array.rio.crs)
                if 'EPSG:4326' in crs_string or 'WGS84' in crs_string:
                    # Rough conversion: 1 degree ≈ 111,319 meters at equator
                    pixel_width *= 111319
                    pixel_height *= 111319
            
            return pixel_width * pixel_height
        
        # Fallback: calculate from coordinates
        x_coords = data_array.x if 'x' in data_array.coords else data_array.longitude
        y_coords = data_array.y if 'y' in data_array.coords else data_array.latitude
        
        x_res = float(np.diff(x_coords)[0])
        y_res = float(np.diff(y_coords)[0])
        
        return abs(x_res * y_res)
        
    except Exception as e:
        print(f"Error calculating pixel area: {e}")
        return 100.0  # Default 10m x 10m for Sentinel-2


def mosaic_arrays(arrays: List[xr.DataArray], method: str = 'first') -> xr.DataArray:
    """
    Mosaic multiple data arrays into a single array.
    
    Args:
        arrays: List of data arrays to mosaic
        method: Mosaic method ('first', 'last', 'mean', 'max', 'min')
        
    Returns:
        Mosaicked data array
    """
    if not arrays:
        raise ValueError("No arrays provided for mosaicking")
    
    if len(arrays) == 1:
        return arrays[0]
    
    try:
        # Ensure all arrays have the same CRS
        reference_crs = arrays[0].rio.crs if hasattr(arrays[0], 'rio') else None
        
        # Reproject all arrays to match the first one's grid
        aligned_arrays = []
        for i, arr in enumerate(arrays):
            if i == 0:
                aligned_arrays.append(arr)
            else:
                reprojected = reproject_to_match(arr, arrays[0])
                aligned_arrays.append(reprojected)
        
        # Combine arrays based on method
        if method == 'first':
            # Use first valid pixel
            combined = xr.concat(aligned_arrays, dim='mosaic')
            result = combined.isel(mosaic=0)
            for i in range(1, len(aligned_arrays)):
                mask = np.isnan(result) | (result == 0)
                result = xr.where(mask, combined.isel(mosaic=i), result)
                
        elif method == 'last':
            # Use last valid pixel
            combined = xr.concat(aligned_arrays, dim='mosaic')
            result = combined.isel(mosaic=-1)
            for i in range(len(aligned_arrays)-2, -1, -1):
                mask = np.isnan(result) | (result == 0)
                result = xr.where(mask, combined.isel(mosaic=i), result)
                
        elif method == 'mean':
            # Average all valid pixels
            combined = xr.concat(aligned_arrays, dim='mosaic')
            result = combined.mean(dim='mosaic', skipna=True)
            
        elif method == 'max':
            # Maximum of all valid pixels
            combined = xr.concat(aligned_arrays, dim='mosaic') 
            result = combined.max(dim='mosaic', skipna=True)
            
        elif method == 'min':
            # Minimum of all valid pixels
            combined = xr.concat(aligned_arrays, dim='mosaic')
            result = combined.min(dim='mosaic', skipna=True)
            
        else:
            raise ValueError(f"Unsupported mosaic method: {method}")
        
        # Preserve attributes from first array
        result.attrs = arrays[0].attrs.copy()
        result.attrs['mosaic_method'] = method
        result.attrs['mosaic_count'] = len(arrays)
        
        return result
        
    except Exception as e:
        print(f"Error mosaicking arrays: {e}")
        # Return first array as fallback
        return arrays[0]


def get_data_extent(data_array: xr.DataArray) -> Tuple[float, float, float, float]:
    """
    Get the spatial extent of a data array.
    
    Args:
        data_array: Data array with spatial coordinates
        
    Returns:
        Extent as (minx, miny, maxx, maxy)
    """
    try:
        if hasattr(data_array, 'rio') and hasattr(data_array.rio, 'bounds'):
            bounds = data_array.rio.bounds()
            return bounds
        
        # Fallback: calculate from coordinates
        x_coords = data_array.x if 'x' in data_array.coords else data_array.longitude
        y_coords = data_array.y if 'y' in data_array.coords else data_array.latitude
        
        minx, maxx = float(x_coords.min()), float(x_coords.max())
        miny, maxy = float(y_coords.min()), float(y_coords.max())
        
        return (minx, miny, maxx, maxy)
        
    except Exception as e:
        print(f"Error getting data extent: {e}")
        return (0.0, 0.0, 1.0, 1.0)  # Default extent