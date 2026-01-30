#!/usr/bin/env python
"""
Place Hyperliquid orders with safety confirmations.

DATA INTEGRITY: Uses real API data only - no fabrication.
SAFETY: Includes balance checks, price validation, and confirmation prompts.
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants


async def place_order(ticker, side, amount, price=None, skip_confirm=False):
    """Place an order with safety checks and confirmation."""

    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Also use raw SDK for validation
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    # Normalize inputs
    ticker = ticker.upper()
    side = side.lower()

    if side in ['long', 'buy', 'b']:
        signed_amount = abs(float(amount))
        side_str = 'LONG/BUY'
    elif side in ['short', 'sell', 's']:
        signed_amount = -abs(float(amount))
        side_str = 'SHORT/SELL'
    else:
        print(f"[ERROR] Invalid side: {side}")
        print("  Valid options: long, buy, b, short, sell, s")
        await hyp.cleanup()
        return False

    print("=" * 60)
    print("ORDER VALIDATION")
    print("=" * 60)

    # 1. Validate ticker exists
    meta = info.meta()
    universe = meta.get('universe', [])
    valid_tickers = [u['name'] for u in universe]

    if ticker not in valid_tickers:
        print(f"[ERROR] Ticker '{ticker}' not found on Hyperliquid")
        print(f"  Similar: {[t for t in valid_tickers if ticker[:2] in t][:5]}")
        await hyp.cleanup()
        return False
    print(f"  [OK] Ticker '{ticker}' exists")

    # 2. Get current price
    mids = info.all_mids()
    current_price = float(mids.get(ticker, 0))
    if current_price == 0:
        print(f"[ERROR] Could not get price for {ticker}")
        await hyp.cleanup()
        return False
    print(f"  [OK] Current price: ${current_price:,.4f}")

    # 3. Validate order price
    order_type = 'MARKET'
    if price:
        price = float(price)
        order_type = 'LIMIT'
        price_diff_pct = abs(price - current_price) / current_price * 100

        if price_diff_pct > 50:
            print(f"  [WARN] Limit price ${price:,.2f} is {price_diff_pct:.1f}% from market!")

        # Check if limit order would fill immediately
        if signed_amount > 0 and price >= current_price:
            print(f"  [INFO] Buy limit at/above market - may fill immediately")
        elif signed_amount < 0 and price <= current_price:
            print(f"  [INFO] Sell limit at/below market - may fill immediately")
    print(f"  [OK] Order type: {order_type}")

    # 4. Check account balance
    balance = await hyp.account_balance()
    equity = float(balance['equity_total'])
    withdrawable = float(balance['equity_withdrawable'])

    # Estimate margin required (rough: 10% of notional at max leverage)
    notional = abs(float(amount)) * (price if price else current_price)
    est_margin = notional * 0.1  # Assuming 10x leverage

    print(f"  [OK] Account equity: ${equity:,.2f}")
    print(f"  [OK] Estimated notional: ${notional:,.2f}")

    if est_margin > withdrawable:
        print(f"  [WARN] May need ${est_margin:,.2f} margin, only ${withdrawable:,.2f} available")

    # 5. Summary and confirmation
    print()
    print("=" * 60)
    print("ORDER SUMMARY")
    print("=" * 60)
    print(f"  Ticker:     {ticker}")
    print(f"  Side:       {side_str}")
    print(f"  Amount:     {abs(float(amount))}")
    print(f"  Type:       {order_type}")
    if price:
        print(f"  Limit:      ${price:,.2f}")
    print(f"  Market:     ${current_price:,.4f}")
    print(f"  Notional:   ~${notional:,.2f}")
    print()

    if not skip_confirm:
        confirm = input("Confirm order? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("\n[CANCELLED] Order not placed.")
            await hyp.cleanup()
            return False

    # 6. Execute order
    print()
    print("Placing order...")

    try:
        if price:
            result = await hyp.limit_order(
                ticker=ticker,
                amount=signed_amount,
                price=price,
                round_price=True,
                round_size=True
            )
        else:
            result = await hyp.market_order(
                ticker=ticker,
                amount=signed_amount,
                round_size=True
            )

        print()
        print("=" * 60)
        print("ORDER RESULT")
        print("=" * 60)

        # Parse result
        status = result.get('status', 'unknown')
        if status == 'ok':
            response = result.get('response', {})
            data = response.get('data', {})
            statuses = data.get('statuses', [])

            for s in statuses:
                if 'resting' in s:
                    oid = s['resting']['oid']
                    print(f"  [SUCCESS] Limit order placed")
                    print(f"  Order ID: {oid}")
                elif 'filled' in s:
                    filled = s['filled']
                    print(f"  [SUCCESS] Order filled!")
                    print(f"  Total Size: {filled.get('totalSz', 'N/A')}")
                    print(f"  Avg Price: ${float(filled.get('avgPx', 0)):,.2f}")
                elif 'error' in s:
                    print(f"  [ERROR] {s['error']}")
                else:
                    print(f"  Status: {s}")
        else:
            print(f"  [ERROR] Order failed: {result}")

        print("=" * 60)
        await hyp.cleanup()
        return status == 'ok'

    except Exception as e:
        print(f"\n[ERROR] Order failed: {e}")
        await hyp.cleanup()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("=" * 60)
        print("HYPERLIQUID ORDER")
        print("=" * 60)
        print()
        print("Usage: python hyp_order.py <ticker> <side> <amount> [price] [--yes]")
        print()
        print("Arguments:")
        print("  ticker  - Asset symbol (e.g., BTC, ETH, SOL)")
        print("  side    - long/buy or short/sell")
        print("  amount  - Order size in contracts")
        print("  price   - Limit price (optional, market if omitted)")
        print("  --yes   - Skip confirmation prompt")
        print()
        print("Examples:")
        print("  python hyp_order.py BTC long 0.001          # Market buy")
        print("  python hyp_order.py ETH short 0.01 2500     # Limit sell @ $2500")
        print("  python hyp_order.py SOL buy 1 100 --yes     # Limit buy, no confirm")
        print()
        sys.exit(1)

    ticker = sys.argv[1]
    side = sys.argv[2]
    amount = sys.argv[3]
    price = None
    skip_confirm = False

    # Parse optional args
    for arg in sys.argv[4:]:
        if arg == '--yes' or arg == '-y':
            skip_confirm = True
        else:
            try:
                price = float(arg)
            except ValueError:
                pass

    asyncio.run(place_order(ticker, side, amount, price, skip_confirm))
