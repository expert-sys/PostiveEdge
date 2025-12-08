"""
DataballR Player Stats Scraper
===============================
Scrapes player game logs and statistics from databallr.com
"""

import logging
import re
import time
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from ..core.schema_map import SchemaMapper, get_databallr_schema_mapper
from ..core.backoff import RetryConfig, retry_request

logger = logging.getLogger(__name__)


class DataballrPlayerScraper:
    """
    Robust scraper for DataballR player statistics.
    Handles retries, schema changes, and data extraction.
    """
    
    def __init__(
        self,
        headless: bool = True,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize player scraper.
        
        Args:
            headless: Run browser in headless mode
            cache_dir: Directory for caching player IDs
        """
        self.headless = headless
        self.schema_mapper = get_databallr_schema_mapper()
        self.cache_dir = cache_dir or Path(__file__).parent.parent.parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.player_cache_file = self.cache_dir / "databallr_player_cache.json"
        self._player_cache: Dict[str, int] = {}
        self._load_player_cache()
        
        # Retry config for Playwright operations
        self.retry_config = RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0)
    
    def _load_player_cache(self):
        """Load player ID cache from file"""
        if self.player_cache_file.exists():
            try:
                import json
                with open(self.player_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._player_cache = data.get('cache', {})
                logger.info(f"Loaded {len(self._player_cache)} players from cache")
            except Exception as e:
                logger.warning(f"Failed to load player cache: {e}")
                self._player_cache = {}
    
    def _save_player_cache(self):
        """Save player ID cache to file"""
        try:
            import json
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'cache': self._player_cache
            }
            with open(self.player_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save player cache: {e}")
    
    def _normalize_player_name(self, name: str) -> str:
        """Normalize player name for cache lookup"""
        return name.lower().strip().replace('.', '').replace('  ', ' ')
    
    def _get_player_id(self, player_name: str) -> Optional[int]:
        """Get player ID from cache with fuzzy matching"""
        normalized = self._normalize_player_name(player_name)
        
        # Try exact match first
        player_id = self._player_cache.get(normalized)
        if player_id:
            return player_id
        
        # Try fuzzy matching - check if any cache key contains the player's last name
        # This handles cases like "Josh Hart" vs "Joshua Hart" or similar variations
        name_parts = normalized.split()
        if len(name_parts) >= 2:
            last_name = name_parts[-1]
            # Look for keys that end with the last name
            for key, pid in self._player_cache.items():
                if key.endswith(last_name) or last_name in key:
                    # Additional check: first name should also match
                    first_name = name_parts[0]
                    if first_name in key or key.startswith(first_name):
                        logger.debug(f"Fuzzy matched '{player_name}' to cache key '{key}'")
                        return pid
        
        logger.debug(f"Player '{player_name}' (normalized: '{normalized}') not found in cache")
        return None
    
    def _launch_browser(self) -> tuple:
        """Launch Playwright browser with anti-detection"""
        p = sync_playwright().start()
        browser = p.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US'
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
        """)
        return p, browser, context
    
    def _player_name_to_slug(self, name: str) -> str:
        """Convert player name to URL slug"""
        return name.lower().replace('.', '').replace(' ', '-').replace("'", '')
    
    def _navigate_to_player_page(self, page: Page, player_id: int, player_slug: str) -> bool:
        """Navigate to player's DataballR page"""
        url = f"https://databallr.com/last-games/{player_id}/{player_slug}"
        try:
            logger.debug(f"Navigating to: {url}")
            page.goto(url, timeout=30000, wait_until='domcontentloaded')
            time.sleep(2)  # Wait for page to settle
            
            # Wait for page to be interactive
            try:
                page.wait_for_load_state('networkidle', timeout=10000)
            except:
                pass  # Continue even if networkidle times out
            
            # Verify we're on player page
            current_url = page.url
            logger.debug(f"Current URL: {current_url}")
            
            if "/last-games/" in current_url:
                # Check if page loaded correctly (look for player name or table)
                page_text = page.content()
                if 'table' in page_text.lower() or 'game' in page_text.lower():
                    return True
                else:
                    logger.warning(f"Page loaded but no game data found in content")
                    return False
            else:
                logger.warning(f"Navigation failed - redirected to: {current_url}")
                return False
        except Exception as e:
            logger.debug(f"Navigation failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def _extract_game_log_table(self, page: Page, last_n_games: int = 20) -> List[Dict]:
        """
        Extract game log from table view.
        
        Args:
            page: Playwright page object
            last_n_games: Number of games to extract
        
        Returns:
            List of game dicts
        """
        try:
            # Wait for page to fully load
            page.wait_for_load_state('networkidle', timeout=10000)
            time.sleep(2)  # Extra wait for dynamic content
            
            # Try to click Table View button if available
            try:
                table_view_btn = page.locator("button:has-text('Table View')")
                if table_view_btn.is_visible(timeout=3000):
                    logger.debug("Clicking Table View button...")
                    table_view_btn.click()
                    time.sleep(2)  # Wait for table to load
            except:
                pass  # Table view might already be active
            
            # Wait for table to appear
            try:
                page.wait_for_selector('table', timeout=5000)
            except:
                logger.warning("Table not found after waiting")
            
            # Scroll to ensure table is in view
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
            # Get page HTML
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            games = []
            tables = soup.find_all('table')
            
            logger.debug(f"Found {len(tables)} tables on page")
            
            if not tables:
                # Try alternative: look for game data in other structures
                logger.debug("No tables found, trying alternative extraction...")
                # Look for divs with game data
                game_rows = soup.find_all(['div', 'tr'], class_=re.compile(r'game|row|match', re.I))
                logger.debug(f"Found {len(game_rows)} potential game rows")
            
            for table in tables:
                rows = table.find_all('tr')
                logger.debug(f"Table has {len(rows)} rows")
                
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 4:
                        continue
                    
                    game = self._parse_table_row(cells)
                    if game:
                        games.append(game)
            
            logger.debug(f"Extracted {len(games)} games from table(s)")
            
            if not games:
                # Try extracting from page text/JSON if table extraction failed
                logger.debug("No games from table, trying JSON extraction...")
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and ('game' in script.string.lower() or 'match' in script.string.lower()):
                        # Could parse JSON here if needed
                        pass
            
            return games[:last_n_games]
        except Exception as e:
            logger.error(f"Failed to extract game log: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _parse_table_row(self, cells) -> Optional[Dict]:
        """Parse table row into game dict with schema mapping"""
        try:
            if len(cells) < 4:
                return None
            
            raw_game = {}
            
            # Extract text from all cells
            for i, cell in enumerate(cells):
                text = cell.get_text(strip=True)
                if not text or text == '-':
                    continue
                
                # Map based on position (DataballR table structure)
                # This is flexible - will adapt to structure changes
                if i == 0:
                    raw_game['date'] = text
                else:
                    # Try to parse as number
                    val = self._parse_float(text)
                    if val is not None:
                        raw_game[f'col_{i}'] = val
            
            # Map to expected schema
            expected_schema = {
                'date': '',
                'points': 0,
                'rebounds': 0,
                'assists': 0,
                'steals': 0,
                'blocks': 0,
                'turnovers': 0,
                'minutes': 0.0,
                'three_pt_made': 0,
                'fg_made': 0,
                'fg_attempted': 0,
                'plus_minus': 0
            }
            
            # Try to map known positions (fallback if schema mapping fails)
            if len(cells) >= 17:
                # Typical DataballR structure
                raw_game['points'] = self._parse_int(cells[3].get_text(strip=True)) if len(cells) > 3 else 0
                raw_game['assists'] = self._parse_int(cells[4].get_text(strip=True)) if len(cells) > 4 else 0
                raw_game['rebounds'] = self._parse_int(cells[6].get_text(strip=True)) if len(cells) > 6 else 0
                raw_game['turnovers'] = self._parse_int(cells[7].get_text(strip=True)) if len(cells) > 7 else 0
                raw_game['steals'] = self._parse_int(cells[13].get_text(strip=True)) if len(cells) > 13 else 0
                raw_game['blocks'] = self._parse_int(cells[14].get_text(strip=True)) if len(cells) > 14 else 0
                raw_game['minutes'] = self._parse_float(cells[15].get_text(strip=True)) if len(cells) > 15 else 0.0
                raw_game['plus_minus'] = self._parse_int(cells[16].get_text(strip=True)) if len(cells) > 16 else 0
            
            # Use schema mapper to ensure all fields exist
            game = self.schema_mapper.map_dict(raw_game, expected_schema)
            
            # Validate minimum required fields
            if game.get('date') and game.get('points') is not None:
                return game
            
            return None
        except Exception as e:
            logger.debug(f"Failed to parse row: {e}")
            return None
    
    def _parse_float(self, text: str) -> Optional[float]:
        """Parse float from text"""
        try:
            cleaned = re.sub(r'[^\d.-]', '', text.strip())
            if cleaned:
                return float(cleaned)
        except:
            pass
        return None
    
    def _parse_int(self, text: str) -> int:
        """Parse int from text"""
        try:
            cleaned = re.sub(r'[^\d-]', '', text.strip())
            if cleaned:
                return int(cleaned)
        except:
            pass
        return 0
    
    def get_player_game_log(
        self,
        player_name: str,
        last_n_games: int = 20,
        retries: int = 3
    ) -> List[Dict]:
        """
        Get player game log from DataballR.
        
        Args:
            player_name: Player name
            last_n_games: Number of recent games to fetch
            retries: Number of retry attempts
        
        Returns:
            List of game dicts
        """
        logger.info(f"[DataballR] Fetching {last_n_games} games for {player_name}")
        
        # Check cache first
        player_id = self._get_player_id(player_name)
        if not player_id:
            logger.warning(f"[DataballR] Player {player_name} not in cache (cache has {len(self._player_cache)} players)")
            # Log some sample cache keys for debugging
            if self._player_cache:
                sample_keys = list(self._player_cache.keys())[:5]
                logger.debug(f"Sample cache keys: {sample_keys}")
            return []
        
        logger.debug(f"[DataballR] Found player ID {player_id} for {player_name}")
        player_slug = self._player_name_to_slug(player_name)
        
        # Retry logic
        for attempt in range(retries):
            try:
                p, browser, context = self._launch_browser()
                page = context.new_page()
                
                # Navigate to player page
                if not self._navigate_to_player_page(page, player_id, player_slug):
                    logger.warning(f"[DataballR] Failed to load page for {player_name} (attempt {attempt + 1}/{retries})")
                    browser.close()
                    p.stop()
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                    continue
                
                # Extract game log
                logger.debug(f"[DataballR] Extracting game log for {player_name}...")
                games = self._extract_game_log_table(page, last_n_games)
                logger.debug(f"[DataballR] Extracted {len(games)} games for {player_name}")
                
                # Add player_name to each game
                for game in games:
                    game['player_name'] = player_name
                
                browser.close()
                p.stop()
                
                if games:
                    logger.info(f"✓ [DataballR] Retrieved {len(games)} games for {player_name}")
                    return games
                else:
                    logger.warning(f"[DataballR] No games found for {player_name}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                    continue
                    
            except Exception as e:
                logger.error(f"[DataballR] Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        
        logger.error(f"[DataballR] All attempts failed for {player_name}")
        return []

