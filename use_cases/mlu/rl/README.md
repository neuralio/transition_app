# RL-02: Reinforcement Learning for Land-Use Decisions

## Quick Start

### 1. Train an RL Model

```bash
cd /home/ggous/Models/Transition/use_cases/mlu/rl

# Quick training (testing - 5-10 min)
python train_rl02.py --scenario rcp45 --timesteps 50000

# Recommended (1-2 hours)
python train_rl02.py --scenario rcp45 --timesteps 500000

# Best quality (3-4 hours)
python train_rl02.py --scenario rcp45 --timesteps 1000000
```

**Output:** `models/rl02/rl02_rcp45_final.zip`

---

### 2. Run Simulation with Trained Model

```bash
cd /home/ggous/Models/Transition/use_cases/mlu

# Run single simulation with RL
python run_mlu.py --use-rl --rl-model rl/models/rl02/rl02_rcp45_final.zip --scenario rcp45
```

---

### 3. Compare RL vs Rule-Based

```bash
cd /home/ggous/Models/Transition/use_cases/mlu/rl

# Compare RL vs traditional rule-based decisions
python compare_rl_vs_rules.py --scenario rcp45 --years 50 --parcels 30 --rl-model models/rl02/rl02_rcp45_final.zip

# Output: results/rl_comparison/comparison_dashboard.html
```

---

## Files

- `train_rl02.py` - Train PPO agent
- `compare_rl_vs_rules.py` - Compare RL vs Rule-based
- `mlu_env.py` - Gymnasium environment wrapper
- `rl_policy.py` - RL policy loader
- `models/rl02/` - Saved models directory

---

## Notes

- **Algorithm:** PPO (Proximal Policy Optimization)
- **State:** 11D vector (LUSA scores, weather, soil, prices, subsidies)
- **Actions:** 0=WHEAT, 1=MAIZE, 2=SOLAR
- **Reward:** Economic profit + sustainability bonus
