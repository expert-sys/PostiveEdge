"""
PositiveEdge - Sports Betting Value Analysis Platform
======================================================
Ultra-simplified launcher - 6 options max

Usage:
  python launcher.py                    # Interactive menu
  python launcher.py --run <number>     # Run option directly (1-6)
"""

import sys
import os
import subprocess
from pathlib import Path


class SimpleLauncher:
    """Ultra-simple launcher with 6 bundled options"""

    def __init__(self):
        self.root_dir = Path(__file__).parent

    def print_header(self):
        """Print header"""
        print("\n" + "=" * 70)
        print("  PositiveEdge - Sports Betting Value Analysis")
        print("=" * 70 + "\n")

    def print_menu(self):
        """Print simple 6-option menu"""
        print("Select an option:\n")
        print("  1. Run Complete Analysis (Sportsbet + Lineups + Value)")
        print("  2. Scrape Data (Sportsbet, RotoWire, or Universal)")
        print("  3. Value Analysis (Run value engine on existing data)")
        print("  4. View Results (Browse analysis outputs)")
        print("  5. Run Tests (Validate system)")
        print("  6. Exit")
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
            subprocess.run([sys.executable, str(script_full)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Failed: {e}")
        except KeyboardInterrupt:
            print(f"\n\n[STOPPED] Interrupted by user")
        except Exception as e:
            print(f"\n[ERROR] {e}")

        input("\n\nPress Enter to return to menu...")

    def option_1_complete_analysis(self):
        """Option 1: Complete Analysis"""
        self.run_script(
            "scrapers/sportsbet_complete_analysis.py",
            "Complete Analysis (Sportsbet + Lineups + Value Engine)"
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

    def option_3_value_analysis(self):
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

    def option_4_view_results(self):
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
            print(f"\n[VIEWING] {file_path.name}\n")

            import json
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                print(json.dumps(data, indent=2)[:3000] + "\n...(truncated)")
            except Exception as e:
                print(f"[ERROR] {e}")

        input("\n\nPress Enter to continue...")

    def option_5_run_tests(self):
        """Option 5: Run Tests"""
        print("\n" + "=" * 70)
        print("RUN TESTS")
        print("=" * 70)
        print("\nSelect test:\n")
        print("  1. Test Stats Extraction")
        print("  2. Test Regression Fix")
        print("  3. Test Value Engine")
        print("  4. Run All Tests")
        print("  5. Back to main menu")
        print("\n" + "-" * 70)

        choice = input("\nSelect (1-5): ").strip()

        if choice == "1":
            self.run_script("test_stats_extraction.py", "Stats Extraction Test")
        elif choice == "2":
            self.run_script("test_regression_fix.py", "Regression Fix Test")
        elif choice == "3":
            self.run_script("tests/test_engine.py", "Value Engine Test")
        elif choice == "4":
            # Run all tests
            tests = [
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
        elif choice == "5":
            return
        else:
            print("\n[ERROR] Invalid choice")
            input("\nPress Enter to continue...")

    def run_interactive(self):
        """Run interactive menu"""
        while True:
            self.print_header()
            self.print_menu()

            choice = input("\nSelect option (1-6): ").strip()

            if choice == "1":
                self.option_1_complete_analysis()
            elif choice == "2":
                self.option_2_scrape_data()
            elif choice == "3":
                self.option_3_value_analysis()
            elif choice == "4":
                self.option_4_view_results()
            elif choice == "5":
                self.option_5_run_tests()
            elif choice == "6":
                print("\n[GOODBYE] Thanks for using PositiveEdge!\n")
                break
            else:
                print("\n[ERROR] Invalid choice. Select 1-6.")
                input("\nPress Enter to continue...")

    def run_direct(self, option_num: str):
        """Run option directly from command line"""
        if option_num == "1":
            self.option_1_complete_analysis()
        elif option_num == "2":
            self.option_2_scrape_data()
        elif option_num == "3":
            self.option_3_value_analysis()
        elif option_num == "4":
            self.option_4_view_results()
        elif option_num == "5":
            self.option_5_run_tests()
        else:
            print(f"[ERROR] Invalid option: {option_num}")
            print("Valid options: 1-5")


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
            print("  python launcher.py --run <1-5>  # Run option directly")
            print("  python launcher.py --help       # Show help")
    else:
        # Interactive mode
        launcher.run_interactive()


if __name__ == "__main__":
    main()
