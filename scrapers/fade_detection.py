"""
Fade Detection Module
=====================
Identifies bets that are attractive to the public but are overconfident or mispriced.
Calculates fade scores and evaluates opposite-side opportunities.
"""

from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_fade_score(bet: Dict, same_game_count: int = 0) -> Tuple[int, List[str]]:
    """
    Calculate fade score (0-100) for a bet.
    
    Fade signals:
    - Market vs Model divergence (market_prob - model_prob >= 0.08) → +30
    - Public heavy / line shading flags → +15, +10
    - Small sample confidence inflation (n < 10, conf >= 60) → +15
    - Correlation risk (same_game_count >= 2) → +10
    - Negative or thin EV (EV < 0 → +20, EV < 0.03 → +10)
    
    Args:
        bet: Bet dictionary with all analysis data
        same_game_count: Number of bets already selected from same game
        
    Returns:
        Tuple of (fade_score, fade_reasons)
    """
    fade_score = 0
    fade_reasons = []
    
    # Get probabilities
    model_prob = bet.get('final_prob', bet.get('historical_probability', 0))
    market_prob = 1.0 / bet.get('odds', 2.0) if bet.get('odds', 0) > 0 else 0.5
    
    # 1. Market vs Model divergence
    prob_divergence = market_prob - model_prob
    if prob_divergence >= 0.08:
        fade_score += 30
        fade_reasons.append(f"Market > Model by {prob_divergence:.1%}")
    elif prob_divergence >= 0.05:
        fade_score += 15
        fade_reasons.append(f"Market > Model by {prob_divergence:.1%}")
    
    # 2. Public / shading flags (heuristic: high market prob + high odds = public heavy)
    # If market probability is high but odds are also high, suggests public is betting heavily
    if market_prob >= 0.55 and bet.get('odds', 0) > 1.8:
        fade_score += 15
        fade_reasons.append("Public heavy (high market prob + odds)")
    
    # 3. Small sample confidence inflation
    sample_size = bet.get('sample_size', 0)
    confidence = bet.get('confidence', 0)
    if sample_size < 10 and confidence >= 60:
        fade_score += 15
        fade_reasons.append(f"Small sample (n={sample_size}) with inflated confidence ({confidence:.0f})")
    elif sample_size < 5 and confidence >= 50:
        fade_score += 10
        fade_reasons.append(f"Very small sample (n={sample_size}) with high confidence ({confidence:.0f})")
    
    # 4. Correlation risk
    if same_game_count >= 2:
        fade_score += 10
        fade_reasons.append(f"Correlation risk ({same_game_count} bets from same game)")
    
    # 5. Negative or thin EV
    ev_pct = bet.get('edge', 0)  # Edge percentage
    if ev_pct < 0:
        fade_score += 20
        fade_reasons.append(f"Negative EV ({ev_pct:.1f}%)")
    elif ev_pct < 3.0:  # Less than 3% edge for props
        fade_score += 10
        fade_reasons.append(f"Thin EV ({ev_pct:.1f}%)")
    
    return fade_score, fade_reasons


def get_fade_tier(fade_score: int) -> Tuple[str, str]:
    """
    Determine fade tier based on score.
    
    Returns:
        Tuple of (tier_name, tier_emoji)
    """
    if fade_score >= 70:
        return "STRONG_FADE", "🔴"
    elif fade_score >= 50:
        return "FADE_LEAN", "🟠"
    elif fade_score >= 30:
        return "WATCH", "🟡"
    else:
        return "NO_FADE", ""


def find_opposite_side_odds(bet: Dict, all_game_markets: Optional[List[Dict]] = None) -> Optional[float]:
    """
    Find opposite side odds for a bet.
    
    For player props: Flip OVER → UNDER (same line)
    For team totals: Find Under odds if Over, or vice versa
    For team moneylines: Find opposite team odds
    
    Args:
        bet: Original bet dictionary
        all_game_markets: List of all markets from the game (for finding opposite odds)
        
    Returns:
        Opposite side odds if found, None otherwise
    """
    bet_type = bet.get('type', 'unknown')
    current_odds = bet.get('odds', 0)
    
    if current_odds <= 0:
        return None
    
    if bet_type == 'player_prop':
        # For player props, opposite side typically has similar odds
        # Estimate: Given vig ~5%, if OVER is 1.90, UNDER ≈ 1.90-1.95
        # Use current odds as conservative estimate (books usually balance these closely)
        return current_odds
    
    elif bet_type == 'team_bet':
        market = bet.get('market', '').lower()
        result = bet.get('result', '').lower()
        
        # Try to find opposite in game markets if provided
        if all_game_markets:
            game = bet.get('game', '')
            for market_data in all_game_markets:
                if market_data.get('game') == game:
                    market_type = market_data.get('market', '').lower()
                    
                    # Total Over/Under
                    if 'total' in market or 'over' in market or 'under' in market:
                        if 'over' in result:
                            # Looking for Under odds
                            if 'under' in market_type and market_data.get('odds'):
                                return market_data.get('odds')
                        elif 'under' in result:
                            # Looking for Over odds
                            if 'over' in market_type and market_data.get('odds'):
                                return market_data.get('odds')
        
        # Fallback: estimate from current odds
        # For balanced markets, opposite side usually has similar odds
        return current_odds
    
    return None


def evaluate_opposite_side(bet: Dict, opposite_odds: float) -> Optional[Dict]:
    """
    Evaluate the opposite side of a fade-worthy bet.
    
    Args:
        bet: Original bet dictionary
        opposite_odds: Odds for the opposite side
        
    Returns:
        Opposite bet dictionary with EV analysis, or None if not viable
    """
    bet_type = bet.get('type', 'unknown')
    model_prob = bet.get('final_prob', bet.get('historical_probability', 0))
    
    # Flip probability
    opposite_prob = 1.0 - model_prob
    
    # Ensure valid range
    opposite_prob = max(0.01, min(0.99, opposite_prob))
    
    # Calculate EV
    opposite_ev_pct = (opposite_prob * (opposite_odds - 1) * 100) - ((1 - opposite_prob) * 100)
    opposite_edge = (opposite_prob - (1.0 / opposite_odds)) * 100
    
    # Only surface if opposite side is viable
    if opposite_ev_pct >= 3.0 and opposite_prob >= 0.52:
        # Create opposite bet dictionary
        opposite_bet = bet.copy()
        
        if bet_type == 'player_prop':
            # Flip prediction
            current_pred = bet.get('prediction', 'OVER')
            opposite_bet['prediction'] = 'UNDER' if current_pred == 'OVER' else 'OVER'
            opposite_bet['fade_opposite'] = True
            opposite_bet['original_prediction'] = current_pred
        elif bet_type == 'team_bet':
            # Flip result
            market = bet.get('market', '')
            result = bet.get('result', '')
            if 'over' in result.lower():
                opposite_bet['result'] = result.replace('Over', 'Under').replace('over', 'under')
            elif 'under' in result.lower():
                opposite_bet['result'] = result.replace('Under', 'Over').replace('under', 'over')
            opposite_bet['fade_opposite'] = True
            opposite_bet['original_result'] = result
        
        # Update odds and probabilities
        opposite_bet['odds'] = opposite_odds
        opposite_bet['final_prob'] = opposite_prob
        opposite_bet['historical_probability'] = opposite_prob
        opposite_bet['edge'] = opposite_edge
        opposite_bet['ev_per_100'] = opposite_ev_pct
        opposite_bet['expected_value'] = opposite_ev_pct / 100.0
        
        # Keep same confidence (opposite side inherits model strength)
        # But might want to adjust based on fade strength
        opposite_bet['fade_original'] = True
        opposite_bet['original_fade_score'] = bet.get('fade_score', 0)
        
        return opposite_bet
    
    return None


def detect_fades(all_bets: List[Dict], games_data: Optional[List[Dict]] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Detect fade-worthy bets and evaluate opposite sides.
    
    Args:
        all_bets: List of all analyzed bets
        games_data: Optional game data for finding opposite odds
        
    Returns:
        Tuple of (fade_alerts, opposite_side_bets)
        - fade_alerts: Original bets with fade scores and reasons
        - opposite_side_bets: Viable opposite side bets
    """
    fade_alerts = []
    opposite_side_bets = []
    
    if not all_bets:
        return fade_alerts, opposite_side_bets
    
    # Count bets per game for correlation risk
    game_counts = {}
    for bet in all_bets:
        game = bet.get('game', 'Unknown')
        game_counts[game] = game_counts.get(game, 0) + 1
    
    # Evaluate each bet for fade signals
    for bet in all_bets:
        game = bet.get('game', 'Unknown')
        same_game_count = game_counts.get(game, 0)
        
        # Calculate fade score
        fade_score, fade_reasons = calculate_fade_score(bet, same_game_count=same_game_count)
        fade_tier, fade_emoji = get_fade_tier(fade_score)
        
        # Store fade info in bet
        bet['fade_score'] = fade_score
        bet['fade_reasons'] = fade_reasons
        bet['fade_tier'] = fade_tier
        bet['fade_emoji'] = fade_emoji
        
        # If strong fade (70+), evaluate opposite side
        if fade_score >= 70:
            # Try to find opposite odds
            opposite_odds = find_opposite_side_odds(bet, all_game_markets=None)  # Could pass games_data if structured
            
            if opposite_odds and opposite_odds > 0:
                opposite_bet = evaluate_opposite_side(bet, opposite_odds)
                if opposite_bet:
                    opposite_side_bets.append(opposite_bet)
                    bet['has_viable_opposite'] = True
                    bet['opposite_ev'] = opposite_bet.get('ev_per_100', 0)
                    bet['opposite_prob'] = opposite_bet.get('final_prob', 0)
                else:
                    bet['has_viable_opposite'] = False
            else:
                bet['has_viable_opposite'] = False
        
        # Track all fades (30+ score)
        if fade_score >= 30:
            fade_alerts.append(bet)
    
    return fade_alerts, opposite_side_bets
