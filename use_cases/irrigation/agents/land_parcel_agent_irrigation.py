"""Land Parcel Agent for Irrigation Use Case

Extends MLU LandParcelAgent with:
- RICE and COTTON crop types
- NDVI-based bare soil detection
- Dynamic crop assignment using EO observations
- Water demand tracking for irrigation planning
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from use_cases.mlu.agents.land_parcel_agent import LandParcelAgent
import yaml


class LandParcelAgentIrrigation(LandParcelAgent):
    """
    Irrigation-specific land parcel agent.

    Inherits from MLU LandParcelAgent and adds:
    - Additional crop types (RICE, COTTON)
    - NDVI-based bare soil detection
    - Seasonal crop rotation logic
    - Water demand tracking
    """

    def __init__(self, model, lat, lon, rl_policy=None, initial_crop=None, config_path=None):
        """Initialize irrigation land parcel agent.

        Args:
            model: LandUseModel instance
            lat: Latitude
            lon: Longitude
            rl_policy: Optional RLPolicy instance
            initial_crop: Optional initial crop assignment
            config_path: Path to irrigation config.yaml
        """
        # Call parent constructor
        super().__init__(model, lat, lon, rl_policy, initial_crop)

        # Load irrigation-specific configuration
        self.config_path = config_path or Path(__file__).parent.parent / "config.yaml"
        self.load_irrigation_config()

        # Irrigation-specific attributes
        self.current_season = None  # "summer" or "winter"
        self.is_bare_soil = False  # Detected via NDVI
        self.ndvi_value = None  # Current NDVI observation
        self.ndwi_value = None  # Current NDWI observation (for rice flood detection)
        self.is_flooded = False  # For rice parcels only
        self.annual_water_demand_mm = 0.0  # Total irrigation water needed (mm)
        self.actual_water_supplied_mm = 0.0  # Actual water supplied by cooperative

    def load_irrigation_config(self):
        """Load irrigation configuration from YAML files."""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Load crop calendar
        crop_calendar_path = Path(self.config_path).parent / config['crop_calendar_file']
        with open(crop_calendar_path, 'r') as f:
            self.crop_calendar = yaml.safe_load(f)

        # Load EO thresholds
        eo_thresholds_path = Path(self.config_path).parent / config['eo_thresholds_file']
        with open(eo_thresholds_path, 'r') as f:
            self.eo_thresholds = yaml.safe_load(f)

    def detect_bare_soil_from_ndvi(self, ndvi_value):
        """
        Detect bare soil using NDVI threshold from configuration.

        Args:
            ndvi_value: NDVI observation from Sentinel-2

        Returns:
            bool: True if parcel is bare soil, False otherwise
        """
        threshold = self.eo_thresholds['bare_soil_detection']['ndvi_threshold']
        confidence = self.eo_thresholds['bare_soil_detection']['confidence_level']

        # Store current NDVI
        self.ndvi_value = ndvi_value

        # Simple threshold-based detection
        # In full implementation, would check pixel-level confidence
        self.is_bare_soil = ndvi_value < threshold

        return self.is_bare_soil

    def detect_rice_flooding_from_ndwi(self, ndwi_value):
        """
        Detect rice flooding using NDWI threshold.

        Args:
            ndwi_value: NDWI observation from Sentinel-2

        Returns:
            bool: True if flooding detected, False otherwise
        """
        if self.current_crop != "RICE":
            return False

        threshold = self.eo_thresholds['rice_flood_detection']['ndwi_threshold']
        min_area_pct = self.eo_thresholds['rice_flood_detection']['min_flooded_area_pct']

        # Store current NDWI
        self.ndwi_value = ndwi_value

        # Simple threshold-based detection
        # In full implementation, would check spatial coverage
        self.is_flooded = ndwi_value > threshold

        return self.is_flooded

    def assign_crop_from_rotation_rules(self, season):
        """
        Assign crop based on seasonal rotation rules from crop calendar.

        Args:
            season: "summer" or "winter"

        Returns:
            str: Assigned crop name
        """
        import random

        if season == "winter":
            # Summer-to-winter rule
            rotation = self.crop_calendar['crop_rotation']['summer_to_winter']

            if 'crop' in rotation:
                # Deterministic rule
                return rotation['crop']
            else:
                # Stochastic rule
                crops = rotation['crops']
                crop_names = [c['name'] for c in crops]
                probabilities = [c['probability'] for c in crops]
                return random.choices(crop_names, weights=probabilities)[0]

        else:  # summer
            # Winter-to-summer rule
            rotation = self.crop_calendar['crop_rotation']['winter_to_summer']

            if 'crop' in rotation:
                return rotation['crop']
            else:
                crops = rotation['crops']
                crop_names = [c['name'] for c in crops]
                probabilities = [c['probability'] for c in crops]
                return random.choices(crop_names, weights=probabilities)[0]

    def calculate_water_demand(self):
        """
        Calculate annual irrigation water demand based on current crop.

        Uses crop-specific irrigation requirements from crop calendar.

        Returns:
            float: Water demand in mm
        """
        if self.current_crop is None:
            return 0.0

        # Find crop in summer or winter crop lists
        for crop_season in ['summer_crops', 'winter_crops']:
            if crop_season not in self.crop_calendar:
                continue

            for crop_info in self.crop_calendar[crop_season]:
                if crop_info['name'] == self.current_crop:
                    # Check if rice is flooded or not
                    if self.current_crop == "RICE" and not self.is_flooded:
                        # Rice not flooded → use alternate crop water demand
                        # Or mark as fallow
                        action = self.eo_thresholds['rice_flood_detection']['no_flood_action']
                        if action == "reassign_or_fallow":
                            return 0.0  # Mark as fallow for now

                    return crop_info.get('total_irrigation_mm', 0.0)

        return 0.0

    def step(self):
        """Execute one time step (one year) with irrigation-specific logic."""
        # 1. Detect bare soil (would use real NDVI from model in full implementation)
        # For now, use placeholder logic

        # 2. Assign crop based on rotation rules if bare soil detected
        # This would be integrated with parent class decision logic

        # 3. Calculate water demand
        self.annual_water_demand_mm = self.calculate_water_demand()

        # 4. Call parent step() for standard land-use decision
        super().step()

        # 5. Validate rice flooding if rice was assigned
        if self.current_crop == "RICE":
            # Would call detect_rice_flooding_from_ndwi() with real NDWI data
            pass

    def get_economic_state(self):
        """
        Get parcel's economic state including water demand (for upward flow).

        Returns:
            Dict with economic indicators + irrigation metrics
        """
        state = super().get_economic_state()

        # Add irrigation-specific metrics
        state.update({
            'annual_water_demand_mm': self.annual_water_demand_mm,
            'actual_water_supplied_mm': self.actual_water_supplied_mm,
            'water_deficit_mm': self.annual_water_demand_mm - self.actual_water_supplied_mm,
            'is_bare_soil': self.is_bare_soil,
            'ndvi_value': self.ndvi_value,
            'is_flooded': self.is_flooded if self.current_crop == "RICE" else None
        })

        return state

    def __repr__(self):
        return f"IrrigationParcel({self.unique_id}, crop={self.current_crop}, water_demand={self.annual_water_demand_mm:.0f}mm)"
