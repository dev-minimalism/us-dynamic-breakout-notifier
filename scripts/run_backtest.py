#!/usr/bin/env python3
"""
Backtest runner for O'Neil breakout strategy.

Runs a backtest with no look-ahead bias - each day screens stocks
using only data available at that time.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from us_dynamic_breakout.backtest import BacktestEngine


def main():
    """Run backtest."""
    import argparse

    parser = argparse.ArgumentParser(description="O'Neil Backtest Runner")
    parser.add_argument(
        '--capital',
        type=float,
        default=100_000_000,
        help='Initial capital in KRW (default: 100M)'
    )
    parser.add_argument(
        '--start',
        type=str,
        default='2023-01-02',
        help='Start date YYYY-MM-DD (default: 2023-01-02)'
    )
    parser.add_argument(
        '--end',
        type=str,
        default='2025-11-18',
        help='End date YYYY-MM-DD (default: 2025-11-18)'
    )
    parser.add_argument(
        '--max-positions',
        type=int,
        default=5,
        help='Max concurrent positions (default: 5)'
    )

    args = parser.parse_args()

    print("🚀 O'Neil Breakout Strategy Backtest\n")
    print(f"   Capital: {args.capital/1e6:.0f}M KRW")
    print(f"   Period: {args.start} to {args.end}")
    print(f"   Max positions: {args.max_positions}")
    print()

    engine = BacktestEngine(
        initial_capital=args.capital,
        max_positions=args.max_positions
    )

    results = engine.run(start_date=args.start, end_date=args.end)

    return results


if __name__ == "__main__":
    main()
