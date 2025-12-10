
"""
Sync to Supabase
================
Uploads local SQLite stats to Supabase Postgres database.
"""

import os
import sys
import sqlite3
import psycopg2
import logging
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("supabase_sync")

# Load environment variables
load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")
LOCAL_DB = "data/nba_stats.db"

def get_postgres_connection():
    try:
        if not DB_URL:
            logger.error("SUPABASE_DB_URL not found in .env")
            return None
        return psycopg2.connect(DB_URL)
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        return None

def create_tables(pg_conn):
    """Create PostgreSQL tables if they don't exist"""
    cursor = pg_conn.cursor()
    
    logger.info("Verifying/Creating tables in Supabase...")
    
    # Teams
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        team_id TEXT PRIMARY KEY,
        team_name TEXT NOT NULL,
        statmuse_slug TEXT,
        statmuse_id TEXT,
        last_updated TIMESTAMP
    );
    """)
    
    # Team Stats
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS team_stats (
        id SERIAL PRIMARY KEY,
        team_id TEXT REFERENCES teams(team_id),
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
        UNIQUE(team_id, season)
    );
    """)
    
    # Players
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        player_id INTEGER PRIMARY KEY,
        player_name TEXT NOT NULL,
        databallr_url TEXT,
        last_updated TIMESTAMP
    );
    """)
    
    # Game Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_game_logs (
        game_id TEXT PRIMARY KEY,
        player_id INTEGER REFERENCES players(player_id),
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
        plus_minus INTEGER
    );
    """)
    
    pg_conn.commit()
    logger.info("Tables synced.")

def sync_data():
    if not os.path.exists(LOCAL_DB):
        logger.error(f"Local database not found at {LOCAL_DB}")
        return

    pg_conn = get_postgres_connection()
    if not pg_conn:
        return
        
    try:
        create_tables(pg_conn)
        
        sqlite_conn = sqlite3.connect(LOCAL_DB)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()
        
        # 1. Sync Teams
        logger.info("Syncing Teams...")
        sqlite_cursor.execute("SELECT * FROM teams")
        teams = [dict(row) for row in sqlite_cursor.fetchall()]
        if teams:
            execute_values(pg_cursor, """
                INSERT INTO teams (team_id, team_name, statmuse_slug, statmuse_id, last_updated)
                VALUES %s
                ON CONFLICT (team_id) DO UPDATE SET
                    team_name = EXCLUDED.team_name,
                    last_updated = EXCLUDED.last_updated
            """, [(t['team_id'], t['team_name'], t['statmuse_slug'], t['statmuse_id'], t['last_updated']) for t in teams])
            
        # 2. Sync Team Stats
        logger.info("Syncing Team Stats...")
        sqlite_cursor.execute("SELECT * FROM team_stats")
        stats = [dict(row) for row in sqlite_cursor.fetchall()]
        if stats:
            # Note: SERIAL id is ignored on insert unless specified, but we have UNIQUE constraint
            execute_values(pg_cursor, """
                INSERT INTO team_stats (team_id, season, gp, points, rebounds, assists, steals, blocks, turnovers, fg_pct, three_pct, ft_pct, collected_at)
                VALUES %s
                ON CONFLICT (team_id, season) DO UPDATE SET
                    points = EXCLUDED.points,
                    collected_at = EXCLUDED.collected_at
            """, [(s['team_id'], s['season'], s['gp'], s['points'], s['rebounds'], s['assists'], 
                   s['steals'], s['blocks'], s['turnovers'], s['fg_pct'], s['three_pct'], s['ft_pct'], s['collected_at']) for s in stats])

        # 3. Sync Players
        logger.info("Syncing Players...")
        sqlite_cursor.execute("SELECT * FROM players")
        players = [dict(row) for row in sqlite_cursor.fetchall()]
        if players:
            execute_values(pg_cursor, """
                INSERT INTO players (player_id, player_name, databallr_url, last_updated)
                VALUES %s
                ON CONFLICT (player_id) DO UPDATE SET
                    player_name = EXCLUDED.player_name,
                    last_updated = EXCLUDED.last_updated
            """, [(p['player_id'], p['player_name'], p['databallr_url'], p['last_updated']) for p in players])

        # 4. Sync Game Logs (Chunked)
        logger.info("Syncing Game Logs (this may take time)...")
        sqlite_cursor.execute("SELECT count(*) as count FROM player_game_logs")
        total_logs = sqlite_cursor.fetchone()['count']
        logger.info(f"  Found {total_logs} logs to sync.")
        
        batch_size = 500
        processed = 0
        sqlite_cursor.execute("SELECT * FROM player_game_logs")
        
        while True:
            batch = sqlite_cursor.fetchmany(batch_size)
            if not batch:
                break
            
            rows = [dict(row) for row in batch]
            execute_values(pg_cursor, """
                INSERT INTO player_game_logs (
                    game_id, player_id, game_date, matchup, result, minutes, 
                    points, rebounds, assists, steals, blocks, turnovers, 
                    fg_made, three_pt_made, ft_made, plus_minus
                )
                VALUES %s
                ON CONFLICT (game_id) DO NOTHING
            """, [(
                r['game_id'], r['player_id'], r['game_date'], r['matchup'], r['result'], r['minutes'],
                r['points'], r['rebounds'], r['assists'], r['steals'], r['blocks'], r['turnovers'],
                r['fg_made'], r['three_pt_made'], r['ft_made'], r['plus_minus']
            ) for r in rows])
            
            processed += len(rows)
            logger.info(f"  Synced {processed}/{total_logs}...")
            
        pg_conn.commit()
        logger.info("Sync Complete!")
        
    except Exception as e:
        pg_conn.rollback()
        logger.error(f"Sync failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pg_conn.close()
        sqlite_conn.close()

if __name__ == "__main__":
    sync_data()
