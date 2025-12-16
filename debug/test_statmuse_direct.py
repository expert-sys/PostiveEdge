import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.statmuse_player_scraper import scrape_player_game_log
import logging

logging.basicConfig(level=logging.INFO)

def test():
    player = "Jaime Jaquez Jr."
    print(f"Testing StatMuse scraper for {player}...")
    logs = scrape_player_game_log(player, headless=False) # Headless False to see
    
    if logs:
        print(f"SUCCESS: Got {len(logs)} games")
        print("First game:", logs[0])
    else:
        print("FAILURE: No logs returned")

if __name__ == "__main__":
    test()
