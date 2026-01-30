#!/usr/bin/env python
"""Show top gainers and losers on Hyperliquid."""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_movers(count=10):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Get all mids and contexts for 24h data
    mids = await hyp.get_all_mids()
    contexts = await hyp.perpetuals_contexts()

    print("=" * 60)
    print("TOP MOVERS (24H)")
    print("=" * 60)

    # Build price change data
    movers = []
    universe_meta, universe_ctx = contexts[0]["universe"], contexts[1]

    for meta, ctx in zip(universe_meta, universe_ctx):
        ticker = meta['name']
        try:
            mark = float(ctx.get('markPx', 0))
            prev = float(ctx.get('prevDayPx', mark))
            if prev > 0 and mark > 0:
                change_pct = ((mark - prev) / prev) * 100
                volume = float(ctx.get('dayNtlVlm', 0))
                movers.append({
                    'ticker': ticker,
                    'price': mark,
                    'change': change_pct,
                    'volume': volume
                })
        except:
            continue

    # Sort by change
    gainers = sorted(movers, key=lambda x: x['change'], reverse=True)[:count]
    losers = sorted(movers, key=lambda x: x['change'])[:count]

    print(f"\nTOP {count} GAINERS:")
    print(f"  {'Ticker':10} {'Price':>14} {'Change':>10} {'Volume':>16}")
    print("-" * 55)
    for m in gainers:
        print(f"  {m['ticker']:10} ${m['price']:>12,.4f} {m['change']:>+9.2f}% ${m['volume']:>14,.0f}")

    print(f"\nTOP {count} LOSERS:")
    print(f"  {'Ticker':10} {'Price':>14} {'Change':>10} {'Volume':>16}")
    print("-" * 55)
    for m in losers:
        print(f"  {m['ticker']:10} ${m['price']:>12,.4f} {m['change']:>+9.2f}% ${m['volume']:>14,.0f}")

    # Market summary
    total_volume = sum(m['volume'] for m in movers)
    avg_change = sum(m['change'] for m in movers) / len(movers) if movers else 0
    up_count = sum(1 for m in movers if m['change'] > 0)
    down_count = sum(1 for m in movers if m['change'] < 0)

    print(f"\nMARKET SUMMARY:")
    print(f"  Total 24h Volume: ${total_volume:,.0f}")
    print(f"  Average Change:   {avg_change:+.2f}%")
    print(f"  Gainers/Losers:   {up_count}/{down_count}")

    print("=" * 60)
    await hyp.cleanup()

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    asyncio.run(get_movers(count))
