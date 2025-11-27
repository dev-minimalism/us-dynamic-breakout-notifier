#!/usr/bin/env python3
"""
Standalone dynamic stock screener for US market.

Screens US markets for stocks meeting O'Neil criteria.
Can be run independently to test screening or update watchlist.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from us_dynamic_breakout.screener import DynamicScreener


def main():
    """Run standalone screening."""
    import argparse

    parser = argparse.ArgumentParser(description="Dynamic Stock Screener (US Market)")
    parser.add_argument('--max', type=int, default=100, help='Max stocks to screen (default: 100)')

    args = parser.parse_args()

    print("🚀 Dynamic Stock Screener (US Market)\n")

    screener = DynamicScreener()
    tickers = screener.run_full_scan(max_stocks=args.max)

    print(f"\n📋 Selected US stocks ({len(tickers)}):")
    for i, ticker in enumerate(tickers[:20], 1):
        print(f"  {i:2d}. {ticker}")
    if len(tickers) > 20:
        print(f"  ... and {len(tickers) - 20} more")


if __name__ == "__main__":
    main()
