"""
StatMuse Team ID Mapping
=========================
Correct team IDs and URL formats extracted from actual StatMuse URLs.
"""

# Team name to StatMuse slug and ID mapping
TEAM_STATMUSE_MAPPING = {
    # Eastern Conference
    "Atlanta Hawks": {"slug": "atlanta-hawks", "id": "22", "url_prefix": "2025-26"},
    "Boston Celtics": {"slug": "boston-celtics", "id": "1", "url_prefix": "2025-26"},
    "Brooklyn Nets": {"slug": "brooklyn-nets", "id": "33", "url_prefix": "2025-26"},
    "Charlotte Hornets": {"slug": "charlotte-hornets", "id": "53", "url_prefix": "2025-26"},
    "Chicago Bulls": {"slug": "chicago-bulls", "id": "25", "url_prefix": "2025-26"},
    "Cleveland Cavaliers": {"slug": "cleveland-cavaliers", "id": "42", "url_prefix": "2025-26"},
    "Indiana Pacers": {"slug": "indiana-pacers", "id": "30", "url_prefix": "2025-26"},
    "Miami Heat": {"slug": "miami-heat", "id": "48", "url_prefix": "2025-26"},
    "Milwaukee Bucks": {"slug": "milwaukee-bucks", "id": "39", "url_prefix": "2025-26"},
    "New York Knicks": {"slug": "new-york-knicks", "id": "5", "url_prefix": "2025-26"},
    "Orlando Magic": {"slug": "orlando-magic", "id": "50", "url_prefix": "2025-26"},
    "Philadelphia 76ers": {"slug": "philadelphia-76ers", "id": "21", "url_prefix": "2025-26"},
    "Toronto Raptors": {"slug": "toronto-raptors", "id": "51", "url_prefix": "2025-26"},
    "Washington Wizards": {"slug": "washington-wizards", "id": "24", "url_prefix": "2025-26"},

    # Western Conference
    "Los Angeles Lakers": {"slug": "los-angeles-lakers", "id": "15", "url_prefix": "2025-26"},
    "Dallas Mavericks": {"slug": "dallas-mavericks", "id": "46", "url_prefix": "2025-26"},
    "Denver Nuggets": {"slug": "denver-nuggets", "id": "28", "url_prefix": "2025-26"},
    "Golden State Warriors": {"slug": "golden-state-warriors", "id": "6", "url_prefix": "2025-26"},
    "Houston Rockets": {"slug": "houston-rockets", "id": "37", "url_prefix": "2025-26"},
    "LA Clippers": {"slug": "la-clippers", "id": "41", "url_prefix": "2025-26"},
    "Los Angeles Clippers": {"slug": "la-clippers", "id": "41", "url_prefix": "2025-26"},
    "Memphis Grizzlies": {"slug": "memphis-grizzlies", "id": "52", "url_prefix": "2025-26"},
    "Minnesota Timberwolves": {"slug": "minnesota-timberwolves", "id": "49", "url_prefix": "2025-26"},
    "New Orleans Pelicans": {"slug": "new-orleans-pelicans", "id": "47", "url_prefix": "2025-26"},
    "Oklahoma City Thunder": {"slug": "oklahoma-city-thunder", "id": "38", "url_prefix": "2025-26"},
    "Phoenix Suns": {"slug": "phoenix-suns", "id": "40", "url_prefix": "2025-26"},
    "Portland Trail Blazers": {"slug": "portland-trail-blazers", "id": "43", "url_prefix": "2025-26"},
    "Sacramento Kings": {"slug": "sacramento-kings", "id": "16", "url_prefix": "2025-26"},
    "San Antonio Spurs": {"slug": "san-antonio-spurs", "id": "27", "url_prefix": "2025-26"},
    "Utah Jazz": {"slug": "utah-jazz", "id": "45", "url_prefix": "2025-26"},
}


def get_statmuse_url(team_name: str, season_year: str = "2026", endpoint: str = "") -> str:
    """
    Build correct StatMuse URL for a team.

    Args:
        team_name: Full team name (e.g., "Los Angeles Lakers")
        season_year: Season year (default: "2026" for 2025-26 season)
        endpoint: Optional endpoint like "/stats" or "/splits"

    Returns:
        Full StatMuse URL

    Examples:
        get_statmuse_url("Los Angeles Lakers")
        -> "https://www.statmuse.com/nba/team/los-angeles-lakers-15/2026"

        get_statmuse_url("Boston Celtics", endpoint="/stats")
        -> "https://www.statmuse.com/nba/team/2025-26-boston-celtics-1/stats/2026"
    """
    # Normalize team name
    team_name = team_name.strip()

    # Get team info
    team_info = TEAM_STATMUSE_MAPPING.get(team_name)
    if not team_info:
        # Try partial match
        for full_name, info in TEAM_STATMUSE_MAPPING.items():
            if team_name.lower() in full_name.lower():
                team_info = info
                break

    if not team_info or not team_info["id"]:
        raise ValueError(f"Team not found or ID missing: {team_name}")

    slug = team_info["slug"]
    team_id = team_info["id"]
    url_prefix = team_info["url_prefix"]

    # Build URL
    if url_prefix:
        team_part = f"{url_prefix}-{slug}-{team_id}"
    else:
        team_part = f"{slug}-{team_id}"

    base_url = f"https://www.statmuse.com/nba/team/{team_part}"

    if endpoint:
        # Insert endpoint before season year
        return f"{base_url}{endpoint}/{season_year}"
    else:
        return f"{base_url}/{season_year}"


def get_team_stats_url(team_name: str) -> str:
    """Get team stats page URL"""
    return get_statmuse_url(team_name, endpoint="/stats")


def get_team_splits_url(team_name: str) -> str:
    """Get team splits page URL"""
    return get_statmuse_url(team_name, endpoint="/splits")


if __name__ == "__main__":
    # Test URL generation
    print("Testing StatMuse URL generation:")
    print()

    test_teams = [
        "Los Angeles Lakers",
        "Boston Celtics",
        "Miami Heat",
        "New York Knicks"
    ]

    for team in test_teams:
        try:
            base_url = get_statmuse_url(team)
            stats_url = get_team_stats_url(team)
            splits_url = get_team_splits_url(team)

            print(f"{team}:")
            print(f"  Base:   {base_url}")
            print(f"  Stats:  {stats_url}")
            print(f"  Splits: {splits_url}")
            print()
        except ValueError as e:
            print(f"{team}: ERROR - {e}")
            print()
