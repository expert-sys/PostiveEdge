"""
Sportsbet.com.au NBA Scraper
=============================
Extracts comprehensive betting odds and historical data from Sportsbet.

Features:
- Current match betting odds (moneyline, handicap, totals)
- Head-to-head historical data
- Team statistics and season results
- Match insights and trends
- Proper session management to avoid blocks

Anti-Detection Measures:
- Browser automation with Playwright
- Realistic headers and cookies
- Request throttling (1 req/sec)
- Session persistence
- Human-like behavior
"""

import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s"
)
logger = logging.getLogger("sportsbet_scraper")


# ---------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------
@dataclass
class MatchOdds:
    """Betting odds for a single match"""
    home_team: str
    away_team: str
    match_time: str

    # Match Betting (Moneyline)
    home_ml_odds: Optional[float] = None
    away_ml_odds: Optional[float] = None

    # Handicap Betting (Spread)
    home_handicap: Optional[str] = None
    home_handicap_odds: Optional[float] = None
    away_handicap: Optional[str] = None
    away_handicap_odds: Optional[float] = None

    # Total Points
    over_line: Optional[str] = None
    over_odds: Optional[float] = None
    under_line: Optional[str] = None
    under_odds: Optional[float] = None

    # Metadata
    num_markets: Optional[int] = None
    match_url: Optional[str] = None
    scraped_at: str = None

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()


@dataclass
class HeadToHeadGame:
    """Single head-to-head historical game"""
    date: str
    venue: str
    home_team: str
    away_team: str
    q1_home: Optional[int] = None
    q1_away: Optional[int] = None
    q2_home: Optional[int] = None
    q2_away: Optional[int] = None
    q3_home: Optional[int] = None
    q3_away: Optional[int] = None
    q4_home: Optional[int] = None
    q4_away: Optional[int] = None
    final_home: Optional[int] = None
    final_away: Optional[int] = None
    winner: Optional[str] = None


@dataclass
class SeasonResult:
    """Single season result for a team"""
    date: str
    opponent: str
    score: str
    result: str  # W or L
    home_away: Optional[str] = None


@dataclass
class TeamStats:
    """Team statistics"""
    team_name: str
    wins: int
    losses: int
    win_percentage: float
    position: int
    conference: str
    last_5_results: List[str] = None
    season_results: List[SeasonResult] = None


@dataclass
class MatchInsight:
    """Match insight/trend"""
    team: str
    insight: str
    value: Optional[str] = None


@dataclass
class ComprehensiveMatchData:
    """Complete data for a single match"""
    match_odds: MatchOdds
    head_to_head: List[HeadToHeadGame]
    team_stats: Dict[str, TeamStats]
    insights: List[MatchInsight]
    scraped_at: str = None

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()


# ---------------------------------------------------------------------
# Sportsbet Scraper
# ---------------------------------------------------------------------
class SportsbetScraper:
    """
    Scraper for sportsbet.com.au with anti-detection measures
    """

    def __init__(self, headless: bool = True, slow_mo: int = 100):
        """
        Initialize scraper

        Args:
            headless: Run browser in headless mode
            slow_mo: Slow down operations by N milliseconds (mimics human)
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.base_url = "https://www.sportsbet.com.au"
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Rate limiting
        self.request_delay = 1.0  # 1 second between requests
        self.last_request_time = 0

    def _throttle(self):
        """Implement request throttling"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            logger.debug(f"Throttling: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def start_browser(self):
        """Start browser with realistic fingerprint"""
        logger.info("Starting browser session...")

        self.playwright = sync_playwright().start()

        # Launch browser with realistic settings
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        # Create context with realistic viewport and user agent
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-AU',
            timezone_id='Australia/Sydney',
            geolocation={'latitude': -33.8688, 'longitude': 151.2093},  # Sydney
            permissions=['geolocation'],
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-AU,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            }
        )

        # Remove automation indicators
        self.context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-AU', 'en']
            });
        """)

        self.page = self.context.new_page()

        logger.info("Browser session started successfully")

    def close_browser(self):
        """Close browser and cleanup"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

        logger.info("Browser session closed")

    def navigate_to_url(self, url: str, wait_for: str = "networkidle") -> bool:
        """
        Navigate to URL with throttling

        Args:
            url: URL to navigate to
            wait_for: Wait strategy (networkidle, load, domcontentloaded)

        Returns:
            Success status
        """
        try:
            self._throttle()

            logger.info(f"Navigating to: {url}")

            # Try with longer timeout and fallback wait strategies
            try:
                self.page.goto(url, wait_until=wait_for, timeout=60000)
            except:
                # Fallback to 'load' if 'networkidle' fails
                logger.warning(f"Failed with {wait_for}, trying 'load'")
                self.page.goto(url, wait_until="load", timeout=60000)

            # Random human-like delay
            time.sleep(0.5 + (time.time() % 1))

            # Check if we got blocked or redirected
            current_url = self.page.url
            if "blocked" in current_url.lower() or "captcha" in current_url.lower():
                logger.error("Page blocked or CAPTCHA detected")
                return False

            return True

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False

    def scrape_nba_overview(self, url: str = None) -> List[MatchOdds]:
        """
        Scrape NBA overview page with all games and odds

        Args:
            url: NBA overview URL (default: /betting/basketball-us/nba)

        Returns:
            List of MatchOdds objects
        """
        if url is None:
            url = f"{self.base_url}/betting/basketball-us/nba"

        if not self.navigate_to_url(url):
            return []

        # Wait for odds to load
        try:
            self.page.wait_for_selector('[class*="price"]', timeout=10000)
        except:
            logger.warning("Odds elements not found, continuing anyway...")

        html = self.page.content()
        soup = BeautifulSoup(html, 'html.parser')

        matches = []

        # Find all match containers
        # Sportsbet typically uses data attributes or specific class patterns
        match_containers = soup.find_all(['div', 'article'], class_=re.compile(r'(market|event|match|game)', re.I))

        logger.info(f"Found {len(match_containers)} potential match containers")

        for container in match_containers:
            try:
                match_data = self._extract_match_odds_from_container(container)
                if match_data:
                    matches.append(match_data)
            except Exception as e:
                logger.debug(f"Failed to extract match data: {e}")
                continue

        logger.info(f"Successfully extracted {len(matches)} matches")
        return matches

    def _extract_match_odds_from_container(self, container) -> Optional[MatchOdds]:
        """Extract match odds from a container element"""

        # Try to find team names
        teams = container.find_all(['span', 'div'], class_=re.compile(r'(team|participant|competitor)', re.I))

        if len(teams) < 2:
            # Try alternative selectors
            teams = container.find_all(['a', 'span'], string=re.compile(r'[A-Z][a-z]+ [A-Z][a-z]+'))

        if len(teams) < 2:
            return None

        # Extract team names
        away_team = teams[0].get_text(strip=True)
        home_team = teams[1].get_text(strip=True) if len(teams) > 1 else "Unknown"

        # Find match time
        time_elem = container.find(['time', 'span'], class_=re.compile(r'(time|date|start)', re.I))
        match_time = time_elem.get_text(strip=True) if time_elem else "Unknown"

        # Find all price/odds elements
        prices = container.find_all(['span', 'div', 'button'], class_=re.compile(r'(price|odd|selection)', re.I))

        # Extract odds values
        odds_values = []
        for price in prices:
            text = price.get_text(strip=True)
            # Match decimal odds like "1.90", "2.75", etc.
            match = re.search(r'\d+\.\d+', text)
            if match:
                try:
                    odds_values.append(float(match.group()))
                except:
                    pass

        # Extract handicap values
        handicap_values = []
        for elem in container.find_all(['span', 'div'], string=re.compile(r'[+-]\d+\.?\d*')):
            text = elem.get_text(strip=True)
            match = re.search(r'([+-]\d+\.?\d*)', text)
            if match:
                handicap_values.append(match.group(1))

        # Try to find match URL
        match_link = container.find('a', href=re.compile(r'/betting/basketball-us/nba/'))
        match_url = match_link['href'] if match_link else None
        if match_url and not match_url.startswith('http'):
            match_url = f"{self.base_url}{match_url}"

        # Count markets
        markets_elem = container.find(string=re.compile(r'\d+ Markets?', re.I))
        num_markets = None
        if markets_elem:
            match = re.search(r'(\d+)', markets_elem)
            if match:
                num_markets = int(match.group(1))

        # Build MatchOdds object
        match_odds = MatchOdds(
            home_team=home_team,
            away_team=away_team,
            match_time=match_time,
            match_url=match_url,
            num_markets=num_markets
        )

        # Assign odds (this is heuristic-based, may need adjustment)
        if len(odds_values) >= 2:
            match_odds.away_ml_odds = odds_values[0]
            match_odds.home_ml_odds = odds_values[1]

        if len(odds_values) >= 4:
            match_odds.away_handicap_odds = odds_values[2]
            match_odds.home_handicap_odds = odds_values[3]

        if len(handicap_values) >= 2:
            match_odds.away_handicap = handicap_values[0]
            match_odds.home_handicap = handicap_values[1]

        if len(odds_values) >= 6:
            match_odds.over_odds = odds_values[4]
            match_odds.under_odds = odds_values[5]

        return match_odds

    def scrape_match_detail(self, match_url: str) -> Optional[ComprehensiveMatchData]:
        """
        Scrape detailed match page with odds, h2h, stats, insights

        Args:
            match_url: Full URL to match detail page

        Returns:
            ComprehensiveMatchData object
        """
        if not self.navigate_to_url(match_url):
            return None

        # Wait for page to fully load
        time.sleep(2)

        html = self.page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Extract match odds
        match_odds = self._extract_detailed_match_odds(soup)

        # Extract head-to-head data
        h2h_games = self._extract_head_to_head(soup)

        # Extract team stats
        team_stats = self._extract_team_stats(soup)

        # Extract insights
        insights = self._extract_match_insights(soup)

        return ComprehensiveMatchData(
            match_odds=match_odds,
            head_to_head=h2h_games,
            team_stats=team_stats,
            insights=insights
        )

    def _extract_detailed_match_odds(self, soup: BeautifulSoup) -> MatchOdds:
        """Extract detailed odds from match page"""

        # Find teams
        teams = []
        team_elements = soup.find_all(['h1', 'h2', 'span'], string=re.compile(r'(Pacers|Pistons|Lakers|Warriors)', re.I))

        for elem in team_elements[:2]:
            text = elem.get_text(strip=True)
            # Extract team name from strings like "Indiana Pacers @ Detroit Pistons"
            team_matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)', text)
            teams.extend(team_matches)

        # Remove duplicates while preserving order
        seen = set()
        unique_teams = []
        for team in teams:
            if team not in seen:
                seen.add(team)
                unique_teams.append(team)

        away_team = unique_teams[0] if len(unique_teams) > 0 else "Unknown"
        home_team = unique_teams[1] if len(unique_teams) > 1 else "Unknown"

        # Find match time
        time_elem = soup.find(['time', 'span'], class_=re.compile(r'(time|live)', re.I))
        match_time = time_elem.get_text(strip=True) if time_elem else "Live"

        match_odds = MatchOdds(
            home_team=home_team,
            away_team=away_team,
            match_time=match_time
        )

        # Find Match Betting section
        match_betting_section = soup.find(string=re.compile(r'Match Betting', re.I))
        if match_betting_section:
            parent = match_betting_section.find_parent(['div', 'section'])
            if parent:
                odds = parent.find_all(['span', 'div'], class_=re.compile(r'(price|odd)', re.I))
                odds_values = []
                for odd in odds:
                    text = odd.get_text(strip=True)
                    match = re.search(r'(\d+\.\d+)', text)
                    if match:
                        odds_values.append(float(match.group(1)))

                if len(odds_values) >= 2:
                    match_odds.away_ml_odds = odds_values[0]
                    match_odds.home_ml_odds = odds_values[1]

        # Find Handicap Betting section
        handicap_section = soup.find(string=re.compile(r'Handicap Betting', re.I))
        if handicap_section:
            parent = handicap_section.find_parent(['div', 'section'])
            if parent:
                # Find handicap lines
                handicaps = parent.find_all(string=re.compile(r'([+-]\d+\.?\d*)'))
                handicap_values = []
                for h in handicaps:
                    match = re.search(r'([+-]\d+\.?\d*)', h)
                    if match:
                        handicap_values.append(match.group(1))

                # Find odds
                odds = parent.find_all(['span', 'div'], class_=re.compile(r'(price|odd)', re.I))
                odds_values = []
                for odd in odds:
                    text = odd.get_text(strip=True)
                    match = re.search(r'(\d+\.\d+)', text)
                    if match:
                        odds_values.append(float(match.group(1)))

                if len(handicap_values) >= 2:
                    match_odds.away_handicap = handicap_values[0]
                    match_odds.home_handicap = handicap_values[1]

                if len(odds_values) >= 2:
                    match_odds.away_handicap_odds = odds_values[0]
                    match_odds.home_handicap_odds = odds_values[1]

        # Find Total Points section
        total_section = soup.find(string=re.compile(r'Total Points', re.I))
        if total_section:
            parent = total_section.find_parent(['div', 'section'])
            if parent:
                # Find over/under lines
                lines = parent.find_all(string=re.compile(r'(Over|Under)\s*\([+-]?\d+\.?\d*\)', re.I))

                for line_text in lines:
                    match = re.search(r'(Over|Under)\s*\(([+-]?\d+\.?\d*)\)', line_text, re.I)
                    if match:
                        line_type = match.group(1).lower()
                        line_value = match.group(2)

                        if line_type == 'over':
                            match_odds.over_line = line_value
                        else:
                            match_odds.under_line = line_value

                # Find odds
                odds = parent.find_all(['span', 'div'], class_=re.compile(r'(price|odd)', re.I))
                odds_values = []
                for odd in odds:
                    text = odd.get_text(strip=True)
                    match = re.search(r'(\d+\.\d+)', text)
                    if match:
                        odds_values.append(float(match.group(1)))

                if len(odds_values) >= 2:
                    match_odds.over_odds = odds_values[0]
                    match_odds.under_odds = odds_values[1]

        return match_odds

    def _extract_head_to_head(self, soup: BeautifulSoup) -> List[HeadToHeadGame]:
        """Extract head-to-head historical games"""
        h2h_games = []

        # Find H2H section
        h2h_section = soup.find(string=re.compile(r'(Last \d+ Head to Head|Head to Head)', re.I))

        if not h2h_section:
            logger.debug("No head-to-head section found")
            return h2h_games

        parent = h2h_section.find_parent(['div', 'section', 'article'])
        if not parent:
            return h2h_games

        # Find game containers
        game_containers = parent.find_all(['div', 'tr'], class_=re.compile(r'(game|match|row)', re.I))

        if not game_containers:
            # Try finding by table rows
            game_containers = parent.find_all('tr')

        for container in game_containers:
            try:
                game = self._parse_h2h_game(container)
                if game:
                    h2h_games.append(game)
            except Exception as e:
                logger.debug(f"Failed to parse H2H game: {e}")
                continue

        logger.info(f"Extracted {len(h2h_games)} head-to-head games")
        return h2h_games

    def _parse_h2h_game(self, container) -> Optional[HeadToHeadGame]:
        """Parse a single H2H game from container"""

        # Find date
        date_elem = container.find(string=re.compile(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}'))
        date = date_elem.strip() if date_elem else "Unknown"

        # Find venue
        venue_elem = container.find(string=re.compile(r'(Fieldhouse|Arena|Center)', re.I))
        venue = venue_elem.strip() if venue_elem else "Unknown"

        # Find teams
        team_elems = container.find_all(['span', 'div'], class_=re.compile(r'team', re.I))
        teams = [t.get_text(strip=True) for t in team_elems[:2]]

        if len(teams) < 2:
            # Try alternative
            teams = [t.strip() for t in container.stripped_strings if re.match(r'^[A-Z]{3}$', t)]

        if len(teams) < 2:
            return None

        # Find quarter scores
        scores = container.find_all(['td', 'span'], class_=re.compile(r'(score|quarter|q\d)', re.I))
        score_values = []

        for score in scores:
            text = score.get_text(strip=True)
            if text.isdigit():
                score_values.append(int(text))

        # Find final score and winner
        final_elem = container.find(['td', 'span'], class_=re.compile(r'(final|total|ft)', re.I))
        winner_elem = container.find(['div', 'span'], class_=re.compile(r'(winner|win|result)', re.I))

        game = HeadToHeadGame(
            date=date,
            venue=venue,
            home_team=teams[0] if teams else "Unknown",
            away_team=teams[1] if len(teams) > 1 else "Unknown"
        )

        # Assign quarter scores (heuristic)
        if len(score_values) >= 10:  # Q1-Q4 + Final for both teams
            game.q1_home = score_values[0]
            game.q2_home = score_values[1]
            game.q3_home = score_values[2]
            game.q4_home = score_values[3]
            game.final_home = score_values[4]

            game.q1_away = score_values[5]
            game.q2_away = score_values[6]
            game.q3_away = score_values[7]
            game.q4_away = score_values[8]
            game.final_away = score_values[9]

            # Determine winner
            if game.final_home > game.final_away:
                game.winner = game.home_team
            else:
                game.winner = game.away_team

        return game

    def _extract_team_stats(self, soup: BeautifulSoup) -> Dict[str, TeamStats]:
        """Extract team statistics and season results"""
        team_stats = {}

        # Find season results section
        season_section = soup.find(string=re.compile(r'Season Results', re.I))

        if not season_section:
            logger.debug("No season results section found")
            return team_stats

        parent = season_section.find_parent(['div', 'section'])
        if not parent:
            return team_stats

        # Find team containers
        team_containers = parent.find_all(['div', 'article'], class_=re.compile(r'team', re.I))

        for container in team_containers:
            try:
                stats = self._parse_team_stats(container)
                if stats:
                    team_stats[stats.team_name] = stats
            except Exception as e:
                logger.debug(f"Failed to parse team stats: {e}")
                continue

        return team_stats

    def _parse_team_stats(self, container) -> Optional[TeamStats]:
        """Parse team stats from container"""

        # Find team name
        team_elem = container.find(['h3', 'span'], class_=re.compile(r'team', re.I))
        team_name = team_elem.get_text(strip=True) if team_elem else "Unknown"

        # Find last 5 results
        last_5 = []
        result_elems = container.find_all(['span', 'div'], class_=re.compile(r'result|last', re.I))

        for elem in result_elems:
            text = elem.get_text(strip=True)
            if text in ['W', 'L']:
                last_5.append(text)

        # Find season results
        season_results = []
        result_rows = container.find_all(['tr', 'div'], class_=re.compile(r'(result|game|match)', re.I))

        for row in result_rows:
            try:
                # Find date
                date_elem = row.find(string=re.compile(r'\d{2}/\d{2}/\d{2}'))
                date = date_elem.strip() if date_elem else ""

                # Find opponent
                opp_elem = row.find(['span', 'div'], class_=re.compile(r'(opponent|team)', re.I))
                opponent = opp_elem.get_text(strip=True) if opp_elem else ""

                # Find score
                score_elem = row.find(string=re.compile(r'\d+-\d+'))
                score = score_elem.strip() if score_elem else ""

                # Find result
                result_elem = row.find(['span', 'div'], class_=re.compile(r'result', re.I))
                result_text = result_elem.get_text(strip=True) if result_elem else ""
                result = 'W' if 'w' in result_text.lower() else 'L'

                if date and opponent:
                    season_results.append(SeasonResult(
                        date=date,
                        opponent=opponent,
                        score=score,
                        result=result
                    ))
            except Exception as e:
                logger.debug(f"Failed to parse season result: {e}")
                continue

        # Calculate wins/losses
        wins = sum(1 for r in season_results if r.result == 'W')
        losses = len(season_results) - wins
        win_pct = wins / len(season_results) if season_results else 0.0

        return TeamStats(
            team_name=team_name,
            wins=wins,
            losses=losses,
            win_percentage=win_pct,
            position=0,  # Would need standings data
            conference="Unknown",
            last_5_results=last_5[:5],
            season_results=season_results
        )

    def _extract_match_insights(self, soup: BeautifulSoup) -> List[MatchInsight]:
        """Extract match insights and trends"""
        insights = []

        # Find insights section
        insights_section = soup.find(string=re.compile(r'(Tips|Insights|Match Insights)', re.I))

        if not insights_section:
            logger.debug("No insights section found")
            return insights

        parent = insights_section.find_parent(['div', 'section'])
        if not parent:
            return insights

        # Find insight containers
        insight_containers = parent.find_all(['div', 'li'], class_=re.compile(r'(insight|tip|stat)', re.I))

        for container in insight_containers:
            try:
                # Find team
                team_elem = container.find(['img', 'span'], attrs={'alt': True})
                team = team_elem.get('alt', 'Unknown') if team_elem else "Unknown"

                # Find insight text
                text_elem = container.find(['p', 'span'], class_=re.compile(r'(text|description)', re.I))
                text = text_elem.get_text(strip=True) if text_elem else container.get_text(strip=True)

                # Find value (if any, like odds)
                value_elem = container.find(['span', 'div'], class_=re.compile(r'(value|price|odd)', re.I))
                value = value_elem.get_text(strip=True) if value_elem else None

                if text:
                    insights.append(MatchInsight(
                        team=team,
                        insight=text,
                        value=value
                    ))
            except Exception as e:
                logger.debug(f"Failed to parse insight: {e}")
                continue

        logger.info(f"Extracted {len(insights)} match insights")
        return insights

    def save_to_json(self, data: Any, filename: str, output_dir: str = "."):
        """Save data to JSON file"""
        output_path = Path(output_dir) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert dataclasses to dicts
        if hasattr(data, '__iter__') and not isinstance(data, (str, dict)):
            data_dict = [asdict(item) if hasattr(item, '__dataclass_fields__') else item for item in data]
        elif hasattr(data, '__dataclass_fields__'):
            data_dict = asdict(data)
        else:
            data_dict = data

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Saved data to: {output_path}")
        return str(output_path)


# ---------------------------------------------------------------------
# High-Level Functions
# ---------------------------------------------------------------------
def scrape_nba_overview(headless: bool = True) -> List[MatchOdds]:
    """
    Scrape NBA overview page

    Args:
        headless: Run browser in headless mode

    Returns:
        List of MatchOdds
    """
    scraper = SportsbetScraper(headless=headless)

    try:
        scraper.start_browser()
        matches = scraper.scrape_nba_overview()

        # Save to JSON
        if matches:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            scraper.save_to_json(
                matches,
                f"sportsbet_nba_overview_{timestamp}.json"
            )

        return matches

    finally:
        scraper.close_browser()


def scrape_match_detail(match_url: str, headless: bool = True) -> Optional[ComprehensiveMatchData]:
    """
    Scrape detailed match page

    Args:
        match_url: Full URL to match page
        headless: Run browser in headless mode

    Returns:
        ComprehensiveMatchData
    """
    scraper = SportsbetScraper(headless=headless)

    try:
        scraper.start_browser()
        data = scraper.scrape_match_detail(match_url)

        # Save to JSON
        if data:
            # Extract match identifier from URL
            match_id = match_url.split('/')[-1].split('-')[-1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            scraper.save_to_json(
                data,
                f"sportsbet_match_{match_id}_{timestamp}.json"
            )

        return data

    finally:
        scraper.close_browser()


# ---------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    print("\n" + "="*70)
    print("  SPORTSBET.COM.AU NBA SCRAPER")
    print("="*70)
    print("\nOptions:")
    print("  1. Scrape NBA Overview (all games)")
    print("  2. Scrape Specific Match (with H2H and stats)")
    print("  3. Exit")

    choice = input("\nSelect option (1-3): ").strip()

    if choice == '1':
        print("\nScraping NBA overview...")
        matches = scrape_nba_overview(headless=False)
        print(f"\nScraped {len(matches)} matches")

        for i, match in enumerate(matches[:5], 1):
            print(f"\n{i}. {match.away_team} @ {match.home_team}")
            print(f"   Time: {match.match_time}")
            print(f"   ML Odds: {match.away_ml_odds} / {match.home_ml_odds}")
            print(f"   Handicap: {match.away_handicap} ({match.away_handicap_odds}) / {match.home_handicap} ({match.home_handicap_odds})")

    elif choice == '2':
        url = input("\nEnter match URL: ").strip()
        if not url:
            url = "https://www.sportsbet.com.au/betting/basketball-us/nba/indiana-pacers-at-detroit-pistons-9852187"

        print(f"\nScraping match: {url}")
        data = scrape_match_detail(url, headless=False)

        if data:
            print(f"\nMatch: {data.match_odds.away_team} @ {data.match_odds.home_team}")
            print(f"H2H Games: {len(data.head_to_head)}")
            print(f"Teams Stats: {list(data.team_stats.keys())}")
            print(f"Insights: {len(data.insights)}")

    else:
        print("\nGoodbye!\n")
