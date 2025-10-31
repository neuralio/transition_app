# RL Usage Guide

## Two Operations

### 1. Single RL Simulation (`run_mlu.py --use-rl`)

Runs ONE simulation using the trained RL model.

```bash
python use_cases/mlu/run_mlu.py --use-rl \
  --rl-model use_cases/mlu/rl/models/rl02/rl02_rcp45_final.zip \
  --scenario rcp45 --years 10 --parcels 20
```

- **Output**: `use_cases/mlu/results/rcp45/` (CSV files only)
- **Speed**: Fast (1 simulation)
- **Purpose**: See RL performance alone

---

### 2. RL vs Rule-Based Comparison (`compare_rl_vs_rules.py`)

Runs TWO simulations (RL + Rule-based) and generates comparison dashboard.

**From project root**:
```bash
python use_cases/mlu/rl/compare_rl_vs_rules.py \
  --scenario rcp45 --years 5 --parcels 10 \
  --rl-model use_cases/mlu/rl/models/rl02/rl02_rcp45_final.zip
```

**From rl/ directory**:
```bash
cd use_cases/mlu/rl
python compare_rl_vs_rules.py \
  --scenario rcp45 --years 5 --parcels 10 \
  --rl-model models/rl02/rl02_rcp45_final.zip
```

- **Output**: `use_cases/mlu/rl/results/rl_comparison/comparison_dashboard.html`
- **Speed**: Slower (2 simulations + comparison)
- **Purpose**: Benchmark RL vs traditional decision-making

---

## Key Differences

| Feature | `run_mlu.py --use-rl` | `compare_rl_vs_rules.py` |
|---------|----------------------|--------------------------|
| Simulations | 1 (RL only) | 2 (RL + Rules) |
| Output | CSV files | Dashboard + charts |
| Location | `use_cases/mlu/results/` | `use_cases/mlu/rl/results/rl_comparison/` |
| Speed | Fast | Slower |

---

## Trained Models

Located in `use_cases/mlu/rl/models/rl02/`:
- `rl02_rcp45_final.zip` (150KB, trained Oct 11, 2024)
- 40+ checkpoints (every 5K steps from 5K to 200K)

---

## Example Results

**Rule-Based**: €348,758 total income, 1,184 tons (100% wheat)
**RL-Based**: €453,662 total income (+30%), 85 tons (90-100% solar)

RL model learned to prioritize solar installations for higher long-term profitability.


## LLM queries

Single Scenario:
----------------
# Optimistic (Low Warming)
"Compare RL versus rule-based under optimistic scenario for 10 years with 20 parcels"

# Moderate (Medium Warming) - CURRENT
"Compare RL versus rule-based under moderate scenario for 5 years with 10 parcels"

# Pessimistic (High Warming)
"Compare RL versus rule-based under pessimistic scenario for 20 years with 30 parcels"

All Scenarios:
--------------
# Compare across ALL 3 climate scenarios
"Compare RL versus rule-based for 10 years with 20 parcels"
# → Runs rcp26, rcp45, rcp85
# → Outputs 6 files (3 HTML dashboards + 3 TXT reports)
Short-term vs Long-term:
# Short-term (5 years)
"Compare RL versus rule-based for 5 years"

# Medium-term (20 years)
"Compare RL versus rule-based for 20 years"

# Long-term (50 years - default)
"Compare RL versus rule-based for 50 years"

Scale Variations:
# Small scale
"Compare RL with 10 parcels for 5 years"

# Medium scale
"Compare RL with 30 parcels for 10 years"

# Large scale
"Compare RL with 50 parcels for 20 years"