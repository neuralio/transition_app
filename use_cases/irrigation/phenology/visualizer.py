"""
Phenology Visualization Module

Creates time-series charts for NDVI/NDWI evolution.
Implements IRR-US-01 phenology visualization requirements.
"""

from pathlib import Path
from typing import List, Dict
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class PhenologyVisualizer:
    """
    Creates interactive phenology visualizations.

    Generates time-series charts showing NDVI/NDWI evolution
    with pattern annotations.
    """

    def __init__(self):
        """Initialize visualizer."""
        pass

    def create_time_series_chart(
        self,
        parcels: List[Dict],
        dates: List[str],
        output_path: Path,
        max_parcels_to_plot: int = 10
    ) -> str:
        """
        Create NDVI/NDWI time-series chart.

        Args:
            parcels: List of parcel dictionaries with time-series data
            dates: List of date labels
            output_path: Path to save HTML chart
            max_parcels_to_plot: Maximum number of parcels to plot (default: 10)

        Returns:
            Path to saved HTML file
        """
        # Create subplots (NDVI on top, NDWI on bottom)
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('NDVI Evolution', 'NDWI Evolution'),
            vertical_spacing=0.12,
            row_heights=[0.5, 0.5]
        )

        # Color map for temporal patterns
        pattern_colors = {
            'harvested_crop': '#2ecc71',  # Green
            'truly_fallow': '#95a5a6',  # Gray
            'irrigated_flooded': '#3498db',  # Blue
            'vegetated': '#27ae60',  # Dark green
            'unknown': '#e74c3c',  # Red
            'insufficient_data': '#7f8c8d'  # Dark gray
        }

        # Plot up to max_parcels_to_plot parcels
        n_to_plot = min(len(parcels), max_parcels_to_plot)

        for i, parcel in enumerate(parcels[:n_to_plot]):
            ndvi_series = parcel.get('ndvi_series', [])
            ndwi_series = parcel.get('ndwi_series', [])
            pattern = parcel.get('temporal_pattern', 'unknown')
            parcel_id = parcel.get('parcel_id', i + 1)

            color = pattern_colors.get(pattern, '#e74c3c')

            # NDVI line
            fig.add_trace(
                go.Scatter(
                    x=dates[:len(ndvi_series)],
                    y=ndvi_series,
                    mode='lines+markers',
                    name=f'Parcel {parcel_id} ({pattern})',
                    line=dict(color=color, width=2),
                    marker=dict(size=6),
                    legendgroup=f'p{parcel_id}',
                    showlegend=True
                ),
                row=1, col=1
            )

            # NDWI line (if available)
            if ndwi_series and any(v is not None for v in ndwi_series):
                fig.add_trace(
                    go.Scatter(
                        x=dates[:len(ndwi_series)],
                        y=ndwi_series,
                        mode='lines+markers',
                        name=f'Parcel {parcel_id}',
                        line=dict(color=color, width=2),
                        marker=dict(size=6),
                        legendgroup=f'p{parcel_id}',
                        showlegend=False
                    ),
                    row=2, col=1
                )

        # Add threshold lines
        # NDVI thresholds
        fig.add_hline(
            y=0.6, line_dash="dash", line_color="green",
            annotation_text="Harvested crop threshold (max NDVI > 0.6)",
            row=1, col=1
        )
        fig.add_hline(
            y=0.3, line_dash="dash", line_color="gray",
            annotation_text="Fallow threshold (max NDVI < 0.3)",
            row=1, col=1
        )
        fig.add_hline(
            y=0.2, line_dash="dash", line_color="red",
            annotation_text="Bare soil threshold (end NDVI < 0.2)",
            row=1, col=1
        )

        # NDWI flooding threshold
        fig.add_hline(
            y=0.0, line_dash="dash", line_color="blue",
            annotation_text="Flooding threshold (NDWI > 0)",
            row=2, col=1
        )

        # Update axes
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="NDVI", range=[-0.2, 1.0], row=1, col=1)
        fig.update_yaxes(title_text="NDWI", range=[-0.5, 0.5], row=2, col=1)

        # Update layout
        fig.update_layout(
            title=f"Temporal Phenology Analysis (showing {n_to_plot}/{len(parcels)} parcels)",
            height=800,
            template="plotly_white",
            hovermode='x unified'
        )

        # Save
        fig.write_html(str(output_path))
        return str(output_path)

    def create_pattern_summary_chart(
        self,
        parcels: List[Dict],
        output_path: Path
    ) -> str:
        """
        Create bar chart summarizing temporal pattern distribution.

        Args:
            parcels: List of parcel dictionaries
            output_path: Path to save HTML chart

        Returns:
            Path to saved HTML file
        """
        # Count patterns
        pattern_counts = {}
        for parcel in parcels:
            pattern = parcel.get('temporal_pattern', 'unknown')
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        # Create bar chart
        patterns = list(pattern_counts.keys())
        counts = [pattern_counts[p] for p in patterns]

        # Color map
        pattern_colors_map = {
            'harvested_crop': '#2ecc71',
            'truly_fallow': '#95a5a6',
            'irrigated_flooded': '#3498db',
            'vegetated': '#27ae60',
            'unknown': '#e74c3c',
            'insufficient_data': '#7f8c8d'
        }
        colors = [pattern_colors_map.get(p, '#e74c3c') for p in patterns]

        fig = go.Figure(data=[
            go.Bar(
                x=patterns,
                y=counts,
                marker_color=colors,
                text=counts,
                textposition='auto'
            )
        ])

        fig.update_layout(
            title="Temporal Pattern Distribution",
            xaxis_title="Pattern",
            yaxis_title="Number of Parcels",
            template="plotly_white",
            height=500
        )

        fig.write_html(str(output_path))
        return str(output_path)
