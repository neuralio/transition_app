# validators.py

def validate_crop_type(value: str):
    value = value.strip().lower()
    return value if value in ["wheat", "maize"] else None

def validate_pilot(value: str):
    value = value.strip().upper()
    return value if value in ["PILOT_THESSALONIKI", "PILOT_PILSEN", "PILOT_OLOMOUC", "GREECE", "CZECHIA"] else None

def validate_time_period(value: str):
    value = value.strip().lower()
    return value if value in ["past", "future"] else None

def validate_validation(value: str):
    value = value.strip().lower()
    return value if value in ["yes", "no"] else None

def validate_geojson(value: str):
    return value if value.strip().startswith("{") and '"type":' in value else None

def validate_zero_one(value):
    return value if 0.0 <= value <= 1.0 else None