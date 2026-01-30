---
name: hyp-stochastic
description: Stochastic oscillator with crossover signals
argument-hint: <ticker> [timeframe] [k_period] [d_period]
---

## Stochastic Oscillator

Shows %K, %D, crossovers, and overbought/oversold zones.

### Usage
```bash
python scripts/hyp_stochastic.py <ticker> [timeframe] [k_period] [d_period]
```

### Parameters
- `ticker`: Asset symbol (BTC, ETH, SOL, etc.)
- `timeframe`: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)
- `k_period`: %K period (default: 14)
- `d_period`: %D smoothing period (default: 3)

### Examples
```bash
python scripts/hyp_stochastic.py BTC              # Stochastic for BTC
python scripts/hyp_stochastic.py ETH 4h           # Stochastic for ETH, 4h
python scripts/hyp_stochastic.py SOL 1d 14 3      # Custom settings
```

### Signal Interpretation
| Signal | Meaning | Strength |
|--------|---------|----------|
| Bullish Cross in Oversold | %K crosses above %D below 20 | STRONG BUY |
| Bearish Cross in Overbought | %K crosses below %D above 80 | STRONG SELL |
| Bullish Crossover | %K crosses above %D | BUY |
| Bearish Crossover | %K crosses below %D | SELL |
| Overbought (>80) | Potential reversal down | CAUTION |
| Oversold (<20) | Potential reversal up | CAUTION |
