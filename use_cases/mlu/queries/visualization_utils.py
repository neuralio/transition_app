"""
Visualization utilities for query mode.

Common visualization functions used across MLU queries.
"""

from pathlib import Path
from typing import Dict, List, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys

# Import scenario utilities for display names
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from scenario_utils import get_scenario_display_name


def create_parcel_map(
    parcels: List[Dict],
    title: str,
    output_file: str,
    category_colors: Optional[Dict] = None
) -> str:
    """
    Create interactive GIS map for categorized parcels.

    Args:
        parcels: List of parcel dicts with 'lat', 'lon', 'category'
        title: Map title
        output_file: Output HTML file path
        category_colors: Dict mapping category names to colors

    Returns:
        Path to generated HTML file
    """
    import folium

    if not parcels:
        return None

    # Default category colors
    if category_colors is None:
        category_colors = {
            'HIGH_AGRICULTURE': '#22c55e',  # Green
            'MODERATE_AGRICULTURE': '#84cc16',  # Lime
            'HIGH_SOLAR': '#f59e0b',  # Amber
            'MIXED_USE': '#3b82f6',  # Blue
            'LOW_SUITABILITY': '#ef4444'  # Red
        }

    # Calculate center
    lats = [p['lat'] for p in parcels]
    lons = [p['lon'] for p in parcels]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='OpenStreetMap',
        control_scale=True
    )

    # Add title
    title_html = f'''
    <div style="position: fixed; top: 10px; left: 50px; width: 400px; height: 50px;
                background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
                padding: 10px">
    <b>{title}</b>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Add parcels
    for p in parcels:
        color = category_colors.get(p.get('category', 'LOW_SUITABILITY'), '#gray')

        # Create popup text
        popup_text = f"""
        <b>Parcel {p.get('parcel_id', 'N/A')}</b><br>
        Category: {p.get('category', 'N/A')}<br>
        Location: ({p['lat']:.4f}, {p['lon']:.4f})<br>
        """

        if 'lusa_score' in p:
            popup_text += f"LUSA Score: {p['lusa_score']:.2f}<br>"
        if 'temperature' in p:
            popup_text += f"Temperature: {p['temperature']:.1f}°C<br>"
        if 'solar_radiation' in p:
            popup_text += f"Solar: {p['solar_radiation']:.1f} W/m²<br>"

        folium.CircleMarker(
            location=[p['lat'], p['lon']],
            radius=8,
            popup=folium.Popup(popup_text, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7
        ).add_to(m)

    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; right: 50px; width: 200px;
                background-color: white; border:2px solid grey; z-index:9999; font-size:12px;
                padding: 10px">
    <b>Categories</b><br>
    '''

    for category, color in category_colors.items():
        legend_html += f'''
        <i class="fa fa-circle" style="color:{color}"></i> {category.replace('_', ' ')}<br>
        '''

    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))

    # Save
    m.save(output_file)
    return str(Path(output_file).absolute())


def create_category_pie_chart(
    category_counts: Dict[str, int],
    title: str,
    output_file: str
) -> str:
    """
    Create pie chart for category distribution.

    Args:
        category_counts: Dict mapping category names to counts
        title: Chart title
        output_file: Output HTML file path

    Returns:
        Path to generated HTML file
    """
    fig = go.Figure(data=[go.Pie(
        labels=list(category_counts.keys()),
        values=list(category_counts.values()),
        hole=0.3
    )])

    fig.update_layout(
        title=title,
        width=800,
        height=600
    )

    fig.write_html(output_file)
    return str(Path(output_file).absolute())


def create_scenario_comparison_chart(
    scenario_data: Dict[str, Dict],
    variable_name: str,
    title: str,
    output_file: str
) -> str:
    """
    Create bar chart comparing scenarios.

    Args:
        scenario_data: Dict mapping scenario names to statistics
        variable_name: Which variable to compare (e.g., 'suitability', 'temperature')
        title: Chart title
        output_file: Output HTML file path

    Returns:
        Path to generated HTML file
    """
    scenarios = []
    means = []
    stds = []

    for scenario, data in scenario_data.items():
        if variable_name in data:
            scenarios.append(scenario)
            means.append(data[variable_name]['mean'])
            stds.append(data[variable_name]['std'])

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=scenarios,
        y=means,
        error_y=dict(type='data', array=stds),
        name='Mean ± Std'
    ))

    fig.update_layout(
        title=title,
        xaxis_title='Scenario',
        yaxis_title=variable_name.title(),
        width=900,
        height=600,
        showlegend=False
    )

    fig.write_html(output_file)
    return str(Path(output_file).absolute())


def create_historical_comparison_chart(
    historical_stats: Dict,
    future_stats: Dict,
    scenario: str,
    title: str,
    output_file: str
) -> str:
    """
    Create comparison chart for historical vs future.

    Args:
        historical_stats: Historical statistics
        future_stats: Future statistics
        scenario: Future scenario name
        title: Chart title
        output_file: Output HTML file path

    Returns:
        Path to generated HTML file
    """
    variables = list(historical_stats.keys())
    historical_values = [historical_stats[v]['mean'] for v in variables]
    future_values = [future_stats[v]['mean'] for v in variables]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Historical',
        x=variables,
        y=historical_values,
        marker_color='#3b82f6'
    ))

    scenario_display = get_scenario_display_name(scenario)
    fig.add_trace(go.Bar(
        name=f'Future ({scenario_display})',
        x=variables,
        y=future_values,
        marker_color='#f59e0b'
    ))

    fig.update_layout(
        title=title,
        xaxis_title='Variable',
        yaxis_title='Value',
        width=900,
        height=600,
        barmode='group'
    )

    fig.write_html(output_file)
    return str(Path(output_file).absolute())
