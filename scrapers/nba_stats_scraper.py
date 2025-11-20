"""
NBA.com Stats Scraper
=====================
Scrapes historical player and team statistics from NBA.com/stats

Features:
- Player stats (points, rebounds, assists, etc.)
- Team stats (points for/against, pace, etc.)
- Historical game-by-game data
- Season averages and totals

Usage:
  from nba_stats_scraper import scrape_player_stats, scrape_team_stats
  player_data = scrape_player_stats("LeBron James", season="2024-25")
  team_data = scrape_team_stats("Lakers", season="2024-25")
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("nba_stats_scraper")


@dataclass
class PlayerGameStats:
    """Individual game statistics for a player"""
    game_date: str
    opponent: str
    home_away: str  # "HOME" or "AWAY"
    points: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    minutes: float
    fg_made: int
    fg_attempted: int
    three_pt_made: int
    three_pt_attempted: int
    ft_made: int
    ft_attempted: int
    game_id: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


@dataclass
class PlayerSeasonStats:
    """Season aggregate statistics for a player"""
    player_name: str
    team: str
    season: str
    games_played: int
    points_per_game: float
    rebounds_per_game: float
    assists_per_game: float
    steals_per_game: float
    blocks_per_game: float
    minutes_per_game: float
    fg_percentage: float
    three_pt_percentage: float
    ft_percentage: float
    game_log: List[PlayerGameStats]
    
    def to_dict(self):
        return {
            **{k: v for k, v in asdict(self).items() if k != 'game_log'},
            'game_log': [game.to_dict() for game in self.game_log]
        }


@dataclass
class TeamGameStats:
    """Individual game statistics for a team"""
    game_date: str
    opponent: str
    home_away: str
    points_for: int
    points_against: int
    total_points: int
    won: bool
    margin: int
    game_id: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


@dataclass
class TeamSeasonStats:
    """Season aggregate statistics for a team"""
    team_name: str
    season: str
    games_played: int
    wins: int
    losses: int
    points_per_game: float
    points_against_per_game: float
    pace: float
    offensive_rating: float
    defensive_rating: float
    game_log: List[TeamGameStats]
    
    def to_dict(self):
        return {
            **{k: v for k, v in asdict(self).items() if k != 'game_log'},
            'game_log': [game.to_dict() for game in self.game_log]
        }


def scrape_player_stats(
    player_name: str,
    season: str = "2024-25",
    headless: bool = True
) -> Optional[PlayerSeasonStats]:
    """
    Scrape player statistics from NBA.com
    
    Args:
        player_name: Full player name (e.g., "LeBron James")
        season: Season in format "YYYY-YY" (e.g., "2024-25")
        headless: Run browser in headless mode
    
    Returns:
        PlayerSeasonStats object or None if not found
    """
    logger.info(f"Scraping stats for {player_name} ({season})")
    
    # NBA.com player stats URL
    # Need to search for player first, then get their stats page
    search_url = f"https://www.nba.com/stats/players"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        try:
            # Navigate to players page
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            
            # Try to search for player
            search_input = page.query_selector('input[type="search"], input[placeholder*="Search"]')
            if search_input:
                search_input.fill(player_name)
                page.wait_for_timeout(1000)
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find player link
            player_link = find_player_link(soup, player_name)
            
            if not player_link:
                logger.warning(f"Player {player_name} not found")
                browser.close()
                return None
            
            # Navigate to player's stats page
            player_url = player_link.get('href')
            if not player_url.startswith('http'):
                player_url = f"https://www.nba.com{player_url}"
            
            page.goto(player_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse player stats
            stats = parse_player_stats_page(soup, player_name, season)
            
            browser.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error scraping player stats: {e}")
            browser.close()
            return None


def scrape_team_stats(
    team_name: str,
    season: str = "2024-25",
    headless: bool = True
) -> Optional[TeamSeasonStats]:
    """
    Scrape team statistics from NBA.com
    
    Args:
        team_name: Team name (e.g., "Lakers", "Los Angeles Lakers")
        season: Season in format "YYYY-YY"
        headless: Run browser in headless mode
    
    Returns:
        TeamSeasonStats object or None if not found
    """
    logger.info(f"Scraping stats for {team_name} ({season})")
    
    # NBA.com team stats URL
    url = f"https://www.nba.com/stats/teams"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find team link
            team_link = find_team_link(soup, team_name)
            
            if not team_link:
                logger.warning(f"Team {team_name} not found")
                browser.close()
                return None
            
            # Navigate to team's stats page
            team_url = team_link.get('href')
            if not team_url.startswith('http'):
                team_url = f"https://www.nba.com{team_url}"
            
            page.goto(team_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse team stats
            stats = parse_team_stats_page(soup, team_name, season)
            
            browser.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error scraping team stats: {e}")
            browser.close()
            return None


def find_player_link(soup: BeautifulSoup, player_name: str):
    """Find link to player's stats page"""
    # Search for player name in links
    links = soup.find_all('a', href=re.compile(r'/stats/player/'))
    
    for link in links:
        text = link.get_text(strip=True)
        if player_name.lower() in text.lower():
            return link
    
    return None


def find_team_link(soup: BeautifulSoup, team_name: str):
    """Find link to team's stats page"""
    # Search for team name in links
    links = soup.find_all('a', href=re.compile(r'/stats/team/'))
    
    normalized_team = normalize_team_name(team_name)
    
    for link in links:
        text = link.get_text(strip=True)
        if normalized_team in normalize_team_name(text):
            return link
    
    return None


def parse_player_stats_page(soup: BeautifulSoup, player_name: str, season: str) -> Optional[PlayerSeasonStats]:
    """Parse player stats from their stats page"""
    try:
        # Extract season averages from stats table
        stats_table = soup.find('table', class_=re.compile(r'stats|table', re.I))
        
        if not stats_table:
            # Try to find stats in data attributes or JSON
            stats_script = soup.find('script', string=re.compile(r'playerStats|gameLog', re.I))
            if stats_script:
                # Parse JSON data
                return parse_player_stats_from_json(stats_script, player_name, season)
            return None
        
        # Parse table data
        rows = stats_table.find_all('tr')[1:]  # Skip header
        
        game_log = []
        total_points = 0
        total_rebounds = 0
        total_assists = 0
        total_steals = 0
        total_blocks = 0
        total_minutes = 0
        games_played = 0
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 5:
                continue
            
            try:
                game_stats = parse_player_game_row(cells)
                if game_stats:
                    game_log.append(game_stats)
                    total_points += game_stats.points
                    total_rebounds += game_stats.rebounds
                    total_assists += game_stats.assists
                    total_steals += game_stats.steals
                    total_blocks += game_stats.blocks
                    total_minutes += game_stats.minutes
                    games_played += 1
            except Exception as e:
                logger.debug(f"Error parsing game row: {e}")
                continue
        
        if games_played == 0:
            return None
        
        # Get team name
        team_elem = soup.find(string=re.compile(r'Team|Current Team', re.I))
        team = extract_team_from_context(soup) if not team_elem else "Unknown"
        
        return PlayerSeasonStats(
            player_name=player_name,
            team=team,
            season=season,
            games_played=games_played,
            points_per_game=total_points / games_played,
            rebounds_per_game=total_rebounds / games_played,
            assists_per_game=total_assists / games_played,
            steals_per_game=total_steals / games_played,
            blocks_per_game=total_blocks / games_played,
            minutes_per_game=total_minutes / games_played,
            fg_percentage=0.0,  # Calculate from game log
            three_pt_percentage=0.0,
            ft_percentage=0.0,
            game_log=game_log
        )
        
    except Exception as e:
        logger.error(f"Error parsing player stats page: {e}")
        return None


def parse_player_game_row(cells) -> Optional[PlayerGameStats]:
    """Parse a single game row from stats table"""
    try:
        # Extract date
        date_text = cells[0].get_text(strip=True)
        
        # Extract opponent
        opponent_elem = cells[1] if len(cells) > 1 else None
        opponent = opponent_elem.get_text(strip=True) if opponent_elem else "Unknown"
        
        # Determine home/away
        home_away = "HOME" if "@" not in opponent else "AWAY"
        opponent = opponent.replace("@", "").strip()
        
        # Extract stats (order may vary)
        points = int(cells[2].get_text(strip=True)) if len(cells) > 2 else 0
        rebounds = int(cells[3].get_text(strip=True)) if len(cells) > 3 else 0
        assists = int(cells[4].get_text(strip=True)) if len(cells) > 4 else 0
        
        # Additional stats if available
        steals = int(cells[5].get_text(strip=True)) if len(cells) > 5 else 0
        blocks = int(cells[6].get_text(strip=True)) if len(cells) > 6 else 0
        turnovers = int(cells[7].get_text(strip=True)) if len(cells) > 7 else 0
        
        # Minutes
        minutes_text = cells[8].get_text(strip=True) if len(cells) > 8 else "0:00"
        minutes = parse_minutes(minutes_text)
        
        return PlayerGameStats(
            game_date=date_text,
            opponent=opponent,
            home_away=home_away,
            points=points,
            rebounds=rebounds,
            assists=assists,
            steals=steals,
            blocks=blocks,
            turnovers=turnovers,
            minutes=minutes,
            fg_made=0,  # Would need to parse from shooting stats
            fg_attempted=0,
            three_pt_made=0,
            three_pt_attempted=0,
            ft_made=0,
            ft_attempted=0
        )
    except Exception as e:
        logger.debug(f"Error parsing game row: {e}")
        return None


def parse_team_stats_page(soup: BeautifulSoup, team_name: str, season: str) -> Optional[TeamSeasonStats]:
    """Parse team stats from team stats page"""
    # Similar structure to player stats
    # Implementation would parse team game log
    return None  # Placeholder


def parse_player_stats_from_json(script, player_name: str, season: str) -> Optional[PlayerSeasonStats]:
    """Parse player stats from embedded JSON data"""
    # Would extract JSON from script tag and parse
    return None  # Placeholder


def parse_minutes(minutes_text: str) -> float:
    """Parse minutes from "MM:SS" format to float"""
    try:
        parts = minutes_text.split(':')
        if len(parts) == 2:
            return float(parts[0]) + float(parts[1]) / 60.0
        return float(minutes_text)
    except:
        return 0.0


def extract_team_from_context(soup: BeautifulSoup) -> str:
    """Extract team name from page context"""
    # Look for team name in various places
    team_elems = soup.find_all(string=re.compile(r'Lakers|Celtics|Warriors|Heat', re.I))
    if team_elems:
        return team_elems[0].strip()
    return "Unknown"


def normalize_team_name(team: str) -> str:
    """Normalize team name for matching"""
    return team.lower().strip()


def main():
    """Test the NBA stats scraper"""
    print("\n" + "="*70)
    print("  NBA.COM STATS SCRAPER")
    print("="*70 + "\n")
    
    # Test player stats
    player_name = "LeBron James"
    print(f"Testing player stats for: {player_name}")
    player_stats = scrape_player_stats(player_name, headless=False)
    
    if player_stats:
        print(f"\n✓ Found stats for {player_stats.player_name}")
        print(f"  Team: {player_stats.team}")
        print(f"  Games: {player_stats.games_played}")
        print(f"  PPG: {player_stats.points_per_game:.1f}")
        print(f"  RPG: {player_stats.rebounds_per_game:.1f}")
        print(f"  APG: {player_stats.assists_per_game:.1f}")
        print(f"  Games in log: {len(player_stats.game_log)}")
    else:
        print(f"✗ Could not find stats for {player_name}")
    
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user\n")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

