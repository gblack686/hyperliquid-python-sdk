#!/usr/bin/env python
"""Transfer funds between spot and perp on Hyperliquid."""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid, sign_l1_action

async def transfer_funds(direction, amount):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    print("=" * 50)
    print("TRANSFER FUNDS")
    print("=" * 50)

    # Validate direction
    direction = direction.lower()
    if direction not in ['to-spot', 'to-perp', 'tospot', 'toperp']:
        print("Invalid direction. Use 'to-spot' or 'to-perp'")
        await hyp.cleanup()
        return

    to_perp = 'perp' in direction
    amount = float(amount)

    print(f"  Direction: {'Spot -> Perp' if to_perp else 'Perp -> Spot'}")
    print(f"  Amount:    ${amount:,.2f} USDC")
    print()

    try:
        # Build the transfer action
        action = {
            "type": "spotUser",
            "classTransfer": {
                "usdc": amount,
                "toPerp": to_perp
            }
        }

        nonce = hyp.get_nonce()

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

        print(f"Result: {result}")
        print()
        print("SUCCESS!")

    except Exception as e:
        print(f"TRANSFER FAILED: {e}")

    print("=" * 50)
    await hyp.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python hyp_transfer.py <direction> <amount>")
        print("  direction: 'to-spot' or 'to-perp'")
        print("  amount: USDC amount to transfer")
        sys.exit(1)

    direction = sys.argv[1]
    amount = sys.argv[2]

    asyncio.run(transfer_funds(direction, amount))
