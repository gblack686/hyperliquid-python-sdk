-- Paper Trading Schema for Supabase
-- Run this in Supabase SQL Editor to create the tables

-- =============================================================================
-- Table: paper_recommendations
-- Stores all paper trading signals/recommendations from strategy agents
-- =============================================================================
CREATE TABLE IF NOT EXISTS paper_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    strategy_name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT', 'HOLD')),
    entry_price NUMERIC(20, 8) NOT NULL,
    target_price_1 NUMERIC(20, 8),
    target_price_2 NUMERIC(20, 8),
    stop_loss_price NUMERIC(20, 8),
    confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'TARGET_HIT', 'STOPPED', 'EXPIRED', 'CANCELLED')),
    expires_at TIMESTAMPTZ,
    strategy_params JSONB DEFAULT '{}',
    notes TEXT
);

-- Indexes for paper_recommendations
CREATE INDEX IF NOT EXISTS idx_paper_recommendations_strategy ON paper_recommendations(strategy_name);
CREATE INDEX IF NOT EXISTS idx_paper_recommendations_symbol ON paper_recommendations(symbol);
CREATE INDEX IF NOT EXISTS idx_paper_recommendations_status ON paper_recommendations(status);
CREATE INDEX IF NOT EXISTS idx_paper_recommendations_created_at ON paper_recommendations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_paper_recommendations_active ON paper_recommendations(status, created_at DESC) WHERE status = 'ACTIVE';

-- =============================================================================
-- Table: paper_recommendation_outcomes
-- Tracks the outcome of each recommendation
-- =============================================================================
CREATE TABLE IF NOT EXISTS paper_recommendation_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id UUID NOT NULL REFERENCES paper_recommendations(id) ON DELETE CASCADE,
    outcome_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    outcome_type TEXT NOT NULL CHECK (outcome_type IN ('TARGET_HIT', 'STOPPED', 'EXPIRED', 'MANUAL_CLOSE')),
    exit_price NUMERIC(20, 8) NOT NULL,
    pnl_pct NUMERIC(10, 4) NOT NULL,
    pnl_usd NUMERIC(20, 2),
    hold_duration_minutes INTEGER NOT NULL,
    peak_pnl_pct NUMERIC(10, 4),
    trough_pnl_pct NUMERIC(10, 4),
    notes TEXT
);

-- Indexes for paper_recommendation_outcomes
CREATE INDEX IF NOT EXISTS idx_paper_outcomes_recommendation ON paper_recommendation_outcomes(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_paper_outcomes_time ON paper_recommendation_outcomes(outcome_time DESC);
CREATE INDEX IF NOT EXISTS idx_paper_outcomes_type ON paper_recommendation_outcomes(outcome_type);

-- =============================================================================
-- Table: paper_strategy_metrics
-- Aggregated metrics per strategy per time period
-- =============================================================================
CREATE TABLE IF NOT EXISTS paper_strategy_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name TEXT NOT NULL,
    period TEXT NOT NULL CHECK (period IN ('24h', '7d', '30d', 'all_time')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_signals INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    still_active INTEGER NOT NULL DEFAULT 0,
    win_rate NUMERIC(5, 2),
    avg_pnl_pct NUMERIC(10, 4),
    total_pnl_pct NUMERIC(12, 4),
    total_pnl_usd NUMERIC(20, 2),
    profit_factor NUMERIC(10, 4),
    sharpe_ratio NUMERIC(10, 4),
    max_drawdown_pct NUMERIC(10, 4),
    avg_hold_duration_minutes NUMERIC(10, 2),
    best_trade_pnl_pct NUMERIC(10, 4),
    worst_trade_pnl_pct NUMERIC(10, 4),
    UNIQUE(strategy_name, period)
);

-- Indexes for paper_strategy_metrics
CREATE INDEX IF NOT EXISTS idx_paper_metrics_strategy ON paper_strategy_metrics(strategy_name);
CREATE INDEX IF NOT EXISTS idx_paper_metrics_period ON paper_strategy_metrics(period);
CREATE INDEX IF NOT EXISTS idx_paper_metrics_updated ON paper_strategy_metrics(updated_at DESC);

-- =============================================================================
-- Table: paper_price_snapshots
-- Periodic price snapshots for tracking recommendation progress
-- =============================================================================
CREATE TABLE IF NOT EXISTS paper_price_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id UUID NOT NULL REFERENCES paper_recommendations(id) ON DELETE CASCADE,
    snapshot_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    price NUMERIC(20, 8) NOT NULL,
    unrealized_pnl_pct NUMERIC(10, 4) NOT NULL
);

-- Indexes for paper_price_snapshots
CREATE INDEX IF NOT EXISTS idx_paper_snapshots_recommendation ON paper_price_snapshots(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_paper_snapshots_time ON paper_price_snapshots(snapshot_time DESC);

-- =============================================================================
-- Enable Row Level Security (optional, recommended for production)
-- =============================================================================
-- ALTER TABLE paper_recommendations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE paper_recommendation_outcomes ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE paper_strategy_metrics ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE paper_price_snapshots ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- Useful Views
-- =============================================================================

-- View: Active recommendations with current status
CREATE OR REPLACE VIEW v_active_recommendations AS
SELECT
    r.*,
    EXTRACT(EPOCH FROM (NOW() - r.created_at)) / 60 AS minutes_since_entry
FROM paper_recommendations r
WHERE r.status = 'ACTIVE'
ORDER BY r.created_at DESC;

-- View: Recent outcomes with recommendation details
CREATE OR REPLACE VIEW v_recent_outcomes AS
SELECT
    o.*,
    r.strategy_name,
    r.symbol,
    r.direction,
    r.entry_price,
    r.target_price_1,
    r.stop_loss_price,
    r.confidence_score
FROM paper_recommendation_outcomes o
JOIN paper_recommendations r ON o.recommendation_id = r.id
ORDER BY o.outcome_time DESC;

-- View: Strategy performance summary
CREATE OR REPLACE VIEW v_strategy_summary AS
SELECT
    strategy_name,
    period,
    total_signals,
    wins,
    losses,
    still_active,
    ROUND(win_rate, 1) AS win_rate_pct,
    ROUND(avg_pnl_pct, 2) AS avg_pnl_pct,
    ROUND(total_pnl_pct, 2) AS total_pnl_pct,
    ROUND(profit_factor, 2) AS profit_factor,
    updated_at
FROM paper_strategy_metrics
ORDER BY strategy_name,
    CASE period
        WHEN '24h' THEN 1
        WHEN '7d' THEN 2
        WHEN '30d' THEN 3
        ELSE 4
    END;
