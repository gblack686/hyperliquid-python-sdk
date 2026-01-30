#!/usr/bin/env python
"""Get Hyperliquid orderbook for a ticker."""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_orderbook(ticker, depth=5):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    book = await hyp.l2_book_get(ticker=ticker.upper(), depth=depth)

    print("=" * 60)
    print(f"ORDERBOOK: {ticker.upper()}")
    print("=" * 60)

    # Get mid price
    mid = await hyp.get_all_mids(ticker=ticker.upper())
    print(f"Mid Price: ${float(mid):,.4f}")
    print()

    print(f"{'ASKS':^28} | {'BIDS':^28}")
    print(f"{'Price':>14} {'Size':>12} | {'Price':>14} {'Size':>12}")
    print("-" * 60)

    # Book uses 'a' for asks and 'b' for bids (numpy arrays)
    asks_raw = book.get('a', book.get('asks', []))
    bids_raw = book.get('b', book.get('bids', []))

    asks = list(reversed(asks_raw[:depth])) if len(asks_raw) > 0 else []
    bids = list(bids_raw[:depth]) if len(bids_raw) > 0 else []

    max_len = max(len(asks), len(bids)) if asks or bids else 0
    for i in range(max_len):
        ask_str = ""
        bid_str = ""
        if i < len(asks):
            ask_str = f"${float(asks[i][0]):>12,.2f} {float(asks[i][1]):>11,.4f}"
        if i < len(bids):
            bid_str = f"${float(bids[i][0]):>12,.2f} {float(bids[i][1]):>11,.4f}"
        print(f"{ask_str:>28} | {bid_str:<28}")

    print("=" * 60)
    await hyp.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hyp_orderbook.py <ticker> [depth]")
        sys.exit(1)
    ticker = sys.argv[1]
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    asyncio.run(get_orderbook(ticker, depth))
