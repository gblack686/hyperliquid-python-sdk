# Fast Market Report

Ultra-fast market status report using parallel API fetching.

## Usage

```bash
python scripts/hyp_fast_report.py          # Text report
python scripts/hyp_fast_report.py --json   # JSON output
```

## What It Fetches (in parallel)

All data fetched in ~1.5 seconds:

| Data | Source | Purpose |
|------|--------|---------|
| Positions + Account | Hyperliquid | Your P&L |
| Prices + Funding | Hyperliquid | Current marks, funding APR |
| CVD (Taker Ratio) | Binance | Buy/sell pressure |
| OI Change | Binance | Deleveraging detection |
| L/S Ratio | Binance | Crowded side |

## Signals Summary

The report ends with quick signals:
- **CVD**: How many assets show BUYING vs SELLING
- **OI**: How many assets have falling OI (deleveraging)
- **L/S**: Average % of accounts that are long
- **Funding**: How many have negative funding (shorts paid)

## Performance

| Method | Time |
|--------|------|
| Sequential (old) | ~60s |
| Parallel (new) | **~1.5s** |

40x faster by running all 14 API calls in parallel with aiohttp.
