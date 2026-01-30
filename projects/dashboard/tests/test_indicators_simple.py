"""
Simple test for all indicators - just tests that they can initialize and run
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import os

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.append('./indicators')

# Import indicators
try:
    from indicators.open_interest import OpenInterestIndicator
    from indicators.funding_rate import FundingRateIndicator
    from indicators.liquidations import LiquidationsIndicator
    from indicators.bollinger_bands import BollingerBandsIndicator
    from indicators.vwap import VWAPIndicator
    from indicators.atr import ATRIndicator
    from indicators.orderbook_imbalance import OrderBookImbalanceIndicator
    from indicators.support_resistance import SupportResistanceIndicator
    from indicators.volume_profile import VolumeProfileIndicator
    from indicators.basis_premium import BasisPremiumIndicator
    from indicators.mtf_aggregator import MTFAggregatorIndicator
    print("[OK] All indicator imports successful")
except ImportError as e:
    print(f"[FAIL] Import error: {e}")
    sys.exit(1)

# Test configuration
TEST_SYMBOLS = ["BTC", "ETH"]


async def test_indicators():
    """Test all indicators"""
    print("\n" + "="*70)
    print(" "*20 + "INDICATOR TESTING")
    print("="*70)
    
    indicators = {
        "open_interest": OpenInterestIndicator(TEST_SYMBOLS),
        "funding_rate": FundingRateIndicator(TEST_SYMBOLS),
        "liquidations": LiquidationsIndicator(TEST_SYMBOLS),
        "bollinger": BollingerBandsIndicator(TEST_SYMBOLS),
        "vwap": VWAPIndicator(TEST_SYMBOLS),
        "atr": ATRIndicator(TEST_SYMBOLS),
        "orderbook": OrderBookImbalanceIndicator(TEST_SYMBOLS),
        "support_resistance": SupportResistanceIndicator(TEST_SYMBOLS),
        "volume_profile": VolumeProfileIndicator(TEST_SYMBOLS),
        "basis_premium": BasisPremiumIndicator(TEST_SYMBOLS),
        "mtf_aggregator": MTFAggregatorIndicator(TEST_SYMBOLS)
    }
    
    print(f"\n[OK] Initialized {len(indicators)} indicators")
    
    # Test each indicator can run (even if just once)
    print("\nTesting indicator execution (5 second test):")
    print("-" * 40)
    
    passed = 0
    failed = 0
    
    for name, indicator in indicators.items():
        try:
            # Create a task that runs for 5 seconds
            task = asyncio.create_task(indicator.run())
            await asyncio.sleep(5)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
                
            print(f"[OK] {name}: Running successfully")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: Failed - {e}")
            failed += 1
    
    # Summary
    print("\n" + "="*70)
    print(" "*25 + "SUMMARY")
    print("="*70)
    print(f"Total indicators: {len(indicators)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(passed / len(indicators) * 100):.1f}%")
    
    if failed == 0:
        print("\n[OK] ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n[FAIL] {failed} TESTS FAILED")
        return 1


async def main():
    """Main test runner"""
    try:
        print(f"Starting tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check for required env vars
        if not os.getenv('SUPABASE_URL'):
            print("[WARN] Warning: SUPABASE_URL not set")
        if not os.getenv('SUPABASE_SERVICE_KEY'):
            print("[WARN] Warning: SUPABASE_SERVICE_KEY not set")
            
        exit_code = await test_indicators()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())