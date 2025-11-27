# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

William O'Neil breakout trading bot with dynamic stock screening. Monitors US markets (S&P 500, NASDAQ 100) for pivot point breakout signals and sends alerts via Telegram.

## Commands

```bash
# Run the main trading bot
python scripts/run_bot.py

# Run dynamic screener standalone
python scripts/run_screener.py
python scripts/run_screener.py --max 100

# Run backtest
python scripts/run_backtest.py
python scripts/run_backtest.py --capital 100000 --start 2023-01-02 --end 2025-11-18

# Install as package (editable)
pip install -e .

# Linting and formatting
ruff check src/                  # Lint
ruff check --fix src/            # Lint and auto-fix
black src/                       # Format code
mypy src/                        # Type check

# Testing
pytest tests/                    # Run tests
pytest tests/test_foo.py -k "test_name"  # Run single test
pytest --cov=src/us_dynamic_breakout tests/   # With coverage
```

## Architecture

### Data Flow

```
DynamicScreener → filters stocks → WatchlistManager (watchlist.json)
                                          ↓
BreakoutDetector → scans watchlist → signals
                                          ↓
TelegramBot ← notifications ← PositionManager (positions.json)
```

### Core Components

**`src/us_dynamic_breakout/bot/detector.py`** - Core breakout detection logic
- `detect_pivot_breakout()`: A valid signal requires:
  - Price breaks above 20-day high (resistance)
  - Volume surge >= 50% above 30-day average
  - Breakout not too extended (within 5% of resistance)

**`src/us_dynamic_breakout/screener/screener.py`** - Stock universe filtering
- Filters by market cap, volume, price before breakout scanning
- US: >=$500M cap, >=$5 price, >=50K volume

**`src/us_dynamic_breakout/bot/position.py`** - Position management
- Auto-close: -8% stop-loss, +20% take-profit, 30-day max hold

**`src/us_dynamic_breakout/backtest/engine.py`** - No look-ahead bias backtesting
- Screens stocks daily using only data available at that time

**`src/us_dynamic_breakout/data/us_provider.py`** - Data provider
- `USStockProvider`: yfinance wrapper with hardcoded S&P500/NASDAQ100 tickers

**`config/settings.py`** - Settings dataclasses loaded from `.env`

**`scripts/run_bot.py`** - `TradingBot` class orchestrates all components

### Configuration

Settings loaded from `.env` file (copy from `.env.example`):

Required:
- `TELEGRAM_TOKEN`: Bot token from @BotFather
- `TELEGRAM_CHAT_ID`: Chat ID for notifications

Optional: `SCREENING_INTERVAL_HOURS`, `MAX_STOCKS`, `SCAN_INTERVAL_SECONDS`, `STOP_LOSS_PCT`, `TAKE_PROFIT_PCT`

### API Rate Limits

- yfinance: 0.1s sleep between requests
