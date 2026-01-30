---
name: hyp-leverage
description: View or set leverage for a ticker
argument-hint: "<ticker> [leverage] [cross/isolated] - e.g., BTC 10 cross"
---

## View/Set Leverage

View current leverage settings or update them.

**Arguments:**
- `ticker` - The asset
- `leverage` (optional) - New leverage value (1-50)
- `type` (optional) - "cross" or "isolated" (default cross)

**Examples:**
- `BTC` - View BTC leverage settings
- `BTC 10` - Set BTC to 10x cross leverage
- `ETH 5 isolated` - Set ETH to 5x isolated margin

Run: `python scripts/hyp_leverage.py <TICKER> [LEVERAGE] [TYPE]`
