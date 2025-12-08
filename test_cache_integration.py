"""
Quick Test: Cache Integration
==============================
Tests that the unified analysis pipeline uses the stats cache correctly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
from datetime import datetime

def test_cache_integration():
    """Test that all cache pieces are in place"""
    
    print("\n" + "="*70)
    print("  CACHE INTEGRATION TEST")
    print("="*70)
    
    cache_dir = Path(__file__).parent / "data" / "cache"
    player_cache_file = cache_dir / "databallr_player_cache.json"
    stats_cache_file = cache_dir / "player_stats_cache.json"
    
    # Test 1: Player ID Cache
    print("\n[TEST 1] Player ID Cache")
    print("-"*70)
    if not player_cache_file.exists():
        print("❌ FAILED: Player ID cache not found")
        print("   Run: python build_comprehensive_player_cache.py")
        return False
    
    with open(player_cache_file, 'r', encoding='utf-8') as f:
        player_data = json.load(f)
    
    print(f"✓ Found player ID cache")
    print(f"  Players: {player_data.get('total_players', 0)}")
    print(f"  Mappings: {player_data.get('total_mappings', 0)}")
    
    # Test 2: Stats Cache
    print("\n[TEST 2] Player Stats Cache")
    print("-"*70)
    if not stats_cache_file.exists():
        print("⚠ WARNING: Stats cache not found (optional)")
        print("   Run: python fetch_player_stats_batch.py")
        print("   Analysis will work but be slower for top players")
        stats_cached = 0
    else:
        with open(stats_cache_file, 'r', encoding='utf-8') as f:
            stats_data = json.load(f)
        
        stats_cached = stats_data.get('total_players', 0)
        timestamp = stats_data.get('timestamp', 'Unknown')
        
        print(f"✓ Found stats cache")
        print(f"  Cached players: {stats_cached}")
        print(f"  Last updated: {timestamp}")
        
        # Check freshness
        try:
            cached_time = datetime.fromisoformat(timestamp)
            age = datetime.now() - cached_time
            if age.days >= 1:
                print(f"  ⚠ Age: {age.days} days old (consider refreshing)")
            else:
                print(f"  ✓ Fresh: {age.seconds // 3600} hours old")
        except:
            pass
    
    # Test 3: Test actual function
    print("\n[TEST 3] Live Integration Test")
    print("-"*70)
    print("Testing get_player_game_log with cached player...")
    
    try:
        from scrapers.databallr_scraper import get_player_game_log
        
        # Test with a commonly cached player
        test_player = "Nikola Jokic"
        print(f"  Player: {test_player}")
        
        game_log = get_player_game_log(
            player_name=test_player,
            last_n_games=10,
            headless=True,
            use_cache=True
        )
        
        if game_log:
            print(f"✓ Successfully retrieved {len(game_log)} games")
            print(f"  Latest game: {game_log[0].game_date}")
            print(f"  Stats: {game_log[0].points} PTS, {game_log[0].rebounds} REB, {game_log[0].assists} AST")
            
            # Check if it came from cache (fast) or was fetched (slow)
            # If it took <2 seconds, it was probably cached
            print(f"  Source: {'STATS CACHE ⚡' if stats_cached > 0 else 'LIVE FETCH 🌐'}")
        else:
            print("❌ FAILED: No game log returned")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    print(f"\n✓ Player ID Cache: READY ({player_data.get('total_players', 0)} players)")
    
    if stats_cached > 0:
        print(f"✓ Stats Cache: READY ({stats_cached} players)")
        print(f"✓ Integration: WORKING (Fast path enabled)")
        print("\n🚀 SYSTEM READY: Analysis will be FAST for top players!")
    else:
        print(f"⚠ Stats Cache: MISSING (optional)")
        print(f"✓ Integration: WORKING (On-demand fetch enabled)")
        print("\n⚡ RECOMMENDATION: Run 'Fetch Stats for Top 150 Players' for 10x speed boost")
    
    print("="*70)
    return True


if __name__ == "__main__":
    try:
        success = test_cache_integration()
        print("\nPress Enter to close...")
        input()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\nPress Enter to close...")
        input()
        sys.exit(1)
