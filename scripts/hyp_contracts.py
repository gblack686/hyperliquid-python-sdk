#!/usr/bin/env python
"""List all available Hyperliquid contracts."""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def list_contracts(search=None):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Get perpetual and spot metadata
    perp_specs = await hyp.contract_specifications(is_perpetuals=True)
    spot_specs = await hyp.contract_specifications(is_perpetuals=False)

    print("=" * 70)
    print("HYPERLIQUID CONTRACTS")
    print("=" * 70)

    # Filter if search term provided
    if search:
        search = search.upper()
        perp_specs = {k: v for k, v in perp_specs.items() if search in k.upper()}
        spot_specs = {k: v for k, v in spot_specs.items() if search in k.upper()}

    print(f"\nPERPETUAL CONTRACTS ({len(perp_specs)}):")
    print(f"  {'Ticker':12} {'Price Prec':>10} {'Size Prec':>10} {'Min Notional':>12}")
    print("-" * 50)

    for ticker in sorted(perp_specs.keys()):
        spec = perp_specs[ticker]
        print(f"  {ticker:12} {spec['price_precision']:>10} {spec['quantity_precision']:>10} ${float(spec['min_notional']):>10,.0f}")

    if len(perp_specs) > 20 and not search:
        print(f"  ... and {len(perp_specs) - 20} more (use search to filter)")

    print(f"\nSPOT CONTRACTS ({len(spot_specs)}):")
    print(f"  {'Ticker':12} {'Price Prec':>10} {'Size Prec':>10} {'Min Notional':>12}")
    print("-" * 50)

    spot_count = 0
    for ticker in sorted(spot_specs.keys()):
        spec = spot_specs[ticker]
        print(f"  {ticker:12} {spec['price_precision']:>10} {spec['quantity_precision']:>10} ${float(spec['min_notional']):>10,.0f}")
        spot_count += 1
        if spot_count >= 20 and not search:
            print(f"  ... and {len(spot_specs) - 20} more (use search to filter)")
            break

    print()
    print(f"Total: {len(perp_specs)} perps, {len(spot_specs)} spot")
    print("=" * 70)
    await hyp.cleanup()

if __name__ == "__main__":
    search = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(list_contracts(search))
