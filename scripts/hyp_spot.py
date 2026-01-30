#!/usr/bin/env python
"""View spot token balances on Hyperliquid."""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_spot_balances():
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Get spot balances
    endpoint = hyp._add_to_request('spot_balances', data={'user': hyp.account_address})
    spot_data = await hyp.http_client.request(**endpoint)

    print("=" * 60)
    print("SPOT BALANCES")
    print("=" * 60)

    balances = spot_data.get('balances', [])

    if not balances:
        print("No spot holdings found.")
        await hyp.cleanup()
        return

    # Get current prices for valuation
    mids = await hyp.get_all_mids()

    print(f"\n  {'Token':12} {'Balance':>16} {'Value (USD)':>14}")
    print("-" * 50)

    total_value = 0

    for bal in balances:
        token = bal.get('coin', 'UNKNOWN')
        total = float(bal.get('total', 0))
        hold = float(bal.get('hold', 0))
        available = total - hold

        if total == 0:
            continue

        # Try to get USD value
        value = 0
        if token == 'USDC':
            value = total
        else:
            # Try to find price (token might be listed as TOKEN or @N)
            for ticker, price in mids.items():
                if token in ticker or ticker.startswith('@'):
                    try:
                        canonical = hyp.get_canonical_name(ticker, return_unmapped=True)
                        if token in canonical:
                            value = total * float(price)
                            break
                    except:
                        pass

        total_value += value

        value_str = f"${value:,.2f}" if value > 0 else "N/A"
        hold_str = f" (hold: {hold:.4f})" if hold > 0 else ""
        print(f"  {token:12} {total:>16.6f} {value_str:>14}{hold_str}")

    print("-" * 50)
    print(f"  {'TOTAL':12} {' ':>16} ${total_value:>13,.2f}")
    print("=" * 60)
    await hyp.cleanup()

if __name__ == "__main__":
    asyncio.run(get_spot_balances())
