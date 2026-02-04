# Websocket Hyperliquid Expert

Expert for real-time streaming of Hyperliquid market data and trading indicators to Supabase.

## Overview

This expert helps you:
- Stream real-time price data via Hyperliquid websockets
- Calculate and stream technical indicators (EMA, RSI, MACD, Volume)
- Store indicator snapshots in Supabase for dashboards
- Monitor positions and trim signals in real-time
- Build automated trading signal pipelines

## Available Commands

| Command | Description |
|---------|-------------|
| `/experts:websocket-hyperliquid:setup` | Set up Supabase tables and configure streaming |
| `/experts:websocket-hyperliquid:stream` | Start streaming indicators to Supabase |
| `/experts:websocket-hyperliquid:question` | Ask questions about websocket streaming |
| `/experts:websocket-hyperliquid:expertise` | Full mental model for websocket trading systems |

## Key Concepts

### Hyperliquid Websocket API

Hyperliquid provides websocket feeds for:
- **allMids**: Real-time mid prices for all assets
- **trades**: Live trade tape
- **l2Book**: Order book updates
- **user**: Account/position updates

### Indicator Streaming Architecture

```
Hyperliquid WS → Calculate Indicators → Supabase → Dashboard/Alerts
      ↓                   ↓                 ↓
  Price feeds      EMA, RSI, MACD      Real-time UI
  Trade tape       Volume analysis     Trim signals
  Order book       Trim scores         Alert triggers
```

### Supabase Tables

The streaming system uses these tables:
- `trading_indicators`: Real-time indicator snapshots
- `trim_signals`: Position trim recommendations
- `price_history`: Historical price data for backtesting

## Quick Start

```bash
# 1. Set up Supabase tables
/experts:websocket-hyperliquid:setup

# 2. Start streaming
python scripts/hyp_indicator_stream.py --tickers BTC,ETH,XRP

# 3. View in Supabase dashboard or connect to your app
```

## Related Commands

- `/hyp-trim-analyzer` - Analyze positions for trim signals
- `/hyp-manage-stops` - Manage stop losses
- `/hyp-validate-coverage` - Validate position coverage
