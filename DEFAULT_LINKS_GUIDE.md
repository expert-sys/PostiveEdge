# Default Sports Scraping Links Guide

This document describes the 24 pre-configured scraping targets available in the Universal Sports Scraper.

## Quick Start

To load all default links:
1. Run `python universal_scraper.py`
2. Choose option `[8] Load Default Sports Links`
3. All 24 links will be added to your scraper

## Default Links Overview

### FlashScore (Global Live Scores)
**Difficulty**: ★★☆☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| FlashScore - Soccer/Football | https://www.flashscore.com/football/ | Live soccer scores worldwide |
| FlashScore - Basketball | https://www.flashscore.com/basketball/ | NBA, EuroLeague, international basketball |

**Notes**: JS-heavy, may need to wait for content. Extremely fast and reliable.

---

### SofaScore (Global Live Scores & Stats)
**Difficulty**: ★★☆☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| SofaScore - Live Scores All Sports | https://www.sofascore.com/ | Comprehensive live scores, all major sports |

**Notes**: Excellent stats coverage. Dynamic content.

---

### ESPN NFL
**Difficulty**: ★★★☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| ESPN NFL Scores | https://www.espn.com/nfl/scoreboard | Live NFL scores and game summaries |
| ESPN NFL Odds | https://www.espn.com/nfl/odds | NFL betting lines from multiple sportsbooks |
| ESPN NFL Injuries | https://www.espn.com/nfl/injuries | Current injury reports for all teams |
| ESPN NFL Standings | https://www.espn.com/nfl/standings | NFL division and conference standings |

**Notes**: Very stable HTML structure. Zero aggressive blocking. Highly recommended.

---

### ESPN NBA
**Difficulty**: ★★★☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| ESPN NBA Scores | https://www.espn.com/nba/scoreboard | NBA live scores and box scores |
| ESPN NBA Odds | https://www.espn.com/nba/odds | NBA betting lines from multiple books |
| ESPN NBA Player Stats | https://www.espn.com/nba/stats | NBA player statistics and leaders |

**Notes**: Consistent structure. Great for daily scraping.

---

### ESPN MLB
**Difficulty**: ★★★☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| ESPN MLB Scores | https://www.espn.com/mlb/scoreboard | MLB live scores and game summaries |
| ESPN MLB Odds | https://www.espn.com/mlb/odds | MLB betting lines (moneylines, totals) |

---

### ESPN NHL
**Difficulty**: ★★★☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| ESPN NHL Scores | https://www.espn.com/nhl/scoreboard | NHL live scores and summaries |
| ESPN NHL Odds | https://www.espn.com/nhl/odds | NHL betting lines from various sportsbooks |

---

### DraftKings (Odds & Props)
**Difficulty**: ★★☆☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| DraftKings NFL | https://sportsbook.draftkings.com/leagues/football/nfl | NFL odds and props |
| DraftKings NBA | https://sportsbook.draftkings.com/leagues/basketball/nba | NBA odds and player props |

**Notes**: JSON-driven. Check network tab for JSON endpoints. May require geo-location.

---

### FanDuel (Odds & Props)
**Difficulty**: ★★☆☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| FanDuel NFL | https://sportsbook.fanduel.com/navigation/nfl | NFL betting markets |
| FanDuel NBA | https://sportsbook.fanduel.com/navigation/nba | NBA betting markets and props |

**Notes**: Structured and predictable. Great for props.

---

### Pinnacle (Sharp Odds)
**Difficulty**: ★★☆☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| Pinnacle NFL | https://www.pinnacle.com/en/football/nfl/matchups/ | Pinnacle sharp lines for NFL |
| Pinnacle NBA | https://www.pinnacle.com/en/basketball/nba/matchups/ | Pinnacle sharp lines for NBA |

**Notes**: Known for accurate, sharp lines. Industry standard for line comparison.

---

### BetFair Exchange (Market Odds)
**Difficulty**: ★☆☆☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| BetFair Exchange - NFL | https://www.betfair.com/exchange/plus/american-football | NFL exchange odds with liquidity |
| BetFair Exchange - NBA | https://www.betfair.com/exchange/plus/basketball | NBA exchange with back/lay odds |

**Notes**: True market prices. Includes liquidity data. Best for implied probability.

---

### PointsBet (Odds & Markets)
**Difficulty**: ★★☆☆☆ | **Reliability**: ★★★★★

| Name | URL | What It Scrapes |
|------|-----|-----------------|
| PointsBet NFL | https://pointsbet.com/sports/american-football/NFL | PointsBet NFL markets and spreads |
| PointsBet NBA | https://pointsbet.com/sports/basketball/NBA | PointsBet NBA markets |

**Notes**: May block datacenter proxies. Residential proxies recommended.

---

## Export Format

All scraped data is exported as **JSON** by default with timestamped filenames:

```
scraped_[link_name]_YYYYMMDD_HHMMSS.json
```

Example:
```
scraped_ESPN_NFL_Odds_20250117_143022.json
```

## Data Structure

Each exported JSON file contains:

```json
{
  "games": [
    {
      "team_name": ["Chiefs", "49ers"],
      "spread": ["-3.5", "+3.5"],
      "moneyline": ["-150", "+130"],
      "total": "47.5"
    }
  ],
  "json": [...],
  "tables": [...],
  "text": "..."
}
```

## Usage Tips

### For Live Scores
- **Best**: FlashScore, SofaScore
- **Update Frequency**: Every 30-60 seconds
- **Scrape**: Individual sport pages

### For Odds Comparison
- **Best**: Pinnacle (sharp), BetFair (market), DraftKings/FanDuel (mainstream)
- **Update Frequency**: Every 5-15 minutes
- **Scrape**: Sport-specific odds pages

### For Stats & Analysis
- **Best**: ESPN (all stats)
- **Update Frequency**: Daily or post-game
- **Scrape**: Stats and standings pages

### For Props
- **Best**: DraftKings, FanDuel
- **Update Frequency**: Multiple times daily
- **Scrape**: Sport-specific sportsbook pages

## Rate Limiting Recommendations

| Site | Recommended Delay | Max Requests/Hour |
|------|------------------|-------------------|
| FlashScore | 30-60s | 60-120 |
| SofaScore | 30-60s | 60-120 |
| ESPN | 10-30s | 120-360 |
| DraftKings | 30-60s | 60-120 |
| FanDuel | 30-60s | 60-120 |
| Pinnacle | 60s | 60 |
| BetFair | 60s | 60 |
| PointsBet | 60s | 60 |

## Troubleshooting

### No Data Extracted
1. Try a different template
2. Run option `[6]` to test the URL manually
3. Check if the site structure has changed
4. Use browser DevTools to find new selectors

### Blocked/Rate Limited
1. Increase delays between requests
2. Use residential proxies (not datacenter)
3. Rotate user agents
4. Respect robots.txt

### Geo-Restrictions
- DraftKings, FanDuel, PointsBet may require US IP
- Use VPN or proxies in allowed regions
- Some betting sites require login

## Adding Custom Sites

If you want to scrape additional sites:

1. Use option `[7]` to view templates
2. Choose closest matching template
3. Use option `[1]` to add the link
4. Test with option `[3]`
5. Adjust selectors if needed

## Best Practices

1. **Respect robots.txt**: Always check site policies
2. **Add delays**: Don't hammer servers
3. **Monitor changes**: Sites update HTML regularly
4. **Verify data**: Always check exported files
5. **Use JSON**: Easier to process programmatically
6. **Batch wisely**: Option `[4]` for all links takes time

## Integration with Value Engine

To use scraped odds with the Value Engine:

1. Scrape odds pages (ESPN, DraftKings, etc.)
2. Extract odds from JSON files
3. Convert to implied probability
4. Compare with historical data in Value Engine
5. Identify +EV opportunities

## Legal & Ethical Considerations

- **Personal Use Only**: These links are for personal data collection
- **Terms of Service**: Always respect site ToS
- **No Redistribution**: Don't sell or share scraped data
- **Rate Limits**: Follow recommended delays
- **Geo-Restrictions**: Respect regional blocking

---

**Total Default Links**: 24
**Total Sites Covered**: 8
**Sports Covered**: NFL, NBA, MLB, NHL, Soccer, Global Sports
**Export Format**: JSON (timestamped)
