"""
CLV Closing Line Update Script
===============================
Manual script to update closing lines/odds for CLV tracking.

Usage:
    python scripts/update_clv_closing.py <bet_id> <closing_line> <closing_odds>
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.clv_tracker import get_clv_tracker
from config.settings import Config


def main():
    if len(sys.argv) < 4:
        print("Usage: python scripts/update_clv_closing.py <bet_id> <closing_line> <closing_odds>")
        print("\nExample:")
        print("  python scripts/update_clv_closing.py abc-123-def 25.5 1.85")
        sys.exit(1)
    
    bet_id = sys.argv[1]
    try:
        closing_line = float(sys.argv[2]) if sys.argv[2] != 'None' else None
        closing_odds = float(sys.argv[3]) if sys.argv[3] != 'None' else None
    except ValueError:
        print("Error: closing_line and closing_odds must be numbers")
        sys.exit(1)
    
    tracker = get_clv_tracker()
    tracker.update_closing(bet_id, closing_line, closing_odds)
    print(f"✓ Updated closing for bet {bet_id}: line={closing_line}, odds={closing_odds}")


if __name__ == "__main__":
    main()
