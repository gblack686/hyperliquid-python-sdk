#!/usr/bin/env python
"""View recent liquidations on Hyperliquid."""
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_liquidations(ticker_filter=None, limit=20):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    print("=" * 80)
    print("RECENT LIQUIDATIONS")
    print("=" * 80)

    # Note: Hyperliquid doesn't have a direct liquidations endpoint in the public API
    # This would need to use websocket subscription or external data source
    # For now, we'll show a placeholder with instructions

    print()
    print("Liquidation data requires websocket subscription to 'liquidations' channel.")
    print()
    print("To watch live liquidations, the SDK would need to subscribe to:")
    print("  {'type': 'subscribe', 'channel': 'liquidations'}")
    print()
    print("Alternative: Check Hyperliquid's liquidation feed at:")
    print("  https://app.hyperliquid.xyz/liquidations")
    print()

    # We can show user's own liquidations from fills if any
    endpoint = hyp._add_to_request('order_fills', data={'user': hyp.account_address})
    fills = await hyp.http_client.request(**endpoint)

    liq_fills = [f for f in fills if f.get('liquidation', False) or 'liq' in str(f.get('oid', '')).lower()]

    if liq_fills:
        print("YOUR LIQUIDATION HISTORY:")
        print(f"  {'Time':19} {'Ticker':8} {'Side':5} {'Size':>12} {'Price':>12}")
        print("-" * 65)

        for fill in liq_fills[:limit]:
            ticker = fill.get('coin', 'N/A')
            side = 'LONG' if fill.get('side') == 'B' else 'SHORT'
            size = float(fill.get('sz', 0))
            price = float(fill.get('px', 0))
            ts = fill.get('time', 0)

            try:
                dt = datetime.fromtimestamp(ts / 1000)
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = str(ts)

            print(f"  {time_str:19} {ticker:8} {side:5} {size:>12.4f} ${price:>10,.2f}")
    else:
        print("No liquidations in your account history.")

    print("=" * 80)
    await hyp.cleanup()

if __name__ == "__main__":
    ticker = None
    limit = 20

    for arg in sys.argv[1:]:
        if arg.isdigit():
            limit = int(arg)
        else:
            ticker = arg

    asyncio.run(get_liquidations(ticker, limit))
