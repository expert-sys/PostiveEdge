# Design Document

## Overview

This design extends the existing Sportsbet scraper (`scrapers/sportsbet_final_enhanced.py`) to extract comprehensive team insights from the Stats & Insights section of NBA game pages. The enhancement focuses on capturing seasonal results and head-to-head matchup data for both teams, providing richer historical context for betting analysis.

The scraper currently extracts betting markets, match insights, and team statistics. This enhancement adds structured extraction of:
- Complete seasonal game results for both teams (opponent, date, score, W/L, home/away)
- Last 5 head-to-head matchup results with quarter-by-quarter scoring breakdowns

## Architecture

### Current Architecture

The existing scraper uses:
- **Playwright** for browser automation and dynamic content handling
- **BeautifulSoup** for HTML parsing
- **Dataclasses** for structured data representation
- **JSON** for data serialization

### Enhanced Architecture

The enhancement maintains the existing architecture and adds:

1. **New Data Models**: `SeasonResult`, `HeadToHeadGame`, `TeamInsights` dataclasses
2. **New Extraction Functions**: 
   - `extract_season_results()` - Extracts seasonal game data for both teams
   - `extract_head_to_head()` - Extracts H2H matchup history
3. **Enhanced CompleteMatchData**: Extended to include `team_insights` field
4. **UI Interaction Logic**: Handles team toggle buttons and "More" button expansion

### Component Interaction Flow

```
scrape_match_complete()
    ├── Navigate to game page
    ├── Click "Stats & Insights" tab
    ├── Wait for dynamic content load
    ├── extract_season_results()
    │   ├── Click away team toggle
    │   ├── Click "More" button (season results)
    │   ├── Extract all game data
    │   ├── Click home team toggle
    │   ├── Click "More" button (season results)
    │   └── Extract all game data
    ├── extract_head_to_head()
    │   ├── Locate "Last 5 Head to Head" section
    │   ├── Click "More" button (H2H)
    │   └── Extract quarter-by-quarter scores
    └── Return CompleteMatchData with team_insights
```

## Components and Interfaces

### Data Models

```python
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
    ot: Optional[int] = None   # Overtime score if applicable
    final: int                 # Final score
    
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
    away_season_results: List[SeasonGameResult]
    home_season_results: List[SeasonGameResult]
    head_to_head: List[HeadToHeadGame]
    
    def to_dict(self):
        return {
            'away_team': self.away_team,
            'home_team': self.home_team,
            'away_season_results': [asdict(r) for r in self.away_season_results],
            'home_season_results': [asdict(r) for r in self.home_season_results],
            'head_to_head': [asdict(h) for h in self.head_to_head]
        }
```

### Extraction Functions

#### extract_season_results()

```python
def extract_season_results(page, away_team: str, home_team: str) -> Tuple[List[SeasonGameResult], List[SeasonGameResult]]:
    """
    Extract seasonal results for both teams.
    
    Args:
        page: Playwright page object
        away_team: Away team name
        home_team: Home team name
        
    Returns:
        Tuple of (away_results, home_results)
        
    Process:
        1. Locate "2025/26 Season Results" section
        2. Click away team toggle button
        3. Click "More" button to expand all games
        4. Extract all game data (opponent, date, score, W/L, home/away)
        5. Click home team toggle button
        6. Click "More" button to expand all games
        7. Extract all game data
        8. Return structured results for both teams
    """
```

#### extract_head_to_head()

```python
def extract_head_to_head(page, away_team: str, home_team: str) -> List[HeadToHeadGame]:
    """
    Extract last 5 head-to-head matchup results.
    
    Args:
        page: Playwright page object
        away_team: Away team name
        home_team: Home team name
        
    Returns:
        List of HeadToHeadGame objects
        
    Process:
        1. Locate "Last 5 Head to Head" section
        2. Click "More" button to expand all games
        3. For each game:
           - Extract date and venue
           - Extract Q1, Q2, Q3, Q4 scores for both teams
           - Extract OT score if present
           - Extract final scores
           - Determine W/L for each team
        4. Return structured H2H data
    """
```

### UI Interaction Helpers

```python
def click_team_toggle(page, team_name: str) -> bool:
    """
    Click team toggle button to switch view.
    
    Selectors to try:
        - Radio button with team name
        - Button with aria-label containing team name
        - Circle button near team name text
        
    Returns:
        True if clicked successfully, False otherwise
    """

def click_more_button(page, section_name: str) -> bool:
    """
    Click "More" button to expand content.
    
    Args:
        section_name: "Season Results" or "Head to Head"
        
    Process:
        1. Locate section by heading text
        2. Find "More" button within section
        3. Click button
        4. Wait for content expansion
        
    Returns:
        True if clicked successfully, False otherwise
    """
```

## Data Models

See "Components and Interfaces" section above for complete data model definitions.

Key design decisions:
- **Separate models for season vs H2H**: Different data structures and granularity
- **QuarterScores nested model**: Keeps quarter data organized and type-safe
- **Boolean for home/away**: More explicit than string indicators
- **Optional OT field**: Not all games go to overtime



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Component Identification

*For any* NBA game page on Sportsbet, when the scraper accesses the Stats & Insights section, it should successfully identify both the "2025/26 Season Results" component and the "Last 5 Head to Head" component, or return a specific error indicating which component was not found.

**Validates: Requirements 1.1, 2.1**

### Property 2: Dual Team Extraction

*For any* NBA game page, when the scraper detects the team toggle control, the output should contain season results for both the home team and away team, with each team having a non-empty list of games.

**Validates: Requirements 1.2**

### Property 3: Content Expansion

*For any* "More" button encountered in either the season results or head-to-head section, clicking the button should result in the number of extracted games being greater than the initial count (typically expanding from 5 to all available games).

**Validates: Requirements 1.3, 2.2**

### Property 4: Complete Game Data

*For any* extracted season result game, all required fields (opponent abbreviation, game date, final score, win/loss indicator, and home/away indicator) should be present and non-null.

**Validates: Requirements 1.4**

### Property 5: Complete H2H Data

*For any* extracted head-to-head game, all required fields (game date, venue name, Q1-Q4 scores for both teams, final score, and win/loss indicator for each team) should be present and non-null, with overtime scores present when applicable.

**Validates: Requirements 2.3**

### Property 6: Chronological Ordering

*For any* extracted season results or head-to-head results, the games should be ordered chronologically (most recent first or oldest first consistently), with each game's date being in valid sequence relative to adjacent games.

**Validates: Requirements 1.5, 2.5**

### Property 7: Team-Quarter Association Integrity

*For any* extracted head-to-head game, the quarter scores for team A should sum to team A's final score (plus or minus overtime), and the same should hold for team B, ensuring correct association between quarters and teams.

**Validates: Requirements 2.4**

### Property 8: JSON Serialization Round-Trip

*For any* extracted insights data, serializing to JSON and then deserializing should produce an equivalent data structure with all fields preserved.

**Validates: Requirements 3.1**

### Property 9: Structural Correctness

*For any* extracted data, the output should contain exactly two separate arrays for season results (one for home team, one for away team) and one array for head-to-head results with nested quarter score objects.

**Validates: Requirements 3.2, 3.3**

### Property 10: Team Identifier Consistency

*For any* extracted data, if a team is identified by a specific abbreviation (e.g., "LAL") in one location, the same abbreviation should be used consistently throughout the entire data structure.

**Validates: Requirements 3.4**

### Property 11: Date Format Preservation

*For any* extracted date, the format should match the expected pattern from the source (DD/MM/YY for season results, "Day DD Mon YYYY" for H2H), with no transformation or corruption.

**Validates: Requirements 3.5**

### Property 12: Numeric Score Validation

*For any* extracted game score, the value should be a valid positive integer within a reasonable range (0-200 for NBA games).

**Validates: Requirements 5.1**

### Property 13: Date Format Validation

*For any* extracted date string, it should match the expected regex pattern for its context (season results vs H2H format).

**Validates: Requirements 5.2**

### Property 14: Abbreviation Length Validation

*For any* extracted team abbreviation, the length should be between 2 and 4 characters inclusive.

**Validates: Requirements 5.3**

### Property 15: Win/Loss Binary Validation

*For any* extracted win/loss indicator, the value should be exactly "W" or "L" with no other variations.

**Validates: Requirements 5.4**

### Property 16: Home/Away Identification

*For any* season result game with a home/away indicator icon in the source, the extracted is_home boolean should correctly reflect whether the game was played at home.

**Validates: Requirements 6.1**

### Property 17: Perspective Consistency

*For any* team's season results, the score_for field should represent that team's score and score_against should represent the opponent's score, maintaining consistent perspective across all games.

**Validates: Requirements 6.4**

### Property 18: Graceful Error Handling

*For any* component extraction failure, the scraper should log an appropriate error message and continue processing remaining components, rather than failing completely.

**Validates: Requirements 4.4, 5.5**

## Error Handling

### Error Categories

1. **Network Errors**
   - Connection timeouts
   - DNS resolution failures
   - HTTP error responses (4xx, 5xx)
   
   **Handling**: Implement retry logic with exponential backoff (1s, 2s, 4s) up to 3 attempts. Log all retry attempts.

2. **UI Interaction Errors**
   - Element not found (button, toggle, section)
   - Element not clickable
   - Timeout waiting for content
   
   **Handling**: Log specific error with element selector. Continue with partial data extraction. Mark affected data as incomplete.

3. **Data Extraction Errors**
   - Unexpected HTML structure
   - Missing expected data fields
   - Malformed data (invalid scores, dates)
   
   **Handling**: Log warning with context. Set field to null. Continue extraction of other fields.

4. **Validation Errors**
   - Score out of range
   - Invalid date format
   - Invalid team abbreviation
   
   **Handling**: Log warning. Mark field as invalid. Include in output with validation_errors list.

### Error Logging Format

```python
logger.error(f"[{error_category}] {component}: {error_message}")
# Example: [UI_INTERACTION] Season Results: More button not found after 5s timeout
```

### Partial Data Strategy

If extraction fails for one component, return partial data with metadata:

```python
{
    "away_season_results": [...],  # Successfully extracted
    "home_season_results": [],     # Failed to extract
    "head_to_head": [...],         # Successfully extracted
    "extraction_errors": [
        {
            "component": "home_season_results",
            "error": "Team toggle button not found",
            "timestamp": "2025-12-05T10:30:00"
        }
    ]
}
```

## Testing Strategy

### Unit Testing

**Framework**: pytest

**Test Coverage**:

1. **Data Model Tests**
   - Test dataclass instantiation with valid data
   - Test to_dict() serialization
   - Test field validation (if implemented)

2. **Parsing Logic Tests**
   - Test score extraction from various HTML patterns
   - Test date parsing for different formats
   - Test team abbreviation extraction
   - Test W/L determination logic

3. **UI Selector Tests**
   - Test selector patterns against sample HTML
   - Test fallback selector logic
   - Test element visibility checks

4. **Error Handling Tests**
   - Test retry logic with mock failures
   - Test partial data extraction
   - Test error logging format

**Example Unit Tests**:

```python
def test_season_result_creation():
    result = SeasonGameResult(
        opponent="TOR",
        date="04/12/25",
        score_for=123,
        score_against=120,
        result="W",
        is_home=False
    )
    assert result.opponent == "TOR"
    assert result.result == "W"

def test_score_extraction_from_html():
    html = '<div>123-120 <span>W</span></div>'
    score_for, score_against, result = extract_score(html)
    assert score_for == 123
    assert score_against == 120
    assert result == "W"

def test_invalid_score_handling():
    html = '<div>ABC-XYZ <span>W</span></div>'
    result = extract_score(html)
    assert result is None  # Should handle gracefully
```

### Property-Based Testing

**Framework**: Hypothesis (Python)

**Configuration**: Minimum 100 iterations per property test

**Property Tests**:

1. **Property 1: Component Identification**
   ```python
   @given(game_url=st.sampled_from(NBA_GAME_URLS))
   def test_component_identification(game_url):
       """
       Feature: sportsbet-insights-scraper, Property 1: Component Identification
       
       For any NBA game page, scraper should identify both Season Results 
       and Head to Head components or return specific errors.
       """
       data = scrape_match_complete(game_url)
       assert data is not None
       assert hasattr(data, 'team_insights')
       # Either both components found or specific errors logged
       if data.team_insights:
           assert len(data.team_insights.away_season_results) > 0 or \
                  "Season Results" in data.extraction_errors
           assert len(data.team_insights.head_to_head) > 0 or \
                  "Head to Head" in data.extraction_errors
   ```

2. **Property 2: Dual Team Extraction**
   ```python
   @given(game_url=st.sampled_from(NBA_GAME_URLS))
   def test_dual_team_extraction(game_url):
       """
       Feature: sportsbet-insights-scraper, Property 2: Dual Team Extraction
       
       For any game page, output should contain season results for both teams.
       """
       data = scrape_match_complete(game_url)
       if data and data.team_insights:
           insights = data.team_insights
           # Both teams should have data
           assert len(insights.away_season_results) > 0
           assert len(insights.home_season_results) > 0
           # Teams should be different
           assert insights.away_team != insights.home_team
   ```

3. **Property 4: Complete Game Data**
   ```python
   @given(game_url=st.sampled_from(NBA_GAME_URLS))
   def test_complete_game_data(game_url):
       """
       Feature: sportsbet-insights-scraper, Property 4: Complete Game Data
       
       For any extracted season game, all required fields should be present.
       """
       data = scrape_match_complete(game_url)
       if data and data.team_insights:
           for result in data.team_insights.away_season_results:
               assert result.opponent is not None
               assert result.date is not None
               assert result.score_for is not None
               assert result.score_against is not None
               assert result.result in ["W", "L"]
               assert isinstance(result.is_home, bool)
   ```

4. **Property 7: Team-Quarter Association Integrity**
   ```python
   @given(game_url=st.sampled_from(NBA_GAME_URLS))
   def test_quarter_score_integrity(game_url):
       """
       Feature: sportsbet-insights-scraper, Property 7: Team-Quarter Association Integrity
       
       For any H2H game, quarter scores should sum to final score.
       """
       data = scrape_match_complete(game_url)
       if data and data.team_insights:
           for h2h in data.team_insights.head_to_head:
               # Away team
               away_sum = (h2h.away_scores.q1 + h2h.away_scores.q2 + 
                          h2h.away_scores.q3 + h2h.away_scores.q4)
               if h2h.away_scores.ot:
                   away_sum += h2h.away_scores.ot
               assert away_sum == h2h.away_scores.final
               
               # Home team
               home_sum = (h2h.home_scores.q1 + h2h.home_scores.q2 + 
                          h2h.home_scores.q3 + h2h.home_scores.q4)
               if h2h.home_scores.ot:
                   home_sum += h2h.home_scores.ot
               assert home_sum == h2h.home_scores.final
   ```

5. **Property 8: JSON Serialization Round-Trip**
   ```python
   @given(game_url=st.sampled_from(NBA_GAME_URLS))
   def test_json_round_trip(game_url):
       """
       Feature: sportsbet-insights-scraper, Property 8: JSON Serialization Round-Trip
       
       For any extracted data, JSON round-trip should preserve all fields.
       """
       data = scrape_match_complete(game_url)
       if data and data.team_insights:
           # Serialize to JSON
           json_str = json.dumps(data.team_insights.to_dict())
           # Deserialize
           restored = json.loads(json_str)
           # Compare
           original_dict = data.team_insights.to_dict()
           assert restored == original_dict
   ```

6. **Property 12: Numeric Score Validation**
   ```python
   @given(game_url=st.sampled_from(NBA_GAME_URLS))
   def test_numeric_score_validation(game_url):
       """
       Feature: sportsbet-insights-scraper, Property 12: Numeric Score Validation
       
       For any extracted score, value should be valid positive integer in range.
       """
       data = scrape_match_complete(game_url)
       if data and data.team_insights:
           # Check season results
           for result in (data.team_insights.away_season_results + 
                         data.team_insights.home_season_results):
               assert isinstance(result.score_for, int)
               assert isinstance(result.score_against, int)
               assert 0 <= result.score_for <= 200
               assert 0 <= result.score_against <= 200
           
           # Check H2H quarter scores
           for h2h in data.team_insights.head_to_head:
               for score in [h2h.away_scores.q1, h2h.away_scores.q2,
                           h2h.away_scores.q3, h2h.away_scores.q4,
                           h2h.home_scores.q1, h2h.home_scores.q2,
                           h2h.home_scores.q3, h2h.home_scores.q4]:
                   assert isinstance(score, int)
                   assert 0 <= score <= 60  # Quarter scores typically 15-40
   ```

### Integration Testing

**Test Scenarios**:

1. **End-to-End Scraping**
   - Test complete scraping flow on live game page
   - Verify all components extracted
   - Verify data structure correctness

2. **Error Recovery**
   - Test with game page missing Season Results
   - Test with game page missing H2H data
   - Verify partial data extraction works

3. **Multiple Games**
   - Test scraping multiple games in sequence
   - Verify no data contamination between games
   - Verify consistent output format

### Test Data

**Live Test URLs**: Maintain list of recent NBA game URLs for testing

**Mock HTML Fixtures**: Create HTML fixtures representing:
- Complete game page with all data
- Game page missing Season Results
- Game page missing H2H data
- Game page with overtime H2H game
- Game page with unusual team names

## Implementation Notes

### Playwright Wait Strategies

1. **After clicking Stats & Insights tab**: Wait 3-5 seconds for initial load
2. **After clicking team toggle**: Wait 1-2 seconds for data swap
3. **After clicking More button**: Wait 1-2 seconds for content expansion
4. **Before extraction**: Verify target elements are visible

### Selector Robustness

Use multiple fallback selectors for each element:

```python
SEASON_RESULTS_SELECTORS = [
    'text=/2025\\/26 Season Results/i',
    'text=/Season Results/i',
    '[data-testid="season-results"]',
    'h3:has-text("Season Results")'
]
```

### Data Validation Ranges

- **Scores**: 0-200 (NBA games rarely exceed 170)
- **Quarter Scores**: 0-60 (typically 15-40)
- **Team Abbreviations**: 2-4 characters (e.g., "LAL", "BOS", "NOP")
- **Dates**: Valid calendar dates within current season

### Performance Considerations

- **Total scrape time**: Target < 30 seconds per game
- **Network timeout**: 60 seconds for page load
- **Element timeout**: 5 seconds for element visibility
- **Retry delays**: 1s, 2s, 4s (exponential backoff)

### Browser Stealth

Maintain existing stealth configuration:
- Disable webdriver flag
- Set realistic user agent
- Set Australian locale/timezone
- Add realistic browser headers
