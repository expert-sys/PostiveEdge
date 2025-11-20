# RotoWire Lineup Integration Guide

## Overview

The RotoWire integration adds **lineup intelligence** to your betting analysis by scraping real-time:
- Starting lineups (confirmed and expected)
- Injury reports (Out, Questionable, Probable, Doubtful)
- Game-time decisions
- Player status updates

This data is automatically cross-referenced with Sportsbet odds to provide injury-aware value analysis.

## Features

### 1. Lineup Data Collection
Scrapes https://www.rotowire.com/basketball/nba-lineups.php for:
- All NBA games for the day
- Expected starting lineups (5 starters per team)
- Bench/injury news
- Player positions and status

### 2. Injury Impact Analysis
Automatically identifies:
- **High Impact Games**: 3+ players out
- **Key Injuries**: Starters who are Out or Doubtful
- **Questionable Players**: GTD (game-time decisions)
- **Lineup Confirmation**: Whether starting 5 is confirmed

### 3. Integrated Analysis
When running Option 8 (Complete Analysis), the system:
1. Fetches lineup data from RotoWire first
2. Matches it with Sportsbet games
3. Shows injury context before analyzing each game
4. Includes lineup data in saved results

## How to Use

### Standalone RotoWire Scraper

```bash
# From launcher
python launcher.py
# Select option 11 (View Historical Data)
# Or run directly:
python scrapers/rotowire_scraper.py
```

**Output:**
```
1. IND @ DET - 7:00 PM ET
──────────────────────────────────────────────────────────────────────

  IND (Indiana Pacers)
  Starters: 5
    • PG: T. Haliburton
    • SG: A. Nembhard
    • SF: B. Mathurin
    • PF: P. Siakam
    • C: M. Turner

  Injuries/News: 2
    ⚠ J. Johnson (F) - Out
    ⚠ I. Jackson (G) - Questionable

  DET (Detroit Pistons)
  Starters: 5
    • PG: C. Cunningham [Questionable]
    • SG: J. Ivey
    • SF: T. Harris
    • PF: I. Stewart
    • C: J. Duren

  Injuries/News: 3
    ⚠ S. Fontecchio (F) - Out
    ⚠ A. Thompson (F) - Questionable

  ⚠️ HIGH INJURY IMPACT GAME (3 out, 2 questionable)
```

### Integrated with Complete Analysis

```bash
# From launcher - Option 8
# Or:
python scrapers/sportsbet_complete_analysis.py
```

**Enhanced Output:**
```
[1/5] Indiana Pacers @ Detroit Pistons
======================================================================

📋 Lineup Context:
  IND: 1 out, 1 questionable
  DET: 2 out, 2 questionable
  ⚠️ HIGH INJURY IMPACT GAME

  IND Key Injuries:
    • J. Johnson (F) - Out

  DET Key Injuries:
    • S. Fontecchio (F) - Out
    • A. Thompson (F) - Questionable

📊 Extracted from Sportsbet:
  - 45 betting markets
  - 12 match insights

🔍 Analyzing insights with Value Engine...
  ✓ Analyzed: 12 insights
  ✓ Value bets: 3
```

## Data Structure

### GameLineup Object
```json
{
  "matchup": "IND @ DET",
  "game_time": "7:00 PM ET",
  "away_team": {
    "name": "Indiana Pacers",
    "abbr": "IND",
    "starters": [
      {
        "name": "T. Haliburton",
        "position": "PG",
        "status": "Expected",
        "is_starter": true
      }
    ],
    "injuries": [
      {
        "name": "J. Johnson",
        "position": "F",
        "status": "Out",
        "injury_info": "Out (ankle)"
      }
    ]
  },
  "home_team": { ... }
}
```

### Injury Impact Summary
```json
{
  "away_team": {
    "team": "IND",
    "out_count": 1,
    "questionable_count": 1,
    "key_injuries": ["J. Johnson (F) - Out"],
    "starters_confirmed": true
  },
  "home_team": { ... },
  "total_injuries": 3,
  "total_questionable": 3,
  "high_impact": true
}
```

## Team Name Matching

The scraper automatically normalizes team names for matching:
- "IND" → "Pacers" → "Indiana Pacers"
- "LAL" → "Lakers" → "Los Angeles Lakers"
- "GSW" → "Warriors" → "Golden State Warriors"

This ensures lineup data matches with Sportsbet game data even when team names differ slightly.

## Value Analysis Impact

### How Injuries Affect Value Bets

**Scenario 1: Star Player Out**
```
Insight: "C. Cunningham has scored 25+ points in 7 of his last 10 games"
Odds: 1.80 (implies 55.6% probability)
Historical: 70% (7/10)

⚠️ BUT: Lineup shows C. Cunningham is QUESTIONABLE
→ Analysis flags this as HIGH RISK
→ User can decide to skip or wait for confirmation
```

**Scenario 2: Role Player Boost**
```
Insight: "Backup PG has averaged 15+ minutes in last 5 games"
Odds: 2.50 (implies 40% probability)
Historical: 60% (3/5)

✓ AND: Starting PG is OUT (per RotoWire)
→ Backup likely to get 30+ minutes
→ ENHANCED VALUE BET (more opportunity)
```

**Scenario 3: Team Total Adjustment**
```
Insight: "Team averages 115 points in last 10 games"
Odds: Over 110.5 at 1.90

⚠️ BUT: 3 starters out (per RotoWire)
→ Scoring likely reduced
→ SKIP or consider Under instead
```

## Best Practices

### 1. Always Check Lineup Status
Before placing bets based on analysis:
- Verify injury status hasn't changed
- Check game-time decisions (GTD)
- Confirm starting lineups

### 2. Timing Matters
RotoWire updates throughout the day:
- **Morning**: Expected lineups posted
- **2-3 hours before game**: GTD updates
- **30-60 min before game**: Final confirmations

Run analysis closer to game time for most accurate data.

### 3. Interpret Impact Levels
- **0-1 injuries**: Normal game, trust historical data
- **2-3 injuries**: Moderate impact, adjust expectations
- **4+ injuries**: High impact, be cautious with value bets

### 4. Position Matters
Not all injuries are equal:
- **PG/Star Out**: Massive impact (usage, playmaking)
- **Bench Player Out**: Minimal impact
- **Starting Big Man Out**: Affects rebounds/blocks props

## Saved Output

Lineup data is saved in two places:

### 1. Standalone Scraper
```
data/outputs/rotowire_lineups_YYYYMMDD_HHMMSS.json
```

### 2. Complete Analysis
```
data/outputs/complete_analysis_YYYYMMDD_HHMMSS.json
```

Includes:
- All game results
- Lineup data for each game
- Injury impact summaries
- Value bet analysis with context

## Troubleshooting

### No Lineup Data Found
**Issue**: "Retrieved lineup data for 0 games"

**Solutions**:
- RotoWire may not have posted lineups yet (check time of day)
- Page structure may have changed
- Run with `headless=False` to see what's happening

### Team Name Mismatch
**Issue**: Lineup data not matching with Sportsbet games

**Solution**:
- Check `normalize_team_name()` function in `rotowire_scraper.py`
- Add team abbreviation/name mapping if needed

### Playwright Errors
**Issue**: Browser automation fails

**Solution**:
```bash
pip install playwright
playwright install
```

## API Reference

### Main Functions

```python
from scrapers.rotowire_scraper import (
    scrape_rotowire_lineups,
    find_lineup_for_matchup,
    get_injury_impact_summary
)

# Scrape all lineups
lineups = scrape_rotowire_lineups(headless=True)

# Find specific game
lineup = find_lineup_for_matchup(lineups, "Pacers", "Pistons")

# Get injury summary
impact = get_injury_impact_summary(lineup)
```

### Classes

- `PlayerStatus`: Individual player info
- `TeamLineup`: Team's starters + injuries
- `GameLineup`: Complete game lineup data

## Examples

### Example 1: Check Injuries Before Betting
```python
from scrapers.rotowire_scraper import scrape_rotowire_lineups, find_lineup_for_matchup

# Get today's lineups
lineups = scrape_rotowire_lineups()

# Check specific game
game = find_lineup_for_matchup(lineups, "Lakers", "Warriors")

if game:
    # Check for star player injuries
    lakers_out = [p for p in game.away_team.bench_news if p.status == "Out"]

    if any("LeBron" in p.name for p in lakers_out):
        print("⚠️ LeBron is out - reconsider Lakers bets")
```

### Example 2: Find Backup Player Opportunities
```python
impact = get_injury_impact_summary(game)

if impact['away_team']['out_count'] >= 2:
    print(f"Multiple players out for {impact['away_team']['team']}")
    print("Look for backup player prop value bets")
```

## Future Enhancements

Potential additions:
1. **Historical injury impact**: Track how teams perform with specific injuries
2. **Rest days tracking**: Identify back-to-back games
3. **Minutes projection**: Estimate backup player minutes
4. **Lineup confidence**: Rate lineup certainty (confirmed vs expected)
5. **Real-time updates**: Monitor lineup changes during the day

---

**The lineup intelligence integration significantly improves betting analysis by providing crucial context that historical data alone cannot capture.**
