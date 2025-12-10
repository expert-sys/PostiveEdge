# NBA Betting System - Intelligent Value Finder

A comprehensive NBA betting analysis system that scrapes Sportsbet insights, validates with DataBallr player stats, and projects high-confidence value bets using statistical models.

## System Overview

**Complete Pipeline:**
1. **Scrape Sportsbet** → NBA games, odds, insights, player props
2. **Validate with DataBallr** → Player game logs, historical hit rates
3. **Project Value** → Statistical models + historical analysis
4. **Rank Bets** → High-confidence recommendations (70%+ confidence, positive EV)

## Features

- **Automated Data Collection** - Scrapes Sportsbet NBA markets and insights
- **Player Stats Validation** - Cross-references with DataBallr game logs
- **Statistical Projections** - Combines model predictions (70%) + historical data (30%)
- **Value Detection** - Identifies positive EV bets with edge calculation
- **Confidence Scoring** - Multi-factor confidence assessment
- **Correlation Control** - Limits bets per game to avoid over-exposure
- **Smart Caching** - Reduces API calls and speeds up analysis

## Quick Start

### Prerequisites
- Python 3.8 or higher
- Internet connection (for scraping)

### Installation & First Run

**Windows:**
```bash
run_betting_system.bat
```

**Linux/Mac:**
```bash
chmod +x run_betting_system.sh
./run_betting_system.sh
```

The launcher will automatically:
1. Create a virtual environment
2. Install dependencies (Playwright, BeautifulSoup4)
3. Download browser drivers (one-time setup)
4. Run the analysis

### Command Line Options

```bash
# Analyze all available games (default)
python nba_betting_system.py

# Analyze only 3 games (faster)
python nba_betting_system.py --games 3

# Higher confidence threshold (75%+)
python nba_betting_system.py --min-confidence 75

# Custom output file
python nba_betting_system.py --output my_bets.json
```

## Example Output

```
================================================================================
FINAL RECOMMENDATIONS
================================================================================

1. LeBron James - Points Over 25.5
   Game: Lakers @ Warriors (7:30 PM ET)
   Odds: 1.90 | Confidence: 78% | Strength: HIGH
   Edge: +5.2% | EV: +8.4%
   Historical: 65.0% (20 games)
   Projected: 70.3%

2. Stephen Curry - Three Pointers Made Over 3.5
   Game: Lakers @ Warriors (7:30 PM ET)
   Odds: 2.10 | Confidence: 75% | Strength: HIGH
   Edge: +4.8% | EV: +7.1%
   Historical: 60.0% (20 games)
   Projected: 68.5%

✓ Saved 2 recommendations to betting_recommendations.json
```

## Understanding the Results

### Confidence Score (0-100%)
- **80%+**: Very High - Strong model agreement + large sample + significant edge
- **70-79%**: High - Good model confidence with positive indicators
- **60-69%**: Medium - Acceptable confidence, smaller edge
- **<60%**: Low - Filtered out by default

### Expected Value (EV)
- **Positive EV**: Long-term profitable bet
- **+5% or higher**: Excellent value
- **+3% to +5%**: Good value
- **+1% to +3%**: Marginal value
- **Negative EV**: Avoid

### Edge Percentage
The difference between your projected probability and the bookmaker's implied probability.
- **+5% edge**: You estimate 55% chance, bookmaker implies 50%
- **Higher edge = Better value**

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

## Testing the System

Before running a full analysis, test that everything is set up correctly:

```bash
python test_system.py
```

This will verify:
- ✓ All dependencies installed
- ✓ Scraper modules present
- ✓ Cache directory created
- ✓ Main script ready

## Documentation

- **📖 [Setup Guide](SETUP_GUIDE.md)** - Complete installation instructions
- **🏗️ [System Architecture](SYSTEM_ARCHITECTURE.md)** - Technical details and design
- **⚡ [Quick Reference](QUICK_REFERENCE.md)** - Commands, metrics, and tips
- **📊 [Workflow Diagram](WORKFLOW_DIAGRAM.md)** - Visual system flow
- **📝 [Changelog](CHANGELOG.md)** - Version history and changes
- **✅ [Rework Complete](REWORK_COMPLETE.md)** - Summary of system rework

## Troubleshooting

### Common Issues

**"Player not in cache"**
```bash
echo "Player Name" >> PLAYERS_TO_ADD.txt
python build_databallr_player_cache.py
```

**"No games found"**
- Check NBA schedule - system only works when games are available

**"Insufficient data"**
- Expected for rookies/injured players - system automatically skips

**Scraping fails**
- Check internet connection
- Verify Playwright installed: `playwright install chromium`
- Check logs: `tail -f nba_betting_system.log`

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed troubleshooting.

## Performance

- **1 game**: ~30-60 seconds
- **3 games**: ~2-3 minutes  
- **All games (5-10)**: ~5-10 minutes

First run takes longer (browser installation). Subsequent runs use cache.

## Responsible Betting

⚠️ **Important Reminders:**
- This system is for educational/research purposes only
- Sports betting involves risk - never bet more than you can afford to lose
- Past performance does not guarantee future results
- Always verify injury reports and lineups before betting
- Check that sports betting is legal in your jurisdiction
- Set limits and stick to them

## Contributing

Improvements welcome! Areas for contribution:
- Team market analysis (spreads, totals, moneylines)
- Live betting support
- Additional sports (NFL, MLB, NHL)
- Machine learning models
- Performance tracking dashboard
- Mobile app

## License

MIT License - See LICENSE file for details

## Disclaimer

This system is for educational and research purposes only. The authors are not responsible for any financial losses incurred through use of this system. Sports betting involves risk. Always bet responsibly and within your means.

---

**Happy Betting! 🏀📊**

*Built with Python, Playwright, and statistical models*

