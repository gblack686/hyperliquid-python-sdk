#!/usr/bin/env python
"""Test Hyperliquid connection for the Trading Dashboard."""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'quantpylib'))

# Load environment variables
load_dotenv()

def test_direct_hyperliquid():
    """Test direct hyperliquid package connection (like greg-examples)."""
    print("\n" + "="*60)
    print("Testing Direct Hyperliquid Package Connection")
    print("="*60)
    
    try:
        from hyperliquid.info import Info
        from hyperliquid.exchange import Exchange
        from hyperliquid.utils import constants
        
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        account_address = os.getenv('ACCOUNT_ADDRESS')
        
        if not secret_key:
            print("[WARNING] HYPERLIQUID_API_KEY not found in .env")
            return False
            
        # Create account from private key
        account: LocalAccount = eth_account.Account.from_key(secret_key)
        api_wallet = account.address
        
        print(f"API Wallet: {api_wallet}")
        print(f"Account Address: {account_address}")
        
        # Connect to mainnet
        base_url = constants.MAINNET_API_URL
        info = Info(base_url, skip_ws=True)
        
        # Test basic connection
        print("\n1. Testing API connection:")
        meta = info.meta()
        print(f"   [OK] Connected to Hyperliquid")
        print(f"   [OK] Found {len(meta.get('universe', []))} tradeable assets")
        
        # Get live price
        print("\n2. Getting live BTC price:")
        all_mids = info.all_mids()
        btc_price = float(all_mids.get("BTC", 0))
        print(f"   [OK] BTC Current Price: ${btc_price:,.2f}")
        
        return True
        
    except ImportError as e:
        print(f"[ERROR] hyperliquid package not installed: {e}")
        print("Install with: pip install hyperliquid-python-sdk")
        return False
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False

def test_quantpylib_connection():
    """Test quantpylib connection (used by dashboard)."""
    print("\n" + "="*60)
    print("Testing Quantpylib Connection (Dashboard Method)")
    print("="*60)
    
    try:
        from quantpylib.wrappers.hyperliquid import Hyperliquid
        from quantpylib.standards import Period
        
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        
        print("\n1. Initializing Hyperliquid client:")
        
        # Try with no credentials first (public endpoints)
        print("   Testing public endpoints...")
        client = Hyperliquid(key=None, secret=None, mode="mainnet")
        
        # Test public endpoint
        print("\n2. Testing public data access:")
        try:
            # Get market data
            markets = asyncio.run(client.get_markets())
            if markets:
                print(f"   [OK] Connected! Found {len(markets)} markets")
                
                # Show first few markets
                print("   Sample markets:")
                for market in list(markets.keys())[:5]:
                    print(f"     - {market}")
            else:
                print("   [WARNING] No markets returned")
        except Exception as e:
            print(f"   [ERROR] Failed to get markets: {e}")
            
        # Test with credentials if available
        if secret_key:
            print("\n3. Testing authenticated connection:")
            try:
                auth_client = Hyperliquid(
                    key=secret_key,
                    secret=None,  # quantpylib might only need the key
                    mode="mainnet"
                )
                
                # Try to get account info
                account_info = asyncio.run(auth_client.get_account())
                if account_info:
                    print("   [OK] Authenticated connection successful")
                    print(f"   Account info: {account_info}")
                else:
                    print("   [WARNING] No account info returned")
                    
            except Exception as e:
                print(f"   [ERROR] Authentication failed: {e}")
        else:
            print("\n3. Skipping authenticated test (no API key in .env)")
            
        return True
        
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False

async def test_dashboard_client():
    """Test the actual dashboard HyperliquidClient."""
    print("\n" + "="*60)
    print("Testing Dashboard HyperliquidClient")
    print("="*60)
    
    try:
        from src.hyperliquid_client import HyperliquidClient
        
        # Load credentials
        api_key = os.getenv('HYPERLIQUID_API_KEY')
        api_secret = os.getenv('HYPERLIQUID_SECRET')
        
        print("\n1. Initializing HyperliquidClient:")
        client = HyperliquidClient(key=api_key, secret=api_secret, mode="mainnet")
        
        print("\n2. Testing connection:")
        connected = await client.connect()
        if connected:
            print("   [OK] Connected successfully!")
        else:
            print("   [ERROR] Connection failed")
            print("   This might be due to missing address attribute in quantpylib")
            
        print("\n3. Testing market data fetch:")
        try:
            # Test getting trade bars
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            bars = await client.get_trade_bars(
                ticker="BTC",
                start=start_time,
                end=end_time
            )
            
            if bars:
                print("   [OK] Successfully fetched trade bars")
                print(f"   Got {len(bars) if hasattr(bars, '__len__') else 'some'} bars")
            else:
                print("   [WARNING] No trade bars returned")
                
        except Exception as e:
            print(f"   [ERROR] Failed to fetch trade bars: {e}")
            
        print("\n4. Testing account info:")
        try:
            account_info = await client.get_account_info()
            if account_info:
                print("   [OK] Account info retrieved")
                print(f"   Balance: ${account_info.get('balance', 0):,.2f}")
            else:
                print("   [WARNING] No account info (might need valid API credentials)")
        except Exception as e:
            print(f"   [ERROR] Failed to get account info: {e}")
            
        return connected
        
    except Exception as e:
        print(f"[ERROR] Dashboard client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_env_configuration():
    """Check environment configuration."""
    print("\n" + "="*60)
    print("Environment Configuration Check")
    print("="*60)
    
    load_dotenv()
    
    required_vars = [
        ('HYPERLIQUID_API_KEY', 'Your private key for API access'),
        ('HYPERLIQUID_SECRET', 'API secret (if required)'),
        ('ACCOUNT_ADDRESS', 'Your Hyperliquid account address'),
        ('SUPABASE_URL', 'Supabase project URL'),
        ('SUPABASE_KEY', 'Supabase anon key')
    ]
    
    print("\nChecking .env file:")
    all_present = True
    
    for var, description in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'SECRET' in var:
                masked = value[:10] + '...' + value[-4:] if len(value) > 14 else '***'
                print(f"  [OK] {var}: {masked}")
            else:
                print(f"  [OK] {var}: {value[:30]}...")
        else:
            print(f"  [MISSING] {var}: {description}")
            all_present = False
    
    if not all_present:
        print("\n[WARNING] Some environment variables are missing.")
        print("Update your .env file with the required values.")
    
    return all_present

def main():
    """Run all connection tests."""
    print("\n" + "="*60)
    print(" HYPERLIQUID CONNECTION TEST SUITE")
    print("="*60)
    
    # Check environment first
    env_ok = check_env_configuration()
    
    # Test different connection methods
    results = {}
    
    # Test 1: Direct hyperliquid package
    results['Direct Package'] = test_direct_hyperliquid()
    
    # Test 2: Quantpylib wrapper
    results['Quantpylib'] = test_quantpylib_connection()
    
    # Test 3: Dashboard client
    results['Dashboard Client'] = asyncio.run(test_dashboard_client())
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    # Recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    if not env_ok:
        print("\n1. Fix missing environment variables in .env file")
        
    if not results['Direct Package']:
        print("\n2. Install hyperliquid package:")
        print("   pip install hyperliquid-python-sdk")
        
    if not results['Dashboard Client']:
        print("\n3. Dashboard client issues:")
        print("   - Check if quantpylib Hyperliquid wrapper needs updating")
        print("   - The error 'NoneType has no attribute address' suggests")
        print("     quantpylib might not be handling authentication properly")
        print("   - Consider using direct hyperliquid package instead")
    
    print("\n" + "="*60)
    
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)