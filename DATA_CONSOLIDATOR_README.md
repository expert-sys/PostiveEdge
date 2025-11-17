# Sports Data Consolidator

Combines multiple scraped JSON files into one clean, analysis-ready dataset.

## What It Does

1. **Loads** all `scraped_*.json` files from a directory
2. **Removes** duplicate games/matches
3. **Cleans** invalid and empty data
4. **Normalizes** field names across different sources
5. **Exports** to JSON and CSV formats
6. **Reports** data quality metrics

## Quick Start

### Interactive Mode (Recommended)

```bash
python data_consolidator.py
# OR double-click run_consolidator.bat
```

The interactive wizard will:
- Find all scraped files
- Show you what will be processed
- Ask for confirmation
- Generate clean output files

### Programmatic Mode

```python
from data_consolidator import SportsDataConsolidator

consolidator = SportsDataConsolidator()
report = consolidator.consolidate(
    directory=".",
    export_json=True,
    export_csv=True
)

print(f"Processed {report['summary']['total_games']} games")
print(f"Data quality: {report['data_quality']['completeness']:.1f}%")
```

## Input Files

The consolidator processes all files matching:
```
scraped_*.json
```

Examples:
- `scraped_ESPN_NFL_Odds_20251117_125742.json`
- `scraped_DraftKings_NBA_20251117_130155.json`
- `scraped_SofaScore_20251117_131022.json`

## Output Files

### 1. consolidated_sports_data.json

**Format:**
```json
{
  "metadata": {
    "files_processed": 24,
    "total_games": 156,
    "duplicates_removed": 12,
    "invalid_entries": 3,
    "sources": ["scraped_ESPN_NFL_Odds_...", ...],
    "consolidation_date": "2025-11-17T13:45:22"
  },
  "games": [
    {
      "teams": ["Chiefs", "49ers"],
      "spread": ["-3.5", "+3.5"],
      "ml": ["-150", "+130"],
      "total": "47.5",
      "_source": "scraped_ESPN_NFL_Odds_20251117_125742.json",
      "_scraped_at": "2025-11-17T12:57:42"
    },
    ...
  ],
  "statistics": {
    "total_games": 156,
    "total_json_objects": 45,
    "total_tables": 8
  }
}
```

**Use case:** Full data with metadata for backup and detailed analysis

### 2. consolidated_sports_data.csv

**Format:**
```csv
_source,_scraped_at,teams,home_team,score,spread,ml,total,game_date,game_time
scraped_ESPN_NFL_Odds_...,2025-11-17T12:57:42,"Chiefs, 49ers",,,"[-3.5, +3.5]","[-150, +130]",47.5,,
```

**Use case:** Easy analysis in Excel, pandas, or database import

## Features

### Duplicate Detection

Duplicates are detected using:
- Team names (normalized)
- Game date/time
- Keeping most recent scrape

Example:
```
Game 1: Chiefs vs 49ers (scraped at 12:00)
Game 2: Chiefs vs 49ers (scraped at 13:00) ✓ Kept (newer)
```

### Data Cleaning

Removes:
- Empty fields
- Null values
- Whitespace
- Invalid entries (no team/game data)

Keeps:
- Valid game data
- Metadata (_source, _scraped_at)
- All odds/scores/stats

### Field Normalization

Standardizes field names across sources:

| Original | Normalized |
|----------|-----------|
| team1, team_name, participant | teams |
| moneyline, money_line | ml |
| pointspread, point_spread | spread |
| over_under, ou | total |
| final_score, final | score |
| start_time, time | game_time |

### Data Quality Metrics

The consolidator calculates:
- **Completeness**: Overall data quality percentage
- **Field Coverage**: % of games with each field
- **Unique Fields**: Total distinct data points

Example Report:
```
Completeness: 87.3%
Unique Fields: 15

Top Fields Coverage:
  - teams: 100.0%
  - _source: 100.0%
  - _scraped_at: 100.0%
  - spread: 89.7%
  - ml: 89.7%
  - total: 85.3%
  - score: 45.2%
```

## Usage Examples

### Consolidate All Scraped Data

```bash
python data_consolidator.py
```

Output:
```
[1/5] Loading files...
Found 24 files to process

[2/5] Removing duplicates...
Removed 12 duplicates. 156 unique games remaining.

[3/5] Cleaning data...
Cleaned 156 games. Removed 3 invalid entries.

[4/5] Normalizing fields...
Normalized 156 game entries

[5/5] Exporting data...
✓ Exported consolidated data to consolidated_sports_data.json
  - 156 unique games
  - 45 JSON objects
  - 8 tables
✓ Exported to CSV: consolidated_sports_data.csv
  - 156 rows
  - 18 columns

CONSOLIDATION COMPLETE
✓ Processed 24 files
✓ 156 unique games
✓ Removed 12 duplicates
✓ Data quality: 87.3%
```

### Consolidate Specific Directory

```python
consolidator = SportsDataConsolidator()
report = consolidator.consolidate(directory="./scraped_data")
```

### Custom File Pattern

```python
consolidator = SportsDataConsolidator(input_pattern="odds_*.json")
consolidator.consolidate()
```

### JSON Only (No CSV)

```python
consolidator = SportsDataConsolidator()
report = consolidator.consolidate(export_csv=False)
```

## Advanced Usage

### Custom Processing Pipeline

```python
from data_consolidator import SportsDataConsolidator

consolidator = SportsDataConsolidator()

# Load files
consolidator.load_all_files("./data")

# Remove duplicates
consolidator.remove_duplicates()

# Clean data
consolidator.clean_data()

# Normalize fields
consolidator.normalize_fields()

# Custom filtering
consolidator.all_games = [
    game for game in consolidator.all_games
    if 'spread' in game  # Only games with spreads
]

# Export
consolidator.export_consolidated("custom_output.json")
consolidator.export_to_csv("custom_output.csv")

# Get report
report = consolidator.generate_report()
print(report)
```

### Access Consolidated Data in Memory

```python
consolidator = SportsDataConsolidator()
consolidator.load_all_files()
consolidator.remove_duplicates()
consolidator.clean_data()

# Access games directly
for game in consolidator.all_games:
    print(f"{game['teams']} - {game.get('spread', 'N/A')}")
```

### Filter by Source

```python
consolidator = SportsDataConsolidator()
consolidator.consolidate()

# Filter ESPN data only
espn_games = [
    game for game in consolidator.all_games
    if 'ESPN' in game.get('_source', '')
]

print(f"ESPN games: {len(espn_games)}")
```

## Integration with Value Engine

Use consolidated data with your Value Engine:

```python
from data_consolidator import SportsDataConsolidator
from value_engine import analyze_simple_market

# Consolidate odds data
consolidator = SportsDataConsolidator()
consolidator.consolidate()

# Extract odds for analysis
for game in consolidator.all_games:
    if 'ml' in game and 'teams' in game:
        teams = game['teams']
        ml_odds = game['ml']

        # Convert to decimal odds and analyze
        # ... your value engine logic here
```

## Data Structure Reference

### Game Object

```python
{
    # Normalized fields
    "teams": ["Team A", "Team B"],        # List of team names
    "home_team": "Team A",                # Home team (if available)
    "score": ["120", "115"],              # Scores (if final)
    "spread": ["-5.5", "+5.5"],          # Point spreads
    "ml": ["-200", "+180"],              # Moneylines
    "total": "225.5",                     # Over/Under
    "game_date": "2025-11-17",           # Game date
    "game_time": "19:00",                # Game time

    # Metadata
    "_source": "scraped_ESPN_NBA_...",   # Source file
    "_scraped_at": "2025-11-17T12:57:42" # Scrape timestamp
}
```

### Report Object

```python
{
    "summary": {
        "files_processed": 24,
        "total_games": 156,
        "duplicates_removed": 12,
        "invalid_entries": 3,
        "consolidation_date": "2025-11-17T13:45:22"
    },
    "sources": ["file1.json", "file2.json", ...],
    "data_quality": {
        "completeness": 87.3,
        "field_coverage": {
            "teams": 100.0,
            "spread": 89.7,
            ...
        },
        "total_unique_fields": 15
    }
}
```

## Best Practices

### 1. Run After Each Scraping Session

```bash
# Scrape data
python universal_scraper.py
# Choose [4] to scrape all

# Consolidate immediately
python data_consolidator.py
```

### 2. Organize Scrapes by Date

```bash
# Create dated folders
mkdir scraped_2025_11_17
python universal_scraper.py
# Move files to folder

# Consolidate by date
python data_consolidator.py
# Enter directory: scraped_2025_11_17
```

### 3. Keep Raw Files

Always keep original `scraped_*.json` files:
- Consolidation is non-destructive
- Can re-consolidate with different settings
- Useful for debugging

### 4. Check Data Quality

Always review the quality report:
- Completeness should be >70%
- Key fields (teams, odds) should be >80%
- Low coverage might indicate scraper issues

### 5. Validate CSV Output

Open CSV in Excel/spreadsheet to verify:
- Team names are correct
- Odds are in expected format
- No obvious errors

## Troubleshooting

### No Files Found

**Issue**: "No files found matching pattern: scraped_*.json"

**Solutions**:
1. Check you're in the correct directory
2. Verify files exist: `ls scraped_*.json`
3. Check file naming pattern

### Low Data Quality

**Issue**: Completeness < 50%

**Solutions**:
1. Check scraper selectors (might be outdated)
2. Review individual scraped files
3. Some sites may have changed structure

### Duplicates Not Removed

**Issue**: Many duplicate games remaining

**Solutions**:
1. Games might be from different dates
2. Team names formatted differently
3. Check `_source` field to identify sources

### CSV Missing Columns

**Issue**: Expected fields missing in CSV

**Solutions**:
1. Check if data exists in JSON output
2. Nested objects are skipped in CSV
3. Use JSON for complex data structures

## File Size Considerations

### Large Datasets

If processing 1000+ files:
- Process in batches by date
- Use JSON for full data
- CSV might have memory limits

### Optimize for Analysis

For large CSV files:
```python
# Only export essential fields
consolidator.all_games = [
    {
        'teams': game.get('teams'),
        'spread': game.get('spread'),
        'ml': game.get('ml'),
        'total': game.get('total'),
        '_source': game.get('_source')
    }
    for game in consolidator.all_games
]
consolidator.export_to_csv()
```

## Command Line Options

For automation, use programmatically:

```python
import sys
from data_consolidator import SportsDataConsolidator

directory = sys.argv[1] if len(sys.argv) > 1 else "."

consolidator = SportsDataConsolidator()
report = consolidator.consolidate(directory)

# Exit with status code
sys.exit(0 if report.get('summary', {}).get('total_games', 0) > 0 else 1)
```

Then run:
```bash
python -c "from data_consolidator import SportsDataConsolidator; SportsDataConsolidator().consolidate()"
```

## Next Steps

After consolidation:

1. **Import to Pandas**
   ```python
   import pandas as pd
   df = pd.read_csv('consolidated_sports_data.csv')
   ```

2. **Import to Database**
   ```python
   df.to_sql('sports_games', conn, if_exists='append')
   ```

3. **Use with Value Engine**
   ```python
   from value_engine import ValueEngine
   # Analyze odds vs historical data
   ```

4. **Visualization**
   ```python
   import matplotlib.pyplot as plt
   df['spread'].hist()
   plt.show()
   ```

---

**Ready to consolidate?** Run:
```bash
python data_consolidator.py
```

All your scraped data will be cleaned, deduplicated, and ready for analysis!
