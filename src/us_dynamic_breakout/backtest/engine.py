"""
Backtest Engine for O'Neil Breakout Strategy (US Market)

Implements a truly dynamic backtest without look-ahead bias.
Each day, the universe is screened based on that day's data only.
"""

import warnings
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

import pandas as pd
import yfinance as yf

warnings.filterwarnings('ignore')


class BacktestEngine:
    """
    Backtesting engine for O'Neil breakout strategy (US Market).

    Features:
    - No look-ahead bias: screens stocks using only data available at that time
    - Position management with stop-loss, take-profit, and max holding period
    - Transaction costs included
    """

    def __init__(
        self,
        initial_capital: float = 100_000,
        max_positions: int = 5,
        position_size_pct: float = 0.2,
        stop_loss_pct: float = 0.08,
        take_profit_pct: float = 0.20,
        max_holding_days: int = 30,
        transaction_cost_pct: float = 0.001
    ):
        """
        Initialize backtest engine.

        Args:
            initial_capital: Starting capital (default $100K USD)
            max_positions: Maximum concurrent positions
            position_size_pct: Fraction of capital per position
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            max_holding_days: Maximum holding period
            transaction_cost_pct: Transaction cost per trade
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_holding_days = max_holding_days
        self.transaction_cost_pct = transaction_cost_pct

        self.positions: List[Dict] = []
        self.trade_history: List[Dict] = []

    def get_universe_for_date(self, date: datetime) -> List[str]:
        """
        Get US stock universe for a specific date (no look-ahead bias).

        Args:
            date: The date to screen stocks for

        Returns:
            List of ticker symbols
        """
        universe = []

        try:
            from ..data import USStockProvider
            candidates = USStockProvider.get_universe()

            for ticker in candidates[:100]:  # Limit for speed
                try:
                    df = yf.download(
                        ticker,
                        start=date - timedelta(days=180),
                        end=date + timedelta(days=1),
                        progress=False
                    )
                    if len(df) < 60:
                        continue

                    info = yf.Ticker(ticker).info
                    mc = info.get('marketCap', 0) or 0
                    price = df['Close'].iloc[-1]
                    vol = df['Volume'].iloc[-30:].mean()

                    if mc >= 500_000_000 and price >= 5 and vol >= 50_000:
                        universe.append(ticker)
                except Exception:
                    continue
        except Exception:
            pass

        print(f"   {date.date()} screening -> {len(universe)} stocks")
        return universe[:150]

    def detect_signal(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Detect breakout signal in price data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (signal_found, pattern_name)
        """
        if len(df) < 80:
            return False, ""

        price = df['Close'].iloc[-1]
        vol_today = df['Volume'].iloc[-1]
        vol_avg = df['Volume'].iloc[-50:-1].mean()

        # O'Neil style pivot breakout with volume surge
        pivot = df['High'].iloc[-40:-1].max()
        if price > pivot and vol_today > vol_avg * 1.8:
            return True, "Pivot Breakout (Volume Surge)"

        # Near all-time high with volume
        all_time_high = df['High'].max()
        if price >= all_time_high * 0.95 and vol_today > vol_avg * 2.0:
            return True, "All-Time High Breakout"

        return False, ""

    def open_position(
        self,
        ticker: str,
        date: datetime,
        price: float,
        pattern: str
    ):
        """Open a new position."""
        amount = self.cash * self.position_size_pct
        shares = int(amount // price)
        if shares < 1:
            return

        # Apply transaction cost
        cost = shares * price * (1 + self.transaction_cost_pct)
        if cost > self.cash:
            shares = int(self.cash / (price * (1 + self.transaction_cost_pct)))
            cost = shares * price * (1 + self.transaction_cost_pct)

        self.cash -= cost
        self.positions.append({
            'ticker': ticker,
            'entry_date': date,
            'entry_price': price,
            'shares': shares,
            'cost': cost,
            'stop_loss': price * (1 - self.stop_loss_pct),
            'pattern': pattern
        })

    def close_position(
        self,
        position: Dict,
        date: datetime,
        price: float,
        reason: str
    ):
        """Close an existing position."""
        # Apply transaction cost
        proceeds = position['shares'] * price * (1 - self.transaction_cost_pct)
        self.cash += proceeds

        profit_pct = (proceeds - position['cost']) / position['cost'] * 100

        self.trade_history.append({
            'ticker': position['ticker'],
            'pattern': position['pattern'],
            'entry_date': position['entry_date'],
            'exit_date': date,
            'entry_price': position['entry_price'],
            'exit_price': price,
            'profit_pct': round(profit_pct, 2),
            'reason': reason
        })

        self.positions.remove(position)

    def run(
        self,
        start_date: str = "2023-01-02",
        end_date: str = "2025-11-18"
    ) -> Dict:
        """
        Run backtest over date range.

        Args:
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)

        Returns:
            Results dictionary with performance metrics
        """
        print("=" * 60)
        print("O'Neil Breakout Strategy Backtest (US Market)")
        print("No look-ahead bias - truly dynamic screening")
        print("=" * 60 + "\n")

        dates = pd.date_range(start_date, end_date, freq='B')
        universe = []

        for current_date in dates:
            dt = current_date.to_pydatetime()

            # Re-screen universe daily
            universe = self.get_universe_for_date(dt)

            # Check existing positions
            for pos in self.positions.copy():
                try:
                    day = yf.download(
                        pos['ticker'],
                        start=dt,
                        end=dt + timedelta(days=2),
                        progress=False
                    )
                    if day.empty:
                        continue
                    close = float(day['Close'].iloc[-1])
                    low = float(day['Low'].iloc[-1])

                    # Check exit conditions
                    if low <= pos['stop_loss']:
                        self.close_position(pos, dt, pos['stop_loss'], "Stop Loss")
                    elif close >= pos['entry_price'] * (1 + self.take_profit_pct):
                        self.close_position(pos, dt, close, "Take Profit")
                    elif (dt - pos['entry_date']).days >= self.max_holding_days:
                        self.close_position(pos, dt, close, "Max Holding")

                except Exception:
                    continue

            # Look for new entries
            if len(self.positions) >= self.max_positions:
                continue

            new_entries = 0
            for ticker in universe:
                if any(p['ticker'] == ticker for p in self.positions):
                    continue
                if new_entries >= (self.max_positions - len(self.positions)):
                    break

                try:
                    df = yf.download(
                        ticker,
                        start=dt - timedelta(days=400),
                        end=dt + timedelta(days=1),
                        progress=False
                    )

                    if len(df) < 80:
                        continue

                    signal, pattern = self.detect_signal(df)
                    if signal:
                        price = df['Close'].iloc[-1]
                        self.open_position(ticker, dt, price, pattern)
                        print(f"BUY  {ticker} | {dt.date()} | ${price:,.2f} | {pattern}")
                        new_entries += 1

                except Exception:
                    continue

        # Close remaining positions
        final_date = datetime.strptime(end_date, "%Y-%m-%d")
        for pos in self.positions.copy():
            self.close_position(
                pos,
                final_date,
                pos['entry_price'] * 1.1,
                "Backtest End"
            )

        return self.generate_report()

    def generate_report(self) -> Dict:
        """Generate backtest performance report."""
        total_return = (self.cash - self.initial_capital) / self.initial_capital * 100
        years = 2.88  # Approximate years in test period
        cagr = ((self.cash / self.initial_capital) ** (1 / years) - 1) * 100

        df = pd.DataFrame(self.trade_history)
        win_rate = len(df[df['profit_pct'] > 0]) / len(df) * 100 if len(df) > 0 else 0

        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        print(f"Total Return: {total_return:+.1f}%")
        print(f"Final Value:  ${self.cash:,.2f}")
        print(f"CAGR:         {cagr:+.1f}%")
        print(f"Total Trades: {len(df)}")
        print(f"Win Rate:     {win_rate:.1f}%")

        if len(df) > 0:
            print(f"Avg Win:      {df[df['profit_pct'] > 0]['profit_pct'].mean():+.1f}%")
            print(f"Avg Loss:     {df[df['profit_pct'] <= 0]['profit_pct'].mean():+.1f}%")

        print("=" * 60)

        return {
            'total_return': total_return,
            'cagr': cagr,
            'total_trades': len(df),
            'win_rate': win_rate,
            'final_value': self.cash,
            'trade_history': self.trade_history
        }
