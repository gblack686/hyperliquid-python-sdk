-- Add missing tables to existing hl_ schema in Supabase
-- These tables complement the existing hl_ tables for complete trading dashboard functionality

-- Price data table (1-minute candles)
CREATE TABLE IF NOT EXISTS hl_candles (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(30, 8) NOT NULL,
    trades_count INTEGER,
    UNIQUE(symbol, timestamp)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_hl_candles_symbol_timestamp 
ON hl_candles(symbol, timestamp DESC);

-- Real-time price ticks
CREATE TABLE IF NOT EXISTS hl_ticks (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    size DECIMAL(20, 8),
    side VARCHAR(10)
);

CREATE INDEX IF NOT EXISTS idx_hl_ticks_symbol_timestamp 
ON hl_ticks(symbol, timestamp DESC);

-- Technical indicators
CREATE TABLE IF NOT EXISTS hl_indicators (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    indicator_name VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    value DECIMAL(20, 8),
    signal VARCHAR(20),
    metadata JSONB,
    UNIQUE(symbol, timestamp, indicator_name, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_hl_indicators_lookup 
ON hl_indicators(symbol, timestamp DESC, indicator_name);

-- Confluence signals
CREATE TABLE IF NOT EXISTS hl_confluence (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    confluence_score DECIMAL(5, 2) NOT NULL,
    direction VARCHAR(10) NOT NULL, -- 'BULLISH', 'BEARISH', 'NEUTRAL'
    strength VARCHAR(10) NOT NULL, -- 'WEAK', 'MODERATE', 'STRONG'
    active_signals JSONB NOT NULL,
    indicator_details JSONB
);

CREATE INDEX IF NOT EXISTS idx_hl_confluence_symbol_timestamp 
ON hl_confluence(symbol, timestamp DESC);

-- Backtest results (if not exists)
CREATE TABLE IF NOT EXISTS hl_backtests (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
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
    trade_log JSONB
);

-- Create views for common queries

-- Latest indicators view
CREATE OR REPLACE VIEW hl_latest_indicators AS
SELECT DISTINCT ON (symbol, indicator_name, timeframe) 
    symbol,
    indicator_name,
    timeframe,
    timestamp,
    value,
    signal,
    metadata
FROM hl_indicators
ORDER BY symbol, indicator_name, timeframe, timestamp DESC;

-- Latest confluence view
CREATE OR REPLACE VIEW hl_latest_confluence AS
SELECT DISTINCT ON (symbol) 
    symbol,
    timestamp,
    confluence_score,
    direction,
    strength,
    active_signals
FROM hl_confluence
ORDER BY symbol, timestamp DESC;

-- Account balance history view (using existing hl_dashboard table)
CREATE OR REPLACE VIEW hl_balance_history AS
SELECT 
    created_at as timestamp,
    account_value as total_balance,
    total_unrealized_pnl as unrealized_pnl,
    total_margin_used as margin_used
FROM hl_dashboard
ORDER BY created_at DESC;

-- Function to clean old tick data (keep last 24 hours)
CREATE OR REPLACE FUNCTION clean_old_hl_ticks()
RETURNS void AS $$
BEGIN
    DELETE FROM hl_ticks 
    WHERE timestamp < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Function to aggregate 1-minute candles into higher timeframes
CREATE OR REPLACE FUNCTION aggregate_hl_candles(
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
    FROM hl_candles c
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