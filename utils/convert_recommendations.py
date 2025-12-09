"""
Convert Dictionary Bets to BettingRecommendation Objects
========================================================
Converts old-style dictionary bets to new BettingRecommendation dataclass.
"""

from typing import List, Dict, Optional
from models import BettingRecommendation


def convert_dict_to_recommendation(bet_dict: Dict, game_info: Optional[Dict] = None) -> Optional[BettingRecommendation]:
    """
    Convert a dictionary bet to BettingRecommendation object.
    
    Args:
        bet_dict: Dictionary with bet information
        game_info: Optional game information dict
    
    Returns:
        BettingRecommendation object or None if conversion fails
    """
    if not bet_dict or not isinstance(bet_dict, dict):
        return None
    
    try:
        bet_type = bet_dict.get('type', 'unknown')
        
        # Extract game information
        if game_info:
            game = f"{game_info.get('away_team', 'Unknown')} @ {game_info.get('home_team', 'Unknown')}"
            match_time = game_info.get('match_time', 'TBD')
        else:
            game = bet_dict.get('game', 'Unknown Game')
            match_time = bet_dict.get('match_time', 'TBD')
        
        # Common fields
        odds = float(bet_dict.get('odds', 0))
        confidence = float(bet_dict.get('confidence', bet_dict.get('confidence_score', 0)))
        ev_per_100 = bet_dict.get('ev_per_100', bet_dict.get('expected_value', 0))
        edge = bet_dict.get('edge', bet_dict.get('edge_percentage', 0))
        
        # Convert EV from per-100 to percentage
        if isinstance(ev_per_100, (int, float)):
            expected_value = ev_per_100 if abs(ev_per_100) < 1 else ev_per_100 / 100.0 * 100
        else:
            expected_value = 0.0
        
        # Convert edge to percentage
        if isinstance(edge, (int, float)):
            edge_percentage = edge if abs(edge) < 1 else edge
        else:
            edge_percentage = 0.0
        
        # Calculate implied probability
        implied_prob = 1.0 / odds if odds > 0 else 0.0
        
        if bet_type == 'player_prop':
            # Player prop fields
            player_name = bet_dict.get('player', bet_dict.get('player_name', 'Unknown'))
            stat_type = bet_dict.get('stat', bet_dict.get('stat_type', 'points'))
            line = bet_dict.get('line', 0)
            prediction = bet_dict.get('prediction', 'OVER')
            
            # Create selection string
            selection = f"{prediction} {line}"
            
            # Extract player team and opponent
            player_team = bet_dict.get('player_team', None)
            opponent_team = bet_dict.get('opponent_team', None)
            
            # Historical data
            historical_hit_rate = bet_dict.get('historical_prob', bet_dict.get('historical_hit_rate', bet_dict.get('historical_probability', 0.0)))
            if isinstance(historical_hit_rate, (int, float)) and historical_hit_rate > 1:
                historical_hit_rate = historical_hit_rate / 100.0
            
            sample_size = bet_dict.get('sample_size', 0)
            
            # Projected probability - check multiple possible field names
            projected_prob = bet_dict.get('projected_prob', bet_dict.get('projected_probability', bet_dict.get('final_prob', 0.0)))
            if isinstance(projected_prob, (int, float)) and projected_prob > 1:
                projected_prob = projected_prob / 100.0
            
            # DataBallr stats
            databallr_stats = bet_dict.get('databallr_stats', {})
            if not databallr_stats and 'avg_value' in bet_dict:
                databallr_stats = {
                    'avg_value': bet_dict.get('avg_value'),
                    'trend': bet_dict.get('trend', 'stable'),
                    'recent_avg': bet_dict.get('recent_avg', bet_dict.get('avg_value'))
                }
            
            # Advanced context - include projection_details
            advanced_context = bet_dict.get('advanced_context', {})
            if 'projection_details' in bet_dict:
                if not advanced_context:
                    advanced_context = {}
                advanced_context['projection_details'] = bet_dict['projection_details']
            
            return BettingRecommendation(
                game=game,
                match_time=match_time,
                bet_type='player_prop',
                market=stat_type.replace('_', ' ').title(),
                selection=selection,
                odds=odds,
                player_name=player_name,
                player_team=player_team,
                opponent_team=opponent_team,
                stat_type=stat_type,
                line=float(line) if line else None,
                historical_hit_rate=historical_hit_rate,
                sample_size=sample_size,
                projected_probability=projected_prob,
                implied_probability=implied_prob,
                edge_percentage=edge_percentage,
                expected_value=expected_value,
                confidence_score=confidence,
                recommendation_strength=_get_strength_from_confidence(confidence, edge_percentage),
                databallr_stats=databallr_stats if databallr_stats else None,
                advanced_context=advanced_context if advanced_context else None,
                sportsbet_insight=bet_dict.get('fact', bet_dict.get('insight', None))
            )
        
        else:
            # Team bet fields
            market = bet_dict.get('market', bet_dict.get('result', 'Unknown Market'))
            selection = bet_dict.get('result', bet_dict.get('selection', 'Unknown'))
            
            # Historical data
            historical_hit_rate = bet_dict.get('historical_probability', 0.0)
            if isinstance(historical_hit_rate, (int, float)) and historical_hit_rate > 1:
                historical_hit_rate = historical_hit_rate / 100.0
            
            sample_size = bet_dict.get('sample_size', 0)
            
            # Projected probability
            projected_prob = bet_dict.get('projected_prob', bet_dict.get('projected_probability', historical_hit_rate))
            if isinstance(projected_prob, (int, float)) and projected_prob > 1:
                projected_prob = projected_prob / 100.0
            
            # Analysis data
            analysis = bet_dict.get('analysis', {})
            if analysis:
                projected_prob = analysis.get('projected_prob', projected_prob)
                historical_hit_rate = analysis.get('historical_probability', historical_hit_rate)
            
            # Advanced context
            advanced_context = bet_dict.get('advanced_context', {})
            if not advanced_context and 'projection_details' in bet_dict:
                advanced_context = {
                    'projection': bet_dict['projection_details']
                }
            elif analysis and 'projection_details' in analysis:
                advanced_context = {
                    'projection': analysis['projection_details']
                }
            
            return BettingRecommendation(
                game=game,
                match_time=match_time,
                bet_type=f"team_{bet_dict.get('market_type', 'unknown')}",
                market=market,
                selection=selection,
                odds=odds,
                historical_hit_rate=historical_hit_rate,
                sample_size=sample_size,
                projected_probability=projected_prob,
                implied_probability=implied_prob,
                edge_percentage=edge_percentage,
                expected_value=expected_value,
                confidence_score=confidence,
                recommendation_strength=_get_strength_from_confidence(confidence, edge_percentage),
                advanced_context=advanced_context if advanced_context else None,
                sportsbet_insight=bet_dict.get('fact', bet_dict.get('insight', None))
            )
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error converting bet dict to recommendation: {e}")
        return None


def convert_dicts_to_recommendations(bet_dicts: List[Dict], game_info: Optional[Dict] = None) -> List[BettingRecommendation]:
    """
    Convert a list of dictionary bets to BettingRecommendation objects.
    
    Args:
        bet_dicts: List of bet dictionaries
        game_info: Optional game information dict
    
    Returns:
        List of BettingRecommendation objects (filters out None conversions)
    """
    recommendations = []
    for bet_dict in bet_dicts:
        rec = convert_dict_to_recommendation(bet_dict, game_info)
        if rec:
            recommendations.append(rec)
    return recommendations


def _get_strength_from_confidence(confidence: float, edge: float) -> str:
    """Determine recommendation strength from confidence and edge"""
    from config import Config
    
    if confidence >= Config.VERY_HIGH_CONFIDENCE and edge >= Config.VERY_HIGH_EDGE:
        return "VERY_HIGH"
    elif confidence >= Config.HIGH_CONFIDENCE and edge >= Config.HIGH_EDGE:
        return "HIGH"
    elif confidence >= Config.MEDIUM_CONFIDENCE and edge >= Config.MEDIUM_EDGE:
        return "MEDIUM"
    else:
        return "LOW"

