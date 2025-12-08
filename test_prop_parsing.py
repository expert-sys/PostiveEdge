"""
Test script to verify player prop parsing from insights
"""
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class MockInsight:
    """Mock insight object for testing"""
    fact: str
    result: str
    market: str
    odds: Optional[float] = None

def is_player_prop_insight(insight) -> bool:
    """Check if insight is about a player prop"""
    fact = str(getattr(insight, 'fact', ''))
    result = str(getattr(insight, 'result', ''))
    market = str(getattr(insight, 'market', ''))
    
    # Method 1: Check for "Over/Under (+X.X) - Player Name Stat" format
    has_over_under_format = bool(re.search(r'(?:Over|Under)\s*\(\+?-?\d+\.?\d*\)\s*-\s*[A-Z]', market, re.IGNORECASE))
    
    if has_over_under_format:
        return True
    
    # Method 2: Check for player name with stat keywords
    combined_text = (fact + ' ' + result + ' ' + market).lower()
    stat_keywords = ['points', 'rebounds', 'assists', 'steals', 'blocks', 'threes', '3-point', 'made threes']
    has_stat = any(keyword in combined_text for keyword in stat_keywords)
    has_player = bool(re.search(r'[A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+){1,2}', result + ' ' + market + ' ' + fact))
    
    # Exclude team insights
    market_lower = market.lower()
    team_keywords = ['timberwolves', 'pelicans', 'warriors', 'lakers', 'celtics']
    has_team_in_market = any(team in market_lower for team in team_keywords)
    is_match_insight = '- match' in market_lower
    
    return has_stat and has_player and not has_team_in_market and not is_match_insight

def parse_prop_from_insight(insight) -> Optional[dict]:
    """Extract player prop details from insight"""
    fact = str(getattr(insight, 'fact', ''))
    result = str(getattr(insight, 'result', ''))
    market = str(getattr(insight, 'market', ''))
    odds = getattr(insight, 'odds', None)
    
    print(f"\nParsing insight:")
    print(f"  Market: {market}")
    print(f"  Fact: {fact[:80]}...")
    print(f"  Result: {result}")
    print(f"  Odds: {odds}")
    
    # METHOD 1: Parse "Over/Under (+X.X) - Player Name Stat Type" format
    # Split on the dash first, then extract player name and stat separately
    market_split = re.split(r'\s*-\s*', market, maxsplit=1)
    if len(market_split) == 2:
        line_part = market_split[0]  # "Over (+3.5)"
        player_stat_part = market_split[1]  # "Anthony Edwards Made Threes"
        
        # Extract over/under and line from first part
        line_match = re.search(r'(Over|Under)\s*\(\+?(-?\d+\.?\d*)\)', line_part, re.IGNORECASE)
        if line_match:
            over_under = line_match.group(1).lower()
            line = float(line_match.group(2))
            
            # Extract player name (everything before stat keywords)
            # Look for stat keywords and take everything before them
            stat_keywords_pattern = r'\b(Made|Points?|Rebounds?|Assists?|Steals?|Blocks?|Threes?|3-Point|Field Goals)\b'
            stat_match = re.search(stat_keywords_pattern, player_stat_part, re.IGNORECASE)
            
            if stat_match:
                player_name = player_stat_part[:stat_match.start()].strip()
                stat_description = player_stat_part[stat_match.start():].strip().lower()
            else:
                player_name = None
                stat_description = player_stat_part.lower()
        else:
            line_match = None
    else:
        line_match = None
    
    if line_match and player_name:
        
        # Map stat description to stat type
        stat_type = None
        if 'point' in stat_description:
            stat_type = 'points'
        elif 'rebound' in stat_description:
            stat_type = 'rebounds'
        elif 'assist' in stat_description:
            stat_type = 'assists'
        elif 'steal' in stat_description:
            stat_type = 'steals'
        elif 'block' in stat_description:
            stat_type = 'blocks'
        elif 'three' in stat_description or 'threes' in stat_description:
            stat_type = 'three_pt_made'
        
        if stat_type:
            print(f"  ✓ Player: {player_name}")
            print(f"  ✓ Stat: {stat_type}")
            print(f"  ✓ Line: {line}")
            print(f"  ✓ Direction: {over_under}")
            print(f"  ✓ Result: {player_name} {stat_type} {over_under.title()} {line} @ {odds if odds else 1.90}")
            return {
                'player': player_name,
                'stat': stat_type,
                'line': line,
                'odds': odds if odds else 1.90
            }
    
    # METHOD 2: Fallback for other formats
    player_match = re.search(r'([A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+){1,2})', result)
    if not player_match:
        player_match = re.search(r'([A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+){1,2})', market)
    if not player_match:
        player_match = re.search(r'([A-Z][a-zA-Z\'-]+(?:\s+[A-Z][a-zA-Z\'-]+){1,2})', fact)
    
    if not player_match:
        print("  ✗ No player name found")
        return None
    
    player_name = player_match.group(1).strip()
    print(f"  ✓ Player: {player_name}")
    
    # Extract stat type and line
    stat_patterns = {
        'points': r'(?:over\s+)?(\d+\.?\d*)\+?\s*points?',
        'rebounds': r'(?:over\s+)?(\d+\.?\d*)\+?\s*rebounds?',
        'assists': r'(?:over\s+)?(\d+\.?\d*)\+?\s*assists?',
        'steals': r'(?:over\s+)?(\d+\.?\d*)\+?\s*steals?',
        'blocks': r'(?:over\s+)?(\d+\.?\d*)\+?\s*blocks?',
        'three_pt_made': r'(?:over\s+)?(\d+\.?\d*)\+?\s*(?:three|3-point|threes)',
    }
    
    search_text = (fact + ' ' + market + ' ' + result).lower()
    for stat, pattern in stat_patterns.items():
        match = re.search(pattern, search_text)
        if match:
            line = float(match.group(1))
            
            if '.' not in match.group(1) and '+' in search_text:
                line = line - 0.5
            
            print(f"  ✓ Stat: {stat}")
            print(f"  ✓ Line: {line}")
            print(f"  ✓ Result: {player_name} {stat} Over {line} @ {odds if odds else 1.90}")
            
            return {
                'player': player_name,
                'stat': stat,
                'line': line,
                'odds': odds if odds else 1.90
            }
    
    print(f"  ✗ No stat pattern matched")
    return None

# Test cases - including the actual format from Sportsbet
test_insights = [
    # NEW FORMAT: "Over (+X.X) - Player Name Stat" (from screenshot)
    MockInsight(
        fact="Anthony Edwards has made four or more three-pointers in each of the Timberwolves' last six games",
        result="",
        market="Over (+3.5) - Anthony Edwards Made Threes",
        odds=1.80
    ),
    # Team insight (should be filtered out)
    MockInsight(
        fact="The Pelicans have lost each of their last 12 games against Western Conference opponents",
        result="",
        market="Minnesota Timberwolves - Match",
        odds=1.17
    ),
    # OLD FORMAT: Traditional player prop formats
    MockInsight(
        fact="Stephen Curry has scored 25+ points in 8 of his last 10 games",
        result="Stephen Curry",
        market="Player Points",
        odds=1.85
    ),
    MockInsight(
        fact="LeBron James averaging 7.5 assists per game this season",
        result="LeBron James",
        market="Player Assists Over 7.5",
        odds=1.90
    ),
    MockInsight(
        fact="Nikola Jokic has recorded 10+ rebounds in 12 of last 15 games",
        result="Nikola Jokic",
        market="Over (+9.5) - Nikola Jokic Rebounds",
        odds=1.80
    ),
]

print("=" * 80)
print("TESTING PLAYER PROP PARSING")
print("=" * 80)

for i, insight in enumerate(test_insights, 1):
    print(f"\n{'=' * 80}")
    print(f"TEST CASE {i}")
    print('=' * 80)
    
    # First check if it's a player prop
    is_prop = is_player_prop_insight(insight)
    print(f"Is Player Prop: {is_prop}")
    
    if is_prop:
        result = parse_prop_from_insight(insight)
        if result:
            print(f"\n✓ SUCCESS: Parsed correctly")
        else:
            print(f"\n✗ FAILED: Could not parse")
    else:
        print(f"\n⊘ SKIPPED: Not a player prop (correctly filtered out)")

print("\n" + "=" * 80)
print("TESTING COMPLETE")
print("=" * 80)
