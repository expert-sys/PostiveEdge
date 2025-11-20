"""
NBA.com Lineup and Injury Scraper
==================================
Replaces Rotowire scraper - scrapes lineup and injury information from NBA.com

Features:
- Starting lineups (expected and confirmed)
- Player injury status (Out, Questionable, Probable)
- Game-time decisions
- Team injury reports

Usage:
  from nba_lineup_scraper import scrape_nba_lineups
  lineups = scrape_nba_lineups()
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
logger = logging.getLogger("nba_lineup_scraper")


@dataclass
class PlayerStatus:
    """Individual player lineup status"""
    name: str
    position: str
    status: str  # "Expected", "Out", "Questionable", "Probable", etc.
    injury_info: Optional[str] = None
    is_starter: bool = False


@dataclass
class TeamLineup:
    """Team lineup information"""
    team_name: str
    team_abbr: str
    starters: List[PlayerStatus]
    bench_news: List[PlayerStatus]  # Players who are Out, Questionable, etc.


@dataclass
class GameLineup:
    """Complete game lineup information"""
    away_team: TeamLineup
    home_team: TeamLineup
    game_time: str
    matchup: str  # e.g., "IND @ DET"
    
    def to_dict(self):
        return {
            'matchup': self.matchup,
            'game_time': self.game_time,
            'away_team': {
                'name': self.away_team.team_name,
                'abbr': self.away_team.team_abbr,
                'starters': [asdict(p) for p in self.away_team.starters],
                'injuries': [asdict(p) for p in self.away_team.bench_news]
            },
            'home_team': {
                'name': self.home_team.team_name,
                'abbr': self.home_team.team_abbr,
                'starters': [asdict(p) for p in self.home_team.starters],
                'injuries': [asdict(p) for p in self.home_team.bench_news]
            }
        }


def scrape_nba_lineups(headless: bool = True, date: Optional[str] = None) -> List[GameLineup]:
    """
    Scrape NBA lineups from NBA.com
    
    Args:
        headless: Run browser in headless mode
        date: Date in YYYY-MM-DD format (default: today)
    
    Returns:
        List of GameLineup objects with starting lineups and injury info
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # NBA.com doesn't have a dedicated lineups page like Rotowire
    # We'll need to scrape from schedule/game pages or use injury reports
    url = f"https://www.nba.com/schedule?date={date}"
    
    logger.info(f"Scraping NBA lineups from {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        try:
            # Load the schedule page
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            games = []
            
            # Find all games on the schedule
            game_links = soup.find_all('a', href=re.compile(r'/game/|/schedule/', re.I))
            
            # Also try to find game containers
            game_containers = soup.find_all(['div', 'article'], 
                                          class_=re.compile(r'game|match|event', re.I))
            
            logger.info(f"Found {len(game_links)} game links, {len(game_containers)} game containers")
            
            # For each game, try to get lineup/injury info
            # This is a simplified version - NBA.com may require clicking into each game
            # For now, we'll extract what we can from the schedule page
            
            # Try to find injury reports or lineup information
            injury_section = soup.find(string=re.compile(r'Injury|Lineup|Status', re.I))
            
            if injury_section:
                # Parse injury information
                games = parse_lineups_from_schedule(soup, date)
            else:
                # Fallback: try to get lineups from individual game pages
                games = scrape_lineups_from_game_pages(page, game_links[:10], date)  # Limit to 10 for testing
            
            browser.close()
            return games
            
        except Exception as e:
            logger.error(f"Error scraping NBA lineups: {e}")
            browser.close()
            return []


def parse_lineups_from_schedule(soup: BeautifulSoup, date: str) -> List[GameLineup]:
    """Parse lineup information from schedule page"""
    games = []
    
    # This is a placeholder - NBA.com structure may vary
    # In practice, you might need to:
    # 1. Click into each game page
    # 2. Parse injury reports separately
    # 3. Use NBA API if available
    
    return games


def scrape_lineups_from_game_pages(page, game_links: List, date: str) -> List[GameLineup]:
    """Scrape lineups by visiting individual game pages"""
    games = []
    
    for link in game_links[:5]:  # Limit for testing
        try:
            href = link.get('href')
            if not href.startswith('http'):
                href = f"https://www.nba.com{href}"
            
            page.goto(href, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to parse lineup from game page
            game_lineup = parse_lineup_from_game_page(soup, date)
            if game_lineup:
                games.append(game_lineup)
                
        except Exception as e:
            logger.debug(f"Error scraping game page: {e}")
            continue
    
    return games


def parse_lineup_from_game_page(soup: BeautifulSoup, date: str) -> Optional[GameLineup]:
    """Parse lineup from individual game page"""
    try:
        # Look for starting lineups
        lineup_section = soup.find(['div', 'section'], 
                                  class_=re.compile(r'lineup|starting|roster', re.I))
        
        if not lineup_section:
            return None
        
        # Extract team names
        teams = lineup_section.find_all(['div', 'section'], 
                                       class_=re.compile(r'team', re.I))
        
        if len(teams) < 2:
            return None
        
        away_lineup = parse_team_lineup_from_page(teams[0])
        home_lineup = parse_team_lineup_from_page(teams[1])
        
        if not away_lineup or not home_lineup:
            return None
        
        matchup = f"{away_lineup.team_abbr} @ {home_lineup.team_abbr}"
        
        # Get game time
        time_elem = soup.find(string=re.compile(r'\d{1,2}:\d{2}\s*(AM|PM|ET|PT)', re.I))
        game_time = time_elem.strip() if time_elem else "TBD"
        
        return GameLineup(
            away_team=away_lineup,
            home_team=home_lineup,
            game_time=game_time,
            matchup=matchup
        )
        
    except Exception as e:
        logger.debug(f"Error parsing game page lineup: {e}")
        return None


def parse_team_lineup_from_page(team_section) -> Optional[TeamLineup]:
    """Parse team lineup from game page section"""
    try:
        # Extract team name
        team_name_elem = team_section.find(string=re.compile(r'Lakers|Celtics|Warriors', re.I))
        team_name = team_name_elem.strip() if team_name_elem else "Unknown"
        team_abbr = get_team_abbr(team_name)
        
        # Find starting lineup
        starters = []
        starter_list = team_section.find_all(['li', 'div'], 
                                            class_=re.compile(r'player|starter', re.I))
        
        for item in starter_list[:5]:  # First 5 are usually starters
            player = parse_player_from_lineup_item(item, is_starter=True)
            if player:
                starters.append(player)
        
        # Find injuries
        injuries = []
        injury_section = team_section.find(string=re.compile(r'Out|Questionable|Injury', re.I))
        if injury_section:
            injury_items = injury_section.find_parent().find_all(['li', 'div'])
            for item in injury_items:
                player = parse_player_from_lineup_item(item, is_starter=False)
                if player and player.status != "Expected":
                    injuries.append(player)
        
        return TeamLineup(
            team_name=team_name,
            team_abbr=team_abbr,
            starters=starters,
            bench_news=injuries
        )
        
    except Exception as e:
        logger.debug(f"Error parsing team lineup: {e}")
        return None


def parse_player_from_lineup_item(item, is_starter: bool) -> Optional[PlayerStatus]:
    """Parse player from lineup list item"""
    try:
        # Get player name
        name_elem = item.find(['a', 'span', 'div'], class_=re.compile(r'name|player', re.I))
        if not name_elem:
            name_elem = item.find(string=re.compile(r'^[A-Z][a-z]+ [A-Z][a-z]+$'))
        
        if not name_elem:
            return None
        
        player_name = name_elem.get_text(strip=True) if hasattr(name_elem, 'get_text') else str(name_elem).strip()
        
        # Get position
        pos_elem = item.find(string=re.compile(r'PG|SG|SF|PF|C|G|F'))
        position = pos_elem.strip() if pos_elem else "N/A"
        
        # Get status
        status = "Expected" if is_starter else "Available"
        injury_info = None
        
        # Check for injury status
        status_text = item.get_text()
        if 'Out' in status_text:
            status = "Out"
            injury_info = "Out"
        elif 'Questionable' in status_text or 'GTD' in status_text:
            status = "Questionable"
            injury_info = "Questionable"
        elif 'Probable' in status_text:
            status = "Probable"
            injury_info = "Probable"
        elif 'Doubtful' in status_text:
            status = "Doubtful"
            injury_info = "Doubtful"
        
        return PlayerStatus(
            name=player_name,
            position=position,
            status=status,
            injury_info=injury_info,
            is_starter=is_starter
        )
        
    except Exception as e:
        logger.debug(f"Error parsing player: {e}")
        return None


def get_team_abbr(team_name: str) -> str:
    """Get team abbreviation from full name"""
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
    
    # Fallback
    return team_name[:3].upper() if len(team_name) >= 3 else team_name.upper()


def find_lineup_for_matchup(lineups: List[GameLineup], away_team: str, home_team: str) -> Optional[GameLineup]:
    """Find lineup data for a specific matchup"""
    away_normalized = normalize_team_name(away_team)
    home_normalized = normalize_team_name(home_team)
    
    for lineup in lineups:
        lineup_away = normalize_team_name(lineup.away_team.team_name)
        lineup_home = normalize_team_name(lineup.home_team.team_name)
        
        if (away_normalized in lineup_away or lineup_away in away_normalized) and \
           (home_normalized in lineup_home or lineup_home in home_normalized):
            return lineup
    
    return None


def normalize_team_name(team: str) -> str:
    """Normalize team name for matching"""
    team_lower = team.lower()
    
    team_map = {
        'mil': 'bucks', 'milwaukee': 'bucks',
        'cle': 'cavaliers', 'cleveland': 'cavaliers',
        'ind': 'pacers', 'indiana': 'pacers',
        'det': 'pistons', 'detroit': 'pistons',
        'lal': 'lakers', 'los angeles lakers': 'lakers',
        'lac': 'clippers', 'los angeles clippers': 'clippers',
        'gsw': 'warriors', 'golden state': 'warriors',
        'bos': 'celtics', 'boston': 'celtics',
        'mia': 'heat', 'miami': 'heat',
        'nyk': 'knicks', 'new york': 'knicks',
        'bkn': 'nets', 'brooklyn': 'nets',
        'phi': '76ers', 'philadelphia': '76ers',
        'tor': 'raptors', 'toronto': 'raptors',
        'chi': 'bulls', 'chicago': 'bulls',
        'atl': 'hawks', 'atlanta': 'hawks',
        'was': 'wizards', 'washington': 'wizards',
        'cha': 'hornets', 'charlotte': 'hornets',
        'orl': 'magic', 'orlando': 'magic',
        'den': 'nuggets', 'denver': 'nuggets',
        'phx': 'suns', 'phoenix': 'suns',
        'dal': 'mavericks', 'dallas': 'mavericks',
        'mem': 'grizzlies', 'memphis': 'grizzlies',
        'hou': 'rockets', 'houston': 'rockets',
        'sas': 'spurs', 'san antonio': 'spurs',
        'nop': 'pelicans', 'new orleans': 'pelicans',
        'okc': 'thunder', 'oklahoma city': 'thunder',
        'min': 'timberwolves', 'minnesota': 'timberwolves',
        'por': 'trail blazers', 'portland': 'blazers',
        'uta': 'jazz', 'utah': 'jazz',
        'sac': 'kings', 'sacramento': 'kings'
    }
    
    return team_map.get(team_lower, team_lower)


def get_injury_impact_summary(lineup: GameLineup) -> Dict:
    """Generate a summary of injury impacts for betting analysis"""
    away_injuries = [p for p in lineup.away_team.bench_news if p.status in ['Out', 'Doubtful']]
    home_injuries = [p for p in lineup.home_team.bench_news if p.status in ['Out', 'Doubtful']]
    
    away_questionable = [p for p in lineup.away_team.bench_news if p.status == 'Questionable']
    home_questionable = [p for p in lineup.home_team.bench_news if p.status == 'Questionable']
    
    return {
        'away_team': {
            'team': lineup.away_team.team_abbr,
            'out_count': len(away_injuries),
            'questionable_count': len(away_questionable),
            'key_injuries': [f"{p.name} ({p.position}) - {p.status}" for p in away_injuries],
            'starters_confirmed': len(lineup.away_team.starters) >= 5
        },
        'home_team': {
            'team': lineup.home_team.team_abbr,
            'out_count': len(home_injuries),
            'questionable_count': len(home_questionable),
            'key_injuries': [f"{p.name} ({p.position}) - {p.status}" for p in home_injuries],
            'starters_confirmed': len(lineup.home_team.starters) >= 5
        },
        'total_injuries': len(away_injuries) + len(home_injuries),
        'total_questionable': len(away_questionable) + len(home_questionable),
        'high_impact': len(away_injuries) + len(home_injuries) > 2
    }


def main():
    """Test the NBA lineup scraper"""
    print("\n" + "="*70)
    print("  NBA.COM LINEUP SCRAPER")
    print("="*70 + "\n")
    
    lineups = scrape_nba_lineups(headless=False)
    
    print(f"\n✓ Scraped {len(lineups)} games\n")
    
    for i, lineup in enumerate(lineups, 1):
        print(f"\n{i}. {lineup.matchup} - {lineup.game_time}")
        print("─" * 70)
        
        # Away team
        print(f"\n  {lineup.away_team.team_abbr} ({lineup.away_team.team_name})")
        print(f"  Starters: {len(lineup.away_team.starters)}")
        for starter in lineup.away_team.starters[:5]:
            status_str = f" [{starter.status}]" if starter.status != "Expected" else ""
            print(f"    • {starter.position}: {starter.name}{status_str}")
        
        if lineup.away_team.bench_news:
            print(f"  Injuries/News: {len(lineup.away_team.bench_news)}")
            for player in lineup.away_team.bench_news:
                print(f"    ⚠ {player.name} ({player.position}) - {player.status}")
        
        # Home team
        print(f"\n  {lineup.home_team.team_abbr} ({lineup.home_team.team_name})")
        print(f"  Starters: {len(lineup.home_team.starters)}")
        for starter in lineup.home_team.starters[:5]:
            status_str = f" [{starter.status}]" if starter.status != "Expected" else ""
            print(f"    • {starter.position}: {starter.name}{status_str}")
        
        if lineup.home_team.bench_news:
            print(f"  Injuries/News: {len(lineup.home_team.bench_news)}")
            for player in lineup.home_team.bench_news:
                print(f"    ⚠ {player.name} ({player.position}) - {player.status}")
        
        # Impact summary
        impact = get_injury_impact_summary(lineup)
        if impact['high_impact']:
            print(f"\n  ⚠️  HIGH INJURY IMPACT GAME ({impact['total_injuries']} out, {impact['total_questionable']} questionable)")
    
    # Save to file
    output_dir = Path(__file__).parent.parent / "data" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = output_dir / f"nba_lineups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'scraped_at': datetime.now().isoformat(),
            'games_count': len(lineups),
            'games': [lineup.to_dict() for lineup in lineups]
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved to: {filename}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user\n")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

