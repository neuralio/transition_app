#!/usr/bin/env python3
"""
GCP Tool - Handles Green Credit Policy queries (GCP-03, GCP-07, GCP-16)
"""
import subprocess
import sys
from pathlib import Path
from atomic_agents import BaseTool, BaseToolConfig, BaseIOSchema
from pydantic import Field


# Input Schema
class GCPQueryInput(BaseIOSchema):
    """Input for GCP queries"""
    query: str = Field(..., description="User's natural language query about green credit policy")
    user_story: str | None = Field(None, description="""User story ID - choose based on query intent:
- GCP-03: PV adoption simulation (keywords: simulate, adoption, landowners, loans, financial institutions)
- GCP-07: Geographic map visualization (keywords: map, geographic, distribution, spatial, where, location)
- GCP-16: Policy feedback loops (keywords: feedback, track subsidy, policy effectiveness, subsidy effectiveness, monitor, policy adjustment, loan rate adjustment)

IMPORTANT: If query contains 'track subsidy', 'subsidy effectiveness', or 'policy effectiveness' → use GCP-16, NOT GCP-03!""")
    scenario: str | None = Field(None, description="Climate scenario: rcp26, rcp45, rcp85")
    policy: str | None = Field(None, description="Policy scenario: low_support, moderate_support, high_support")
    years: int | None = Field(None, description="Simulation years")
    landowners: int | None = Field(None, description="Number of landowner agents")
    # Multi-level ABM parameters (GCP uses 3-level: Individual → Market → Policy, NO collectives)
    financial_institutions: int | None = Field(None, description="Number of financial institutions (banks)")
    policymakers: int | None = Field(None, description="Number of policymaker agents")
    # Spatial filtering
    geojson_file: str | None = Field(None, description="Path to GeoJSON file for polygon-based spatial filtering")
    # User-specified landowner locations (NEW - 2025-10-21)
    farmer_locations: list[dict] | None = Field(None, description="""CRITICAL: Extract ALL GPS coordinates for PV/solar installations.

Examples:
- "PV at (40.5, 22.7)" → [{"lat": 40.5, "lon": 22.7, "crop": "PV"}]
- "PV at (40.65, 22.75), (40.6, 22.58)" → [{"lat": 40.65, "lon": 22.75, "crop": "PV"}, {"lat": 40.6, "lon": 22.58, "crop": "PV"}]
- "solar at (40.5, 22.7) and (40.6, 22.8)" → [{"lat": 40.5, "lon": 22.7, "crop": "PV"}, {"lat": 40.6, "lon": 22.8, "crop": "PV"}]

ALWAYS set crop="PV" for GCP (never wheat/maize).
Extract ALL coordinates - if multiple coords present, return multiple dicts.
If user specifies coordinates, do NOT use landowners field.""")


# Output Schema
class GCPQueryOutput(BaseIOSchema):
    """Output from GCP simulation"""
    user_story: str = Field(..., description="Identified user story (e.g., GCP-03)")
    result: str = Field(..., description="Simulation results")
    output_files: list[str] = Field(default=[], description="Generated files")
    status: str = Field(..., description="success or error")


# Tool Config
class GCPToolConfig(BaseToolConfig):
    """GCP Tool configuration"""
    gcp_path: str = Field(
        default="/app/use_cases/gcp",
        description="Path to GCP directory"
    )


# Tool Implementation
class GCPTool(BaseTool[GCPQueryInput, GCPQueryOutput]):
    """
    Executes Green Credit Policy (GCP) simulations.

    Handles user stories:
    - GCP-03: Simulate PV Adoption by Farmers and Landowners
    - GCP-07: View Geographic Distribution of PV Adoption
    - GCP-16: Monitor Feedback Loop Between Policy and Financial Institutions
    """

    input_schema = GCPQueryInput
    output_schema = GCPQueryOutput

    def __init__(self, config: GCPToolConfig = GCPToolConfig()):
        super().__init__(config)
        self.gcp_path = Path(config.gcp_path)

    def run(self, params: GCPQueryInput) -> GCPQueryOutput:
        """Execute GCP simulation"""
        # ALWAYS check keywords first for GCP-16 (policy feedback) - LLM often gets this wrong
        keyword_story = self._identify_user_story(params.query)

        # Use LLM-provided user story if available, but OVERRIDE with keywords for GCP-16
        if params.user_story:
            user_story = params.user_story
            print(f"📌 LLM identified: {user_story}", file=sys.stderr)

            # OVERRIDE: If keywords say GCP-16 and LLM said something else, trust keywords
            if keyword_story == "GCP-16" and user_story != "GCP-16":
                print(f"⚠️  OVERRIDE: Keyword match says GCP-16 (feedback loops) - using that instead!", file=sys.stderr)
                user_story = "GCP-16"
            elif keyword_story == "GCP-16" and user_story == "GCP-16":
                print(f"✅ LLM correctly identified GCP-16 (feedback loops)", file=sys.stderr)

            print(f"   Final user story: {user_story}", file=sys.stderr)
            print(f"   Query: {params.query}", file=sys.stderr)
        else:
            user_story = keyword_story
            print(f"📌 Using keyword-matched user story: {user_story}", file=sys.stderr)

        try:
            if user_story == "GCP-03":
                return self._run_gcp_03(params)
            elif user_story == "GCP-07":
                return self._run_gcp_07(params)
            elif user_story == "GCP-16":
                return self._run_gcp_16(params)
            else:
                return GCPQueryOutput(
                    user_story="UNKNOWN",
                    result=f"Could not identify user story from: {params.query}",
                    output_files=[],
                    status="error"
                )
        except Exception as e:
            return GCPQueryOutput(
                user_story=user_story,
                result=f"Error: {str(e)}",
                output_files=[],
                status="error"
            )

    def _extract_coordinates_regex(self, query: str) -> list[dict] | None:
        """
        Fallback coordinate extractor using regex.
        Extracts all (lat, lon) pairs from query.
        """
        import re

        # Pattern: (number, number) where numbers can be floats
        pattern = r'\((\d+\.?\d*),\s*(\d+\.?\d*)\)'
        matches = re.findall(pattern, query)

        if not matches:
            return None

        locations = []
        for lat_str, lon_str in matches:
            locations.append({
                'lat': float(lat_str),
                'lon': float(lon_str),
                'crop': 'PV'  # Always PV for GCP
            })

        return locations

    def _validate_coordinates(self, farmer_locations: list[dict], user_story: str) -> GCPQueryOutput | None:
        """
        Validate landowner coordinates against data bounds.
        Returns error output if invalid, None if valid.
        """
        LAT_MIN, LAT_MAX = 40.4, 40.9
        LON_MIN, LON_MAX = 22.5, 22.9

        location_errors = []
        for i, loc in enumerate(farmer_locations, 1):
            lat, lon = loc['lat'], loc['lon']
            coord_errors = []

            if not (LAT_MIN <= lat <= LAT_MAX):
                coord_errors.append(f"latitude {lat}° outside range [{LAT_MIN:.4f}°, {LAT_MAX:.4f}°]")
            if not (LON_MIN <= lon <= LON_MAX):
                coord_errors.append(f"longitude {lon}° outside range [{LON_MIN:.4f}°, {LON_MAX:.4f}°]")

            if coord_errors:
                location_errors.append(f"Location {i}: {'; '.join(coord_errors)}")

        if location_errors:
            error_msg = f"❌ COORDINATE VALIDATION FAILED! {' | '.join(location_errors)} | ⚠️ Coordinates must be within valid data bounds!"
            print("\n" + error_msg, file=sys.stderr)
            return GCPQueryOutput(
                user_story=user_story,
                result=error_msg,
                output_files=[],
                status="error"
            )
        return None

    def _identify_user_story(self, query: str) -> str:
        """Map query to user story - PRIORITY ORDER"""
        q = query.lower()

        # Priority 1: Feedback loops → GCP-16
        if any(phrase in q for phrase in [
            "feedback loop", "feedback", "policy feedback", "financial feedback",
            "policy adjustment", "dynamic policy", "policy response",
            "track subsidy", "subsidy effectiveness", "policy effectiveness",
            "monitor feedback", "subsidy adjustment", "loan rate adjustment"
        ]):
            return "GCP-16"

        # Priority 2: Geographic distribution / maps → GCP-07
        if any(phrase in q for phrase in [
            "geographic", "geographic distribution", "map", "spatial",
            "where", "location", "distribution of pv", "distribution of solar",
            "view geographic", "show map"
        ]):
            return "GCP-07"

        # Priority 3: PV adoption simulation → GCP-03
        if any(phrase in q for phrase in [
            "pv adoption", "solar adoption", "green credit", "simulate pv", "simulate solar",
            "landowner", "financial institution", "loan"
        ]):
            return "GCP-03"

        # Default: GCP-03 (PV adoption simulation is most common)
        return "GCP-03"

    def _run_gcp_03(self, params: GCPQueryInput) -> GCPQueryOutput:
        """GCP-03: Simulate PV Adoption"""
        # VALIDATION: Require spatial filter (geojson OR farmer_locations)
        if not params.geojson_file and not params.farmer_locations:
            return GCPQueryOutput(
                user_story="GCP-03",
                result=(
                    "❌ ERROR: No spatial filter provided!\n\n"
                    "📍 TRANSITION requires a spatial filter to run simulations.\n\n"
                    "Please either:\n"
                    "  1. Draw a polygon on the map (click 'Draw Polygon for Spatial Filtering')\n"
                    "  2. OR specify exact coordinates in your query (e.g., 'simulate PV adoption at (40.5, 22.7)')\n\n"
                    "Without a spatial filter, the simulation cannot determine which geographic area to analyze."
                ),
                output_files=[],
                status="error"
            )

        cmd = [sys.executable, str(self.gcp_path / "run_gcp.py"), "--query", "gcp_03"]

        # DEBUG: Show what LLM extracted
        print(f"🔍 DEBUG GCP-03 extraction:", file=sys.stderr)
        print(f"   farmer_locations: {params.farmer_locations}", file=sys.stderr)
        print(f"   landowners: {params.landowners}", file=sys.stderr)
        print(f"   scenario: {params.scenario}", file=sys.stderr)
        print(f"   policy: {params.policy}", file=sys.stderr)

        # FALLBACK: If LLM failed to extract coordinates, use regex
        # Trigger if query contains coordinate pattern (lat, lon) anywhere
        if not params.farmer_locations:
            import re
            if re.search(r'\(\d+\.?\d*,\s*\d+\.?\d*\)', params.query):
                print(f"⚠️  LLM failed to extract coordinates - using regex fallback", file=sys.stderr)
                params.farmer_locations = self._extract_coordinates_regex(params.query)
                if params.farmer_locations:
                    print(f"✅ Regex extracted {len(params.farmer_locations)} coordinates", file=sys.stderr)

        # Validate coordinates against data bounds
        if params.farmer_locations:
            error_output = self._validate_coordinates(params.farmer_locations, "GCP-03")
            if error_output:
                return error_output

        # Track defaults used (for user notification)
        defaults_used = []

        # Climate scenario: If not specified, run_gcp.py will run ALL climate scenarios
        if params.scenario:
            cmd.extend(["--scenario", params.scenario])
        # Note: No default notification - omitting scenario triggers all-scenarios mode

        # Policy scenario: If not specified, run_gcp.py will run ALL policy scenarios
        if params.policy:
            cmd.extend(["--policy", params.policy])
        # Note: No default notification - omitting policy triggers all-policies mode

        if params.years:
            cmd.extend(["--years", str(params.years)])
        else:
            defaults_used.append("years=10")

        # Add user-specified farmer locations (NEW - 2025-10-21)
        # CRITICAL: Check farmer_locations BEFORE adding --landowners
        if params.farmer_locations:
            import json
            locations_json = json.dumps(params.farmer_locations)
            cmd.extend(["--farmer-locations", locations_json])
            print(f"📍 Using {len(params.farmer_locations)} user-specified landowner locations", file=sys.stderr)

            # Warn if user also provided --landowners (will be overridden)
            if params.landowners:
                print(f"⚠️  WARNING: Ignoring --landowners={params.landowners} (using {len(params.farmer_locations)} user-specified locations instead)", file=sys.stderr)
        elif params.landowners:
            cmd.extend(["--landowners", str(params.landowners)])
        else:
            defaults_used.append("landowners=20")

        # Multi-level ABM parameters (GCP = 3-level: Individual → Market → Policy)
        if params.financial_institutions is not None:
            cmd.extend(["--financial-institutions", str(params.financial_institutions)])
        else:
            defaults_used.append("financial_institutions=2")

        if params.policymakers is not None:
            cmd.extend(["--policymakers", str(params.policymakers)])
        else:
            defaults_used.append("policymakers=1")

        # Add geojson spatial filtering if provided
        if params.geojson_file:
            cmd.extend(["--geojson-file", params.geojson_file])

        # Allow stderr to flow to terminal (for snap-to-grid logging), only capture stdout
        result = subprocess.run(cmd, capture_output=False, stdout=subprocess.PIPE, text=True, cwd=self.gcp_path, timeout=600)

        # Collect output files
        output_files = []
        output_dir = self.gcp_path / "results" / "gcp_03"
        if output_dir.exists():
            output_files.extend([str(f) for f in output_dir.glob("*.html")])
            output_files.extend([str(f) for f in output_dir.glob("*.txt")])
            output_files.extend([str(f) for f in output_dir.glob("*.csv")])

        # Prepend defaults notification to result
        result_text = result.stdout if result.returncode == 0 else result.stderr
        if defaults_used:
            defaults_msg = "ℹ️  Using default values: " + ", ".join(defaults_used)
            result_text = defaults_msg + "\n\n" + result_text

        return GCPQueryOutput(
            user_story="GCP-03",
            result=result_text,
            output_files=output_files,
            status="success" if result.returncode == 0 else "error"
        )

    def _run_gcp_07(self, params: GCPQueryInput) -> GCPQueryOutput:
        """GCP-07: Geographic Distribution"""
        # VALIDATION: Require spatial filter (geojson OR farmer_locations)
        if not params.geojson_file and not params.farmer_locations:
            return GCPQueryOutput(
                user_story="GCP-07",
                result=(
                    "❌ ERROR: No spatial filter provided!\n\n"
                    "📍 TRANSITION requires a spatial filter to run simulations.\n\n"
                    "Please either:\n"
                    "  1. Draw a polygon on the map (click 'Draw Polygon for Spatial Filtering')\n"
                    "  2. OR specify exact coordinates in your query (e.g., 'show PV distribution at (40.5, 22.7)')\n\n"
                    "Without a spatial filter, the simulation cannot determine which geographic area to analyze."
                ),
                output_files=[],
                status="error"
            )

        # FALLBACK: If LLM failed to extract coordinates, use regex
        # Trigger if query contains coordinate pattern (lat, lon) anywhere
        if not params.farmer_locations:
            import re
            if re.search(r'\(\d+\.?\d*,\s*\d+\.?\d*\)', params.query):
                print(f"⚠️  LLM failed to extract coordinates - using regex fallback", file=sys.stderr)
                params.farmer_locations = self._extract_coordinates_regex(params.query)
                if params.farmer_locations:
                    print(f"✅ Regex extracted {len(params.farmer_locations)} coordinates", file=sys.stderr)

        # Validate coordinates against data bounds
        if params.farmer_locations:
            error_output = self._validate_coordinates(params.farmer_locations, "GCP-07")
            if error_output:
                return error_output

        # GCP-07 REQUIRES both scenario and policy (cannot visualize "all" on a single map)
        if not params.scenario:
            error_msg = (
                "❌ ERROR: GCP-07 requires a climate scenario parameter.\n\n"
                "Geographic map visualization needs a specific climate scenario.\n"
                "Please specify one of:\n"
                "  - 'optimistic' (Low Warming ~2°C)\n"
                "  - 'moderate' (Medium Warming ~3°C)\n"
                "  - 'pessimistic' (High Warming ~4-5°C)\n\n"
                "Example: 'Map PV adoption under moderate support with optimistic scenario'"
            )
            return GCPQueryOutput(user_story="GCP-07", result=error_msg, output_files=[], status="error")

        if not params.policy:
            error_msg = (
                "❌ ERROR: GCP-07 requires a policy scenario parameter.\n\n"
                "Geographic map visualization needs a specific policy scenario.\n"
                "Please specify one of:\n"
                "  - 'low support' (10% subsidy, 3% loan rate)\n"
                "  - 'moderate support' (20% subsidy, 2% loan rate)\n"
                "  - 'high support' (30% subsidy, 1% loan rate)\n\n"
                "Example: 'Map PV adoption under moderate support with optimistic scenario'"
            )
            return GCPQueryOutput(user_story="GCP-07", result=error_msg, output_files=[], status="error")

        cmd = [sys.executable, str(self.gcp_path / "run_gcp.py"), "--query", "gcp_07"]

        # Track defaults used (for user notification)
        defaults_used = []

        # Add required parameters (both validated above)
        cmd.extend(["--scenario", params.scenario])
        cmd.extend(["--policy", params.policy])

        if params.years:
            cmd.extend(["--years", str(params.years)])
        else:
            defaults_used.append("years=10")

        # Add user-specified farmer locations (NEW - 2025-10-21)
        # CRITICAL: Check farmer_locations BEFORE adding --landowners
        if params.farmer_locations:
            import json
            locations_json = json.dumps(params.farmer_locations)
            cmd.extend(["--farmer-locations", locations_json])
            print(f"📍 Using {len(params.farmer_locations)} user-specified landowner locations", file=sys.stderr)

            # Warn if user also provided --landowners (will be overridden)
            if params.landowners:
                print(f"⚠️  WARNING: Ignoring --landowners={params.landowners} (using {len(params.farmer_locations)} user-specified locations instead)", file=sys.stderr)
        elif params.landowners:
            cmd.extend(["--landowners", str(params.landowners)])
        else:
            defaults_used.append("landowners=50")

        # Multi-level ABM parameters (GCP = 3-level: Individual → Market → Policy)
        if params.financial_institutions is not None:
            cmd.extend(["--financial-institutions", str(params.financial_institutions)])
        else:
            defaults_used.append("financial_institutions=2")

        if params.policymakers is not None:
            cmd.extend(["--policymakers", str(params.policymakers)])
        else:
            defaults_used.append("policymakers=1")

        # Add geojson spatial filtering if provided
        if params.geojson_file:
            cmd.extend(["--geojson-file", params.geojson_file])

        print(f"🚀 Running GCP-07 command: {' '.join(cmd)}", file=sys.stderr)
        # Allow stderr to flow to terminal (for snap-to-grid logging), only capture stdout
        result = subprocess.run(cmd, capture_output=False, stdout=subprocess.PIPE, text=True, cwd=self.gcp_path, timeout=600)
        print(f"✅ GCP-07 completed with return code: {result.returncode}", file=sys.stderr)

        # DEBUG: Show stdout and stderr
        if result.stdout:
            print(f"📤 STDOUT length: {len(result.stdout)} chars", file=sys.stderr)
        if result.stderr:
            print(f"📤 STDERR length: {len(result.stderr)} chars", file=sys.stderr)
            print(f"📤 STDERR preview: {result.stderr[:500]}", file=sys.stderr)

        # Collect output files
        output_files = []
        output_dir = self.gcp_path / "results" / "gcp_07"
        if output_dir.exists():
            output_files.extend([str(f) for f in output_dir.glob("*.html")])
            output_files.extend([str(f) for f in output_dir.glob("*.txt")])
        print(f"📁 Found {len(output_files)} output files", file=sys.stderr)

        # Prepend defaults notification to result
        result_text = result.stdout if result.returncode == 0 else result.stderr
        if defaults_used:
            defaults_msg = "ℹ️  Using default values: " + ", ".join(defaults_used)
            result_text = defaults_msg + "\n\n" + result_text

        return GCPQueryOutput(
            user_story="GCP-07",
            result=result_text,
            output_files=output_files,
            status="success" if result.returncode == 0 else "error"
        )

    def _run_gcp_16(self, params: GCPQueryInput) -> GCPQueryOutput:
        """GCP-16: Policy Feedback Loops"""
        # VALIDATION: Require spatial filter (geojson OR farmer_locations)
        if not params.geojson_file and not params.farmer_locations:
            return GCPQueryOutput(
                user_story="GCP-16",
                result=(
                    "❌ ERROR: No spatial filter provided!\n\n"
                    "📍 TRANSITION requires a spatial filter to run simulations.\n\n"
                    "Please either:\n"
                    "  1. Draw a polygon on the map (click 'Draw Polygon for Spatial Filtering')\n"
                    "  2. OR specify exact coordinates in your query (e.g., 'monitor feedback at (40.5, 22.7)')\n\n"
                    "Without a spatial filter, the simulation cannot determine which geographic area to analyze."
                ),
                output_files=[],
                status="error"
            )

        # DEBUG: Show what LLM extracted
        print(f"🔍 DEBUG GCP-16 extraction:", file=sys.stderr)
        print(f"   landowners: {params.landowners}", file=sys.stderr)
        print(f"   financial_institutions: {params.financial_institutions}", file=sys.stderr)
        print(f"   policymakers: {params.policymakers}", file=sys.stderr)
        print(f"   scenario: {params.scenario}", file=sys.stderr)
        print(f"   years: {params.years}", file=sys.stderr)

        # FALLBACK: If LLM failed to extract coordinates, use regex
        # Trigger if query contains coordinate pattern (lat, lon) anywhere
        if not params.farmer_locations:
            import re
            if re.search(r'\(\d+\.?\d*,\s*\d+\.?\d*\)', params.query):
                print(f"⚠️  LLM failed to extract coordinates - using regex fallback", file=sys.stderr)
                params.farmer_locations = self._extract_coordinates_regex(params.query)
                if params.farmer_locations:
                    print(f"✅ Regex extracted {len(params.farmer_locations)} coordinates", file=sys.stderr)

        # Validate coordinates against data bounds
        if params.farmer_locations:
            error_output = self._validate_coordinates(params.farmer_locations, "GCP-16")
            if error_output:
                return error_output

        # GCP-16 REQUIRES scenario (automatically runs ALL policies)
        if not params.scenario:
            error_msg = (
                "❌ ERROR: GCP-16 requires a climate scenario parameter.\n\n"
                "Feedback loop analysis needs a specific climate scenario.\n"
                "Please specify one of:\n"
                "  - 'optimistic' (Low Warming ~2°C)\n"
                "  - 'moderate' (Medium Warming ~3°C)\n"
                "  - 'pessimistic' (High Warming ~4-5°C)\n\n"
                "Note: GCP-16 automatically runs ALL policy scenarios (low, moderate, high support).\n"
                "The policy parameter is ignored if provided.\n\n"
                "Example: 'Monitor feedback loops with 50 landowners under optimistic scenario for 15 years'"
            )
            return GCPQueryOutput(user_story="GCP-16", result=error_msg, output_files=[], status="error")

        cmd = [sys.executable, str(self.gcp_path / "run_gcp.py"), "--query", "gcp_16"]

        # Track defaults used (for user notification)
        defaults_used = []

        # Add required scenario parameter (validated above)
        cmd.extend(["--scenario", params.scenario])

        # Policy is automatically ALL policies (user doesn't specify)
        # If user provided policy, it will be passed but ignored by query function
        if params.policy:
            cmd.extend(["--policy", params.policy])  # Passed but ignored

        if params.years:
            cmd.extend(["--years", str(params.years)])
        else:
            defaults_used.append("years=15 (longer simulation for feedback)")

        # Add user-specified farmer locations (NEW - 2025-10-21)
        # CRITICAL: Check farmer_locations BEFORE adding --landowners
        if params.farmer_locations:
            import json
            locations_json = json.dumps(params.farmer_locations)
            cmd.extend(["--farmer-locations", locations_json])
            print(f"📍 Using {len(params.farmer_locations)} user-specified landowner locations", file=sys.stderr)

            # Warn if user also provided --landowners (will be overridden)
            if params.landowners:
                print(f"⚠️  WARNING: Ignoring --landowners={params.landowners} (using {len(params.farmer_locations)} user-specified locations instead)", file=sys.stderr)
        elif params.landowners:
            cmd.extend(["--landowners", str(params.landowners)])
            # Don't add to defaults - user specified it
        else:
            defaults_used.append("landowners=20")

        # Multi-level ABM parameters (GCP = 3-level: Individual → Market → Policy)
        if params.financial_institutions is not None:
            cmd.extend(["--financial-institutions", str(params.financial_institutions)])
        else:
            defaults_used.append("financial_institutions=2")

        if params.policymakers is not None:
            cmd.extend(["--policymakers", str(params.policymakers)])
        else:
            defaults_used.append("policymakers=1")

        # Add geojson spatial filtering if provided
        if params.geojson_file:
            cmd.extend(["--geojson-file", params.geojson_file])

        # Allow stderr to flow to terminal (for snap-to-grid logging), only capture stdout
        result = subprocess.run(cmd, capture_output=False, stdout=subprocess.PIPE, text=True, cwd=self.gcp_path, timeout=600)

        # Collect output files
        output_files = []
        output_dir = self.gcp_path / "results" / "gcp_16"
        if output_dir.exists():
            output_files.extend([str(f) for f in output_dir.glob("*.html")])
            output_files.extend([str(f) for f in output_dir.glob("*.txt")])
            output_files.extend([str(f) for f in output_dir.glob("*.csv")])

        # Prepend defaults notification to result
        result_text = result.stdout if result.returncode == 0 else result.stderr
        if defaults_used:
            defaults_msg = "ℹ️  Using default values: " + ", ".join(defaults_used)
            result_text = defaults_msg + "\n\n" + result_text

        return GCPQueryOutput(
            user_story="GCP-16",
            result=result_text,
            output_files=output_files,
            status="success" if result.returncode == 0 else "error"
        )


# ==================== Tool Definition ====================

def get_gcp_tool():
    """Get configured GCP tool instance"""
    return GCPTool()
