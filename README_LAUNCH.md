# How to Run the PositiveEdge System

## Quick Start

### Option 1: Double-Click Launch (Windows)
Simply double-click `run_analysis.bat` in the project root directory.

### Option 2: Command Line
```bash
python scrapers/unified_analysis_pipeline.py
```

### Option 3: Use the Batch File
```bash
run_analysis.bat
```

## What Gets Analyzed

The system will:
1. **Scrape Sportsbet** - Get games, markets, insights, and player props
2. **Analyze Team Bets** - Use context-aware analysis with DataballR data
3. **Project Player Props** - Calculate probabilities using advanced projection model
4. **Filter & Rank** - Apply quality thresholds and market-specific tiers
5. **Display Results** - Show all high-confidence bets with full transparency

## Features Enabled

- ✅ **Market-Specific Confidence Tiers**
  - Player Props: C-Tier = 35 (soft floor 0.92x)
  - Team Sides: C-Tier = 40
  - Totals: C-Tier = 45 (soft floor 1.05x)

- ✅ **Role Modifier System**
  - Starter minutes increase detection (≥6 min = +3%)
  - Teammate usage impact (≥18 = +2%, 10-18 = +1%)
  - Max +5% probability boost, confidence-scaled

- ✅ **Insight Decay Penalties**
  - Age-based decay (≤7 days: 100%, ≤30: 85%, ≤90: 65%, >90: 45%)
  - Multi-season penalty (75% multiplier)
  - Roster overlap check (50% if no overlap)

- ✅ **Prop Volatility Index (PVI)**
  - Bench player penalty (-30% confidence)
  - Low minutes penalty (<15 min: -40%)
  - High variance penalty (-30%)

- ✅ **Correlation Awareness**
  - De-tier correlated bets instead of blocking
  - A→B, B→C, C→WATCHLIST downgrades

- ✅ **CLV Tracking**
  - Opening vs closing line tracking
  - Variance/luck flagging
  - View metrics: `python scripts/analyze_clv.py`

- ✅ **Consistency Validation**
  - Validates rationale against data
  - Auto-downgrades tier if contradictions found

- ✅ **SQLite Persistent Cache**
  - Caches minutes/usage/injuries/role data
  - Auto-invalidation (24h for usage, 6h for injuries)

## Filtering Criteria

- **EV Thresholds**: Props ≥ +3%, Sides/Totals ≥ +2%
- **Confidence Tiers**: Market-specific (see above)
- **Max per game**: Unlimited (correlation handled by de-tiering)
- **Watchlist**: Near-miss bets (Conf 35-49, Prob ≥ 55%, Edge ≥ +4%)

## Output Files

- Results saved to: `data/outputs/`
- CLV tracking: `data/clv_tracking.db`
- Player cache: `data/cache/player_data.db`
- Error logs: `error_log.txt` (if errors occur)

## Helper Scripts

- **View CLV Metrics**: `python scripts/analyze_clv.py [days] [tier]`
- **Update Closing Lines**: `python scripts/update_clv_closing.py <bet_id> <line> <odds>`
- **Record Results**: `python scripts/record_clv_result.py <bet_id> <WIN|LOSS|PUSH>`
- **View Results**: `python view_results.py` or double-click `view_results.bat`

## Command Line Options

The main pipeline accepts optional arguments:
```bash
python scrapers/unified_analysis_pipeline.py [max_games] [headless]
```

- `max_games`: Maximum number of games to analyze (default: all available)
- `headless`: Run browser in headless mode (default: True)

Example:
```bash
python scrapers/unified_analysis_pipeline.py 5 false
```

This analyzes 5 games with visible browser.

## Troubleshooting

### Python Not Found
- Ensure Python 3.8+ is installed
- Add Python to your system PATH
- Verify with: `python --version`

### Module Not Found Errors
- Install requirements: `pip install -r requirements.txt`

### Browser Issues
- If Playwright errors occur, install browsers: `playwright install chromium`

### Cache Issues
- Clear cache: Delete `data/cache/` directory
- Cache will regenerate on next run

## System Requirements

- Python 3.8 or higher
- Windows 10/11 (for .bat files)
- Internet connection (for scraping)
- ~500MB disk space (for databases and cache)
