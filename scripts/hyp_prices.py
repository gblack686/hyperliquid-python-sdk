#!/usr/bin/env python
"""Get current Hyperliquid prices for specified tickers."""
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

if __name__ == "__main__":
    tickers = sys.argv[1:] if len(sys.argv) > 1 else None
    asyncio.run(get_prices(tickers))
