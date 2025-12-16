
import re
from typing import Dict, Optional

def _is_player_prop_insight(insight: Dict) -> bool:
    """Check if an insight is a player prop (points, rebounds, assists, etc.)"""
    fact = (insight.get('fact') or '').lower()
    market = (insight.get('market') or '').lower()
    result = (insight.get('result') or '').lower()
    
    # Check for player prop keywords
    prop_keywords = ['points', 'rebounds', 'assists', 'steals', 'blocks', 'threes', '3-pointers']
    stat_indicators = ['scored', 'recorded', 'made', 'grabbed', 'dished']
    
    # Must have a player name in result and a stat keyword
    has_player = result and len(result.split()) >= 2  # Likely a player name
    has_stat = any(keyword in fact or keyword in market for keyword in prop_keywords)
    has_indicator = any(indicator in fact for indicator in stat_indicators)
    
    print(f"DEBUG: player={has_player}, stat={has_stat}, indicator={has_indicator}")
    print(f"DEBUG: fact='{fact}', market='{market}', result='{result}'")
    
    return has_player and (has_stat or has_indicator)

def _extract_prop_info_from_insight(insight: Dict) -> Optional[Dict]:
    """Extract player name, stat type, and line from insight"""
    
    fact = insight.get('fact') or ''
    result = insight.get('result') or ''
    market = insight.get('market') or ''
    
    # Extract player name (usually in result field)
    player_name = result.strip() if result else None
    
    # Extract stat type and threshold from fact
    # Pattern: "scored 20+ points" or "recorded 8+ assists"
    patterns = [
        (r'(\d+)\+?\s*points?', 'points'),
        (r'(\d+)\+?\s*rebounds?', 'rebounds'),
        (r'(\d+)\+?\s*assists?', 'assists'),
        (r'(\d+)\+?\s*steals?', 'steals'),
        (r'(\d+)\+?\s*blocks?', 'blocks'),
        (r'(\d+)\+?\s*threes?', 'three_pt_made'),
    ]
    
    stat_type = None
    line = None
    
    for pattern, stat in patterns:
        match = re.search(pattern, fact.lower())
        if match:
            line = float(match.group(1))
            stat_type = stat
            break
            
    # DEBUG: Check market if fact failed
    if not stat_type:
        print("DEBUG: Checking market for patterns (Change Proposal)...")
        for pattern, stat in patterns:
            match = re.search(pattern, market.lower())
            if match:
                print(f"DEBUG: Found in market! {stat} {match.group(1)}")
                # line = float(match.group(1))
                # stat_type = stat
                # break

    if not player_name or not stat_type or not line:
        return None
        
    return {
        'player': player_name,
        'stat': stat_type,
        'line': line
    }

# Test Case from User Report
insight = {
    'market': 'Kevin Durant To Score 20+ Points',
    'result': 'Kevin Durant',
    'fact': '', # Assuming fact is empty or irrelevant based on output
    'odds': 1.24
}

print(f"Testing insight: {insight}")
is_prop = _is_player_prop_insight(insight)
print(f"Is Player Prop: {is_prop}")

if is_prop:
    extracted = _extract_prop_info_from_insight(insight)
    print(f"Extracted: {extracted}")
else:
    print("Not classified as player prop.")
