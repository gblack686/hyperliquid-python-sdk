-- Paper Trading System Tables
-- Run this in Supabase SQL Editor

-- Table: paper_recommendations
-- Stores all trading recommendations from strategy agents
CREATE TABLE IF NOT EXISTS paper_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    strategy_name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT', 'HOLD')),
    entry_price DECIMAL NOT NULL,
    target_price_1 DECIMAL NOT NULL,
    stop_loss_price DECIMAL NOT NULL,
    confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
    status TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'TARGET_HIT', 'STOPPED', 'EXPIRED')),
    expires_at TIMESTAMPTZ NOT NULL,
    position_size DECIMAL DEFAULT 1000,
    strategy_params JSONB DEFAULT '{}'::jsonb
);

-- Table: paper_recommendation_outcomes
-- Tracks what happened to each recommendation
CREATE TABLE IF NOT EXISTS paper_recommendation_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id UUID NOT NULL REFERENCES paper_recommendations(id) ON DELETE CASCADE,
    outcome_time TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    outcome_type TEXT NOT NULL CHECK (outcome_type IN ('TARGET_HIT', 'STOPPED', 'EXPIRED')),
    exit_price DECIMAL NOT NULL,
    pnl_pct DECIMAL NOT NULL,
    pnl_amount DECIMAL NOT NULL,
    hold_duration_minutes INTEGER NOT NULL
);

-- Table: paper_strategy_metrics
-- Aggregated performance metrics per strategy per period
CREATE TABLE IF NOT EXISTS paper_strategy_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name TEXT NOT NULL,
    period TEXT NOT NULL CHECK (period IN ('24h', '7d', '30d', 'all_time')),
    calculated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    total_signals INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    active INTEGER DEFAULT 0,
    win_rate DECIMAL,
    total_pnl_pct DECIMAL DEFAULT 0,
    total_pnl_amount DECIMAL DEFAULT 0,
    avg_pnl_pct DECIMAL DEFAULT 0,
    best_trade_pnl DECIMAL,
    worst_trade_pnl DECIMAL,
    profit_factor DECIMAL,
    avg_hold_duration_minutes INTEGER,
    UNIQUE(strategy_name, period)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_paper_recommendations_created_at ON paper_recommendations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_paper_recommendations_status ON paper_recommendations(status);
CREATE INDEX IF NOT EXISTS idx_paper_recommendations_strategy ON paper_recommendations(strategy_name);
CREATE INDEX IF NOT EXISTS idx_paper_recommendations_symbol ON paper_recommendations(symbol);
CREATE INDEX IF NOT EXISTS idx_paper_recommendations_expires ON paper_recommendations(expires_at);

CREATE INDEX IF NOT EXISTS idx_paper_outcomes_recommendation ON paper_recommendation_outcomes(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_paper_outcomes_time ON paper_recommendation_outcomes(outcome_time DESC);

CREATE INDEX IF NOT EXISTS idx_paper_metrics_strategy_period ON paper_strategy_metrics(strategy_name, period);

-- Enable Row Level Security (optional, for production)
-- ALTER TABLE paper_recommendations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE paper_recommendation_outcomes ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE paper_strategy_metrics ENABLE ROW LEVEL SECURITY;
