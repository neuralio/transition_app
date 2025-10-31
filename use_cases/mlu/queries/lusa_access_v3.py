"""
MLU-01: Access LUSA Module (v3 - CORRECT APPROACH)

Just run the EXISTING simulation code with minimal parameters!
Don't try to fake ResultCollector - use the real simulation!
"""

import sys
from pathlib import Path
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def query_lusa_access(
    data_path: str,
    crop: str,
    scenario: str,
    n_parcels: int = 15,
    output_dir: str = None
) -> Dict:
    """
    Access LUSA predictions by running a MINIMAL simulation.

    This runs the EXISTING simulation code (which works!) with minimal parameters.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA directory
        crop: Crop type (WHEAT, MAIZE)
        scenario: Climate scenario (rcp26, rcp45, rcp85, historical)
        n_parcels: Number of parcels to sample
        output_dir: Output directory

    Returns:
        Dictionary with status and visualization paths
    """
    print(f"\n{'='*60}")
    print(f"MLU-01: Access LUSA Module")
    print(f"{'='*60}")
    print(f"Crop: {crop.upper()}")
    print(f"Scenario: {scenario.upper()}")
    print(f"Parcels: {n_parcels}")
    print(f"{'='*60}\n")

    try:
        # Just run the EXISTING simulation code!
        # It already works and produces all the visualizations we need!
        from use_cases.mlu.scripts.run_mlu_simulation import run_simulation_with_results

        # Set output directory
        if output_dir is None:
            output_dir = f"results/mlu01_{crop.lower()}_{scenario.lower()}"

        # Run the simulation (it already works!)
        print(f"Running simulation to generate LUSA visualizations...")

        collector = run_simulation_with_results(
            scenario=scenario,
            n_years=1,  # Just 1 year for quick LUSA access
            n_parcels=n_parcels,
            n_farmers=None,
            n_pv_installations=None,
            output_dir=output_dir,
            data_path=data_path,
            n_collectives=0,  # Disable multi-level for speed
            n_markets=0,
            n_policies=0,
            enable_multi_level=False,
            rl_policy=None
        )

        # The simulation already generated all visualizations!
        output_path = Path(output_dir) / scenario
        viz_files = list(output_path.glob('*.html'))

        print(f"\n{'='*60}")
        print(f"MLU-01: COMPLETE")
        print(f"{'='*60}")
        print(f"Output Directory: {output_path}")
        print(f"Visualizations Generated: {len(viz_files)}")
        print(f"\nFiles:")
        for f in sorted(viz_files):
            print(f"  - {f.name}")
        print(f"{'='*60}\n")

        return {
            'status': 'success',
            'crop': crop.upper(),
            'scenario': scenario.upper(),
            'output_dir': str(output_path),
            'visualizations': [str(f) for f in viz_files],
            'collector': collector
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f"Failed to access LUSA data: {str(e)}",
            'crop': crop,
            'scenario': scenario
        }


def main():
    """Example usage."""
    import argparse

    parser = argparse.ArgumentParser(description="MLU-01: Access LUSA Module")
    parser.add_argument("--data-path", required=True, help="Path to PILOT_THESSALONIKI_DATA")
    parser.add_argument("--crop", required=True, choices=["WHEAT", "MAIZE"], help="Crop type")
    parser.add_argument("--scenario", required=True,
                       choices=["rcp26", "rcp45", "rcp85", "historical"],
                       help="Climate scenario")
    parser.add_argument("--parcels", type=int, default=15, help="Number of parcels")
    parser.add_argument("--output", default=None, help="Output directory")

    args = parser.parse_args()

    result = query_lusa_access(
        data_path=args.data_path,
        crop=args.crop,
        scenario=args.scenario,
        n_parcels=args.parcels,
        output_dir=args.output
    )

    if result['status'] == 'error':
        print(f"\n❌ Error: {result['message']}")
        sys.exit(1)

    print(f"\n✅ Query completed!")


if __name__ == "__main__":
    main()
