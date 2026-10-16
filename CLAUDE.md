# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

William O'Neil pivot-breakout trading bot for US stocks (S&P 500 + NASDAQ 100). Screens a universe, scans a watchlist for breakouts on a fixed schedule, tracks positions in PostgreSQL, and sends alerts/accepts commands via Telegram. Runs long-lived (`nohup`), designed for a host in KST (Korea Standard Time).

## Commands

```bash
# Install (dev extras include pytest, ruff, black, mypy)
pip install -e ".[dev]"

# Run the bot (long-running; needs .env with Telegram + SSH + DB settings)
python scripts/run_us_dynamic_breakout_notifier.py
nohup python -u scripts/run_us_dynamic_breakout_notifier.py &   # background
tail -f logs/bot.log                                            # follow logs
pkill -f run_us_dynamic_breakout_notifier                       # stop

# Screener only (no Telegram/DB needed)
python scripts/run_screener.py --max 100

# Backtest (slow: downloads via yfinance per ticker per day)
python scripts/run_backtest.py --capital 100000 --start 2023-01-02 --end 2025-11-18 --max-positions 5

# Lint / format / type check
ruff check src/            # ruff --fix to auto-fix
black src/
mypy src/

# Tests (tests/ currently contains only __init__.py)
pytest tests/
pytest tests/test_foo.py -k "test_name"
pytest --cov=src/us_dynamic_breakout tests/
```

Scripts prepend `src/` to `sys.path`, so they work without `pip install -e .`. The `[project.scripts]` console entry points in `pyproject.toml` reference `scripts.run_*:main`, but `scripts/` is not a package under `src/`, so run the scripts directly.

## Architecture

### Data Flow

```
DynamicScreener (yfinance info + 3mo history) ──► WatchlistManager ──► data/watchlist.json
                                                        │
BreakoutDetector.scan_watchlist() ◄─────────────────────┘
        │ signals
        ▼
TradingBot.run_scan() ──► TelegramBot.send_message()
        │
        └──► DBPositionManager ──► SSH tunnel ──► PostgreSQL (positions, trades)
```

`TradingBot` in `scripts/run_us_dynamic_breakout_notifier.py` is the orchestrator; everything in `src/` is a library with no scheduling or env-var knowledge.

### Scheduling and market hours (all KST, naive `datetime.now()`)

- **Scan**: `_get_next_scan_time()` sleeps until HH:05 / HH:35 every hour, then runs `check_positions()` followed by `run_scan()`.
- **Screening**: `needs_rescreening()` fires once per day after 10:05 KST (post US close), persisted via `last_screening` in `watchlist.json`. Disable with `USE_DYNAMIC_SCREENING=false`.
- **Market open check**: `utils/market.py` maps KST time to US sessions (Day 10:00-17:50, Pre 18:00-23:29, Regular 23:30-05:59, After 06:00-09:50; closed 09:51-09:59) with weekday adjustments because KST morning = US previous evening. Scans are skipped when `is_open` is False.
- No timezone library is used. The host clock must be KST or every schedule and session boundary is wrong.

### Signal detection (`bot/detector.py`)

`detect_pivot_breakout()` on the last 30 bars of a 6-month daily history: close > highest close of the preceding 19 bars (`close[-20:-1]`, called the "20-day high" in comments), volume >= `min_volume_surge`% above the mean of the 29 prior bars, and 0 < breakout% <= `max_breakout_pct`. Defaults 50% / 5%, overridable via `MIN_VOLUME_SURGE` / `MAX_BREAKOUT_PCT`. `scan_watchlist()` sleeps 0.5s per ticker; the screener sleeps 0.1s per ticker.

### Persistence

- **Watchlist**: local JSON (`data/watchlist.json`), accepts legacy `us` key as well as `tickers`.
- **Positions and trades**: `DBPositionManager` (`bot/position_db.py`), **not** the JSON `PositionManager`. The bot always constructs `DBPositionManager`; `position.py` and `data/positions.json` are legacy leftovers from the pre-DB (and Korean-market) version and are not used at runtime.
- Each DB call opens a fresh SSH tunnel (`sshtunnel`, retry with exponential backoff, 3 attempts) and psycopg2 connection, then tears both down. The `positions` property hits the DB on every access.
- Tables used: `positions` (unique on `ticker`, upsert on insert; columns ticker, entry_price, entry_date, pattern, stop_loss, take_profit, signal_data JSON, updated_at) and `trades` (ticker, pattern, entry_date, entry_price, exit_date, exit_price, exit_reason, profit_pct, holding_days, signal_data). No schema/migration file lives in this repo.
- NumPy scalars from pandas must pass through `_convert_numpy_types()` before hitting psycopg2 or `json.dumps`.

### Telegram (`bot/telegram.py` + `TradingBot`)

- Plain `requests` against the Bot API, no framework. A daemon thread long-polls `getUpdates` every 2s and only acts on messages whose `chat.id` equals `TELEGRAM_CHAT_ID`.
- `handle_command()` returns either response text or the sentinels `'SCAN'` / `'RESCREEN'`; the listener spawns a thread for those. `is_scanning` / `is_screening` flags prevent overlap with the main loop.
- Every `send_message()` attaches a persistent reply keyboard (`DEFAULT_KEYBOARD`) unless `show_keyboard=False`.
- Commands: `/scan /rescreen /status /list /add /remove /positions /close /trades /stats /help`.

### Logging

`setup_logging()` installs a `TimedRotatingFileHandler` (`logs/bot.log`, rotate at midnight, 30-day retention) plus stdout. Only `TradingBot` and `position_db.py` use `logging`; `detector`, `screener`, `telegram`, `watchlist` use `print()`, so their output reaches stdout but not the log file.

### Backtest (`backtest/engine.py`)

Self-contained and intentionally **not** sharing the live detector: it uses a 40-bar pivot on `High`, 1.8x volume, an additional all-time-high pattern, 80-bar minimum, and re-downloads data per ticker per day. `generate_report()` hardcodes `years = 2.88` for CAGR. `run_backtest.py` defaults to `--capital 100_000_000` and prints "KRW" (legacy); the engine treats capital as USD.

## Configuration (`.env`, loaded by the bot script only)

Required for the bot to start: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`.

Effectively also required at startup, because `TradingBot.__init__` logs the position count, which opens the tunnel (3 failed attempts then an exception): `SSH_HOST`, `SSH_USER`, `SSH_KEY_PATH` (tilde expanded), `DB_NAME`, `DB_USER`, `DB_PASSWORD`. Optional: `SSH_PORT` (22), `DB_HOST` (localhost, as seen from the SSH host), `DB_PORT` (5432).

Optional tuning: `USE_DYNAMIC_SCREENING` (true), `MAX_STOCKS` (100), `STOP_LOSS_PCT` (0.08), `TAKE_PROFIT_PCT` (0.20), `MIN_VOLUME_SURGE` (50.0), `MAX_BREAKOUT_PCT` (5.0).

`SCREENING_INTERVAL_HOURS` and `SCAN_INTERVAL_SECONDS` are still read into `TradingBot` but no longer affect anything; scheduling is fixed-time. `STOP_LOSS_PCT` / `TAKE_PROFIT_PCT` are read but `positions.add()` is called without them, so the 8% / 20% defaults in `DBPositionManager.add()` apply. `.env.example` predates the SSH/DB settings.

## Gotchas

- `bot/telegram.py` uses `list | None` (PEP 604), so the effective minimum is Python 3.10 despite `requires-python = ">=3.9"`.
- `requirements.txt` omits `psycopg2-binary`, `sshtunnel`, `paramiko`; install via `pip install -e .` to get them.
- `USStockProvider` ticker lists are hardcoded (Wikipedia scraping was unreliable); `get_universe()` dedups S&P 500 + NASDAQ 100 into an unordered set, so screening order varies run to run.
- yfinance stderr is suppressed inside `suppress_stderr()`; failed fetches return `None` silently.
