#!/usr/bin/env python
"""
Cancel Hyperliquid orders with confirmation.

DATA INTEGRITY: Uses real API data only.
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants


async def cancel_orders(ticker=None, order_id=None, skip_confirm=False):
    """Cancel orders with confirmation."""

    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Use raw SDK for accurate order display
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    open_orders = info.open_orders(hyp.account_address)

    print("=" * 60)
    print("CANCEL ORDERS")
    print("=" * 60)

    if not open_orders:
        print("No open orders to cancel.")
        await hyp.cleanup()
        return

    print(f"\nCurrent open orders: {len(open_orders)}")
    print()
    print(f"  {'OID':>15}  {'Ticker':8}  {'Side':6}  {'Size':>12}  {'Price':>14}")
    print("-" * 60)

    for order in open_orders:
        oid = order.get('oid', 'N/A')
        coin = order.get('coin', 'N/A')
        side = "BUY" if order.get('side') == 'B' else "SELL"
        sz = float(order.get('sz', 0))
        limit_px = float(order.get('limitPx', 0))

        print(f"  {oid:>15}  {coin:8}  {side:6}  {sz:>12.6f}  ${limit_px:>12,.2f}")

    print()

    try:
        if ticker and ticker.lower() == 'all':
            # Cancel all orders
            if not skip_confirm:
                confirm = input(f"Cancel ALL {len(open_orders)} orders? (yes/no): ").strip().lower()
                if confirm not in ['yes', 'y']:
                    print("\n[CANCELLED] No orders cancelled.")
                    await hyp.cleanup()
                    return

            print("Cancelling ALL orders...")
            result = await hyp.cancel_open_orders()

        elif ticker and order_id:
            # Cancel specific order
            ticker = ticker.upper()
            oid = int(order_id)

            # Verify order exists
            matching = [o for o in open_orders if o.get('oid') == oid and o.get('coin') == ticker]
            if not matching:
                print(f"[ERROR] Order {oid} for {ticker} not found")
                await hyp.cleanup()
                return

            if not skip_confirm:
                confirm = input(f"Cancel order {oid}? (yes/no): ").strip().lower()
                if confirm not in ['yes', 'y']:
                    print("\n[CANCELLED] Order not cancelled.")
                    await hyp.cleanup()
                    return

            print(f"Cancelling order {oid} for {ticker}...")
            result = await hyp.cancel_order(ticker=ticker, oid=oid)

        elif ticker:
            # Cancel all orders for ticker
            ticker = ticker.upper()
            ticker_orders = [o for o in open_orders if o.get('coin') == ticker]

            if not ticker_orders:
                print(f"No open orders for {ticker}")
                await hyp.cleanup()
                return

            if not skip_confirm:
                confirm = input(f"Cancel all {len(ticker_orders)} {ticker} orders? (yes/no): ").strip().lower()
                if confirm not in ['yes', 'y']:
                    print("\n[CANCELLED] No orders cancelled.")
                    await hyp.cleanup()
                    return

            print(f"Cancelling all {ticker} orders...")
            result = await hyp.cancel_open_orders(ticker=ticker)

        else:
            print("Usage: python hyp_cancel.py <all|ticker> [order_id]")
            await hyp.cleanup()
            return

        # Parse result
        status = result.get('status', 'unknown')
        if status == 'ok':
            response = result.get('response', {})
            data = response.get('data', {})
            statuses = data.get('statuses', [])

            success_count = sum(1 for s in statuses if s == 'success')
            print(f"\n[SUCCESS] Cancelled {success_count} order(s)")
        else:
            print(f"\n[ERROR] Cancel failed: {result}")

    except Exception as e:
        print(f"\n[ERROR] Cancel failed: {e}")

    print("=" * 60)
    await hyp.cleanup()


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else None
    order_id = None
    skip_confirm = False

    for arg in sys.argv[2:]:
        if arg == '--yes' or arg == '-y':
            skip_confirm = True
        elif arg.isdigit():
            order_id = arg

    if not ticker:
        print("=" * 60)
        print("CANCEL ORDERS")
        print("=" * 60)
        print()
        print("Usage: python hyp_cancel.py <all|ticker> [order_id] [--yes]")
        print()
        print("Arguments:")
        print("  all       - Cancel all open orders")
        print("  ticker    - Cancel all orders for specific ticker")
        print("  order_id  - Cancel specific order (requires ticker)")
        print("  --yes     - Skip confirmation prompt")
        print()
        print("Examples:")
        print("  python hyp_cancel.py all              # Cancel all orders")
        print("  python hyp_cancel.py BTC              # Cancel all BTC orders")
        print("  python hyp_cancel.py BTC 12345 --yes  # Cancel specific order")
        print()
    else:
        asyncio.run(cancel_orders(ticker, order_id, skip_confirm))
