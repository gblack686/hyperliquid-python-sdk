"""
Test account info fetching from Hyperliquid
"""

import os
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants
import eth_account
import json

load_dotenv()

def test_account_info():
    secret_key = os.getenv('HYPERLIQUID_API_KEY')
    account_address = os.getenv('ACCOUNT_ADDRESS')
    
    if not account_address and secret_key:
        # Derive address from private key
        account = eth_account.Account.from_key(secret_key)
        account_address = account.address
        print(f"Derived account address: {account_address}")
    
    if not account_address:
        print("No account address available")
        return
    
    print(f"Testing account: {account_address}")
    print("=" * 60)
    
    # Initialize Info client
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    
    # Get user state
    print("1. User State:")
    user_state = info.user_state(account_address)
    margin_summary = user_state.get("marginSummary", {})
    
    print(f"   Account Value: ${float(margin_summary.get('accountValue', 0)):,.2f}")
    print(f"   Total Margin Used: ${float(margin_summary.get('totalMarginUsed', 0)):,.2f}")
    print(f"   Total Notional: ${float(margin_summary.get('totalNtlPos', 0)):,.2f}")
    print(f"   Withdrawable: ${float(user_state.get('withdrawable', 0)):,.2f}")
    
    # Get positions
    print("\n2. Positions:")
    positions = user_state.get("assetPositions", [])
    if positions:
        for pos in positions:
            position = pos.get("position", {})
            coin = position.get("coin", "Unknown")
            szi = float(position.get("szi", 0))
            if szi != 0:
                entry_px = float(position.get("entryPx", 0))
                mark_px = float(position.get("markPx", 0))
                unrealized_pnl = float(position.get("unrealizedPnl", 0))
                print(f"   {coin}: {'LONG' if szi > 0 else 'SHORT'} {abs(szi)} @ ${entry_px:,.2f}")
                print(f"      Mark: ${mark_px:,.2f}, Unrealized PnL: ${unrealized_pnl:,.2f}")
    else:
        print("   No open positions")
    
    # Get fills
    print("\n3. Recent Trades (last 5):")
    fills = info.user_fills(account_address)
    if fills:
        for fill in fills[:5]:
            dt = datetime.fromtimestamp(int(fill.get("time", 0)) / 1000)
            coin = fill.get("coin", "")
            side = fill.get("side", "")
            sz = float(fill.get("sz", 0))
            px = float(fill.get("px", 0))
            fee = float(fill.get("fee", 0))
            print(f"   {dt.strftime('%Y-%m-%d %H:%M')} - {coin} {side} {sz} @ ${px:,.2f} (fee: ${fee:,.4f})")
    else:
        print("   No recent trades")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")

if __name__ == "__main__":
    from datetime import datetime
    test_account_info()