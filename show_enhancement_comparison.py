"""
Show Enhanced vs Basic Analysis Comparison
==========================================

Takes existing betting recommendations and applies the enhanced analysis
to show the difference between old and new formats.
"""

import json
from enhanced_player_analysis import enhance_player_prop_prediction, format_enhanced_prediction_display

# Mock projection for enhancement
class MockProjection:
    def __init__(self, player_name, stat_type):
        self.expected_value = 6.2
        self.probability_over_line = 0.68
        self.confidence_score = 75
        self.std_dev = 1.8
        self.matchup_adjustments = MockMatchupAdjustments(stat_type)
        self.role_change = MockRoleChange()
        self.minutes_projection = MockMinutesProjection()

class MockMatchupAdjustments:
    def __init__(self, stat_type):
        # Vary adjustments by stat type
        if stat_type == 'rebounds':
            self.pace_multiplier = 1.08
            self.defense_adjustment = 1.12
        elif stat_type == 'assists':
            self.pace_multiplier = 1.02
            self.defense_adjustment = 0.95
        else:
            self.pace_multiplier = 1.05
            self.defense_adjustment = 1.03

class MockRoleChange:
    def __init__(self):
        self.detected = True

class MockMinutesProjection:
    def __init__(self):
        self.projected_minutes = 32.5

class MockGame:
    def __init__(self, minutes, points, rebounds, assists):
        self.minutes = minutes
        self.points = points
        self.rebounds = rebounds
        self.assists = assists

# Mock game log
def create_mock_game_log():
    return [
        MockGame(35, 18, 6, 4),
        MockGame(32, 22, 5, 3),
        MockGame(28, 15, 7, 5),
        MockGame(34, 20, 6, 4),
        MockGame(31, 16, 8, 3),
        MockGame(33, 19, 5, 6),
        MockGame(29, 14, 7, 4),
        MockGame(36, 24, 6, 5),
        MockGame(30, 17, 6, 3),
        MockGame(32, 21, 7, 4),
    ]

def show_comparison():
    """Show before/after comparison using existing recommendations"""
    
    print("=" * 100)
    print("ENHANCED ANALYSIS COMPARISON - OLD vs NEW")
    print("=" * 100)
    
    # Try to load existing recommendations
    try:
        with open('betting_recommendations_v2.json', 'r') as f:
            existing_bets = json.load(f)
    except FileNotFoundError:
        print("No existing recommendations found. Creating sample data...")
        existing_bets = [
            {
                "player_name": "Jaden McDaniels",
                "stat_type": "rebounds",
                "line": 3.5,
                "odds": 1.36,
                "edge_percentage": 4.7,
                "confidence_score": 57.6,
                "game": "Minnesota Timberwolves @ New Orleans Pelicans"
            },
            {
                "player_name": "Keyonte George", 
                "stat_type": "assists",
                "line": 5.5,
                "odds": 1.32,
                "edge_percentage": 0.9,
                "confidence_score": 57.4,
                "game": "Utah Jazz @ Brooklyn Nets"
            }
        ]
    
    for i, bet in enumerate(existing_bets[:3], 1):  # Show first 3
        player = bet.get('player_name', bet.get('player', 'Unknown Player'))
        stat = bet.get('stat_type', bet.get('stat', 'points'))
        line = bet.get('line', 0)
        odds = bet.get('odds', 1.0)
        edge = bet.get('edge_percentage', bet.get('edge', 0))
        confidence = bet.get('confidence_score', bet.get('confidence', 0))
        game = bet.get('game', 'Unknown @ Unknown')
        
        print(f"\n{i}. PLAYER: {player} - {stat.upper()} OVER {line}")
        print("=" * 80)
        
        # OLD FORMAT
        print("📊 OLD FORMAT (Basic):")
        print("-" * 40)
        print(f"🏀 {player} {stat.upper()} OVER {line} @ {odds}")
        print(f"   Edge: {edge:.1f}% | Confidence: {confidence:.0f}% | Game: {game}")
        print(f"   Basic stats only - no context or risk assessment")
        
        # NEW FORMAT (Enhanced)
        print("\n🚀 NEW FORMAT (Enhanced):")
        print("-" * 40)
        
        # Convert to enhanced format
        enhanced_bet = {
            'player': player,
            'stat': stat,
            'line': line,
            'prediction': 'OVER',
            'odds': odds,
            'expected_value': line + 1.2,
            'projected_prob': 0.68,
            'historical_prob': 0.65,
            'final_prob': 0.67,
            'confidence': confidence,
            'sample_size': 20,
            'edge': edge,
            'ev_per_100': edge * 2,
            'game': game,
            'market_name': f'Player {stat.title()}'
        }
        
        # Apply enhancements
        mock_projection = MockProjection(player, stat)
        mock_game_log = create_mock_game_log()
        
        try:
            enhanced_bet = enhance_player_prop_prediction(enhanced_bet, mock_projection, mock_game_log)
            enhanced_display = format_enhanced_prediction_display(enhanced_bet)
            print(enhanced_display)
        except Exception as e:
            print(f"Enhancement failed: {e}")
            print("Falling back to basic display...")
        
        print("\n" + "🔥 KEY IMPROVEMENTS:" + " " * 50)
        print("   ✅ Risk assessment (blowout, foul trouble, minutes volatility)")
        print("   ✅ 'Why' explanation (role changes, matchup advantages)")  
        print("   ✅ Variance-adjusted edge (prevents overconfidence)")
        print("   ✅ Usage change tracking (recent vs season trends)")
        print("   ✅ Pace/Defense context (clear explanations)")
        
        if i < len(existing_bets[:3]):
            print("\n" + "─" * 100)

    print("\n" + "=" * 100)
    print("SUMMARY: Enhanced analysis provides professional, trustworthy betting intelligence")
    print("that bettors can confidently act on, with full transparency on risks and reasoning.")
    print("=" * 100)

if __name__ == "__main__":
    show_comparison()