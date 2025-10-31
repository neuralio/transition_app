# MLU Example Commands

**Climate Scenarios** (both naming conventions work):
- **optimistic** or `rcp26` - Low Warming (~2°C)
- **moderate** or `rcp45` - Medium Warming (~3°C)
- **pessimistic** or `rcp85` - High Warming (~4-5°C)

## Direct CLI (`run_mlu.py`)

### MLU-04: Categorize Land Parcels
```bash
# User-friendly scenario names (RECOMMENDED)
python use_cases/mlu/run_mlu.py --query mlu_04 --parcels 15 --scenario moderate

# Traditional RCP codes (still supported)
python use_cases/mlu/run_mlu.py --query mlu_04 --parcels 15 --scenario rcp45
```

### MLU-05: Multi-Level ABM Simulation
```bash
# User-friendly scenario names (RECOMMENDED)
python use_cases/mlu/run_mlu.py --query mlu_05 --years 10 --parcels 15 --scenario moderate

# With default multi-level agents (2 collectives, 1 market, 1 policymaker)
python use_cases/mlu/run_mlu.py --query mlu_05 --years 10 --parcels 15 --scenario rcp45

# Custom multi-level configuration
python use_cases/mlu/run_mlu.py --query mlu_05 --years 10 --parcels 15 --scenario rcp45 --collectives 5 --markets 2 --policies 3

# Without multi-level (individual agents only)
python use_cases/mlu/run_mlu.py --query mlu_05 --years 10 --parcels 15 --scenario rcp45 --disable-multilevel

# ADVANCED: User-specified farmer locations with initial crops (NEW - 2025-10-21)
# Coordinates must be within Thessaloniki bounds (40.4-40.9°N, 22.5-22.9°E)
python use_cases/mlu/run_mlu.py --query mlu_05 --scenario moderate --years 10 \
  --farmer-locations '[{"lat":40.5,"lon":22.7,"crop":"WHEAT"},{"lat":40.6,"lon":22.8,"crop":"MAIZE"}]'

# With multi-level agents and custom locations
python use_cases/mlu/run_mlu.py --query mlu_05 --scenario pessimistic --years 15 \
  --farmer-locations '[{"lat":40.55,"lon":22.65,"crop":"WHEAT"},{"lat":40.7,"lon":22.75,"crop":"MAIZE"},{"lat":40.65,"lon":22.85,"crop":"WHEAT"}]' \
  --collectives 3 --markets 2 --policies 1
```

### MLU-07: Historical Benchmarking
```bash
# User-friendly scenario names (RECOMMENDED)
python use_cases/mlu/run_mlu.py --query mlu_07 --crop WHEAT --scenario moderate

# Traditional RCP codes (still supported)
python use_cases/mlu/run_mlu.py --query mlu_07 --crop WHEAT --scenario rcp45
```

### MLU-08: Future Climate Scenarios with Ensemble
```bash
# User-friendly scenario names (RECOMMENDED)
python use_cases/mlu/run_mlu.py --query mlu_08 --scenario moderate --ensemble-size 3

# With ensemble (3 realizations)
python use_cases/mlu/run_mlu.py --query mlu_08 --scenario rcp45 --ensemble-size 3

# Without ensemble (single run)
python use_cases/mlu/run_mlu.py --query mlu_08 --scenario rcp45 --no-ensemble
```

---

## LLM Interface (`transition_agent.py`)

### MLU-04: Categorize Land Parcels
**Note**: MLU-04 always shows ALL categories (WHEAT vs MAIZE vs SOLAR). You can mention a crop if you want, but results will compare all options.

**Year parameter**: Specify which year to categorize (default: 2050). Different scenarios show different climate impacts at the same year.

```bash
# User-friendly scenario names (RECOMMENDED)
python llm_interface/transition_agent.py "Categorize 15 land parcels for wheat under pessimistic scenario"

# With specific year (to see climate change impact)
python llm_interface/transition_agent.py "Categorize 15 land parcels in 2070 under pessimistic scenario"
python llm_interface/transition_agent.py "Categorize 15 land parcels in 2030 under optimistic scenario"

# Traditional RCP codes (still supported)
python llm_interface/transition_agent.py "Categorize 15 land parcels for wheat under RCP 8.5"

# Without scenario (shows all scenarios for comparison, year 2050)
python llm_interface/transition_agent.py "Categorize 15 land parcels"
```

### MLU-05: Multi-Level ABM Simulation
**Note**: MLU-05 simulates **all crops** (WHEAT + MAIZE + SOLAR) dynamically - parcels switch based on market conditions

```bash
# User-friendly scenario names (RECOMMENDED)
python llm_interface/transition_agent.py "Simulate land use under moderate scenario for 10 years with 15 parcels"
python llm_interface/transition_agent.py "Simulate crops under moderate scenario for 10 years with 15 parcels"

# With custom multi-level agents
python llm_interface/transition_agent.py "Simulate land use with 5 collectives, 2 markets, and 1 policymaker under moderate scenario for 7 years with 15 parcels"
python llm_interface/transition_agent.py "Run 20 parcels for 10 years with 4 cooperatives, 2 markets, and 3 policymakers under pessimistic scenario"
python llm_interface/transition_agent.py "Simulate crops for 20 years with 3 farmer groups, 2 markets, with 20 parcels and 1 policymaker under optimistic scenario"

# Alternative phrasings (all work - LLM understands context)
python llm_interface/transition_agent.py "Simulate wheat with 5 collectives, 2 markets, and 1 policymaker under moderate scenario for 7 years with 15 parcels"  # "wheat" indicates agricultural context, not wheat-only
python llm_interface/transition_agent.py "Simulate wheat under RCP 4.5 for 10 years with 15 parcels"  # Traditional RCP codes still supported

# ADVANCED: User-specified farmer locations (NEW - 2025-10-21)
# LLM can parse natural language coordinate patterns
python llm_interface/transition_agent.py "Simulate wheat at (40.5, 22.7) under moderate scenario for 10 years"

python llm_interface/transition_agent.py "Simulate 10 years: wheat at (40.5, 22.7), maize at (40.6, 22.8) under moderate scenario"

python llm_interface/transition_agent.py "Run simulation with wheat at 40.55, 22.65 and maize at 40.7, 22.75 for 15 years under pessimistic scenario"

# With multi-level agents
python llm_interface/transition_agent.py "Simulate wheat at (40.5, 22.7) with 3 collectives and 2 markets under pessimistic scenario for 15 years"

python llm_interface/transition_agent.py "Simulate 10 years: wheat at (40.5, 22.7), maize at (40.6, 22.8), wheat at (40.65, 22.85) with 5 collectives, 2 markets, and 1 policymaker under moderate scenario"
```

### MLU-07: Historical Benchmarking
```bash
# User-friendly scenario names (RECOMMENDED)
python llm_interface/transition_agent.py "Benchmark historical vs future land suitability for wheat under moderate scenario"

python llm_interface/transition_agent.py "Benchmark historical vs future land suitability"

python llm_interface/transition_agent.py "Historical vs future land suitability for wheat"

```

### MLU-08: Future Climate Scenarios with Ensemble
```bash
# User-friendly scenario names (RECOMMENDED)
python llm_interface/transition_agent.py "Show future climate scenarios for wheat under moderate scenario with ensemble size 3"

python llm_interface/transition_agent.py "Show future climate scenarios for wheat under moderate scenario with ensemble size 3 for 10 parcels for 5 years with 3 markets and 2 policy makers"

python llm_interface/transition_agent.py "Future climate for wheat with uncertainty quantification"

python llm_interface/transition_agent.py "Future climate under pessimistic scenario with 50 ensemble runs"

python llm_interface/transition_agent.py "Future climate for wheat with 5 collectives and 3 markets under pessimistic scenario"

python llm_interface/transition_agent.py "Simulate climate scenarios for maize for 20 years with 30 parcels, 6 collectives, 3 markets, and 2 policymakers with ensemble size 50"

python llm_interface/transition_agent.py "Show all future climate scenarios for wheat"

# Alternative phrasings
#"How does wheat suitability change under climate change with #ensemble?"
#"Analyze future climate scenarios with uncertainty"

```
