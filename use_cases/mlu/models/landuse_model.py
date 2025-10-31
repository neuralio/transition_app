"""Land-Use Suitability Model - Mesa ABM with real pilot data."""

import mesa
from mesa.datacollection import DataCollector
from use_cases.mlu.agents.farmer_agent import FarmerAgent
from use_cases.mlu.agents.collective_agent import CollectiveAgent
from use_cases.mlu.agents.market_agent import CommodityMarketAgent
from use_cases.mlu.agents.policymaker_agent import PolicymakerAgent
from use_cases.mlu.agents.pv_agent import PVInstallationAgent
from backend.simulation.framework.orchestrator import MultiLevelOrchestrator
from backend.data.loaders.data_loader import (
    load_crop_suitability,
    load_all_meteo,
    load_all_soil,
    load_dem
)
from backend.data.loaders.yield_loader import YieldDataLoader


class LandUseModel(mesa.Model):
    """Model for land-use suitability simulation."""

    def __init__(self,
                 data_path,
                 crops,
                 scenario,
                 n_parcels=15,  # Consistent default across all MLU cases
                 n_farmers=None,  # DEPRECATED: use n_parcels instead
                 n_pv_installations=None,  # DEPRECATED: use n_parcels instead
                 n_collectives=1,
                 n_markets=1,
                 n_policies=1,
                 lat_bounds=None,
                 lon_bounds=None,
                 start_year=2021,
                 seed=None,
                 enable_multi_level=True,
                 use_land_parcels=True,
                 geojson=None,
                 farmer_locations=None,  #User-specified locations
                 rl_policy=None):
        """Initialize the land-use model.

        Args:
            data_path: Path to data directory
            crops: List of crop names (e.g., ['MAIZE', 'WHEAT'])
            scenario: Climate scenario (e.g., 'rcp26', 'rcp45', 'rcp85')
            n_parcels: Number of land parcel agents (each decides: farm OR solar)
            n_farmers: DEPRECATED - for backward compatibility
            n_pv_installations: DEPRECATED - for backward compatibility
            n_collectives: Number of collective/community agents
            n_markets: Number of market agents
            n_policies: Number of policy agents
            lat_bounds: (min_lat, max_lat) or None for auto-detect
            lon_bounds: (min_lon, max_lon) or None for auto-detect
            start_year: Starting year for simulation
            seed: Random seed
            enable_multi_level: Enable multi-level ABM (default True)
            use_land_parcels: Use LandParcelAgent (True) or legacy FarmerAgent+PV (False)
            geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)
            farmer_locations: User-specified locations (coords)
            rl_policy: Reinforcement learning policy for agent decision-making (optional)
        """
        super().__init__(seed=seed)
        self.data_path = data_path
        self.crops = crops
        self.scenario = scenario
        self.current_year = start_year
        self.enable_multi_level = enable_multi_level
        self.use_land_parcels = use_land_parcels
        self.rl_policy = rl_policy  # RL-02: Store RL policy for agent creation

        # DEBUG: Check geojson before storing (use stderr to ensure it appears in output)
        import sys
        sys.stderr.write(f"🔍 DEBUG __init__: geojson type = {type(geojson)}, is None = {geojson is None}, bool = {bool(geojson)}\n")
        sys.stderr.flush()
        if geojson:
            if isinstance(geojson, dict):
                sys.stderr.write(f"🔍 DEBUG __init__: geojson is dict with keys = {list(geojson.keys())}\n")
            elif isinstance(geojson, str):
                sys.stderr.write(f"🔍 DEBUG __init__: geojson is string, length = {len(geojson)}, first 100 chars = {geojson[:100]}\n")
            sys.stderr.flush()

        self.geojson = geojson  # Store geojson for validation
        sys.stderr.write(f"🔍 DEBUG __init__: self.geojson stored, is None = {self.geojson is None}\n")
        sys.stderr.flush()

        # Handle backward compatibility (convert old n_farmers parameter to n_parcels)
        # Only apply if user explicitly passed n_farmers (not None) and didn't customize n_parcels
        default_n_parcels = 15  # Same as function default parameter
        if n_farmers is not None and n_parcels == default_n_parcels:
            n_parcels = n_farmers + (n_pv_installations or 0)

        self.n_parcels = n_parcels

        # Multi-level agent lists
        self.collective_agents = []
        self.market_agents = []
        self.policy_agents = []
        self.parcel_agents = []  # NEW: land parcels that decide farm vs solar
        # Legacy (for backward compatibility)
        self.pv_agents = []

        # Load crop suitability data
        print(f"Loading crop data ({scenario})...")
        self.crop_data = {}
        for crop in crops:
            print(f"  - {crop}")
            self.crop_data[crop] = load_crop_suitability(data_path, crop, scenario, geojson=geojson)

        # Load meteorological data
        print(f"Loading meteo data ({scenario})...")
        self.meteo_data = load_all_meteo(data_path, scenario, geojson=geojson)
        print(f"  - temperature, precipitation, solar_radiation, evapotranspiration")

        # Load soil data
        print(f"Loading soil data...")
        self.soil_data = load_all_soil(data_path, geojson=geojson)
        print(f"  - soil_type, cec, ph, organic_carbon")

        # Load DEM
        print(f"Loading terrain data...")
        self.dem_data = load_dem(data_path, geojson=geojson)
        print(f"  - elevation")

        # Load yield data (REAL AquaCrop simulations)
        print(f"Loading yield data ({scenario})...")
        self.yield_loader = YieldDataLoader(data_path)
        self.yield_data = self.yield_loader.load_scenario_yields(scenario)
        print(f"  - Y(fresh) for {len(self.yield_data)} daily records")

        # Auto-detect bounds from first crop if not provided
        if lat_bounds is None or lon_bounds is None:
            first_crop_data = self.crop_data[crops[0]]
            lat_bounds = lat_bounds or (float(first_crop_data.lat.min()), float(first_crop_data.lat.max()))
            lon_bounds = lon_bounds or (float(first_crop_data.lon.min()), float(first_crop_data.lon.max()))

        self.lat_bounds = lat_bounds
        self.lon_bounds = lon_bounds

        # Find locations with non-zero suitability for at least one crop
        print(f"Finding suitable locations for {n_parcels} land parcels...")
        if farmer_locations is not None:
            print(f"📍 Using {len(farmer_locations)} user-specified locations")
            suitable_locs = self._validate_user_locations(farmer_locations, self.geojson)
            n_parcels = len(farmer_locations)
        else:
            suitable_locs = self._find_suitable_locations(n_parcels)

        # Create parcel agents
        farmer_agents = []
        from use_cases.mlu.agents.land_parcel_agent import LandParcelAgent

        for i in range(n_parcels):
            if farmer_locations is not None:
                lat = farmer_locations[i]['lat']
                lon = farmer_locations[i]['lon']
                initial_crop = farmer_locations[i]['crop']
            else:
                lat, lon = suitable_locs[i] if i < len(suitable_locs) else suitable_locs[i % len(suitable_locs)]
                initial_crop = None

            parcel = LandParcelAgent(model=self, lat=lat, lon=lon, rl_policy=self.rl_policy, initial_crop=initial_crop)
            self.parcel_agents.append(parcel)
            farmer_agents.append(parcel)

        print(f"\n✅ Created {n_parcels} land parcels (each decides: farm OR solar)")
        print(f"  Using {min(n_parcels, len(suitable_locs))} suitable locations")
        print(f"  Lat: {lat_bounds[0]:.2f} to {lat_bounds[1]:.2f}")
        print(f"  Lon: {lon_bounds[0]:.2f} to {lon_bounds[1]:.2f}")

        if False:  # LEGACY MODE DISABLED - LandParcelAgent is now the standard
            # LEGACY MODE: Separate FarmerAgent and PVInstallationAgent
            n_farmers_legacy = n_farmers if n_farmers is not None else n_parcels
            n_pv_legacy = n_pv_installations if n_pv_installations is not None else 0

            for i in range(n_farmers_legacy):
                if i < len(suitable_locs):
                    lat, lon = suitable_locs[i]
                else:
                    lat, lon = suitable_locs[i % len(suitable_locs)]
                farmer = FarmerAgent(self, lat, lon)
                farmer_agents.append(farmer)

            print(f"\nCreated {n_farmers_legacy} farmers (legacy mode)")
            print(f"  Using {min(n_farmers_legacy, len(suitable_locs))} suitable locations")
            print(f"  Lat: {lat_bounds[0]:.2f} to {lat_bounds[1]:.2f}")
            print(f"  Lon: {lon_bounds[0]:.2f} to {lon_bounds[1]:.2f}")

            # Create PV installation agents at suitable locations
            if n_pv_legacy > 0:
                from use_cases.mlu.agents.pv_agent import PVInstallationAgent

                print(f"\nCreating {n_pv_legacy} PV installations...")
                for i in range(n_pv_legacy):
                    loc_idx = (n_farmers_legacy + i) % len(suitable_locs)
                    lat, lon = suitable_locs[loc_idx]
                    pv_agent = PVInstallationAgent(
                        model=self,
                        lat=lat,
                        lon=lon
                    )
                    self.pv_agents.append(pv_agent)
                print(f"  ✓ Created {len(self.pv_agents)} PV installations")

        # Initialize multi-level ABM if enabled
        if self.enable_multi_level:
            print(f"\n=== Initializing Multi-Level ABM ===")
            self._initialize_multi_level_agents(
                farmer_agents=farmer_agents,
                n_collectives=n_collectives,
                n_markets=n_markets,
                n_policies=n_policies
            )
            # Create orchestrator
            self.orchestrator = MultiLevelOrchestrator(self)
        else:
            self.orchestrator = None

        # Initialize data collector for metrics
        self._initialize_data_collector()

        # Capture initial characteristics (for text reports - shows varied initial prices/norms)
        self._capture_initial_characteristics()

        # Build spatial index for neighbor queries (after all farmers created)
        self._build_spatial_index()

        print()

    def get_suitability(self,
                        lat,
                        lon,
                        crop,
                        year):
        """Get suitability score for a crop at location and year.

        Args:
            lat: Latitude
            lon: Longitude
            crop: Crop name
            year: Year

        Returns:
            Suitability score (0-100)
        """
        if crop not in self.crop_data:
            raise ValueError(f"Crop '{crop}' not loaded. Available: {list(self.crop_data.keys())}")

        data = self.crop_data[crop]
        score_data = data.sel(lat=lat, lon=lon, time=f"{year}-01-01", method="nearest")
        return float(score_data.score.values)

    def get_meteo(self,
                  lat,
                  lon,
                  variable,
                  year):
        """Get meteorological data at location and year.

        Args:
            lat: Latitude
            lon: Longitude
            variable: Meteo variable ('temperature', 'precipitation', 'solar_radiation', 'evapotranspiration')
            year: Year

        Returns:
            Value for the variable
        """
        if variable not in self.meteo_data:
            raise ValueError(f"Variable '{variable}' not loaded. Available: {list(self.meteo_data.keys())}")

        data = self.meteo_data[variable]
        var_name = list(data.data_vars)[0]  # Get actual variable name (tas, pr, rsds, evptsp)

        # Get available time range first
        time_min = int(data.time.min().dt.year.values)
        time_max = int(data.time.max().dt.year.values)

        # Check if year is within available range
        if year < time_min or year > time_max:
            raise ValueError(
                f"❌ ERROR: Year {year} is outside available data range!\n"
                f"   Available years: {time_min} to {time_max}\n"
                f"   Requested year: {year}\n"
                f"   Please reduce the number of simulation years to fit within the available data range.\n"
                f"   Maximum simulation duration: {time_max - time_min + 1} years (starting from {time_min})"
            )

        # Use nearest neighbor with tolerance for spatial filtering
        # This ensures agents slightly outside filtered bounds can still access data
        try:
            value = data[var_name].sel(lat=lat, lon=lon, time=f"{year}-01-01", method="nearest")
            return float(value.values)
        except KeyError as e:
            # If coordinate is outside filtered region, use closest available point
            lat_nearest = data.lat.sel(lat=lat, method="nearest").values
            lon_nearest = data.lon.sel(lon=lon, method="nearest").values
            value = data[var_name].sel(lat=lat_nearest, lon=lon_nearest, time=f"{year}-01-01", method="nearest")
            return float(value.values)

    def get_soil(self,
                 lat,
                 lon,
                 variable):
        """Get soil data at location.

        Args:
            lat: Latitude
            lon: Longitude
            variable: Soil variable ('soil_type', 'cec', 'ph', 'organic_carbon')

        Returns:
            Value for the variable
        """
        if variable not in self.soil_data:
            raise ValueError(f"Variable '{variable}' not loaded. Available: {list(self.soil_data.keys())}")

        data = self.soil_data[variable]
        var_name = list(data.data_vars)[0]  # Get actual variable name

        # Use nearest neighbor with tolerance for spatial filtering
        try:
            value = data[var_name].sel(lat=lat, lon=lon, method="nearest", tolerance=0.1)
            return float(value.values)
        except KeyError:
            # If coordinate is outside filtered region, use closest available point
            lat_nearest = data.lat.sel(lat=lat, method="nearest").values
            lon_nearest = data.lon.sel(lon=lon, method="nearest").values
            value = data[var_name].sel(lat=lat_nearest, lon=lon_nearest)
            return float(value.values)

    def get_elevation(self,
                      lat,
                      lon):
        """Get elevation at location.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Elevation (meters)
        """
        var_name = list(self.dem_data.data_vars)[0]

        # Use nearest neighbor with tolerance for spatial filtering
        try:
            value = self.dem_data[var_name].sel(lat=lat, lon=lon, method="nearest", tolerance=0.1)
            return float(value.values)
        except KeyError:
            # If coordinate is outside filtered region, use closest available point
            lat_nearest = self.dem_data.lat.sel(lat=lat, method="nearest").values
            lon_nearest = self.dem_data.lon.sel(lon=lon, method="nearest").values
            value = self.dem_data[var_name].sel(lat=lat_nearest, lon=lon_nearest)
            return float(value.values)

    def get_expected_yield(self,
                          crop,
                          year):
        """
        Get expected crop yield from REAL AquaCrop simulation data.

        Args:
            crop: Crop name (e.g., 'WHEAT', 'MAIZE')
            year: Year to query

        Returns:
            Expected yield in tons/hectare (from real Y(fresh) data)
        """
        return self.yield_loader.get_annual_yield(
            scenario=self.scenario,
            year=year,
            crop=crop.lower()
        )

    def _find_suitable_locations(self, n_locations):
        """Find LUSA grid pixels with actual crop suitability data and place farmers there.

        Args:
            n_locations: Number of suitable locations to find

        Returns:
            List of (lat, lon) tuples placed ON LUSA grid pixels (with small offset for variety)
        """
        import numpy as np

        # Get first year data for first crop
        first_crop = self.crops[0]
        first_year = self.current_year
        crop_data = self.crop_data[first_crop]

        # Get scores for first timestep
        scores = crop_data.sel(time=f"{first_year}-01-01", method="nearest").score

        # Determine bounds to use: geojson polygon bounds OR model's lat/lon bounds
        if self.geojson:
            # Extract bounds from user's drawn polygon
            from backend.data.loaders.geojson_utils import extract_features, get_bounding_box
            features = extract_features(self.geojson)

            # If multiple polygons, get union bounds
            all_bounds = [get_bounding_box(f.get('geometry', f)) for f in features]
            lat_min = min(b['lat_min'] for b in all_bounds)
            lat_max = max(b['lat_max'] for b in all_bounds)
            lon_min = min(b['lon_min'] for b in all_bounds)
            lon_max = max(b['lon_max'] for b in all_bounds)

            print(f"🔍 Received {len(features)} polygon(s) from user")
            for i, bounds in enumerate(all_bounds, 1):
                print(f"   Polygon {i}: lat=[{bounds['lat_min']:.4f}, {bounds['lat_max']:.4f}], lon=[{bounds['lon_min']:.4f}, {bounds['lon_max']:.4f}]")
            print(f"🔍 Using union bounds: lat=[{lat_min:.4f}, {lat_max:.4f}], lon=[{lon_min:.4f}, {lon_max:.4f}]")
        else:
            # Use model's default bounds
            lat_min, lat_max = self.lat_bounds
            lon_min, lon_max = self.lon_bounds
            print(f"🔍 Using model bounds: lat=[{lat_min:.4f}, {lat_max:.4f}], lon=[{lon_min:.4f}, {lon_max:.4f}]")

        # Filter to specified bounds
        scores_region = scores.sel(
            lat=slice(lat_min, lat_max),
            lon=slice(lon_min, lon_max)
        )

        # Find locations where ANY crop has score > 0 (and not NaN)
        suitable_mask = (~np.isnan(scores_region.values)) & (scores_region.values > 0)
        for crop in self.crops[1:]:
            crop_data = self.crop_data[crop]
            scores = crop_data.sel(time=f"{first_year}-01-01", method="nearest").score
            scores_region = scores.sel(
                lat=slice(lat_min, lat_max),
                lon=slice(lon_min, lon_max)
            )
            crop_mask = (~np.isnan(scores_region.values)) & (scores_region.values > 0)
            suitable_mask = suitable_mask | crop_mask

        # Get LUSA grid pixel coordinates where data exists
        lat_indices, lon_indices = np.where(suitable_mask)

        suitable_locs = []

        # If using geojson, prepare point-in-polygon validator with buffering
        if self.geojson:
            from backend.data.loaders.spatial_filter import point_in_polygon
            from shapely.geometry import shape
            from shapely.ops import unary_union

            # Parse geojson and create buffered polygon for more lenient check
            # Buffer by 0.05° (~5km) to catch LUSA pixels near polygon edges
            if self.geojson.get('type') == 'FeatureCollection':
                features = self.geojson.get('features', [])
            elif self.geojson.get('type') == 'Feature':
                features = [self.geojson]
            else:
                features = [{'type': 'Feature', 'geometry': self.geojson}]

            polygons = [shape(f.get('geometry', f)) for f in features]
            combined_polygon = unary_union(polygons)
            buffered_polygon = combined_polygon.buffer(0.05)  # ~5km buffer for LUSA pixel capture

        for lat_idx, lon_idx in zip(lat_indices, lon_indices):
            # Get exact LUSA grid pixel center
            lat = float(scores_region.lat[lat_idx].values)
            lon = float(scores_region.lon[lon_idx].values)

            # If geojson provided, validate point is inside BUFFERED polygon(s)
            # This catches LUSA pixels that overlap with the polygon even if their centers are slightly outside
            if self.geojson:
                from shapely.geometry import Point
                point = Point(lon, lat)  # GeoJSON uses (lon, lat) order
                if not buffered_polygon.covers(point):
                    # Skip locations outside the buffered polygon
                    continue

            # Add small random offset within the pixel (±0.01° ≈ ±1km for visual variety)
            # Keep within bounds
            lat_offset = self.random.uniform(-0.01, 0.01)
            lon_offset = self.random.uniform(-0.01, 0.01)

            final_lat = lat + lat_offset
            final_lon = lon + lon_offset

            # Clamp to bounds to ensure we don't go outside
            final_lat = max(lat_min, min(lat_max, final_lat))
            final_lon = max(lon_min, min(lon_max, final_lon))

            # Final validation after offset: ensure still inside polygon(s)
            if self.geojson:
                if not point_in_polygon(final_lat, final_lon, self.geojson):
                    # If offset pushed us outside, use original LUSA pixel center
                    final_lat = lat
                    final_lon = lon

            suitable_locs.append((
                round(final_lat, 4),
                round(final_lon, 4)
            ))

        # Check if we found any suitable locations
        if len(suitable_locs) == 0:
            raise ValueError(
                f"❌ No suitable locations found in the specified area!\n\n"
                f"Polygon bounds: lat=[{lat_min:.4f}, {lat_max:.4f}], lon=[{lon_min:.4f}, {lon_max:.4f}]\n"
                f"The drawn polygon may be too small or outside areas with crop suitability data.\n\n"
                f"Suggestions:\n"
                f"  1. Draw a larger polygon to cover more area\n"
                f"  2. Ensure the polygon overlaps with agricultural land\n"
                f"  3. Check that the polygon is within Thessaloniki region (lat: 40.4-40.9, lon: 22.5-22.9)"
            )

        # Shuffle and return requested number
        self.random.shuffle(suitable_locs)
        return suitable_locs[:n_locations] if len(suitable_locs) >= n_locations else suitable_locs

    def _validate_user_locations(self, farmer_locations, geojson=None):
        """
        Validate and snap user-specified farmer locations to LUSA grid.

        Strategy:
        1. Validate coordinates are within bounds (polygon or Thessaloniki)
        2. Snap to nearest LUSA pixel (data alignment)
        3. Add small random offset (±0.01°) for visual variety
        4. Ensure snap distance is reasonable (<0.1°)

        Args:
            farmer_locations: List of {"lat": float, "lon": float, "crop": str}
            geojson: Optional GeoJSON for polygon validation

        Returns:
            List of (lat, lon) tuples - SNAPPED to LUSA grid with offsets
        """
        from backend.data.loaders.spatial_filter import point_in_polygon, get_polygon_bounds
        import sys

        # Terminal logging
        sys.stderr.write(f"\n{'='*80}\n")
        sys.stderr.write(f"📍 VALIDATING & SNAPPING USER COORDINATES TO LUSA GRID\n")
        sys.stderr.write(f"{'='*80}\n")
        sys.stderr.flush()

        # Determine validation bounds based on polygon availability
        if geojson:
            # User drew polygon - use polygon bounds for validation
            polygon_bounds = get_polygon_bounds(geojson)
            lat_min, lat_max = polygon_bounds['lat_min'], polygon_bounds['lat_max']
            lon_min, lon_max = polygon_bounds['lon_min'], polygon_bounds['lon_max']
            bounds_desc = f"drawn polygon [{lat_min:.2f}, {lat_max:.2f}]°N, [{lon_min:.2f}, {lon_max:.2f}]°E"
            use_polygon = True
        else:
            # No polygon - use full data bounds
            lat_min, lat_max = self.lat_bounds
            lon_min, lon_max = self.lon_bounds
            bounds_desc = f"Thessaloniki data bounds [{lat_min:.1f}, {lat_max:.1f}]°N, [{lon_min:.1f}, {lon_max:.1f}]°E"
            use_polygon = False

        sys.stderr.write(f"Validation bounds: {bounds_desc}\n")
        sys.stderr.flush()

        errors = []
        validated_locs = []

        # Import centralized epsilon configuration
        from backend.config.validation_config import get_coordinate_epsilon
        epsilon = get_coordinate_epsilon()

        # Max distance for snapping to LUSA pixel (0.1° ≈ 11km - one LUSA pixel spacing)
        MAX_SNAP_DISTANCE = 0.1

        # Get first crop's LUSA data for snapping
        first_crop = self.crops[0]
        lusa_data = self.crop_data[first_crop]

        sys.stderr.write(f"\n📍 Processing {len(farmer_locations)} user-specified locations:\n")
        sys.stderr.write(f"{'-'*80}\n")
        sys.stderr.flush()

        for i, loc in enumerate(farmer_locations, 1):
            user_lat, user_lon, crop = loc['lat'], loc['lon'], loc['crop']
            location_errors = []

            sys.stderr.write(f"\nLocation {i}: User requested ({user_lat}, {user_lon}) for {crop}\n")
            sys.stderr.flush()

            # Check latitude bounds (with epsilon tolerance for boundary points)
            if not (lat_min - epsilon <= user_lat <= lat_max + epsilon):
                location_errors.append(f"latitude {user_lat}° outside range [{lat_min:.4f}°, {lat_max:.4f}°]")

            # Check longitude bounds (with epsilon tolerance for boundary points)
            if not (lon_min - epsilon <= user_lon <= lon_max + epsilon):
                location_errors.append(f"longitude {user_lon}° outside range [{lon_min:.4f}°, {lon_max:.4f}°]")

            # Check crop name
            if crop.upper() not in self.crops:
                location_errors.append(f"invalid crop '{crop}' (valid: {', '.join(self.crops)})")

            # If basic validation failed, skip snapping
            if location_errors:
                errors.append(f"Location {i}: {'; '.join(location_errors)}")
                sys.stderr.write(f"  ❌ Validation failed: {'; '.join(location_errors)}\n")
                sys.stderr.flush()
                continue

            # ========== SNAP TO NEAREST LUSA PIXEL ==========
            # Find nearest LUSA pixel
            lusa_lat_nearest = float(lusa_data.lat.sel(lat=user_lat, method='nearest').values)
            lusa_lon_nearest = float(lusa_data.lon.sel(lon=user_lon, method='nearest').values)

            # Calculate snap distance
            snap_distance = ((lusa_lat_nearest - user_lat)**2 + (lusa_lon_nearest - user_lon)**2)**0.5

            # Validate snap distance
            if snap_distance > MAX_SNAP_DISTANCE:
                location_errors.append(
                    f"too far from LUSA grid - nearest pixel at ({lusa_lat_nearest}, {lusa_lon_nearest}) "
                    f"is {snap_distance:.4f}° away (max: {MAX_SNAP_DISTANCE}°)"
                )
                errors.append(f"Location {i}: {'; '.join(location_errors)}")
                sys.stderr.write(f"  ❌ Snap distance too large: {snap_distance:.4f}° > {MAX_SNAP_DISTANCE}°\n")
                sys.stderr.flush()
                continue

            # Add small random offset for visual variety (±0.001° ≈ ±110m)
            offset_lat = self.random.uniform(-0.001, 0.001)
            offset_lon = self.random.uniform(-0.001, 0.001)

            final_lat = lusa_lat_nearest + offset_lat
            final_lon = lusa_lon_nearest + offset_lon

            # Clamp to bounds to ensure we don't go outside
            final_lat = max(lat_min, min(lat_max, final_lat))
            final_lon = max(lon_min, min(lon_max, final_lon))

            # Round to 4 decimal places
            final_lat = round(final_lat, 4)
            final_lon = round(final_lon, 4)

            # Add to validated list
            validated_locs.append((final_lat, final_lon))

            # Terminal logging
            sys.stderr.write(f"  ✅ {crop.upper():<6} → Snapped to LUSA grid:\n")
            sys.stderr.write(f"     User requested:  ({user_lat:.4f}, {user_lon:.4f})\n")
            sys.stderr.write(f"     LUSA pixel:      ({lusa_lat_nearest:.4f}, {lusa_lon_nearest:.4f})\n")
            sys.stderr.write(f"     Final location:  ({final_lat:.4f}, {final_lon:.4f}) [with ±0.001° offset]\n")
            sys.stderr.write(f"     Snap distance:   {snap_distance:.6f}°\n")
            sys.stderr.flush()

        # Terminal summary
        sys.stderr.write(f"\n{'-'*80}\n")
        sys.stderr.write(f"📊 SUMMARY:\n")
        sys.stderr.write(f"   Total requested: {len(farmer_locations)}\n")
        sys.stderr.write(f"   Successfully validated & snapped: {len(validated_locs)}\n")
        sys.stderr.write(f"   Errors: {len(errors)}\n")
        sys.stderr.write(f"{'='*80}\n\n")
        sys.stderr.flush()

        # Raise error with ALL violations (single-line format for frontend)
        if errors:
            error_msg = f"❌ COORDINATE VALIDATION FAILED! {' | '.join(errors)}"
            if use_polygon:
                error_msg += " | ⚠️ Coordinates must be inside your drawn polygon!"
            raise ValueError(error_msg)

        return validated_locs

    def _capture_initial_characteristics(self):
        """Capture initial agent characteristics BEFORE simulation starts.

        This captures the varied initial state (e.g., market prices €80-120)
        AFTER agents are created but BEFORE any simulation steps run.
        """
        self.initial_characteristics = {}

        # Capture market initial states (VARIED prices €80-120)
        if hasattr(self, 'market_agents') and self.market_agents:
            self.initial_characteristics['markets'] = []
            for market in self.market_agents:
                self.initial_characteristics['markets'].append({
                    'name': market.market_name,
                    'crops': market.crops.copy(),
                    'prices': market.crop_prices.copy(),  # Captures varied €80-120
                    'demand': market.demand.copy()
                })

        # Capture collective initial states
        if hasattr(self, 'collective_agents') and self.collective_agents:
            self.initial_characteristics['collectives'] = []
            for collective in self.collective_agents:
                self.initial_characteristics['collectives'].append({
                    'name': collective.region_name,
                    'members': len(collective.members),
                    'wealth': collective.collective_wealth,
                    'social_norms': collective.social_norms.copy() if collective.social_norms else {},
                    'knowledge_pool': len(collective.knowledge_pool)
                })

        # Capture policymaker initial states
        if hasattr(self, 'policy_agents') and self.policy_agents:
            self.initial_characteristics['policymakers'] = []
            for policymaker in self.policy_agents:
                self.initial_characteristics['policymakers'].append({
                    'name': policymaker.policy_name,
                    'goals': policymaker.policy_goals.copy(),
                    'subsidy_rates': policymaker.subsidy_rates.copy() if policymaker.subsidy_rates else {},
                    'price_floors': policymaker.price_floors.copy() if policymaker.price_floors else {}
                })

    def _initialize_multi_level_agents(self,
                                        farmer_agents,
                                        n_collectives,
                                        n_markets,
                                        n_policies):
        """Initialize multi-level ABM agents.

        Args:
            farmer_agents: List of created FarmerAgent instances
            n_collectives: Number of collectives to create
            n_markets: Number of markets to create
            n_policies: Number of policy agents to create
        """
        # 1. Create Community Level (Collectives)
        print(f"Creating {n_collectives} collective(s)...")
        farmers_per_collective = len(farmer_agents) // n_collectives
        for i in range(n_collectives):
            start_idx = i * farmers_per_collective
            if i == n_collectives - 1:
                # Last collective gets remaining members
                member_farmers = farmer_agents[start_idx:]
            else:
                end_idx = start_idx + farmers_per_collective
                member_farmers = farmer_agents[start_idx:end_idx]

            collective = CollectiveAgent(
                model=self,
                region_name=f"Region_{i+1}",
                member_farmers=member_farmers
            )

            # Add heterogeneous initial characteristics (like CCA)
            import random
            rng_collectives = random.Random(42 + i)  # Deterministic but varied per collective

            # Collective wealth varies based on member count and average land size
            total_farmer_wealth = sum(
                getattr(f, 'land_hectares', 10.0) * rng_collectives.uniform(1000, 5000)
                for f in member_farmers
            )
            collective.collective_wealth = total_farmer_wealth * rng_collectives.uniform(0.05, 0.15)  # 5-15% pooled

            # Social norms vary by collective (risk aversion: 0.3-0.9)
            collective.social_norms = {
                'risk_aversion': rng_collectives.uniform(0.3, 0.9),
                'innovation_openness': rng_collectives.uniform(0.2, 0.8)
            }

            # Knowledge pool starts small but varies (0-3 initial practices)
            initial_knowledge = rng_collectives.randint(0, 3)
            collective.knowledge_pool = set([f"practice_{j}" for j in range(initial_knowledge)])

            self.collective_agents.append(collective)
            print(f"  - Collective {i+1}: {len(member_farmers)} members (land parcels)")

        # 2. Create Market Level
        print(f"Creating {n_markets} market(s)...")
        import random
        rng_markets = random.Random(42 + n_markets)  # Deterministic but varied

        for i in range(n_markets):
            # Create varied initial prices for each market (€80-120 range like CCA)
            initial_prices = {crop: rng_markets.uniform(80.0, 120.0) for crop in self.crops}
            # Create varied initial demand for each market (500-1000 tons like CCA)
            initial_demand = {crop: rng_markets.uniform(500.0, 1000.0) for crop in self.crops}

            market = CommodityMarketAgent(
                model=self,
                market_name=f"Market_{i+1}",
                crops=self.crops,
                initial_prices=initial_prices,
                initial_demand=initial_demand
            )
            self.market_agents.append(market)
            # Show initial prices for transparency
            price_str = ', '.join([f"{crop}: €{initial_prices[crop]:.0f}" for crop in self.crops])
            print(f"  - Market {i+1}: trading {', '.join(self.crops)} | Initial: {price_str}")

        # 3. Create Policy Level
        print(f"Creating {n_policies} policy agent(s)...")

        # Generate diverse policy profiles with controlled randomness
        # Use fixed seed for reproducibility but varied profiles
        import random
        rng = random.Random(42)  # Fixed seed for reproducible diversity

        goal_types = ['food_security', 'price_stability', 'sustainability']

        for i in range(n_policies):
            # Determine policy focus (rotate through 3 main types first, then randomize)
            if i < 3:
                # First 3 policies: one focused on each goal
                primary_goal = goal_types[i]
                goals = {goal: 0.9 if goal == primary_goal else rng.uniform(0.5, 0.7) for goal in goal_types}
                profile_name = f"{primary_goal.replace('_', ' ').title()} Focused"
            else:
                # Additional policies: varied priorities
                # Shuffle goals to create unique combinations
                shuffled_goals = goal_types.copy()
                rng.shuffle(shuffled_goals)

                # Assign decreasing priorities
                goals = {
                    shuffled_goals[0]: rng.uniform(0.8, 0.95),  # High priority
                    shuffled_goals[1]: rng.uniform(0.6, 0.75),  # Medium priority
                    shuffled_goals[2]: rng.uniform(0.45, 0.6)   # Lower priority
                }
                profile_name = f"Mixed Priority {i-2}"

            policy = PolicymakerAgent(
                model=self,
                policy_name=f"Policy_{i+1}_{profile_name.replace(' ', '_')}",
                policy_goals=goals
            )
            # Initialize default policies
            policy.initialize_default_policies(self.crops)
            self.policy_agents.append(policy)

            # Format goals for display (rounded to 2 decimals)
            goals_display = {k: round(v, 2) for k, v in goals.items()}
            print(f"  - Policy {i+1} ({profile_name}): goals={goals_display}")

    def _initialize_data_collector(self):
        """Initialize Mesa DataCollector for multi-level metrics."""
        model_reporters = {
            # Individual level metrics
            "Year": lambda m: m.current_year,
        }

        # Add crop count reporters
        for crop in self.crops:
            model_reporters[f"{crop}_count"] = lambda m, c=crop: sum(
                1 for a in m.agents if hasattr(a, 'current_crop') and a.current_crop == c
            )

        # Multi-level metrics
        if self.enable_multi_level:
            # Market level metrics
            for crop in self.crops:
                model_reporters[f"{crop}_price"] = lambda m, c=crop: (
                    m.market_agents[0].crop_prices.get(c, 0) if m.market_agents else 0
                )
                model_reporters[f"{crop}_supply"] = lambda m, c=crop: (
                    m.market_agents[0].supply.get(c, 0) if m.market_agents else 0
                )

            # Policy level metrics
            model_reporters["food_security_effectiveness"] = lambda m: (
                m.policy_agents[0].policy_effectiveness.get('food_security', 0)
                if m.policy_agents else 0
            )
            model_reporters["price_stability_effectiveness"] = lambda m: (
                m.policy_agents[0].policy_effectiveness.get('price_stability', 0)
                if m.policy_agents else 0
            )

        # Agent-level reporters
        agent_reporters = {
            "crop": lambda a: getattr(a, 'current_crop', None),
            "lat": lambda a: getattr(a, 'lat', None),
            "lon": lambda a: getattr(a, 'lon', None),
        }

        self.datacollector = DataCollector(
            model_reporters=model_reporters,
            agent_reporters=agent_reporters
        )

    def step(self):
        """Advance model by one year."""
        if self.enable_multi_level and self.orchestrator:
            # Use multi-level orchestrator
            self.orchestrator.step_all_levels()
        else:
            # Simple single-level ABM (only FarmerAgents)
            self.agents.shuffle_do("step")

        # Step PV agents (always, independent of multi-level)
        for pv in self.pv_agents:
            pv.step()

        # Step parcel agents (new mode)
        for parcel in self.parcel_agents:
            parcel.step()

        # Count land use decisions
        from use_cases.mlu.agents.farmer_agent import FarmerAgent
        farmer_agents = [a for a in self.agents if isinstance(a, FarmerAgent)]

        # Combine farmers and parcels for counting
        all_agents = list(farmer_agents) + list(self.parcel_agents)

        # Count crops
        crop_counts = {crop: sum(1 for a in all_agents if a.current_crop == crop) for crop in self.crops}

        # Count solar PV parcels
        solar_count = sum(1 for a in self.parcel_agents if getattr(a, 'land_use', None) == 'solar_pv')

        # Build output string
        counts_parts = [f"{count} {crop}" for crop, count in crop_counts.items()]
        if solar_count > 0:
            counts_parts.append(f"{solar_count} SOLAR")
        counts_str = ", ".join(counts_parts)

        # Collect data
        self.datacollector.collect(self)

        # Add multi-level info if enabled
        if self.enable_multi_level:
            # Show market prices
            if self.market_agents:
                market = self.market_agents[0]
                prices_str = ", ".join([f"{crop}=${price:.1f}" for crop, price in market.crop_prices.items()])
                print(f"Year {self.current_year}: {counts_str} | Prices: {prices_str}")
            else:
                print(f"Year {self.current_year}: {counts_str}")
        else:
            print(f"Year {self.current_year}: {counts_str}")

        self.current_year += 1

    def get_model_data(self):
        """Get collected model-level data as pandas DataFrame.

        Returns:
            DataFrame with model metrics over time
        """
        return self.datacollector.get_model_vars_dataframe()

    def get_agent_data(self):
        """Get collected agent-level data as pandas DataFrame.

        Returns:
            DataFrame with agent attributes over time
        """
        return self.datacollector.get_agent_vars_dataframe()

    def _build_spatial_index(self):
        """Build spatial index for fast neighbor queries.

        Uses a simple grid-based spatial index for efficient neighbor lookup.
        Each grid cell is ~5km (0.05 degrees) and stores all spatial agents.
        """
        from use_cases.mlu.agents.farmer_agent import FarmerAgent
        from use_cases.mlu.agents.land_parcel_agent import LandParcelAgent

        self.spatial_index = {}  # Dict[(grid_i, grid_j)] -> list of agents

        # Index all agents with lat/lon attributes
        spatial_agents = []

        # Collect FarmerAgents (legacy mode)
        farmer_agents = [a for a in self.agents if isinstance(a, FarmerAgent)]
        spatial_agents.extend(farmer_agents)

        # Collect LandParcelAgents (new mode)
        spatial_agents.extend(self.parcel_agents)

        # Collect PV agents (legacy mode)
        spatial_agents.extend(self.pv_agents)

        # Build index
        for agent in spatial_agents:
            grid_i = int(round(agent.lat / 0.05))
            grid_j = int(round(agent.lon / 0.05))

            grid_cell = (grid_i, grid_j)
            if grid_cell not in self.spatial_index:
                self.spatial_index[grid_cell] = []
            self.spatial_index[grid_cell].append(agent)

        # Report
        n_parcels = len(self.parcel_agents)
        n_farmers = len(farmer_agents)
        n_pv = len(self.pv_agents)

        if n_parcels > 0:
            print(f"Built spatial index: {len(self.spatial_index)} grid cells, {n_parcels} land parcels")
        else:
            print(f"Built spatial index: {len(self.spatial_index)} grid cells, {n_farmers} farmers, {n_pv} PV installations")

    def get_spatial_neighbors(self, farmer, radius_km=10.0):
        """Get neighboring farmers within a given radius.

        Args:
            farmer: FarmerAgent to find neighbors for
            radius_km: Search radius in kilometers (default 10km)

        Returns:
            List of FarmerAgent instances within radius (excluding self)
        """
        import math

        # Convert km to degrees (approximate: 1° ≈ 111km at this latitude)
        radius_deg = radius_km / 111.0

        # Haversine distance formula for accuracy
        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate distance in km between two lat/lon points."""
            R = 6371  # Earth radius in km

            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)

            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                 math.sin(dlon / 2) ** 2)

            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = R * c

            return distance

        neighbors = []

        # Check grid cells within bounding box using integer grid indices
        farmer_grid_i = int(round(farmer.lat / 0.05))
        farmer_grid_j = int(round(farmer.lon / 0.05))

        radius_cells = int(math.ceil(radius_deg / 0.05))

        # Search all grid cells within radius_cells
        for di in range(-radius_cells, radius_cells + 1):
            for dj in range(-radius_cells, radius_cells + 1):
                grid_cell = (farmer_grid_i + di, farmer_grid_j + dj)

                if grid_cell in self.spatial_index:
                    for candidate in self.spatial_index[grid_cell]:
                        if candidate.unique_id == farmer.unique_id:
                            continue  # Skip self

                        dist = haversine_distance(
                            farmer.lat, farmer.lon,
                            candidate.lat, candidate.lon
                        )

                        if dist <= radius_km:
                            neighbors.append(candidate)

        return neighbors
