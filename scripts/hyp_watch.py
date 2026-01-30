#!/usr/bin/env python
"""Watch live Hyperliquid prices via websocket."""
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def watch_price(ticker, duration=30):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    ticker = ticker.upper()
    print("=" * 50)
    print(f"WATCHING {ticker} (press Ctrl+C to stop)")
    print("=" * 50)

    last_price = None

    async def price_handler(msg):
        nonlocal last_price
        try:
            if 'mids' in msg.get('data', {}):
                mids = msg['data']['mids']
                if ticker in mids:
                    price = float(mids[ticker])
                    now = datetime.now().strftime('%H:%M:%S')

                    if last_price:
                        change = price - last_price
                        pct = (change / last_price) * 100
                        arrow = '+' if change >= 0 else ''
                        print(f"[{now}] {ticker}: ${price:,.2f} ({arrow}{change:,.2f} / {arrow}{pct:.3f}%)")
                    else:
                        print(f"[{now}] {ticker}: ${price:,.2f}")

                    last_price = price
        except Exception as e:
            pass

    await hyp.all_mids_subscribe(handler=price_handler)

    try:
        await asyncio.sleep(duration)
    except asyncio.CancelledError:
        pass

    await hyp.all_mids_unsubscribe()
    print()
    print(f"Stopped watching {ticker}")
    print("=" * 50)
    await hyp.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hyp_watch.py <ticker> [seconds]")
        sys.exit(1)

    ticker = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    asyncio.run(watch_price(ticker, duration))
