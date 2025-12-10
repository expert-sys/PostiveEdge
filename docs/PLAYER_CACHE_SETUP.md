# Player Cache System - Hybrid Approach

## 🎯 System Overview

The hybrid cache system combines **fast ID lookups** with **pre-cached game stats** for optimal performance:

- **Player ID Cache**: Instant name-to-ID mapping (~30 seconds to build)
- **Stats Cache**: Pre-fetched game data for top 150 players (~5-10 minutes)
- **On-Demand**: Rare/bench players fetched during analysis

## 📋 Setup Steps

### First-Time Setup (Required)

1. **Build Player ID Cache** (30 seconds)
   ```bash
   python launcher.py
   # Select: 3 → 1 (Build Comprehensive Cache)
   ```
   - Reads PlayerIDsV2.txt (600+ players)
   - Creates smart name mappings
   - Handles variants: "E.J. Liddell" → "ej liddell", "e j liddell"

2. **Fetch Stats for Top Players** (5-10 minutes, optional but recommended)
   ```bash
   python launcher.py
   # Select: 3 → 2 (Fetch Stats for Top 150 Players)
   ```
   - Pre-fetches last 15 games for 150 top players
   - Calculates averages (PPG, RPG, APG, etc.)
   - Caches for 24 hours

### Daily Maintenance

**Quick Update** (1-2 minutes)
```bash
python launcher.py
# Select: 3 → 3 (Update Cache Daily)
```
- Adds new players from PlayerIDsV2.txt
- Optionally refreshes stats (only if >24 hours old)

## 📊 Cache Files

### 1. Player ID Cache
**Location**: `data/cache/databallr_player_cache.json`

**Contents**:
```json
{
  "timestamp": "2025-12-03T10:30:00",
  "total_players": 600,
  "cache": {
    "lebron james": 2544,
    "ej liddell": 1630604,
    "shai gilgeous alexander": 1628983
  },
  "display_names": {
    "2544": "LeBron James",
    "1630604": "E.J. Liddell"
  },
  "teams": {
    "2544": ["Los Angeles Lakers"]
  }
}
```

### 2. Player Stats Cache
**Location**: `data/cache/player_stats_cache.json`

**Contents**:
```json
{
  "timestamp": "2025-12-03T11:00:00",
  "total_players": 150,
  "cache": {
    "nikola jokic": {
      "timestamp": "2025-12-03T11:00:00",
      "game_count": 15,
      "averages": {
        "points": 26.8,
        "rebounds": 12.3,
        "assists": 9.1,
        "minutes": 34.5
      },
      "game_log": [ /* last 15 games */ ],
      "last_game_date": "12/02/2024"
    }
  }
}
```

## 🚀 Usage During Analysis

When running unified analysis:

1. **Top 150 Players**: Uses cached stats (instant)
2. **Other Players in Cache**: Fetches from databallr (2-3 seconds)
3. **Not in Cache**: Skips with warning (add to PlayerIDsV2.txt)

## 🔧 Maintenance Schedule

### Daily (Automated via launcher)
- Run "Update Cache Daily" before analysis
- Only fetches fresh stats if >24 hours old

### Weekly
- Check for new players on rosters
- Add URLs to PlayerIDsV2.txt
- Run "Build Comprehensive Cache"

### Monthly
- Review stats cache size
- Clean up inactive players if needed

## 📈 Performance Benefits

| Action | Without Cache | With ID Cache | With Both Caches |
|--------|--------------|---------------|------------------|
| Initial Setup | N/A | 30 sec | 10 min |
| Analysis (10 props) | 30-60 sec | 20-40 sec | 5-10 sec |
| Daily Update | N/A | 1 min | 2-3 min |

## 🎮 Quick Reference

### Launcher Menu → Option 3: Player Cache Management

```
1. Build Comprehensive Cache (First-time: IDs only, 30 seconds)
2. Fetch Stats for Top 150 Players (Pre-cache game stats, 5-10 mins)
3. Update Cache Daily (Quick: Add new players, refresh top stats)
4. View Cache Stats
5. Back to main menu
```

### View Cache Stats Output

```
[1] PLAYER ID CACHE
Status: READY
Last Updated: 2025-12-03T10:30:00
Total Players: 600
Total Mappings: 750 (includes variants)

[2] PLAYER STATS CACHE
Status: READY
Last Updated: 2025-12-03T11:00:00 (2h ago)
Cached Players: 150

Sample (with averages):
  Nikola Jokic: 26.8/12.3/9.1 (15G)
  Shai Gilgeous-Alexander: 30.5/5.2/6.3 (15G)
  ...

RECOMMENDATION:
  All caches are fresh! Ready for analysis.
```

## 🛠️ Troubleshooting

### "Player not in cache" warning
1. Find player on databallr.com
2. Copy URL: `https://databallr.com/last-games/ID/slug`
3. Add to `PlayerIDsV2.txt`
4. Run: Build Comprehensive Cache

### Stats cache is old
- Run: Fetch Stats for Top 150 Players
- Or: Update Cache Daily → Yes to stats refresh

### Analysis is slow
- Make sure both caches are built
- Check "View Cache Stats" for freshness
- Consider adding frequently-analyzed players to TOP_PLAYERS list in `fetch_player_stats_batch.py`

## 📝 Advanced: Customizing Top Players List

Edit `fetch_player_stats_batch.py`:

```python
TOP_PLAYERS = [
    # Add your most-analyzed players here
    "Your Favorite Player",
    "Another Player",
    # ... existing list ...
]
```

Then run "Fetch Stats for Top 150 Players" to pre-cache them.

## ✅ Verification

After setup, verify everything works:

```bash
python launcher.py
# 3 → 4 (View Cache Stats)
```

Expected output:
- Player ID Cache: READY (600+ players)
- Stats Cache: READY (150 players)
- Recommendation: "All caches are fresh!"

Then run analysis to test:
```bash
python launcher.py
# 1 (Run Unified Analysis)
```

Should see: Fast lookups for cached players, minimal scraping delays.

