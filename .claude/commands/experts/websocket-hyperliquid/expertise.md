# Websocket Hyperliquid Expertise

## Complete Mental Model for Real-Time Trading Systems

### Architecture Overview

```
                    +------------------+
                    | Hyperliquid API  |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+       +-----------v-----------+
    | REST API          |       | WebSocket API         |
    | (Historical data) |       | (Real-time streams)   |
    +-------------------+       +-----------+-----------+
                                            |
                      +---------------------+----------------------+
                      |                     |                      |
            +---------v--------+  +---------v--------+  +---------v--------+
            | allMids          |  | trades           |  | userFills        |
            | (price updates)  |  | (trade tape)     |  | (your fills)     |
            +--------+---------+  +--------+---------+  +--------+---------+
                     |                     |                     |
                     +----------+----------+---------------------+
                                |
                     +----------v----------+
                     | Indicator Calculator |
                     | EMA, RSI, MACD, etc |
                     +----------+----------+
                                |
                     +----------v----------+
                     | Supabase            |
                     | - trading_indicators|
                     | - trim_signals      |
                     +----------+----------+
                                |
              +-----------------+------------------+
              |                 |                  |
    +---------v--------+  +----v-----+  +---------v--------+
    | Dashboard UI     |  | Alerts   |  | Trading Bot      |
    | (Realtime)       |  | (Telegram)|  | (Auto-execute)  |
    +------------------+  +----------+  +------------------+
```

### Data Flow Patterns

#### Pattern 1: Price-to-Indicator Pipeline
```
allMids WS -> Price Update -> Trigger Recalc -> Push to Supabase
                                    |
                              Fetch candles
                                    |
                              Calculate EMA/RSI/MACD
                                    |
                              Push trading_indicators
```

#### Pattern 2: Position Monitoring Pipeline
```
userFills WS -> Fill Event -> Update Position State
                                    |
                              Check trim conditions
                                    |
                              Calculate score
                                    |
                              Push trim_signals
                                    |
                              Trigger alert (optional)
```

### Indicator Calculation Deep Dive

#### EMA (Exponential Moving Average)
```python
def ema(data, period):
    k = 2 / (period + 1)  # Smoothing factor
    ema_vals = [data[0]]   # First value is same as data
    for i in range(1, len(data)):
        ema_vals.append(data[i] * k + ema_vals[-1] * (1 - k))
    return ema_vals
```

**Key insight:** EMA reacts faster to recent prices than SMA. The lower the period, the more reactive.

#### RSI (Relative Strength Index)
```python
def rsi(closes, period=14):
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
```

**Key insight:** RSI measures momentum, not direction. RSI 70+ in uptrend means strong momentum, not necessarily "sell."

#### MACD
```python
def macd(closes):
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
    signal = ema(macd_line, 9)
    histogram = macd_line[-1] - signal[-1]
    return {'line': macd_line[-1], 'signal': signal[-1], 'histogram': histogram}
```

**Key insight:** Histogram crossing zero is a momentum shift. Divergence between price and MACD often precedes reversals.

### Trim Signal Philosophy

The trim signal system is designed to:
1. **Protect profits** - Don't let winners turn to losers
2. **Reduce risk** - Scale out as momentum weakens
3. **Stay in trends** - Don't exit too early

#### Scoring Logic (for SHORT positions)

| Signal | Bearish (Hold) | Neutral | Bullish (Trim) |
|--------|---------------|---------|----------------|
| Price vs EMA9 | Below (+2) | At (0) | Above (-2) |
| Price vs EMA20 | Below (+2) | At (0) | Above (-3) |
| RSI 1H | <45 (+2) | 45-55 (0) | >55 (-2) |
| RSI Trend | Falling (+1) | Flat (0) | Rising (-1) |
| MACD Histogram | Negative (+2) | Near zero (0) | Positive (-2) |
| MACD Momentum | Strengthening (+1) | Flat (0) | Weakening (-1) |
| Volume on Bounce | Low (+1) | Normal (0) | High/Spike (-2) |
| 4H Trend | Bearish (+1) | Mixed (0) | Bullish (-2) |

**Maximum score:** +11 (all signals bearish = HOLD)
**Minimum score:** -14 (all signals bullish = EXIT)

### WebSocket Best Practices

#### 1. Connection Management
```python
# Always handle reconnection
while True:
    try:
        ws.run_forever()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        time.sleep(5)  # Backoff before reconnect
```

#### 2. Ping/Pong for Keep-Alive
```python
# Hyperliquid requires ping every 50 seconds
def send_ping():
    while True:
        time.sleep(50)
        ws.send(json.dumps({"method": "ping"}))
```

#### 3. Rate Limiting
- Hyperliquid WS has no explicit rate limit
- Supabase: ~1000 inserts/minute on free tier
- Batch inserts when possible

#### 4. Data Validation
```python
# Always validate before storing
def validate_indicator(data):
    required = ['ticker', 'timeframe', 'price', 'ema9', 'rsi']
    for field in required:
        if field not in data or data[field] is None:
            return False
    return True
```

### Supabase Schema Design

#### trading_indicators
```sql
CREATE TABLE trading_indicators (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    price DECIMAL(20, 8) NOT NULL,

    -- EMAs for trend
    ema9 DECIMAL(20, 8),
    ema20 DECIMAL(20, 8),
    ema50 DECIMAL(20, 8),

    -- RSI for momentum
    rsi DECIMAL(5, 2),
    rsi_trend VARCHAR(10),

    -- MACD for momentum direction
    macd_line DECIMAL(20, 8),
    macd_signal DECIMAL(20, 8),
    macd_histogram DECIMAL(20, 8),
    macd_side VARCHAR(10),
    macd_momentum VARCHAR(15),

    -- Volume for confirmation
    volume DECIMAL(20, 8),
    volume_avg DECIMAL(20, 8),
    volume_ratio DECIMAL(10, 2),
    volume_trend VARCHAR(15),

    -- Bollinger for volatility
    bb_upper DECIMAL(20, 8),
    bb_middle DECIMAL(20, 8),
    bb_lower DECIMAL(20, 8),
    bb_position DECIMAL(5, 2),

    -- Overall trend
    trend VARCHAR(10),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Composite index for common queries
CREATE INDEX idx_indicators_ticker_tf_ts
ON trading_indicators(ticker, timeframe, timestamp DESC);

-- Enable realtime
ALTER PUBLICATION supabase_realtime ADD TABLE trading_indicators;
```

### Common Issues & Solutions

#### Issue: Stale indicators
**Cause:** Candle data not updating
**Solution:** Use WebSocket candle subscription instead of REST polling

#### Issue: High Supabase costs
**Cause:** Too frequent inserts
**Solution:** Batch inserts, increase interval, use upsert

#### Issue: Trim signals not generating
**Cause:** No position or address not configured
**Solution:** Check ACCOUNT_ADDRESS in .env, verify positions exist

#### Issue: WebSocket disconnects
**Cause:** No ping, network issues
**Solution:** Implement ping/pong, auto-reconnect logic

### Frontend Integration (React Example)

```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

// Subscribe to real-time updates
const channel = supabase
  .channel('indicator-changes')
  .on(
    'postgres_changes',
    {
      event: 'INSERT',
      schema: 'public',
      table: 'trading_indicators',
      filter: 'ticker=eq.BTC'
    },
    (payload) => {
      console.log('New indicator:', payload.new)
      updateDashboard(payload.new)
    }
  )
  .subscribe()

// Cleanup
return () => {
  supabase.removeChannel(channel)
}
```

### Key Files Reference

| File | Purpose |
|------|---------|
| `scripts/hyp_indicator_stream.py` | Main streaming script |
| `scripts/hyp_trim_analyzer.py` | Standalone trim analysis |
| `hyperliquid/websocket_manager.py` | SDK WebSocket handling |
| `integrations/websocket/supabase_integration.py` | Fill tracking |
| `scripts/websocket_monitor.py` | Order event monitor |

### Performance Tuning

1. **Reduce timeframes:** Only track timeframes you use (e.g., just 1H)
2. **Selective tickers:** Don't stream all 100+ tickers
3. **Longer intervals:** 60s is fine for most use cases
4. **Upsert vs insert:** Update existing rows instead of always inserting
5. **Prune old data:** Delete indicators older than 24h

```sql
-- Prune old data
DELETE FROM trading_indicators
WHERE timestamp < NOW() - INTERVAL '24 hours';
```

This expert provides a complete foundation for building real-time trading dashboards, automated trim alerts, and signal-based trading systems using Hyperliquid data streamed to Supabase.
