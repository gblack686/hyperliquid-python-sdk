---
name: hyp-rsi
description: RSI indicator with multi-timeframe analysis
argument-hint: <ticker> [period] [timeframe]
---

## RSI (Relative Strength Index)

Shows RSI value, overbought/oversold zones, and multi-timeframe analysis.

### Usage
```bash
python scripts/hyp_rsi.py <ticker> [period] [timeframe]
```

### Parameters
- `ticker`: Asset symbol (BTC, ETH, SOL, etc.)
- `period`: RSI period (default: 14)
- `timeframe`: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)

### Examples
```bash
python scripts/hyp_rsi.py BTC              # RSI for BTC
python scripts/hyp_rsi.py ETH 14 4h        # RSI for ETH, 4h
python scripts/hyp_rsi.py SOL 21 1d        # RSI for SOL, 21 period
```

### Signal Interpretation
| RSI Range | Zone | Signal |
|-----------|------|--------|
| >= 80 | Extreme Overbought | STRONG SELL |
| 70-80 | Overbought | SELL |
| 50-70 | Bullish | - |
| 30-50 | Bearish | - |
| 20-30 | Oversold | BUY |
| <= 20 | Extreme Oversold | STRONG BUY |
