import os
from dotenv import load_dotenv
import eth_account
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

# Test both uppercase and lowercase addresses
addresses_to_test = [
    "0x7f18e47b09dda0ba3f51ec7072ad10197d91904b",  # Your original address
    "0x7F18E47B09DDA0BA3F51EC7072AD10197D91904B",  # Uppercase version
    "0x1e5fe6457cbeaf5683faa8e21c6404a76793db6e",  # The other address that was in .env
]

base_url = getattr(constants, 'MAINNET_API_URL')
info = Info(base_url, skip_ws=True)

print("Testing different address formats:\n")

for addr in addresses_to_test:
    print(f"Address: {addr}")
    try:
        user_state = info.user_state(addr)
        margin_summary = user_state.get("marginSummary", {})
        account_value = float(margin_summary.get("accountValue", 0))
        
        spot_state = info.spot_user_state(addr)
        spot_balances = spot_state.get("balances", [])
        
        print(f"  Perp Account Value: ${account_value:,.2f}")
        
        if spot_balances:
            for balance in spot_balances:
                token = balance.get("token", "Unknown")
                total = float(balance.get("total", 0))
                if total > 0:
                    print(f"  Spot {token}: {total:,.6f}")
        
        # Also check if there's any vault equity
        if "vaultEquity" in user_state:
            for vault in user_state["vaultEquity"]:
                vault_addr = vault.get("vault", "")
                equity = float(vault.get("equity", 0))
                if equity > 0:
                    print(f"  Vault {vault_addr}: ${equity:,.2f}")
                    
    except Exception as e:
        print(f"  Error: {e}")
    
    print("-" * 40)