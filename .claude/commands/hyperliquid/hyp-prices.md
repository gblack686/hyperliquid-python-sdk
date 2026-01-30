---
name: hyp-prices
description: Get current mid prices for Hyperliquid tickers (default BTC, ETH, SOL or specify tickers)
argument-hint: "[tickers] - e.g., BTC ETH SOL HYPE"
---

## Fetch Hyperliquid Prices

Get current mid prices for specified tickers. If no tickers provided, defaults to BTC, ETH, SOL, HYPE.

Run this Python script with the user's specified tickers (or defaults):

```python
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_prices(tickers=None):
    if tickers is None:
        tickers = ['BTC', 'ETH', 'SOL', 'HYPE']

    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    mids = await hyp.get_all_mids()

    print("=" * 40)
    print("HYPERLIQUID PRICES")
    print("=" * 40)

    for ticker in tickers:
        ticker_upper = ticker.upper()
        if ticker_upper in mids:
            price = float(mids[ticker_upper])
            print(f"  {ticker_upper:8} ${price:>12,.4f}")
        else:
            print(f"  {ticker_upper:8} NOT FOUND")

    print("=" * 40)
    await hyp.cleanup()

# Parse tickers from args or use defaults
tickers = sys.argv[1:] if len(sys.argv) > 1 else None
asyncio.run(get_prices(tickers))
```

Execute with: `python scripts/hyp_prices.py [TICKER1] [TICKER2] ...`
