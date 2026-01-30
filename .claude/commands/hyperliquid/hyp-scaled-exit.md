---
name: hyp-scaled-exit
description: Set multiple take-profit levels with a stop loss
argument-hint: <ticker> <tp1> <tp2> <tp3> <sl> [--execute] [--monitor]
---

## Scaled Exit (TP/SL)

Places multiple take-profit orders at different levels with a stop-loss.

### How It Works
- Divides position into N parts (one for each TP level)
- Places limit orders at each TP price
- SL requires monitoring (Hyperliquid doesn't have native SL)
- When SL triggers, cancels remaining TPs and closes at market

### Usage
```bash
python scripts/hyp_scaled_exit.py <ticker> <tp1> <tp2> <tp3> <sl> [--execute] [--monitor]
```

### Examples
```bash
# Preview: TP at 2%, 4%, 6% with SL at -3%
python scripts/hyp_scaled_exit.py BTC 2 4 6 -3

# Execute: Place TP orders
python scripts/hyp_scaled_exit.py ETH 1.5 3 5 -2 --execute

# Execute and monitor for SL
python scripts/hyp_scaled_exit.py SOL 2 4 -1.5 --execute --monitor
```

### Output
```
EXIT PLAN:
----------------------------------------------------------------------
    Type     Level           Price          Size    Expected PnL
----------------------------------------------------------------------
     TP1     +2.0%  $   84,500.00      0.003333  $      56.00
     TP2     +4.0%  $   86,000.00      0.003333  $     112.00
     TP3     +6.0%  $   87,500.00      0.003333  $     168.00
      SL     -3.0%  $   80,275.00    (remaining)  $    -252.00
----------------------------------------------------------------------
```

### Notes
- Requires an open position in the specified ticker
- TP percentages must be positive, SL must be negative
- Use `--monitor` to actively watch for SL trigger
