---
name: hyp-atr
description: ATR volatility with stop loss suggestions
argument-hint: <ticker> [timeframe] [period]
---

## ATR (Average True Range)

Shows volatility levels, suggested stop losses, and position sizing.

### Usage
```bash
python scripts/hyp_atr.py <ticker> [timeframe] [period]
```

### Parameters
- `ticker`: Asset symbol (BTC, ETH, SOL, etc.)
- `timeframe`: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)
- `period`: ATR period (default: 14)

### Examples
```bash
python scripts/hyp_atr.py BTC              # ATR for BTC
python scripts/hyp_atr.py ETH 4h           # ATR for ETH, 4h
python scripts/hyp_atr.py SOL 1d 21        # ATR for SOL, 21 period
```

### Volatility Levels
| Level | Meaning | Action |
|-------|---------|--------|
| HIGH | >1.5x average ATR | Reduce position size |
| INCREASING | >1.2x average ATR | Caution |
| NORMAL | 0.7-1.2x average ATR | Normal trading |
| LOW | <0.7x average ATR | Breakout potential |

### Stop Loss Usage
- **1x ATR**: Tight stop, high probability of hit
- **2x ATR**: Standard stop, balanced
- **3x ATR**: Wide stop, room for volatility
