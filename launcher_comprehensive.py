"""
PositiveEdge - Comprehensive Betting Analysis Launcher
======================================================
Complete pipeline: Scrapers → Model Engine → Bet Recommendations

Flow:
1. Sportsbet Scraper (with enhanced anti-detection)
2. DataballR Scraper (robust with retries)
3. RotoWire Scraper (lineups & injuries)
4. Unified Analysis Pipeline (model projections)
5. Display Top Bets (filtered & ranked)

Usage:
  python launcher_comprehensive.py           # Interactive mode
  python launcher_comprehensive.py --auto    # Auto-run full pipeline
  python launcher_comprehensive.py --view    # View latest results
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("launcher")


class ComprehensiveLauncher:
    """Complete betting analysis pipeline launcher"""

    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.data_dir = self.root_dir / "data"
        self.output_dir = self.data_dir / "outputs"
        self.scraped_dir = self.data_dir / "scraped"
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scraped_dir.mkdir(parents=True, exist_ok=True)

    def print_header(self):
        """Print application header"""
        print("\n" + "="*80)
        print("  PositiveEdge - Comprehensive Betting Analysis System")
        print("  " + datetime.now().strftime("%A, %B %d, %Y - %I:%M %p"))
        print("="*80 + "\n")

    def print_menu(self):
        """Print main menu"""
        print("Main Menu:")
        print()
        print("  [1] Run Full Pipeline (All Scrapers + Analysis + Top Bets)")
        print("  [2] Quick Analysis (Use existing data)")
        print("  [3] Scrape Data Only (No analysis)")
        print("  [4] View Latest Results")
        print("  [5] View All Results")
        print("  [6] System Settings")
        print("  [7] Exit")
        print()
        print("="*80)

    def run_full_pipeline(self, silent: bool = False):
        """
        Run complete pipeline:
        Sportsbet → DataballR → RotoWire → Analysis → Display
        """
        if not silent:
            print("\n" + "="*80)
            print("  FULL PIPELINE EXECUTION")
            print("="*80)
            print()
            print("Pipeline Flow:")
            print("  All steps are handled by the Unified Analysis Pipeline:")
            print("  - Sportsbet Scraper (Markets, Insights, Stats)")
            print("  - DataballR Scraper (Player Game Logs)")
            print("  - Insight Analysis (Context-Aware Value Engine)")
            print("  - Model Projections (Player Props + Team Bets)")
            print("  - Display Top Bets (50+ Confidence, Max 2 per game)")
            print()
            print("="*80)
            print()
            
            confirm = input("Start full pipeline? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Cancelled.")
                return False

        start_time = datetime.now()
        print(f"\n[PIPELINE START] {start_time.strftime('%I:%M:%S %p')}")
        print("="*80 + "\n")

        # Note: Unified pipeline handles ALL scraping internally
        # No need to run separate scrapers first
        
        # Unified Analysis Pipeline (handles Sportsbet + DataballR + Analysis)
        print("\n" + "-"*80)
        print("UNIFIED ANALYSIS PIPELINE")
        print("-"*80)
        print("Running: Sportsbet → DataballR → Insights → Model → Display")
        print("(All scraping is handled automatically within the pipeline)")
        print()
        success = self._run_step(
            "scrapers/unified_analysis_pipeline.py",
            "Running unified analysis with model projections"
        )
        
        if not success:
            print("\n[ERROR] Analysis pipeline failed.")
            input("\nPress Enter to continue...")
            return False

        # Pipeline complete
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*80)
        print(f"  PIPELINE COMPLETE - Duration: {duration:.1f}s")
        print("="*80)
        
        # Show results
        self._show_latest_summary()
        
        if not silent:
            input("\nPress Enter to return to menu...")
        
        return True

    def run_quick_analysis(self):
        """Run analysis using existing scraped data"""
        print("\n" + "="*80)
        print("  QUICK ANALYSIS (Using Existing Data)")
        print("="*80)
        print()
        print("This will analyze the most recent scraped data.")
        print()
        
        # Check if we have recent data
        scraped_files = sorted(self.scraped_dir.glob("sportsbet_match_*.json"), reverse=True)
        if not scraped_files:
            print("[ERROR] No scraped data found. Run 'Scrape Data Only' first.")
            input("\nPress Enter to continue...")
            return
        
        latest = scraped_files[0]
        age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
        age_str = f"{age.seconds // 60} minutes ago" if age.days == 0 else f"{age.days} days ago"
        
        print(f"Latest scraped data: {latest.name}")
        print(f"Age: {age_str}")
        print()
        
        confirm = input("Run analysis? (y/n): ").strip().lower()
        if confirm != 'y':
            return
        
        print("\n" + "-"*80)
        print("RUNNING ANALYSIS")
        print("-"*80)
        
        success = self._run_step(
            "scrapers/unified_analysis_pipeline.py",
            "Analyzing existing data with model projections"
        )
        
        if success:
            self._show_latest_summary()
        
        input("\nPress Enter to continue...")

    def scrape_data_only(self):
        """Scrape data without running analysis"""
        print("\n" + "="*80)
        print("  SCRAPE DATA ONLY")
        print("="*80)
        print()
        print("Select scraper:")
        print()
        print("  [1] Sportsbet (Full: Markets + Insights + Stats)")
        print("  [2] DataballR Test (Single player)")
        print("  [3] Both (Sportsbet + DataballR)")
        print("  [4] Back to menu")
        print()
        
        choice = input("Select (1-4): ").strip()
        
        if choice == "1":
            self._run_step("scrapers/sportsbet_final_enhanced.py", "Sportsbet Scraper")
        elif choice == "2":
            self._run_step("scrapers/databallr_robust/main.py", "DataballR Scraper Test")
        elif choice == "3":
            self._run_step("scrapers/sportsbet_final_enhanced.py", "Sportsbet Scraper")
            print()
            self._run_step("scrapers/databallr_robust/main.py", "DataballR Scraper Test")
        elif choice == "4":
            return
        else:
            print("[ERROR] Invalid choice")
        
        input("\nPress Enter to continue...")

    def view_latest_results(self):
        """View latest analysis results"""
        print("\n" + "="*80)
        print("  LATEST RESULTS")
        print("="*80)
        print()
        
        self._show_latest_summary(detailed=True)
        input("\nPress Enter to continue...")

    def view_all_results(self):
        """View all analysis results"""
        self._run_step("view_results.py", "View Analysis Results")
        input("\nPress Enter to continue...")

    def system_settings(self):
        """Configure system settings"""
        print("\n" + "="*80)
        print("  SYSTEM SETTINGS")
        print("="*80)
        print()
        print("  [1] View Cache Status")
        print("  [2] Build Player Cache")
        print("  [3] Update Player Cache")
        print("  [4] Clear Cache")
        print("  [5] View Logs")
        print("  [6] Back to menu")
        print()
        
        choice = input("Select (1-6): ").strip()
        
        if choice == "1":
            self._view_cache_status()
        elif choice == "2":
            self._run_step("build_comprehensive_player_cache.py", "Building Player Cache")
        elif choice == "3":
            self._run_step("update_player_cache_daily.py", "Updating Player Cache")
        elif choice == "4":
            self._clear_cache()
        elif choice == "5":
            self._view_logs()
        elif choice == "6":
            return
        else:
            print("[ERROR] Invalid choice")
        
        input("\nPress Enter to continue...")

    def _run_step(self, script_path: str, description: str) -> bool:
        """
        Run a pipeline step (script)
        
        Returns:
            True if successful, False otherwise
        """
        script_full = self.root_dir / script_path
        
        if not script_full.exists():
            logger.error(f"Script not found: {script_path}")
            return False
        
        logger.info(f"Starting: {description}")
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_full)],
                check=False,
                cwd=str(self.root_dir)
            )
            
            if result.returncode != 0:
                logger.error(f"Step failed with exit code {result.returncode}")
                return False
            
            logger.info(f"Completed: {description}")
            return True
            
        except KeyboardInterrupt:
            logger.warning("Interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Error running step: {e}")
            return False

    def _show_latest_summary(self, detailed: bool = False):
        """Show summary of latest analysis results"""
        result_files = sorted(self.output_dir.glob("unified_analysis_*.json"), reverse=True)
        
        if not result_files:
            print("\n[INFO] No analysis results found.")
            return
        
        latest_file = result_files[0]
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print("\n" + "="*80)
            print("  TOP BET RECOMMENDATIONS")
            print("="*80)
            
            timestamp = data.get('timestamp', 'Unknown')
            print(f"\nAnalysis Time: {timestamp}")
            
            bets = data.get('top_bets', [])
            if not bets:
                print("\nNo bets met the confidence threshold.")
                return
            
            print(f"\nTop {len(bets)} Bets (Confidence 50+, Max 2 per game):")
            print("-"*80)
            
            for i, bet in enumerate(bets, 1):
                self._print_bet_summary(bet, i, detailed)
            
            print("="*80)
            
        except Exception as e:
            logger.error(f"Error reading results: {e}")

    def _print_bet_summary(self, bet: dict, index: int, detailed: bool = False):
        """Print a single bet summary"""
        try:
            bet_type = bet.get('type', 'unknown')
            
            if bet_type == 'player_prop':
                player = bet.get('player', 'Unknown')
                stat = bet.get('stat', 'points').title()
                line = bet.get('line', 0)
                print(f"\n{index}. {player} - {stat} OVER {line}")
            else:
                market = bet.get('market', 'Unknown')
                result = bet.get('result', '')
                print(f"\n{index}. {result} - {market}")
            
            # Key metrics
            odds = bet.get('odds', 0)
            confidence = bet.get('confidence', 0)
            ev = bet.get('ev_per_100', 0)
            edge = bet.get('edge', 0)
            
            print(f"   Odds: {odds:.2f} | Confidence: {confidence:.0f}/100")
            print(f"   EV: ${ev:+.2f}/100 | Edge: {edge:+.1f}%")
            
            if detailed:
                # Show projection details
                prob = bet.get('final_prob', bet.get('historical_probability', 0))
                sample = bet.get('sample_size', 0)
                print(f"   Probability: {prob:.1%} | Sample: n={sample}")
                
                game = bet.get('game', 'Unknown')
                print(f"   Game: {game}")
            
        except Exception as e:
            print(f"\n{index}. [Error displaying bet: {e}]")

    def _view_cache_status(self):
        """View player cache status"""
        cache_file = self.data_dir / "cache" / "databallr_player_cache.json"
        
        print("\n" + "-"*80)
        print("CACHE STATUS")
        print("-"*80)
        
        if not cache_file.exists():
            print("\nStatus: NOT FOUND")
            print("Action: Run 'Build Player Cache' to create")
        else:
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                print(f"\nStatus: READY")
                print(f"Last Updated: {data.get('timestamp', 'Unknown')}")
                print(f"Total Players: {data.get('total_players', 0)}")
                print(f"Total Mappings: {data.get('total_mappings', 0)}")
            except Exception as e:
                print(f"\nStatus: ERROR - {e}")

    def _clear_cache(self):
        """Clear player cache"""
        cache_file = self.data_dir / "cache" / "databallr_player_cache.json"
        
        if not cache_file.exists():
            print("\n[INFO] No cache to clear")
            return
        
        confirm = input("\nClear player cache? (y/n): ").strip().lower()
        if confirm == 'y':
            cache_file.unlink()
            print("[SUCCESS] Cache cleared")

    def _view_logs(self):
        """View recent logs"""
        log_file = self.root_dir / "output.log"
        
        if not log_file.exists():
            print("\n[INFO] No logs found")
            return
        
        print("\n" + "-"*80)
        print("RECENT LOGS (Last 50 lines)")
        print("-"*80 + "\n")
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-50:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"[ERROR] {e}")

    def run_interactive(self):
        """Run interactive menu"""
        while True:
            self.print_header()
            self.print_menu()
            
            choice = input("Select option (1-7): ").strip()
            
            if choice == "1":
                self.run_full_pipeline()
            elif choice == "2":
                self.run_quick_analysis()
            elif choice == "3":
                self.scrape_data_only()
            elif choice == "4":
                self.view_latest_results()
            elif choice == "5":
                self.view_all_results()
            elif choice == "6":
                self.system_settings()
            elif choice == "7":
                print("\n[GOODBYE] Thanks for using PositiveEdge!\n")
                break
            else:
                print("\n[ERROR] Invalid choice. Select 1-7.")
                input("\nPress Enter to continue...")


def main():
    """Main entry point"""
    launcher = ComprehensiveLauncher()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg == "--auto":
            # Auto-run full pipeline
            launcher.run_full_pipeline(silent=True)
        elif arg == "--view":
            # View latest results
            launcher.view_latest_results()
        elif arg == "--help" or arg == "-h":
            print(__doc__)
        else:
            print(f"[ERROR] Unknown argument: {arg}")
            print("\nUsage:")
            print("  python launcher_comprehensive.py          # Interactive mode")
            print("  python launcher_comprehensive.py --auto   # Auto-run full pipeline")
            print("  python launcher_comprehensive.py --view   # View latest results")
    else:
        # Interactive mode
        launcher.run_interactive()


if __name__ == "__main__":
    main()

