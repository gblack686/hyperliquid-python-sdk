---
name: hyp-bollinger
description: Bollinger Bands with squeeze detection
argument-hint: <ticker> [timeframe] [period] [std_dev]
---

## Bollinger Bands

Shows upper/lower bands, price position, and squeeze detection.

### Usage
```bash
python scripts/hyp_bollinger.py <ticker> [timeframe] [period] [std_dev]
```

### Parameters
- `ticker`: Asset symbol (BTC, ETH, SOL, etc.)
- `timeframe`: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)
- `period`: BB period (default: 20)
- `std_dev`: Standard deviation multiplier (default: 2.0)

### Examples
```bash
python scripts/hyp_bollinger.py BTC              # BB for BTC
python scripts/hyp_bollinger.py ETH 4h           # BB for ETH, 4h
python scripts/hyp_bollinger.py SOL 1d 20 2.5    # Custom settings
```

### Signal Interpretation
| Position | Signal | Meaning |
|----------|--------|---------|
| Above Upper | BREAKOUT UP | Overbought, potential reversal |
| Below Lower | BREAKOUT DOWN | Oversold, potential reversal |
| Squeeze | PREPARE | Low volatility, breakout imminent |
| 80-100% | Near Upper | Caution, approaching resistance |
| 0-20% | Near Lower | Caution, approaching support |
