"""Quick check that caches are ready"""
import json
from pathlib import Path
from datetime import datetime

print("\n" + "="*70)
print("  CACHE STATUS CHECK")
print("="*70)

# Check Player ID Cache
id_cache = Path("data/cache/databallr_player_cache.json")
print("\n[1] Player ID Cache:")
if id_cache.exists():
    data = json.load(open(id_cache, 'r', encoding='utf-8'))
    print(f"    ✓ READY - {data.get('total_players', 0)} players")
else:
    print("    ❌ NOT FOUND")

# Check Stats Cache  
stats_cache = Path("data/cache/player_stats_cache.json")
print("\n[2] Stats Cache:")
if stats_cache.exists():
    data = json.load(open(stats_cache, 'r', encoding='utf-8'))
    cached = data.get('total_players', 0)
    timestamp = data.get('timestamp', '')
    try:
        age = datetime.now() - datetime.fromisoformat(timestamp)
        age_str = f"{age.seconds // 3600}h ago" if age.days == 0 else f"{age.days}d ago"
    except:
        age_str = "unknown"
    print(f"    ✓ READY - {cached} players ({age_str})")
    
    # Show sample
    cache = data.get('cache', {})
    if cache:
        sample = list(cache.items())[0]
        player_name = sample[0]
        player_stats = sample[1]
        avg = player_stats.get('averages', {})
        print(f"    Sample: {player_name.title()}")
        print(f"      {avg.get('points', 0):.1f} PPG, {avg.get('rebounds', 0):.1f} RPG, {avg.get('assists', 0):.1f} APG")
else:
    print("    ⚠ NOT FOUND (optional - run 'Fetch Stats' for 10x speedup)")

print("\n" + "="*70)
print("RESULT: Pipeline will use cached stats when available!")
print("="*70 + "\n")

