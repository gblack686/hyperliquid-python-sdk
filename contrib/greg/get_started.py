import os
import sys
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount

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
    
    if not secret_key:
        print("Error: HYPERLIQUID_API_KEY not found in .env file")
        print("Please update the .env file with your actual API private key")
        sys.exit(1)
    
    if not account_address:
        print("Error: ACCOUNT_ADDRESS not found in .env file")
        sys.exit(1)
    
    # Validate the placeholder key hasn't been used
    if secret_key == "0x0000000000000000000000000000000000000000000000000000000000000000":
        print("\nWARNING: You're using a placeholder private key!")
        print("Please replace the HYPERLIQUID_API_KEY in .env with your actual API wallet private key")
        print("\nTo get your API key:")
        print("1. Go to https://app.hyperliquid.xyz/API")
        print("2. Generate and authorize a new API private key")
        print("3. Replace the placeholder in .env with your actual key")
        print("\nYour main wallet address (configured): {}".format(account_address))
        sys.exit(1)
    
    try:
        # Create account from private key
        account: LocalAccount = eth_account.Account.from_key(secret_key)
        api_wallet_address = account.address
        
        # Select network
        base_url = getattr(constants, network)
        
        print("=" * 60)
        print("Hyperliquid SDK - Getting Started")
        print("=" * 60)
        print(f"Network: {network.replace('_API_URL', '')}")
        print(f"Main Wallet Address: {account_address}")
        print(f"API Wallet Address: {api_wallet_address}")
        print("=" * 60)
        
        # Initialize Info client (read-only operations)
        info = Info(base_url, skip_ws=True)
        
        # Get user state
        print("\nFetching account information...")
        user_state = info.user_state(account_address)
        
        # Check if account has any positions or balances
        margin_summary = user_state.get("marginSummary", {})
        account_value = float(margin_summary.get("accountValue", 0))
        
        print(f"\nAccount Value: ${account_value:,.2f}")
        
        # Get spot balances
        spot_user_state = info.spot_user_state(account_address)
        spot_balances = spot_user_state.get("balances", [])
        
        if spot_balances:
            print("\nSpot Balances:")
            for balance in spot_balances:
                token = balance.get("token", "Unknown")
                hold = float(balance.get("hold", 0))
                total = float(balance.get("total", 0))
                if total > 0:
                    print(f"  {token}: {total:,.4f} (available: {total - hold:,.4f})")
        
        # Get open positions
        positions = user_state.get("assetPositions", [])
        if positions:
            print("\nOpen Positions:")
            for pos in positions:
                position = pos.get("position", {})
                coin = position.get("coin", "Unknown")
                szi = float(position.get("szi", 0))
                entry_px = float(position.get("entryPx", 0))
                if szi != 0:
                    side = "LONG" if szi > 0 else "SHORT"
                    print(f"  {coin}: {side} {abs(szi)} @ ${entry_px:,.2f}")
        
        # Initialize Exchange client (for trading operations)
        exchange = Exchange(account, base_url, account_address=account_address)
        
        # Get all tradeable assets
        meta = info.meta()
        universe = meta.get("universe", [])
        perp_assets = [asset.get("name") for asset in universe if asset.get("name")]
        
        print(f"\nTradeable Perpetual Assets: {len(perp_assets)} available")
        print(f"Examples: {', '.join(perp_assets[:5])}...")
        
        # Get spot metadata
        spot_meta = info.spot_meta()
        spot_tokens = spot_meta.get("tokens", [])
        spot_pairs = spot_meta.get("universe", [])
        
        print(f"\nSpot Tokens: {len(spot_tokens)} available")
        print(f"Spot Trading Pairs: {len(spot_pairs)} available")
        
        print("\n" + "=" * 60)
        print("Successfully connected to Hyperliquid!")
        print("=" * 60)
        
        print("\nNext steps:")
        print("1. Replace the placeholder private key in .env with your actual API key")
        print("2. Check out the examples folder for trading examples:")
        print("   - basic_order.py: Place limit orders")
        print("   - basic_market_order.py: Place market orders")
        print("   - basic_spot_order.py: Trade spot pairs")
        print("   - basic_transfer.py: Transfer between accounts")
        print("\nExample usage:")
        print("  python examples/basic_order.py")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure your API key is correct")
        print("2. Ensure your main wallet address is correct")
        print("3. Check your network connection")
        print("4. Verify you're using the correct network (MAINNET vs TESTNET)")
        sys.exit(1)

if __name__ == "__main__":
    main()