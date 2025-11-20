"""
RotoWire NBA Lineups Scraper
============================
Scrapes lineup and injury information from RotoWire for enhanced betting analysis.

Features:
- Starting lineups (expected and confirmed)
- Player injury status (Out, Questionable, Probable)
- Game-time decisions
- Recent lineup changes

Usage:
  from rotowire_scraper import scrape_rotowire_lineups
  lineups = scrape_rotowire_lineups()
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
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
logger = logging.getLogger("rotowire_scraper")


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


def scrape_rotowire_lineups(headless: bool = True) -> List[GameLineup]:
    """
    Scrape NBA lineups from RotoWire

    Returns:
        List of GameLineup objects with starting lineups and injury info
    """
    url = "https://www.rotowire.com/basketball/nba-lineups.php"

    logger.info(f"Scraping RotoWire lineups from {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        try:
            # Load the page
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)  # Wait for dynamic content

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            games = []

            # Find all game lineup containers
            lineup_boxes = soup.find_all('div', class_='lineup')

            logger.info(f"Found {len(lineup_boxes)} games")

            for box in lineup_boxes:
                try:
                    game_lineup = parse_lineup_box(box)
                    if game_lineup:
                        games.append(game_lineup)
                        logger.info(f"Parsed: {game_lineup.matchup}")
                except Exception as e:
                    logger.error(f"Error parsing lineup box: {e}")
                    continue

            browser.close()
            return games

        except Exception as e:
            logger.error(f"Error scraping RotoWire: {e}")
            browser.close()
            return []


def parse_lineup_box(box) -> Optional[GameLineup]:
    """Parse a single game lineup box"""

    try:
        # Get game time
        time_elem = box.find('div', class_='lineup__time')
        game_time = time_elem.get_text(strip=True) if time_elem else "Unknown"

        # Get teams - RotoWire has two team sections per game
        teams = box.find_all('div', class_='lineup__box')

        if len(teams) < 2:
            return None

        # Parse away team (first) and home team (second)
        away_lineup = parse_team_lineup(teams[0])
        home_lineup = parse_team_lineup(teams[1])

        if not away_lineup or not home_lineup:
            return None

        matchup = f"{away_lineup.team_abbr} @ {home_lineup.team_abbr}"

        return GameLineup(
            away_team=away_lineup,
            home_team=home_lineup,
            game_time=game_time,
            matchup=matchup
        )

    except Exception as e:
        logger.error(f"Error parsing lineup box: {e}")
        return None


def parse_team_lineup(team_box) -> Optional[TeamLineup]:
    """Parse lineup for a single team"""

    try:
        # Get team name and abbreviation
        team_header = team_box.find('div', class_='lineup__abbr')
        if not team_header:
            return None

        team_abbr = team_header.get_text(strip=True)

        # Get full team name
        team_name_elem = team_box.find('a', class_='lineup__team')
        team_name = team_name_elem.get_text(strip=True) if team_name_elem else team_abbr

        starters = []
        bench_news = []

        # Parse starting lineup
        starter_section = team_box.find('ul', class_='lineup__list')
        if starter_section:
            starter_items = starter_section.find_all('li')

            for item in starter_items:
                player = parse_player_status(item, is_starter=True)
                if player:
                    starters.append(player)

        # Parse injury/bench news
        bench_section = team_box.find('div', class_='lineup__player')
        if bench_section:
            bench_items = bench_section.find_all('li')

            for item in bench_items:
                player = parse_player_status(item, is_starter=False)
                if player:
                    bench_news.append(player)

        return TeamLineup(
            team_name=team_name,
            team_abbr=team_abbr,
            starters=starters,
            bench_news=bench_news
        )

    except Exception as e:
        logger.error(f"Error parsing team lineup: {e}")
        return None


def parse_player_status(item, is_starter: bool) -> Optional[PlayerStatus]:
    """Parse individual player status"""

    try:
        # Get player name
        name_elem = item.find('a')
        if not name_elem:
            return None

        player_name = name_elem.get_text(strip=True)

        # Get position
        pos_elem = item.find('div', class_='lineup__pos')
        position = pos_elem.get_text(strip=True) if pos_elem else "N/A"

        # Get status (Prob, Ques, Out, etc.)
        status = "Expected" if is_starter else "Available"
        injury_info = None

        # Check for status indicators
        status_elem = item.find('span', class_='lineup__inj')
        if status_elem:
            status_text = status_elem.get_text(strip=True)

            if 'Out' in status_text:
                status = "Out"
            elif 'Ques' in status_text or 'GTD' in status_text:
                status = "Questionable"
            elif 'Prob' in status_text:
                status = "Probable"
            elif 'Doubt' in status_text:
                status = "Doubtful"

            injury_info = status_text

        return PlayerStatus(
            name=player_name,
            position=position,
            status=status,
            injury_info=injury_info,
            is_starter=is_starter
        )

    except Exception as e:
        logger.error(f"Error parsing player: {e}")
        return None


def find_lineup_for_matchup(lineups: List[GameLineup], away_team: str, home_team: str) -> Optional[GameLineup]:
    """
    Find lineup data for a specific matchup

    Args:
        lineups: List of GameLineup objects from RotoWire
        away_team: Away team name or abbreviation
        home_team: Home team name or abbreviation

    Returns:
        GameLineup if found, None otherwise
    """
    # Normalize team names for matching
    away_normalized = normalize_team_name(away_team)
    home_normalized = normalize_team_name(home_team)

    for lineup in lineups:
        lineup_away = normalize_team_name(lineup.away_team.team_name)
        lineup_home = normalize_team_name(lineup.home_team.team_name)

        if away_normalized in lineup_away or home_normalized in lineup_home:
            return lineup

    return None


def normalize_team_name(team: str) -> str:
    """Normalize team name for matching"""
    # Remove common words and convert to lowercase
    team_lower = team.lower()

    # Map of abbreviations to common names
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
    """
    Generate a summary of injury impacts for betting analysis

    Returns:
        Dict with injury impact information
    """
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
    """Test the RotoWire scraper"""
    print("\n" + "="*70)
    print("  ROTOWIRE NBA LINEUPS SCRAPER")
    print("="*70 + "\n")

    lineups = scrape_rotowire_lineups(headless=False)

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

    filename = output_dir / f"rotowire_lineups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'scraped_at': datetime.now().isoformat(),
            'games_count': len(lineups),
            'games': [lineup.to_dict() for lineup in lineups]
        }, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved to: {filename}")
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
