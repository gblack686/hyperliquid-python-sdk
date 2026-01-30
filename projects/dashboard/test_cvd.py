"""
Test CVD indicator standalone
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append('.')
from indicators.cvd import CVDIndicator

load_dotenv()

async def test_cvd():
    """Test CVD indicator"""
    print("=" * 70)
    print("TESTING CVD INDICATOR")
    print("=" * 70)
    
    # Create CVD indicator with multiple symbols
    cvd = CVDIndicator(symbols=['BTC', 'ETH', 'HYPE'])
    
    print("\n[1] Connecting to WebSocket...")
    connected = await cvd.connect_websocket()
    
    if not connected:
        print("[ERROR] Failed to connect to WebSocket")
        return
    
    print("[OK] WebSocket connected")
    
    # Run for 30 seconds
    print("\n[2] Collecting trade data for 30 seconds...")
    cvd.running = True
    
    # Start processing in background
    update_task = asyncio.create_task(cvd.update())
    
    # Let it run for a bit
    for i in range(6):
        await asyncio.sleep(5)
        
        # Print status
        print(f"\n[{i+1}/6] Status at {i*5+5} seconds:")
        for symbol in cvd.symbols:
            stats = cvd.stats[symbol]
            print(f"  {symbol}: Trades={stats['total_trades']}, Buy={stats['buy_trades']}, Sell={stats['sell_trades']}, CVD={cvd.cvd[symbol]:.2f}")
    
    # Save to Supabase
    print("\n[3] Saving to Supabase...")
    await cvd.save_to_supabase()
    
    # Stop
    cvd.running = False
    update_task.cancel()
    
    print("\n[4] Test complete!")
    
    # Show final metrics
    print("\n[5] Final metrics:")
    for symbol in cvd.symbols:
        metrics = cvd.calculate_cvd_metrics(symbol)
        print(f"\n{symbol} Metrics:")
        print(f"  CVD: {metrics['cvd']:.2f}")
        print(f"  Buy Volume: {metrics['buy_volume']:.2f}")
        print(f"  Sell Volume: {metrics['sell_volume']:.2f}")
        print(f"  Buy Ratio: {metrics['buy_ratio']:.2%}")
        print(f"  Signal: {metrics['signal']}")
        print(f"  Total Trades: {metrics['total_trades']}")

if __name__ == "__main__":
    asyncio.run(test_cvd())