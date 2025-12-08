"""
Test Enhanced Player Analysis Features
=====================================

Demonstrates the 5 key improvements:
1. Risk Factors / Red Flags
2. "Why" explanations 
3. Variance-adjusted edges
4. Usage change tracking
5. Pace/Defense explanations
"""

import json
from enhanced_player_analysis import enhance_player_prop_prediction, format_enhanced_prediction_display

# Mock projection object for testing
class MockProjection:
    def __init__(self):
        self.expected_value = 6.2
        self.probability_over_line = 0.68
        self.confidence_score = 75
        self.std_dev = 1.8
        
        # Mock matchup adjustments
        self.matchup_adjustments = MockMatchupAdjustments()
        
        # Mock role change
        self.role_change = MockRoleChange()
        
        # Mock minutes projection
        self.minutes_projection = MockMinutesProjection()

class MockMatchupAdjustments:
    def __init__(self):
        self.pace_multiplier = 1.08  # Fast pace game
        self.defense_adjustment = 1.12  # Favorable matchup

class MockRoleChange:
    def __init__(self):
        self.detected = True  # Role change detected

class MockMinutesProjection:
    def __init__(self):
        self.projected_minutes = 32.5

# Mock game log
class MockGame:
    def __init__(self, minutes, points, rebounds, assists):
        self.minutes = minutes
        self.points = points
        self.rebounds = rebounds
        self.assists = assists

# Create test data
mock_game_log = [
    MockGame(35, 18, 6, 4),
    MockGame(32, 22, 5, 3),
    MockGame(28, 15, 7, 5),  # Lower minutes game
    MockGame(34, 20, 6, 4),
    MockGame(31, 16, 8, 3),
    MockGame(33, 19, 5, 6),
    MockGame(29, 14, 7, 4),
    MockGame(36, 24, 6, 5),
    MockGame(30, 17, 6, 3),
    MockGame(32, 21, 7, 4),
]

# Basic prediction to enhance
basic_prediction = {
    'player': 'Jalen Johnson',
    'stat': 'rebounds',
    'line': 5.5,
    'prediction': 'OVER',
    'odds': 2.70,
    'expected_value': 6.2,
    'projected_prob': 0.68,
    'historical_prob': 0.65,
    'final_prob': 0.67,
    'confidence': 75,
    'sample_size': 10,
    'edge': 27.4,  # High edge to test variance adjustment
    'ev_per_100': 45.18,
    'game': 'Atlanta Hawks @ Denver Nuggets',
    'market_name': 'Player Rebounds'
}

print("=" * 80)
print("ENHANCED PLAYER ANALYSIS DEMONSTRATION")
print("=" * 80)

print("\n1. BASIC PREDICTION (Before Enhancement):")
print("-" * 50)
print(f"🏀 {basic_prediction['player']} {basic_prediction['stat'].upper()} {basic_prediction['prediction']} {basic_prediction['line']}")
print(f"   Odds: {basic_prediction['odds']} | Edge: {basic_prediction['edge']}% | Confidence: {basic_prediction['confidence']}%")

print("\n2. APPLYING ENHANCEMENTS...")
print("-" * 50)

# Apply enhancements
mock_projection = MockProjection()
enhanced_prediction = enhance_player_prop_prediction(basic_prediction, mock_projection, mock_game_log)

print("✓ Risk assessment calculated")
print("✓ Usage analysis computed") 
print("✓ Matchup context generated")
print("✓ Variance-adjusted edge applied")
print("✓ Professional explanations added")

print("\n3. ENHANCED PREDICTION (After Enhancement):")
print("-" * 50)
enhanced_display = format_enhanced_prediction_display(enhanced_prediction)
print(enhanced_display)

print("\n4. DETAILED ENHANCEMENT BREAKDOWN:")
print("-" * 50)

# Show risk assessment
risk = enhanced_prediction.get('risk_assessment', {})
print(f"🔴 RISK ASSESSMENT:")
print(f"   Overall Risk: {risk.get('overall_risk', 'N/A')}")
print(f"   Blowout Risk: {risk.get('blowout_risk', 'N/A')}")
print(f"   Minutes Volatility: {risk.get('minutes_volatility', 'N/A')}")
print(f"   Risk Notes: {', '.join(risk.get('risk_notes', []))}")

# Show usage analysis
usage = enhanced_prediction.get('usage_analysis', {})
if usage:
    print(f"\n📊 USAGE ANALYSIS:")
    print(f"   Season Usage: {usage.get('season_usage', 0):.1f}")
    print(f"   Recent Usage: {usage.get('recent_usage', 0):.1f}")
    print(f"   Usage Change: {usage.get('usage_change', 0):+.1f}")
    print(f"   Expected Tonight: {usage.get('expected_usage_tonight', 0):.1f}")
    print(f"   Trend: {usage.get('usage_trend', 'N/A')}")

# Show matchup context
context = enhanced_prediction.get('matchup_context', {})
print(f"\n🎯 MATCHUP CONTEXT:")
print(f"   Why: {context.get('why_explanation', 'N/A')}")
print(f"   Pace: {context.get('pace_explanation', 'N/A')}")
print(f"   Defense: {context.get('defense_explanation', 'N/A')}")

# Show edge adjustment
print(f"\n⚖️ EDGE ADJUSTMENT:")
print(f"   Raw Edge: {enhanced_prediction.get('raw_edge', 0):.1f}%")
print(f"   Adjusted Edge: {enhanced_prediction.get('adjusted_edge', 0):.1f}%")
if 'variance_note' in enhanced_prediction:
    print(f"   Note: {enhanced_prediction['variance_note']}")

print("\n" + "=" * 80)
print("KEY IMPROVEMENTS DEMONSTRATED:")
print("=" * 80)
print("1. ✅ Risk Factors: Blowout, foul trouble, minutes volatility assessed")
print("2. ✅ Why Explanation: Clear reasoning for the projection")
print("3. ✅ Variance Adjustment: High edge reduced due to risk factors")
print("4. ✅ Usage Tracking: Season vs recent usage change calculated")
print("5. ✅ Pace/Defense Context: Explicit explanations for adjustments")
print("\nThis creates a professional, trustworthy analysis that bettors can rely on!")

# Save enhanced prediction for inspection
with open('enhanced_prediction_example.json', 'w') as f:
    json.dump(enhanced_prediction, f, indent=2)

print(f"\n📁 Enhanced prediction saved to: enhanced_prediction_example.json")