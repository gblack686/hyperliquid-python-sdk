---
name: hyp-trailing-stop
description: Start a trailing stop monitor for an open position
argument-hint: <ticker> <trail_pct> [--interval=5]
---

## Trailing Stop

Monitors an open position and closes it when price reverses by the specified percentage.

### How It Works
- For **LONG** positions: Stop trails below the highest price reached
- For **SHORT** positions: Stop trails above the lowest price reached
- When price reverses by `trail_pct`, position is closed at market

### Usage
```bash
python scripts/hyp_trailing_stop.py <ticker> <trail_pct> [--interval=5]
```

### Examples
```bash
# 2% trailing stop for BTC position
python scripts/hyp_trailing_stop.py BTC 2.0

# 1.5% trailing stop, check every 3 seconds
python scripts/hyp_trailing_stop.py ETH 1.5 --interval=3
```

### Output
```
08:30:15 | Price: $82,500.00 | Best: $83,000.00 | Stop: $81,340.00 | Dist: 1.40% | PnL: $+125.00
```

### Notes
- Requires an open position in the specified ticker
- Runs continuously until stop triggers or Ctrl+C
- Stop loss executes as market order when triggered
