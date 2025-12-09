"""
Betting Recommendation Data Model
==================================
Data structure for betting recommendations with all analysis and metadata.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict


@dataclass
class BettingRecommendation:
    """
    Final betting recommendation with all analysis.
    
    This dataclass represents a complete betting recommendation including:
    - Game and bet details
    - Player information (if player prop)
    - Statistical analysis and projections
    - Value metrics and confidence scores
    - Supporting data from various sources
    """
    # Game context
    game: str
    match_time: str
    
    # Bet details
    bet_type: str  # 'team_total', 'team_spread', 'team_moneyline', 'player_prop'
    market: str
    selection: str
    odds: float
    
    # Player-specific (if player prop)
    player_name: Optional[str] = None
    player_team: Optional[str] = None  # Player's team
    opponent_team: Optional[str] = None  # Opponent team
    stat_type: Optional[str] = None
    line: Optional[float] = None
    
    # Analysis
    sportsbet_insight: Optional[str] = None
    historical_hit_rate: float = 0.0
    sample_size: int = 0
    
    # Projections
    projected_value: Optional[float] = None
    projected_probability: float = 0.0
    model_confidence: float = 0.0
    
    # Value metrics
    implied_probability: float = 0.0
    edge_percentage: float = 0.0
    expected_value: float = 0.0
    
    # Final score
    confidence_score: float = 0.0
    recommendation_strength: str = "MEDIUM"  # LOW, MEDIUM, HIGH, VERY_HIGH
    
    # Supporting data
    databallr_stats: Optional[Dict] = None
    matchup_factors: Optional[Dict] = None
    advanced_context: Optional[Dict] = None  # Advanced contextual factors
    
    def to_dict(self) -> Dict:
        """
        Convert the recommendation to a dictionary.
        
        Returns:
            Dictionary representation of the recommendation
        """
        return asdict(self)

