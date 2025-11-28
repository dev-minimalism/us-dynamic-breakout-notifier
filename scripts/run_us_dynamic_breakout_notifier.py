#!/usr/bin/env python3
"""
Main entry point for the O'Neil Breakout Trading Bot (US Market).

This script runs the complete trading bot with:
- Dynamic stock screening (configurable)
- Breakout signal detection
- Position tracking with stop-loss/take-profit
- Telegram notifications and commands
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
load_dotenv(Path(__file__).parent.parent / ".env")

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from us_dynamic_breakout.bot import (
    BreakoutDetector,
    TelegramBot,
    DBPositionManager,
    WatchlistManager
)
from us_dynamic_breakout.screener import DynamicScreener
from us_dynamic_breakout.data import USStockProvider
from us_dynamic_breakout.utils import get_market_status


class TradingBot:
    """Main trading bot orchestrator for US market."""

    def __init__(self):
        """Initialize the trading bot."""
        # Load settings from environment
        self.telegram_token = os.getenv('TELEGRAM_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

        # Screening settings
        self.use_dynamic_screening = os.getenv('USE_DYNAMIC_SCREENING', 'true').lower() == 'true'
        self.screening_interval_hours = int(os.getenv('SCREENING_INTERVAL_HOURS', '24'))
        self.max_stocks = int(os.getenv('MAX_STOCKS', '100'))

        # Trading settings
        self.scan_interval_seconds = int(os.getenv('SCAN_INTERVAL_SECONDS', '1800'))
        self.stop_loss_pct = float(os.getenv('STOP_LOSS_PCT', '0.08'))
        self.take_profit_pct = float(os.getenv('TAKE_PROFIT_PCT', '0.20'))
        self.min_volume_surge = float(os.getenv('MIN_VOLUME_SURGE', '50.0'))
        self.max_breakout_pct = float(os.getenv('MAX_BREAKOUT_PCT', '5.0'))

        # SSH settings
        ssh_host = os.getenv('SSH_HOST', '')
        ssh_port = int(os.getenv('SSH_PORT', '22'))
        ssh_user = os.getenv('SSH_USER', '')
        ssh_key_path = os.path.expanduser(os.getenv('SSH_KEY_PATH', ''))

        # Database settings
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = int(os.getenv('DB_PORT', '5432'))
        db_name = os.getenv('DB_NAME', '')
        db_user = os.getenv('DB_USER', '')
        db_password = os.getenv('DB_PASSWORD', '')

        # Validate required settings
        if not self.telegram_token or not self.telegram_chat_id:
            print("❌ Telegram credentials not configured!")
            print("   Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env file")
            sys.exit(1)

        # Initialize components
        self.telegram = TelegramBot(self.telegram_token, self.telegram_chat_id)
        self.watchlist = WatchlistManager("data/watchlist.json")
        self.positions = DBPositionManager(
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
            ssh_key_path=ssh_key_path,
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password
        )
        self.detector = BreakoutDetector(
            min_volume_surge=self.min_volume_surge,
            max_breakout_pct=self.max_breakout_pct
        )
        self.screener = DynamicScreener()

        self.last_screening_time = self.watchlist.last_screening_time
        self.is_scanning = False
        self.is_screening = False

        print("✅ Trading bot initialized (US Market)")
        print(f"   Mode: {'Dynamic Screening' if self.use_dynamic_screening else 'Manual Watchlist'}")
        print(f"   Stocks: {len(self.watchlist.tickers)}")
        print(f"   Positions: {len(self.positions.positions)}")

    def needs_rescreening(self) -> bool:
        """Check if rescreening is needed."""
        if not self.use_dynamic_screening:
            return False
        if self.last_screening_time is None:
            return True
        hours_passed = (datetime.now() - self.last_screening_time).total_seconds() / 3600
        return hours_passed >= self.screening_interval_hours

    def run_screening(self):
        """Run dynamic stock screening."""
        if self.is_screening:
            return

        self.is_screening = True
        try:
            self.telegram.send_message(
                "🔄 <b>Dynamic Screening Started</b>\n\n"
                "Finding US stocks that meet criteria...\n"
                "This may take 5-10 minutes."
            )

            tickers = self.screener.run_full_scan(max_stocks=self.max_stocks)

            self.watchlist.update_from_screening(tickers)
            self.last_screening_time = datetime.now()

            self.telegram.send_message(
                f"✅ <b>Screening Complete!</b>\n\n"
                f"📊 Updated watchlist:\n"
                f"   🇺🇸 US: {len(tickers)} stocks\n\n"
                f"⏰ Next screening: {self.screening_interval_hours}h"
            )

        except Exception as e:
            self.telegram.send_message(f"❌ Screening error: {e}")
        finally:
            self.is_screening = False

    def run_scan(self):
        """Run breakout signal scan."""
        if self.is_scanning:
            return []

        self.is_scanning = True
        market_status = get_market_status()

        if not market_status['is_open']:
            msg = "⏸️ US market closed. Skipping scan."
            print(msg)
            self.telegram.send_message(msg)
            self.is_scanning = False
            return []

        try:
            signals = self.detector.scan_watchlist(self.watchlist.tickers)

            # Process signals
            for signal in signals:
                # Send notification
                msg = self.telegram.format_signal_message(signal)
                self.telegram.send_message(msg)

                # Add position if not already held
                if not self.positions.has_position(signal['ticker']):
                    self.positions.add(
                        ticker=signal['ticker'],
                        entry_price=signal['current_price'],
                        pattern=signal['pattern'],
                        signal=signal
                    )

            if not signals:
                print("⚪ No signals found")
                self.telegram.send_message(
                    f"✅ Scan complete. No breakout signals found.\n"
                    f"📊 Scanned: {len(self.watchlist.tickers)} stocks"
                )

            return signals

        finally:
            self.is_scanning = False

    def check_positions(self):
        """Check and manage open positions."""
        for pos in self.positions.get_all():
            try:
                df = USStockProvider.get_stock_data(pos['ticker'], period='5d')

                if df is None or len(df) == 0:
                    continue

                current_price = df['Close'].iloc[-1]
                low_price = df['Low'].iloc[-1]

                exit_reason = self.positions.check_exit_conditions(
                    pos, current_price, low_price
                )

                if exit_reason:
                    # Close position
                    profit_pct = self.positions.calculate_pnl(pos, current_price)
                    holding_days = self.positions.get_holding_days(pos)

                    msg = self.telegram.format_position_close_message(
                        pos['ticker'], pos['pattern'],
                        pos['entry_price'], current_price,
                        profit_pct, holding_days, exit_reason
                    )
                    self.telegram.send_message(msg)

                    # Record trade before removing position
                    self.positions.record_trade(pos, current_price, exit_reason)
                    self.positions.remove(pos['ticker'])

            except Exception as e:
                print(f"  Position check error for {pos['ticker']}: {e}")

    def handle_command(self, text: str) -> str:
        """Handle Telegram command and return response."""
        parts = text.strip().split()
        if not parts:
            return None

        cmd = parts[0].lower()

        if cmd in ['/help', '/start']:
            return self._get_help_text()
        elif cmd == '/scan':
            return 'SCAN'
        elif cmd == '/rescreen':
            return 'RESCREEN'
        elif cmd == '/status':
            return self._get_status_text()
        elif cmd == '/list':
            return self._get_watchlist_text()
        elif cmd == '/positions':
            return self._get_positions_text()
        elif cmd == '/trades':
            return self._get_trades_text()
        elif cmd == '/stats':
            return self._get_stats_text()
        elif cmd == '/add' and len(parts) > 1:
            success, msg = self.watchlist.add(parts[1])
            return msg
        elif cmd == '/remove' and len(parts) > 1:
            success, msg = self.watchlist.remove(parts[1])
            return msg
        elif cmd == '/close' and len(parts) > 1:
            return self._close_position(parts[1].upper())

        return None

    def _close_position(self, ticker: str) -> str:
        """Manually close a position."""
        position = self.positions.get(ticker)
        if not position:
            return f"❌ No position found for {ticker}"

        # Get current price for P&L calculation
        df = USStockProvider.get_stock_data(ticker, period='5d')
        if df is not None and len(df) > 0:
            current_price = df['Close'].iloc[-1]
            profit_pct = self.positions.calculate_pnl(position, current_price)
            holding_days = self.positions.get_holding_days(position)
        else:
            current_price = position['entry_price']
            profit_pct = 0
            holding_days = 0

        # Record trade before removing position
        self.positions.record_trade(position, current_price, "Manual Close")
        self.positions.remove(ticker)

        return (
            f"✅ <b>Position Closed</b>\n\n"
            f"📊 {ticker}\n"
            f"💰 Entry: ${position['entry_price']:.2f}\n"
            f"💵 Exit: ${current_price:.2f}\n"
            f"📈 P&L: {profit_pct:+.2f}%\n"
            f"📅 Held: {holding_days} days\n"
            f"📝 Reason: Manual Close"
        )

    def _get_help_text(self) -> str:
        return """
🤖 <b>O'Neil Breakout Bot Commands (US)</b>

<b>Scanning:</b>
/scan - Run immediate market scan
/rescreen - Run dynamic screening

<b>Watchlist:</b>
/list - Show watchlist
/add [TICKER] - Add stock (e.g., /add AAPL)
/remove [TICKER] - Remove stock

<b>Positions:</b>
/positions - Show open positions
/close [TICKER] - Close position manually

<b>Trade History:</b>
/trades - Recent trade history
/stats - Trading statistics

<b>Status:</b>
/status - Market and bot status
/help - Show this help
"""

    def _get_status_text(self) -> str:
        status = get_market_status()
        return f"""
📊 <b>Bot Status</b>

⏰ Time: {status['time']}
🇺🇸 US Market: {'Open' if status['is_open'] else 'Closed'}

📈 Watchlist: {len(self.watchlist.tickers)} stocks
📊 Positions: {len(self.positions.positions)}
"""

    def _get_watchlist_text(self) -> str:
        count = self.watchlist.get_count()
        preview = ', '.join(self.watchlist.tickers[:10])
        if count > 10:
            preview += f" +{count - 10} more"

        return f"""
📋 <b>Watchlist</b>

🇺🇸 US ({count}): {preview}
"""

    def _get_positions_text(self) -> str:
        positions = self.positions.get_all()
        if not positions:
            return "📊 No open positions"

        text = f"📊 <b>Positions</b> ({len(positions)})\n"
        for p in positions[:5]:
            text += f"\n• {p['ticker']} @ ${p['entry_price']:.2f}"
        return text

    def _get_trades_text(self) -> str:
        trades = self.positions.get_trades(limit=10)
        if not trades:
            return "📜 No trade history"

        text = "📜 <b>Recent Trades</b>\n"
        for t in trades:
            pnl = t['profit_pct']
            emoji = "🟢" if pnl > 0 else "🔴"
            text += f"\n{emoji} {t['ticker']} {pnl:+.1f}% ({t['exit_reason']})"
        return text

    def _get_stats_text(self) -> str:
        stats = self.positions.get_trade_stats()
        if stats['total_trades'] == 0:
            return "📈 No trades yet"

        return f"""
📈 <b>Trading Stats</b>

🎯 Total Trades: {stats['total_trades']}
✅ Wins: {stats['winning_trades']} | ❌ Losses: {stats['losing_trades']}
📊 Win Rate: {stats['win_rate']:.1f}%

💰 Avg Profit: {stats['avg_profit_pct']:+.2f}%
🟢 Avg Win: {stats['avg_win_pct']:+.2f}%
🔴 Avg Loss: {stats['avg_loss_pct']:+.2f}%

📅 Avg Holding: {stats['avg_holding_days']:.1f} days
💵 Total P&L: {stats['total_profit_pct']:+.2f}%
"""

    def start_command_listener(self):
        """Start background thread for Telegram commands."""
        def listener():
            while True:
                try:
                    updates = self.telegram.get_updates(timeout=10)
                    for update in updates:
                        if 'message' in update and 'text' in update['message']:
                            text = update['message']['text']
                            chat_id = str(update['message']['chat']['id'])

                            if chat_id == self.telegram_chat_id:
                                response = self.handle_command(text)

                                if response == 'SCAN':
                                    self.telegram.send_message("🔍 Starting scan...")
                                    threading.Thread(
                                        target=self.run_scan,
                                        daemon=True
                                    ).start()
                                elif response == 'RESCREEN':
                                    self.telegram.send_message("🔄 Starting screening...")
                                    threading.Thread(
                                        target=self.run_screening,
                                        daemon=True
                                    ).start()
                                elif response:
                                    self.telegram.send_message(response)
                except Exception as e:
                    print(f"Command listener error: {e}")
                time.sleep(2)

        thread = threading.Thread(target=listener, daemon=True)
        thread.start()
        print("✅ Command listener started")

    def run(self):
        """Main bot loop."""
        self.start_command_listener()

        # Initial screening if needed
        if self.needs_rescreening():
            print("\n🚀 Running initial screening...")
            self.run_screening()

        # Send startup message
        self.telegram.send_message(
            f"🤖 <b>O'Neil Breakout Bot Started (US)</b>\n\n"
            f"📊 Watchlist: {len(self.watchlist.tickers)} stocks\n"
            f"📈 Scan interval: {self.scan_interval_seconds // 60} min\n\n"
            f"Send /help for commands"
        )

        # Main loop
        try:
            while True:
                # Check for rescreening
                if self.needs_rescreening():
                    self.run_screening()

                # Run scan
                print(f"\n{'='*50}")
                print(f"🔍 Scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.check_positions()
                self.run_scan()

                # Wait for next scan
                next_scan = datetime.now() + timedelta(seconds=self.scan_interval_seconds)
                print(f"⏰ Next scan: {next_scan.strftime('%H:%M:%S')}")
                time.sleep(self.scan_interval_seconds)

        except KeyboardInterrupt:
            print("\n\n⛔ Bot stopped")
            self.telegram.send_message("⛔ Bot stopped")


def main():
    """Entry point."""
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()
