
import sqlite3
import os

try:
    if os.path.exists('data/nba_stats.db'):
        conn = sqlite3.connect('data/nba_stats.db')
        c = conn.cursor()
        
        # Check tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        print(f"Tables: {tables}")
        
        for table in tables:
            t = table[0]
            c.execute(f"SELECT count(*) FROM {t}")
            count = c.fetchone()[0]
            print(f"Table '{t}' has {count} rows")
            
        conn.close()
    else:
        print("data/nba_stats.db not found")
except Exception as e:
    print(f"Error: {e}")
