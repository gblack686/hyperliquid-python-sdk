---
name: hyp-cancel
description: Cancel open orders on Hyperliquid
argument-hint: "[ticker] [order_id] - e.g., 'BTC' or 'all' or specific order ID"
---

## Cancel Hyperliquid Orders

Cancel open orders. Options:
- `all` - Cancel all open orders
- `<ticker>` - Cancel all orders for a specific ticker
- `<ticker> <order_id>` - Cancel a specific order

Run this Python script:

```python
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def cancel_orders(ticker=None, order_id=None):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Get current open orders
    orders = await hyp.orders_get()

    print("=" * 50)
    print("CANCEL ORDERS")
    print("=" * 50)

    if not orders:
        print("No open orders to cancel.")
        await hyp.cleanup()
        return

    print(f"Current open orders: {len(orders)}")
    for oid, order in orders.items():
        side = "BUY" if float(order.get('amount_total', 0)) > 0 else "SELL"
        print(f"  [{oid}] {order.get('ticker')}: {side} {abs(float(order.get('amount_total', 0)))} @ ${order.get('limit_price')}")
    print()

    try:
        if ticker and ticker.lower() == 'all':
            # Cancel all orders
            print("Cancelling ALL orders...")
            result = await hyp.cancel_open_orders()
            print(f"Result: {result}")

        elif ticker and order_id:
            # Cancel specific order
            print(f"Cancelling order {order_id} for {ticker.upper()}...")
            result = await hyp.cancel_order(ticker=ticker.upper(), oid=int(order_id))
            print(f"Result: {result}")

        elif ticker:
            # Cancel all orders for ticker
            print(f"Cancelling all {ticker.upper()} orders...")
            result = await hyp.cancel_open_orders(ticker=ticker.upper())
            print(f"Result: {result}")

        else:
            print("Specify 'all', a ticker, or ticker + order_id")

        print("\nDone!")

    except Exception as e:
        print(f"CANCEL FAILED: {e}")

    print("=" * 50)
    await hyp.cleanup()

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else None
    order_id = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(cancel_orders(ticker, order_id))
```

Execute with:
- `python scripts/hyp_cancel.py all` - Cancel all orders
- `python scripts/hyp_cancel.py BTC` - Cancel all BTC orders
- `python scripts/hyp_cancel.py BTC 12345` - Cancel specific order
