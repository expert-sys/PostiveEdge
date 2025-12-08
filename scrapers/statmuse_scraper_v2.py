"""
StatMuse Scraper V2 - Robust Edition
=====================================
Enhanced with retry logic, better error handling, and anti-timeout measures.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import time
from typing import List, Optional
from dataclasses import dataclass, asdict
from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("statmuse_scraper_v2")


@dataclass
class TeamStats:
    """Team statistics from StatMuse"""
    team_name: str
    season: str
    games_played: int = 0
    points: float = 0.0
    rebounds: float = 0.0
    assists: float = 0.0
    steals: float = 0.0
    blocks: float = 0.0
    turnovers: float = 0.0
    fg_pct: float = 0.0
    three_pct: float = 0.0
    ft_pct: float = 0.0
    # Rankings
    points_rank: Optional[str] = None
    rebounds_rank: Optional[str] = None
    assists_rank: Optional[str] = None
    # Opponent stats
    opp_points: float = 0.0
    opp_rebounds: float = 0.0
    opp_assists: float = 0.0
    # Net stats
    net_points: float = 0.0
    net_rebounds: float = 0.0
    net_assists: float = 0.0

    def to_dict(self):
        return asdict(self)


@dataclass
class PlayerStats:
    """Individual player statistics from StatMuse"""
    player_name: str
    team: str
    season: str
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


@dataclass
class TeamSplitStats:
    """Team performance splits (Home/Road, Wins/Losses, etc.)"""
    team_name: str
    season: str
    split_type: str  # "Home", "Road", "Wins", "Losses", "Eastern", "Western", etc.
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    points: float = 0.0
    rebounds: float = 0.0
    assists: float = 0.0
    fg_pct: float = 0.0
    three_pct: float = 0.0
    ft_pct: float = 0.0

    def to_dict(self):
        return asdict(self)


def robust_page_load(page: Page, url: str, max_retries: int = 3) -> bool:
    """
    Robustly load a page with retries and multiple strategies.

    Args:
        page: Playwright page object
        url: URL to load
        max_retries: Maximum number of retry attempts

    Returns:
        True if successful, False otherwise
    """
    strategies = [
        {"wait_until": "load", "timeout": 60000},
        {"wait_until": "domcontentloaded", "timeout": 45000},
        {"wait_until": "commit", "timeout": 30000}
    ]

    for attempt in range(max_retries):
        for strategy_idx, strategy in enumerate(strategies):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries}, Strategy {strategy_idx + 1}: {strategy['wait_until']}")
                page.goto(url, **strategy)

                # Wait for table to appear
                page.wait_for_selector('table', timeout=10000)
                time.sleep(1)

                logger.info(f"Successfully loaded page with strategy: {strategy['wait_until']}")
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


def scrape_team_stats(team_slug: str, season: str = "2025-26", headless: bool = True) -> Optional[TeamStats]:
    """
    Scrape team statistics from StatMuse (robust version).

    Args:
        team_slug: Team slug (e.g., "los-angeles-lakers")
        season: Season string (e.g., "2025-26")
        headless: Run browser in headless mode

    Returns:
        TeamStats object or None if scraping failed
    """
    url = f"https://www.statmuse.com/nba/team/{season}-{team_slug}-13/stats/2026"
    logger.info(f"Scraping team stats: {team_slug} ({season})")
    logger.info(f"URL: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage'
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br'
                }
            )
            page = context.new_page()

            # Robust page load
            if not robust_page_load(page, url):
                browser.close()
                return None

            # Get page content
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Extract team name
            team_name = team_slug.replace("-", " ").title()

            # Initialize team stats
            team_stats = TeamStats(team_name=team_name, season=season)

            # Find the stats table
            tables = soup.find_all('table')

            if not tables:
                logger.warning("No tables found on page")
                browser.close()
                return None

            # Look for team stats table (first table usually)
            team_table = tables[0]

            # Extract headers
            headers = []
            header_row = team_table.find('thead')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
                logger.debug(f"Found headers: {headers[:5]}...")

            # Extract team row data
            tbody = team_table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')

                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 5:
                        continue

                    # Extract stats from cells
                    try:
                        idx = 0
                        for i, header in enumerate(headers):
                            if i >= len(cells):
                                break

                            value = cells[i].get_text(strip=True)

                            # Parse numeric values
                            try:
                                if header == 'GP' or header == 'G':
                                    team_stats.games_played = int(value)
                                elif header == 'PTS':
                                    team_stats.points = float(value)
                                elif header == 'REB' or header == 'TRB':
                                    team_stats.rebounds = float(value)
                                elif header == 'AST':
                                    team_stats.assists = float(value)
                                elif header == 'STL':
                                    team_stats.steals = float(value)
                                elif header == 'BLK':
                                    team_stats.blocks = float(value)
                                elif header == 'TOV':
                                    team_stats.turnovers = float(value)
                                elif header == 'FG%':
                                    team_stats.fg_pct = float(value)
                                elif header == '3P%':
                                    team_stats.three_pct = float(value)
                                elif header == 'FT%':
                                    team_stats.ft_pct = float(value)
                            except (ValueError, AttributeError):
                                continue

                        break  # Only process first data row

                    except Exception as e:
                        logger.error(f"Error parsing row: {e}")
                        continue

            browser.close()

            logger.info(f"Successfully scraped: {team_stats.games_played} GP, {team_stats.points} PPG")
            return team_stats

    except Exception as e:
        logger.error(f"Error scraping team stats: {e}")
        return None


def scrape_player_stats(team_slug: str, season: str = "2025-26", headless: bool = True) -> List[PlayerStats]:
    """
    Scrape player statistics for a team from StatMuse (robust version).
    """
    url = f"https://www.statmuse.com/nba/team/{season}-{team_slug}-13/stats/2026"
    logger.info(f"Scraping player stats: {team_slug} ({season})")

    players = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()

            # Robust page load
            if not robust_page_load(page, url):
                browser.close()
                return players

            # Scroll to load all content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            team_name = team_slug.replace("-", " ").title()

            # Find player tables (usually second table onward)
            tables = soup.find_all('table')

            if len(tables) > 1:
                player_table = tables[1]  # Second table is usually players

                # Extract headers
                headers = []
                header_row = player_table.find('thead')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all('th')]

                # Extract player rows
                tbody = player_table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    logger.info(f"Found {len(rows)} player rows")

                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) < 3:
                            continue

                        # Extract player name (check first or second cell)
                        player_name = None
                        if cells[0].get_text(strip=True):
                            player_name = cells[0].get_text(strip=True)
                        elif len(cells) > 1 and cells[1].get_text(strip=True):
                            player_name = cells[1].get_text(strip=True)

                        # Also check for links
                        if not player_name:
                            for cell in cells[:2]:
                                link = cell.find('a')
                                if link:
                                    name = link.get_text(strip=True)
                                    if name and len(name) > 2:
                                        player_name = name
                                        break

                        if not player_name:
                            continue

                        # Initialize player stats
                        player = PlayerStats(
                            player_name=player_name,
                            team=team_name,
                            season=season
                        )

                        # Extract stats from cells
                        try:
                            for i, header in enumerate(headers):
                                if i >= len(cells):
                                    break

                                value = cells[i].get_text(strip=True)

                                try:
                                    if header == 'GP' or header == 'G':
                                        player.games_played = int(value)
                                    elif header == 'MIN' or header == 'MP':
                                        player.minutes = float(value)
                                    elif header == 'PTS':
                                        player.points = float(value)
                                    elif header == 'REB' or header == 'TRB':
                                        player.rebounds = float(value)
                                    elif header == 'AST':
                                        player.assists = float(value)
                                    elif header == 'STL':
                                        player.steals = float(value)
                                    elif header == 'BLK':
                                        player.blocks = float(value)
                                    elif header == 'TOV':
                                        player.turnovers = float(value)
                                    elif header == 'FG%':
                                        player.fg_pct = float(value)
                                    elif header == '3P%':
                                        player.three_pct = float(value)
                                    elif header == 'FT%':
                                        player.ft_pct = float(value)
                                except (ValueError, AttributeError):
                                    continue

                        except Exception as e:
                            logger.warning(f"Error parsing player row: {e}")

                        players.append(player)

            browser.close()
            logger.info(f"Successfully scraped {len(players)} players")
            return players

    except Exception as e:
        logger.error(f"Error scraping player stats: {e}")
        return players


def scrape_team_splits(team_slug: str, season: str = "2025-26", headless: bool = True) -> List[TeamSplitStats]:
    """
    Scrape team split statistics from StatMuse (robust version).
    """
    url = f"https://www.statmuse.com/nba/team/{team_slug}-13/splits/2026"
    logger.info(f"Scraping team splits: {team_slug} ({season})")
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
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()

            # Robust page load
            if not robust_page_load(page, url):
                browser.close()
                return splits

            # Scroll to load all splits
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            team_name = team_slug.replace("-", " ").title()

            # Find split tables
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables on splits page")

            for table in tables:
                # Extract headers
                headers = []
                header_row = table.find('thead')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all('th')]

                # Extract split rows
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')

                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) < 3:
                            continue

                        # First cell is split type
                        split_type = cells[0].get_text(strip=True)

                        if not split_type:
                            continue

                        # Initialize split stats
                        split = TeamSplitStats(
                            team_name=team_name,
                            season=season,
                            split_type=split_type
                        )

                        # Extract stats
                        try:
                            for i, header in enumerate(headers):
                                if i >= len(cells):
                                    break

                                value = cells[i].get_text(strip=True)

                                try:
                                    if header == 'GP' or header == 'G':
                                        split.games_played = int(value)
                                    elif header == 'W':
                                        split.wins = int(value)
                                    elif header == 'L':
                                        split.losses = int(value)
                                    elif header == 'PTS':
                                        split.points = float(value)
                                    elif header == 'REB' or header == 'TRB':
                                        split.rebounds = float(value)
                                    elif header == 'AST':
                                        split.assists = float(value)
                                    elif header == 'FG%':
                                        split.fg_pct = float(value)
                                    elif header == '3P%':
                                        split.three_pct = float(value)
                                    elif header == 'FT%':
                                        split.ft_pct = float(value)
                                except (ValueError, AttributeError):
                                    continue

                        except Exception as e:
                            logger.warning(f"Error parsing split row: {e}")

                        splits.append(split)

            browser.close()
            logger.info(f"Successfully scraped {len(splits)} splits")
            return splits

    except Exception as e:
        logger.error(f"Error scraping team splits: {e}")
        return splits


if __name__ == "__main__":
    # Test scraper
    print("=" * 80)
    print("TESTING STATMUSE SCRAPER V2 (ROBUST)")
    print("=" * 80)
    print()

    # Test with Lakers
    print("Testing with Los Angeles Lakers...")
    print()

    # Test team stats
    print("[1/3] Team Stats...")
    team_stats = scrape_team_stats("los-angeles-lakers", "2025-26", headless=True)
    if team_stats:
        print(f"  OK {team_stats.games_played} GP, {team_stats.points} PPG, {team_stats.rebounds} RPG")
    else:
        print(f"  FAILED")

    # Test player stats
    print()
    print("[2/3] Player Stats...")
    players = scrape_player_stats("los-angeles-lakers", "2025-26", headless=True)
    if players:
        print(f"  OK {len(players)} players found")
        for player in players[:3]:
            print(f"    - {player.player_name}: {player.points} PPG")
    else:
        print(f"  FAILED")

    # Test splits
    print()
    print("[3/3] Team Splits...")
    splits = scrape_team_splits("los-angeles-lakers", "2025-26", headless=True)
    if splits:
        print(f"  OK {len(splits)} splits found")
        for split in splits[:5]:
            print(f"    - {split.split_type}: {split.games_played} GP, {split.points} PPG")
    else:
        print(f"  FAILED")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
