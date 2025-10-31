"""
RL Tool for TRANSITION LLM Agent
Handles RL training and RL vs rule-based comparisons.
"""

import subprocess
from pathlib import Path
from atomic_agents import BaseTool, BaseToolConfig, BaseIOSchema
from pydantic import Field


class RLQueryInput(BaseIOSchema):
    """Input for RL queries"""
    query: str = Field(..., description="User's natural language query about RL")
    scenario: str | None = Field(None, description="Climate scenario: rcp26, rcp45, rcp85")
    timesteps: int | None = Field(None, description="Training timesteps (default: 500000)")
    years: int | None = Field(None, description="Simulation years for comparison")
    parcels: int | None = Field(None, description="Number of parcels for comparison")
    collectives: int | None = Field(None, description="Number of farmer collectives (default: 2)")
    markets: int | None = Field(None, description="Number of commodity markets (default: 1)")
    policymakers: int | None = Field(None, description="Number of policymaker agents (default: 1)")
    rl_model_path: str | None = Field(None, description="Path to trained RL model (.zip)")
    geojson_file: str | None = Field(None, description="Path to GeoJSON file for spatial filtering")


class RLQueryOutput(BaseIOSchema):
    """Output from RL operations"""
    operation: str = Field(..., description="Operation performed: train or compare")
    result: str = Field(..., description="Operation results")
    output_files: list[str] = Field(default=[], description="Generated files")
    status: str = Field(..., description="success or error")


class RLTool(BaseTool[RLQueryInput, RLQueryOutput]):
    """
    Tool for Reinforcement Learning operations:
    - Train RL models for adaptive agricultural agents
    - Compare RL vs rule-based decision making
    """

    def __init__(self, config: BaseToolConfig = BaseToolConfig()):
        super().__init__(config)
        self.project_root = Path(__file__).parent.parent
        self.rl_path = self.project_root / "use_cases" / "mlu" / "rl"

    def run(self, params: RLQueryInput) -> RLQueryOutput:
        """Execute RL operation based on query"""

        # Identify operation
        operation = self._identify_operation(params.query)

        if operation == "train":
            return self._train_rl_model(params)
        elif operation == "compare":
            return self._compare_rl_vs_rules(params)
        else:
            return RLQueryOutput(
                operation="unknown",
                result=f"Could not identify RL operation from query: {params.query}",
                output_files=[],
                status="error"
            )

    def _identify_operation(self, query: str) -> str:
        """Map natural language query to RL operation"""
        query_lower = query.lower()

        # Training keywords
        if any(word in query_lower for word in ["train", "training", "learn", "optimize"]):
            return "train"

        # Comparison keywords
        if any(word in query_lower for word in ["compare", "comparison", "vs", "versus", "benchmark"]):
            return "compare"

        return "unknown"

    def _train_rl_model(self, params: RLQueryInput) -> RLQueryOutput:
        """
        Train RL model using train_rl02.py
        RL-02: Adaptive Agricultural Agents
        """
        cmd = ["python3", str(self.rl_path / "train_rl02.py")]

        if params.scenario:
            cmd.extend(["--scenario", params.scenario])
        if params.timesteps:
            cmd.extend(["--timesteps", str(params.timesteps)])

        print(f"🏋️  Training RL model")
        print(f"   Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.rl_path),
                capture_output=True,
                text=True,
                timeout=7200  # 2 hours max
            )

            if result.returncode == 0:
                # Try to find the model file
                output_files = []
                models_dir = self.rl_path / "models" / "rl02"
                if models_dir.exists():
                    output_files = [str(f) for f in models_dir.glob("*.zip")]

                return RLQueryOutput(
                    operation="train",
                    result=f"✅ RL model trained successfully!\n\n{result.stdout}",
                    output_files=output_files,
                    status="success"
                )
            else:
                return RLQueryOutput(
                    operation="train",
                    result=f"❌ Training failed:\n{result.stderr}",
                    output_files=[],
                    status="error"
                )

        except subprocess.TimeoutExpired:
            return RLQueryOutput(
                operation="train",
                result="❌ Training timed out (exceeded 2 hours)",
                output_files=[],
                status="error"
            )
        except Exception as e:
            return RLQueryOutput(
                operation="train",
                result=f"❌ Error during training: {str(e)}",
                output_files=[],
                status="error"
            )

    def _compare_rl_vs_rules(self, params: RLQueryInput) -> RLQueryOutput:
        """
        Compare RL vs rule-based decisions using compare_rl_vs_rules.py
        """
        defaults_used = []

        cmd = ["python3", str(self.rl_path / "compare_rl_vs_rules.py")]

        if params.scenario:
            cmd.extend(["--scenario", params.scenario])
        else:
            defaults_used.append("scenario=ALL (all climate scenarios)")

        if params.years:
            cmd.extend(["--years", str(params.years)])
        else:
            defaults_used.append("years=50")

        if params.parcels:
            cmd.extend(["--parcels", str(params.parcels)])
        else:
            defaults_used.append("parcels=30")

        if params.collectives:
            cmd.extend(["--collectives", str(params.collectives)])
        else:
            defaults_used.append("collectives=2")

        if params.markets:
            cmd.extend(["--markets", str(params.markets)])
        else:
            defaults_used.append("markets=1")

        if params.policymakers:
            cmd.extend(["--policymakers", str(params.policymakers)])
        else:
            defaults_used.append("policymakers=1")

        # Add RL model path if provided
        if params.rl_model_path:
            cmd.extend(["--rl-model", params.rl_model_path])

        # Add geojson spatial filtering if provided (reject empty strings)
        if params.geojson_file and params.geojson_file.strip():
            cmd.extend(["--geojson-file", params.geojson_file])

        print(f"📊 Comparing RL vs Rule-based")
        print(f"   Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.rl_path),
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes max
            )

            if result.returncode == 0:
                # Parse output files from stdout (the script prints file paths)
                output_files = []

                # Try default locations (both relative to RL dir and project root)
                possible_dirs = [
                    self.rl_path / "results" / "rl_comparison",  # When run from RL dir
                    self.project_root / "results" / "rl_comparison"  # When run from project root
                ]

                for output_dir in possible_dirs:
                    if output_dir.exists():
                        # Search recursively for HTML/PNG/TXT files (handles nested scenario dirs)
                        output_files.extend([str(f) for f in output_dir.rglob("*.html")])
                        output_files.extend([str(f) for f in output_dir.rglob("*.png")])
                        output_files.extend([str(f) for f in output_dir.rglob("*.txt")])

                # Remove duplicates
                output_files = list(set(output_files))

                # Prepend defaults notification if any defaults were used
                result_text = result.stdout
                if defaults_used:
                    defaults_msg = "ℹ️  Using default values: " + ", ".join(defaults_used)
                    result_text = defaults_msg + "\n\n" + result_text

                return RLQueryOutput(
                    operation="compare",
                    result=f"✅ RL vs Rule-based comparison complete!\n\n{result_text}",
                    output_files=output_files,
                    status="success"
                )
            else:
                # Extract clean error message (filter out warnings and debug messages)
                stderr_lines = result.stderr.split('\n') if result.stderr else []

                # Look for our clean error message (starts with ❌ ERROR:)
                clean_error_lines = [line for line in stderr_lines if line.strip().startswith('❌ ERROR:') or (line.strip() and not line.strip().startswith(('🔍 DEBUG', 'UserWarning:', 'warnings.warn')))]

                # If we found clean error lines, use those; otherwise use full stderr
                if any(line.strip().startswith('❌ ERROR:') for line in stderr_lines):
                    # Extract the error block (ERROR line + following lines until next empty line or end)
                    error_block = []
                    in_error = False
                    for line in stderr_lines:
                        if line.strip().startswith('❌ ERROR:'):
                            in_error = True
                            error_block.append(line)
                        elif in_error:
                            if line.strip():  # Non-empty line
                                error_block.append(line)
                            else:  # Empty line marks end of error block
                                break
                    error_msg = '\n'.join(error_block)
                else:
                    # No clean error found, use filtered stderr
                    error_msg = '\n'.join(clean_error_lines) if clean_error_lines else result.stderr

                return RLQueryOutput(
                    operation="compare",
                    result=f"❌ Comparison failed:\n{error_msg}",
                    output_files=[],
                    status="error"
                )

        except subprocess.TimeoutExpired:
            return RLQueryOutput(
                operation="compare",
                result="❌ Comparison timed out (exceeded 10 minutes)",
                output_files=[],
                status="error"
            )
        except Exception as e:
            return RLQueryOutput(
                operation="compare",
                result=f"❌ Error during comparison: {str(e)}",
                output_files=[],
                status="error"
            )


if __name__ == "__main__":
    # Test RLTool
    print("=" * 60)
    print("RL TOOL TEST")
    print("=" * 60)

    tool = RLTool()

    # Test 1: Comparison query
    print("\n📝 Test 1: Comparison query")
    test_input = RLQueryInput(
        query="Compare RL vs rule-based for 50 years",
        scenario="rcp45",
        years=50,
        parcels=30
    )

    result = tool.run(test_input)
    print(f"Operation: {result.operation}")
    print(f"Status: {result.status}")
    print(f"Result:\n{result.result}")

    print("\n✅ RLTool test complete!")
