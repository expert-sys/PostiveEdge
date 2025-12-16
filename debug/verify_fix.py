
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.player_projection_model import PlayerProjectionModel, GameLogEntry
from scrapers.unified_analysis_pipeline import _extract_prop_info_from_insight

def test_historical_hit_rate_field():
    print("Testing StatProjection.historical_hit_rate...")
    try:
        model = PlayerProjectionModel()
        
        # Create mock games
        games = []
        for i in range(10):
            games.append(GameLogEntry(
                game_date="2024-01-01", game_id="1", matchup="GSW vs LAL", home_away="HOME",
                opponent="LAL", opponent_id=1, won=True, minutes=30, points=25 if i < 6 else 15,
                rebounds=5, assists=5, steals=1, blocks=0, turnovers=2, fg_made=10, fg_attempted=20,
                three_pt_made=2, three_pt_attempted=5, ft_made=3, ft_attempted=4, plus_minus=5,
                team_points=110, opponent_points=100, total_points=210
            ))
            
        # Project stats (line = 20.5 points)
        # 6 games have 25 points (Over), 4 games have 15 points (Under)
        # Hit rate should be 6/10 = 60%
        projection = model.project_stat(
            player_name="Test Player", stat_type="points", game_log=games, prop_line=20.5,
            min_games=5
        )
        
        if projection is None:
            print("FAILED: Projection returned None")
            return False
            
        if not hasattr(projection, 'historical_hit_rate'):
            print("FAILED: StatProjection missing 'historical_hit_rate' attribute")
            return False
            
        print(f"Historical Hit Rate: {projection.historical_hit_rate}")
        
        if projection.historical_hit_rate == 0.6:
            print("SUCCESS: Historical hit rate correctly calculated and stored")
            return True
        else:
            print(f"FAILED: Expected 0.6, got {projection.historical_hit_rate}")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_extract_prop_info():
    print("\nTesting _extract_prop_info_from_insight logic...")
    
    # Test case: Stat in Market, Fact empty
    insight = {
        'market': 'Kevin Durant To Score 20+ Points',
        'result': 'Kevin Durant',
        'fact': '', 
        'odds': 1.24
    }
    
    result = _extract_prop_info_from_insight(insight)
    print(f"Input: {insight}")
    print(f"Result: {result}")
    
    if result and result.get('player') == 'Kevin Durant' and result.get('stat') == 'points' and result.get('line') == 20.0:
        print("SUCCESS: Correctly extracted from 'market' field")
        return True
    else:
        print("FAILED: Could not extract prop info from market string")
        return False

if __name__ == "__main__":
    t1 = test_historical_hit_rate_field()
    t2 = test_extract_prop_info()
    
    if t1 and t2:
        print("\nALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\nTESTS FAILED")
        sys.exit(1)
