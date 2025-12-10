"""
PositiveEdge - Sports Betting Value Analysis Platform
======================================================
Streamlined launcher with player cache management

Usage:
  python launcher.py                    # Interactive menu
  python launcher.py --run <number>     # Run option directly (1-7)
"""

import sys
import os
import subprocess
from pathlib import Path


class SimpleLauncher:
    """Streamlined launcher with player cache management"""

    def __init__(self):
        self.root_dir = Path(__file__).parent

    def print_header(self):
        """Print header"""
        print("\n" + "=" * 70)
        print("  PositiveEdge - Sports Betting Value Analysis")
        print("=" * 70 + "\n")

    def print_menu(self):
        """Print simple menu"""
        print("Select an option:\n")
        print("  1. Run Unified Analysis (Team Bets + Player Props)")
        print("  2. Scrape Data (Sportsbet, RotoWire, or Universal)")
        print("  3. Player Cache Management (Build/Update player database)")
        print("  4. Value Analysis (Run value engine on existing data)")
        print("  5. View Results (Browse analysis outputs)")
        print("  6. Run Tests (Validate system)")
        print("  7. Exit")
        print("\n" + "=" * 70)

    def run_script(self, script_path: str, description: str):
        """Run a script"""
        script_full = self.root_dir / script_path

        if not script_full.exists():
            print(f"\n[ERROR] Script not found: {script_path}")
            input("\nPress Enter to continue...")
            return

        print(f"\n[RUNNING] {description}")
        print("-" * 70 + "\n")

        try:
            # Don't capture output - let it stream directly to console
            # This allows real-time output and interactive scripts
            result = subprocess.run(
                [sys.executable, str(script_full)],
                check=False  # Don't raise on error, handle manually
            )
            
            if result.returncode != 0:
                print("\n" + "="*70)
                print(f"  Script exited with error code: {result.returncode}")
                print("="*70)
                
        except KeyboardInterrupt:
            print(f"\n\n[STOPPED] Interrupted by user")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()

        input("\n\nPress Enter to return to menu...")

    def option_1_unified_analysis(self):
        """Option 1: Unified Analysis Pipeline"""
        print("\n" + "=" * 70)
        print("UNIFIED ANALYSIS PIPELINE")
        print("=" * 70)
        print("\nPipeline Flow:")
        print("  1. [SPORTSBET SCRAPER] Scrapes games, markets, insights, and player props")
        print("  2. [DATABALLR SCRAPER] Fetches player game logs (robust, with retries)")
        print("  3. [INSIGHT ANALYZER] Analyzes team bets using Context-Aware Value Engine")
        print("  4. [MODEL PROJECTIONS] Calculates player prop projections with matchup adjustments")
        print("  5. [DISPLAY] Filters to high-confidence bets and returns top 5 (max 2 per game)")
        print("\n" + "-" * 70)
        input("\nPress Enter to start pipeline...")
        
        self.run_script(
            "scrapers/unified_analysis_pipeline.py",
            "Unified Analysis Pipeline (Sportsbet → DataballR → Insights → Model → Display)"
        )

    def option_2_scrape_data(self):
        """Option 2: Scrape Data"""
        print("\n" + "=" * 70)
        print("SCRAPE DATA")
        print("=" * 70)
        print("\nSelect scraper:\n")
        print("  1. Sportsbet (Markets, Insights, Stats)")
        print("  2. RotoWire (Lineups, Injuries)")
        print("  3. Universal (Multi-site)")
        print("  4. Back to main menu")
        print("\n" + "-" * 70)

        choice = input("\nSelect (1-4): ").strip()

        if choice == "1":
            self.run_script("scrapers/sportsbet_final_enhanced.py", "Sportsbet Scraper")
        elif choice == "2":
            self.run_script("scrapers/rotowire_scraper.py", "RotoWire Scraper")
        elif choice == "3":
            self.run_script("scrapers/universal_scraper.py", "Universal Scraper")
        elif choice == "4":
            return
        else:
            print("\n[ERROR] Invalid choice")
            input("\nPress Enter to continue...")

    def option_3_player_cache(self):
        """Option 3: Player Cache Management"""
        print("\n" + "=" * 70)
        print("PLAYER CACHE MANAGEMENT")
        print("=" * 70)
        print("\nSelect action:\n")
        print("  1. Build Comprehensive Cache (First-time: IDs only, 30 seconds)")
        print("  2. Fetch Stats for Top 150 Players (Pre-cache game stats, 5-10 mins)")
        print("  3. Update Cache Daily (Quick: Add new players, refresh top stats)")
        print("  4. View Cache Stats")
        print("  5. Back to main menu")
        print("\n" + "-" * 70)

        choice = input("\nSelect (1-5): ").strip()

        if choice == "1":
            self.run_script(
                "build_comprehensive_player_cache.py",
                "Build Comprehensive Player Cache (Player IDs)"
            )
        elif choice == "2":
            self.run_script(
                "fetch_player_stats_batch.py",
                "Fetch Stats for Top 150 Players"
            )
        elif choice == "3":
            self.run_script(
                "update_player_cache_daily.py",
                "Update Player Cache Daily"
            )
        elif choice == "4":
            self.view_cache_stats()
        elif choice == "5":
            return
        else:
            print("\n[ERROR] Invalid choice")
            input("\nPress Enter to continue...")

    def view_cache_stats(self):
        """View player cache statistics"""
        import json
        from datetime import datetime
        
        player_cache_file = self.root_dir / "data" / "cache" / "databallr_player_cache.json"
        stats_cache_file = self.root_dir / "data" / "cache" / "player_stats_cache.json"
        
        print("\n" + "=" * 70)
        print("CACHE STATISTICS")
        print("=" * 70)
        
        # Player ID Cache
        print("\n[1] PLAYER ID CACHE")
        print("-" * 70)
        if not player_cache_file.exists():
            print("Status: NOT FOUND")
            print("Action: Run 'Build Comprehensive Cache' to create")
        else:
            try:
                with open(player_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                print(f"Status: READY")
                print(f"Last Updated: {cache_data.get('timestamp', 'Unknown')}")
                print(f"Total Players: {cache_data.get('total_players', 0)}")
                print(f"Total Mappings: {cache_data.get('total_mappings', 0)}")
                
                if 'update_summary' in cache_data:
                    summary = cache_data['update_summary']
                    print(f"Last Update: +{summary.get('added', 0)} -{summary.get('updated', 0)}")
            except Exception as e:
                print(f"Status: ERROR - {e}")
        
        # Stats Cache
        print("\n[2] PLAYER STATS CACHE (Pre-fetched Game Data)")
        print("-" * 70)
        if not stats_cache_file.exists():
            print("Status: NOT FOUND")
            print("Action: Run 'Fetch Stats for Top 150 Players' to create")
        else:
            try:
                with open(stats_cache_file, 'r', encoding='utf-8') as f:
                    stats_data = json.load(f)
                
                timestamp_str = stats_data.get('timestamp', 'Unknown')
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    age = datetime.now() - timestamp
                    age_str = f"{age.seconds // 3600}h ago" if age.days == 0 else f"{age.days}d ago"
                except:
                    age_str = "Unknown"
                
                print(f"Status: READY")
                print(f"Last Updated: {timestamp_str} ({age_str})")
                print(f"Cached Players: {stats_data.get('total_players', 0)}")
                
                # Sample a few players with stats
                stats_cache = stats_data.get('cache', {})
                if stats_cache:
                    print(f"\nSample (with averages):")
                    count = 0
                    for player_name, player_stats in list(stats_cache.items())[:5]:
                        averages = player_stats.get('averages', {})
                        pts = averages.get('points', 0)
                        reb = averages.get('rebounds', 0)
                        ast = averages.get('assists', 0)
                        games = player_stats.get('game_count', 0)
                        print(f"  {player_name.title()}: {pts:.1f}/{reb:.1f}/{ast:.1f} ({games}G)")
                        count += 1
                        if count >= 5:
                            break
            except Exception as e:
                print(f"Status: ERROR - {e}")
        
        print("\n" + "=" * 70)
        print("\nRECOMMENDATION:")
        
        if not player_cache_file.exists():
            print("  1. Run 'Build Comprehensive Cache' first (30 sec)")
            print("  2. Then 'Fetch Stats for Top 150 Players' (5-10 min)")
        elif not stats_cache_file.exists():
            print("  Run 'Fetch Stats for Top 150 Players' for faster analysis")
        else:
            try:
                with open(stats_cache_file, 'r') as f:
                    stats_data = json.load(f)
                timestamp = datetime.fromisoformat(stats_data.get('timestamp'))
                age = datetime.now() - timestamp
                if age.days >= 1:
                    print(f"  Stats cache is {age.days} days old - consider updating")
                else:
                    print("  All caches are fresh! Ready for analysis.")
            except:
                pass
        
        print("=" * 70)
        input("\nPress Enter to continue...")

    def option_4_value_analysis(self):
        """Option 3: Value Analysis"""
        print("\n" + "=" * 70)
        print("VALUE ANALYSIS")
        print("=" * 70)
        print("\nSelect engine:\n")
        print("  1. Enhanced Value Engine (with team stats)")
        print("  2. Original Value Engine")
        print("  3. Back to main menu")
        print("\n" + "-" * 70)

        choice = input("\nSelect (1-3): ").strip()

        if choice == "1":
            self.run_script("value_engine_enhanced.py", "Enhanced Value Engine")
        elif choice == "2":
            self.run_script("main.py", "Original Value Engine")
        elif choice == "3":
            return
        else:
            print("\n[ERROR] Invalid choice")
            input("\nPress Enter to continue...")

    def option_5_view_results(self):
        """Option 4: View Results"""
        output_dir = self.root_dir / "data" / "outputs"

        if not output_dir.exists():
            print("\n[INFO] No output directory found")
            input("\nPress Enter to continue...")
            return

        json_files = sorted(output_dir.glob("*.json"), reverse=True)

        if not json_files:
            print("\n[INFO] No results found")
            input("\nPress Enter to continue...")
            return

        print("\n" + "=" * 70)
        print("RECENT RESULTS")
        print("=" * 70 + "\n")

        for i, file in enumerate(json_files[:10], 1):
            size_kb = file.stat().st_size / 1024
            print(f"  {i:2d}. {file.name} ({size_kb:.1f} KB)")

        print("\n" + "-" * 70)
        choice = input("\nEnter number to view (or Enter to skip): ").strip()

        if choice.isdigit() and 1 <= int(choice) <= min(10, len(json_files)):
            file_path = json_files[int(choice) - 1]
            
            # Use the dedicated viewer script
            if "unified_analysis" in file_path.name:
                script = "show_enhanced_bets.py"
            elif "betting_recommendations" in file_path.name:
                 script = "view_enhanced_bets.py"
            else:
                 script = "view_analysis_results.py"
                 
            self.run_script(f"{script} --file {file_path.name}", f"Viewing {file_path.name}")

        input("\n\nPress Enter to continue...")

    def option_6_run_tests(self):
        """Option 5: Run Tests"""
        print("\n" + "=" * 70)
        print("RUN TESTS")
        print("=" * 70)
        print("\nSelect test:\n")
        print("  1. Test Engine Improvements (NEW - Comprehensive)")
        print("  2. Test Stats Extraction")
        print("  3. Test Regression Fix")
        print("  4. Test Value Engine")
        print("  5. Run All Tests")
        print("  6. Back to main menu")
        print("\n" + "-" * 70)

        choice = input("\nSelect (1-6): ").strip()

        if choice == "1":
            self.run_script("test_engine_improvements.py", "Engine Improvements Test Suite")
        elif choice == "2":
            self.run_script("test_stats_extraction.py", "Stats Extraction Test")
        elif choice == "3":
            self.run_script("test_regression_fix.py", "Regression Fix Test")
        elif choice == "4":
            self.run_script("tests/test_engine.py", "Value Engine Test")
        elif choice == "5":
            # Run all tests
            tests = [
                ("test_engine_improvements.py", "Engine Improvements"),
                ("test_stats_extraction.py", "Stats Extraction"),
                ("test_regression_fix.py", "Regression Fix"),
                ("tests/test_engine.py", "Value Engine")
            ]
            for test_path, test_name in tests:
                print(f"\n[RUNNING] {test_name} Test")
                print("-" * 70)
                try:
                    subprocess.run([sys.executable, str(self.root_dir / test_path)])
                except Exception as e:
                    print(f"[ERROR] {e}")
            input("\n\nPress Enter to continue...")
        elif choice == "6":
            return
        else:
            print("\n[ERROR] Invalid choice")
            input("\nPress Enter to continue...")

    # Option 6 (Improved Pipeline) merged into Option 1 (Unified Analysis)

    def run_interactive(self):
        """Run interactive menu"""
        while True:
            self.print_header()
            self.print_menu()

            choice = input("\nSelect option (1-7): ").strip()

            if choice == "1":
                self.option_1_unified_analysis()
            elif choice == "2":
                self.option_2_scrape_data()
            elif choice == "3":
                self.option_3_player_cache()
            elif choice == "4":
                self.option_4_value_analysis()
            elif choice == "5":
                self.option_5_view_results()
            elif choice == "6":
                self.option_6_run_tests()
            elif choice == "7":
                print("\n[GOODBYE] Thanks for using PositiveEdge!\n")
                break
            else:
                print("\n[ERROR] Invalid choice. Select 1-7.")
                input("\nPress Enter to continue...")

    def run_direct(self, option_num: str):
        """Run option directly from command line"""
        if option_num == "1":
            self.option_1_unified_analysis()
        elif option_num == "2":
            self.option_2_scrape_data()
        elif option_num == "3":
            self.option_3_player_cache()
        elif option_num == "4":
            self.option_4_value_analysis()
        elif option_num == "5":
            self.option_5_view_results()
        elif option_num == "6":
            self.option_6_run_tests()
        else:
            print(f"[ERROR] Invalid option: {option_num}")
            print("Valid options: 1-6")


def main():
    """Main entry point"""
    launcher = SimpleLauncher()

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--run" and len(sys.argv) > 2:
            launcher.run_direct(sys.argv[2])
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(__doc__)
        else:
            print(f"[ERROR] Unknown argument: {sys.argv[1]}")
            print("Usage:")
            print("  python launcher.py              # Interactive menu")
            print("  python launcher.py --run <1-7>  # Run option directly")
            print("  python launcher.py --help       # Show help")
    else:
        # Interactive mode
        launcher.run_interactive()


if __name__ == "__main__":
    main()
