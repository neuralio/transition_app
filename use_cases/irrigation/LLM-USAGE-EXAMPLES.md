# IRR-US-01 LLM Interface Usage Examples

## How to Use Temporal Phenology Analysis via LLM

---

## 🎯 Quick Answer

**For STANDARD classification (single-date, fast)**:
```
"Classify my fields using bare soil analysis from July 12 to July 16, 2025"
```

**For PHENOLOGY analysis (time-series, advanced)**:
```
"Analyze temporal phenology for my fields from May to September 2025"
```

**For PHENOLOGY with specific season**:
```
"Show me harvested crop patterns from June to September 2024"
```

---

## 📖 Detailed Examples

### 1. Standard Classification (Original Behavior)

These queries use **single-date composite** classification (fast):

```
"Classify my fields using bare soil analysis from July 12 to July 16, 2025"

"Classify bare soil for 20 parcels from 2024-06-01 to 2024-06-30"

"Show me NDVI classification for my drawn polygon from August 1 to August 15"

"Identify fallow fields from 2024-07-10 to 2024-07-20"
```

**When to use**: Quick classification, short date ranges (days to weeks)

---

### 2. Temporal Phenology Analysis (NEW!)

These queries trigger **time-series phenology mode** automatically:

#### Basic Phenology Queries
```
"Analyze temporal phenology for my fields from May to September 2025"

"Show me phenology patterns from June to September 2024"

"Detect harvested crops using time-series analysis from May 1 to September 30, 2024"

"Analyze NDVI evolution throughout the season from May to September"
```

#### Specific Pattern Detection
```
"Show me harvested crop patterns from June to September 2024"

"Identify truly fallow fields using temporal analysis from May to August"

"Detect flooding patterns in rice fields from May to July"

"Analyze seasonal vegetation evolution from April to October"
```

#### With Coordinates
```
"Analyze temporal phenology at (40.6, 22.8) from May to September 2024"

"Show harvest patterns at (40.5, 22.7) and (40.6, 22.8) from June to September"
```

**When to use**: Distinguish harvested from fallow, detect seasonal patterns, analyze entire growing season

---

## 🔑 Keywords That Trigger Phenology Mode

The LLM automatically detects these keywords and enables phenology:

- **"phenology"** - Direct request
- **"temporal"** - Time-series analysis
- **"time-series" / "time series"** - Multi-date analysis
- **"harvested" / "harvest"** - Crop harvest detection
- **"season" / "seasonal"** - Full season analysis
- **"evolution"** - NDVI evolution over time
- **"pattern" / "patterns"** - Temporal pattern recognition
- **"throughout"** - Analysis across entire period

**Example**: Any query with these keywords will automatically use phenology mode:
- "Show me **seasonal** patterns..." ✅ Phenology enabled
- "Analyze **harvest** patterns..." ✅ Phenology enabled
- "NDVI **evolution** from May..." ✅ Phenology enabled

---

## 📅 Date Range Recommendations

### Standard Mode (Single-Date)
- **Short ranges**: 1-30 days
- **Example**: "July 12 to July 16" (5 days)
- **Purpose**: Snapshot classification at specific moment

### Phenology Mode (Time-Series)
- **Long ranges**: 60+ days (entire season)
- **Example**: "May to September" (150 days)
- **Purpose**: Detect temporal patterns across season
- **Minimum**: At least 30 days for meaningful temporal analysis

---

## 🎨 What You Get

### Standard Mode Output
- Classification map (GeoJSON)
- Text report with class distribution
- Pie chart (class percentages)
- NDVI histogram
- Interactive map

### Phenology Mode Output (Additional)
- **Time-series charts**: NDVI/NDWI evolution graphs
- **Pattern classification**: Harvested, fallow, flooded, vegetated
- **Phenology metrics**: Max NDVI, drop rate, flooding days
- **Pattern distribution chart**: Bar chart of detected patterns
- **Enhanced report**: Temporal pattern details per parcel

---

## 🧪 Example Conversation Flows

### Flow 1: Quick Classification
```
User: "Classify my fields from July 12 to July 16, 2025"

System: ✅ Classification Complete
- Mode: Random sampling (20 parcels)
- Vegetated: 12 parcels (60%)
- Bare soil: 8 parcels (40%)
- Flooded: 0 parcels (0%)
```

### Flow 2: Phenology Analysis
```
User: "Analyze temporal phenology for my fields from May to September 2024"

System: 🔍 Detected phenology keywords - enabling temporal analysis mode
✅ Phenology Analysis Complete
- Temporal observations: 15
- Harvested crops: 8 parcels (40%)
- Truly fallow: 3 parcels (15%)
- Vegetated: 6 parcels (30%)
- Irrigated/flooded: 3 parcels (15%)

📁 Interactive charts generated:
- NDVI/NDWI evolution time-series
- Pattern distribution bar chart
```

### Flow 3: Mixed Query (Phenology with Coordinates)
```
User: "Show me harvest patterns at (40.6, 22.8) from June to September 2024"

System: 🔍 Detected phenology keywords - enabling temporal analysis mode
📍 Extracted 1 coordinate from query
✅ Phenology Analysis Complete
- Mode: Point coordinates (1 location)
- Pattern detected: Harvested crop (confidence: 0.92)
- Max NDVI: 0.74 (July 15)
- End NDVI: 0.18 (September 30)
- NDVI drop rate: 0.037/day
```

---

## ⚙️ Advanced: Explicit Parameters

You can also explicitly control phenology parameters (advanced users):

```python
# Via Python API
from llm_interface.irrigation_tool import IrrigationTool, IrrigationQueryInput

result = tool.run(IrrigationQueryInput(
    query="Classify my fields",
    start_date="2024-05-01",
    end_date="2024-09-30",
    parcels=10,
    enable_phenology=True,
    temporal_window_days=15  # Larger windows = fewer observations but more cloud-free data
))
```

**Temporal Window Trade-off**:
- **Smaller windows** (5-7 days): More observations, but more cloud interference
- **Default** (10 days): Balanced
- **Larger windows** (15-20 days): Fewer observations, but more cloud-free composites

---

## 🚫 What NOT to Say

These will **NOT** trigger phenology mode (standard mode instead):

```
❌ "Classify fields from July 12 to July 16" - Too short, no phenology keywords
❌ "Show me NDVI for my polygon" - No date range
❌ "Identify bare soil on August 1" - Single date implied
```

---

## 💡 Tips

1. **Use full season dates** for phenology: "May to September" not "July 12 to July 16"
2. **Include keywords** explicitly: "phenology", "temporal", "harvested", "seasonal"
3. **Longer ranges** = Better temporal patterns (minimum 30 days, ideal 90+ days)
4. **Coordinates work too**: Phenology analysis works with specific GPS points
5. **Natural language**: Just describe what you want to see (evolution, patterns, harvest)

---

## 📚 Related Documentation

- [IRR-US-01-IMPLEMENTATION-SUMMARY.md](IRR-US-01-IMPLEMENTATION-SUMMARY.md) - Technical implementation details
- [PAPER_METHODOLOGY.md](PAPER_METHODOLOGY.md) - Scientific methodology
- [PRD.md](PRD.md) - Product requirements

---

## ✅ Summary

| Query Type | Example | Output Mode |
|------------|---------|-------------|
| **Standard** | "Classify fields from July 12 to July 16" | Single-date composite |
| **Phenology (keyword)** | "Analyze **phenology** from May to September" | Time-series analysis |
| **Phenology (harvest)** | "Show **harvested** crops from June to September" | Time-series analysis |
| **Phenology (seasonal)** | "Analyze **seasonal** patterns from May to September" | Time-series analysis |

**The key is**: Include phenology-related keywords for time-series mode, or use short date ranges for quick classification!
