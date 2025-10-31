# RL Implementation Strategy

## RL User Stories ARE NOT Use-Case Specific - They Are Cross-Cutting Enhancements

### **Use Cases** (3 distinct scenarios):
1. **CCA** (Climate Change Adaptation) - UC-CCA-01
2. **GCP** (Green Credit Policy Impact) - UC-GCP-01
3. **MLU** (Multi-Land Use) - UC-MLU-01

### **RL User Stories** (5 enhancement techniques):
1. **RL-01**: Policy Optimization
2. **RL-02**: Adaptive Agricultural Agents
3. **RL-03**: Market Strategies
4. **RL-04**: Climate Resilience
5. **RL-05**: Multi-Agent Feedback Loops

## RL-to-Use Case Mapping:

### ✅ **RL-01: Policy Optimization**
- **Applies to**: ALL use cases (CCA, GCP, MLU)
- **Why**: All use cases involve policymaker agents who need to optimize policies
- **CCA context**: Optimize climate adaptation policies
- **GCP context**: Optimize green credit/subsidy policies
- **MLU context**: Optimize land-use policies

### ✅ **RL-02: Adaptive Agricultural Agents**
- **Primary**: MLU, CCA
- **Secondary**: GCP (if farmers are included)
- **Why**: Focuses on farmer crop selection decisions
- **What we implemented**: MLU context (WHEAT/MAIZE/SOLAR decisions)

### ✅ **RL-03: Market Strategies**
- **Primary**: GCP
- **Secondary**: CCA (if energy markets included)
- **Not MLU**: MLU focuses on land suitability, not market investment strategies
- **Why**: Optimizes renewable energy investment decisions

### ✅ **RL-04: Climate Resilience**
- **Primary**: CCA
- **Secondary**: MLU (overlaps with RL-02)
- **Not GCP**: GCP focuses on policy incentives, not climate resilience
- **Why**: Adapts strategies based on climate feedback (droughts, floods)

### ✅ **RL-05: Multi-Agent Feedback Loops**
- **Applies to**: ALL use cases (CCA, GCP, MLU)
- **Why**: All use cases have multi-level ABM with feedback between agents
- **Universal**: Optimizes Individual ↔ Community ↔ Market ↔ Policy interactions

## Implementation Priority:

### **Phase 1: MLU Focus** (Current)
- ✅ **RL-02** (Adaptive Agricultural Agents) - DONE
- 🔜 **RL-01** (Policy Optimization) - Train PolicymakerAgent to optimize subsidies
- 🔜 **RL-05** (Multi-Agent Feedback) - Optimize cross-level interactions

### **Phase 2: GCP Focus** (Future)
- **RL-03** (Market Strategies) - Optimize PV investment decisions
- **RL-01** (Policy Optimization) - Optimize green credit policies
- **RL-05** (Multi-Agent Feedback) - Optimize farmer-bank-policy loops

### **Phase 3: CCA Focus** (Future)
- **RL-04** (Climate Resilience) - Adapt to droughts/floods dynamically
- **RL-02** (Adaptive Agricultural Agents) - Extend to CCA context
- **RL-01** (Policy Optimization) - Optimize climate adaptation policies
- **RL-05** (Multi-Agent Feedback) - Optimize collective-farmer-policy loops

---

## Quick Guide: RL-02 (MLU)

### 1. Train Model
```bash
cd use_cases/mlu/rl
python train_rl02.py --scenario rcp45 --timesteps 500000
# Output: models/rl02/rl02_rcp45_final.zip
```

### 2. Run Simulation with RL
```bash
cd use_cases/mlu
python run_mlu.py --use-rl --rl-model rl/models/rl02/rl02_rcp45_final.zip --scenario rcp45
```

### 3. Compare RL vs Rule-Based
```bash
cd use_cases/mlu/rl
python compare_rl_vs_rules.py --scenario rcp45 --years 50 --parcels 30
# Output: results/rl_comparison/comparison_dashboard.html
```

**See:** [use_cases/mlu/rl/README.md](use_cases/mlu/rl/README.md) for details
