"""Position management for tracking US stock trades."""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class PositionManager:
    """Manages open positions and trade history."""

    def __init__(self, positions_file: str = "data/positions.json"):
        """
        Initialize position manager.

        Args:
            positions_file: Path to positions JSON file
        """
        self.positions_file = positions_file
        self.positions: List[Dict] = []
        self.load()

    def load(self) -> List[Dict]:
        """Load positions from file."""
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.positions = data.get('positions', [])
            except Exception as e:
                print(f"⚠️  Failed to load positions: {e}")
                self.positions = []
        return self.positions

    def save(self) -> bool:
        """Save positions to file."""
        try:
            # Ensure directory exists
            Path(self.positions_file).parent.mkdir(parents=True, exist_ok=True)

            data = {
                'positions': self.positions,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ Failed to save positions: {e}")
            return False

    def add(
        self,
        ticker: str,
        entry_price: float,
        pattern: str,
        signal: Dict,
        stop_loss_pct: float = 0.08,
        take_profit_pct: float = 0.20
    ) -> Dict:
        """
        Add new position.

        Args:
            ticker: Stock ticker symbol
            entry_price: Entry price
            pattern: Pattern name that triggered entry
            signal: Original signal dictionary
            stop_loss_pct: Stop loss percentage (default 8%)
            take_profit_pct: Take profit percentage (default 20%)

        Returns:
            Created position dictionary
        """
        position = {
            'ticker': ticker,
            'entry_price': entry_price,
            'entry_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'pattern': pattern,
            'stop_loss': entry_price * (1 - stop_loss_pct),
            'take_profit': entry_price * (1 + take_profit_pct),
            'signal': signal
        }
        self.positions.append(position)
        self.save()
        print(f"  📝 Position added: {ticker} @ ${entry_price:.2f}")
        return position

    def remove(self, ticker: str) -> Optional[Dict]:
        """
        Remove position by ticker.

        Args:
            ticker: Stock ticker to remove

        Returns:
            Removed position or None
        """
        for pos in self.positions:
            if pos['ticker'] == ticker:
                self.positions.remove(pos)
                self.save()
                return pos
        return None

    def get(self, ticker: str) -> Optional[Dict]:
        """Get position by ticker."""
        for pos in self.positions:
            if pos['ticker'] == ticker:
                return pos
        return None

    def has_position(self, ticker: str) -> bool:
        """Check if position exists for ticker."""
        return any(p['ticker'] == ticker for p in self.positions)

    def get_all(self) -> List[Dict]:
        """Get all positions."""
        return self.positions.copy()

    def calculate_pnl(self, position: Dict, current_price: float) -> float:
        """Calculate P&L percentage for a position."""
        entry_price = position['entry_price']
        return ((current_price - entry_price) / entry_price) * 100

    def get_holding_days(self, position: Dict) -> int:
        """Get number of days position has been held."""
        entry_date = datetime.strptime(position['entry_date'], '%Y-%m-%d %H:%M:%S')
        return (datetime.now() - entry_date).days

    def check_exit_conditions(
        self,
        position: Dict,
        current_price: float,
        low_price: Optional[float] = None,
        max_holding_days: int = 30
    ) -> Optional[str]:
        """
        Check if position should be closed.

        Args:
            position: Position dictionary
            current_price: Current stock price
            low_price: Today's low price (for stop loss check)
            max_holding_days: Maximum days to hold

        Returns:
            Exit reason string or None if should stay open
        """
        check_price = low_price if low_price else current_price

        # Stop loss check
        if check_price <= position['stop_loss']:
            return "Stop Loss (-8%)"

        # Take profit check
        if current_price >= position['take_profit']:
            return "Take Profit (+20%)"

        # Max holding period check
        if self.get_holding_days(position) >= max_holding_days:
            return f"Max Holding Period ({max_holding_days} days)"

        return None
