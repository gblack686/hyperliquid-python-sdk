---
name: hyp-volume
description: Volume analysis with spike detection
argument-hint: <ticker> [timeframe] [lookback]
---

## Volume Analysis

Shows volume spikes, trends, and volume-price relationships.

### Usage
```bash
python scripts/hyp_volume.py <ticker> [timeframe] [lookback]
```

### Parameters
- `ticker`: Asset symbol (BTC, ETH, SOL, etc.)
- `timeframe`: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)
- `lookback`: MA period for comparison (default: 20)

### Examples
```bash
python scripts/hyp_volume.py BTC              # Volume for BTC
python scripts/hyp_volume.py ETH 4h           # Volume for ETH, 4h
python scripts/hyp_volume.py SOL 1d 50        # Volume for SOL, 50 bar MA
```

### Volume Levels
| Level | Spike Ratio | Meaning |
|-------|-------------|---------|
| EXTREME | >= 2.0x | Major interest, potential breakout |
| HIGH | >= 1.5x | Above average interest |
| ABOVE_AVERAGE | >= 1.0x | Normal to slightly elevated |
| BELOW_AVERAGE | >= 0.5x | Low interest |
| LOW | < 0.5x | Very weak conviction |

### Volume-Price Relationships
| Relationship | Meaning |
|--------------|---------|
| BULLISH_CONFIRMATION | Price up + Volume up = Strong move |
| BEARISH_CONFIRMATION | Price down + Volume up = Strong move |
| BULLISH_DIVERGENCE | Price up + Volume down = Weak move |
| BEARISH_DIVERGENCE | Price down + Volume down = Weak move |
