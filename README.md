# Sports Value Engine - Implied Probability & EV Calculator

A comprehensive Python engine for calculating implied probability, odds, and expected value (EV) for any sports market using historical performance data.

## Features

- **Implied Probability Calculation** - Binary and continuous outcomes
- **Odds Conversion** - Convert between probability and decimal odds
- **Value Rating** - Compare historical vs. bookmaker odds
- **Expected Value (EV)** - Calculate profit/loss expectation
- **Sample Size Handling** - Bayesian shrinkage and fallback strategies
- **Data Processing** - Load from CSV, JSON, or manual input
- **Batch Analysis** - Analyze multiple markets at once
- **Recency Weighting** - Give more weight to recent games
- **Opponent Adjustment** - Normalize by opponent strength
- **Home/Away Splits** - Separate analysis by location
- **Minutes Adjustment** - Normalize player stats by minutes played

## Installation

### Prerequisites
- Python 3.7 or higher
- No external dependencies required (uses only Python standard library)

### Setup

**Windows (Batch):**
```bash
run.bat
```

**Windows (PowerShell):**
```powershell
.\run.ps1
```

**Linux/Mac:**
```bash
python main.py
```

If you get Python not found errors on Windows, ensure Python is added to your PATH.

## Quick Start

### 1. Launch the Application
```bash
python main.py
```

### 2. Select an Option

#### Option 1: Manual Input
Enter outcomes manually (e.g., `1,0,1,1,0`) and bookmaker odds.

#### Option 2: CSV Analysis
Load historical data from CSV file with columns for dates, outcomes, opponents, etc.

#### Option 3: JSON Analysis
Load pre-formatted JSON files with market definitions.

#### Option 4: Sample Data
Generates sample player performance data for demonstration.

#### Option 5: Batch Analysis
Analyze multiple markets from a JSON array.

### Example: Manual Analysis

```
Event Type: Player to Score
Outcome Type: Binary (0/1)
Historical Outcomes: 1,0,1,1,0,1,0,1
Bookmaker Odds: 2.50

Results:
- Sample Size: 8
- Historical Probability: 62.5%
- Implied Odds: 1.60
- Bookmaker Odds: 2.50
- Value: +88% (HAS VALUE!)
- EV per $100: +$112.50
```

## Data Formats

### CSV Format
```csv
date,opponent,location,minutes_played,goals,assists
2024-01-15,Manchester United,home,90,1,0
2024-01-12,Liverpool,away,75,0,1
```

### JSON Format
```json
[
  {
    "event_type": "Player to Score",
    "outcomes": [1, 0, 1, 1, 0],
    "bookmaker_odds": 2.50,
    "outcome_type": "binary"
  }
]
```

## Concepts & Formulas

### Historical Probability

**Binary Outcomes:**
```
probability = successes / total_attempts
```

Example: 5 goals in 10 games = 0.50 (50%)

**Continuous Outcomes:**
```
probability = count(outcome >= threshold) / total
```

Example: 6 games with 2+ assists in 10 games = 0.60 (60%)

### Implied Odds

```
implied_odds = 1 / probability
```

- 50% probability → 2.00 odds
- 67% probability → 1.49 odds
- 25% probability → 4.00 odds

### Value Detection

```
bookmaker_probability = 1 / bookmaker_odds
value_percentage = (historical_prob - bookmaker_prob) * 100
has_value = (value_percentage > 0)
```

### Expected Value (EV)

```
EV = (probability × (odds - 1)) - (1 - probability)
```

For a $100 stake:
```
expected_return = EV × 100
```

**Interpretation:**
- EV > 0: Positive expected value (good bet)
- EV < 0: Negative expected value (bad bet)
- EV = 0: Fair bet

**Example:**
```
Probability: 60%
Bookmaker Odds: 2.50
EV = (0.60 × 1.50) - 0.40 = 0.90 - 0.40 = +0.50
Expected Return per $100: +$50
```

### Sample Size Handling

When sample size < minimum threshold:

1. **Binary Outcomes:** Apply Bayesian shrinkage
   ```
   adjusted_prob = (successes + prior_weight × prior) / (total + prior_weight)
   ```

2. **Continuous Outcomes:** Use fallback probability (default 0.5)

3. **Analysis Mark:** Results flagged as "insufficient sample"

## Python API

### Quick Analysis

```python
from value_engine import analyze_simple_market

analysis = analyze_simple_market(
    event_type="Player to Score",
    historical_outcomes=[1, 0, 1, 1, 0, 1],
    bookmaker_odds=2.50,
    outcome_type="binary"
)

print(analysis)
print(f"Has value: {analysis.has_value}")
print(f"EV per unit: {analysis.ev_per_unit}")
```

### Advanced Analysis

```python
from value_engine import ValueEngine, HistoricalData, MarketConfig, OutcomeType

engine = ValueEngine()

# Prepare data
data = HistoricalData(
    outcomes=[1, 0, 1, 1, 0, 1, 0, 1],
    weights=[0.1, 0.1, 0.1, 0.1, 0.1, 0.15, 0.15, 0.25]  # Recent games weighted higher
)

# Configure market
config = MarketConfig(
    event_type="Player to Score",
    outcome_type=OutcomeType.BINARY,
    bookmaker_odds=2.50,
    minimum_sample_size=5,
    use_recency_weighting=True
)

# Analyze
analysis = engine.analyze_market(data, config)
```

### Data Processing

```python
from data_processor import DataProcessor, SampleDataGenerator

# Load CSV
data = DataProcessor.load_csv("player_data.csv")

# Extract outcomes
outcomes = DataProcessor.extract_outcomes(data, "goals")

# Filter by window
recent_data = DataProcessor.filter_by_window(
    data,
    date_field="date",
    window_games=10
)

# Calculate weights for recency
weights = DataProcessor.calculate_recency_weights(data, decay_factor=0.95)

# Generate sample data for testing
sample_data = SampleDataGenerator.generate_sample_player_data(
    game_count=20,
    goal_probability=0.35
)
```

## Advanced Features

### Recency Weighting

Weight recent games more heavily using exponential decay:

```python
from data_processor import DataProcessor

weights = DataProcessor.calculate_recency_weights(
    data,
    date_field="date",
    decay_factor=0.95
)

analysis = analyze_simple_market(
    event_type="Event",
    historical_outcomes=outcomes,
    bookmaker_odds=2.50,
    weights=weights
)
```

### Opponent Strength Adjustment

Adjust probabilities based on opponent strength:

```python
from data_processor import DataProcessor

opponent_strengths = [0.85, 0.90, 0.65, 0.75, ...]  # 0-1 scale
adjusted_outcomes = DataProcessor.apply_opponent_adjustment(
    outcomes,
    opponent_strengths
)
```

### Home/Away Splits

Analyze performance by location:

```python
from data_processor import DataProcessor

home_outcomes, away_outcomes = DataProcessor.calculate_home_away_split(
    data,
    outcome_field="goals",
    location_field="location"
)

# Analyze separately
home_analysis = analyze_simple_market("Home Goals", home_outcomes, 2.50)
away_analysis = analyze_simple_market("Away Goals", away_outcomes, 2.30)
```

### Minutes Adjustment

Normalize player stats by minutes played:

```python
from data_processor import DataProcessor

minutes_played = [90, 75, 85, 60, ...]
adjusted_outcomes = DataProcessor.minutes_adjustment(
    outcomes,
    minutes_played,
    full_game_minutes=90
)
```

## File Structure

```
├── value_engine.py              # Core calculation engine
├── data_processor.py            # Data handling & processing
├── main.py                      # Interactive CLI application
├── run.bat                      # Windows batch launcher
├── run.ps1                      # Windows PowerShell launcher
├── sample_player_data.csv       # Example CSV data
├── sample_markets.json          # Example JSON markets
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Examples

### Example 1: Simple Goal Scoring

```
Historical Data: 10 goals in 20 games (50% probability)
Bookmaker Odds: 1.80
Bookmaker Probability: 55.6%
Value: -5.6% (NO VALUE)
EV: -0.105 per unit
Expected Loss: -$10.50 per $100 staked
```

### Example 2: Player Assists

```
Historical Data: 3+ assists in 8 of 15 games (53.3%)
Bookmaker Odds: 2.20
Bookmaker Probability: 45.5%
Value: +7.8% (HAS VALUE)
EV: +0.173 per unit
Expected Win: +$17.30 per $100 staked
```

### Example 3: High-Variance Outcome

```
Historical Data: 2 successes in 3 games (66.7% prob)
Bookmaker Odds: 1.50
Sample Size: 3 (below minimum of 5)
Adjusted Probability: 58.3% (Bayesian shrinkage applied)
Value: -13.1%
Note: Small sample size - results less reliable
```

## Limitations & Considerations

1. **Historical Performance:** Engine assumes past performance predicts future outcomes. Adjust for injuries, transfers, form changes.

2. **Bookmaker Efficiency:** Bookmakers may be smarter than historical averages. Large positive EVs may indicate underpriced odds (potential value) or bookmaker knowledge advantage.

3. **Sample Size:** Minimum 5-10 games recommended. Bayesian shrinkage helps but can't overcome very small samples.

4. **Market Conditions:** Odds change over time. Use current odds in comparison.

5. **Correlation:** Multiple bets on same event may be correlated (not independent).

6. **Live Betting:** Engine designed for pre-match betting. Adjust for live conditions.

## Best Practices

1. **Use Adequate Samples:** Aim for 10+ games minimum
2. **Monitor Recency:** Apply weighting to give recent games more importance
3. **Adjust for Context:** Account for injuries, weather, schedule density
4. **Diversify:** Don't bet on outcomes with very small EV positive margins
5. **Track Results:** Compare actual outcomes vs. predicted probabilities
6. **Validate Frequently:** Update historical data regularly
7. **Consider Margins:** Account for betting fees (juice/vig) in odds

## Troubleshooting

### Python Not Found (Windows)
- Install Python from python.org
- Check "Add Python to PATH" during installation
- Restart computer after installation

### ImportError: No Module Named
- Run `pip install -r requirements.txt` (should work automatically)
- Ensure virtual environment is activated

### CSV Load Error
- Check file path is correct
- Verify CSV has headers in first row
- Ensure all data fields are present

### Invalid Odds
- Odds must be greater than 1.0 (decimal format)
- Example: 1.50, 2.00, 3.50 (NOT 0.50, -2.0)

## Contributing

Improvements welcome! Consider:
- Additional market types
- ML-based probability estimation
- Live betting adjustments
- Performance tracking dashboard
- Bet slip management

## License

MIT License - Use freely for personal and commercial projects

## Support

For issues, questions, or suggestions, please check the documentation and code comments.

---

**Happy Value Hunting! 🎯**
