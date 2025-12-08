# Pipeline Integration - DataballR Robust Scraper

## Pipeline Flow

The unified analysis pipeline now uses the robust DataballR scraper with the following flow:

```
┌─────────────────────┐
│ 1. SPORTSBET SCRAPER│
│    - Scrapes games   │
│    - Markets         │
│    - Insights        │
│    - Player props    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. DATABALLR SCRAPER│ ← NEW: Robust scraper with retries
│    - Player stats    │
│    - Game logs       │
│    - Retry logic     │
│    - Schema mapping  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. INSIGHT ANALYZER │
│    - Context-aware   │
│    - Value engine    │
│    - Team bets       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 4. MODEL PROJECTIONS│
│    - Player props    │
│    - Matchup adj.    │
│    - Probabilities   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 5. DISPLAY           │
│    - Filter & rank   │
│    - Top 5 bets      │
│    - Save results    │
└─────────────────────┘
```

## Integration Details

### Automatic Fallback

The pipeline automatically uses the robust DataballR scraper if available, with fallback to the original:

```python
# In unified_analysis_pipeline.py
try:
    from scrapers.databallr_robust.integration import get_player_game_log
    DATABALLR_ROBUST_AVAILABLE = True
    logger.info("[PIPELINE] Using robust DataballR scraper")
except ImportError:
    from scrapers.databallr_scraper import get_player_game_log
    DATABALLR_ROBUST_AVAILABLE = False
    logger.warning("Robust scraper not available, using original")
```

### Benefits

1. **Reliability**: Automatic retries with exponential backoff
2. **Schema Adaptation**: Handles field name changes automatically
3. **Error Recovery**: Never crashes, always logs and continues
4. **Performance**: Session reuse and optimized requests

### Usage

Run from launcher:
```bash
python launcher.py
# Select option 1: Run Unified Analysis
```

Or directly:
```bash
python scrapers/unified_analysis_pipeline.py
```

### Verification

The pipeline will show which scraper is being used:
- ✓ ROBUST scraper: If robust version is available
- ⚠ Original scraper: If robust version is not available

Check logs for:
```
[PIPELINE] Using robust DataballR scraper with retry logic and schema mapping
```

## Troubleshooting

### Robust Scraper Not Available

If you see "⚠ Original scraper", check:
1. `scrapers/databallr_robust/` directory exists
2. All dependencies installed: `pip install playwright beautifulsoup4`
3. No import errors in logs

### Integration Issues

The robust scraper uses the same interface as the original:
- Same function signature: `get_player_game_log(player_name, ...)`
- Same return type: `List[GameLogEntry]`
- Drop-in replacement - no code changes needed

