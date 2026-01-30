---
name: hyp-bracket-order
description: Entry order with automatic TP and SL
argument-hint: <ticker> <side> <size> <entry> <tp_pct> <sl_pct> [--execute]
---

## Bracket Order

Places an entry order with automatic take-profit and stop-loss. Monitors until one side hits.

### How It Works
1. Places entry order (market or limit)
2. Waits for entry fill
3. Places TP limit order
4. Monitors for TP fill or SL trigger
5. When SL triggers, cancels TP and closes at market

### Usage
```bash
python scripts/hyp_bracket_order.py <ticker> <side> <size> <entry> <tp_pct> <sl_pct> [--execute]
```

### Parameters
- `entry`: Price for limit entry, or "market" for market order
- `tp_pct`: Take profit percentage (positive)
- `sl_pct`: Stop loss percentage (negative)

### Examples
```bash
# Preview: Long BTC at $80k with 5% TP and 2% SL
python scripts/hyp_bracket_order.py BTC long 0.001 80000 5 -2

# Execute: Short ETH at market with 3% TP and 1.5% SL
python scripts/hyp_bracket_order.py ETH short 0.01 market 3 -1.5 --execute

# Execute: Long SOL at limit $100 with 4% TP and 2% SL
python scripts/hyp_bracket_order.py SOL long 1 100 4 -2 --execute
```

### Output
```
BRACKET ORDER PREVIEW
======================================================================
  Ticker:        BTC
  Side:          LONG
  Size:          0.001
  Current Price: $82,754.50

ORDER LEVELS:
----------------------------------------------------------------------
  Entry:    $80,000.00 (LIMIT)
  TP:       $84,000.00 (+5.0%) -> PnL: $4.00
  SL:       $78,400.00 (-2.0%) -> PnL: $-1.60
----------------------------------------------------------------------
  Notional:     $80.00
  Risk/Reward:  1:2.50
```

### Notes
- Monitors continuously after entry fills
- SL is monitored (not a native order) - requires script running
- Ctrl+C stops monitoring but leaves position/orders active
