# Universal Sports Data Scraper

A powerful, interactive web scraper designed for sports data with link management, site templates, and flexible extraction.

## Features

- **Link Management**: Save and organize scraping targets
- **Interactive CLI**: User-friendly menu system
- **Site Templates**: Pre-configured selectors for popular sports sites
- **Dynamic Rendering**: Handles JavaScript-heavy sites with Playwright
- **Multiple Export Formats**: CSV and JSON
- **Batch Scraping**: Scrape all saved links at once
- **Error Handling**: Automatic retries and resilient parsing
- **Flexible Extraction**: Games, tables, JSON, or custom data

## Installation

1. Install dependencies:
```bash
pip install -r scraper_requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

## Quick Start

Run the interactive scraper:
```bash
python universal_scraper.py
```

## Menu Options

```
[1] Add New Link          - Save a URL with custom name and template
[2] List Saved Links      - View all saved scraping targets
[3] Scrape a Saved Link   - Scrape one link by ID
[4] Scrape All Links      - Batch scrape all saved links
[5] Remove a Link         - Delete a saved link
[6] Scrape Custom URL     - One-time scrape without saving
[7] View Site Templates   - See available pre-configured templates
[0] Exit
```

## Site Templates

The scraper includes pre-configured templates for:

- **espn_odds**: ESPN odds pages (spreads, moneylines, totals)
- **espn_scores**: ESPN scores and results
- **generic_table**: Extract HTML tables from any site
- **generic_json**: Extract embedded JSON data
- **custom**: Define your own selectors

## Usage Examples

### Add a New Link

1. Select option `[1]`
2. Enter URL: `https://www.espn.com/nfl/odds`
3. Enter name: `NFL Odds`
4. Choose template: `espn_odds` or `1`
5. Add notes (optional)

### Scrape a Saved Link

1. Select option `[3]`
2. Enter link ID from your saved links
3. Choose whether to export (default: yes)
4. Results saved to `scraped_[name]_[timestamp].json`

### Batch Scraping

1. Select option `[4]`
2. Confirm batch scraping
3. Choose export option
4. All links scraped sequentially

### One-Time Scraping

1. Select option `[6]`
2. Enter any URL
3. Choose export option
4. Results extracted automatically

## Programmatic Usage

You can also use the scraper in your Python scripts:

```python
import asyncio
from universal_scraper import UniversalSportsScraper

async def scrape_example():
    scraper = UniversalSportsScraper(headless=True)

    # Scrape with auto-detection
    data = await scraper.scrape(
        url="https://www.espn.com/nfl/odds",
        export_path="nfl_odds.json"
    )

    print(f"Found {len(data.get('games', []))} games")
    print(f"Found {len(data.get('tables', []))} tables")
    print(f"Found {len(data.get('json', []))} JSON objects")

asyncio.run(scrape_example())
```

### Using Link Manager

```python
from universal_scraper import LinkManager

manager = LinkManager()

# Add a link
manager.add_link(
    url="https://www.espn.com/nba/scores",
    name="NBA Scores",
    template="espn_scores",
    notes="Daily scores"
)

# List all links
for link in manager.list_links():
    print(f"{link['id']}: {link['name']} - {link['url']}")

# Remove a link
manager.remove_link(link_id=1)
```

### Custom Selectors

```python
async def scrape_custom():
    scraper = UniversalSportsScraper()

    custom_selectors = {
        "game_container": ".matchup-row",
        "team_name": ".team-name",
        "score": ".final-score",
        "spread": ".point-spread"
    }

    data = await scraper.scrape(
        url="https://example.com/games",
        selectors=custom_selectors,
        extraction_type="games",
        export_path="custom_games.csv"
    )

asyncio.run(scrape_custom())
```

## Data Storage

Saved links are stored in `scraper_links.json`:

```json
[
  {
    "id": 1,
    "name": "NFL Odds",
    "url": "https://www.espn.com/nfl/odds",
    "template": "espn_odds",
    "selectors": {...},
    "extraction_type": "games",
    "notes": "Updated daily",
    "created_at": "2025-01-17T10:30:00",
    "last_scraped": "2025-01-17T15:45:00",
    "scrape_count": 5
  }
]
```

## Export Formats

### JSON Export
All data types (games, tables, JSON objects, text) in structured format:
```json
{
  "games": [...],
  "json": [...],
  "tables": [...]
}
```

### CSV Export
Tabular data (games or first table found):
```csv
team_name,spread,moneyline,total
Chiefs,+3.5,-110,47.5
49ers,-3.5,-110,47.5
```

## Extraction Types

- **games**: Extract game/matchup data using selectors
- **json**: Extract embedded JSON from `<script>` tags
- **tables**: Extract HTML tables (all tables on page)
- **auto**: Try all extraction methods

## Advanced Features

### Recency Weighting
The scraper timestamps all scraped data and tracks scrape frequency.

### Error Handling
- Automatic retries (up to 3 attempts)
- Random delays between retries
- Graceful failure with detailed logging

### Headless Mode
Default: Headless (no browser window)
```python
scraper = UniversalSportsScraper(headless=False)  # Show browser
```

### Custom Timeout
Default: 15 seconds
```python
scraper = UniversalSportsScraper(timeout=30000)  # 30 seconds
```

## Troubleshooting

### Issue: Playwright not found
**Solution**: Run `playwright install chromium`

### Issue: No data extracted
**Solutions**:
1. Try different template
2. Inspect page and update selectors
3. Check if site requires login/cookies
4. Increase timeout for slow sites

### Issue: Selectors not working
**Solution**: Use browser DevTools to find correct CSS selectors:
1. Right-click element → Inspect
2. Right-click in Elements panel → Copy → Copy selector
3. Use that selector in custom configuration

## Best Practices

1. **Start with Templates**: Use pre-configured templates when possible
2. **Test First**: Use option `[6]` to test URLs before saving
3. **Respect Robots.txt**: Check site's robots.txt before scraping
4. **Add Delays**: Don't hammer servers - use batch scraping carefully
5. **Verify Data**: Always check exported files for accuracy
6. **Update Selectors**: Sites change - update selectors when extraction fails

## API Reference

### UniversalSportsScraper

**Methods**:
- `scrape(url, selectors, extraction_type, export_path)` - Main scraping method
- `scrape_saved_link(link_id, export)` - Scrape by link ID
- `scrape_all_saved_links(export)` - Batch scrape all links
- `extract_games(soup, selectors)` - Extract game data
- `extract_json(soup)` - Extract JSON objects
- `extract_tables(html)` - Extract HTML tables

### LinkManager

**Methods**:
- `add_link(url, name, template, selectors, notes)` - Add new link
- `remove_link(link_id)` - Remove link
- `get_link(link_id)` - Get link by ID
- `list_links()` - Get all links
- `update_scrape_stats(link_id)` - Update scrape statistics

## Examples for Popular Sites

### ESPN NFL Odds
```python
manager.add_link(
    url="https://www.espn.com/nfl/odds",
    name="NFL Odds",
    template="espn_odds"
)
```

### Generic Sports Table
```python
manager.add_link(
    url="https://example.com/stats",
    name="Stats Table",
    template="generic_table"
)
```

### Custom Site
```python
custom_selectors = {
    "game_container": ".game-card",
    "team_name": ".team h3",
    "score": ".score-value"
}

manager.add_link(
    url="https://custom-site.com/games",
    name="Custom Games",
    template="custom",
    selectors=custom_selectors
)
```

## License

This scraper is for educational and personal use. Always respect website Terms of Service and rate limits.

## Support

For issues or questions:
1. Check this README
2. Review the code comments
3. Test with option `[6]` first
4. Check browser DevTools for selector issues
