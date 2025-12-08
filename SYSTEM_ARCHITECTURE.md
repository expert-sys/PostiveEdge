# NBA Betting System - Architecture Documentation

## Overview

The NBA Betting System is a complete pipeline that automates the process of finding high-value NBA bets by combining web scraping, statistical analysis, and machine learning projections.

## System Components

### 1. Sportsbet Collector (`SportsbetCollector`)

**Purpose**: Scrape NBA betting markets from Sportsbet.com.au

**Technology**: 
- Playwright (browser automation)
- BeautifulSoup4 (HTML parsing)
- Anti-detection measures (realistic headers, throttling)

**Outputs**:
- Game information (teams, time, URL)
- Team markets (spreads, totals, moneylines)
- Player props (points, rebounds, assists, etc.)
- Sportsbet insights and trends
- Match statistics

**Key Features**:
- Headless browser operation
- Request throttling (1 req/sec)
- Session persistence
- Automatic retry logic

### 2. DataBallr Validator (`DataBallrValidator`)

**Purpose**: Validate betting insights with actual player performance data

**Technology**:
- Playwright (browser automation)
- Player ID caching system
- Game log extraction

**Outputs**:
- Player game logs (last 20 games)
- Historical hit rates
- Average stat values
- Performance trends (improving/declining/stable)
- Sample size validation

**Key Features**:
- Smart caching (reduces scraping time)
- Minimum 5 games required
- Minutes-played filtering (10+ min)
- Trend detection (recent vs previous performance)

### 3. Value Projector (`ValueProjector`)

**Purpose**: Project betting value using statistical models

**Technology**:
- PlayerProjectionModel (statistical projections)
- Bayesian probability combination
- Multi-factor confidence scoring

**Outputs**:
- Projected probability
- Expected value (EV)
- Edge percentage
- Confidence score
- Recommendation strength

**Projection Formula**:
```
Final Probability = (0.7 × Model Projection) + (0.3 × Historical Hit Rate)
```

**Confidence Calculation**:
```
Confidence = Base Model Confidence
           + Sample Size Boost (0-5 points)
           + Edge Boost (0-5 points)
           (capped at 95%)
```

**Recommendation Strength**:
- **VERY_HIGH**: Confidence ≥80% AND EV ≥5%
- **HIGH**: Confidence ≥70% AND EV ≥3%
- **MEDIUM**: Confidence ≥60% AND EV ≥1%
- **LOW**: Below thresholds (filtered out)

### 4. NBA Betting Pipeline (`NBAbettingPipeline`)

**Purpose**: Orchestrate the complete analysis workflow

**Process**:
1. Scrape all NBA games from Sportsbet
2. For each player prop:
   - Fetch player stats from DataBallr
   - Validate minimum sample size (5 games)
   - Calculate historical hit rate
   - Run projection model
   - Combine model + historical data
   - Calculate value metrics
3. Filter recommendations:
   - Minimum confidence threshold (default 70%)
   - Positive EV only
   - Correlation control (max 2 bets per game)
4. Rank by confidence score
5. Output top recommendations

## Data Structures

### BettingRecommendation

Complete betting recommendation with all analysis:

```python
@dataclass
class BettingRecommendation:
    # Game context
    game: str                    # "Lakers @ Warriors"
    match_time: str              # "7:30 PM ET"
    
    # Bet details
    bet_type: str                # "player_prop"
    market: str                  # "Points"
    selection: str               # "Over 25.5"
    odds: float                  # 1.90
    
    # Player-specific
    player_name: str             # "LeBron James"
    stat_type: str               # "points"
    line: float                  # 25.5
    
    # Analysis
    historical_hit_rate: float   # 0.65 (65%)
    sample_size: int             # 20 games
    
    # Projections
    projected_probability: float # 0.703 (70.3%)
    model_confidence: float      # 75.0
    
    # Value metrics
    implied_probability: float   # 0.526 (52.6%)
    edge_percentage: float       # 5.2%
    expected_value: float        # 8.4%
    
    # Final score
    confidence_score: float      # 78.0
    recommendation_strength: str # "HIGH"
```

## File Structure

```
nba_betting_system/
├── nba_betting_system.py          # Main pipeline
├── run_betting_system.bat         # Windows launcher
├── run_betting_system.sh          # Linux/Mac launcher
├── scrapers/
│   ├── sportsbet_final_enhanced.py    # Sportsbet scraper
│   ├── databallr_scraper.py           # DataBallr scraper
│   ├── player_projection_model.py     # Statistical models
│   └── nba_player_cache.py            # Player ID cache
├── data/
│   └── cache/
│       ├── databallr_player_cache.json  # Player ID mappings
│       └── player_stats_cache.json      # Cached game logs
├── betting_recommendations.json   # Output file
└── nba_betting_system.log        # Execution log
```

## Configuration

### Minimum Requirements

- **Sample Size**: 5 games minimum per player
- **Minutes Played**: 10+ minutes per game
- **Confidence Threshold**: 70% (configurable via `--min-confidence`)
- **Expected Value**: Positive EV only

### Correlation Control

To avoid over-exposure to correlated outcomes:
- Maximum 2 bets per game
- Recommendations ranked by confidence
- Higher confidence bets selected first

### Caching Strategy

**Player ID Cache** (`databallr_player_cache.json`):
- Maps player names to DataBallr IDs
- Reduces scraping time significantly
- Updated via `build_databallr_player_cache.py`

**Stats Cache** (`player_stats_cache.json`):
- Stores recent game logs (24-hour TTL)
- Reduces API calls
- Auto-refreshes when stale

## Performance Optimization

### Speed Improvements

1. **Parallel Processing**: Could be added for multiple games
2. **Smart Caching**: Reuses player stats within 24 hours
3. **Headless Mode**: Faster browser automation
4. **Request Throttling**: Avoids rate limiting

### Typical Execution Times

- **1 game**: ~30-60 seconds
- **3 games**: ~2-3 minutes
- **All games (5-10)**: ~5-10 minutes

*Times vary based on number of player props and cache hits*

## Error Handling

### Common Issues

1. **Player Not in Cache**
   - **Solution**: Add to `PLAYERS_TO_ADD.txt`, run `build_databallr_player_cache.py`

2. **Insufficient Game Data**
   - **Cause**: Player hasn't played 5+ games
   - **Solution**: System automatically skips

3. **Scraping Failures**
   - **Cause**: Website changes, network issues
   - **Solution**: Automatic retry logic (3 attempts)

4. **Browser Issues**
   - **Cause**: Playwright not installed
   - **Solution**: Run `playwright install chromium`

## Future Enhancements

### Planned Features

1. **Team Market Analysis**: Spreads, totals, moneylines
2. **Live Betting**: Real-time odds monitoring
3. **Bankroll Management**: Kelly Criterion sizing
4. **Performance Tracking**: Track actual vs projected results
5. **Machine Learning**: Neural network projections
6. **Multi-Sport Support**: NFL, MLB, NHL

### Scalability

- **Database Integration**: PostgreSQL for historical data
- **API Development**: REST API for external access
- **Cloud Deployment**: AWS Lambda for scheduled runs
- **Notification System**: Email/SMS alerts for high-value bets

## Security & Ethics

### Responsible Use

- **For Educational Purposes**: Learn about sports analytics and probability
- **Bet Responsibly**: Never bet more than you can afford to lose
- **Legal Compliance**: Ensure sports betting is legal in your jurisdiction
- **Terms of Service**: Respect website terms when scraping

### Anti-Detection

- Realistic browser fingerprints
- Human-like request timing
- Session persistence
- Respectful rate limiting

## Support & Maintenance

### Updating Player Cache

```bash
# Add new players to PLAYERS_TO_ADD.txt
echo "Ja Morant" >> PLAYERS_TO_ADD.txt
echo "Victor Wembanyama" >> PLAYERS_TO_ADD.txt

# Rebuild cache
python build_databallr_player_cache.py
```

### Troubleshooting

Check logs:
```bash
tail -f nba_betting_system.log
```

Clear cache:
```bash
rm data/cache/player_stats_cache.json
```

Reinstall dependencies:
```bash
pip install --upgrade -r requirements.txt
playwright install chromium
```

## License

MIT License - See LICENSE file for details

## Disclaimer

This system is for educational and research purposes only. Sports betting involves risk. Past performance does not guarantee future results. Always bet responsibly and within your means.
