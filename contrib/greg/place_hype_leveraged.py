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
    print("HYPE 2x Leveraged Order Placement")
    print("=" * 60)
    
    # Get current HYPE price
    all_mids = info.all_mids()
    hype_price = float(all_mids.get("HYPE", 0))
    
    if hype_price == 0:
        print("Error: Could not get HYPE price")
        sys.exit(1)
    
    print(f"Current HYPE Price: ${hype_price:,.2f}")
    
    # Get current position to add to it
    user_state = info.user_state(account_address)
    current_hype_position = 0
    
    for pos in user_state.get("assetPositions", []):
        position = pos.get("position", {})
        if position.get("coin") == "HYPE":
            current_hype_position = float(position.get("szi", 0))
            print(f"Current HYPE Position: {current_hype_position} HYPE")
            break
    
    # Calculate order details for 2x leverage
    # With 2x leverage, $100 margin controls $200 worth of HYPE
    margin_usd = 100  # Your margin
    notional_usd = 200  # Total position size (2x leverage)
    hype_quantity = notional_usd / hype_price
    
    # Round to appropriate decimals
    hype_quantity = round(hype_quantity, 2)
    
    # Set limit price slightly above current price to ensure fill
    limit_price = round(hype_price * 1.001, 2)
    
    print(f"\n2x Leveraged Order Details:")
    print(f"  Leverage: 2x")
    print(f"  Margin Required: ${margin_usd:,.2f}")
    print(f"  Total Position Size: ${notional_usd:,.2f}")
    print(f"  Side: BUY")
    print(f"  Quantity: {hype_quantity} HYPE")
    print(f"  Limit Price: ${limit_price:,.2f}")
    print(f"  Order Type: Limit Order (IOC)")
    
    # Check available margin
    margin_summary = user_state.get("marginSummary", {})
    account_value = float(margin_summary.get("accountValue", 0))
    total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
    available_margin = account_value - total_margin_used
    
    print(f"\nMargin Check:")
    print(f"  Account Value: ${account_value:,.2f}")
    print(f"  Currently Used Margin: ${total_margin_used:,.2f}")
    print(f"  Available for Trading: ${available_margin:,.2f}")
    
    # Estimate new margin requirement
    estimated_new_margin = margin_usd  # Rough estimate
    print(f"  Estimated New Margin Required: ${estimated_new_margin:,.2f}")
    
    if available_margin < estimated_new_margin:
        print(f"\nWarning: May not have sufficient available margin")
        print(f"Proceeding anyway - exchange will reject if insufficient...")
    
    # Confirm before placing
    print("\nPlacing 2x leveraged order...")
    
    try:
        # Place the leveraged order
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
                        print(f"  Total Notional: ${total_sz * avg_px:,.2f}")
                        
                        # Calculate actual leverage
                        margin_used_estimate = (total_sz * avg_px) / 2  # Assuming 2x leverage
                        print(f"  Estimated Margin Used: ${margin_used_estimate:,.2f}")
                        print(f"  Leverage: 2x")
                
                # Check if there was a resting order
                resting = status.get("resting", {})
                if resting and resting.get("oid"):
                    print(f"\nResting Order ID: {resting.get('oid')}")
        else:
            print(f"\nOrder failed: {order_result}")
            
    except Exception as e:
        print(f"\nError placing order: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Check updated position and margin
    print("\n" + "=" * 60)
    print("Checking updated position and margin usage...")
    
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
            position_value = abs(szi) * entry_px
            
            if szi != 0:
                side = "LONG" if szi > 0 else "SHORT"
                print(f"\nUpdated HYPE Position:")
                print(f"  Side: {side}")
                print(f"  Size: {abs(szi)} HYPE")
                print(f"  Entry Price: ${entry_px:,.2f}")
                print(f"  Position Value: ${position_value:,.2f}")
                print(f"  Unrealized PnL: ${unrealized_pnl:,.2f}")
                
                # Show position increase
                if current_hype_position > 0:
                    increase = abs(szi) - current_hype_position
                    print(f"  Position Increase: {increase:.2f} HYPE")
                break
    
    # Show updated margin summary
    margin_summary = user_state.get("marginSummary", {})
    new_account_value = float(margin_summary.get("accountValue", 0))
    new_margin_used = float(margin_summary.get("totalMarginUsed", 0))
    new_total_position = float(margin_summary.get("totalNtlPos", 0))
    
    print(f"\nUpdated Margin Summary:")
    print(f"  Account Value: ${new_account_value:,.2f}")
    print(f"  Total Margin Used: ${new_margin_used:,.2f}")
    print(f"  Total Position Value: ${new_total_position:,.2f}")
    
    if new_margin_used > 0 and new_total_position > 0:
        effective_leverage = new_total_position / new_account_value
        print(f"  Effective Account Leverage: {effective_leverage:.2f}x")
    
    margin_increase = new_margin_used - total_margin_used
    if margin_increase > 0:
        print(f"  Margin Used for This Trade: ${margin_increase:,.2f}")

if __name__ == "__main__":
    main()