"""
NBA Player ID Cache
===================
Manages a local cache of NBA player IDs to avoid repeated API calls.

Features:
- Downloads full player list once per day
- Normalizes player names for consistent matching
- Supports fuzzy matching with Levenshtein distance
- Manual override table for edge cases
- Fast local lookups (no API calls needed)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import requests
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path
import logging
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nba_player_cache")

# Cache file paths - ensure directory exists
def _get_cache_dir():
    """Get cache directory, creating it if needed"""
    cache_dir = Path(__file__).parent.parent / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

CACHE_DIR = _get_cache_dir()
PLAYER_CACHE_FILE = CACHE_DIR / "nba_player_cache.json"
MANUAL_OVERRIDES_FILE = CACHE_DIR / "nba_player_overrides.json"

# NBA API endpoint
NBA_STATS_API = "https://stats.nba.com/stats"
CACHE_EXPIRY_HOURS = 24  # Refresh cache once per day


def normalize_player_name(name: str) -> str:
    """
    Normalize player name for consistent matching
    
    Steps:
    1. Lowercase everything
    2. Remove punctuation
    3. Remove Jr., Sr., III, etc.
    4. Convert multiple spaces → one
    5. Trim whitespace
    """
    if not name:
        return ""
    
    # Lowercase
    normalized = name.lower()
    
    # Remove common suffixes
    suffixes = ['jr.', 'jr', 'sr.', 'sr', 'ii', 'iii', 'iv', 'v']
    for suffix in suffixes:
        # Remove with comma and without
        normalized = re.sub(rf',?\s*{re.escape(suffix)}\b', '', normalized, flags=re.IGNORECASE)
    
    # Remove punctuation
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    # Convert multiple spaces to one
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Trim whitespace
    normalized = normalized.strip()
    
    return normalized


def build_player_cache() -> Dict[str, int]:
    """
    Download full NBA player list and build cache
    
    Returns:
        Dictionary mapping normalized names to player IDs
    """
    logger.info("Building NBA player ID cache...")
    
    try:
        url = f"{NBA_STATS_API}/commonallplayers"
        params = {
            "LeagueID": "00",
            "Season": "2024-25",
            "IsOnlyCurrentSeason": "1"  # Only current season players
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.nba.com/",
            "Accept": "application/json"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        players = data.get("resultSets", [{}])[0].get("rowSet", [])
        
        cache = {}
        
        for player in players:
            if len(player) < 3:
                continue
            
            player_id = player[0]
            first_name = player[1] if len(player) > 1 else ""
            last_name = player[2] if len(player) > 2 else ""
            
            if not first_name or not last_name:
                continue
            
            # Create multiple normalized variations
            full_name = f"{first_name} {last_name}"
            last_first = f"{last_name}, {first_name}"
            last_only = last_name
            
            # Normalize each variation
            variations = [
                normalize_player_name(full_name),
                normalize_player_name(last_first),
                normalize_player_name(last_only),
                # Also add with underscore
                normalize_player_name(full_name).replace(' ', '_'),
            ]
            
            # Add all variations to cache
            for variation in variations:
                if variation and variation not in cache:
                    cache[variation] = player_id
        
        logger.info(f"Built cache with {len(cache)} name variations for {len(players)} players")
        return cache
        
    except Exception as e:
        logger.error(f"Error building player cache: {e}")
        return {}


def load_player_cache() -> Tuple[Dict[str, int], bool]:
    """
    Load player cache from file
    
    Returns:
        (cache_dict, needs_refresh) where needs_refresh is True if cache is expired
    """
    if not PLAYER_CACHE_FILE.exists():
        return {}, True
    
    try:
        with open(PLAYER_CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache is expired
        cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
        age = datetime.now() - cache_time
        
        if age > timedelta(hours=CACHE_EXPIRY_HOURS):
            logger.info(f"Player cache expired (age: {age})")
            return cache_data.get('cache', {}), True
        
        logger.info(f"Loaded player cache ({len(cache_data.get('cache', {}))} entries)")
        return cache_data.get('cache', {}), False
        
    except Exception as e:
        logger.warning(f"Error loading player cache: {e}")
        return {}, True


def save_player_cache(cache: Dict[str, int]):
    """Save player cache to file"""
    try:
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'cache': cache
        }
        
        with open(PLAYER_CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Saved player cache to {PLAYER_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error saving player cache: {e}")


def load_manual_overrides() -> Dict[str, int]:
    """Load manual override table"""
    if not MANUAL_OVERRIDES_FILE.exists():
        # Create default overrides file
        default_overrides = {
            "bogdan bogdanovic": 203992,
            "bojan bogdanovic": 202711,
            "kelly oubre": 1626162,
            "bob portis": 1626171  # Common misspelling of Bobby Portis
        }
        save_manual_overrides(default_overrides)
        return default_overrides
    
    try:
        with open(MANUAL_OVERRIDES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading manual overrides: {e}")
        return {}


def save_manual_overrides(overrides: Dict[str, int]):
    """Save manual override table"""
    try:
        with open(MANUAL_OVERRIDES_FILE, 'w') as f:
            json.dump(overrides, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving manual overrides: {e}")


def similarity_score(s1: str, s2: str) -> float:
    """Calculate similarity score between two strings (0.0 to 1.0)"""
    return SequenceMatcher(None, s1, s2).ratio()


def find_player_id_fuzzy(cache: Dict[str, int], normalized_name: str, threshold: float = 0.90) -> Optional[int]:
    """
    Find player ID using fuzzy matching
    
    Args:
        cache: Player cache dictionary
        normalized_name: Normalized player name to search for
        threshold: Minimum similarity score (0.0 to 1.0)
    
    Returns:
        Player ID if found, None otherwise
    """
    best_match = None
    best_score = 0.0
    
    # Token matching: "john collins" should match "collins john"
    name_tokens = set(normalized_name.split())
    
    for cached_name, player_id in cache.items():
        # Try exact match first
        if normalized_name == cached_name:
            return player_id
        
        # Calculate similarity
        score = similarity_score(normalized_name, cached_name)
        
        # Token matching bonus
        cached_tokens = set(cached_name.split())
        if name_tokens == cached_tokens:
            score = max(score, 0.95)  # High score for token match
        
        if score > best_score:
            best_score = score
            best_match = player_id
    
    # Return if above threshold
    if best_score >= threshold:
        logger.debug(f"Fuzzy match: '{normalized_name}' -> score {best_score:.2f}")
        return best_match
    
    return None


class PlayerIDCache:
    """Manages NBA player ID cache with automatic refresh"""

    def __init__(self):
        self.cache: Dict[str, int] = {}
        self.overrides: Dict[str, int] = {}
        # Performance tracking
        self.stats = {
            'total_lookups': 0,
            'cache_hits': 0,
            'override_hits': 0,
            'fuzzy_hits': 0,
            'misses': 0,
            'failed_lookups': []  # Track failed lookups for manual override additions
        }
        self._load_cache()
    
    def _load_cache(self):
        """Load cache and overrides"""
        # Load manual overrides first
        self.overrides = load_manual_overrides()
        
        # Load cache
        cache, needs_refresh = load_player_cache()
        self.cache = cache
        
        # Refresh if needed
        if needs_refresh or not self.cache:
            print("\n[INIT] Building NBA player ID cache (one-time setup)...")
            logger.info("Refreshing player cache...")
            new_cache = build_player_cache()
            if new_cache:
                self.cache = new_cache
                save_player_cache(new_cache)
                print(f"[OK] Player cache built: {len(new_cache)} name variations")
            else:
                print("[WARNING] Could not build player cache - will use fallback methods")
        else:
            logger.debug(f"Using cached player data ({len(self.cache)} entries)")
    
    def get_player_id(self, player_name: str) -> Optional[int]:
        """
        Get player ID from cache

        Args:
            player_name: Player name (any format)

        Returns:
            Player ID or None if not found
        """
        # Track statistics
        self.stats['total_lookups'] += 1

        # Normalize name
        normalized = normalize_player_name(player_name)

        if not normalized:
            self.stats['misses'] += 1
            return None

        # Check manual overrides first
        if normalized in self.overrides:
            self.stats['override_hits'] += 1
            return self.overrides[normalized]

        # Check cache (exact match)
        if normalized in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[normalized]

        # Try fuzzy matching
        fuzzy_match = find_player_id_fuzzy(self.cache, normalized, threshold=0.90)
        if fuzzy_match:
            self.stats['fuzzy_hits'] += 1
            return fuzzy_match

        # Not found - track for potential manual override
        self.stats['misses'] += 1
        if normalized not in self.stats['failed_lookups']:
            self.stats['failed_lookups'].append(normalized)
            logger.warning(f"Player not found in cache: '{player_name}' (normalized: '{normalized}')")

        return None
    
    def add_override(self, player_name: str, player_id: int):
        """Add a manual override entry"""
        normalized = normalize_player_name(player_name)
        self.overrides[normalized] = player_id
        save_manual_overrides(self.overrides)
        logger.info(f"Added manual override: '{normalized}' -> {player_id}")

    def get_statistics(self) -> Dict:
        """
        Get cache performance statistics

        Returns:
            Dictionary with cache hit rates and failed lookups
        """
        total = self.stats['total_lookups']
        if total == 0:
            return {
                'total_lookups': 0,
                'hit_rate': 0.0,
                'cache_hits': 0,
                'override_hits': 0,
                'fuzzy_hits': 0,
                'misses': 0,
                'failed_lookups': []
            }

        hits = self.stats['cache_hits'] + self.stats['override_hits'] + self.stats['fuzzy_hits']
        hit_rate = (hits / total) * 100

        return {
            'total_lookups': total,
            'hit_rate': round(hit_rate, 2),
            'cache_hits': self.stats['cache_hits'],
            'override_hits': self.stats['override_hits'],
            'fuzzy_hits': self.stats['fuzzy_hits'],
            'misses': self.stats['misses'],
            'failed_lookups': list(set(self.stats['failed_lookups']))  # Unique failed lookups
        }

    def print_statistics(self):
        """Print formatted cache statistics"""
        stats = self.get_statistics()

        print("\n" + "="*70)
        print("  NBA PLAYER CACHE STATISTICS")
        print("="*70)
        print(f"Total Lookups:    {stats['total_lookups']}")
        print(f"Hit Rate:         {stats['hit_rate']}%")
        print(f"  - Cache Hits:   {stats['cache_hits']} (exact match)")
        print(f"  - Override Hits: {stats['override_hits']} (manual)")
        print(f"  - Fuzzy Hits:   {stats['fuzzy_hits']} (fuzzy match)")
        print(f"  - Misses:       {stats['misses']}")

        if stats['failed_lookups']:
            print(f"\nFailed Lookups ({len(stats['failed_lookups'])}):")
            for name in stats['failed_lookups'][:10]:  # Show first 10
                print(f"  • {name}")
            if len(stats['failed_lookups']) > 10:
                print(f"  ... and {len(stats['failed_lookups']) - 10} more")
        print("="*70 + "\n")


# Global cache instance
_player_cache_instance: Optional[PlayerIDCache] = None
_cache_initialized = False


def initialize_cache():
    """Initialize the player cache (called on module import)"""
    global _cache_initialized
    if not _cache_initialized:
        try:
            # Ensure cache directory exists
            _get_cache_dir()
            _cache_initialized = True
            logger.debug("Player cache system initialized")
        except Exception as e:
            logger.warning(f"Error initializing cache directory: {e}")


def get_player_cache() -> PlayerIDCache:
    """Get global player cache instance (singleton)"""
    global _player_cache_instance
    initialize_cache()  # Ensure cache is initialized
    if _player_cache_instance is None:
        _player_cache_instance = PlayerIDCache()
    return _player_cache_instance


# Initialize on module import
initialize_cache()


if __name__ == "__main__":
    # Test the cache
    print("\n" + "="*70)
    print("  NBA PLAYER ID CACHE TEST")
    print("="*70 + "\n")
    
    cache = get_player_cache()
    
    # Test various name formats
    test_names = [
        "LeBron James",
        "lebron james",
        "LeBron James Jr.",
        "Gary Trent Jr.",
        "gary trent jr",
        "John Collins",
        "collins, john",
        "Bogdan Bogdanovic",
        "bob portis"  # Should use override
    ]
    
    for name in test_names:
        player_id = cache.get_player_id(name)
        if player_id:
            print(f"✓ '{name}' -> {player_id}")
        else:
            print(f"✗ '{name}' -> Not found")

