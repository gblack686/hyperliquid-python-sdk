# Websocket Streaming Setup

## Purpose

Set up Supabase tables and configuration for streaming Hyperliquid indicators.

## Instructions

### Step 1: Create Supabase Tables

Run this migration to create the required tables:

```sql
-- Trading indicators table for real-time streaming
CREATE TABLE IF NOT EXISTS trading_indicators (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- Price data
    price DECIMAL(20, 8) NOT NULL,

    -- EMAs
    ema9 DECIMAL(20, 8),
    ema20 DECIMAL(20, 8),
    ema50 DECIMAL(20, 8),

    -- RSI
    rsi DECIMAL(5, 2),
    rsi_trend VARCHAR(10),

    -- MACD
    macd_line DECIMAL(20, 8),
    macd_signal DECIMAL(20, 8),
    macd_histogram DECIMAL(20, 8),
    macd_side VARCHAR(10),
    macd_momentum VARCHAR(15),

    -- Volume
    volume DECIMAL(20, 8),
    volume_avg DECIMAL(20, 8),
    volume_ratio DECIMAL(10, 2),
    volume_trend VARCHAR(15),

    -- Bollinger Bands
    bb_upper DECIMAL(20, 8),
    bb_middle DECIMAL(20, 8),
    bb_lower DECIMAL(20, 8),
    bb_position DECIMAL(5, 2),

    -- Trend
    trend VARCHAR(10),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast queries
CREATE INDEX idx_indicators_ticker_tf ON trading_indicators(ticker, timeframe);
CREATE INDEX idx_indicators_timestamp ON trading_indicators(timestamp DESC);

-- Trim signals table
CREATE TABLE IF NOT EXISTS trim_signals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,

    -- Position info
    position_size DECIMAL(20, 8),
    entry_price DECIMAL(20, 8),
    current_price DECIMAL(20, 8),
    pnl_percent DECIMAL(10, 2),

    -- Signal
    trim_score INTEGER,
    recommendation VARCHAR(20),
    trim_percent DECIMAL(5, 2),
    reason TEXT,

    -- Key levels
    ema9_1h DECIMAL(20, 8),
    ema20_1h DECIMAL(20, 8),
    ema9_4h DECIMAL(20, 8),

    -- Timestamps
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trim_ticker ON trim_signals(ticker);
CREATE INDEX idx_trim_timestamp ON trim_signals(timestamp DESC);

-- Enable realtime for live updates
ALTER PUBLICATION supabase_realtime ADD TABLE trading_indicators;
ALTER PUBLICATION supabase_realtime ADD TABLE trim_signals;
```

### Step 2: Get Supabase Credentials

Add to your `.env` file:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### Step 3: Install Dependencies

```bash
pip install supabase websockets
```

### Step 4: Test Connection

```bash
python scripts/hyp_indicator_stream.py --test
```

## Verification

After setup, verify tables exist:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('trading_indicators', 'trim_signals');
```
