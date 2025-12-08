"""
Player ID Cache (Databallr Source)
==================================
Manages a local cache of NBA player IDs from Databallr comprehensive cache.

Features:
- Loads from databallr_player_cache.json (comprehensive cache)
- Normalizes player names for consistent matching
- Supports fuzzy matching with Levenshtein distance
- Manual override table for edge cases
- Fast local lookups (no API calls needed)
- Uses Databallr and Sportsbet as data sources only
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
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
# Use databallr comprehensive cache as primary source
DATABALLR_CACHE_FILE = CACHE_DIR / "databallr_player_cache.json"
PLAYER_CACHE_FILE = DATABALLR_CACHE_FILE  # Alias for compatibility
MANUAL_OVERRIDES_FILE = CACHE_DIR / "nba_player_overrides.json"


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
    
    # Remove common suffixes (process longer ones first to avoid partial matches)
    # e.g., "iii" must be processed before "ii" to avoid "murphy iii" -> "murphy i"
    suffixes = ['jr.', 'jr', 'sr.', 'sr', 'iii', 'ii', 'iv', 'v']
    for suffix in suffixes:
        # Remove with comma and without, ensure word boundary at end
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
    DEPRECATED: This function is no longer used.
    Player cache is loaded from databallr_player_cache.json instead.
    
    Returns:
        Empty dict (function kept for compatibility)
    """
    logger.warning("build_player_cache() is deprecated - using databallr cache instead")
    return {}


def load_player_cache() -> Tuple[Dict[str, int], bool]:
    """
    Load player cache from databallr_player_cache.json
    
    Returns:
        (cache_dict, needs_refresh) where needs_refresh is always False (no auto-refresh)
    """
    # Try databallr cache first (primary source)
    if DATABALLR_CACHE_FILE.exists():
        try:
            with open(DATABALLR_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Extract name_to_id mapping from databallr cache structure
            # Databallr cache has: {'cache': {name: id}, 'display_names': {}, 'teams': {}, ...}
            name_to_id = cache_data.get('cache', {})
            
            if name_to_id:
                logger.info(f"Loaded player cache from databallr ({len(name_to_id)} entries)")
                return name_to_id, False  # Never needs refresh (no API)
            else:
                logger.warning(f"Databallr cache file exists but 'cache' key is empty")
                return {}, False
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing databallr cache JSON: {e}")
            return {}, False
        except UnicodeDecodeError as e:
            logger.error(f"Error reading databallr cache (encoding issue): {e}")
            return {}, False
        except Exception as e:
            logger.warning(f"Error loading databallr cache: {e}")
            return {}, False
    
    # Fallback to old nba_player_cache.json if databallr doesn't exist
    old_cache_file = CACHE_DIR / "nba_player_cache.json"
    if old_cache_file.exists():
        try:
            with open(old_cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            name_to_id = cache_data.get('cache', {})
            if name_to_id:
                logger.info(f"Loaded player cache from legacy nba cache ({len(name_to_id)} entries)")
                return name_to_id, False
        except Exception as e:
            logger.warning(f"Error loading legacy cache: {e}")
    
    logger.warning("No player cache file found. Please run build_comprehensive_player_cache.py")
    return {}, False


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
    """Manages player ID cache from Databallr comprehensive cache (no API calls)"""

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
        """Load cache from databallr_player_cache.json (no auto-refresh)"""
        # Load manual overrides first
        self.overrides = load_manual_overrides()
        
        # Load cache from databallr (no refresh needed - it's a static file)
        cache, _ = load_player_cache()
        self.cache = cache
        
        if self.cache:
            logger.info(f"Loaded player cache ({len(self.cache)} entries) from databallr")
        else:
            logger.warning("No player cache loaded. Please run build_comprehensive_player_cache.py to create cache.")
    
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

