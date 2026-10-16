-- PostgreSQL schema for us-dynamic-breakout-notifier
--
-- Tables used by src/us_dynamic_breakout/bot/position_db.py (DBPositionManager).
-- Column names and constraints are taken from the INSERT/SELECT statements there.
--
-- Apply once (through your SSH tunnel or directly on the DB host):
--   psql -h <db_host> -p <db_port> -U <db_user> -d <db_name> -f schema.sql

-- Open positions. One row per ticker; DBPositionManager.add() upserts on ticker.
CREATE TABLE IF NOT EXISTS positions (
    id           SERIAL        PRIMARY KEY,
    ticker       VARCHAR(16)   NOT NULL UNIQUE,
    entry_price  NUMERIC(12,4) NOT NULL,
    entry_date   TIMESTAMP     NOT NULL,
    pattern      VARCHAR(64)   NOT NULL,
    stop_loss    NUMERIC(12,4) NOT NULL,
    take_profit  NUMERIC(12,4) NOT NULL,
    signal_data  JSONB,
    created_at   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Closed trades. Appended by DBPositionManager.record_trade(); read by /trades and /stats.
CREATE TABLE IF NOT EXISTS trades (
    id            SERIAL        PRIMARY KEY,
    ticker        VARCHAR(16)   NOT NULL,
    pattern       VARCHAR(64)   NOT NULL,
    entry_date    TIMESTAMP     NOT NULL,
    entry_price   NUMERIC(12,4) NOT NULL,
    exit_date     TIMESTAMP     NOT NULL,
    exit_price    NUMERIC(12,4) NOT NULL,
    exit_reason   VARCHAR(64)   NOT NULL,
    profit_pct    NUMERIC(8,4)  NOT NULL,
    holding_days  INTEGER       NOT NULL,
    signal_data   JSONB,
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trades_exit_date ON trades (exit_date DESC);
CREATE INDEX IF NOT EXISTS idx_trades_ticker    ON trades (ticker);
