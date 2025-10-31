"""
MLU-05: Analyze Land Suitability Using Multi-Level ABM (Simplified Query)

User Story: "Displays dynamic outputs showing how agents adjust behaviors
based on changing conditions (e.g., parcels switch from solar to agriculture
when wheat prices rise)"

This is a SIMPLIFIED query that focuses on showing the DYNAMIC behavior:
- Time-series evolution of land use decisions
- Interactive year slider to see changes over time
- Price dynamics that influence decisions
- Decision switches (when and why parcels change crops)
"""

import sys
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from use_cases.mlu.scripts.run_mlu_simulation import run_simulation_with_results
from use_cases.mlu.utils.scenario_utils import get_scenario_display_name, get_scenario_short_name

# LLM imports for insight generation
from openai import OpenAI


def query_mlu_05(
    data_path: str,
    scenario: str,
    n_years: int = 10,
    n_parcels: int = 15,
    output_dir: str = None,
    enable_multi_level: bool = True,
    n_collectives: int = 2,
    n_markets: int = 1,
    n_policies: int = 1,
    geojson: dict = None,
    print_insights: bool = True,  # NEW: Control whether to print insights
    farmer_locations: list = None  # NEW (2025-10-21): User-specified farmer locations
):
    """
    MLU-05: Run multi-level ABM and create SIMPLIFIED dynamic visualizations.

    Focus: Show how agents change decisions over time (dynamic behavior)

    Args:
        data_path: Path to PILOT_THESSALONIKI_DATA
        scenario: Climate scenario (rcp26, rcp45, rcp85)
        n_years: Number of years to simulate
        n_parcels: Number of land parcels
        output_dir: Output directory
        enable_multi_level: Enable multi-level ABM
        n_collectives: Number of collectives
        n_markets: Number of markets
        n_policies: Number of policymakers
        geojson: Optional GeoJSON polygon for spatial filtering

    Returns:
        Dict with results and visualization paths
    """
    scenario_display = get_scenario_display_name(scenario)
    scenario_short = get_scenario_short_name(scenario)  # For chart titles

    print(f"\n{'='*80}")
    print(f"MLU-05: Multi-Level ABM - Dynamic Land Use Evolution")
    print(f"{'='*80}")
    print(f"Scenario: {scenario_display}")
    print(f"Duration: {n_years} years")
    print(f"Parcels: {n_parcels}")
    print(f"Multi-Level ABM: {'✅ ENABLED' if enable_multi_level else '❌ DISABLED'}")
    if enable_multi_level:
        print(f"  Levels: Individual ({n_parcels}) → Community ({n_collectives}) → Market ({n_markets}) → Policy ({n_policies})")
    print(f"{'='*80}\n")

    try:
        # Create output directory first - make it relative to use_cases/mlu/
        if output_dir:
            output_path = Path(output_dir)
        else:
            # Default: use_cases/mlu/results/mlu_05_{scenario}
            mlu_dir = Path(__file__).parent.parent
            output_path = mlu_dir / 'results' / f'mlu_05_{scenario.lower()}'
        output_path.mkdir(parents=True, exist_ok=True)

        # Run the simulation (pass output_dir WITHOUT scenario suffix since we already have mlu_05_{scenario})
        # Simulation will create: output_dir/scenario/ but we want: output_dir/
        # So we pass the query-specific path directly and modify simulation to not add scenario subdir
        print("🔄 Running multi-level ABM simulation...")
        collector = run_simulation_with_results(
            scenario=scenario,
            n_years=n_years,
            n_parcels=n_parcels,
            n_farmers=None,
            n_pv_installations=None,
            output_dir=str(output_path),  # Pass full path directly (mlu_05_rcp26)
            data_path=data_path,
            n_collectives=n_collectives,
            n_markets=n_markets,
            n_policies=n_policies,
            enable_multi_level=enable_multi_level,
            rl_policy=None,
            skip_scenario_subdir=True,  # NEW FLAG: don't add /scenario/ subdirectory
            geojson=geojson,  # Pass GeoJSON for spatial filtering
            farmer_locations=farmer_locations  # NEW (2025-10-21): User-specified farmer locations
        )

        # Display multi-level ABM initial characteristics
        if enable_multi_level and hasattr(collector, 'model') and collector.model:
            model = collector.model
            print(f"\n{'='*80}")
            print(f"MULTI-LEVEL ABM: INITIAL AGENT CHARACTERISTICS")
            print(f"{'='*80}\n")

            # Individual Level: Land Parcels
            if hasattr(model, 'land_parcel_agents') and model.land_parcel_agents and n_parcels <= 10:
                # Only show all parcels if there are 10 or fewer (to avoid console spam)
                print(f"🌾 Individual Level: Land Parcels (All {len(model.land_parcel_agents)}):")
                print("-" * 80)
                for parcel in model.land_parcel_agents:
                    print(f"\nParcel {parcel.unique_id}:")
                    print(f"   • Location: ({parcel.lat:.4f}, {parcel.lon:.4f})")
                    print(f"   • Land Size: {parcel.land_hectares:.1f} ha")
                    print(f"   • Initial Decision: {parcel.current_crop if parcel.current_crop else 'Will decide'}")
            elif hasattr(model, 'land_parcel_agents') and model.land_parcel_agents:
                print(f"🌾 Individual Level: {len(model.land_parcel_agents)} Land Parcels (see results for full details)")

            # Community Level: Collectives
            if hasattr(model, 'collective_agents') and model.collective_agents:
                print(f"\n🏘️  Community Level: Collectives ({len(model.collective_agents)}):")
                print("-" * 80)
                for collective in model.collective_agents:
                    print(f"\n{collective.region_name}:")
                    print(f"   • Members: {len(collective.members)} parcels")
                    print(f"   • Member IDs: {[p.unique_id for p in collective.members]}")

            # Market Level: Commodity Markets
            if hasattr(model, 'market_agents') and model.market_agents:
                print(f"\n🏪 Market Level: Commodity Markets ({len(model.market_agents)}):")
                print("-" * 80)
                for market in model.market_agents:
                    print(f"\n{market.market_name}:")
                    print(f"   • Crops Traded: {', '.join(market.crops)}")
                    print(f"   • Initial Prices: {', '.join([f'{crop}=€{price:.2f}/t' for crop, price in market.crop_prices.items()])}")

            # Policy Level: Policymakers
            if hasattr(model, 'policymaker_agents') and model.policymaker_agents:
                print(f"\n🏛️  Policy Level: Policymakers ({len(model.policymaker_agents)}):")
                print("-" * 80)
                for policymaker in model.policymaker_agents:
                    print(f"\n{policymaker.policy_name}:")
                    print(f"   • Policy Goals: {policymaker.policy_goals}")
                    if policymaker.subsidy_rates:
                        print(f"   • Subsidy Rates: {policymaker.subsidy_rates}")
                    if policymaker.price_floors:
                        print(f"   • Price Floors: {policymaker.price_floors}")

        print(f"\n📊 Creating dynamic visualizations...")
        viz_files = []

        # Use timestamped output path from collector for all visualizations
        if hasattr(collector, 'output_path') and collector.output_path:
            timestamped_output = Path(collector.output_path)
        else:
            # Fallback to output_path if collector doesn't have output_path attribute
            print(f"⚠️  Warning: collector.output_path not found, using base output_path")
            timestamped_output = output_path

        # Create visualizations subfolder (to match CCA/GCP pattern)
        viz_output = timestamped_output / "visualizations"
        viz_output.mkdir(parents=True, exist_ok=True)

        # ADD TEXT RESULTS FILE FIRST (so it appears at top in UI)
        results_txt = timestamped_output / f"{scenario}_results.txt"
        if results_txt.exists():
            viz_files.append(results_txt)

        # Extract time-series data
        years_data = []
        land_use_counts = {'WHEAT': [], 'MAIZE': [], 'SOLAR': []}
        wheat_prices = []
        maize_prices = []
        switches = []

        for snapshot in collector.spatial_snapshots:
            year = snapshot['year']
            years_data.append(year)

            # Count land use by crop
            parcels = snapshot['parcels']
            wheat_count = sum(1 for p in parcels if p['current_crop'] == 'WHEAT')
            maize_count = sum(1 for p in parcels if p['current_crop'] == 'MAIZE')
            solar_count = sum(1 for p in parcels if p.get('land_use') == 'solar_pv')

            land_use_counts['WHEAT'].append(wheat_count)
            land_use_counts['MAIZE'].append(maize_count)
            land_use_counts['SOLAR'].append(solar_count)

        # Get market data
        market_df = collector.get_market_dataframe()
        if not market_df.empty:
            wheat_prices = market_df['WHEAT_price'].tolist() if 'WHEAT_price' in market_df.columns else [250] * len(years_data)
            maize_prices = market_df['MAIZE_price'].tolist() if 'MAIZE_price' in market_df.columns else [200] * len(years_data)
        else:
            wheat_prices = [250] * len(years_data)
            maize_prices = [200] * len(years_data)

        # Calculate switches (how many parcels changed crop each year)
        # Also track TYPES of switches (from what to what)
        switch_types = {}  # Track all switch types across the simulation

        def get_land_use(parcel):
            """Get unified land use (crop or solar)"""
            if parcel.get('land_use') == 'solar_pv':
                return 'SOLAR'
            crop = parcel.get('current_crop')
            return crop if crop else 'UNASSIGNED'

        for i in range(1, len(collector.spatial_snapshots)):
            prev_parcels = {p.get('farmer_id', idx): get_land_use(p)
                          for idx, p in enumerate(collector.spatial_snapshots[i-1]['parcels'])}
            curr_parcels = {p.get('farmer_id', idx): get_land_use(p)
                          for idx, p in enumerate(collector.spatial_snapshots[i]['parcels'])}

            switch_count = 0
            for pid, curr_use in curr_parcels.items():
                if pid in prev_parcels:
                    prev_use = prev_parcels[pid]
                    # Only count switches if both states are assigned (skip UNASSIGNED)
                    if prev_use != curr_use and prev_use != 'UNASSIGNED' and curr_use != 'UNASSIGNED':
                        switch_count += 1
                        # Track the type of switch
                        switch_key = f"{prev_use}→{curr_use}"
                        switch_types[switch_key] = switch_types.get(switch_key, 0) + 1

            switches.append(switch_count)

        switches.insert(0, 0)  # No switches in year 0

        # VISUALIZATION 1: Land Use Evolution (Stacked Area Chart) - SHADCN STYLE
        print(f"   Creating land use evolution chart...")

        fig1 = go.Figure()

        # Shadcn color scheme
        colors = {
            'WHEAT': '#3b82f6',   # Blue
            'MAIZE': '#f97316',   # Orange
            'SOLAR': '#eab308'    # Yellow
        }

        fig1.add_trace(go.Scatter(
            x=years_data,
            y=land_use_counts['WHEAT'],
            mode='lines',
            name='WHEAT',
            line=dict(width=0),
            stackgroup='one',
            fillcolor=colors['WHEAT'],
            hovertemplate='<b>WHEAT</b><br>Year: %{x}<br>Parcels: %{y}<extra></extra>'
        ))

        fig1.add_trace(go.Scatter(
            x=years_data,
            y=land_use_counts['MAIZE'],
            mode='lines',
            name='MAIZE',
            line=dict(width=0),
            stackgroup='one',
            fillcolor=colors['MAIZE'],
            hovertemplate='<b>MAIZE</b><br>Year: %{x}<br>Parcels: %{y}<extra></extra>'
        ))

        fig1.add_trace(go.Scatter(
            x=years_data,
            y=land_use_counts['SOLAR'],
            mode='lines',
            name='SOLAR PV',
            line=dict(width=0),
            stackgroup='one',
            fillcolor=colors['SOLAR'],
            hovertemplate='<b>SOLAR PV</b><br>Year: %{x}<br>Parcels: %{y}<extra></extra>'
        ))

        fig1.update_layout(
            title=dict(
                text=f'Dynamic Land Use Evolution - {scenario_display}<br><sub>How parcels adapt to changing conditions over time</sub>',
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            xaxis=dict(
                title=dict(text='Year', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b'),
                gridcolor='#e2e8f0'
            ),
            yaxis=dict(
                title=dict(text='Number of Parcels', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b'),
                gridcolor='#e2e8f0'
            ),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            hovermode='x unified',
            width=1000,
            height=500,
            margin=dict(l=60, r=40, t=100, b=60),
            legend=dict(
                x=0.01,
                y=0.99,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#e2e8f0',
                borderwidth=1
            )
        )

        # Add scenario prefix to filename for clarity in frontend
        land_use_file = viz_output / f'{scenario_short}_land_use_evolution.html'
        fig1.write_html(str(land_use_file))
        viz_files.append(land_use_file)
        print(f"      ✅ {land_use_file.name}")

        # VISUALIZATION 2: Price Dynamics (Dual Axis) - SHADCN STYLE
        print(f"   Creating price dynamics chart...")

        fig2 = make_subplots(specs=[[{"secondary_y": False}]])

        fig2.add_trace(go.Scatter(
            x=years_data,
            y=wheat_prices,
            mode='lines+markers',
            name='WHEAT Price',
            line=dict(color=colors['WHEAT'], width=3),
            marker=dict(size=8),
            hovertemplate='<b>WHEAT</b><br>Year: %{x}<br>Price: €%{y:.0f}/ton<extra></extra>'
        ))

        fig2.add_trace(go.Scatter(
            x=years_data,
            y=maize_prices,
            mode='lines+markers',
            name='MAIZE Price',
            line=dict(color=colors['MAIZE'], width=3),
            marker=dict(size=8),
            hovertemplate='<b>MAIZE</b><br>Year: %{x}<br>Price: €%{y:.0f}/ton<extra></extra>'
        ))

        fig2.update_layout(
            title=dict(
                text=f'Market Price Dynamics - {scenario_display}<br><sub>Prices influence farmer decisions</sub>',
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            xaxis=dict(
                title=dict(text='Year', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b'),
                gridcolor='#e2e8f0'
            ),
            yaxis=dict(
                title=dict(text='Price (€/ton)', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b'),
                gridcolor='#e2e8f0'
            ),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            hovermode='x unified',
            width=1000,
            height=500,
            margin=dict(l=60, r=40, t=100, b=60),
            legend=dict(
                x=0.01,
                y=0.99,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#e2e8f0',
                borderwidth=1
            )
        )

        # Add scenario prefix to filename for clarity in frontend
        price_file = viz_output / f'{scenario_short}_price_dynamics.html'
        fig2.write_html(str(price_file))
        viz_files.append(price_file)
        print(f"      ✅ {price_file.name}")

        # VISUALIZATION 3: Decision Switches (Bar Chart) - SHADCN STYLE
        print(f"   Creating decision switches chart...")

        fig3 = go.Figure(data=[go.Bar(
            x=years_data,
            y=switches,
            marker=dict(
                color=switches,
                colorscale='RdYlGn_r',
                line=dict(color='#ffffff', width=1)
            ),
            text=switches,
            textposition='outside',
            textfont=dict(size=12, color='#0f172a', family='Inter, sans-serif'),
            hovertemplate='<b>Year %{x}</b><br>Parcels switched: %{y}<extra></extra>'
        )])

        fig3.update_layout(
            title=dict(
                text=f'Agent Decision Switches - {scenario_display}<br><sub>How many parcels changed crops each year</sub>',
                font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
            ),
            xaxis=dict(
                title=dict(text='Year', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b'),
                gridcolor='#e2e8f0'
            ),
            yaxis=dict(
                title=dict(text='Number of Parcels Switched', font=dict(size=14, color='#475569')),
                tickfont=dict(size=12, color='#64748b'),
                gridcolor='#e2e8f0'
            ),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            width=1000,
            height=500,
            margin=dict(l=60, r=40, t=100, b=60)
        )

        # Add scenario prefix to filename for clarity in frontend
        switches_file = viz_output / f'{scenario_short}_decision_switches.html'
        fig3.write_html(str(switches_file))
        viz_files.append(switches_file)
        print(f"      ✅ {switches_file.name}")

        # 4. Switch Types Breakdown (WHAT switches happened: WHEAT→SOLAR, etc.)
        print(f"   Creating switch types breakdown...")
        if switch_types:
            # Sort switch types by count (descending)
            sorted_switches = sorted(switch_types.items(), key=lambda x: x[1], reverse=True)
            switch_labels = [s[0] for s in sorted_switches]
            switch_counts = [s[1] for s in sorted_switches]

            # Color code by target (what they switched TO)
            colors_map = {
                'WHEAT': '#3b82f6',
                'MAIZE': '#f97316',
                'SOLAR': '#eab308'
            }
            bar_colors = []
            for switch_label in switch_labels:
                # Extract target from "SOURCE→TARGET"
                if '→' in switch_label:
                    target = switch_label.split('→')[1]
                    bar_colors.append(colors_map.get(target, '#64748b'))
                else:
                    bar_colors.append('#64748b')

            fig4 = go.Figure(data=[go.Bar(
                x=switch_labels,
                y=switch_counts,
                marker=dict(color=bar_colors),
                text=switch_counts,
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
            )])

            fig4.update_layout(
                title=dict(
                    text=f'Switch Types Breakdown - {scenario_short}<br><sub>What switches happened (e.g., WHEAT→SOLAR)</sub>',
                    font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
                ),
                xaxis=dict(
                    title=dict(text='Switch Type', font=dict(size=14, color='#475569')),
                    tickfont=dict(size=12, color='#64748b'),
                    tickangle=-45
                ),
                yaxis=dict(
                    title=dict(text='Number of Switches', font=dict(size=14, color='#475569')),
                    tickfont=dict(size=12, color='#64748b'),
                    gridcolor='#e2e8f0'
                ),
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                width=1000,
                height=600,
                margin=dict(l=60, r=40, t=100, b=120)
            )

            # Add scenario prefix to filename for clarity in frontend
            switch_types_file = viz_output / f'{scenario_short}_switch_types_breakdown.html'
            fig4.write_html(str(switch_types_file))
            viz_files.append(switch_types_file)
            print(f"      ✅ {switch_types_file.name}")
        else:
            print(f"      ⚠️  No switches occurred (all parcels kept their initial land use)")

        # Print summary
        print(f"\n{'='*80}")
        print(f"✅ MLU-05 COMPLETE")
        print(f"{'='*80}")
        print(f"Output: {timestamped_output}")
        print(f"\nDynamic Visualizations:")
        for f in viz_files:
            print(f"  - {f.name}")
        print(f"\nKey Insights:")
        print(f"  - Total parcels: {n_parcels}")
        print(f"  - Final land use: {land_use_counts['WHEAT'][-1]} WHEAT, {land_use_counts['MAIZE'][-1]} MAIZE, {land_use_counts['SOLAR'][-1]} SOLAR")
        print(f"  - Total decision switches over {n_years} years: {sum(switches)}")
        print(f"  - Final wheat price: €{wheat_prices[-1]:.0f}/ton")

        # Generate LLM-powered insights for each visualization (only if print_insights=True)
        insights = _generate_visualization_insights(
            land_use_counts=land_use_counts,
            wheat_prices=wheat_prices,
            maize_prices=maize_prices,
            switches=switches,
            switch_types=switch_types,
            n_years=n_years,
            n_parcels=n_parcels,
            scenario=scenario_display
        )

        if print_insights:
            print(f"\n📊 AI-Generated Insights:")
            for viz_name, insight in insights.items():
                print(f"\n  {viz_name}:")
                print(f"    {insight}")

        print(f"{'='*80}\n")

        return {
            'status': 'success',
            'scenario': scenario_display,
            'n_years': n_years,
            'n_parcels': n_parcels,
            'multi_level_enabled': enable_multi_level,
            'output_dir': str(timestamped_output.absolute()),  # Return timestamped path, not base path
            'visualizations': [str(f.absolute()) for f in viz_files],
            'total_switches': sum(switches),
            'switch_types': switch_types,  # Track what kind of switches happened
            'final_land_use': {
                'WHEAT': land_use_counts['WHEAT'][-1],
                'MAIZE': land_use_counts['MAIZE'][-1],
                'SOLAR': land_use_counts['SOLAR'][-1]
            },
            'ai_insights': insights  # Include AI-generated insights for frontend
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
            'message': error_msg,
            'scenario': scenario
        }
    except Exception as e:
        # Full traceback for unexpected errors (debugging)
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'message': str(e),
            'scenario': scenario
        }


def create_scenario_comparison(results_by_scenario: dict, output_dir: str = None):
    """
    Create comparison visualizations across all scenarios.

    Args:
        results_by_scenario: Dict mapping scenario name -> result dict
        output_dir: Output directory for comparison charts

    Returns:
        List of generated visualization files
    """
    if not results_by_scenario:
        return []

    # Create comparison output directory - make it relative to use_cases/mlu/
    if output_dir:
        output_path = Path(output_dir)
    else:
        mlu_dir = Path(__file__).parent.parent
        output_path = mlu_dir / 'results' / 'mlu_05_comparison'
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"📊 Creating Scenario Comparison Charts")
    print(f"{'='*80}")

    viz_files = []
    colors = {
        'rcp26': '#22c55e',  # Green (low emissions)
        'rcp45': '#f59e0b',  # Orange (medium)
        'rcp85': '#ef4444'   # Red (high emissions)
    }

    # Extract data from all scenarios
    scenarios_data = {}
    for scenario, result in results_by_scenario.items():
        if result.get('status') == 'success':
            scenarios_data[scenario] = result

    if not scenarios_data:
        print("   ⚠️  No successful scenarios to compare")
        return []

    # COMPARISON 1: Final Land Use Across Scenarios (Bar Chart)
    print(f"   Creating final land use comparison...")

    fig1 = go.Figure()

    categories = ['WHEAT', 'MAIZE', 'SOLAR']
    cat_colors = {
        'WHEAT': '#3b82f6',
        'MAIZE': '#f97316',
        'SOLAR': '#eab308'
    }

    for category in categories:
        counts = []
        scenario_labels = []
        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in scenarios_data:
                count = scenarios_data[scenario]['final_land_use'].get(category, 0)
                counts.append(count)
                scen_display = get_scenario_display_name(scenario)
                scenario_labels.append(scen_display)

        fig1.add_trace(go.Bar(
            name=category,
            x=scenario_labels,
            y=counts,
            marker=dict(color=cat_colors[category]),
            text=counts,
            textposition='outside',
            hovertemplate=f'<b>{category}</b><br>Count: %{{y}}<extra></extra>'
        ))

    fig1.update_layout(
        title=dict(
            text='Final Land Use Across Climate Scenarios<br><sub>How different climate pathways affect final land allocation</sub>',
            font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
        ),
        xaxis=dict(
            title=dict(text='Climate Scenario', font=dict(size=14, color='#475569')),
            tickfont=dict(size=12, color='#64748b')
        ),
        yaxis=dict(
            title=dict(text='Number of Parcels', font=dict(size=14, color='#475569')),
            tickfont=dict(size=12, color='#64748b'),
            gridcolor='#e2e8f0'
        ),
        barmode='group',
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        width=1000,
        height=600,
        margin=dict(l=60, r=40, t=100, b=60),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#e2e8f0',
            borderwidth=1
        )
    )

    final_land_use_file = output_path / 'final_land_use_comparison.html'
    fig1.write_html(str(final_land_use_file))
    viz_files.append(final_land_use_file)
    print(f"      ✅ {final_land_use_file.name}")

    # COMPARISON 2: Total Decision Switches Across Scenarios (Bar Chart)
    print(f"   Creating decision switches comparison...")

    fig2 = go.Figure(data=[go.Bar(
        x=[get_scenario_display_name(scenario) for scenario in ['rcp26', 'rcp45', 'rcp85'] if scenario in scenarios_data],
        y=[scenarios_data[s]['total_switches'] for s in ['rcp26', 'rcp45', 'rcp85'] if s in scenarios_data],
        marker=dict(
            color=[colors[s] for s in ['rcp26', 'rcp45', 'rcp85'] if s in scenarios_data],
            line=dict(color='#ffffff', width=2)
        ),
        text=[scenarios_data[s]['total_switches'] for s in ['rcp26', 'rcp45', 'rcp85'] if s in scenarios_data],
        textposition='outside',
        textfont=dict(size=14, color='#0f172a', family='Inter, sans-serif'),
        hovertemplate='<b>%{x}</b><br>Total switches: %{y}<extra></extra>'
    )])

    fig2.update_layout(
        title=dict(
            text='Total Decision Switches Across Scenarios<br><sub>Higher switches = more adaptation/volatility</sub>',
            font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
        ),
        xaxis=dict(
            title=dict(text='Climate Scenario', font=dict(size=14, color='#475569')),
            tickfont=dict(size=12, color='#64748b')
        ),
        yaxis=dict(
            title=dict(text='Total Switches Over Time', font=dict(size=14, color='#475569')),
            tickfont=dict(size=12, color='#64748b'),
            gridcolor='#e2e8f0'
        ),
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        width=1000,
        height=600,
        margin=dict(l=60, r=40, t=100, b=60)
    )

    switches_file = output_path / 'decision_switches_comparison.html'
    fig2.write_html(str(switches_file))
    viz_files.append(switches_file)
    print(f"      ✅ {switches_file.name}")

    # COMPARISON 3: Switch Types Breakdown (Stacked Bar Chart)
    print(f"   Creating switch types breakdown...")

    # Collect all unique switch types across scenarios
    all_switch_types = set()
    for scenario_data in scenarios_data.values():
        all_switch_types.update(scenario_data.get('switch_types', {}).keys())

    # Define colors for each switch type
    switch_type_colors = {
        'WHEAT→MAIZE': '#3b82f6',
        'WHEAT→SOLAR': '#eab308',
        'MAIZE→WHEAT': '#f97316',
        'MAIZE→SOLAR': '#eab308',
        'SOLAR→WHEAT': '#3b82f6',
        'SOLAR→MAIZE': '#f97316'
    }

    fig3 = go.Figure()

    # Create stacked bars for each switch type
    for switch_type in sorted(all_switch_types):
        counts = []
        scenario_labels = []
        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in scenarios_data:
                count = scenarios_data[scenario].get('switch_types', {}).get(switch_type, 0)
                counts.append(count)
                scen_display = get_scenario_display_name(scenario)
                scenario_labels.append(scen_display)

        fig3.add_trace(go.Bar(
            name=switch_type,
            x=scenario_labels,
            y=counts,
            marker=dict(color=switch_type_colors.get(switch_type, '#64748b')),
            text=counts,
            textposition='inside',
            textfont=dict(size=12, color='#ffffff', family='Inter, sans-serif'),
            hovertemplate=f'<b>{switch_type}</b><br>Count: %{{y}}<extra></extra>'
        ))

    fig3.update_layout(
        title=dict(
            text='Switch Types Breakdown Across Scenarios<br><sub>What kind of land use changes happened (e.g., WHEAT→SOLAR)</sub>',
            font=dict(size=20, color='#0f172a', family='Inter, sans-serif')
        ),
        xaxis=dict(
            title=dict(text='Climate Scenario', font=dict(size=14, color='#475569')),
            tickfont=dict(size=12, color='#64748b')
        ),
        yaxis=dict(
            title=dict(text='Number of Switches', font=dict(size=14, color='#475569')),
            tickfont=dict(size=12, color='#64748b'),
            gridcolor='#e2e8f0'
        ),
        barmode='stack',
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        width=1000,
        height=600,
        margin=dict(l=60, r=40, t=100, b=60),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#e2e8f0',
            borderwidth=1
        )
    )

    switch_types_file = output_path / 'switch_types_breakdown.html'
    fig3.write_html(str(switch_types_file))
    viz_files.append(switch_types_file)
    print(f"      ✅ {switch_types_file.name}")

    # Generate AI insights for comparison mode
    print(f"\n📊 AI-Generated Insights:")
    comparison_insights = _generate_comparison_insights(scenarios_data)
    for viz_name, insight in comparison_insights.items():
        print(f"\n  {viz_name}:")
        print(f"    {insight}")

    print(f"\n{'='*80}")
    print(f"✅ SCENARIO COMPARISON COMPLETE")
    print(f"{'='*80}")
    print(f"Output: {output_path}")
    print(f"Comparison visualizations:")
    for f in viz_files:
        print(f"  - {f.name}")
    print(f"{'='*80}\n")

    return viz_files


def _generate_comparison_insights(scenarios_data: dict):
    """
    Generate LLM-powered insights for COMPARISON MODE visualizations.
    This is called when running ALL scenarios (no scenario specified).

    Args:
        scenarios_data: Dict mapping scenario name -> result dict

    Returns:
        Dict of insights for each comparison visualization
    """
    try:
        from openai import OpenAI
        client = OpenAI()

        # Extract comparison data
        scenario_names = []
        final_wheat = []
        final_maize = []
        final_solar = []
        total_switches = []

        for scenario in ['rcp26', 'rcp45', 'rcp85']:
            if scenario in scenarios_data:
                scenario_names.append(get_scenario_display_name(scenario))
                final_wheat.append(scenarios_data[scenario]['final_land_use'].get('WHEAT', 0))
                final_maize.append(scenarios_data[scenario]['final_land_use'].get('MAIZE', 0))
                final_solar.append(scenarios_data[scenario]['final_land_use'].get('SOLAR', 0))
                total_switches.append(scenarios_data[scenario]['total_switches'])

        # Prepare summary
        data_summary = f"""
Multi-Scenario Comparison Results:
- Scenarios: {', '.join(scenario_names)}
- Final WHEAT: {dict(zip(scenario_names, final_wheat))}
- Final MAIZE: {dict(zip(scenario_names, final_maize))}
- Final SOLAR: {dict(zip(scenario_names, final_solar))}
- Total switches: {dict(zip(scenario_names, total_switches))}
"""

        insights = {}

        # 1. Final Land Use Comparison (Grouped Bar Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an agricultural economics expert analyzing climate scenario impacts on land use. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Final Land Use Comparison (Grouped Bar Chart) showing how WHEAT, MAIZE, and SOLAR adoption differs across {', '.join(scenario_names)}. What climate-driven patterns emerge? Which land use categories show the strongest climate sensitivity?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Final Land Use Comparison (Grouped Bar Chart)"] = response.choices[0].message.content.strip()

        # 2. Decision Switches Comparison (Bar Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a climate adaptation analyst studying behavioral volatility under different climate pathways. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Decision Switches Comparison (Bar Chart) showing total switches: {dict(zip(scenario_names, total_switches))}. How does adaptation volatility scale with climate severity? What does this reveal about agent decision-making under uncertainty?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Decision Switches Comparison (Bar Chart)"] = response.choices[0].message.content.strip()

        # 3. Switch Types Breakdown (Stacked Bar Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a land-use transition specialist analyzing pathway differences across climate scenarios. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Switch Types Breakdown (Stacked Bar Chart) showing specific transition patterns (WHEAT→SOLAR, MAIZE→WHEAT, etc.) across scenarios. Do climate-stressed scenarios show more abandonment of crops for solar? What adaptation strategies dominate in each climate pathway?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Switch Types Breakdown (Stacked Bar Chart)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate LLM insights: {e}")
        # Fallback generic insights
        return {
            "Final Land Use Comparison (Grouped Bar Chart)": f"Climate scenarios show divergent land use outcomes across WHEAT, MAIZE, and SOLAR categories, revealing differential climate sensitivity",
            "Decision Switches Comparison (Bar Chart)": f"Adaptation volatility varies across scenarios: {dict(zip(scenario_names, total_switches))}, indicating climate-dependent behavioral responses",
            "Switch Types Breakdown (Stacked Bar Chart)": f"Specific transition patterns (e.g., WHEAT→SOLAR, MAIZE→WHEAT) differ by climate pathway, showing distinct adaptation strategies under varying climate stress"
        }


def main():
    """CLI interface for simplified MLU-05."""
    import argparse

    parser = argparse.ArgumentParser(description="MLU-05: Simplified Multi-Level ABM Query")
    parser.add_argument("--data-path", required=True, help="Path to PILOT_THESSALONIKI_DATA")
    parser.add_argument("--scenario", required=True,
                       choices=["rcp26", "rcp45", "rcp85"],
                       help="Climate scenario")
    parser.add_argument("--years", type=int, required=True, help="Number of years")
    parser.add_argument("--parcels", type=int, required=True, help="Number of parcels")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--disable-multilevel", action="store_true",
                       help="Disable multi-level ABM")

    args = parser.parse_args()

    result = query_mlu_05(
        data_path=args.data_path,
        scenario=args.scenario,
        n_years=args.years,
        n_parcels=args.parcels,
        output_dir=args.output,
        enable_multi_level=not args.disable_multilevel
    )

    if result['status'] == 'error':
        print(f"\n❌ Error: {result['message']}")
        sys.exit(1)

    print(f"✅ Success!")


def _generate_visualization_insights(land_use_counts, wheat_prices, maize_prices, switches, switch_types, n_years, n_parcels, scenario):
    """Generate LLM-powered insights for each visualization."""
    try:
        client = OpenAI()

        # Prepare data summary for LLM
        data_summary = f"""
Simulation Results for {scenario}:
- Duration: {n_years} years
- Number of parcels: {n_parcels}
- Initial land use: {land_use_counts['WHEAT'][0]} WHEAT, {land_use_counts['MAIZE'][0]} MAIZE, {land_use_counts['SOLAR'][0]} SOLAR
- Final land use: {land_use_counts['WHEAT'][-1]} WHEAT, {land_use_counts['MAIZE'][-1]} MAIZE, {land_use_counts['SOLAR'][-1]} SOLAR
- Total decision switches: {sum(switches)}
- Switch types: {switch_types}
- Initial wheat price: €{wheat_prices[0]:.0f}/ton
- Final wheat price: €{wheat_prices[-1]:.0f}/ton
- Price range: €{min(wheat_prices):.0f}-€{max(wheat_prices):.0f}/ton
"""

        # Generate insights for each visualization
        insights = {}

        # 1. Land Use Evolution (Stacked Area Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an agricultural economics expert analyzing land use transitions in multi-level agent-based models. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Land Use Evolution Stacked Area Chart showing how {n_parcels} parcels changed from initial ({land_use_counts['WHEAT'][0]} WHEAT, {land_use_counts['MAIZE'][0]} MAIZE, {land_use_counts['SOLAR'][0]} SOLAR) to final ({land_use_counts['WHEAT'][-1]} WHEAT, {land_use_counts['MAIZE'][-1]} MAIZE, {land_use_counts['SOLAR'][-1]} SOLAR). What does this trajectory reveal about agent adaptation to climate and market conditions?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Land Use Evolution (Stacked Area Chart)"] = response.choices[0].message.content.strip()

        # 2. Price Dynamics (Dual Axis Line Chart)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a commodity market analyst studying agricultural price impacts on farmer decisions. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Price Dynamics Dual Axis Chart showing wheat prices ranging from €{min(wheat_prices):.0f}-€{max(wheat_prices):.0f}/ton. How do market price fluctuations drive the land use changes observed in the stacked area chart? What role does the market level play in multi-level ABM?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Price Dynamics (Dual Axis Chart)"] = response.choices[0].message.content.strip()

        # 3. Decision Switches (Bar Chart by Year)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an agricultural policy analyst studying farmer behavioral adaptation. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nAnalyze the Decision Switches Bar Chart showing {sum(switches)} total switches over {n_years} years. What does the temporal pattern of switching behavior reveal about agent decision-making? Are farmers rapidly adapting or showing path dependency?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Decision Switches Over Time (Bar Chart)"] = response.choices[0].message.content.strip()

        # 4. Switch Types Breakdown (Bar Chart of Transitions)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a land-use transition specialist analyzing agent behavior patterns. Provide detailed, actionable insights in 2-3 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nInterpret the Switch Types Breakdown Chart showing specific transitions (e.g., WHEAT→SOLAR, MAIZE→WHEAT). What do the most common switch types reveal about the economic drivers and climate adaptation strategies? Are farmers abandoning crops for solar, or optimizing within agriculture?"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        insights["Switch Types Breakdown (Transition Chart)"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate LLM insights: {e}")
        total_switches = sum(switches)
        return {
            "Land Use Evolution (Stacked Area Chart)": f"Parcels transitioned from initial mix ({land_use_counts['WHEAT'][0]} WHEAT, {land_use_counts['MAIZE'][0]} MAIZE, {land_use_counts['SOLAR'][0]} SOLAR) to final state ({land_use_counts['WHEAT'][-1]} WHEAT, {land_use_counts['MAIZE'][-1]} MAIZE, {land_use_counts['SOLAR'][-1]} SOLAR), showing agent convergence based on suitability and market signals",
            "Price Dynamics (Dual Axis Chart)": f"Wheat prices varied from €{min(wheat_prices):.0f} to €{max(wheat_prices):.0f}/ton, with market fluctuations driving crop selection decisions through multi-level price signals",
            "Decision Switches Over Time (Bar Chart)": f"Total of {total_switches} switches occurred over {n_years} years, indicating {'high' if total_switches > n_parcels else 'moderate' if total_switches > n_parcels/2 else 'low'} behavioral adaptation volatility",
            "Switch Types Breakdown (Transition Chart)": f"Specific transition patterns {switch_types} reveal dominant adaptation pathways, showing whether farmers optimize within agriculture or diversify into solar PV"
        }


if __name__ == "__main__":
    main()
