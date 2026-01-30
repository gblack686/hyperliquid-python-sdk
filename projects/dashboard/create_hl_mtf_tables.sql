
-- Drop existing tables if they exist
DROP TABLE IF EXISTS hl_mtf_output CASCADE;
DROP TABLE IF EXISTS hl_mtf_context CASCADE;

-- Create MTF Context table (input data)
CREATE TABLE hl_mtf_context (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    sym INTEGER NOT NULL,
    t BIGINT NOT NULL,
    p NUMERIC(20, 2) NOT NULL,
    exec_tf INTEGER NOT NULL,
    tf INTEGER[] NOT NULL,
    px_z NUMERIC(10, 3)[] NOT NULL,
    v_z NUMERIC(10, 3)[] NOT NULL,
    vwap_z NUMERIC(10, 3)[] NOT NULL,
    bb_pos NUMERIC(10, 3)[] NOT NULL,
    atr_n NUMERIC(10, 3)[] NOT NULL,
    cvd_s NUMERIC(10, 3)[] NOT NULL,
    cvd_lvl NUMERIC(10, 3)[] NOT NULL,
    oi_d NUMERIC(10, 3)[] NOT NULL,
    liq_n NUMERIC(10, 3)[] NOT NULL,
    reg INTEGER[] NOT NULL,
    l_sup NUMERIC(20, 2) NOT NULL,
    l_res NUMERIC(20, 2) NOT NULL,
    l_q_bid NUMERIC(10, 2) NOT NULL,
    l_q_ask NUMERIC(10, 2) NOT NULL,
    l_dsup NUMERIC(10, 3) NOT NULL,
    l_dres NUMERIC(10, 3) NOT NULL,
    basis_bp NUMERIC(10, 1) NOT NULL,
    fund_bp NUMERIC(10, 1) NOT NULL,
    px_disp_bp NUMERIC(10, 2) NOT NULL,
    pos NUMERIC(10, 3) NOT NULL,
    avg NUMERIC(20, 2) NOT NULL,
    unrlz NUMERIC(10, 2) NOT NULL,
    rsk INTEGER NOT NULL,
    hr12 NUMERIC(5, 2) NOT NULL,
    slip_bp NUMERIC(10, 2) NOT NULL,
    dd_pct NUMERIC(10, 2) NOT NULL
);

-- Create MTF Output table (LLM predictions)
CREATE TABLE hl_mtf_output (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    context_id BIGINT REFERENCES hl_mtf_context(id) ON DELETE CASCADE,
    sym INTEGER NOT NULL,
    t BIGINT NOT NULL,
    p NUMERIC(20, 2) NOT NULL,
    tf INTEGER[] NOT NULL,
    s INTEGER[] NOT NULL,
    c INTEGER[] NOT NULL,
    o INTEGER[] NOT NULL,
    f INTEGER[] NOT NULL,
    conf INTEGER[] NOT NULL,
    s_a INTEGER NOT NULL,
    f_a INTEGER NOT NULL,
    conf_a INTEGER NOT NULL,
    prob_cont INTEGER NOT NULL,
    sc_in INTEGER NOT NULL,
    sc_out INTEGER NOT NULL,
    hold INTEGER NOT NULL,
    tp_atr NUMERIC(10, 2) NOT NULL,
    sl_atr NUMERIC(10, 2) NOT NULL,
    hedge INTEGER NOT NULL,
    reasons INTEGER[] NOT NULL
);

-- Create indices for better query performance
CREATE INDEX idx_hl_mtf_context_sym ON hl_mtf_context(sym);
CREATE INDEX idx_hl_mtf_context_t ON hl_mtf_context(t);
CREATE INDEX idx_hl_mtf_context_created ON hl_mtf_context(created_at);

CREATE INDEX idx_hl_mtf_output_sym ON hl_mtf_output(sym);
CREATE INDEX idx_hl_mtf_output_t ON hl_mtf_output(t);
CREATE INDEX idx_hl_mtf_output_context ON hl_mtf_output(context_id);
CREATE INDEX idx_hl_mtf_output_created ON hl_mtf_output(created_at);

-- Create views for easier data access
CREATE VIEW hl_mtf_latest_context AS
SELECT DISTINCT ON (sym) *
FROM hl_mtf_context
ORDER BY sym, created_at DESC;

CREATE VIEW hl_mtf_latest_output AS
SELECT DISTINCT ON (sym) *
FROM hl_mtf_output
ORDER BY sym, created_at DESC;

-- Add comments for documentation
COMMENT ON TABLE hl_mtf_context IS 'Multi-timeframe context data from Hyperliquid';
COMMENT ON TABLE hl_mtf_output IS 'LLM predictions based on MTF context';

COMMENT ON COLUMN hl_mtf_context.sym IS 'Symbol ID (1=BTC, 2=ETH, 3=SOL, etc.)';
COMMENT ON COLUMN hl_mtf_context.t IS 'Unix timestamp';
COMMENT ON COLUMN hl_mtf_context.p IS 'Current price';
COMMENT ON COLUMN hl_mtf_context.exec_tf IS 'Execution timeframe in minutes';
COMMENT ON COLUMN hl_mtf_context.tf IS 'Timeframes array [10080, 1440, 240, 60, 15, 5] (1w, 1d, 4h, 1h, 15m, 5m)';
COMMENT ON COLUMN hl_mtf_context.px_z IS 'Price z-scores for each timeframe';
COMMENT ON COLUMN hl_mtf_context.v_z IS 'Volume z-scores for each timeframe';
COMMENT ON COLUMN hl_mtf_context.cvd_s IS 'CVD signal for each timeframe';
COMMENT ON COLUMN hl_mtf_context.cvd_lvl IS 'CVD level for each timeframe';
COMMENT ON COLUMN hl_mtf_context.oi_d IS 'Open interest delta for each timeframe';

COMMENT ON COLUMN hl_mtf_output.s IS 'Structure signals per timeframe';
COMMENT ON COLUMN hl_mtf_output.c IS 'Context signals per timeframe';
COMMENT ON COLUMN hl_mtf_output.o IS 'Orderflow signals per timeframe';
COMMENT ON COLUMN hl_mtf_output.f IS 'Flow signals per timeframe';
COMMENT ON COLUMN hl_mtf_output.conf IS 'Confidence scores per timeframe';
COMMENT ON COLUMN hl_mtf_output.s_a IS 'Aggregate structure signal';
COMMENT ON COLUMN hl_mtf_output.f_a IS 'Aggregate flow signal';
COMMENT ON COLUMN hl_mtf_output.prob_cont IS 'Probability of continuation (%)';
COMMENT ON COLUMN hl_mtf_output.tp_atr IS 'Take profit in ATR units';
COMMENT ON COLUMN hl_mtf_output.sl_atr IS 'Stop loss in ATR units';
