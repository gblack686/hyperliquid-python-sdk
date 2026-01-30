#!/usr/bin/env python
"""
Scaled Entry - Layer into a position at multiple price levels.

HOW IT WORKS:
- Divides total size into N layers
- Places limit orders at progressively better prices
- Can use linear or exponential spacing

USAGE:
  python hyp_scaled_entry.py <ticker> <side> <total_size> <start_price> <end_price> [layers] [--execute]

EXAMPLES:
  python hyp_scaled_entry.py BTC long 0.01 80000 75000 5        # Preview 5 layers
  python hyp_scaled_entry.py ETH short 0.1 2600 2800 4 --execute  # Execute 4 layers
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants


async def scaled_entry(ticker, side, total_size, start_price, end_price, layers=5, execute=False):
    """Create scaled entry orders."""

    ticker = ticker.upper()
    side = side.lower()
    total_size = float(total_size)
    start_price = float(start_price)
    end_price = float(end_price)
    layers = int(layers)

    # Validate side
    if side not in ['long', 'buy', 'short', 'sell']:
        print(f"[ERROR] Invalid side: {side}")
        return

    is_long = side in ['long', 'buy']

    # Connect
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    print("=" * 70)
    print("SCALED ENTRY")
    print("=" * 70)

    # Get current price
    mids = info.all_mids()
    current_price = float(mids.get(ticker, 0))

    if current_price == 0:
        print(f"[ERROR] Could not get price for {ticker}")
        await hyp.cleanup()
        return

    print(f"  Ticker:        {ticker}")
    print(f"  Side:          {'LONG' if is_long else 'SHORT'}")
    print(f"  Total Size:    {total_size}")
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  Price Range:   ${start_price:,.2f} -> ${end_price:,.2f}")
    print(f"  Layers:        {layers}")
    print()

    # Validate price direction
    if is_long:
        # For longs, we want to buy at lower prices
        if start_price > current_price * 1.05:
            print(f"[WARN] Start price ${start_price:,.2f} is above market for a long")
    else:
        # For shorts, we want to sell at higher prices
        if start_price < current_price * 0.95:
            print(f"[WARN] Start price ${start_price:,.2f} is below market for a short")

    # Calculate layer prices and sizes
    price_step = (end_price - start_price) / (layers - 1) if layers > 1 else 0
    size_per_layer = total_size / layers

    orders = []
    for i in range(layers):
        price = start_price + (price_step * i)
        size = size_per_layer

        # Adjust size for contract minimums
        orders.append({
            'layer': i + 1,
            'price': price,
            'size': size,
            'side': 'long' if is_long else 'short',
            'notional': price * size
        })

    # Display order plan
    print("ORDER PLAN:")
    print("-" * 70)
    print(f"  {'Layer':>5}  {'Price':>14}  {'Size':>12}  {'Notional':>14}  {'From Market':>12}")
    print("-" * 70)

    total_notional = 0
    avg_price = 0
    for order in orders:
        pct_from_market = (order['price'] - current_price) / current_price * 100
        print(f"  {order['layer']:>5}  ${order['price']:>12,.2f}  {order['size']:>12.6f}  "
              f"${order['notional']:>12,.2f}  {pct_from_market:>+11.2f}%")
        total_notional += order['notional']
        avg_price += order['price'] * order['size']

    avg_price = avg_price / total_size
    print("-" * 70)
    print(f"  {'TOTAL':>5}  ${avg_price:>12,.2f}  {total_size:>12.6f}  ${total_notional:>12,.2f}")
    print()

    # Check balance
    balance = await hyp.account_balance()
    equity = float(balance['equity_total'])
    withdrawable = float(balance['equity_withdrawable'])
    est_margin = total_notional * 0.1  # ~10x leverage

    print(f"  Account Equity:   ${equity:,.2f}")
    print(f"  Est. Margin Req:  ${est_margin:,.2f}")

    if est_margin > withdrawable:
        print(f"  [WARN] May not have enough margin!")
    print()

    if not execute:
        print("[PREVIEW MODE] Add --execute to place orders")
        await hyp.cleanup()
        return

    # Execute orders
    print("EXECUTING ORDERS...")
    print("-" * 70)

    successful = 0
    failed = 0

    for order in orders:
        signed_amount = order['size'] if is_long else -order['size']

        try:
            result = await hyp.limit_order(
                ticker=ticker,
                amount=signed_amount,
                price=order['price'],
                round_price=True,
                round_size=True
            )

            if result.get('status') == 'ok':
                response = result.get('response', {})
                data = response.get('data', {})
                statuses = data.get('statuses', [])

                for s in statuses:
                    if 'resting' in s:
                        oid = s['resting']['oid']
                        print(f"  Layer {order['layer']}: [OK] Order {oid} @ ${order['price']:,.2f}")
                        successful += 1
                    elif 'filled' in s:
                        print(f"  Layer {order['layer']}: [FILLED] Immediate fill @ ${order['price']:,.2f}")
                        successful += 1
                    elif 'error' in s:
                        print(f"  Layer {order['layer']}: [ERROR] {s['error']}")
                        failed += 1
            else:
                print(f"  Layer {order['layer']}: [FAILED] {result}")
                failed += 1

        except Exception as e:
            print(f"  Layer {order['layer']}: [ERROR] {e}")
            failed += 1

        # Small delay between orders
        await asyncio.sleep(0.2)

    print("-" * 70)
    print(f"\n[COMPLETE] {successful} orders placed, {failed} failed")
    print("=" * 70)

    await hyp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    side = sys.argv[2]
    total_size = sys.argv[3]
    start_price = sys.argv[4]
    end_price = sys.argv[5]
    layers = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6].isdigit() else 5
    execute = '--execute' in sys.argv or '-x' in sys.argv

    asyncio.run(scaled_entry(ticker, side, total_size, start_price, end_price, layers, execute))
