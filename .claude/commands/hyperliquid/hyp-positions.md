---
name: hyp-positions
description: View detailed position information with PnL, liquidation price, leverage
argument-hint: "[ticker] - show specific position or all"
---

## Fetch Hyperliquid Positions

Get detailed position information including entry price, PnL, liquidation price, and leverage.

Run this Python script:

```python
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_positions(ticker_filter=None):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Get raw perpetuals account data for more details
    account_data = await hyp.perpetuals_account()

    print("=" * 70)
    print("HYPERLIQUID POSITIONS")
    print("=" * 70)

    # Account summary
    margin_summary = account_data.get('marginSummary', {})
    print(f"Account Value:  ${float(margin_summary.get('accountValue', 0)):,.2f}")
    print(f"Total Margin:   ${float(margin_summary.get('totalMarginUsed', 0)):,.2f}")
    print(f"Total Notional: ${float(margin_summary.get('totalNtlPos', 0)):,.2f}")
    print()

    positions = account_data.get('assetPositions', [])

    if not positions:
        print("No open positions.")
        await hyp.cleanup()
        return

    # Filter if ticker specified
    if ticker_filter:
        ticker_filter = ticker_filter.upper()
        positions = [p for p in positions if p.get('position', {}).get('coin', '').upper() == ticker_filter]

    if not positions:
        print(f"No position found for {ticker_filter}")
        await hyp.cleanup()
        return

    print(f"{'Ticker':8} {'Side':6} {'Size':>12} {'Entry':>12} {'Mark':>12} {'Liq':>12} {'uPnL':>12} {'ROE':>8}")
    print("-" * 90)

    for pos_data in positions:
        pos = pos_data.get('position', {})
        coin = pos.get('coin', 'N/A')
        size = float(pos.get('szi', 0))

        if size == 0:
            continue

        side = 'LONG' if size > 0 else 'SHORT'
        entry = float(pos.get('entryPx', 0))
        mark = float(pos.get('markPx', entry))
        liq = float(pos.get('liquidationPx', 0)) if pos.get('liquidationPx') else 0
        upnl = float(pos.get('unrealizedPnl', 0))
        margin = float(pos.get('marginUsed', 1))
        roe = (upnl / margin * 100) if margin > 0 else 0

        liq_str = f"${liq:,.2f}" if liq > 0 else "N/A"

        print(f"{coin:8} {side:6} {abs(size):>12.4f} ${entry:>10,.2f} ${mark:>10,.2f} {liq_str:>12} ${upnl:>10,.2f} {roe:>7.1f}%")

        # Additional details
        leverage = pos.get('leverage', {})
        if leverage:
            lev_type = leverage.get('type', 'cross')
            lev_val = leverage.get('value', 'N/A')
            print(f"         Leverage: {lev_val}x ({lev_type}) | Margin: ${margin:,.2f}")

    print("=" * 70)
    await hyp.cleanup()

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(get_positions(ticker))
```

Execute with: `python scripts/hyp_positions.py [TICKER]`
