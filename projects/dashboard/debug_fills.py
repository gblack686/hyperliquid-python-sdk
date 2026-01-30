"""Debug fills structure"""
import os
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants
import eth_account
import json

load_dotenv()

secret_key = os.getenv('HYPERLIQUID_API_KEY')
account_address = os.getenv('ACCOUNT_ADDRESS')

if not account_address and secret_key:
    account = eth_account.Account.from_key(secret_key)
    account_address = account.address

info = Info(constants.MAINNET_API_URL, skip_ws=True)
fills = info.user_fills(account_address)

print("Type of fills:", type(fills))
if fills:
    print("Number of fills:", len(fills))
    print("\nFirst fill structure:")
    if len(fills) > 0:
        print(json.dumps(fills[0], indent=2))