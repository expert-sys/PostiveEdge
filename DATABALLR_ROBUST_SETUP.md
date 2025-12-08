# DataballR Robust Scraper - Setup Guide

## Quick Start

1. **Install Dependencies**
```bash
pip install playwright beautifulsoup4 pandas pyarrow httpx
playwright install chromium
```

2. **Run Scraper**
```bash
# Scrape all players for today
python scrape.py

# Scrape for specific date
python scrape.py --date 2025-01-05

# Scrape specific player
python scrape.py --player "LeBron James"
```

## Architecture Overview

The robust scraper is organized into modular components:

### Core Modules (`core/`)
- **requester.py**: Handles all HTTP requests with retries and backoff
- **headers.py**: Rotating user agents and browser headers
- **backoff.py**: Exponential backoff with jitter
- **schema_map.py**: Automatic schema adaptation for structure changes
- **logs.py**: Centralized logging
- **cookies.py**: Cookie management for sessions

### DataballR Modules (`databallr/`)
- **players.py**: Player game log scraper (Playwright-based)
- **props.py**: Player prop statistics
- **matchups.py**: Matchup-specific stats
- **pace.py**: Pace and tempo statistics

### Gameplay Modules (`gameplay/`)
- **recent_form.py**: Recent performance trends
- **advanced_metrics.py**: Advanced efficiency metrics
- **trends.py**: Historical trend analysis

### Storage (`storage/`)
- **save_raw.py**: Raw JSON storage with metadata
- **save_processed.py**: Cleaned Parquet/CSV storage

## Key Features

### 1. Robust Request Handling
- Automatic retries (3-6 attempts)
- Exponential backoff with jitter
- Handles 403, 429, 500, 502, 503, 504 errors
- Timeout protection
- Session reuse for efficiency

### 2. Schema Adaptation
- Automatically maps renamed fields
- Handles missing keys gracefully
- Type conversion with validation
- Safe defaults for all fields

### 3. Error Recovery
- Never crashes - always logs and continues
- Graceful degradation
- Detailed error logging
- Retry with different strategies

### 4. Data Validation
- Non-empty response checks
- Schema field validation
- Type checking
- Duplicate removal

## Integration with Existing System

The robust scraper can be used alongside or as a replacement for `databallr_scraper.py`:

```python
# Option 1: Use integration wrapper (drop-in replacement)
from scrapers.databallr_robust.integration import get_player_game_log

games = get_player_game_log("LeBron James", last_n_games=20)

# Option 2: Use new robust scraper directly
from scrapers.databallr_robust.main import DataballrRobustScraper

scraper = DataballrRobustScraper()
data = scraper.scrape_player_stats("LeBron James")
```

## Configuration

### Retry Settings
Modify in `core/backoff.py` or pass `RetryConfig`:
- `max_attempts`: Number of retries (default: 5)
- `base_delay`: Initial delay in seconds (default: 1.0)
- `max_delay`: Maximum delay (default: 60.0)
- `exponential_base`: Backoff multiplier (default: 2.0)

### Storage Paths
Default paths:
- Raw data: `./data/raw/{date}/`
- Processed: `./data/processed/{date}/`
- Logs: `./logs/scraper.log`
- Cache: `./data/cache/`

## Performance

- **Single player**: < 5 seconds (with cache)
- **Full scrape**: < 30 seconds (with caching)
- **Handles throttling**: Automatic backoff
- **Session reuse**: Reduces overhead

## Troubleshooting

### Common Issues

1. **403 Forbidden**
   - Scraper automatically retries with backoff
   - Rotates user agents
   - Check logs for details

2. **429 Too Many Requests**
   - Automatic exponential backoff
   - Increases delays between requests
   - Logs retry attempts

3. **Schema Changes**
   - Schema mapper logs warnings
   - Auto-maps known alternatives
   - Uses safe defaults

4. **Missing Players**
   - Check player cache: `data/cache/databallr_player_cache.json`
   - Add players using existing cache builder
   - Scraper skips gracefully if not in cache

## Testing

Run validation tests:
```bash
python -m pytest tests/test_databallr_robust.py -v
```

Tests verify:
- Request handling
- Schema mapping
- Data storage
- Error recovery

## Logging

All operations logged to:
- Console (INFO+)
- `logs/scraper.log` (all levels)

Log format:
```
2025-01-05 12:34:56 [INFO] databallr_robust: Scraping player stats for LeBron James
2025-01-05 12:34:58 [WARNING] databallr_robust: Schema change detected: 'pts' mapped to 'points'
2025-01-05 12:35:00 [INFO] databallr_robust: ✓ Successfully scraped 20 games
```

## Next Steps

1. **Extend Scrapers**: Add more DataballR endpoints in `databallr/`
2. **Add Gameplay Sources**: Implement in `gameplay/`
3. **Customize Schema**: Update `core/schema_map.py` for new fields
4. **Schedule Scrapes**: Use cron/task scheduler for daily runs

