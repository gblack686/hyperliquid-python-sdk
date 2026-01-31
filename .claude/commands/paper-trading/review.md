# Paper Trading Review

Generate a comprehensive review of paper trading performance.

## What to do

1. Run the paper trading review script:
   ```bash
   python -m scripts.paper_trading.scheduler --review 24h
   ```

   Or programmatically:
   ```python
   import asyncio
   from scripts.paper_trading.scheduler import PaperTradingScheduler

   scheduler = PaperTradingScheduler()
   asyncio.run(scheduler.run_review("$ARGUMENTS"))
   ```

2. The review will:
   - Calculate metrics for all strategies over the specified period
   - Generate a formatted report
   - Optionally send summary to Telegram

## Arguments

- `$ARGUMENTS` - Period to review: `24h` (default), `7d`, `30d`, or `all_time`

## Expected Output

```
=== PAPER TRADING REVIEW ===
Period: 2026-01-30 00:00 to 2026-01-31 00:00 (24h)

FUNDING_ARBITRAGE
  Signals: 8
  Wins: 5 (62.5%)
  Losses: 2
  Active: 1
  Avg P&L: +0.85%
  Best: +2.1%
  Worst: -0.8%

GRID_TRADING
  Signals: 12
  Wins: 7 (58.3%)
  Losses: 4
  Active: 1
  Avg P&L: +0.42%
  Best: +1.5%
  Worst: -1.2%

DIRECTIONAL_MOMENTUM
  Signals: 5
  Wins: 2 (40%)
  Losses: 2
  Active: 1
  Avg P&L: -0.15%
  Best: +3.2%
  Worst: -2.5%

COMBINED
  Total Signals: 25
  Overall Win Rate: 56%
  Total P&L: +1.12% (+$11.20)
  Best Strategy: FUNDING_ARBITRAGE
```
