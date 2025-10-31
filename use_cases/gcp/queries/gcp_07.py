"""
GCP-07: View Geographic Distribution of PV Adoption

User Story: "As a Policymaker or Energy Company
I want to view the geographic distribution of PV adoption across the region
So that I can identify spatial patterns and target policies to specific areas."

This query focuses on:
- Geographic visualization of PV installations
- Spatial clustering analysis
- Regional adoption patterns
- Suitability vs actual adoption comparison
"""

import sys
from pathlib import Path
from openai import OpenAI

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Add GCP utils for scenario display names
gcp_utils_path = Path(__file__).parent.parent / "utils"
sys.path.insert(0, str(gcp_utils_path))

from use_cases.gcp.scripts.run_gcp_simulation import run_simulation_with_results
from scenario_utils import get_scenario_display_name
import numpy as np


def _generate_geographic_insights(adoption_rate, lat_spread, lon_spread, wealthy_pct, policy_scenario):
    """Generate AI insights for geographic distribution analysis."""
    try:
        client = OpenAI()

        clustering = "high" if (lat_spread < 0.05 and lon_spread < 0.05) else ("moderate" if (lat_spread < 0.1 and lon_spread < 0.1) else "wide")

        data_summary = f"""
Geographic Distribution of PV Adoption:
- Policy Scenario: {policy_scenario}
- Overall Adoption Rate: {adoption_rate:.1%}
- Spatial Clustering: {clustering} (spread: ±{lat_spread:.4f}° lat, ±{lon_spread:.4f}° lon)
- Wealthy Landowner Adoption: {wealthy_pct:.1%}
"""

        insights = {}

        # Spatial Equity Analysis
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a geographic equity analyst for green energy policy. Provide concise, actionable insights in 1-2 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nProvide a key insight about spatial equity. Does PV adoption reach all geographic areas and socioeconomic groups fairly?"}
            ],
            temperature=0.7,
            max_tokens=100
        )
        insights["Spatial Equity Analysis"] = response.choices[0].message.content.strip()

        # Targeted Policy Recommendations
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a regional development policy advisor. Provide concise, actionable insights in 1-2 sentences."},
                {"role": "user", "content": f"{data_summary}\n\nProvide a key insight about geographic targeting. Which regions or demographics should policymakers focus on to improve adoption?"}
            ],
            temperature=0.7,
            max_tokens=100
        )
        insights["Targeted Policy Recommendations"] = response.choices[0].message.content.strip()

        return insights

    except Exception as e:
        print(f"⚠️  Could not generate AI insights: {e}")
        return {
            "Spatial Equity Analysis": f"{clustering.capitalize()} spatial clustering with {wealthy_pct:.1%} wealthy adopters indicates need for broader policy reach",
            "Targeted Policy Recommendations": f"Focus on underserved regions and moderate-income landowners to achieve more equitable {adoption_rate:.1%} adoption"
        }


def query_gcp_07(
    data_path: str,
    scenario: str = 'rcp45',
    policy_scenario: str = 'moderate_support',
    n_years: int = 10,
    n_landowners: int = 20,
    n_financial_institutions: int = 2,
    n_policymakers: int = 1,
    output_dir: str = None,
    geojson: dict = None,
    farmer_locations: list = None
):
    """
    GCP-07: View geographic distribution of PV adoption.

    Args:
        data_path: Path to GCP data directory
        scenario: Climate scenario (rcp26, rcp45, rcp85)
        policy_scenario: Green credit policy scenario
        n_years: Number of years to simulate
        n_landowners: Number of landowner agents
        n_financial_institutions: Number of financial institution agents
        n_policymakers: Number of policymaker agents
        output_dir: Output directory (default: results/gcp_07)
        geojson: GeoJSON polygon for spatial filtering
        farmer_locations: User-specified landowner locations with crops

    Returns:
        Dict with simulation results and geographic analysis
    """
    try:
        print(f"\n{'='*80}")
        print(f"GCP-07: Geographic Distribution of PV Adoption")
        print(f"{'='*80}")
        print(f"Climate Scenario: {get_scenario_display_name(scenario)}")
        print(f"Policy Scenario: {policy_scenario}")
        print(f"Duration: {n_years} years")
        print(f"Landowners: {n_landowners}")
        print(f"{'='*80}\n")

        # Set default output directory
        if output_dir is None:
            gcp_dir = Path(__file__).parent.parent
            output_dir = str(gcp_dir / "results" / "gcp_07")

        # Run simulation to get PV adoption data
        print("🔄 Running simulation to collect PV adoption data...")
        results = run_simulation_with_results(
            scenario=scenario,
            policy_scenario=policy_scenario,
            n_years=n_years,
            n_landowners=n_landowners,
            n_financial_institutions=n_financial_institutions,
            n_policymakers=n_policymakers,
            output_dir=output_dir,
            data_path=data_path,
            geojson=geojson,
            farmer_locations=farmer_locations
        )

        # Extract geographic data
        model = results.get('model')
        yearly_landowner_snapshots = results.get('yearly_landowner_snapshots', [])

        if model and yearly_landowner_snapshots:
            print(f"\n{'='*80}")
            print(f"GCP-07 RESULTS: GEOGRAPHIC ANALYSIS")
            print(f"{'='*80}\n")

            # Get final year data
            final_year_data = yearly_landowner_snapshots[-1]
            landowners = final_year_data.get('landowners', [])

            # Separate adopters and non-adopters
            adopters = [lo for lo in landowners if lo['has_pv']]
            non_adopters = [lo for lo in landowners if not lo['has_pv']]

            print(f"📍 Geographic Distribution Summary:")
            print(f"   Total Landowners: {len(landowners)}")
            print(f"   PV Adopters: {len(adopters)} ({len(adopters)/len(landowners):.1%})")
            print(f"   Non-Adopters: {len(non_adopters)} ({len(non_adopters)/len(landowners):.1%})")

            if adopters:
                # Calculate geographic statistics
                adopter_lats = [a['lat'] for a in adopters]
                adopter_lons = [a['lon'] for a in adopters]

                center_lat = np.mean(adopter_lats)
                center_lon = np.mean(adopter_lons)
                lat_spread = np.std(adopter_lats)
                lon_spread = np.std(adopter_lons)

                print(f"\n   Adoption Centroid:")
                print(f"     Latitude: {center_lat:.4f}°")
                print(f"     Longitude: {center_lon:.4f}°")
                print(f"     Spatial Spread: ±{lat_spread:.4f}° lat, ±{lon_spread:.4f}° lon")

                # Total capacity by location
                total_capacity = sum(a['pv_capacity_kw'] for a in adopters)
                print(f"\n   Total PV Capacity: {total_capacity:,.0f} kW")
                print(f"   Average Capacity per Installation: {total_capacity/len(adopters):,.0f} kW")

                # Top installations
                sorted_adopters = sorted(adopters, key=lambda x: x['pv_capacity_kw'], reverse=True)
                print(f"\n   Top 5 PV Installations:")
                for i, adopter in enumerate(sorted_adopters[:5], 1):
                    print(f"     {i}. Landowner {adopter['id']}: {adopter['pv_capacity_kw']:.0f} kW "
                          f"at ({adopter['lat']:.4f}, {adopter['lon']:.4f})")

                # Geographic clustering analysis
                print(f"\n🗺️  Spatial Clustering Analysis:")
                if lat_spread < 0.05 and lon_spread < 0.05:
                    print(f"   ✓ High spatial clustering - adoptions concentrated in small area")
                    print(f"   → Consider expanding policy outreach to broader regions")
                elif lat_spread < 0.1 and lon_spread < 0.1:
                    print(f"   → Moderate spatial distribution")
                    print(f"   → Policy is reaching multiple local clusters")
                else:
                    print(f"   ✓ Wide spatial distribution - adoptions across entire region")
                    print(f"   → Policy has broad geographic reach")

                # Financial pattern analysis
                adopter_financial_situations = [a['financial_situation'] for a in adopters]
                wealthy_count = sum(1 for fs in adopter_financial_situations if fs == 'wealthy')
                moderate_count = sum(1 for fs in adopter_financial_situations if fs == 'moderate')
                poor_count = sum(1 for fs in adopter_financial_situations if fs == 'poor')

                print(f"\n💰 Adopter Financial Profile:")
                print(f"   Wealthy: {wealthy_count} ({wealthy_count/len(adopters):.1%})")
                print(f"   Moderate: {moderate_count} ({moderate_count/len(adopters):.1%})")
                print(f"   Poor: {poor_count} ({poor_count/len(adopters):.1%})")

                if wealthy_count > len(adopters) * 0.6:
                    print(f"\n   ⚠️  Adoption skewed toward wealthy landowners")
                    print(f"   → Consider increasing subsidies to reach moderate/poor segments")
                elif poor_count > len(adopters) * 0.3:
                    print(f"\n   ✓ Policy successfully reaching economically diverse landowners")
                else:
                    print(f"\n   → Policy reaching primarily moderate-income landowners")

                # Generate AI insights
                print(f"\n📊 AI-Generated Insights:")
                insights = _generate_geographic_insights(
                    adoption_rate=len(adopters)/len(landowners),
                    lat_spread=lat_spread,
                    lon_spread=lon_spread,
                    wealthy_pct=wealthy_count/len(adopters),
                    policy_scenario=policy_scenario
                )
                for viz_name, insight in insights.items():
                    print(f"\n  {viz_name}:")
                    print(f"    {insight}")

            # PV installation timeline analysis
            print(f"\n📈 Temporal-Spatial Dynamics:")
            pv_installations = model.pv_installations  # List of {year, agent_id, capacity_kw, lat, lon}

            if pv_installations:
                # Group installations by year
                installations_by_year = {}
                for inst in pv_installations:
                    year = inst['year']
                    if year not in installations_by_year:
                        installations_by_year[year] = []
                    installations_by_year[year].append(inst)

                print(f"   PV Installation Timeline:")
                for year in sorted(installations_by_year.keys()):
                    n_installs = len(installations_by_year[year])
                    total_capacity = sum(i['capacity_kw'] for i in installations_by_year[year])
                    print(f"     Year {year}: {n_installs} installations, {total_capacity:,.0f} kW added")

                # Early vs late adopters
                early_years = sorted(installations_by_year.keys())[:max(1, len(installations_by_year) // 3)]
                late_years = sorted(installations_by_year.keys())[-max(1, len(installations_by_year) // 3):]

                early_installs = sum(len(installations_by_year[y]) for y in early_years)
                late_installs = sum(len(installations_by_year[y]) for y in late_years)

                print(f"\n   Adoption Momentum:")
                if late_installs > early_installs * 1.5:
                    print(f"     ✓ Accelerating adoption (late years > early years)")
                    print(f"     → Policy effectiveness is increasing over time")
                elif late_installs < early_installs * 0.7:
                    print(f"     ⚠️  Decelerating adoption (late years < early years)")
                    print(f"     → Policy may be losing effectiveness or market saturation")
                else:
                    print(f"     → Steady adoption rate maintained over time")

        # Generate geographic visualizations
        try:
            from use_cases.gcp.scripts.gcp_visualizations import generate_gcp_07_visualizations

            visualization_files = generate_gcp_07_visualizations(
                yearly_landowner_snapshots,
                scenario=scenario,
                policy_scenario=policy_scenario,
                output_dir=f"{results.get('output_path', output_dir)}/visualizations",
                data_path=data_path
            )

            if visualization_files:
                print(f"\n📊 Generated Visualizations:")
                for viz_type, file_path in visualization_files.items():
                    print(f"   - {viz_type}: {file_path}")

        except Exception as e:
            print(f"\n⚠️  Warning: Could not generate geographic visualizations: {e}")
            print("   Install dependencies: pip install folium")
            import traceback
            print("\nFull traceback:")
            traceback.print_exc(file=sys.stdout)

        # Always return results (success case)
        print(f"\n{'='*80}")
        print(f"✅ Results saved to: {output_dir}/")
        print(f"   - Text summary: {output_dir}/{scenario}/{policy_scenario}/{scenario}_{policy_scenario}_results.txt")
        print(f"   - Geographic data: Available in model.pv_installations")
        print(f"{'='*80}\n")

        # Add insights to results if they were generated
        if 'insights' in locals():
            results['ai_insights'] = insights

        return results

    except ValueError as e:
        # Clean error message for validation errors (user-friendly)
        error_msg = str(e)
        print(f"\n🚨 CAUGHT ValueError in query_gcp_07!")
        print(f"   Exception: {e}")
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"{error_msg}", file=sys.stderr)
        print(f"{'='*80}\n", file=sys.stderr)
        # ALSO print to stdout so we can see it
        print(f"\n{'='*80}")
        print(f"{error_msg}")
        print(f"{'='*80}\n")
        return {
            'status': 'error',
            'message': error_msg,
            'scenario': scenario,
            'policy_scenario': policy_scenario
        }


if __name__ == "__main__":
    # Example usage
    query_gcp_07(
        data_path="/Users/theanomamouka/Desktop/TRANSITION/transition/backend/data/GCP",
        scenario="rcp45",
        policy_scenario="moderate_support",
        n_years=10,
        n_landowners=20,
        n_financial_institutions=2,
        n_policymakers=1
    )
