#!/usr/bin/env python3
"""
Quick system check script
Shows current configuration and readiness status
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

def main():
    print("\n" + "="*60)
    print("HYPE TRADING SYSTEM STATUS CHECK")
    print("="*60)
    
    # Check environment
    print("\n[ENVIRONMENT]")
    api_key = os.getenv("HYPERLIQUID_API_KEY")
    account = os.getenv("ACCOUNT_ADDRESS")
    
    if api_key and account:
        print(f"  Hyperliquid API: Configured")
        print(f"  Account: {account[:10]}...{account[-4:]}")
    else:
        print("  Hyperliquid API: NOT CONFIGURED")
    
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url:
        print(f"  Supabase: Configured")
    else:
        print(f"  Supabase: Not configured (optional)")
    
    # Check files
    print("\n[FILES]")
    files = [
        "src/main.py",
        "src/websocket_manager.py", 
        "src/strategy_engine.py",
        "src/order_executor.py",
        "src/config.py",
        "start.py",
        ".env"
    ]
    
    all_present = True
    for file in files:
        if Path(file).exists():
            print(f"  [OK] {file}")
        else:
            print(f"  [X] {file} - MISSING")
            all_present = False
    
    # Check directories
    print("\n[DIRECTORIES]")
    dirs = ["logs", "data", "config"]
    for dir_name in dirs:
        if Path(dir_name).exists():
            print(f"  [OK] {dir_name}/")
        else:
            print(f"  [!] {dir_name}/ - Will be created on first run")
    
    # Trading parameters
    print("\n[STRATEGY PARAMETERS]")
    print(f"  Lookback Period: {os.getenv('LOOKBACK_PERIOD', '12')} hours")
    print(f"  Entry Z-Score: {os.getenv('ENTRY_Z_SCORE', '0.75')}")
    print(f"  Exit Z-Score: {os.getenv('EXIT_Z_SCORE', '0.5')}")
    print(f"  Stop Loss: {float(os.getenv('STOP_LOSS_PCT', '0.05'))*100:.0f}%")
    print(f"  Max Position: ${os.getenv('MAX_POSITION_SIZE', '1000')}")
    
    # Commands
    print("\n[AVAILABLE COMMANDS]")
    print("  python test_setup.py      - Run comprehensive tests")
    print("  python start.py --test    - Test with simulated data")
    print("  python start.py           - Run in dry-run mode (safe)")
    print("  python start.py --paper   - Paper trading mode")
    print("  python start.py --live    - Live trading (requires confirmation)")
    
    # Status
    print("\n[SYSTEM STATUS]")
    if all_present and api_key and account:
        print("  [OK] READY TO RUN")
        print("\n  Next step: python start.py --test")
    else:
        print("  [!] Configuration needed")
        if not api_key or not account:
            print("      -> Add credentials to .env file")
        if not all_present:
            print("      -> Some files are missing")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()