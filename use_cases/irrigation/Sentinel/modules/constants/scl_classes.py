"""
Sentinel-2 Scene Classification Layer (SCL) values and cloud masking definitions
"""

# SCL (Scene Classification Layer) values for cloud masking
SCL_CLASSES = {
    0: "NO_DATA",
    1: "SATURATED_OR_DEFECTIVE", 
    2: "DARK_AREA_PIXELS",
    3: "CLOUD_SHADOWS",
    4: "VEGETATION",
    5: "NOT_VEGETATED",
    6: "WATER",
    7: "UNCLASSIFIED",
    8: "CLOUD_MEDIUM_PROBABILITY",
    9: "CLOUD_HIGH_PROBABILITY",
    10: "THIN_CIRRUS",
    11: "SNOW"
}

# Define which SCL classes to mask out (clouds, shadows, etc.)
SCL_CLOUD_MASK = [0, 1, 3, 8, 9, 10]  # No data, defective, shadows, clouds, cirrus

# Define clear/valid classes
SCL_CLEAR_CLASSES = [2, 4, 5, 6, 7, 11]  # Dark areas, vegetation, non-vegetated, water, unclassified, snow