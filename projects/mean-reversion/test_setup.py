#!/usr/bin/env python3
"""
Test script to verify trading system setup
Run this before starting the actual trading system
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_environment():
    """Test environment configuration"""
    print("\n1. Testing Environment Configuration...")
    
    # Check .env file
    if not Path(".env").exists():
        print("   [X] .env file not found")
        print("   -> Copy .env.example to .env and configure")
        return False
    
    load_dotenv()
    
    # Check required variables
    required = {
        "HYPERLIQUID_API_KEY": os.getenv("HYPERLIQUID_API_KEY"),
        "ACCOUNT_ADDRESS": os.getenv("ACCOUNT_ADDRESS")
    }
    
    for key, value in required.items():
        if value:
            masked = value[:6] + "..." + value[-4:] if len(value) > 10 else "***"
            print(f"   [OK] {key}: {masked}")
        else:
            print(f"   [X] {key}: Not set")
            return False
    
    # Check optional variables
    optional = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY")
    }
    
    for key, value in optional.items():
        if value:
            print(f"   [OK] {key}: Configured")
        else:
            print(f"   [!] {key}: Not configured (optional)")
    
    return True


def test_imports():
    """Test all required imports"""
    print("\n2. Testing Python Imports...")
    
    modules = [
        ("hyperliquid.info", "Hyperliquid SDK"),
        ("eth_account", "Ethereum Account"),
        ("supabase", "Supabase Client"),
        ("loguru", "Loguru Logger"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("tenacity", "Tenacity"),
        ("websockets", "WebSockets")
    ]
    
    failed = []
    for module, name in modules:
        try:
            __import__(module)
            print(f"   [OK] {name}")
        except ImportError as e:
            print(f"   [X] {name}: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n   Install missing modules: pip install {' '.join(failed)}")
        return False
    
    return True


def test_components():
    """Test system components"""
    print("\n3. Testing System Components...")
    
    try:
        from config import Config
        config = Config()
        print("   [OK] Configuration Manager")
    except Exception as e:
        print(f"   [X] Configuration Manager: {e}")
        return False
    
    try:
        from strategy_engine import StrategyEngine
        strategy = StrategyEngine()
        print("   [OK] Strategy Engine")
    except Exception as e:
        print(f"   [X] Strategy Engine: {e}")
        return False
    
    try:
        from order_executor import OrderExecutor
        executor = OrderExecutor(dry_run=True)
        print("   [OK] Order Executor")
    except Exception as e:
        print(f"   [X] Order Executor: {e}")
        return False
    
    try:
        from websocket_manager import WebSocketManager
        print("   [OK] WebSocket Manager")
    except Exception as e:
        print(f"   [X] WebSocket Manager: {e}")
        return False
    
    try:
        from main import TradingSystem
        print("   [OK] Trading System")
    except Exception as e:
        print(f"   [X] Trading System: {e}")
        return False
    
    return True


async def test_connections():
    """Test external connections"""
    print("\n4. Testing External Connections...")
    
    # Test Hyperliquid API
    try:
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Try to get HYPE price
        l2_data = info.l2_snapshot("HYPE")
        if l2_data:
            print("   [OK] Hyperliquid API Connection")
            if "levels" in l2_data:
                print(f"      Current HYPE price: ~${float(l2_data['levels'][0][0]['px']):.2f}")
        else:
            print("   [!] Hyperliquid API: Connected but no data")
    except Exception as e:
        print(f"   [X] Hyperliquid API: {e}")
        return False
    
    # Test Supabase (if configured)
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if supabase_url and supabase_key:
            client = create_client(supabase_url, supabase_key)
            # Try to query a table
            result = client.table("hl_system_health").select("*").limit(1).execute()
            print("   [OK] Supabase Connection")
        else:
            print("   [!] Supabase: Not configured")
    except Exception as e:
        print(f"   [!] Supabase: {e}")
    
    return True


def test_directories():
    """Test and create required directories"""
    print("\n5. Testing Directory Structure...")
    
    dirs = ["logs", "data", "config"]
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"   [OK] Created {dir_name}/")
        else:
            print(f"   [OK] {dir_name}/ exists")
    
    return True


async def test_strategy():
    """Test strategy with sample data"""
    print("\n6. Testing Strategy Engine...")
    
    try:
        from strategy_engine import StrategyEngine, SignalType
        import numpy as np
        
        strategy = StrategyEngine()
        
        # Generate sample prices
        np.random.seed(42)
        base_price = 44.0
        
        signals_generated = 0
        for i in range(20):
            price = base_price + np.random.normal(0, 1)
            strategy.update_price(price, 1000)
            
            if i >= strategy.lookback_period:
                signal = strategy.generate_signal()
                if signal.action != SignalType.HOLD:
                    signals_generated += 1
        
        stats = strategy.get_statistics()
        print(f"   [OK] Strategy test complete")
        print(f"      Signals generated: {signals_generated}")
        print(f"      Current Z-score: {stats['current_indicators']['z_score']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"   [X] Strategy test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("HYPE Trading System - Setup Test")
    print("="*60)
    
    # Run tests
    tests = [
        test_environment(),
        test_imports(),
        test_components(),
        asyncio.run(test_connections()),
        test_directories(),
        asyncio.run(test_strategy())
    ]
    
    # Summary
    print("\n" + "="*60)
    if all(tests):
        print("[OK] ALL TESTS PASSED - System ready to run!")
        print("\nNext steps:")
        print("1. Run in dry-run mode: python start.py")
        print("2. Run in test mode: python start.py --test")
        print("3. Check logs in logs/ directory")
    else:
        print("[X] SOME TESTS FAILED - Please fix issues above")
        print("\nCommon fixes:")
        print("1. Copy .env.example to .env and add credentials")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Check your Hyperliquid API key and address")
    print("="*60)
    
    return 0 if all(tests) else 1


if __name__ == "__main__":
    sys.exit(main())