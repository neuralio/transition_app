#!/usr/bin/env python3
"""
Irrigation Tool - Handles irrigation simulation queries (IRR-US-01 through IRR-US-17)

Supports:
- IRR-US-01: Automated Bare Soil Classification (NDVI-based)
- Future: IRR-US-03/04 (Crop Assignment), IRR-US-05 (Rice Flood Detection)
"""
import subprocess
import json
import tempfile
import sys
from pathlib import Path
from datetime import datetime
from dateutil import parser as date_parser
from atomic_agents import BaseTool, BaseToolConfig, BaseIOSchema
from pydantic import Field


class IrrigationQueryInput(BaseIOSchema):
    """Input for irrigation queries"""
    query: str = Field(..., description="User's natural language query about irrigation")
    user_story: str | None = Field(
        None,
        description="User story ID (e.g., IRR-US-01) - if provided by LLM"
    )
    start_date: str | None = Field(
        None,
        description="Start date for EO data (YYYY-MM-DD). REQUIRED for irrigation queries."
    )
    end_date: str | None = Field(
        None,
        description="End date for EO data (YYYY-MM-DD). REQUIRED for irrigation queries."
    )
    parcels: int | None = Field(
        None,
        description="Number of land parcels to analyze (default: 20, ignored if parcel_locations or use_polygons provided)"
    )
    parcel_locations: str | None = Field(
        None,
        description="JSON string with parcel coordinates: '[{\"lat\":40.5,\"lon\":22.7}]' - extracted from user query"
    )
    use_polygons: bool = Field(
        False,
        description="If True, analyze full polygon geometries (all pixels) instead of point locations"
    )
    collectives: int | None = Field(
        None,
        description="Number of water cooperatives (Community Level ABM)"
    )
    geojson_file: str | None = Field(
        None,
        description="Path to GeoJSON file for polygon-based spatial filtering (REQUIRED unless parcel_locations provided)"
    )
    enable_phenology: bool = Field(
        False,
        description="Enable temporal phenology analysis (time-series NDVI/NDWI to distinguish harvested crops from fallow fields)"
    )
    temporal_window_days: int | None = Field(
        None,
        description="Temporal window size in days for phenology analysis (default: 10)"
    )


class IrrigationQueryOutput(BaseIOSchema):
    """Output from irrigation simulation"""
    user_story: str = Field(..., description="Identified user story (e.g., IRR-US-01)")
    result: str = Field(..., description="Simulation results")
    output_files: list[str] = Field(default=[], description="Generated files")
    status: str = Field(..., description="success or error")


class IrrigationToolConfig(BaseToolConfig):
    """Irrigation Tool configuration"""
    irrigation_path: str = Field(
        default="/app/use_cases/irrigation",
        description="Path to irrigation directory"
    )
    geojson_state: dict | None = Field(
        default=None,
        description="Current GeoJSON polygon state from user"
    )


class IrrigationTool(BaseTool[IrrigationQueryInput, IrrigationQueryOutput]):
    """
    Executes irrigation simulation queries with automatic EO data download.

    Handles user stories:
    - IRR-US-01: Automated Bare Soil Classification (NDVI thresholding)
    - Future: IRR-US-03/04 (Dynamic Crop Assignment)
    - Future: IRR-US-05 (Rice Flood Detection - NDWI)
    - Future: IRR-US-09-11 (Multi-Level ABM)
    """

    input_schema = IrrigationQueryInput
    output_schema = IrrigationQueryOutput

    def __init__(self, config: IrrigationToolConfig = IrrigationToolConfig()):
        super().__init__(config)
        self.irrigation_path = Path(config.irrigation_path)
        self.geojson_state = config.geojson_state

    def run(self, params: IrrigationQueryInput) -> IrrigationQueryOutput:
        """Execute irrigation simulation"""
        # Identify user story
        if params.user_story:
            user_story = params.user_story.upper()
            print(f"📌 Using LLM-identified user story: {user_story}", file=sys.stderr)
        else:
            user_story = self._identify_user_story(params.query)
            print(f"📌 Using keyword-matched user story: {user_story}", file=sys.stderr)

        # Validate date range (CRITICAL for irrigation!)
        date_validation = self._validate_dates(params)
        if date_validation["status"] == "error":
            return IrrigationQueryOutput(
                user_story=user_story,
                result=date_validation["message"],
                output_files=[],
                status="error"
            )

        params.start_date = date_validation["start_date"]
        params.end_date = date_validation["end_date"]

        # Execute appropriate user story
        try:
            if user_story == "IRR-US-01":
                return self._run_irr_us_01(params)
            else:
                return IrrigationQueryOutput(
                    user_story=user_story,
                    result=f"❌ User story {user_story} not yet implemented.\n\nAvailable: IRR-US-01 (Bare Soil Classification)",
                    output_files=[],
                    status="error"
                )
        except Exception as e:
            return IrrigationQueryOutput(
                user_story=user_story,
                result=f"❌ Error: {str(e)}",
                output_files=[],
                status="error"
            )

    def _identify_user_story(self, query: str) -> str:
        """Map natural language query to user story"""
        q = query.lower()

        # IRR-US-01: Bare soil classification (with or without phenology)
        if any(keyword in q for keyword in [
            "bare soil", "classify", "classification",
            "ndvi", "fallow", "vegetated", "bare parcels",
            "phenology", "temporal", "time-series", "harvested"
        ]):
            return "IRR-US-01"

        # IRR-US-05: Rice flood detection (future)
        if any(keyword in q for keyword in ["rice", "flood", "ndwi", "paddy"]):
            return "IRR-US-05"

        # IRR-US-03/04: Crop assignment (future)
        if any(keyword in q for keyword in ["crop assignment", "rotation", "assign crop"]):
            return "IRR-US-03"

        # Default to bare soil classification
        return "IRR-US-01"

    def _detect_phenology_mode(self, query: str) -> bool:
        """Detect if user wants temporal phenology analysis"""
        q = query.lower()
        phenology_keywords = [
            "phenology", "temporal", "time-series", "time series",
            "harvested", "harvest", "season", "evolution",
            "pattern", "throughout"
        ]
        return any(keyword in q for keyword in phenology_keywords)

    def _validate_dates(self, params: IrrigationQueryInput) -> dict:
        """
        Validate and parse date range from user input.

        Critical for irrigation: dates are REQUIRED for EO data download.
        """
        # Check if dates provided
        if not params.start_date and not params.end_date:
            # Try to extract from natural language query
            dates = self._extract_dates_from_query(params.query)
            if dates["start_date"] and dates["end_date"]:
                return {
                    "status": "success",
                    "start_date": dates["start_date"],
                    "end_date": dates["end_date"]
                }
            else:
                return {
                    "status": "error",
                    "message": "❌ Date range required for irrigation queries.\n\n"
                              "Please specify dates (e.g., 'from July 15 to August 31, 2023' or '2023-07-15 to 2023-08-31')"
                }

        # Parse provided dates
        try:
            if params.start_date:
                start = self._parse_date(params.start_date)
            else:
                return {"status": "error", "message": "Start date missing"}

            if params.end_date:
                end = self._parse_date(params.end_date)
            else:
                return {"status": "error", "message": "End date missing"}

            # Validate order
            if start > end:
                return {
                    "status": "error",
                    "message": f"Start date ({start}) must be before end date ({end})"
                }

            return {
                "status": "success",
                "start_date": start,
                "end_date": end
            }

        except Exception as e:
            return {"status": "error", "message": f"Invalid date format: {e}"}

    def _parse_date(self, date_str: str) -> str:
        """Parse date string to YYYY-MM-DD format"""
        try:
            parsed = date_parser.parse(date_str)
            return parsed.strftime("%Y-%m-%d")
        except Exception as e:
            raise ValueError(f"Could not parse date '{date_str}': {e}")

    def _extract_dates_from_query(self, query: str) -> dict:
        """
        Extract date range from natural language query.

        Examples:
        - "July 15 to August 31, 2023"
        - "from 2023-07-01 to 2023-08-31"
        - "between 7/15/23 and 8/31/23"
        """
        import re

        # Pattern 1: "from DATE to DATE"
        pattern1 = r"from\s+([^\s]+(?:\s+\d{1,2},?\s+\d{4})?)\s+to\s+([^\s]+(?:\s+\d{1,2},?\s+\d{4})?)"
        match1 = re.search(pattern1, query, re.IGNORECASE)
        if match1:
            try:
                start = self._parse_date(match1.group(1))
                end = self._parse_date(match1.group(2))
                return {"start_date": start, "end_date": end}
            except:
                pass

        # Pattern 2: "DATE to DATE" (without "from")
        pattern2 = r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})\s+to\s+(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})"
        match2 = re.search(pattern2, query, re.IGNORECASE)
        if match2:
            try:
                start = self._parse_date(match2.group(1))
                end = self._parse_date(match2.group(2))
                return {"start_date": start, "end_date": end}
            except:
                pass

        # Pattern 3: "in MONTH YEAR" → entire month
        pattern3 = r"in\s+(\w+)\s+(\d{4})"
        match3 = re.search(pattern3, query, re.IGNORECASE)
        if match3:
            try:
                month_year = f"{match3.group(1)} {match3.group(2)}"
                month_start = date_parser.parse(f"{match3.group(1)} 1, {match3.group(2)}")

                # Get last day of month
                if month_start.month == 12:
                    month_end = month_start.replace(day=31)
                else:
                    next_month = month_start.replace(month=month_start.month + 1, day=1)
                    month_end = next_month.replace(day=1) - datetime.timedelta(days=1)

                return {
                    "start_date": month_start.strftime("%Y-%m-%d"),
                    "end_date": month_end.strftime("%Y-%m-%d")
                }
            except:
                pass

        return {"start_date": None, "end_date": None}

    def _extract_coordinates_from_query(self, query: str) -> list[dict]:
        """
        Extract GPS coordinates from natural language query.

        Supports formats:
        - "at (40.5, 22.7)"
        - "at (40.5, 22.7) and (40.6, 22.8)"
        - "coordinates: 40.5, 22.7"
        - "lat 40.5 lon 22.7"

        Returns:
            List of dicts: [{"lat": 40.5, "lon": 22.7}, ...]
        """
        import re

        coords = []

        # Pattern 1: (lat, lon) format
        pattern1 = r'\((\d+\.?\d*),\s*(\d+\.?\d*)\)'
        matches1 = re.findall(pattern1, query)
        for match in matches1:
            coords.append({
                "lat": float(match[0]),
                "lon": float(match[1])
            })

        # Pattern 2: "lat X lon Y" format
        if not coords:
            pattern2 = r'lat[:\s]+(\d+\.?\d*)[,\s]+lon[:\s]+(\d+\.?\d*)'
            matches2 = re.findall(pattern2, query, re.IGNORECASE)
            for match in matches2:
                coords.append({
                    "lat": float(match[0]),
                    "lon": float(match[1])
                })

        return coords

    def _run_irr_us_01(self, params: IrrigationQueryInput) -> IrrigationQueryOutput:
        """
        IRR-US-01: Automated Bare Soil Classification

        Uses NDVI thresholding (< 0.25) to classify parcels.
        Optionally enables temporal phenology analysis for enhanced pattern detection.
        """
        # Track defaults used
        defaults_used = []

        # Auto-detect phenology mode if not explicitly set
        if not params.enable_phenology and self._detect_phenology_mode(params.query):
            params.enable_phenology = True
            print(f"🔍 Detected phenology keywords - enabling temporal analysis mode", file=sys.stderr)

        # Extract coordinates from query if not provided
        if not params.parcel_locations:
            coords = self._extract_coordinates_from_query(params.query)
            if coords:
                # Validate coordinates against Thessaloniki data bounds
                # EXACTLY like MLU/CCA/GCP do
                LAT_MIN, LAT_MAX = 40.4, 40.9
                LON_MIN, LON_MAX = 22.5, 22.9

                # Validate each coordinate - EXACTLY like MLU format
                location_errors = []
                for i, coord in enumerate(coords, 1):
                    lat, lon = coord['lat'], coord['lon']
                    coord_errors = []

                    if not (LAT_MIN <= lat <= LAT_MAX):
                        coord_errors.append(f"latitude {lat}° outside range [{LAT_MIN:.4f}°, {LAT_MAX:.4f}°]")
                    if not (LON_MIN <= lon <= LON_MAX):
                        coord_errors.append(f"longitude {lon}° outside range [{LON_MIN:.4f}°, {LON_MAX:.4f}°]")

                    if coord_errors:
                        location_errors.append(f"Location {i}: {'; '.join(coord_errors)}")

                if location_errors:
                    # EXACTLY like MLU: single line with " | " separators
                    # Different message based on whether there's a polygon or not
                    if self.geojson_state:
                        warning = "⚠️ Coordinates must be inside your drawn polygon!"
                    else:
                        warning = "⚠️ Coordinates must be within valid data bounds!"
                    error_msg = f"❌ COORDINATE VALIDATION FAILED! {' | '.join(location_errors)} | {warning}"
                    # Print to terminal like MLU does
                    print("\n" + error_msg, file=sys.stderr)
                    return IrrigationQueryOutput(
                        user_story="IRR-US-01",
                        result=error_msg,
                        output_files=[],
                        status="error"
                    )

                params.parcel_locations = json.dumps(coords)
                print(f"📍 Extracted {len(coords)} coordinate(s) from query", file=sys.stderr)
                print(f"✅ All coordinates within valid bounds: lat [{LAT_MIN}, {LAT_MAX}], lon [{LON_MIN}, {LON_MAX}]", file=sys.stderr)

        # Set defaults and track them
        if params.parcels is None:
            params.parcels = 20
            if not params.parcel_locations and not params.use_polygons:
                # Only mention parcels default if using random sampling mode
                defaults_used.append("parcels=20")

        if params.collectives is None:
            params.collectives = 0
            # Don't mention this default unless user is doing multi-level ABM

        # Track mode if not explicitly stated
        if params.parcel_locations:
            mode_info = f"point coordinates mode ({json.loads(params.parcel_locations).__len__()} location(s))"
        elif params.use_polygons:
            mode_info = "full polygon analysis mode"
        else:
            mode_info = "random sampling mode"

        # Prepare GeoJSON file or validate coordinates
        temp_geojson = None
        if params.parcel_locations:
            # User provided explicit coordinates - no polygon needed
            print(f"📍 Using user-specified coordinates (no polygon required)", file=sys.stderr)
        elif not self.geojson_state:
            return IrrigationQueryOutput(
                user_story="IRR-US-01",
                result="❌ No polygon drawn and no coordinates provided. Please either:\n" +
                       "1. Draw a region on the map, OR\n" +
                       "2. Specify coordinates in your query (e.g., 'at (40.5, 22.7)')",
                output_files=[],
                status="error"
            )
        else:
            # Save GeoJSON to temp file
            temp_geojson = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.geojson',
                delete=False,
                dir='/tmp'
            )
            json.dump(self.geojson_state, temp_geojson)
            temp_geojson.close()

        # Build CLI command
        cmd = [
            "python",
            str(self.irrigation_path / "run_irrigation.py"),
            "--query", "irr_01",
            "--start-date", params.start_date,
            "--end-date", params.end_date
        ]

        # Add mode-specific arguments
        if params.parcel_locations:
            # Point coordinates mode
            cmd.extend(["--parcel-locations", params.parcel_locations])
        elif params.use_polygons:
            # Full polygon analysis mode
            cmd.extend(["--geojson-file", temp_geojson.name, "--use-polygons"])
        else:
            # Random sampling mode (default)
            cmd.extend(["--geojson-file", temp_geojson.name, "--parcels", str(params.parcels)])

        # Add phenology flags if enabled
        if params.enable_phenology:
            cmd.append("--enable-phenology")
            if params.temporal_window_days:
                cmd.extend(["--temporal-window-days", str(params.temporal_window_days)])
            else:
                defaults_used.append("temporal_window_days=10")

        # Execute (capture for parsing but also print to terminal)
        print(f"🚀 Executing: {' '.join(cmd)}", file=sys.stderr)
        print("=" * 80, file=sys.stderr)

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,  # Capture for parsing
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            timeout=600
        )

        # Print output to terminal (filter out spatial filtering errors)
        output_text = result.stdout
        # Filter out "Failed to apply spatial filtering" lines (noise from data loaders)
        filtered_lines = [
            line for line in output_text.split('\n')
            if "Failed to apply spatial filtering" not in line
        ]
        filtered_output = '\n'.join(filtered_lines)
        print(filtered_output, file=sys.stderr)
        print("=" * 80, file=sys.stderr)

        # Parse output
        if result.returncode == 0:

            # Parse results
            bare_count = self._extract_metric(output_text, "Bare soil parcels:")
            veg_count = self._extract_metric(output_text, "Vegetated parcels:")
            total = self._extract_metric(output_text, "Total parcels analyzed:")
            mean_ndvi_bare = self._extract_metric(output_text, "Mean NDVI (bare):")
            mean_ndvi_veg = self._extract_metric(output_text, "Mean NDVI (vegetated):")

            # Find output files
            output_files = []
            for line in output_text.split('\n'):
                if "classification_map" in line or "classification_report" in line:
                    # Extract file path
                    if ":" in line:
                        path = line.split(":")[-1].strip()
                        if Path(path).exists():
                            output_files.append(path)

            # Format response
            response = f"✅ **Bare Soil Classification Complete**\n\n"
            response += f"📊 **Results** ({params.start_date} to {params.end_date}):\n"
            response += f"- Analysis mode: {mode_info}\n"
            response += f"- Total parcels analyzed: {total}\n"
            response += f"- Bare soil: {bare_count} ({100*int(bare_count)/int(total):.1f}%)\n"
            response += f"- Vegetated: {veg_count} ({100*int(veg_count)/int(total):.1f}%)\n"
            if mean_ndvi_bare != "N/A":
                response += f"- Mean NDVI (bare): {mean_ndvi_bare}\n"
            if mean_ndvi_veg != "N/A":
                response += f"- Mean NDVI (vegetated): {mean_ndvi_veg}\n"

            response += f"\n📁 **Output Files**:\n"
            for file in output_files:
                response += f"- {file}\n"

            response += f"\n💡 **Interpretation**:\n"
            if int(bare_count) > int(veg_count):
                response += f"Majority of parcels show bare soil (NDVI < 0.25), typical for "
                response += f"post-harvest or fallow periods in Mediterranean summer.\n"
            else:
                response += f"Majority of parcels are vegetated (NDVI ≥ 0.25), indicating "
                response += f"active crop growth.\n"

            # Add defaults notification EXACTLY like MLU/CCA/GCP (prepend to response)
            if defaults_used:
                defaults_msg = "ℹ️  Using default values: " + ", ".join(defaults_used)
                # Print to terminal like MLU/CCA/GCP do
                print(defaults_msg, file=sys.stderr)
                response = defaults_msg + "\n\n" + response

            return IrrigationQueryOutput(
                user_story="IRR-US-01",
                result=response,
                output_files=output_files,
                status="success"
            )
        else:
            # Error occurred - use stdout (contains formatted error from run_irrigation.py)
            # Don't wrap with "Simulation failed" - the error message is already formatted
            error_msg = result.stdout.strip()
            return IrrigationQueryOutput(
                user_story="IRR-US-01",
                result=error_msg,  # Use error as-is (already has ❌ prefix)
                output_files=[],
                status="error"
            )

    def _extract_metric(self, text: str, label: str) -> str:
        """Extract metric value from output text"""
        for line in text.split('\n'):
            if label in line:
                # Extract number after label
                parts = line.split(":")
                if len(parts) >= 2:
                    value = parts[-1].strip().split()[0]
                    return value
        return "N/A"
