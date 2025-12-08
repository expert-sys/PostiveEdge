"""
Daily Player Cache Update Script
==================================
Updates player cache with the latest data without rebuilding from scratch.

This script:
1. Loads existing player cache
2. Adds any new players from PlayerIDsV2.txt
3. Updates metadata (timestamp, player counts)
4. Refreshes stats for top 150 players (smart: only if >24hrs old)
5. Saves updated cache

Usage:
    python update_player_cache_daily.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
import logging
from datetime import datetime
from typing import Dict, Optional, List

# Import the comprehensive builder for shared functions
from build_comprehensive_player_cache import (
    parse_player_ids_file,
    build_cache_metadata,
    save_cache,
    print_sample_mappings,
    CACHE_FILE,
    PLAYER_IDS_FILE
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("update_cache")


def load_existing_cache() -> Optional[Dict]:
    """Load existing cache file"""
    if not CACHE_FILE.exists():
        logger.warning(f"Cache file not found: {CACHE_FILE}")
        logger.info("Run 'build_comprehensive_player_cache.py' first to create initial cache")
        return None
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        logger.info(f"[OK] Loaded existing cache:")
        logger.info(f"     Last updated: {cache_data.get('timestamp', 'Unknown')}")
        logger.info(f"     Players: {cache_data.get('total_players', 0)}")
        logger.info(f"     Mappings: {cache_data.get('total_mappings', 0)}")
        
        return cache_data
    except Exception as e:
        logger.error(f"Error loading cache: {e}")
        return None


def compare_and_merge_caches(
    existing_cache: Dict,
    new_name_to_id: Dict[str, int],
    new_id_to_display_name: Dict[str, str],
    new_id_to_team: Dict[str, List[str]]
) -> Dict:
    """
    Compare existing cache with new data and merge intelligently.
    
    Returns:
        Updated cache data with:
        - All existing players preserved
        - New players added
        - Updated metadata
    """
    logger.info("\nComparing caches...")
    
    existing_mappings = existing_cache.get('cache', {})
    existing_display_names = existing_cache.get('display_names', {})
    existing_teams = existing_cache.get('teams', {})
    
    # Count changes
    added_count = 0
    updated_count = 0
    unchanged_count = 0
    
    # Merge name mappings
    merged_mappings = existing_mappings.copy()
    for name, player_id in new_name_to_id.items():
        if name not in existing_mappings:
            merged_mappings[name] = player_id
            added_count += 1
        elif existing_mappings[name] != player_id:
            merged_mappings[name] = player_id
            updated_count += 1
            logger.warning(f"  Updated: '{name}' changed from ID {existing_mappings[name]} to {player_id}")
        else:
            unchanged_count += 1
    
    # Merge display names
    merged_display_names = existing_display_names.copy()
    for player_id, display_name in new_id_to_display_name.items():
        merged_display_names[str(player_id)] = display_name
    
    # Merge teams
    merged_teams = existing_teams.copy()
    for player_id, teams in new_id_to_team.items():
        merged_teams[str(player_id)] = teams
    
    # Build updated cache data
    updated_cache = {
        'timestamp': datetime.now().isoformat(),
        'source': 'PlayerIDsV2.txt',
        'total_players': len(new_id_to_display_name),
        'total_mappings': len(merged_mappings),
        'cache': merged_mappings,
        'display_names': merged_display_names,
        'teams': merged_teams,
        'description': (
            'Comprehensive NBA player cache for prop projections. '
            'Includes normalized names, variants, and team mappings.'
        ),
        'update_summary': {
            'added': added_count,
            'updated': updated_count,
            'unchanged': unchanged_count,
            'previous_total': len(existing_mappings),
            'new_total': len(merged_mappings)
        }
    }
    
    logger.info(f"\n[OK] Cache comparison complete:")
    logger.info(f"     Added: {added_count} new mappings")
    logger.info(f"     Updated: {updated_count} mappings")
    logger.info(f"     Unchanged: {unchanged_count} mappings")
    logger.info(f"     Total: {len(merged_mappings)} mappings")
    
    return updated_cache


def print_update_summary(cache_data: Dict):
    """Print update summary"""
    print("\n" + "="*70)
    print("  UPDATE SUMMARY")
    print("="*70)
    
    summary = cache_data.get('update_summary', {})
    print(f"\nChanges:")
    print(f"  Added: {summary.get('added', 0)} new mappings")
    print(f"  Updated: {summary.get('updated', 0)} mappings")
    print(f"  Unchanged: {summary.get('unchanged', 0)} mappings")
    print(f"\nTotals:")
    print(f"  Previous: {summary.get('previous_total', 0)} mappings")
    print(f"  Current: {summary.get('new_total', 0)} mappings")
    print(f"  Players: {cache_data.get('total_players', 0)}")
    
    print("\n" + "="*70)


def update_stats_cache():
    """Update stats cache for top players (calls fetch_player_stats_batch)"""
    from pathlib import Path
    import subprocess
    
    fetch_script = Path(__file__).parent / "fetch_player_stats_batch.py"
    
    if not fetch_script.exists():
        logger.warning("Stats fetch script not found, skipping stats update")
        return False
    
    print("\nSTEP 5: Refreshing stats for top players...")
    print("-"*70)
    print("This will take a few minutes...\n")
    sys.stdout.flush()
    
    try:
        result = subprocess.run(
            [sys.executable, str(fetch_script)],
            check=False
        )
        
        if result.returncode == 0:
            print("\n[OK] Stats cache updated successfully")
            return True
        else:
            print(f"\n[WARNING] Stats update exited with code {result.returncode}")
            return False
    except Exception as e:
        logger.error(f"Error updating stats cache: {e}")
        return False


def main():
    sys.stdout.flush()
    
    print("\n" + "="*70)
    print("  DAILY PLAYER CACHE UPDATE")
    print("="*70)
    print("\nThis script:")
    print("  1. Adds new players from PlayerIDsV2.txt")
    print("  2. Refreshes game stats for top 150 players (if needed)\n")
    sys.stdout.flush()
    
    # Check if input file exists
    if not PLAYER_IDS_FILE.exists():
        print(f"\n[ERROR] Input file not found: {PLAYER_IDS_FILE}")
        print("\nCreate PlayerIDsV2.txt with player URLs before running this script.")
        print("\nPress Enter to close...")
        sys.stdout.flush()
        input()
        sys.exit(1)
    
    try:
        # Load existing cache
        print("STEP 1: Loading existing cache...")
        print("-"*70)
        existing_cache = load_existing_cache()
        
        if not existing_cache:
            print("\n[WARNING] No existing cache found!")
            print("\nWould you like to create a new cache? (Y/N): ", end='')
            sys.stdout.flush()
            response = input().strip().upper()
            
            if response == 'Y':
                print("\nRedirecting to comprehensive cache builder...")
                print("Please run: python build_comprehensive_player_cache.py")
                print("\nPress Enter to close...")
                sys.stdout.flush()
                input()
                sys.exit(0)
            else:
                print("\nCancelled.")
                print("\nPress Enter to close...")
                sys.stdout.flush()
                input()
                sys.exit(0)
        
        # Parse PlayerIDsV2.txt for latest data
        print("\nSTEP 2: Reading PlayerIDsV2.txt for updates...")
        print("-"*70)
        name_to_id, id_to_display_name, id_to_team = parse_player_ids_file()
        
        if not name_to_id:
            print("\n[ERROR] No players found in PlayerIDsV2.txt!")
            print("\nPress Enter to close...")
            sys.stdout.flush()
            input()
            sys.exit(1)
        
        # Compare and merge
        print("\nSTEP 3: Comparing and merging caches...")
        print("-"*70)
        updated_cache = compare_and_merge_caches(
            existing_cache,
            name_to_id,
            id_to_display_name,
            id_to_team
        )
        sys.stdout.flush()
        
        # Save updated cache
        print("\nSTEP 4: Saving updated cache...")
        print("-"*70)
        save_cache(updated_cache)
        sys.stdout.flush()
        
        # Print summary
        print("\n" + "="*70)
        print("  PLAYER ID UPDATE COMPLETE")
        print("="*70)
        print_update_summary(updated_cache)
        print(f"\nCache File: {CACHE_FILE}")
        print(f"Last Updated: {updated_cache['timestamp']}")
        
        # Print sample if there were additions
        if updated_cache['update_summary']['added'] > 0:
            print("\nNew players added:")
            print_sample_mappings(updated_cache, sample_size=10)
        
        print("\n[OK] Player ID cache is up to date!")
        sys.stdout.flush()
        
        # Ask if user wants to update stats cache
        print("\n" + "="*70)
        print("Would you like to refresh game stats for top 150 players?")
        print("(Recommended if stats are >24 hours old, takes 5-10 minutes)")
        print("="*70)
        response = input("\nUpdate stats cache? (Y/N): ").strip().upper()
        
        if response == 'Y':
            stats_updated = update_stats_cache()
            if stats_updated:
                print("\n[OK] All caches updated successfully!")
            else:
                print("\n[WARNING] Stats update had issues, but player cache is updated")
        else:
            print("\n[OK] Skipping stats update. Run 'Fetch Stats' from menu if needed later.")
        
        sys.stdout.flush()
        
    except Exception as e:
        print("\n" + "="*70)
        print("  ERROR - Cache Update Failed")
        print("="*70)
        print(f"\nError: {e}\n")
        import traceback
        traceback.print_exc()
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
        error_log = Path(__file__).parent / "cache_update_error_log.txt"
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

