"""Position management using PostgreSQL database with SSH tunnel."""

import json
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from sshtunnel import SSHTunnelForwarder


class DBPositionManager:
    """Manages positions in PostgreSQL database via SSH tunnel."""

    def __init__(
        self,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        ssh_key_path: str,
        db_host: str,
        db_port: int,
        db_name: str,
        db_user: str,
        db_password: str
    ):
        """
        Initialize DB position manager.

        Args:
            ssh_host: SSH server hostname
            ssh_port: SSH server port
            ssh_user: SSH username
            ssh_key_path: Path to SSH private key
            db_host: Database host (usually localhost via tunnel)
            db_port: Database port
            db_name: Database name
            db_user: Database username
            db_password: Database password
        """
        self.ssh_config = {
            'ssh_host': ssh_host,
            'ssh_port': ssh_port,
            'ssh_user': ssh_user,
            'ssh_key_path': ssh_key_path,
        }
        self.db_config = {
            'host': db_host,
            'port': db_port,
            'dbname': db_name,
            'user': db_user,
            'password': db_password,
        }
        self._tunnel = None
        self._local_port = None

    @contextmanager
    def _get_connection(self):
        """Get database connection via SSH tunnel."""
        tunnel = SSHTunnelForwarder(
            (self.ssh_config['ssh_host'], self.ssh_config['ssh_port']),
            ssh_username=self.ssh_config['ssh_user'],
            ssh_pkey=self.ssh_config['ssh_key_path'],
            remote_bind_address=(self.db_config['host'], self.db_config['port'])
        )
        tunnel.start()

        try:
            conn = psycopg2.connect(
                host='127.0.0.1',
                port=tunnel.local_bind_port,
                dbname=self.db_config['dbname'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                cursor_factory=RealDictCursor
            )
            try:
                yield conn
            finally:
                conn.close()
        finally:
            tunnel.stop()

    @property
    def positions(self) -> List[Dict]:
        """Get all positions (for compatibility)."""
        return self.get_all()

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
            'entry_date': datetime.now(),
            'pattern': pattern,
            'stop_loss': entry_price * (1 - stop_loss_pct),
            'take_profit': entry_price * (1 + take_profit_pct),
            'signal': signal
        }

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO positions (ticker, entry_price, entry_date, pattern, stop_loss, take_profit, signal_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker) DO UPDATE SET
                        entry_price = EXCLUDED.entry_price,
                        entry_date = EXCLUDED.entry_date,
                        pattern = EXCLUDED.pattern,
                        stop_loss = EXCLUDED.stop_loss,
                        take_profit = EXCLUDED.take_profit,
                        signal_data = EXCLUDED.signal_data,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (
                    ticker,
                    entry_price,
                    position['entry_date'],
                    pattern,
                    position['stop_loss'],
                    position['take_profit'],
                    json.dumps(signal)
                ))
                conn.commit()

        print(f"  [DB] Position added: {ticker} @ ${entry_price:.2f}")
        return position

    def remove(self, ticker: str) -> Optional[Dict]:
        """
        Remove position by ticker.

        Args:
            ticker: Stock ticker to remove

        Returns:
            Removed position or None
        """
        position = self.get(ticker)
        if not position:
            return None

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM positions WHERE ticker = %s", (ticker,))
                conn.commit()

        print(f"  [DB] Position removed: {ticker}")
        return position

    def get(self, ticker: str) -> Optional[Dict]:
        """Get position by ticker."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticker, entry_price, entry_date, pattern, stop_loss, take_profit, signal_data
                    FROM positions WHERE ticker = %s
                """, (ticker,))
                row = cur.fetchone()

        if not row:
            return None

        return self._row_to_position(row)

    def has_position(self, ticker: str) -> bool:
        """Check if position exists for ticker."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM positions WHERE ticker = %s", (ticker,))
                return cur.fetchone() is not None

    def get_all(self) -> List[Dict]:
        """Get all positions."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticker, entry_price, entry_date, pattern, stop_loss, take_profit, signal_data
                    FROM positions ORDER BY entry_date
                """)
                rows = cur.fetchall()

        return [self._row_to_position(row) for row in rows]

    def _row_to_position(self, row: Dict) -> Dict:
        """Convert database row to position dictionary."""
        entry_date = row['entry_date']
        if isinstance(entry_date, str):
            entry_date = datetime.strptime(entry_date, '%Y-%m-%d %H:%M:%S')

        return {
            'ticker': row['ticker'],
            'entry_price': float(row['entry_price']),
            'entry_date': entry_date.strftime('%Y-%m-%d %H:%M:%S'),
            'pattern': row['pattern'],
            'stop_loss': float(row['stop_loss']),
            'take_profit': float(row['take_profit']),
            'signal': row['signal_data'] if row['signal_data'] else {}
        }

    def calculate_pnl(self, position: Dict, current_price: float) -> float:
        """Calculate P&L percentage for a position."""
        entry_price = position['entry_price']
        return ((current_price - entry_price) / entry_price) * 100

    def get_holding_days(self, position: Dict) -> int:
        """Get number of days position has been held."""
        entry_date_str = position['entry_date']
        if isinstance(entry_date_str, str):
            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d %H:%M:%S')
        else:
            entry_date = entry_date_str
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

    # ========================================
    # Trade History Methods
    # ========================================

    def record_trade(
        self,
        position: Dict,
        exit_price: float,
        exit_reason: str
    ) -> Dict:
        """
        Record a completed trade to history.

        Args:
            position: Position dictionary being closed
            exit_price: Exit price
            exit_reason: Reason for exit

        Returns:
            Trade record dictionary
        """
        entry_date_str = position['entry_date']
        if isinstance(entry_date_str, str):
            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d %H:%M:%S')
        else:
            entry_date = entry_date_str

        exit_date = datetime.now()
        profit_pct = self.calculate_pnl(position, exit_price)
        holding_days = (exit_date - entry_date).days

        trade = {
            'ticker': position['ticker'],
            'pattern': position['pattern'],
            'entry_date': entry_date,
            'entry_price': position['entry_price'],
            'exit_date': exit_date,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'profit_pct': profit_pct,
            'holding_days': holding_days,
            'signal_data': position.get('signal', {})
        }

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trades
                    (ticker, pattern, entry_date, entry_price, exit_date, exit_price,
                     exit_reason, profit_pct, holding_days, signal_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    trade['ticker'],
                    trade['pattern'],
                    trade['entry_date'],
                    trade['entry_price'],
                    trade['exit_date'],
                    trade['exit_price'],
                    trade['exit_reason'],
                    trade['profit_pct'],
                    trade['holding_days'],
                    json.dumps(trade['signal_data'])
                ))
                conn.commit()

        print(f"  [DB] Trade recorded: {trade['ticker']} | {profit_pct:+.2f}% | {exit_reason}")
        return trade

    def get_trades(self, limit: int = 50) -> List[Dict]:
        """Get recent trade history."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticker, pattern, entry_date, entry_price,
                           exit_date, exit_price, exit_reason, profit_pct, holding_days
                    FROM trades
                    ORDER BY exit_date DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()

        return [dict(row) for row in rows]

    def get_trade_stats(self) -> Dict:
        """Get trading statistics."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN profit_pct > 0 THEN 1 END) as winning_trades,
                        COUNT(CASE WHEN profit_pct <= 0 THEN 1 END) as losing_trades,
                        COALESCE(AVG(profit_pct), 0) as avg_profit_pct,
                        COALESCE(AVG(CASE WHEN profit_pct > 0 THEN profit_pct END), 0) as avg_win_pct,
                        COALESCE(AVG(CASE WHEN profit_pct <= 0 THEN profit_pct END), 0) as avg_loss_pct,
                        COALESCE(SUM(profit_pct), 0) as total_profit_pct,
                        COALESCE(AVG(holding_days), 0) as avg_holding_days
                    FROM trades
                """)
                row = cur.fetchone()

        total = row['total_trades'] or 0
        wins = row['winning_trades'] or 0

        return {
            'total_trades': total,
            'winning_trades': wins,
            'losing_trades': row['losing_trades'] or 0,
            'win_rate': (wins / total * 100) if total > 0 else 0,
            'avg_profit_pct': float(row['avg_profit_pct'] or 0),
            'avg_win_pct': float(row['avg_win_pct'] or 0),
            'avg_loss_pct': float(row['avg_loss_pct'] or 0),
            'total_profit_pct': float(row['total_profit_pct'] or 0),
            'avg_holding_days': float(row['avg_holding_days'] or 0)
        }
