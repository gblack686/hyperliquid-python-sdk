-- Hyperliquid Trading Dashboard Supabase Schema
-- All tables use trading_dash_ prefix

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Price data table (1-minute candles)
CREATE TABLE IF NOT EXISTS trading_dash_candles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(30, 8) NOT NULL,
    trades_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, timestamp)
);

-- Create index for faster queries
CREATE INDEX idx_trading_dash_candles_symbol_timestamp 
ON trading_dash_candles(symbol, timestamp DESC);

-- Real-time price ticks
CREATE TABLE IF NOT EXISTS trading_dash_ticks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    size DECIMAL(20, 8),
    side VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trading_dash_ticks_symbol_timestamp 
ON trading_dash_ticks(symbol, timestamp DESC);

-- Technical indicators
CREATE TABLE IF NOT EXISTS trading_dash_indicators (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    indicator_name VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    value DECIMAL(20, 8),
    signal VARCHAR(20),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, timestamp, indicator_name, timeframe)
);

CREATE INDEX idx_trading_dash_indicators_lookup 
ON trading_dash_indicators(symbol, timestamp DESC, indicator_name);

-- Confluence signals
CREATE TABLE IF NOT EXISTS trading_dash_confluence (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    confluence_score DECIMAL(5, 2) NOT NULL,
    direction VARCHAR(10) NOT NULL, -- 'BULLISH', 'BEARISH', 'NEUTRAL'
    strength VARCHAR(10) NOT NULL, -- 'WEAK', 'MODERATE', 'STRONG'
    active_signals JSONB NOT NULL,
    indicator_details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trading_dash_confluence_symbol_timestamp 
ON trading_dash_confluence(symbol, timestamp DESC);

-- Account balance snapshots
CREATE TABLE IF NOT EXISTS trading_dash_account (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    account_address VARCHAR(100),
    total_balance DECIMAL(20, 8) NOT NULL,
    available_balance DECIMAL(20, 8),
    margin_used DECIMAL(20, 8),
    unrealized_pnl DECIMAL(20, 8),
    realized_pnl DECIMAL(20, 8),
    positions JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trading_dash_account_timestamp 
ON trading_dash_account(timestamp DESC);

-- Trade history
CREATE TABLE IF NOT EXISTS trading_dash_trades (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    trade_id VARCHAR(100) UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    side VARCHAR(10) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    size DECIMAL(20, 8) NOT NULL,
    fee DECIMAL(20, 8),
    order_type VARCHAR(20),
    pnl DECIMAL(20, 8),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trading_dash_trades_symbol_timestamp 
ON trading_dash_trades(symbol, timestamp DESC);

-- Backtest results
CREATE TABLE IF NOT EXISTS trading_dash_backtests (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    initial_capital DECIMAL(20, 8) NOT NULL,
    final_capital DECIMAL(20, 8) NOT NULL,
    total_return DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    win_rate DECIMAL(10, 4),
    total_trades INTEGER,
    parameters JSONB,
    trade_log JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- System health monitoring
CREATE TABLE IF NOT EXISTS trading_dash_health (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    component VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    latency_ms INTEGER,
    error_count INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trading_dash_health_component_timestamp 
ON trading_dash_health(component, timestamp DESC);

-- Create views for common queries

-- Latest indicators view
CREATE OR REPLACE VIEW trading_dash_latest_indicators AS
SELECT DISTINCT ON (symbol, indicator_name, timeframe) 
    symbol,
    indicator_name,
    timeframe,
    timestamp,
    value,
    signal,
    metadata
FROM trading_dash_indicators
ORDER BY symbol, indicator_name, timeframe, timestamp DESC;

-- Latest confluence view
CREATE OR REPLACE VIEW trading_dash_latest_confluence AS
SELECT DISTINCT ON (symbol) 
    symbol,
    timestamp,
    confluence_score,
    direction,
    strength,
    active_signals
FROM trading_dash_confluence
ORDER BY symbol, timestamp DESC;

-- Account balance history view
CREATE OR REPLACE VIEW trading_dash_balance_history AS
SELECT 
    timestamp,
    total_balance,
    unrealized_pnl,
    realized_pnl,
    margin_used
FROM trading_dash_account
ORDER BY timestamp DESC;

-- Row Level Security (RLS) - Optional, enable if needed
-- ALTER TABLE trading_dash_account ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE trading_dash_trades ENABLE ROW LEVEL SECURITY;

-- Create functions for data management

-- Function to clean old tick data (keep last 24 hours)
CREATE OR REPLACE FUNCTION clean_old_ticks()
RETURNS void AS $$
BEGIN
    DELETE FROM trading_dash_ticks 
    WHERE timestamp < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Function to aggregate 1-minute candles into higher timeframes
CREATE OR REPLACE FUNCTION aggregate_candles(
    p_symbol VARCHAR,
    p_timeframe VARCHAR,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
)
RETURNS TABLE (
    timestamp TIMESTAMPTZ,
    open DECIMAL,
    high DECIMAL,
    low DECIMAL,
    close DECIMAL,
    volume DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        date_trunc(p_timeframe, c.timestamp) as timestamp,
        (array_agg(c.open ORDER BY c.timestamp))[1] as open,
        MAX(c.high) as high,
        MIN(c.low) as low,
        (array_agg(c.close ORDER BY c.timestamp DESC))[1] as close,
        SUM(c.volume) as volume
    FROM trading_dash_candles c
    WHERE c.symbol = p_symbol
        AND c.timestamp >= p_start_time
        AND c.timestamp < p_end_time
    GROUP BY date_trunc(p_timeframe, c.timestamp)
    ORDER BY timestamp;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust based on your Supabase setup)
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;