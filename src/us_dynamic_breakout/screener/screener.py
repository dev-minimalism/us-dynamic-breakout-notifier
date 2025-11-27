"""
Dynamic Stock Screener for US Market

Screens US stocks based on market cap, volume, price, and trend conditions.
"""

import time
from datetime import datetime
from typing import List

from ..data import USStockProvider


class DynamicScreener:
    """Dynamic stock screener that finds US stocks meeting O'Neil criteria."""

    def __init__(
        self,
        min_market_cap_usd: int = 500_000_000,
        min_avg_volume: int = 50_000,
        min_price_usd: float = 5.0
    ):
        """
        Initialize screener with filtering criteria.

        Args:
            min_market_cap_usd: Minimum market cap in USD ($500M default)
            min_avg_volume: Minimum average volume (50K default)
            min_price_usd: Minimum stock price in USD ($5 default)
        """
        self.min_market_cap_usd = min_market_cap_usd
        self.min_avg_volume = min_avg_volume
        self.min_price_usd = min_price_usd

    def screen_stocks(
        self,
        tickers: List[str] = None,
        max_stocks: int = 100
    ) -> List[str]:
        """
        Screen US stocks based on criteria.

        Args:
            tickers: List of tickers to screen (defaults to full universe)
            max_stocks: Maximum number of stocks to return

        Returns:
            List of qualified ticker symbols
        """
        if tickers is None:
            tickers = USStockProvider.get_universe()

        qualified = []
        print(f"\n🔍 US Stock Screening ({len(tickers)} candidates, max {max_stocks})")
        print("=" * 60)

        for i, ticker in enumerate(tickers):
            if len(qualified) >= max_stocks:
                break

            try:
                if (i + 1) % 50 == 0:
                    print(f"Progress: {i + 1}/{len(tickers)} ({len(qualified)} passed)")

                info = USStockProvider.get_stock_info(ticker)
                if not info:
                    continue

                # Check market cap
                market_cap = info.get('marketCap', 0)
                if market_cap < self.min_market_cap_usd:
                    continue

                # Check price
                current_price = info.get('currentPrice', 0)
                if current_price < self.min_price_usd:
                    continue

                # Get historical data for volume check
                df = USStockProvider.get_stock_data(ticker, period='3mo')
                if df is None or len(df) < 20:
                    continue

                recent = df.tail(30)

                # Check average volume
                avg_volume = recent['Volume'].mean()
                if avg_volume < self.min_avg_volume:
                    continue

                # Calculate distance from 20-day high (for reference)
                high_20 = recent['High'].iloc[-20:].max()
                current = recent['Close'].iloc[-1]
                distance_from_high = ((current / high_20 - 1) * 100)

                qualified.append({
                    'ticker': ticker,
                    'market_cap': market_cap,
                    'price': current_price,
                    'avg_volume': int(avg_volume),
                    'distance_from_high': distance_from_high
                })

            except Exception:
                continue

            time.sleep(0.1)  # API rate limit

        # Sort by market cap
        qualified.sort(key=lambda x: x['market_cap'], reverse=True)

        print(f"\n✅ Screening complete: {len(qualified)} stocks selected")
        print("=" * 60)

        if qualified:
            print("\n📊 Top 10 stocks:")
            for i, s in enumerate(qualified[:10], 1):
                mc_b = s['market_cap'] / 1e9
                print(f"{i:2d}. {s['ticker']:6s} - "
                      f"Cap: ${mc_b:6.1f}B, "
                      f"Price: ${s['price']:7.2f}, "
                      f"From High: {s['distance_from_high']:+.1f}%")
        else:
            print("\n⚠️  No stocks passed the screening criteria.")

        return [s['ticker'] for s in qualified]

    def run_full_scan(self, max_stocks: int = 100) -> List[str]:
        """
        Run full market screening for US stocks.

        Args:
            max_stocks: Maximum stocks to select

        Returns:
            List of qualified ticker symbols
        """
        print("\n" + "=" * 60)
        print("🌍 Dynamic Stock Screening (US)")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        tickers = self.screen_stocks(max_stocks=max_stocks)

        print("\n" + "=" * 60)
        print("✅ Dynamic screening complete!")
        print(f"   🇺🇸 US: {len(tickers)} stocks")
        print("=" * 60 + "\n")

        return tickers
