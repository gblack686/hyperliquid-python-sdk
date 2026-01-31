# Paper Trading Status

View current status and performance of paper trading strategies.

## What to do

Run the scheduler with --status flag:

```bash
python -m scripts.paper_trading.scheduler --status
```

This will query the database and show:
   - Per-strategy performance (signals, wins, losses, P&L)
   - Combined metrics
   - Active signals with current unrealized P&L

## Expected Output Format

```
=== PAPER TRADING STATUS ===
Period: Last 24 hours

FUNDING_ARBITRAGE
  Signals: 8
  Wins: 5 (62.5%)
  Losses: 2
  Active: 1
  Avg P&L: +0.85%

GRID_TRADING
  Signals: 12
  Wins: 7 (58.3%)
  Losses: 4
  Active: 1
  Avg P&L: +0.42%

DIRECTIONAL_MOMENTUM
  Signals: 5
  Wins: 2 (40%)
  Losses: 2
  Active: 1
  Avg P&L: -0.15%

COMBINED
  Total Signals: 25
  Overall Win Rate: 56%
  Total P&L: +$45.20
  Best Strategy: FUNDING_ARBITRAGE

=== ACTIVE SIGNALS ===
BTC LONG (directional_momentum)
  Entry: $83,500 | Current: $84,200
  Unrealized: +0.84%
  Duration: 2h 15m
```

## Arguments

- `$ARGUMENTS` - Optional: period (24h, 7d, 30d, all_time)
