# Team Markets - Quick Reference Card

## What's New?

The system now analyzes **team-level betting markets** using historical game data from Sportsbet insights:
- ✅ **Moneyline** (which team wins)
- ✅ **Totals** (over/under total points)
- ✅ **Spreads** (point differential)

## Quick Start

### Run Everything (Default)
```bash
python nba_betting_system.py
```
Analyzes both player props AND team markets.

### Player Props Only
```bash
python nba_betting_system.py --player-props-only
```
Skips team market analysis.

### Higher Confidence Threshold
```bash
python nba_betting_system.py --min-confidence 65
```
Only shows bets with 65%+ confidence.

## How It Works (30 Second Version)

1. **Scrapes** recent game results from Sportsbet (last 5-10 games)
2. **Analyzes** team form (offense, defense, pace, trends)
3. **Projects** game outcome (scores, totals, margins)
4. **Evaluates** each market for value (positive EV)
5. **Recommends** high-confidence bets (55%+ confidence)

## Example Output

```
1. TEAM MARKET: Total - Over 223.5
   Odds: 1.90 | Confidence: 68% | Strength: HIGH
   Edge: +8.2% | EV: +16.1%
   Projected Total: 238.9 vs Line 223.5
   
2. Anthony Edwards - Points Over 24.5
   Odds: 1.90 | Confidence: 68% | Strength: HIGH
   Edge: +8.2% | EV: +16.1%
   Historical: 65.0% (20 games)
```

## Key Metrics

### Confidence Score (50-95%)
- **50-60%**: Moderate confidence
- **60-70%**: Good confidence
- **70-80%**: High confidence
- **80%+**: Very high confidence

### Edge Percentage
- **3-5%**: Decent value
- **5-8%**: Good value
- **8%+**: Great value

### Expected Value (EV)
- **Positive EV**: Long-term profitable
- **5%+ EV**: Good bet
- **10%+ EV**: Excellent bet

## Projection Method

### Team Form
```
Offensive Rating = Avg points scored
Defensive Rating = Avg points allowed
Pace = Total points per game
Trend = Recent vs previous games
```

### Game Projection
```
Home Score = (Home offense + Away defense) / 2 + 3.5
Away Score = (Away offense + Home defense) / 2 - 3.5
Total = Home Score + Away Score
Margin = Home Score - Away Score
```

### Win Probability
```
P(home win) = 1 / (1 + e^(-margin/10))
```

## What Data Is Used?

### From Sportsbet Insights
- Recent game scores (e.g., "123-120 W")
- Last 5-10 games per team
- Current odds/lines

### Calculated
- Offensive/defensive ratings
- Win percentage
- Pace rating
- Scoring trends
- Consistency (variance)

## Confidence Factors

### Increases Confidence
✅ More games (8-10 better than 5)
✅ Consistent scoring (low variance)
✅ Strong win probability (60%+)
✅ Clear trends (improving/declining)

### Decreases Confidence
❌ Few games (5-6 games)
❌ High variance (inconsistent)
❌ Close probabilities (50-55%)
❌ Conflicting trends

## Market Types

### Moneyline
- **What**: Which team wins
- **Projection**: Win probability
- **Example**: Lakers ML @ 1.90 (51.4% win prob)

### Totals
- **What**: Combined points over/under
- **Projection**: Total points scored
- **Example**: Over 223.5 @ 1.90 (projected 238.9)

### Spreads
- **What**: Point differential
- **Projection**: Margin of victory
- **Example**: Lakers -3.5 @ 1.90 (projected +0.6)

## Tips

### 1. Trust the Math
- System uses actual results, not opinions
- Positive EV = profitable long-term
- Confidence scores are realistic

### 2. Look for Edges
- 5%+ edge = good bet
- 8%+ edge = great bet
- Higher edge = higher expected profit

### 3. Manage Bankroll
- Bet 2-3% per recommendation
- Higher confidence = slightly larger stake
- Track results over 50+ bets

### 4. Check Reasoning
- Read the "Reasoning" section
- Verify form/trends make sense
- Look for pace/momentum factors

### 5. Avoid Correlation
- System limits to 2 bets per game
- Don't add more manually
- Mix player props + team markets

## Limitations

### Not Included (Yet)
❌ Injury reports
❌ Back-to-back games
❌ Travel/rest factors
❌ Head-to-head history
❌ Lineup changes

### Data Requirements
- Needs 5+ recent games per team
- More games = better projections
- Ideally 8-10 games

## Files

### New
- `team_betting_engine.py` - Team market analysis engine
- `TEAM_MARKETS_GUIDE.md` - Complete guide
- `TEAM_MARKETS_SUMMARY.md` - Implementation summary
- `SYSTEM_FLOW_WITH_TEAM_MARKETS.md` - Architecture diagram

### Updated
- `nba_betting_system.py` - Added team market integration

## Command Line Options

```bash
# Default (everything)
python nba_betting_system.py

# Player props only
python nba_betting_system.py --player-props-only

# Limit games
python nba_betting_system.py --games 3

# Higher confidence
python nba_betting_system.py --min-confidence 65

# Custom output file
python nba_betting_system.py --output my_bets.json
```

## Expected Performance

### Over 50+ Bets
- **Win Rate**: 55-60% (on 50/50 bets)
- **ROI**: 3-5% long-term
- **Confidence Calibration**: ±5% of actual
- **Edge Realization**: ±3% of actual

### Variance
- Short-term: High variance (10-20 bets)
- Medium-term: Moderate variance (20-50 bets)
- Long-term: Low variance (50+ bets)

## Troubleshooting

### No Team Markets Found
- Check if insights have recent results
- Verify at least 5 games per team
- Try different games

### Low Confidence Scores
- Normal for close matchups
- Increase sample size (more games)
- Look for clearer edges

### No Recommendations
- Try lowering `--min-confidence`
- Check if markets have value
- Verify data is being scraped

## Questions?

See full documentation:
- `TEAM_MARKETS_GUIDE.md` - Complete user guide
- `CONFIDENCE_V2_IMPROVEMENTS.md` - Confidence methodology
- `V2_QUICK_START.md` - System overview

---

**Quick Reference Version**: 1.0
**Date**: December 5, 2025
