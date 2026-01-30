#!/usr/bin/env python
"""Test the app's main components without running Streamlit."""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_components():
    """Test main components of the app."""
    
    print("Testing imports...")
    try:
        from src.hyperliquid_client import HyperliquidClient
        from src.data.supabase_manager import SupabaseManager
        from src.confluence.aggregator import ConfluenceAggregator
        print("[OK] All main imports successful")
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        return False
    
    print("\nTesting HyperliquidClient initialization...")
    try:
        client = HyperliquidClient()
        print("[OK] HyperliquidClient initialized")
    except Exception as e:
        print(f"[ERROR] HyperliquidClient initialization failed: {e}")
        return False
    
    print("\nTesting SupabaseManager initialization...")
    try:
        # Check if .env file exists and has credentials
        from dotenv import load_dotenv
        load_dotenv()
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("[WARNING] Supabase credentials not found in .env file")
            print("         Please update .env with your Supabase URL and key")
        else:
            manager = SupabaseManager()
            print("[OK] SupabaseManager initialized")
    except Exception as e:
        print(f"[WARNING] SupabaseManager initialization failed: {e}")
        print("         This is expected if Supabase is not configured")
    
    print("\nTesting ConfluenceAggregator initialization...")
    try:
        aggregator = ConfluenceAggregator()
        print("[OK] ConfluenceAggregator initialized")
    except Exception as e:
        print(f"[ERROR] ConfluenceAggregator initialization failed: {e}")
        return False
    
    print("\nTesting indicator imports...")
    indicators_to_test = [
        "volume_spike.VolumeSpike",
        "ma_crossover.MACrossover",
        "rsi_mtf.RSIMultiTimeframe",
        "bollinger.BollingerBands",
        "macd.MACD",
        "stochastic.StochasticOscillator",
        "support_resistance.SupportResistance",
        "atr.ATRVolatility",
        "vwap.VWAP",
        "divergence.PriceDivergence"
    ]
    
    failed_indicators = []
    for indicator in indicators_to_test:
        module_name, class_name = indicator.rsplit('.', 1)
        try:
            module = __import__(f"src.indicators.{module_name}", fromlist=[class_name])
            getattr(module, class_name)
            print(f"[OK] {indicator}")
        except Exception as e:
            failed_indicators.append((indicator, str(e)))
            print(f"[ERROR] {indicator}: {e}")
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    if failed_indicators:
        print(f"Failed indicators: {len(failed_indicators)}")
        for indicator, error in failed_indicators:
            print(f"  - {indicator}: {error}")
    else:
        print("All components tested successfully!")
        print("\nNext steps:")
        print("1. Update .env file with your Supabase credentials")
        print("2. Run: streamlit run app.py")
        print("3. The dashboard should open in your browser")
    
    return len(failed_indicators) == 0

if __name__ == "__main__":
    success = asyncio.run(test_components())
    sys.exit(0 if success else 1)