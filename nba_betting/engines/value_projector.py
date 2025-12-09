"""
Value Projector Engine
======================
Projects betting value using statistical models and calculates confidence scores.
"""

import logging
from typing import Dict, Optional

from models import BettingRecommendation
from config import Config

logger = logging.getLogger(__name__)


class ValueProjector:
    """Projects betting value using statistical models"""
    
    def __init__(self):
        self._init_models()
    
    def _init_models(self):
        """Initialize projection models"""
        try:
            from scrapers.player_projection_model import PlayerProjectionModel
            self.player_model = PlayerProjectionModel()
            logger.info("✓ Player projection model initialized")
        except ImportError:
            logger.warning("Player projection model not available")
            self.player_model = None
        
        # Initialize V2 confidence engine
        try:
            from confidence_engine_v2 import ConfidenceEngineV2
            self.confidence_engine = ConfidenceEngineV2()
            logger.info("✓ Confidence Engine V2 initialized")
        except ImportError:
            logger.warning("Confidence Engine V2 not available")
            self.confidence_engine = None
        
        # Initialize matchup engine
        try:
            from matchup_engine import MatchupEngine
            self.matchup_engine = MatchupEngine()
            logger.info("✓ Matchup Engine initialized")
        except ImportError:
            logger.warning("Matchup Engine not available")
            self.matchup_engine = None
    
    def project_player_prop(
        self,
        player_name: str,
        stat_type: str,
        line: float,
        odds: float,
        databallr_stats: Dict,
        match_stats: Optional[Dict] = None
    ) -> Optional[BettingRecommendation]:
        """
        Project value for a player prop using model + historical data
        
        Combines:
        - Statistical projection model (70% weight)
        - Historical hit rate from DataBallr (30% weight)
        """
        if not self.player_model:
            logger.warning(f"  {player_name}: Player projection model not available")
            return None
        
        if not databallr_stats:
            logger.warning(f"  {player_name}: No DataBallr stats provided")
            return None
        
        try:
            game_log = databallr_stats.get('game_log')
            historical_hit_rate = databallr_stats.get('hit_rate', 0.5)
            
            if not game_log:
                logger.warning(f"  {player_name}: No game log in DataBallr stats")
                return None
            
            # Get model projection
            projection = self.player_model.project_stat(
                player_name=player_name,
                stat_type=stat_type,
                game_log=game_log,
                prop_line=line,
                team_stats=match_stats,
                min_games=5
            )
            
            if not projection:
                logger.debug(f"  {player_name}: Projection model returned None (likely insufficient games or model error)")
                return None
            
            # Combine model (70%) + historical (30%)
            model_prob = projection.probability_over_line
            final_prob = Config.MODEL_CONFIDENCE_WEIGHT * model_prob + Config.HISTORICAL_WEIGHT * historical_hit_rate
            
            # Calculate value metrics
            implied_prob = 1.0 / odds
            edge = final_prob - implied_prob
            ev = (final_prob * (odds - 1)) - (1 - final_prob)
            
            # Use V2 confidence engine if available
            if self.confidence_engine:
                # Extract volatility data
                stat_mean = databallr_stats['avg_value']
                stat_std_dev = projection.std_dev if projection.std_dev else stat_mean * 0.25
                
                # Check minutes stability
                minutes_stable = True
                role_change_detected = False
                if projection.minutes_projection:
                    minutes_stable = projection.minutes_projection.volatility < 8.0
                if projection.role_change:
                    role_change_detected = projection.role_change.detected
                
                # Get enhanced matchup factors from matchup engine
                matchup_factors = None
                if self.matchup_engine and match_stats:
                    # Determine teams
                    away_team = match_stats.away_team_stats.team_name if hasattr(match_stats, 'away_team_stats') else "Unknown"
                    home_team = match_stats.home_team_stats.team_name if hasattr(match_stats, 'home_team_stats') else "Unknown"
                    
                    # Try to determine which team player is on
                    # This is a simplified approach - in production, track this properly
                    player_team = away_team  # Default assumption
                    opponent_team = home_team
                    
                    try:
                        from matchup_engine import get_matchup_factors_for_confidence
                        matchup_factors = get_matchup_factors_for_confidence(
                            player_name=player_name,
                            stat_type=stat_type,
                            opponent_team=opponent_team,
                            player_team=player_team,
                            game_log=game_log
                        )
                        logger.debug(f"  Matchup factors: {matchup_factors}")
                    except Exception as e:
                        logger.debug(f"  Could not get matchup factors: {e}")
                        # Fallback to projection matchup adjustments
                        if projection.matchup_adjustments:
                            matchup_factors = {
                                'pace_multiplier': projection.matchup_adjustments.pace_multiplier,
                                'defense_adjustment': projection.matchup_adjustments.defense_adjustment
                            }
                elif projection.matchup_adjustments:
                    # Fallback to projection matchup adjustments
                    matchup_factors = {
                        'pace_multiplier': projection.matchup_adjustments.pace_multiplier,
                        'defense_adjustment': projection.matchup_adjustments.defense_adjustment
                    }
                
                # Calculate V2 confidence
                confidence_result = self.confidence_engine.calculate_confidence(
                    sample_size=databallr_stats['sample_size'],
                    historical_hit_rate=historical_hit_rate,
                    projected_probability=final_prob,
                    stat_mean=stat_mean,
                    stat_std_dev=stat_std_dev,
                    minutes_stable=minutes_stable,
                    role_change_detected=role_change_detected,
                    matchup_factors=matchup_factors,
                    injury_context=None
                )
                
                confidence = confidence_result.final_confidence
                final_prob = confidence_result.adjusted_probability
                
                # Recalculate edge and EV with adjusted probability
                edge = final_prob - implied_prob
                ev = (final_prob * (odds - 1)) - (1 - final_prob)
            else:
                # Fallback to old confidence calculation
                confidence = self._calculate_confidence(
                    model_confidence=projection.confidence_score,
                    sample_size=databallr_stats['sample_size'],
                    edge_pct=edge * 100
                )
            
            # Determine recommendation strength
            strength = self._get_recommendation_strength(confidence, ev * 100)
            
            # Relaxed filtering: Let more bets through to enhanced filtering stage
            # Enhanced filtering will apply stricter quality filters
            min_confidence = Config.MIN_CONFIDENCE if self.confidence_engine else Config.MIN_CONFIDENCE + 5
            
            # Allow slightly negative EV (-2%) to pass through, enhanced filtering will handle quality
            min_ev = -0.02  # Allow up to -2% EV
            
            # Log why recommendation might be rejected
            if ev <= min_ev:
                logger.debug(f"  {player_name}: EV={ev:.2%} (below {min_ev:.2%} threshold, rejecting)")
            if confidence < min_confidence:
                logger.debug(f"  {player_name}: Confidence={confidence:.0f}% < {min_confidence}% (rejecting)")
            
            # Relaxed criteria: confidence >= min AND EV > min_ev (allows slightly negative EV)
            if ev > min_ev and confidence >= min_confidence:
                logger.debug(f"  {player_name}: ✓ Creating recommendation (EV={ev:.2%}, Confidence={confidence:.0f}%)")
                return BettingRecommendation(
                    game=f"{player_name}'s game",
                    match_time="TBD",
                    bet_type="player_prop",
                    market=f"{stat_type.replace('_', ' ').title()}",
                    selection=f"Over {line}",
                    odds=odds,
                    player_name=player_name,
                    stat_type=stat_type,
                    line=line,
                    historical_hit_rate=historical_hit_rate,
                    sample_size=databallr_stats['sample_size'],
                    projected_value=projection.expected_value,
                    projected_probability=final_prob,
                    model_confidence=projection.confidence_score,
                    implied_probability=implied_prob,
                    edge_percentage=edge * 100,
                    expected_value=ev * 100,
                    confidence_score=confidence,
                    recommendation_strength=strength,
                    databallr_stats={
                        'avg_value': databallr_stats['avg_value'],
                        'trend': databallr_stats['trend'],
                        'recent_avg': databallr_stats['recent_avg']
                    }
                )
            
            logger.debug(f"  {player_name}: ✗ Rejected (EV={ev:.2%}, Confidence={confidence:.0f}%, Min={min_confidence}%)")
            return None
            
        except Exception as e:
            logger.debug(f"  Error projecting {player_name}: {e}")
            return None
    
    def _calculate_confidence(self, model_confidence: float, sample_size: int, edge_pct: float) -> float:
        """Calculate final confidence score"""
        import math
        
        # Base from model
        confidence = model_confidence
        
        # Boost for sample size
        if sample_size >= Config.SAMPLE_SIZE_LARGE:
            confidence += 5
        elif sample_size >= Config.SAMPLE_SIZE_MEDIUM:
            confidence += 3
        
        # Boost for edge
        if edge_pct > Config.HIGH_EDGE:
            confidence += 5
        elif edge_pct > Config.MEDIUM_EDGE:
            confidence += 3
        
        return min(95, confidence)
    
    def _get_recommendation_strength(self, confidence: float, ev_pct: float) -> str:
        """Determine recommendation strength (updated for V2 realistic confidence)"""
        # Use configurable thresholds from Config
        if confidence >= Config.VERY_HIGH_CONFIDENCE and ev_pct >= Config.VERY_HIGH_EDGE:
            return "VERY_HIGH"
        elif confidence >= Config.HIGH_CONFIDENCE and ev_pct >= Config.HIGH_EDGE:
            return "HIGH"
        elif confidence >= Config.MEDIUM_CONFIDENCE and ev_pct >= Config.MEDIUM_EDGE:
            return "MEDIUM"
        else:
            return "LOW"

