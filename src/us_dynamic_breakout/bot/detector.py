"""Breakout pattern detection for O'Neil style trading (US market)."""

import time
from typing import Dict, Optional, List

import numpy as np
import pandas as pd

from ..data import USStockProvider


class BreakoutDetector:
    """Detects pivot point breakout patterns in US stock data."""

    def __init__(
        self,
        min_volume_surge: float = 50.0,
        max_breakout_pct: float = 5.0
    ):
        """
        Initialize detector with parameters.

        Args:
            min_volume_surge: Minimum volume increase % for valid signal
            max_breakout_pct: Maximum % above resistance for valid signal
        """
        self.min_volume_surge = min_volume_surge
        self.max_breakout_pct = max_breakout_pct

    def detect_pivot_breakout(
        self,
        df: pd.DataFrame,
        ticker: str
    ) -> Optional[Dict]:
        """
        Detect pivot point breakout pattern.

        A valid breakout requires:
        - Price breaks above 20-day high (resistance)
        - Volume surge >= min_volume_surge%
        - Breakout not too extended (within max_breakout_pct%)

        Args:
            df: DataFrame with OHLCV data
            ticker: Stock ticker symbol

        Returns:
            Signal dictionary or None if no signal
        """
        if df is None or len(df) < 30:
            return None

        try:
            recent = df.tail(30).copy()

            # Volume analysis
            avg_volume = recent['Volume'].iloc[:-1].mean()
            current_volume = recent['Volume'].iloc[-1]
            volume_surge = (current_volume / avg_volume - 1) * 100

            # Price analysis
            close = recent['Close'].values
            current_price = close[-1]
            resistance = np.max(close[-20:-1])  # 20-day high excluding today

            # Breakout conditions
            breakout = current_price > resistance
            breakout_pct = ((current_price - resistance) / resistance) * 100

            if (breakout and
                volume_surge >= self.min_volume_surge and
                0 < breakout_pct <= self.max_breakout_pct):

                signal = {
                    'ticker': ticker,
                    'pattern': 'Pivot Breakout',
                    'resistance': resistance,
                    'current_price': current_price,
                    'breakout_pct': round(breakout_pct, 2),
                    'volume_surge': round(volume_surge, 2)
                }

                return signal

        except Exception:
            pass

        return None

    def analyze_stock(self, ticker: str) -> List[Dict]:
        """
        Analyze US stock for breakout signals.

        Args:
            ticker: US stock ticker

        Returns:
            List of signals found (empty if none)
        """
        df = USStockProvider.get_stock_data(ticker)
        if df is None:
            return []

        signals = []
        pivot_signal = self.detect_pivot_breakout(df, ticker)
        if pivot_signal:
            signals.append(pivot_signal)

        return signals

    def scan_watchlist(self, tickers: List[str]) -> List[Dict]:
        """
        Scan watchlist for breakout signals.

        Args:
            tickers: List of US tickers

        Returns:
            List of all signals found
        """
        all_signals = []

        if not tickers:
            return all_signals

        print("🇺🇸 Scanning US stocks...\n")
        for ticker in tickers:
            try:
                print(f"  🔍 {ticker}...", end=" ")
                signals = self.analyze_stock(ticker)
                if signals:
                    all_signals.extend(signals)
                    print("✅ Signal!")
                else:
                    print("⚪")
            except Exception:
                print("❌ Error")
            time.sleep(0.5)
        print()

        return all_signals
