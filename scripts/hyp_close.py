#!/usr/bin/env python
"""Close a position on Hyperliquid."""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def close_position(ticker, percent=100):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    ticker = ticker.upper()

    # Get current position
    account_data = await hyp.perpetuals_account()
    positions = account_data.get('assetPositions', [])

    position = None
    for pos_data in positions:
        pos = pos_data.get('position', {})
        if pos.get('coin', '').upper() == ticker:
            size = float(pos.get('szi', 0))
            if size != 0:
                position = pos
                break

    print("=" * 50)
    print("CLOSE POSITION")
    print("=" * 50)

    if not position:
        print(f"No open position found for {ticker}")
        await hyp.cleanup()
        return

    size = float(position.get('szi', 0))
    entry = float(position.get('entryPx', 0))
    upnl = float(position.get('unrealizedPnl', 0))

    side = 'LONG' if size > 0 else 'SHORT'
    close_size = abs(size) * (percent / 100)
    close_amount = -size * (percent / 100)  # Opposite direction

    print(f"  Current Position: {ticker} {side} {abs(size)}")
    print(f"  Entry Price:      ${entry:,.2f}")
    print(f"  Unrealized PnL:   ${upnl:,.2f}")
    print(f"  Closing:          {percent}% ({close_size:.6f})")
    print()

    try:
        result = await hyp.market_order(
            ticker=ticker,
            amount=close_amount,
            reduce_only=True,
            round_size=True
        )

        print("CLOSE ORDER RESULT:")
        print(f"  {result}")
        print()
        print("SUCCESS!")

    except Exception as e:
        print(f"CLOSE FAILED: {e}")

    print("=" * 50)
    await hyp.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hyp_close.py <ticker> [percent]")
        print("  percent: 1-100 (default 100)")
        sys.exit(1)

    ticker = sys.argv[1]
    percent = float(sys.argv[2]) if len(sys.argv) > 2 else 100

    asyncio.run(close_position(ticker, percent))
