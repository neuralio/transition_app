# MLU Use Case Architecture

## Directory Structure

```
use_cases/mlu/
├── agents/                    # MLU-specific agents
│   ├── farmer_agent.py       # Individual farmer crop decisions
│   ├── land_parcel_agent.py  # Farm vs Solar PV decisions
│   ├── pv_agent.py          # Solar PV installations
│   ├── collective_agent.py   # Farmer cooperatives
│   ├── market_agent.py      # Agricultural commodity markets
│   └── policymaker_agent.py # Agricultural policy agents
│
├── models/                    # MLU-specific models
│   └── landuse_model.py      # Land-use suitability model
│
├── scripts/                   # MLU utilities
│   ├── run_mlu_simulation.py # Simulation runner
│   ├── result_collector.py   # Data collection
│   ├── visualizer.py        # Charts & plots
│   └── gis_visualizer_v2.py # GIS maps
│
├── results/                   # Simulation outputs (gitignored)
│
├── config.yaml               # Configuration file
├── config_loader.py          # Config loader utility
├── run_mlu.py               # Main CLI entry point
└── README.md                # Documentation
```

## Shared Framework

The MLU use case uses the generic **Multi-Level ABM Framework** from backend:

```
backend/simulation/framework/
└── orchestrator.py           # Generic 4-level coordination pattern
```

This orchestrator manages cross-scale interactions:
- **Downward flow**: Policy → Market → Community → Individual
- **Upward flow**: Individual → Community → Market → Policy
- **Lateral flow**: Peer interactions within each level

## Independence from Other Use Cases

The MLU agents and models are **completely independent** from other use cases:

- **CCA (Climate Change Adaptation)** will have its own agents in `use_cases/cca/agents/`
- **GCP (Green Credit Policy)** will have its own agents in `use_cases/gcp/agents/`

Each use case has different agent types with different behaviors:
- MLU: Farmers, agricultural markets, agricultural subsidies
- CCA: Households, water markets, climate policies
- GCP: Homeowners, energy markets, green subsidies

Only the orchestrator framework is shared - the agents are use-case-specific.

## Import Paths

All imports now use use-case-specific paths:

```python
# MLU model
from use_cases.mlu.models.landuse_model import LandUseModel

# MLU agents
from use_cases.mlu.agents.farmer_agent import FarmerAgent
from use_cases.mlu.agents.land_parcel_agent import LandParcelAgent

# Shared framework
from backend.simulation.framework.orchestrator import MultiLevelOrchestrator

# Shared data loaders
from backend.data.loaders.data_loader import load_crop_suitability
```

## Running the Simulation

```bash
# From project root
python use_cases/mlu/run_mlu.py

# Configuration is in use_cases/mlu/config.yaml
```

All data paths and parameters are configured in `config.yaml` - no hardcoding!
