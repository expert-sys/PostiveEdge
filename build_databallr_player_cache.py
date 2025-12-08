"""
Build Databallr Player ID Cache
================================
One-time script to scrape all NBA player IDs from databallr.com and save them to a cache file.

This eliminates the need for hardcoded player mappings - just run this once to build a complete cache.

Usage:
    python build_databallr_player_cache.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
import re

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("build_databallr_cache")

CACHE_DIR = Path(__file__).parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "databallr_player_cache.json"


def normalize_player_name(name: str) -> str:
    """Normalize player name for consistent matching"""
    # Remove periods (e.g., C.J. -> CJ), lowercase, and remove extra whitespace
    normalized = name.lower().strip().replace('.', '')
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def extract_player_id_from_url(url: str) -> Optional[int]:
    """Extract player ID from databallr URL"""
    # URL format: https://databallr.com/last-games/1626171/bobby-portis
    match = re.search(r'/last-games/(\d+)/', url)
    if match:
        return int(match.group(1))
    return None


def scrape_all_players_from_databallr(headless: bool = True) -> Dict[str, int]:
    """
    Scrape all NBA players from databallr.com by searching/browsing the site.
    
    Returns:
        Dictionary mapping normalized player names to player IDs
    """
    logger.info("Starting databallr player cache build...")
    
    player_cache = {}
    
    # Try multiple approaches to get player list
    # Approach 1: Search/browse NBA players section
    # Approach 2: Extract from player pages we visit
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        )
        
        page = context.new_page()
        
        try:
            # Try to find a players listing page or search functionality
            logger.info("Navigating to databallr.com...")
            page.goto("https://databallr.com", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=10000)
            
            # Look for navigation that might lead to player listings
            # Try common patterns like "Players", "NBA Players", etc.
            
            logger.info("Looking for player listing or search functionality...")
            
            # Method 1: Try to find a search box or player listing
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="search" i]',
                'input[placeholder*="player" i]',
                '.search-input',
                '#search',
            ]
            
            search_found = False
            for selector in search_selectors:
                try:
                    search_box = page.query_selector(selector)
                    if search_box and search_box.is_visible():
                        logger.info(f"Found search box with selector: {selector}")
                        search_found = True
                        break
                except:
                    continue
            
            # Method 2: Extract from known players by visiting their pages
            # We'll use a comprehensive list of current NBA players
            known_players = [
                # Stars (already in mapping)
                "LeBron James", "Stephen Curry", "Kevin Durant", "Giannis Antetokounmpo",
                "Luka Doncic", "Nikola Jokic", "Joel Embiid", "Jayson Tatum",
                "Damian Lillard", "Anthony Davis", "Kawhi Leonard", "James Harden",
                "Kyrie Irving", "Paul George", "Devin Booker", "Donovan Mitchell",
                "Trae Young", "Ja Morant", "Zion Williamson", "LaMelo Ball",
                "Shai Gilgeous-Alexander", "Jimmy Butler", "Bam Adebayo",
                "Karl-Anthony Towns", "Pascal Siakam", "Domantas Sabonis",
                "Dejounte Murray", "Fred VanVleet", "CJ McCollum", "Bradley Beal",
                "Kyle Kuzma", "Jordan Poole", "Tyrese Haliburton", "Julius Randle",
                "Draymond Green", "Klay Thompson", "Russell Westbrook", "Chris Paul",
                # Additional players
                "Bobby Portis", "Alex Sarr", "Andrew Wiggins", "Jrue Holiday",
                "Khris Middleton", "Brook Lopez", "De'Aaron Fox", "Malik Monk",
                "Keegan Murray", "Harrison Barnes", "Domantas Sabonis", "De'Aaron Fox",
                "Desmond Bane", "Jaren Jackson Jr.", "Marcus Smart", "Ja Morant",
                "RJ Barrett", "Jalen Brunson", "Julius Randle", "Mitchell Robinson",
                "Jalen Green", "Alperen Sengun", "Jabari Smith Jr.", "Fred VanVleet",
                "DeMar DeRozan", "Zach LaVine", "Nikola Vucevic", "Coby White",
                "Darius Garland", "Donovan Mitchell", "Evan Mobley", "Jarrett Allen",
                "Luka Doncic", "Kyrie Irving", "Tim Hardaway Jr.", "Derrick Jones Jr.",
                "Jamal Murray", "Michael Porter Jr.", "Aaron Gordon", "Kentavious Caldwell-Pope",
                "Jayson Tatum", "Jaylen Brown", "Kristaps Porzingis", "Jrue Holiday",
                "Shai Gilgeous-Alexander", "Chet Holmgren", "Jalen Williams", "Luguentz Dort",
                "Paul George", "Kawhi Leonard", "James Harden", "Ivica Zubac",
                "Stephen Curry", "Klay Thompson", "Draymond Green", "Andrew Wiggins",
                "LeBron James", "Anthony Davis", "Austin Reaves", "D'Angelo Russell",
                "Damian Lillard", "Giannis Antetokounmpo", "Khris Middleton", "Brook Lopez",
                "Joel Embiid", "Tyrese Maxey", "Tobias Harris", "Nicolas Batum",
                "Devin Booker", "Bradley Beal", "Kevin Durant", "Jusuf Nurkic",
                "Trae Young", "Dejounte Murray", "Bogdan Bogdanovic", "Clint Capela",
                "Cade Cunningham", "Jaden Ivey", "Ausar Thompson", "Jalen Duren",
                "Paolo Banchero", "Franz Wagner", "Jalen Suggs", "Wendell Carter Jr.",
            ]
            
            logger.info(f"Attempting to extract player IDs from {len(known_players)} known players...")
            
            for i, player_name in enumerate(known_players, 1):
                try:
                    normalized = normalize_player_name(player_name)
                    
                    # Skip if already in cache
                    if normalized in player_cache:
                        continue
                    
                    # Try to find player by searching or constructing URL
                    logger.info(f"[{i}/{len(known_players)}] Looking up: {player_name}")
                    
                    # Method: Try to construct URL pattern and verify it exists
                    # We'll try a few common slug formats
                    name_slug = player_name.lower().replace(' ', '-').replace('.', '').replace("'", '')
                    
                    # Try to search for the player
                    if search_found:
                        try:
                            search_box = page.query_selector(search_selectors[0])
                            if search_box:
                                search_box.clear()
                                search_box.fill(player_name)
                                page.wait_for_timeout(1000)
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(2000)
                                
                                # Check if we navigated to a player page
                                current_url = page.url
                                if '/last-games/' in current_url:
                                    player_id = extract_player_id_from_url(current_url)
                                    if player_id:
                                        player_cache[normalized] = player_id
                                        logger.info(f"  [OK] Found: {player_name} (ID: {player_id})")
                                        continue
                        except Exception as e:
                            logger.debug(f"  Search failed: {e}")
                    
                    # Throttle requests
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"  Error processing {player_name}: {e}")
                    continue
            
            browser.close()
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            browser.close()
    
    logger.info(f"Scraped {len(player_cache)} player IDs from databallr")
    return player_cache


def extract_player_from_url(url: str) -> Optional[tuple]:
    """
    Extract player name and ID from databallr URL.
    
    Returns:
        (player_name, player_id) tuple or None
    """
    match = re.search(r'/last-games/(\d+)/([^/?]+)', url)
    if match:
        player_id = int(match.group(1))
        player_slug = match.group(2)
        # Convert slug to readable name (e.g., "bobby-portis" -> "Bobby Portis")
        player_name = ' '.join(word.capitalize() for word in player_slug.split('-'))
        return (player_name, player_id)
    return None


def build_cache_from_urls(urls: List[str]) -> Dict[str, int]:
    """
    Build cache by extracting player IDs from databallr URLs.
    
    Args:
        urls: List of databallr player URLs
    """
    logger.info(f"Building cache from {len(urls)} player URLs...")
    
    player_cache = {}
    errors = []
    
    for i, url in enumerate(urls, 1):
        try:
            result = extract_player_from_url(url)
            if result:
                player_name, player_id = result
                normalized = normalize_player_name(player_name)
                
                # Check for duplicates
                if normalized in player_cache:
                    logger.warning(f"  [SKIP] Duplicate: {player_name} (already in cache)")
                else:
                    player_cache[normalized] = player_id
                    logger.info(f"  [{i}/{len(urls)}] [OK] Added: {player_name} (ID: {player_id})")
            else:
                error_msg = f"Invalid URL format: {url}"
                logger.warning(f"  [{i}/{len(urls)}] [ERROR] {error_msg}")
                errors.append(error_msg)
        except Exception as e:
            error_msg = f"Error processing {url}: {e}"
            logger.error(f"  [{i}/{len(urls)}] [ERROR] {error_msg}")
            errors.append(error_msg)
    
    if errors:
        logger.warning(f"\n{len(errors)} errors encountered (see above)")
    
    return player_cache


def load_player_ids_file(file_path: Optional[str] = None) -> List[str]:
    """Load URLs from PlayerIDs.txt file if it exists"""
    if file_path is None:
        # Check for PlayerIDs.txt in project root
        project_root = Path(__file__).parent
        file_path = project_root / "PlayerIDs.txt"
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            urls = [line.strip() for line in lines if line.strip() and 'databallr.com/last-games/' in line]
            logger.info(f"Loaded {len(urls)} URLs from {file_path} (total lines: {len(lines)})")
            return urls
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error reading {file_path}: {e}")
        logger.info("Trying with different encoding...")
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                lines = f.readlines()
                urls = [line.strip() for line in lines if line.strip() and 'databallr.com/last-games/' in line]
                logger.info(f"Loaded {len(urls)} URLs with latin-1 encoding")
                return urls
        except Exception as e2:
            logger.error(f"Failed with latin-1 encoding: {e2}")
            return []
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []


def build_cache_from_existing_urls() -> Dict[str, int]:
    """
    Build cache from hardcoded known player URLs.
    """
    logger.info("Building cache from known player URLs...")
    
    # Known player URLs - add more as you find them
    known_urls = [
        "https://databallr.com/last-games/1626171/bobby-portis",
        "https://databallr.com/last-games/203507/giannis-antetokounmpo",
        # Add more URLs here as you discover them
    ]
    
    return build_cache_from_urls(known_urls)


def merge_with_existing_cache(new_cache: Dict[str, int]) -> Dict[str, int]:
    """Merge new cache with existing cache file if it exists"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                existing_data = json.load(f)
                existing_cache = existing_data.get('cache', {})
                
                # Merge (new entries override old)
                merged = {**existing_cache, **new_cache}
                logger.info(f"Merged with existing cache: {len(existing_cache)} + {len(new_cache)} = {len(merged)} entries")
                return merged
        except Exception as e:
            logger.warning(f"Error loading existing cache: {e}")
    
    return new_cache


def save_cache(cache: Dict[str, int]):
    """Save player cache to file"""
    if not cache:
        logger.warning("Cache is empty, not saving")
        return
    
    cache_data = {
        'timestamp': datetime.now().isoformat(),
        'cache': cache,
        'source': 'databallr.com',
        'total_players': len(cache)
    }
    
    try:
        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[OK] Saved {len(cache)} player IDs to {CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise




def main():
    import sys
    sys.stdout.flush()
    
    print("\nThis script extracts player IDs from databallr.com URLs")
    print("and saves them to a cache file for fast lookups.\n")
    sys.stdout.flush()
    
    # Check if PlayerIDs.txt exists
    player_ids_file = Path(__file__).parent / "PlayerIDs.txt"
    has_player_ids_file = player_ids_file.exists()
    
    print(f"Checking for PlayerIDs.txt: {player_ids_file}")
    print(f"File exists: {has_player_ids_file}")
    sys.stdout.flush()
    
    cache = {}
    
    if has_player_ids_file:
        print(f"[OK] Found PlayerIDs.txt with top-rated players")
        print(f"  Loading from: {player_ids_file}\n")
        sys.stdout.flush()
        
        try:
            urls = load_player_ids_file()
            print(f"  Loaded {len(urls)} URLs from file")
            sys.stdout.flush()
            
            if urls:
                print(f"  Processing {len(urls)} player URLs...")
                sys.stdout.flush()
                cache = build_cache_from_urls(urls)
                print(f"  Successfully processed {len(cache)} players")
                sys.stdout.flush()
            else:
                print("  [ERROR] No valid URLs found in PlayerIDs.txt")
                print("  Check that URLs are in format: https://databallr.com/last-games/ID/name")
                sys.stdout.flush()
        except Exception as e:
            print(f"  [ERROR] Failed to load PlayerIDs.txt: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
    else:
        print("Options:")
        print("  1. Load from PlayerIDs.txt (create this file with one URL per line)")
        print("  2. Add player URLs manually (paste URLs one by one)")
        print("  3. Load URLs from a custom text file")
        print("  4. Use built-in known players")
        
        choice = input("\nSelect option (1-4, default: 1): ").strip() or "1"
        
        if choice == "1":
            file_path = input("\nEnter path to PlayerIDs.txt file (or press Enter to skip): ").strip()
            if file_path:
                urls = load_player_ids_file(file_path)
                if urls:
                    cache = build_cache_from_urls(urls)
                else:
                    print("  [ERROR] No valid URLs found in file")
            else:
                print("  [ERROR] No file specified")
        
        elif choice == "2":
            print("\nEnter databallr player URLs (press Enter with empty line to finish):")
            print("Example: https://databallr.com/last-games/1626171/bobby-portis\n")
            
            urls = []
            while True:
                url = input("URL: ").strip()
                if not url:
                    break
                if 'databallr.com/last-games/' in url:
                    urls.append(url)
                    print(f"  [OK] Added URL")
                else:
                    print(f"  [ERROR] Invalid URL format (must contain 'databallr.com/last-games/')")
            
            if urls:
                cache = build_cache_from_urls(urls)
        
        elif choice == "3":
            file_path = input("\nEnter path to text file with URLs (one per line): ").strip()
            if file_path:
                urls = load_player_ids_file(file_path)
                if urls:
                    cache = build_cache_from_urls(urls)
                else:
                    print("  [ERROR] No valid URLs found in file")
        
        elif choice == "4":
            cache = build_cache_from_existing_urls()
    
    # Merge with existing cache if it exists
    if cache:
        cache = merge_with_existing_cache(cache)
    
    # Save cache
    import sys
    sys.stdout.flush()
    
    if cache:
        print(f"\nSaving cache with {len(cache)} player IDs...")
        sys.stdout.flush()
        try:
            save_cache(cache)
            print(f"\n[OK] Cache built successfully: {len(cache)} player IDs")
            print(f"\nCache file: {CACHE_FILE}")
            print("\nThe databallr scraper will now use this cache for fast player lookups!")
            sys.stdout.flush()
        except Exception as e:
            print(f"\n[ERROR] Failed to save cache: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
    else:
        print("\n[WARNING] No player IDs found. Cache not saved.")
        print("\nPossible reasons:")
        print("  - PlayerIDs.txt is empty or has invalid URLs")
        print("  - All URLs failed to parse")
        print("  - File encoding issue")
        sys.stdout.flush()
    
    print("\n" + "="*70)
    print("Script completed. Press Enter to close...")
    sys.stdout.flush()
    try:
        input()
    except:
        pass


if __name__ == "__main__":
    # Wrap everything in try-except to catch even import errors
    try:
        # Immediate output to verify script is running
        import sys
        sys.stdout.flush()
        
        print("="*70)
        print("  BUILD DATABALLR PLAYER ID CACHE")
        print("="*70)
        print()
        sys.stdout.flush()
        
        # Test imports first
        try:
            from playwright.sync_api import sync_playwright
            from bs4 import BeautifulSoup
            print("[OK] All imports successful")
            sys.stdout.flush()
        except ImportError as import_err:
            print(f"[ERROR] Missing required package: {import_err}")
            print("\nPlease install missing packages:")
            print("  pip install playwright beautifulsoup4")
            print("\nThen install playwright browsers:")
            print("  playwright install chromium")
            print("\nPress Enter to close...")
            sys.stdout.flush()
            input()
            sys.exit(1)
        
        # Run main (header already printed above)
        main()
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except SystemExit:
        pass  # Let system exits through
    except Exception as e:
        print("\n" + "="*70)
        print("  ERROR - Cache Builder Failed")
        print("="*70)
        print(f"\nError Type: {type(e).__name__}")
        print(f"Error Message: {e}\n")
        
        import traceback
        print("Full Traceback:")
        print("-"*70)
        traceback.print_exc()
        print("-"*70)
        
        # Save error to file
        error_log = Path(__file__).parent / "cache_builder_error_log.txt"
        try:
            with open(error_log, 'w', encoding='utf-8') as f:
                f.write(f"ERROR at {datetime.now()}\n")
                f.write(f"Error Type: {type(e).__name__}\n")
                f.write(f"Error Message: {str(e)}\n\n")
                f.write(traceback.format_exc())
            print(f"\nFull error saved to: {error_log}")
        except Exception as save_err:
            print(f"\nCould not save error log: {save_err}")
        
        print("\nPress Enter to close...")
        try:
            input()
        except:
            pass

