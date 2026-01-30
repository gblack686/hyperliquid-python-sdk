#!/usr/bin/env python3

import sys
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from loguru import logger

sys.path.append(os.path.dirname(__file__))

from src.api.mtf_data_feed import MTFDataFeedService

async def get_real_mtf_data():
    """Get real MTF data directly from the service"""
    
    print("=" * 60)
    print("Getting Real MTF Data from Hyperliquid")
    print("=" * 60)
    
    service = MTFDataFeedService()
    
    # Initialize the service
    print("\n1. Initializing service...")
    await service.initialize()
    print("[OK] Service initialized")
    
    responses = {}
    
    try:
        # Get MTF context for BTC
        print("\n2. Fetching MTF context for BTC-USD...")
        btc_context = await service.calculate_mtf_metrics("BTC-USD", exec_tf=5)
        responses['mtf_context'] = btc_context.dict()
        
        print(f"[OK] BTC Price: ${btc_context.p:,.2f}")
        print(f"  Support: ${btc_context.L_sup:,.2f}")
        print(f"  Resistance: ${btc_context.L_res:,.2f}")
        print(f"  Bid Liquidity: {btc_context.L_q_bid:.2f}")
        print(f"  Ask Liquidity: {btc_context.L_q_ask:.2f}")
        
        # Process the context to get signals
        print("\n3. Processing MTF data for signals...")
        output = await service.process_llm_output(btc_context)
        responses['mtf_output'] = output.dict()
        
        print(f"[OK] Confidence: {output.confA}%")
        print(f"  Hold Signal: {'Yes' if output.hold else 'No'}")
        print(f"  Probability of Continuation: {output.prob_cont}%")
        print(f"  TP (ATR): {output.tp_atr}")
        print(f"  SL (ATR): {output.sl_atr}")
        
        # Try ETH as well
        print("\n4. Fetching MTF context for ETH-USD...")
        eth_context = await service.calculate_mtf_metrics("ETH-USD", exec_tf=5)
        responses['eth_context'] = eth_context.dict()
        print(f"[OK] ETH Price: ${eth_context.p:,.2f}")
        
    except Exception as e:
        print(f"\n[ERROR] Error getting real data: {e}")
        import traceback
        traceback.print_exc()
    
    # Save responses
    if responses:
        output_file = Path('real_api_responses.json')
        with open(output_file, 'w') as f:
            json.dump(responses, f, indent=2, default=str)
        print(f"\n[OK] Real API responses saved to {output_file}")
        
        # Print structure summary
        print("\n" + "=" * 60)
        print("Data Structure Summary:")
        print("=" * 60)
        
        if 'mtf_context' in responses:
            ctx = responses['mtf_context']
            print("\nMTF Context Fields:")
            for key in sorted(ctx.keys()):
                val = ctx[key]
                if isinstance(val, list):
                    print(f"  {key}: array[{len(val)}] = {val[:3]}..." if len(val) > 3 else f"  {key}: array[{len(val)}] = {val}")
                elif isinstance(val, (int, float)):
                    print(f"  {key}: {val}")
                else:
                    print(f"  {key}: {type(val).__name__}")
    
    return responses

def generate_supabase_tables(responses):
    """Generate Supabase SQL based on real data"""
    
    sql = []
    
    # hl_mtf_context table
    sql.append("""
-- ===========================================
-- Hyperliquid MTF Context Table
-- ===========================================

CREATE TABLE IF NOT EXISTS hl_mtf_context (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Core fields
    sym INTEGER NOT NULL,
    symbol_name TEXT,
    t BIGINT NOT NULL,
    timestamp_utc TIMESTAMPTZ GENERATED ALWAYS AS (to_timestamp(t)) STORED,
    p DECIMAL(20, 8) NOT NULL,
    exec_tf INTEGER NOT NULL,
    
    -- Timeframe arrays (JSONB for flexibility)
    tf JSONB NOT NULL,
    px_z JSONB NOT NULL,
    v_z JSONB NOT NULL,
    vwap_z JSONB NOT NULL,
    bb_pos JSONB NOT NULL,
    atr_n JSONB NOT NULL,
    cvd_s JSONB NOT NULL,
    cvd_lvl JSONB NOT NULL,
    oi_d JSONB NOT NULL,
    liq_n JSONB NOT NULL,
    reg JSONB NOT NULL,
    
    -- Market levels
    l_sup DECIMAL(20, 8),
    l_res DECIMAL(20, 8),
    l_q_bid DECIMAL(20, 8),
    l_q_ask DECIMAL(20, 8),
    l_dsup DECIMAL(10, 4),
    l_dres DECIMAL(10, 4),
    
    -- Market metrics
    basis_bp DECIMAL(10, 2),
    fund_bp DECIMAL(10, 2),
    px_disp_bp DECIMAL(10, 2),
    
    -- Position data
    pos DECIMAL(20, 8),
    avg DECIMAL(20, 8),
    unrlz DECIMAL(20, 8),
    rsk INTEGER,
    hr12 DECIMAL(10, 4),
    slip_bp DECIMAL(10, 2),
    dd_pct DECIMAL(10, 4)
);

-- Indexes for performance
CREATE INDEX idx_hl_mtf_context_sym_t ON hl_mtf_context(sym, t DESC);
CREATE INDEX idx_hl_mtf_context_created ON hl_mtf_context(created_at DESC);
CREATE INDEX idx_hl_mtf_context_symbol ON hl_mtf_context(symbol_name);
""")
    
    # hl_mtf_output table
    sql.append("""
-- ===========================================
-- Hyperliquid MTF Output (Signals) Table
-- ===========================================

CREATE TABLE IF NOT EXISTS hl_mtf_output (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Core fields
    sym INTEGER NOT NULL,
    t BIGINT NOT NULL,
    p DECIMAL(20, 8) NOT NULL,
    
    -- Signal arrays
    tf JSONB NOT NULL,
    s JSONB NOT NULL,  -- structure scores
    c JSONB NOT NULL,  -- confluence scores
    o JSONB NOT NULL,  -- order flow scores
    f JSONB NOT NULL,  -- final scores
    conf JSONB NOT NULL,  -- confidence levels
    
    -- Aggregated signals
    s_a INTEGER,  -- structure average (using underscore for PostgreSQL)
    f_a INTEGER,  -- final average
    conf_a INTEGER,  -- confidence average
    
    -- Trading metrics
    prob_cont INTEGER,
    sc_in INTEGER,
    sc_out INTEGER,
    hold INTEGER CHECK (hold IN (0, 1)),
    tp_atr DECIMAL(10, 4),
    sl_atr DECIMAL(10, 4),
    hedge INTEGER,
    reasons JSONB
);

-- Indexes
CREATE INDEX idx_hl_mtf_output_sym_t ON hl_mtf_output(sym, t DESC);
CREATE INDEX idx_hl_mtf_output_created ON hl_mtf_output(created_at DESC);
CREATE INDEX idx_hl_mtf_output_conf ON hl_mtf_output(conf_a DESC);
CREATE INDEX idx_hl_mtf_output_hold ON hl_mtf_output(hold);
""")
    
    # Combined view
    sql.append("""
-- ===========================================
-- Combined View for Easy Querying
-- ===========================================

CREATE OR REPLACE VIEW hl_mtf_analysis AS
SELECT 
    c.id,
    c.created_at,
    c.symbol_name,
    c.p as price,
    c.l_sup as support,
    c.l_res as resistance,
    c.l_q_bid as bid_liquidity,
    c.l_q_ask as ask_liquidity,
    c.basis_bp,
    c.fund_bp,
    o.conf_a as confidence,
    o.hold,
    o.prob_cont as continuation_prob,
    o.tp_atr,
    o.sl_atr,
    o.hedge,
    
    -- Calculate risk/reward ratio
    CASE 
        WHEN o.sl_atr > 0 THEN ROUND(o.tp_atr / o.sl_atr, 2)
        ELSE NULL 
    END as risk_reward_ratio,
    
    -- Signal strength
    CASE 
        WHEN o.conf_a >= 80 THEN 'STRONG'
        WHEN o.conf_a >= 60 THEN 'MODERATE'
        WHEN o.conf_a >= 40 THEN 'WEAK'
        ELSE 'VERY_WEAK'
    END as signal_strength
    
FROM hl_mtf_context c
LEFT JOIN hl_mtf_output o ON c.sym = o.sym AND c.t = o.t
ORDER BY c.created_at DESC;

-- Enable Row Level Security
ALTER TABLE hl_mtf_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE hl_mtf_output ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users
CREATE POLICY "Enable all for authenticated" ON hl_mtf_context
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Enable all for authenticated" ON hl_mtf_output
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
""")
    
    return '\n\n'.join(sql)

async def main():
    # Get real data
    responses = await get_real_mtf_data()
    
    if responses:
        # Generate SQL
        sql = generate_supabase_tables(responses)
        
        # Save SQL
        sql_file = Path('create_hl_tables_real.sql')
        with open(sql_file, 'w') as f:
            f.write("-- Supabase Tables for Hyperliquid MTF Data\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write("-- Based on REAL API responses\n\n")
            f.write(sql)
        
        print(f"\n[OK] SQL file created: {sql_file}")
        print("\nNext steps:")
        print("1. Open Supabase SQL editor")
        print("2. Run the SQL from 'create_hl_tables_real.sql'")
        print("3. Tables will be created with proper structure")
    else:
        print("\n[ERROR] Failed to get real data")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))