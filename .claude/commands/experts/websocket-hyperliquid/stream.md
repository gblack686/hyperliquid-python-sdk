# Stream Indicators

## Purpose

Start streaming Hyperliquid indicators to Supabase for real-time dashboard updates and trim signal monitoring.

## Variables

- **TICKERS**: $ARGUMENTS or "BTC,ETH,XRP" (comma-separated ticker list)

## Instructions

### Step 1: Verify Prerequisites

Before starting the stream, verify:
1. Supabase tables exist (run `/experts:websocket-hyperliquid:setup` if not)
2. Environment variables are set in `.env`:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (or `SUPABASE_ANON_KEY`)
   - `ACCOUNT_ADDRESS` (for trim signals)

### Step 2: Start Streaming

```bash
cd C:\Users\gblac\OneDrive\Desktop\hyperliquid-python-sdk

# Stream specific tickers
python scripts/hyp_indicator_stream.py --tickers {TICKERS}

# Stream with custom interval (default 60s)
python scripts/hyp_indicator_stream.py --tickers {TICKERS} --interval 30

# Stream all available tickers
python scripts/hyp_indicator_stream.py --all
```

### Step 3: Monitor Output

The stream will output:
- Indicator calculations for each ticker/timeframe
- Trim signal scores for open positions
- Supabase push confirmations

## What Gets Streamed

### trading_indicators table
| Field | Description |
|-------|-------------|
| ticker | Asset symbol |
| timeframe | 15m, 1h, or 4h |
| price | Current price |
| ema9, ema20, ema50 | Exponential moving averages |
| rsi, rsi_trend | RSI value and direction |
| macd_line, macd_signal, macd_histogram | MACD components |
| macd_side, macd_momentum | BULLISH/BEARISH, STRENGTHENING/WEAKENING |
| volume, volume_avg, volume_ratio, volume_trend | Volume analysis |
| bb_upper, bb_middle, bb_lower, bb_position | Bollinger Bands |
| trend | BULLISH/BEARISH/MIXED |

### trim_signals table
| Field | Description |
|-------|-------------|
| ticker | Asset symbol |
| direction | LONG/SHORT |
| position_size | Position size |
| entry_price, current_price | Prices |
| pnl_percent | Current P&L % |
| trim_score | Signal score (-11 to +11) |
| recommendation | HOLD/TRIM_25/TRIM_50/EXIT_75 |
| trim_percent | Suggested trim % |
| reason | Explanation |
| ema9_1h, ema20_1h, ema9_4h | Key levels |

## Examples

```bash
# Stream XRP indicators
/experts:websocket-hyperliquid:stream XRP

# Stream multiple tickers
/experts:websocket-hyperliquid:stream BTC,ETH,XRP,SOL

# Stream with faster updates (30s)
/experts:websocket-hyperliquid:stream BTC,ETH --interval 30
```

## Background Streaming

To run as a background service:

```bash
# Windows (PowerShell)
Start-Process -NoNewWindow python "scripts/hyp_indicator_stream.py --tickers BTC,ETH,XRP"

# Linux/Mac
nohup python scripts/hyp_indicator_stream.py --tickers BTC,ETH,XRP &
```

## Stopping the Stream

Press `Ctrl+C` to gracefully stop the streaming service.
