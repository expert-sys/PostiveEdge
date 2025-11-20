"""
NBA.com Schedule Scraper
========================
Scrapes game schedule from NBA.com/schedule to determine:
- Final games (already played)
- Upcoming games (with times)
- Game status and scores

Usage:
  from nba_schedule_scraper import scrape_nba_schedule
  games = scrape_nba_schedule()
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
logger = logging.getLogger("nba_schedule_scraper")


@dataclass
class ScheduledGame:
    """Game schedule information"""
    away_team: str
    home_team: str
    away_team_abbr: str
    home_team_abbr: str
    game_date: str
    game_time: Optional[str]  # None for final games
    status: str  # "FINAL", "LIVE", "UPCOMING", "POSTPONED"
    away_score: Optional[int] = None
    home_score: Optional[int] = None
    game_id: Optional[str] = None
    venue: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


def scrape_nba_schedule(headless: bool = True, date: Optional[str] = None) -> List[ScheduledGame]:
    """
    Scrape NBA schedule from NBA.com
    
    Args:
        headless: Run browser in headless mode
        date: Date in YYYY-MM-DD format (default: today)
    
    Returns:
        List of ScheduledGame objects
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # NBA.com schedule URL format
    url = f"https://www.nba.com/schedule?date={date}"
    
    logger.info(f"Scraping NBA schedule from {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        try:
            # Load the page and wait for content
            logger.info("Loading page...")
            page.goto(url, wait_until="load", timeout=60000)
            
            # Wait longer for dynamic content to load
            logger.info("Waiting for dynamic content...")
            page.wait_for_timeout(5000)
            
            # Try scrolling to trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(2000)
            
            # Try to wait for specific elements that indicate games are loaded
            selectors_to_wait = [
                '[data-testid*="game"]',
                '[class*="GameCard"]',
                '[class*="ScheduleGame"]',
                'a[href*="/game/"]',
                '[class*="game"]'
            ]
            
            for selector in selectors_to_wait:
                try:
                    page.wait_for_selector(selector, timeout=3000)
                    logger.info(f"Found content with selector: {selector}")
                    break
                except:
                    continue
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Save HTML for debugging
            debug_file = Path(__file__).parent.parent / "debug" / f"nba_schedule_{date}.html"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"Saved page HTML to {debug_file}")
            
            games = []
            
            # Strategy 1: Look for embedded JSON data (NBA.com often uses this)
            games_from_json = extract_games_from_json(soup, date)
            if games_from_json:
                logger.info(f"Found {len(games_from_json)} games from JSON data")
                games.extend(games_from_json)
            
            # Strategy 2: Find all game containers with various selectors
            game_containers = []
            
            # Try multiple selector patterns
            selectors = [
                ('div', {'class': re.compile(r'game|match|event|card', re.I)}),
                ('article', {'class': re.compile(r'game|match', re.I)}),
                ('a', {'href': re.compile(r'/game/|/schedule/', re.I)}),
                ('div', {'data-testid': re.compile(r'game|match', re.I)}),
                ('div', {'data-game-id': True}),
                ('div', {'id': re.compile(r'game|match', re.I)}),
            ]
            
            for tag, attrs in selectors:
                found = soup.find_all(tag, attrs)
                if found:
                    game_containers.extend(found)
                    logger.info(f"Found {len(found)} elements with {tag} and {list(attrs.keys())}")
            
            # Remove duplicates
            seen = set()
            unique_containers = []
            for container in game_containers:
                container_id = id(container)
                if container_id not in seen:
                    seen.add(container_id)
                    unique_containers.append(container)
            
            game_containers = unique_containers
            logger.info(f"Found {len(game_containers)} unique potential game containers")
            
            # Strategy 3: Parse containers
            if game_containers and not games:
                for container in game_containers:
                    try:
                        game = parse_game_container(container, date)
                        if game:
                            games.append(game)
                    except Exception as e:
                        logger.debug(f"Error parsing game container: {e}")
                        continue
            
            # Strategy 4: Try parsing schedule structure
            if not games:
                games = parse_schedule_structure(soup, date)
            
            # Strategy 5: Look for team names directly in the page
            if not games:
                games = extract_games_from_team_names(soup, date)
            
            browser.close()
            logger.info(f"Successfully parsed {len(games)} games")
            return games
            
        except Exception as e:
            logger.error(f"Error scraping NBA schedule: {e}")
            browser.close()
            return []


def extract_games_from_json(soup: BeautifulSoup, date: str) -> List[ScheduledGame]:
    """Extract games from embedded JSON data in page"""
    games = []
    
    # Look for script tags with JSON data
    scripts = soup.find_all('script', type=re.compile(r'application/json|text/javascript', re.I))
    
    for script in scripts:
        try:
            content = script.string
            if not content:
                continue
            
            # Try to parse as JSON
            if 'games' in content.lower() or 'schedule' in content.lower():
                # Extract JSON object
                json_match = re.search(r'\{.*"games?":.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    
                    # Try to extract games from various JSON structures
                    if 'games' in data:
                        games_data = data['games']
                    elif 'schedule' in data:
                        games_data = data['schedule']
                    elif isinstance(data, list):
                        games_data = data
                    else:
                        continue
                    
                    for game_data in games_data:
                        try:
                            game = parse_game_from_json(game_data, date)
                            if game:
                                games.append(game)
                        except Exception as e:
                            logger.debug(f"Error parsing game from JSON: {e}")
                            continue
        except Exception as e:
            logger.debug(f"Error extracting JSON: {e}")
            continue
    
    return games


def parse_game_from_json(game_data: Dict, date: str) -> Optional[ScheduledGame]:
    """Parse a game from JSON data structure"""
    try:
        # Handle different JSON structures
        away_team = game_data.get('awayTeam', {}).get('teamName') or game_data.get('away_team') or game_data.get('awayTeamName')
        home_team = game_data.get('homeTeam', {}).get('teamName') or game_data.get('home_team') or game_data.get('homeTeamName')
        
        if not away_team or not home_team:
            return None
        
        away_abbr = game_data.get('awayTeam', {}).get('teamAbbreviation') or extract_team_abbr(None, away_team)
        home_abbr = game_data.get('homeTeam', {}).get('teamAbbreviation') or extract_team_abbr(None, home_team)
        
        # Determine status
        status = game_data.get('gameStatusText', 'UPCOMING').upper()
        if 'FINAL' in status:
            status = "FINAL"
        elif 'LIVE' in status or 'IN PROGRESS' in status:
            status = "LIVE"
        else:
            status = "UPCOMING"
        
        # Get scores
        away_score = game_data.get('awayTeam', {}).get('score') or game_data.get('awayScore')
        home_score = game_data.get('homeTeam', {}).get('score') or game_data.get('homeScore')
        
        # Get game time
        game_time = game_data.get('gameTimeUTC') or game_data.get('gameTime') or game_data.get('startTime')
        
        return ScheduledGame(
            away_team=away_team,
            home_team=home_team,
            away_team_abbr=away_abbr or extract_team_abbr(None, away_team),
            home_team_abbr=home_abbr or extract_team_abbr(None, home_team),
            game_date=date,
            game_time=str(game_time) if game_time else None,
            status=status,
            away_score=int(away_score) if away_score else None,
            home_score=int(home_score) if home_score else None
        )
    except Exception as e:
        logger.debug(f"Error parsing game from JSON: {e}")
        return None


def extract_games_from_team_names(soup: BeautifulSoup, date: str) -> List[ScheduledGame]:
    """Fallback: Try to extract games by finding team name pairs"""
    games = []
    
    # Look for common team name patterns
    team_names = [
        'Lakers', 'Celtics', 'Warriors', 'Heat', 'Knicks', 'Bulls', 'Mavericks',
        'Cavaliers', 'Pacers', 'Pistons', 'Clippers', 'Nuggets', 'Suns', 'Rockets',
        'Spurs', 'Pelicans', 'Thunder', 'Timberwolves', 'Trail Blazers', 'Jazz',
        'Kings', 'Nets', '76ers', 'Raptors', 'Hawks', 'Wizards', 'Hornets', 'Magic',
        'Grizzlies', 'Bucks'
    ]
    
    # Find all text containing team names
    page_text = soup.get_text()
    
    # Look for patterns like "Team1 @ Team2" or "Team1 vs Team2"
    for team1 in team_names:
        for team2 in team_names:
            if team1 == team2:
                continue
            
            pattern = rf'{team1}.*?(@|vs|at).*?{team2}'
            matches = re.findall(pattern, page_text, re.I)
            if matches:
                # Found a potential game
                games.append(ScheduledGame(
                    away_team=team1,
                    home_team=team2,
                    away_team_abbr=extract_team_abbr(None, team1),
                    home_team_abbr=extract_team_abbr(None, team2),
                    game_date=date,
                    game_time=None,
                    status="UPCOMING"
                ))
    
    return games


def parse_schedule_structure(soup: BeautifulSoup, date: str) -> List[ScheduledGame]:
    """Parse schedule from table/list structure"""
    games = []
    
    # Look for schedule rows or game cards
    schedule_sections = soup.find_all(['div', 'section', 'article'], 
                                     class_=re.compile(r'schedule|game-day|game-list|ScheduleDay', re.I))
    
    for section in schedule_sections:
        # Find individual game rows/cards
        game_items = section.find_all(['div', 'tr', 'li'], 
                                     class_=re.compile(r'game|match|row|GameCard|ScheduleGame', re.I))
        
        for item in game_items:
            try:
                game = parse_game_item(item, date)
                if game:
                    games.append(game)
            except Exception as e:
                logger.debug(f"Error parsing game item: {e}")
                continue
    
    return games


def parse_game_container(container, date: str) -> Optional[ScheduledGame]:
    """Parse a single game container"""
    try:
        # Extract team names
        teams = container.find_all(['span', 'div', 'a'], 
                                  class_=re.compile(r'team|name', re.I))
        
        if len(teams) < 2:
            return None
        
        away_team_elem = teams[0]
        home_team_elem = teams[1]
        
        away_team = away_team_elem.get_text(strip=True)
        home_team = home_team_elem.get_text(strip=True)
        
        # Extract abbreviations (often in data attributes or classes)
        away_abbr = extract_team_abbr(away_team_elem, away_team)
        home_abbr = extract_team_abbr(home_team_elem, home_team)
        
        # Determine status
        status = "UPCOMING"
        game_time = None
        away_score = None
        home_score = None
        
        # Check for final status
        status_elem = container.find(string=re.compile(r'FINAL|LIVE|POSTPONED', re.I))
        if status_elem:
            status_text = status_elem.strip().upper()
            if 'FINAL' in status_text:
                status = "FINAL"
            elif 'LIVE' in status_text:
                status = "LIVE"
            elif 'POSTPONED' in status_text:
                status = "POSTPONED"
        
        # Check for scores
        score_elems = container.find_all(string=re.compile(r'^\d+$'))
        if len(score_elems) >= 2:
            try:
                away_score = int(score_elems[0].strip())
                home_score = int(score_elems[1].strip())
                if status == "UPCOMING":
                    status = "FINAL"  # Has scores, must be final
            except ValueError:
                pass
        
        # Check for time (if not final)
        if status == "UPCOMING":
            time_elem = container.find(string=re.compile(r'\d{1,2}:\d{2}\s*(AM|PM|ET|PT)', re.I))
            if time_elem:
                game_time = time_elem.strip()
        
        # Extract game ID if available
        game_id = None
        if container.get('data-game-id'):
            game_id = container.get('data-game-id')
        elif container.get('href'):
            href = container.get('href')
            match = re.search(r'/game/(\d+)', href)
            if match:
                game_id = match.group(1)
        
        # Extract venue
        venue_elem = container.find(string=re.compile(r'Arena|Center|Fieldhouse|Forum', re.I))
        venue = venue_elem.strip() if venue_elem else None
        
        return ScheduledGame(
            away_team=away_team,
            home_team=home_team,
            away_team_abbr=away_abbr,
            home_team_abbr=home_abbr,
            game_date=date,
            game_time=game_time,
            status=status,
            away_score=away_score,
            home_score=home_score,
            game_id=game_id,
            venue=venue
        )
        
    except Exception as e:
        logger.debug(f"Error parsing game container: {e}")
        return None


def parse_game_item(item, date: str) -> Optional[ScheduledGame]:
    """Parse a game from schedule list/table item"""
    try:
        # Similar logic to parse_game_container
        return parse_game_container(item, date)
    except Exception as e:
        logger.debug(f"Error parsing game item: {e}")
        return None


def extract_team_abbr(elem, team_name: str) -> str:
    """Extract team abbreviation from element or name"""
    # Try data attributes first (if elem is provided)
    if elem and hasattr(elem, 'get'):
        if elem.get('data-team'):
            return elem.get('data-team')
        if elem.get('data-abbr'):
            return elem.get('data-abbr')
        
        # Try class names
        classes = elem.get('class', [])
        for cls in classes:
            if 'team-' in cls.lower():
                match = re.search(r'team-(\w+)', cls.lower())
                if match:
                    return match.group(1).upper()
    
    # Extract from team name
    team_map = {
        'Milwaukee Bucks': 'MIL', 'Cleveland Cavaliers': 'CLE',
        'Indiana Pacers': 'IND', 'Detroit Pistons': 'DET',
        'Los Angeles Lakers': 'LAL', 'LA Lakers': 'LAL',
        'Los Angeles Clippers': 'LAC', 'LA Clippers': 'LAC',
        'Golden State Warriors': 'GSW', 'Boston Celtics': 'BOS',
        'Miami Heat': 'MIA', 'New York Knicks': 'NYK',
        'Brooklyn Nets': 'BKN', 'Philadelphia 76ers': 'PHI',
        'Toronto Raptors': 'TOR', 'Chicago Bulls': 'CHI',
        'Atlanta Hawks': 'ATL', 'Washington Wizards': 'WAS',
        'Charlotte Hornets': 'CHA', 'Orlando Magic': 'ORL',
        'Denver Nuggets': 'DEN', 'Phoenix Suns': 'PHX',
        'Dallas Mavericks': 'DAL', 'Memphis Grizzlies': 'MEM',
        'Houston Rockets': 'HOU', 'San Antonio Spurs': 'SAS',
        'New Orleans Pelicans': 'NOP', 'Oklahoma City Thunder': 'OKC',
        'Minnesota Timberwolves': 'MIN', 'Portland Trail Blazers': 'POR',
        'Utah Jazz': 'UTA', 'Sacramento Kings': 'SAC'
    }
    
    for full_name, abbr in team_map.items():
        if full_name.lower() in team_name.lower():
            return abbr
    
    # Fallback: use first 3 letters
    return team_name[:3].upper() if len(team_name) >= 3 else team_name.upper()


def get_final_games(games: List[ScheduledGame]) -> List[ScheduledGame]:
    """Filter to only final games"""
    return [g for g in games if g.status == "FINAL"]


def get_upcoming_games(games: List[ScheduledGame]) -> List[ScheduledGame]:
    """Filter to only upcoming games"""
    return [g for g in games if g.status == "UPCOMING"]


def get_live_games(games: List[ScheduledGame]) -> List[ScheduledGame]:
    """Filter to only live games"""
    return [g for g in games if g.status == "LIVE"]


def find_game_by_teams(games: List[ScheduledGame], away: str, home: str) -> Optional[ScheduledGame]:
    """Find a game by team names with improved matching"""
    if not away or not home:
        return None
    
    away_norm = normalize_team_name(away)
    home_norm = normalize_team_name(home)
    
    # Try exact match first
    for game in games:
        game_away = normalize_team_name(game.away_team)
        game_home = normalize_team_name(game.home_team)
        
        # Exact match
        if away_norm == game_away and home_norm == game_home:
            return game
        
        # Also try reversed (in case home/away are swapped)
        if away_norm == game_home and home_norm == game_away:
            return game
    
    # Try partial matching if exact match fails
    for game in games:
        game_away = normalize_team_name(game.away_team)
        game_home = normalize_team_name(game.home_team)
        
        # Check if normalized names contain each other
        away_match = (away_norm in game_away or game_away in away_norm) and len(away_norm) > 2 and len(game_away) > 2
        home_match = (home_norm in game_home or game_home in home_norm) and len(home_norm) > 2 and len(game_home) > 2
        
        if away_match and home_match:
            return game
        
        # Try reversed
        away_match_rev = (away_norm in game_home or game_home in away_norm) and len(away_norm) > 2 and len(game_home) > 2
        home_match_rev = (home_norm in game_away or game_away in home_norm) and len(home_norm) > 2 and len(game_away) > 2
        
        if away_match_rev and home_match_rev:
            return game
    
    return None


def normalize_team_name(team: str) -> str:
    """Normalize team name for matching"""
    if not team:
        return ""
    
    team_lower = team.lower().strip()
    
    # Team name mapping for better matching
    team_map = {
        # Full names to normalized
        'milwaukee bucks': 'bucks', 'milwaukee': 'bucks',
        'cleveland cavaliers': 'cavaliers', 'cleveland': 'cavaliers',
        'indiana pacers': 'pacers', 'indiana': 'pacers',
        'detroit pistons': 'pistons', 'detroit': 'pistons',
        'los angeles lakers': 'lakers', 'la lakers': 'lakers', 'lakers': 'lakers',
        'los angeles clippers': 'clippers', 'la clippers': 'clippers', 'clippers': 'clippers',
        'golden state warriors': 'warriors', 'golden state': 'warriors', 'warriors': 'warriors',
        'boston celtics': 'celtics', 'boston': 'celtics',
        'miami heat': 'heat', 'miami': 'heat',
        'new york knicks': 'knicks', 'new york': 'knicks',
        'brooklyn nets': 'nets', 'brooklyn': 'nets',
        'philadelphia 76ers': '76ers', 'philadelphia': '76ers', 'sixers': '76ers',
        'toronto raptors': 'raptors', 'toronto': 'raptors',
        'chicago bulls': 'bulls', 'chicago': 'bulls',
        'atlanta hawks': 'hawks', 'atlanta': 'hawks',
        'washington wizards': 'wizards', 'washington': 'wizards',
        'charlotte hornets': 'hornets', 'charlotte': 'hornets',
        'orlando magic': 'magic', 'orlando': 'magic',
        'denver nuggets': 'nuggets', 'denver': 'nuggets',
        'phoenix suns': 'suns', 'phoenix': 'suns',
        'dallas mavericks': 'mavericks', 'dallas': 'mavericks',
        'memphis grizzlies': 'grizzlies', 'memphis': 'grizzlies',
        'houston rockets': 'rockets', 'houston': 'rockets',
        'san antonio spurs': 'spurs', 'san antonio': 'spurs',
        'new orleans pelicans': 'pelicans', 'new orleans': 'pelicans',
        'oklahoma city thunder': 'thunder', 'oklahoma city': 'thunder', 'okc': 'thunder',
        'minnesota timberwolves': 'timberwolves', 'minnesota': 'timberwolves',
        'portland trail blazers': 'trail blazers', 'portland': 'trail blazers', 'blazers': 'trail blazers',
        'utah jazz': 'jazz', 'utah': 'jazz',
        'sacramento kings': 'kings', 'sacramento': 'kings',
        # Abbreviations
        'mil': 'bucks', 'cle': 'cavaliers', 'ind': 'pacers', 'det': 'pistons',
        'lal': 'lakers', 'lac': 'clippers', 'gsw': 'warriors', 'bos': 'celtics',
        'mia': 'heat', 'nyk': 'knicks', 'bkn': 'nets', 'phi': '76ers',
        'tor': 'raptors', 'chi': 'bulls', 'atl': 'hawks', 'was': 'wizards',
        'cha': 'hornets', 'orl': 'magic', 'den': 'nuggets', 'phx': 'suns',
        'dal': 'mavericks', 'mem': 'grizzlies', 'hou': 'rockets', 'sas': 'spurs',
        'nop': 'pelicans', 'okc': 'thunder', 'min': 'timberwolves',
        'por': 'trail blazers', 'uta': 'jazz', 'sac': 'kings'
    }
    
    # Check direct mapping first
    if team_lower in team_map:
        return team_map[team_lower]
    
    # Try partial matching
    for key, value in team_map.items():
        if key in team_lower or team_lower in key:
            return value
    
    # Remove common prefixes/suffixes and return
    team_lower = re.sub(r'\b(los angeles|la|new york|new orleans|san antonio|golden state|oklahoma city|portland trail)\b', '', team_lower)
    team_lower = re.sub(r'\s+', ' ', team_lower).strip()
    
    return team_lower


def main():
    """Test the NBA schedule scraper"""
    print("\n" + "="*70)
    print("  NBA.COM SCHEDULE SCRAPER")
    print("="*70 + "\n")
    
    games = scrape_nba_schedule(headless=False)
    
    print(f"\n✓ Scraped {len(games)} games\n")
    
    final_games = get_final_games(games)
    upcoming_games = get_upcoming_games(games)
    live_games = get_live_games(games)
    
    print(f"Final: {len(final_games)} | Upcoming: {len(upcoming_games)} | Live: {len(live_games)}\n")
    
    for i, game in enumerate(games, 1):
        status_icon = "✓" if game.status == "FINAL" else "⏰" if game.status == "UPCOMING" else "🔴"
        print(f"{i}. {status_icon} {game.away_team_abbr} @ {game.home_team_abbr}")
        print(f"   Status: {game.status}")
        if game.status == "FINAL" and game.away_score is not None:
            print(f"   Score: {game.away_team_abbr} {game.away_score} - {game.home_team_abbr} {game.home_score}")
        elif game.game_time:
            print(f"   Time: {game.game_time}")
        if game.venue:
            print(f"   Venue: {game.venue}")
        print()
    
    # Save to file
    output_dir = Path(__file__).parent.parent / "data" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = output_dir / f"nba_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'scraped_at': datetime.now().isoformat(),
            'games_count': len(games),
            'final_count': len(final_games),
            'upcoming_count': len(upcoming_games),
            'live_count': len(live_games),
            'games': [game.to_dict() for game in games]
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved to: {filename}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user\n")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

