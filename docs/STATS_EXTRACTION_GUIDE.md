# Sportsbet Stats & Insights Extraction

## Overview

The enhanced scraper now extracts comprehensive team statistics from Sportsbet's "Stats & Insights" tab for each match. This data is critical for the value engine to make more informed predictions.

## Data Extracted

### 1. **Records Section**
- ✅ **Average Points For** - Team's average scoring
- ✅ **Average Points Against** - Team's average points allowed
- ✅ **Average Winning Margin** - Average margin when winning
- ✅ **Average Losing Margin** - Average margin when losing
- ✅ **Average Total Match Points** - Average combined score

### 2. **Performance Records**
- ✅ **Favorite Win %** - Win rate when favored
- ✅ **Underdog Win %** - Win rate as underdog
- ✅ **Night Record** - Win/Loss % in night games

### 3. **Under Pressure Stats**
- ✅ **Clutch Win %** - Win rate in games decided by ≤5 points
- ✅ **Reliability %** - Win rate after leading at halftime
- ✅ **Comeback %** - Win rate after trailing at halftime
- ✅ **Choke %** - Loss rate after leading at halftime

### 4. **Data Range**
- Tracks which dataset is being used (e.g., "Last 10 Matches", "Last 5 Matches", "Season 2025/26")

## Data Structure

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

    # Performance Records
    favorite_win_pct: Optional[float]
    underdog_win_pct: Optional[float]
    night_win_pct: Optional[float]
    night_loss_pct: Optional[float]

    # Under Pressure
    clutch_win_pct: Optional[float]
    reliability_pct: Optional[float]
    comeback_pct: Optional[float]
    choke_pct: Optional[float]

@dataclass
class MatchStats:
    away_team_stats: TeamStats
    home_team_stats: TeamStats
    data_range: str
```

## Usage

### Basic Extraction

```python
from scrapers.sportsbet_final_enhanced import scrape_match_complete

# Scrape match with stats
match_data = scrape_match_complete(game_url, headless=True)

# Access stats
if match_data.match_stats:
    away_stats = match_data.match_stats.away_team_stats
    home_stats = match_data.match_stats.home_team_stats

    print(f"Away Avg Points For: {away_stats.avg_points_for}")
    print(f"Home Clutch Win %: {home_stats.clutch_win_pct}%")
```

### Complete Match Data

```python
# The CompleteMatchData object now includes:
{
    'away_team': str,
    'home_team': str,
    'markets': {...},           # Betting markets
    'match_insights': [...],    # Historical insights
    'match_stats': {            # NEW: Team statistics
        'data_range': str,
        'away_team': {
            'team_name': str,
            'avg_points_for': float,
            'clutch_win_pct': float,
            ...
        },
        'home_team': {
            'team_name': str,
            'avg_points_for': float,
            'clutch_win_pct': float,
            ...
        }
    }
}
```

## Value to the Engine

This data is **extremely valuable** for context-aware analysis:

### 1. **Scoring Context**
- `avg_points_for` / `avg_points_against` → Inform total/spread predictions
- `avg_total_points` → Direct input for over/under analysis

### 2. **Situational Performance**
- `favorite_win_pct` / `underdog_win_pct` → Adjust confidence based on betting line
- `night_win_pct` → Game time context factor
- `clutch_win_pct` → High-pressure situation reliability

### 3. **Momentum & Psychology**
- `reliability_pct` → Team's ability to close out leads
- `comeback_pct` → Resilience when trailing
- `choke_pct` → Risk of blowing leads (inverse reliability)

### 4. **Trend Quality Enhancement**

Can now classify insights with additional context:

```python
# Before: "Team has won 8/10 games" → 80% probability
# After:  "Team has won 8/10 games" + favorite_win_pct=65% → More nuanced analysis
```

## Integration with Value Engine

### Current Usage

The stats are automatically extracted and stored with each match. To use in analysis:

```python
# In context_aware_analysis.py
def enhance_with_match_stats(match_stats: MatchStats, context_factors: ContextFactors):
    """
    Enhance context factors with match statistics
    """
    away = match_stats.away_team_stats
    home = match_stats.home_team_stats

    # Adjust probability based on favorite/underdog status
    if is_favorite:
        base_prob *= (away.favorite_win_pct / 50.0)  # Scale around 50%
    else:
        base_prob *= (away.underdog_win_pct / 50.0)

    # Adjust for clutch situations
    if is_close_game:
        context_factors.reliability_multiplier = away.clutch_win_pct / 50.0

    # Penalize choke risk
    if team_leading:
        choke_risk = away.choke_pct / 100.0
        confidence_adjustment -= choke_risk * 20  # Up to -20 confidence points
```

### Recommended Enhancements

1. **Add Stats-Based Priors**
   ```python
   # Use team stats as Bayesian priors instead of flat 50%
   league_avg = 0.50
   team_prior = (avg_points_for / (avg_points_for + avg_points_against))
   ```

2. **Situational Weighting**
   ```python
   # Weight insights based on situational stats
   if "when favorite" in insight:
       weight = favorite_win_pct / 50.0
   elif "clutch" in insight:
       weight = clutch_win_pct / 50.0
   ```

3. **Confidence Boosting**
   ```python
   # Boost confidence when stats align with insights
   if reliability_pct > 70 and insight == "leads at HT":
       confidence_score += 15
   ```

## Testing

Run the test script to verify extraction:

```bash
python test_stats_extraction.py
```

Expected output:
```
✅ STATS EXTRACTED SUCCESSFULLY!

Extracted Fields:
  ✅ Average Points For/Against
  ✅ Winning/Losing Margins
  ✅ Average Total Points
  ✅ Favorite Win %
  ✅ Underdog Win %
  ✅ Night Record
  ✅ Clutch Win %
  ✅ Reliability %
  ✅ Comeback %
  ✅ Choke %
```

## Files Modified

- `scrapers/sportsbet_final_enhanced.py` - Added stats extraction
- `scrapers/sportsbet_complete_analysis.py` - Will use stats (TODO)
- `scrapers/context_aware_analysis.py` - Will integrate stats (TODO)

## Next Steps

1. ✅ Extract all stats from Sportsbet
2. ⏳ Pass stats to context-aware analyzer
3. ⏳ Use stats as Bayesian priors
4. ⏳ Adjust confidence based on situational stats
5. ⏳ Add stats-based trend quality modifiers
