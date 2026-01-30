"""
Quick test of CVD with Supabase upload
"""
import asyncio
from cvd_supabase_integration import CVDSupabaseCalculator
import signal
import sys

async def test_cvd(duration=15):
    calculator = CVDSupabaseCalculator(symbols=['BTC', 'ETH', 'SOL'])
    
    # Run for specified duration
    task = asyncio.create_task(calculator.run())
    
    await asyncio.sleep(duration)
    
    # Stop the calculator
    calculator.running = False
    
    # Give it time to save final data
    await asyncio.sleep(2)
    
    print("\n[TEST] CVD Calculator test complete")
    print("[TEST] Check Supabase tables for data")
    
    # Cancel the task
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    return True

if __name__ == "__main__":
    print("Testing CVD Calculator with Supabase (15 seconds)...")
    asyncio.run(test_cvd(15))