---
name: hyp-macd
description: MACD indicator with crossover detection
argument-hint: <ticker> [timeframe] [fast] [slow] [signal]
---

## MACD (Moving Average Convergence Divergence)

Shows MACD line, signal line, histogram, and crossover signals.

### Usage
```bash
python scripts/hyp_macd.py <ticker> [timeframe] [fast] [slow] [signal]
```

### Parameters
- `ticker`: Asset symbol (BTC, ETH, SOL, etc.)
- `timeframe`: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)
- `fast`: Fast EMA period (default: 12)
- `slow`: Slow EMA period (default: 26)
- `signal`: Signal line period (default: 9)

### Examples
```bash
python scripts/hyp_macd.py BTC              # MACD for BTC
python scripts/hyp_macd.py ETH 4h           # MACD for ETH, 4h
python scripts/hyp_macd.py SOL 1d 12 26 9   # Custom settings
```

### Signal Interpretation
| Signal | Meaning |
|--------|---------|
| Bullish Crossover | Histogram crosses above 0 - BUY signal |
| Bearish Crossover | Histogram crosses below 0 - SELL signal |
| Bullish | Histogram positive - Upward momentum |
| Bearish | Histogram negative - Downward momentum |
