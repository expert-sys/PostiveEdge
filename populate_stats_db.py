
"""
Populate Stats Database
=======================
Standalone script to:
1. Extract Databallr stats for each player (Game Logs)
2. Extract StatMuse team stats for every team
3. Upload to SQLite database (data/nba_stats.db)

Usage:
    python populate_stats_db.py
"""

import sys
import os
import sqlite3
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import scrapers
from scrapers.statmuse_scraper_v2 import scrape_team_stats, TeamStats
from scrapers.statmuse_team_ids import TEAM_STATMUSE_MAPPING
from scrapers.databallr_scraper import get_player_game_log, GameLogEntry
from build_databallr_player_cache import load_player_ids_file, extract_player_from_url

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("db_population.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("db_populator")

DB_PATH = Path("data/nba_stats.db")

def setup_db():
    """Initialize SQLite database and schema"""
    logger.info(f"Setting up database at {DB_PATH}...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Teams Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        team_id TEXT PRIMARY KEY,
        team_name TEXT NOT NULL,
        statmuse_slug TEXT,
        statmuse_id TEXT,
        last_updated TIMESTAMP
    )
    """)
    
    # 2. Team Stats Table (StatMuse)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS team_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id TEXT,
        season TEXT,
        gp INTEGER,
        points REAL,
        rebounds REAL,
        assists REAL,
        steals REAL,
        blocks REAL,
        turnovers REAL,
        fg_pct REAL,
        three_pct REAL,
        ft_pct REAL,
        collected_at TIMESTAMP,
        FOREIGN KEY(team_id) REFERENCES teams(team_id),
        UNIQUE(team_id, season)
    )
    """)
    
    # 3. Players Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        player_id INTEGER PRIMARY KEY,
        player_name TEXT NOT NULL,
        databallr_url TEXT,
        last_updated TIMESTAMP
    )
    """)
    
    # 4. Player Game Logs Table (DataBallr)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_game_logs (
        game_id TEXT PRIMARY KEY,
        player_id INTEGER,
        game_date DATE,
        matchup TEXT,
        result TEXT,
        minutes REAL,
        points INTEGER,
        rebounds INTEGER,
        assists INTEGER,
        steals INTEGER,
        blocks INTEGER,
        turnovers INTEGER,
        fg_made INTEGER,
        three_pt_made INTEGER,
        ft_made INTEGER,
        plus_minus INTEGER,
        FOREIGN KEY(player_id) REFERENCES players(player_id)
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database setup complete.")

def process_teams(season="2025-26"):
    """Scrape StatMuse for all teams"""
    logger.info("="*60)
    logger.info("PROCESSING TEAMS (STATMUSE)")
    logger.info("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total = len(TEAM_STATMUSE_MAPPING)
    
    for i, (team_name, info) in enumerate(TEAM_STATMUSE_MAPPING.items(), 1):
        slug = info['slug']
        statmuse_id = info['id']
        logger.info(f"[{i}/{total}] Scraping {team_name}...")
        
        # 1. Insert/Update Team Info
        cursor.execute("""
        INSERT OR REPLACE INTO teams (team_id, team_name, statmuse_slug, statmuse_id, last_updated)
        VALUES (?, ?, ?, ?, ?)
        """, (slug, team_name, slug, statmuse_id, datetime.now()))
        conn.commit()
        
        # 2. Scrape Stats
        try:
            stats = scrape_team_stats(slug, season=season, headless=True)
            
            if stats:
                cursor.execute("""
                INSERT OR REPLACE INTO team_stats 
                (team_id, season, gp, points, rebounds, assists, steals, blocks, turnovers, fg_pct, three_pct, ft_pct, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    slug, season, stats.games_played, stats.points, stats.rebounds, 
                    stats.assists, stats.steals, stats.blocks, stats.turnovers,
                    stats.fg_pct, stats.three_pct, stats.ft_pct, datetime.now()
                ))
                conn.commit()
                logger.info(f"  ✓ Saved stats: {stats.points} PPG, {stats.rebounds} RPG")
            else:
                logger.warning(f"  FAILED to scrape stats for {team_name}")
                
        except Exception as e:
            logger.error(f"  Error processing {team_name}: {e}")
            
        time.sleep(2)  # Generous rate limiting
        
    conn.close()

def process_players(season="2024-25"):
    """Scrape DataBallr for all players in PlayerIDs.txt"""
    logger.info("="*60)
    logger.info("PROCESSING PLAYERS (DATABALLR)")
    logger.info("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Load players
    urls = load_player_ids_file()
    total = len(urls)
    logger.info(f"Found {total} players to process.")
    
    for i, url in enumerate(urls, 1):
        try:
            player_info = extract_player_from_url(url) # Returns (name, id)
            if not player_info:
                logger.warning(f"[{i}/{total}] Invalid URL: {url}")
                continue
                
            player_name, player_id = player_info
            logger.info(f"[{i}/{total}] Processing {player_name} (ID: {player_id})...")
            
            # 1. Insert/Update Player
            cursor.execute("""
            INSERT OR REPLACE INTO players (player_id, player_name, databallr_url, last_updated)
            VALUES (?, ?, ?, ?)
            """, (player_id, player_name, url, datetime.now()))
            conn.commit()
            
            # 2. Scrape Game Log
            # Use databallr_scraper directly
            logs = get_player_game_log(
                player_name, 
                season=season, 
                last_n_games=82, # Get full season
                use_cache=False, # Force fresh scrape
                headless=True
            )
            
            if logs:
                saved_count = 0
                for log in logs:
                    cursor.execute("""
                    INSERT OR REPLACE INTO player_game_logs 
                    (game_id, player_id, game_date, matchup, result, minutes, points, rebounds, assists, 
                     steals, blocks, turnovers, fg_made, three_pt_made, ft_made, plus_minus)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        log.game_id, player_id, log.game_date, log.matchup, 
                        "W" if log.won else "L", log.minutes, log.points, log.rebounds, log.assists,
                        log.steals, log.blocks, log.turnovers, log.fg_made, log.three_pt_made,
                        log.ft_made, log.plus_minus
                    ))
                    saved_count += 1
                
                conn.commit()
                logger.info(f"  ✓ Saved {saved_count} game logs")
            else:
                logger.warning(f"  No logs found for {player_name}")
                
        except Exception as e:
            logger.error(f"  Error processing {url}: {e}")
            
        time.sleep(2) # Rate limiting
        
    conn.close()

def main():
    print("\nStarting Stats DB Population...")
    print(f"Database: {DB_PATH}")
    print("This may take a while depending on the number of players/teams.\n")
    
    try:
        setup_db()
        
        # Ask user what to process
        print("Select mode:")
        print("1. All (Teams + Players)")
        print("2. Teams Only (StatMuse)")
        print("3. Players Only (DataBallr)")
        choice = input("Choice (1-3): ").strip()
        
        if choice in ['1', '2']:
            process_teams(season="2025-26")
            
        if choice in ['1', '3']:
            process_players(season="2024-25")
            
        print("\nDONE! Database population complete.")
        print(f"Log saved to db_population.log")
        
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
