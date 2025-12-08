"""
Main DataballR Robust Scraper
==============================
Unified scraper entry point with CLI interface.
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .core.logs import setup_logging
from .databallr.players import DataballrPlayerScraper
from .storage.save_raw import RawDataStorage
from .storage.save_processed import ProcessedDataStorage

logger = logging.getLogger(__name__)


class DataballrRobustScraper:
    """
    Main scraper orchestrator.
    Coordinates all scraping modules and storage.
    """
    
    def __init__(
        self,
        raw_storage_dir: Path = Path("data/raw"),
        processed_storage_dir: Path = Path("data/processed"),
        log_file: Optional[Path] = None
    ):
        """
        Initialize main scraper.
        
        Args:
            raw_storage_dir: Directory for raw JSON data
            processed_storage_dir: Directory for processed data
            log_file: Optional log file path
        """
        # Setup logging
        setup_logging(log_file=log_file or Path("logs/scraper.log"))
        
        # Initialize components
        self.player_scraper = DataballrPlayerScraper(headless=True)
        self.raw_storage = RawDataStorage(raw_storage_dir)
        self.processed_storage = ProcessedDataStorage(processed_storage_dir, format='parquet')
        
        logger.info("DataballR Robust Scraper initialized")
    
    def scrape_player_stats(
        self,
        player_name: str,
        last_n_games: int = 20,
        save_raw: bool = True,
        save_processed: bool = True,
        date: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Scrape player statistics.
        
        Args:
            player_name: Player name
            last_n_games: Number of games to fetch
            save_raw: Save raw JSON data
            save_processed: Save processed data
            date: Date string for storage organization
        
        Returns:
            Scraped data dict or None if failed
        """
        logger.info(f"Scraping player stats for {player_name}")
        
        try:
            # Scrape data
            games = self.player_scraper.get_player_game_log(player_name, last_n_games)
            
            if not games:
                logger.warning(f"No games found for {player_name}")
                return None
            
            data = {
                'player_name': player_name,
                'games': games,
                'game_count': len(games)
            }
            
            # Save raw data
            if save_raw:
                self.raw_storage.save(
                    data,
                    date=date,
                    source='databallr_players',
                    filename=f"player_{player_name.replace(' ', '_')}.json"
                )
            
            # Save processed data
            if save_processed:
                self.processed_storage.save_dict_list(
                    games,
                    name='player_stats',
                    date=date,
                    schema={
                        'player_name': player_name,
                        'date': '',
                        'points': 0,
                        'rebounds': 0,
                        'assists': 0,
                        'steals': 0,
                        'blocks': 0,
                        'turnovers': 0,
                        'minutes': 0.0
                    }
                )
            
            logger.info(f"✓ Successfully scraped {len(games)} games for {player_name}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to scrape player stats for {player_name}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def scrape_all(
        self,
        date: Optional[str] = None,
        player_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Scrape all available data.
        
        Args:
            date: Date string (YYYY-MM-DD) or None for today
            player_names: Optional list of specific players to scrape
        
        Returns:
            Summary dict with scrape results
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Starting full scrape for {date}")
        
        results = {
            'date': date,
            'scraped_at': datetime.now().isoformat(),
            'players': {},
            'success_count': 0,
            'failure_count': 0
        }
        
        # If no player list provided, scrape from cache
        if player_names is None:
            # Load player names from cache
            cache_file = Path("data/cache/databallr_player_cache.json")
            if cache_file.exists():
                import json
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    player_names = list(cache_data.get('cache', {}).keys())
            else:
                logger.warning("No player cache found and no player list provided")
                return results
        
        # Scrape each player
        for player_name in player_names:
            try:
                data = self.scrape_player_stats(
                    player_name,
                    last_n_games=20,
                    date=date
                )
                
                if data:
                    results['players'][player_name] = {
                        'status': 'success',
                        'game_count': data.get('game_count', 0)
                    }
                    results['success_count'] += 1
                else:
                    results['players'][player_name] = {
                        'status': 'failed',
                        'game_count': 0
                    }
                    results['failure_count'] += 1
                    
            except Exception as e:
                logger.error(f"Error scraping {player_name}: {e}")
                results['players'][player_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                results['failure_count'] += 1
        
        logger.info(
            f"Scrape complete: {results['success_count']} success, "
            f"{results['failure_count']} failures"
        )
        
        return results
    
    def close(self):
        """Cleanup resources"""
        pass  # Playwright handles its own cleanup


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='DataballR Robust Scraper')
    parser.add_argument(
        '--date',
        type=str,
        help='Date to scrape (YYYY-MM-DD), defaults to today'
    )
    parser.add_argument(
        '--player',
        type=str,
        help='Specific player name to scrape'
    )
    parser.add_argument(
        '--players',
        type=str,
        nargs='+',
        help='List of player names to scrape'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        default='logs/scraper.log',
        help='Log file path'
    )
    parser.add_argument(
        '--raw-dir',
        type=str,
        default='data/raw',
        help='Raw data directory'
    )
    parser.add_argument(
        '--processed-dir',
        type=str,
        default='data/processed',
        help='Processed data directory'
    )
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = DataballrRobustScraper(
        raw_storage_dir=Path(args.raw_dir),
        processed_storage_dir=Path(args.processed_dir),
        log_file=Path(args.log_file)
    )
    
    try:
        if args.player:
            # Scrape single player
            scraper.scrape_player_stats(args.player, date=args.date)
        elif args.players:
            # Scrape specific players
            results = scraper.scrape_all(date=args.date, player_names=args.players)
            print(f"\nScrape Results:")
            print(f"  Success: {results['success_count']}")
            print(f"  Failures: {results['failure_count']}")
        else:
            # Scrape all
            results = scraper.scrape_all(date=args.date)
            print(f"\nScrape Results:")
            print(f"  Success: {results['success_count']}")
            print(f"  Failures: {results['failure_count']}")
    finally:
        scraper.close()


if __name__ == '__main__':
    main()

