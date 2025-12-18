"""
Team IDs
========
StatMuse team ID lookups and mappings.

This module provides team ID resolution using StatMuse numeric IDs (e.g., 13, 5, etc.)
parsed from Statsmuse_nba_teams.txt.

CRITICAL: Slug is cosmetic only and never used for cache keys or logic.
Only the numeric ID is authoritative.
"""

import sys
from pathlib import Path
import re
import logging
from typing import Optional, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("team_ids")

# StatMuse team ID mapping: team_name (normalized) -> StatMuse numeric ID
# Populated by load_statmuse_team_ids_from_file()
STATMUSE_TEAM_IDS: Dict[str, int] = {}

# Slug to canonical team name mapping
# Used to convert URL slugs to normalized team names
SLUG_TO_TEAM_NAME: Dict[str, str] = {
    "detroit-pistons": "Detroit Pistons",
    "new-york-knicks": "New York Knicks",
    "toronto-raptors": "Toronto Raptors",
    "boston-celtics": "Boston Celtics",
    "orlando-magic": "Orlando Magic",
    "philadelphia-76ers": "Philadelphia 76ers",
    "cleveland-cavaliers": "Cleveland Cavaliers",
    "atlanta-hawks": "Atlanta Hawks",
    "miami-heat": "Miami Heat",
    "milwaukee-bucks": "Milwaukee Bucks",
    "chicago-bulls": "Chicago Bulls",
    "charlotte-hornets": "Charlotte Hornets",
    "brooklyn-nets": "Brooklyn Nets",
    "indiana-pacers": "Indiana Pacers",
    "washington-wizards": "Washington Wizards",
    "oklahoma-city-thunder": "Oklahoma City Thunder",
    "denver-nuggets": "Denver Nuggets",
    "los-angeles-lakers": "Los Angeles Lakers",
    "san-antonio-spurs": "San Antonio Spurs",
    "houston-rockets": "Houston Rockets",
    "minnesota-timberwolves": "Minnesota Timberwolves",
    "phoenix-suns": "Phoenix Suns",
    "golden-state-warriors": "Golden State Warriors",
    "memphis-grizzlies": "Memphis Grizzlies",
    "utah-jazz": "Utah Jazz",
    "portland-trail-blazers": "Portland Trail Blazers",
    "dallas-mavericks": "Dallas Mavericks",
    "sacramento-kings": "Sacramento Kings",
    "la-clippers": "LA Clippers",
    "los-angeles-clippers": "Los Angeles Clippers",  # Handle both variants
    "new-orleans-pelicans": "New Orleans Pelicans",
}

# Team abbreviations for matching
TEAM_ABBREVIATIONS: Dict[str, str] = {
    "ATL": "Atlanta Hawks",
    "BOS": "Boston Celtics",
    "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",
    "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks",
    "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors",
    "HOU": "Houston Rockets",
    "IND": "Indiana Pacers",
    "LAC": "LA Clippers",
    "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",
    "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans",
    "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",
    "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
}


def normalize_team_name(name: str) -> str:
    """
    Normalize team name to canonical format.
    
    Canonical format: Title Case, Full city + nickname, No abbreviations
    Examples:
        "LA Clippers" -> "Los Angeles Clippers"
        "detroit pistons" -> "Detroit Pistons"
        "LAL" -> "Los Angeles Lakers" (via abbreviation lookup)
    
    Args:
        name: Team name in any format
        
    Returns:
        Normalized team name in Title Case
    """
    name = name.strip()
    
    # Try abbreviation first
    name_upper = name.upper()
    if name_upper in TEAM_ABBREVIATIONS:
        name = TEAM_ABBREVIATIONS[name_upper]
    
    # Handle special cases
    if name.lower() == "la clippers":
        return "Los Angeles Clippers"
    
    # Title case normalization
    return name.title()


def load_statmuse_team_ids_from_file(file_path: Optional[Path] = None) -> Dict[str, int]:
    """
    Parse Statsmuse_nba_teams.txt to extract team name → StatMuse numeric ID mapping.
    
    URL format: https://www.statmuse.com/nba/team/2025-26-detroit-pistons-13/2026
    Extracts: slug (detroit-pistons) [cosmetic], ID (13) [authoritative]
    Maps to canonical team name using normalize_team_name()
    
    Args:
        file_path: Path to Statsmuse_nba_teams.txt. Defaults to workspace root.
    
    Returns:
        Dict mapping normalized team name to StatMuse numeric ID
    """
    if file_path is None:
        file_path = Path(__file__).parent.parent / "Statsmuse_nba_teams.txt"
    
    team_ids = {}
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith("http"):
                    continue
                
                # Extract slug and ID from URL
                # Pattern: https://www.statmuse.com/nba/team/2025-26-{slug}-{id}/2026
                match = re.search(r'/team/\d{4}-\d{2}-([^/]+)/', line)
                if not match:
                    continue
                
                slug_with_id = match.group(1)
                
                # Extract numeric ID (last number in slug, after last hyphen)
                # e.g., "detroit-pistons-13" -> ID = 13
                id_match = re.search(r'-(\d+)$', slug_with_id)
                if not id_match:
                    continue
                
                statmuse_id = int(id_match.group(1))
                
                # Extract slug without ID (cosmetic, not used in logic)
                slug = slug_with_id[:id_match.start()]
                
                # Map slug to canonical team name
                if slug in SLUG_TO_TEAM_NAME:
                    canonical_name = SLUG_TO_TEAM_NAME[slug]
                else:
                    # Fallback: convert slug to title case
                    # Replace hyphens with spaces, then title case
                    canonical_name = slug.replace("-", " ").title()
                
                # Normalize to ensure consistency
                canonical_name = normalize_team_name(canonical_name)
                
                team_ids[canonical_name] = statmuse_id
                logger.debug(f"Loaded: {canonical_name} -> {statmuse_id} (slug: {slug})")
        
        logger.info(f"Loaded {len(team_ids)} StatMuse team IDs from {file_path}")
        return team_ids
        
    except FileNotFoundError:
        logger.error(f"Statsmuse_nba_teams.txt not found at {file_path}")
        return {}
    except Exception as e:
        logger.error(f"Error parsing StatMuse team IDs: {e}")
        return {}


# Load team IDs on module import
STATMUSE_TEAM_IDS = load_statmuse_team_ids_from_file()


def get_team_id(team_name: str) -> Optional[int]:
    """
    Get StatMuse team ID from team name.
    
    Args:
        team_name: Team name in any format (full name, abbreviation, etc.)
    
    Returns:
        StatMuse numeric ID (e.g., 13, 5) or None if not found
    """
    # Normalize input
    normalized = normalize_team_name(team_name)
    
    # Try direct lookup
    if normalized in STATMUSE_TEAM_IDS:
        return STATMUSE_TEAM_IDS[normalized]
    
    # Try abbreviation
    team_upper = team_name.upper().strip()
    if team_upper in TEAM_ABBREVIATIONS:
        full_name = TEAM_ABBREVIATIONS[team_upper]
        if full_name in STATMUSE_TEAM_IDS:
            return STATMUSE_TEAM_IDS[full_name]
    
    # Try partial match (case-insensitive)
    team_lower = team_name.lower().strip()
    for full_name, team_id in STATMUSE_TEAM_IDS.items():
        if team_lower in full_name.lower() or full_name.lower() in team_lower:
            return team_id
    
    return None
