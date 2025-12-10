# NBA Betting System - Setup Guide

## Complete Installation Instructions

### Step 1: Install Python

**Windows:**
1. Download Python 3.8+ from [python.org](https://www.python.org/downloads/)
2. Run installer
3. ✅ **IMPORTANT**: Check "Add Python to PATH"
4. Click "Install Now"
5. Verify installation:
   ```bash
   python --version
   ```

**Mac:**
```bash
# Using Homebrew
brew install python3

# Verify
python3 --version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Verify
python3 --version
```

### Step 2: Download the System

**Option A: Git Clone (Recommended)**
```bash
git clone <repository-url>
cd nba-betting-system
```

**Option B: Download ZIP**
1. Download ZIP from repository
2. Extract to a folder
3. Open terminal/command prompt in that folder

### Step 3: Run the System

**Windows:**
```bash
run_betting_system.bat
```

**Linux/Mac:**
```bash
chmod +x run_betting_system.sh
./run_betting_system.sh
```

The launcher will automatically:
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Download browser drivers
- ✅ Run the analysis

### Step 4: First Run

On first run, you'll see:
```
Creating virtual environment...
Installing dependencies...
Installing Playwright browsers (one-time setup)...
Starting NBA Betting System...
```

This takes 2-3 minutes. Subsequent runs are much faster.

## Manual Installation (Advanced)

If the launcher doesn't work, install manually:

### 1. Create Virtual Environment
```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Playwright Browsers
```bash
playwright install chromium
```

### 5. Run the System
```bash
python nba_betting_system.py
```

## Configuration

### Player Cache Setup

The system uses a player cache to speed up DataBallr lookups.

**Add New Players:**

1. Create/edit `PLAYERS_TO_ADD.txt`:
   ```
   LeBron James
   Stephen Curry
   Giannis Antetokounmpo
   ```

2. Build the cache:
   ```bash
   python build_databallr_player_cache.py
   ```

3. The cache is saved to `data/cache/databallr_player_cache.json`

**Pre-built Cache:**

The system includes a cache with 100+ common NBA players. You only need to add players if you see warnings like:
```
WARNING: Player "Victor Wembanyama" not in cache
```

### Command Line Options

```bash
# Analyze specific number of games
python nba_betting_system.py --games 5

# Change confidence threshold
python nba_betting_system.py --min-confidence 75

# Custom output file
python nba_betting_system.py --output my_bets.json

# Show browser (for debugging)
python nba_betting_system.py --no-headless
```

### Environment Variables

Optional environment variables for advanced configuration:

```bash
# Set log level
export NBA_BETTING_LOG_LEVEL=DEBUG

# Set cache directory
export NBA_BETTING_CACHE_DIR=/path/to/cache

# Set timeout (seconds)
export NBA_BETTING_TIMEOUT=60
```

## Troubleshooting

### Issue: "Python not found"

**Windows:**
1. Reinstall Python with "Add to PATH" checked
2. Or add manually:
   - Search "Environment Variables"
   - Edit PATH
   - Add `C:\Python3X\` and `C:\Python3X\Scripts\`

**Mac/Linux:**
- Use `python3` instead of `python`
- Or create alias: `alias python=python3`

### Issue: "playwright: command not found"

```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Then install
pip install playwright
playwright install chromium
```

### Issue: "Permission denied" (Linux/Mac)

```bash
# Make launcher executable
chmod +x run_betting_system.sh

# Or run with bash
bash run_betting_system.sh
```

### Issue: "Module not found"

```bash
# Ensure virtual environment is activated
# Then reinstall dependencies
pip install -r requirements.txt
```

### Issue: Scraping fails / No data returned

**Possible causes:**
1. **Website changes**: Sportsbet updated their HTML structure
   - Check logs for specific errors
   - May need scraper updates

2. **Network issues**: Connection timeout
   - Check internet connection
   - Try again later

3. **Rate limiting**: Too many requests
   - System has built-in throttling
   - Wait a few minutes and retry

4. **No games available**: No NBA games scheduled
   - Check NBA schedule
   - System will show "No games found"

### Issue: Player not in cache

```
WARNING: Player "New Player" not in cache
```

**Solution:**
1. Add player to `PLAYERS_TO_ADD.txt`
2. Run `python build_databallr_player_cache.py`
3. Re-run analysis

### Issue: Insufficient game data

```
Skipping Player X - insufficient data (n=3)
```

**Cause**: Player hasn't played enough games (need 5+)

**Solution**: This is expected for:
- Rookies early in season
- Injured players returning
- Players with limited minutes

System automatically skips these players.

## Performance Tips

### Speed Up Analysis

1. **Analyze fewer games**: `--games 3`
2. **Use cache**: System auto-caches for 24 hours
3. **Headless mode**: Default, faster than showing browser
4. **Parallel processing**: Future enhancement

### Reduce API Calls

1. **Pre-build player cache**: Run `build_databallr_player_cache.py` with all players
2. **Use stats cache**: Automatically enabled
3. **Batch analysis**: Analyze multiple games in one run

## Updating the System

### Update Code

**Git:**
```bash
git pull origin main
```

**Manual:**
1. Download latest version
2. Replace files (keep `data/cache/` folder)

### Update Dependencies

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Update packages
pip install --upgrade -r requirements.txt
```

### Update Player Cache

```bash
# Add new players to PLAYERS_TO_ADD.txt
# Then rebuild
python build_databallr_player_cache.py
```

## System Requirements

### Minimum Requirements
- **CPU**: Dual-core processor
- **RAM**: 4 GB
- **Storage**: 500 MB (including dependencies)
- **Internet**: Broadband connection
- **OS**: Windows 10+, macOS 10.14+, Ubuntu 18.04+

### Recommended Requirements
- **CPU**: Quad-core processor
- **RAM**: 8 GB
- **Storage**: 1 GB
- **Internet**: High-speed connection

## Security & Privacy

### Data Collection

The system:
- ✅ Scrapes public betting data from Sportsbet
- ✅ Scrapes public player stats from DataBallr
- ✅ Stores data locally only
- ❌ Does NOT collect personal information
- ❌ Does NOT send data to external servers
- ❌ Does NOT place bets automatically

### Safe Scraping Practices

The system includes:
- Respectful rate limiting (1 request/second)
- Realistic browser fingerprints
- Session management
- Automatic retry with backoff

### Legal Compliance

- ✅ Scrapes publicly available data
- ✅ Respects robots.txt
- ✅ Educational/research purposes
- ⚠️ Check local laws regarding sports betting
- ⚠️ Review website terms of service

## Getting Help

### Check Logs

```bash
# View recent logs
tail -f nba_betting_system.log

# Search for errors
grep ERROR nba_betting_system.log
```

### Debug Mode

```bash
# Run with debug logging
python nba_betting_system.py --log-level DEBUG
```

### Common Log Messages

**INFO**: Normal operation
```
[INFO] Found 5 games to analyze
[INFO] ✓ LeBron James points Over 25.5 - Confidence: 78%
```

**WARNING**: Non-critical issues
```
[WARNING] Player "New Player" not in cache
[WARNING] Insufficient data for Player X (n=3)
```

**ERROR**: Critical issues
```
[ERROR] Failed to scrape Sportsbet
[ERROR] DataBallr connection timeout
```

## Support

For issues not covered in this guide:

1. Check `SYSTEM_ARCHITECTURE.md` for technical details
2. Review logs in `nba_betting_system.log`
3. Search existing issues in repository
4. Create new issue with:
   - Error message
   - Log excerpt
   - System info (OS, Python version)

## Next Steps

After successful setup:

1. **Run first analysis**: `python nba_betting_system.py --games 3`
2. **Review results**: Check `betting_recommendations.json`
3. **Understand metrics**: Read "Understanding the Results" in README
4. **Build player cache**: Add your favorite players
5. **Customize settings**: Adjust confidence threshold, output format

## Disclaimer

This system is for educational and research purposes only. Sports betting involves risk. Always bet responsibly and within your means. Past performance does not guarantee future results.
