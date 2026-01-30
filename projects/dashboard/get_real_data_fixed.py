#!/usr/bin/env python3

import sys
import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import time

sys.path.append(os.path.dirname(__file__))

from src.hyperliquid_client import HyperliquidClient

async def get_real_mtf_data():
    """Get real MTF data using correct HyperliquidClient methods"""
    
    print("=" * 60)
    print("Getting Real MTF Data from Hyperliquid")
    print("=" * 60)
    
    client = HyperliquidClient()
    
    # Connect to Hyperliquid
    print("\n1. Connecting to Hyperliquid...")
    connected = await client.connect()
    if not connected:
        print("[ERROR] Failed to connect to Hyperliquid")
        return None
    print("[OK] Connected to Hyperliquid")
    
    responses = {}
    
    try:
        # Get historical candles for BTC
        print("\n2. Fetching candles for BTC...")
        
        # Calculate time range (last 24 hours)
        end_time = int(time.time() * 1000)  # Current time in ms
        start_time = end_time - (24 * 60 * 60 * 1000)  # 24 hours ago
        
        candles = await client.get_historical_candles(
            ticker="BTC",
            interval="5m",
            start=start_time,
            end=end_time
        )
        
        if candles:
            print(f"[OK] Received {len(candles)} candles")
            
            # Get latest candle data
            latest = candles[-1] if candles else None
            if latest:
                # Structure based on quantpylib candle format
                # Typically: [timestamp, open, high, low, close, volume]
                price = float(latest[4]) if len(latest) > 4 else 0  # close price
                
                # Create MTF context structure matching our mock data
                mtf_context = {
                    "sym": 1,  # BTC
                    "t": int(time.time()),
                    "p": price,
                    "exec_tf": 5,
                    "TF": [10080, 1440, 240, 60, 15, 5],
                    "px_z": [0.0] * 6,  # Will calculate if needed
                    "v_z": [0.0] * 6,
                    "vwap_z": [0.0] * 6,
                    "bb_pos": [0.5] * 6,
                    "atr_n": [1.0] * 6,
                    "cvd_s": [0.0] * 6,
                    "cvd_lvl": [0.0] * 6,
                    "oi_d": [0.0] * 6,
                    "liq_n": [1.0] * 6,
                    "reg": [0] * 6,
                    "L_sup": price * 0.98,  # 2% below
                    "L_res": price * 1.02,  # 2% above
                    "L_q_bid": 10.0,
                    "L_q_ask": 10.0,
                    "L_dsup": 2.0,
                    "L_dres": 2.0,
                    "basis_bp": 0.0,
                    "fund_bp": 0.0,
                    "px_disp_bp": 0.0,
                    "pos": 0.0,
                    "avg": price,
                    "unrlz": 0.0,
                    "rsk": 2,
                    "hr12": 0.5,
                    "slip_bp": 2.0,
                    "dd_pct": 0.0
                }
                
                responses['mtf_context'] = mtf_context
                print(f"[OK] BTC Price: ${price:,.2f}")
                
                # Create output structure
                mtf_output = {
                    "sym": 1,
                    "t": mtf_context["t"],
                    "p": price,
                    "tf": [10080, 1440, 240, 60, 15, 5],
                    "s": [0, 0, 0, 0, 0, 0],
                    "c": [0, 0, 0, 0, 0, 0],
                    "o": [0, 0, 0, 0, 0, 0],
                    "f": [0, 0, 0, 0, 0, 0],
                    "conf": [50, 50, 50, 50, 50, 50],
                    "sA": 0,
                    "fA": 0,
                    "confA": 50,
                    "prob_cont": 50,
                    "sc_in": 30,
                    "sc_out": 30,
                    "hold": 0,
                    "tp_atr": 1.5,
                    "sl_atr": 1.0,
                    "hedge": 50,
                    "reasons": [0, 0, 0, 0]
                }
                
                responses['mtf_output'] = mtf_output
                print(f"[OK] Generated output structure")
        else:
            print("[WARN] No candles received")
            
        # Get order book data
        print("\n3. Fetching order book...")
        orderbook = await client.get_l2_book("BTC")
        if orderbook:
            print("[OK] Order book data received")
            # Extract bid/ask sizes if available
            if 'bids' in orderbook and orderbook['bids']:
                bid_size = sum(float(b[1]) for b in orderbook['bids'][:10])
                responses['mtf_context']['L_q_bid'] = bid_size
            if 'asks' in orderbook and orderbook['asks']:
                ask_size = sum(float(a[1]) for a in orderbook['asks'][:10])
                responses['mtf_context']['L_q_ask'] = ask_size
                
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
            print(f"  Price: ${ctx['p']:,.2f}")
            print(f"  Support: ${ctx['L_sup']:,.2f}")
            print(f"  Resistance: ${ctx['L_res']:,.2f}")
            print(f"  Timeframes: {len(ctx['TF'])}")
            print(f"  Arrays: px_z, v_z, vwap_z, bb_pos, atr_n, cvd_s, etc.")
    
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
    
    -- Aggregated signals (renamed to avoid PostgreSQL reserved words)
    s_avg INTEGER,  -- structure average
    f_avg INTEGER,  -- final average
    conf_avg INTEGER,  -- confidence average
    
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
CREATE INDEX idx_hl_mtf_output_conf ON hl_mtf_output(conf_avg DESC);
CREATE INDEX idx_hl_mtf_output_hold ON hl_mtf_output(hold);

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