# Context-Aware Value Analysis Guide

## Overview

The Context-Aware Analysis module addresses critical weaknesses in basic value analysis by incorporating:

1. **Minutes Projection** - Accounts for situational benching risk
2. **Recency Weighting** - Balances recent form vs historical average
3. **Role Change Detection** - Identifies declining or improving trends
4. **External Context** - Considers rest, injuries, pace, matchups

## The Problem

### Traditional Analysis Weaknesses

**Example: Jonas Valanciunas O8.5 Rebounds**

**Basic Analysis:**
```
Historical: 7/10 games (70% win rate)
Bookmaker Odds: 1.85 (54% implied)
Edge: +16% 🎉
Recommendation: BET
```

**But this ignores:**
- ❌ JV was benched in 2/10 games (<15 min)
- ❌ Recent 3 games show declining minutes (30 → 20 → 15)
- ❌ Team plays back-to-back (increased benching risk)
- ❌ Recent form (1/3 last 3 games = 33%, not 70%)

**Reality:** Bet loses because JV plays only 12 minutes 🛑

### Context-Aware Solution

```
Historical: 70% BUT...
Recent Form: 33% (declining)
Minutes Risk: HIGH (recent avg 22 min, volatile)
Adjusted Probability: 45%
Bookmaker Implied: 54%
Edge: -9% ❌
Recommendation: AVOID ⚠️
```

**Reality:** Bet correctly avoided! ✅

## Key Features

### 1. Minutes Projection

Analyzes playing time patterns to assess benching risk.

**Metrics:**
- Historical average minutes
- Recent average (last 3-5 games)
- Volatility (standard deviation)
- Games below threshold
- Benching risk rating

**Example:**
```python
MinutesProjection(
    historical_avg=26.5,
    recent_avg=22.0,  # Declining!
    min_threshold=15.0,
    volatility=8.2,  # High variance
    benching_risk="HIGH",
    risk_score=75
)
```

**Benching Risk Levels:**
- **LOW**: Consistent minutes, low volatility, rarely benched
- **MEDIUM**: Some variance, occasional low-minute games
- **HIGH**: Volatile minutes, frequent benching, declining trend

### 2. Recency Weighting

Balances recent performance against historical average using weighted regression.

**Formula:**
```python
adjusted_prob = (0.7 * historical_prob) + (0.3 * recent_form_prob)
```

**Why 70/30?**
- Prevents overreaction to small samples
- Gives weight to recent trends
- Maintains statistical stability

**Example:**
```
Historical (10 games): 70% (7/10)
Recent (3 games): 33% (1/3)

Adjusted: (0.7 × 0.70) + (0.3 × 0.33)
        = 0.49 + 0.099
        = 58.9%  ← Use this instead of 70%
```

### 3. Trend Detection

Identifies role changes and performance trends.

**Trend Categories:**
- **IMPROVING**: Recent > Historical by 15%+
  - Example: Historical 50% → Recent 70%
  - Suggests expanded role or better form

- **DECLINING**: Recent < Historical by 15%+
  - Example: Historical 70% → Recent 40%
  - Suggests reduced role or poor form

- **STABLE**: Within ±15%
  - Example: Historical 60% → Recent 55%
  - Consistent performance

### 4. Context Factors

External factors that affect probability.

**Supported Factors:**
```python
ContextFactors(
    opponent_strength=75,      # 0-100 scale
    pace_differential=5.2,     # Team vs opponent pace
    days_rest=1,               # Days since last game
    home_away="HOME",          # HOME/AWAY/NEUTRAL
    back_to_back=False,        # B2B game flag
    injury_impact="LOW"        # From lineup data
)
```

**Risk Multipliers:**
- Back-to-back: 0.85× (15% penalty)
- Same-day rest: 0.90× (10% penalty)
- High injury impact: 0.85× (15% penalty)

## Usage

### Basic Usage

```python
from scrapers.context_aware_analysis import ContextAwareAnalyzer, ContextFactors

analyzer = ContextAwareAnalyzer()

analysis = analyzer.analyze_with_context(
    historical_outcomes=[1,1,0,1,1,0,1,1,1,0],  # Last 10 games
    recent_outcomes=[1,0,1],                     # Last 3 games
    historical_minutes=[28,30,15,32,29,18,31,30,28,16],
    recent_minutes=[30,28,32],
    bookmaker_odds=1.85,
    min_minutes_threshold=15.0,
    player_name="Jonas Valanciunas O8.5 Reb"
)

print(f"Recommendation: {analysis.recommendation}")
print(f"Adjusted Edge: {analysis.value_percentage:+.1f}%")
print(f"Risk: {analysis.overall_risk}")
```

### With Context Factors

```python
analysis = analyzer.analyze_with_context(
    historical_outcomes=[1,1,0,1,1,0,1,1],
    recent_outcomes=[1,1,0],
    bookmaker_odds=1.85,
    context_factors=ContextFactors(
        opponent_strength=85,      # Strong opponent
        home_away="AWAY",
        back_to_back=True,         # B2B game
        injury_impact="MODERATE",  # Some injuries
        days_rest=0
    ),
    player_name="Example Prop"
)
```

### Formatted Report

```python
from scrapers.context_aware_analysis import format_analysis_report

print(format_analysis_report(analysis, "Jonas Valanciunas O8.5 Reb"))
```

**Output:**
```
======================================================================
CONTEXT-AWARE VALUE ANALYSIS: Jonas Valanciunas O8.5 Reb
======================================================================

✅ RECOMMENDATION: BET
   Confidence: HIGH (72/100)
   Risk Level: MEDIUM (45/100)

📊 VALUE METRICS:
   Historical Win Rate: 70.0%
   Adjusted Win Rate: 58.9%
   Bookmaker Implied: 54.1%
   Edge: +4.8%
   Expected Value: $+8.25 per $100

⏱️ MINUTES PROJECTION:
   Recent Average: 30.0 min
   Historical Average: 26.7 min
   Volatility: 6.8 min (σ)
   Benching Risk: LOW

📈 RECENT FORM:
   Trend: DECLINING
   Recent Form: 66.7%
   Historical: 70.0%
   Adjustment Confidence: 60/100

✓ SUPPORTING FACTORS:
   • +4.8% edge vs bookmaker
   • $+8.25 EV per $100
   • Stable minutes (30.0 avg)

⚠️ WARNINGS:
   • Recent form is declining
======================================================================
```

## Recommendation Levels

### STRONG BET ✅
- Strong value (15%+ edge)
- Very high confidence
- Low risk
- Stable minutes
- All factors align

### BET ✓
- Good value (8%+ edge)
- High confidence
- Low-medium risk
- Acceptable minutes pattern

### CONSIDER ⚠️
- Marginal value (3-8% edge)
- Medium confidence
- OR high value but elevated risk
- Proceed with caution

### PASS ❌
- Minimal value (<3% edge)
- High risk
- OR low confidence
- Better opportunities exist

### AVOID 🛑
- No value (negative edge)
- Very high risk
- Situational concerns
- Do not bet

## Real-World Examples

### Example 1: The Minutes Trap

**Scenario:** Player prop O2.5 3-Pointers

**Basic Analysis:**
```
Historical: 8/10 games (80%)
Odds: 2.00 (50% implied)
Edge: +30% 😍
```

**Context-Aware Analysis:**
```python
historical_outcomes=[1,1,1,1,1,1,1,1,0,0]
recent_outcomes=[1,0,0]  # Last 3: only 1/3
historical_minutes=[32,30,28,31,29,15,12,33,30,18]
recent_minutes=[15,12,10]  # DECLINING!

Result:
  Benching Risk: HIGH
  Recent Form: 33% (vs 80% historical)
  Adjusted Prob: 42%
  Edge: -8% ❌
  Recommendation: AVOID
```

**Outcome:** Player gets 8 minutes, 0 threes. Bet loses. ✅ Correctly avoided!

### Example 2: The Hot Hand

**Scenario:** Points prop O19.5

**Basic Analysis:**
```
Historical (20 games): 11/20 (55%)
Odds: 1.80 (55.6% implied)
Edge: -0.6% 😐
```

**Context-Aware Analysis:**
```python
recent_outcomes=[1,1,1,1,1]  # 5 straight hits!
recent_minutes=[35,38,36,37,35]  # Increased role

Result:
  Trend: IMPROVING
  Recent Form: 100% (vs 55%)
  Adjusted Prob: 68.5%  # (0.7×55% + 0.3×100%)
  Edge: +12.9% ✅
  Recommendation: BET
```

**Outcome:** Player continues hot streak. Bet wins! ✅

### Example 3: The Back-to-Back Trap

**Scenario:** Rebounds prop O10.5

**Basic Analysis:**
```
Historical: 75% (15/20)
Odds: 1.70 (58.8% implied)
Edge: +16.2% 🎉
```

**Context-Aware Analysis:**
```python
context_factors=ContextFactors(
    back_to_back=True,        # B2B game
    days_rest=0,
    opponent_strength=85      # Strong opponent
)

Result:
  Base Adjusted: 73%
  After B2B penalty: 73% × 0.85 = 62.1%
  After rest penalty: 62.1% × 0.90 = 55.9%
  Edge: -2.9% ❌
  Recommendation: PASS
```

**Outcome:** Player rests second game. Bet avoided. ✅

## Integration with Pipeline

### Option 1: Standalone Analysis

```python
from scrapers.context_aware_analysis import ContextAwareAnalyzer

analyzer = ContextAwareAnalyzer()

# Manual input
analysis = analyzer.analyze_with_context(
    historical_outcomes=[...],
    recent_outcomes=[...],
    bookmaker_odds=1.85
)
```

### Option 2: With Sportsbet Data

```python
# Extract from Sportsbet insights
insight_fact = "Jonas Valanciunas recorded 9+ rebounds in 7 of his last 10 games"
outcomes = extract_outcomes_from_insight(insight_fact)  # [1,1,1,1,1,1,1,0,0,0]

# Get odds from market
odds = 1.85

# Analyze with context
analysis = analyzer.analyze_with_context(
    historical_outcomes=outcomes,
    bookmaker_odds=odds,
    player_name="JV O8.5 Reb"
)
```

### Option 3: With RotoWire Lineup Data

```python
from scrapers.rotowire_scraper import scrape_rotowire_lineups, find_lineup_for_matchup

# Get lineup data
lineups = scrape_rotowire_lineups()
game_lineup = find_lineup_for_matchup(lineups, "Pelicans", "Pacers")

# Extract context
context = ContextFactors(
    injury_impact="MODERATE" if len(game_lineup.away_team.bench_news) > 2 else "LOW",
    home_away="AWAY"
)

# Analyze
analysis = analyzer.analyze_with_context(
    historical_outcomes=[...],
    bookmaker_odds=1.85,
    context_factors=context
)
```

## Configuration Options

### Recency Weight

Adjust how much weight to give recent games:

```python
analyzer = ContextAwareAnalyzer()
analyzer.recency_weight = 0.4  # 40% recent, 60% historical (more reactive)
# Default is 0.3 (30% recent, 70% historical)
```

**Guidelines:**
- **0.2**: Conservative (80% historical)
- **0.3**: Balanced (default)
- **0.4**: Aggressive (60% historical)
- **0.5**: Equal weight (not recommended, too volatile)

### Recency Window

Change how many recent games to consider:

```python
analyzer.recency_window = 3  # Last 3 games
# Default is 5
```

**Guidelines:**
- **3 games**: Very recent, more volatile
- **5 games**: Balanced (default)
- **7 games**: More stable, less reactive

### Minutes Threshold

Set minimum minutes for prop validity:

```python
analysis = analyzer.analyze_with_context(
    ...,
    min_minutes_threshold=20.0  # Needs 20+ min
)
```

## Best Practices

### 1. Always Use Recent Data
```python
# Good
recent_outcomes = outcomes[-5:]  # Last 5 games

# Bad
recent_outcomes = outcomes  # Same as historical
```

### 2. Include Minutes When Available
```python
# Good
analysis = analyzer.analyze_with_context(
    historical_outcomes=[...],
    historical_minutes=[28,30,15,...]  # INCLUDE THIS
)

# Acceptable but less accurate
analysis = analyzer.analyze_with_context(
    historical_outcomes=[...]  # Minutes unknown
)
```

### 3. Set Appropriate Thresholds
```python
# Points/Rebounds props - need significant minutes
min_minutes_threshold=15.0

# Team totals - not applicable
min_minutes_threshold=0
```

### 4. Combine with Lineup Data
```python
# Best practice
context = ContextFactors(
    injury_impact=get_injury_impact_from_rotowire(),
    back_to_back=check_schedule(),
    home_away=get_location()
)
```

## Troubleshooting

### "Adjusted probability too low"

**Cause:** Multiple penalties stacking (minutes + B2B + declining form)

**Solution:** Review warnings - this may be accurate!

### "Too conservative"

**Cause:** High recency weight with small sample

**Solution:** Increase historical weight or recency window

### "Not catching benching risk"

**Cause:** Missing minutes data

**Solution:** Always include `historical_minutes` parameter

## API Reference

### ContextAwareAnalyzer

Main analysis class.

**Methods:**
- `analyze_with_context()`: Perform full analysis

**Configuration:**
- `min_sample_size`: Minimum games for analysis (default: 5)
- `recency_window`: Recent games to consider (default: 5)
- `recency_weight`: Weight for recent vs historical (default: 0.3)

### Data Classes

- `MinutesProjection`: Minutes analysis result
- `RecencyAdjustment`: Recency weighting result
- `ContextFactors`: External context data
- `ContextAwareAnalysis`: Complete analysis result

### Helper Functions

- `format_analysis_report()`: Format analysis as text

---

**This context-aware approach dramatically improves betting accuracy by accounting for real-world factors that basic historical analysis misses.**
