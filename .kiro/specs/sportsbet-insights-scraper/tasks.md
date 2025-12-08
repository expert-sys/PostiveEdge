# Implementation Plan

- [ ] 1. Create new data models for team insights






  - Add `SeasonGameResult` dataclass with fields: opponent, date, score_for, score_against, result, is_home
  - Add `QuarterScores` dataclass with fields: q1, q2, q3, q4, ot (optional), final
  - Add `HeadToHeadGame` dataclass with fields: date, venue, away_team, home_team, away_scores, home_scores, away_result, home_result
  - Add `TeamInsights` dataclass with fields: away_team, home_team, away_season_results, home_season_results, head_to_head
  - Implement `to_dict()` method for `TeamInsights` to support JSON serialization
  - _Requirements: 3.1, 3.2, 3.3_

- [ ]* 1.1 Write property test for JSON serialization round-trip
  - **Property 8: JSON Serialization Round-Trip**
  - **Validates: Requirements 3.1**

- [x] 2. Implement UI interaction helper functions


  - Create `click_team_toggle(page, team_name)` function with multiple selector fallbacks
  - Create `click_more_button(page, section_name)` function to expand content sections
  - Implement wait conditions after each click (1-2 seconds)
  - Add error handling and logging for failed interactions
  - _Requirements: 4.1, 4.2, 4.3_

- [ ]* 2.1 Write property test for content expansion
  - **Property 3: Content Expansion**
  - **Validates: Requirements 1.3, 2.2**

- [x] 3. Implement season results extraction function


  - Create `extract_season_results(page, away_team, home_team)` function
  - Locate "2025/26 Season Results" section using multiple selector patterns
  - Click away team toggle button
  - Click "More" button to expand all games
  - Extract game data: opponent abbreviation, date, score, W/L, home/away indicator
  - Parse score strings (e.g., "123-120") into separate integers
  - Determine home/away from icon presence
  - Click home team toggle button
  - Click "More" button again
  - Extract home team game data
  - Return tuple of (away_results, home_results) as lists of `SeasonGameResult` objects
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.1_

- [ ]* 3.1 Write property test for dual team extraction
  - **Property 2: Dual Team Extraction**
  - **Validates: Requirements 1.2**

- [ ]* 3.2 Write property test for complete game data
  - **Property 4: Complete Game Data**
  - **Validates: Requirements 1.4**

- [x] 4. Implement head-to-head extraction function


  - Create `extract_head_to_head(page, away_team, home_team)` function
  - Locate "Last 5 Head to Head" section using multiple selector patterns
  - Click "More" button to expand all matchups
  - For each game row, extract: date, venue, Q1-Q4 scores for both teams, OT if present, final scores
  - Parse quarter score tables to associate scores with correct teams
  - Determine W/L for each team based on final scores
  - Create `QuarterScores` objects for each team
  - Return list of `HeadToHeadGame` objects
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.2_

- [ ]* 4.1 Write property test for complete H2H data
  - **Property 5: Complete H2H Data**
  - **Validates: Requirements 2.3**

- [ ]* 4.2 Write property test for team-quarter association integrity
  - **Property 7: Team-Quarter Association Integrity**
  - **Validates: Requirements 2.4**

- [x] 5. Implement data validation functions


  - Create `validate_score(score)` function to check numeric range (0-200)
  - Create `validate_date(date_str, format_type)` function to check format patterns
  - Create `validate_team_abbrev(abbrev)` function to check length (2-4 chars)
  - Create `validate_result(result)` function to check W/L values
  - Add validation calls in extraction functions
  - Log warnings for validation failures and set fields to null
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 5.1 Write property test for numeric score validation
  - **Property 12: Numeric Score Validation**
  - **Validates: Requirements 5.1**

- [ ]* 5.2 Write property test for date format validation
  - **Property 13: Date Format Validation**
  - **Validates: Requirements 5.2**

- [ ]* 5.3 Write property test for abbreviation validation
  - **Property 14: Abbreviation Length Validation**
  - **Validates: Requirements 5.3**

- [ ]* 5.4 Write property test for win/loss validation
  - **Property 15: Win/Loss Binary Validation**
  - **Validates: Requirements 5.4**

- [x] 6. Integrate insights extraction into main scraper


  - Modify `scrape_match_complete()` function to call new extraction functions
  - After clicking Stats & Insights tab, call `extract_season_results()`
  - Call `extract_head_to_head()` after season results
  - Create `TeamInsights` object with extracted data
  - Add `team_insights` field to `CompleteMatchData` dataclass
  - Update `CompleteMatchData.to_dict()` to include team insights
  - _Requirements: 1.5, 2.5, 3.2, 3.3, 3.4, 3.5_

- [ ]* 6.1 Write property test for structural correctness
  - **Property 9: Structural Correctness**
  - **Validates: Requirements 3.2, 3.3**

- [ ]* 6.2 Write property test for team identifier consistency
  - **Property 10: Team Identifier Consistency**
  - **Validates: Requirements 3.4**

- [ ]* 6.3 Write property test for chronological ordering
  - **Property 6: Chronological Ordering**
  - **Validates: Requirements 1.5, 2.5**

- [x] 7. Implement error handling and retry logic


  - Add try-catch blocks around each extraction function
  - Implement exponential backoff retry logic (1s, 2s, 4s) for network errors
  - Add `extraction_errors` list to output for tracking failures
  - Ensure partial data is returned when some components fail
  - Log all errors with appropriate context and severity
  - _Requirements: 4.4, 4.5, 5.5_

- [ ]* 7.1 Write property test for graceful error handling
  - **Property 18: Graceful Error Handling**
  - **Validates: Requirements 4.4, 5.5**

- [x] 8. Add robust selector patterns

  - Define multiple fallback selectors for Season Results section
  - Define multiple fallback selectors for Head to Head section
  - Define multiple fallback selectors for team toggle buttons
  - Define multiple fallback selectors for More buttons
  - Implement selector iteration logic to try each pattern until one succeeds
  - _Requirements: 1.1, 2.1, 4.1_

- [ ]* 8.1 Write property test for component identification
  - **Property 1: Component Identification**
  - **Validates: Requirements 1.1, 2.1**

- [x] 9. Update wait strategies for dynamic content

  - Add 3-5 second wait after clicking Stats & Insights tab
  - Add 1-2 second wait after clicking team toggle
  - Add 1-2 second wait after clicking More button
  - Implement visibility checks before extraction
  - Add scroll actions to ensure sections are in viewport
  - _Requirements: 4.2, 4.3_

- [x] 10. Add perspective consistency logic

  - Ensure score_for always represents the team being analyzed
  - Ensure score_against always represents the opponent
  - Maintain consistent home/away labeling across both teams
  - Verify perspective is correct when switching between team toggles
  - _Requirements: 6.3, 6.4, 6.5_

- [ ]* 10.1 Write property test for perspective consistency
  - **Property 17: Perspective Consistency**
  - **Validates: Requirements 6.4**

- [x] 11. Checkpoint - Ensure all tests pass



  - Ensure all tests pass, ask the user if questions arise.
