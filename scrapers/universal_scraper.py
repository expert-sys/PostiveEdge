"""
Universal Sports Data Scraper with Link Management
--------------------------------------------------
Features:
- Save and manage scraping targets
- Interactive CLI menu
- Site-specific templates
- Dynamic JS rendering (Playwright)
- Clean HTML parsing (BeautifulSoup)
- Resilient error handling + retries
- Configurable selectors per site
- Export to CSV/JSON
"""

import asyncio
import logging
import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd
import re
from tenacity import retry, wait_random, stop_after_attempt

# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s"
)
logger = logging.getLogger("universal_scraper")

# ---------------------------------------------------------------------
# Site Templates (Pre-configured selectors for popular sites)
# ---------------------------------------------------------------------
SITE_TEMPLATES = {
    # ===== FLASHSCORE / SOFASCORE =====
    "flashscore": {
        "name": "FlashScore (Live Scores & Stats)",
        "selectors": {
            "game_container": ".event__match, .sportName",
            "team_name": ".event__participant",
            "score": ".event__score",
            "time": ".event__time",
            "status": ".event__stage"
        },
        "extraction_type": "games",
        "difficulty": "medium",
        "reliability": "high"
    },
    "sofascore": {
        "name": "SofaScore (Live Scores & Stats)",
        "selectors": {
            "game_container": "[class*='event'], [class*='match']",
            "team_name": "[class*='participant'], [class*='team']",
            "score": "[class*='score']",
            "odds": "[class*='odds']"
        },
        "extraction_type": "games",
        "difficulty": "medium",
        "reliability": "high"
    },

    # ===== ESPN SPORTS =====
    "espn_nfl": {
        "name": "ESPN NFL (Stats, Scores, Injuries)",
        "selectors": {
            "game_container": ".Scoreboard__Row, .Table__TR",
            "team_name": ".ScoreCell__TeamName, .Table__Team",
            "score": ".ScoreCell__Score",
            "stats": ".Boxscore__Team, .Table__TD"
        },
        "extraction_type": "games",
        "wait_strategy": "auto",
        "difficulty": "low",
        "reliability": "very_high"
    },
    "espn_nba": {
        "name": "ESPN NBA (Stats, Scores, Injuries)",
        "selectors": {
            "game_container": ".Scoreboard__Row, .Table__TR",
            "team_name": ".ScoreCell__TeamName, .Table__Team",
            "score": ".ScoreCell__Score",
            "stats": ".Boxscore__Team, .PlayerStats"
        },
        "extraction_type": "games",
        "wait_strategy": "auto",
        "difficulty": "low",
        "reliability": "very_high"
    },
    "espn_mlb": {
        "name": "ESPN MLB (Stats, Scores, Schedule)",
        "selectors": {
            "game_container": ".Scoreboard__Row, .Table__TR",
            "team_name": ".ScoreCell__TeamName",
            "score": ".ScoreCell__Score",
            "pitcher": ".Baseball__Pitcher"
        },
        "extraction_type": "games",
        "wait_strategy": "auto",
        "difficulty": "low",
        "reliability": "very_high"
    },
    "espn_nhl": {
        "name": "ESPN NHL (Stats, Scores, Schedule)",
        "selectors": {
            "game_container": ".Scoreboard__Row, .Table__TR",
            "team_name": ".ScoreCell__TeamName",
            "score": ".ScoreCell__Score",
            "period": ".ScoreCell__Period"
        },
        "extraction_type": "games",
        "wait_strategy": "auto",
        "difficulty": "low",
        "reliability": "very_high"
    },
    "espn_odds": {
        "name": "ESPN Odds (General)",
        "selectors": {
            "game_container": ".Odds__Table, .OddsGrid__Game",
            "team_name": ".Odds__Team, .OddsGrid__Team",
            "spread": ".Odds__Spread",
            "moneyline": ".Odds__Moneyline",
            "total": ".Odds__Total"
        },
        "extraction_type": "games",
        "wait_strategy": "auto",
        "difficulty": "medium",
        "reliability": "very_high"
    },
    "espn_scores": {
        "name": "ESPN Scores (General)",
        "selectors": {
            "game_container": ".ScoreCell, .Scoreboard__Row",
            "team_name": ".ScoreCell__TeamName",
            "score": ".ScoreCell__Score"
        },
        "extraction_type": "games",
        "wait_strategy": "auto",
        "difficulty": "low",
        "reliability": "very_high"
    },

    # ===== BETTING SITES =====
    "draftkings": {
        "name": "DraftKings (Odds & Props)",
        "selectors": {
            "game_container": "[class*='event'], [class*='game']",
            "team_name": "[class*='team'], [class*='participant']",
            "spread": "[class*='spread']",
            "moneyline": "[class*='moneyline']",
            "total": "[class*='total'], [class*='over']",
            "prop": "[class*='prop']"
        },
        "extraction_type": "games",
        "difficulty": "low",
        "reliability": "very_high",
        "notes": "Check network tab for JSON endpoints"
    },
    "fanduel": {
        "name": "FanDuel (Odds & Props)",
        "selectors": {
            "game_container": "[class*='event'], [class*='market']",
            "team_name": "[class*='runner'], [class*='team']",
            "odds": "[class*='odds'], [class*='price']",
            "spread": "[class*='handicap']"
        },
        "extraction_type": "games",
        "difficulty": "low",
        "reliability": "very_high",
        "notes": "Structured and predictable"
    },
    "pointsbet": {
        "name": "PointsBet (Odds & Markets)",
        "selectors": {
            "game_container": "[class*='event'], [class*='fixture']",
            "team_name": "[class*='team'], [class*='competitor']",
            "odds": "[class*='odds'], [class*='price']"
        },
        "extraction_type": "games",
        "difficulty": "low",
        "reliability": "very_high"
    },
    "pinnacle": {
        "name": "Pinnacle (Sharp Odds)",
        "selectors": {
            "game_container": ".event-row, [class*='market']",
            "team_name": ".team-name, [class*='participant']",
            "spread": "[class*='spread']",
            "moneyline": "[class*='moneyline']",
            "total": "[class*='total']"
        },
        "extraction_type": "games",
        "difficulty": "low",
        "reliability": "very_high",
        "notes": "Known for sharp lines"
    },
    "betfair": {
        "name": "BetFair Exchange (Market Odds)",
        "selectors": {
            "game_container": ".event-row, [class*='market']",
            "team_name": ".runner-name, [class*='selection']",
            "back_odds": "[class*='back']",
            "lay_odds": "[class*='lay']",
            "liquidity": "[class*='depth'], [class*='volume']"
        },
        "extraction_type": "games",
        "difficulty": "low",
        "reliability": "very_high",
        "notes": "True market odds with liquidity data"
    },

    # ===== GENERIC TEMPLATES =====
    "generic_table": {
        "name": "Generic Table Scraper",
        "selectors": {
            "table": "table"
        },
        "extraction_type": "tables",
        "difficulty": "very_low",
        "reliability": "high"
    },
    "generic_json": {
        "name": "Generic JSON Scraper",
        "selectors": {},
        "extraction_type": "json",
        "difficulty": "very_low",
        "reliability": "high"
    },
    "custom": {
        "name": "Custom Selectors",
        "selectors": {},
        "extraction_type": "custom",
        "difficulty": "variable",
        "reliability": "variable"
    }
}

# ---------------------------------------------------------------------
# Link Manager (Save/Load Scraping Targets)
# ---------------------------------------------------------------------
class LinkManager:

    def __init__(self, storage_file: str = "scraper_links.json", auto_load_defaults: bool = True):
        self.storage_file = storage_file
        self.links = self.load_links()

        # Auto-load default links on first run
        if auto_load_defaults and len(self.links) == 0:
            logger.info("No saved links found. Loading default sports links...")
            count = self.load_default_links()
            if count > 0:
                logger.info(f"✓ Loaded {count} default sports links automatically!")

    def load_links(self) -> List[Dict]:
        """Load saved links from JSON file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading links: {e}")
                return []
        return []

    def save_links(self) -> bool:
        """Save links to JSON file"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.links, f, indent=2, ensure_ascii=False)
            logger.info(f"Links saved to {self.storage_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving links: {e}")
            return False

    def add_link(self, url: str, name: str, template: str = "custom",
                 selectors: Optional[Dict] = None, notes: str = "") -> bool:
        """Add a new scraping target"""
        link_data = {
            "id": len(self.links) + 1,
            "name": name,
            "url": url,
            "template": template,
            "selectors": selectors or SITE_TEMPLATES.get(template, {}).get("selectors", {}),
            "extraction_type": SITE_TEMPLATES.get(template, {}).get("extraction_type", "custom"),
            "wait_strategy": SITE_TEMPLATES.get(template, {}).get("wait_strategy", "auto"),
            "notes": notes,
            "created_at": datetime.now().isoformat(),
            "last_scraped": None,
            "scrape_count": 0
        }
        self.links.append(link_data)
        return self.save_links()

    def remove_link(self, link_id: int) -> bool:
        """Remove a scraping target by ID"""
        original_count = len(self.links)
        self.links = [link for link in self.links if link.get("id") != link_id]
        if len(self.links) < original_count:
            return self.save_links()
        return False

    def get_link(self, link_id: int) -> Optional[Dict]:
        """Get a specific link by ID"""
        for link in self.links:
            if link.get("id") == link_id:
                return link
        return None

    def list_links(self) -> List[Dict]:
        """Get all saved links"""
        return self.links

    def update_scrape_stats(self, link_id: int):
        """Update scrape statistics after successful scrape"""
        for link in self.links:
            if link.get("id") == link_id:
                link["last_scraped"] = datetime.now().isoformat()
                link["scrape_count"] = link.get("scrape_count", 0) + 1
                self.save_links()
                break

    def load_default_links(self, defaults_file: str = "default_scraper_links.json") -> int:
        """
        Load default links from configuration file

        Returns:
            Number of links added
        """
        if not os.path.exists(defaults_file):
            logger.warning(f"Default links file not found: {defaults_file}")
            return 0

        try:
            with open(defaults_file, 'r', encoding='utf-8') as f:
                default_links = json.load(f)

            added_count = 0
            for link_data in default_links:
                # Check if URL already exists
                url_exists = any(link.get("url") == link_data.get("url") for link in self.links)

                if not url_exists:
                    self.add_link(
                        url=link_data.get("url"),
                        name=link_data.get("name"),
                        template=link_data.get("template", "custom"),
                        notes=link_data.get("notes", "")
                    )
                    added_count += 1

            logger.info(f"Loaded {added_count} default links (skipped {len(default_links) - added_count} duplicates)")
            return added_count

        except Exception as e:
            logger.error(f"Error loading default links: {e}")
            return 0

    def clear_all_links(self) -> bool:
        """Clear all saved links"""
        self.links = []
        return self.save_links()

# ---------------------------------------------------------------------
# Universal Scraper Class
# ---------------------------------------------------------------------
class UniversalSportsScraper:

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.link_manager = LinkManager()

    # --------------------------
    # Fetch Page (Dynamic Load)
    # --------------------------
    @retry(wait=wait_random(min=2, max=5), stop=stop_after_attempt(3))
    async def fetch_page(self, url: str, wait_strategy: str = "auto") -> str:
        logger.info(f"Fetching URL: {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            # Set user agent to avoid bot detection
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            try:
                # Try with domcontentloaded first (faster, more reliable)
                if wait_strategy == "auto":
                    try:
                        await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
                        await page.wait_for_timeout(2000)   # Wait for JS to execute
                    except Exception:
                        # Fallback to load
                        await page.goto(url, timeout=self.timeout, wait_until="load")
                        await page.wait_for_timeout(1500)
                elif wait_strategy == "networkidle":
                    await page.goto(url, timeout=self.timeout, wait_until="networkidle")
                    await page.wait_for_timeout(1500)
                else:
                    await page.goto(url, timeout=self.timeout, wait_until=wait_strategy)
                    await page.wait_for_timeout(2000)

                html = await page.content()
                await browser.close()
                return html

            except Exception as e:
                logger.error(f"Page fetch failed: {e}")
                await browser.close()
                raise

    # --------------------------
    # Extract Game Data
    # --------------------------
    def extract_games(self, soup: BeautifulSoup, selectors: Dict) -> List[Dict]:
        logger.info("Parsing game data...")
        games = []

        containers = soup.select(selectors.get("game_container", "div"))
        if not containers:
            logger.warning("No game containers found — check selectors.")
            return games

        for game in containers:
            try:
                game_data = {}

                # Extract all selector fields
                for key, selector in selectors.items():
                    if key == "game_container":
                        continue

                    elements = game.select(selector)
                    if elements:
                        if "team" in key.lower():
                            game_data[key] = [el.get_text(" ", strip=True) for el in elements]
                        else:
                            game_data[key] = elements[0].get_text(" ", strip=True)
                    else:
                        game_data[key] = None

                games.append(game_data)

            except Exception as e:
                logger.error(f"Error parsing game block: {e}")
                continue

        return games

    # --------------------------
    # Extract Embedded JSON
    # --------------------------
    def extract_json(self, soup: BeautifulSoup) -> List[dict]:
        logger.info("Extracting JSON data...")
        json_blobs = []

        for script in soup.find_all("script"):
            try:
                txt = script.string
                if txt and "{" in txt:
                    # Try to find JSON-LD or other structured data
                    if "application/ld+json" in str(script.get("type", "")):
                        json_blobs.append(json.loads(txt))
                    # Try to extract JSON objects from inline scripts
                    elif "window." in txt or "var " in txt:
                        matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', txt)
                        for match in matches:
                            try:
                                json_blobs.append(json.loads(match))
                            except:
                                continue
            except:
                continue

        logger.info(f"Found {len(json_blobs)} JSON objects")
        return json_blobs

    # --------------------------
    # Extract Tables
    # --------------------------
    def extract_tables(self, html: str) -> List[pd.DataFrame]:
        logger.info("Extracting tables...")
        try:
            tables = pd.read_html(html)
            logger.info(f"Found {len(tables)} tables")
            return tables
        except:
            logger.warning("No tables found")
            return []

    # --------------------------
    # Extract All Content
    # --------------------------
    def extract_all(self, soup: BeautifulSoup, html: str, selectors: Dict) -> Dict:
        """Extract all types of content"""
        return {
            "games": self.extract_games(soup, selectors),
            "json": self.extract_json(soup),
            "tables": self.extract_tables(html),
            "text": soup.get_text(" ", strip=True)[:1000]  # First 1000 chars
        }

    # --------------------------
    # Main Scrape Function
    # --------------------------
    async def scrape(self, url: str, selectors: Optional[Dict] = None,
                     extraction_type: str = "auto", export_path: Optional[str] = None,
                     wait_strategy: str = "auto") -> Dict:
        """
        Scrape a URL with specified selectors

        Args:
            url: URL to scrape
            selectors: CSS selectors for extraction
            extraction_type: Type of extraction (games, json, tables, auto)
            export_path: Optional path to export results
            wait_strategy: Page load wait strategy (auto, domcontentloaded, load, networkidle)
        """
        html = await self.fetch_page(url, wait_strategy=wait_strategy)
        soup = BeautifulSoup(html, "html.parser")

        # Use default selectors if none provided
        if selectors is None:
            selectors = SITE_TEMPLATES["custom"]["selectors"]

        # Extract based on type
        if extraction_type == "auto" or extraction_type == "custom":
            data = self.extract_all(soup, html, selectors)
        elif extraction_type == "games":
            data = {"games": self.extract_games(soup, selectors)}
        elif extraction_type == "json":
            data = {"json": self.extract_json(soup)}
        elif extraction_type == "tables":
            data = {"tables": self.extract_tables(html)}
        else:
            data = self.extract_all(soup, html, selectors)

        # Export if requested
        if export_path:
            self._export_data(data, export_path)

        return data

    # --------------------------
    # Export Data
    # --------------------------
    def _export_data(self, data: Dict, export_path: str):
        """Export scraped data to file"""
        ext = os.path.splitext(export_path)[1].lower()

        try:
            if ext == ".json":
                # Convert DataFrames to dicts for JSON serialization
                export_data = {}
                for key, value in data.items():
                    if key == "tables" and isinstance(value, list):
                        export_data[key] = [df.to_dict() for df in value if isinstance(df, pd.DataFrame)]
                    elif isinstance(value, pd.DataFrame):
                        export_data[key] = value.to_dict()
                    else:
                        export_data[key] = value

                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Exported JSON → {export_path}")

            elif ext == ".csv":
                # Export games or first table to CSV
                if "games" in data and data["games"]:
                    df = pd.DataFrame(data["games"])
                    df.to_csv(export_path, index=False)
                    logger.info(f"Exported CSV → {export_path}")
                elif "tables" in data and data["tables"]:
                    data["tables"][0].to_csv(export_path, index=False)
                    logger.info(f"Exported CSV → {export_path}")
                else:
                    logger.warning("No tabular data to export to CSV")
            else:
                logger.warning(f"Unsupported export format: {ext}")

        except Exception as e:
            logger.error(f"Export failed: {e}")

    # --------------------------
    # Scrape from Saved Link
    # --------------------------
    async def scrape_saved_link(self, link_id: int, export: bool = True) -> Optional[Dict]:
        """Scrape a saved link by ID"""
        link = self.link_manager.get_link(link_id)
        if not link:
            logger.error(f"Link ID {link_id} not found")
            return None

        logger.info(f"Scraping: {link['name']} ({link['url']})")

        export_path = None
        if export:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r'[^\w\-_]', '_', link['name'])
            export_path = f"scraped_{safe_name}_{timestamp}.json"

        data = await self.scrape(
            url=link['url'],
            selectors=link.get('selectors'),
            extraction_type=link.get('extraction_type', 'auto'),
            export_path=export_path,
            wait_strategy=link.get('wait_strategy', 'auto')
        )

        self.link_manager.update_scrape_stats(link_id)
        return data

    # --------------------------
    # Scrape All Saved Links
    # --------------------------
    async def scrape_all_saved_links(self, export: bool = True) -> Dict[int, Dict]:
        """Scrape all saved links"""
        results = {}
        links = self.link_manager.list_links()

        logger.info(f"Scraping {len(links)} saved links...")

        for link in links:
            try:
                data = await self.scrape_saved_link(link['id'], export)
                results[link['id']] = data
            except Exception as e:
                logger.error(f"Failed to scrape link {link['id']}: {e}")
                results[link['id']] = None

        return results


# ---------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------
class ScraperCLI:

    def __init__(self):
        self.scraper = UniversalSportsScraper(headless=True)
        self.link_manager = self.scraper.link_manager

    def show_menu(self):
        """Display main menu"""
        print("\n" + "="*60)
        print("  UNIVERSAL SPORTS DATA SCRAPER")
        print("="*60)
        print("\n[1] Add New Link")
        print("[2] List Saved Links")
        print("[3] Scrape a Saved Link")
        print("[4] Scrape All Saved Links")
        print("[5] Remove a Link")
        print("[6] Scrape Custom URL (One-time)")
        print("[7] View Site Templates")
        print("[8] Load Default Sports Links")
        print("[9] Clear All Links")
        print("[0] Exit")
        print("\n" + "="*60)

    def view_templates(self):
        """Display available site templates"""
        print("\n" + "="*60)
        print("  AVAILABLE SITE TEMPLATES")
        print("="*60)
        for key, template in SITE_TEMPLATES.items():
            print(f"\n[{key}] {template['name']}")
            print(f"  Extraction Type: {template['extraction_type']}")
            if template['selectors']:
                print(f"  Selectors: {len(template['selectors'])} defined")
        print("\n" + "="*60)

    def list_links(self):
        """Display all saved links"""
        links = self.link_manager.list_links()

        if not links:
            print("\nNo saved links yet. Add one using option [1].")
            return

        print("\n" + "="*60)
        print("  SAVED LINKS")
        print("="*60)

        for link in links:
            print(f"\n[ID: {link['id']}] {link['name']}")
            print(f"  URL: {link['url']}")
            print(f"  Template: {link['template']}")
            print(f"  Scraped: {link['scrape_count']} times")
            if link['last_scraped']:
                print(f"  Last Scraped: {link['last_scraped'][:19]}")
            if link['notes']:
                print(f"  Notes: {link['notes']}")

        print("\n" + "="*60)

    def add_link_interactive(self):
        """Interactive link addition"""
        print("\n" + "="*60)
        print("  ADD NEW SCRAPING TARGET")
        print("="*60)

        url = input("\nEnter URL: ").strip()
        if not url:
            print("URL cannot be empty!")
            return

        name = input("Enter a name for this link: ").strip() or f"Link_{len(self.link_manager.links) + 1}"

        # Show templates
        print("\nAvailable templates:")
        for i, (key, template) in enumerate(SITE_TEMPLATES.items(), 1):
            print(f"  [{i}] {template['name']} ({key})")

        template_choice = input("\nChoose template (number or key) [custom]: ").strip() or "custom"

        # Map number to key
        if template_choice.isdigit():
            template_keys = list(SITE_TEMPLATES.keys())
            idx = int(template_choice) - 1
            if 0 <= idx < len(template_keys):
                template_choice = template_keys[idx]

        if template_choice not in SITE_TEMPLATES:
            template_choice = "custom"

        notes = input("Notes (optional): ").strip()

        success = self.link_manager.add_link(
            url=url,
            name=name,
            template=template_choice,
            notes=notes
        )

        if success:
            print(f"\n✓ Link '{name}' added successfully!")
        else:
            print("\n✗ Failed to add link")

    def remove_link_interactive(self):
        """Interactive link removal"""
        self.list_links()

        if not self.link_manager.list_links():
            return

        try:
            link_id = int(input("\nEnter link ID to remove: ").strip())
            link = self.link_manager.get_link(link_id)

            if link:
                confirm = input(f"Remove '{link['name']}'? (y/n): ").strip().lower()
                if confirm == 'y':
                    if self.link_manager.remove_link(link_id):
                        print(f"\n✓ Link removed successfully!")
                    else:
                        print("\n✗ Failed to remove link")
            else:
                print(f"\n✗ Link ID {link_id} not found")
        except ValueError:
            print("\n✗ Invalid ID")

    async def scrape_link_interactive(self):
        """Interactive link scraping"""
        self.list_links()

        if not self.link_manager.list_links():
            return

        try:
            link_id = int(input("\nEnter link ID to scrape: ").strip())
            export = input("Export results? (y/n) [y]: ").strip().lower() != 'n'

            print("\nScraping...")
            data = await self.scraper.scrape_saved_link(link_id, export)

            if data:
                print("\n✓ Scraping completed!")
                print(f"\nResults summary:")
                for key, value in data.items():
                    if isinstance(value, list):
                        print(f"  - {key}: {len(value)} items")
                    elif isinstance(value, dict):
                        print(f"  - {key}: {len(value)} keys")
                    else:
                        print(f"  - {key}: {type(value).__name__}")
            else:
                print("\n✗ Scraping failed")

        except ValueError:
            print("\n✗ Invalid ID")
        except Exception as e:
            print(f"\n✗ Error: {e}")

    async def scrape_all_interactive(self):
        """Interactive batch scraping"""
        links = self.link_manager.list_links()

        if not links:
            print("\nNo saved links to scrape.")
            return

        print(f"\nFound {len(links)} saved links.")
        confirm = input("Scrape all? This may take a while (y/n): ").strip().lower()

        if confirm != 'y':
            return

        export = input("Export results? (y/n) [y]: ").strip().lower() != 'n'

        print("\nScraping all links...")
        results = await self.scraper.scrape_all_saved_links(export)

        print(f"\n✓ Batch scraping completed!")
        print(f"  Success: {sum(1 for v in results.values() if v)} / {len(results)}")

    async def scrape_custom_interactive(self):
        """Interactive one-time scraping"""
        print("\n" + "="*60)
        print("  SCRAPE CUSTOM URL (ONE-TIME)")
        print("="*60)

        url = input("\nEnter URL: ").strip()
        if not url:
            print("URL cannot be empty!")
            return

        export = input("Export results? (y/n) [y]: ").strip().lower() != 'n'
        export_path = None

        if export:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"scraped_custom_{timestamp}.json"

        print("\nScraping...")
        data = await self.scraper.scrape(url, export_path=export_path)

        print("\n✓ Scraping completed!")
        print(f"\nResults summary:")
        for key, value in data.items():
            if isinstance(value, list):
                print(f"  - {key}: {len(value)} items")
            elif isinstance(value, dict):
                print(f"  - {key}: {len(value)} keys")

    def load_defaults_interactive(self):
        """Interactive default links loading"""
        print("\n" + "="*60)
        print("  LOAD DEFAULT SPORTS LINKS")
        print("="*60)

        print("\nThis will load pre-configured links for popular sports sites:")
        print("  - FlashScore / SofaScore (live scores)")
        print("  - ESPN (NFL, NBA, MLB, NHL)")
        print("  - DraftKings, FanDuel, PointsBet")
        print("  - Pinnacle, BetFair Exchange")
        print("\nTotal: ~24 default links")

        if self.link_manager.list_links():
            print(f"\nYou currently have {len(self.link_manager.list_links())} saved links.")
            print("Duplicates will be skipped automatically.")

        confirm = input("\nLoad default links? (y/n): ").strip().lower()

        if confirm != 'y':
            print("\nCancelled.")
            return

        print("\nLoading defaults...")
        added_count = self.link_manager.load_default_links()

        if added_count > 0:
            print(f"\n✓ Successfully added {added_count} default links!")
            print("Use option [2] to view all saved links.")
        else:
            print("\n✗ No new links added (all defaults already exist)")

    def clear_links_interactive(self):
        """Interactive clear all links"""
        print("\n" + "="*60)
        print("  CLEAR ALL LINKS")
        print("="*60)

        links = self.link_manager.list_links()

        if not links:
            print("\nNo links to clear.")
            return

        print(f"\nYou have {len(links)} saved links.")
        print("⚠ WARNING: This will permanently delete all saved links!")

        confirm = input("\nAre you sure? Type 'DELETE' to confirm: ").strip()

        if confirm == "DELETE":
            if self.link_manager.clear_all_links():
                print("\n✓ All links cleared successfully!")
            else:
                print("\n✗ Failed to clear links")
        else:
            print("\nCancelled.")

    async def run(self):
        """Main CLI loop"""
        # Show welcome message on first iteration
        first_run = True

        while True:
            if first_run:
                first_run = False
                link_count = len(self.link_manager.list_links())
                if link_count > 0:
                    print(f"\n✓ Ready! {link_count} scraping targets loaded.")
                    print("Use option [2] to view all links, or [4] to scrape all.")

            self.show_menu()
            choice = input("\nChoose option: ").strip()

            if choice == "0":
                print("\nGoodbye!")
                break
            elif choice == "1":
                self.add_link_interactive()
            elif choice == "2":
                self.list_links()
            elif choice == "3":
                await self.scrape_link_interactive()
            elif choice == "4":
                await self.scrape_all_interactive()
            elif choice == "5":
                self.remove_link_interactive()
            elif choice == "6":
                await self.scrape_custom_interactive()
            elif choice == "7":
                self.view_templates()
            elif choice == "8":
                self.load_defaults_interactive()
            elif choice == "9":
                self.clear_links_interactive()
            else:
                print("\n✗ Invalid option")


# ---------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------
async def main():
    """Run the interactive CLI"""
    cli = ScraperCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
