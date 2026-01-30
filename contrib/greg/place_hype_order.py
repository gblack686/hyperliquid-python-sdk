import os
import sys
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount
from decimal import Decimal

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Load environment variables
load_dotenv()

def main():
    # Get configuration
    secret_key = os.getenv('HYPERLIQUID_API_KEY')
    account_address = os.getenv('ACCOUNT_ADDRESS')
    
    # Create account from private key
    account: LocalAccount = eth_account.Account.from_key(secret_key)
    
    # Initialize clients
    base_url = constants.MAINNET_API_URL
    info = Info(base_url, skip_ws=True)
    exchange = Exchange(account, base_url, account_address=account_address)
    
    print("=" * 60)
    print("HYPE Order Placement")
    print("=" * 60)
    
    # Get current HYPE price
    all_mids = info.all_mids()
    hype_price = float(all_mids.get("HYPE", 0))
    
    if hype_price == 0:
        print("Error: Could not get HYPE price")
        sys.exit(1)
    
    print(f"Current HYPE Price: ${hype_price:,.2f}")
    
    # Calculate order details
    # You want to buy $100 worth of HYPE
    usd_amount = 100
    hype_quantity = usd_amount / hype_price
    
    # Round to appropriate decimals (HYPE typically uses 2 decimals for size)
    hype_quantity = round(hype_quantity, 2)
    
    # Set limit price slightly above current price to ensure fill
    # Adding 0.1% buffer
    limit_price = round(hype_price * 1.001, 2)
    
    print(f"\nOrder Details:")
    print(f"  Side: BUY")
    print(f"  Quantity: {hype_quantity} HYPE")
    print(f"  Notional Value: ${hype_quantity * hype_price:,.2f}")
    print(f"  Limit Price: ${limit_price:,.2f}")
    print(f"  Order Type: Limit Order (IOC - Immediate or Cancel)")
    
    # Confirm before placing
    print("\nPlacing order...")
    
    try:
        # Place the order
        order_result = exchange.order(
            "HYPE",  # coin
            True,    # is_buy
            hype_quantity,  # sz
            limit_price,    # limit_px
            {"limit": {"tif": "Ioc"}},  # order_type - Immediate or Cancel
            False  # reduce_only
        )
        
        if order_result.get("status") == "ok":
            print("\nOrder placed successfully!")
            
            statuses = order_result.get("response", {}).get("data", {}).get("statuses", [])
            for status in statuses:
                filled = status.get("filled", {})
                if filled:
                    total_sz = float(filled.get("totalSz", 0))
                    avg_px = float(filled.get("avgPx", 0))
                    if total_sz > 0:
                        print(f"\nOrder Filled:")
                        print(f"  Filled Size: {total_sz} HYPE")
                        print(f"  Average Price: ${avg_px:,.2f}")
                        print(f"  Total Cost: ${total_sz * avg_px:,.2f}")
                
                # Check if there was a resting order
                resting = status.get("resting", {})
                if resting:
                    oid = resting.get("oid")
                    if oid:
                        print(f"\nResting Order ID: {oid}")
        else:
            print(f"\nOrder failed: {order_result}")
            
    except Exception as e:
        print(f"\nError placing order: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Check updated position
    print("\n" + "=" * 60)
    print("Checking updated positions...")
    
    user_state = info.user_state(account_address)
    positions = user_state.get("assetPositions", [])
    
    for pos in positions:
        position = pos.get("position", {})
        coin = position.get("coin", "Unknown")
        if coin == "HYPE":
            szi = float(position.get("szi", 0))
            entry_px = float(position.get("entryPx", 0))
            mark_px = float(position.get("markPx", 0))
            unrealized_pnl = float(position.get("unrealizedPnl", 0))
            if szi != 0:
                side = "LONG" if szi > 0 else "SHORT"
                print(f"\nHYPE Position:")
                print(f"  Side: {side}")
                print(f"  Size: {abs(szi)} HYPE")
                print(f"  Entry Price: ${entry_px:,.2f}")
                print(f"  Current Price: ${mark_px:,.2f}")
                print(f"  Unrealized PnL: ${unrealized_pnl:,.2f}")
                break
    else:
        print("\nNo HYPE position found (order may not have filled)")

if __name__ == "__main__":
    main()