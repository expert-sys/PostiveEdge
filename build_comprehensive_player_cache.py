"""
Build Comprehensive Player Cache from PlayerIDsV2.txt
======================================================
One-time script to build a complete player cache with all data needed for prop projections.

This script:
1. Reads PlayerIDsV2.txt with all NBA players and their databallr URLs
2. Extracts player IDs and creates normalized name mappings
3. Optionally fetches recent game stats for each player
4. Saves comprehensive cache for instant lookups

Usage:
    python build_comprehensive_player_cache.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("build_comprehensive_cache")

CACHE_DIR = Path(__file__).parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "databallr_player_cache.json"
PLAYER_IDS_FILE = Path(__file__).parent / "PlayerIDsV2.txt"


def normalize_player_name(name: str) -> str:
    """
    Normalize player name for consistent matching.
    Handles: periods, extra spaces, apostrophes, special chars
    
    Examples:
        "E.J. Liddell" -> "ej liddell"
        "Day'Ron Sharpe" -> "dayron sharpe"
        "Nikola Vučević" -> "nikola vucevic"
    """
    # Remove periods
    normalized = name.replace('.', '')
    # Replace apostrophes
    normalized = normalized.replace("'", '')
    # Remove accents/diacritics (simple version)
    replacements = {
        'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a',
        'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e',
        'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i',
        'ó': 'o', 'ò': 'o', 'ö': 'o', 'ô': 'o',
        'ú': 'u', 'ù': 'u', 'ü': 'u', 'û': 'u',
        'ñ': 'n', 'ç': 'c', 'š': 's', 'ž': 'z',
        'Š': 's', 'Ž': 'z', 'č': 'c', 'ć': 'c',
        'đ': 'd', 'ğ': 'g', 'ı': 'i', 'ş': 's',
        'ū': 'u', 'ė': 'e', 'ą': 'a', 'ę': 'e',
        'į': 'i', 'ų': 'u', 'ū': 'u',
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
        normalized = normalized.replace(old.upper(), new.upper())
    
    # Lowercase and clean whitespace
    normalized = normalized.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized


def generate_name_variants(player_name: str) -> List[str]:
    """
    Generate common name variants for robust matching.
    
    Examples:
        "E.J. Liddell" -> ["ej liddell", "e j liddell", "liddell"]
        "Shai Gilgeous-Alexander" -> ["shai gilgeous alexander", "shai gilgeousalexander", "shai"]
    """
    variants = []
    
    # Primary normalized name
    normalized = normalize_player_name(player_name)
    variants.append(normalized)
    
    # Remove spaces in compound names (e.g., "Gilgeous-Alexander" -> "GilgeousAlexander")
    if '-' in player_name:
        no_hyphen = player_name.replace('-', ' ')
        variants.append(normalize_player_name(no_hyphen))
        no_hyphen_nospace = player_name.replace('-', '')
        variants.append(normalize_player_name(no_hyphen_nospace))
    
    # First name only (for unique players like "Giannis", "Luka", "Shai")
    parts = normalized.split()
    if len(parts) >= 2:
        variants.append(parts[0])  # First name only
    
    # Last name only
    if len(parts) >= 2:
        variants.append(parts[-1])  # Last name only
    
    # Handle Jr./II/III suffixes
    if 'jr' in normalized or 'ii' in normalized or 'iii' in normalized:
        # Version without suffix
        without_suffix = re.sub(r'\s+(jr|ii|iii)$', '', normalized)
        if without_suffix != normalized:
            variants.append(without_suffix)
    
    return list(set(variants))  # Remove duplicates


def extract_player_from_url_line(line: str) -> Optional[Tuple[str, int, str]]:
    """
    Extract player info from a line in PlayerIDsV2.txt.
    
    Format: "Player Name - https://databallr.com/last-games/ID/slug"
    
    Returns:
        (display_name, player_id, team) tuple or None
    """
    # Skip empty lines or team headers (lines without URLs)
    if not line.strip() or 'databallr.com/last-games/' not in line:
        return None
    
    # Extract player name (before the dash)
    match = re.match(r'^(.+?)\s*-\s*https://databallr\.com/last-games/(\d+)/([^/?]+)', line)
    if match:
        player_name = match.group(1).strip()
        player_id = int(match.group(2))
        player_slug = match.group(3)
        return (player_name, player_id, player_slug)
    
    return None


def parse_player_ids_file() -> Tuple[Dict[str, int], Dict[str, str], Dict[str, List[str]]]:
    """
    Parse PlayerIDsV2.txt and build comprehensive player mappings.
    
    Returns:
        Tuple of:
        - name_to_id: Normalized name -> Player ID mapping
        - id_to_display_name: Player ID -> Display name mapping
        - id_to_team: Player ID -> Team name mapping
    """
    logger.info(f"Reading: {PLAYER_IDS_FILE}")
    
    if not PLAYER_IDS_FILE.exists():
        logger.error(f"File not found: {PLAYER_IDS_FILE}")
        return {}, {}, {}
    
    name_to_id = {}
    id_to_display_name = {}
    id_to_team = {}
    variant_to_id = {}  # Track all name variants
    
    current_team = None
    players_added = 0
    errors = []
    
    try:
        with open(PLAYER_IDS_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if it's a team header (no URL, no dash)
            if ' - ' not in line and 'databallr.com' not in line:
                current_team = line
                logger.debug(f"  Team: {current_team}")
                continue
            
            # Try to parse player line
            result = extract_player_from_url_line(line)
            if result:
                player_name, player_id, player_slug = result
                
                # Primary normalized name
                normalized_name = normalize_player_name(player_name)
                
                # Check for duplicates
                if normalized_name in name_to_id:
                    existing_id = name_to_id[normalized_name]
                    if existing_id != player_id:
                        logger.warning(
                            f"  [Line {line_num}] Duplicate name with different ID: "
                            f"{player_name} (ID: {player_id} vs {existing_id})"
                        )
                
                # Add primary mapping
                name_to_id[normalized_name] = player_id
                id_to_display_name[player_id] = player_name
                
                # Track team
                if current_team:
                    if player_id not in id_to_team:
                        id_to_team[player_id] = []
                    id_to_team[player_id].append(current_team)
                
                # Generate and store name variants
                variants = generate_name_variants(player_name)
                for variant in variants:
                    if variant not in variant_to_id:
                        variant_to_id[variant] = player_id
                        # Add variant to main mapping if not duplicate
                        if variant not in name_to_id:
                            name_to_id[variant] = player_id
                
                players_added += 1
                logger.info(
                    f"  [{players_added}] {player_name} (ID: {player_id}, Team: {current_team or 'Unknown'})"
                )
            else:
                if 'databallr.com' in line:
                    error_msg = f"Line {line_num}: Failed to parse: {line[:60]}"
                    logger.warning(f"  [ERROR] {error_msg}")
                    errors.append(error_msg)
        
        logger.info(f"\n[OK] Parsed {players_added} players from {len(lines)} lines")
        logger.info(f"     Primary mappings: {len(name_to_id)}")
        logger.info(f"     Name variants: {len(variant_to_id)}")
        
        if errors:
            logger.warning(f"\n{len(errors)} parsing errors (see above)")
        
        return name_to_id, id_to_display_name, id_to_team
    
    except Exception as e:
        logger.error(f"Error reading {PLAYER_IDS_FILE}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}, {}, {}


def build_cache_metadata(
    name_to_id: Dict[str, int],
    id_to_display_name: Dict[str, str],
    id_to_team: Dict[str, List[str]]
) -> Dict:
    """Build comprehensive cache data structure"""
    cache_data = {
        'timestamp': datetime.now().isoformat(),
        'source': 'PlayerIDsV2.txt',
        'total_players': len(id_to_display_name),
        'total_mappings': len(name_to_id),
        'cache': name_to_id,
        'display_names': {str(k): v for k, v in id_to_display_name.items()},
        'teams': {str(k): v for k, v in id_to_team.items()},
        'description': (
            'Comprehensive NBA player cache for prop projections. '
            'Includes normalized names, variants, and team mappings.'
        )
    }
    return cache_data


def save_cache(cache_data: Dict):
    """Save cache to file"""
    try:
        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n[OK] Cache saved successfully!")
        logger.info(f"     Location: {CACHE_FILE}")
        logger.info(f"     Players: {cache_data['total_players']}")
        logger.info(f"     Mappings: {cache_data['total_mappings']}")
    except Exception as e:
        logger.error(f"\n[ERROR] Failed to save cache: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def merge_with_existing_cache(new_cache_data: Dict) -> Dict:
    """Merge new cache with existing cache, preserving any manual additions"""
    if CACHE_FILE.exists():
        try:
            logger.info(f"\nMerging with existing cache...")
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            existing_cache = existing_data.get('cache', {})
            new_cache = new_cache_data['cache']
            
            # Merge (new entries override old)
            merged_cache = {**existing_cache, **new_cache}
            
            # Update cache data
            new_cache_data['cache'] = merged_cache
            new_cache_data['total_mappings'] = len(merged_cache)
            
            logger.info(f"  Existing: {len(existing_cache)} mappings")
            logger.info(f"  New: {len(new_cache)} mappings")
            logger.info(f"  Merged: {len(merged_cache)} mappings")
            
            return new_cache_data
        except Exception as e:
            logger.warning(f"  Error loading existing cache: {e}")
            logger.warning(f"  Proceeding with new cache only")
    
    return new_cache_data


def print_sample_mappings(cache_data: Dict, sample_size: int = 10):
    """Print sample mappings for verification"""
    cache = cache_data['cache']
    display_names = cache_data.get('display_names', {})
    
    print("\n" + "="*70)
    print("SAMPLE PLAYER MAPPINGS")
    print("="*70)
    
    sample_keys = list(cache.keys())[:sample_size]
    for key in sample_keys:
        player_id = cache[key]
        display_name = display_names.get(str(player_id), "Unknown")
        print(f"  '{key}' -> {player_id} ({display_name})")
    
    if len(cache) > sample_size:
        print(f"  ... and {len(cache) - sample_size} more mappings")
    print("="*70)


def main():
    sys.stdout.flush()
    
    print("\n" + "="*70)
    print("  BUILD COMPREHENSIVE PLAYER CACHE")
    print("="*70)
    print("\nThis script builds a complete player cache from PlayerIDsV2.txt")
    print("for instant lookups during prop projection analysis.\n")
    sys.stdout.flush()
    
    # Check if input file exists
    if not PLAYER_IDS_FILE.exists():
        print(f"\n[ERROR] Input file not found: {PLAYER_IDS_FILE}")
        print("\nExpected file format:")
        print("  Team Name")
        print("  ")
        print("  Player Name - https://databallr.com/last-games/ID/slug")
        print("  Player Name - https://databallr.com/last-games/ID/slug")
        print("  ...")
        print("\nPress Enter to close...")
        sys.stdout.flush()
        input()
        sys.exit(1)
    
    print(f"[OK] Found input file: {PLAYER_IDS_FILE}\n")
    sys.stdout.flush()
    
    try:
        # Parse player IDs file
        print("STEP 1: Parsing PlayerIDsV2.txt...")
        print("-"*70)
        name_to_id, id_to_display_name, id_to_team = parse_player_ids_file()
        
        if not name_to_id:
            print("\n[ERROR] No players found in input file!")
            print("\nPress Enter to close...")
            sys.stdout.flush()
            input()
            sys.exit(1)
        
        # Build cache data structure
        print("\nSTEP 2: Building cache data structure...")
        print("-"*70)
        cache_data = build_cache_metadata(name_to_id, id_to_display_name, id_to_team)
        print(f"[OK] Cache structure built")
        sys.stdout.flush()
        
        # Merge with existing cache
        print("\nSTEP 3: Merging with existing cache (if exists)...")
        print("-"*70)
        cache_data = merge_with_existing_cache(cache_data)
        print(f"[OK] Merge complete")
        sys.stdout.flush()
        
        # Save cache
        print("\nSTEP 4: Saving cache to disk...")
        print("-"*70)
        save_cache(cache_data)
        sys.stdout.flush()
        
        # Print summary
        print("\n" + "="*70)
        print("  CACHE BUILD COMPLETE")
        print("="*70)
        print(f"\nTotal Players: {cache_data['total_players']}")
        print(f"Total Mappings (including variants): {cache_data['total_mappings']}")
        print(f"Cache File: {CACHE_FILE}")
        print("\nThe system will now use this cache for instant player lookups!")
        
        # Print sample mappings
        print_sample_mappings(cache_data, sample_size=15)
        
        print("\n[OK] All done! You can now run prop projection analysis.")
        sys.stdout.flush()
        
    except Exception as e:
        print("\n" + "="*70)
        print("  ERROR - Cache Build Failed")
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
        error_log = Path(__file__).parent / "cache_builder_error_log.txt"
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

