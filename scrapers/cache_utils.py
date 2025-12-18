"""
Cache Utilities
===============
Cache normalization utilities with numeric ID-based keys and season year extraction.

CRITICAL RULES:
- Cache keys MUST use numeric IDs only (never names, slugs, or URLs)
- Cache keys use integer season year (2026), never "2025-26" string format
- Display/URLs use "2025-26" string format
- Primary path: explicit mappings/registries only
- Fallback: string matching only when explicitly allowed
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_season_year(season: str) -> int:
    """
    Extract integer end year from season string.
    
    Canonical representation:
    - Cache keys → integer end year only (2026)
    - Display/URLs → "2025-26" string format
    
    Args:
        season: Season string like "2025-26" or "2024-25"
    
    Returns:
        Integer year (e.g., 2026 for "2025-26")
    
    Examples:
        extract_season_year("2025-26") -> 2026
        extract_season_year("2024-25") -> 2025
    """
    try:
        # Extract end year: "2025-26" -> "26" -> 2000 + 26 = 2026
        end_year_str = season.split("-")[1]
        return int(end_year_str) + 2000
    except (IndexError, ValueError) as e:
        logger.warning(f"Failed to extract season year from '{season}', using current year")
        from datetime import datetime
        return datetime.now().year


def normalize_season_for_cache(season: str) -> int:
    """
    Normalize season string to integer year for cache keys.
    
    Alias for extract_season_year() - explicit function name for cache operations.
    Always use this when building cache keys.
    
    Args:
        season: Season string like "2025-26"
    
    Returns:
        Integer year for cache keys
    """
    return extract_season_year(season)


def normalize_cache_key_by_id(entity_type: str, entity_id: int, season_year: int, data_type: str) -> str:
    """
    Generate cache key using numeric IDs only.
    
    CRITICAL: Never use names, slugs, or URLs in cache keys.
    
    Args:
        entity_type: "player" or "team"
        entity_id: Numeric ID (e.g., player_id=1629636, team_id=1610612737)
        season_year: Integer end year (e.g., 2026 for 2025-26 season) - NOT "2025-26" string
        data_type: Type of data ('game_log', 'minutes', 'usage', 'injuries', 'role', 'baseline')
    
    Returns:
        Cache key string: "{entity_type}_{entity_id}_{season_year}_{data_type}"
    
    Examples:
        normalize_cache_key_by_id("player", 1629636, 2026, "game_log")
        -> "player_1629636_2026_game_log"
        
        normalize_cache_key_by_id("team", 13, 2026, "stats")
        -> "team_13_2026_stats"  # Uses StatMuse ID (13 = Detroit Pistons)
    """
    if entity_type not in ["player", "team"]:
        raise ValueError(f"Invalid entity_type: '{entity_type}' (must be 'player' or 'team')")
    
    if not isinstance(entity_id, int) or entity_id <= 0:
        raise ValueError(f"Invalid entity_id: {entity_id} (must be positive integer)")
    
    if not isinstance(season_year, int) or season_year < 2000 or season_year > 2100:
        raise ValueError(f"Invalid season_year: {season_year} (must be integer between 2000-2100)")
    
    return f"{entity_type}_{entity_id}_{season_year}_{data_type}"


def get_entity_id(entity_type: str, name: str, allow_fallback: bool = False) -> Optional[int]:
    """
    Get numeric ID for player or team.
    
    PRIMARY PATH: Uses explicit mappings/registries only.
    FALLBACK: String matching only when allow_fallback=True (last resort).
    
    Args:
        entity_type: "player" or "team"
        name: Entity name (e.g., "LeBron James" or "Los Angeles Lakers")
        allow_fallback: If True, allow string matching as last resort (logs warning)
    
    Returns:
        Numeric ID or None if not found
    
    Examples:
        get_entity_id("player", "LeBron James") -> 2544
        get_entity_id("team", "Los Angeles Lakers") -> 15  # StatMuse ID
    """
    if entity_type == "player":
        try:
            from scrapers.nba_player_cache import get_player_cache
            cache = get_player_cache()
            player_id = cache.get_player_id(name)
            if player_id:
                return player_id
        except ImportError:
            logger.warning("nba_player_cache not available for player ID lookup")
        
        # Fallback string matching (only if allowed)
        if allow_fallback:
            logger.warning(f"[ID RESOLUTION] player='{name}' not found in registry, attempting fallback string matching")
            # Could implement fuzzy matching here if needed
            return None
        
        return None
    
    elif entity_type == "team":
        try:
            from scrapers.team_ids import get_team_id
            team_id = get_team_id(name)
            if team_id:
                return team_id
        except ImportError:
            logger.warning("team_ids not available for team ID lookup")
        
        # Fallback string matching (only if allowed)
        if allow_fallback:
            logger.warning(f"[ID RESOLUTION] team='{name}' resolved using fallback string matching (not ideal)")
            # Could implement abbreviation/partial matching here if needed
            return None
        
        return None
    
    else:
        raise ValueError(f"Invalid entity_type: '{entity_type}' (must be 'player' or 'team')")


def check_cache_before_scrape(cache_key: str, cache) -> Optional[dict]:
    """
    Check cache (hot cache then SQLite) before scraping.
    
    Args:
        cache_key: Normalized cache key (numeric ID-based)
        cache: DataCache instance
    
    Returns:
        Cached data dict or None if cache miss
    """
    # This function signature depends on DataCache implementation
    # For now, return None to indicate cache miss
    # Actual implementation will be done when integrating with DataCache
    logger.debug(f"[CACHE CHECK] Checking cache for key: {cache_key}")
    return None
