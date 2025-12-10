# NBA Betting System - Complete Flow with Team Markets

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SPORTSBET DATA COLLECTION                    │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Markets    │  │   Insights   │  │ Match Stats  │          │
│  │ (Odds/Lines) │  │ (Trends/Form)│  │ (Team Data)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        DATA EXTRACTION                           │
│                                                                   │
│  ┌─────────────────────┐         ┌─────────────────────┐       │
│  │  PLAYER PROP DATA   │         │   TEAM MARKET DATA  │       │
│  │                     │         │                     │       │
│  │ • Player names      │         │ • Recent results    │       │
│  │ • Stat types        │         │ • Scores (W/L)      │       │
│  │ • Lines/odds        │         │ • Last 5-10 games   │       │
│  │ • Insights          │         │ • Both teams        │       │
│  └─────────────────────┘         └─────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
           ↓                                    ↓
┌──────────────────────────┐      ┌──────────────────────────┐
│   PLAYER PROP ANALYSIS   │      │   TEAM MARKET ANALYSIS   │
│                          │      │                          │
│  ┌────────────────────┐  │      │  ┌────────────────────┐  │
│  │ DataBallr Scraper  │  │      │  │ Team Form Analysis │  │
│  │ • Game logs        │  │      │  │ • Offensive rating │  │
│  │ • Historical stats │  │      │  │ • Defensive rating │  │
│  │ • Hit rates        │  │      │  │ • Win percentage   │  │
│  └────────────────────┘  │      │  │ • Pace/trends      │  │
│           ↓              │      │  └────────────────────┘  │
│  ┌────────────────────┐  │      │           ↓              │
│  │ Projection Model   │  │      │  ┌────────────────────┐  │
│  │ • Statistical proj │  │      │  │ Game Projection    │  │
│  │ • Expected value   │  │      │  │ • Score prediction │  │
│  │ • Probability      │  │      │  │ • Win probability  │  │
│  └────────────────────┘  │      │  │ • Total/spread     │  │
│           ↓              │      │  └────────────────────┘  │
│  ┌────────────────────┐  │      │           ↓              │
│  │ Matchup Engine     │  │      │  ┌────────────────────┐  │
│  │ • Opponent defense │  │      │  │ Market Evaluation  │  │
│  │ • Pace factors     │  │      │  │ • Moneyline value  │  │
│  │ • Blowout risk     │  │      │  │ • Total value      │  │
│  └────────────────────┘  │      │  │ • Spread value     │  │
│           ↓              │      │  └────────────────────┘  │
│  ┌────────────────────┐  │      │           ↓              │
│  │ Confidence Engine  │  │      │  ┌────────────────────┐  │
│  │ • Sample size      │  │      │  │ Confidence Scoring │  │
│  │ • Volatility       │  │      │  │ • Sample size      │  │
│  │ • Role changes     │  │      │  │ • Consistency      │  │
│  │ • Risk class       │  │      │  │ • Probability      │  │
│  └────────────────────┘  │      │  └────────────────────┘  │
└──────────────────────────┘      └──────────────────────────┘
           ↓                                    ↓
           └────────────────┬───────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RECOMMENDATION FILTERING                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Minimum Confidence Filter (default: 55%)             │   │
│  │ 2. Positive Expected Value Filter (EV > 0)              │   │
│  │ 3. Correlation Filter (max 2 bets per game)             │   │
│  │ 4. Sort by Projected Probability (highest first)        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FINAL RECOMMENDATIONS                       │
│                                                                   │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │   PLAYER PROPS      │  │   TEAM MARKETS      │              │
│  │                     │  │                     │              │
│  │ • Player name       │  │ • Market type       │              │
│  │ • Stat/line         │  │ • Selection         │              │
│  │ • Odds              │  │ • Odds              │              │
│  │ • Confidence        │  │ • Confidence        │              │
│  │ • Edge/EV           │  │ • Edge/EV           │              │
│  │ • Matchup factors   │  │ • Projection        │              │
│  │ • Historical data   │  │ • Reasoning         │              │
│  └─────────────────────┘  └─────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                           OUTPUT                                 │
│                                                                   │
│  • Console display (ranked by probability)                       │
│  • JSON file (betting_recommendations.json)                      │
│  • Top 5 recommendations                                         │
└─────────────────────────────────────────────────────────────────┘
```

## Data Sources

### Player Props
```
Sportsbet Insights → DataBallr Stats → Projection Model → Confidence Engine
```

### Team Markets
```
Sportsbet Insights → Recent Results → Team Form → Game Projection → Market Evaluation
```

## Analysis Components

### Player Prop Pipeline
1. **Data Collection**: Scrape player prop insights from Sportsbet
2. **Validation**: Fetch game logs from DataBallr (last 20 games)
3. **Projection**: Statistical model projects expected value
4. **Matchup**: Adjust for opponent defense, pace, blowout risk
5. **Confidence**: V2 engine with sample size caps, volatility penalties
6. **Value**: Calculate edge and expected value vs odds

### Team Market Pipeline
1. **Data Collection**: Extract recent game results from insights
2. **Form Analysis**: Calculate offensive/defensive ratings, pace, trends
3. **Projection**: Project scores using four factors approach
4. **Adjustments**: Apply home court advantage, pace, momentum
5. **Probabilities**: Calculate win/cover/over probabilities
6. **Value**: Evaluate each market for positive EV

## Key Differences

| Aspect | Player Props | Team Markets |
|--------|-------------|--------------|
| **Data Source** | DataBallr game logs | Sportsbet insights |
| **Sample Size** | 5-20 games | 5-10 games |
| **Projection** | Statistical model | Form-based |
| **Adjustments** | Matchup, volatility | Pace, momentum |
| **Confidence** | 55-95% | 50-95% |
| **Markets** | Over/under stats | ML/Total/Spread |

## Confidence Scoring

### Player Props (Confidence Engine V2)
```
Base Confidence (60-80%)
  + Sample Size Boost (0-10%)
  + Consistency Boost (0-5%)
  - Volatility Penalty (0-10%)
  - Role Change Penalty (0-15%)
  + Matchup Adjustment (±5%)
  = Final Confidence (55-95%)
```

### Team Markets
```
Base Confidence (Sample Size × 10)
  + Consistency Boost (Low variance)
  + Probability Boost (Higher win %)
  = Final Confidence (50-95%)
```

## Output Format

### Player Prop Example
```
1. Anthony Edwards (Timberwolves) - Points Over 24.5
   Game: Timberwolves @ Pelicans (Dec 5, 2025 7:30 PM)
   Matchup: vs Pelicans
   Odds: 1.90 | Confidence: 68% | Strength: HIGH
   Edge: +8.2% | EV: +16.1%
   Historical: 65.0% (20 games)
   Projected: 68.5%
   
   Minutes: 35.2min avg (last 5), STABLE rotation
   Scoring: 26.8 ppg (last 5) | Consistency: 80%
   
   Matchup: 1.08x multiplier (FAVORABLE)
   Pace: Fast (1.05x)
   Defense: Weak vs points (1.06x, rank 28)
```

### Team Market Example
```
2. TEAM MARKET: Total - Over 223.5
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
     • Lakers offense trending up
```

## Integration Benefits

### Diversification
- **Player Props**: Individual performance bets
- **Team Markets**: Game outcome bets
- **Combined**: Broader opportunity set

### Risk Management
- Correlation filter prevents over-betting single games
- Different data sources reduce systematic risk
- Confidence scores guide stake sizing

### Value Identification
- Player props: Exploit matchup inefficiencies
- Team markets: Exploit form/momentum inefficiencies
- Both: Positive EV focus

## Usage Patterns

### Default (Both)
```bash
python nba_betting_system.py
# Analyzes player props + team markets
# Outputs top 5 combined recommendations
```

### Player Props Only
```bash
python nba_betting_system.py --player-props-only
# Skips team market analysis
# Faster execution
```

### Team Markets Only
```bash
python nba_betting_system.py --team-markets
# Could add flag to skip player props
# Currently not implemented
```

## Performance Tracking

### Metrics to Track
1. **Win Rate**: % of bets that win
2. **ROI**: Return on investment
3. **Confidence Calibration**: Does 70% confidence = 70% win rate?
4. **Edge Realization**: Does +8% edge = +8% ROI?
5. **Market Performance**: Player props vs team markets

### Expected Results (50+ bets)
- **Win Rate**: 55-60% on 50/50 bets
- **ROI**: 3-5% long-term
- **Confidence**: Within ±5% of actual win rate
- **Edge**: Within ±3% of actual ROI

---

**System Version**: 2.0 (with Team Markets)
**Last Updated**: December 5, 2025
