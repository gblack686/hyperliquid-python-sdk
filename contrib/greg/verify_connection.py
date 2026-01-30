import os
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import json

load_dotenv()

secret_key = os.getenv('HYPERLIQUID_API_KEY')
account_address = os.getenv('ACCOUNT_ADDRESS')

# Create account from private key
account: LocalAccount = eth_account.Account.from_key(secret_key)
api_wallet = account.address

base_url = getattr(constants, 'MAINNET_API_URL')
info = Info(base_url, skip_ws=True)

print("=" * 60)
print("Verifying Hyperliquid Connection")
print("=" * 60)

# 1. Test basic connection with market data
print("\n1. Testing API connection with market data:")
try:
    meta = info.meta()
    print(f"   SUCCESS: Connected to Hyperliquid")
    print(f"   Found {len(meta.get('universe', []))} tradeable assets")
except Exception as e:
    print(f"   FAILED: {e}")

# 2. Get current BTC price to verify data is live
print("\n2. Getting live market data (BTC):")
try:
    all_mids = info.all_mids()
    btc_price = float(all_mids.get("BTC", 0))
    print(f"   BTC Current Price: ${btc_price:,.2f}")
except Exception as e:
    print(f"   FAILED: {e}")

# 3. Check your actual wallet on Hyperliquid
print(f"\n3. Checking account: {account_address}")
print(f"   API Wallet being used: {api_wallet}")

# Initialize exchange to test authenticated endpoints
exchange = Exchange(account, base_url, account_address=account_address)

# 4. Try to get account info through exchange
print("\n4. Testing authenticated API access:")
try:
    # Try a simple authenticated request
    result = exchange.post("/info", {"type": "clearinghouseState", "user": account_address})
    if result:
        print("   SUCCESS: Authenticated API access working")
        # Check the actual response
        if "assetPositions" in result:
            print(f"   Found {len(result.get('assetPositions', []))} asset positions")
        if "marginSummary" in result:
            margin = result.get("marginSummary", {})
            print(f"   Account Value from direct API: ${float(margin.get('accountValue', 0)):,.2f}")
    else:
        print("   No data returned")
except Exception as e:
    print(f"   FAILED: {e}")

# 5. Double-check the wallet addresses match what's expected
print("\n5. Wallet verification:")
print(f"   Your provided main account: {account_address}")
print(f"   API wallet from private key: {api_wallet}")
print("\n   To verify this is correct:")
print("   1. Go to https://app.hyperliquid.xyz/API")
print("   2. Check that your API wallet address matches:", api_wallet)
print("   3. Make sure it's authorized for your main account")

# 6. Try to fetch using the API wallet address itself
print(f"\n6. Checking if funds are in API wallet itself:")
api_state = info.user_state(api_wallet.lower())
api_margin = api_state.get("marginSummary", {})
api_value = float(api_margin.get("accountValue", 0))
print(f"   API Wallet Account Value: ${api_value:,.2f}")

# Also check spot
api_spot = info.spot_user_state(api_wallet.lower())
api_spot_balances = api_spot.get("balances", [])
if api_spot_balances:
    print("   API Wallet Spot Balances:")
    for balance in api_spot_balances:
        token = balance.get("token", "Unknown")
        total = float(balance.get("total", 0))
        if total > 0:
            print(f"     {token}: {total:,.6f}")