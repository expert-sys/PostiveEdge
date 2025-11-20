# Automated Betting Analysis Pipeline Guide

## Overview

This pipeline automatically processes scraped sports betting data and feeds it into the implied probability engine to identify value betting opportunities.

## System Architecture

```
┌─────────────────┐
│  Web Scraper    │ (universal_scraper.py)
└────────┬────────┘
         │ Creates: scraped_*.json files
         ▼
┌─────────────────┐
│  Consolidator   │ (data_consolidator.py)
└────────┬────────┘
         │ Creates: consolidated_sports_data.json
         ▼
┌─────────────────┐
│ Market Extractor│ (auto_analysis_pipeline.py)
└────────┬────────┘
         │ Extracts: spreads, moneylines, totals, props
         ▼
┌─────────────────┐
│ Historical Data │ (./historical_data/*.json)
│    Matcher      │
└────────┬────────┘
         │ Matches markets with past outcomes
         ▼
┌─────────────────┐
│  Value Engine   │ (value_engine.py)
└────────┬────────┘
         │ Calculates: Implied Probability, EV, Edge
         ▼
┌─────────────────┐
│    Insights     │ (betting_insights.json)
└─────────────────┘
```

## Quick Start

### 1. Run the Scraper

First, scrape betting sites to get current odds:

```bash
python universal_scraper.py
```

This creates files like:
- `scraped_DraftKings_NBA_20251117_152030.json`
- `scraped_FanDuel_NFL_20251117_152041.json`
- `scraped_ESPN_NBA_Odds_20251117_151952.json`

### 2. Add Historical Data

Create historical outcome data for teams/players you want to analyze.

**Option A: From CSV**
```python
from historical_data_helper import quick_create_from_csv

quick_create_from_csv(
    csv_file="lakers_games_2024.csv",
    team_name="Lakers",
    market_type="moneyline",
    outcome_column="won"  # Column with W/L or 1/0
)
```

**Option B: Create Sample Data (for testing)**
```python
from historical_data_helper import quick_create_sample

quick_create_sample(
    team_name="Lakers",
    market_type="moneyline",
    num_games=20,
    win_rate=0.58  # 58% win rate
)
```

**Option C: Interactive Mode**
```bash
python historical_data_helper.py
```

Historical data files are saved to `./historical_data/` as:
- `Lakers_moneyline.json`
- `Warriors_spread.json`
- `LeBron_points_over.json`

### 3. Run the Analysis Pipeline

Process all scraped data and identify value bets:

```bash
python auto_analysis_pipeline.py
```

Or programmatically:
```python
from auto_analysis_pipeline import run_auto_analysis

summary = run_auto_analysis(
    scraped_dir=".",
    historical_dir="./historical_data",
    output_file="betting_insights.json"
)
```

### 4. Review Insights

The pipeline generates two outputs:

**betting_insights.json** - Detailed JSON with all analysis
```json
{
  "summary": {
    "total_opportunities": 15,
    "avg_ev": 0.0823
  },
  "value_opportunities": [
    {
      "event_type": "Lakers vs Warriors - Moneyline",
      "bookmaker_odds": 2.10,
      "implied_odds": 1.72,
      "value_percentage": +6.89,
      "ev_per_unit": +0.0689,
      "has_value": true,
      "sample_size": 25
    }
  ]
}
```

**betting_insights_report.txt** - Human-readable summary
```
TOP VALUE OPPORTUNITIES (Sorted by Expected Value)

1. Lakers vs Warriors - Moneyline
   Bookmaker Odds: 2.10
   Fair Odds (from history): 1.72
   Edge: +6.89%
   Expected Value: +0.0689 per unit
   Expected Return per $100: $6.89
   Sample Size: 25 games
```

## File Reference

### Core Pipeline Files

| File | Purpose |
|------|---------|
| `auto_analysis_pipeline.py` | Main automated pipeline |
| `historical_data_helper.py` | Manage historical data |
| `value_engine.py` | Implied probability calculations |
| `data_consolidator.py` | Combine scraped files |
| `universal_scraper.py` | Scrape betting sites |

### Data Files

| Location | Contents |
|----------|----------|
| `scraped_*.json` | Raw scraped data from betting sites |
| `consolidated_sports_data.json` | All scraped data combined |
| `historical_data/*.json` | Historical outcomes for analysis |
| `betting_insights.json` | Value analysis results |
| `betting_insights_report.txt` | Human-readable report |

## Understanding the Analysis

### Metrics Explained

**Historical Probability**
- Based on actual past outcomes
- Example: Team won 15 of last 25 games = 60% probability

**Implied Odds (Fair Odds)**
- Odds that reflect the historical probability
- Formula: `1 / historical_probability`
- Example: 60% probability = 1.67 decimal odds

**Bookmaker Probability**
- What the bookmaker thinks will happen
- Formula: `1 / bookmaker_odds`
- Example: Odds of 2.10 = 47.6% probability

**Edge (Value %)**
- The difference between your estimate and theirs
- Formula: `(historical_prob - bookmaker_prob) × 100`
- Example: 60% - 47.6% = +12.4% edge

**Expected Value (EV)**
- Average profit per $1 bet over time
- Formula: `(prob × (odds - 1)) - (1 - prob)`
- Positive EV = Good bet
- Negative EV = Bad bet

**Example Analysis:**

```
Team: Lakers
Market: Moneyline
Historical Record: 15-10 (60% win rate)

Bookmaker Odds: 2.10 (implies 47.6%)
Fair Odds: 1.67 (from 60% probability)

Edge: +12.4%
EV per $1: +$0.124

Interpretation:
- Bet $100, expect to profit $12.40 on average
- The bookmaker underestimates the Lakers by 12.4%
- This is a VALUE BET ✓
```

## Configuring Historical Data

### Binary Outcomes (Win/Loss)

```json
{
  "outcomes": [1, 0, 1, 1, 0, 1, 0, 1, 1, 1],
  "metadata": {
    "team": "Lakers",
    "market_type": "moneyline",
    "season": "2024"
  }
}
```
- `1` = Win, Cover, Over, Success
- `0` = Loss, Miss, Under, Failure

### Continuous Outcomes (Points, Totals)

```json
{
  "outcomes": [112, 98, 125, 89, 103, 117],
  "metadata": {
    "team": "Lakers",
    "market_type": "total_points",
    "threshold": 110.5
  }
}
```

The engine converts to binary using the threshold:
- 112 ≥ 110.5 → 1
- 98 < 110.5 → 0

### From CSV

If you have a CSV like this:

```csv
date,opponent,won,points,covered_spread
2024-01-01,Warriors,1,112,1
2024-01-03,Bulls,0,98,0
2024-01-05,Heat,1,125,1
```

Create historical data:

```python
from historical_data_helper import HistoricalDataManager

manager = HistoricalDataManager()

# Moneyline market
manager.create_from_csv(
    csv_file="lakers_2024.csv",
    team_name="Lakers",
    market_type="moneyline",
    outcome_column="won"
)

# Spread market
manager.create_from_csv(
    csv_file="lakers_2024.csv",
    team_name="Lakers",
    market_type="spread",
    outcome_column="covered_spread"
)

# Total points (over 110.5)
manager.create_from_csv(
    csv_file="lakers_2024.csv",
    team_name="Lakers",
    market_type="total",
    outcome_column="points",
    threshold=110.5
)
```

## Improving Scraper Accuracy

The current scraped files show mostly empty odds fields. To improve:

### 1. Check Scraper Configuration

Look at `scraper_links.json` and `default_scraper_links.json`. Make sure selectors match the current site structure:

```json
{
  "DraftKings_NBA": {
    "url": "https://sportsbook.draftkings.com/leagues/basketball/nba",
    "selectors": {
      "spread": ".sportsbook-outcome-cell__label",
      "moneyline": ".sportsbook-odds",
      "total": ".total-line"
    }
  }
}
```

### 2. Inspect Site Structure

Use browser DevTools to find the correct CSS selectors for odds.

### 3. Test Individual Sites

```python
from universal_scraper import UniversalSportsScraper

scraper = UniversalSportsScraper()
data = scraper.scrape_site("https://sportsbook.draftkings.com/...")

print(data)  # Check if odds are extracted
```

### 4. Manual Data Entry

For important games, manually add the odds to scraped files:

```json
{
  "games": [
    {
      "team_name": ["Lakers", "Warriors"],
      "spread": "-3.5",
      "moneyline": "-150",
      "total": "220.5"
    }
  ]
}
```

## Advanced Usage

### Batch Analysis

Analyze multiple markets at once:

```python
from value_engine import ValueEngine, HistoricalData, MarketConfig, OutcomeType

engine = ValueEngine()

markets = [
    {
        "team": "Lakers",
        "outcomes": [1,0,1,1,0,1,1,1,0,1],
        "odds": 2.10
    },
    {
        "team": "Warriors",
        "outcomes": [1,1,1,0,1,1,1,0,1,1],
        "odds": 1.75
    }
]

for market in markets:
    hist_data = HistoricalData(outcomes=market["outcomes"])
    config = MarketConfig(
        event_type=market["team"],
        outcome_type=OutcomeType.BINARY,
        bookmaker_odds=market["odds"]
    )

    result = engine.analyze_market(hist_data, config)
    print(result)
```

### Recency Weighting

Give more weight to recent games:

```python
from data_processor import DataProcessor

processor = DataProcessor()

# Exponential decay: recent games weighted more
weights = processor.calculate_recency_weights(
    num_outcomes=20,
    decay_factor=0.95
)

# Use in analysis
from value_engine import analyze_simple_market

analysis = analyze_simple_market(
    event_type="Lakers Moneyline",
    historical_outcomes=[1,0,1,1,0,1,0,1,1,1],
    bookmaker_odds=2.10,
    weights=weights
)
```

### Opponent Adjustments

Adjust outcomes based on opponent strength:

```python
from data_processor import DataProcessor

processor = DataProcessor()

outcomes = [1, 0, 1, 1, 0]
opponent_strengths = [0.6, 0.8, 0.5, 0.4, 0.9]  # 0-1 scale

adjusted = processor.apply_opponent_adjustment(
    outcomes=outcomes,
    opponent_strengths=opponent_strengths,
    adjustment_factor=0.3
)
```

## Troubleshooting

### "No markets extracted"

**Problem:** Pipeline finds no betting markets in scraped data

**Solutions:**
1. Check if scraped files have odds data (not all `null`)
2. Verify scraper selectors match current site structure
3. Manually add odds to a test file
4. Check consolidated_sports_data.json for actual data

### "No historical data found"

**Problem:** Markets have no historical outcomes to compare

**Solutions:**
1. Create historical data files in `./historical_data/`
2. Use `historical_data_helper.py` to generate sample data
3. Ensure filenames match: `{TeamName}_{market_type}.json`
4. Check team name spelling matches scraped data

### "Small sample warning"

**Problem:** Not enough historical games for reliable analysis

**Solutions:**
1. Gather more historical data (aim for 20+ games)
2. The engine applies Bayesian shrinkage automatically
3. Use results with caution if sample < 10 games

### "No value found"

**Problem:** No positive EV opportunities identified

**This is normal if:**
- Markets are efficient (bookmakers are accurate)
- Historical data doesn't predict future well
- Sample sizes are too small
- You need more diverse data sources

## Best Practices

### 1. Data Quality
- Use at least 15-20 historical games
- Update historical data regularly
- Account for recent changes (injuries, trades)

### 2. Market Selection
- Focus on markets you understand
- Specialize in specific sports/teams
- Avoid low-sample exotic props

### 3. Odds Shopping
- Scrape multiple betting sites
- Compare odds across bookmakers
- Best odds increase your edge

### 4. Bankroll Management
- Bet sizing based on Kelly Criterion
- Don't bet entire bankroll on high EV
- Account for variance

### 5. Continuous Improvement
- Track your bets and results
- Refine your models over time
- Add new data sources

## Next Steps

1. **Improve Scraping**
   - Update selectors for current sites
   - Add more betting sites
   - Implement odds comparison

2. **Expand Historical Data**
   - Connect to sports APIs (ESPN, NBA, etc.)
   - Build database of historical results
   - Automate data collection

3. **Enhance Analysis**
   - Add injury adjustments
   - Incorporate weather data
   - Build ML models

4. **Automation**
   - Schedule scraping (cron jobs)
   - Auto-run pipeline daily
   - Alert on high-value opportunities

## Support

For issues or questions:
1. Check this guide first
2. Review the code comments
3. Test with sample data
4. Open an issue on GitHub

## Summary

You now have a complete pipeline that:
- ✓ Scrapes betting sites
- ✓ Consolidates data
- ✓ Extracts markets
- ✓ Matches historical data
- ✓ Calculates implied probabilities
- ✓ Identifies value bets
- ✓ Generates actionable insights

**The system is ready to use!** Just add:
1. Better scraper configuration for actual odds
2. Historical data for teams you want to analyze
3. Regular updates to keep data fresh

Happy betting!
