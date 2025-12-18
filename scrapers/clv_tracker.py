"""
CLV (Closing Line Value) Tracking System
=========================================
Tracks opening vs closing lines and results for bet validation.

Features:
- Record bets at creation time (opening line)
- Update with closing line (post-game)
- Record results (win/loss/push)
- Calculate CLV metrics by tier/confidence
- Flag variance (good CLV + loss) and luck (bad CLV + win)
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import threading
import uuid

logger = logging.getLogger(__name__)


@dataclass
class CLVBetRecord:
    """CLV tracking record for a bet"""
    bet_id: str
    game_date: str
    market: str
    player_name: Optional[str]
    opening_line: float
    opening_odds: float
    closing_line: Optional[float]
    closing_odds: Optional[float]
    model_probability: float
    model_edge: float
    confidence: float
    tier: str
    result: Optional[str]  # 'WIN', 'LOSS', 'PUSH'
    clv: Optional[float]  # closing_line - opening_line (for props)
    clv_percentage: Optional[float]  # (closing_odds - opening_odds) / opening_odds
    variance_flag: bool = False  # Good CLV + Lost (variance)
    luck_flag: bool = False  # Bad CLV + Won (luck)
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class CLVTracker:
    """
    SQLite-based CLV tracking system.
    
    Tracks:
    - Opening vs closing lines/odds
    - Results (win/loss/push)
    - CLV metrics by tier/confidence
    - Variance and luck flags
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize CLV tracker.
        
        Args:
            db_path: Path to SQLite database (default: data/clv_tracking.db)
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "clv_tracking.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for database operations
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"[CLV] Initialized CLV tracker at {self.db_path}")
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            # Main CLV tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clv_tracking (
                    bet_id TEXT PRIMARY KEY,
                    game_date DATE NOT NULL,
                    market TEXT NOT NULL,
                    player_name TEXT,
                    opening_line REAL NOT NULL,
                    opening_odds REAL NOT NULL,
                    closing_line REAL,
                    closing_odds REAL,
                    model_probability REAL NOT NULL,
                    model_edge REAL NOT NULL,
                    confidence REAL NOT NULL,
                    tier TEXT NOT NULL,
                    result TEXT,
                    clv REAL,
                    clv_percentage REAL,
                    variance_flag INTEGER DEFAULT 0,
                    luck_flag INTEGER DEFAULT 0,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
            
            # Metrics aggregation table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clv_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    tier TEXT NOT NULL,
                    confidence_bucket TEXT NOT NULL,
                    total_bets INTEGER NOT NULL,
                    wins INTEGER NOT NULL,
                    hit_rate REAL,
                    avg_clv REAL,
                    positive_clv_count INTEGER,
                    variance_flag_count INTEGER,
                    luck_flag_count INTEGER,
                    created_at TIMESTAMP NOT NULL,
                    UNIQUE(date, tier, confidence_bucket)
                )
            """)
            
            # Indexes for fast lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_game_date ON clv_tracking(game_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tier ON clv_tracking(tier)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_result ON clv_tracking(result)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_date ON clv_metrics(date)")
            
            conn.commit()
    
    def generate_bet_id(self) -> str:
        """Generate unique bet ID"""
        return str(uuid.uuid4())
    
    def record_bet(
        self,
        bet: Dict[str, Any],
        opening_line: Optional[float] = None,
        opening_odds: Optional[float] = None
    ) -> str:
        """
        Record bet at creation time.
        
        Args:
            bet: Bet dictionary
            opening_line: Opening line (for props)
            opening_odds: Opening odds
        
        Returns:
            bet_id (generated or existing)
        """
        bet_id = bet.get('bet_id')
        if not bet_id:
            bet_id = self.generate_bet_id()
            bet['bet_id'] = bet_id
        
        # Extract opening line/odds from bet if not provided
        if opening_line is None:
            opening_line = bet.get('line') or bet.get('market_line') or 0.0
        if opening_odds is None:
            opening_odds = bet.get('odds', 0.0)
        
        # Extract other fields
        game_date = bet.get('game_date') or bet.get('match_time') or datetime.now().strftime('%Y-%m-%d')
        market = bet.get('market') or bet.get('market_name') or 'Unknown'
        player_name = bet.get('player_name') or bet.get('player')
        model_prob = bet.get('final_prob') or bet.get('projected_probability') or bet.get('historical_probability', 0.5)
        model_edge = bet.get('edge', 0.0)  # Edge percentage
        confidence = bet.get('confidence', 0.0)
        tier = bet.get('tier', 'WATCHLIST')
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO clv_tracking
                    (bet_id, game_date, market, player_name, opening_line, opening_odds,
                     model_probability, model_edge, confidence, tier, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bet_id, game_date, market, player_name,
                    opening_line, opening_odds, model_prob, model_edge,
                    confidence, tier, datetime.now().isoformat(), datetime.now().isoformat()
                ))
                conn.commit()
        
        logger.debug(f"[CLV] Recorded bet {bet_id}: {market} (opening odds: {opening_odds:.2f})")
        return bet_id
    
    def update_closing(
        self,
        bet_id: str,
        closing_line: Optional[float] = None,
        closing_odds: Optional[float] = None
    ):
        """
        Update bet with closing line/odds.
        
        Args:
            bet_id: Bet ID
            closing_line: Closing line (for props)
            closing_odds: Closing odds
        """
        # Get opening values to calculate CLV
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT opening_line, opening_odds
                FROM clv_tracking
                WHERE bet_id = ?
            """, (bet_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"[CLV] Bet {bet_id} not found for closing update")
                return
            
            opening_line = row['opening_line']
            opening_odds = row['opening_odds']
        
        # Calculate CLV
        clv = None
        clv_percentage = None
        
        if closing_line is not None and opening_line > 0:
            clv = closing_line - opening_line
        
        if closing_odds is not None and opening_odds > 0:
            clv_percentage = ((closing_odds - opening_odds) / opening_odds) * 100
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE clv_tracking
                    SET closing_line = ?, closing_odds = ?, clv = ?, clv_percentage = ?,
                        updated_at = ?
                    WHERE bet_id = ?
                """, (
                    closing_line, closing_odds, clv, clv_percentage,
                    datetime.now().isoformat(), bet_id
                ))
                conn.commit()
        
        logger.debug(f"[CLV] Updated closing for bet {bet_id}: line={closing_line}, odds={closing_odds:.2f}, CLV={clv_percentage:+.2f}%")
    
    def record_result(
        self,
        bet_id: str,
        result: str  # 'WIN', 'LOSS', 'PUSH'
    ):
        """
        Record bet result.
        
        Args:
            bet_id: Bet ID
            result: 'WIN', 'LOSS', or 'PUSH'
        """
        result = result.upper()
        if result not in ['WIN', 'LOSS', 'PUSH']:
            logger.warning(f"[CLV] Invalid result: {result}, must be WIN/LOSS/PUSH")
            return
        
        # Get CLV and result to flag variance/luck
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT clv_percentage, result as current_result
                FROM clv_tracking
                WHERE bet_id = ?
            """, (bet_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"[CLV] Bet {bet_id} not found for result update")
                return
            
            clv_pct = row['clv_percentage']
            current_result = row['current_result']
            
            # Flag variance (good CLV + loss) or luck (bad CLV + win)
            variance_flag = False
            luck_flag = False
            
            if clv_pct is not None:
                if clv_pct > 0 and result == 'LOSS':
                    variance_flag = True  # Good CLV but lost (variance)
                elif clv_pct < -2 and result == 'WIN':  # Bad CLV (line moved against us)
                    luck_flag = True  # Bad CLV but won (luck)
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE clv_tracking
                    SET result = ?, variance_flag = ?, luck_flag = ?, updated_at = ?
                    WHERE bet_id = ?
                """, (
                    result, 1 if variance_flag else 0, 1 if luck_flag else 0,
                    datetime.now().isoformat(), bet_id
                ))
                conn.commit()
        
        logger.debug(f"[CLV] Recorded result for bet {bet_id}: {result}" + 
                    (f" (variance)" if variance_flag else "") +
                    (f" (luck)" if luck_flag else ""))
    
    def get_clv_metrics(
        self,
        days: int = 30,
        tier: Optional[str] = None,
        confidence_bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated CLV metrics.
        
        Args:
            days: Number of days to look back
            tier: Optional tier filter ('A', 'B', 'C')
            confidence_bucket: Optional confidence bucket ('HIGH', 'MEDIUM', 'LOW')
        
        Returns:
            Dictionary with aggregated metrics
        """
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build query
            query = """
                SELECT 
                    tier,
                    CASE
                        WHEN confidence >= 65 THEN 'HIGH'
                        WHEN confidence >= 50 THEN 'MEDIUM'
                        ELSE 'LOW'
                    END as confidence_bucket,
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    AVG(clv_percentage) as avg_clv,
                    SUM(CASE WHEN clv_percentage > 0 THEN 1 ELSE 0 END) as positive_clv_count,
                    SUM(variance_flag) as variance_flag_count,
                    SUM(luck_flag) as luck_flag_count
                FROM clv_tracking
                WHERE game_date >= ? AND result IS NOT NULL
            """
            params = [date_from]
            
            if tier:
                query += " AND tier = ?"
                params.append(tier)
            
            if confidence_bucket:
                query += " AND CASE WHEN confidence >= 65 THEN 'HIGH' WHEN confidence >= 50 THEN 'MEDIUM' ELSE 'LOW' END = ?"
                params.append(confidence_bucket)
            
            query += " GROUP BY tier, confidence_bucket"
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            metrics = []
            for row in rows:
                hit_rate = row['wins'] / row['total_bets'] if row['total_bets'] > 0 else 0.0
                metrics.append({
                    'tier': row['tier'],
                    'confidence_bucket': row['confidence_bucket'],
                    'total_bets': row['total_bets'],
                    'wins': row['wins'],
                    'hit_rate': round(hit_rate, 3),
                    'avg_clv': round(row['avg_clv'] or 0.0, 2),
                    'positive_clv_count': row['positive_clv_count'] or 0,
                    'variance_flag_count': row['variance_flag_count'] or 0,
                    'luck_flag_count': row['luck_flag_count'] or 0
                })
            
            return {
                'period_days': days,
                'date_from': date_from,
                'metrics': metrics
            }
    
    def flag_variance_luck(self, bet_id: str):
        """
        Flag bet as variance (good CLV + loss) or luck (bad CLV + win).
        
        Called automatically by record_result, but can be called manually.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT clv_percentage, result
                FROM clv_tracking
                WHERE bet_id = ?
            """, (bet_id,))
            row = cursor.fetchone()
            
            if not row or not row['result']:
                return
            
            clv_pct = row['clv_percentage']
            result = row['result']
            
            variance_flag = False
            luck_flag = False
            
            if clv_pct is not None:
                if clv_pct > 0 and result == 'LOSS':
                    variance_flag = True
                elif clv_pct < -2 and result == 'WIN':
                    luck_flag = True
            
            conn.execute("""
                UPDATE clv_tracking
                SET variance_flag = ?, luck_flag = ?
                WHERE bet_id = ?
            """, (1 if variance_flag else 0, 1 if luck_flag else 0, bet_id))
            conn.commit()


# Global tracker instance
_tracker_instance: Optional[CLVTracker] = None


def get_clv_tracker(db_path: Optional[Path] = None) -> CLVTracker:
    """Get or create global CLV tracker instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = CLVTracker(db_path)
    return _tracker_instance
