# Enhanced Value Engine - Complete Guide

## Overview

The **Enhanced Value Engine v2** integrates team-level statistics from Sportsbet to make smarter, data-driven betting predictions. It fixes the critical sample-size overweighting problem and adds sophisticated team-form adjustments.

## Key Improvements

### 1. **Sample Size Regression** ✅
**Problem**: 5/5 success rate was treated as 100% probability (locked bet)

**Solution**: Bayesian shrinkage + regression to mean
- 5/5 → ~72% probability (not 100%)
- 30/30 → ~95% probability (trust builds with sample size)
- Small samples are heavily regressed to league average (50%)

### 2. **Team Stats Integration** ✅
**Integrates data from Sportsbet Stats & Insights**:
- Records (Points For/Against, Margins, Totals)
- Performance (Favorite/Underdog Win %, Night Records)
- Under Pressure (Clutch Win %, Reliability %, Comeback %, Choke %)

### 3. **Market-Specific Adjustments** ✅

#### **Match Markets** (Moneyline)
- **Form Adjustment**: Based on offensive/defensive performance differential
  - Formula: `(Points For - Points Against) difference × 0.006`
  - Example: Team A +5 net pts vs Team B = +3% probability boost

- **Favorite/Underdog Adjustment**: Historical conversion rates
  - Strong favorite (65% win rate) = +2.4% boost
  - Weak underdog (30% win rate) = -3.2% penalty

- **Clutch Adjustment**: For close games
  - Teams with 60%+ clutch win rate get boosted in tight matchups

#### **Total Markets** (Over/Under)
- **Projected Total**: Calculated from team scoring averages
  - Method 1: Average of both teams' avg_total_points
  - Method 2: Weighted projection from Points For/Against
  - Formula: `(Team A offense × 0.6 + Team B defense × 0.4) + (Team B offense × 0.6 + Team A defense × 0.4)`

- **Line Comparison**: Projected vs Bookmaker line
  - Each point difference = 1.5% probability shift
  - Example: Projected 220, line 215 → +7.5% to OVER

### 4. **Sophisticated Probability Pipeline** ✅

```
Raw Historical (e.g., 5/5 = 100%)
    ↓
Bayesian Shrinkage (85.7%)
    ↓
Recency Weighting (exponential decay for recent games)
    ↓
Sample Size Weighting (logarithmic scaling)
    ↓
Regression to Mean (72.1%)
    ↓
Team Form Adjustments (+/- based on stats)
    ↓
Volatility Adjustment (confidence penalty for 50/50 bets)
    ↓
Final Adjusted Probability (57.1%)
```

## Usage

### Basic Example

```python
from value_engine_enhanced import EnhancedValueEngine, TeamStats

# Create engine
engine = EnhancedValueEngine()

# Load team stats (from Sportsbet)
lakers_stats = TeamStats(
    team_name="Lakers",
    avg_points_for=113.1,
    avg_points_against=113.4,
    favorite_win_pct=60.0,
    underdog_win_pct=40.0,
    clutch_win_pct=50.0
)

warriors_stats = TeamStats(
    team_name="Warriors",
    avg_points_for=116.3,
    avg_points_against=111.8,
    favorite_win_pct=62.5,
    clutch_win_pct=33.3
)

# Analyze match market
analysis = engine.analyze_with_team_stats(
    historical_outcomes=[1, 1, 0, 1, 1, 0, 1, 1],  # 6/8 historical wins
    bookmaker_odds=1.85,
    team_a_stats=lakers_stats,
    team_b_stats=warriors_stats,
    market_type="match",
    is_favourite=True
)

print(analysis)
```

### Output

```
Sample Size: 8

PROBABILITIES:
  Raw Historical: 75.0%
  Bayesian Adjusted: 70.0%
  Recency Weighted: 75.4%
  Regressed to Mean: 69.1%
  Final Adjusted: 67.8%
  Bookmaker Implied: 54.1%

ADJUSTMENTS:
  Team Form: -0.029
  Fav/Underdog: +0.016
  Volatility: 0.564x

VALUE:
  Edge: +13.8%
  EV per $100: $+14.38
  Has Value: True

CONFIDENCE: 58.5/100
```

### Total Market Example

```python
# Analyze Over/Under
analysis = engine.analyze_with_team_stats(
    historical_outcomes=[1, 1, 1, 1, 1],  # 5/5 overs hit
    bookmaker_odds=1.9,
    team_a_stats=lakers_stats,
    team_b_stats=warriors_stats,
    market_type="total",
    market_line=237.5
)
```

Output shows projected total vs line:
```
Projected Total: 227.3 (line: 237.5)
Total adjustment: -0.150
Final Adjusted: 57.1%  (down from 100% raw)
```

### Integration with Sportsbet Data

```python
from scrapers.sportsbet_final_enhanced import scrape_match_complete
from value_engine_enhanced import EnhancedValueEngine, TeamStats

# Scrape match
match_data = scrape_match_complete(game_url)

if match_data.match_stats:
    # Extract stats
    away_stats_dict = match_data.match_stats.away_team_stats.to_dict()
    home_stats_dict = match_data.match_stats.home_team_stats.to_dict()

    # Convert to TeamStats
    away_stats = TeamStats(**away_stats_dict)
    home_stats = TeamStats(**home_stats_dict)

    # Analyze
    engine = EnhancedValueEngine()
    analysis = engine.analyze_with_team_stats(
        historical_outcomes=extracted_from_insights,
        bookmaker_odds=odds,
        team_a_stats=away_stats,
        team_b_stats=home_stats,
        market_type="match"
    )
```

## Features & Formulas

### Sample Size Weighting

```python
weight = min(1.0, log(n + 1) / log(21))

# n=5:  weight = 0.56
# n=10: weight = 0.79
# n=20: weight = 1.00
```

### Bayesian Shrinkage

```python
adjusted = (wins + 1) / (n + 2)

# 5/5 → 6/7 = 85.7% (not 100%)
# 10/10 → 11/12 = 91.7%
# 50/50 → 51/52 = 98.1%
```

### Regression to Mean

```python
weight = min(1.0, n / 11)
regressed = observed × weight + league_avg × (1 - weight)

# Small n → pulls hard toward 50%
# Large n → trusts observed value
```

### Team Form Score

```python
form_score = avg_points_for - avg_points_against

# Lakers: 113.1 - 113.4 = -0.3
# Warriors: 116.3 - 111.8 = +4.5
# Differential: -4.8
# Adjustment: -4.8 × 0.006 = -2.9%
```

### Projected Total

```python
team_a_score = (a_points_for × 0.6) + (b_points_against × 0.4)
team_b_score = (b_points_for × 0.6) + (a_points_against × 0.4)
projected_total = team_a_score + team_b_score
```

## Confidence Scoring

```python
confidence = (
    0.6 × sample_size_weight +
    0.3 × recency_score +
    0.1 × market_agreement
) × (1 - 0.4 × volatility)
```

**Factors**:
- Sample size (60% weight)
- Recent form consistency (30% weight)
- Market agreement with sharp books (10% weight)
- Penalty for high volatility (reduces up to 40%)

## Warnings System

Automatic warnings for:
- ❌ Very small samples (n<5)
- ❌ Small samples with regression (n<10)
- ❌ High choke rates (>25%)
- ❌ Extreme value (>20% edge) - verify data
- ❌ Missing team stats

## Comparison: Old vs New

### Example: 5/5 Success Rate

**Old Engine**:
```
Historical Probability: 100.0%
Implied Odds: 1.00
EV: Massive
Recommendation: LOCK BET
```

**New Enhanced Engine**:
```
Raw Historical: 100.0%
Bayesian Adjusted: 85.7%
Regressed to Mean: 72.1%
Final Adjusted: 57.1% (after team stats)
Confidence: 56.5/100
Warnings: Small sample - probability heavily regressed
```

### Example: Total Market

**Old Engine**:
```
Historical: 5/5 overs = 100%
No team context
Pure historical
```

**New Enhanced Engine**:
```
Historical: 5/5 = 100% raw
Projected Total: 227.3 (from team stats)
Market Line: 237.5
Adjustment: -15% (line too high)
Final: 57.1%
Note: Projected total 10 points UNDER line
```

## API Reference

### TeamStats

```python
@dataclass
class TeamStats:
    team_name: str
    # Records
    avg_points_for: Optional[float]
    avg_points_against: Optional[float]
    avg_winning_margin: Optional[float]
    avg_losing_margin: Optional[float]
    avg_total_points: Optional[float]
    # Performance
    favorite_win_pct: Optional[float]
    underdog_win_pct: Optional[float]
    night_win_pct: Optional[float]
    # Under Pressure
    clutch_win_pct: Optional[float]
    reliability_pct: Optional[float]
    comeback_pct: Optional[float]
    choke_pct: Optional[float]
```

### EnhancedValueEngine.analyze_with_team_stats()

```python
def analyze_with_team_stats(
    historical_outcomes: List[int],      # Required: [1,1,0,1,...]
    bookmaker_odds: float,               # Required: decimal odds
    team_a_stats: Optional[TeamStats],   # Team stats
    team_b_stats: Optional[TeamStats],   # Opponent stats
    market_type: str = "match",          # "match", "total", "handicap", "prop"
    is_favourite: bool = False,          # For fav/dog adjustment
    market_line: Optional[float] = None, # For totals/handicap
    is_close_game: bool = False,         # For clutch adjustment
    days_ago: Optional[List[int]] = None,# For recency weighting
    context: Optional[Dict] = None       # Additional context
) -> EnhancedValueAnalysis
```

## Next Steps

1. ✅ Created enhanced engine with team stats
2. ⏳ Integrate with sportsbet_complete_analysis.py
3. ⏳ Use in insights_to_value_analysis.py
4. ⏳ Add handicap market projections
5. ⏳ Add player prop adjustments (minutes risk, role changes)

## Files

- `value_engine_enhanced.py` - New enhanced engine
- `value_engine.py` - Original simple engine (kept for backwards compatibility)
- `docs/ENHANCED_ENGINE_GUIDE.md` - This guide
- `docs/STATS_EXTRACTION_GUIDE.md` - Stats extraction documentation
