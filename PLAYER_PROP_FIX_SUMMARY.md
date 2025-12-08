# Player Prop Recognition Fix - Summary

## Problem
The NBA betting system was not properly recognizing and parsing player prop insights from Sportsbet. Player props were being missed or incorrectly parsed.

## Root Causes Identified

### 1. **Incorrect Line Adjustment**
- **Issue**: The code was subtracting 0.5 from ALL lines, even when they were already in decimal format (e.g., 3.5)
- **Fix**: Only subtract 0.5 when the line is a whole number with "+" (e.g., "4+" becomes 3.5)

### 2. **Sportsbet Format Not Recognized**
- **Issue**: Sportsbet uses a specific format for player props: `"Over (+X.X) - Player Name Stat Type"`
  - Example: `"Over (+3.5) - Anthony Edwards Made Threes"`
- **Previous code**: Only looked for generic patterns, missing this specific format
- **Fix**: Added dedicated parsing for this format (Method 1) with fallback to generic patterns (Method 2)

### 3. **Player Name Extraction Issues**
- **Issue**: Regex was capturing stat keywords as part of player names
  - Example: "Anthony Edwards Made" instead of "Anthony Edwards"
- **Fix**: Split market string on dash first, then extract player name by finding everything before stat keywords

### 4. **Team vs Player Insight Confusion**
- **Issue**: Team-level insights were being mistaken for player props
  - Example: "Minnesota Timberwolves - Match" insights about team performance
- **Fix**: Added filters to exclude insights with:
  - Team names in the market field
  - "- Match" suffix in market
  - Team keywords without player names

### 5. **Name Pattern Limitations**
- **Issue**: Regex pattern `[A-Z][a-z]+` couldn't handle names like "LeBron" (capital B in middle)
- **Fix**: Updated pattern to `[A-Z][a-zA-Z\'-]+` to handle:
  - Mixed case names (LeBron, DeAndre)
  - Hyphenated names (Karl-Anthony)
  - Apostrophes (D'Angelo)

## Changes Made

### File: `nba_betting_system.py`

#### 1. Enhanced `_is_player_prop_insight()` method
```python
# Added Method 1: Check for "Over/Under (+X.X) - Player Name" format
has_over_under_format = bool(re.search(r'(?:Over|Under)\s*\(\+?-?\d+\.?\d*\)\s*-\s*[A-Z]', market))

# Added team filtering
has_team_in_market = any(team in market_lower for team in team_keywords)
is_match_insight = '- match' in market_lower

return has_stat and has_player and not has_team_in_market and not is_match_insight
```

#### 2. Rewrote `_parse_prop_from_insight()` method
```python
# METHOD 1: Parse "Over (+X.X) - Player Name Stat" format
# Split on dash, extract line and player/stat separately
market_split = re.split(r'\s*-\s*', market, maxsplit=1)

# Extract player name by finding text before stat keywords
stat_keywords_pattern = r'\b(Made|Points?|Rebounds?|...)\b'
player_name = player_stat_part[:stat_match.start()].strip()

# METHOD 2: Fallback for other formats (existing logic)
```

#### 3. Fixed line adjustment logic
```python
# Only adjust whole numbers with "+"
if '.' not in match.group(1) and '+' in search_text:
    line = line - 0.5  # "4+" becomes 3.5
# Otherwise use line as-is (3.5 stays 3.5)
```

#### 4. Improved player name regex
```python
# Old: r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})'
# New: r'([A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+){1,2})'
```

#### 5. Added debug logging
```python
logger.debug(f"  Total insights found: {len(insights)}")
logger.debug(f"  Found {len(player_prop_insights)} player prop insights")
logger.debug(f"    Parsing insight - Market: {market}")
```

## Test Results

Created `test_prop_parsing.py` with 5 test cases:

1. ✓ **New Sportsbet format**: `"Over (+3.5) - Anthony Edwards Made Threes"` → Parsed correctly
2. ✓ **Team insight filtered**: `"Minnesota Timberwolves - Match"` → Correctly excluded
3. ✓ **Whole number with +**: `"25+ points"` → Converted to 24.5 line
4. ✓ **Decimal line**: `"Over 7.5 assists"` → Used 7.5 as-is
5. ✓ **Standard format**: `"Over (+9.5) - Nikola Jokic Rebounds"` → Parsed correctly

All tests passing ✓

## Impact

### Before Fix
- Player props in Sportsbet's "Over (+X.X) - Player Name Stat" format were not recognized
- Lines were incorrectly adjusted (3.5 became 3.0)
- Team insights were processed as player props
- Names like "LeBron" were parsed as "Bron"

### After Fix
- ✓ Correctly identifies player props in Sportsbet's format
- ✓ Properly handles both whole number and decimal lines
- ✓ Filters out team-level insights
- ✓ Handles all name formats (LeBron, Karl-Anthony, D'Angelo)
- ✓ Better logging for debugging

## Next Steps

1. Run the full pipeline on live Sportsbet data to verify
2. Monitor logs for any edge cases
3. Consider adding more stat types if needed (turnovers, minutes, etc.)

## Files Modified
- `nba_betting_system.py` - Main pipeline (enhanced parsing logic)
- `test_prop_parsing.py` - Test script (created for validation)
- `PLAYER_PROP_FIX_SUMMARY.md` - This document
