"""Telegram bot integration for notifications and commands."""

import json
import requests
from datetime import datetime


# Default command keyboard layout
DEFAULT_KEYBOARD = [
    ["📊 /status", "📈 /positions"],
    ["🔍 /scan", "❓ /help"]
]


class TelegramBot:
    """Telegram bot for sending notifications and receiving commands."""

    def __init__(self, token: str, chat_id: str):
        """
        Initialize Telegram bot.

        Args:
            token: Telegram bot token from BotFather
            chat_id: Chat ID to send messages to
        """
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0

    def send_message(
        self,
        message: str,
        parse_mode: str = "HTML",
        keyboard: list | None = None,
        show_keyboard: bool = True
    ) -> bool:
        """
        Send message to Telegram chat.

        Args:
            message: Message text (can include HTML formatting)
            parse_mode: Message parse mode ("HTML" or "Markdown")
            keyboard: Custom keyboard layout (2D list of button texts)
            show_keyboard: If True, show reply keyboard (default keyboard if none provided)

        Returns:
            True if sent successfully
        """
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }

            if show_keyboard:
                kb = keyboard if keyboard else DEFAULT_KEYBOARD
                reply_markup = {
                    "keyboard": kb,
                    "resize_keyboard": True,
                    "is_persistent": True,
                }
                payload['reply_markup'] = json.dumps(reply_markup)

            response = requests.post(f"{self.base_url}/sendMessage", data=payload)
            if response.status_code == 200:
                print("✅ Telegram message sent")
                return True
            else:
                print(f"❌ Telegram send failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Telegram error: {e}")
            return False

    def hide_keyboard(self, message: str = "키보드가 숨겨졌습니다.") -> bool:
        """
        Send message and hide the reply keyboard.

        Args:
            message: Message to send when hiding keyboard

        Returns:
            True if sent successfully
        """
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'reply_markup': json.dumps({"remove_keyboard": True})
            }
            response = requests.post(f"{self.base_url}/sendMessage", data=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Telegram error: {e}")
            return False

    def get_updates(self, timeout: int = 10) -> list:
        """
        Get new messages/commands from Telegram.

        Args:
            timeout: Long polling timeout in seconds

        Returns:
            List of update objects
        """
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': timeout
            }
            response = requests.get(url, params=params, timeout=timeout + 5)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok') and data.get('result'):
                    updates = data['result']
                    if updates:
                        self.last_update_id = updates[-1]['update_id']
                    return updates
            return []
        except Exception as e:
            print(f"⚠️  Telegram update error: {e}")
            return []

    def format_signal_message(self, signal: dict) -> str:
        """
        Format breakout signal as Telegram message.

        Args:
            signal: Signal dictionary with pattern, ticker, prices, etc.

        Returns:
            Formatted HTML message string
        """
        ticker = signal['ticker']

        return f"""
🇺🇸 <b>[Pivot Point Breakout!]</b>

📊 Market: US
🏢 Stock: <b>{ticker}</b>
💰 Current: ${signal['current_price']:.2f}
🎯 Breakout: ${signal['resistance']:.2f}
📈 Breakout %: {signal['breakout_pct']}%

📊 Volume Surge: +{signal['volume_surge']}%

✅ Strong Buy Signal!
⛔ Stop Loss: -7~8% from entry

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    def format_position_close_message(
        self,
        ticker: str,
        pattern: str,
        entry_price: float,
        exit_price: float,
        profit_pct: float,
        holding_days: int,
        reason: str
    ) -> str:
        """Format position close notification."""
        return f"""
🇺🇸 <b>[Position Closed]</b>

🏢 Stock: <b>{ticker}</b>
📊 Pattern: {pattern}
💰 Entry: ${entry_price:.2f}
💵 Exit: ${exit_price:.2f}
{'📈' if profit_pct > 0 else '📉'} P&L: {profit_pct:+.2f}%
📅 Held: {holding_days} days

🔔 Reason: {reason}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
