"""Test Open Interest fetching"""
import os
import sys
sys.path.append('..')  # Add parent directory to path
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

def test_oi():
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    
    print("Testing Open Interest fetch...")
    
    # Method 1: meta_and_asset_ctxs
    try:
        meta_and_state = info.meta_and_asset_ctxs()
        print(f"\nResponse type: {type(meta_and_state)}")
        print(f"Response length: {len(meta_and_state) if hasattr(meta_and_state, '__len__') else 'N/A'}")
        
        if isinstance(meta_and_state, tuple) and len(meta_and_state) >= 2:
            meta = meta_and_state[0]
            ctxs = meta_and_state[1]
            print(f"Meta type: {type(meta)}, Ctxs type: {type(ctxs)}")
            
            # If meta is a list of dicts
            if isinstance(meta, list):
                print(f"Found {len(meta)} assets")
                for i, asset in enumerate(meta[:5]):  # Check first 5
                    if isinstance(asset, dict):
                        coin = asset.get('coin', '')
                        print(f"  Asset {i}: {coin} - keys: {list(asset.keys())[:5]}")
                    else:
                        print(f"  Asset {i}: type={type(asset)}")
        else:
            print(f"Unexpected response format: {meta_and_state[:200] if str(meta_and_state) else 'empty'}")
            
    except Exception as e:
        print(f"Error with meta_and_asset_ctxs: {e}")
        import traceback
        traceback.print_exc()
    
    # Method 2: Try open_interest endpoint directly
    print("\n" + "="*50)
    print("Testing alternate methods...")
    
    try:
        # Try getting all open positions
        positions = info.all_mids()
        print(f"Got {len(positions)} mid prices")
        
        # Look for OI in metadata
        for symbol in ['BTC', 'ETH']:
            if symbol in positions:
                print(f"{symbol} mid price: ${positions[symbol]:,.2f}")
    except Exception as e:
        print(f"Error with mids: {e}")

if __name__ == "__main__":
    test_oi()