# Multi-Model Sports Value Engine

A sharp betting system that runs 5 independent projection paths and combines them intelligently.

## 🌟 The 5 Models

### 🔵 Model 1: Deterministic (Usage × Minutes)
**Weight: 45%**
A structured, physics-like model.
`Projection = Minutes × Usage × Pace × Opponent Modifier`
- **Strengths:** Transparent, stable, easy to debug.
- **Weaknesses:** Struggles with role changes and hot/cold streaks.

### 🟢 Model 2: Empirical (Rolling Distribution)
**Weight: 25%**
Calculates how often the player beats the line historically under similar conditions (Minutes, etc.).
- **Strengths:** Reality-grounded, no distribution assumptions.
- **Weaknesses:** Sample-size sensitive.

### 🟡 Model 3: Regression-Based Expectation
**Weight: 20%**
A statistical model mapping inputs (Minutes, Home/Away, Rest) to output using Linear Regression.
- **Strengths:** Captures interactions, adjusts for context.
- **Weaknesses:** Needs clean historical data.

### 🔴 Model 4: Market-Implied Reverse Model
**Weight: 10%**
Infers the market's "True Mean" from the odds and line.
- **Strengths:** Market-aware, excellent "Disagreement Detector".
- **Weaknesses:** Cannot generate bets alone.

### 🟣 Model 5: Bayesian Update
**Weight: 5%**
Updates a long-term prior (Season Avg) with recent evidence (Last 5 Games).
- **Strengths:** Handles uncertainty, smooth transitions.
- **Weaknesses:** Complex to tune.

## 🧮 Combination Logic

The engine uses a **Weighted + Disagreement Aware** approach.
1. Calculates weighted average of all models.
2. measures **Disagreement Level** (Std Dev / Mean).
3. If Disagreement > 10%, **Confidence is reduced**.
4. Checks if "Fighting the Market" (Model vs Market > 15% diff).

## 🚀 Usage

### Running the Demo
```bash
./run_multi_model.bat
```

### Integration
To use in your pipeline:

```python
from multi_model_engine.engine import MultiModelEngine
from multi_model_engine.domain import ModelInput, GameLogEntry

# Initialize
engine = MultiModelEngine()

# Prepare Input
input_data = ModelInput(
    player_name="LeBron James",
    stat_type="points",
    line=24.5,
    game_log=[...], # List of GameLogEntry
    opponent="BOS",
    is_home=True,
    minutes_projected=34.0,
    market_odds=1.85
)

# Analyze
result = engine.analyze(input_data)

print(f"Projection: {result.final_projection}")
print(f"Bet? {result.is_bet}")
```
