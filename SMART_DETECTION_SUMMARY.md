# Smart Player Detection - Databallr Scraper

## Overview

The databallr scraper now has **smart auto-detection** that automatically finds and caches players even when they're not in the cache yet. This solves the "chicken-and-egg" problem where the cache can't be built because players aren't in it.

## How It Works

When a player is requested but not found in cache, the system automatically:

### 1. **Cache Check (Fast)**
- First checks the existing cache file
- If found, verifies the URL works

### 2. **Smart Search Strategies**
If not in cache, tries multiple strategies:

#### Strategy A: Dashboard Search
- Navigates to databallr.com/dashboard
- Looks for search functionality
- Searches for player name
- Extracts player ID from search results

#### Strategy B: Last X Game Page Scan
- Navigates to databallr.com/last-games
- Scans page for player links
- Matches player name to links
- Extracts ID from matching URLs

#### Strategy C: Page Content Scan
- Searches through page HTML
- Looks for links matching player name patterns
- Verifies by navigating to candidate URLs
- Confirms player name appears on page

### 3. **Auto-Save to Cache**
- When a player is found via search, automatically saves to cache
- Cache file: `data/cache/databallr_player_cache.json`
- Player name is normalized (lowercase, periods removed)
- Next time, the player will be found instantly in cache

## Benefits

✅ **No Manual Setup Required** - Players are discovered automatically  
✅ **Cache Grows Automatically** - First time finds player, future times use cache  
✅ **Multiple Search Strategies** - Tries different methods to find players  
✅ **Graceful Fallback** - If search fails, provides helpful instructions  

## Example Flow

```
1. Request: "C.J. McCollum" (not in cache)
   → Tries cache: ❌ Not found
   → Tries dashboard search: ✅ Found!
   → Extracts ID: 203468
   → Auto-saves to cache
   → Returns player data

2. Request: "C.J. McCollum" (next time)
   → Tries cache: ✅ Found instantly!
   → Returns player data (no search needed)
```

## Manual Override

If smart detection fails, you can still add players manually:

1. Find player on databallr.com
2. Copy URL: `https://databallr.com/last-games/[ID]/[slug]`
3. Add to `PlayerIDs.txt`
4. Run: `python build_databallr_player_cache.py`

## Files Modified

- `scrapers/databallr_scraper.py`:
  - Added `smart_search_player_databallr()` function
  - Added `_save_player_to_cache()` function
  - Updated `search_player_databallr()` to use smart search

## Technical Details

### Name Normalization
- Lowercase conversion
- Period removal (C.J. → CJ)
- Extra space removal
- Example: "C.J. McCollum" → "cj mccollum"

### Cache Format
```json
{
  "timestamp": "2025-12-02T...",
  "cache": {
    "cj mccollum": 203468,
    "alex sarr": 1642259,
    ...
  }
}
```

### Search Patterns
- URL pattern: `/last-games/(\d+)/(.+)`
- Name matching: Word overlap algorithm
- Verification: Navigate to URL and check page content

## Future Improvements

Potential enhancements:
- Search API integration (if databallr adds one)
- Fuzzy name matching for misspellings
- Batch player discovery
- Cache refresh automation

