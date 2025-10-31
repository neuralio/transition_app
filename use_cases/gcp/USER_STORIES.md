# GCP User Stories - Green Credit Policy

**Status**: ✅ **3 User Stories Implemented** (GCP-03, GCP-07, GCP-16)

**Use Case**: UC-GCP-02 - Green Credit Policy Analysis Using Multi-Level Agent-Based Modeling

**Deliverable**: TRANSITION D1.1 - Use Case Documentation

---

## 📋 Implemented User Stories

### GCP-03: Simulate PV Adoption by Farmers/Landowners ✅

**User Story**:
> As a **Landowner** or **Farmer**
> I want to **simulate the effects of green credit policies on PV adoption by landowners**
> So that I can **understand how green credit policies influence renewable energy adoption at the micro-level**.

**Acceptance Criteria**:
- The system must allow users to simulate PV adoption based on different policy scenarios (low, moderate, high support).
- The model must incorporate agent-specific variables such as financial situation, risk tolerance, and perceived benefits.
- The system should provide visualizations of PV adoption rates, showing geographic and demographic variations.
- Users should be able to track energy savings, loan approvals/denials, and policy effectiveness over time.

**Implementation Details**:
- **Entry Point**: `python run_gcp.py --query gcp_03 --scenario rcp45 --policy moderate_support --years 10 --landowners 20`
- **Module**: `use_cases/gcp/queries/gcp_03.py`
- **Output**: `results/gcp_03/`
- **Features**:
  - **Multi-Level ABM Framework** (3 levels):
    - **Individual Level**: LandownerAgent PV adoption decisions
    - **Market Level**: FinancialInstitutionAgent loan risk assessment
    - **Policy Level**: PolicymakerAgent subsidy/loan rate management
  - **Financial Modeling**:
    - Financial situation tracking (poor, moderate, wealthy)
    - Risk tolerance assessment (low, moderate, high)
    - Loan application and approval/denial workflow
    - ROI calculation with subsidies and green credits
    - Payback period estimation
  - **Social Influence**: Peer adoption effects
  - **Energy Economics**:
    - Annual energy savings tracking
    - Feed-in tariff revenue calculation
    - Installation cost modeling with elevation adjustments
  - **Policy Effectiveness Evaluation**:
    - Adoption rate tracking across demographics
    - Subsidy spending analysis
    - Cost-per-adoption efficiency metrics
  - **Demographic Analysis** (ESA Compliance):
    - Adoption rates by financial situation
    - Adoption rates by risk tolerance
    - Average ROI by demographics
    - Payback period variations
- **Multi-Level Configuration**:
  - **Default**: 2 financial institutions, 1 policymaker
  - **Custom**: `--financial-institutions N --policymakers N` flags
  - **LLM Interface**: Natural language support (e.g., "simulate with 3 banks and 2 policymakers")

**Natural Language Interface**:
```bash
# Mode 1: Single scenario + policy (1 simulation)
python llm_interface/transition_agent.py "Simulate PV adoption under moderate support policy with optimistic scenario"
python llm_interface/transition_agent.py "Show PV adoption with high support under pessimistic climate"

# Mode 2: Scenario only - runs ALL policies (3 simulations)
python llm_interface/transition_agent.py "Simulate PV adoption under optimistic scenario"
python llm_interface/transition_agent.py "Compare policies under pessimistic climate for 20 landowners"

# Mode 3: Policy only - runs ALL scenarios (3 simulations)
python llm_interface/transition_agent.py "Simulate PV adoption with moderate support policy"
python llm_interface/transition_agent.py "Show green credit high support effects across all climates"

# Mode 4: Neither - runs ALL combinations (9 simulations)
python llm_interface/transition_agent.py "Compare PV adoption across all scenarios and policies"
python llm_interface/transition_agent.py "Simulate PV adoption for 20 landowners"  # Full matrix

# With custom multi-level agents
python llm_interface/transition_agent.py "Simulate PV adoption with 30 landowners and 3 financial institutions under high support policy"
```

**Outputs**:
- **Text Summary**: `results/gcp_03/{scenario}/{policy}/{scenario}_{policy}_results.txt`
  - Yearly adoption statistics
  - Loan approval/denial rates
  - Energy savings and revenue
  - Policy effectiveness analysis

- **Time-Series Charts**: `results/gcp_03/visualizations/{scenario}_{policy}_time_series.html`
  - 10 interactive subplots (5x2 grid) showing:
    - PV adoption rate over time
    - Total PV capacity (kW)
    - Loan applications (approved/denied)
    - Default rate evolution
    - Policy subsidy rate trajectory
    - Total subsidy spending
    - Adopters vs non-adopters split
    - Loan approval rate
    - Energy savings & feed-in revenue
    - Average savings per installation

- **Policy Comparison**: `results/gcp_03/visualizations/{scenario}_policy_comparison.html` **(only generated when running all policies)**
  - 6 comparative charts across low/moderate/high support:
    - Final adoption rates
    - Total capacity installed
    - Total subsidy spending
    - Default rates
    - Loan approval rates
    - Cost-per-adoption efficiency

- **Demographic Breakdown**: `results/gcp_03/visualizations/{scenario}_{policy}_demographic_breakdown.html` ✨
  - 6 charts analyzing adoption by demographics:
    - Adoption rate by financial situation (time-series)
    - Adoption rate by risk tolerance (time-series)
    - Average ROI by financial situation
    - Average payback period by risk tolerance
    - Financial situation distribution (pie chart)
    - Risk tolerance distribution (pie chart)

---

### GCP-07: View Geographic Distribution of PV Adoption ✅

**User Story**:
> As a **Policymaker** or **Agricultural Developer**
> I want to **view the geographic distribution of PV adoption based on the green credit policy**
> So that I can **identify areas with higher adoption rates and understand regional impacts**.

**Acceptance Criteria**:
- The system must provide a map-based visualization showing the geographic distribution of PV installations across different regions.
- The visualization should highlight areas with high or low adoption rates, and allow users to drill down into regional data.
- The system must allow users to filter the map by demographic or geographic factors such as rural vs. urban areas or income levels.

**Implementation Details**:
- **Entry Point**: `python run_gcp.py --query gcp_07 --scenario rcp45 --policy moderate_support --years 10 --landowners 50`
- **Module**: `use_cases/gcp/queries/gcp_07.py`
- **Output**: `results/gcp_07/`
- **Features**:
  - **Interactive Folium Map** with year-by-year selector
  - **Color-Coded Markers**:
    - 🟢 Green: PV installed (with capacity details)
    - 🟠 Orange: Loan approved but not yet installed
    - ⚪ Gray: No PV installation
  - **Detailed Popups** showing:
    - Landowner financial situation
    - Risk tolerance level
    - PV capacity (kW)
    - ROI percentage
    - Payback period
    - Energy savings
    - Installation year
  - **Spatial Analysis**:
    - Adoption clustering detection
    - Geographic centroid calculation
    - Regional adoption rate statistics
  - **Multiple Basemaps**: OpenStreetMap, satellite imagery
  - **Temporal Animation**: Year slider to see adoption spread over time

**Natural Language Interface**:
```bash
# REQUIRED: Must specify BOTH climate scenario AND policy scenario
python llm_interface/transition_agent.py "View geographic distribution of solar installations with 50 landowners under moderate support with optimistic scenario"
python llm_interface/transition_agent.py "Map PV adoption under low support policy with pessimistic scenario"
python llm_interface/transition_agent.py "Show map of PV installations under high support with moderate scenario"
python llm_interface/transition_agent.py "View geographic distribution with 50 farmers under low support with pessimistic scenario"
```

**IMPORTANT**: GCP-07 requires **both** `--scenario` AND `--policy` parameters. Map visualization cannot show "all scenarios" or "all policies" simultaneously - you must specify one specific combination. If either parameter is missing, the system will show an error message.

**Outputs**:
- **Text Summary**: `results/gcp_07/{scenario}/{policy}/{scenario}_{policy}_results.txt`
  - Geographic statistics
  - Regional adoption clusters
  - Spatial distribution analysis

- **Interactive Map**: `results/gcp_07/visualizations/{scenario}_{policy}_pv_map.html`
  - Multi-year interactive map
  - Clickable markers with detailed popups
  - Year selector for temporal analysis
  - Legend with adoption statistics

---

### GCP-16: Monitor Feedback Loop Between Policy and Financial Institutions ✅

**User Story**:
> As a **Policymaker** or **Financial Institution Representative**
> I want to **monitor the feedback loop between green credit policies and financial institutions**
> So that I can **see how policy changes affect financial decision-making and vice versa**.

**Acceptance Criteria**:
- The system must simulate and visualize feedback loops between green credit policies, PV adoption rates, and financial institution behaviors.
- Users should be able to track how policy changes influence loan portfolios, financial risk profiles, and PV adoption over time.
- The system must provide insights into how financial institutions respond to evolving policy environments, including risk mitigation and loan adjustments.

**Implementation Details**:
- **Entry Point**: `python run_gcp.py --query gcp_16 --scenario rcp45 --years 15`
  - **Note**: GCP-16 **automatically runs ALL policy scenarios** (low, moderate, high support) for comprehensive feedback loop analysis
  - The `--policy` flag is **IGNORED** - all three policies are always simulated
- **Module**: `use_cases/gcp/queries/gcp_16.py`
- **Output**: `results/gcp_16/`
- **Features**:
  - **Multi-Policy Comparison** (runs all 3 policies automatically)
  - **Bidirectional Feedback Tracking**:
    - **Top-Down**: Policy → Financial Institutions → Landowners
      - Subsidy rate adjustments
      - Loan rate changes
      - Tax incentive modifications
    - **Bottom-Up**: Landowners → Financial Institutions → Policy
      - Adoption rates influence FI risk assessment
      - Default rates trigger FI credit threshold adjustments
      - Portfolio performance informs policy evaluation
  - **Financial Institution Response Tracking**:
    - Loan approval rate evolution
    - Portfolio risk score dynamics
    - Credit threshold adjustments
    - Risk mitigation strategies
  - **Loan Portfolio Dynamics**:
    - Active loan tracking over time
    - Loan volume growth/decline
    - Default rate monitoring
    - Portfolio composition analysis
  - **Policy Adjustment Timeline**:
    - Subsidy rate evolution (based on adoption effectiveness)
    - Loan rate modifications (based on FI risk tolerance)
    - Tax incentive changes
  - **Correlation Analysis**:
    - Policy-adoption correlations
    - Risk-default correlations
    - Subsidy effectiveness metrics
  - **Feedback Loop Effectiveness**:
    - Response time analysis
    - Adjustment magnitude tracking
    - System stability assessment
- **Recommended Configuration**:
  - **Duration**: 15-20 years (longer simulations reveal feedback patterns)
  - **Landowners**: 30-50 (sufficient sample for statistical analysis)
  - **FIs**: 2-3 (multiple institutions show competitive dynamics)

**Natural Language Interface**:
```bash
# REQUIRED: Must specify climate scenario (policy is automatic - all 3 policies run)
python llm_interface/transition_agent.py "Monitor feedback loops between policy and financial institutions under moderate scenario"
python llm_interface/transition_agent.py "Show how policy changes affect loan portfolios over 15 years with optimistic scenario"
python llm_interface/transition_agent.py "Analyze policy-FI feedback with 50 landowners under pessimistic scenario for 20 years"

# If user specifies policy, it will be ignored (all policies run anyway)
python llm_interface/transition_agent.py "Monitor feedback loops with moderate support under optimistic scenario"
# → Runs ALL policies (low, moderate, high) despite "moderate support" being mentioned
```

**IMPORTANT**:
- GCP-16 **REQUIRES** `--scenario` parameter (climate scenario is needed for context)
- GCP-16 **IGNORES** `--policy` parameter (automatically runs ALL 3 policies: low, moderate, high support)
- This design enables comprehensive feedback loop comparison across all policy scenarios

**Outputs**:
- **Text Summary**: `results/gcp_16/{scenario}/{policy}/{scenario}_{policy}_results.txt` (one per policy)
  - Policy adjustment timeline
  - FI response analysis
  - Loan portfolio evolution
  - Feedback loop effectiveness

- **Enhanced Feedback Loop Charts**: `results/gcp_16/visualizations/{scenario}_{policy}_feedback_loop.html` (3 files)
  - **12 interactive subplots** showing:
    - **Row 1: Policy Adjustments**
      - Subsidy rate evolution
      - Loan rate evolution
      - Adoption response to policy changes
    - **Row 2: Financial Institution Response**
      - Loan approval rate trends
      - Portfolio risk score dynamics
      - Credit threshold adjustments
    - **Row 3: Loan Portfolio Dynamics**
      - Active loans over time
      - Loan volume growth
      - Default rate monitoring
    - **Row 4: Bidirectional Feedback**
      - Total subsidy spending
      - Policy-adoption correlation
      - Risk-default correlation

- **Multi-Policy Comparison**: `results/gcp_16/visualizations/{scenario}_policy_comparison.html`
  - Comparative effectiveness analysis across all three policies
  - Feedback loop strength comparison
  - FI response patterns across policy scenarios

**⚠️ Important Notes**:
- GCP-16 automatically runs **ALL three policy scenarios** (low, moderate, high support)
- Longer simulations (15+ years) are recommended to observe policy adjustment cycles
- The `--policy` flag has **no effect** on this query

---

## 🚀 Quick Start Examples

### Via Direct CLI

```bash
# GCP-03: PV adoption simulation
python use_cases/gcp/run_gcp.py --query gcp_03 --scenario rcp45 --policy moderate_support --years 10 --landowners 20

# GCP-07: Geographic distribution map
python use_cases/gcp/run_gcp.py --query gcp_07 --scenario rcp45 --policy high_support --years 10 --landowners 50

# GCP-16: Feedback loop monitoring (runs all policies automatically)
python use_cases/gcp/run_gcp.py --query gcp_16 --scenario rcp45 --years 15 --landowners 30
```

### Via Natural Language Interface

```bash
# GCP-03 examples
python llm_interface/transition_agent.py "Simulate PV adoption with moderate support policy"
python llm_interface/transition_agent.py "Show green credit effects with 30 landowners under high support"

# GCP-07 examples
python llm_interface/transition_agent.py "Show PV adoption map with 50 landowners"
python llm_interface/transition_agent.py "View geographic distribution under high support policy"

# GCP-16 examples
python llm_interface/transition_agent.py "Monitor policy feedback loops for 15 years"
python llm_interface/transition_agent.py "Show how financial institutions respond to policy changes"
```

---

## 🎛️ Policy Scenarios

Green Credit Policy supports three policy scenarios with varying levels of government support:

| Policy Scenario | PV Subsidy Rate | Low-Interest Loan Rate | Tax Incentive | Description |
|-----------------|-----------------|------------------------|---------------|-------------|
| **low_support** | 10% | 5% | 5% | Minimal government intervention |
| **moderate_support** | 20% | 3% | 10% | Balanced incentive approach (baseline) |
| **high_support** | 30% | 2% | 15% | Aggressive renewable energy push |

---

## 🌍 Climate Scenarios

Climate scenarios affect **solar radiation availability**, which directly impacts PV energy production and financial attractiveness.

| Scenario | RCP Code | Description | Warming Level | Solar Impact |
|----------|----------|-------------|---------------|--------------|
| **RCP 2.6** | rcp26 | Low emissions pathway | ~2°C by 2100 | Changes in cloud cover patterns |
| **RCP 4.5** | rcp45 | Medium emissions (baseline) | ~3°C by 2100 | Baseline solar radiation |
| **RCP 8.5** | rcp85 | High emissions pathway | ~4-5°C by 2100 | Variable solar potential |

**Why Climate Matters for PV Adoption:**
- ☀️ **Solar radiation** varies by climate scenario (rcp26/rcp45/rcp85)
- ⚡ **PV energy production** = Solar potential × System capacity
- 💰 **Financial attractiveness** = Higher solar → More energy → Better ROI
- 📈 **Adoption decisions** = Better ROI → Higher adoption probability

**Default**: If not specified, runs **ALL climate scenarios** (rcp26, rcp45, rcp85) for comprehensive climate comparison under the specified policy.

---

## 🏗️ Multi-Level Agent-Based Modeling Architecture

GCP uses a **3-level ML-ABM** framework:

### Individual Level: LandownerAgent
- **Decision**: Adopt PV or not?
- **Factors**:
  - Financial situation (poor, moderate, wealthy)
  - Risk tolerance (low, moderate, high)
  - Perceived ROI and payback period
  - Social influence (peer adoption)
  - Loan approval status
- **Actions**:
  - Apply for green loans
  - Install PV systems
  - Pay loan installments
  - Generate energy savings

### Market Level: FinancialInstitutionAgent
- **Decision**: Approve or deny loans?
- **Factors**:
  - Credit score assessment
  - Debt-to-income ratio
  - Loan-to-value ratio
  - Portfolio risk tolerance
  - Policy loan rate incentives
- **Actions**:
  - Evaluate loan applications
  - Manage loan portfolios
  - Adjust risk thresholds
  - Track default rates
  - Report to policymakers

### Policy Level: PolicymakerAgent
- **Decision**: Adjust policy parameters?
- **Factors**:
  - Current adoption rates
  - Policy effectiveness metrics
  - Budget constraints
  - Environmental goals
  - FI portfolio health
- **Actions**:
  - Set subsidy rates
  - Adjust loan interest rates
  - Modify tax incentives
  - Evaluate policy effectiveness
  - Respond to adoption trends

### Cross-Scale Interactions

**Downward Flow** (Policy → Market → Individual):
- Policymaker sets subsidy rates → FIs adjust loan terms → Landowners evaluate ROI

**Upward Flow** (Individual → Market → Policy):
- Landowners adopt PV → FIs adjust risk models → Policymaker evaluates effectiveness

**Lateral Flow** (within levels):
- Landowners influence peers (social adoption)
- FIs compete on loan terms
- Policymakers coordinate with regional authorities

---

## 📊 Key Metrics Tracked

### Adoption Metrics
- PV adoption rate (%)
- Total installed capacity (kW)
- Number of installations
- Adoption rate by demographics

### Financial Metrics
- Loan approval rate (%)
- Default rate (%)
- Total subsidy spending (€)
- Average ROI (%)
- Average payback period (years)
- Cost per adoption (€/installation)

### Energy Metrics
- Annual energy savings (kWh)
- Feed-in tariff revenue (€/year)
- Total energy generated (kWh)
- Carbon emissions avoided (tons CO2)

### Policy Effectiveness
- Adoption efficiency (installations per € spent)
- Budget utilization rate
- Regional coverage (% of area covered)
- Demographic equity (adoption across income levels)

### Financial Institution Metrics
- Portfolio risk score
- Active loan count
- Loan volume (€)
- Credit threshold evolution
- Approval rate trends

---

## 📁 Output Directory Structure

```
use_cases/gcp/results/
├── gcp_03/                                    # PV adoption simulation
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
│       ├── rcp45_low_support_demographic_breakdown.html
│       ├── rcp45_moderate_support_demographic_breakdown.html
│       ├── rcp45_high_support_demographic_breakdown.html
│       └── rcp45_policy_comparison.html
│
├── gcp_07/                                    # Geographic distribution
│   ├── rcp45/
│   │   └── moderate_support/
│   │       └── rcp45_moderate_support_results.txt
│   └── visualizations/
│       └── rcp45_moderate_support_pv_map.html
│
└── gcp_16/                                    # Policy feedback loops
    ├── rcp45/
    │   ├── low_support/
    │   │   └── rcp45_low_support_results.txt
    │   ├── moderate_support/
    │   │   └── rcp45_moderate_support_results.txt
    │   └── high_support/
    │       └── rcp45_high_support_results.txt
    └── visualizations/
        ├── rcp45_low_support_feedback_loop.html
        ├── rcp45_moderate_support_feedback_loop.html
        ├── rcp45_high_support_feedback_loop.html
        └── rcp45_policy_comparison.html
```

---

## 🎯 Advanced Features

### ESA Compliance (GCP-03)
**Demographic Breakdown Analysis** ensures compliance with ESA (European Space Agency) requirements:
- Agent-level heterogeneity tracking
- Financial situation stratification
- Risk tolerance profiling
- Adoption equity analysis
- ROI distribution by demographics

### Bidirectional Feedback Loops (GCP-16)
**Full feedback loop implementation**:
- Policy adjustments based on adoption performance
- FI risk model adaptations based on defaults
- Loan term modifications based on portfolio health
- Adoption response to policy changes
- System-level equilibrium analysis

### Realistic Financial Modeling
- Credit score calculation (FICO-style)
- Debt-to-income ratio assessment
- Loan-to-value ratio analysis
- Installation cost with terrain factors
- Energy production modeling
- Feed-in tariff integration

---

## 🔬 Testing & Validation

### Minimal Test (Fast - 2 minutes)
```bash
python use_cases/gcp/run_gcp.py --query gcp_03 --scenario rcp45 --policy moderate_support --years 5 --landowners 10
```

### Standard Test (Recommended - 5 minutes)
```bash
python use_cases/gcp/run_gcp.py --scenario rcp45 --years 10 --landowners 20
```

### Comprehensive Test (Full Analysis - 15 minutes)
```bash
python use_cases/gcp/run_gcp.py --scenario rcp45 --years 15 --landowners 50 --financial-institutions 3
```

### Feedback Loop Analysis (20+ minutes)
```bash
python use_cases/gcp/run_gcp.py --query gcp_16 --scenario rcp45 --years 20 --landowners 50
```

---

## 📚 Related Documentation

- [EXAMPLE_CASES_PROMPTS.md](EXAMPLE_CASES_PROMPTS.md) - Quick reference commands
- [config.yaml](config.yaml) - Configuration parameters
- [../../CLAUDE.md](../../CLAUDE.md) - Project documentation
- [../../MULTILEVEL-ABM.md](../../MULTILEVEL-ABM.md) - Multi-level architecture guide

---

## 🐛 Common Issues & Solutions

### Low Adoption Rates
**Issue**: PV adoption rate is very low (< 5%)

**Solutions**:
- ✅ Use `high_support` policy scenario
- ✅ Increase simulation duration (15-20 years)
- ✅ Check FI loan approval rates
- ✅ Verify subsidy rates are applying correctly

### No Feedback Loop Visible (GCP-16)
**Issue**: Policy adjustments not visible

**Solutions**:
- ✅ Run longer simulations (20+ years)
- ✅ Increase landowner count (50+)
- ✅ Verify policy effectiveness threshold is met
- ✅ Check that adoption rates trigger policy adjustments

### Geographic Clustering Issues (GCP-07)
**Issue**: All PV installations in one area

**Solutions**:
- ✅ Increase landowner count (50+)
- ✅ Check spatial distribution of landowner locations
- ✅ Verify financial situation is distributed across demographics
- ✅ Run longer simulations to see diffusion

---

**Questions?** Check simulation outputs for detailed insights, or review generated visualizations for interactive exploration!
