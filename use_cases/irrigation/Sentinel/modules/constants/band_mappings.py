"""
Band mappings for different STAC providers
"""

BAND_MAPPINGS = {
    "standard": {
        "B02": "B02", "B03": "B03", "B04": "B04", "B08": "B08", "SCL": "SCL"
    },
    "aws": {
        "B02": "blue", "B03": "green", "B04": "red", "B08": "nir08", "SCL": "scl"
    }
}

def get_band_mapping(stac_url: str) -> dict:
    """Get the appropriate band mapping based on STAC provider"""
    if "earth-search.aws" in stac_url:
        return BAND_MAPPINGS["aws"]
    else:
        return BAND_MAPPINGS["standard"]