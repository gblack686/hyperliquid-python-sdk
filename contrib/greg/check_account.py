import os
import sys
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount
import json

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Load environment variables from .env file
load_dotenv()

def main():
    # Get configuration from environment variables
    secret_key = os.getenv('HYPERLIQUID_API_KEY')
    account_address = os.getenv('ACCOUNT_ADDRESS')
    network = os.getenv('NETWORK', 'MAINNET_API_URL')
    
    if not secret_key or not account_address:
        print("Error: Missing configuration in .env file")
        sys.exit(1)
    
    try:
        # Create account from private key
        account: LocalAccount = eth_account.Account.from_key(secret_key)
        api_wallet_address = account.address
        
        # Select network
        base_url = getattr(constants, network)
        
        print("=" * 60)
        print("Hyperliquid Account Details")
        print("=" * 60)
        print(f"Network: {network.replace('_API_URL', '')}")
        print(f"Main Account: {account_address}")
        print(f"API Wallet: {api_wallet_address}")
        print("=" * 60)
        
        # Initialize Info client
        info = Info(base_url, skip_ws=True)
        
        # Get complete user state
        print("\n[1] PERPETUALS ACCOUNT:")
        print("-" * 40)
        user_state = info.user_state(account_address)
        
        # Account value and margin
        margin_summary = user_state.get("marginSummary", {})
        account_value = float(margin_summary.get("accountValue", 0))
        total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
        total_ntl_pos = float(margin_summary.get("totalNtlPos", 0))
        total_raw_usd = float(margin_summary.get("totalRawUsd", 0))
        
        print(f"Account Value: ${account_value:,.2f}")
        print(f"Total Margin Used: ${total_margin_used:,.2f}")
        print(f"Total Notional Position: ${total_ntl_pos:,.2f}")
        print(f"Total Raw USD: ${total_raw_usd:,.2f}")
        
        # Cross margin details
        cross_margin = user_state.get("crossMarginSummary", {})
        if cross_margin:
            cross_value = float(cross_margin.get("accountValue", 0))
            total_pnl = float(cross_margin.get("totalPnl", 0))
            print(f"\nCross Margin Account Value: ${cross_value:,.2f}")
            print(f"Total PnL: ${total_pnl:,.2f}")
        
        # Withdrawable balance
        withdrawable = user_state.get("withdrawable", 0)
        if withdrawable:
            print(f"\nWithdrawable: ${float(withdrawable):,.2f}")
        
        # Open positions
        positions = user_state.get("assetPositions", [])
        if positions:
            print("\nOpen Positions:")
            for pos in positions:
                position = pos.get("position", {})
                coin = position.get("coin", "Unknown")
                szi = float(position.get("szi", 0))
                entry_px = float(position.get("entryPx", 0))
                mark_px = float(position.get("markPx", 0))
                unrealized_pnl = float(position.get("unrealizedPnl", 0))
                if szi != 0:
                    side = "LONG" if szi > 0 else "SHORT"
                    print(f"  {coin}: {side} {abs(szi)} @ ${entry_px:,.2f}")
                    print(f"    Mark: ${mark_px:,.2f}, Unrealized PnL: ${unrealized_pnl:,.2f}")
        
        # Get spot balances
        print("\n[2] SPOT ACCOUNT:")
        print("-" * 40)
        spot_user_state = info.spot_user_state(account_address)
        spot_balances = spot_user_state.get("balances", [])
        
        if spot_balances:
            print("Spot Balances:")
            total_spot_value = 0
            for balance in spot_balances:
                token = balance.get("token", "Unknown")
                hold = float(balance.get("hold", 0))
                total = float(balance.get("total", 0))
                if total > 0:
                    available = total - hold
                    print(f"  {token}:")
                    print(f"    Total: {total:,.6f}")
                    print(f"    Available: {available:,.6f}")
                    print(f"    On Hold: {hold:,.6f}")
                    
                    # Try to get USD value if it's USDC
                    if token == "USDC":
                        total_spot_value += total
            
            if total_spot_value > 0:
                print(f"\nTotal Spot Value (USDC): ${total_spot_value:,.2f}")
        else:
            print("No spot balances found")
        
        # Get open orders
        print("\n[3] OPEN ORDERS:")
        print("-" * 40)
        open_orders = info.open_orders(account_address)
        if open_orders:
            print(f"Found {len(open_orders)} open orders:")
            for order in open_orders[:5]:  # Show first 5 orders
                coin = order.get("coin", "Unknown")
                side = order.get("side", "")
                sz = float(order.get("sz", 0))
                limit_px = float(order.get("limitPx", 0))
                print(f"  {coin}: {side} {sz} @ ${limit_px:,.2f}")
        else:
            print("No open orders")
        
        # Get user fees
        print("\n[4] FEE STRUCTURE:")
        print("-" * 40)
        user_fees = info.user_fees(account_address)
        if user_fees:
            print(f"Fee Schedule: {user_fees.get('feeSchedule', 'Unknown')}")
            print(f"Maker Rate: {float(user_fees.get('makerRate', 0)) * 100:.4f}%")
            print(f"Taker Rate: {float(user_fees.get('takerRate', 0)) * 100:.4f}%")
        
        # Check clearinghouse state for more details
        print("\n[5] CLEARINGHOUSE STATE:")
        print("-" * 40)
        clearinghouse = info.clearinghouse_state(account_address)
        
        # Print raw response for debugging
        print("\nRaw clearinghouse response (first 500 chars):")
        print(json.dumps(clearinghouse, indent=2)[:500])
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()