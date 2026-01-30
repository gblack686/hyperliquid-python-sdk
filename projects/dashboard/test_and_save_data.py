#!/usr/bin/env python
"""Test data fetching and save sample data to JSON for debugging."""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Add src to path
sys.path.append('src')

# Load environment variables
load_dotenv()

from src.hyperliquid_client import HyperliquidClient
from loguru import logger

async def test_data_fetching():
    """Test all data fetching methods and save sample data."""
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("HYPERLIQUID DATA FETCHING TEST")
    print("=" * 60)
    
    # Initialize client
    api_key = os.getenv('HYPERLIQUID_API_KEY')
    if not api_key:
        print("ERROR: HYPERLIQUID_API_KEY not found in environment")
        return False
    
    print(f"\nAPI Key (masked): {api_key[:10]}...{api_key[-4:]}")
    
    client = HyperliquidClient(key=api_key, mode="mainnet")
    
    # Test connection
    print("\n1. Testing connection...")
    connected = await client.connect()
    if not connected:
        print("   FAILED: Could not connect to Hyperliquid")
        return False
    print("   SUCCESS: Connected to Hyperliquid")
    
    # Test get_all_mids
    print("\n2. Testing get_all_mids()...")
    mids = await client.get_all_mids()
    if mids:
        print(f"   SUCCESS: Got {len(mids)} mid prices")
        print(f"   BTC Price: ${mids.get('BTC', 'N/A')}")
        print(f"   ETH Price: ${mids.get('ETH', 'N/A')}")
        
        # Save sample data (convert Decimal to str for JSON)
        mids_json = {k: str(v) for k, v in mids.items()}
        with open(data_dir / "sample_mids.json", "w") as f:
            json.dump(mids_json, f, indent=2)
        print(f"   Saved to: data/sample_mids.json")
    else:
        print("   FAILED: No mid prices returned")
    
    # Test get_historical_candles
    print("\n3. Testing get_historical_candles()...")
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (24 * 60 * 60 * 1000)  # 24 hours ago
    
    candles = await client.get_historical_candles(
        ticker='BTC',
        interval='15m',
        start=start_time,
        end=end_time
    )
    
    if candles:
        print(f"   SUCCESS: Got {len(candles)} candles")
        print(f"   First candle: {candles[0] if candles else 'None'}")
        
        # Save sample data
        with open(data_dir / "sample_candles.json", "w") as f:
            json.dump(candles, f, indent=2)
        print(f"   Saved to: data/sample_candles.json")
        
        # Test DataFrame conversion (like app.py does)
        print("\n   Testing DataFrame conversion...")
        try:
            df = pd.DataFrame(candles)
            print(f"   Original columns: {list(df.columns)}")
            
            # Map columns based on what we see
            if 't' in df.columns:
                # Quantpylib format
                df = df.rename(columns={
                    't': 'timestamp',
                    'o': 'open',
                    'h': 'high',
                    'l': 'low',
                    'c': 'close',
                    'v': 'volume'
                })
            
            # Required columns for the app
            required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                print(f"   WARNING: Missing columns after rename: {missing_cols}")
            else:
                print(f"   SUCCESS: All required columns present")
                
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            print(f"   DataFrame shape: {df.shape}")
            print(f"   Latest price: {df['close'].iloc[-1] if not df.empty else 'N/A'}")
            
            # Save processed DataFrame
            df.to_csv(data_dir / "sample_candles_df.csv")
            print(f"   Saved processed data to: data/sample_candles_df.csv")
            
        except Exception as e:
            print(f"   ERROR converting to DataFrame: {e}")
    else:
        print("   FAILED: No candles returned")
    
    # Test get_trade_bars
    print("\n4. Testing get_trade_bars()...")
    end = datetime.now()
    start = end - timedelta(hours=2)
    
    from quantpylib.standards import Period
    
    bars = await client.get_trade_bars(
        ticker='BTC',
        start=start,
        end=end,
        granularity=Period.MINUTE,
        granularity_multiplier=15
    )
    
    if bars is not None:
        print(f"   SUCCESS: Got trade bars DataFrame")
        print(f"   Shape: {bars.shape}")
        print(f"   Columns: {list(bars.columns)}")
        if not bars.empty:
            print(f"   Latest close: ${bars['close'].iloc[-1]}")
            
            # Save sample data
            bars.to_csv(data_dir / "sample_trade_bars.csv")
            print(f"   Saved to: data/sample_trade_bars.csv")
    else:
        print("   FAILED: No trade bars returned")
    
    # Test L2 book
    print("\n5. Testing get_l2_book()...")
    book = await client.get_l2_book('BTC')
    if book:
        print(f"   SUCCESS: Got L2 book data")
        
        # Save sample data (handle numpy arrays and other non-serializable types)
        try:
            # Convert numpy arrays to lists for JSON serialization
            import numpy as np
            
            def convert_to_serializable(obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, (np.integer, np.floating)):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: convert_to_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_to_serializable(item) for item in obj]
                else:
                    return obj
            
            book_serializable = convert_to_serializable(book)
            with open(data_dir / "sample_l2_book.json", "w") as f:
                json.dump(book_serializable, f, indent=2)
            print(f"   Saved to: data/sample_l2_book.json")
        except Exception as e:
            print(f"   WARNING: Could not save L2 book to JSON: {e}")
            # Save as string representation instead
            with open(data_dir / "sample_l2_book.txt", "w") as f:
                f.write(str(book))
            print(f"   Saved string representation to: data/sample_l2_book.txt")
    else:
        print("   FAILED: No L2 book returned")
    
    # Test account balance (if authenticated)
    print("\n6. Testing get_account_balance()...")
    balance = await client.get_account_balance()
    if balance:
        print(f"   SUCCESS: Got account balance")
        print(f"   Keys in response: {list(balance.keys())}")
        
        # Save sample structure (mask sensitive data)
        sample_balance = {k: "***" if isinstance(v, (int, float)) else type(v).__name__ 
                         for k, v in balance.items()}
        with open(data_dir / "sample_balance_structure.json", "w") as f:
            json.dump(sample_balance, f, indent=2)
        print(f"   Saved structure to: data/sample_balance_structure.json")
    else:
        print("   INFO: No account balance (may need authentication)")
    
    # Clean up
    await client.cleanup()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("Sample data saved in 'data/' directory")
    print("=" * 60)
    
    return True

async def test_fetch_market_data_function():
    """Test the exact fetch_market_data function from app.py"""
    print("\n" + "=" * 60)
    print("TESTING APP'S fetch_market_data FUNCTION")
    print("=" * 60)
    
    api_key = os.getenv('HYPERLIQUID_API_KEY')
    client = HyperliquidClient(key=api_key, mode="mainnet")
    
    connected = await client.connect()
    if not connected:
        print("Failed to connect")
        return None
        
    symbol = "BTC"
    timeframe = "15m"
    
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (24 * 60 * 60 * 1000)
    
    print(f"\nFetching {symbol} {timeframe} candles...")
    print(f"Start: {datetime.fromtimestamp(start_time/1000)}")
    print(f"End: {datetime.fromtimestamp(end_time/1000)}")
    
    candles = await client.get_historical_candles(
        ticker=symbol,
        interval=timeframe,
        start=start_time,
        end=end_time
    )
    
    if candles:
        print(f"\nGot {len(candles)} candles")
        print(f"First candle keys: {list(candles[0].keys())}")
        
        df = pd.DataFrame(candles)
        print(f"\nDataFrame columns before rename: {list(df.columns)}")
        
        # This is what app.py tries to do - it will fail if columns don't match
        try:
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            print("ERROR: Column assignment would fail - wrong number of columns!")
        except ValueError as e:
            print(f"Column assignment error (expected): {e}")
            
            # Fix: Map the actual columns
            if 't' in df.columns:
                df = df.rename(columns={
                    't': 'timestamp',
                    'o': 'open',
                    'h': 'high',
                    'l': 'low',
                    'c': 'close',
                    'v': 'volume'
                })
                # Drop extra columns
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        print(f"\nFinal DataFrame shape: {df.shape}")
        print(f"Final columns: {list(df.columns)}")
        print(f"Sample data:\n{df.head()}")
        
        return df
    else:
        print("No candles returned!")
        return None
    
    await client.cleanup()

if __name__ == "__main__":
    # Run tests
    asyncio.run(test_data_fetching())
    
    # Test the app's specific function
    asyncio.run(test_fetch_market_data_function())