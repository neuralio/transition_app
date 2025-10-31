#!/usr/bin/env python3
"""
NetCDF Inspector Script

Quick script to inspect NetCDF files and see their structure, variables, and data.

Usage:
    python inspect_netcdf.py <path_to_nc_file>
    python inspect_netcdf.py /home/ggous/Downloads/PILOT_THESSALONIKI_DATA/WHEAT/RCP26_LUSA_PREDICTIONS.nc
"""

import sys
import xarray as xr
import numpy as np
from pathlib import Path


def inspect_netcdf(file_path: str):
    """
    Inspect a NetCDF file and print detailed information.

    Args:
        file_path: Path to NetCDF file
    """
    file_path = Path(file_path)

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    print(f"\n{'='*80}")
    print(f"📁 Inspecting NetCDF File")
    print(f"{'='*80}")
    print(f"File: {file_path.name}")
    print(f"Path: {file_path}")
    print(f"Size: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"{'='*80}\n")

    # Load dataset
    print("📂 Loading dataset...")
    ds = xr.open_dataset(file_path)

    # Print full dataset structure
    print("\n1️⃣  DATASET STRUCTURE")
    print("-" * 80)
    print(ds)

    # Print dimensions
    print(f"\n2️⃣  DIMENSIONS")
    print("-" * 80)
    for dim_name, dim_size in ds.dims.items():
        print(f"  {dim_name:20s}: {dim_size}")

    # Print coordinates
    print(f"\n3️⃣  COORDINATES")
    print("-" * 80)
    for coord_name, coord_data in ds.coords.items():
        if coord_name in ds.dims:
            print(f"  {coord_name:20s}: {coord_data.dtype} [{coord_data.min().values} to {coord_data.max().values}]")
            if len(coord_data) <= 10:
                print(f"    Values: {coord_data.values}")

    # Print data variables
    print(f"\n4️⃣  DATA VARIABLES")
    print("-" * 80)
    for var_name, var_data in ds.data_vars.items():
        print(f"\n  Variable: {var_name}")
        print(f"    Dimensions: {var_data.dims}")
        print(f"    Shape: {var_data.shape}")
        print(f"    Dtype: {var_data.dtype}")
        print(f"    Size: {var_data.size:,} values")

        # Statistics
        print(f"    Statistics:")
        print(f"      Min:    {float(var_data.min().values):.6f}")
        print(f"      Max:    {float(var_data.max().values):.6f}")
        print(f"      Mean:   {float(var_data.mean().values):.6f}")
        print(f"      Median: {float(var_data.median().values):.6f}")
        print(f"      Std:    {float(var_data.std().values):.6f}")

        # Count non-zero/non-nan
        non_zero = int((var_data != 0).sum().values)
        non_nan = int((~np.isnan(var_data)).sum().values)
        print(f"      Non-zero: {non_zero:,} ({non_zero/var_data.size*100:.1f}%)")
        print(f"      Non-NaN:  {non_nan:,} ({non_nan/var_data.size*100:.1f}%)")

        # Attributes
        if var_data.attrs:
            print(f"    Attributes:")
            for attr_name, attr_value in var_data.attrs.items():
                print(f"      {attr_name}: {attr_value}")

    # Print global attributes
    if ds.attrs:
        print(f"\n5️⃣  GLOBAL ATTRIBUTES")
        print("-" * 80)
        for attr_name, attr_value in ds.attrs.items():
            print(f"  {attr_name}: {attr_value}")

    # Sample data
    print(f"\n6️⃣  SAMPLE DATA")
    print("-" * 80)
    for var_name in ds.data_vars:
        var_data = ds[var_name]
        print(f"\n  {var_name} (first few values):")

        # Show first time slice if it's a time series
        if 'time' in var_data.dims:
            sample = var_data.isel(time=0)
            print(f"    Time slice 0 (shape: {sample.shape}):")
            if sample.ndim == 2:
                print(f"      First 5x5 grid:\n{sample.values[:5, :5]}")
            elif sample.ndim == 1:
                print(f"      First 10 values: {sample.values[:10]}")
        else:
            if var_data.ndim == 2:
                print(f"    First 5x5 grid:\n{var_data.values[:5, :5]}")
            elif var_data.ndim == 1:
                print(f"    First 10 values: {var_data.values[:10]}")
            else:
                print(f"    Shape: {var_data.shape}")

    print(f"\n{'='*80}")
    print(f"✅ Inspection Complete!")
    print(f"{'='*80}\n")

    ds.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n❌ Usage: python inspect_netcdf.py <path_to_nc_file>")
        print("\nExample:")
        print("  python inspect_netcdf.py /app/data/WHEAT/RCP26_LUSA_PREDICTIONS.nc")
        print("\nOr inspect multiple files:")
        print("  python inspect_netcdf.py /path/to/data/WHEAT/*.nc\n")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        inspect_netcdf(file_path)
        if len(sys.argv) > 2:
            print("\n" + "="*80 + "\n")
