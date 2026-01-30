#!/usr/bin/env python
"""View recent trade fills on Hyperliquid."""
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_fills(ticker_filter=None, limit=20):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Get fills using the raw endpoint
    endpoint = hyp._add_to_request('order_fills', data={'user': hyp.account_address})
    fills = await hyp.http_client.request(**endpoint)

    print("=" * 80)
    print("RECENT TRADE FILLS")
    print("=" * 80)

    if not fills:
        print("No fills found.")
        await hyp.cleanup()
        return

    # Filter by ticker if specified
    if ticker_filter:
        ticker_filter = ticker_filter.upper()
        fills = [f for f in fills if f.get('coin', '').upper() == ticker_filter]

    # Limit results
    fills = fills[:limit]

    if not fills:
        print(f"No fills found for {ticker_filter}")
        await hyp.cleanup()
        return

    print(f"{'Time':19} {'Ticker':8} {'Side':5} {'Size':>12} {'Price':>12} {'Fee':>10} {'PnL':>12}")
    print("-" * 85)

    total_pnl = 0
    total_fees = 0

    for fill in fills:
        coin = fill.get('coin', 'N/A')
        side = 'BUY' if fill.get('side') == 'B' else 'SELL'
        size = float(fill.get('sz', 0))
        price = float(fill.get('px', 0))
        fee = float(fill.get('fee', 0))
        pnl = float(fill.get('closedPnl', 0))
        ts = fill.get('time', 0)

        total_pnl += pnl
        total_fees += fee

        # Format timestamp
        try:
            dt = datetime.fromtimestamp(ts / 1000)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            time_str = str(ts)

        pnl_str = f"${pnl:>10,.2f}" if pnl != 0 else ""
        print(f"{time_str:19} {coin:8} {side:5} {size:>12.4f} ${price:>10,.2f} ${fee:>9.4f} {pnl_str}")

    print("-" * 85)
    print(f"{'TOTALS':53} ${total_fees:>9.4f} ${total_pnl:>11,.2f}")
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

    asyncio.run(get_fills(ticker, limit))
