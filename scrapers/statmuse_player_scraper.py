"""
StatMuse Player Scraper
========================
Scrapes individual player data from StatMuse including:
- Player profiles (bio + season averages)
- Game logs (game-by-game performance)
- Player splits (home/road, wins/losses, rest days, monthly, vs opponents)

This scraper is designed to be the PRIMARY source for player data in the hybrid pipeline,
with Databallr as a supplementary source for unique metrics.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import time
import json
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict
from datetime import datetime
from playwright.sync_api import sync_playwright, Page

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("statmuse_player_scraper")

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "statmuse_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PlayerProfile:
    """Player biographical info and season averages"""
    player_name: str
    team: str
    season: str
    position: str = ""
    height: str = ""
    weight: str = ""
    age: int = 0
    experience: int = 0
    # Season averages
    games_played: int = 0
    games_started: int = 0
    minutes: float = 0.0
    points: float = 0.0
    rebounds: float = 0.0
    assists: float = 0.0
    steals: float = 0.0
    blocks: float = 0.0
    turnovers: float = 0.0
    fg_pct: float = 0.0
    fg_made: float = 0.0
    fg_attempted: float = 0.0
    three_pct: float = 0.0
    three_made: float = 0.0
    three_attempted: float = 0.0
    ft_pct: float = 0.0
    ft_made: float = 0.0
    ft_attempted: float = 0.0
    
    def to_dict(self):
        return asdict(self)


@dataclass
class PlayerGameLog:
    """Single game performance"""
    player_name: str
    date: str
    opponent: str
    home_away: str  # "HOME" or "AWAY"
    win_loss: str   # "W" or "L"
    minutes: float = 0.0
    points: int = 0
    rebounds: int = 0
    assists: int = 0
    steals: int = 0
    blocks: int = 0
    turnovers: int = 0
    fouls: int = 0
    fg_made: int = 0
    fg_attempted: int = 0
    fg_pct: float = 0.0
    three_made: int = 0
    three_attempted: int = 0
    three_pct: float = 0.0
    ft_made: int = 0
    ft_attempted: int = 0
    ft_pct: float = 0.0
    plus_minus: int = 0
    
    def to_dict(self):
        return asdict(self)


@dataclass
class PlayerSplitStats:
    """Player performance in specific context (home/road, wins/losses, etc.)"""
    player_name: str
    season: str
    split_type: str  # "Home", "Road", "Wins", "Losses", "0 Days Rest", "December", etc.
    games_played: int = 0
    minutes: float = 0.0
    points: float = 0.0
    rebounds: float = 0.0
    assists: float = 0.0
    steals: float = 0.0
    blocks: float = 0.0
    turnovers: float = 0.0
    fg_pct: float = 0.0
    three_pct: float = 0.0
    ft_pct: float = 0.0
    
    def to_dict(self):
        return asdict(self)


def _player_name_to_slug(player_name: str) -> str:
    """Convert player name to URL slug (e.g., 'LeBron James' -> 'lebron-james')"""
    return player_name.lower().replace(" ", "-").replace("'", "")


def _parse_float(text: str) -> float:
    """Parse float from text, handling % and other characters"""
    try:
        return float(text.strip().replace("%", "").replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def _parse_int(text: str) -> int:
    """Parse int from text"""
    try:
        return int(text.strip().replace(",", ""))
    except (ValueError, AttributeError):
        return 0


def robust_page_load(page: Page, url: str, max_retries: int = 3) -> bool:
    """
    Robustly load a page with retries and multiple strategies.
    Copied from statmuse_scraper_v2.py for consistency.
    """
    strategies = [
        {"wait_until": "load", "timeout": 60000},
        {"wait_until": "domcontentloaded", "timeout": 45000},
        {"wait_until": "commit", "timeout": 30000}
    ]

    for attempt in range(max_retries):
        for strategy_idx, strategy in enumerate(strategies):
            try:
                logger.info(f"Loading page (attempt {attempt + 1}/{max_retries}, strategy {strategy_idx + 1})")
                page.goto(url, **strategy)
                
                # Wait for content to appear
                page.wait_for_selector('table, .player-card, .stats-table', timeout=10000)
                time.sleep(1)
                
                logger.info(f"Successfully loaded page")
                return True
                
            except Exception as e:
                logger.warning(f"Strategy {strategy_idx + 1} failed: {e}")
                if strategy_idx < len(strategies) - 1:
                    continue
        
        # Wait before retry
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 3
            logger.info(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    logger.error(f"All attempts failed to load: {url}")
    return False


def scrape_player_profile(
    player_name: str,
    season: str = "2024-25",
    headless: bool = True
) -> Optional[PlayerProfile]:
    """
    Scrape player profile (bio + season averages) from StatMuse.
    
    Args:
        player_name: Player's full name (e.g., "Nikola Jokic")
        season: Season string (e.g., "2024-25")
        headless: Run browser in headless mode
    
    Returns:
        PlayerProfile object or None if scraping failed
        
    Example:
        profile = scrape_player_profile("Nikola Jokic", "2024-25")
        print(f"{profile.player_name}: {profile.points} PPG, {profile.rebounds} RPG")
    """
    player_slug = _player_name_to_slug(player_name)
    
    # Try multiple URL patterns (StatMuse has different formats)
    urls_to_try = [
        f"https://www.statmuse.com/nba/ask/{player_slug}-stats-{season}",
        f"https://www.statmuse.com/nba/ask/{player_slug}-{season}",
        f"https://www.statmuse.com/nba/player/{player_slug}"
    ]
    
    logger.info(f"Scraping profile for {player_name} ({season})")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            # Try each URL until one works
            loaded = False
            for url in urls_to_try:
                logger.info(f"Trying URL: {url}")
                if robust_page_load(page, url, max_retries=2):
                    loaded = True
                    break
            
            if not loaded:
                browser.close()
                return None
            
            # Scroll to load all content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
            html = page.content()
            browser.close()
            
            # Parse the HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Initialize profile
            profile = PlayerProfile(
                player_name=player_name,
                team="",
                season=season
            )
            
            # Extract bio info from text or headers
            # StatMuse structure varies, so we'll look for common patterns
            
            # Find team name (usually in title or near player name)
            title = soup.find('title')
            if title:
                title_text = title.get_text()
                # Pattern: "Player Name Stats | Team"
                if '|' in title_text:
                    parts = title_text.split('|')
                    if len(parts) > 1:
                        profile.team = parts[1].strip().replace(' Stats', '')
            
            # Find stats table
            tables = soup.find_all('table')
            
            for table in tables:
                headers = []
                header_row = table.find('thead')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
                
                # Look for season average row
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    
                    # Process first data row (usually season average)
                    if rows:
                        cells = rows[0].find_all('td')
                        
                        if len(cells) >= 3:
                            # Map headers to values
                            # Temp vars for totals
                            total_points = 0.0
                            total_rebounds = 0.0
                            total_assists = 0.0
                            
                            # Map headers to values
                            for i, header in enumerate(headers):
                                if i >= len(cells):
                                    break
                                
                                value = cells[i].get_text(strip=True)
                                
                                # Parse based on header
                                try:
                                    if header in ['GP', 'G', 'Games']:
                                        profile.games_played = _parse_int(value)
                                    elif header in ['GS', 'Started']:
                                        profile.games_started = _parse_int(value)
                                    elif header in ['MIN', 'MPG', 'MP']:
                                        # MIN is usually MPG, MP is sometimes Total Minutes
                                        val = _parse_float(value)
                                        if header == 'MP' and val > 60: # Likely total minutes
                                            pass # Ignore total minutes for now or divide later if needed
                                        else:
                                            profile.minutes = val
                                    elif header == 'PPG':
                                        profile.points = _parse_float(value)
                                    elif header == 'PTS': # Usually total points if PPG exists, or could be PPG
                                        # If value is > 50, it's definitely total
                                        val = _parse_float(value)
                                        if val > 60:
                                            total_points = val
                                        else:
                                            # Could be PPG (e.g. 30.5)
                                            # We generally prefer 'PPG' header if it exists
                                            if profile.points == 0:
                                                 profile.points = val
                                    elif header in ['RPG', 'TRB']: # TRB can be total
                                        profile.rebounds = _parse_float(value)
                                    elif header == 'REB':
                                        val = _parse_float(value)
                                        if val > 30: # Likely total
                                            total_rebounds = val
                                        else:
                                            if profile.rebounds == 0:
                                                profile.rebounds = val
                                    elif header == 'APG':
                                        profile.assists = _parse_float(value)
                                    elif header == 'AST':
                                        val = _parse_float(value)
                                        if val > 20: # Likely total
                                            total_assists = val
                                        else:
                                            if profile.assists == 0:
                                                profile.assists = val
                                    elif header in ['STL', 'SPG']:
                                        profile.steals = _parse_float(value)
                                    elif header in ['BLK', 'BPG']:
                                        profile.blocks = _parse_float(value)
                                    elif header in ['TOV', 'TOPG']:
                                        profile.turnovers = _parse_float(value)
                                    elif header in ['FG%']:
                                        profile.fg_pct = _parse_float(value)
                                    elif header in ['FGM']:
                                        profile.fg_made = _parse_float(value)
                                    elif header in ['FGA']:
                                        profile.fg_attempted = _parse_float(value)
                                    elif header in ['3P%']:
                                        profile.three_pct = _parse_float(value)
                                    elif header in ['3PM']:
                                        profile.three_made = _parse_float(value)
                                    elif header in ['3PA']:
                                        profile.three_attempted = _parse_float(value)
                                    elif header in ['FT%']:
                                        profile.ft_pct = _parse_float(value)
                                    elif header in ['FTM']:
                                        profile.ft_made = _parse_float(value)
                                    elif header in ['FTA']:
                                        profile.ft_attempted = _parse_float(value)
                                except Exception as e:
                                    logger.debug(f"Error parsing {header}: {e}")
                                    continue
                            
                            # Post-processing: Calculate averages from totals if needed
                            if profile.games_played > 0:
                                if profile.points == 0 and total_points > 0:
                                    profile.points = round(total_points / profile.games_played, 1)
                                if profile.rebounds == 0 and total_rebounds > 0:
                                    profile.rebounds = round(total_rebounds / profile.games_played, 1)
                                if profile.assists == 0 and total_assists > 0:
                                    profile.assists = round(total_assists / profile.games_played, 1)
                            
                            # If we found stats, we can stop
                            if profile.games_played > 0:
                                break
            
            if profile.games_played == 0:
                logger.warning(f"No stats found for {player_name}")
                return None
            
            logger.info(f"Successfully scraped: {profile.games_played} GP, {profile.points} PPG")
            return profile
            
    except Exception as e:
        logger.error(f"Error scraping player profile: {e}")
        return None


def scrape_player_splits(
    player_name: str,
    season: str = "2024-25",
    headless: bool = True
) -> List[PlayerSplitStats]:
    """
    Scrape player splits from StatMuse.
    
    Returns splits for:
    - Home vs Road
    - Wins vs Losses  
    - Days of rest (0, 1, 2+ days)
    - Monthly performance
    - Vs specific opponents/conferences
    
    Args:
        player_name: Player's full name
        season: Season string
        headless: Run browser in headless mode
    
    Returns:
        List of PlayerSplitStats objects
    """
    player_slug = _player_name_to_slug(player_name)
    url = f"https://www.statmuse.com/nba/ask/{player_slug}-splits-{season}"
    
    logger.info(f"Scraping splits for {player_name} ({season})")
    logger.info(f"URL: {url}")
    
    splits = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            if not robust_page_load(page, url):
                browser.close()
                return splits
            
            # Scroll to load all splits
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            html = page.content()
            browser.close()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all tables
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables")
            
            for table in tables:
                headers = []
                header_row = table.find('thead')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
                
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) < 3:
                            continue
                        
                        # First cell is split type
                        split_type = cells[0].get_text(strip=True)
                        
                        if not split_type or split_type in ['Total', 'Overall', 'Season']:
                            continue
                        
                        # Initialize split
                        split = PlayerSplitStats(
                            player_name=player_name,
                            season=season,
                            split_type=split_type
                        )
                        
                        # Extract stats from cells
                        try:
                            for i, header in enumerate(headers):
                                if i >= len(cells):
                                    break
                                
                                value = cells[i].get_text(strip=True)
                                
                                try:
                                    if header in ['GP', 'G']:
                                        split.games_played = _parse_int(value)
                                    elif header in ['MIN', 'MPG']:
                                        split.minutes = _parse_float(value)
                                    elif header in ['PTS', 'PPG']:
                                        split.points = _parse_float(value)
                                    elif header in ['REB', 'RPG', 'TRB']:
                                        split.rebounds = _parse_float(value)
                                    elif header in ['AST', 'APG']:
                                        split.assists = _parse_float(value)
                                    elif header in ['STL', 'SPG']:
                                        split.steals = _parse_float(value)
                                    elif header in ['BLK', 'BPG']:
                                        split.blocks = _parse_float(value)
                                    elif header in ['TOV', 'TOPG']:
                                        split.turnovers = _parse_float(value)
                                    elif header in ['FG%']:
                                        split.fg_pct = _parse_float(value)
                                    elif header in ['3P%']:
                                        split.three_pct = _parse_float(value)
                                    elif header in ['FT%']:
                                        split.ft_pct = _parse_float(value)
                                except Exception as e:
                                    logger.debug(f"Error parsing {header}: {e}")
                                    continue
                        
                        except Exception as e:
                            logger.warning(f"Error parsing split row: {e}")
                            continue
                        
                        splits.append(split)
            
            logger.info(f"Successfully scraped {len(splits)} splits")
            return splits
            
    except Exception as e:
        logger.error(f"Error scraping player splits: {e}")
        return splits



def scrape_player_game_log(
    player_name: str,
    season: str = "2024-25",
    headless: bool = True
) -> List[PlayerGameLog]:
    """
    Scrape player game log from StatMuse.
    
    Args:
        player_name: Player's full name
        season: Season string
        headless: Run browser in headless mode
    
    Returns:
        List of PlayerGameLog objects (most recent first)
    """
    player_slug = _player_name_to_slug(player_name)
    url = f"https://www.statmuse.com/nba/ask/{player_slug}-game-log-{season}"
    
    logger.info(f"Scraping game log for {player_name} ({season})")
    logger.info(f"URL: {url}")
    
    logs = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            if not robust_page_load(page, url):
                browser.close()
                return logs
            
            # Scroll to load all games
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            html = page.content()
            browser.close()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all tables
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables")
            
            for table in tables:
                headers = []
                header_row = table.find('thead')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
                
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) < 5: # Need basic info
                            continue
                        
                        # First cell is usually DATE (or NAME in some views, but game log starts with DATE)
                        date_str = cells[0].get_text(strip=True)
                        
                        # Skip header rows embedded in body or invalid rows
                        if not date_str or date_str == 'DATE' or 'Season' in date_str:
                            continue
                            
                        # Initialize log
                        log = PlayerGameLog(
                            player_name=player_name,
                            date=date_str,
                            opponent="",
                            home_away="",
                            win_loss=""
                        )
                        
                        # Extract stats from cells
                        try:
                            for i, header in enumerate(headers):
                                if i >= len(cells):
                                    break
                                
                                value = cells[i].get_text(strip=True)
                                
                                try:
                                    if header == 'OPP' or header == 'Opp':
                                        log.opponent = value
                                        if 'vs' in value:
                                            log.home_away = "HOME"
                                        elif '@' in value:
                                            log.home_away = "AWAY"
                                    elif header == 'W/L':
                                        log.win_loss = value
                                    elif header in ['MIN', 'MP']:
                                        log.minutes = _parse_float(value)
                                    elif header in ['PTS', 'TM']: # TM sometimes used for points? Unlikely but check
                                        log.points = _parse_int(value)
                                    elif header in ['REB', 'TRB']:
                                        log.rebounds = _parse_int(value)
                                    elif header in ['AST']:
                                        log.assists = _parse_int(value)
                                    elif header in ['STL']:
                                        log.steals = _parse_int(value)
                                    elif header in ['BLK']:
                                        log.blocks = _parse_int(value)
                                    elif header in ['TOV']:
                                        log.turnovers = _parse_int(value)
                                    elif header in ['PF']:
                                        log.fouls = _parse_int(value)
                                    elif header in ['FGM']:
                                        log.fg_made = _parse_int(value)
                                    elif header in ['FGA']:
                                        log.fg_attempted = _parse_int(value)
                                    elif header in ['FG%']:
                                        log.fg_pct = _parse_float(value)
                                    elif header in ['3PM']:
                                        log.three_made = _parse_int(value)
                                    elif header in ['3PA']:
                                        log.three_attempted = _parse_int(value)
                                    elif header in ['3P%']:
                                        log.three_pct = _parse_float(value)
                                    elif header in ['FTM']:
                                        log.ft_made = _parse_int(value)
                                    elif header in ['FTA']:
                                        log.ft_attempted = _parse_int(value)
                                    elif header in ['FT%']:
                                        log.ft_pct = _parse_float(value)
                                    elif header in ['+/-']:
                                        log.plus_minus = _parse_int(value)
                                except Exception as e:
                                    # logger.debug(f"Error parsing {header}: {e}")
                                    continue
                        
                        except Exception as e:
                            logger.warning(f"Error parsing game log row: {e}")
                            continue
                        
                        logs.append(log)
            
            logger.info(f"Successfully scraped {len(logs)} games")
            return logs
            
    except Exception as e:
        logger.error(f"Error scraping player game log: {e}")
        return logs


# Export main classes and functions
__all__ = [
    'PlayerProfile',
    'PlayerGameLog', 
    'PlayerSplitStats',
    'scrape_player_profile',
    'scrape_player_splits',
    'scrape_player_game_log'
]


if __name__ == "__main__":
    # Test scraper
    print("=" * 80)
    print("TESTING STATMUSE PLAYER SCRAPER")
    print("=" * 80)
    print()
    
    # Test with Nikola Jokic
    test_player = "Nikola Jokic"
    test_season = "2024-25"
    
    print(f"Testing with {test_player} ({test_season})...")
    print()
    
    # Test profile scraping
    print("[1/2] Player Profile...")
    profile = scrape_player_profile(test_player, test_season, headless=True)
    if profile:
        print(f"  ✓ {profile.player_name} ({profile.team})")
        print(f"    {profile.games_played} GP | {profile.points} PPG | {profile.rebounds} RPG | {profile.assists} APG")
        print(f"    {profile.fg_pct}% FG | {profile.three_pct}% 3P | {profile.ft_pct}% FT")
    else:
        print("  ✗ FAILED")
    
    print()
    
    # Test splits scraping
    print("[2/2] Player Splits...")
    splits = scrape_player_splits(test_player, test_season, headless=True)
    if splits:
        print(f"  ✓ Found {len(splits)} splits:")
        for split in splits[:10]:  # Show first 10
            print(f"    - {split.split_type}: {split.games_played} GP, {split.points} PPG")
    else:
        print("  ✗ No splits found")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
