"""
Temporal compositing for Sentinel-2 time series data
"""

from typing import List, Tuple, Dict, Any
from pathlib import Path
import pandas as pd
import xarray as xr
import numpy as np
from datetime import datetime


class TemporalCompositor:
    """
    Creates temporal composites from Sentinel-2 time series data.
    
    Supports dekadal (10-day) and 16-day compositing with various
    reduction methods (max, median, mean).
    """
    
    def __init__(self, rule: str = "10D", reducer: str = "max", outdir: str = "data"):
        """
        Initialize temporal compositor.
        
        Args:
            rule: Temporal resampling rule ('10D' for dekadal, '16D' for 16-day)
            reducer: Reduction method ('max', 'median', 'mean')
            outdir: Output directory for composite files
        """
        self.rule = rule
        self.reducer = reducer
        self.outdir = Path(outdir)
        
        # Validate inputs
        if rule not in ['10D', '16D']:
            raise ValueError(f"Unsupported rule: {rule}. Use '10D' or '16D'")
        if reducer not in ['max', 'median', 'mean']:
            raise ValueError(f"Unsupported reducer: {reducer}. Use 'max', 'median', or 'mean'")
        
        print(f"TemporalCompositor initialized: {rule} periods using {reducer} reduction")
    
    def create_time_series(self, per_date_datasets: List[Tuple[xr.Dataset, str]], 
                          index_name: str = "NDVI") -> xr.DataArray:
        """
        Create time series from per-date datasets for a specific index.
        
        Args:
            per_date_datasets: List of (dataset, date_string) tuples
            index_name: Name of index to create time series for
            
        Returns:
            Time series data array with time dimension
        """
        from ..indices import index_registry
        
        print(f"    Creating {index_name} time series from {len(per_date_datasets)} dates...")
        
        time_slices = []
        valid_dates = []
        
        for ds, date_str in per_date_datasets:
            try:
                # Check if required bands are available
                index_obj = index_registry.get_index(index_name)
                required_bands = index_obj.required_bands
                
                if all(band in ds for band in required_bands):
                    # Calculate index for this date
                    index_data = index_obj(ds)
                    
                    # Convert date string to datetime and add time dimension
                    date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                    index_data = index_data.expand_dims(time=[np.datetime64(date_obj)])
                    time_slices.append(index_data)
                    valid_dates.append(date_str)
                    print(f"      ✓ Added {index_name} for {date_str}")
                else:
                    missing = [b for b in required_bands if b not in ds]
                    print(f"      - Skipped {date_str}: missing bands {missing}")
                    
            except Exception as e:
                print(f"      ✗ Failed to process {index_name} for {date_str}: {e}")
                continue
        
        if not time_slices:
            raise ValueError(f"No valid {index_name} data found in any date")
        
        # Create time series by concatenating along time dimension
        time_series = xr.concat(time_slices, dim="time")
        time_series.name = f"{index_name}_timeseries"
        
        print(f"    ✓ Created {index_name} time series with {len(valid_dates)} dates")
        return time_series
    
    def apply_temporal_reduction(self, time_series: xr.DataArray) -> xr.DataArray:
        """
        Apply temporal reduction to create composites.
        
        Args:
            time_series: Time series data array
            
        Returns:
            Temporal composites
        """
        print(f"    Applying {self.rule} temporal compositing using {self.reducer} reduction...")
        
        # Group by temporal rule
        grouped = time_series.resample(time=self.rule)
        
        # Apply reduction method
        if self.reducer == "max":
            composites = grouped.max()
        elif self.reducer == "median":
            composites = grouped.median()
        elif self.reducer == "mean":
            composites = grouped.mean()
        else:
            raise ValueError(f"Unsupported reducer: {self.reducer}")
        
        # Update attributes
        composites.name = f"{time_series.name}_{self.rule}_{self.reducer}"
        composites.attrs = time_series.attrs.copy()
        composites.attrs.update({
            'temporal_rule': self.rule,
            'reduction_method': self.reducer,
            'composite_type': 'temporal'
        })
        
        print(f"    ✓ Created {len(composites.time)} temporal composites")
        return composites
    
    def save_individual_composites(self, composites: xr.DataArray, index_name: str) -> List[str]:
        """
        Save individual composite files (one per time period).
        
        Args:
            composites: Temporal composites data array
            index_name: Name of the index
            
        Returns:
            List of saved file paths
        """
        from ..utils.file_utils import save_geotiff
        
        # Use unified dekadal directory for all indices
        dekadal_dir = self.outdir / "products" / "indices" / "dekadal"
        dekadal_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        print(f"    Saving {len(composites.time)} individual {self.rule} composites...")
        
        for i, time_slice in enumerate(composites.time):
            # Get the period start date
            period_start_dt = pd.to_datetime(time_slice.values)
            period_start = period_start_dt.strftime('%Y%m%d')
            
            # Calculate period end date based on the rule
            if self.rule == '10D':
                period_end_dt = period_start_dt + pd.Timedelta(days=9)  # 10 days inclusive
            elif self.rule == '16D':
                period_end_dt = period_start_dt + pd.Timedelta(days=15)  # 16 days inclusive
            else:
                period_end_dt = period_start_dt + pd.Timedelta(days=9)  # Fallback
            
            period_end = period_end_dt.strftime('%Y%m%d')
            
            # Extract composite for this period
            composite_slice = composites.isel(time=i)
            composite_slice.name = f"{index_name}_dekadal_{self.reducer}"
            
            # Create descriptive filename with start and end dates
            filename = f"{index_name}_dekadal_{self.reducer}_{period_start}_{period_end}.tif"
            file_path = dekadal_dir / filename
            
            # Save composite
            if save_geotiff(composite_slice, file_path):
                saved_files.append(str(file_path))
                print(f"      ✓ Saved dekadal period {period_start} to {period_end} ({self.rule})")
            else:
                print(f"      ✗ Failed to save {filename}")
        
        return saved_files
    
    def save_daily_timeseries(self, time_series: xr.DataArray, index_name: str) -> List[str]:
        """
        Save individual daily files from time series.
        
        Args:
            time_series: Time series data array
            index_name: Name of the index
            
        Returns:
            List of saved file paths
        """
        from ..utils.file_utils import save_geotiff
        
        # Use unified daily temporal directory for all indices
        daily_dir = self.outdir / "products" / "indices" / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        print(f"    Saving {len(time_series.time)} daily {index_name} files...")
        
        for i, time_slice in enumerate(time_series.time):
            date_str = pd.to_datetime(time_slice.values).strftime('%Y%m%d')
            daily_slice = time_series.isel(time=i)
            daily_slice.name = f"{index_name}_daily"
            
            filename = f"{index_name}_daily_{date_str}.tif"
            file_path = daily_dir / filename
            
            # Save daily file
            if save_geotiff(daily_slice, file_path):
                saved_files.append(str(file_path))
                print(f"      ✓ Saved daily {index_name} for {date_str}")
            else:
                print(f"      ✗ Failed to save {filename}")
        
        return saved_files
    
    def process_temporal_composites(self, per_date_datasets: List[Tuple[xr.Dataset, str]], 
                                   index_name: str = "NDVI") -> Dict[str, Any]:
        """
        Complete temporal composite processing workflow.
        
        Args:
            per_date_datasets: List of (dataset, date_string) tuples
            index_name: Name of index to process
            
        Returns:
            Dictionary with processing results and file paths
        """
        try:
            print(f"\nProcessing {self.rule} temporal composites for {index_name}...")
            
            # Create time series
            time_series = self.create_time_series(per_date_datasets, index_name)
            
            # Apply temporal reduction
            composites = self.apply_temporal_reduction(time_series)
            
            # Save individual composite files
            composite_files = self.save_individual_composites(composites, index_name)
            
            # Save individual daily files  
            daily_files = self.save_daily_timeseries(time_series, index_name)
            
            return {
                'index_name': index_name,
                'rule': self.rule,
                'reducer': self.reducer,
                'composites_created': len(composite_files),
                'daily_files_created': len(daily_files),
                'composite_files': composite_files,
                'daily_files': daily_files,
                'status': 'success'
            }
            
        except Exception as e:
            print(f"    ✗ Failed to process temporal composites for {index_name}: {e}")
            return {
                'index_name': index_name,
                'status': 'failed',
                'error': str(e),
                'composites_created': 0
            }