# Team Markets Analysis - Moneyline, Totals, and Spreads

## Overview

The system now analyzes **team-level betting markets** in addition to player props:
- **Moneyline** (win probability)
- **Totals** (over/under total points)
- **Spreads/Handicaps** (point differential)

This uses the historical game data visible in Sportsbet's "Stats & Insights" section (e.g., "2025/26 Season Results").

## How It Works

### 1. Data Collection
The system extracts recent game results from Sportsbet insights:
- Last 5-10 games for each team
- Scores (e.g., "123-120")
- Results (W/L)

### 2. Team Form Analysis
For each team, calculates:
- **Offensive Rating**: Average points scored
- **Defensive Rating**: Average points allowed
- **Win Percentage**: Recent win rate
- **Streak**: Current winning/losing streak
- **Pace**: Total points per game (fast/slow)
- **Trends**: Improving/declining offense/defense
- **Consistency**: Standard deviation of scoring

### 3. Game Projection
Projects the game outcome using:
- **Four Factors Approach**: 
  - Home score = (Home offense + Away defense) / 2
  - Away score = (Away offense + Home defense) / 2
- **Home Court Advantage**: +3.5 points
- **Pace Adjustments**: Fast-paced games = higher scoring
- **Momentum**: Teams on 3+ game streaks get slight boost

### 4. Market Evaluation
For each market (moneyline, total, spread):
- Calculates projected probability
- Compares to implied probability from odds
- Identifies positive expected value (EV) bets
- Assigns confidence score (50-95%)

## Usage

### Run with Team Markets (Default)
```bash
python nba_betting_system.py
```

### Player Props Only
```bash
python nba_betting_system.py --player-props-only
```

### Adjust Confidence Threshold
```bash
python nba_betting_system.py --min-confidence 60
```

## Example Output

```
1. TEAM MARKET: Total - Over 223.5
   Game: Celtics @ Lakers (Dec 5, 2025 7:30 PM)
   Odds: 1.90 | Confidence: 68% | Strength: HIGH
   Edge: +8.2% | EV: +16.1%
   Projected Probability: 61.1%
   Projected Score: 119.2 - 119.8
   Projected Total: 238.9 | Margin: +0.6
   Reasoning:
     • Projected total: 238.9 vs line 223.5
     • Over probability: 61.1%
     • Fast-paced matchup (1.08x) - expect higher scoring

2. TEAM MARKET: Spread - Lakers -3.5
   Game: Celtics @ Lakers (Dec 5, 2025 7:30 PM)
   Odds: 1.90 | Confidence: 72% | Strength: HIGH
   Edge: +6.5% | EV: +12.3%
   Projected Probability: 58.9%
   Projected Margin: +0.6 vs spread -3.5
   Cover probability: 58.9%
```

## Projection Methodology

### Win Probability
Uses logistic function based on projected margin:
```
P(home win) = 1 / (1 + e^(-margin/10))
```

### Spread Probability
Calculates probability of covering spread:
```
P(cover) = 1 / (1 + e^(-margin_diff/8))
```

### Total Probability
Based on projected total vs betting line:
- Projected > Line → Over favored
- Projected < Line → Under favored
- Adjusted for scoring variance

### Confidence Scoring
Combines:
- **Sample Size**: More games = higher confidence
- **Consistency**: Lower variance = higher confidence
- **Probability**: Higher win probability = higher confidence

## Key Features

### 1. Form-Based Projections
- Uses actual recent results, not season averages
- Captures hot/cold streaks
- Identifies trending teams

### 2. Pace Adjustments
- Fast-paced matchups → Higher totals
- Slow-paced matchups → Lower totals
- Accounts for both teams' pace

### 3. Home Court Advantage
- Standard +3.5 points for home team
- Can be disabled for neutral site games

### 4. Momentum Factors
- Teams on 3+ game win streaks get +3% probability boost
- Captures psychological edge

### 5. Blowout Risk
- Considers team strength differential
- Reduces projections for likely blowouts

## Limitations

### Data Requirements
- Needs at least 5 recent games per team
- More games = better projections
- Ideally 8-10 games for accuracy

### Not Included (Yet)
- Injury reports
- Back-to-back games
- Travel/rest days
- Head-to-head history
- Lineup changes

### Confidence Ranges
- **50-60%**: Moderate confidence, small edges
- **60-70%**: Good confidence, solid edges
- **70-80%**: High confidence, strong edges
- **80%+**: Very high confidence, excellent edges

## Integration with Player Props

The system now provides **both** player props and team markets:
- Player props use DataBallr stats + projection models
- Team markets use recent game results + form analysis
- Both use same confidence engine and value calculations
- Correlation filter limits bets per game (max 2)

## Tips for Using Team Markets

### 1. Trust the Projections
- System uses actual results, not opinions
- Confidence scores are realistic (not inflated)
- Positive EV = long-term profitable

### 2. Look for Edges
- 5%+ edge = good bet
- 8%+ edge = great bet
- 10%+ edge = excellent bet

### 3. Consider Context
- Check the reasoning section
- Look for pace/momentum factors
- Verify team form makes sense

### 4. Manage Bankroll
- Don't bet more than 2-3% per bet
- Higher confidence = slightly larger stake
- Track results over 50+ bets

### 5. Combine with Player Props
- System limits to 2 bets per game
- Mix team markets + player props
- Avoid correlated bets (e.g., team total + player points)

## Technical Details

### Team Form Object
```python
TeamForm(
    team_name="Lakers",
    avg_points_scored=119.9,
    avg_points_allowed=120.8,
    win_pct=0.50,
    recent_form="W-W-L-L-L",
    streak="2W",
    scoring_std_dev=8.2,
    pace_rating=1.05,
    scoring_trend="improving"
)
```

### Game Projection Object
```python
GameProjection(
    home_team="Lakers",
    away_team="Celtics",
    projected_home_score=119.8,
    projected_away_score=119.2,
    projected_total=238.9,
    projected_margin=0.6,
    home_win_probability=0.514,
    recommended_spread=0.5,
    recommended_total=239.0,
    projection_confidence=74.0
)
```

## Future Enhancements

### Planned Features
1. **Injury Integration**: Adjust for key player absences
2. **Rest/Travel**: Account for back-to-backs and travel
3. **Head-to-Head**: Use historical matchup data
4. **Live Updates**: Real-time form updates during season
5. **Advanced Stats**: Incorporate offensive/defensive ratings from NBA API

### Data Sources
- Currently: Sportsbet insights (recent results)
- Future: NBA Stats API, Basketball Reference, ESPN

## Questions?

See also:
- `CONFIDENCE_V2_IMPROVEMENTS.md` - Confidence scoring methodology
- `MATCHUP_ENGINE_GUIDE.md` - Player matchup analysis
- `V2_QUICK_START.md` - System overview
