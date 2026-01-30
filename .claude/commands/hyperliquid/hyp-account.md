---
name: hyp-account
description: Fetch Hyperliquid mainnet account details - balance, positions, open orders
argument-hint: none
---

## Fetch Hyperliquid Account Details

Run the following Python script to get account information from Hyperliquid mainnet.

```python
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_account_details():
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    print("=" * 60)
    print("HYPERLIQUID ACCOUNT SUMMARY")
    print("=" * 60)
    print(f"Account: {hyp.account_address}")
    print()

    # Balance
    bal = await hyp.account_balance()
    print("BALANCE:")
    print(f"  Equity:       ${float(bal['equity_total']):,.2f}")
    print(f"  Withdrawable: ${float(bal['equity_withdrawable']):,.2f}")
    print(f"  Margin Used:  ${float(bal['margin_total']):,.2f}")
    print(f"  Maintenance:  ${float(bal['margin_maintenance']):,.2f}")
    print(f"  Notional Pos: ${float(bal['notional_position']):,.2f}")
    print()

    # Positions
    positions = await hyp.positions_get()
    print("OPEN POSITIONS:")
    if positions and len(positions.positions) > 0:
        for pos in positions.positions:
            side = "LONG" if pos.amount > 0 else "SHORT"
            print(f"  {pos.ticker}: {side} {abs(pos.amount)} @ ${pos.entry_price:.4f} | PnL: ${pos.unrealized_pnl:.2f}")
    else:
        print("  No open positions")
    print()

    # Open Orders
    orders = await hyp.orders_get()
    print("OPEN ORDERS:")
    if orders:
        for oid, order in orders.items():
            side = "BUY" if float(order.get('amount_total', 0)) > 0 else "SELL"
            print(f"  [{oid}] {order.get('ticker')}: {side} {abs(float(order.get('amount_total', 0)))} @ ${order.get('limit_price')}")
    else:
        print("  No open orders")
    print()

    # Rate Limits
    limits = await hyp.account_rate_limits()
    print("RATE LIMITS:")
    print(f"  {limits}")
    print()

    await hyp.cleanup()
    print("=" * 60)

asyncio.run(get_account_details())
```

Execute this script using Bash and report the results to the user in a clean formatted way.
