#!/usr/bin/env python
"""View or set leverage on Hyperliquid."""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def manage_leverage(ticker, new_leverage=None, margin_type='cross'):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    ticker = ticker.upper()

    # Get current position/leverage info
    account_data = await hyp.perpetuals_account()
    positions = account_data.get('assetPositions', [])

    current_leverage = None
    current_type = None
    has_position = False

    for pos_data in positions:
        pos = pos_data.get('position', {})
        if pos.get('coin', '').upper() == ticker:
            leverage_info = pos.get('leverage', {})
            current_leverage = leverage_info.get('value', 'N/A')
            current_type = leverage_info.get('type', 'cross')
            has_position = float(pos.get('szi', 0)) != 0
            break

    print("=" * 50)
    print(f"LEVERAGE: {ticker}")
    print("=" * 50)

    if current_leverage:
        print(f"  Current Leverage: {current_leverage}x ({current_type})")
        print(f"  Has Position:     {'Yes' if has_position else 'No'}")
    else:
        print(f"  No leverage info found for {ticker}")
        print(f"  (Will use default when position opened)")

    if new_leverage:
        print()
        print(f"  Setting new leverage: {new_leverage}x ({margin_type})")

        try:
            # Use the update_leverage endpoint
            is_cross = margin_type.lower() == 'cross'

            action = {
                "type": "updateLeverage",
                "asset": hyp.ticker_to_idx.get(ticker, 0),
                "isCross": is_cross,
                "leverage": int(new_leverage)
            }

            nonce = hyp.get_nonce()
            from quantpylib.wrappers.hyperliquid import sign_l1_action

            signature = sign_l1_action(
                wallet=hyp.wallet,
                action=action,
                vault=hyp.vault_address,
                nonce=nonce,
                is_mainnet=hyp.is_mainnet
            )

            payload = {
                "action": action,
                "nonce": nonce,
                "signature": signature,
                "vaultAddress": hyp.vault_address
            }

            result = await hyp.http_client.request(
                endpoint="/exchange",
                method="POST",
                data=payload
            )

            print(f"  Result: {result}")
            print()
            print("SUCCESS!")

        except Exception as e:
            print(f"  FAILED: {e}")

    print("=" * 50)
    await hyp.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hyp_leverage.py <ticker> [leverage] [cross/isolated]")
        sys.exit(1)

    ticker = sys.argv[1]
    leverage = int(sys.argv[2]) if len(sys.argv) > 2 else None
    margin_type = sys.argv[3] if len(sys.argv) > 3 else 'cross'

    asyncio.run(manage_leverage(ticker, leverage, margin_type))
