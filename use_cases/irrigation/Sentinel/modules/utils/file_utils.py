"""
File handling utilities for Sentinel-2 processing pipeline
"""

from typing import Union, Optional
from pathlib import Path
import xarray as xr
import rasterio
from rasterio.enums import Resampling


def save_geotiff(data_array: xr.DataArray, output_path: Union[str, Path], 
                 compress: str = 'lzw', dtype: Optional[str] = None) -> bool:
    """
    Save xarray DataArray as GeoTIFF with proper compression and metadata.
    
    Args:
        data_array: Data to save
        output_path: Path to save file
        compress: Compression method ('lzw', 'deflate', None)
        dtype: Data type to save as (if None, preserves original)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare data for saving
        save_data = data_array.copy()
        
        # Handle dtype conversion if specified
        if dtype:
            save_data = save_data.astype(dtype)
        
        # Set up compression options
        compress_opts = {}
        if compress:
            compress_opts['compress'] = compress
            if compress == 'lzw':
                compress_opts['predictor'] = 2  # Horizontal differencing for better compression
        
        # Save using rioxarray
        if hasattr(save_data, 'rio'):
            save_data.rio.to_raster(
                output_path,
                driver='GTiff',
                dtype=save_data.dtype if not dtype else dtype,
                **compress_opts
            )
        else:
            # Fallback: convert to rioxarray first
            save_data = save_data.rio.write_crs("EPSG:4326")  # Default CRS if none
            save_data.rio.to_raster(
                output_path,
                driver='GTiff',
                dtype=save_data.dtype if not dtype else dtype,
                **compress_opts
            )
        
        return True
        
    except Exception as e:
        print(f"Error saving {output_path}: {e}")
        return False


def create_output_directories(base_dir: Union[str, Path], 
                            subdirs: list = None) -> dict:
    """
    Create standardized output directory structure.
    
    Args:
        base_dir: Base output directory
        subdirs: List of subdirectories to create
        
    Returns:
        Dictionary mapping subdirectory names to Path objects
    """
    base_path = Path(base_dir)
    
    if subdirs is None:
        subdirs = [
            'products/rgb',
            'products/indices/daily',
            'products/indices/dekadal', 
            'products/indices/legacy',
            'metadata',
            'logs'
        ]
    
    created_dirs = {}
    
    for subdir in subdirs:
        dir_path = base_path / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Use just the last part as key for easy access
        key = Path(subdir).name if '/' in subdir else subdir
        created_dirs[key] = dir_path
    
    print(f"Created output directory structure in {base_path}")
    return created_dirs


def get_file_size_mb(file_path: Union[str, Path]) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB
    """
    try:
        size_bytes = Path(file_path).stat().st_size
        return size_bytes / (1024 * 1024)
    except FileNotFoundError:
        return 0.0


def list_geotiff_files(directory: Union[str, Path], 
                      pattern: str = "*.tif") -> list:
    """
    List GeoTIFF files in directory matching pattern.
    
    Args:
        directory: Directory to search
        pattern: File pattern to match
        
    Returns:
        List of matching file paths
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []
    
    return sorted(list(dir_path.glob(pattern)))


def validate_geotiff(file_path: Union[str, Path]) -> dict:
    """
    Validate GeoTIFF file and return metadata.
    
    Args:
        file_path: Path to GeoTIFF file
        
    Returns:
        Dictionary with validation results and metadata
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {'valid': False, 'error': 'File does not exist'}
    
    try:
        with rasterio.open(file_path) as src:
            meta = {
                'valid': True,
                'width': src.width,
                'height': src.height,
                'count': src.count,
                'dtype': str(src.dtype),
                'crs': str(src.crs) if src.crs else None,
                'bounds': src.bounds,
                'transform': src.transform,
                'nodata': src.nodata,
                'file_size_mb': get_file_size_mb(file_path)
            }
            return meta
            
    except Exception as e:
        return {'valid': False, 'error': str(e)}