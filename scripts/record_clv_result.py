"""
CLV Result Recording Script
===========================
Record bet results for CLV tracking.

Usage:
    python scripts/record_clv_result.py <bet_id> <result>
    where result is: WIN, LOSS, or PUSH
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.clv_tracker import get_clv_tracker


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/record_clv_result.py <bet_id> <result>")
        print("\nExample:")
        print("  python scripts/record_clv_result.py abc-123-def WIN")
        print("\nResult must be: WIN, LOSS, or PUSH")
        sys.exit(1)
    
    bet_id = sys.argv[1]
    result = sys.argv[2].upper()
    
    if result not in ['WIN', 'LOSS', 'PUSH']:
        print(f"Error: Result must be WIN, LOSS, or PUSH (got: {result})")
        sys.exit(1)
    
    tracker = get_clv_tracker()
    tracker.record_result(bet_id, result)
    print(f"✓ Recorded result for bet {bet_id}: {result}")


if __name__ == "__main__":
    main()
