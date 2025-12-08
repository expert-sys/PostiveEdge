# PositiveEdge - Comprehensive Launcher

## Overview

The **Comprehensive Launcher** is a streamlined, automated pipeline that runs all scrapers, analyzes data with model projections, and displays high-confidence bet recommendations.

## Features

### 🚀 Full Pipeline Automation
- **Sportsbet Scraper**: Scrapes betting markets, insights, and historical stats
- **DataballR Scraper**: Fetches player game logs with robust error handling
- **RotoWire Integration**: (Optional) Lineups and injury data
- **Unified Analysis**: Runs model projections with weighted confidence system
- **Smart Display**: Shows only top 5 bets (50+ confidence, max 2 per game)

### 🛡️ Enhanced Anti-Detection
- **User Agent Rotation**: Pool of 20+ real user agents
- **Random Timing**: Human-like delays between actions
- **Mouse Movements**: Simulated human cursor behavior
- **Viewport Randomization**: Different screen sizes per session
- **Canvas Fingerprinting**: Randomized to avoid tracking
- **WebGL Protection**: Masked vendor/renderer info
- **Geolocation Spoofing**: Australian IPs and timezones

### 📊 Intelligent Filtering
- **Weighted Confidence**: EV + matchup + sample strength - correlation penalties
- **Combined EV + Probability**: Filters out low-quality bets early
- **Correlation Control**: Limits bets per player/game to reduce risk
- **Trend Quality Scoring**: Validates historical trends before using them

## Quick Start

### Windows (Command Prompt)
```cmd
quick-start-comprehensive.bat
```

### Windows (PowerShell)
```powershell
.\quick-start-comprehensive.ps1
```

### Manual (All Platforms)
```bash
python launcher_comprehensive.py
```

## Command Line Options

### Interactive Mode (Menu-Driven)
```bash
python launcher_comprehensive.py
```

### Auto-Run Full Pipeline
```bash
python launcher_comprehensive.py --auto
```

### View Latest Results Only
```bash
python launcher_comprehensive.py --view
```

## Menu Options

### [1] Run Full Pipeline
Runs complete workflow:
1. Scrapes Sportsbet for today's games
2. Fetches player stats from DataballR
3. Analyzes all data with model projections
4. Displays top 5 high-confidence bets

**Time**: ~30-60 seconds

### [2] Quick Analysis
Uses existing scraped data (no new scraping).
Fast analysis if you already have recent data.

**Time**: ~5-10 seconds

### [3] Scrape Data Only
Run scrapers without analysis.
Options:
- Sportsbet only
- DataballR test
- Both

**Time**: ~20-40 seconds

### [4] View Latest Results
Quick summary of most recent analysis.

### [5] View All Results
Browse all historical analysis outputs.

### [6] System Settings
- View cache status
- Build/update player cache
- Clear cache
- View logs

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    FULL PIPELINE                             │
│         (All handled by Unified Analysis Pipeline)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────┐
        │  UNIFIED ANALYSIS PIPELINE            │
        │  ├─ Scrape Sportsbet (markets)        │
        │  ├─ Extract insights & stats          │
        │  ├─ Fetch DataballR player logs       │
        │  ├─ Analyze team bets (insights)      │
        │  ├─ Calculate player projections      │
        │  ├─ Apply weighted confidence         │
        │  ├─ Filter by EV + probability        │
        │  ├─ Rank by confidence                │
        │  └─ Display top 5 bets                │
        └──────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────┐
        │  RESULTS SAVED                        │
        │  - data/outputs/*.json                │
        │  - Confidence: 50+/100                │
        │  - Max 2 per game, Max 5 total        │
        └──────────────────────────────────────┘
```

## Anti-Detection Details

### Browser Fingerprinting Protection

**User Agent Rotation**
- 15+ unique, real user agents
- Chrome, Edge, Firefox, Safari
- Windows 10/11, macOS versions

**Viewport Randomization**
- 1920x1080 (Full HD)
- 1366x768 (Laptop)
- 1440x900 (MacBook)
- 2560x1440 (2K)

**Locale & Timezone**
- en-AU locale
- Australia/Sydney, Melbourne, Brisbane, Perth
- Geolocation coordinates randomized

### Behavioral Stealth

**Human-Like Delays**
```python
human_delay(0.5, 2.0)  # Random 0.5-2 second delay
```

**Random Scrolling**
```python
random_scroll(page, num_scrolls=3)  # Scroll like a human
```

**Mouse Movements**
```python
random_mouse_move(page, num_moves=5)  # Simulate cursor
```

**Human-Like Clicking**
```python
human_like_click(page, selector)  # Click with random offset
```

### Technical Protections

**WebDriver Property**
- `navigator.webdriver` set to `undefined`

**Chrome Object**
- Injected `window.chrome.runtime` object

**Plugins Array**
- Non-empty `navigator.plugins`

**WebGL Fingerprint**
- Vendor: "Intel Inc."
- Renderer: "Intel Iris OpenGL Engine"

**Canvas Fingerprint**
- Random noise added to canvas data
- Prevents tracking via `toDataURL()` / `toBlob()`

**Permissions API**
- Realistic notification permission handling

## Output Files

### Scraped Data
```
data/scraped/sportsbet_match_<match_id>_<timestamp>.json
```

### Analysis Results
```
data/outputs/unified_analysis_<timestamp>.json
```

### Logs
```
output.log
```

## Configuration

### Confidence Threshold
Edit `scrapers/unified_analysis_pipeline.py`:
```python
confidence_thresholds = [50, 45, 40, 35, 30, 25, 20]  # Start at 50
```

### EV Thresholds
```python
MIN_EV_PLAYER_PROP = 3.0   # +3% for player props
MIN_EV_TEAM_BET = 2.0      # +2% for sides/totals
```

### Max Bets Per Game
```python
MAX_BETS_PER_GAME = 2
MAX_TOTAL_BETS = 5
```

### Anti-Detection Settings
Edit `scrapers/anti_detection.py`:
```python
USER_AGENTS = [...]        # Add more user agents
VIEWPORTS = [...]          # Add more viewport sizes
LOCALES = [...]            # Add more locales
```

## Troubleshooting

### Issue: "No scraped data found"
**Solution**: Run "Scrape Data Only" first, then "Quick Analysis"

### Issue: "Player cache not found"
**Solution**: Go to System Settings → Build Player Cache

### Issue: "Script failed with exit code 1"
**Solution**: Check `output.log` for detailed error messages

### Issue: "UnicodeEncodeError"
**Solution**: Already fixed in latest version (uses ASCII characters)

### Issue: "Sportsbet blocked/403 error"
**Solution**: 
- Anti-detection is enabled by default
- Try running with `headless=False` to see browser
- Check if Sportsbet is accessible in your region
- Consider using a proxy (edit `anti_detection.py`)

## Performance

### Expected Execution Times
- **Sportsbet Scraper**: 20-30 seconds (3-5 games)
- **Unified Analysis**: 5-10 seconds
- **Total Pipeline**: 30-60 seconds

### Optimization Tips
1. **Pre-build Player Cache**: Run once, saves time on every analysis
2. **Use Quick Analysis**: If data is fresh (< 1 hour old)
3. **Reduce Scraper Delay**: Edit `human_delay()` parameters (but increases detection risk)

## Best Practices

### Daily Workflow
1. **Morning**: Build/update player cache
2. **Game Day**: Run full pipeline 1-2 hours before games
3. **Review**: Check top 5 bets, validate with your own research
4. **Bet Responsibly**: Use bet recommendations as guidance, not absolutes

### Scraping Etiquette
- Don't run scraper more than once per 10 minutes
- Use random delays (already implemented)
- Respect robots.txt
- Don't abuse anti-detection for malicious purposes

## Support

For issues, questions, or feature requests, refer to the main `README.md` or check the `docs/` folder for detailed guides.

---

**Version**: 2.0  
**Last Updated**: December 2025  
**License**: MIT

