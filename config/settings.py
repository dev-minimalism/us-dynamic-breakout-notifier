"""
Application settings and configuration for US market.

Settings are loaded from .env file or environment variables.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# Load .env file from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class TelegramSettings:
    """Telegram bot settings."""
    token: str = ""
    chat_id: str = ""


@dataclass
class ScreeningSettings:
    """Stock screening settings."""
    use_dynamic_screening: bool = True
    screening_interval_hours: int = 24
    max_stocks: int = 100
    min_market_cap_usd: int = 500_000_000  # $500M
    min_avg_volume: int = 50_000
    min_price_usd: float = 5.0


@dataclass
class TradingSettings:
    """Trading parameters."""
    scan_interval_seconds: int = 1800  # 30 minutes
    stop_loss_pct: float = 0.08  # 8%
    take_profit_pct: float = 0.20  # 20%
    max_holding_days: int = 30
    min_volume_surge: float = 50.0  # 50%
    max_breakout_pct: float = 5.0  # 5%


@dataclass
class PathSettings:
    """File path settings."""
    data_dir: str = "data"
    watchlist_file: str = "data/watchlist.json"
    positions_file: str = "data/positions.json"


@dataclass
class Settings:
    """Main application settings container."""
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    screening: ScreeningSettings = field(default_factory=ScreeningSettings)
    trading: TradingSettings = field(default_factory=TradingSettings)
    paths: PathSettings = field(default_factory=PathSettings)


def get_settings() -> Settings:
    """
    Load settings from .env file or environment variables.

    Required:
        TELEGRAM_TOKEN: Telegram bot token from @BotFather
        TELEGRAM_CHAT_ID: Chat ID for notifications

    Optional:
        SCREENING_INTERVAL_HOURS: Hours between screenings (default: 24)
        MAX_STOCKS: Max stocks to screen (default: 100)
        SCAN_INTERVAL_SECONDS: Seconds between scans (default: 1800)
        STOP_LOSS_PCT: Stop loss percentage (default: 0.08)
        TAKE_PROFIT_PCT: Take profit percentage (default: 0.20)

    Returns:
        Settings object with loaded configuration
    """
    settings = Settings()

    # Required settings
    settings.telegram.token = os.getenv('TELEGRAM_TOKEN', '')
    settings.telegram.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

    # Optional screening settings
    if os.getenv('SCREENING_INTERVAL_HOURS'):
        settings.screening.screening_interval_hours = int(os.getenv('SCREENING_INTERVAL_HOURS'))

    if os.getenv('MAX_STOCKS'):
        settings.screening.max_stocks = int(os.getenv('MAX_STOCKS'))

    # Optional trading settings
    if os.getenv('SCAN_INTERVAL_SECONDS'):
        settings.trading.scan_interval_seconds = int(os.getenv('SCAN_INTERVAL_SECONDS'))

    if os.getenv('STOP_LOSS_PCT'):
        settings.trading.stop_loss_pct = float(os.getenv('STOP_LOSS_PCT'))

    if os.getenv('TAKE_PROFIT_PCT'):
        settings.trading.take_profit_pct = float(os.getenv('TAKE_PROFIT_PCT'))

    return settings
