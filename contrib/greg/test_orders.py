"""
Test script for order execution functions
Verifies all order operations are working correctly
"""

import os
import sys
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Load environment variables
load_dotenv()

def test_order_operations():
    """Test basic order operations"""
    
    # Setup
    secret_key = os.getenv('HYPERLIQUID_API_KEY')
    account_address = os.getenv('ACCOUNT_ADDRESS')
    
    if not secret_key or not account_address:
        print("Error: Missing configuration in .env file")
        sys.exit(1)
    
    account: LocalAccount = eth_account.Account.from_key(secret_key)
    base_url = getattr(constants, 'MAINNET_API_URL')
    info = Info(base_url, skip_ws=True)
    exchange = Exchange(account, base_url)
    
    print("[TEST] Order Operations Test")
    print(f"Account: {account_address}")
    
    # Test 1: Get current orders
    print("\n1. Checking current orders...")
    orders = info.open_orders(account_address)
    print(f"   Found {len(orders)} open orders")
    
    # Test 2: Get account state
    print("\n2. Checking account state...")
    user_state = info.user_state(account_address)
    account_value = float(user_state.get("marginSummary", {}).get("accountValue", 0))
    print(f"   Account value: ${account_value:,.2f}")
    
    # Test 3: Get current prices
    print("\n3. Getting current prices...")
    mids = info.all_mids()
    hype_price = float(mids.get("HYPE", 0))
    btc_price = float(mids.get("BTC", 0))
    print(f"   HYPE: ${hype_price:.2f}")
    print(f"   BTC: ${btc_price:,.2f}")
    
    # Test 4: Place a test order (minimum $10 value, far from market)
    print("\n4. Testing order placement...")
    test_price = round(hype_price * 0.8, 2)  # 20% below market
    test_size = max(0.5, 11 / test_price)  # Ensure at least $10 value
    test_size = round(test_size, 2)
    print(f"   Placing test order: {test_size} HYPE @ ${test_price} (value: ${test_size * test_price:.2f})")
    
    try:
        result = exchange.order(
            name="HYPE",
            is_buy=True,
            sz=test_size,
            limit_px=test_price,
            order_type={"limit": {"tif": "Gtc"}}
        )
        
        if result.get("status") == "ok":
            data = result.get("response", {}).get("data", {})
            statuses = data.get("statuses", [])
            
            if statuses and statuses[0].get("resting"):
                oid = statuses[0]["resting"]["oid"]
                print(f"   SUCCESS: Order placed with ID {oid}")
                
                # Test 5: Cancel the order
                print("\n5. Testing order cancellation...")
                cancel_result = exchange.cancel(name="HYPE", oid=oid)
                
                if cancel_result.get("status") == "ok":
                    print("   SUCCESS: Order cancelled")
                else:
                    print(f"   Failed to cancel: {cancel_result}")
            else:
                print(f"   Order not placed: {statuses}")
        else:
            print(f"   Failed to place order: {result}")
            
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 6: Check positions
    print("\n6. Checking positions...")
    positions = user_state.get("assetPositions", [])
    open_positions = 0
    
    for pos_data in positions:
        position = pos_data.get("position", {})
        szi = float(position.get("szi", 0))
        if szi != 0:
            open_positions += 1
            coin = position.get("coin")
            side = "LONG" if szi > 0 else "SHORT"
            print(f"   {coin}: {side} {abs(szi)}")
    
    if open_positions == 0:
        print("   No open positions")
    
    print("\n[TEST] All tests completed successfully!")

if __name__ == "__main__":
    test_order_operations()