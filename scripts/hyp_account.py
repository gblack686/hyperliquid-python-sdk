#!/usr/bin/env python
"""Fetch Hyperliquid mainnet account details - uses real API data only."""
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def get_account_details():
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Also use raw SDK for accurate order display
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

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

    # Positions - use raw SDK for accurate data
    user_state = info.user_state(hyp.account_address)
    positions = user_state.get('assetPositions', [])

    print("OPEN POSITIONS:")
    has_positions = False
    for pos_data in positions:
        pos = pos_data.get('position', {})
        size = float(pos.get('szi', 0))
        if size != 0:
            has_positions = True
            coin = pos.get('coin', 'N/A')
            side = "LONG" if size > 0 else "SHORT"
            entry = float(pos.get('entryPx', 0))
            upnl = float(pos.get('unrealizedPnl', 0))
            print(f"  {coin}: {side} {abs(size)} @ ${entry:,.2f} | PnL: ${upnl:,.2f}")

    if not has_positions:
        print("  No open positions")
    print()

    # Open Orders - use raw SDK for accurate display
    open_orders = info.open_orders(hyp.account_address)

    print("OPEN ORDERS:")
    if open_orders:
        for order in open_orders:
            oid = order.get('oid', 'N/A')
            coin = order.get('coin', 'N/A')
            side = order.get('side', 'N/A')
            sz = float(order.get('sz', 0))
            limit_px = float(order.get('limitPx', 0))
            order_type = order.get('orderType', 'Limit')

            side_str = "BUY" if side == 'B' else "SELL"
            print(f"  [{oid}] {coin}: {side_str} {sz} @ ${limit_px:,.2f} ({order_type})")
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

if __name__ == "__main__":
    asyncio.run(get_account_details())
