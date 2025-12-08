# StatMuse V2 Integration - Complete Update

## Summary of Changes

### ✅ Completed:

1. **Team ID Mapping** (`scrapers/statmuse_team_ids.py`)
   - All 30 NBA teams mapped with correct StatMuse IDs
   - Eastern Conference: 14 teams
   - Western Conference: 16 teams
   - URL generation functions for stats/splits endpoints

2. **V2 Scraper with Robust Loading** (`scrapers/statmuse_scraper.py`)
   - 3 retry attempts with exponential backoff
   - Multiple load strategies (load → domcontentloaded → commit)
   - 60-second timeout (vs old 30s)
   - Anti-detection browser flags
   - **Now uses correct team IDs from mapping**

3. **Correct URL Format**
   - Old (WRONG): `https://www.statmuse.com/nba/team/2025-26-{slug}-13/stats/2026`
   - New (CORRECT): `https://www.statmuse.com/nba/team/2025-26-{slug}-{id}/stats/2026`
   - Example: Lakers = ID 15, Celtics = ID 1, Thunder = ID 38

### 🔄 In Progress:

4. **Update remaining scraper functions**
   - `scrape_player_stats()` - needs URL update
   - `scrape_team_splits()` - needs URL update
   - Extract team name properly from team_name parameter

5. **Adapter Integration**
   - Update `statmuse_adapter.py` to use new scraper
   - Remove old team slug logic
   - Use full team names instead of slugs

### 📝 Next Steps:

1. **Complete scraper function updates** (player_stats, team_splits)
2. **Update adapter** to pass full team names
3. **Test complete flow**: Lakers @ Celtics with correct URLs
4. **Verify DataballR cache** is being used for player props
5. **Run full pipeline** with StatMuse V2

## Key URLs Verified:

| Team | URL | Status |
|------|-----|--------|
| Lakers | https://www.statmuse.com/nba/team/2025-26-los-angeles-lakers-15/2026 | ✅ |
| Celtics | https://www.statmuse.com/nba/team/2025-26-boston-celtics-1/2026 | ✅ |
| Thunder | https://www.statmuse.com/nba/team/2025-26-oklahoma-city-thunder-38/2026 | ✅ |
| Warriors | https://www.statmuse.com/nba/team/2025-26-golden-state-warriors-6/2026 | ✅ |

## DataballR Cache Integration

**Current Status**: DataballR cache is already integrated in pipeline (`scrapers/unified_analysis_pipeline.py`)

**For Player Props**:
- DataballR scraper fetches player game logs
- Cache is stored at `data/cache/databallr_player_cache.json`
- Used by projection model for player prop calculations
- Reduces API calls and improves performance

**Verification Needed**:
- Confirm cache is being populated correctly
- Verify projection model uses cached data for player props
- Check cache expiry logic (daily refresh)

## Files Modified:

1. `scrapers/statmuse_team_ids.py` - NEW (Complete team ID mapping)
2. `scrapers/statmuse_scraper.py` - UPDATED (V2 with correct URLs)
3. `scrapers/statmuse_scraper_v2.py` - NEW (Robust scraper prototype)
4. `scrapers/statmuse_scraper_old.py` - BACKUP (Original version)
5. `scrapers/statmuse_adapter.py` - NEEDS UPDATE (Pass team names)
6. `scrapers/statmuse_adapter_old.py` - BACKUP (Original adapter)

## Test Results:

### V2 Scraper (Before URL Fix):
```
[1/3] Team Stats: OK 22 GP, 118.3 PPG, 46.9 RPG
[2/3] Player Stats: OK 18 players found
[3/3] Team Splits: OK 52 splits found
```

### After URL Fix:
- Pending full test with Lakers/Celtics
- Expected: Correct data with proper team IDs
- Should eliminate all timeout errors

## Performance Improvements:

| Metric | Old Scraper | V2 Scraper |
|--------|------------|------------|
| Timeout | 30s | 60s |
| Retries | 0 | 3 |
| Load Strategies | 1 (networkidle) | 3 (load/dom/commit) |
| Success Rate | ~40% (timeouts) | ~95% (estimated) |
| Anti-Detection | Basic | Enhanced |

## Integration Checklist:

- [x] Create team ID mapping
- [x] Build V2 scraper with robust loading
- [x] Test V2 scraper (successful with 18 players, 52 splits)
- [x] Update scrape_team_stats() to use correct URLs
- [ ] Update scrape_player_stats() to use correct URLs
- [ ] Update scrape_team_splits() to use correct URLs
- [ ] Update adapter to pass team names (not slugs)
- [ ] Test with Lakers @ Celtics
- [ ] Run full pipeline
- [ ] Verify StatMuse data in betting recommendations
- [ ] Confirm DataballR cache for player props

## Priority: HIGH

StatMuse data with 52 splits per team is **critical** for accurate projections. Sportsbet trends alone are insufficient for reliable predictions.
