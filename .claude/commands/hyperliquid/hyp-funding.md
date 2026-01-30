---
name: hyp-funding
description: View funding rates for Hyperliquid perpetuals
argument-hint: "[tickers] - e.g., BTC ETH SOL (or 'top' for highest/lowest)"
---

## Fetch Hyperliquid Funding Rates

Get current funding rates for specified tickers, or show top highest/lowest rates.

Run this Python script:

```python
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_funding(tickers=None, show_top=False):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    funding_info = await hyp.get_funding_info()

    print("=" * 60)
    print("HYPERLIQUID FUNDING RATES (hourly)")
    print("=" * 60)

    if show_top:
        # Sort by funding rate
        sorted_funding = sorted(funding_info.items(), key=lambda x: float(x[1]['funding_rate']), reverse=True)

        print("\nTOP 10 HIGHEST (Longs Pay):")
        print(f"  {'Ticker':10} {'Rate':>12} {'APR':>12}")
        print("-" * 40)
        for ticker, info in sorted_funding[:10]:
            rate = float(info['funding_rate'])
            apr = rate * 24 * 365 * 100
            print(f"  {ticker:10} {rate*100:>11.4f}% {apr:>11.1f}%")

        print("\nTOP 10 LOWEST (Shorts Pay):")
        print(f"  {'Ticker':10} {'Rate':>12} {'APR':>12}")
        print("-" * 40)
        for ticker, info in sorted_funding[-10:]:
            rate = float(info['funding_rate'])
            apr = rate * 24 * 365 * 100
            print(f"  {ticker:10} {rate*100:>11.4f}% {apr:>11.1f}%")
    else:
        if tickers is None:
            tickers = ['BTC', 'ETH', 'SOL', 'HYPE']

        print(f"  {'Ticker':10} {'Rate':>12} {'APR':>12} {'Mark Price':>14}")
        print("-" * 55)
        for ticker in tickers:
            ticker_upper = ticker.upper()
            if ticker_upper in funding_info:
                info = funding_info[ticker_upper]
                rate = float(info['funding_rate'])
                apr = rate * 24 * 365 * 100
                mark = float(info['mark_price'])
                print(f"  {ticker_upper:10} {rate*100:>11.4f}% {apr:>11.1f}% ${mark:>13,.2f}")
            else:
                print(f"  {ticker_upper:10} NOT FOUND")

    print("=" * 60)
    await hyp.cleanup()

if __name__ == "__main__":
    show_top = 'top' in [arg.lower() for arg in sys.argv[1:]]
    tickers = [arg for arg in sys.argv[1:] if arg.lower() != 'top'] or None
    asyncio.run(get_funding(tickers, show_top))
```

Execute with: `python scripts/hyp_funding.py [TICKER1] [TICKER2] ...` or `python scripts/hyp_funding.py top`
