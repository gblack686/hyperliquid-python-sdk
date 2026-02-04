# Websocket Expert - Question Mode

## Purpose

Answer questions about Hyperliquid websocket integration and indicator streaming.

## Variables

- **QUESTION**: $ARGUMENTS (the user's question)

## Knowledge Base

### Hyperliquid Websocket API

**Available Subscriptions:**
- `allMids`: Real-time mid prices for all assets
- `trades`: Live trade tape for specific coin
- `l2Book`: Order book updates
- `candle`: Candle/OHLCV updates
- `userFills`: User's trade fills
- `orderUpdates`: Order status changes
- `userEvents`: General user events (liquidations, etc.)

**Connection URL:** `wss://api.hyperliquid.xyz/ws`

**Subscription Format:**
```json
{"method": "subscribe", "subscription": {"type": "allMids"}}
{"method": "subscribe", "subscription": {"type": "trades", "coin": "BTC"}}
{"method": "subscribe", "subscription": {"type": "candle", "coin": "BTC", "interval": "1h"}}
```

### Indicator Calculations

**EMA (Exponential Moving Average):**
- Formula: EMA = Price * k + EMA_prev * (1-k), where k = 2/(period+1)
- Common periods: 9, 20, 50

**RSI (Relative Strength Index):**
- Period: 14 (standard)
- Overbought: > 70, Oversold: < 30
- Trend zones: Bullish > 50, Bearish < 50

**MACD:**
- Fast EMA: 12 periods
- Slow EMA: 26 periods
- Signal line: 9-period EMA of MACD line
- Histogram = MACD line - Signal line

**Bollinger Bands:**
- Middle: 20-period SMA
- Upper/Lower: +/- 2 standard deviations
- Position: 0 = at lower, 1 = at upper

### Trim Signal Scoring

**Score Range:** -11 to +11

| Score | Recommendation |
|-------|----------------|
| +6 to +11 | HOLD full position |
| +1 to +5 | HOLD (minor caution) |
| -4 to 0 | TRIM 25-33% |
| -7 to -5 | TRIM 50% |
| -11 to -8 | EXIT 75%+ |

### Supabase Integration

**Required Tables:**
- `trading_indicators`: Real-time indicator snapshots
- `trim_signals`: Position trim recommendations

**Realtime:**
- Tables are added to `supabase_realtime` publication
- Subscribe in frontend: `supabase.channel('indicators').on('postgres_changes', ...)`

### Common Files

| File | Purpose |
|------|---------|
| `scripts/hyp_indicator_stream.py` | Main streaming script |
| `scripts/hyp_trim_analyzer.py` | Trim signal calculator |
| `integrations/websocket/supabase_integration.py` | Fill/position tracking |
| `hyperliquid/websocket_manager.py` | SDK websocket handling |

## Instructions

Based on the QUESTION provided, answer using the knowledge base above. If the question requires:
- Code examples: Provide working Python snippets
- Architecture: Explain the data flow
- Troubleshooting: Check common issues
- Configuration: Reference .env variables

## Response Format

Provide a clear, concise answer. Include code examples when helpful. Reference specific files in the codebase when relevant.
