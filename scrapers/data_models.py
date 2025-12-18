"""
Data Models
===========
Shared data structures for player and team statistics.

These models are source-agnostic and can be populated from any data source
(StatsMuse, DataballR, etc.).
"""

from dataclasses import dataclass, asdict


@dataclass
class GameLogEntry:
    """Single game entry from game log"""
    game_date: str
    game_id: str
    matchup: str  # "LAL vs. BOS" or "LAL @ BOS"
    home_away: str  # "HOME" or "AWAY"
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
    team_points: int  # For team logs
    opponent_points: int  # For team logs
    total_points: int  # team_points + opponent_points
    
    def to_dict(self):
        return asdict(self)
