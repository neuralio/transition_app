#!/usr/bin/env python3
"""
Compare RL-based vs Rule-based Land-Use Decisions

Runs both approaches on same scenario and generates comparison visualizations.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from datetime import datetime

from use_cases.mlu.config_loader import load_config
from use_cases.mlu.scripts.run_mlu_simulation import run_simulation_with_results
from use_cases.mlu.rl.rl_policy import RLPolicy


def run_comparison(
    scenario: str,
    n_years: int,
    n_parcels: int,
    rl_model_path: str,
    data_path: str,
    output_dir: str = "results/rl_comparison",
    config=None,
    n_collectives: int = 2,
    n_markets: int = 1,
    n_policymakers: int = 1,
    geojson: dict = None
):
    """
    Run both rule-based and RL-based simulations and compare results.

    Args:
        scenario: Climate scenario (rcp26, rcp45, rcp85)
        n_years: Number of years to simulate
        n_parcels: Number of land parcels
        rl_model_path: Path to trained RL model (.zip)
        data_path: Path to data directory
        output_dir: Output directory for results
        config: Configuration object
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"RL vs RULE-BASED COMPARISON")
    print(f"{'='*80}")
    print(f"Scenario:      {scenario.upper()}")
    print(f"Duration:      {n_years} years")
    print(f"Parcels:       {n_parcels}")
    print(f"RL Model:      {rl_model_path}")
    print(f"Output:        {output_dir}/")
    print(f"{'='*80}\n")

    # Load RL policy
    print("Loading RL policy...")
    rl_policy = RLPolicy(rl_model_path, framework="sb3")

    # Run rule-based simulation
    print(f"\n{'='*80}")
    print(f"1/2: Running RULE-BASED simulation...")
    print(f"{'='*80}\n")

    rule_output = f"{output_dir}/rule_based"
    os.makedirs(rule_output, exist_ok=True)

    rule_results = run_simulation_with_results(
        scenario=scenario,
        n_years=n_years,
        n_parcels=n_parcels,
        output_dir=rule_output,
        data_path=data_path,
        n_collectives=n_collectives,
        n_markets=n_markets,
        n_policies=n_policymakers,
        enable_multi_level=config.multilevel['enabled'] if config else True,
        rl_policy=None,  # Rule-based
        config=config,
        geojson=geojson
    )

    # Run RL-based simulation
    print(f"\n{'='*80}")
    print(f"2/2: Running RL-BASED simulation...")
    print(f"{'='*80}\n")

    rl_output = f"{output_dir}/rl_based"
    os.makedirs(rl_output, exist_ok=True)

    rl_results = run_simulation_with_results(
        scenario=scenario,
        n_years=n_years,
        n_parcels=n_parcels,
        output_dir=rl_output,
        data_path=data_path,
        n_collectives=n_collectives,
        n_markets=n_markets,
        n_policies=n_policymakers,
        enable_multi_level=config.multilevel['enabled'] if config else True,
        rl_policy=rl_policy,  # RL-based
        config=config,
        geojson=geojson
    )

    # Convert ResultCollector to dict format
    rule_dict = rule_results.get_timeseries_summary()
    rl_dict = rl_results.get_timeseries_summary()

    # Generate comparison visualizations
    print(f"\n{'='*80}")
    print(f"GENERATING COMPARISON VISUALIZATIONS")
    print(f"{'='*80}\n")

    create_comparison_visualizations(
        rule_results=rule_dict,
        rl_results=rl_dict,
        scenario=scenario,
        output_dir=output_dir
    )

    # Generate comparison report
    create_comparison_report(
        rule_results=rule_dict,
        rl_results=rl_dict,
        scenario=scenario,
        output_path=f"{output_dir}/comparison_report.txt"
    )

    print(f"\n{'='*80}")
    print(f"✅ COMPARISON COMPLETE")
    print(f"{'='*80}")
    print(f"📊 Interactive charts: {output_dir}/comparison_dashboard.html")
    print(f"📄 Report:            {output_dir}/comparison_report.txt")
    print(f"{'='*80}\n")


def create_comparison_visualizations(
    rule_results: dict,
    rl_results: dict,
    scenario: str,
    output_dir: str
):
    """Generate comparison visualizations."""

    # Map scenario codes to user-friendly names
    scenario_names = {
        'rcp26': 'Optimistic (Low Warming ~2°C)',
        'rcp45': 'Moderate (Medium Warming ~3°C)',
        'rcp85': 'Pessimistic (High Warming ~4-5°C)'
    }
    scenario_display = scenario_names.get(scenario.lower(), scenario.upper())

    # Extract time series data
    rule_df = pd.DataFrame(rule_results['timeseries'])
    rl_df = pd.DataFrame(rl_results['timeseries'])

    years = rule_df['year'].values

    # Create subplots (2x2 grid)
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "Land-Use Distribution Over Time",
            "Economic Performance",
            "Sustainability Metrics",
            "Final Distribution (Last Year)"
        ],
        specs=[
            [{"type": "scatter"}, {"type": "scatter"}],
            [{"type": "scatter"}, {"type": "bar"}]
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.10
    )

    # shadcn-inspired color palette with STRONG contrast between Rule vs RL
    colors = {
        # Rule-based colors (DARK, saturated earth tones)
        'rule_wheat': '#c2410c',      # Orange-700 - very dark orange
        'rule_maize': '#a16207',      # Yellow-700 - dark golden brown
        'rule_solar': '#075985',      # Sky-700 - dark blue

        # RL colors (BRIGHT, light vibrant tones - clearly distinct)
        'rl_wheat': '#fdba74',        # Orange-300 - bright peachy orange
        'rl_maize': '#fde047',        # Yellow-300 - very bright yellow
        'rl_solar': '#7dd3fc',        # Sky-300 - bright cyan/light blue

        # Economic/other colors
        'rule_primary': '#16a34a',   # Green-600
        'rule_secondary': '#22c55e', # Green-500
        'rl_primary': '#2563eb',     # Blue-600
        'rl_secondary': '#60a5fa',   # Blue-400
        'diversity_rule': '#9333ea', # Purple-600
        'diversity_rl': '#ec4899'    # Pink-500
    }

    # 1. Land-Use Distribution - STACKED AREA CHART
    # Rule-based stacked area
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rule_df['pct_wheat'].values,
            name='Rule: WHEAT',
            mode='lines',
            line=dict(color=colors['rule_wheat'], width=2),
            stackgroup='rule',
            showlegend=True
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rule_df['pct_maize'].values,
            name='Rule: MAIZE',
            mode='lines',
            line=dict(color=colors['rule_maize'], width=2),
            stackgroup='rule',
            showlegend=True
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rule_df['pct_solar'].values,
            name='Rule: SOLAR',
            mode='lines',
            line=dict(color=colors['rule_solar'], width=2),
            stackgroup='rule',
            showlegend=True
        ),
        row=1, col=1
    )

    # RL stacked area
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rl_df['pct_wheat'].values,
            name='RL: WHEAT',
            mode='lines',
            line=dict(color=colors['rl_wheat'], width=2),
            stackgroup='rl',
            showlegend=True
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rl_df['pct_maize'].values,
            name='RL: MAIZE',
            mode='lines',
            line=dict(color=colors['rl_maize'], width=2),
            stackgroup='rl',
            showlegend=True
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rl_df['pct_solar'].values,
            name='RL: SOLAR',
            mode='lines',
            line=dict(color=colors['rl_solar'], width=2),
            stackgroup='rl',
            showlegend=True
        ),
        row=1, col=1
    )

    # 2. Economic Performance
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rule_df['total_income'].values,
            name='Rule: Income',
            mode='lines',
            line=dict(color=colors['rule_primary'], width=3),
            showlegend=True
        ),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rl_df['total_income'].values,
            name='RL: Income',
            mode='lines',
            line=dict(color=colors['rl_primary'], width=3, dash='dash'),
            showlegend=True
        ),
        row=1, col=2
    )

    fig.add_trace(
        go.Scatter(
            x=years,
            y=rule_df['total_profit'].values,
            name='Rule: Profit',
            mode='lines',
            line=dict(color=colors['rule_secondary'], width=2),
            showlegend=True
        ),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rl_df['total_profit'].values,
            name='RL: Profit',
            mode='lines',
            line=dict(color=colors['rl_secondary'], width=2, dash='dash'),
            showlegend=True
        ),
        row=1, col=2
    )

    # 3. Sustainability Metrics
    # Calculate diversity index (Shannon diversity)
    rule_diversity = []
    rl_diversity = []
    for i in range(len(years)):
        # Rule-based diversity
        rule_probs = [
            rule_df['pct_wheat'].values[i] / 100.0,
            rule_df['pct_maize'].values[i] / 100.0,
            rule_df['pct_solar'].values[i] / 100.0
        ]
        rule_probs = [p for p in rule_probs if p > 0]
        rule_div = -sum(p * np.log(p) for p in rule_probs) if rule_probs else 0
        rule_diversity.append(rule_div)

        # RL diversity
        rl_probs = [
            rl_df['pct_wheat'].values[i] / 100.0,
            rl_df['pct_maize'].values[i] / 100.0,
            rl_df['pct_solar'].values[i] / 100.0
        ]
        rl_probs = [p for p in rl_probs if p > 0]
        rl_div = -sum(p * np.log(p) for p in rl_probs) if rl_probs else 0
        rl_diversity.append(rl_div)

    fig.add_trace(
        go.Scatter(
            x=years,
            y=rule_diversity,
            name='Rule: Diversity',
            mode='lines',
            line=dict(color=colors['diversity_rule'], width=3),
            showlegend=True
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rl_diversity,
            name='RL: Diversity',
            mode='lines',
            line=dict(color=colors['diversity_rl'], width=3, dash='dash'),
            showlegend=True
        ),
        row=2, col=1
    )

    # 4. Final Distribution (bar chart)
    last_year_idx = -1
    categories = ['WHEAT', 'MAIZE', 'SOLAR']
    rule_final = [
        rule_df['pct_wheat'].values[last_year_idx],
        rule_df['pct_maize'].values[last_year_idx],
        rule_df['pct_solar'].values[last_year_idx]
    ]
    rl_final = [
        rl_df['pct_wheat'].values[last_year_idx],
        rl_df['pct_maize'].values[last_year_idx],
        rl_df['pct_solar'].values[last_year_idx]
    ]

    fig.add_trace(
        go.Bar(
            x=categories,
            y=rule_final,
            name='Rule-Based',
            marker=dict(color=colors['rule_primary']),
            showlegend=True
        ),
        row=2, col=2
    )
    fig.add_trace(
        go.Bar(
            x=categories,
            y=rl_final,
            name='RL-Based',
            marker=dict(color=colors['rl_primary']),
            showlegend=True
        ),
        row=2, col=2
    )

    # Update layout
    fig.update_xaxes(title_text="Year", row=1, col=1)
    fig.update_yaxes(title_text="Percentage (%)", row=1, col=1)

    fig.update_xaxes(title_text="Year", row=1, col=2)
    fig.update_yaxes(title_text="€ (Total)", row=1, col=2)

    fig.update_xaxes(title_text="Year", row=2, col=1)
    fig.update_yaxes(title_text="Shannon Diversity", row=2, col=1)

    fig.update_xaxes(title_text="Land Use", row=2, col=2)
    fig.update_yaxes(title_text="Percentage (%)", row=2, col=2)

    # Configure layout - vertical legend at top-right
    fig.update_layout(
        title=f"RL vs Rule-Based Comparison ({scenario_display})",
        height=800,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1.0,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor="rgba(0, 0, 0, 0.1)",
            borderwidth=1
        ),
        template="plotly_white",
        hovermode='x unified'
    )

    # Save
    output_path = f"{output_dir}/comparison_dashboard.html"
    fig.write_html(output_path)
    print(f"✅ Dashboard saved: {output_path}")


def create_comparison_report(
    rule_results: dict,
    rl_results: dict,
    scenario: str,
    output_path: str
):
    """Generate text comparison report."""

    # Map scenario codes to user-friendly names
    scenario_names = {
        'rcp26': 'Optimistic (Low Warming ~2°C)',
        'rcp45': 'Moderate (Medium Warming ~3°C)',
        'rcp85': 'Pessimistic (High Warming ~4-5°C)'
    }
    scenario_display = scenario_names.get(scenario.lower(), scenario.upper())

    rule_df = pd.DataFrame(rule_results['timeseries'])
    rl_df = pd.DataFrame(rl_results['timeseries'])

    # Calculate summary statistics
    rule_summary = rule_results.get('summary', {})
    rl_summary = rl_results.get('summary', {})

    # Final year distributions
    rule_final_wheat = rule_df['pct_wheat'].values[-1]
    rule_final_maize = rule_df['pct_maize'].values[-1]
    rule_final_solar = rule_df['pct_solar'].values[-1]

    rl_final_wheat = rl_df['pct_wheat'].values[-1]
    rl_final_maize = rl_df['pct_maize'].values[-1]
    rl_final_solar = rl_df['pct_solar'].values[-1]

    # Economic metrics
    rule_total_income = rule_df['total_income'].sum()
    rl_total_income = rl_df['total_income'].sum()
    income_diff_pct = ((rl_total_income - rule_total_income) / rule_total_income) * 100

    rule_total_profit = rule_df['total_profit'].sum()
    rl_total_profit = rl_df['total_profit'].sum()
    profit_diff_pct = ((rl_total_profit - rule_total_profit) / rule_total_profit) * 100

    # Diversity (mean Shannon diversity)
    def calc_diversity(row):
        probs = [row['pct_wheat']/100, row['pct_maize']/100, row['pct_solar']/100]
        probs = [p for p in probs if p > 0]
        return -sum(p * np.log(p) for p in probs) if probs else 0

    rule_mean_diversity = rule_df.apply(calc_diversity, axis=1).mean()
    rl_mean_diversity = rl_df.apply(calc_diversity, axis=1).mean()
    diversity_diff_pct = ((rl_mean_diversity - rule_mean_diversity) / rule_mean_diversity) * 100

    # Write report
    with open(output_path, 'w') as f:
        f.write("="*80 + "\n")
        f.write("RL vs RULE-BASED COMPARISON REPORT\n")
        f.write("="*80 + "\n\n")

        f.write(f"Scenario:  {scenario_display}\n")
        f.write(f"Duration:  {len(rule_df)} years ({rule_df['year'].values[0]} - {rule_df['year'].values[-1]})\n")
        f.write(f"Parcels:   {rule_summary.get('n_parcels', 'N/A')}\n\n")

        f.write("="*80 + "\n")
        f.write("FINAL LAND-USE DISTRIBUTION (Last Year)\n")
        f.write("="*80 + "\n\n")

        f.write(f"{'Method':<15} {'WHEAT':<15} {'MAIZE':<15} {'SOLAR':<15}\n")
        f.write("-"*60 + "\n")
        f.write(f"{'Rule-Based':<15} {rule_final_wheat:>12.1f}%  {rule_final_maize:>12.1f}%  {rule_final_solar:>12.1f}%\n")
        f.write(f"{'RL-Based':<15} {rl_final_wheat:>12.1f}%  {rl_final_maize:>12.1f}%  {rl_final_solar:>12.1f}%\n")
        f.write("-"*60 + "\n")
        f.write(f"{'Difference':<15} {rl_final_wheat - rule_final_wheat:>+12.1f}%  {rl_final_maize - rule_final_maize:>+12.1f}%  {rl_final_solar - rule_final_solar:>+12.1f}%\n\n")

        f.write("="*80 + "\n")
        f.write("ECONOMIC PERFORMANCE (Cumulative)\n")
        f.write("="*80 + "\n\n")

        f.write(f"{'Metric':<30} {'Rule-Based':<20} {'RL-Based':<20} {'Difference':<15}\n")
        f.write("-"*85 + "\n")
        f.write(f"{'Total Income':<30} €{rule_total_income:>15,.0f}  €{rl_total_income:>15,.0f}  {income_diff_pct:>+10.1f}%\n")
        f.write(f"{'Total Profit':<30} €{rule_total_profit:>15,.0f}  €{rl_total_profit:>15,.0f}  {profit_diff_pct:>+10.1f}%\n\n")

        f.write("="*80 + "\n")
        f.write("SUSTAINABILITY METRICS (Mean)\n")
        f.write("="*80 + "\n\n")

        f.write(f"{'Metric':<30} {'Rule-Based':<20} {'RL-Based':<20} {'Difference':<15}\n")
        f.write("-"*85 + "\n")
        f.write(f"{'Shannon Diversity':<30} {rule_mean_diversity:>18.3f}  {rl_mean_diversity:>18.3f}  {diversity_diff_pct:>+10.1f}%\n\n")

        f.write("="*80 + "\n")
        f.write("KEY INSIGHTS\n")
        f.write("="*80 + "\n\n")

        # Generate insights
        if abs(income_diff_pct) < 5:
            f.write(f"• Economic performance is similar (~{abs(income_diff_pct):.1f}% difference)\n")
        elif income_diff_pct > 0:
            f.write(f"• ✅ RL policy achieves {income_diff_pct:.1f}% HIGHER income than rule-based\n")
        else:
            f.write(f"• ⚠️  RL policy achieves {abs(income_diff_pct):.1f}% LOWER income than rule-based\n")

        if abs(diversity_diff_pct) < 5:
            f.write(f"• Diversity is similar (~{abs(diversity_diff_pct):.1f}% difference)\n")
        elif diversity_diff_pct > 0:
            f.write(f"• ✅ RL policy shows {diversity_diff_pct:.1f}% HIGHER diversity (better resilience)\n")
        else:
            f.write(f"• ⚠️  RL policy shows {abs(diversity_diff_pct):.1f}% LOWER diversity\n")

        # Solar adoption
        solar_diff = rl_final_solar - rule_final_solar
        if abs(solar_diff) < 5:
            f.write(f"• Solar adoption is similar (~{abs(solar_diff):.1f}% difference)\n")
        elif solar_diff > 0:
            f.write(f"• RL policy favors MORE solar PV (+{solar_diff:.1f}%)\n")
        else:
            f.write(f"• RL policy favors LESS solar PV ({solar_diff:.1f}%)\n")

        f.write("\n" + "="*80 + "\n")

    print(f"✅ Report saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare RL-based vs Rule-based land-use decisions"
    )
    parser.add_argument("--scenario", default=None, choices=["rcp26", "rcp45", "rcp85"],
                       help="Climate scenario (default: all scenarios)")
    parser.add_argument("--years", type=int, default=50,
                       help="Number of years to simulate (default: 50)")
    parser.add_argument("--parcels", type=int, default=30,
                       help="Number of land parcels (default: 30)")
    parser.add_argument("--collectives", type=int, default=None,
                       help="Number of farmer collectives (default: 2 from config)")
    parser.add_argument("--markets", type=int, default=None,
                       help="Number of commodity markets (default: 1 from config)")
    parser.add_argument("--policymakers", type=int, default=None,
                       help="Number of policymaker agents (default: 1 from config)")
    parser.add_argument("--rl-model", type=str, default="models/rl02/rl02_rcp45_final.zip",
                       help="Path to trained RL model")
    parser.add_argument("--output", type=str, default=None,
                       help="Output directory (default: use_cases/mlu/results/rl_comparison)")
    parser.add_argument("--config", type=str, default=None,
                       help="Config file path")
    parser.add_argument("--geojson", type=str, default=None,
                       help="GeoJSON string for spatial filtering (polygon)")
    parser.add_argument("--geojson-file", type=str, default=None,
                       help="Path to GeoJSON file for spatial filtering")

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Validate spatial filtering (REQUIRED - no defaults)
    if not (args.geojson or args.geojson_file):
        print(f"❌ ERROR: No spatial filter polygon provided!", file=sys.stderr)
        print(f"   Please draw a polygon on the map before running simulations.", file=sys.stderr)
        print(f"   Click 'Draw Polygon for Spatial Filtering' to select your area of interest.", file=sys.stderr)
        print(f"   OR specify exact coordinates", file=sys.stderr)
        sys.exit(1)

    # Load GeoJSON data (convert file path to dict for run_simulation_with_results)
    import json
    geojson_data = None
    if args.geojson_file:
        try:
            with open(args.geojson_file, 'r') as f:
                geojson_data = json.load(f)
            print(f"📍 Loaded GeoJSON from file: {args.geojson_file}")
        except Exception as e:
            print(f"❌ ERROR: Failed to load GeoJSON file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.geojson:
        try:
            geojson_data = json.loads(args.geojson)
            print(f"📍 Parsed GeoJSON string")
        except Exception as e:
            print(f"❌ ERROR: Failed to parse GeoJSON string: {e}", file=sys.stderr)
            sys.exit(1)

    # Verify RL model exists
    if not Path(args.rl_model).exists():
        print(f"❌ ERROR: RL model not found: {args.rl_model}")
        print(f"   Train a model first with: cd use_cases/mlu/rl && python train_rl02.py")
        sys.exit(1)

    # Determine scenarios to run
    scenarios = [args.scenario] if args.scenario else ["rcp26", "rcp45", "rcp85"]

    # Set default output path if not provided (use MLU results folder)
    if args.output is None:
        # Default: use_cases/mlu/results/rl_comparison
        mlu_dir = Path(__file__).parent.parent
        args.output = str(mlu_dir / "results" / "rl_comparison")

    # Create timestamped output directory to prevent overwriting
    import shutil
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output = Path(args.output)
    timestamped_output = base_output / timestamp
    timestamped_output.mkdir(parents=True, exist_ok=True)

    print(f"📁 Saving results to: {timestamped_output}/\n")

    # Run comparison for each scenario (wrapped in try/except for clean error messages)
    try:
        for scenario in scenarios:
            # Use scenario subdirectory inside timestamped folder
            scenario_output = str(timestamped_output / scenario)

            print(f"\n{'='*80}")
            print(f"Running comparison for {scenario.upper()}")
            print(f"{'='*80}\n")

            # Use CLI arguments if provided, otherwise fallback to config defaults
            n_collectives = args.collectives if args.collectives is not None else (config.multilevel['n_collectives'] if config else 2)
            n_markets = args.markets if args.markets is not None else (config.multilevel['n_markets'] if config else 1)
            n_policymakers_val = args.policymakers if args.policymakers is not None else (config.multilevel['n_policymakers'] if config else 1)

            run_comparison(
                scenario=scenario,
                n_years=args.years,
                n_parcels=args.parcels,
                rl_model_path=args.rl_model,
                data_path=config.data_path,
                output_dir=scenario_output,
                config=config,
                n_collectives=n_collectives,
                n_markets=n_markets,
                n_policymakers=n_policymakers_val,
                geojson=geojson_data
            )

        # Summary
        if len(scenarios) > 1:
            print(f"\n{'='*80}")
            print(f"✅ ALL SCENARIOS COMPLETE")
            print(f"{'='*80}")
            for scenario in scenarios:
                print(f"  {scenario.upper()}: {timestamped_output}/{scenario}/comparison_dashboard.html")
            print(f"{'='*80}\n")
        else:
            # Single scenario summary
            print(f"\n{'='*80}")
            print(f"✅ COMPARISON COMPLETE")
            print(f"{'='*80}")
            print(f"  {scenarios[0].upper()}: {timestamped_output}/{scenarios[0]}/comparison_dashboard.html")
            print(f"{'='*80}\n")

    except ValueError as e:
        # Catch user-friendly errors (like year out of range) and print cleanly without traceback
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Catch unexpected errors with a clean message
        print(f"❌ Unexpected error: {str(e)}", file=sys.stderr)
        sys.exit(1)
