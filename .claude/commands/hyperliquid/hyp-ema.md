---
name: hyp-ema
description: EMA crossover with golden/death cross detection
argument-hint: <ticker> [timeframe] [fast] [slow]
---

## EMA/MA Crossover

Shows moving average crossovers, golden/death cross, and trend direction.

### Usage
```bash
python scripts/hyp_ema.py <ticker> [timeframe] [fast] [slow]
```

### Parameters
- `ticker`: Asset symbol (BTC, ETH, SOL, etc.)
- `timeframe`: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)
- `fast`: Fast EMA period (default: 20)
- `slow`: Slow EMA period (default: 50)

### Examples
```bash
python scripts/hyp_ema.py BTC              # EMA for BTC (20/50)
python scripts/hyp_ema.py ETH 4h           # EMA for ETH, 4h
python scripts/hyp_ema.py SOL 1d 50 200    # Classic golden cross setup
```

### Signal Interpretation
| Signal | Meaning | Strength |
|--------|---------|----------|
| Golden Cross | Fast crosses above slow (50/200) | STRONG BUY |
| Death Cross | Fast crosses below slow (50/200) | STRONG SELL |
| Bullish Crossover | Fast crosses above slow | BUY |
| Bearish Crossover | Fast crosses below slow | SELL |
| Bullish Trend | Price > Fast > Slow | BULLISH |
| Bearish Trend | Price < Fast < Slow | BEARISH |

### Common Setups
- **9/21**: Short-term momentum
- **20/50**: Medium-term trend
- **50/200**: Long-term trend (golden/death cross)
