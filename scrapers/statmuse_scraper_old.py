"""
StatMuse NBA Data Scraper
=========================
Scrapes team and player statistics from StatMuse for betting analysis.

StatMuse provides clean, comprehensive NBA data including:
- Team regular season statistics
- Player per-game statistics
- Rankings and percentiles
- Offensive and defensive metrics

Usage:
    from scrapers.statmuse_scraper import scrape_team_stats, scrape_player_stats

    team_stats = scrape_team_stats("detroit-pistons", "2025-26")
    player_stats = scrape_player_stats("detroit-pistons", "2025-26")
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("statmuse_scraper")


@dataclass
class TeamStats:
    """Team statistics from StatMuse"""
    team_name: str
    season: str

    # Basic stats
    games_played: int = 0
    minutes: float = 0.0
    points: float = 0.0
    rebounds: float = 0.0
    assists: float = 0.0
    steals: float = 0.0
    blocks: float = 0.0

    # Shooting stats
    fgm: float = 0.0  # Field goals made
    fga: float = 0.0  # Field goals attempted
    fg_pct: float = 0.0  # Field goal percentage
    three_pm: float = 0.0  # 3-pointers made
    three_pa: float = 0.0  # 3-pointers attempted
    three_pct: float = 0.0  # 3-point percentage
    ftm: float = 0.0  # Free throws made
    fta: float = 0.0  # Free throws attempted
    ft_pct: float = 0.0  # Free throw percentage

    # Rankings
    points_rank: Optional[str] = None
    rebounds_rank: Optional[str] = None
    assists_rank: Optional[str] = None
    fg_pct_rank: Optional[str] = None
    three_pct_rank: Optional[str] = None

    # Opponent stats
    opp_points: float = 0.0
    opp_rebounds: float = 0.0
    opp_assists: float = 0.0
    opp_fg_pct: float = 0.0

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

    # Basic info
    games_played: int = 0
    games_started: int = 0
    minutes: float = 0.0

    # Scoring
    points: float = 0.0
    fgm: float = 0.0
    fga: float = 0.0
    fg_pct: float = 0.0
    three_pm: float = 0.0
    three_pa: float = 0.0
    three_pct: float = 0.0
    ftm: float = 0.0
    fta: float = 0.0
    ft_pct: float = 0.0

    # Other stats
    rebounds: float = 0.0
    assists: float = 0.0
    steals: float = 0.0
    blocks: float = 0.0
    turnovers: float = 0.0
    fouls: float = 0.0

    def to_dict(self):
        return asdict(self)


@dataclass
class TeamSplitStats:
    """Team performance splits from StatMuse (Home/Road, Wins/Losses, etc.)"""
    team_name: str
    season: str
    split_type: str  # "Home", "Road", "Wins", "Losses", "vs Eastern", etc.

    # Basic stats
    games_played: int = 0
    points: float = 0.0
    rebounds: float = 0.0
    assists: float = 0.0

    # Shooting stats
    fgm: float = 0.0
    fga: float = 0.0
    fg_pct: float = 0.0
    three_pm: float = 0.0
    three_pa: float = 0.0
    three_pct: float = 0.0
    ftm: float = 0.0
    fta: float = 0.0
    ft_pct: float = 0.0

    # Other stats
    steals: float = 0.0
    blocks: float = 0.0
    turnovers: float = 0.0
    fouls: float = 0.0

    def to_dict(self):
        return asdict(self)


def scrape_team_stats(team_slug: str, season: str = "2025-26", headless: bool = True) -> Optional[TeamStats]:
    """
    Scrape team statistics from StatMuse.

    Args:
        team_slug: Team URL slug (e.g., "detroit-pistons")
        season: Season string (e.g., "2025-26")
        headless: Run browser in headless mode

    Returns:
        TeamStats object or None if failed

    Example:
        stats = scrape_team_stats("detroit-pistons", "2025-26")
    """

    # Construct URL
    url = f"https://www.statmuse.com/nba/team/{season}-{team_slug}-13/stats/2026"

    logger.info(f"Scraping team stats: {team_slug} ({season})")
    logger.info(f"URL: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        try:
            # Load page
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Get page content
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Extract team name
            team_name = team_slug.replace("-", " ").title()

            # Initialize team stats
            team_stats = TeamStats(team_name=team_name, season=season)

            # Find the stats table
            # StatMuse uses a table structure - look for "Team Regular Season" section
            tables = soup.find_all('table')

            if not tables:
                logger.warning("No tables found on page")
                return None

            # Look for team stats table (first table usually)
            team_table = tables[0]

            # Extract headers
            headers = []
            header_row = team_table.find('thead')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
                logger.info(f"Found headers: {headers}")

            # Extract team row data
            tbody = team_table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')

                for row in rows:
                    cells = row.find_all('td')
                    if not cells:
                        continue

                    row_label = cells[0].get_text(strip=True)

                    if 'Team' in row_label:
                        # Main team stats row
                        values = [cell.get_text(strip=True) for cell in cells[1:]]

                        # Map values to stats based on headers
                        for i, header in enumerate(headers[1:]):  # Skip first column (label)
                            if i >= len(values):
                                break

                            value = values[i]

                            try:
                                # Convert to appropriate type
                                if header == 'GP':
                                    team_stats.games_played = int(value)
                                elif header == 'MIN':
                                    team_stats.minutes = float(value)
                                elif header == 'PTS':
                                    team_stats.points = float(value)
                                elif header == 'REB':
                                    team_stats.rebounds = float(value)
                                elif header == 'AST':
                                    team_stats.assists = float(value)
                                elif header == 'STL':
                                    team_stats.steals = float(value)
                                elif header == 'BLK':
                                    team_stats.blocks = float(value)
                                elif header == 'FGM':
                                    team_stats.fgm = float(value)
                                elif header == 'FGA':
                                    team_stats.fga = float(value)
                                elif header == 'FG%':
                                    team_stats.fg_pct = float(value)
                                elif header == '3PM':
                                    team_stats.three_pm = float(value)
                                elif header == '3PA':
                                    team_stats.three_pa = float(value)
                                elif header == '3P%':
                                    team_stats.three_pct = float(value)
                                elif header == 'FTM':
                                    team_stats.ftm = float(value)
                                elif header == 'FTA':
                                    team_stats.fta = float(value)
                                elif header == 'FT%' or header == 'FTM':
                                    team_stats.ft_pct = float(value)
                            except (ValueError, AttributeError) as e:
                                logger.debug(f"Could not parse {header}: {value} - {e}")
                                continue

                    elif 'Rank' in row_label:
                        # Rankings row
                        values = [cell.get_text(strip=True) for cell in cells[1:]]

                        for i, header in enumerate(headers[1:]):
                            if i >= len(values):
                                break

                            value = values[i]

                            if header == 'PTS':
                                team_stats.points_rank = value
                            elif header == 'REB':
                                team_stats.rebounds_rank = value
                            elif header == 'AST':
                                team_stats.assists_rank = value
                            elif header == 'FG%':
                                team_stats.fg_pct_rank = value
                            elif header == '3P%':
                                team_stats.three_pct_rank = value

                    elif 'Opponent' in row_label:
                        # Opponent stats row
                        values = [cell.get_text(strip=True) for cell in cells[1:]]

                        for i, header in enumerate(headers[1:]):
                            if i >= len(values):
                                break

                            value = values[i]

                            try:
                                if header == 'PTS':
                                    team_stats.opp_points = float(value)
                                elif header == 'REB':
                                    team_stats.opp_rebounds = float(value)
                                elif header == 'AST':
                                    team_stats.opp_assists = float(value)
                                elif header == 'FG%':
                                    team_stats.opp_fg_pct = float(value)
                            except (ValueError, AttributeError):
                                continue

                    elif 'Net' in row_label:
                        # Net stats row
                        values = [cell.get_text(strip=True) for cell in cells[1:]]

                        for i, header in enumerate(headers[1:]):
                            if i >= len(values):
                                break

                            value = values[i].replace('+', '')  # Remove + sign

                            try:
                                if header == 'PTS':
                                    team_stats.net_points = float(value)
                                elif header == 'REB':
                                    team_stats.net_rebounds = float(value)
                                elif header == 'AST':
                                    team_stats.net_assists = float(value)
                            except (ValueError, AttributeError):
                                continue

            logger.info(f"Successfully scraped team stats for {team_name}")
            logger.info(f"  Games: {team_stats.games_played}, PPG: {team_stats.points}, RPG: {team_stats.rebounds}, APG: {team_stats.assists}")

            return team_stats

        except Exception as e:
            logger.error(f"Error scraping team stats: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            browser.close()


def scrape_player_stats(team_slug: str, season: str = "2025-26", headless: bool = True) -> List[PlayerStats]:
    """
    Scrape player statistics for a team from StatMuse.

    Args:
        team_slug: Team URL slug (e.g., "detroit-pistons")
        season: Season string (e.g., "2025-26")
        headless: Run browser in headless mode

    Returns:
        List of PlayerStats objects

    Example:
        players = scrape_player_stats("detroit-pistons", "2025-26")
    """

    # Construct URL (same page has both team and player stats)
    url = f"https://www.statmuse.com/nba/team/{season}-{team_slug}-13/stats/2026"

    logger.info(f"Scraping player stats: {team_slug} ({season})")
    logger.info(f"URL: {url}")

    players = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        try:
            # Load page
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Scroll to load player stats
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

            # Get page content
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Find all tables (player stats are usually in the second table)
            tables = soup.find_all('table')

            if len(tables) < 2:
                logger.warning("Player stats table not found")
                return players

            # Player stats table (second table)
            player_table = tables[1] if len(tables) > 1 else tables[0]

            # Extract headers
            headers = []
            header_row = player_table.find('thead')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
                logger.info(f"Found player headers: {headers}")

            # Extract player rows
            tbody = player_table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')

                for row in rows:
                    cells = row.find_all('td')
                    if not cells or len(cells) < 3:
                        continue

                    # First cell might be empty (image), second cell has player name
                    # Try both first and second cell for player name
                    player_name = None

                    # Check first cell
                    if cells[0].get_text(strip=True):
                        player_name = cells[0].get_text(strip=True)
                    # Check second cell (common in StatMuse)
                    elif len(cells) > 1 and cells[1].get_text(strip=True):
                        player_name = cells[1].get_text(strip=True)

                    # Also check for links with player names
                    if not player_name:
                        for cell in cells[:2]:
                            link = cell.find('a')
                            if link:
                                name = link.get_text(strip=True)
                                if name and len(name) > 2:  # Valid name
                                    player_name = name
                                    break

                    if not player_name:
                        continue

                    # Initialize player stats
                    player = PlayerStats(
                        player_name=player_name,
                        team=team_slug.replace("-", " ").title(),
                        season=season
                    )

                    # Extract stats based on headers
                    values = [cell.get_text(strip=True) for cell in cells[1:]]

                    for i, header in enumerate(headers[1:]):  # Skip first column (player name)
                        if i >= len(values):
                            break

                        value = values[i]

                        try:
                            if header == 'GP':
                                player.games_played = int(value)
                            elif header == 'GS':
                                player.games_started = int(value)
                            elif header == 'MIN':
                                player.minutes = float(value)
                            elif header == 'PTS':
                                player.points = float(value)
                            elif header == 'REB':
                                player.rebounds = float(value)
                            elif header == 'AST':
                                player.assists = float(value)
                            elif header == 'STL':
                                player.steals = float(value)
                            elif header == 'BLK':
                                player.blocks = float(value)
                            elif header == 'FGM':
                                player.fgm = float(value)
                            elif header == 'FGA':
                                player.fga = float(value)
                            elif header == 'FG%':
                                player.fg_pct = float(value)
                            elif header == '3PM':
                                player.three_pm = float(value)
                            elif header == '3PA':
                                player.three_pa = float(value)
                            elif header == '3P%':
                                player.three_pct = float(value)
                            elif header == 'FTM':
                                player.ftm = float(value)
                            elif header == 'FTA':
                                player.fta = float(value)
                            elif header == 'FT%':
                                player.ft_pct = float(value)
                            elif header == 'TO' or header == 'TOV':
                                player.turnovers = float(value)
                            elif header == 'PF':
                                player.fouls = float(value)
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"Could not parse {header} for {player_name}: {value}")
                            continue

                    players.append(player)
                    logger.debug(f"Extracted stats for {player_name}: {player.points} PPG, {player.rebounds} RPG, {player.assists} APG")

            logger.info(f"Successfully scraped {len(players)} player stats")

            return players

        except Exception as e:
            logger.error(f"Error scraping player stats: {e}")
            import traceback
            traceback.print_exc()
            return players

        finally:
            browser.close()


def scrape_team_splits(team_slug: str, season: str = "2025-26", headless: bool = True) -> List[TeamSplitStats]:
    """
    Scrape team performance splits from StatMuse (Home/Road, Wins/Losses, Conference, etc.).

    Args:
        team_slug: Team URL slug (e.g., "detroit-pistons")
        season: Season string (e.g., "2025-26")
        headless: Run browser in headless mode

    Returns:
        List of TeamSplitStats objects for each split category

    Example:
        splits = scrape_team_splits("detroit-pistons", "2025-26")
        home_split = [s for s in splits if s.split_type == "Home"][0]
    """

    # Construct URL - note: splits URL uses different format
    url = f"https://www.statmuse.com/nba/team/{team_slug}-13/splits/2026"

    logger.info(f"Scraping team splits: {team_slug} ({season})")
    logger.info(f"URL: {url}")

    splits = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        try:
            # Load page
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Get HTML
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Find all tables
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables on splits page")

            for table_idx, table in enumerate(tables):
                # Get headers
                thead = table.find('thead')
                if not thead:
                    continue

                headers = [th.get_text(strip=True) for th in thead.find_all('th')]
                logger.debug(f"Table {table_idx + 1} headers: {headers}")

                # Get tbody
                tbody = table.find('tbody')
                if not tbody:
                    continue

                rows = tbody.find_all('tr')

                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue

                    # First cell is the split category (Home, Road, Wins, etc.)
                    split_type = cells[0].get_text(strip=True)

                    if not split_type:
                        continue

                    # Create split object
                    split = TeamSplitStats(
                        team_name=team_slug.replace('-', ' ').title(),
                        season=season,
                        split_type=split_type
                    )

                    # Extract stats from remaining cells
                    for i, header in enumerate(headers[1:], start=1):  # Skip first header (split type)
                        if i >= len(cells):
                            break

                        value = cells[i].get_text(strip=True)
                        if not value or value == '-':
                            continue

                        try:
                            # Map headers to attributes
                            if header == 'GP' or header == 'G':
                                split.games_played = int(value)
                            elif header == 'PTS':
                                split.points = float(value)
                            elif header == 'REB':
                                split.rebounds = float(value)
                            elif header == 'AST':
                                split.assists = float(value)
                            elif header == 'STL':
                                split.steals = float(value)
                            elif header == 'BLK':
                                split.blocks = float(value)
                            elif header == 'FGM':
                                split.fgm = float(value)
                            elif header == 'FGA':
                                split.fga = float(value)
                            elif header == 'FG%':
                                split.fg_pct = float(value)
                            elif header == '3PM':
                                split.three_pm = float(value)
                            elif header == '3PA':
                                split.three_pa = float(value)
                            elif header == '3P%':
                                split.three_pct = float(value)
                            elif header == 'FTM':
                                split.ftm = float(value)
                            elif header == 'FTA':
                                split.fta = float(value)
                            elif header == 'FT%':
                                split.ft_pct = float(value)
                            elif header == 'TO' or header == 'TOV':
                                split.turnovers = float(value)
                            elif header == 'PF':
                                split.fouls = float(value)
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"Could not parse {header} for {split_type}: {value}")
                            continue

                    splits.append(split)
                    logger.debug(f"Extracted split: {split_type} - {split.games_played} GP, {split.points} PPG")

            logger.info(f"Successfully scraped {len(splits)} team splits")

            return splits

        except Exception as e:
            logger.error(f"Error scraping team splits: {e}")
            import traceback
            traceback.print_exc()
            return splits

        finally:
            browser.close()


def scrape_team_complete(team_slug: str, season: str = "2025-26", headless: bool = True) -> Dict:
    """
    Scrape complete team and player statistics.

    Args:
        team_slug: Team URL slug (e.g., "detroit-pistons")
        season: Season string (e.g., "2025-26")
        headless: Run browser in headless mode

    Returns:
        Dictionary with team_stats and player_stats
    """

    logger.info(f"Scraping complete stats for {team_slug} ({season})")

    team_stats = scrape_team_stats(team_slug, season, headless)
    player_stats = scrape_player_stats(team_slug, season, headless)

    return {
        'team_stats': team_stats.to_dict() if team_stats else None,
        'player_stats': [p.to_dict() for p in player_stats],
        'season': season,
        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }


# Test function
if __name__ == "__main__":
    import sys

    # Test with Detroit Pistons
    team_slug = "detroit-pistons"
    season = "2025-26"

    print("=" * 80)
    print(f"TESTING STATMUSE SCRAPER: {team_slug}")
    print("=" * 80)
    print()

    # Test team stats
    print("Scraping team stats...")
    team_stats = scrape_team_stats(team_slug, season, headless=False)

    if team_stats:
        print("\nTeam Stats:")
        print(f"  Games: {team_stats.games_played}")
        print(f"  Points: {team_stats.points} (Rank: {team_stats.points_rank})")
        print(f"  Rebounds: {team_stats.rebounds} (Rank: {team_stats.rebounds_rank})")
        print(f"  Assists: {team_stats.assists} (Rank: {team_stats.assists_rank})")
        print(f"  FG%: {team_stats.fg_pct}% (Rank: {team_stats.fg_pct_rank})")
        print(f"  3P%: {team_stats.three_pct}% (Rank: {team_stats.three_pct_rank})")
        print(f"  Net Points: {team_stats.net_points:+.1f}")

    print("\n" + "-" * 80)
    print()

    # Test player stats
    print("Scraping player stats...")
    player_stats = scrape_player_stats(team_slug, season, headless=False)

    if player_stats:
        print(f"\nFound {len(player_stats)} players:")
        for player in player_stats[:5]:  # Show top 5
            print(f"  {player.player_name}: {player.points} PPG, {player.rebounds} RPG, {player.assists} APG")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
