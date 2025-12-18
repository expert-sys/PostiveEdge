"""
SQLite Persistent Cache System
===============================
Manages persistent caching of player data (minutes, usage, injuries, role) with TTL support.

Cache Strategy:
- Hot Cache: In-memory (current run)
- Warm Cache: SQLite (multi-run, persistent)
- Cold Cache: Historical baselines (permanent)
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry structure"""
    player_name: str
    team: str
    date: str
    data_type: str  # 'minutes', 'usage', 'injuries', 'role', 'baseline'
    source: str  # 'statsmuse', 'databallr', 'inferred'
    confidence_score: float
    data_json: Dict[str, Any]
    last_updated: datetime


class DataCache:
    """
    SQLite-based persistent cache for player data.
    
    TTL Rules:
    - Minutes/Usage: 24h
    - Injuries: 6h
    - Role flags: 48h
    - Game logs: 168h (7 days) - historical data that rarely changes
    - Historical baselines: Permanent (no TTL)
    """
    
    # TTL in hours
    TTL_MINUTES = 24
    TTL_USAGE = 24
    TTL_INJURIES = 6
    TTL_ROLE = 48
    TTL_GAME_LOG = 168  # 7 days
    TTL_BASELINE = None  # Permanent
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize cache database.
        
        Args:
            db_path: Path to SQLite database file (default: data/cache/player_data.db)
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "cache" / "player_data.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for database operations
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # In-memory hot cache (current run only)
        self._hot_cache: Dict[str, CacheEntry] = {}
        
        logger.debug(f"Cache initialized: {self.db_path}")
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player_data_cache (
                    player_name TEXT NOT NULL,
                    team TEXT NOT NULL,
                    date TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    data_json TEXT NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
                    PRIMARY KEY (player_name, team, date, data_type)
                )
            """)
            
            # Composite index for fast lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_player_lookup 
                ON player_data_cache(player_name, team, date, data_type)
            """)
            
            conn.commit()
    
    def _get_cache_key(self, player_name: str, team: str, date: str, data_type: str) -> str:
        """Generate cache key"""
        return f"{player_name}|{team}|{date}|{data_type}"
    
    def _get_ttl_hours(self, data_type: str) -> Optional[int]:
        """Get TTL in hours for data type"""
        ttl_map = {
            'minutes': self.TTL_MINUTES,
            'usage': self.TTL_USAGE,
            'injuries': self.TTL_INJURIES,
            'role': self.TTL_ROLE,
            'game_log': self.TTL_GAME_LOG,
            'baseline': self.TTL_BASELINE
        }
        return ttl_map.get(data_type, self.TTL_MINUTES)  # Default to 24h
    
    def get(
        self,
        player_name: str,
        team: str,
        date: str,
        data_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached data if valid.
        
        Args:
            player_name: Player name
            team: Team name
            date: Date string (YYYY-MM-DD)
            data_type: Type of data ('minutes', 'usage', 'injuries', 'role', 'baseline')
        
        Returns:
            Cached data dict with 'data', 'source', 'confidence_score', 'last_updated'
            or None if not found or expired
        """
        # Check hot cache first
        cache_key = self._get_cache_key(player_name, team, date, data_type)
        if cache_key in self._hot_cache:
            entry = self._hot_cache[cache_key]
            if self._is_valid(entry, data_type):
                ttl_remaining = self._get_ttl_remaining(entry, data_type)
                ttl_str = f"{ttl_remaining:.1f}h" if ttl_remaining is not None else "permanent"
                logger.debug(f"Cache hit (hot): {cache_key}")
                return {
                    'data': entry.data_json,
                    'source': entry.source,
                    'confidence_score': entry.confidence_score,
                    'last_updated': entry.last_updated.isoformat(),
                    'ttl_remaining_hours': ttl_remaining
                }
        
        # Check SQLite cache
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT source, confidence_score, data_json, last_updated
                    FROM player_data_cache
                    WHERE player_name = ? AND team = ? AND date = ? AND data_type = ?
                """, (player_name, team, date, data_type))
                
                row = cursor.fetchone()
                if row:
                    last_updated = datetime.fromisoformat(row['last_updated'])
                    entry = CacheEntry(
                        player_name=player_name,
                        team=team,
                        date=date,
                        data_type=data_type,
                        source=row['source'],
                        confidence_score=row['confidence_score'],
                        data_json=json.loads(row['data_json']),
                        last_updated=last_updated
                    )
                    
                    if self._is_valid(entry, data_type):
                        # Add to hot cache
                        self._hot_cache[cache_key] = entry
                        ttl_remaining = self._get_ttl_remaining(entry, data_type)
                        ttl_str = f"{ttl_remaining:.1f}h" if ttl_remaining is not None else "permanent"
                        logger.debug(f"Cache hit (SQLite): {cache_key}")
                        return {
                            'data': entry.data_json,
                            'source': entry.source,
                            'confidence_score': entry.confidence_score,
                            'last_updated': entry.last_updated.isoformat(),
                            'ttl_remaining_hours': ttl_remaining
                        }
                    else:
                        # Expired - remove from database
                        conn.execute("""
                            DELETE FROM player_data_cache
                            WHERE player_name = ? AND team = ? AND date = ? AND data_type = ?
                        """, (player_name, team, date, data_type))
                        conn.commit()
                        logger.debug(f"[CACHE] Expired entry removed: {cache_key}")
        
        logger.debug(f"Cache miss: {cache_key}")
        return None
    
    def set(
        self,
        player_name: str,
        team: str,
        date: str,
        data_type: str,
        data: Dict[str, Any],
        source: str,
        confidence_score: float
    ):
        """
        Store data in cache.
        
        Args:
            player_name: Player name
            team: Team name
            date: Date string (YYYY-MM-DD)
            data_type: Type of data
            data: Data to cache (dict)
            source: Data source ('statsmuse', 'databallr', 'inferred')
            confidence_score: Confidence in data (0.0-1.0)
        """
        cache_key = self._get_cache_key(player_name, team, date, data_type)
        now = datetime.now()
        
        entry = CacheEntry(
            player_name=player_name,
            team=team,
            date=date,
            data_type=data_type,
            source=source,
            confidence_score=confidence_score,
            data_json=data,
            last_updated=now
        )
        
        # Add to hot cache
        self._hot_cache[cache_key] = entry
        
        # Store in SQLite
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO player_data_cache
                    (player_name, team, date, data_type, source, confidence_score, data_json, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    player_name, team, date, data_type, source,
                    confidence_score, json.dumps(data), now.isoformat()
                ))
                conn.commit()
        
        logger.debug(f"[CACHE] Stored: {cache_key} (source={source}, conf={confidence_score:.2f})")
    
    def _is_valid(self, entry: CacheEntry, data_type: str) -> bool:
        """Check if cache entry is still valid (not expired)"""
        ttl_hours = self._get_ttl_hours(data_type)
        
        # Permanent entries (baselines) never expire
        if ttl_hours is None:
            return True
        
        age = datetime.now() - entry.last_updated
        return age < timedelta(hours=ttl_hours)
    
    def _get_ttl_remaining(self, entry: CacheEntry, data_type: str) -> Optional[float]:
        """
        Calculate TTL remaining in hours for a cache entry.
        
        Args:
            entry: Cache entry
            data_type: Type of data
        
        Returns:
            TTL remaining in hours, or None if permanent
        """
        ttl_hours = self._get_ttl_hours(data_type)
        if ttl_hours is None:
            return None  # Permanent
        
        age = datetime.now() - entry.last_updated
        remaining = timedelta(hours=ttl_hours) - age
        return max(0.0, remaining.total_seconds() / 3600.0)  # Convert to hours
    
    def invalidate(
        self,
        player_name: str,
        team: Optional[str] = None,
        date: Optional[str] = None,
        data_type: Optional[str] = None
    ):
        """
        Invalidate cache entries matching criteria.
        
        Args:
            player_name: Player name (required)
            team: Team name (optional, None = all teams)
            date: Date string (optional, None = all dates)
            data_type: Data type (optional, None = all types)
        """
        # Clear from hot cache
        keys_to_remove = []
        for key in self._hot_cache.keys():
            parts = key.split('|')
            if len(parts) == 4:
                p_name, p_team, p_date, p_type = parts
                if p_name == player_name:
                    if team is None or p_team == team:
                        if date is None or p_date == date:
                            if data_type is None or p_type == data_type:
                                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._hot_cache[key]
        
        # Remove from SQLite
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                if data_type:
                    conn.execute("""
                        DELETE FROM player_data_cache
                        WHERE player_name = ? AND (team = ? OR ? IS NULL)
                        AND (date = ? OR ? IS NULL) AND data_type = ?
                    """, (player_name, team, team, date, date, data_type))
                else:
                    conn.execute("""
                        DELETE FROM player_data_cache
                        WHERE player_name = ? AND (team = ? OR ? IS NULL)
                        AND (date = ? OR ? IS NULL)
                    """, (player_name, team, team, date, date))
                conn.commit()
        
        logger.debug(f"Cache invalidated: {player_name}" + (f" ({data_type})" if data_type else ""))
    
    def clear_hot_cache(self):
        """Clear in-memory hot cache (useful for testing)"""
        self._hot_cache.clear()
        logger.debug("[CACHE] Hot cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(DISTINCT player_name) as unique_players,
                    COUNT(DISTINCT data_type) as data_types
                FROM player_data_cache
            """)
            row = cursor.fetchone()
            
            # Count by data type
            cursor = conn.execute("""
                SELECT data_type, COUNT(*) as count
                FROM player_data_cache
                GROUP BY data_type
            """)
            by_type = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                'total_entries': row[0],
                'unique_players': row[1],
            'data_types': row[2],
            'by_type': by_type,
            'hot_cache_size': len(self._hot_cache)
            }
    
    def get_game_log(
        self,
        player_name: str,
        season: str,
        team: str = "N/A"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached game log for a player and season.
        
        Args:
            player_name: Player name
            season: Season string (e.g., "2024-25")
            team: Team name (optional, defaults to "N/A" for game logs)
        
        Returns:
            List of game log entries (as dicts) or None if not found/expired
        """
        cached = self.get(player_name, team, season, 'game_log')
        if cached:
            # Game logs are stored as a list in the 'data' field
            return cached['data'].get('games', [])
        return None
    
    def set_game_log(
        self,
        player_name: str,
        season: str,
        game_logs: List[Any],
        source: str,
        confidence_score: float,
        team: str = "N/A"
    ):
        """
        Store game log in cache.
        
        Args:
            player_name: Player name
            season: Season string (e.g., "2024-25")
            game_logs: List of GameLogEntry objects or dicts
            source: Data source ('statsmuse', 'databallr', 'inferred')
            confidence_score: Confidence in data (0.0-1.0)
            team: Team name (optional, defaults to "N/A" for game logs)
        """
        # Convert GameLogEntry objects to dicts if needed
        games_data = []
        for game in game_logs:
            if hasattr(game, 'to_dict'):
                games_data.append(game.to_dict())
            elif isinstance(game, dict):
                games_data.append(game)
            else:
                # Try to convert dataclass
                try:
                    games_data.append(asdict(game))
                except:
                    logger.warning(f"[CACHE] Could not serialize game log entry: {type(game)}")
                    continue
        
        # Store as dict with 'games' key
        data = {
            'games': games_data,
            'count': len(games_data),
            'season': season
        }
        
        self.set(
            player_name=player_name,
            team=team,
            date=season,  # Use season as "date" for game logs
            data_type='game_log',
            data=data,
            source=source,
            confidence_score=confidence_score
        )
        
        logger.debug(f"Stored game log: {player_name} ({season}), {len(games_data)} games")


# Global cache instance
_cache_instance: Optional[DataCache] = None


def get_cache(db_path: Optional[Path] = None) -> DataCache:
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DataCache(db_path)
    return _cache_instance
