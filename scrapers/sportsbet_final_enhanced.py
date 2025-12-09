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
import random
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
import logging
import sys

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.retry_utils import retry_scraper_call

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
class InsightCard:
    """Individual insight card from Tips & Match Insights tab (DOM-extracted)"""
    title: str                          # e.g., "Boston Celtics (-6.5) - Handicap Betting"
    description: str                    # Full insight text
    odds: Optional[float] = None
    icon_url: Optional[str] = None
    market_type: Optional[str] = None   # "handicap", "total", "match", "player_prop"
    team: Optional[str] = None
    player: Optional[str] = None        # For player props
    line: Optional[str] = None          # Line value (e.g., "3.5")
    is_expanded: bool = False           # Whether "Show Tip" was clicked
    extraction_method: str = "dom"

    def to_dict(self):
        return asdict(self)


@dataclass
class MatchPreview:
    """Match preview descriptive text"""
    preview_text: str
    timestamp: Optional[str] = None

    def to_dict(self):
        return asdict(self)


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
class SeasonGameResult:
    """Individual game result from season"""
    opponent: str              # Team abbreviation (e.g., "TOR", "PHX")
    date: str                  # Date in format "DD/MM/YY"
    score_for: int             # Team's score
    score_against: int         # Opponent's score
    result: str                # "W" or "L"
    is_home: bool              # True if home game, False if away


@dataclass
class QuarterScores:
    """Quarter-by-quarter scoring"""
    q1: int
    q2: int
    q3: int
    q4: int
    final: int                 # Final score
    ot: Optional[int] = None   # Overtime score if applicable


@dataclass
class HeadToHeadGame:
    """Single head-to-head matchup"""
    date: str                  # Date in format "Day DD Mon YYYY"
    venue: str                 # Venue name (e.g., "TD Garden")
    away_team: str             # Away team abbreviation
    home_team: str             # Home team abbreviation
    away_scores: QuarterScores # Away team quarter scores
    home_scores: QuarterScores # Home team quarter scores
    away_result: str           # "W" or "L"
    home_result: str           # "W" or "L"


@dataclass
class TeamInsights:
    """Complete team insights data"""
    away_team: str
    home_team: str
    away_season_results: List[SeasonGameResult] = field(default_factory=list)
    home_season_results: List[SeasonGameResult] = field(default_factory=list)
    head_to_head: List[HeadToHeadGame] = field(default_factory=list)
    extraction_errors: List[Dict] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'away_team': self.away_team,
            'home_team': self.home_team,
            'away_season_results': [asdict(r) for r in self.away_season_results],
            'home_season_results': [asdict(r) for r in self.home_season_results],
            'head_to_head': [asdict(h) for h in self.head_to_head],
            'extraction_errors': self.extraction_errors
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
    team_insights: Optional[TeamInsights] = None
    match_preview: Optional[MatchPreview] = None
    insight_cards: List[InsightCard] = field(default_factory=list)
    insights_extraction_stats: Dict = field(default_factory=dict)

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
            'match_stats': self.match_stats.to_dict() if self.match_stats else None,
            'team_insights': self.team_insights.to_dict() if self.team_insights else None,
            'match_preview': self.match_preview.to_dict() if self.match_preview else None,
            'insight_cards': [card.to_dict() for card in self.insight_cards],
            'insights_extraction_stats': self.insights_extraction_stats
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

    # Explicit win phrasing
    if ('win' in text_lower or 'to win' in text_lower) and (away_last in text_lower or home_last in text_lower):
        return 'moneyline'

    if re.search(r'\([+-]\d+\.?\d*\)', selection_text) and (away_last in text_lower or home_last in text_lower):
        return 'handicap'

    prop_keywords = ['points', 'rebounds', 'assists', 'threes', 'first', 'anytime', 'scorer', 'basket', 'player']
    if any(word in text_lower for word in prop_keywords):
        return 'prop'

    return 'unknown'


def retry_with_backoff(func, max_attempts=3, initial_delay=1.0):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        
    Returns:
        Function result if successful, None if all attempts fail
    """
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt < max_attempts - 1:
                delay = initial_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_attempts} attempts failed: {e}")
                return None


def validate_score(score: int) -> bool:
    """
    Validate that a score is a valid positive integer within reasonable range.
    
    Args:
        score: Score value to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if not isinstance(score, int):
            logger.warning(f"Score is not an integer: {score} (type: {type(score)})")
            return False
        
        if score < 0 or score > 200:
            logger.warning(f"Score out of valid range (0-200): {score}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating score: {e}")
        return False


def validate_date(date_str: str, format_type: str = "season") -> bool:
    """
    Validate that a date string follows the expected format pattern.
    
    Args:
        date_str: Date string to validate
        format_type: "season" for DD/MM/YY or "h2h" for "Day DD Mon YYYY"
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if not isinstance(date_str, str):
            logger.warning(f"Date is not a string: {date_str}")
            return False
        
        if format_type == "season":
            # Format: DD/MM/YY (e.g., "04/12/25")
            pattern = r'^\d{2}/\d{2}/\d{2}$'
            if not re.match(pattern, date_str):
                logger.warning(f"Date does not match season format (DD/MM/YY): {date_str}")
                return False
        elif format_type == "h2h":
            # Format: Day DD Mon YYYY (e.g., "Sat 8 Mar 2025")
            pattern = r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{1,2}\s+\w+\s+\d{4}'
            if not re.match(pattern, date_str, re.I):
                logger.warning(f"Date does not match H2H format: {date_str}")
                return False
        else:
            logger.warning(f"Unknown date format type: {format_type}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating date: {e}")
        return False


def validate_team_abbrev(abbrev: str) -> bool:
    """
    Validate that a team abbreviation is 2-4 characters.
    
    Args:
        abbrev: Team abbreviation to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if not isinstance(abbrev, str):
            logger.warning(f"Team abbreviation is not a string: {abbrev}")
            return False
        
        if len(abbrev) < 2 or len(abbrev) > 4:
            logger.warning(f"Team abbreviation length invalid (must be 2-4 chars): {abbrev}")
            return False
        
        # Should be uppercase letters
        if not abbrev.isupper():
            logger.warning(f"Team abbreviation should be uppercase: {abbrev}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating team abbreviation: {e}")
        return False


def validate_result(result: str) -> bool:
    """
    Validate that a win/loss indicator is exactly "W" or "L".
    
    Args:
        result: Result string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if not isinstance(result, str):
            logger.warning(f"Result is not a string: {result}")
            return False
        
        if result not in ["W", "L"]:
            logger.warning(f"Result must be 'W' or 'L': {result}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating result: {e}")
        return False


def click_team_toggle(page, team_name: str) -> bool:
    """
    Click team toggle button to switch view between teams.
    
    Args:
        page: Playwright page object
        team_name: Full team name (e.g., "Los Angeles Lakers")
        
    Returns:
        True if clicked successfully, False otherwise
    """
    try:
        # Extract team abbreviation for matching
        team_abbrev = team_name.split()[-1][:3].upper()
        
        # Try multiple selector strategies
        selectors = [
            f'button:has-text("{team_name}")',
            f'button:has-text("{team_abbrev}")',
            f'button[aria-label*="{team_name}"]',
            f'button[aria-label*="{team_abbrev}"]',
            f'[role="radio"]:has-text("{team_name}")',
            f'[role="radio"]:has-text("{team_abbrev}")',
        ]
        
        for selector in selectors:
            try:
                button = page.locator(selector).first
                if button.is_visible(timeout=2000):
                    logger.info(f"Clicking team toggle for {team_name} using selector: {selector}")
                    button.click()
                    time.sleep(1.5)  # Wait for data to swap
                    return True
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        logger.warning(f"Could not find team toggle button for {team_name}")
        return False
        
    except Exception as e:
        logger.error(f"Error clicking team toggle for {team_name}: {e}")
        return False


def click_more_button(page, section_name: str) -> bool:
    """
    Click "More" button to expand content in a specific section.
    
    Args:
        page: Playwright page object
        section_name: Section name like "Season Results" or "Head to Head"
        
    Returns:
        True if clicked successfully, False otherwise
    """
    try:
        logger.info(f"Looking for More button in {section_name} section...")
        
        # First, try to find the section heading
        section_found = False
        section_selectors = [
            f'text=/{section_name}/i',
            f'h2:has-text("{section_name}")',
            f'h3:has-text("{section_name}")',
            f'h4:has-text("{section_name}")',
        ]
        
        section_locator = None
        for selector in section_selectors:
            try:
                loc = page.locator(selector).first
                if loc.is_visible(timeout=2000):
                    section_locator = loc
                    section_found = True
                    logger.info(f"Found {section_name} section")
                    break
            except:
                continue
        
        if not section_found:
            logger.warning(f"Could not find {section_name} section")
            return False
        
        # Now look for More button near the section
        # Try multiple strategies
        more_selectors = [
            'button:has-text("More")',
            'button:has-text("more")',
            'text=/More/i',
            '[role="button"]:has-text("More")',
        ]
        
        # First try to find More button within the section's parent container
        try:
            parent = section_locator.locator('xpath=ancestor::div[3]')
            for selector in more_selectors:
                try:
                    more_button = parent.locator(selector).first
                    if more_button.is_visible(timeout=1000):
                        logger.info(f"Clicking More button in {section_name}")
                        more_button.click()
                        time.sleep(1.5)  # Wait for content expansion
                        return True
                except:
                    continue
        except:
            pass
        
        # If that didn't work, try finding More button globally on the page
        for selector in more_selectors:
            try:
                buttons = page.locator(selector).all()
                for button in buttons:
                    if button.is_visible():
                        logger.info(f"Clicking More button (global search) for {section_name}")
                        button.click()
                        time.sleep(1.5)
                        return True
            except:
                continue
        
        logger.warning(f"Could not find More button in {section_name} section")
        return False
        
    except Exception as e:
        logger.error(f"Error clicking More button in {section_name}: {e}")
        return False


def click_show_tip_buttons(page, max_buttons: int = 50) -> int:
    """
    Click all "Show Tip" buttons to reveal hidden insights.

    Args:
        page: Playwright page object
        max_buttons: Maximum buttons to click (safety limit)

    Returns:
        Number of buttons successfully clicked
    """
    clicked_count = 0

    try:
        logger.info("Searching for Show Tip buttons...")

        # Multiple selector strategies
        selectors = [
            'button:has-text("Show Tip")',
            'button:has-text("show tip")',
            '[aria-label*="Show Tip"]',
            'button[class*="show"][class*="tip"]',
            'button:has-text("Tip")',  # Partial match
        ]

        for selector in selectors:
            try:
                buttons = page.locator(selector).all()
                logger.info(f"Found {len(buttons)} buttons with selector: {selector}")

                for i, button in enumerate(buttons):
                    if clicked_count >= max_buttons:
                        logger.warning(f"Reached max_buttons limit: {max_buttons}")
                        break

                    try:
                        if button.is_visible(timeout=1000):
                            logger.debug(f"Clicking Show Tip button {i+1}")
                            button.click()
                            clicked_count += 1

                            # Wait for expansion animation
                            time.sleep(0.5)

                            # Random delay to avoid detection
                            time.sleep(random.uniform(0.1, 0.3))
                    except Exception as e:
                        logger.debug(f"Could not click button {i+1}: {e}")
                        continue

                if clicked_count > 0:
                    break  # Found working selector

            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        logger.info(f"Successfully clicked {clicked_count} Show Tip buttons")
        return clicked_count

    except Exception as e:
        logger.error(f"Error clicking Show Tip buttons: {e}")
        return clicked_count


def click_display_more_insights(page, max_clicks: int = 5) -> int:
    """
    Click "Display More" button to load additional insights.

    Args:
        page: Playwright page object
        max_clicks: Maximum times to click (prevent infinite loop)

    Returns:
        Number of times button was clicked
    """
    click_count = 0

    try:
        logger.info("Looking for Display More button in insights section...")

        selectors = [
            # Context-aware (within insights section)
            'section[id*="insights"] button:has-text("Display More")',
            'div[class*="insights"] button:has-text("More")',
            'div[class*="tips"] button:has-text("More")',

            # Generic
            'button:has-text("Display More")',
            'button:has-text("Load More")',
            'button:has-text("Show More")',
            '[aria-label*="More insights"]',
        ]

        for attempt in range(max_clicks):
            button_found = False

            for selector in selectors:
                try:
                    button = page.locator(selector).first
                    if button.is_visible(timeout=2000):
                        logger.info(f"Clicking Display More button (attempt {attempt + 1})")
                        button.click()
                        click_count += 1
                        button_found = True

                        # Wait for new content to load
                        time.sleep(2)

                        # Wait for network to settle
                        try:
                            page.wait_for_load_state('networkidle', timeout=5000)
                        except:
                            pass  # Continue even if networkidle times out

                        break  # Found and clicked, move to next attempt
                except:
                    continue

            if not button_found:
                logger.info("Display More button no longer visible (all content loaded)")
                break

        logger.info(f"Clicked Display More button {click_count} times")
        return click_count

    except Exception as e:
        logger.error(f"Error clicking Display More button: {e}")
        return click_count


def extract_match_insights(html: str) -> List[MatchInsight]:
    """
    Extract match insights from embedded JSON in HTML.

    The insights are embedded as: "matchInsights":[{...}, {...}]
    Uses bracket matching to properly extract the complete JSON array.
    """
    insights = []

    try:
        # Try multiple search patterns
        search_patterns = [
            '"matchInsights":[',
            '"matchInsights" : [',
            "'matchInsights':[",
            'matchInsights:['
        ]
        
        start_pos = -1
        search_str = None
        
        for pattern in search_patterns:
            start_pos = html.find(pattern)
            if start_pos != -1:
                search_str = pattern
                logger.info(f"Found matchInsights using pattern: {pattern}")
                break
        
        if start_pos == -1:
            logger.warning("Could not find matchInsights in HTML with any pattern")
            # Try to find it case-insensitively
            import re
            match = re.search(r'matchInsights["\']?\s*:\s*\[', html, re.IGNORECASE)
            if match:
                start_pos = match.start()
                search_str = match.group()
                logger.info(f"Found matchInsights with regex: {search_str}")
            else:
                logger.warning("matchInsights not found even with regex")
                return insights

        # Start after the opening bracket
        json_start = html.find('[', start_pos)
        if json_start == -1:
            logger.warning("Could not find opening bracket for matchInsights")
            return insights

        # Use bracket matching to find the closing bracket
        bracket_count = 0
        in_string = False
        escape_next = False
        end_pos = json_start

        for i in range(json_start, min(json_start + 1000000, len(html))):  # Limit search to 1MB
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
            logger.warning(f"Could not find matching closing bracket for matchInsights (bracket_count={bracket_count})")
            return insights

        # Extract the JSON string
        json_str = html[json_start:end_pos]

        # Parse the JSON
        insights_data = json.loads(json_str)

        logger.info(f"Successfully parsed {len(insights_data)} match insights")
        
        # Debug: show what we got
        if len(insights_data) == 0:
            logger.warning("matchInsights array is empty - no insights available for this game")
            logger.debug(f"JSON extracted: {json_str[:200]}")
        else:
            logger.info(f"Sample insight: {insights_data[0] if insights_data else 'N/A'}")

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
        if 'json_str' in locals():
            logger.error(f"Attempted to parse: {json_str[:500]}...")
    except Exception as e:
        logger.error(f"Failed to extract match insights: {e}")
        import traceback
        traceback.print_exc()

    return insights


def extract_insight_cards_from_dom(page) -> List[InsightCard]:
    """
    Extract all insight cards from the DOM (after expanding).

    Returns:
        List of InsightCard objects
    """
    insight_cards = []

    try:
        logger.info("Extracting insight cards from DOM...")

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Try multiple card container patterns
        card_selectors = [
            {'name': 'insight-card', 'type': 'class'},
            {'name': 'tip-card', 'type': 'class'},
            {'name': 'match-insight', 'type': 'class'},
            {'name': 'insight-card', 'type': 'data-testid'},
            {'name': 'tip', 'type': 'class'},
            {'name': 'betInsight', 'type': 'class'},
        ]

        cards = []
        for selector in card_selectors:
            if selector['type'] == 'class':
                cards = soup.find_all(class_=re.compile(selector['name'], re.I))
            elif selector['type'] == 'data-testid':
                cards = soup.find_all(attrs={'data-testid': re.compile(selector['name'], re.I)})

            if cards:
                logger.info(f"Found {len(cards)} cards using selector: {selector}")
                break

        if not cards:
            logger.warning("No insight card containers found in DOM")
            return insight_cards

        # NBA teams for matching
        nba_teams = [
            'Lakers', 'Celtics', 'Warriors', 'Nets', 'Heat', 'Bulls',
            'Knicks', 'Suns', 'Mavericks', 'Nuggets', 'Clippers', 'Bucks',
            'Sixers', '76ers', 'Raptors', 'Rockets', 'Spurs', 'Thunder',
            'Pacers', 'Pistons', 'Hawks', 'Cavaliers', 'Hornets', 'Jazz',
            'Kings', 'Magic', 'Pelicans', 'Timberwolves', 'Trail Blazers',
            'Grizzlies', 'Wizards'
        ]

        for i, card in enumerate(cards):
            try:
                # Extract title
                title_elem = card.find(class_=re.compile('title|header|heading', re.I))
                if not title_elem:
                    # Try finding h2-h6 tags
                    title_elem = card.find(['h2', 'h3', 'h4', 'h5', 'h6'])
                title = title_elem.get_text(strip=True) if title_elem else f"Insight {i+1}"

                # Extract description
                desc_elem = card.find(class_=re.compile('description|body|text|content', re.I))
                if not desc_elem:
                    # Try finding p tags
                    desc_elem = card.find('p')
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                # Extract odds
                odds_elem = card.find(class_=re.compile('odds|price|decimal', re.I))
                odds = None
                if odds_elem:
                    try:
                        odds_text = odds_elem.get_text(strip=True)
                        # Extract number from text
                        odds_match = re.search(r'(\d+\.?\d*)', odds_text)
                        if odds_match:
                            odds = float(odds_match.group(1))
                    except:
                        pass

                # Extract icon URL
                icon_elem = card.find('img')
                icon_url = icon_elem.get('src', None) if icon_elem else None
                if icon_url and icon_url.startswith('//'):
                    icon_url = 'https:' + icon_url

                # Parse market details from title
                market_type = None
                team = None
                player = None
                line = None

                title_lower = title.lower()

                # Determine market type
                if 'handicap' in title_lower or 'spread' in title_lower:
                    market_type = 'handicap'
                elif 'total' in title_lower or 'over' in title_lower or 'under' in title_lower:
                    market_type = 'total'
                elif ('match' in title_lower or 'winner' in title_lower or 'win' in title_lower) and 'record' not in title_lower:
                    market_type = 'match'
                elif any(prop in title_lower for prop in ['points', 'rebounds', 'assists', 'threes', 'steals', 'blocks', 'record']):
                    market_type = 'player_prop'

                # Extract line value (e.g., "6.5", "223.5", "3.5")
                line_match = re.search(r'[+-]?(\d+\.?\d*)', title)
                if line_match:
                    line = line_match.group(1)

                # Extract player name (for props)
                # Pattern: "FirstName LastName" before "To" or "-"
                player_match = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:To|-|Record)', title)
                if player_match:
                    player = player_match.group(1).strip()

                # Extract team name
                for team_name in nba_teams:
                    if team_name.lower() in title_lower:
                        team = team_name
                        break

                insight_card = InsightCard(
                    title=title,
                    description=description,
                    odds=odds,
                    icon_url=icon_url,
                    market_type=market_type,
                    team=team,
                    player=player,
                    line=line,
                    is_expanded=True,  # We clicked Show Tip
                    extraction_method="dom"
                )

                insight_cards.append(insight_card)
                logger.debug(f"Extracted card: {title}")

            except Exception as e:
                logger.debug(f"Error parsing card {i+1}: {e}")
                continue

        logger.info(f"Successfully extracted {len(insight_cards)} insight cards from DOM")

    except Exception as e:
        logger.error(f"Error extracting insight cards from DOM: {e}")
        import traceback
        traceback.print_exc()

    return insight_cards


def extract_match_preview(page) -> Optional[MatchPreview]:
    """
    Extract match preview descriptive paragraph.

    Returns:
        MatchPreview object or None
    """
    try:
        logger.info("Extracting match preview text...")

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Try multiple preview section patterns
        preview_selectors = [
            # Look for heading + paragraph
            soup.find(['h2', 'h3', 'h4'], string=re.compile('Preview', re.I)),
            soup.find(['h2', 'h3', 'h4'], string=re.compile('Match Preview', re.I)),
            soup.find(['h2', 'h3', 'h4'], string=re.compile('Overview', re.I)),
            # Look for section/div with preview class
            soup.find(class_=re.compile('preview', re.I)),
            soup.find(id=re.compile('preview', re.I)),
            soup.find(class_=re.compile('match.*overview', re.I)),
        ]

        preview_text = None

        for selector in preview_selectors:
            if not selector:
                continue

            # Find paragraph(s) near the heading/section
            paragraphs = []

            if selector.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                # Get next siblings until next heading
                for sibling in selector.next_siblings:
                    if sibling.name == 'p':
                        paragraphs.append(sibling.get_text(strip=True))
                    elif sibling.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                        break
                    # Also check if sibling has paragraphs
                    if hasattr(sibling, 'find_all'):
                        paras_in_sibling = sibling.find_all('p', recursive=False)
                        if paras_in_sibling:
                            paragraphs.extend([p.get_text(strip=True) for p in paras_in_sibling])
                            if len(paragraphs) > 0:
                                break
            else:
                # Find paragraphs within the container
                paragraphs = [p.get_text(strip=True) for p in selector.find_all('p')]

            if paragraphs:
                preview_text = ' '.join(paragraphs)
                logger.info(f"Found preview text ({len(preview_text)} chars)")
                break

        if not preview_text:
            logger.warning("Match preview text not found")
            return None

        return MatchPreview(
            preview_text=preview_text,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Error extracting match preview: {e}")
        return None


def extract_season_results(page, away_team: str, home_team: str) -> Tuple[List[SeasonGameResult], List[SeasonGameResult]]:
    """
    Extract seasonal results for both teams from the Stats & Insights section.
    
    Args:
        page: Playwright page object
        away_team: Away team name (e.g., "Los Angeles Lakers")
        home_team: Home team name (e.g., "Boston Celtics")
        
    Returns:
        Tuple of (away_results, home_results) as lists of SeasonGameResult objects
    """
    away_results = []
    home_results = []
    
    try:
        logger.info("Extracting season results for both teams...")
        
        # Locate Season Results section
        season_section_found = False
        season_selectors = [
            'text=/2025\\/26 Season Results/i',
            'text=/Season Results/i',
            'h2:has-text("Season Results")',
            'h3:has-text("Season Results")',
        ]
        
        for selector in season_selectors:
            try:
                section = page.locator(selector).first
                if section.is_visible(timeout=2000):
                    season_section_found = True
                    logger.info("Found Season Results section")
                    break
            except:
                continue
        
        if not season_section_found:
            logger.warning("Could not find Season Results section")
            return (away_results, home_results)
        
        # Extract away team results
        logger.info(f"Extracting season results for {away_team}...")
        if click_team_toggle(page, away_team):
            time.sleep(1)  # Wait for data to load
            click_more_button(page, "Season Results")  # Expand all games
            time.sleep(1)  # Wait for expansion
            away_results = _parse_season_results(page, away_team)
            logger.info(f"Extracted {len(away_results)} games for {away_team}")
        else:
            logger.warning(f"Could not switch to {away_team} view")
        
        # Extract home team results
        logger.info(f"Extracting season results for {home_team}...")
        if click_team_toggle(page, home_team):
            time.sleep(1)  # Wait for data to load
            click_more_button(page, "Season Results")  # Expand all games
            time.sleep(1)  # Wait for expansion
            home_results = _parse_season_results(page, home_team)
            logger.info(f"Extracted {len(home_results)} games for {home_team}")
        else:
            logger.warning(f"Could not switch to {home_team} view")
        
    except Exception as e:
        logger.error(f"Error extracting season results: {e}")
        import traceback
        traceback.print_exc()
    
    return (away_results, home_results)


def _parse_season_results(page, team_name: str) -> List[SeasonGameResult]:
    """
    Parse season results from the currently visible team view.
    
    Args:
        page: Playwright page object
        team_name: Team name for logging
        
    Returns:
        List of SeasonGameResult objects
    """
    results = []
    
    try:
        html = page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all game rows with dates (format: DD/MM/YY)
        date_pattern = re.compile(r'\d{2}/\d{2}/\d{2}')
        date_elements = soup.find_all(string=date_pattern)
        
        logger.debug(f"Found {len(date_elements)} date elements")
        
        for date_elem in date_elements:
            try:
                # Get parent row
                row = date_elem.find_parent()
                for _ in range(5):  # Go up to find the full row container
                    if row and row.parent:
                        row = row.parent
                    else:
                        break
                
                if not row:
                    continue
                
                row_text = row.get_text(' ', strip=True)
                
                # Extract date
                date_match = date_pattern.search(row_text)
                if not date_match:
                    continue
                date = date_match.group()
                
                # Extract opponent (3-letter abbreviation)
                # Look for 2-4 letter uppercase abbreviations
                opponent_match = re.search(r'\b([A-Z]{2,4})\b', row_text)
                if not opponent_match:
                    continue
                opponent = opponent_match.group(1)
                
                # Extract score (format: 123-120 or 123 - 120)
                score_match = re.search(r'(\d{2,3})\s*-\s*(\d{2,3})', row_text)
                if not score_match:
                    continue
                score_for = int(score_match.group(1))
                score_against = int(score_match.group(2))
                
                # Determine W/L
                if 'W' in row_text and 'L' not in row_text:
                    result = 'W'
                elif 'L' in row_text:
                    result = 'L'
                else:
                    # Infer from score
                    result = 'W' if score_for > score_against else 'L'
                
                # Determine home/away (look for home indicator icon or arrow)
                # Common indicators: ↑ (away), ↓ (home), or specific icons
                is_home = '↓' in row_text or 'home' in row_text.lower()
                # If there's an up arrow or away indicator
                if '↑' in row_text or 'away' in row_text.lower():
                    is_home = False
                
                game_result = SeasonGameResult(
                    opponent=opponent,
                    date=date,
                    score_for=score_for,
                    score_against=score_against,
                    result=result,
                    is_home=is_home
                )
                
                results.append(game_result)
                logger.debug(f"Parsed game: {opponent} {date} {score_for}-{score_against} {result}")
                
            except Exception as e:
                logger.debug(f"Error parsing game row: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error parsing season results for {team_name}: {e}")
    
    return results


def extract_head_to_head(page, away_team: str, home_team: str) -> List[HeadToHeadGame]:
    """
    Extract last 5 head-to-head matchup results with quarter-by-quarter scores.
    
    Args:
        page: Playwright page object
        away_team: Away team name (e.g., "Los Angeles Lakers")
        home_team: Home team name (e.g., "Boston Celtics")
        
    Returns:
        List of HeadToHeadGame objects
    """
    h2h_games = []
    
    try:
        logger.info("Extracting head-to-head matchup history...")
        
        # Locate Head to Head section
        h2h_section_found = False
        h2h_selectors = [
            'text=/Last 5 Head to Head/i',
            'text=/Head to Head/i',
            'h2:has-text("Head to Head")',
            'h3:has-text("Head to Head")',
        ]
        
        for selector in h2h_selectors:
            try:
                section = page.locator(selector).first
                if section.is_visible(timeout=2000):
                    h2h_section_found = True
                    logger.info("Found Head to Head section")
                    break
            except:
                continue
        
        if not h2h_section_found:
            logger.warning("Could not find Head to Head section")
            return h2h_games
        
        # Click More button to expand all matchups
        click_more_button(page, "Head to Head")
        time.sleep(1)  # Wait for expansion
        
        # Parse the H2H games
        html = page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find H2H section in HTML
        h2h_heading = soup.find(string=re.compile(r'Head to Head', re.I))
        if not h2h_heading:
            logger.warning("Could not find H2H section in HTML")
            return h2h_games
        
        # Get container
        h2h_container = h2h_heading.find_parent()
        for _ in range(5):
            if h2h_container and h2h_container.parent:
                h2h_container = h2h_container.parent
        
        if not h2h_container:
            return h2h_games
        
        # Find all game entries (look for date + venue patterns)
        # Format: "Sat 8 Mar 2025 - TD Garden" or "Thu 23 Jan 2025 - Crypto.com Arena"
        date_venue_pattern = re.compile(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{1,2}\s+\w+\s+\d{4}\s*-\s*(.+?)(?=\n|$)', re.I)
        
        # Get all text from H2H container
        h2h_text = h2h_container.get_text('\n', strip=True)
        
        # Find all date-venue matches
        date_venue_matches = date_venue_pattern.findall(h2h_text)
        logger.info(f"Found {len(date_venue_matches)} potential H2H games")
        
        # For each game, extract quarter scores
        for match in date_venue_matches:
            try:
                full_date = match[0] if isinstance(match, tuple) else match
                venue = match[1] if isinstance(match, tuple) and len(match) > 1 else "Unknown"
                
                # Find the game data near this date
                # Look for Q1, Q2, Q3, Q4, FT scores
                # Pattern: team rows with quarter scores
                
                # Extract team abbreviations
                away_abbrev = away_team.split()[-1][:3].upper()
                home_abbrev = home_team.split()[-1][:3].upper()
                
                # Find score rows for this game
                # Look for patterns like: "LAL 33 21 13 34 101 L"
                score_pattern = re.compile(rf'({away_abbrev}|{home_abbrev})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+(\d+))?\s+(\d+)\s+([WL])')
                
                # Search in a window around the date
                date_pos = h2h_text.find(full_date)
                if date_pos == -1:
                    continue
                
                # Get text window (500 chars after date)
                window = h2h_text[date_pos:date_pos+500]
                
                score_matches = score_pattern.findall(window)
                
                if len(score_matches) < 2:
                    logger.debug(f"Could not find both team scores for game on {full_date}")
                    continue
                
                # Parse scores for both teams
                team1_data = score_matches[0]
                team2_data = score_matches[1]
                
                # Determine which is away/home
                if team1_data[0] == away_abbrev:
                    away_data = team1_data
                    home_data = team2_data
                else:
                    away_data = team2_data
                    home_data = team1_data
                
                # Parse away team scores
                away_q1 = int(away_data[1])
                away_q2 = int(away_data[2])
                away_q3 = int(away_data[3])
                away_q4 = int(away_data[4])
                away_ot = int(away_data[5]) if away_data[5] else None
                away_final = int(away_data[6])
                away_result = away_data[7]
                
                away_scores = QuarterScores(
                    q1=away_q1,
                    q2=away_q2,
                    q3=away_q3,
                    q4=away_q4,
                    final=away_final,
                    ot=away_ot
                )
                
                # Parse home team scores
                home_q1 = int(home_data[1])
                home_q2 = int(home_data[2])
                home_q3 = int(home_data[3])
                home_q4 = int(home_data[4])
                home_ot = int(home_data[5]) if home_data[5] else None
                home_final = int(home_data[6])
                home_result = home_data[7]
                
                home_scores = QuarterScores(
                    q1=home_q1,
                    q2=home_q2,
                    q3=home_q3,
                    q4=home_q4,
                    final=home_final,
                    ot=home_ot
                )
                
                h2h_game = HeadToHeadGame(
                    date=full_date,
                    venue=venue.strip(),
                    away_team=away_abbrev,
                    home_team=home_abbrev,
                    away_scores=away_scores,
                    home_scores=home_scores,
                    away_result=away_result,
                    home_result=home_result
                )
                
                h2h_games.append(h2h_game)
                logger.debug(f"Parsed H2H game: {full_date} at {venue} - {away_abbrev} {away_final} vs {home_abbrev} {home_final}")
                
            except Exception as e:
                logger.debug(f"Error parsing H2H game: {e}")
                continue
        
        logger.info(f"Extracted {len(h2h_games)} head-to-head games")
        
    except Exception as e:
        logger.error(f"Error extracting head-to-head data: {e}")
        import traceback
        traceback.print_exc()
    
    return h2h_games


def extract_season_results_from_playwright(page, away_team: str, home_team: str) -> Optional[Dict]:
    """
    Simple extraction: Get ALL page text and extract scores with regex.
    """
    try:
        logger.info("Getting all page text...")
        
        # Get ALL text from the page
        all_text = page.evaluate("() => document.body.innerText")
        
        # Save to debug file
        debug_file = Path(__file__).parent.parent / "debug" / "page_full_text.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(all_text)
        logger.info(f"Saved full page text to {debug_file}")
        
        # Find ALL score patterns: "123-456 W" or "123-456 L"
        # Pattern: 2-3 digits, dash, 2-3 digits, optional space, W or L
        score_patterns = re.findall(r'(\d{2,3})-(\d{2,3})\s*([WL])', all_text)
        
        logger.info(f"Found {len(score_patterns)} scores in page")
        
        if not score_patterns:
            logger.warning("No scores found")
            return None
        
        # Convert to results
        results = {
            'away_team': away_team,
            'home_team': home_team,
            'away_results': [],
            'home_results': []
        }
        
        # Add all scores (we'll split them later if needed)
        for score1, score2, result in score_patterns:
            results['away_results'].append((int(score1), int(score2), result))
        
        logger.info(f"Extracted {len(results['away_results'])} game results")
        return results
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_season_results_from_page(page, away_team: str, home_team: str) -> Optional[Dict]:
    """
    Extract season results (recent game scores) from the Stats & Insights tab.
    
    Returns:
        Dict with 'away_results' and 'home_results' lists of (score_for, score_against, result) tuples
    """
    try:
        logger.info("Extracting season results...")
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        results = {
            'away_team': away_team,
            'home_team': home_team,
            'away_results': [],
            'home_results': []
        }
        
        # Find the "2025/26 Season Results" section - try multiple patterns
        season_results_heading = None
        patterns = [
            r'2025/26 Season Results',
            r'Season Results',
            r'\d{4}/\d{2} Season Results'
        ]
        
        for pattern in patterns:
            season_results_heading = soup.find(string=re.compile(pattern, re.I))
            if season_results_heading:
                logger.info(f"Found Season Results section with pattern: {pattern}")
                break
        
        if not season_results_heading:
            # Try finding by looking for the heading element directly
            headings = soup.find_all(['h2', 'h3', 'h4', 'div'], string=re.compile(r'Season Results', re.I))
            if headings:
                season_results_heading = headings[0]
                logger.info("Found Season Results section via heading search")
            else:
                logger.warning("Could not find Season Results section")
                return None
        
        # Get the parent container - go up several levels to get the full section
        results_container = season_results_heading
        for _ in range(10):  # Go up more levels
            if results_container and results_container.parent:
                results_container = results_container.parent
            else:
                break
        
        if not results_container:
            logger.warning("Could not find results container")
            return None
        
        logger.info("Found results container, looking for team buttons...")
        
        # Find team toggle buttons to click and get each team's results
        # Look for buttons with team names
        away_abbrev = away_team.split()[-1][:3].upper()  # e.g., "LAK" from "Lakers"
        home_abbrev = home_team.split()[-1][:3].upper()  # e.g., "CEL" from "Celtics"
        
        # Try to find which team is currently selected
        # Look for all score patterns in the visible content
        all_text = results_container.get_text(' ', strip=True)
        
        # Find all score patterns like "146-101", "117-123"
        score_patterns = re.findall(r'(\d{2,3})-(\d{2,3})', all_text)
        
        logger.info(f"Found {len(score_patterns)} score patterns in Season Results")
        
        # Also look for W/L indicators next to scores
        # Pattern: score followed by W or L
        game_entries = re.findall(r'(\d{2,3})-(\d{2,3})\s*([WL])', all_text)
        
        logger.info(f"Found {len(game_entries)} complete game entries (score + W/L)")
        
        # Extract results - assume first half are for one team, second half for other
        # Or look for team abbreviations near scores
        for score1, score2, result in game_entries:
            score_for = int(score1)
            score_against = int(score2)
            
            # For now, add to away team (we'll improve this with team detection)
            results['away_results'].append((score_for, score_against, result))
            logger.debug(f"Extracted: {score_for}-{score_against} ({result})")
        
        # If we got results, split them between teams
        # Typically the page shows one team's results at a time
        if results['away_results']:
            # For now, assume all results are for the currently visible team
            # We'll need to click the team toggle to get the other team's results
            logger.info(f"Extracted {len(results['away_results'])} results")
        
        logger.info(f"Total extracted: {len(results['away_results'])} away, {len(results['home_results'])} home")
        
        # Return None if no results found
        if not results['away_results'] and not results['home_results']:
            logger.warning("No results extracted")
            return None
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to extract season results: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_season_results_from_page(page, away_team: str, home_team: str) -> Dict[str, List[Tuple[int, int, str]]]:
    """
    Extract season results for both teams from the expanded Stats & Insights tab.
    
    Returns:
        Dict with 'home_results' and 'away_results' as lists of (score_for, score_against, result) tuples
    """
    results = {
        'home_team': home_team,
        'away_team': away_team,
        'home_results': [],
        'away_results': [],
        'head_to_head': []
    }
    
    try:
        logger.info("Extracting season results from page...")
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find the Season Results section
        season_section = soup.find(string=re.compile(r'2025/26 Season Results', re.I))
        if not season_section:
            logger.warning("Could not find Season Results section")
            return results
        
        # Get the parent container
        container = season_section.find_parent()
        for _ in range(5):  # Go up a few levels to get the full section
            if container:
                container = container.find_parent()
        
        if not container:
            logger.warning("Could not find Season Results container")
            return results
        
        logger.info("Found Season Results container, extracting game data...")
        
        # Find all game rows (they have team abbreviations, dates, and scores)
        # Pattern: TOR  04/12/25  123-120  W
        game_rows = container.find_all(string=re.compile(r'\d{2}/\d{2}/\d{2}'))
        
        logger.info(f"Found {len(game_rows)} date entries")
        
        for date_elem in game_rows:
            try:
                # Get the parent row
                row = date_elem.find_parent()
                for _ in range(3):
                    if row:
                        row = row.find_parent()
                
                if not row:
                    continue
                
                row_text = row.get_text(' ', strip=True)
                
                # Extract score pattern: "123-120" or "123 - 120"
                score_match = re.search(r'(\d{2,3})\s*-\s*(\d{2,3})', row_text)
                if not score_match:
                    continue
                
                score_for = int(score_match.group(1))
                score_against = int(score_match.group(2))
                
                # Determine W/L
                result = 'W' if score_for > score_against else 'L'
                
                # Check if this row has a home indicator (🏠 or "home" icon)
                is_home_game = '🏠' in row_text or 'home' in row_text.lower()
                
                # Determine which team this belongs to
                # If we see the away team name in the row, it's away team's result
                # If we see the home team name, it's home team's result
                away_last = away_team.split()[-1].upper()
                home_last = home_team.split()[-1].upper()
                
                if away_last in row_text.upper():
                    results['away_results'].append((score_for, score_against, result))
                    logger.debug(f"Away team result: {score_for}-{score_against} {result}")
                elif home_last in row_text.upper():
                    results['home_results'].append((score_for, score_against, result))
                    logger.debug(f"Home team result: {score_for}-{score_against} {result}")
                
            except Exception as e:
                logger.debug(f"Error parsing game row: {e}")
                continue
        
        # Extract Head to Head results
        logger.info("Extracting Head to Head results...")
        h2h_section = soup.find(string=re.compile(r'Last 5 Head to Head', re.I))
        if h2h_section:
            h2h_container = h2h_section.find_parent()
            for _ in range(5):
                if h2h_container:
                    h2h_container = h2h_container.find_parent()
            
            if h2h_container:
                # Find all game entries with FT (Final Time) scores
                ft_entries = h2h_container.find_all(string=re.compile(r'FT'))
                logger.info(f"Found {len(ft_entries)} head-to-head games")
                
                for ft_elem in ft_entries:
                    try:
                        row = ft_elem.find_parent()
                        for _ in range(3):
                            if row:
                                row = row.find_parent()
                        
                        if not row:
                            continue
                        
                        row_text = row.get_text(' ', strip=True)
                        
                        # Extract both team scores from the row
                        # Pattern: LAL 101 L  BOS 111 W
                        scores = re.findall(r'(\d{2,3})', row_text)
                        if len(scores) >= 2:
                            # First score is usually away team, second is home team
                            away_score = int(scores[0])
                            home_score = int(scores[1])
                            
                            results['head_to_head'].append({
                                'away_score': away_score,
                                'home_score': home_score,
                                'away_result': 'W' if away_score > home_score else 'L',
                                'home_result': 'W' if home_score > away_score else 'L'
                            })
                            logger.debug(f"H2H: {away_score}-{home_score}")
                    except Exception as e:
                        logger.debug(f"Error parsing H2H row: {e}")
                        continue
        
        logger.info(f"Extracted {len(results['away_results'])} away results, {len(results['home_results'])} home results, {len(results['head_to_head'])} H2H games")
        
    except Exception as e:
        logger.error(f"Error extracting season results: {e}")
        import traceback
        traceback.print_exc()
    
    return results


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
        # Look for dropdown button or selected option
        dropdown_buttons = soup.find_all(['button', 'div'], string=re.compile(r'Last \d+ Matches|Season \d{4}/\d{2}', re.I))
        for btn in dropdown_buttons:
            text = btn.get_text(strip=True)
            if 'Last' in text or 'Season' in text:
                # Avoid CSS or long strings
                if len(text) < 50 and not '{' in text:
                    data_range = text
                    logger.info(f"Data range: {data_range}")
                    break

        # Fallbacks: if key records missing, search globally by labels
        def fill_from_label(label_regex: str, set_attrs: tuple):
            elems = soup.find_all(string=re.compile(label_regex, re.I))
            for elem in elems:
                parent = elem.find_parent()
                if not parent:
                    continue
                text = parent.get_text(" ", strip=True)
                nums = re.findall(r'(\d+\.?\d+)', text)
                if len(nums) >= 2:
                    try:
                        a_val = float(nums[0])
                        h_val = float(nums[-1])
                        # Sanity ranges
                        if set_attrs[0] in ['avg_points_for', 'avg_points_against']:
                            if not (60.0 <= a_val <= 150.0 and 60.0 <= h_val <= 150.0):
                                continue
                        if set_attrs[0] == 'avg_total_points':
                            if not (150.0 <= a_val <= 300.0 and 150.0 <= h_val <= 300.0):
                                continue
                        setattr(away_stats, set_attrs[0], a_val)
                        setattr(home_stats, set_attrs[1], h_val)
                        return True
                    except:
                        continue
            return False

        if away_stats.avg_points_for is None or home_stats.avg_points_for is None:
            fill_from_label(r'Average\s+Points\s+For|Points\s+For', ('avg_points_for', 'avg_points_for'))
        if away_stats.avg_points_against is None or home_stats.avg_points_against is None:
            fill_from_label(r'Average\s+Points\s+Against|Points\s+Against', ('avg_points_against', 'avg_points_against'))
        if away_stats.avg_total_points is None or home_stats.avg_total_points is None:
            fill_from_label(r'Total\s+Match\s+Points|Total\s+Points', ('avg_total_points', 'avg_total_points'))

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


@retry_scraper_call(max_attempts=3, min_wait=2.0, max_wait=10.0)
def scrape_match_complete(url: str, headless: bool = True) -> Optional[CompleteMatchData]:
    """
    Scrape complete match data including:
    - Betting markets
    - Match insights from Stats & Insights tab
    
    This function has retry logic - it will automatically retry up to 3 times
    with exponential backoff if scraping fails.
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
                    
                    # Wait for content to load
                    logger.info("Waiting 20 seconds for Stats & Insights to fully load...")
                    time.sleep(20)
                    
                    # Check what we have
                    test_text = page.evaluate("() => document.body.innerText")
                    if "Season Results" in test_text:
                        logger.info("✓ Season Results IS in page text")
                    else:
                        logger.warning("✗ Season Results NOT in page text")
                    
                    # Count scores
                    scores = re.findall(r'\d{2,3}-\d{2,3}', test_text)
                    logger.info(f"Found {len(scores)} score patterns after clicking tab")
                    
                    stats_clicked = True

                    # Click on "Stats" sub-tab to ensure we're on the right view
                    try:
                        # Try multiple selectors for the Stats tab
                        stats_found = False
                        for selector in ['text="Stats"', 'button:has-text("Stats")', '[role="tab"]:has-text("Stats")']:
                            try:
                                stats_subtab = page.locator(selector).first
                                if stats_subtab.is_visible(timeout=1000):
                                    logger.info(f"Clicking Stats sub-tab with selector: {selector}")
                                    stats_subtab.click()
                                    time.sleep(3)  # Wait longer for content
                                    stats_found = True
                                    break
                            except:
                                continue
                        
                        if not stats_found:
                            logger.info("No Stats sub-tab found - may already be on Stats view")
                    except Exception as e:
                        logger.info(f"Stats sub-tab interaction: {e}")
                    
                    # Scroll down aggressively to load all sections
                    logger.info("Scrolling to load all sections...")
                    for i in range(10):
                        page.evaluate(f"window.scrollBy(0, {500 * (i + 1)})")
                        time.sleep(0.5)
                    
                    # Scroll back to top
                    page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(1)
                    
                    # Scroll down again slowly
                    for i in range(5):
                        page.evaluate("window.scrollBy(0, 800)")
                        time.sleep(1)

                    # ============================================================
                    # NEW: COMPREHENSIVE INSIGHTS EXTRACTION
                    # ============================================================

                    # PHASE 1: Navigate to Tips & Insights Sub-tab
                    logger.info("=" * 60)
                    logger.info("PHASE 1: Tips & Insights Tab Navigation")
                    logger.info("=" * 60)

                    try:
                        tips_tab_selectors = [
                            'button:has-text("Tips")',
                            '[role="tab"]:has-text("Tips")',
                            'a:has-text("Match Insights")',
                            'button:has-text("Insights")',
                        ]

                        tips_tab_found = False
                        for selector in tips_tab_selectors:
                            try:
                                tips_tab = page.locator(selector).first
                                if tips_tab.is_visible(timeout=2000):
                                    logger.info(f"✓ Clicking Tips sub-tab: {selector}")
                                    tips_tab.click()
                                    time.sleep(3)  # Wait for insights to load
                                    try:
                                        page.wait_for_load_state('networkidle', timeout=10000)
                                    except:
                                        pass  # Continue even if networkidle times out
                                    tips_tab_found = True
                                    break
                            except:
                                continue

                        if not tips_tab_found:
                            logger.info("No separate Tips tab found - may already be on correct view")

                    except Exception as e:
                        logger.debug(f"Tips tab navigation: {e}")

                    # PHASE 2: Click "Display More" for insights
                    logger.info("=" * 60)
                    logger.info("PHASE 2: Expanding Insights with Display More")
                    logger.info("=" * 60)

                    display_more_clicks = 0
                    try:
                        display_more_clicks = click_display_more_insights(page, max_clicks=5)
                        logger.info(f"✓ Clicked Display More {display_more_clicks} times")
                    except Exception as e:
                        logger.debug(f"Display More clicks: {e}")
                        display_more_clicks = 0

                    # PHASE 3: Click all "Show Tip" buttons
                    logger.info("=" * 60)
                    logger.info("PHASE 3: Revealing Hidden Insights (Show Tip)")
                    logger.info("=" * 60)

                    show_tip_clicks = 0
                    try:
                        show_tip_clicks = click_show_tip_buttons(page, max_buttons=50)
                        logger.info(f"✓ Clicked {show_tip_clicks} Show Tip buttons")
                    except Exception as e:
                        logger.debug(f"Show Tip clicks: {e}")
                        show_tip_clicks = 0

                    # Wait for all expansions to complete
                    time.sleep(2)

                    # PHASE 4: Extract insight cards from DOM
                    logger.info("=" * 60)
                    logger.info("PHASE 4: Extracting Insight Cards from DOM")
                    logger.info("=" * 60)

                    insight_cards = []
                    try:
                        insight_cards = extract_insight_cards_from_dom(page)
                        logger.info(f"✓ Extracted {len(insight_cards)} insight cards from DOM")
                    except Exception as e:
                        logger.error(f"Insight cards extraction failed: {e}")
                        insight_cards = []

                    # PHASE 5: Extract match preview
                    logger.info("=" * 60)
                    logger.info("PHASE 5: Extracting Match Preview Text")
                    logger.info("=" * 60)

                    match_preview = None
                    try:
                        match_preview = extract_match_preview(page)
                        if match_preview:
                            logger.info(f"✓ Match preview extracted ({len(match_preview.preview_text)} chars)")
                        else:
                            logger.warning("✗ Match preview not found")
                    except Exception as e:
                        logger.debug(f"Match preview extraction: {e}")
                        match_preview = None

                    # Screenshot for verification
                    try:
                        screenshot_path = Path(__file__).parent.parent / "debug" / "insights_expanded.png"
                        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(screenshot_path), full_page=True)
                        logger.info(f"Saved insights screenshot: {screenshot_path}")
                    except Exception as e:
                        logger.debug(f"Could not save screenshot: {e}")

                    # PHASE 6: Navigate back to Stats sub-tab for season results/H2H
                    logger.info("=" * 60)
                    logger.info("PHASE 6: Switching to Stats Sub-tab")
                    logger.info("=" * 60)

                    try:
                        for selector in ['text="Stats"', 'button:has-text("Stats")', '[role="tab"]:has-text("Stats")']:
                            try:
                                stats_subtab = page.locator(selector).first
                                if stats_subtab.is_visible(timeout=1000):
                                    logger.info(f"Clicking Stats sub-tab: {selector}")
                                    stats_subtab.click()
                                    time.sleep(3)
                                    break
                            except:
                                continue
                    except Exception as e:
                        logger.debug(f"Stats sub-tab navigation: {e}")

                    # ============================================================
                    # END: COMPREHENSIVE INSIGHTS EXTRACTION
                    # ============================================================

                    # Click team toggle buttons to get both teams' season results
                    logger.info("Looking for team toggle buttons...")
                    try:
                        # Find the season results section
                        season_results_heading = page.locator('text=/2025\\/26 Season Results/i').first
                        if season_results_heading.is_visible(timeout=2000):
                            logger.info("Found Season Results section")
                            
                            # Click the away team button (first circle button)
                            try:
                                away_button = page.locator('button[aria-label*="' + away_team + '"], button:has-text("' + away_team.split()[-1] + '")').first
                                if away_button.is_visible(timeout=1000):
                                    logger.info(f"Clicking {away_team} button...")
                                    away_button.click()
                                    time.sleep(2)
                            except Exception as e:
                                logger.debug(f"Could not click away team button: {e}")
                            
                            # Click the home team button (second circle button)
                            try:
                                home_button = page.locator('button[aria-label*="' + home_team + '"], button:has-text("' + home_team.split()[-1] + '")').first
                                if home_button.is_visible(timeout=1000):
                                    logger.info(f"Clicking {home_team} button...")
                                    home_button.click()
                                    time.sleep(2)
                            except Exception as e:
                                logger.debug(f"Could not click home team button: {e}")
                    except Exception as e:
                        logger.debug(f"Error with team toggle buttons: {e}")
                    
                    # DISABLED: Season Results scraping - it's never available on Sportsbet
                    # We get team seasonal data from StatMuse instead (faster and more reliable)
                    # This saves ~15 seconds per game
                    logger.info("Skipping Season Results search (use StatMuse for team stats instead)")

                    # Save a screenshot to see what's visible
                    try:
                        screenshot_path = Path(__file__).parent.parent / "debug" / "stats_insights_view.png"
                        page.screenshot(path=str(screenshot_path))
                        logger.info(f"Saved Stats & Insights screenshot to {screenshot_path}")
                    except Exception as e:
                        logger.debug(f"Could not save screenshot: {e}")
                    
                    logger.info("Finished expanding all data sections")
            except Exception as e:
                logger.warning(f"Could not click Stats & Insights tab: {e}")

            # Get team names
            # First try robust extraction from URL slug as fallback
            away_team = "Unknown"
            home_team = "Unknown"

            try:
                slug = url.rstrip('/').split('/')[-1]
                parts = slug.split('-')
                if 'at' in parts:
                    idx = parts.index('at')
                    away_tokens = parts[:idx]
                    home_tokens = parts[idx+1:]
                    def normalize(tokens):
                        cleaned = [t for t in tokens if not t.isdigit()]
                        return ' '.join([t.capitalize() for t in cleaned])
                    away_team = normalize(away_tokens)
                    home_team = normalize(home_tokens)
            except Exception:
                pass

            # If slug parse failed, fall back to title heuristic
            if away_team == "Unknown" or home_team == "Unknown":
                title = page.title()
                # Capture sequences of capitalized words (handles 2-3 word names)
                teams = re.findall(r'([A-Z][a-z]+(?: [A-Z][a-z]+)+)', title)
                away_team = teams[0] if len(teams) > 0 else away_team
                home_team = teams[1] if len(teams) > 1 else home_team

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
            # Secondary extraction for moneyline using outcome price and name labels
            logger.info("Secondary extraction for moneyline markets...")
            price_spans = soup.find_all('span', {'data-automation-id': re.compile(r'outcome-price-text')})
            for price in price_spans:
                try:
                    odds_value = float(price.get_text(strip=True))
                except:
                    continue
                container = price
                for _ in range(6):
                    if container and container.parent:
                        container = container.parent
                if not container:
                    continue
                name_span = container.find('span', {'data-automation-id': re.compile(r'outcome-name')})
                selection_text = None
                if name_span:
                    selection_text = name_span.get_text(strip=True)
                else:
                    txt = container.get_text(" ", strip=True)
                    for t in [away_team, home_team]:
                        last = t.split()[-1]
                        if last and last.lower() in txt.lower():
                            selection_text = t
                            break
                if not selection_text:
                    continue
                category = categorize_market(selection_text, away_team, home_team)
                team = None
                sel_lower = selection_text.lower()
                away_last = away_team.split()[-1].lower()
                home_last = home_team.split()[-1].lower()
                if away_team.lower() in sel_lower or away_last in sel_lower:
                    team = away_team
                elif home_team.lower() in sel_lower or home_last in sel_lower:
                    team = home_team
                market_key = f"{selection_text}_{odds_value}"
                if team and category == 'moneyline' and market_key not in seen:
                    markets.append(BettingMarket(
                        selection_text=selection_text,
                        odds=odds_value,
                        team=team,
                        line=None,
                        market_category='moneyline'
                    ))
                    seen.add(market_key)

            # Extract match insights from HTML
            logger.info("Extracting match insights...")
            # Check if matchInsights exists in the HTML
            if 'matchInsights' in html:
                logger.info("matchInsights found in HTML, extracting...")
            else:
                logger.warning("matchInsights NOT found in HTML - insights may not have loaded")
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

            # Extract team insights (season results + head-to-head) if Stats tab was clicked
            team_insights = None
            extraction_errors = []
            
            if stats_clicked:
                try:
                    # DISABLED: Season results and H2H extraction from Sportsbet
                    # These sections are never available, and trying to scrape them wastes 15+ seconds per game
                    # We get this data from StatMuse instead (faster and more reliable)
                    logger.info("Skipping team insights extraction (use StatMuse for team seasonal data)")

                    # Create empty TeamInsights since we don't extract from Sportsbet anymore
                    team_insights = TeamInsights(
                        away_team=away_team,
                        home_team=home_team,
                        away_season_results=[],
                        home_season_results=[],
                        head_to_head=[],
                        extraction_errors=[]
                    )

                    logger.info(f"Team insights extracted: 0 away games, 0 home games, 0 H2H games (use StatMuse instead)")

                except Exception as e:
                    logger.error(f"[CRITICAL] Error creating team insights: {e}")
                    import traceback
                    traceback.print_exc()
                    # Create empty TeamInsights with error
                    team_insights = TeamInsights(
                        away_team=away_team,
                        home_team=home_team,
                        extraction_errors=[{
                            "component": "team_insights",
                            "error": f"Critical failure: {str(e)}",
                            "timestamp": datetime.now().isoformat()
                        }]
                    )
            
            # Extract team statistics (if Stats tab was clicked)
            match_stats = None
            if stats_clicked:
                match_stats = extract_team_stats_from_page(page, away_team, home_team)

            # ============================================================
            # EXTRACTION STATISTICS TRACKING
            # ============================================================

            # Track extraction success rates
            insights_extraction_stats = {
                'total_json_insights': len(insights),  # From embedded JSON
                'total_dom_insights': len(insight_cards) if 'insight_cards' in locals() else 0,  # From DOM extraction
                'combined_insights': len(insights) + (len(insight_cards) if 'insight_cards' in locals() else 0),
                'show_tip_buttons_clicked': show_tip_clicks if 'show_tip_clicks' in locals() else 0,
                'display_more_clicks': display_more_clicks if 'display_more_clicks' in locals() else 0,
                'match_preview_found': (match_preview is not None) if 'match_preview' in locals() else False,
                'season_results_away': len(team_insights.away_season_results) if team_insights else 0,
                'season_results_home': len(team_insights.home_season_results) if team_insights else 0,
                'head_to_head_games': len(team_insights.head_to_head) if team_insights else 0,
                'team_stats_populated': match_stats is not None,
            }

            logger.info("=" * 60)
            logger.info("EXTRACTION SUMMARY")
            logger.info("=" * 60)
            for key, value in insights_extraction_stats.items():
                logger.info(f"{key}: {value}")
            logger.info("=" * 60)

            complete_data = CompleteMatchData(
                away_team=away_team,
                home_team=home_team,
                url=url,
                scraped_at=datetime.now().isoformat(),
                all_markets=markets,
                match_insights=insights,
                match_stats=match_stats,
                team_insights=team_insights,
                match_preview=match_preview if 'match_preview' in locals() else None,
                insight_cards=insight_cards if 'insight_cards' in locals() else [],
                insights_extraction_stats=insights_extraction_stats
            )

            return complete_data

        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            browser.close()


@retry_scraper_call(max_attempts=3, min_wait=2.0, max_wait=10.0)
def scrape_nba_overview(headless: bool = True) -> List[Dict]:
    """
    Scrape NBA overview to get all games.
    
    This function has retry logic - it will automatically retry up to 3 times
    with exponential backoff if scraping fails.
    """

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
            
            # RATE LIMITING: Wait longer for dynamic content to load
            time.sleep(8)  # Increased from 5 to 8 seconds

            # Try scrolling to trigger lazy loading (with delays to appear more human)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)  # Increased from 2 to 3 seconds
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(3)  # Increased from 2 to 3 seconds

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
