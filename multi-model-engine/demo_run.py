import datetime
import random
from typing import List

from domain import GameLogEntry, ModelInput
from engine import MultiModelEngine

def create_mock_gamelog(player_name: str, n_games: int = 50) -> List[GameLogEntry]:
    logs = []
    base_date = datetime.datetime.now()
    
    # Mock consistent player (e.g. 25 pts avg)
    mu = 25
    sigma = 5
    
    for i in range(n_games):
        # Random gap between games (1-4 days)
        gap = random.randint(1, 4)
        base_date = base_date - datetime.timedelta(days=gap)
        date = base_date
        
        mins = random.uniform(30, 38)
        pts = int(random.gauss(mu, sigma) * (mins/34.0)) # Correlate with minutes
        
        entry = GameLogEntry(
            game_date=date.strftime("%Y-%m-%d"),
            game_id=f"GAME_{i}",
            matchup="LAL vs BOS",
            home_away="HOME" if random.random() > 0.5 else "AWAY",
            opponent="BOS",
            opponent_id=1,
            won=random.choice([True, False]),
            minutes=mins,
            points=pts,
            rebounds=random.randint(5, 15),
            assists=random.randint(2, 10),
            steals=random.randint(0, 3),
            blocks=random.randint(0, 2),
            turnovers=random.randint(1, 5),
            fg_made=10, fg_attempted=20,
            three_pt_made=2, three_pt_attempted=6,
            ft_made=3, ft_attempted=4,
            plus_minus=random.randint(-10, 10)
        )
        logs.append(entry)
    return logs

def main():
    print("Initializing Multi-Model Engine...")
    engine = MultiModelEngine()
    
    print("\n--- TEST CASE 1: Standard Star Player (Line 24.5) ---")
    logs = create_mock_gamelog("LeBron James", 50)
    
    # Mock Input
    input_data = ModelInput(
        player_name="LeBron James",
        stat_type="points",
        line=24.5,
        game_log=logs,
        opponent="BOS",
        is_home=True,
        minutes_projected=34.0,
        team_pace=100.0,
        opponent_pace=98.0,
        opponent_def_rating=110.0,
        market_odds=1.85, # Implied prob ~54%
        implied_probability=0.54
    )
    
    result = engine.analyze(input_data)
    
    print(f"Final Projection: {result.final_projection:.2f}")
    print(f"Final Probability: {result.final_probability:.1%}")
    print(f"Confidence: {result.confidence_score:.2f}")
    print(f"Disagreement Level: {result.disagreement_level:.1%}")
    print("\nModel Breakdown:")
    for name, out in result.model_outputs.items():
        print(f"  {name:25s}: Proj {out.expected_value:.1f} | Prob {out.probability_over:.1%} | W {out.weight:.2f}")
        
    print("\nNotes:")
    for note in result.notes:
        print(f"  - {note}")
        
    print("\n\n--- TEST CASE 2: Bench Player / Volatile (Line 12.5) ---")
    # Volatile bench player
    logs_bench = create_mock_gamelog("Bench Guy", 30)
    for g in logs_bench:
        g.minutes = random.uniform(10, 25) # Wildly varying minutes
        g.points = int(g.minutes * 0.5 + random.gauss(0, 3))
        
    input_bench = ModelInput(
        player_name="Bench Guy",
        stat_type="points",
        line=12.5,
        game_log=logs_bench,
        opponent="PHI",
        is_home=False,
        minutes_projected=18.0,
        market_odds=1.91
    )
    
    result_bench = engine.analyze(input_bench)
    print(f"Final Projection: {result_bench.final_projection:.2f}")
    print(f"Disagreement Level: {result_bench.disagreement_level:.1%}")
    print("\nNotes:")
    for note in result_bench.notes:
        print(f"  - {note}")

if __name__ == "__main__":
    main()
