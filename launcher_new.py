"""
PositiveEdge - Sports Betting Value Analysis Platform
======================================================
Simplified launcher with bundled scripts and individual options.

Usage:
  python launcher.py                    # Interactive menu
  python launcher.py --script <name>    # Run specific script
  python launcher.py --list             # List all available scripts

Examples:
  python launcher.py --script sportsbet-analysis
  python launcher.py --script value-engine
  python launcher.py --script test-regression
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple


class Script:
    """Represents a runnable script"""
    def __init__(self, name: str, path: str, description: str, category: str):
        self.name = name
        self.path = path
        self.description = description
        self.category = category


class SimplifiedLauncher:
    """Simplified launcher with organized categories"""

    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.scripts = self._register_scripts()

    def _register_scripts(self) -> Dict[str, Script]:
        """Register all available scripts"""
        scripts = {}

        # ========== VALUE ANALYSIS ==========
        scripts["value-engine"] = Script(
            "value-engine",
            "main.py",
            "Interactive Value Engine (original)",
            "analysis"
        )
        scripts["value-engine-enhanced"] = Script(
            "value-engine-enhanced",
            "value_engine_enhanced.py",
            "Enhanced Value Engine with Team Stats (demo)",
            "analysis"
        )
        scripts["demo"] = Script(
            "demo",
            "demo.py",
            "Demo Mode (sample data)",
            "analysis"
        )

        # ========== SCRAPERS ==========
        scripts["sportsbet-scraper"] = Script(
            "sportsbet-scraper",
            "scrapers/sportsbet_final_enhanced.py",
            "Sportsbet Markets, Insights & Stats",
            "scraper"
        )
        scripts["rotowire-scraper"] = Script(
            "rotowire-scraper",
            "scrapers/rotowire_scraper.py",
            "RotoWire Lineup & Injury Data",
            "scraper"
        )
        scripts["universal-scraper"] = Script(
            "universal-scraper",
            "scrapers/universal_scraper.py",
            "Universal Multi-Site Scraper",
            "scraper"
        )

        # ========== COMPLETE ANALYSIS PIPELINES ==========
        scripts["sportsbet-analysis"] = Script(
            "sportsbet-analysis",
            "scrapers/sportsbet_complete_analysis.py",
            "Sportsbet Complete Analysis (Insights + Lineups + Value Engine)",
            "pipeline"
        )
        scripts["auto-pipeline"] = Script(
            "auto-pipeline",
            "scrapers/auto_analysis_pipeline.py",
            "Automated Analysis Pipeline",
            "pipeline"
        )
        scripts["sportsbet-pipeline"] = Script(
            "sportsbet-pipeline",
            "scrapers/sportsbet_pipeline_integration.py",
            "Sportsbet Pipeline Integration",
            "pipeline"
        )

        # ========== DATA UTILITIES ==========
        scripts["data-consolidator"] = Script(
            "data-consolidator",
            "scrapers/data_consolidator.py",
            "Data Consolidator",
            "utility"
        )
        scripts["historical-helper"] = Script(
            "historical-helper",
            "scrapers/historical_data_helper.py",
            "Historical Data Helper",
            "utility"
        )
        scripts["data-processor"] = Script(
            "data-processor",
            "data_processor.py",
            "Data Processor",
            "utility"
        )

        # ========== TESTS ==========
        scripts["test-engine"] = Script(
            "test-engine",
            "tests/test_engine.py",
            "Test Value Engine",
            "test"
        )
        scripts["test-integration"] = Script(
            "test-integration",
            "test_integration.py",
            "Test Integration",
            "test"
        )
        scripts["test-regression"] = Script(
            "test-regression",
            "test_regression_fix.py",
            "Test Sample Size Regression Fix",
            "test"
        )
        scripts["test-stats"] = Script(
            "test-stats",
            "test_stats_extraction.py",
            "Test Stats Extraction from Sportsbet",
            "test"
        )

        return scripts

    def print_header(self):
        """Print application header"""
        print("\n" + "=" * 70)
        print("  ____           _ _   _           _____ _            ")
        print(" |  _ \\ ___  ___(_) |_(_)_   _____| ____| | ____ _  ___ ")
        print(" | |_) / _ \\/ __| | __| \\ \\ / / _ \\  _| | |/ _` |/ _ \\")
        print(" |  __/ (_) \\__ \\ | |_| |\\ V /  __/ |___| | (_| |  __/")
        print(" |_|   \\___/|___/_|\\__|_| \\_/ \\___|_____|_|\\__, |\\___|")
        print("                                            |___/      ")
        print("=" * 70)
        print("         Sports Betting Value Analysis Platform")
        print("=" * 70 + "\n")

    def get_scripts_by_category(self) -> Dict[str, List[Script]]:
        """Group scripts by category"""
        categories = {}
        for script in self.scripts.values():
            if script.category not in categories:
                categories[script.category] = []
            categories[script.category].append(script)
        return categories

    def print_menu(self):
        """Print simplified menu with categories"""
        categories_display = {
            "analysis": ("[ANALYSIS]", "Value Analysis & Engines"),
            "scraper": ("[SCRAPERS]", "Data Collection"),
            "pipeline": ("[PIPELINES]", "Complete Analysis Workflows"),
            "utility": ("[UTILITIES]", "Data Processing"),
            "test": ("[TESTS]", "Testing & Validation")
        }

        categories = self.get_scripts_by_category()

        option_num = 1
        option_map = {}

        for cat_key, (cat_icon, cat_name) in categories_display.items():
            if cat_key not in categories:
                continue

            print(f"\n{cat_icon} {cat_name.upper()}")
            print("-" * 70)

            for script in sorted(categories[cat_key], key=lambda s: s.name):
                print(f"  {option_num:2d}. {script.description}")
                option_map[str(option_num)] = script
                option_num += 1

        print("\n[SYSTEM]")
        print("-" * 70)
        print(f"  {option_num:2d}. View Analysis Results")
        option_map[str(option_num)] = "view-results"
        option_num += 1

        print(f"  {option_num:2d}. System Status")
        option_map[str(option_num)] = "system-status"
        option_num += 1

        print(f"  {option_num:2d}. Documentation")
        option_map[str(option_num)] = "docs"
        option_num += 1

        print(f"  {option_num:2d}. List All Scripts")
        option_map[str(option_num)] = "list-scripts"
        option_num += 1

        print(f"  {option_num:2d}. Exit")
        option_map[str(option_num)] = "exit"

        print("=" * 70)

        return option_map

    def run_script(self, script: Script):
        """Run a script"""
        script_path = self.root_dir / script.path

        if not script_path.exists():
            print(f"\n[ERROR] Script not found: {script_path}")
            input("\nPress Enter to continue...")
            return

        print(f"\n[LAUNCHING] {script.description}")
        print(f"Script: {script.path}")
        print("-" * 70 + "\n")

        try:
            subprocess.run([sys.executable, str(script_path)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Script failed: {e}")
        except KeyboardInterrupt:
            print(f"\n\n[INTERRUPTED] Script stopped by user")
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")

        input("\n\nPress Enter to return to menu...")

    def view_analysis_results(self):
        """View previous analysis results"""
        output_dir = self.root_dir / "data" / "outputs"

        if not output_dir.exists():
            print("\n[ERROR] No output directory found")
            input("\nPress Enter to return to menu...")
            return

        json_files = sorted(output_dir.glob("complete_analysis_*.json"), reverse=True)

        if not json_files:
            print("\n[INFO] No analysis results found")
            input("\nPress Enter to return to menu...")
            return

        print("\n[RECENT ANALYSIS RESULTS]")
        print("-" * 70)
        for i, file in enumerate(json_files[:10], 1):
            size_kb = file.stat().st_size / 1024
            modified = file.stat().st_mtime
            from datetime import datetime
            mod_time = datetime.fromtimestamp(modified).strftime("%Y-%m-%d %H:%M")
            print(f"  {i:2d}. {file.name}")
            print(f"      Size: {size_kb:.1f} KB | Modified: {mod_time}")

        print("-" * 70)
        choice = input("\nEnter number to view (or Enter to skip): ").strip()

        if choice.isdigit() and 1 <= int(choice) <= min(10, len(json_files)):
            file_path = json_files[int(choice) - 1]
            print(f"\n[VIEWING] {file_path.name}\n")

            import json
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                # Show summary
                print(f"Analysis Date: {data.get('analysis_date', 'N/A')}")
                print(f"Games Analyzed: {data.get('games_analyzed', 0)}")
                print(f"Total Insights: {data.get('total_insights', 0)}")
                print(f"Value Bets Found: {data.get('value_bets_found', 0)}")
                print("\nFull data:")
                print(json.dumps(data, indent=2)[:2000] + "\n... (truncated)")
            except Exception as e:
                print(f"[ERROR] Error reading file: {e}")

        input("\n\nPress Enter to return to menu...")

    def check_system_status(self):
        """Check system status"""
        print("\n[SYSTEM STATUS]")
        print("=" * 70)

        # Python version
        print(f"\nPython: {sys.version.split()[0]}")

        # Directory structure
        print("\n[DIRECTORIES]")
        dirs = ["data", "data/outputs", "scrapers", "tests", "docs", "archive", "historical_data"]
        for dir_name in dirs:
            dir_path = self.root_dir / dir_name
            status = "[OK]" if dir_path.exists() else "[MISSING]"
            print(f"  {status} {dir_name}/")

        # Key files
        print("\n[KEY FILES]")
        files = [
            "value_engine.py",
            "value_engine_enhanced.py",
            "scrapers/sportsbet_final_enhanced.py",
            "scrapers/sportsbet_complete_analysis.py",
            "scrapers/context_aware_analysis.py"
        ]
        for file_name in files:
            file_path = self.root_dir / file_name
            status = "[OK]" if file_path.exists() else "[MISSING]"
            print(f"  {status} {file_name}")

        # Dependencies
        print("\n[DEPENDENCIES]")
        dependencies = {
            "playwright": "Web scraping",
            "beautifulsoup4": "HTML parsing",
            "requests": "HTTP requests",
            "pandas": "Data processing",
            "numpy": "Numerical computing",
            "scipy": "Scientific computing"
        }
        for dep, purpose in dependencies.items():
            try:
                __import__(dep.replace("-", "_").replace("beautifulsoup4", "bs4"))
                print(f"  [OK] {dep:20s} ({purpose})")
            except ImportError:
                print(f"  [MISSING] {dep:20s} ({purpose})")

        # Data statistics
        print("\n[DATA]")
        output_dir = self.root_dir / "data" / "outputs"
        if output_dir.exists():
            analysis_count = len(list(output_dir.glob("complete_analysis_*.json")))
            print(f"  Analysis Results: {analysis_count}")

        historical_dir = self.root_dir / "historical_data"
        if historical_dir.exists():
            hist_count = len(list(historical_dir.glob("*.json")))
            print(f"  Historical Data: {hist_count} files")

        print("=" * 70)
        input("\nPress Enter to return to menu...")

    def list_all_scripts(self):
        """List all available scripts"""
        print("\n[ALL AVAILABLE SCRIPTS]")
        print("=" * 70)

        categories = self.get_scripts_by_category()

        for category in ["analysis", "scraper", "pipeline", "utility", "test"]:
            if category not in categories:
                continue

            cat_name = category.upper()
            print(f"\n{cat_name}:")
            print("-" * 70)

            for script in sorted(categories[category], key=lambda s: s.name):
                print(f"\n  Name: {script.name}")
                print(f"  Description: {script.description}")
                print(f"  Path: {script.path}")
                print(f"  Command: python launcher.py --script {script.name}")

        print("\n" + "=" * 70)
        print("\nTo run any script directly:")
        print("  python launcher.py --script <script-name>")
        print("\nExample:")
        print("  python launcher.py --script sportsbet-analysis")
        print("=" * 70)

        input("\nPress Enter to return to menu...")

    def open_documentation(self):
        """Open documentation"""
        docs_dir = self.root_dir / "docs"

        print("\n[DOCUMENTATION]")
        print("=" * 70)

        if docs_dir.exists():
            doc_files = sorted(docs_dir.glob("*.md"))
            if doc_files:
                print("\nAvailable Guides:")
                for i, doc in enumerate(doc_files, 1):
                    size_kb = doc.stat().st_size / 1024
                    print(f"  {i:2d}. {doc.name:40s} ({size_kb:.1f} KB)")

        readme = self.root_dir / "README.md"
        if readme.exists():
            print(f"\nMain README: {readme}")

        print("\nDocumentation Location:")
        print(f"  {docs_dir}/")

        print("\n" + "=" * 70)
        input("\nPress Enter to return to menu...")

    def run_interactive(self):
        """Run interactive menu"""
        while True:
            self.print_header()
            option_map = self.print_menu()

            choice = input(f"\nSelect option (1-{len(option_map)}): ").strip()

            if choice not in option_map:
                print("\n[ERROR] Invalid choice")
                input("\nPress Enter to continue...")
                continue

            action = option_map[choice]

            if action == "exit":
                print("\n[GOODBYE] Thanks for using PositiveEdge!\n")
                break
            elif action == "view-results":
                self.view_analysis_results()
            elif action == "system-status":
                self.check_system_status()
            elif action == "docs":
                self.open_documentation()
            elif action == "list-scripts":
                self.list_all_scripts()
            elif isinstance(action, Script):
                self.run_script(action)

    def run_by_name(self, script_name: str):
        """Run script by name"""
        if script_name not in self.scripts:
            print(f"\n[ERROR] Unknown script: {script_name}")
            print("\nAvailable scripts:")
            for name in sorted(self.scripts.keys()):
                print(f"  - {name}")
            print("\nUse 'python launcher.py --list' to see all scripts")
            return

        script = self.scripts[script_name]
        self.run_script(script)

    def list_scripts_cli(self):
        """List scripts for CLI"""
        categories = self.get_scripts_by_category()

        for category in ["analysis", "scraper", "pipeline", "utility", "test"]:
            if category not in categories:
                continue

            print(f"\n{category.upper()}:")
            for script in sorted(categories[category], key=lambda s: s.name):
                print(f"  {script.name:30s} - {script.description}")

        print("\nUsage:")
        print("  python launcher.py --script <name>")
        print("\nExample:")
        print("  python launcher.py --script sportsbet-analysis")


def main():
    """Main entry point"""
    launcher = SimplifiedLauncher()

    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--script" and len(sys.argv) > 2:
            launcher.run_by_name(sys.argv[2])
        elif sys.argv[1] == "--list":
            launcher.list_scripts_cli()
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(__doc__)
        else:
            print(f"[ERROR] Unknown argument: {sys.argv[1]}")
            print("Use --help for usage information")
    else:
        # Interactive mode
        launcher.run_interactive()


if __name__ == "__main__":
    main()
