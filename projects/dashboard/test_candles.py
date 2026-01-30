#!/usr/bin/env python
"""Test Hyperliquid candles API"""

import sys
import time

# Try to import hyperliquid
sys.path.append('..')
from hyperliquid.info import Info
from hyperliquid.utils import constants

def test_candles():
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    
    # Test different coin names
    symbols = ['BTC', 'ETH', 'SOL', 'BTC-1228', 'ETH-1228']
    
    for symbol in symbols:
        print(f"\nTesting {symbol}:")
        try:
            # Try with current timestamp
            end_time = int(time.time() * 1000)
            start_time = end_time - (60 * 60 * 1000)  # 1 hour ago
            
            print(f"  Using timestamps: start={start_time}, end={end_time}")
            print(f"  Current time: {time.time()}")
            
            candles = info.candles_snapshot(
                symbol,  
                '5m', 
                start_time,
                end_time
            )
            
            if candles:
                print(f"  SUCCESS: Got {len(candles)} candles")
                if candles:
                    print(f"  Sample: {candles[0]}")
            else:
                print(f"  EMPTY: No candles returned")
                
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # Also test what coins are available
    print("\n\nAvailable coins from meta:")
    try:
        meta = info.meta()
        universe = meta.get('universe', [])
        
        # Find BTC, ETH, SOL variants
        relevant_coins = []
        for asset in universe[:50]:  # Check first 50
            name = asset.get('name', '')
            if any(x in name for x in ['BTC', 'ETH', 'SOL', 'HYPE']):
                relevant_coins.append(name)
        
        print(f"Found: {relevant_coins}")
        
    except Exception as e:
        print(f"Error getting meta: {e}")

if __name__ == "__main__":
    test_candles()