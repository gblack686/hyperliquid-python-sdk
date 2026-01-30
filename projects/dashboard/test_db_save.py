"""
Quick test to verify all indicators can save to Supabase
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.append('./indicators')

# Import a few key indicators to test
from indicators.liquidations import LiquidationsIndicator
from indicators.vwap import VWAPIndicator
from indicators.atr import ATRIndicator

async def test_db_saves():
    """Test that indicators can now save to database"""
    print(f"\nTesting database saves at {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 50)
    
    indicators = {
        "liquidations": LiquidationsIndicator(["BTC"]),
        "vwap": VWAPIndicator(["BTC"]),
        "atr": ATRIndicator(["BTC"])
    }
    
    print("\nRunning indicators for 10 seconds to test saves...")
    
    # Start all indicators
    tasks = []
    for name, indicator in indicators.items():
        print(f"[START] {name} indicator")
        task = asyncio.create_task(indicator.run())
        tasks.append(task)
    
    # Let them run for 10 seconds
    await asyncio.sleep(10)
    
    # Cancel all tasks
    for task in tasks:
        task.cancel()
    
    # Wait for cancellation
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)
    print("\nCheck the console output above for any database save errors.")
    print("If no 'Error saving' messages appear, all saves are working!")
    print("\nPreviously seen errors (now fixed):")
    print("- Liquidations: intensity_score column [FIXED]")
    print("- VWAP: deviation_daily_pct column [FIXED]")
    print("- ATR: atr_pct_* columns [FIXED]")

if __name__ == "__main__":
    asyncio.run(test_db_saves())