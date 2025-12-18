from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class GameLogEntry:
    """Single game entry from game log - Mirroring existing structure for compatibility"""
    game_date: str
    game_id: str
    matchup: str
    home_away: str
    opponent: str
    opponent_id: int
    won: bool
    minutes: float
    points: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    fg_made: int
    fg_attempted: int
    three_pt_made: int
    three_pt_attempted: int
    ft_made: int
    ft_attempted: int
    plus_minus: int
    team_points: int = 0
    opponent_points: int = 0
    total_points: int = 0

@dataclass
class ModelInput:
    """Standard input for all models"""
    player_name: str
    stat_type: str  # "points", "rebounds", etc.
    line: float
    game_log: List[GameLogEntry]
    opponent: str
    is_home: bool
    # Optional advanced stats that might be needed
    minutes_projected: Optional[float] = None
    team_pace: float = 100.0
    opponent_pace: float = 100.0
    opponent_def_rating: Optional[float] = None
    market_odds: Optional[float] = None  # Decimal odds (e.g. 1.90)
    implied_probability: Optional[float] = None

@dataclass
class ModelOutput:
    """Standard output from any model"""
    model_name: str
    expected_value: float
    probability_over: float  # The probability of going OVER the line
    confidence: float = 0.5  # 0.0 to 1.0
    weight: float = 1.0      # Suggested weight in final ensemble
    reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

