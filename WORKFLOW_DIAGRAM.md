# NBA Betting System - Visual Workflow

## Complete System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                     NBA BETTING SYSTEM                              │
│                  Intelligent Value Finder                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ User runs:
                                │ python nba_betting_system.py
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: SCRAPE SPORTSBET                                           │
│  ═══════════════════════════                                        │
│                                                                     │
│  ┌──────────────┐                                                  │
│  │  Playwright  │  → Navigate to Sportsbet.com.au                  │
│  │   Browser    │  → Find NBA games                                │
│  └──────────────┘  → Extract odds, insights, player props          │
│                                                                     │
│  Output:                                                            │
│  • Game Info: Lakers @ Warriors, 7:30 PM                           │
│  • Team Markets: Spreads, totals, moneylines                       │
│  • Player Props: LeBron 25.5 points @ 1.90                         │
│  • Insights: "LeBron scored 25+ in 13 of last 20"                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: VALIDATE WITH DATABALLR                                    │
│  ════════════════════════════════                                   │
│                                                                     │
│  For each player prop:                                              │
│                                                                     │
│  ┌──────────────┐                                                  │
│  │  DataBallr   │  → Search player: "LeBron James"                 │
│  │   Scraper    │  → Fetch last 20 games                           │
│  └──────────────┘  → Extract stats (points, rebounds, etc.)        │
│                                                                     │
│  ┌──────────────┐                                                  │
│  │  Calculate   │  → Hit Rate: 13/20 = 65%                         │
│  │  Metrics     │  → Average: 27.3 points                          │
│  └──────────────┘  → Trend: Improving (recent avg 28.5)            │
│                                                                     │
│  Validation:                                                        │
│  ✓ Sample Size: 20 games (≥5 required)                             │
│  ✓ Minutes: 35+ per game (≥10 required)                            │
│  ✓ Data Quality: High                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: PROJECT VALUE                                              │
│  ══════════════════                                                 │
│                                                                     │
│  ┌──────────────────┐                                              │
│  │ Projection Model │  → Analyze game log                          │
│  │  (Statistical)   │  → Consider matchup factors                  │
│  └──────────────────┘  → Project probability: 70.3%                │
│                                                                     │
│  ┌──────────────────┐                                              │
│  │ Combine Signals  │  → Model: 70.3% (70% weight)                 │
│  │  (Bayesian)      │  → Historical: 65.0% (30% weight)            │
│  └──────────────────┘  → Final: 68.8%                              │
│                                                                     │
│  ┌──────────────────┐                                              │
│  │ Calculate Value  │  → Implied Prob: 52.6% (from odds 1.90)      │
│  │  (EV & Edge)     │  → Edge: 68.8% - 52.6% = +16.2%              │
│  └──────────────────┘  → EV: +31.4% per $100                       │
│                                                                     │
│  ┌──────────────────┐                                              │
│  │ Confidence Score │  → Base: 75 (from model)                     │
│  │  (Multi-Factor)  │  → Sample boost: +5 (20 games)               │
│  └──────────────────┘  → Edge boost: +5 (16% edge)                 │
│                         → Final: 85% → VERY HIGH                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: FILTER & RANK                                              │
│  ══════════════════                                                 │
│                                                                     │
│  Filters Applied:                                                   │
│  ✓ Confidence ≥ 70%                                                 │
│  ✓ Expected Value > 0                                               │
│  ✓ Sample Size ≥ 5 games                                            │
│  ✓ Max 2 bets per game (correlation control)                        │
│                                                                     │
│  Ranking:                                                           │
│  1. Sort by confidence score (highest first)                        │
│  2. Apply correlation filter                                        │
│  3. Select top recommendations                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  OUTPUT: BETTING RECOMMENDATIONS                                    │
│  ════════════════════════════                                       │
│                                                                     │
│  Console Output:                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 1. LeBron James - Points Over 25.5                          │  │
│  │    Game: Lakers @ Warriors (7:30 PM ET)                     │  │
│  │    Odds: 1.90 | Confidence: 85% | Strength: VERY HIGH       │  │
│  │    Edge: +16.2% | EV: +31.4%                                │  │
│  │    Historical: 65.0% (20 games)                             │  │
│  │    Projected: 68.8%                                         │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  JSON Output (betting_recommendations.json):                        │
│  {                                                                  │
│    "player_name": "LeBron James",                                  │
│    "stat_type": "points",                                          │
│    "line": 25.5,                                                   │
│    "odds": 1.90,                                                   │
│    "confidence_score": 85.0,                                       │
│    "recommendation_strength": "VERY_HIGH",                         │
│    "edge_percentage": 16.2,                                        │
│    "expected_value": 31.4                                          │
│  }                                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌──────────────┐
│  Sportsbet   │
│   Website    │
└──────┬───────┘
       │
       │ Scrape
       ▼
┌──────────────┐      ┌──────────────┐
│ Game Data    │      │  DataBallr   │
│ • Teams      │      │   Website    │
│ • Odds       │      └──────┬───────┘
│ • Props      │             │
└──────┬───────┘             │ Scrape
       │                     ▼
       │              ┌──────────────┐
       │              │ Player Stats │
       │              │ • Game Log   │
       │              │ • Hit Rate   │
       │              │ • Trends     │
       │              └──────┬───────┘
       │                     │
       └─────────┬───────────┘
                 │
                 │ Combine
                 ▼
         ┌───────────────┐
         │  Projection   │
         │    Model      │
         │ • Probability │
         │ • Confidence  │
         └───────┬───────┘
                 │
                 │ Calculate
                 ▼
         ┌───────────────┐
         │ Value Metrics │
         │ • Edge        │
         │ • EV          │
         │ • Confidence  │
         └───────┬───────┘
                 │
                 │ Filter & Rank
                 ▼
         ┌───────────────┐
         │Recommendations│
         │ (Top 5 Bets)  │
         └───────────────┘
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                    NBAbettingPipeline                       │
│                   (Main Orchestrator)                       │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         │ uses               │ uses               │ uses
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ SportsbetCollector│ │DataBallrValidator│ │  ValueProjector  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
         │                    │                    │
         │ uses               │ uses               │ uses
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│sportsbet_scraper │ │databallr_scraper │ │projection_model  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
         │                    │                    │
         │ uses               │ uses               │ uses
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   Playwright     │ │   Playwright     │ │  Statistical     │
│   (Browser)      │ │   (Browser)      │ │   Functions      │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Decision Tree

```
                    Start Analysis
                         │
                         ▼
              ┌──────────────────────┐
              │ Scrape Sportsbet     │
              │ for NBA games        │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Games found?         │
              └──────────┬───────────┘
                    Yes  │  No
                         │  └──→ Exit: No games
                         ▼
              ┌──────────────────────┐
              │ For each player prop │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Fetch DataBallr      │
              │ stats for player     │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Data available?      │
              └──────────┬───────────┘
                    Yes  │  No
                         │  └──→ Skip: No data
                         ▼
              ┌──────────────────────┐
              │ Sample size ≥ 5?     │
              └──────────┬───────────┘
                    Yes  │  No
                         │  └──→ Skip: Insufficient data
                         ▼
              ┌──────────────────────┐
              │ Run projection model │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Model successful?    │
              └──────────┬───────────┘
                    Yes  │  No
                         │  └──→ Skip: Model failed
                         ▼
              ┌──────────────────────┐
              │ Calculate EV & Edge  │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ EV > 0 AND           │
              │ Confidence ≥ 70%?    │
              └──────────┬───────────┘
                    Yes  │  No
                         │  └──→ Skip: Low value
                         ▼
              ┌──────────────────────┐
              │ Add to               │
              │ recommendations      │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ More props?          │
              └──────────┬───────────┘
                    Yes  │  No
                    │    │
                    └────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Rank by confidence   │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Apply correlation    │
              │ filter (max 2/game)  │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Output top           │
              │ recommendations      │
              └──────────────────────┘
```

## Caching Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                      CACHE SYSTEM                           │
└─────────────────────────────────────────────────────────────┘

Player ID Cache (Permanent)
┌──────────────────────────────────────┐
│ databallr_player_cache.json          │
│                                      │
│ {                                    │
│   "lebron james": 2544,              │
│   "stephen curry": 201939,           │
│   ...                                │
│ }                                    │
│                                      │
│ • Built once                         │
│ • Updated manually                   │
│ • Speeds up player lookups           │
└──────────────────────────────────────┘

Stats Cache (24-hour TTL)
┌──────────────────────────────────────┐
│ player_stats_cache.json              │
│                                      │
│ {                                    │
│   "lebron james": {                  │
│     "timestamp": "2024-12-05T10:00", │
│     "game_log": [...],               │
│     "game_count": 20                 │
│   }                                  │
│ }                                    │
│                                      │
│ • Auto-refreshes after 24h           │
│ • Reduces scraping time              │
│ • Improves reliability               │
└──────────────────────────────────────┘

Cache Hit Flow:
┌─────────────┐
│ Need player │
│   stats     │
└──────┬──────┘
       │
       ▼
┌─────────────┐     Yes    ┌─────────────┐
│ In ID cache?├───────────→│ Use cached  │
└──────┬──────┘            │   ID        │
       │ No                └──────┬──────┘
       │                          │
       ▼                          ▼
┌─────────────┐            ┌─────────────┐     Yes    ┌─────────────┐
│ Search      │            │ In stats    ├───────────→│ Use cached  │
│ DataBallr   │            │ cache?      │            │   stats     │
└──────┬──────┘            └──────┬──────┘            └─────────────┘
       │                          │ No
       │                          │
       ▼                          ▼
┌─────────────┐            ┌─────────────┐
│ Save to     │            │ Scrape      │
│ ID cache    │            │ DataBallr   │
└─────────────┘            └──────┬──────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │ Save to     │
                           │ stats cache │
                           └─────────────┘
```

## Error Handling Flow

```
                    Operation
                         │
                         ▼
              ┌──────────────────────┐
              │ Try operation        │
              └──────────┬───────────┘
                         │
                    Success? ──Yes──→ Continue
                         │
                         No
                         │
                         ▼
              ┌──────────────────────┐
              │ Log error            │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Retry count < 3?     │
              └──────────┬───────────┘
                    Yes  │  No
                         │  └──→ Log failure, skip
                         ▼
              ┌──────────────────────┐
              │ Wait (exponential    │
              │ backoff)             │
              └──────────┬───────────┘
                         │
                         └──→ Retry operation
```

## Performance Optimization

```
┌─────────────────────────────────────────────────────────────┐
│                  PERFORMANCE LAYERS                         │
└─────────────────────────────────────────────────────────────┘

Layer 1: Caching
┌──────────────────────────────────────┐
│ • Player ID cache (instant lookup)   │
│ • Stats cache (24h TTL)              │
│ • Reduces scraping by 80%            │
└──────────────────────────────────────┘

Layer 2: Request Throttling
┌──────────────────────────────────────┐
│ • 1 request per second               │
│ • Prevents rate limiting             │
│ • Maintains reliability              │
└──────────────────────────────────────┘

Layer 3: Headless Browser
┌──────────────────────────────────────┐
│ • No GUI rendering                   │
│ • Faster page loads                  │
│ • Lower resource usage               │
└──────────────────────────────────────┘

Layer 4: Smart Filtering
┌──────────────────────────────────────┐
│ • Skip low-confidence bets early     │
│ • Validate sample size first         │
│ • Reduce unnecessary calculations    │
└──────────────────────────────────────┘

Result: 1 game in ~30-60 seconds
```

---

**Visual Guide Version**: 1.0.0  
**Last Updated**: December 2024
