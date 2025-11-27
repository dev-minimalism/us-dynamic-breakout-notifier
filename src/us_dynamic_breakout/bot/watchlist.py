"""Watchlist management for tracking monitored US stocks."""

import json
import os
from datetime import datetime
from typing import List, Tuple, Optional
from pathlib import Path


class WatchlistManager:
    """Manages the list of US stocks being monitored for breakouts."""

    def __init__(self, watchlist_file: str = "data/watchlist.json"):
        """
        Initialize watchlist manager.

        Args:
            watchlist_file: Path to watchlist JSON file
        """
        self.watchlist_file = watchlist_file
        self.tickers: List[str] = []
        self.last_screening_time: Optional[datetime] = None
        self.screening_mode: str = "manual"
        self.load()

    def load(self) -> List[str]:
        """Load watchlist from file."""
        if os.path.exists(self.watchlist_file):
            try:
                with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tickers = data.get('tickers', data.get('us', []))
                    self.screening_mode = data.get('screening_mode', 'manual')
                    if data.get('last_screening'):
                        self.last_screening_time = datetime.strptime(
                            data['last_screening'], '%Y-%m-%d %H:%M:%S'
                        )
            except Exception as e:
                print(f"⚠️  Failed to load watchlist: {e}")
                self._set_defaults()
        else:
            self._set_defaults()

        return self.tickers

    def _set_defaults(self):
        """Set default watchlist."""
        self.tickers = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "AMZN", "META"]

    def save(self) -> bool:
        """Save watchlist to file."""
        try:
            # Ensure directory exists
            Path(self.watchlist_file).parent.mkdir(parents=True, exist_ok=True)

            data = {
                'tickers': self.tickers,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'screening_mode': self.screening_mode,
                'last_screening': (
                    self.last_screening_time.strftime('%Y-%m-%d %H:%M:%S')
                    if self.last_screening_time else None
                )
            }
            with open(self.watchlist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ Failed to save watchlist: {e}")
            return False

    def add(self, ticker: str) -> Tuple[bool, str]:
        """
        Add US stock to watchlist.

        Returns:
            Tuple of (success, message)
        """
        ticker = ticker.upper().strip()
        if ticker in self.tickers:
            return False, f"⚠️  {ticker} is already in watchlist."

        self.tickers.append(ticker)
        if self.save():
            return True, f"✅ 🇺🇸 {ticker} added! Total: {len(self.tickers)} stocks"
        else:
            self.tickers.remove(ticker)
            return False, "❌ Save failed"

    def remove(self, ticker: str) -> Tuple[bool, str]:
        """Remove US stock from watchlist."""
        ticker = ticker.upper().strip()
        if ticker not in self.tickers:
            return False, f"⚠️  {ticker} not found in watchlist."

        self.tickers.remove(ticker)
        if self.save():
            return True, f"✅ 🇺🇸 {ticker} removed! Total: {len(self.tickers)} stocks"
        else:
            self.tickers.append(ticker)
            return False, "❌ Save failed"

    def update_from_screening(self, tickers: List[str]):
        """Update watchlist from screening results."""
        self.tickers = tickers
        self.last_screening_time = datetime.now()
        self.screening_mode = "dynamic"
        self.save()

    def get_count(self) -> int:
        """Get count of stocks in watchlist."""
        return len(self.tickers)
