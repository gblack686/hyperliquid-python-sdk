#!/usr/bin/env python3

import subprocess
import time
import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path
from loguru import logger

# Test API and capture responses
def test_api_endpoints():
    """Test API endpoints and capture response structures"""
    base_url = "http://localhost:8000"
    responses = {}
    
    # Start API server
    print("Starting API server...")
    api_process = subprocess.Popen(
        [sys.executable, "run_mtf_api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent
    )
    
    # Wait for server to start
    time.sleep(10)
    
    try:
        # Test MTF context endpoint
        print("Testing MTF context endpoint...")
        response = requests.get(f"{base_url}/api/mtf/context/BTC-USD?exec_tf=5", timeout=30)
        if response.status_code == 200:
            responses['mtf_context'] = response.json()
            print(f"✓ MTF context captured: {len(responses['mtf_context'])} fields")
        
        # Test batch endpoint
        print("Testing batch MTF endpoint...")
        response = requests.get(f"{base_url}/api/mtf/batch?symbols=BTC-USD,ETH-USD&exec_tf=5", timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                responses['mtf_batch'] = data[0]  # Same structure as single
        
        # Test process endpoint
        if 'mtf_context' in responses:
            print("Testing MTF process endpoint...")
            response = requests.post(f"{base_url}/api/mtf/process", json=responses['mtf_context'], timeout=30)
            if response.status_code == 200:
                responses['mtf_output'] = response.json()
                print(f"✓ MTF output captured: {len(responses['mtf_output'])} fields")
        
    except Exception as e:
        print(f"Error testing API: {e}")
    finally:
        # Stop API server
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except:
            api_process.kill()
    
    return responses

def generate_supabase_sql(responses):
    """Generate SQL for creating Supabase tables based on responses"""
    
    sql_commands = []
    
    # Create hl_mtf_context table
    if 'mtf_context' in responses:
        sql_commands.append("""
-- Table for MTF context data
CREATE TABLE IF NOT EXISTS hl_mtf_context (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Symbol and timing
    sym INTEGER NOT NULL,
    symbol_name TEXT,
    t BIGINT NOT NULL,
    timestamp_utc TIMESTAMPTZ,
    p DECIMAL(20, 8) NOT NULL,
    exec_tf INTEGER NOT NULL,
    
    -- Arrays stored as JSONB for flexibility
    tf JSONB NOT NULL,  -- timeframes array
    px_z JSONB NOT NULL,  -- price z-scores array
    v_z JSONB NOT NULL,  -- volume z-scores array
    vwap_z JSONB NOT NULL,  -- VWAP z-scores array
    bb_pos JSONB NOT NULL,  -- Bollinger Band positions array
    atr_n JSONB NOT NULL,  -- ATR normalized array
    cvd_s JSONB NOT NULL,  -- CVD slopes array
    cvd_lvl JSONB NOT NULL,  -- CVD levels array
    oi_d JSONB NOT NULL,  -- OI deltas array
    liq_n JSONB NOT NULL,  -- Liquidity norms array
    reg JSONB NOT NULL,  -- Regression trends array
    
    -- Support/Resistance levels
    l_sup DECIMAL(20, 8),
    l_res DECIMAL(20, 8),
    l_q_bid DECIMAL(20, 8),
    l_q_ask DECIMAL(20, 8),
    l_dsup DECIMAL(10, 4),
    l_dres DECIMAL(10, 4),
    
    -- Basis and funding
    basis_bp DECIMAL(10, 2),
    fund_bp DECIMAL(10, 2),
    px_disp_bp DECIMAL(10, 2),
    
    -- Position data
    pos DECIMAL(20, 8),
    avg DECIMAL(20, 8),
    unrlz DECIMAL(20, 8),
    rsk INTEGER,
    
    -- Risk metrics
    hr12 DECIMAL(10, 4),
    slip_bp DECIMAL(10, 2),
    dd_pct DECIMAL(10, 4),
    
    -- Indexes
    CONSTRAINT hl_mtf_context_sym_t_unique UNIQUE (sym, t)
);

-- Create indexes for performance
CREATE INDEX idx_hl_mtf_context_sym ON hl_mtf_context(sym);
CREATE INDEX idx_hl_mtf_context_timestamp ON hl_mtf_context(t DESC);
CREATE INDEX idx_hl_mtf_context_created ON hl_mtf_context(created_at DESC);
CREATE INDEX idx_hl_mtf_context_symbol_name ON hl_mtf_context(symbol_name);

-- Enable Row Level Security
ALTER TABLE hl_mtf_context ENABLE ROW LEVEL SECURITY;
""")
    
    # Create hl_mtf_output table (LLM processed signals)
    if 'mtf_output' in responses:
        sql_commands.append("""
-- Table for MTF output/signals
CREATE TABLE IF NOT EXISTS hl_mtf_output (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Link to context
    context_id UUID REFERENCES hl_mtf_context(id),
    
    -- Symbol and timing
    sym INTEGER NOT NULL,
    t BIGINT NOT NULL,
    p DECIMAL(20, 8) NOT NULL,
    
    -- Arrays stored as JSONB
    tf JSONB NOT NULL,  -- timeframes
    s JSONB NOT NULL,  -- structure scores
    c JSONB NOT NULL,  -- confluence scores
    o JSONB NOT NULL,  -- order flow scores
    f JSONB NOT NULL,  -- final scores
    conf JSONB NOT NULL,  -- confidence levels
    
    -- Aggregate scores
    s_a INTEGER,  -- structure average
    f_a INTEGER,  -- final average
    conf_a INTEGER,  -- confidence average
    
    -- Trading signals
    prob_cont INTEGER,  -- probability of continuation
    sc_in INTEGER,  -- score in
    sc_out INTEGER,  -- score out
    hold INTEGER,  -- hold signal (0/1)
    
    -- Risk management
    tp_atr DECIMAL(10, 4),  -- take profit in ATR
    sl_atr DECIMAL(10, 4),  -- stop loss in ATR
    hedge INTEGER,  -- hedge percentage
    
    -- Reasons array
    reasons JSONB,
    
    -- Indexes
    CONSTRAINT hl_mtf_output_sym_t_unique UNIQUE (sym, t)
);

-- Create indexes
CREATE INDEX idx_hl_mtf_output_sym ON hl_mtf_output(sym);
CREATE INDEX idx_hl_mtf_output_timestamp ON hl_mtf_output(t DESC);
CREATE INDEX idx_hl_mtf_output_created ON hl_mtf_output(created_at DESC);
CREATE INDEX idx_hl_mtf_output_context ON hl_mtf_output(context_id);
CREATE INDEX idx_hl_mtf_output_conf_a ON hl_mtf_output(conf_a DESC);
CREATE INDEX idx_hl_mtf_output_hold ON hl_mtf_output(hold);

-- Enable Row Level Security
ALTER TABLE hl_mtf_output ENABLE ROW LEVEL SECURITY;
""")
    
    # Create a summary view
    sql_commands.append("""
-- Create a view for easy querying
CREATE OR REPLACE VIEW hl_mtf_summary AS
SELECT 
    c.id,
    c.created_at,
    c.symbol_name,
    c.p as price,
    c.exec_tf,
    c.l_sup as support,
    c.l_res as resistance,
    c.basis_bp,
    c.fund_bp,
    o.conf_a as confidence,
    o.hold,
    o.prob_cont,
    o.tp_atr,
    o.sl_atr,
    o.hedge,
    o.reasons
FROM hl_mtf_context c
LEFT JOIN hl_mtf_output o ON c.sym = o.sym AND c.t = o.t
ORDER BY c.created_at DESC;

-- Grant permissions (adjust as needed)
GRANT SELECT ON hl_mtf_summary TO authenticated;
GRANT ALL ON hl_mtf_context TO authenticated;
GRANT ALL ON hl_mtf_output TO authenticated;
""")
    
    # Create RLS policies
    sql_commands.append("""
-- RLS Policies for authenticated users
CREATE POLICY "Enable read for authenticated users" ON hl_mtf_context
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable insert for authenticated users" ON hl_mtf_context
    FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Enable update for authenticated users" ON hl_mtf_context
    FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Enable read for authenticated users" ON hl_mtf_output
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable insert for authenticated users" ON hl_mtf_output
    FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Enable update for authenticated users" ON hl_mtf_output
    FOR UPDATE TO authenticated USING (true);
""")
    
    return sql_commands

def main():
    print("=" * 60)
    print("Testing API and Creating Supabase Tables")
    print("=" * 60)
    
    # Test API endpoints
    responses = test_api_endpoints()
    
    if not responses:
        print("Failed to get API responses")
        return 1
    
    # Save responses for reference
    with open('api_responses.json', 'w') as f:
        json.dump(responses, f, indent=2, default=str)
    print(f"\nAPI responses saved to api_responses.json")
    
    # Generate SQL
    sql_commands = generate_supabase_sql(responses)
    
    # Save SQL to file
    sql_file = Path('create_hl_tables.sql')
    with open(sql_file, 'w') as f:
        f.write("-- Supabase tables for Hyperliquid MTF data\n")
        f.write("-- Generated: " + datetime.now().isoformat() + "\n\n")
        for cmd in sql_commands:
            f.write(cmd)
            f.write("\n\n")
    
    print(f"\nSQL commands saved to {sql_file}")
    
    # Print sample data structure
    print("\n" + "=" * 60)
    print("Sample Data Structures:")
    print("=" * 60)
    
    if 'mtf_context' in responses:
        ctx = responses['mtf_context']
        print("\nMTF Context Fields:")
        for key in sorted(ctx.keys()):
            val = ctx[key]
            if isinstance(val, list):
                print(f"  {key}: array[{len(val)}]")
            else:
                print(f"  {key}: {type(val).__name__}")
    
    if 'mtf_output' in responses:
        out = responses['mtf_output']
        print("\nMTF Output Fields:")
        for key in sorted(out.keys()):
            val = out[key]
            if isinstance(val, list):
                print(f"  {key}: array[{len(val)}]")
            else:
                print(f"  {key}: {type(val).__name__}")
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Review the generated SQL in 'create_hl_tables.sql'")
    print("2. Run the SQL in your Supabase SQL editor")
    print("3. Test data insertion with the API")
    print("4. Set up periodic data collection")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())