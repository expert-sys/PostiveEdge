# Sports Value Engine - Quick Start Guide

## 🚀 Getting Started (30 seconds)

### Windows Users
1. **Double-click** `run.bat` in the project folder
2. Choose option from menu (try `4` for sample data demo)

### Mac/Linux Users
```bash
python main.py
```

## 📊 What It Does

The Value Engine analyzes sports betting markets to find **+EV (positive expected value)** opportunities by comparing:
- **Historical probability**: Based on past performance data
- **Bookmaker odds**: Current odds offered

If historical probability > bookmaker probability = **VALUE FOUND** ✓

## 💡 Quick Examples

### Example 1: Manual Analysis
```
Event: Player to Score
Historical: 7 goals in 10 games (70%)
Bookmaker Odds: 1.80 (55.56% implied)
Result: +14.44% value ✓ BUY
```

### Example 2: CSV File Analysis
```bash
1. Choose option 2 (CSV file)
2. Load: sample_player_data.csv
3. Outcome field: goals
4. Enter odds: 1.95
→ Get instant analysis
```

### Example 3: Batch Markets
```bash
1. Choose option 5 (Batch)
2. Load: sample_markets.json
→ Analyze 5+ markets instantly
```

## 📁 Input Formats

### CSV Format
```
date,opponent,location,goals,assists
2024-01-15,Manchester,home,1,0
2024-01-12,Liverpool,away,0,1
```

### JSON Format
```json
{
  "event_type": "Player to Score",
  "outcomes": [1, 0, 1, 1, 0, 1],
  "bookmaker_odds": 2.50,
  "outcome_type": "binary"
}
```

## 🔢 Key Metrics Explained

| Metric | What It Means |
|--------|---------------|
| **Probability** | Likelihood based on history (0-100%) |
| **Implied Odds** | Odds that match historical probability |
| **Bookmaker Odds** | What the sportsbook is offering |
| **Value %** | How much better than fair (>0 is good) |
| **EV** | Expected profit per $1 staked |
| **EV per $100** | Expected profit per $100 staked |

## ✅ Value Decision Matrix

```
Value % = +5%  →  ✓ Likely value (check sample size)
Value % = +10% →  ✓✓ Strong value
Value % = +20% →  ✓✓✓ Excellent value (but risky - verify data)
Value % = -5%  →  ✗ Skip it
Value % = -10% →  ✗✗ Bad bet
```

## 📈 EV Interpretation

```
EV = +0.50  →  Expected +$50 per $100 staked
EV = +0.25  →  Expected +$25 per $100 staked  
EV = 0.00   →  Fair bet
EV = -0.25  →  Expected -$25 per $100 staked
```

**Rule:** Only bet if EV is meaningfully positive (0.05+) after accounting for fees.

## 🎯 Sample Size Matters

```
Sample Size < 5    →  ⚠️ Very unreliable
Sample Size 5-10   →  ⚠️ Somewhat unreliable  
Sample Size 10-20  →  ✓ Reasonable
Sample Size 20+    →  ✓✓ Reliable
```

The engine shows a warning if sample is too small.

## 💻 Python API Usage

### Quick Analysis (1 line)
```python
from value_engine import analyze_simple_market

result = analyze_simple_market(
    event_type="Player to Score",
    historical_outcomes=[1, 0, 1, 1, 0, 1],
    bookmaker_odds=2.50
)
print(result)
```

### Load CSV and Analyze
```python
from data_processor import DataProcessor
from value_engine import analyze_simple_market

data = DataProcessor.load_csv("games.csv")
goals = DataProcessor.extract_outcomes(data, "goals_scored")

result = analyze_simple_market(
    event_type="Goals",
    historical_outcomes=goals,
    bookmaker_odds=1.95
)
```

### Advanced: Weighted Recency
```python
from value_engine import ValueEngine, HistoricalData, MarketConfig, OutcomeType
from data_processor import DataProcessor

engine = ValueEngine()
weights = DataProcessor.calculate_recency_weights(data, decay_factor=0.95)

hist_data = HistoricalData(outcomes=goals, weights=weights)
config = MarketConfig(
    event_type="Goals",
    outcome_type=OutcomeType.BINARY,
    bookmaker_odds=1.95
)

result = engine.analyze_market(hist_data, config)
```

## ⚙️ Configuration Options

### Minimum Sample Size (default: 5)
```python
analyze_simple_market(
    ...,
    minimum_sample_size=10  # Require 10+ observations
)
```

### Continuous Outcomes with Threshold
```python
analyze_simple_market(
    event_type="Over 2.5 Assists",
    historical_outcomes=[1, 3, 2, 1, 4],
    bookmaker_odds=1.90,
    outcome_type="continuous",
    threshold=2.5  # Count 2.5+ as success
)
```

### Weighted by Recency
```python
from data_processor import DataProcessor

outcomes = [1, 0, 1, 1, 0]
weights = DataProcessor.calculate_recency_weights(
    outcomes,
    decay_factor=0.95  # Recent games weighted higher
)

result = analyze_simple_market(
    ...,
    weights=weights
)
```

## 🚨 Common Mistakes

### ❌ Mistake 1: Betting Without Value
```
Prob: 45%, Odds: 1.50 (67% implied)
→ -22% value, don't bet!
```

### ❌ Mistake 2: Ignoring Sample Size
```
Data: 2 goals in 2 games (100%)
→ Unreliable! Need 10+ games
```

### ❌ Mistake 3: Betting Tiny Value
```
Value: +0.5%, EV: +0.001
→ After fees, it's break-even. Skip it.
```

### ✅ Correct Approach
```
1. Historical data: ✓ 15+ games
2. Value found: ✓ >5%
3. EV positive: ✓ >0.05 after fees
4. Edge is real: ✓ Consider context
→ Place bet
```

## 📊 Demo Scenarios

Run these to see the engine in action:

```bash
python demo.py
```

Includes:
- Simple player analysis
- Over/under goals
- CSV data analysis
- Batch market evaluation
- Odds comparison

## 🔍 Troubleshooting

### "Python not found" on Windows
- Install from python.org
- Check "Add Python to PATH"
- Restart computer

### "File not found"
- CSV/JSON must be in project folder
- Use full path: `C:\path\to\file.csv`

### "Column not found"
- Check CSV headers match exactly
- Field names are case-sensitive

### "Invalid odds"
- Odds must be > 1.0
- Use decimal format: 1.50, 2.00, etc.
- Not: -110, +150 (use conversion tool first)

## 📚 Learn More

- **README.md** - Full documentation
- **test_engine.py** - Code examples
- **demo.py** - Real use cases
- **value_engine.py** - Implementation details

## ⭐ Pro Tips

1. **Combine Multiple Data Sources**: Historical avg + opponent strength
2. **Track Results**: Record predictions vs. actual outcomes
3. **Validate Regularly**: Update data frequently
4. **Account for Context**: Injuries, form changes, schedule density
5. **Diversify Markets**: Don't rely on single event type
6. **Bankroll Management**: Only bet a small % per market

## 🎯 Next Steps

1. **Run the demo**: `python demo.py`
2. **Try manual input**: Option 1 in main menu
3. **Load your data**: Option 2 (CSV) or 3 (JSON)
4. **Start finding value**: Track results over time

---

**Happy value hunting!** 🎲📈

For questions or issues, check the README.md or examine the code in value_engine.py
