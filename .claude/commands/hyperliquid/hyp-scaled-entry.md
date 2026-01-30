---
name: hyp-scaled-entry
description: Layer into a position at multiple price levels
argument-hint: <ticker> <side> <total_size> <start_price> <end_price> [layers] [--execute]
---

## Scaled Entry

Divides a position into multiple layers at progressively better prices (DCA-style entry).

### How It Works
- Splits `total_size` into `N` equal layers
- Places limit orders from `start_price` to `end_price`
- Uses linear price spacing between layers

### Usage
```bash
python scripts/hyp_scaled_entry.py <ticker> <side> <total_size> <start_price> <end_price> [layers] [--execute]
```

### Examples
```bash
# Preview: 5 layers of BTC longs from $80k to $75k
python scripts/hyp_scaled_entry.py BTC long 0.01 80000 75000 5

# Execute: 4 layers of ETH shorts from $2600 to $2800
python scripts/hyp_scaled_entry.py ETH short 0.1 2600 2800 4 --execute
```

### Output
```
ORDER PLAN:
----------------------------------------------------------------------
  Layer           Price          Size        Notional    From Market
----------------------------------------------------------------------
      1  $   80,000.00      0.002000  $      160.00        -3.50%
      2  $   78,750.00      0.002000  $      157.50        -5.00%
      3  $   77,500.00      0.002000  $      155.00        -6.50%
      4  $   76,250.00      0.002000  $      152.50        -8.00%
      5  $   75,000.00      0.002000  $      150.00        -9.50%
----------------------------------------------------------------------
```

### Notes
- Preview mode by default (add `--execute` to place orders)
- Orders are placed with reduce_only=False
- Each layer gets equal size (total_size / layers)
