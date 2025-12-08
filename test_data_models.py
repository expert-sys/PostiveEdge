"""
Test the new data models to ensure they work correctly
"""
from scrapers.sportsbet_final_enhanced import (
    SeasonGameResult,
    QuarterScores,
    HeadToHeadGame,
    TeamInsights
)
import json

print("=" * 80)
print("Testing New Data Models")
print("=" * 80)

# Test SeasonGameResult
print("\n1. Testing SeasonGameResult...")
season_game = SeasonGameResult(
    opponent="TOR",
    date="04/12/25",
    score_for=123,
    score_against=120,
    result="W",
    is_home=False
)
print(f"   ✓ Created: {season_game.opponent} {season_game.date} {season_game.score_for}-{season_game.score_against} ({season_game.result})")

# Test QuarterScores
print("\n2. Testing QuarterScores...")
quarter_scores = QuarterScores(
    q1=33,
    q2=21,
    q3=13,
    q4=34,
    final=101
)
print(f"   ✓ Created: Q1={quarter_scores.q1} Q2={quarter_scores.q2} Q3={quarter_scores.q3} Q4={quarter_scores.q4} Final={quarter_scores.final}")

# Test with overtime
quarter_scores_ot = QuarterScores(
    q1=27,
    q2=27,
    q3=27,
    q4=24,
    final=121,
    ot=16
)
print(f"   ✓ Created with OT: Q1={quarter_scores_ot.q1} Q2={quarter_scores_ot.q2} Q3={quarter_scores_ot.q3} Q4={quarter_scores_ot.q4} OT={quarter_scores_ot.ot} Final={quarter_scores_ot.final}")

# Test HeadToHeadGame
print("\n3. Testing HeadToHeadGame...")
h2h_game = HeadToHeadGame(
    date="Sat 8 Mar 2025",
    venue="TD Garden",
    away_team="LAL",
    home_team="BOS",
    away_scores=quarter_scores,
    home_scores=QuarterScores(q1=33, q2=25, q3=29, q4=24, final=111),
    away_result="L",
    home_result="W"
)
print(f"   ✓ Created: {h2h_game.date} at {h2h_game.venue}")
print(f"     {h2h_game.away_team} {h2h_game.away_scores.final} ({h2h_game.away_result}) vs {h2h_game.home_team} {h2h_game.home_scores.final} ({h2h_game.home_result})")

# Test TeamInsights
print("\n4. Testing TeamInsights...")
team_insights = TeamInsights(
    away_team="Los Angeles Lakers",
    home_team="Boston Celtics",
    away_season_results=[season_game],
    home_season_results=[
        SeasonGameResult(
            opponent="WAS",
            date="04/12/25",
            score_for=146,
            score_against=101,
            result="W",
            is_home=False
        )
    ],
    head_to_head=[h2h_game]
)
print(f"   ✓ Created TeamInsights:")
print(f"     Away team: {team_insights.away_team} ({len(team_insights.away_season_results)} games)")
print(f"     Home team: {team_insights.home_team} ({len(team_insights.home_season_results)} games)")
print(f"     H2H games: {len(team_insights.head_to_head)}")

# Test JSON serialization
print("\n5. Testing JSON serialization...")
insights_dict = team_insights.to_dict()
json_str = json.dumps(insights_dict, indent=2)
print("   ✓ Successfully serialized to JSON")
print(f"   JSON length: {len(json_str)} characters")

# Test deserialization
print("\n6. Testing JSON deserialization...")
restored = json.loads(json_str)
print("   ✓ Successfully deserialized from JSON")
print(f"   Restored away_team: {restored['away_team']}")
print(f"   Restored home_team: {restored['home_team']}")
print(f"   Restored away games: {len(restored['away_season_results'])}")
print(f"   Restored home games: {len(restored['home_season_results'])}")
print(f"   Restored H2H games: {len(restored['head_to_head'])}")

# Save sample output
with open("sample_team_insights.json", "w") as f:
    f.write(json_str)
print("\n   ✓ Sample output saved to: sample_team_insights.json")

print("\n" + "=" * 80)
print("✓ All data model tests passed!")
print("=" * 80)
