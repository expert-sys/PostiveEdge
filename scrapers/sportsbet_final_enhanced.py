"""
Enhanced Sportsbet Scraper - WITH WORKING Historical Data Extraction
=====================================================================
Extracts:
- Betting markets (moneyline, handicap, totals, props)
- Match Insights (embedded JSON from Stats & Insights tab)
- Real historical data for value analysis

Usage:
  python sportsbet_final_enhanced.py
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("sportsbet_final_enhanced")


@dataclass
class BettingMarket:
    selection_text: str
    odds: float
    team: Optional[str] = None
    line: Optional[str] = None
    market_category: str = "unknown"


@dataclass
class MatchInsight:
    """Match insight from the Stats & Insights tab"""
    fact: str
    tags: List[str]
    market: Optional[str] = None
    result: Optional[str] = None
    odds: Optional[float] = None
    icon: Optional[str] = None


@dataclass
class TeamStats:
    """Team statistics from Stats & Insights"""
    team_name: str

    # Records
    avg_points_for: Optional[float] = None
    avg_points_against: Optional[float] = None
    avg_winning_margin: Optional[float] = None
    avg_losing_margin: Optional[float] = None
    avg_total_points: Optional[float] = None

    # Performance Records
    favorite_win_pct: Optional[float] = None  # Win % when favorite
    underdog_win_pct: Optional[float] = None  # Win % when underdog
    night_win_pct: Optional[float] = None     # Night game win %
    night_loss_pct: Optional[float] = None    # Night game loss %

    # Under Pressure Stats
    clutch_win_pct: Optional[float] = None      # Win % in games decided by 5 points or less
    reliability_pct: Optional[float] = None     # Win % after leading at halftime
    comeback_pct: Optional[float] = None        # Win % after trailing at halftime
    choke_pct: Optional[float] = None           # Loss % after leading at halftime

    def to_dict(self):
        return asdict(self)


@dataclass
class MatchStats:
    """Complete match statistics from Stats & Insights"""
    away_team_stats: TeamStats
    home_team_stats: TeamStats
    data_range: str = "Last 10 Matches"  # e.g., "Last 5 Matches", "Last 10 Matches", "Season 2025/26"

    def to_dict(self):
        return {
            'data_range': self.data_range,
            'away_team': self.away_team_stats.to_dict(),
            'home_team': self.home_team_stats.to_dict()
        }


@dataclass
class CompleteMatchData:
    """Complete match data including markets, insights, and stats"""
    away_team: str
    home_team: str
    url: str
    scraped_at: str
    all_markets: List[BettingMarket] = field(default_factory=list)
    match_insights: List[MatchInsight] = field(default_factory=list)
    match_stats: Optional[MatchStats] = None

    def get_moneyline(self):
        return [m for m in self.all_markets if m.market_category == 'moneyline']

    def get_handicap(self):
        return [m for m in self.all_markets if m.market_category == 'handicap']

    def get_totals(self):
        return [m for m in self.all_markets if m.market_category == 'total']

    def get_props(self):
        return [m for m in self.all_markets if m.market_category == 'prop']

    def to_dict(self):
        return {
            'away_team': self.away_team,
            'home_team': self.home_team,
            'url': self.url,
            'scraped_at': self.scraped_at,
            'markets': {
                'total': len(self.all_markets),
                'moneyline': [asdict(m) for m in self.get_moneyline()],
                'handicap': [asdict(m) for m in self.get_handicap()],
                'totals': [asdict(m) for m in self.get_totals()],
                'props': [asdict(m) for m in self.get_props()]
            },
            'match_insights': [asdict(i) for i in self.match_insights],
            'insights_count': len(self.match_insights),
            'match_stats': self.match_stats.to_dict() if self.match_stats else None
        }


def categorize_market(selection_text: str, away_team: str, home_team: str) -> str:
    """Categorize market type"""
    text_lower = selection_text.lower()

    if any(word in text_lower for word in ['over', 'under']):
        return 'total'

    away_last = away_team.split()[-1].lower()
    home_last = home_team.split()[-1].lower()

    if text_lower == away_team.lower() or text_lower == home_team.lower():
        return 'moneyline'

    if (away_last in text_lower or home_last in text_lower) and '(' not in selection_text:
        return 'moneyline'

    if re.search(r'\([+-]\d+\.?\d*\)', selection_text) and (away_last in text_lower or home_last in text_lower):
        return 'handicap'

    prop_keywords = ['points', 'rebounds', 'assists', 'threes', 'first', 'anytime', 'scorer', 'basket', 'player']
    if any(word in text_lower for word in prop_keywords):
        return 'prop'

    return 'unknown'


def extract_match_insights(html: str) -> List[MatchInsight]:
    """
    Extract match insights from embedded JSON in HTML.

    The insights are embedded as: "matchInsights":[{...}, {...}]
    Uses bracket matching to properly extract the complete JSON array.
    """
    insights = []

    try:
        # Find the start of matchInsights
        search_str = '"matchInsights":['
        start_pos = html.find(search_str)

        if start_pos == -1:
            logger.warning("Could not find matchInsights in HTML")
            return insights

        # Start after the opening bracket
        json_start = start_pos + len(search_str) - 1  # Position of '['

        # Use bracket matching to find the closing bracket
        bracket_count = 0
        in_string = False
        escape_next = False
        end_pos = json_start

        for i in range(json_start, len(html)):
            char = html[i]

            # Handle string escaping
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            # Handle strings (ignore brackets inside strings)
            if char == '"':
                in_string = not in_string
                continue

            if not in_string:
                if char == '[' or char == '{':
                    bracket_count += 1
                elif char == ']' or char == '}':
                    bracket_count -= 1

                    # Found the closing bracket
                    if bracket_count == 0:
                        end_pos = i + 1
                        break

        if bracket_count != 0:
            logger.warning("Could not find matching closing bracket for matchInsights")
            return insights

        # Extract the JSON string
        json_str = html[json_start:end_pos]

        # Parse the JSON
        insights_data = json.loads(json_str)

        logger.info(f"Found {len(insights_data)} match insights")

        for insight_obj in insights_data:
            fact = insight_obj.get('fact', '')
            tags = insight_obj.get('tags', [])

            # Extract target bet info
            target_bet = insight_obj.get('targetBet', {})
            market = target_bet.get('market')
            result = target_bet.get('result')
            odds = target_bet.get('price')
            icon = target_bet.get('icon')

            insight = MatchInsight(
                fact=fact,
                tags=tags,
                market=market,
                result=result,
                odds=odds,
                icon=icon
            )

            insights.append(insight)

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        logger.error(f"Attempted to parse: {json_str[:200]}...")
    except Exception as e:
        logger.error(f"Failed to extract match insights: {e}")
        import traceback
        traceback.print_exc()

    return insights


def extract_team_stats_from_page(page, away_team: str, home_team: str) -> Optional[MatchStats]:
    """
    Extract team statistics from the Stats & Insights tab.

    Returns:
        MatchStats object with both teams' statistics
    """
    try:
        logger.info("Extracting team statistics...")

        # Helper function to extract percentage from text like "60.0%"
        def extract_percentage(text: str) -> Optional[float]:
            match = re.search(r'(\d+\.?\d*)\s*%', text)
            if match:
                return float(match.group(1))
            return None

        # Helper function to extract number from text like "113.1"
        def extract_number(text: str) -> Optional[float]:
            match = re.search(r'(\d+\.?\d+)', text)
            if match:
                return float(match.group(1))
            return None

        # Initialize team stats
        away_stats = TeamStats(team_name=away_team)
        home_stats = TeamStats(team_name=home_team)

        # Get the page content
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Extract Records section (Average Points, Margins, Total)
        logger.info("Looking for Records section...")
        records_section = soup.find('h3', string=re.compile(r'Records', re.I))

        if records_section:
            logger.info("Found Records section")
            records_container = records_section.find_parent()

            # Look for rows with data
            # Typical structure: two columns with team stats
            stat_rows = records_container.find_all(['div', 'tr'], recursive=True, limit=20)

            for row in stat_rows:
                row_text = row.get_text(strip=True)

                # Average Points For
                if 'Average Points For' in row_text or 'Points For' in row_text:
                    numbers = re.findall(r'(\d+\.?\d+)', row_text)
                    if len(numbers) >= 2:
                        away_stats.avg_points_for = float(numbers[0])
                        home_stats.avg_points_for = float(numbers[-1])
                        logger.info(f"Avg Points For: {numbers[0]} (away) | {numbers[-1]} (home)")

                # Average Points Against
                elif 'Average Points Against' in row_text or 'Points Against' in row_text:
                    numbers = re.findall(r'(\d+\.?\d+)', row_text)
                    if len(numbers) >= 2:
                        away_stats.avg_points_against = float(numbers[0])
                        home_stats.avg_points_against = float(numbers[-1])
                        logger.info(f"Avg Points Against: {numbers[0]} (away) | {numbers[-1]} (home)")

                # Average Winning Margin
                elif 'Winning Margin' in row_text:
                    numbers = re.findall(r'(\d+\.?\d+)', row_text)
                    if len(numbers) >= 2:
                        away_stats.avg_winning_margin = float(numbers[0])
                        home_stats.avg_winning_margin = float(numbers[-1])
                        logger.info(f"Avg Winning Margin: {numbers[0]} (away) | {numbers[-1]} (home)")

                # Average Losing Margin
                elif 'Losing Margin' in row_text:
                    numbers = re.findall(r'(\d+\.?\d+)', row_text)
                    if len(numbers) >= 2:
                        away_stats.avg_losing_margin = float(numbers[0])
                        home_stats.avg_losing_margin = float(numbers[-1])
                        logger.info(f"Avg Losing Margin: {numbers[0]} (away) | {numbers[-1]} (home)")

                # Average Total Match Points
                elif 'Total Match Points' in row_text or 'Total Points' in row_text:
                    numbers = re.findall(r'(\d+\.?\d+)', row_text)
                    if len(numbers) >= 2:
                        away_stats.avg_total_points = float(numbers[0])
                        home_stats.avg_total_points = float(numbers[-1])
                        logger.info(f"Avg Total Points: {numbers[0]} (away) | {numbers[-1]} (home)")

        # Extract Favorite/Underdog Records
        logger.info("Looking for Favorite/Underdog records...")

        # Favorite Record
        favorite_elements = soup.find_all(string=re.compile(r'Favourite Record', re.I))
        for elem in favorite_elements:
            parent = elem.find_parent()
            if parent:
                text = parent.get_text(strip=True)
                percentages = re.findall(r'(\d+\.?\d+)\s*%', text)
                if len(percentages) >= 2:
                    away_stats.favorite_win_pct = float(percentages[0])
                    home_stats.favorite_win_pct = float(percentages[-1])
                    logger.info(f"Favorite Win %: {percentages[0]}% (away) | {percentages[-1]}% (home)")
                    break

        # Underdog Record
        underdog_elements = soup.find_all(string=re.compile(r'Underdog Record', re.I))
        for elem in underdog_elements:
            parent = elem.find_parent()
            if parent:
                text = parent.get_text(strip=True)
                percentages = re.findall(r'(\d+\.?\d+)\s*%', text)
                if len(percentages) >= 2:
                    away_stats.underdog_win_pct = float(percentages[0])
                    home_stats.underdog_win_pct = float(percentages[-1])
                    logger.info(f"Underdog Win %: {percentages[0]}% (away) | {percentages[-1]}% (home)")
                    break

        # Night Record
        night_elements = soup.find_all(string=re.compile(r'Night Record', re.I))
        for elem in night_elements:
            parent = elem.find_parent()
            if parent:
                text = parent.get_text(strip=True)
                # Look for Win/Loss percentages
                percentages = re.findall(r'(\d+\.?\d+)\s*%', text)
                if len(percentages) >= 4:  # Win% (away), Loss% (away), Win% (home), Loss% (home)
                    away_stats.night_win_pct = float(percentages[0])
                    away_stats.night_loss_pct = float(percentages[1])
                    home_stats.night_win_pct = float(percentages[2])
                    home_stats.night_loss_pct = float(percentages[3])
                    logger.info(f"Night Record - Away: {percentages[0]}% W / {percentages[1]}% L")
                    logger.info(f"Night Record - Home: {percentages[2]}% W / {percentages[3]}% L")
                    break

        # Extract Under Pressure Stats
        logger.info("Looking for Under Pressure stats...")

        # Clutch Win
        clutch_elements = soup.find_all(string=re.compile(r'Clutch Win', re.I))
        for elem in clutch_elements:
            parent = elem.find_parent()
            if parent:
                text = parent.get_text(strip=True)
                percentages = re.findall(r'(\d+\.?\d+)\s*%', text)
                if len(percentages) >= 2:
                    away_stats.clutch_win_pct = float(percentages[0])
                    home_stats.clutch_win_pct = float(percentages[-1])
                    logger.info(f"Clutch Win %: {percentages[0]}% (away) | {percentages[-1]}% (home)")
                    break

        # Reliability (win after leading at halftime)
        reliability_elements = soup.find_all(string=re.compile(r'Reliability', re.I))
        for elem in reliability_elements:
            parent = elem.find_parent()
            if parent:
                text = parent.get_text(strip=True)
                percentages = re.findall(r'(\d+\.?\d+)\s*%', text)
                if len(percentages) >= 2:
                    away_stats.reliability_pct = float(percentages[0])
                    home_stats.reliability_pct = float(percentages[-1])
                    logger.info(f"Reliability %: {percentages[0]}% (away) | {percentages[-1]}% (home)")
                    break

        # Comeback (win after trailing at halftime)
        comeback_elements = soup.find_all(string=re.compile(r'Comeback', re.I))
        for elem in comeback_elements:
            parent = elem.find_parent()
            if parent:
                text = parent.get_text(strip=True)
                percentages = re.findall(r'(\d+\.?\d+)\s*%', text)
                if len(percentages) >= 2:
                    away_stats.comeback_pct = float(percentages[0])
                    home_stats.comeback_pct = float(percentages[-1])
                    logger.info(f"Comeback %: {percentages[0]}% (away) | {percentages[-1]}% (home)")
                    break

        # Choke (lose after leading at halftime)
        choke_elements = soup.find_all(string=re.compile(r'Choke', re.I))
        for elem in choke_elements:
            parent = elem.find_parent()
            if parent:
                text = parent.get_text(strip=True)
                percentages = re.findall(r'(\d+\.?\d+)\s*%', text)
                if len(percentages) >= 2:
                    away_stats.choke_pct = float(percentages[0])
                    home_stats.choke_pct = float(percentages[-1])
                    logger.info(f"Choke %: {percentages[0]}% (away) | {percentages[-1]}% (home)")
                    break

        # Determine data range (Last 5, Last 10, Season, etc.)
        data_range = "Last 10 Matches"  # Default
        dropdown_elem = soup.find(string=re.compile(r'Last \d+ Matches|Season', re.I))
        if dropdown_elem:
            data_range = dropdown_elem.strip()
            logger.info(f"Data range: {data_range}")

        match_stats = MatchStats(
            away_team_stats=away_stats,
            home_team_stats=home_stats,
            data_range=data_range
        )

        logger.info("Successfully extracted team statistics")
        return match_stats

    except Exception as e:
        logger.error(f"Failed to extract team stats: {e}")
        import traceback
        traceback.print_exc()
        return None


def scrape_match_complete(url: str, headless: bool = True) -> Optional[CompleteMatchData]:
    """
    Scrape complete match data including:
    - Betting markets
    - Match insights from Stats & Insights tab
    """

    logger.info(f"Scraping complete match data: {url}")

    with sync_playwright() as p:
        # Launch with more realistic browser args
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security'
            ]
        )

        # More realistic browser context
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-AU',
            timezone_id='Australia/Sydney',
            extra_http_headers={
                'Accept-Language': 'en-AU,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )

        page = context.new_page()

        # Add stealth scripts to avoid detection
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-AU', 'en-US', 'en']
            });

            window.chrome = {
                runtime: {}
            };
        """)

        try:
            page.goto(url, wait_until="load", timeout=60000)
            page.wait_for_selector('[data-automation-id*="outcome-text"]', timeout=10000)

            # Scroll to load all content
            logger.info("Scrolling to load content...")
            for i in range(10):
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(0.3)

            # Click Stats & Insights tab to load insights data
            logger.info("Looking for Stats & Insights tab...")
            stats_clicked = False
            try:
                stats_tab = page.locator('text=/Stats.*Insights/i').first
                if stats_tab.is_visible(timeout=2000):
                    logger.info("Clicking Stats & Insights tab...")
                    stats_tab.click()
                    time.sleep(2)  # Wait for content to load
                    stats_clicked = True

                    # Click on "Stats" sub-tab to ensure we're on the right view
                    try:
                        stats_subtab = page.locator('text="Stats"').first
                        if stats_subtab.is_visible(timeout=1000):
                            logger.info("Clicking Stats sub-tab...")
                            stats_subtab.click()
                            time.sleep(2)
                    except:
                        logger.info("No Stats sub-tab found or not needed")
            except:
                logger.warning("Could not click Stats & Insights tab")

            # Get team names from title
            title = page.title()
            teams = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)', title)
            away_team = teams[0] if len(teams) > 0 else "Unknown"
            home_team = teams[1] if len(teams) > 1 else "Unknown"

            logger.info(f"Match: {away_team} @ {home_team}")

            # Get HTML
            html = page.content()

            # Extract betting markets
            logger.info("Extracting betting markets...")
            soup = BeautifulSoup(html, 'html.parser')
            odds_elements = soup.find_all('span', {'data-automation-id': re.compile(r'outcome-text')})

            markets = []
            seen = set()

            for odds_elem in odds_elements:
                try:
                    odds_value = float(odds_elem.get_text(strip=True))
                except:
                    continue

                parent = odds_elem.parent
                for _ in range(4):
                    if parent:
                        parent = parent.parent

                if not parent:
                    continue

                full_text = parent.get_text(strip=True)
                selection_text = full_text.replace(str(odds_value), '').strip()

                market_key = f"{selection_text}_{odds_value}"
                if market_key in seen:
                    continue
                seen.add(market_key)

                category = categorize_market(selection_text, away_team, home_team)

                line = None
                line_match = re.search(r'[+-]?\d+\.?\d*', selection_text)
                if line_match and category in ['handicap', 'total']:
                    line = line_match.group()

                team = None
                if away_team.split()[-1] in selection_text:
                    team = away_team
                elif home_team.split()[-1] in selection_text:
                    team = home_team

                market = BettingMarket(
                    selection_text=selection_text,
                    odds=odds_value,
                    team=team,
                    line=line,
                    market_category=category
                )

                markets.append(market)

            logger.info(f"Extracted {len(markets)} betting markets")

            # Extract match insights from HTML
            logger.info("Extracting match insights...")
            insights = extract_match_insights(html)

            # Enhance insights with total lines for over/under markets
            for insight in insights:
                if insight.market and 'Total' in insight.market and insight.result in ['Over', 'Under']:
                    # Find matching total market to get the line
                    for market in markets:
                        if market.market_category == 'total' and market.odds == insight.odds:
                            if market.line:
                                # Add line to market name
                                line_value = market.line.replace('+', '')
                                insight.market = f"{insight.market} ({insight.result} {line_value})"
                                break

            # Extract team statistics (if Stats tab was clicked)
            match_stats = None
            if stats_clicked:
                match_stats = extract_team_stats_from_page(page, away_team, home_team)

            complete_data = CompleteMatchData(
                away_team=away_team,
                home_team=home_team,
                url=url,
                scraped_at=datetime.now().isoformat(),
                all_markets=markets,
                match_insights=insights,
                match_stats=match_stats
            )

            return complete_data

        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            browser.close()


def scrape_nba_overview(headless: bool = True) -> List[Dict]:
    """Scrape NBA overview to get all games"""

    url = "https://www.sportsbet.com.au/betting/basketball-us/nba"
    logger.info(f"Scraping NBA overview: {url}")

    with sync_playwright() as p:
        # Launch with more realistic browser args
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security'
            ]
        )

        # More realistic browser context
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-AU',
            timezone_id='Australia/Sydney',
            extra_http_headers={
                'Accept-Language': 'en-AU,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )

        page = context.new_page()

        # Add stealth scripts to avoid detection
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-AU', 'en-US', 'en']
            });

            window.chrome = {
                runtime: {}
            };
        """)

        try:
            # Changed from "networkidle" to "load" for better reliability
            logger.info("Attempting to load page (timeout: 60s)...")
            page.goto(url, wait_until="load", timeout=60000)
            logger.info("Page loaded, waiting for dynamic content...")
            
            # Wait longer for dynamic content to load
            time.sleep(5)
            
            # Try scrolling to trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(2)

            # Wait for game links to appear with multiple strategies
            selectors_to_try = [
                'a[href*="/betting/basketball-us/nba"]',
                'a[href*="/betting/basketball"]',
                '[data-testid*="game"]',
                '[class*="event"]',
                '[class*="match"]'
            ]
            
            found_selector = None
            for selector in selectors_to_try:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    logger.info(f"Found content using selector: {selector}")
                    found_selector = selector
                    break
                except:
                    continue
            
            if not found_selector:
                logger.warning("No content selectors found, continuing anyway...")

            # Take screenshot for debugging
            screenshot_file = Path(__file__).parent.parent / "debug" / "sportsbet_nba_page.png"
            screenshot_file.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_file), full_page=False)
            logger.info(f"Saved screenshot to {screenshot_file}")

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Debug: Save HTML to see what we're getting
            debug_file = Path(__file__).parent.parent / "debug" / "sportsbet_nba_page.html"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"Saved page HTML to {debug_file}")

            # Try multiple strategies to find game links
            links = []
            
            # Strategy 1: Direct NBA game links
            links = soup.find_all('a', href=re.compile(r'/betting/basketball-us/nba/.*-\d+$'))
            logger.info(f"Strategy 1: Found {len(links)} NBA game links with pattern '/betting/basketball-us/nba/.*-\\d+$'")
            
            # Strategy 2: Any basketball links ending with numbers
            if not links:
                links = soup.find_all('a', href=re.compile(r'/betting/basketball.*-\d+$'))
                logger.info(f"Strategy 2: Found {len(links)} basketball links ending with numbers")
            
            # Strategy 3: Links containing NBA and team names
            if not links:
                all_basketball_links = soup.find_all('a', href=re.compile(r'/betting/basketball'))
                logger.info(f"Strategy 3: Found {len(all_basketball_links)} total basketball links")
                
                # Filter for NBA-specific patterns
                for link in all_basketball_links:
                    href = link.get('href', '')
                    if '/nba/' in href and any(team in href.lower() for team in ['lakers', 'celtics', 'warriors', 'heat', 'knicks', 'bulls', 'mavericks']):
                        links.append(link)
                logger.info(f"Strategy 3: Filtered to {len(links)} NBA links with team names")
            
            # Strategy 4: Look for data attributes or other indicators
            if not links:
                # Try finding by data attributes
                game_elements = soup.find_all(attrs={'data-testid': re.compile(r'game|match|event', re.I)})
                for elem in game_elements:
                    link_elem = elem.find('a', href=re.compile(r'/betting'))
                    if link_elem:
                        links.append(link_elem)
                logger.info(f"Strategy 4: Found {len(links)} links via data attributes")
            
            # Debug: Show first few links found
            if links:
                logger.info("Sample links found:")
                for link in links[:5]:
                    href = link.get('href', 'NO HREF')
                    text = link.get_text(strip=True)[:50]
                    logger.info(f"  {href} - '{text}'")
            else:
                logger.warning("No game links found! Checking page structure...")
                # Try to find any links at all
                all_links = soup.find_all('a', href=True)
                logger.info(f"Total links on page: {len(all_links)}")
                if all_links:
                    logger.info("Sample links on page:")
                    for link in all_links[:10]:
                        href = link.get('href', '')
                        if '/betting' in href:
                            logger.info(f"  {href}")

            games = []
            seen_urls = set()

            for link in links[:30]:  # Increased limit
                href = link.get('href')
                if not href:
                    continue
                
                # Normalize href
                if href.startswith('/'):
                    href = f"https://www.sportsbet.com.au{href}"
                elif not href.startswith('http'):
                    continue
                
                if href in seen_urls:
                    continue

                seen_urls.add(href)
                
                # Try to extract team names from URL
                try:
                    url_parts = href.split('/')
                    last_part = url_parts[-1] if url_parts else ''
                    
                    # Remove trailing numbers
                    if '-' in last_part:
                        teams_str = last_part.rsplit('-', 1)[0]
                        teams = teams_str.replace('-', ' ').title().split(' At ')
                    else:
                        # Try to get from link text
                        link_text = link.get_text(strip=True)
                        if ' @ ' in link_text or ' vs ' in link_text.lower():
                            teams = re.split(r' @ | vs ', link_text, flags=re.I)
                        else:
                            teams = ['Unknown', 'Unknown']
                    
                    games.append({
                        'url': href,
                        'away_team': teams[0].strip() if len(teams) > 0 else 'Unknown',
                        'home_team': teams[1].strip() if len(teams) > 1 else 'Unknown',
                        'teams_str': ' @ '.join(teams) if len(teams) >= 2 else 'Unknown'
                    })
                except Exception as e:
                    logger.debug(f"Error parsing link {href}: {e}")
                    # Still add the game with URL
                    games.append({
                        'url': href,
                        'away_team': 'Unknown',
                        'home_team': 'Unknown',
                        'teams_str': 'Unknown'
                    })

            logger.info(f"Successfully extracted {len(games)} games")
            return games

        except Exception as e:
            logger.error(f"Error scraping NBA overview: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
        finally:
            try:
                browser.close()
            except:
                pass


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  ENHANCED SPORTSBET SCRAPER - WITH MATCH INSIGHTS")
    print("="*70)
    print("\nExtracts:")
    print("  - Betting markets (moneyline, handicap, totals, props)")
    print("  - Match insights & statistics from Stats & Insights tab")
    print("  - Real historical performance data")
    print()

    # Get games
    print("Getting NBA games...\n")
    games = scrape_nba_overview(headless=True)

    if games:
        print(f"Found {len(games)} games\n")
        print("Scraping first game with complete data...\n")

        first_game = games[0]
        print(f"Target: {first_game['away_team']} @ {first_game['home_team']}\n")

        complete_data = scrape_match_complete(first_game['url'], headless=True)

        if complete_data:
            print("\n" + "="*70)
            print("  EXTRACTION COMPLETE")
            print("="*70)

            print(f"\nMatch: {complete_data.away_team} @ {complete_data.home_team}")

            print(f"\nBetting Markets: {len(complete_data.all_markets)}")
            print(f"  - Moneyline: {len(complete_data.get_moneyline())}")
            print(f"  - Handicap: {len(complete_data.get_handicap())}")
            print(f"  - Totals: {len(complete_data.get_totals())}")
            print(f"  - Props: {len(complete_data.get_props())}")

            print(f"\nMatch Insights: {len(complete_data.match_insights)}")

            # Show match stats if available
            if complete_data.match_stats:
                print("\n" + "="*70)
                print("  MATCH STATISTICS")
                print("="*70)
                print(f"\nData Range: {complete_data.match_stats.data_range}")

                away_stats = complete_data.match_stats.away_team_stats
                home_stats = complete_data.match_stats.home_team_stats

                print(f"\n{away_stats.team_name} (Away) vs {home_stats.team_name} (Home)")
                print("-"*70)

                # Records
                print("\nRECORDS:")
                if away_stats.avg_points_for and home_stats.avg_points_for:
                    print(f"  Avg Points For:      {away_stats.avg_points_for:>6.1f} | {home_stats.avg_points_for:<6.1f}")
                if away_stats.avg_points_against and home_stats.avg_points_against:
                    print(f"  Avg Points Against:  {away_stats.avg_points_against:>6.1f} | {home_stats.avg_points_against:<6.1f}")
                if away_stats.avg_winning_margin and home_stats.avg_winning_margin:
                    print(f"  Avg Winning Margin:  {away_stats.avg_winning_margin:>6.1f} | {home_stats.avg_winning_margin:<6.1f}")
                if away_stats.avg_losing_margin and home_stats.avg_losing_margin:
                    print(f"  Avg Losing Margin:   {away_stats.avg_losing_margin:>6.1f} | {home_stats.avg_losing_margin:<6.1f}")
                if away_stats.avg_total_points and home_stats.avg_total_points:
                    print(f"  Avg Total Points:    {away_stats.avg_total_points:>6.1f} | {home_stats.avg_total_points:<6.1f}")

                # Performance
                print("\nPERFORMANCE RECORDS:")
                if away_stats.favorite_win_pct and home_stats.favorite_win_pct:
                    print(f"  Favorite Win %:      {away_stats.favorite_win_pct:>5.1f}% | {home_stats.favorite_win_pct:<5.1f}%")
                if away_stats.underdog_win_pct and home_stats.underdog_win_pct:
                    print(f"  Underdog Win %:      {away_stats.underdog_win_pct:>5.1f}% | {home_stats.underdog_win_pct:<5.1f}%")
                if away_stats.night_win_pct and home_stats.night_win_pct:
                    print(f"  Night Win %:         {away_stats.night_win_pct:>5.1f}% | {home_stats.night_win_pct:<5.1f}%")

                # Under Pressure
                print("\nUNDER PRESSURE:")
                if away_stats.clutch_win_pct and home_stats.clutch_win_pct:
                    print(f"  Clutch Win %:        {away_stats.clutch_win_pct:>5.1f}% | {home_stats.clutch_win_pct:<5.1f}%")
                if away_stats.reliability_pct and home_stats.reliability_pct:
                    print(f"  Reliability %:       {away_stats.reliability_pct:>5.1f}% | {home_stats.reliability_pct:<5.1f}%")
                if away_stats.comeback_pct and home_stats.comeback_pct:
                    print(f"  Comeback %:          {away_stats.comeback_pct:>5.1f}% | {home_stats.comeback_pct:<5.1f}%")
                if away_stats.choke_pct and home_stats.choke_pct:
                    print(f"  Choke %:             {away_stats.choke_pct:>5.1f}% | {home_stats.choke_pct:<5.1f}%")

            # Show sample insights
            if complete_data.match_insights:
                print("\n" + "="*70)
                print("  SAMPLE INSIGHTS")
                print("="*70)
                for insight in complete_data.match_insights[:5]:
                    print(f"\n  - {insight.fact}")
                    if insight.market and insight.result:
                        print(f"    Market: {insight.market} - {insight.result}")
                    if insight.odds:
                        print(f"    Odds: {insight.odds}")
                    if insight.tags:
                        print(f"    Tags: {', '.join(insight.tags[:3])}")

            # Save
            filename = f"complete_match_with_insights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(complete_data.to_dict(), f, indent=2, ensure_ascii=False)

            print(f"\nSaved to: {filename}\n")

            # Summary
            print("="*70)
            print("INSIGHT SUMMARY")
            print("="*70)

            # Categorize insights
            team_insights = [i for i in complete_data.match_insights if any(team in ' '.join(i.tags) for team in [complete_data.away_team, complete_data.home_team]) and 'Win/Loss' in i.tags]
            player_insights = [i for i in complete_data.match_insights if any(tag not in [complete_data.away_team, complete_data.home_team, 'Win/Loss', 'Over/Under'] for tag in i.tags)]

            print(f"\nTeam Performance Insights: {len(team_insights)}")
            for insight in team_insights[:3]:
                print(f"  - {insight.fact}")

            print(f"\nPlayer Performance Insights: {len(player_insights)}")
            for insight in player_insights[:3]:
                print(f"  - {insight.fact}")

            print("\n" + "="*70)
            print()

        else:
            print("\nFailed to scrape match\n")
