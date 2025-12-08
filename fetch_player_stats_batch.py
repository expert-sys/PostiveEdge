"""
Batch Fetch Player Stats for Cache
===================================
Fetches recent game stats for top NBA players and caches them for fast analysis.

This script:
1. Loads player cache
2. Fetches last 10-20 games for top ~150 players
3. Calculates averages and trends
4. Saves to stats cache with timestamp

Usage:
    python fetch_player_stats_batch.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import asdict

# Import databallr scraper
try:
    from scrapers.databallr_scraper import get_player_game_log, GameLogEntry
except ImportError:
    print("[ERROR] Failed to import databallr_scraper")
    print("Make sure scrapers/databallr_scraper.py exists")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("fetch_stats")

CACHE_DIR = Path(__file__).parent / "data" / "cache"
PLAYER_CACHE_FILE = CACHE_DIR / "databallr_player_cache.json"
STATS_CACHE_FILE = CACHE_DIR / "player_stats_cache.json"

# Top NBA players to pre-fetch (by popularity/fantasy relevance)
TOP_PLAYERS = [
    "Nikola Jokic", "Shai Gilgeous-Alexander", "Giannis Antetokounmpo", "Luka Doncic",
    "Anthony Edwards", "Stephen Curry", "LeBron James", "Kevin Durant", "Joel Embiid",
    "Jayson Tatum", "Anthony Davis", "Donovan Mitchell", "Tyrese Haliburton",
    "Damian Lillard", "Devin Booker", "Jaylen Brown", "Kawhi Leonard", "Jimmy Butler",
    "Paul George", "Bam Adebayo", "DeMar DeRozan", "Trae Young", "Ja Morant",
    "De'Aaron Fox", "Jalen Brunson", "Karl-Anthony Towns", "Pascal Siakam",
    "Domantas Sabonis", "LaMelo Ball", "Tyrese Maxey", "Cade Cunningham",
    "Paolo Banchero", "Franz Wagner", "Scottie Barnes", "Alperen Sengun",
    "Victor Wembanyama", "Evan Mobley", "Jaren Jackson Jr.", "Julius Randle",
    "Zion Williamson", "Brandon Ingram", "Mikal Bridges", "OG Anunoby",
    "Jalen Williams", "Desmond Bane", "Jamal Murray", "Kyrie Irving",
    "Bradley Beal", "Zach LaVine", "CJ McCollum", "Fred VanVleet",
    # Add top prop targets
    "Nikola Vucevic", "Clint Capela", "Draymond Green", "Darius Garland",
    "Tyler Herro", "Jordan Poole", "Anfernee Simons", "Jalen Green",
    "Chet Holmgren", "Jaden Ivey", "Devin Vassell", "RJ Barrett",
    "Donte DiVincenzo", "Malik Monk", "Immanuel Quickley", "Coby White",
    "Herbert Jones", "Alex Caruso", "Derrick White", "Marcus Smart",
    "Jrue Holiday", "Brook Lopez", "Myles Turner", "Jarrett Allen",
    "Rudy Gobert", "Jakob Poeltl", "Nic Claxton", "Isaiah Hartenstein",
    "Cam Thomas", "Collin Sexton", "Jordan Clarkson", "Bobby Portis",
    "Kyle Kuzma", "Tobias Harris", "Harrison Barnes", "Andrew Wiggins",
    "Bogdan Bogdanovic", "Buddy Hield", "Gary Trent Jr", "Kentavious Caldwell-Pope",
    "Tim Hardaway Jr", "Josh Hart", "Derrick Jones Jr", "Caleb Martin",
    # More rotation players
    "Bones Hyland", "Christian Braun", "Payton Pritchard", "Miles McBride",
    "Naz Reid", "Jalen Suggs", "Cole Anthony", "Russell Westbrook",
    "Dennis Schroder", "Monte Morris", "Tyus Jones", "Tre Jones",
    "Aaron Nesmith", "Obi Toppin", "Jalen Smith", "Isaiah Jackson",
    "Walker Kessler", "Mark Williams", "Nick Richards", "Daniel Gafford",
    "PJ Washington", "John Collins", "Jerami Grant", "Kelly Olynyk",
    "Jonas Valanciunas", "Andre Drummond", "Steven Adams", "Mason Plumlee",
    "Ivica Zubac", "Jusuf Nurkic", "Deandre Ayton", "Kristaps Porzingis",
    "Lauri Markkanen", "Michael Porter Jr", "Keegan Murray", "Jeremy Sochan",
    "Ausar Thompson", "Brandin Podziemski", "Jaime Jaquez Jr", "Keyonte George",
    "Gradey Dick", "Bilal Coulibaly", "Cason Wallace", "Amen Thompson",
    "Cam Whitmore", "Kris Murray", "Kobe Brown", "GG Jackson",
    "Leonard Miller", "Trayce Jackson-Davis", "Dereck Lively II", "Noah Clowney",
    "Onyeka Okongwu", "Jalen Johnson", "Dyson Daniels", "Trey Murphy III",
    "Jose Alvarado", "Naji Marshall", "Max Christie", "Jaden Hardy",
    "Ochai Agbaji", "David Roddy", "Maxwell Lewis", "Julian Strawther",
    "Toumani Camara", "Rayan Rupert", "Scoot Henderson", "Kobe Bufkin"
]


def calculate_averages(game_log: List[GameLogEntry]) -> Dict:
    """Calculate averages from game log"""
    if not game_log:
        return {}
    
    total_games = len(game_log)
    
    stats = {
        'games': total_games,
        'minutes': sum(g.minutes for g in game_log) / total_games,
        'points': sum(g.points for g in game_log) / total_games,
        'rebounds': sum(g.rebounds for g in game_log) / total_games,
        'assists': sum(g.assists for g in game_log) / total_games,
        'steals': sum(g.steals for g in game_log) / total_games,
        'blocks': sum(g.blocks for g in game_log) / total_games,
        'turnovers': sum(g.turnovers for g in game_log) / total_games,
        'three_pt_made': sum(g.three_pt_made for g in game_log) / total_games,
        'ft_made': sum(g.ft_made for g in game_log) / total_games,
    }
    
    # Calculate recent trends (last 3 vs last 10)
    if total_games >= 5:
        recent_3 = game_log[:3]
        stats['recent_pts'] = sum(g.points for g in recent_3) / len(recent_3)
        stats['recent_reb'] = sum(g.rebounds for g in recent_3) / len(recent_3)
        stats['recent_ast'] = sum(g.assists for g in recent_3) / len(recent_3)
    
    return stats


def load_player_cache() -> Dict:
    """Load player ID cache"""
    if not PLAYER_CACHE_FILE.exists():
        logger.error(f"Player cache not found: {PLAYER_CACHE_FILE}")
        logger.info("Run 'build_comprehensive_player_cache.py' first")
        return {}
    
    try:
        with open(PLAYER_CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error loading player cache: {e}")
        return {}


def load_stats_cache() -> Dict:
    """Load existing stats cache"""
    if not STATS_CACHE_FILE.exists():
        return {}
    
    try:
        with open(STATS_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading stats cache: {e}")
        return {}


def save_stats_cache(stats_cache: Dict):
    """Save stats cache to file"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'total_players': len(stats_cache),
            'cache': stats_cache,
            'description': 'Pre-fetched game stats for top NBA players'
        }
        
        with open(STATS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[OK] Saved stats for {len(stats_cache)} players to {STATS_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error saving stats cache: {e}")
        raise


def is_cache_fresh(player_stats: Dict, max_age_hours: int = 24) -> bool:
    """Check if cached stats are still fresh"""
    if not player_stats or 'timestamp' not in player_stats:
        return False
    
    try:
        cached_time = datetime.fromisoformat(player_stats['timestamp'])
        age = datetime.now() - cached_time
        return age < timedelta(hours=max_age_hours)
    except:
        return False


def fetch_stats_for_player(player_name: str, force_refresh: bool = False) -> Optional[Dict]:
    """
    Fetch game stats for a single player.
    
    Args:
        player_name: Player name to fetch
        force_refresh: If True, ignore cache and fetch fresh
    
    Returns:
        Dict with game_log and averages, or None if failed
    """
    # Check existing cache first
    if not force_refresh:
        existing_cache = load_stats_cache()
        player_cache = existing_cache.get('cache', {})
        
        if player_name.lower() in player_cache:
            player_stats = player_cache[player_name.lower()]
            if is_cache_fresh(player_stats):
                logger.info(f"  [CACHED] {player_name} (age: {player_stats.get('timestamp', 'unknown')})")
                return player_stats
    
    # Fetch fresh stats
    try:
        logger.info(f"  [FETCHING] {player_name}...")
        game_log = get_player_game_log(
            player_name,
            last_n_games=15,
            headless=True,
            use_cache=True
        )
        
        if not game_log:
            logger.warning(f"  [FAILED] No games found for {player_name}")
            return None
        
        # Calculate averages
        averages = calculate_averages(game_log)
        
        # Convert game log to serializable format
        game_log_dict = [asdict(game) for game in game_log]
        
        player_stats = {
            'timestamp': datetime.now().isoformat(),
            'game_count': len(game_log),
            'averages': averages,
            'game_log': game_log_dict,
            'last_game_date': game_log[0].game_date if game_log else None
        }
        
        logger.info(f"  [OK] {player_name}: {len(game_log)} games, {averages.get('points', 0):.1f} PPG")
        return player_stats
        
    except Exception as e:
        logger.error(f"  [ERROR] {player_name}: {e}")
        return None


def main():
    sys.stdout.flush()
    
    print("\n" + "="*70)
    print("  FETCH PLAYER STATS (TOP 150)")
    print("="*70)
    print("\nThis script pre-fetches game stats for top NBA players")
    print("to speed up prop analysis. Runs in ~5-10 minutes.\n")
    sys.stdout.flush()
    
    # Load player cache
    print("STEP 1: Loading player cache...")
    print("-"*70)
    player_cache = load_player_cache()
    
    if not player_cache:
        print("\n[ERROR] Player cache not found!")
        print("Run 'build_comprehensive_player_cache.py' first.")
        print("\nPress Enter to close...")
        sys.stdout.flush()
        input()
        sys.exit(1)
    
    print(f"[OK] Loaded {player_cache.get('total_players', 0)} players from cache\n")
    sys.stdout.flush()
    
    # Load existing stats cache
    print("STEP 2: Loading existing stats cache...")
    print("-"*70)
    existing_stats = load_stats_cache()
    stats_cache = existing_stats.get('cache', {})
    print(f"[OK] Found {len(stats_cache)} players with cached stats\n")
    sys.stdout.flush()
    
    # Fetch stats for top players
    print(f"STEP 3: Fetching stats for top {len(TOP_PLAYERS)} players...")
    print("-"*70)
    print("This will take 5-10 minutes. Please be patient...\n")
    sys.stdout.flush()
    
    success_count = 0
    failed_count = 0
    cached_count = 0
    
    for i, player_name in enumerate(TOP_PLAYERS, 1):
        print(f"[{i}/{len(TOP_PLAYERS)}] Processing: {player_name}")
        
        player_stats = fetch_stats_for_player(player_name, force_refresh=False)
        
        if player_stats:
            stats_cache[player_name.lower()] = player_stats
            if 'game_log' in player_stats and len(player_stats['game_log']) > 0:
                success_count += 1
            else:
                cached_count += 1
        else:
            failed_count += 1
        
        # Progress update every 25 players
        if i % 25 == 0:
            print(f"\nProgress: {i}/{len(TOP_PLAYERS)} processed")
            print(f"  Success: {success_count}, Cached: {cached_count}, Failed: {failed_count}\n")
            sys.stdout.flush()
    
    # Save stats cache
    print("\nSTEP 4: Saving stats cache...")
    print("-"*70)
    save_stats_cache(stats_cache)
    sys.stdout.flush()
    
    # Print summary
    print("\n" + "="*70)
    print("  FETCH COMPLETE")
    print("="*70)
    print(f"\nTotal Processed: {len(TOP_PLAYERS)}")
    print(f"Successfully Fetched: {success_count}")
    print(f"Used Cache: {cached_count}")
    print(f"Failed: {failed_count}")
    print(f"\nTotal in Cache: {len(stats_cache)} players")
    print(f"Cache File: {STATS_CACHE_FILE}")
    print("\n[OK] Stats cache is ready for fast analysis!")
    sys.stdout.flush()
    
    print("\nPress Enter to close...")
    sys.stdout.flush()
    try:
        input()
    except:
        pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except SystemExit:
        pass
    except Exception as e:
        print("\n" + "="*70)
        print("  FATAL ERROR")
        print("="*70)
        print(f"\n{e}\n")
        
        import traceback
        traceback.print_exc()
        
        # Save error to file
        error_log = Path(__file__).parent / "fetch_stats_error_log.txt"
        try:
            with open(error_log, 'w', encoding='utf-8') as f:
                f.write(f"ERROR at {datetime.now()}\n")
                f.write(f"{str(e)}\n\n")
                f.write(traceback.format_exc())
            print(f"\nFull error saved to: {error_log}")
        except:
            pass
        
        print("\nPress Enter to close...")
        try:
            input()
        except:
            pass

