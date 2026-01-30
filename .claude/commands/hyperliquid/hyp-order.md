---
name: hyp-order
description: Place a limit or market order on Hyperliquid
argument-hint: "<ticker> <side> <amount> [price] - e.g., BTC long 0.001 95000"
---

## Place Hyperliquid Order

Place a limit or market order. If price is omitted, places a market order.

**Arguments:**
- `ticker` - The asset (BTC, ETH, SOL, etc.)
- `side` - "long" or "short" (or "buy"/"sell")
- `amount` - Size in base asset
- `price` (optional) - Limit price. If omitted, market order.

**Examples:**
- `BTC long 0.001 95000` - Limit buy 0.001 BTC at $95,000
- `ETH short 0.1` - Market sell 0.1 ETH
- `SOL long 10 150` - Limit buy 10 SOL at $150

Run this Python script:

```python
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def place_order(ticker, side, amount, price=None):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Normalize side
    side = side.lower()
    if side in ['long', 'buy']:
        signed_amount = abs(float(amount))
    elif side in ['short', 'sell']:
        signed_amount = -abs(float(amount))
    else:
        print(f"Invalid side: {side}. Use 'long'/'buy' or 'short'/'sell'")
        return

    ticker = ticker.upper()

    print("=" * 50)
    print("PLACING ORDER")
    print("=" * 50)
    print(f"  Ticker: {ticker}")
    print(f"  Side:   {'LONG' if signed_amount > 0 else 'SHORT'}")
    print(f"  Amount: {abs(signed_amount)}")
    print(f"  Type:   {'LIMIT @ $' + str(price) if price else 'MARKET'}")
    print()

    try:
        if price:
            result = await hyp.limit_order(
                ticker=ticker,
                amount=signed_amount,
                price=float(price),
                round_price=True,
                round_size=True
            )
        else:
            result = await hyp.market_order(
                ticker=ticker,
                amount=signed_amount,
                round_size=True
            )

        print("ORDER RESULT:")
        print(f"  {result}")
        print()
        print("SUCCESS!")

    except Exception as e:
        print(f"ORDER FAILED: {e}")

    print("=" * 50)
    await hyp.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python hyp_order.py <ticker> <side> <amount> [price]")
        print("  side: long/buy or short/sell")
        print("  price: optional (market order if omitted)")
        sys.exit(1)

    ticker = sys.argv[1]
    side = sys.argv[2]
    amount = sys.argv[3]
    price = sys.argv[4] if len(sys.argv) > 4 else None

    asyncio.run(place_order(ticker, side, amount, price))
```

**CAUTION:** This places REAL orders on mainnet. Always double-check before confirming.
