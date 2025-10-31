"""
MLU-08: Simulate Future Climate Scenarios

This query runs ABM simulations for future climate scenarios to show how agents
dynamically update their land-use decisions based on climate inputs (temperature, rainfall).

Supports Monte Carlo ensemble mode for uncertainty quantification.
"""

import sys
from pathlib import Path
from openai import OpenAI
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def _generate_ensemble_insights(scenarios, enable_ensemble, ensemble_size):
    """Generate AI insights for ensemble simulation results."""
    try:
        from use_cases.mlu.utils.scenario_utils import get_scenario_display_name
        client = OpenAI()

        # Convert scenario codes to display names
        scenario_display_names = [get_scenario_display_name(s) for s in scenarios]

        data_summary = f"""
Future Climate Scenario Simulation Results:
- Scenarios analyzed: {', '.join(scenario_display_names)}
- Ensemble mode: {'Enabled' if enable_ensemble else 'Disabled'}
- Ensemble size: {ensemble_size if enable_ensemble else 1} realizations
- Analysis type: Agent-based modeling with multi-level interactions (Individual ↔ Community ↔ Market ↔ Policy)
"""

        insights = {}

        # Time-Series with Uncertainty Dashboard (2x2 Grid: Land Use, Income, Yield, Energy)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a climate modeling expert specializing in uncertainty quantification with Monte Carlo methods. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Time-Series Dashboard with 4 subplots: (1) Land Use Adoption (WHEAT/MAIZE/SOLAR with 95% CI), (2) Total Income evolution, (3) Average Yield trends, (4) Solar Energy Production. What do the confidence band widths across these 4 metrics reveal about stochastic variability in multi-level ABM? Which metrics show highest uncertainty?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Time-Series with Uncertainty Dashboard (4-Panel: Land Use, Income, Yield, Energy)"] = response.choices[0].message.content.strip()

        # Probabilistic Summary Dashboard (Distribution Histograms & Probability Bars)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a risk analyst interpreting probabilistic climate projections. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Probabilistic Summary Dashboard showing likelihood distributions across {ensemble_size} runs: final land use distributions (histogram), probability bars for key outcomes, and confidence intervals. How should stakeholders use these probability statements (e.g., '73% probability of high solar adoption') for risk management and investment planning?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Probabilistic Summary Dashboard (Histograms & Probability Bars)"] = response.choices[0].message.content.strip()

        # Uncertainty Metrics Dashboard (Mean, Median, Min, Max, StdDev)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a statistical analyst evaluating ensemble model outputs. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Uncertainty Metrics Dashboard showing ensemble statistics: mean trajectories, median values, min/max ranges, and standard deviations across all key variables (land use, income, yield, energy). What do the spread metrics tell us about model sensitivity and decision robustness under uncertainty?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Uncertainty Metrics Dashboard (Statistical Summary Panels)"] = response.choices[0].message.content.strip()

        # Qualitative Summary & Policy Recommendations (Multi-Tab Insights Dashboard)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a climate policy strategist synthesizing ensemble results for decision-makers. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nSynthesize the Qualitative Insights Dashboard with multiple tabs: (1) Qualitative Summary (environmental benefits, community impact, probabilistic projections), (2) Policy Recommendations (scenario-specific + cross-scenario analysis), (3) Technical Details. How do {ensemble_size} ensemble runs across {', '.join(scenario_display_names)} inform robust climate adaptation strategies?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Qualitative Summary & Policy Recommendations (Multi-Tab Insights Dashboard)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate AI insights: {e}")
        return {
            "Ensemble Uncertainty Quantification (Confidence Bands)": f"Ensemble mode with {ensemble_size} Monte Carlo realizations quantifies stochastic variability in agent decisions and climate impacts, with 95% confidence bands showing range of plausible outcomes",
            "Probabilistic Projections (Distribution Charts)": f"Probabilistic analysis across {ensemble_size} runs enables risk-based decision making by providing likelihood distributions rather than single deterministic projections",
            "Scenario Pathway Comparison (Multi-Scenario Dashboard)": f"Comparing {len(scenarios)} climate scenarios ({', '.join(scenario_display_names)}) reveals range of possible futures, with uncertainty bands indicating robustness of adaptation strategies across pathways",
            "Dynamic Suitability Evolution (Climate Impact Trajectories)": "Agent-based model captures temporal evolution of crop suitability under changing climate conditions, showing how farmers dynamically adapt land use decisions as environmental conditions shift"
        }


def query_mlu_08(
    data_path: str,
    scenarios: list = None,
    crops: list = None,
    output_dir: str = None,
    enable_ensemble: bool = None,
    ensemble_size: int = None,
    config = None,
    n_years: int = None,
    n_parcels: int = None,
    n_collectives: int = None,  # NEW: Multi-level parameter
    n_markets: int = None,      # NEW: Multi-level parameter
    n_policies: int = None,     # NEW: Multi-level parameter
    geojson: dict = None,
    farmer_locations: list = None  # NEW (2025-10-21): User-specified farmer locations
):
    """
    Run MLU-08: Future Climate Scenario Simulation with Uncertainty.

    Runs ABM simulations for future climate scenarios to show how agents
    dynamically update their land-use decisions based on climate inputs.
    Supports Monte Carlo ensemble mode for uncertainty quantification.

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        scenarios: List of scenarios to simulate (default: ['rcp26', 'rcp45', 'rcp85'])
        crops: List of crops to analyze (default: ['WHEAT', 'MAIZE']) - NOT USED (agents decide dynamically)
        output_dir: Output directory for results
        enable_ensemble: Enable Monte Carlo ensemble mode (default: from config)
        ensemble_size: Number of ensemble realizations (default: from config)
        n_years: Number of years to simulate (default: from config)
        n_parcels: Number of land parcels (default: from config)
        n_collectives: Number of farmer collectives (default: from config)
        n_markets: Number of commodity markets (default: from config)
        n_policies: Number of policymakers (default: from config)
        config: MLUConfig object (optional, will load from default if None)
        geojson: GeoJSON dict/string for polygon-based spatial filtering (optional)
        farmer_locations: List of user-specified farmer locations with crops (optional)

    Returns:
        dict: Result dictionary with status, outputs, and metrics
    """
    try:
        # Load config if not provided
        if config is None:
            from use_cases.mlu.config_loader import load_config
            config = load_config()

        # Import ABM simulation runner
        from use_cases.mlu.scripts.run_mlu_simulation import run_multi_scenario_analysis

        if scenarios is None:
            scenarios = ['rcp26', 'rcp45', 'rcp85']

        # Handle ensemble parameters
        if enable_ensemble is None:
            enable_ensemble = config.ensemble_size > 1 if hasattr(config, 'ensemble_size') else False

        if ensemble_size is None:
            ensemble_size = config.ensemble_size if hasattr(config, 'ensemble_size') else 1

        # Get simulation parameters from config
        if n_years is None:
            n_years = config.n_years if hasattr(config, 'n_years') else 10

        if n_parcels is None:
            n_parcels = config.n_parcels if hasattr(config, 'n_parcels') else 15

        # Create output directory with timestamp to prevent overwriting
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_dir:
            output_path = Path(output_dir) / 'mlu_08' / timestamp
        else:
            # Default: use_cases/mlu/results/mlu_08/{timestamp}
            mlu_dir = Path(__file__).parent.parent
            output_path = mlu_dir / 'results' / 'mlu_08' / timestamp
        output_path.mkdir(parents=True, exist_ok=True)

        # Get multi-level settings - prioritize CLI arguments over config
        if n_collectives is None:
            n_collectives = config.multilevel['n_collectives'] if hasattr(config, 'multilevel') else 2

        if n_markets is None:
            n_markets = config.multilevel['n_markets'] if hasattr(config, 'multilevel') else 1

        if n_policies is None:
            n_policies = config.multilevel['n_policymakers'] if hasattr(config, 'multilevel') else 1

        enable_multi_level = config.multilevel['enabled'] if hasattr(config, 'multilevel') else True

        print(f"\n{'='*80}")
        print(f"🌍 MLU-08: Future Climate Scenario ABM Simulation")
        print(f"{'='*80}")
        print(f"Scenarios: {', '.join([s.upper() for s in scenarios])}")
        print(f"Duration: {n_years} years")
        print(f"Land Parcels: {n_parcels} (agents decide crops dynamically)")
        print(f"Multi-Level ABM: {'✅ ENABLED' if enable_multi_level else '❌ DISABLED'}")
        if enable_multi_level:
            print(f"  - Individual Level: {n_parcels} land parcels")
            print(f"  - Community Level: {n_collectives} farmer collectives")
            print(f"  - Market Level: {n_markets} commodity markets")
            print(f"  - Policy Level: {n_policies} policymakers")
        if enable_ensemble:
            print(f"Mode: 🎲 Monte Carlo Ensemble ({ensemble_size} realizations per scenario)")
        else:
            print(f"Mode: Single run per scenario")
        print(f"{'='*80}\n")

        # Run ABM simulations for all scenarios
        results_by_scenario = run_multi_scenario_analysis(
            scenarios=scenarios,
            n_years=n_years,
            n_parcels=n_parcels,
            output_dir=str(output_path),
            data_path=data_path,
            enable_ensemble=enable_ensemble,
            ensemble_size=ensemble_size,
            confidence_level=config.confidence_level if hasattr(config, 'confidence_level') else 0.95,
            n_collectives=n_collectives,
            n_markets=n_markets,
            n_policies=n_policies,
            enable_multi_level=enable_multi_level,
            rl_policy=None,
            config=config,
            geojson=geojson,
            farmer_locations=farmer_locations
        )

        print(f"\n{'='*80}")
        print(f"✅ MLU-08 COMPLETE")
        print(f"{'='*80}")
        print(f"Output: {output_path}")
        print(f"\nResults:")
        print(f"  - ABM simulation data for each scenario")
        print(f"  - Visualization showing how agents adapt to climate changes")
        if enable_ensemble:
            print(f"  - Ensemble uncertainty bands ({ensemble_size} realizations)")
            print(f"  - Probabilistic statements (e.g., '70% probability of high solar adoption')")
        print(f"\nKey Insights:")
        print(f"  - Agents dynamically update land-use decisions based on climate inputs")
        print(f"  - Suitability scores influence agent behavior (LUSA predictions used)")
        print(f"  - Multi-level interactions: Individual ↔ Community ↔ Market ↔ Policy")

        # Generate AI insights
        print(f"\n📊 AI-Generated Insights:")
        insights = _generate_ensemble_insights(scenarios, enable_ensemble, ensemble_size if enable_ensemble else 1)
        for viz_name, insight in insights.items():
            print(f"\n  {viz_name}:")
            print(f"    {insight}")

        print(f"{'='*80}\n")

        return {
            'status': 'success',
            'message': f'MLU-08 complete - {len(scenarios)} scenarios simulated',
            'output_dir': str(output_path),
            'scenarios': scenarios,
            'ensemble_enabled': enable_ensemble,
            'ensemble_size': ensemble_size if enable_ensemble else 1,
            'results': results_by_scenario,
            'ai_insights': insights
        }

    except ValueError as e:
        # Clean error message for validation errors (user-friendly)
        # Print with red box styling to stderr
        error_msg = str(e)
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"{error_msg}", file=sys.stderr)
        print(f"{'='*80}\n", file=sys.stderr)
        return {
            'status': 'error',
            'message': error_msg
        }
    except Exception as e:
        # Full traceback for unexpected errors (debugging)
        import traceback
        return {
            'status': 'error',
            'message': f'MLU-08 failed: {str(e)}',
            'traceback': traceback.format_exc()
        }
