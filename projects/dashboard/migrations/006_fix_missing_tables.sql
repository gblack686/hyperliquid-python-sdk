-- Migration: Fix missing tables and columns for indicators
-- Run this in Supabase SQL Editor

-- Fix liquidations table - add missing bias column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'hl_liquidations_current' 
                   AND column_name = 'bias') THEN
        ALTER TABLE hl_liquidations_current 
        ADD COLUMN bias TEXT DEFAULT 'neutral';
    END IF;
END $$;

-- Create bollinger bands tables if they don't exist
CREATE TABLE IF NOT EXISTS hl_bollinger_current (
    symbol TEXT PRIMARY KEY,
    current_price NUMERIC,
    bb_upper_5m NUMERIC,
    bb_middle_5m NUMERIC,
    bb_lower_5m NUMERIC,
    bb_position_5m NUMERIC,
    bb_upper_15m NUMERIC,
    bb_middle_15m NUMERIC,
    bb_lower_15m NUMERIC,
    bb_position_15m NUMERIC,
    bb_upper_1h NUMERIC,
    bb_middle_1h NUMERIC,
    bb_lower_1h NUMERIC,
    bb_position_1h NUMERIC,
    bb_width_1h NUMERIC,
    bandwidth_pct NUMERIC,
    squeeze_5m BOOLEAN DEFAULT FALSE,
    squeeze_15m BOOLEAN DEFAULT FALSE,
    squeeze_1h BOOLEAN DEFAULT FALSE,
    upper_walk_count INTEGER DEFAULT 0,
    lower_walk_count INTEGER DEFAULT 0,
    signal TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hl_bollinger_snapshots (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    symbol TEXT NOT NULL,
    price NUMERIC,
    bb_position_1h NUMERIC,
    bandwidth_pct NUMERIC,
    squeeze_1h BOOLEAN DEFAULT FALSE,
    signal TEXT,
    timestamp TIMESTAMPTZ NOT NULL
);

-- Create VWAP tables if they don't exist
CREATE TABLE IF NOT EXISTS hl_vwap_current (
    symbol TEXT PRIMARY KEY,
    current_price NUMERIC,
    vwap_session NUMERIC,
    vwap_daily NUMERIC,
    vwap_weekly NUMERIC,
    vwap_hourly NUMERIC,
    volume_session NUMERIC,
    volume_daily NUMERIC,
    deviation_pct NUMERIC,
    position TEXT,
    trend TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hl_vwap_snapshots (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    symbol TEXT NOT NULL,
    price NUMERIC,
    vwap_daily NUMERIC,
    deviation_pct NUMERIC,
    volume NUMERIC,
    position TEXT,
    timestamp TIMESTAMPTZ NOT NULL
);

-- Create ATR tables if they don't exist
CREATE TABLE IF NOT EXISTS hl_atr_current (
    symbol TEXT PRIMARY KEY,
    current_price NUMERIC,
    atr_5m NUMERIC,
    atr_15m NUMERIC,
    atr_1h NUMERIC,
    atr_4h NUMERIC,
    atr_1d NUMERIC,
    atr_pct_5m NUMERIC,
    atr_pct_1h NUMERIC,
    atr_pct_1d NUMERIC,
    volatility_rank NUMERIC,
    volatility_state TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hl_atr_snapshots (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    symbol TEXT NOT NULL,
    price NUMERIC,
    atr_1h NUMERIC,
    atr_pct_1h NUMERIC,
    volatility_state TEXT,
    timestamp TIMESTAMPTZ NOT NULL
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_bollinger_snapshots_symbol_timestamp 
ON hl_bollinger_snapshots(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_vwap_snapshots_symbol_timestamp 
ON hl_vwap_snapshots(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_atr_snapshots_symbol_timestamp 
ON hl_atr_snapshots(symbol, timestamp DESC);

-- Create orderbook tables if they don't exist  
CREATE TABLE IF NOT EXISTS hl_orderbook_current (
    symbol TEXT PRIMARY KEY,
    bid_ask_ratio NUMERIC,
    bid_volume NUMERIC,
    ask_volume NUMERIC,
    order_book_pressure NUMERIC,
    large_bid_orders INTEGER DEFAULT 0,
    large_ask_orders INTEGER DEFAULT 0,
    support_levels JSONB,
    resistance_levels JSONB,
    spread NUMERIC,
    spread_pct NUMERIC,
    trend TEXT,
    state TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hl_orderbook_snapshots (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    symbol TEXT NOT NULL,
    bid_ask_ratio NUMERIC,
    order_book_pressure NUMERIC,
    bid_volume NUMERIC,
    ask_volume NUMERIC,
    spread_pct NUMERIC,
    state TEXT,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orderbook_snapshots_symbol_timestamp 
ON hl_orderbook_snapshots(symbol, timestamp DESC);

-- Create Support/Resistance tables if they don't exist
CREATE TABLE IF NOT EXISTS hl_sr_current (
    symbol TEXT PRIMARY KEY,
    current_price NUMERIC,
    support_1 NUMERIC,
    support_2 NUMERIC,
    support_3 NUMERIC,
    resistance_1 NUMERIC,
    resistance_2 NUMERIC,
    resistance_3 NUMERIC,
    pivot NUMERIC,
    pivot_r1 NUMERIC,
    pivot_s1 NUMERIC,
    ma_20 NUMERIC,
    ma_50 NUMERIC,
    ma_200 NUMERIC,
    nearest_support NUMERIC,
    nearest_resistance NUMERIC,
    support_distance_pct NUMERIC,
    resistance_distance_pct NUMERIC,
    position TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hl_sr_snapshots (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    symbol TEXT NOT NULL,
    price NUMERIC,
    nearest_support NUMERIC,
    nearest_resistance NUMERIC,
    position TEXT,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sr_snapshots_symbol_timestamp 
ON hl_sr_snapshots(symbol, timestamp DESC);

-- Grant appropriate permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;