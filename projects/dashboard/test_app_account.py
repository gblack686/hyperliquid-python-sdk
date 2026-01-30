"""Test account data fetching in app"""
from app import fetch_account_data_cached
import os
from dotenv import load_dotenv

load_dotenv()

# Test the cached function
result = fetch_account_data_cached()

if result['success']:
    user_state = result['user_state']
    margin_summary = user_state.get('marginSummary', {})
    account_value = float(margin_summary.get('accountValue', 0))
    withdrawable = float(user_state.get('withdrawable', 0))
    
    print(f'Account Value: ${account_value:,.2f}')
    print(f'Withdrawable: ${withdrawable:,.2f}')
    print(f'Account Address: {result["account_address"]}')
    
    # Check positions
    positions = user_state.get("assetPositions", [])
    if positions:
        print(f'\nFound {len(positions)} position(s):')
        for pos in positions:
            position = pos.get("position", {})
            coin = position.get("coin", "Unknown")
            szi = float(position.get("szi", 0))
            if szi != 0:
                entry_px = float(position.get("entryPx", 0))
                unrealized_pnl = float(position.get("unrealizedPnl", 0))
                print(f'  {coin}: {"LONG" if szi > 0 else "SHORT"} {abs(szi)} @ ${entry_px:,.2f} (PnL: ${unrealized_pnl:,.2f})')
    
    print('\n✅ Account data fetching works!')
else:
    print(f'❌ Error: {result.get("error", "Unknown error")}')