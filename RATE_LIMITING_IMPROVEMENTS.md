# Sportsbet Rate Limiting Improvements

## Issue
Sportsbet banned/rate-limited our scraper due to too many requests in a short time period.

## Solution Implemented

### 1. Pipeline-Level Rate Limiting (`scrapers/unified_analysis_pipeline.py`)

**Initial Delay After Overview Page** (Line 222-225):
```python
# Wait 5-8 seconds before starting to scrape individual games
initial_delay = random.uniform(5, 8)
logger.info(f"Rate limiting: waiting {initial_delay:.1f}s before scraping games...")
time.sleep(initial_delay)
```

**Between-Game Delays** (Line 304-309):
```python
# Wait 10-15 seconds between each game scrape
if i < actual_max:
    delay = random.uniform(10, 15)  # Increased from 2 seconds
    logger.info(f"  Rate limiting: waiting {delay:.1f}s before next game...")
    time.sleep(delay)
```

### 2. Scraper-Level Rate Limiting (`scrapers/sportsbet_final_enhanced.py`)

**Overview Page Loading** (Line 2633-2640):
```python
# Wait 8 seconds for dynamic content (increased from 5s)
time.sleep(8)

# Scroll delays increased from 2s to 3s each
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(3)  # Increased from 2 seconds
page.evaluate("window.scrollTo(0, 0)")
time.sleep(3)  # Increased from 2 seconds
```

## Rate Limiting Strategy

### Conservative Approach
- **Random delays** between 10-15 seconds per game
- **No predictable patterns** - randomization makes it harder to detect as a bot
- **Initial cooldown** of 5-8 seconds after loading overview page
- **Slower page interactions** with 3-second delays instead of 2

### Expected Behavior

For a typical session analyzing 4-5 games:
1. Load overview page: ~14 seconds (8s load + 6s scrolling)
2. Initial delay: 5-8 seconds
3. Game 1: ~3-5 minutes to scrape
4. Delay: 10-15 seconds
5. Game 2: ~3-5 minutes to scrape
6. Delay: 10-15 seconds
7. Game 3: ~3-5 minutes to scrape
8. (etc.)

**Total time for 5 games**: ~20-30 minutes (vs ~10-15 minutes before)

## Trade-offs

### Benefits
✅ **Much lower risk of being banned/rate-limited**
✅ **Appears more human-like** with random delays
✅ **Sustainable for daily use** without triggering anti-bot measures
✅ **Preserves access** to Sportsbet data source

### Costs
❌ **Slower pipeline execution** (~50% longer runtime)
❌ **Need to plan for longer waits** when analyzing multiple games

## Recommendations

### For Daily Use
- **Analyze only the games you need** (use selective analysis, not "all")
- **Run once per day** rather than multiple times
- **Schedule during off-peak hours** if possible
- **Limit to 5-7 games maximum** per session

### If Still Getting Banned
If you continue to see rate limiting issues:

1. **Increase delays further**:
   ```python
   delay = random.uniform(15, 25)  # Even more conservative
   ```

2. **Add daily limits**:
   - Only scrape once every 24 hours
   - Cache results more aggressively

3. **Use rotating user agents**:
   - Implement user agent rotation
   - Rotate IP addresses if possible (VPN)

4. **Implement exponential backoff on errors**:
   - If you get blocked, wait progressively longer before retry
   - Start with 5 minutes, then 15, then 30, etc.

## Files Modified

1. **`scrapers/unified_analysis_pipeline.py`**
   - Line 222-225: Added initial delay after overview page
   - Line 304-309: Increased between-game delays to 10-15 seconds

2. **`scrapers/sportsbet_final_enhanced.py`**
   - Line 2633-2640: Increased page load and scroll delays

## Monitoring

Watch the logs for these messages:
```
[INFO] Rate limiting: waiting 6.3s before scraping games...
[INFO]   Rate limiting: waiting 12.7s before next game...
```

These indicate the rate limiting is working properly.

## Testing

The rate limiting is active immediately. Next time you run:
```bash
python scrapers/unified_analysis_pipeline.py
```

You should see:
- Slower execution with visible delays
- Clear logging of rate limit waits
- No ban/blocking from Sportsbet (if successful)

---

**Status**: ✅ IMPLEMENTED
**Date**: December 6, 2025
**Priority**: CRITICAL (required to maintain Sportsbet access)
