"""
MLU Constants - Shared configuration values across all MLU code.

This file contains constant values that should be used consistently across
all MLU queries, models, and scripts.
"""

# ==============================================================================
# THESSALONIKI REGION COORDINATES
# ==============================================================================
# These are the EXACT coordinates from the meteorological NetCDF files
# Source: /home/ggous/Downloads/PILOT_THESSALONIKI_DATA/meteo/evptsp_rcp85.nc
#
# All meteorological data (temperature, precipitation, evapotranspiration, etc.)
# uses these exact bounds. LUSA files cover all of Greece and must be filtered
# to these coordinates.
#
# Latitude values: [40.9, 40.8, 40.7, 40.6, 40.5, 40.4]  (DESCENDING order!)
# Longitude values: [22.5, 22.6, 22.7, 22.8, 22.9]  (ASCENDING order)
#
# ⚠️  IMPORTANT: When using xarray.sel() with slice():
#     - Meteorological files (tas, pr, etc.): lat is DESCENDING → use slice(LAT_MAX, LAT_MIN)
#     - LUSA files: lat is ASCENDING → use slice(LAT_MIN, LAT_MAX)
# ==============================================================================

THESSALONIKI_LAT_MIN = 40.4
THESSALONIKI_LAT_MAX = 40.9
THESSALONIKI_LON_MIN = 22.5
THESSALONIKI_LON_MAX = 22.9

# Tuple format for model initialization
THESSALONIKI_LAT_BOUNDS = (THESSALONIKI_LAT_MIN, THESSALONIKI_LAT_MAX)
THESSALONIKI_LON_BOUNDS = (THESSALONIKI_LON_MIN, THESSALONIKI_LON_MAX)

# ==============================================================================
# CLIMATE DATA TIME RANGES
# ==============================================================================
# Climate data (tas, pr, rsds, evptsp) is available for 2021-2030 (10 years)
# LUSA data is available for 2021-2100 (80 years)
# ==============================================================================

CLIMATE_DATA_START_YEAR = 2021
CLIMATE_DATA_END_YEAR = 2030
LUSA_DATA_START_YEAR = 2021
LUSA_DATA_END_YEAR = 2100

# ==============================================================================
# RCP SCENARIOS
# ==============================================================================

RCP_SCENARIOS = ['rcp26', 'rcp45', 'rcp85']
RCP_SCENARIO_NAMES = {
    'rcp26': 'RCP 2.6 (Low Emissions)',
    'rcp45': 'RCP 4.5 (Medium Emissions)',
    'rcp85': 'RCP 8.5 (High Emissions)'
}

# ==============================================================================
# VISUALIZATION COLORS (Shadcn palette)
# ==============================================================================

SCENARIO_COLORS = {
    'rcp26': '#22c55e',  # Green (low emissions)
    'rcp45': '#f59e0b',  # Orange (medium)
    'rcp85': '#ef4444'   # Red (high emissions)
}

CROP_COLORS = {
    'WHEAT': '#3b82f6',  # Blue
    'MAIZE': '#f97316',  # Orange
    'SOLAR': '#eab308'   # Yellow
}
