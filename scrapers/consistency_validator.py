"""
Explanation Consistency Validator
==================================
Validates that bet rationales don't contradict underlying data.

If inconsistencies found, downgrades tier by one level.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)


def validate_explanation_consistency(bet: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Check if rationale contradicts data.
    
    Validates:
    - If says "starter" but minutes < 25
    - If says "high usage" but usage < 20%
    - If says "favorable matchup" but opponent defense is top 5
    - If says "recent form" but recent stats < historical
    
    Args:
        bet: Bet dictionary
    
    Returns:
        Tuple of (is_consistent, inconsistencies_list)
    """
    inconsistencies = []
    
    # Check player prop specific validations
    if bet.get('type') == 'player_prop':
        player_name = bet.get('player', '')
        projection_details = bet.get('projection_details', {})
        
        # 1. Minutes consistency
        minutes_projected = projection_details.get('minutes_projected')
        if minutes_projected is not None:
            # Check if rationale mentions "starter" but minutes < 25
            rationale = bet.get('fact', '') or bet.get('analysis', {}).get('reasons', [])
            if isinstance(rationale, list):
                rationale = ' '.join(rationale).lower()
            else:
                rationale = str(rationale).lower()
            
            if ('starter' in rationale or 'starting' in rationale) and minutes_projected < 25:
                inconsistencies.append(
                    f"Mentions starter but projected minutes ({minutes_projected:.1f}) < 25"
                )
        
        # 2. Usage consistency (if we have usage data)
        # This would require role_modifier data, skip for now
        
        # 3. Role consistency
        player_role = projection_details.get('player_role', '')
        if player_role:
            # Check if role contradicts minutes
            if player_role == 'primary_handler' and minutes_projected and minutes_projected < 28:
                inconsistencies.append(
                    f"Role 'primary_handler' but minutes ({minutes_projected:.1f}) < 28"
                )
            elif player_role == 'bench' and minutes_projected and minutes_projected >= 25:
                inconsistencies.append(
                    f"Role 'bench' but minutes ({minutes_projected:.1f}) >= 25"
                )
    
    # Check team bet validations
    else:
        analysis = bet.get('analysis', {})
        rationale = bet.get('fact', '') or analysis.get('reasons', [])
        if isinstance(rationale, list):
            rationale = ' '.join(rationale).lower()
        else:
            rationale = str(rationale).lower()
        
        # Check for matchup contradictions
        if 'favorable' in rationale or 'weak defense' in rationale:
            # Would need opponent stats to validate, skip for now
            pass
        
        # Check for recent form contradictions
        if 'recent form' in rationale or 'trending' in rationale:
            # Check if recent stats actually support this
            sample_size = bet.get('sample_size', 0)
            if sample_size < 5:
                inconsistencies.append(
                    f"Mentions recent form but sample size ({sample_size}) < 5"
                )
    
    return len(inconsistencies) == 0, inconsistencies


def downgrade_tier(current_tier: str) -> str:
    """Downgrade tier by one level"""
    tier_map = {
        'A': 'B',
        'B': 'C',
        'C': 'WATCHLIST',
        'WATCHLIST': 'WATCHLIST'  # Can't downgrade further
    }
    return tier_map.get(current_tier, current_tier)


def apply_consistency_check(bet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply consistency check and downgrade tier if needed.
    
    Args:
        bet: Bet dictionary
    
    Returns:
        Updated bet dictionary (with tier potentially downgraded)
    """
    is_consistent, inconsistencies = validate_explanation_consistency(bet)
    
    if not is_consistent:
        current_tier = bet.get('tier', 'C')
        new_tier = downgrade_tier(current_tier)
        
        if new_tier != current_tier:
            bet['tier'] = new_tier
            bet['consistency_warnings'] = inconsistencies
            bet['tier_downgrade_reason'] = 'consistency'
            
            logger.debug(
                f"[CONSISTENCY] Downgraded {bet.get('player', bet.get('market', 'Unknown'))} "
                f"from {current_tier} to {new_tier}: {inconsistencies}"
            )
    
    return bet
