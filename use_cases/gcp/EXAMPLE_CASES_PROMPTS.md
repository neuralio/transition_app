# GCP (Green Credit Policy) - Example Commands & Prompts

Quick reference for running GCP (Use Case 2) simulations from the command line.

---

## 🚀 Quick Start

### Run All Policy Scenarios (Recommended for First Test)

```bash
# Compare low_support, moderate_support, and high_support
python use_cases/gcp/run_gcp.py --scenario rcp45 --years 10 --landowners 20
```

This generates **comparative analysis** across all three policy scenarios!

---

## 📋 User Story Queries

### GCP-03: Simulate PV Adoption by Farmers/Landowners

**Purpose**: Simulate the effects of green credit policies on PV adoption by landowners.

```bash
# Basic usage
python use_cases/gcp/run_gcp.py --query gcp_03 --scenario rcp45 --policy moderate_support

# With custom parameters
python use_cases/gcp/run_gcp.py --query gcp_03 --scenario rcp45 --policy moderate_support --years 10 --landowners 20

# Compare all policy scenarios
python use_cases/gcp/queries/gcp_03.py  # Runs from queries/ directory

# ADVANCED: User-specified landowner locations with initial crops (NEW - 2025-10-21)
# Coordinates must be within Thessaloniki bounds (40.4-40.9°N, 22.5-22.9°E)
python use_cases/gcp/run_gcp.py --query gcp_03 --scenario rcp45 --policy moderate_support --years 10 \
  --farmer-locations '[{"lat":40.5,"lon":22.7,"crop":"WHEAT"},{"lat":40.6,"lon":22.8,"crop":"MAIZE"}]'

# With multi-level agents and custom locations
python use_cases/gcp/run_gcp.py --query gcp_03 --scenario rcp85 --policy high_support --years 15 \
  --farmer-locations '[{"lat":40.55,"lon":22.65,"crop":"WHEAT"},{"lat":40.7,"lon":22.75,"crop":"MAIZE"}]' \
  --financial-institutions 3 --policymakers 2
```

**Key Features**:
- ✅ Multi-level ABM (Individual, Market, Policy levels)
- ✅ Energy savings tracking
- ✅ Loan approval/denial statistics
- ✅ Policy effectiveness evaluation
- ✅ Interactive time-series visualizations
- ✅ **Demographic breakdown analysis** (financial situation, risk tolerance) - **GCP-03 ESA Compliance**

**Outputs**:
- Text summary: `results/gcp_03/{scenario}/{policy}/{scenario}_{policy}_results.txt`
- Time-series charts: `results/gcp_03/visualizations/{scenario}_{policy}_time_series.html`
- Policy comparison: `results/gcp_03/visualizations/{scenario}_policy_comparison.html`
- **Demographic breakdown**: `results/gcp_03/visualizations/{scenario}_{policy}_demographic_breakdown.html` ✨ **NEW**
  - Adoption rates by financial situation (poor/moderate/wealthy)
  - Adoption rates by risk tolerance (low/moderate/high)
  - Average ROI by financial situation
  - Average payback period by risk tolerance
  - Distribution of adopters by demographics

---

### GCP-07: View Geographic Distribution of PV Adoption

**Purpose**: Visualize the geographic distribution of PV installations across the region.

```bash
# Basic usage
python use_cases/gcp/run_gcp.py --query gcp_07 --scenario rcp45 --policy moderate_support

# With more landowners for better spatial analysis
python use_cases/gcp/run_gcp.py --query gcp_07 --scenario rcp45 --policy high_support --years 10 --landowners 50
```

**Key Features**:
- ✅ Interactive Folium map with year selector
- ✅ Color-coded markers (green=PV installed, orange=loan approved, gray=no PV)
- ✅ Detailed popups showing financial situation, ROI, capacity
- ✅ Spatial clustering analysis
- ✅ Adoption centroid calculation

**Outputs**:
- Text summary: `results/gcp_07/{scenario}/{policy}/{scenario}_{policy}_results.txt`
- Interactive map: `results/gcp_07/visualizations/{scenario}_{policy}_pv_map.html`

---

### GCP-16: Monitor Feedback Loop Between Policy and Financial Institutions

**Purpose**: Monitor the feedback loop between policy changes and financial institution behavior.

**⚠️ IMPORTANT**: GCP-16 **automatically runs ALL policy scenarios** (low_support, moderate_support, high_support) for comprehensive comparison. The `--policy` flag is **IGNORED** for this query.

```bash
# Longer simulation recommended (15+ years to see feedback effects)
python use_cases/gcp/run_gcp.py --query gcp_16 --scenario rcp45 --years 15

# Even longer for better feedback loop analysis
python use_cases/gcp/run_gcp.py --query gcp_16 --scenario rcp85 --years 20 --landowners 50

# NOTE: --policy flag is ignored - all three policies run automatically
python use_cases/gcp/run_gcp.py --query gcp_16 --scenario rcp45 --years 15  # Runs all policies
```

**Key Features**:
- ✅ **Multi-policy comparison** (runs all 3 policies automatically)
- ✅ Policy adjustment timeline tracking (subsidy rate, loan rate evolution)
- ✅ **Financial institution response tracking** (approval rates, portfolio risk, credit thresholds)
- ✅ **Loan portfolio dynamics** (active loans, loan volume, default rates over time)
- ✅ **Bidirectional feedback visualization** (Policy → FI → Adoption AND Adoption → FI → Policy)
- ✅ Policy-adoption correlation analysis
- ✅ Risk-default correlation analysis
- ✅ Feedback loop effectiveness evaluation
- ✅ Cross-policy effectiveness comparison

**Outputs**:
- Text summary: `results/gcp_16/{scenario}/{policy}/{scenario}_{policy}_results.txt` (for each policy)
- **Enhanced Feedback loop charts**: `results/gcp_16/visualizations/{scenario}_{policy}_feedback_loop.html` (3 files - one per policy)
  - **12 interactive charts** showing:
    - Row 1: Policy adjustments (subsidy rate, loan rate, adoption)
    - Row 2: FI response (approval rate, risk score, credit threshold)
    - Row 3: Loan portfolio (active loans, volume, defaults)
    - Row 4: Feedback effectiveness (spending, correlations)
- **Policy comparison**: `results/gcp_16/visualizations/{scenario}_policy_comparison.html`

**⚠️ Note**:
- GCP-16 works best with 15+ years to observe policy adjustments over time
- Always runs **all three policy scenarios** for comprehensive feedback loop comparison
- The `--policy` flag has **no effect** on this query

---

## 🎛️ Available Parameters

### Required Parameters

| Parameter | Options | Description |
|-----------|---------|-------------|
| `--scenario` | `rcp26`, `rcp45`, `rcp85` | Climate scenario (default: `rcp45`) |

### Optional Parameters

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| `--query` | `gcp_03`, `gcp_07`, `gcp_16` | None | User story query (omit for full simulation) |
| `--policy` | `low_support`, `moderate_support`, `high_support` | All three | Policy scenario (omit to run all) |
| `--years` | Integer | 10 | Simulation duration in years |
| `--landowners` | Integer | 20 | Number of landowner agents |
| `--financial-institutions` | Integer | 2 | Number of financial institution agents |
| `--policymakers` | Integer | 1 | Number of policymaker agents |
| `--output` | Path | `use_cases/gcp/results/` | Custom output directory |
| `--data-path` | Path | From `config.yaml` | Path to GCP data directory |

---

## 🎯 Understanding GCP's Two Scenario Dimensions

GCP has a **2D scenario matrix**: **Climate** × **Policy**

### 🌍 Climate Scenarios (affects solar radiation)

Climate scenarios determine **solar radiation availability**, which impacts PV energy production and financial attractiveness.

| Scenario | Description | Warming Level | Solar Impact |
|----------|-------------|---------------|--------------|
| `rcp26` | Low emissions | ~2°C by 2100 | Changes in cloud cover |
| `rcp45` | Medium emissions (baseline) | ~3°C by 2100 | Baseline solar radiation |
| `rcp85` | High emissions | ~4-5°C by 2100 | Variable solar potential |

**Default**: If not specified, runs **ALL climate scenarios** (rcp26, rcp45, rcp85)

### 💰 Policy Scenarios (affects green credit incentives)

Policy scenarios determine **government support levels** for PV adoption.

| Policy | PV Subsidy Rate | Low-Interest Loan Rate | Tax Incentive |
|--------|-----------------|------------------------|---------------|
| `low_support` | 10% | 5% | 5% |
| `moderate_support` | 20% | 3% | 10% |
| `high_support` | 30% | 2% | 15% |

**Default**: If not specified, runs **ALL policy scenarios** for comparison

### 📊 Scenario Matrix Examples

| User Query | Climate | Policy | What Runs |
|------------|---------|--------|-----------|
| "Simulate with **moderate support**" | ✅ rcp45 (default) | ✅ moderate_support | 1 simulation |
| "Simulate under **optimistic** scenario" | ✅ rcp26 (optimistic) | ✅ ALL policies | 3 simulations |
| "Simulate PV adoption" | ✅ rcp45 (default) | ✅ ALL policies | 3 simulations |
| "Simulate with **high support** under **pessimistic**" | ✅ rcp85 (pessimistic) | ✅ high_support | 1 simulation |

---

## 📁 Output Structure

```
use_cases/gcp/results/
├── gcp_03/                          # PV adoption simulation
│   ├── rcp45/
│   │   ├── low_support/
│   │   │   └── rcp45_low_support_results.txt
│   │   ├── moderate_support/
│   │   │   └── rcp45_moderate_support_results.txt
│   │   └── high_support/
│   │       └── rcp45_high_support_results.txt
│   └── visualizations/
│       ├── rcp45_low_support_time_series.html
│       ├── rcp45_moderate_support_time_series.html
│       ├── rcp45_high_support_time_series.html
│       └── rcp45_policy_comparison.html
│
├── gcp_07/                          # Geographic distribution
│   └── visualizations/
│       └── rcp45_moderate_support_pv_map.html
│
└── gcp_16/                          # Policy feedback loops
    └── visualizations/
        └── rcp45_moderate_support_feedback_loop.html
```

---

## 🔬 Example Test Runs

### Minimal Test (Fast)

```bash
# Quick 5-year test with 10 landowners
python use_cases/gcp/run_gcp.py --query gcp_03 --scenario rcp45 --policy moderate_support --years 5 --landowners 10
```

### Standard Test (Recommended)

```bash
# 10-year simulation with 20 landowners
python use_cases/gcp/run_gcp.py --scenario rcp45 --years 10 --landowners 20
```

### Comprehensive Test (Full Analysis)

```bash
# All policy scenarios, 15 years, 50 landowners
python use_cases/gcp/run_gcp.py --scenario rcp45 --years 15 --landowners 50 --financial-institutions 3
```

### Climate Comparison

```bash
# Compare different climate scenarios
python use_cases/gcp/run_gcp.py --scenario rcp26 --policy high_support --years 10 --landowners 20
python use_cases/gcp/run_gcp.py --scenario rcp45 --policy high_support --years 10 --landowners 20
python use_cases/gcp/run_gcp.py --scenario rcp85 --policy high_support --years 10 --landowners 20
```

---

## 📊 What Gets Generated

### Text Reports
✅ Yearly statistics (adoption rate, capacity, loans, defaults)
✅ Financial institution portfolio summary
✅ Policy effectiveness analysis
✅ Energy savings and revenue tracking
✅ Policy adjustment timeline
✅ Recommendations based on results

### Interactive Visualizations
✅ **Time-series charts** (10 subplots):
   - PV adoption rate over time
   - Total PV capacity growth
   - Loan outcomes (approved/denied)
   - Default rate trends
   - Subsidy rate evolution
   - Energy savings & feed-in revenue
   - Landowner adoption breakdown
   - Loan approval rate
   - Average energy savings per installation
   - Combined economic benefits

✅ **Policy comparison charts** (6 subplots):
   - Final adoption rates across policies
   - Total capacity comparison
   - Subsidy spending comparison
   - Default rates
   - Approval rates
   - Cost per adoption efficiency

✅ **Demographic breakdown charts** (6 subplots - **NEW for GCP-03 ESA Compliance**):
   - PV adoption rate by financial situation (time series)
   - PV adoption rate by risk tolerance (time series)
   - Average ROI by financial situation (time series)
   - Average payback period by risk tolerance (time series)
   - Financial situation distribution among adopters (pie chart)
   - Risk tolerance distribution among adopters (pie chart)

✅ **Enhanced Feedback loop charts** (12 subplots - GCP-16 FULL COMPLIANCE):
   - **Policy Level**: Subsidy rate, loan rate, adoption response
   - **Financial Institution Response**: Approval rates, portfolio risk, credit thresholds
   - **Loan Portfolio Dynamics**: Active loans, loan volume, defaults
   - **Bidirectional Feedback**: Policy-adoption correlation, risk-default correlation

✅ **Geographic maps** (GCP-07):
   - Interactive Folium map with year selector
   - Color-coded PV installations
   - Detailed popups with financial data
   - Multiple basemap options

---

## 🎯 Advanced Usage

### Multi-Policy Analysis from Python

```python
from use_cases.gcp.queries.gcp_03 import query_gcp_03_all_policies

results = query_gcp_03_all_policies(
    data_path="/path/to/data/GCP",
    scenario="rcp45",
    n_years=10,
    n_landowners=20,
    n_financial_institutions=2,
    n_policymakers=1
)
```

### Direct Query Execution

```bash
# Run queries directly
python use_cases/gcp/queries/gcp_03.py
python use_cases/gcp/queries/gcp_07.py
python use_cases/gcp/queries/gcp_16.py
```

---

## 🐛 Troubleshooting

### No PV Adoption?

If you see 0% adoption:
- ✅ Try longer simulations (15-20 years)
- ✅ Use `high_support` policy scenario
- ✅ Increase number of landowners (30-50)
- ✅ Check that data path is correct in `config.yaml`

### Missing Visualizations?

Install required dependencies:
```bash
pip install plotly folium
```

### Low Adoption Rates?

This is realistic! PV adoption depends on:
- Financial attractiveness (ROI, payback period)
- Policy support level (subsidies, loan rates)
- Social influence (peer adoption)
- Loan approval by financial institutions
- Risk tolerance and financial situation

Try `high_support` policy for higher adoption rates.

---

## 📚 Related Documentation

- [USER_STORIES.md](USER_STORIES.md) - Full user story specifications
- [config.yaml](config.yaml) - Configuration parameters
- [../gcp/README.md](README.md) - GCP use case overview
- [../../CLAUDE.md](../../CLAUDE.md) - Project documentation

---

**Questions?** Check the simulation output for detailed insights, or review the generated visualizations for interactive exploration!
