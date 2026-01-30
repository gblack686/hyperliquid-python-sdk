#!/usr/bin/env python
"""Open interest data for Hyperliquid."""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_oi(ticker=None, show_top=False):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    contexts = await hyp.perpetuals_contexts()
    universe_meta, universe_ctx = contexts[0]["universe"], contexts[1]

    print("=" * 70)
    print("OPEN INTEREST")
    print("=" * 70)

    oi_data = []
    for meta, ctx in zip(universe_meta, universe_ctx):
        name = meta['name']
        oi = float(ctx.get('openInterest', 0))
        mark = float(ctx.get('markPx', 0))
        oi_usd = oi * mark if mark > 0 else oi

        oi_data.append({
            'ticker': name,
            'oi': oi,
            'oi_usd': oi_usd,
            'mark': mark
        })

    # Filter or sort
    if ticker and ticker.lower() != 'top':
        ticker = ticker.upper()
        oi_data = [d for d in oi_data if d['ticker'].upper() == ticker]

        if not oi_data:
            print(f"No data found for {ticker}")
            await hyp.cleanup()
            return

        d = oi_data[0]
        print(f"\n{d['ticker']}:")
        print(f"  Open Interest:     {d['oi']:,.2f} contracts")
        print(f"  OI Value (USD):    ${d['oi_usd']:,.0f}")
        print(f"  Mark Price:        ${d['mark']:,.2f}")

    else:
        # Sort by OI value
        oi_data = sorted(oi_data, key=lambda x: x['oi_usd'], reverse=True)

        # Total OI
        total_oi = sum(d['oi_usd'] for d in oi_data)

        if show_top or ticker and ticker.lower() == 'top':
            oi_data = oi_data[:20]
            print("\nTOP 20 BY OPEN INTEREST:")
        else:
            oi_data = oi_data[:30]
            print("\nTOP 30 BY OPEN INTEREST:")

        print(f"  {'Ticker':10} {'OI (contracts)':>18} {'OI (USD)':>18} {'Mark':>12}")
        print("-" * 65)

        for d in oi_data:
            print(f"  {d['ticker']:10} {d['oi']:>18,.2f} ${d['oi_usd']:>16,.0f} ${d['mark']:>10,.2f}")

        print("-" * 65)
        print(f"  {'TOTAL':10} {' ':>18} ${total_oi:>16,.0f}")

    print("=" * 70)
    await hyp.cleanup()

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else None
    show_top = ticker and ticker.lower() == 'top'
    asyncio.run(get_oi(ticker, show_top))
