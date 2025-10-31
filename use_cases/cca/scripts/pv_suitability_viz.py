"""
PV Suitability Visualization for CCA-04

Generates visualizations showing which land parcels are most suitable for PV installations.

Per CCA-04 acceptance criteria:
- "Users should be able to visualize which land parcels are most suitable"
- "The system should provide a suitability score for each parcel of land"
"""

from pathlib import Path
import sys
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from folium import plugins
from global_land_mask import globe

# Import scenario utilities for display names
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from scenario_utils import get_scenario_display_name


def generate_pv_suitability_visualizations(model, scenario: str, output_dir: str) -> dict:
    """
    Generate PV suitability visualizations for CCA-04.

    Creates:
    1. Interactive map showing parcel suitability (color-coded)
    2. Suitability ranking table (sortable)
    3. Suitability score distribution chart

    Args:
        model: LandUseModel with farmer agents and PV developers
        scenario: Climate scenario (rcp26, rcp45, rcp85)
        output_dir: Output directory for visualizations

    Returns:
        Dict mapping visualization type to file path
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get user-friendly display name for scenario
    scenario_display = get_scenario_display_name(scenario, use_case="cca")

    viz_files = {}

    # Collect suitability data for all parcels
    parcel_data = []

    # Build index of actual installations for fast lookup
    installation_by_farmer = {}
    for pv_dev in model.pv_developer_agents:
        for installation in pv_dev.pv_installations:
            installation_by_farmer[installation['farmer_id']] = installation

    for farmer in model.farmer_agents:
        # Get PV developer to evaluate suitability
        if model.pv_developer_agents:
            pv_dev = model.pv_developer_agents[0]

            # Check if this farmer has an actual installation
            actual_installation = installation_by_farmer.get(farmer.unique_id)

            # Get suitability metrics for this location (needed for all parcels)
            suitability = pv_dev.evaluate_location_suitability(
                farmer.lat, farmer.lon, model.start_year
            )

            # Use UNCAPPED capacity factor for suitability score (shows differentiation)
            suitability_score_display = suitability.get('capacity_factor_uncapped', suitability['capacity_factor'])

            if actual_installation:
                # USE ACTUAL INSTALLATION DATA (not recalculated!)
                # Calculate payback from actual ROI
                if actual_installation['roi'] > 0 and actual_installation['annual_profit'] > 0:
                    # Payback = installation cost / annual profit
                    # We don't have installation cost stored, so estimate from ROI
                    # ROI = (annual_profit * lifetime - cost) / cost
                    # Solve for payback ≈ 1 / (ROI / lifetime + 1)
                    payback = pv_dev.pv_lifetime_years / (actual_installation['roi'] + 1)
                else:
                    payback = float('inf')

                parcel_data.append({
                    'farmer_id': farmer.unique_id,
                    'lat': actual_installation['location'][0],
                    'lon': actual_installation['location'][1],
                    'land_hectares': farmer.land_hectares,
                    'solar_radiation': actual_installation['solar_radiation'],
                    'capacity_factor': actual_installation['capacity_factor'],
                    'suitability_score': suitability_score_display,  # ✅ Use UNCAPPED CF
                    'capacity_kw': actual_installation['capacity_kw'],
                    'roi': actual_installation['roi'],  # ✅ USE ACTUAL ROI FROM INSTALLATION!
                    'feasible': True,  # Was installed, so was feasible
                    'has_pv': farmer.has_pv_installation,
                    'payback_period': payback,
                    'status': 'Installed'  # Has PV installation
                })
            else:
                # No installation - SHOW WHY IT WASN'T CHOSEN
                # Use the PV developer that would evaluate this parcel
                # Calculate what the ROI WOULD HAVE BEEN during decision time

                # Calculate ROI using CURRENT policy settings (approximation)
                # Skip budget check since we're just visualizing potential, not making actual decisions
                roi_analysis = pv_dev.calculate_roi(
                    land_hectares=farmer.land_hectares * 0.2,
                    suitability_metrics=suitability,
                    farmer_id=farmer.unique_id,
                    skip_budget_check=True  # Don't fail due to depleted budget
                )

                # Determine why no installation was made
                # Three categories:
                # 1. "Installed" - Has PV installation
                # 2. "Budget Constrained" - Economically feasible but companies ran out of money
                # 3. "Infeasible" - Not economically viable (ROI too low or payback too long)

                is_feasible = roi_analysis['feasible']

                # If feasible but not installed → Budget Constrained
                # If not feasible and not installed → Infeasible
                status = "Budget Constrained" if is_feasible else "Infeasible"

                parcel_data.append({
                    'farmer_id': farmer.unique_id,
                    'lat': farmer.lat,
                    'lon': farmer.lon,
                    'land_hectares': farmer.land_hectares,
                    'solar_radiation': suitability['solar_radiation'],
                    'capacity_factor': suitability['capacity_factor'],
                    'suitability_score': suitability_score_display,  # ✅ Use UNCAPPED CF
                    'capacity_kw': roi_analysis['capacity_kw'],
                    'roi': roi_analysis['roi'],  # Calculated with current settings
                    'feasible': is_feasible,  # Economic feasibility
                    'has_pv': farmer.has_pv_installation,
                    'payback_period': roi_analysis.get('payback_period', float('inf')),
                    'status': status  # Why no installation: "Budget Constrained" or "Infeasible"
                })

    if not parcel_data:
        print("⚠️  No parcel data available for visualization")
        return {}

    # Sort by suitability score (best first)
    parcel_data_sorted = sorted(parcel_data, key=lambda x: x['suitability_score'], reverse=True)

    # 1. INTERACTIVE MAP - Color-coded by suitability
    print("   Creating interactive suitability map...")
    map_file = _create_suitability_map(parcel_data, scenario, output_path, scenario_display)
    if map_file:
        viz_files['suitability_map'] = str(map_file)

    # 2. SUITABILITY RANKING TABLE
    print("   Creating suitability ranking table...")
    table_file = _create_suitability_table(parcel_data_sorted, scenario, output_path, scenario_display)
    if table_file:
        viz_files['suitability_table'] = str(table_file)

    # 3. SUITABILITY DISTRIBUTION CHARTS
    print("   Creating suitability distribution charts...")
    charts_file = _create_suitability_charts(parcel_data, scenario, output_path, scenario_display)
    if charts_file:
        viz_files['suitability_charts'] = str(charts_file)

    return viz_files


def _create_suitability_map(parcel_data, scenario, output_path, scenario_display=None):
    """Create Folium map showing parcel suitability with color coding."""
    if not parcel_data:
        return None

    # Calculate map center
    avg_lat = sum(p['lat'] for p in parcel_data) / len(parcel_data)
    avg_lon = sum(p['lon'] for p in parcel_data) / len(parcel_data)

    # Create map
    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=10,
        tiles='OpenStreetMap'
    )

    # Add title with 3-way status legend
    display_name = scenario_display if scenario_display else scenario.upper()
    title_html = f'''
        <div style="position: fixed;
                    top: 10px; left: 50px; width: 450px; height: 110px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:14px; padding: 10px">
        <b>PV Suitability Map - {display_name}</b><br>
        🟢 Green = Installed (PV installed)<br>
        🟡 Yellow = Budget Constrained (feasible but not funded)<br>
        🔴 Red = Infeasible (ROI < 50% or payback > 10 years)
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Add parcels with color coding based on 3-way status
    for parcel in parcel_data:
        # Skip if location is in the sea
        if not globe.is_land(parcel['lat'], parcel['lon']):
            continue

        # Color based on 3-way status
        status = parcel['status']
        if status == 'Installed':
            color = 'green'
            status_emoji = '🟢'
        elif status == 'Budget Constrained':
            color = 'orange'  # Yellow was requested, but orange is more visible
            status_emoji = '🟡'
        else:  # Infeasible
            color = 'red'
            status_emoji = '🔴'

        # Popup with detailed info
        popup_html = f"""
        <b>Parcel: {parcel['farmer_id']}</b><br>
        <b>Status: {status_emoji} {status}</b><br>
        {'✅ PV Installed' if parcel['has_pv'] else '⬜ No PV'}<br>
        <hr>
        <b>Suitability Metrics:</b><br>
        Solar Radiation: {parcel['solar_radiation']:.2f} kWh/m²/day<br>
        Capacity Factor: {parcel['capacity_factor']:.1%}<br>
        Suitability Score: {parcel['suitability_score']:.3f}<br>
        <hr>
        <b>Economic Metrics:</b><br>
        PV Capacity: {parcel['capacity_kw']:.0f} kW<br>
        ROI: {parcel['roi']:.1%}<br>
        Payback: {parcel['payback_period']:.1f} years<br>
        Economic Viability: {'Yes' if parcel['feasible'] else 'No'}
        """

        folium.CircleMarker(
            location=[parcel['lat'], parcel['lon']],
            radius=8,
            popup=folium.Popup(popup_html, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(m)

    # Save map
    map_file = output_path / f"pv_suitability_map_{scenario}.html"
    m.save(str(map_file))
    return map_file


def _create_suitability_table(parcel_data_sorted, scenario, output_path, scenario_display=None):
    """Create interactive HTML table with parcel suitability rankings."""
    if not parcel_data_sorted:
        return None

    # Create table data with 3-way status
    headers = [
        'Rank', 'Parcel ID', 'Status', 'Suitability Score', 'Solar (kWh/m²/day)',
        'Capacity Factor', 'PV Capacity (kW)', 'ROI', 'Payback (years)'
    ]

    rows = []
    for rank, parcel in enumerate(parcel_data_sorted, 1):
        # Add emoji to status for visual clarity
        status = parcel['status']
        if status == 'Installed':
            status_display = '🟢 Installed'
        elif status == 'Budget Constrained':
            status_display = '🟡 Budget Constrained'
        else:
            status_display = '🔴 Infeasible'

        rows.append([
            rank,
            parcel['farmer_id'],
            status_display,
            f"{parcel['suitability_score']:.3f}",
            f"{parcel['solar_radiation']:.2f}",
            f"{parcel['capacity_factor']:.1%}",
            f"{parcel['capacity_kw']:.0f}",
            f"{parcel['roi']:.1%}",
            f"{parcel['payback_period']:.1f}"
        ])

    # Create Plotly table
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=headers,
            fill_color='#3498db',
            font=dict(color='white', size=12),
            align='left'
        ),
        cells=dict(
            values=list(zip(*rows)),  # Transpose rows to columns
            fill_color=[['#ecf0f1' if i % 2 == 0 else 'white' for i in range(len(rows))]],
            align='left',
            font=dict(size=11),
            height=25
        )
    )])

    display_name = scenario_display if scenario_display else scenario.upper()
    fig.update_layout(
        title=f"PV Suitability Rankings - {display_name} (Sorted by Suitability Score)",
        height=600
    )

    table_file = output_path / f"pv_suitability_table_{scenario}.html"
    fig.write_html(str(table_file))
    return table_file


def _create_suitability_charts(parcel_data, scenario, output_path, scenario_display=None):
    """Create charts showing suitability score distribution and metrics."""
    if not parcel_data:
        return None

    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Suitability Score Distribution',
            'Solar Radiation vs Capacity Factor',
            'ROI Distribution',
            'Parcel Status Distribution'
        ),
        specs=[
            [{"type": "histogram"}, {"type": "scatter"}],
            [{"type": "histogram"}, {"type": "bar"}]
        ]
    )

    # 1. Suitability Score Distribution
    fig.add_trace(
        go.Histogram(
            x=[p['suitability_score'] for p in parcel_data],
            nbinsx=10,
            name='Suitability Score',
            marker_color='#2ecc71'
        ),
        row=1, col=1
    )

    # 2. Solar Radiation vs Capacity Factor
    fig.add_trace(
        go.Scatter(
            x=[p['solar_radiation'] for p in parcel_data],
            y=[p['capacity_factor'] for p in parcel_data],
            mode='markers',
            marker=dict(
                size=10,
                color=[p['roi'] for p in parcel_data],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="ROI")
            ),
            text=[p['farmer_id'] for p in parcel_data],
            name='Parcels'
        ),
        row=1, col=2
    )

    # 3. ROI Distribution
    fig.add_trace(
        go.Histogram(
            x=[p['roi'] * 100 for p in parcel_data],  # Convert to percentage
            nbinsx=10,
            name='ROI (%)',
            marker_color='#f39c12'
        ),
        row=2, col=1
    )

    # 4. 3-Way Status Distribution (Bar Chart)
    installed_count = sum(1 for p in parcel_data if p['status'] == 'Installed')
    budget_constrained_count = sum(1 for p in parcel_data if p['status'] == 'Budget Constrained')
    infeasible_count = sum(1 for p in parcel_data if p['status'] == 'Infeasible')

    fig.add_trace(
        go.Bar(
            x=['🟢 Installed', '🟡 Budget Constrained', '🔴 Infeasible'],
            y=[installed_count, budget_constrained_count, infeasible_count],
            marker=dict(color=['#2ecc71', '#f39c12', '#e74c3c']),  # Green, Orange, Red
            text=[f"{installed_count}<br>({installed_count/len(parcel_data)*100:.1f}%)",
                  f"{budget_constrained_count}<br>({budget_constrained_count/len(parcel_data)*100:.1f}%)",
                  f"{infeasible_count}<br>({infeasible_count/len(parcel_data)*100:.1f}%)"],
            textposition='auto',
            name='Parcel Count'
        ),
        row=2, col=2
    )

    # Update layout
    fig.update_xaxes(title_text="Suitability Score", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_xaxes(title_text="Solar Radiation (kWh/m²/day)", row=1, col=2)
    fig.update_yaxes(title_text="Capacity Factor", row=1, col=2)
    fig.update_xaxes(title_text="ROI (%)", row=2, col=1)
    fig.update_yaxes(title_text="Count", row=2, col=1)
    fig.update_xaxes(title_text="Parcel Status", row=2, col=2)
    fig.update_yaxes(title_text="Number of Parcels", row=2, col=2)

    display_name = scenario_display if scenario_display else scenario.upper()
    fig.update_layout(
        title_text=f"PV Suitability Analysis - {display_name}",
        showlegend=False,
        height=800
    )

    charts_file = output_path / f"pv_suitability_charts_{scenario}.html"
    fig.write_html(str(charts_file))
    return charts_file
