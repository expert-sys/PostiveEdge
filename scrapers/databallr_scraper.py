"""
Databallr.com Scraper - Playwright-based player game log scraper
================================================================
Alternative data source for NBA player stats when NBA Stats API times out.

Usage:
    from scrapers.databallr_scraper import get_player_game_log
    log = get_player_game_log("LeBron James", last_n_games=10)
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import logging
import re
import time
import json
import sys
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from datetime import datetime

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.retry_utils import retry_scraper_call

# Import GameLogEntry for data structure compatibility only
try:
    from scrapers.data_models import GameLogEntry
except ImportError:
    GameLogEntry = None

# Use centralized logging
from config.logging_config import get_logger
logger = get_logger(__name__)


# Static player ID mapping (fallback when NBA API is down)
# These are the most common NBA players
PLAYER_ID_FALLBACK = {
    "lebron james": 2544,
    "stephen curry": 201939,
    "kevin durant": 201142,
    "giannis antetokounmpo": 203507,
    "luka doncic": 1629029,
    "nikola jokic": 203999,
    "joel embiid": 203954,
    "jayson tatum": 1628369,
    "damian lillard": 203081,
    "anthony davis": 203076,
    "kawhi leonard": 202695,
    "james harden": 201935,
    "kyrie irving": 202681,
    "paul george": 202331,
    "devin booker": 1626164,
    "donovan mitchell": 1628378,
    "trae young": 1629027,
    "ja morant": 1629630,
    "zion williamson": 1629627,
    "lamelo ball": 1630163,
    "shai gilgeous-alexander": 1628983,
    "jimmy butler": 202710,
    "bam adebayo": 1628389,
    "karl-anthony towns": 1626157,
    "pascal siakam": 1627783,
    "domantas sabonis": 1627734,
    "dejounte murray": 1627749,
    "fred vanvleet": 1627832,
    "cj mccollum": 203468,
    "bradley beal": 203078,
    "kyle kuzma": 1628398,
    "jordan poole": 1629673,
    "tyrese haliburton": 1630169,
    "julius randle": 203944,
    "draymond green": 203110,
    "klay thompson": 202691,
    "russell westbrook": 201566,
    "chris paul": 101108,
    "bobby portis": 1626171,  # Added based on user feedback
}


def launch_databallr_browser(headless: bool = True) -> Tuple:
    """
    Launch Playwright browser with anti-detection measures.

    Returns:
        Tuple of (playwright, browser, context)
    """
    p = sync_playwright().start()

    browser = p.chromium.launch(
        headless=headless,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
        ]
    )

    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='en-US'
    )

    # Anti-detection JavaScript
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        window.chrome = {runtime: {}};
    """)

    return p, browser, context


def _player_name_to_slug(player_name: str) -> str:
    """Convert player name to URL slug format (e.g., 'LeBron James' -> 'lebron-james')"""
    # Remove periods first, then convert spaces to hyphens
    return player_name.lower().replace('.', '').replace(' ', '-').replace("'", '')


def _load_databallr_cache() -> Dict[str, int]:
    """Load databallr player ID cache from file"""
    cache_file = Path(__file__).parent.parent / "data" / "cache" / "databallr_player_cache.json"
    
    if not cache_file.exists():
        return {}
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('cache', {})
    except Exception as e:
        logger.warning(f"Failed to load databallr cache: {e}")
        return {}


def _load_stats_cache() -> Dict:
    """Load pre-cached player stats from file"""
    cache_file = Path(__file__).parent.parent / "data" / "cache" / "player_stats_cache.json"
    
    if not cache_file.exists():
        return {}
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('cache', {})
    except Exception as e:
        logger.warning(f"Failed to load stats cache: {e}")
        return {}


def _is_stats_cache_fresh(player_stats: Dict, max_age_hours: int = 24) -> bool:
    """Check if cached stats are still fresh (< 24 hours old)"""
    if not player_stats or 'timestamp' not in player_stats:
        return False
    
    try:
        from datetime import datetime, timedelta
        cached_time = datetime.fromisoformat(player_stats['timestamp'])
        age = datetime.now() - cached_time
        return age < timedelta(hours=max_age_hours)
    except:
        return False


def _save_player_to_cache(player_name: str, player_id: int, player_slug: str) -> None:
    """
    Save a newly discovered player to the cache automatically.
    
    Args:
        player_name: Player name (normalized)
        player_id: Player ID from databallr
        player_slug: Player slug (for URL construction)
    """
    cache_file = Path(__file__).parent.parent / "data" / "cache" / "databallr_player_cache.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing cache
    existing_cache = _load_databallr_cache()
    
    # Normalize player name (same as _get_player_id)
    player_name_normalized = player_name.lower().strip().replace('.', '').replace('  ', ' ')
    
    # Add to cache if not already there
    if player_name_normalized not in existing_cache:
        existing_cache[player_name_normalized] = player_id
        logger.info(f"[Databallr] Auto-saving {player_name} (ID: {player_id}) to cache")
        
        # Save cache
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'cache': existing_cache
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"[Databallr] Cache updated: {len(existing_cache)} players")
        except Exception as e:
            logger.warning(f"[Databallr] Failed to save cache: {e}")


def _get_player_id(player_name: str) -> Optional[int]:
    """
    Get player ID from cache, fallback mapping, or return None.
    
    Checks in order:
    1. Databallr cache file (if exists)
    2. Hardcoded fallback mapping
    """
    # Normalize: remove periods, extra spaces, lowercase
    player_name_normalized = player_name.lower().strip().replace('.', '').replace('  ', ' ')
    
    # Try cache file first
    cache = _load_databallr_cache()
    if cache and player_name_normalized in cache:
        return cache[player_name_normalized]
    
    # Fallback to hardcoded mapping
    if player_name_normalized in PLAYER_ID_FALLBACK:
        return PLAYER_ID_FALLBACK[player_name_normalized]
    
    return None


def smart_search_player_databallr(page, player_name: str) -> Optional[Tuple[int, str, str]]:
    """
    Smart search for a player on databallr.com using multiple strategies.
    
    This function will:
    1. Try cache first
    2. Try navigating to constructed URL
    3. Try searching on dashboard/search page
    4. Extract player ID and slug from successful URL
    5. Auto-save to cache
    
    Args:
        page: Playwright page object
        player_name: Player name to search for
        
    Returns:
        Tuple of (player_id, player_slug, player_url) if found, None otherwise
    """
    logger.info(f"[Databallr] Smart searching for: {player_name}")
    
    # Strategy 1: Check cache first (FAST PATH)
    player_id = _get_player_id(player_name)
    if player_id:
        player_slug = _player_name_to_slug(player_name)
        player_url = f"https://databallr.com/last-games/{player_id}/{player_slug}"
        
        # Verify URL works
        try:
            page.goto(player_url, timeout=15000)
            page.wait_for_load_state("domcontentloaded", timeout=8000)  # Faster: domcontentloaded instead of networkidle
            
            # Quick check if page loaded
            try:
                # Just check if we're on a player page (URL contains /last-games/)
                if "/last-games/" in page.url:
                    logger.info(f"[Databallr] Found in cache: {player_name} (ID: {player_id})")
                    return (player_id, player_slug, player_url)
            except:
                pass
        except Exception as e:
            logger.debug(f"[Databallr] Cache URL failed: {e}")
    
    # Player not in cache - DON'T search, just fail fast
    # Searching takes too long and causes loops
    logger.warning(f"[Databallr] Player {player_name} not in cache. Skipping search to avoid loops.")
    logger.info(f"[Databallr] To add this player:")
    logger.info(f"[Databallr]   1. Find on databallr.com: https://databallr.com")
    logger.debug(f"Databallr: Copy URL format: https://databallr.com/last-games/[ID]/[slug]")
    logger.info(f"[Databallr]   3. Add to PlayerIDs.txt")
    logger.info(f"[Databallr]   4. Run: python build_databallr_player_cache.py")
    return None


def search_player_databallr(page, player_name: str) -> Optional[str]:
    """
    Navigate to player's databallr page using smart search.
    
    This function uses smart_search_player_databallr which will:
    1. Check cache first
    2. Try searching on databallr.com
    3. Auto-save newly found players to cache
    
    Args:
        page: Playwright page object
        player_name: Player name to search for

    Returns:
        Player URL if found, None otherwise
    """
    result = smart_search_player_databallr(page, player_name)
    
    if result:
        player_id, player_slug, player_url = result
        # smart_search already navigated and verified the page, so we can return the URL
        # But verify we're still on the right page
        if page.url.startswith("https://databallr.com/last-games/"):
            logger.debug(f"Found player: {player_name} (ID: {player_id})")
            return player_url
        else:
            # Navigate to the URL if we're not already there
            try:
                page.goto(player_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=10000)
                page.wait_for_selector("table, [class*='game'], [class*='stat']", timeout=5000)
                logger.debug(f"Loaded player page: {player_url}")
                return player_url
            except Exception as e:
                logger.error(f"[Databallr] Navigation error: {e}")
                return None
    
    return None


def _parse_float(text: str) -> Optional[float]:
    """Parse float from text, handling % and other characters"""
    try:
        cleaned = re.sub(r'[^\d.-]', '', text.strip())
        if cleaned:
            return float(cleaned)
    except:
        pass
    return None


def _parse_int(text: str) -> int:
    """Parse int from text"""
    try:
        cleaned = re.sub(r'[^\d-]', '', text.strip())
        if cleaned:
            return int(cleaned)
    except:
        pass
    return 0


def _parse_table_row(cells) -> Optional[Dict]:
    """
    Parse table row into game dict.
    Based on databallr table structure.
    Returns dict with all available stats.
    """
    try:
        if len(cells) < 4:
            return None
        game = {}
        for i, cell in enumerate(cells):
            text = cell.get_text(strip=True)
            if not text or text == '-':
                continue
            if i == 0:
                game['date'] = text
                continue
            val = _parse_float(text)
            if val is None:
                continue
            if i == 3:
                game['points'] = int(val)
            elif i == 4:
                game['assists'] = int(val)
            elif i == 6:
                game['rebounds'] = int(val)
            elif i == 7:
                game['turnovers'] = int(val)
            elif i == 13:
                game['steals'] = int(val)
            elif i == 14:
                game['blocks'] = int(val)
            elif i == 15:
                game['minutes'] = val
            elif i == 16:
                game['plus_minus'] = int(val)
        if 'date' in game and 'points' in game:
            game.setdefault('assists', 0)
            game.setdefault('rebounds', 0)
            game.setdefault('turnovers', 0)
            game.setdefault('steals', 0)
            game.setdefault('blocks', 0)
            game.setdefault('minutes', 0.0)
            game.setdefault('plus_minus', 0)
            game.setdefault('fta', 0)
            return game
        return None
    except Exception as e:
        logger.debug(f"Failed to parse row: {e}")
        return None


def scrape_player_game_log_databallr(page, player_url: str, last_n_games: int = 20) -> List[Dict]:
    """Scrape game log from player page using Table View."""
    logger.debug(f"Scraping games from: {player_url}")
    try:
        if page.url != player_url:
            page.goto(player_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=10000)
        logger.info(f"[Databallr] Setting to Last {last_n_games} games...")
        try:
            table_view_button = page.locator("button:has-text('Table View')")
            if table_view_button.is_visible(timeout=5000):
                table_view_button.click()
                logger.info(f"[Databallr] Clicked Table View, waiting for data to load...")
                page.wait_for_timeout(3000)
        except:
            logger.debug("[Databallr] Table View button not found or already selected")
            pass

        # CRITICAL FIX: Wait for table data to actually load
        # The table exists immediately but is populated by JavaScript
        logger.info(f"[Databallr] Waiting for table data to populate...")
        try:
            # Wait for table with actual data (not "No season data added yet")
            # Strategy 1: Wait for table rows with td elements (actual data)
            page.wait_for_selector("table tbody tr td", timeout=10000)
            logger.info(f"[Databallr] ✓ Table data detected")
        except:
            logger.warning(f"[Databallr] Table data not detected, will try to parse anyway")

        # Additional wait to ensure all rows are loaded
        page.wait_for_timeout(2000)

        # Take debug screenshot AFTER waiting for data
        try:
            debug_dir = Path(__file__).parent.parent / "debug"
            debug_dir.mkdir(exist_ok=True)
            page.screenshot(path=str(debug_dir / "databallr_table_view.png"))
        except:
            pass

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        games = []
        tables = soup.find_all('table')
        logger.info(f"[Databallr] Found {len(tables)} table(s) in HTML")

        for table in tables:
            rows = table.find_all('tr')
            logger.info(f"[Databallr] Processing table with {len(rows)} rows")
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                game = _parse_table_row(cells)
                if game:
                    games.append(game)

        logger.debug(f"Scraped {len(games)} games")
        return games[:last_n_games]
    except Exception as e:
        logger.error(f"[Databallr] Failed to scrape game log: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []


def map_to_game_log_entry(raw_game: Dict, player_name: str) -> GameLogEntry:
    """Convert databallr game dict to GameLogEntry format."""
    date_str = raw_game.get('date', 'Unknown')
    game_id = f"DB_{date_str.replace('/', '')}_{player_name.replace(' ', '_')}"
    return GameLogEntry(
        game_date=date_str,
        game_id=game_id,
        matchup=f"{player_name} vs Unknown",
        home_away="UNKNOWN",
        opponent="Unknown",
        opponent_id=0,
        won=False,
        minutes=raw_game.get('minutes', 0.0),
        points=raw_game.get('points', 0),
        rebounds=raw_game.get('rebounds', 0),
        assists=raw_game.get('assists', 0),
        steals=raw_game.get('steals', 0),
        blocks=raw_game.get('blocks', 0),
        turnovers=raw_game.get('turnovers', 0),
        fg_made=0,
        fg_attempted=0,
        three_pt_made=0,
        three_pt_attempted=0,
        ft_made=0,
        ft_attempted=raw_game.get('fta', 0),
        plus_minus=raw_game.get('plus_minus', 0),
        team_points=0,
        opponent_points=0,
        total_points=0
    )


@retry_scraper_call(max_attempts=3, min_wait=2.0, max_wait=10.0)
def get_player_game_log(
    player_name: str,
    season: str = "2024-25",
    last_n_games: Optional[int] = None,
    retries: int = 3,
    use_cache: bool = True,
    headless: bool = True
) -> List[GameLogEntry]:
    """
    Get player game log from databallr.com.
    
    This function has retry logic - it will automatically retry up to 3 times
    with exponential backoff if scraping fails.
    """
    if last_n_games is None:
        last_n_games = 20
    logger.info(f"[Databallr] Fetching {last_n_games} games for {player_name}")
    
    # Check player ID cache first - if not found, DON'T retry (avoids infinite loops)
    player_id = _get_player_id(player_name)
    player_not_in_cache = (player_id is None)
    
    # If player not in ID cache, don't even try - just return empty list
    if player_not_in_cache:
        logger.warning(f"[Databallr] Player {player_name} not in ID cache. Skipping (no retries).")
        logger.debug(f"To add player: Find on databallr.com, add URL to PlayerIDs.txt")
        return []
    
    # Check stats cache for pre-fetched data (FAST PATH)
    if use_cache:
        stats_cache = _load_stats_cache()
        player_name_normalized = player_name.lower().strip()
        
        if player_name_normalized in stats_cache:
            player_stats = stats_cache[player_name_normalized]
            
            # Use cached stats if fresh (<24 hours old)
            if _is_stats_cache_fresh(player_stats, max_age_hours=24):
                logger.info(f"[Databallr] Using cached stats for {player_name} (cached {player_stats.get('game_count', 0)} games)")
                
                # Convert cached game log back to GameLogEntry objects
                try:
                    game_log_data = player_stats.get('game_log', [])
                    game_log = []
                    
                    for game_dict in game_log_data[:last_n_games]:
                        # Convert dict back to GameLogEntry
                        game_entry = GameLogEntry(**game_dict)
                        game_log.append(game_entry)
                    
                    logger.info(f"✓ [Databallr] Retrieved {len(game_log)} games from cache for {player_name}")
                    return game_log
                except Exception as e:
                    logger.warning(f"[Databallr] Failed to load from stats cache: {e}, falling back to live fetch")
            else:
                logger.info(f"[Databallr] Stats cache expired for {player_name}, fetching fresh data")
    
    # Player IS in cache - proceed with fetching (can retry on network errors)
    p = None
    browser = None
    
    for attempt in range(retries):
        try:
            logger.info(f"[Databallr] Launching browser (headless={headless})...")
            p, browser, context = launch_databallr_browser(headless)
            page = context.new_page()
            logger.info(f"[Databallr] Looking up player from cache...")
            player_url = search_player_databallr(page, player_name)
            if not player_url:
                logger.warning(f"[Databallr] Could not load player page: {player_name}")
                browser.close()
                p.stop()
                
                # Retry only if it was a network/page load issue (player is in cache)
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                continue
            raw_games = scrape_player_game_log_databallr(page, player_url, last_n_games)
            browser.close()
            p.stop()
            if not raw_games:
                logger.warning(f"[Databallr] No games found for {player_name}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                continue
            game_log = [map_to_game_log_entry(game, player_name) for game in raw_games]
            logger.info(f"✓ [Databallr] Retrieved {len(game_log)} games for {player_name}")
            return game_log
        except Exception as e:
            logger.error(f"[Databallr] Attempt {attempt + 1} failed for {player_name}: {e}")
            if browser:
                try:
                    browser.close()
                except:
                    pass
            if p:
                try:
                    p.stop()
                except:
                    pass
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    logger.error(f"[Databallr] All attempts failed for {player_name}")
    return []
