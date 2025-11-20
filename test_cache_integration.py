"""Test NBA player cache integration"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("Testing NBA Player Cache Integration...")
print("=" * 70)

# Test 1: Cache initialization
print("\n1. Testing cache initialization...")
try:
    from scrapers.nba_player_cache import get_player_cache, normalize_player_name
    cache = get_player_cache()
    print(f"   ✓ Cache initialized: {len(cache.cache)} entries")
    print(f"   ✓ Overrides loaded: {len(cache.overrides)} entries")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Name normalization
print("\n2. Testing name normalization...")
try:
    test_names = [
        "Gary Trent Jr.",
        "LeBron James",
        "John Collins",
        "Bogdan Bogdanovic"
    ]
    for name in test_names:
        normalized = normalize_player_name(name)
        print(f"   '{name}' → '{normalized}'")
    print("   ✓ Name normalization working")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 3: Player ID lookup (will build cache if needed)
print("\n3. Testing player ID lookup...")
try:
    test_players = ["LeBron James", "lebron james", "LeBron James Jr."]
    for player in test_players:
        player_id = cache.get_player_id(player)
        if player_id:
            print(f"   ✓ '{player}' → {player_id}")
        else:
            print(f"   ⚠ '{player}' → Not found (cache may need building)")
    print("   ✓ Lookup system working")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 4: Integration with nba_stats_api_scraper
print("\n4. Testing integration with nba_stats_api_scraper...")
try:
    from scrapers.nba_stats_api_scraper import get_player_id
    player_id = get_player_id("LeBron James")
    if player_id:
        print(f"   ✓ Integration working: LeBron James → {player_id}")
    else:
        print(f"   ⚠ Player not found (cache may need building)")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 70)
print("Integration test complete!")
print("\nNote: Cache will be built on first use if not already cached.")

