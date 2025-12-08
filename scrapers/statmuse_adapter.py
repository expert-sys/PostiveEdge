"""
StatMuse Data Adapter
=====================
Provides team and player statistics from StatMuse as a drop-in replacement
for the broken NBA API scraper.

This adapter provides the same interface as nba_stats_api_scraper.py but uses
StatMuse as the data source instead of the unreliable NBA stats API.

Usage:
    from scrapers.statmuse_adapter import get_team_stats_for_matchup, get_player_season_average

    # Get team stats for a matchup
    away_stats, home_stats = get_team_stats_for_matchup("Los Angeles Lakers", "Boston Celtics")

    # Get player season average
    player_avg = get_player_season_average("LeBron James", "Los Angeles Lakers")
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, asdict

# Import StatMuse scraper
from scrapers.statmuse_scraper import (
    scrape_team_stats,
    scrape_player_stats,
    scrape_team_splits,
    TeamStats,
    PlayerStats,
    TeamSplitStats
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("statmuse_adapter")

# Team name mapping to StatMuse slugs
TEAM_NAME_TO_SLUG = {
    "Atlanta Hawks": "atlanta-hawks",
    "Boston Celtics": "boston-celtics",
    "Brooklyn Nets": "brooklyn-nets",
    "Charlotte Hornets": "charlotte-hornets",
    "Chicago Bulls": "chicago-bulls",
    "Cleveland Cavaliers": "cleveland-cavaliers",
    "Dallas Mavericks": "dallas-mavericks",
    "Denver Nuggets": "denver-nuggets",
    "Detroit Pistons": "detroit-pistons",
    "Golden State Warriors": "golden-state-warriors",
    "Houston Rockets": "houston-rockets",
    "Indiana Pacers": "indiana-pacers",
    "LA Clippers": "la-clippers",
    "Los Angeles Clippers": "la-clippers",
    "Los Angeles Lakers": "los-angeles-lakers",
    "Memphis Grizzlies": "memphis-grizzlies",
    "Miami Heat": "miami-heat",
    "Milwaukee Bucks": "milwaukee-bucks",
    "Minnesota Timberwolves": "minnesota-timberwolves",
    "New Orleans Pelicans": "new-orleans-pelicans",
    "New York Knicks": "new-york-knicks",
    "Oklahoma City Thunder": "oklahoma-city-thunder",
    "Orlando Magic": "orlando-magic",
    "Philadelphia 76ers": "philadelphia-76ers",
    "Phoenix Suns": "phoenix-suns",
    "Portland Trail Blazers": "portland-trail-blazers",
    "Sacramento Kings": "sacramento-kings",
    "San Antonio Spurs": "san-antonio-spurs",
    "Toronto Raptors": "toronto-raptors",
    "Utah Jazz": "utah-jazz",
    "Washington Wizards": "washington-wizards"
}

# Cache for scraped data to avoid redundant scrapes
_team_stats_cache = {}
_player_stats_cache = {}
_team_splits_cache = {}


def normalize_team_name(team_name: str) -> str:
    """
    Normalize team name to match StatMuse format.

    Args:
        team_name: Team name (e.g., "Lakers", "Los Angeles Lakers", "LAL")

    Returns:
        Full team name for lookup
    """
    # Strip whitespace
    team_name = team_name.strip()

    # Already full name
    if team_name in TEAM_NAME_TO_SLUG:
        return team_name

    # Try partial match (e.g., "Lakers" -> "Los Angeles Lakers")
    for full_name in TEAM_NAME_TO_SLUG.keys():
        if team_name.lower() in full_name.lower():
            return full_name

    # Try abbreviation expansion (basic)
    team_expansions = {
        "LAL": "Los Angeles Lakers",
        "LAC": "Los Angeles Clippers",
        "BOS": "Boston Celtics",
        "MIA": "Miami Heat",
        "GSW": "Golden State Warriors",
        "PHX": "Phoenix Suns",
        # Add more as needed
    }

    if team_name in team_expansions:
        return team_expansions[team_name]

    logger.warning(f"Could not normalize team name: {team_name}")
    return team_name


def get_team_slug(team_name: str) -> Optional[str]:
    """Get StatMuse slug for a team name."""
    normalized = normalize_team_name(team_name)
    return TEAM_NAME_TO_SLUG.get(normalized)


def get_team_stats_for_matchup(
    away_team: str,
    home_team: str,
    season: str = "2025-26",
    headless: bool = True
) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Get team statistics for both teams in a matchup.

    This is the primary function for the betting pipeline. It returns
    comprehensive team stats including overall performance and situational splits.

    Args:
        away_team: Away team name
        home_team: Home team name
        season: Season string (default: "2025-26")
        headless: Run browser in headless mode

    Returns:
        Tuple of (away_team_dict, home_team_dict) with stats, or (None, None) on error

    Example:
        away, home = get_team_stats_for_matchup("Los Angeles Lakers", "Boston Celtics")
        print(f"Lakers PPG: {away['stats']['points']}")
        print(f"Lakers road PPG: {away['splits']['road']['points']}")
    """
    logger.info(f"Fetching stats for matchup: {away_team} @ {home_team}")

    # Normalize team names (validate they exist in mapping)
    away_normalized = normalize_team_name(away_team)
    home_normalized = normalize_team_name(home_team)

    if not away_normalized or not home_normalized:
        logger.error(f"Could not normalize team names: {away_team}, {home_team}")
        return None, None

    # Fetch team stats and splits using team names
    away_data = _get_team_complete_stats(away_normalized, season, headless)
    home_data = _get_team_complete_stats(home_normalized, season, headless)

    if not away_data or not home_data:
        logger.error("Failed to fetch team stats")
        return None, None

    return away_data, home_data


def _get_team_complete_stats(team_name: str, season: str, headless: bool) -> Optional[Dict]:
    """
    Get complete team stats including overall and splits.

    Args:
        team_name: Full team name (e.g., "Los Angeles Lakers")
        season: Season string (e.g., "2025-26")
        headless: Run browser in headless mode

    Returns dictionary with:
        - team_name: Full team name
        - stats: Overall season stats (TeamStats.to_dict())
        - splits: Dictionary of split stats organized by category
          - overall: Season totals
          - home: Home game stats
          - road: Road game stats
          - wins: Stats in wins
          - losses: Stats in losses
          - vs_eastern: vs Eastern Conference
          - vs_western: vs Western Conference
          - monthly: Dict of stats by month
          - vs_opponent: Dict of stats vs specific opponents
    """
    cache_key = f"{team_name}_{season}"

    # Check cache
    if cache_key in _team_stats_cache:
        logger.debug(f"Using cached stats for {team_name}")
        return _team_stats_cache[cache_key]

    # Scrape team stats using team name
    team_stats = scrape_team_stats(team_name, season, headless)
    if not team_stats:
        return None

    # Scrape team splits using team name
    splits = scrape_team_splits(team_name, season, headless)

    # Organize splits by category
    splits_dict = {
        'overall': None,
        'home': None,
        'road': None,
        'wins': None,
        'losses': None,
        'vs_eastern': None,
        'vs_western': None,
        'monthly': {},
        'vs_opponent': {},
        'all_splits': []
    }

    for split in splits:
        split_dict = split.to_dict()
        splits_dict['all_splits'].append(split_dict)

        split_type = split.split_type

        # Categorize splits
        if split_type == "Home":
            splits_dict['home'] = split_dict
        elif split_type == "Road":
            splits_dict['road'] = split_dict
        elif split_type == "Wins":
            splits_dict['wins'] = split_dict
        elif split_type == "Losses":
            splits_dict['losses'] = split_dict
        elif split_type == "Eastern":
            splits_dict['vs_eastern'] = split_dict
        elif split_type == "Western":
            splits_dict['vs_western'] = split_dict
        elif split_type in ["October", "November", "December", "January", "February", "March", "April"]:
            splits_dict['monthly'][split_type] = split_dict
        elif len(split_type) == 3:  # Opponent abbreviation (e.g., "LAL", "BOS")
            splits_dict['vs_opponent'][split_type] = split_dict
        elif split_type.startswith("2025") or split_type.startswith("2024"):
            splits_dict['overall'] = split_dict

    result = {
        'team_name': team_stats.team_name,
        'season': season,
        'stats': team_stats.to_dict(),
        'splits': splits_dict
    }

    # Cache result
    _team_stats_cache[cache_key] = result

    return result


def get_player_season_average(
    player_name: str,
    team_name: str,
    season: str = "2025-26",
    headless: bool = True
) -> Optional[Dict]:
    """
    Get season average stats for a player.

    Args:
        player_name: Player's full name (e.g., "LeBron James")
        team_name: Player's team name
        season: Season string
        headless: Run browser in headless mode

    Returns:
        Dictionary with player stats or None if not found

    Example:
        stats = get_player_season_average("LeBron James", "Los Angeles Lakers")
        print(f"PPG: {stats['points']}, RPG: {stats['rebounds']}, APG: {stats['assists']}")
    """
    # Normalize team name
    team_normalized = normalize_team_name(team_name)
    if not team_normalized:
        logger.error(f"Could not normalize team name: {team_name}")
        return None

    cache_key = f"{team_normalized}_{season}_players"

    # Check cache
    if cache_key not in _player_stats_cache:
        # Scrape all players for this team using team name
        players = scrape_player_stats(team_normalized, season, headless)
        _player_stats_cache[cache_key] = players

    players = _player_stats_cache[cache_key]

    # Find player by name (case-insensitive, partial match)
    player_name_lower = player_name.lower()
    for player in players:
        if player_name_lower in player.player_name.lower() or player.player_name.lower() in player_name_lower:
            return player.to_dict()

    logger.warning(f"Player not found: {player_name} on {team_name}")
    return None


def get_team_matchup_context(
    away_team: str,
    home_team: str,
    season: str = "2025-26",
    headless: bool = True
) -> Optional[Dict]:
    """
    Get matchup-specific context for betting analysis.

    This function provides enhanced context including:
    - Overall team stats
    - Home/Road splits
    - Head-to-head history (from splits if available)
    - Recent form (from monthly splits)

    Args:
        away_team: Away team name
        home_team: Home team name
        season: Season string
        headless: Run browser in headless mode

    Returns:
        Dictionary with matchup context for betting analysis
    """
    away_data, home_data = get_team_stats_for_matchup(away_team, home_team, season, headless)

    if not away_data or not home_data:
        return None

    # Extract key matchup indicators
    context = {
        'away_team': {
            'name': away_data['team_name'],
            'overall_ppg': away_data['stats']['points'],
            'road_ppg': away_data['splits']['road']['points'] if away_data['splits']['road'] else None,
            'overall_fg_pct': away_data['stats']['fg_pct'],
            'road_fg_pct': away_data['splits']['road']['fg_pct'] if away_data['splits']['road'] else None,
        },
        'home_team': {
            'name': home_data['team_name'],
            'overall_ppg': home_data['stats']['points'],
            'home_ppg': home_data['splits']['home']['points'] if home_data['splits']['home'] else None,
            'overall_fg_pct': home_data['stats']['fg_pct'],
            'home_fg_pct': home_data['splits']['home']['fg_pct'] if home_data['splits']['home'] else None,
        },
        'pace_differential': None,  # Could calculate from data
        'strength_differential': away_data['stats']['points'] - home_data['stats']['points'],
    }

    return context


# Export main functions
__all__ = [
    'get_team_stats_for_matchup',
    'get_player_season_average',
    'get_team_matchup_context',
    'normalize_team_name',
    'get_team_slug'
]


# Test function
if __name__ == "__main__":
    import sys

    # Test matchup
    print("=" * 80)
    print("TESTING STATMUSE ADAPTER")
    print("=" * 80)
    print()

    # Test team stats
    print("Fetching team stats for Lakers @ Celtics...")
    away, home = get_team_stats_for_matchup("Los Angeles Lakers", "Boston Celtics", headless=False)

    if away and home:
        print("\nAWAY TEAM (Lakers):")
        print(f"  Overall: {away['stats']['points']} PPG, {away['stats']['rebounds']} RPG")
        if away['splits']['road']:
            print(f"  On Road: {away['splits']['road']['points']} PPG, {away['splits']['road']['rebounds']} RPG")

        print("\nHOME TEAM (Celtics):")
        print(f"  Overall: {home['stats']['points']} PPG, {home['stats']['rebounds']} RPG")
        if home['splits']['home']:
            print(f"  At Home: {home['splits']['home']['points']} PPG, {home['splits']['home']['rebounds']} RPG")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
