#!/usr/bin/env python
"""View vault information on Hyperliquid."""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_vault_info(vault_address=None):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Use provided vault address or check if user has a vault
    if not vault_address:
        vault_address = hyp.vault_address

    print("=" * 60)
    print("VAULT INFORMATION")
    print("=" * 60)

    if not vault_address:
        print("No vault address specified or configured.")
        print()
        print("Usage: python hyp_vault.py <vault_address>")
        print()
        print("To find vaults, visit: https://app.hyperliquid.xyz/vaults")
        await hyp.cleanup()
        return

    print(f"\nVault: {vault_address}")
    print()

    try:
        # Get vault details
        endpoint = {
            "endpoint": "/info",
            "method": "POST",
            "data": {
                "type": "vaultDetails",
                "vaultAddress": vault_address
            }
        }
        vault_data = await hyp.http_client.request(**endpoint)

        if vault_data:
            # Basic info
            name = vault_data.get('name', 'N/A')
            leader = vault_data.get('leader', 'N/A')
            follower_state = vault_data.get('followerState', {})

            print(f"  Name:           {name}")
            print(f"  Leader:         {leader[:10]}...{leader[-6:]}" if len(leader) > 16 else f"  Leader:         {leader}")
            print()

            # Performance
            portfolio = vault_data.get('portfolio', {})
            if portfolio:
                pnl = float(portfolio.get('allTimePnl', 0))
                vlm = float(portfolio.get('allTimeVlm', 0))
                print("  PERFORMANCE:")
                print(f"    All-Time PnL: ${pnl:,.2f}")
                print(f"    All-Time Vol: ${vlm:,.0f}")
                print()

            # Positions
            positions = vault_data.get('positions', [])
            if positions:
                print("  POSITIONS:")
                for pos in positions[:5]:
                    coin = pos.get('coin', 'N/A')
                    size = float(pos.get('szi', 0))
                    entry = float(pos.get('entryPx', 0))
                    print(f"    {coin}: {size:+.4f} @ ${entry:,.2f}")
            else:
                print("  No open positions")

        else:
            print("  Vault not found or no data available.")

    except Exception as e:
        print(f"  Error fetching vault data: {e}")

    print("=" * 60)
    await hyp.cleanup()

if __name__ == "__main__":
    vault_address = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(get_vault_info(vault_address))
