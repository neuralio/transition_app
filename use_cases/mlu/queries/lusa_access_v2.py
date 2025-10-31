"""
MLU-01: Access LUSA Module (REDESIGNED)

NOW USES THE SAME VISUALIZATION CODE AS FULL SIMULATION!

User Story: As a Policymaker, I want to access the LUSA module to retrieve
land-use suitability predictions for specific crops and climate scenarios.
"""

import sys
from pathlib import Path
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.mlu.queries.query_utils import (
    create_lusa_result_collector,
    generate_visualizations
)


def query_lusa_access(
    data_path: str,
    crop: str,
    scenario: str,
    n_parcels: int = 15,
    output_dir: str = None
) -> Dict:
    """
    Access LUSA predictions and generate FULL visualizations.

    This uses THE SAME visualization code as the full simulation!

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA directory
        crop: Crop type (WHEAT, MAIZE)
        scenario: Climate scenario (rcp26, rcp45, rcp85, historical)
        n_parcels: Number of parcels to sample from grid
        output_dir: Output directory (default: results/mlu01_{crop}_{scenario})

    Returns:
        Dictionary with status and visualization paths
    """
    print(f"\n{'='*60}")
    print(f"MLU-01: Access LUSA Module")
    print(f"{'='*60}")
    print(f"Crop: {crop.upper()}")
    print(f"Scenario: {scenario.upper()}")
    print(f"Data Path: {data_path}")
    print(f"Sampled Parcels: {n_parcels}")
    print(f"{'='*60}\n")

    try:
        # Create ResultCollector with LUSA data and sampled parcels
        print(f"Loading LUSA data and sampling REAL grid points...")
        start_year = 1990 if scenario.lower() == 'historical' else 2021

        collector = create_lusa_result_collector(
            data_path=data_path,
            crop=crop,
            scenario=scenario,
            n_parcels=n_parcels,
            start_year=start_year
        )

        # Set output directory
        if output_dir is None:
            output_dir = f"results/mlu01_{crop.lower()}_{scenario.lower()}"

        # Generate visualizations using EXISTING visualization code
        # This produces THE SAME visualizations as full simulation!
        viz_result = generate_visualizations(
            collector=collector,
            data_path=data_path,
            output_dir=output_dir,
            crops=[crop.upper()]
        )

        # Print summary
        print(f"\n{'='*60}")
        print(f"MLU-01: LUSA ACCESS COMPLETE")
        print(f"{'='*60}")
        print(f"Output Directory: {viz_result['output_dir']}")
        print(f"Visualizations Generated: {len(viz_result['files_generated'])}")
        print(f"\nGenerated Files:")
        for f in sorted(viz_result['files_generated']):
            print(f"  - {f.name}")
        print(f"{'='*60}\n")

        return {
            'status': 'success',
            'crop': crop.upper(),
            'scenario': scenario.upper(),
            'output_dir': viz_result['output_dir'],
            'visualizations': [str(f) for f in viz_result['files_generated']],
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
    """Example usage of MLU-01 query."""
    import argparse

    parser = argparse.ArgumentParser(description="MLU-01: Access LUSA Module (Redesigned)")
    parser.add_argument("--data-path", required=True, help="Path to PILOT_THESSALONIKI_DATA")
    parser.add_argument("--crop", required=True, choices=["WHEAT", "MAIZE"], help="Crop type")
    parser.add_argument("--scenario", required=True,
                       choices=["rcp26", "rcp45", "rcp85", "historical"],
                       help="Climate scenario")
    parser.add_argument("--parcels", type=int, default=15, help="Number of parcels to sample")
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

    print(f"\n✅ Query completed successfully!")
    print(f"📂 Open visualizations in: {result['output_dir']}")


if __name__ == "__main__":
    main()
