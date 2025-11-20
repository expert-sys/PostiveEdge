# NBA Player ID Cache System

## Overview

The NBA Player ID Cache system eliminates API timeouts and failures by maintaining a local cache of all NBA player IDs. This makes player lookups instant and reliable.

## How It Works

### 1. **Automatic Cache Building**
- On first run, downloads full NBA player list from `stats.nba.com`
- Stores in `data/cache/nba_player_cache.json`
- Refreshes automatically once per day
- Creates multiple name variations for each player

### 2. **Name Normalization**
All player names are normalized before lookup:
- Lowercase everything
- Remove punctuation
- Remove Jr., Sr., III, etc.
- Convert multiple spaces → one
- Example: "Gary Trent Jr." → "gary trent"

### 3. **Fuzzy Matching**
If exact match fails:
- Uses Levenshtein similarity (≥ 90% threshold)
- Token matching ("john collins" = "collins john")
- Handles misspellings and variations

### 4. **Manual Overrides**
File: `data/cache/nba_player_overrides.json`

Add entries for edge cases:
```json
{
  "bogdan bogdanovic": 203992,
  "bojan bogdanovic": 202711,
  "bob portis": 1626171
}
```

### 5. **Integration**
- Automatically initializes when any scraper imports `nba_stats_api_scraper`
- Works through launcher, scripts, and all entry points
- Falls back gracefully if cache unavailable

## Benefits

✅ **Zero timeouts** - No API calls for player ID lookups  
✅ **Zero failures** - Local dictionary lookup  
✅ **Faster analysis** - Instant lookups  
✅ **More reliable** - Works even if NBA API is down  

## Cache Files

- `data/cache/nba_player_cache.json` - Main player cache (auto-generated)
- `data/cache/nba_player_overrides.json` - Manual overrides (editable)

## Usage

The cache is used automatically. No manual intervention needed.

To manually refresh the cache:
```python
from scrapers.nba_player_cache import get_player_cache
cache = get_player_cache()
cache._load_cache()  # Force refresh
```

## Troubleshooting

**Cache not building?**
- Check internet connection
- Check `data/cache/` directory exists and is writable
- Check NBA.com API is accessible

**Player not found?**
- Add to `nba_player_overrides.json`
- Check name normalization (remove Jr., punctuation, etc.)
- Verify player is active in current season

