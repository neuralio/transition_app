"""
Historical Benchmarking - Compare historical vs future scenarios

Implements MLU-07 user story:
- View historical data alongside current land-use suitability scores
- Benchmark current and future land suitability against past conditions
- Highlight changes over time
"""

import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path


def load_scenario_results(results_dir: str, scenario: str):
    """Load results from a scenario simulation (ensemble or single run)."""
    # First, check for ensemble stats (preferred for benchmark mode)
    ensemble_stats_path = Path(results_dir) / f"{scenario}_ensemble_stats.json"
    if ensemble_stats_path.exists():
        with open(ensemble_stats_path, 'r') as f:
            stats = json.load(f)

        # Convert stats_by_year to timeseries format
        stats_by_year = stats["stats_by_year"]
        years = sorted([int(y) for y in stats_by_year.keys()])

        timeseries = {
            "years": years,
            "wheat_count": [stats_by_year[str(y)]["wheat"]["mean"] for y in years],
            "maize_count": [stats_by_year[str(y)]["maize"]["mean"] for y in years],
            "solar_count": [stats_by_year[str(y)]["solar"]["mean"] for y in years],
            "total_income": [stats_by_year[str(y)]["income"]["mean"] for y in years],
            "total_production": [stats_by_year[str(y)]["wheat"]["mean"] + stats_by_year[str(y)]["maize"]["mean"] for y in years],
            "total_energy": [stats_by_year[str(y)]["energy"]["mean"] for y in years]
        }

        # Get final year metrics
        final_year = str(max(years))
        final_stats = stats_by_year[final_year]

        final_metrics = {
            "wheat_count": final_stats["wheat"]["mean"],
            "maize_count": final_stats["maize"]["mean"],
            "solar_count": final_stats["solar"]["mean"],
            "total_income": final_stats["income"]["mean"],
            "total_production": final_stats["wheat"]["mean"] + final_stats["maize"]["mean"]
        }

        return {
            "timeseries": timeseries,
            "final_metrics": final_metrics
        }

    # Fall back to single simulation results
    results_path = Path(results_dir) / scenario / f"{scenario}_results.json"
    if not results_path.exists():
        return None

    with open(results_path, 'r') as f:
        data = json.load(f)

    # Convert farmer_data to timeseries
    if "farmer_data" in data:
        farmer_data = data["farmer_data"]

        # Group by year
        years_data = {}
        for entry in farmer_data:
            year = entry["year"]
            if year not in years_data:
                years_data[year] = []
            years_data[year].append(entry)

        # Calculate aggregates per year
        timeseries = {
            "years": sorted(years_data.keys()),
            "wheat_count": [],
            "maize_count": [],
            "solar_count": [],
            "total_income": [],
            "total_production": [],
            "total_energy": []
        }

        final_metrics = {}

        for year in timeseries["years"]:
            year_entries = years_data[year]

            wheat = sum(1 for e in year_entries if e.get("crop") == "WHEAT")
            maize = sum(1 for e in year_entries if e.get("crop") == "MAIZE")
            solar = sum(1 for e in year_entries if e.get("land_use") == "solar_pv")
            income = sum(e.get("annual_income", 0) for e in year_entries)
            production = sum(e.get("total_production", 0) for e in year_entries)
            energy = sum(e.get("annual_energy_kwh", 0) for e in year_entries)

            timeseries["wheat_count"].append(wheat)
            timeseries["maize_count"].append(maize)
            timeseries["solar_count"].append(solar)
            timeseries["total_income"].append(income)
            timeseries["total_production"].append(production)
            timeseries["total_energy"].append(energy)

            # Store final year as final_metrics
            if year == timeseries["years"][-1]:
                final_metrics = {
                    "wheat_count": wheat,
                    "maize_count": maize,
                    "solar_count": solar,
                    "total_income": income,
                    "total_production": production
                }

        data["timeseries"] = timeseries
        data["final_metrics"] = final_metrics

    return data


def create_historical_comparison(results_dir: str = "results", output_file: str = "historical_comparison.html"):
    """
    Create comparison visualization: Historical vs RCP26/45/85.

    Shows:
    - Land use changes over time (historical baseline vs future scenarios)
    - Suitability score trends
    - Economic impacts (income, production)
    - Highlights how future scenarios deviate from historical patterns
    """

    # Load all scenario results
    scenarios = ["historical", "rcp26", "rcp45", "rcp85"]
    scenario_data = {}

    for scenario in scenarios:
        data = load_scenario_results(results_dir, scenario)
        if data:
            scenario_data[scenario] = data

    if "historical" not in scenario_data:
        print("❌ Historical scenario not run yet. Run: python run_mlu.py --scenario historical")
        return

    if len(scenario_data) < 2:
        print("❌ Not enough scenarios to compare. Run future scenarios first.")
        return

    # Create figure with subplots
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "Land Use: Historical vs Future",
            "Income: Historical vs Future",
            "Crop Production: Historical vs Future",
            "Solar Energy: Historical vs Future",
            "Suitability Scores: Wheat",
            "Suitability Scores: Maize"
        ),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )

    # Colors for scenarios
    colors = {
        "historical": "black",
        "rcp26": "green",
        "rcp45": "orange",
        "rcp85": "red"
    }

    labels = {
        "historical": "Historical (Past)",
        "rcp26": "RCP 2.6 (Low Emissions)",
        "rcp45": "RCP 4.5 (Medium Emissions)",
        "rcp85": "RCP 8.5 (High Emissions)"
    }

    # Plot each scenario
    for scenario, data in scenario_data.items():
        color = colors.get(scenario, "blue")
        label = labels.get(scenario, scenario.upper())

        timeseries = data.get("timeseries", {})
        years = timeseries.get("years", [])

        # Row 1, Col 1: Land use (wheat + maize)
        wheat_count = timeseries.get("wheat_count", [])
        maize_count = timeseries.get("maize_count", [])
        total_ag = [w + m for w, m in zip(wheat_count, maize_count)]

        fig.add_trace(
            go.Scatter(x=years, y=total_ag, name=f"{label} - Agriculture",
                      line=dict(color=color, dash="solid" if scenario != "historical" else "dash"),
                      legendgroup=scenario),
            row=1, col=1
        )

        # Row 1, Col 2: Income
        income = timeseries.get("total_income", [])
        fig.add_trace(
            go.Scatter(x=years, y=income, name=f"{label} - Income",
                      line=dict(color=color, dash="solid" if scenario != "historical" else "dash"),
                      legendgroup=scenario, showlegend=False),
            row=1, col=2
        )

        # Row 2, Col 1: Crop production
        production = timeseries.get("total_production", [])
        fig.add_trace(
            go.Scatter(x=years, y=production, name=f"{label} - Production",
                      line=dict(color=color, dash="solid" if scenario != "historical" else "dash"),
                      legendgroup=scenario, showlegend=False),
            row=2, col=1
        )

        # Row 2, Col 2: Solar energy
        solar_energy = timeseries.get("total_energy", [])
        fig.add_trace(
            go.Scatter(x=years, y=solar_energy, name=f"{label} - Solar",
                      line=dict(color=color, dash="solid" if scenario != "historical" else "dash"),
                      legendgroup=scenario, showlegend=False),
            row=2, col=2
        )

    # Update layout
    fig.update_xaxes(title_text="Year", row=3, col=1)
    fig.update_xaxes(title_text="Year", row=3, col=2)

    fig.update_yaxes(title_text="# Parcels in Agriculture", row=1, col=1)
    fig.update_yaxes(title_text="Total Income (€)", row=1, col=2)
    fig.update_yaxes(title_text="Production (tons)", row=2, col=1)
    fig.update_yaxes(title_text="Solar Energy (kWh)", row=2, col=2)

    fig.update_layout(
        title_text="Historical Benchmarking: Past vs Future Scenarios<br><sub>MLU-07: Compare historical baseline against climate change projections</sub>",
        height=1000,
        showlegend=True,
        hovermode='x unified'
    )

    # Save
    output_path = Path(results_dir) / output_file
    fig.write_html(str(output_path))
    print(f"✅ Historical comparison saved: {output_path}")

    # Create summary statistics
    create_summary_report(scenario_data, results_dir)


def create_summary_report(scenario_data: dict, results_dir: str):
    """Create text summary comparing historical vs future."""

    output_path = Path(results_dir) / "historical_benchmark_report.txt"

    with open(output_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("HISTORICAL BENCHMARKING REPORT\n")
        f.write("MLU-07: Compare Past vs Future Land-Use Suitability\n")
        f.write("=" * 80 + "\n\n")

        if "historical" not in scenario_data:
            f.write("❌ No historical baseline available\n")
            return

        historical = scenario_data["historical"]
        hist_final = historical.get("final_metrics", {})

        f.write("HISTORICAL BASELINE (Past Conditions):\n")
        f.write("-" * 40 + "\n")
        hist_ag_total = hist_final.get('wheat_count', 0) + hist_final.get('maize_count', 0)
        f.write(f"  Agriculture Parcels: {hist_ag_total:.0f}\n")
        f.write(f"  Solar PV Parcels: {hist_final.get('solar_count', 0):.0f}\n")
        f.write(f"  Total Income: €{hist_final.get('total_income', 0):,.2f}\n")
        f.write(f"  Crop Production: {hist_final.get('total_production', 0):.2f} tons\n\n")

        f.write("FUTURE SCENARIO COMPARISONS:\n")
        f.write("=" * 80 + "\n\n")

        for scenario in ["rcp26", "rcp45", "rcp85"]:
            if scenario not in scenario_data:
                continue

            future = scenario_data[scenario]
            future_final = future.get("final_metrics", {})

            f.write(f"{scenario.upper()} vs HISTORICAL:\n")
            f.write("-" * 40 + "\n")

            # Calculate changes
            hist_ag = hist_final.get('wheat_count', 0) + hist_final.get('maize_count', 0)
            future_ag = future_final.get('wheat_count', 0) + future_final.get('maize_count', 0)
            ag_change = future_ag - hist_ag
            ag_pct = (ag_change / hist_ag * 100) if hist_ag > 0 else 0

            hist_solar = hist_final.get('solar_count', 0)
            future_solar = future_final.get('solar_count', 0)
            solar_change = future_solar - hist_solar
            solar_pct = (solar_change / hist_solar * 100) if hist_solar > 0 else 0

            hist_income = hist_final.get('total_income', 0)
            future_income = future_final.get('total_income', 0)
            income_change = future_income - hist_income
            income_pct = (income_change / hist_income * 100) if hist_income > 0 else 0

            f.write(f"  Agriculture: {future_ag:.0f} parcels ({ag_change:+.0f}, {ag_pct:+.1f}%)\n")
            f.write(f"  Solar PV: {future_solar:.0f} parcels ({solar_change:+.0f}, {solar_pct:+.1f}%)\n")
            f.write(f"  Income: €{future_income:,.2f} ({income_pct:+.1f}%)\n")

            # Interpretation
            if ag_change < 0:
                f.write(f"  ⚠️  Agricultural land DECREASED under {scenario.upper()}\n")
            elif ag_change > 0:
                f.write(f"  ✅ Agricultural land INCREASED under {scenario.upper()}\n")

            if solar_change > 0:
                f.write(f"  ☀️  Solar adoption INCREASED by {solar_change} parcels\n")

            f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("KEY INSIGHTS:\n")
        f.write("-" * 40 + "\n")
        f.write("• Historical data provides baseline for validating future projections\n")
        f.write("• Changes show impact of climate scenarios on land-use decisions\n")
        f.write("• Use this benchmarking to assess adaptation strategies\n")
        f.write("=" * 80 + "\n")

    print(f"✅ Benchmark report saved: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate historical benchmarking comparison")
    parser.add_argument("--results", default="results", help="Results directory")
    parser.add_argument("--output", default="historical_comparison.html", help="Output filename")

    args = parser.parse_args()

    create_historical_comparison(args.results, args.output)
