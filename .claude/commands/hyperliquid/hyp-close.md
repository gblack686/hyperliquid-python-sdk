---
name: hyp-close
description: Close an open position (market order)
argument-hint: "<ticker> [percent] - e.g., BTC 100 or BTC 50"
---

## Close Position

Close all or part of a position with a market order.

**Arguments:**
- `ticker` - The position to close
- `percent` (optional) - Percentage to close (default 100%)

**Examples:**
- `BTC` - Close entire BTC position
- `BTC 50` - Close 50% of BTC position
- `ETH 25` - Close 25% of ETH position

Run: `python scripts/hyp_close.py <TICKER> [PERCENT]`

**CAUTION:** This executes a market order on mainnet.
