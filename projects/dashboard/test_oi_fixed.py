"""Test Open Interest fetching with correct parsing"""
import os
import sys
sys.path.append('..')
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

def test_oi():
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    
    print("Testing Open Interest fetch...")
    
    try:
        # Get metadata and asset contexts
        response = info.meta_and_asset_ctxs()
        
        if isinstance(response, list) and len(response) == 2:
            meta = response[0]
            ctxs = response[1]
            
            # The universe is in meta['universe']
            universe = meta.get('universe', [])
            
            print(f"\nFound {len(universe)} assets")
            print(f"Found {len(ctxs)} contexts")
            
            # Map symbols we care about
            symbols = ['BTC', 'ETH', 'SOL', 'HYPE']
            
            for i, asset_meta in enumerate(universe):
                coin = asset_meta.get('name', '')
                if coin in symbols and i < len(ctxs):
                    ctx = ctxs[i]
                    
                    # Extract data from context
                    oi = float(ctx.get('openInterest', 0))
                    funding = float(ctx.get('funding', 0)) * 10000  # Convert to basis points
                    mark_px = float(ctx.get('markPx', 0))
                    volume = float(ctx.get('dayNtlVlm', 0))
                    
                    print(f"\n{coin}:")
                    print(f"  Open Interest: ${oi:,.0f}")
                    print(f"  OI (USD millions): ${oi * mark_px / 1_000_000:.2f}M")
                    print(f"  Funding Rate: {funding:.4f} bp")
                    print(f"  Mark Price: ${mark_px:,.2f}")
                    print(f"  24h Volume: ${volume:,.0f}")
                    
        else:
            print(f"Unexpected response format")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_oi()