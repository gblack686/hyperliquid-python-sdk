---
name: hyp-levels
description: Support and resistance level identification
argument-hint: <ticker> [timeframe] [lookback]
---

## Support & Resistance Levels

Identifies key price levels based on pivot points and price clustering.

### Usage
```bash
python scripts/hyp_levels.py <ticker> [timeframe] [lookback]
```

### Parameters
- `ticker`: Asset symbol (BTC, ETH, SOL, etc.)
- `timeframe`: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)
- `lookback`: Number of bars to analyze (default: 100)

### Examples
```bash
python scripts/hyp_levels.py BTC              # S/R for BTC
python scripts/hyp_levels.py ETH 4h           # S/R for ETH, 4h
python scripts/hyp_levels.py SOL 1d 200       # S/R for SOL, 200 bar lookback
```

### Signal Interpretation
| Signal | Meaning | Action |
|--------|---------|--------|
| AT RESISTANCE | Price at strong resistance | Watch for rejection |
| AT SUPPORT | Price at strong support | Watch for bounce |
| NEAR RESISTANCE | Price approaching resistance | Caution on longs |
| NEAR SUPPORT | Price approaching support | Caution on shorts |

### Level Strength
- Strength indicates how many times price has tested the level
- Higher strength = more significant level
- Look for confluence with other timeframes
