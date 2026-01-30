"""
Test the indicator manager with all indicators including CVD
"""

import asyncio
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add path for indicators
sys.path.append('./indicators')

load_dotenv()

async def test_indicator_manager():
    """Test the indicator manager"""
    
    print("=" * 70)
    print("INDICATOR MANAGER TEST")
    print("=" * 70)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Import indicator manager
    from indicator_manager import IndicatorManager
    
    # Test with all indicators
    symbols = ['BTC', 'ETH', 'SOL', 'HYPE']
    indicators = ['cvd', 'open_interest', 'funding_rate', 'vwap', 'bollinger', 'volume_profile', 'atr', 'liquidations']
    
    print(f"\nTesting with symbols: {', '.join(symbols)}")
    print(f"Testing indicators: {', '.join(indicators)}")
    print("-" * 70)
    
    try:
        # Create manager
        manager = IndicatorManager(symbols=symbols, indicators=indicators)
        print("[OK] Indicator Manager created")
        
        # Run startup tests
        print("\nRunning startup tests...")
        test_result = await manager.run_startup_tests()
        
        if test_result:
            print("[OK] All startup tests passed")
        else:
            print("[WARNING] Some startup tests failed, continuing anyway...")
        
        # Get initial status
        status = manager.status()
        print(f"\n[OK] Initial status retrieved")
        print(f"    Active indicators: {len(status.get('indicators', {}))}")
        
        # Run for a short time to test
        print("\nRunning indicators for 30 seconds...")
        print("(Press Ctrl+C to stop early)")
        
        # Create task and run for limited time
        task = asyncio.create_task(manager.run())
        
        try:
            await asyncio.wait_for(task, timeout=30)
        except asyncio.TimeoutError:
            print("\n[OK] 30 second test completed")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Get final status
        final_status = manager.status()
        print(f"\n[OK] Final status retrieved")
        print(f"    Active indicators: {len(final_status.get('indicators', {}))}")
        
        # Show sample values
        print("\nSample indicator values:")
        print("-" * 50)
        for indicator_name, values in final_status.get('indicators', {}).items():
            print(f"\n{indicator_name.upper()}:")
            for symbol, value in values.items():
                if value:
                    print(f"  {symbol}: {value}")
        
        print("\n" + "=" * 70)
        print("INDICATOR MANAGER TEST COMPLETE")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_indicator_manager())
    sys.exit(0 if result else 1)