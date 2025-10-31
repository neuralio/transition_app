# CCA Example Commands

**Climate Scenarios** (both naming conventions work):
- **optimistic** or `rcp26` - Low Warming (~2°C)
- **moderate** or `rcp45` - Medium Warming (~3°C)
- **pessimistic** or `rcp85` - High Warming (~4-5°C)

---

## 🔑 CCA vs MLU: Important Distinction

**CCA focuses on CROP PERFORMANCE** (yield, adaptation, resilience):
- Use keywords: **"yield"**, **"productivity"**, **"climate adaptation"**, **"resilience"**
- Example: "Simulate wheat **YIELD** under moderate scenario"
- Example: "Show how **crop adaptation** strategies work"

**MLU focuses on LAND ALLOCATION** (agriculture vs solar PV):
- Use keywords: **"land use"**, **"parcels"**, **"markets"**, **"categorize"**
- Example: "Simulate land use under moderate scenario with 15 parcels"
- Example: "Simulate wheat at (40.5, 22.7)" (coordinates without "yield" → land use)

**Critical**: Coordinates alone → MLU (land use). Add "YIELD" keyword for CCA!
- ❌ "Simulate wheat at (40.5, 22.7)" → MLU-05 (land use)
- ✅ "Simulate wheat **YIELD** at (40.5, 22.7)" → CCA-03 (crop performance)

---

## Direct CLI (`run_cca.py`)

### CCA-03: Simulate Crop Yield Under Climate Change

**NOTE**: CCA-03 is about **individual farmer decisions** - multi-level parameters (collectives, markets, policymakers) are **optional** and NOT required. If you need cross-scale interactions, use **CCA-10** instead.

```bash
# User-friendly scenario names (RECOMMENDED)
python use_cases/cca/run_cca.py --query cca_03 --crop WHEAT --scenario moderate --years 10 --farmers 10

# Traditional RCP codes (still supported)
python use_cases/cca/run_cca.py --query cca_03 --crop WHEAT --scenario rcp45 --years 10 --farmers 10

# Different crop
python use_cases/cca/run_cca.py --query cca_03 --crop MAIZE --scenario pessimistic --years 5 --farmers 5

# OPTIONAL: With custom multi-level settings (only if you explicitly want them)
python use_cases/cca/run_cca.py --query cca_03 --crop WHEAT --scenario moderate --farmers 20 --collectives 3 --markets 2 --policies 1

# ADVANCED: User-specified farmer locations with initial crops (NEW - 2025-10-21)
# Coordinates must be within Thessaloniki bounds (40.4-40.9°N, 22.5-22.9°E)
python use_cases/cca/run_cca.py --query cca_03 --crop WHEAT --scenario moderate --years 10 \
  --farmer-locations '[{"lat":40.5,"lon":22.7,"crop":"WHEAT"},{"lat":40.6,"lon":22.8,"crop":"MAIZE"}]'

# With multi-level agents and custom locations
python use_cases/cca/run_cca.py --query cca_03 --crop WHEAT --scenario pessimistic --years 15 \
  --farmer-locations '[{"lat":40.55,"lon":22.65,"crop":"WHEAT"},{"lat":40.7,"lon":22.75,"crop":"MAIZE"}]' \
  --collectives 3 --markets 2 --policies 1
```

### CCA-04: Evaluate Land Suitability for PV Installations
```bash
# User-friendly scenario names (RECOMMENDED)
python use_cases/cca/run_cca.py --query cca_04 --scenario moderate --farmers 10 --pv-developers 2

# Traditional RCP codes (still supported)
python use_cases/cca/run_cca.py --query cca_04 --scenario rcp45 --farmers 10 --pv-developers 2

# More PV developers for comparison
python use_cases/cca/run_cca.py --query cca_04 --scenario optimistic --farmers 15 --pv-developers 3
```

### CCA-10: Simulate Cross-Scale Interactions
```bash
# User-friendly scenario names (RECOMMENDED) - scenario REQUIRED
python use_cases/cca/run_cca.py --query cca_10 --scenario moderate --years 10 --farmers 20

# Traditional RCP codes (still supported)
python use_cases/cca/run_cca.py --query cca_10 --scenario rcp45 --years 10 --farmers 20

# With custom multi-level settings
python use_cases/cca/run_cca.py --query cca_10 --scenario pessimistic --years 15 --farmers 30 --collectives 3 --markets 2 --policies 1

# Different scenarios
python use_cases/cca/run_cca.py --query cca_10 --scenario optimistic --years 10 --farmers 20
```

---

## LLM Interface (`transition_agent.py`)

### CCA-03: Simulate Crop Yield Under Climate Change

**NOTE**: CCA-03 focuses on **individual farmer decisions**. Multi-level parameters are optional. For cross-scale interactions, use CCA-10.

```bash
# ALL SCENARIOS (comparison mode) - NO scenario specified
python llm_interface/transition_agent.py "Simulate wheat yield for 10 years"
python llm_interface/transition_agent.py "Compare wheat yields across all climate scenarios for 10 years with 20 farmers"

# SINGLE SCENARIO - User-friendly scenario names (RECOMMENDED)
python llm_interface/transition_agent.py "Simulate wheat yield under moderate scenario for 10 years"
python llm_interface/transition_agent.py "Simulate wheat yield under moderate scenario for 10 years with 20 farmers"

# Different crop
python llm_interface/transition_agent.py "Show how maize yield changes under pessimistic scenario"

# OPTIONAL: With custom multi-level agents (only if explicitly needed)
python llm_interface/transition_agent.py "Simulate wheat yield with 50 farmers, 3 cooperatives, 2 market, and 2 policymakers under optimistic scenario"

# ADVANCED: User-specified farmer locations (NEW - 2025-10-21)
# IMPORTANT: Must include "YIELD" keyword to route to CCA-03 (otherwise goes to MLU land use)
# LLM can parse natural language coordinate patterns
python llm_interface/transition_agent.py "Simulate wheat YIELD at (40.5, 22.7) under moderate scenario for 10 years"

python llm_interface/transition_agent.py "Simulate crop YIELDS for 10 years: wheat at (40.5, 22.7), maize at (40.6, 22.8) under moderate scenario"

python llm_interface/transition_agent.py "Run wheat YIELD simulation with farmer at 40.55, 22.65 and maize at 40.7, 22.75 for 15 years under pessimistic scenario"

# NOTE: Without "YIELD" keyword, coordinates go to MLU land use simulation
# ❌ "Simulate wheat at (40.5, 22.7)" → Routes to MLU-05 (land use)
# ✅ "Simulate wheat YIELD at (40.5, 22.7)" → Routes to CCA-03 (crop performance)
```

### CCA-04: Evaluate Land Suitability for PV Installations
```bash
# User-friendly scenario names (RECOMMENDED)
python llm_interface/transition_agent.py "Evaluate PV suitability under moderate scenario with 2 energy companies"

# Traditional RCP codes (still supported)
python llm_interface/transition_agent.py "Evaluate land for PV installations with 2 energy companies"

# More specific
python llm_interface/transition_agent.py "Show which parcels are best for solar installations under optimistic scenario"
```

### CCA-10: Simulate Cross-Scale Interactions
```bash
# Scenario REQUIRED - specify climate context
python llm_interface/transition_agent.py "Show cross-scale interactions under moderate scenario for 10 years"

# With custom multi-level agents (MUST include "cross-scale" or "feedback" or "interaction" keywords!)
python llm_interface/transition_agent.py "Run cross-scale interactions with 20 farmers, 4 collectives, 2 markets, and 1 policymaker under pessimistic scenario"
python llm_interface/transition_agent.py "Simulate cross-scale interactions with 30 farmers, 5 cooperatives, 2 markets, and 2 policymakers under moderate scenario"
python llm_interface/transition_agent.py "Analyze farmer-to-policy interactions with 20 farmers and 3 collectives under optimistic scenario"

# Different scenarios (note: "cross-scale" or "interactions" keyword ensures CCA-10 routing)
python llm_interface/transition_agent.py "Show cross-scale interactions under pessimistic scenario"
python llm_interface/transition_agent.py "Simulate cross-scale interactions with 20 farmers under optimistic scenario"
```

---

## Output Directories

Results are saved to query-specific subdirectories:
- **CCA-03**: `/home/ggous/Models/Transition/use_cases/cca/results/cca_03/`
- **CCA-04**: `/home/ggous/Models/Transition/use_cases/cca/results/cca_04/`
- **CCA-10**: `/home/ggous/Models/Transition/use_cases/cca/results/cca_10/`

---

## Quick Reference

| Query | Use Case | Focus | Required Args | Optional Args |
|-------|----------|-------|---------------|---------------|
| `cca_03` | Crop Yield Simulation | **Individual farmer decisions** | `--crop`, `--scenario` | `--years`, `--farmers` (multi-level params NOT required) |
| `cca_04` | PV Suitability | Energy company evaluation | `--scenario` | `--farmers`, `--pv-developers` |
| `cca_10` | Cross-Scale Interactions | **Multi-level interactions** | `--scenario` | `--years`, `--farmers`, `--collectives`, `--markets`, `--policies` |

---

---

## Important Notes

- **CCA-03** is designed for **individual farmer decisions** (crop yield simulation). Multi-level parameters (collectives, markets, policymakers) are **optional** and will NOT be applied by default.
- **CCA-10** is designed for **cross-scale interactions** (Individual → Community → Market → Policy). Multi-level parameters are **core** to this user story and will use defaults if not specified.
- If you want to analyze multi-level interactions, use **CCA-10**, not CCA-03!

**Last Updated**: 2025-10-20
