#!/usr/bin/env python
"""Get detailed contract info for a Hyperliquid ticker."""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_info(ticker):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    ticker = ticker.upper()

    print("=" * 60)
    print(f"CONTRACT INFO: {ticker}")
    print("=" * 60)

    # Check if perp or spot
    is_perp = ticker in hyp.ticker_to_idx and hyp.ticker_to_idx[ticker] < 10000

    if is_perp:
        # Get perp-specific data
        contexts = await hyp.perpetuals_contexts()
        universe_meta, universe_ctx = contexts[0]["universe"], contexts[1]

        contract_meta = None
        contract_ctx = None

        for meta, ctx in zip(universe_meta, universe_ctx):
            if meta['name'].upper() == ticker:
                contract_meta = meta
                contract_ctx = ctx
                break

        if not contract_meta:
            print(f"Contract {ticker} not found.")
            await hyp.cleanup()
            return

        # Contract specifications
        print("\nSPECIFICATIONS:")
        print(f"  Asset Index:      {hyp.ticker_to_idx.get(ticker, 'N/A')}")
        print(f"  Price Precision:  {hyp.ticker_to_price_precision.get(ticker, 'N/A')} decimals")
        print(f"  Size Precision:   {hyp.ticker_to_lot_precision.get(ticker, 'N/A')} decimals")
        print(f"  Min Notional:     $10.00")
        print(f"  Max Leverage:     {contract_meta.get('maxLeverage', 'N/A')}x")

        # Current market data
        print("\nMARKET DATA:")
        mark = float(contract_ctx.get('markPx', 0))
        oracle = float(contract_ctx.get('oraclePx', 0))
        funding = float(contract_ctx.get('funding', 0))
        oi = float(contract_ctx.get('openInterest', 0))
        volume = float(contract_ctx.get('dayNtlVlm', 0))
        prev = float(contract_ctx.get('prevDayPx', mark))
        change = ((mark - prev) / prev * 100) if prev > 0 else 0

        print(f"  Mark Price:       ${mark:,.4f}")
        print(f"  Oracle Price:     ${oracle:,.4f}")
        print(f"  24h Change:       {change:+.2f}%")
        print(f"  Funding Rate:     {funding*100:.4f}% (hourly)")
        print(f"  Funding APR:      {funding*100*24*365:.1f}%")
        print(f"  Open Interest:    ${oi:,.0f}")
        print(f"  24h Volume:       ${volume:,.0f}")

        # Premium/discount
        if oracle > 0:
            premium = ((mark - oracle) / oracle) * 100
            print(f"  Premium/Discount: {premium:+.3f}%")

    else:
        # Spot info
        print(f"\nSPOT CONTRACT")
        print(f"  Asset Index:      {hyp.ticker_to_idx.get(ticker, 'N/A')}")
        print(f"  Price Precision:  {hyp.ticker_to_price_precision.get(ticker, 'N/A')} decimals")
        print(f"  Size Precision:   {hyp.ticker_to_lot_precision.get(ticker, 'N/A')} decimals")

        # Get current price
        try:
            mid = await hyp.get_all_mids(ticker=ticker)
            print(f"  Current Price:    ${float(mid):,.4f}")
        except:
            pass

        # Canonical name
        canonical = hyp.get_canonical_name(ticker, return_unmapped=True)
        if canonical != ticker:
            print(f"  Canonical Name:   {canonical}")

    print("=" * 60)
    await hyp.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hyp_info.py <ticker>")
        sys.exit(1)

    ticker = sys.argv[1]
    asyncio.run(get_info(ticker))
