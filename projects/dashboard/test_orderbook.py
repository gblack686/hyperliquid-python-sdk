#!/usr/bin/env python
"""Test Order Book API"""

import sys
import json
sys.path.append('..')
from hyperliquid.info import Info
from hyperliquid.utils import constants

def test_orderbook():
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    
    symbol = 'BTC'
    print(f"Testing order book for {symbol}:")
    
    try:
        book = info.l2_snapshot(symbol)
        
        print(f"\nBook type: {type(book)}")
        print(f"Book keys: {book.keys() if isinstance(book, dict) else 'not a dict'}")
        
        if book and 'levels' in book:
            print(f"\nLevels type: {type(book['levels'])}")
            print(f"Levels length: {len(book['levels'])}")
            
            if len(book['levels']) > 0:
                print(f"\nFirst level type: {type(book['levels'][0])}")
                print(f"First level length: {len(book['levels'][0])} items")
                
                if book['levels'][0]:
                    print(f"\nFirst bid: {book['levels'][0][0]}")
                    print(f"First bid type: {type(book['levels'][0][0])}")
                    
                if len(book['levels']) > 1 and book['levels'][1]:
                    print(f"\nFirst ask: {book['levels'][1][0]}")
                    print(f"First ask type: {type(book['levels'][1][0])}")
        
        # Save full book for inspection
        with open('orderbook_sample.json', 'w') as f:
            json.dump(book, f, indent=2)
        print("\nFull order book saved to orderbook_sample.json")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_orderbook()