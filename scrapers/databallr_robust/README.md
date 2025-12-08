# DataballR Robust Scraper

Production-ready, robust scraper for DataballR and gameplay statistics with comprehensive error handling, retry logic, and schema adaptation.

## Features

- ✅ **Robust Request Handling**: Automatic retries with exponential backoff
- ✅ **Schema Mapping**: Handles structure changes automatically
- ✅ **Error Recovery**: Never crashes, always logs and continues
- ✅ **Data Validation**: Ensures data integrity before storage
- ✅ **Modular Architecture**: Easy to extend and maintain
- ✅ **Storage System**: Raw JSON + processed Parquet/CSV
- ✅ **CLI Interface**: Easy to run from command line
- ✅ **Comprehensive Logging**: Detailed logs for debugging

## Architecture

```
scrapers/databallr_robust/
├── core/
│   ├── requester.py      # Robust HTTP request handler
│   ├── headers.py        # Rotating user agents & headers
│   ├── backoff.py        # Exponential backoff logic
│   ├── schema_map.py     # Schema mapping & adaptation
│   └── logs.py           # Logging configuration
├── databallr/
│   ├── players.py        # Player stats scraper
│   ├── props.py          # Player props scraper
│   ├── matchups.py       # Matchup stats scraper
│   └── pace.py           # Pace statistics scraper
├── gameplay/
│   ├── recent_form.py    # Recent form scraper
│   ├── advanced_metrics.py  # Advanced metrics
│   └── trends.py         # Trend analysis
├── storage/
│   ├── save_raw.py       # Raw JSON storage
│   └── save_processed.py # Processed data storage
└── main.py               # Main orchestrator
```

## Usage

### CLI

```bash
# Scrape all players for today
python scrape.py

# Scrape for specific date
python scrape.py --date 2025-01-05

# Scrape specific player
python scrape.py --player "LeBron James"

# Scrape multiple players
python scrape.py --players "LeBron James" "Stephen Curry"

# Custom directories
python scrape.py --raw-dir data/raw --processed-dir data/processed
```

### Python API

```python
from scrapers.databallr_robust.main import DataballrRobustScraper

scraper = DataballrRobustScraper()

# Scrape single player
data = scraper.scrape_player_stats("LeBron James", last_n_games=20)

# Scrape all
results = scraper.scrape_all(date="2025-01-05")

scraper.close()
```

## Configuration

### Retry Settings

Default retry configuration:
- Max attempts: 5
- Base delay: 1.0 seconds
- Max delay: 60.0 seconds
- Exponential base: 2.0
- Jitter: Enabled

### Storage

- **Raw Data**: `./data/raw/{date}/` (JSON files)
- **Processed Data**: `./data/processed/{date}/` (Parquet/CSV)
- **Logs**: `./logs/scraper.log`

## Error Handling

The scraper handles:
- 403 Forbidden (retries with backoff)
- 429 Too Many Requests (retries with backoff)
- 500/502/503/504 Server Errors (retries)
- Timeout errors (retries)
- Connection errors (retries)
- Schema changes (auto-maps fields)
- Missing fields (uses defaults)

## Schema Mapping

The schema mapper automatically handles:
- Renamed fields (e.g., `pts` → `points`)
- Missing fields (uses safe defaults)
- Type conversions
- Nested data access

## Testing

Run validation tests:

```bash
python -m pytest tests/test_databallr_robust.py -v
```

Tests verify:
- Response validation
- Schema mapping
- Data storage
- Error handling

## Requirements

- Python 3.10+
- playwright
- beautifulsoup4
- pandas
- pyarrow (for Parquet)
- httpx or requests

Install dependencies:
```bash
pip install playwright beautifulsoup4 pandas pyarrow httpx
playwright install chromium
```

## Performance

- Full scrape: < 30 seconds (with caching)
- Single player: < 5 seconds
- Handles throttling automatically
- Caches player IDs to avoid lookups

## Logging

All operations are logged to:
- Console (INFO level)
- `logs/scraper.log` (all levels)

Logs include:
- Success/failure for each scrape
- Schema mismatch warnings
- Retry attempts
- Error details

