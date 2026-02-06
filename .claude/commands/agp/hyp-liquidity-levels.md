---
model: sonnet
description: Identify key liquidity zones for strategic order placement (TP/SL)
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Liquidity Levels

Identify key liquidity zones for strategic order placement (TP/SL).

## Usage

```bash
python scripts/hyp_liquidity_levels.py BTC              # Default 5% depth, SHORT bias
python scripts/hyp_liquidity_levels.py SOL --depth 10   # 10% depth analysis
python scripts/hyp_liquidity_levels.py XRP --side LONG  # LONG position suggestions
python scripts/hyp_liquidity_levels.py BTC --json       # JSON output
```

## What It Analyzes

| Section | Data | Purpose |
|---------|------|---------|
| Volume Profile | POC, VAH, VAL, HVN, LVN | Where price spent most time (support/resistance) |
| Orderbook Liquidity | Bid/Ask clusters | Where large orders sit (walls) |
| Liquidation Estimates | By leverage level | Where cascading liquidations cluster |
| Suggested Orders | TP/SL levels | Actionable levels based on liquidity |

## Key Concepts

### Volume Profile
- **POC (Point of Control)**: Price with highest volume - strongest S/R
- **VAH (Value Area High)**: Upper bound of 70% volume - resistance
- **VAL (Value Area Low)**: Lower bound of 70% volume - support
- **HVN (High Volume Node)**: Areas of acceptance, price tends to stay
- **LVN (Low Volume Node)**: Areas of rejection, price moves quickly through

### Orderbook Imbalance
- **BID heavy** (+imbalance): More buy orders = potential support
- **ASK heavy** (-imbalance): More sell orders = potential resistance

### Liquidation Levels
Shows where positions at common leverage (5x, 10x, 20x, 25x, 50x, 100x) would liquidate if entered at current price. Useful for identifying cascade zones.

## Strategy Tips

**For SHORT positions:**
- TP at HVN below current price (absorption zones)
- TP at VAL (lower value area boundary)
- SL above VAH (breakout invalidation)

**For LONG positions:**
- TP at HVN above current price
- TP at VAH (upper value area boundary)
- SL below VAL (breakdown invalidation)

## Sample Output

```
VOLUME PROFILE
  Point of Control (POC):  $ 64,065.87  (-1.00%)
  Value Area High (VAH):   $ 66,977.95  (+3.50%)
  Value Area Low (VAL):    $ 61,800.91  (-4.50%)

ORDERBOOK LIQUIDITY
  Total Bid Liquidity:  $2,125,354
  Total Ask Liquidity:  $4,676,832
  Imbalance:            -37.5% (ASK heavy)

SUGGESTED ORDER LEVELS (SHORT)
  TAKE PROFIT: $63,095.17 (+2.50%) [high_volume_node]
  STOP LOSS:   $66,977.95 (-3.50%) [value_area_high]
```
