#!/usr/bin/env python3
"""
Main entry point for the O'Neil Breakout Trading Bot (US Market).

This script runs the complete trading bot with:
- Dynamic stock screening (configurable)
- Breakout signal detection
- Position tracking with stop-loss/take-profit
- Telegram notifications and commands
"""

import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from us_dynamic_breakout.bot import (
    BreakoutDetector,
    TelegramBot,
    PositionManager,
    WatchlistManager
)
from us_dynamic_breakout.screener import DynamicScreener
from us_dynamic_breakout.data import USStockProvider
from us_dynamic_breakout.utils import get_market_status
from config import get_settings


class TradingBot:
    """Main trading bot orchestrator for US market."""

    def __init__(self):
        """Initialize the trading bot."""
        self.settings = get_settings()

        # Validate required settings
        if not self.settings.telegram.token or not self.settings.telegram.chat_id:
            print("❌ Telegram credentials not configured!")
            print("   Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID environment variables")
            print("   Or create .env file with these values")
            sys.exit(1)

        # Initialize components
        self.telegram = TelegramBot(
            self.settings.telegram.token,
            self.settings.telegram.chat_id
        )
        self.watchlist = WatchlistManager(self.settings.paths.watchlist_file)
        self.positions = PositionManager(self.settings.paths.positions_file)
        self.detector = BreakoutDetector(
            min_volume_surge=self.settings.trading.min_volume_surge,
            max_breakout_pct=self.settings.trading.max_breakout_pct
        )
        self.screener = DynamicScreener()

        self.use_dynamic_screening = self.settings.screening.use_dynamic_screening
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
        return hours_passed >= self.settings.screening.screening_interval_hours

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

            tickers = self.screener.run_full_scan(
                max_stocks=self.settings.screening.max_stocks
            )

            self.watchlist.update_from_screening(tickers)
            self.last_screening_time = datetime.now()

            self.telegram.send_message(
                f"✅ <b>Screening Complete!</b>\n\n"
                f"📊 Updated watchlist:\n"
                f"   🇺🇸 US: {len(tickers)} stocks\n\n"
                f"⏰ Next screening: {self.settings.screening.screening_interval_hours}h"
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
            print("⏸️  US market closed. Skipping scan.")
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
        elif cmd == '/add' and len(parts) > 1:
            success, msg = self.watchlist.add(parts[1])
            return msg
        elif cmd == '/remove' and len(parts) > 1:
            success, msg = self.watchlist.remove(parts[1])
            return msg

        return None

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

                            if chat_id == self.settings.telegram.chat_id:
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
            f"📈 Scan interval: {self.settings.trading.scan_interval_seconds // 60} min\n\n"
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
                next_scan = datetime.now() + timedelta(
                    seconds=self.settings.trading.scan_interval_seconds
                )
                print(f"⏰ Next scan: {next_scan.strftime('%H:%M:%S')}")
                time.sleep(self.settings.trading.scan_interval_seconds)

        except KeyboardInterrupt:
            print("\n\n⛔ Bot stopped")
            self.telegram.send_message("⛔ Bot stopped")


def main():
    """Entry point."""
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()
