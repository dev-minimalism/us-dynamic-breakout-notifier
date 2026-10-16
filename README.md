# William O'Neil Breakout Trading Bot (US Market)

Dynamic stock screening and breakout signal detection for US markets based on William O'Neil's trading methodology.

## Features

- **Dynamic Stock Screening**: Automatically screens S&P 500 + NASDAQ 100 stocks
- **Pivot Point Breakout Detection**: O'Neil style breakout signals with volume confirmation
- **Telegram Notifications**: Real-time alerts for breakout signals
- **Position Management**: Automatic stop-loss (-8%), take-profit (+20%), and max holding period (30 days)
- **Backtesting**: No look-ahead bias backtesting engine

## Quick Start

### 1. Installation

```bash
# Clone and install
git clone https://github.com/dev-minimalism/us-dynamic-breakout-notifier.git
cd us-dynamic-breakout-notifier
pip install -e .

# Or install dependencies directly
pip install yfinance pandas numpy requests python-dotenv psycopg2-binary sshtunnel paramiko
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Telegram, SSH tunnel, and PostgreSQL settings
# (see "Configuration Options" below for the full list)
TELEGRAM_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Run

```bash
# Run the trading bot
python scripts/run_us_dynamic_breakout_notifier.py

# Run screener only
python scripts/run_screener.py

# Run backtest
python scripts/run_backtest.py
```

## How It Works

### Data Flow

```
DynamicScreener (filters S&P 500 + NASDAQ 100)
       |
       v
WatchlistManager (watchlist.json)
       |
       v
BreakoutDetector (pivot breakout + volume surge)
       |
       v
TelegramBot (notifications) + DBPositionManager (PostgreSQL via SSH tunnel)
```

### Screening Criteria

| Criteria | Threshold |
|----------|-----------|
| Market Cap | >= $500M |
| Stock Price | >= $5 |
| Average Volume | >= 50K shares/day |

### Breakout Signal Conditions

A valid breakout signal requires:
1. **Price breakout**: Current price > 20-day high (resistance)
2. **Volume surge**: Today's volume >= 150% of 30-day average
3. **Not too extended**: Breakout within 5% of resistance level

## Project Structure

```
us-dynamic-breakout-notifier/
├── src/us_dynamic_breakout/
│   ├── bot/
│   │   ├── detector.py      # Breakout pattern detection
│   │   ├── telegram.py      # Telegram integration
│   │   ├── position.py      # Position management (legacy JSON store)
│   │   ├── position_db.py   # Position/trade store (PostgreSQL via SSH tunnel)
│   │   └── watchlist.py     # Watchlist management
│   ├── screener/
│   │   └── screener.py      # Dynamic stock screener
│   ├── backtest/
│   │   └── engine.py        # Backtesting engine
│   ├── data/
│   │   └── us_provider.py   # US stock data (yfinance)
│   └── utils/
│       └── market.py        # Market hours utilities
├── scripts/
│   ├── run_us_dynamic_breakout_notifier.py  # Main bot runner
│   ├── run_screener.py      # Screener runner
│   └── run_backtest.py      # Backtest runner
├── data/                    # Runtime data (JSON)
│   └── watchlist.json
├── logs/                    # Log files (auto-rotated daily)
│   └── bot.log
└── .env                     # Environment variables
```

## Configuration Options

Edit `.env` file:

```bash
# Required: Telegram
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Required: SSH tunnel to the PostgreSQL host
SSH_HOST=your.server.example.com
SSH_PORT=22
SSH_USER=ubuntu
SSH_KEY_PATH=~/.ssh/id_rsa

# Required: PostgreSQL (host/port as seen from the SSH host)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=breakout
DB_USER=breakout
DB_PASSWORD=your_db_password

# Optional
USE_DYNAMIC_SCREENING=true     # false = manual watchlist only
MAX_STOCKS=100                 # Max stocks selected by screening
MIN_VOLUME_SURGE=50.0          # Min volume increase % for a signal
MAX_BREAKOUT_PCT=5.0           # Max % above resistance for a signal
STOP_LOSS_PCT=0.08             # Stop loss percentage (8%)
TAKE_PROFIT_PCT=0.20           # Take profit percentage (20%)
```

Positions and trade history are stored in PostgreSQL (tables `positions` and `trades`), reached through an SSH tunnel. The schedule is fixed in KST: breakout scans at HH:05 and HH:35 while the US market (including pre/after-hours) is open, and re-screening daily at 10:05.

## Telegram Commands

### Scanning
```
/scan          - Scan all watchlist stocks
/rescreen      - Re-run dynamic screening now
/status        - Check market status
```

### Watchlist Management
```
/list          - View current watchlist
/add AAPL      - Add stock to watchlist
/remove AAPL   - Remove stock from watchlist
```

### Position Management
```
/positions     - View open positions
/close AAPL    - Close position manually
```

### Trade History
```
/trades        - Recent closed trades
/stats         - Win rate, average P&L, holding days
```

## Backtesting

```bash
# Basic backtest
python scripts/run_backtest.py

# Custom parameters
python scripts/run_backtest.py --capital 100000 --start 2023-01-02 --end 2025-11-18
```

The backtest engine:
- Screens stocks daily using only data available at that time (no look-ahead bias)
- Applies transaction costs (0.1%)
- Manages positions with stop-loss, take-profit, and max holding period

## Background Execution

```bash
# Run in background (logs auto-rotate daily)
nohup python -u scripts/run_us_dynamic_breakout_notifier.py &
```

**Log files** are automatically managed:
- Location: `logs/bot.log` (current) + `logs/bot.log.YYYYMMDD` (rotated)
- Rotation: Daily at midnight
- Retention: 30 days

**Useful commands:**

```bash
# Check if running
ps aux | grep run_us_dynamic_breakout_notifier

# Watch logs in real-time
tail -f logs/bot.log

# Stop the bot
pkill -f run_us_dynamic_breakout_notifier
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Linting
ruff check src/
black src/
mypy src/
```

## O'Neil Trading Methodology

This bot implements key concepts from William O'Neil's CAN SLIM methodology:

1. **Pivot Point Breakout**: Buy when stock breaks out of a consolidation base on high volume
2. **Volume Confirmation**: Volume should surge at least 50% above average on breakout
3. **Don't Chase**: Avoid buying stocks that have already moved too far (>5% above pivot)
4. **Cut Losses**: Strict 7-8% stop loss rule
5. **Let Winners Run**: Take profit at 20-25% gain

## Disclaimer

This software is for educational and research purposes only. Trading stocks involves risk of loss. Past performance does not guarantee future results. Always do your own research before making investment decisions.

## License

MIT License
