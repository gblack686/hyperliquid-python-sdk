#!/usr/bin/env python
"""
Scaled Exit with TP/SL - Take profits at multiple levels with a stop loss.

HOW IT WORKS:
- Places multiple take-profit orders at different prices
- Sets a single stop-loss order
- Monitors until all TPs hit or SL triggers
- SL closes remaining position

USAGE:
  python hyp_scaled_exit.py <ticker> <tp1_pct> <tp2_pct> <tp3_pct> <sl_pct> [--execute]

EXAMPLES:
  python hyp_scaled_exit.py BTC 2 4 6 -3            # Preview: TP at 2%, 4%, 6%, SL at -3%
  python hyp_scaled_exit.py ETH 1.5 3 5 -2 --execute  # Execute with these levels
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants


async def scaled_exit(ticker, tp_pcts, sl_pct, execute=False, monitor=False):
    """Create scaled exit orders with TP levels and SL."""

    ticker = ticker.upper()

    # Connect
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    print("=" * 70)
    print("SCALED EXIT (TP/SL)")
    print("=" * 70)

    # Get current position
    user_state = info.user_state(hyp.account_address)
    positions = user_state.get('assetPositions', [])

    position = None
    for pos_data in positions:
        pos = pos_data.get('position', {})
        if pos.get('coin') == ticker:
            size = float(pos.get('szi', 0))
            if size != 0:
                position = {
                    'size': size,
                    'side': 'long' if size > 0 else 'short',
                    'entry_price': float(pos.get('entryPx', 0)),
                    'unrealized_pnl': float(pos.get('unrealizedPnl', 0))
                }
                break

    if not position:
        print(f"[ERROR] No open position for {ticker}")
        await hyp.cleanup()
        return

    is_long = position['side'] == 'long'
    entry = position['entry_price']
    total_size = abs(position['size'])

    print(f"  Ticker:        {ticker}")
    print(f"  Position:      {position['side'].upper()} {total_size}")
    print(f"  Entry Price:   ${entry:,.2f}")
    print(f"  Current PnL:   ${position['unrealized_pnl']:,.2f}")
    print()

    # Calculate TP and SL prices
    orders = []
    tp_count = len(tp_pcts)
    size_per_tp = total_size / tp_count

    print("EXIT PLAN:")
    print("-" * 70)
    print(f"  {'Type':>6}  {'Level':>8}  {'Price':>14}  {'Size':>12}  {'Expected PnL':>14}")
    print("-" * 70)

    # Take profit levels
    for i, tp_pct in enumerate(tp_pcts):
        if is_long:
            tp_price = entry * (1 + tp_pct / 100)
        else:
            tp_price = entry * (1 - tp_pct / 100)

        expected_pnl = size_per_tp * entry * (tp_pct / 100)

        orders.append({
            'type': 'TP',
            'level': i + 1,
            'pct': tp_pct,
            'price': tp_price,
            'size': size_per_tp,
            'expected_pnl': expected_pnl
        })

        print(f"  {'TP' + str(i+1):>6}  {tp_pct:>+7.1f}%  ${tp_price:>12,.2f}  {size_per_tp:>12.6f}  ${expected_pnl:>12,.2f}")

    # Stop loss (closes remaining position)
    if is_long:
        sl_price = entry * (1 + sl_pct / 100)  # sl_pct is negative for longs
    else:
        sl_price = entry * (1 - sl_pct / 100)  # sl_pct is negative for shorts

    expected_sl_loss = total_size * entry * (sl_pct / 100)

    orders.append({
        'type': 'SL',
        'level': 0,
        'pct': sl_pct,
        'price': sl_price,
        'size': total_size,  # SL closes full remaining
        'expected_pnl': expected_sl_loss
    })

    print(f"  {'SL':>6}  {sl_pct:>+7.1f}%  ${sl_price:>12,.2f}  {'(remaining)':>12}  ${expected_sl_loss:>12,.2f}")
    print("-" * 70)

    # Summary
    total_tp_pnl = sum(o['expected_pnl'] for o in orders if o['type'] == 'TP')
    print(f"\n  If all TPs hit: ${total_tp_pnl:,.2f} profit")
    print(f"  If SL hits:     ${expected_sl_loss:,.2f} loss")
    print()

    if not execute:
        print("[PREVIEW MODE] Add --execute to place orders")
        await hyp.cleanup()
        return

    # Execute TP orders
    print("PLACING ORDERS...")
    print("-" * 70)

    placed_orders = []

    for order in orders:
        if order['type'] == 'TP':
            # For TP, we're closing position (opposite direction)
            signed_amount = -order['size'] if is_long else order['size']

            try:
                result = await hyp.limit_order(
                    ticker=ticker,
                    amount=signed_amount,
                    price=order['price'],
                    reduce_only=True,
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
                            print(f"  TP{order['level']}: [OK] Order {oid} @ ${order['price']:,.2f}")
                            placed_orders.append({'type': 'TP', 'oid': oid, 'price': order['price']})
                        elif 'error' in s:
                            print(f"  TP{order['level']}: [ERROR] {s['error']}")
                else:
                    print(f"  TP{order['level']}: [FAILED] {result}")

            except Exception as e:
                print(f"  TP{order['level']}: [ERROR] {e}")

            await asyncio.sleep(0.2)

    # Note: Hyperliquid doesn't have native SL orders, so we need to monitor
    print()
    print(f"  [INFO] TP orders placed. SL at ${sl_price:,.2f} requires monitoring.")
    print(f"         Run with --monitor to actively watch for SL trigger.")
    print()

    if monitor:
        print("MONITORING FOR STOP LOSS...")
        print("-" * 70)

        try:
            while True:
                current_price = float(info.all_mids().get(ticker, 0))

                # Check SL trigger
                sl_triggered = False
                if is_long and current_price <= sl_price:
                    sl_triggered = True
                elif not is_long and current_price >= sl_price:
                    sl_triggered = True

                if sl_triggered:
                    print(f"\n[SL TRIGGERED] Price ${current_price:,.2f} hit SL ${sl_price:,.2f}")
                    print("Closing remaining position...")

                    # Cancel remaining TP orders
                    for po in placed_orders:
                        try:
                            await hyp.cancel_order(ticker=ticker, oid=po['oid'])
                            print(f"  Cancelled TP order {po['oid']}")
                        except:
                            pass

                    # Close position
                    remaining = await get_remaining_position(info, hyp.account_address, ticker)
                    if remaining:
                        close_amount = -remaining if is_long else remaining
                        result = await hyp.market_order(
                            ticker=ticker,
                            amount=close_amount,
                            reduce_only=True,
                            round_size=True
                        )
                        print(f"  Position closed: {result}")

                    break

                now = datetime.now().strftime('%H:%M:%S')
                print(f"{now} | Price: ${current_price:,.2f} | SL: ${sl_price:,.2f} | "
                      f"{'OK' if not sl_triggered else 'TRIGGERED'}")

                await asyncio.sleep(5)

        except KeyboardInterrupt:
            print("\n\n[STOPPED] Monitor stopped. TP orders remain active.")

    print("=" * 70)
    await hyp.cleanup()


async def get_remaining_position(info, address, ticker):
    """Get remaining position size."""
    user_state = info.user_state(address)
    positions = user_state.get('assetPositions', [])

    for pos_data in positions:
        pos = pos_data.get('position', {})
        if pos.get('coin') == ticker:
            return float(pos.get('szi', 0))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    tp_pcts = []
    sl_pct = None
    execute = '--execute' in sys.argv or '-x' in sys.argv
    monitor = '--monitor' in sys.argv or '-m' in sys.argv

    # Parse TP and SL percentages
    for arg in sys.argv[2:]:
        # Skip flags (but not negative numbers)
        if arg.startswith('--'):
            continue
        if arg.startswith('-') and not arg.lstrip('-').replace('.', '').isdigit():
            continue
        try:
            pct = float(arg)
            if pct < 0:
                sl_pct = pct
            else:
                tp_pcts.append(pct)
        except ValueError:
            pass

    if not tp_pcts or sl_pct is None:
        print("[ERROR] Need at least 1 TP level (positive) and 1 SL (negative)")
        print("Example: python hyp_scaled_exit.py BTC 2 4 6 -3")
        sys.exit(1)

    asyncio.run(scaled_exit(ticker, tp_pcts, sl_pct, execute, monitor))
