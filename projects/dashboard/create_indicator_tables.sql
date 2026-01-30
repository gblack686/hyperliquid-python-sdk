-- Create tables for new indicators
-- Run this in Supabase SQL editor

-- Open Interest Tables
CREATE TABLE IF NOT EXISTS hl_oi_current (
    symbol TEXT PRIMARY KEY,
    oi_current FLOAT,
    oi_delta_1m FLOAT,
    oi_delta_5m FLOAT, 
    oi_delta_15m FLOAT,
    oi_delta_1h FLOAT,
    oi_change_pct_1h FLOAT,
    trend TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hl_oi_snapshots (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    oi FLOAT,
    oi_delta_5m FLOAT,
    oi_change_pct_1h FLOAT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_oi_symbol_time (symbol, timestamp DESC)
);

-- Funding Rate Tables  
CREATE TABLE IF NOT EXISTS hl_funding_current (
    symbol TEXT PRIMARY KEY,
    funding_current FLOAT,
    funding_predicted FLOAT,
    funding_8h_cumulative FLOAT,
    funding_24h_cumulative FLOAT,
    funding_avg_24h FLOAT,
    trend TEXT,
    sentiment TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hl_funding_snapshots (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    funding_rate FLOAT,
    funding_predicted FLOAT,
    cumulative_24h FLOAT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_funding_symbol_time (symbol, timestamp DESC)
);

-- Liquidations Tables
CREATE TABLE IF NOT EXISTS hl_liquidations_current (
    symbol TEXT PRIMARY KEY,
    liq_long_1h FLOAT,
    liq_short_1h FLOAT,
    liq_ratio FLOAT,
    liq_total_24h FLOAT,
    largest_liq_size FLOAT,
    trend TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hl_liquidations_snapshots (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT,
    size FLOAT,
    price FLOAT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_liq_symbol_time (symbol, timestamp DESC)
);

-- Order Book Tables
CREATE TABLE IF NOT EXISTS hl_orderbook_current (
    symbol TEXT PRIMARY KEY,
    bid_liquidity_1pct FLOAT,
    ask_liquidity_1pct FLOAT,
    book_imbalance FLOAT,
    spread_bp FLOAT,
    bid_depth_score FLOAT,
    ask_depth_score FLOAT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hl_orderbook_snapshots (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    best_bid FLOAT,
    best_ask FLOAT,
    bid_size FLOAT,
    ask_size FLOAT,
    book_imbalance FLOAT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_book_symbol_time (symbol, timestamp DESC)
);

-- Add descriptions to columns
COMMENT ON COLUMN hl_oi_current.oi_current IS 'Current open interest in millions';
COMMENT ON COLUMN hl_oi_current.oi_delta_1m IS 'Change in OI over last 1 minute';
COMMENT ON COLUMN hl_oi_current.oi_delta_5m IS 'Change in OI over last 5 minutes';
COMMENT ON COLUMN hl_oi_current.oi_change_pct_1h IS 'Percentage change in OI over last hour';
COMMENT ON COLUMN hl_oi_current.trend IS 'OI trend: increasing/decreasing/neutral';

COMMENT ON COLUMN hl_funding_current.funding_current IS 'Current funding rate in basis points';
COMMENT ON COLUMN hl_funding_current.funding_predicted IS 'Predicted next funding rate in basis points';
COMMENT ON COLUMN hl_funding_current.funding_24h_cumulative IS 'Cumulative funding over 24 hours in basis points';
COMMENT ON COLUMN hl_funding_current.sentiment IS 'Market sentiment based on funding: very_bullish/bullish/neutral/bearish/very_bearish';

COMMENT ON COLUMN hl_liquidations_current.liq_long_1h IS 'Long liquidations in last hour (USD millions)';
COMMENT ON COLUMN hl_liquidations_current.liq_short_1h IS 'Short liquidations in last hour (USD millions)';
COMMENT ON COLUMN hl_liquidations_current.liq_ratio IS 'Ratio of long to short liquidations';

COMMENT ON COLUMN hl_orderbook_current.book_imbalance IS 'Order book imbalance (-1 to 1, positive = more bids)';
COMMENT ON COLUMN hl_orderbook_current.spread_bp IS 'Bid-ask spread in basis points';
COMMENT ON COLUMN hl_orderbook_current.bid_depth_score IS 'Bid side depth score (0-100)';

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;