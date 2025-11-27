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
git clone <repository-url>
cd dynamic-oneil-breakout
pip install -e .

# Or install dependencies directly
pip install yfinance pandas numpy requests python-dotenv
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Telegram credentials
TELEGRAM_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Run

```bash
# Run the trading bot
python scripts/run_bot.py

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
TelegramBot (notifications) + PositionManager (positions.json)
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
dynamic-oneil-breakout/
├── src/us_dynamic_breakout/
│   ├── bot/
│   │   ├── detector.py      # Breakout pattern detection
│   │   ├── telegram.py      # Telegram integration
│   │   ├── position.py      # Position management
│   │   └── watchlist.py     # Watchlist management
│   ├── screener/
│   │   └── screener.py      # Dynamic stock screener
│   ├── backtest/
│   │   └── engine.py        # Backtesting engine
│   ├── data/
│   │   └── us_provider.py   # US stock data (yfinance)
│   └── utils/
│       └── market.py        # Market hours utilities
├── config/
│   └── settings.py          # Settings dataclasses
├── scripts/
│   ├── run_bot.py           # Main bot runner
│   ├── run_screener.py      # Screener runner
│   └── run_backtest.py      # Backtest runner
├── data/                    # Runtime data (JSON)
│   ├── watchlist.json
│   └── positions.json
└── .env                     # Environment variables
```

## Configuration Options

Edit `.env` file:

```bash
# Required
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional
SCREENING_INTERVAL_HOURS=24    # Re-screening interval
MAX_STOCKS=100                 # Max stocks to screen
SCAN_INTERVAL_SECONDS=1800     # Signal scan interval (30 min)
STOP_LOSS_PCT=0.08             # Stop loss percentage (8%)
TAKE_PROFIT_PCT=0.20           # Take profit percentage (20%)
```

## Telegram Commands

### Scanning
```
/scan          - Scan all watchlist stocks
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
