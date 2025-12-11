"""
Daily Sportsbet Analysis
========================
Combines:
1. Sportsbet Enhanced Scraper (Real-time odds + insights)
2. Database (Historical player stats)
3. Projection Model (EV calculation)

Usage:
    python daily_sportsbet_analysis.py
"""

import sys
import os
import sqlite3
import logging
import time
import random
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the working enhanced scraper
from scrapers.sportsbet_final_enhanced import (
    scrape_match_complete,
    CompleteMatchData,
    MatchInsight,
    InsightCard
)

# Import projection model
from scrapers.player_projection_model import PlayerProjectionModel
from scrapers.nba_stats_api_scraper import GameLogEntry

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("daily_analysis.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("daily_analysis")

DB_PATH = Path("data/nba_stats.db")

class DailyAnalysisEngine:
    """
    Daily analysis engine that scrapes Sportsbet and validates insights
    against database projections.
    """
    
    def __init__(self):
        self.db_conn = sqlite3.connect(DB_PATH)
        self.db_conn.row_factory = sqlite3.Row
        self.projection_model = PlayerProjectionModel()
        
    def get_player_logs(self, player_name: str, limit: int = 20) -> List[GameLogEntry]:
        """Fetch game logs for a player from DB"""
        cursor = self.db_conn.cursor()
        
        # Fuzzy match player name
        cursor.execute(
            "SELECT player_id, player_name FROM players WHERE player_name LIKE ?",
            (f"%{player_name}%",)
        )
        matches = cursor.fetchall()
        
        if not matches:
            return []
            
        # Use first match
        player_id = matches[0]['player_id']
        actual_name = matches[0]['player_name']
        
        cursor.execute("""
            SELECT * FROM player_game_logs 
            WHERE player_id = ? 
            ORDER BY game_date DESC
            LIMIT ?
        """, (player_id, limit))
        
        rows = cursor.fetchall()
        logs = []
        
        for row in rows:
            # Convert DB row to GameLogEntry
            log = GameLogEntry(
                game_id=row['game_id'],
                game_date=row['game_date'],
                matchup=row['matchup'],
                wl=row['result'],
                minutes=row['minutes'],
                pts=row['points'],
                reb=row['rebounds'],
                ast=row['assists'],
                stl=row['steals'],
                blk=row['blocks'],
                tov=row['turnovers'],
                fg3m=row['three_pt_made'],
                team_id=0,
                player_id=player_id,
                player_name=actual_name
            )
            logs.append(log)
            
        return logs

    def parse_insight(self, insight_text: str) -> Optional[Dict]:
        """
        Parse insight text to extract player, stat, and threshold.
        Example: "LeBron James has scored 25+ points in his last 5 games"
        """
        # 1. Detect Stat Type
        stat_map = {
            "points": ["points", "scored", "pts", "point"],
            "rebounds": ["rebounds", "boards", "rebs", "rebound"],
            "assists": ["assists", "dimes", "ast", "assist"],
            "three_pt_made": ["threes", "3-pointers", "3pt", "three-pointer"],
            "blocks": ["blocks", "blks", "block"],
            "steals": ["steals", "stls", "steal"]
        }
        
        found_stat = None
        for stat, keywords in stat_map.items():
            if any(k in insight_text.lower() for k in keywords):
                found_stat = stat
                break
                
        if not found_stat:
            return None
            
        # 2. Detect Threshold (Number)
        number_match = re.search(r'(\d+\.?\d*)\+?', insight_text)
        if not number_match:
            return None
            
        threshold = float(number_match.group(1))
        
        return {
            "stat_type": found_stat,
            "threshold": threshold,
            "raw_text": insight_text
        }

    def extract_player_name_from_text(self, text: str) -> Optional[str]:
        """
        Extract player name from insight text.
        This is heuristic - assumes "FirstName LastName" at start.
        """
        words = text.split()
        if len(words) < 2:
            return None
        
        # Try first two words (common pattern)
        potential_name = f"{words[0]} {words[1]}"
        
        # Clean punctuation
        potential_name = potential_name.replace("'s", "").strip(".,!?;:")
        
        return potential_name

    def analyze_match(self, match_url: str):
        """Analyze a single match"""
        logger.info(f"Analyzing match: {match_url}")
        
        try:
            # Scrape match using the enhanced scraper
            match_data: CompleteMatchData = scrape_match_complete(match_url, headless=True)
            
            if not match_data:
                logger.error("Failed to scrape match data")
                return
                
            # Display header
            header = f" {match_data.away_team} @ {match_data.home_team} "
            print(f"\n{'='*70}")
            print(header.center(70))
            print('='*70)
            
            # Process Match Insights (JSON-extracted)
            if match_data.match_insights:
                print(f"\n📊 Found {len(match_data.match_insights)} Match Insights (JSON)")
                
                for insight in match_data.match_insights:
                    self._process_match_insight(insight, match_data)
            
            # Process Insight Cards (DOM-extracted)
            if match_data.insight_cards:
                print(f"\n💡 Found {len(match_data.insight_cards)} Insight Cards (DOM)")
                
                for card in match_data.insight_cards:
                    self._process_insight_card(card, match_data)
                    
        except Exception as e:
            logger.error(f"Error analyzing match: {e}", exc_info=True)

    def _process_match_insight(self, insight: MatchInsight, match_data: CompleteMatchData):
        """Process a JSON-extracted MatchInsight"""
        text = insight.fact
        
        # Parse
        parsed = self.parse_insight(text)
        if not parsed:
            return
            
        # Extract player name
        player_name = self.extract_player_name_from_text(text)
        if not player_name:
            return
        
        # Get logs
        logs = self.get_player_logs(player_name)
        
        if not logs:
            # Try with cleaned name
            player_name = player_name.replace("'s", "")
            logs = self.get_player_logs(player_name)
        
        if not logs:
            return
            
        actual_player_name = logs[0].player_name
        
        # Run Projection
        print(f"  🔍 {actual_player_name}: {parsed['stat_type']} > {parsed['threshold']}")
        
        try:
            proj = self.projection_model.project_stat(
                player_name=actual_player_name,
                stat_type=parsed['stat_type'],
                game_log=logs,
                prop_line=parsed['threshold'],
                min_games=5
            )
            
            if proj:
                # Display Result
                ev_diff = proj.expected_value - parsed['threshold']
                ev_color = "\033[92m" if ev_diff > 0 else "\033[91m"
                reset = "\033[0m"
                
                print(f"     Insight: {text}")
                print(f"     Model:   {ev_color}{proj.expected_value:.1f}{reset} EV")
                print(f"     Prob:    {proj.probability_over_line:.1%}")
                
                if proj.probability_over_line > 0.6 and ev_diff > 0:
                    print(f"     \033[93m⭐ HIGH VALUE ⭐\033[0m")
                    
        except Exception as e:
            logger.debug(f"Error projecting {actual_player_name}: {e}")

    def _process_insight_card(self, card: InsightCard, match_data: CompleteMatchData):
        """Process a DOM-extracted InsightCard"""
        text = card.description
        
        # Parse
        parsed = self.parse_insight(text)
        if not parsed:
            return
            
        # If card has player field, use it; otherwise extract
        player_name = card.player if card.player else self.extract_player_name_from_text(text)
        
        if not player_name:
            return
        
        # Get logs
        logs = self.get_player_logs(player_name)
        
        if not logs:
            player_name = player_name.replace("'s", "")
            logs = self.get_player_logs(player_name)
        
        if not logs:
            return
            
        actual_player_name = logs[0].player_name
        
        # Run Projection
        print(f"  💡 {card.title}")
        print(f"     Player: {actual_player_name}, Stat: {parsed['stat_type']} > {parsed['threshold']}")
        
        try:
            proj = self.projection_model.project_stat(
                player_name=actual_player_name,
                stat_type=parsed['stat_type'],
                game_log=logs,
                prop_line=parsed['threshold'],
                min_games=5
            )
            
            if proj:
                ev_diff = proj.expected_value - parsed['threshold']
                ev_color = "\033[92m" if ev_diff > 0 else "\033[91m"
                reset = "\033[0m"
                
                print(f"     Model: {ev_color}{proj.expected_value:.1f}{reset} (Prob: {proj.probability_over_line:.1%})")
                
                if proj.probability_over_line > 0.6 and ev_diff > 0:
                    print(f"     \033[93m⭐ HIGH VALUE ⭐\033[0m")
                    
        except Exception as e:
            logger.debug(f"Error projecting {actual_player_name}: {e}")

    def run(self):
        """Main execution"""
        try:
            print("\n" + "="*70)
            print("DAILY SPORTSBET ANALYSIS - INSIGHT VALIDATOR")
            print("="*70)
            
            # Get match URL from user
            match_url = input("\nEnter Sportsbet match URL: ").strip()
            
            if not match_url:
                logger.error("No URL provided")
                return
                
            # Analyze the match
            self.analyze_match(match_url)
            
            print("\n" + "="*70)
            print("ANALYSIS COMPLETE")
            print("="*70)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            if self.db_conn:
                self.db_conn.close()

if __name__ == "__main__":
    engine = DailyAnalysisEngine()
    engine.run()
