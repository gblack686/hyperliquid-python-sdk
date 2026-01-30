"""
Debug script to understand margin calculations in Hyperliquid
"""

import os
import json
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount

from hyperliquid.info import Info
from hyperliquid.utils import constants

# Load environment variables
load_dotenv()

def main():
    # Get configuration
    secret_key = os.getenv('HYPERLIQUID_API_KEY')
    account_address = os.getenv('ACCOUNT_ADDRESS')
    
    # Create account from private key
    account: LocalAccount = eth_account.Account.from_key(secret_key)
    
    # Initialize Info client
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    
    # Get user state
    user_state = info.user_state(account_address)
    
    # Print the entire user state to understand structure
    print("=" * 80)
    print("FULL USER STATE:")
    print("=" * 80)
    print(json.dumps(user_state, indent=2))
    
    # Extract margin information
    print("\n" + "=" * 80)
    print("MARGIN SUMMARY:")
    print("=" * 80)
    margin_summary = user_state.get("marginSummary", {})
    print(json.dumps(margin_summary, indent=2))
    
    # Extract cross margin summary
    print("\n" + "=" * 80)
    print("CROSS MARGIN SUMMARY:")
    print("=" * 80)
    cross_margin = user_state.get("crossMarginSummary", {})
    print(json.dumps(cross_margin, indent=2))
    
    # Extract position details
    print("\n" + "=" * 80)
    print("POSITIONS WITH LEVERAGE:")
    print("=" * 80)
    positions = user_state.get("assetPositions", [])
    for pos in positions:
        position = pos.get("position", {})
        if float(position.get("szi", 0)) != 0:
            print(f"\nCoin: {position.get('coin')}")
            print(f"Position: {json.dumps(position, indent=2)}")
            
            # Check leverage field
            leverage = position.get("leverage", {})
            print(f"Leverage info: {json.dumps(leverage, indent=2)}")
    
    # Calculate actual margin and leverage
    print("\n" + "=" * 80)
    print("CALCULATED VALUES:")
    print("=" * 80)
    
    account_value = float(margin_summary.get("accountValue", 0))
    total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
    total_ntl_pos = float(margin_summary.get("totalNtlPos", 0))
    
    print(f"Account Value: ${account_value:,.2f}")
    print(f"Total Margin Used: ${total_margin_used:,.2f}")
    print(f"Total Notional Position: ${total_ntl_pos:,.2f}")
    
    # Calculate leverage
    if account_value > 0:
        leverage = total_ntl_pos / account_value
        print(f"Calculated Leverage: {leverage:.2f}x")
        
        # Calculate margin ratio
        margin_ratio = (total_margin_used / account_value) * 100
        print(f"Margin Usage Ratio: {margin_ratio:.2f}%")
        
        # Calculate free margin
        free_margin = account_value - total_margin_used
        print(f"Free Margin: ${free_margin:,.2f}")
        
        # Calculate margin level
        if total_margin_used > 0:
            margin_level = (account_value / total_margin_used) * 100
            print(f"Margin Level: {margin_level:.2f}%")
    
    # Check metadata for asset info
    print("\n" + "=" * 80)
    print("CHECKING ASSET METADATA:")
    print("=" * 80)
    meta = info.meta()
    universe = meta.get("universe", [])
    
    # Find HYPE asset info
    for asset in universe:
        if asset.get("name") == "HYPE":
            print(f"HYPE Asset Info:")
            print(json.dumps(asset, indent=2))
            break

if __name__ == "__main__":
    main()