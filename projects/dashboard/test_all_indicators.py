#!/usr/bin/env python
"""Test all indicators to ensure they work properly"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Add indicators to path
sys.path.append('./indicators')
sys.path.append('..')

# Import all indicators
from indicators.open_interest import OpenInterestIndicator
from indicators.funding_rate import FundingRateIndicator
from indicators.liquidations import LiquidationsIndicator
from indicators.orderbook_imbalance import OrderBookImbalanceIndicator
from indicators.vwap import VWAPIndicator
from indicators.atr import ATRIndicator
from indicators.bollinger_bands import BollingerBandsIndicator
from indicators.support_resistance import SupportResistanceIndicator

load_dotenv()

async def test_indicator(indicator_class, name, symbols=['BTC', 'ETH'], iterations=2):
    """Test a single indicator"""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")
    
    try:
        # Initialize
        indicator = indicator_class(symbols)
        print(f"✓ Initialized {name}")
        
        # Test update method
        for i in range(iterations):
            print(f"\nIteration {i+1}/{iterations}:")
            await indicator.update()
            print(f"✓ Update completed")
            
            # Test metrics calculation
            for symbol in symbols:
                if hasattr(indicator, 'calculate_oi_metrics'):
                    metrics = indicator.calculate_oi_metrics(symbol)
                elif hasattr(indicator, 'calculate_funding_metrics'):
                    metrics = indicator.calculate_funding_metrics(symbol)
                elif hasattr(indicator, 'calculate_liquidation_metrics'):
                    metrics = indicator.calculate_liquidation_metrics(symbol)
                elif hasattr(indicator, 'calculate_orderbook_metrics'):
                    metrics = indicator.calculate_orderbook_metrics(symbol)
                elif hasattr(indicator, 'calculate_vwap_metrics'):
                    metrics = indicator.calculate_vwap_metrics(symbol)
                elif hasattr(indicator, 'calculate_atr_metrics'):
                    metrics = indicator.calculate_atr_metrics(symbol)
                elif hasattr(indicator, 'calculate_bb_metrics'):
                    metrics = indicator.calculate_bb_metrics(symbol)
                elif hasattr(indicator, 'calculate_sr_metrics'):
                    metrics = indicator.calculate_sr_metrics(symbol)
                else:
                    metrics = {'symbol': symbol, 'status': 'no metrics method'}
                
                # Print key metrics
                print(f"  {symbol}: {metrics.get('symbol', 'N/A')}")
                for key, value in list(metrics.items())[:3]:
                    if key != 'symbol':
                        print(f"    {key}: {value}")
            
            # Small delay between iterations
            if i < iterations - 1:
                await asyncio.sleep(2)
        
        print(f"\n✓ {name} test PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ {name} test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all indicator tests"""
    print("HYPERLIQUID INDICATORS TEST SUITE")
    print("="*60)
    
    # Test configuration
    symbols = ['BTC', 'ETH']
    iterations = 1
    
    # List of indicators to test
    indicators_to_test = [
        (OpenInterestIndicator, "Open Interest"),
        (FundingRateIndicator, "Funding Rate"),
        (LiquidationsIndicator, "Liquidations"),
        (OrderBookImbalanceIndicator, "Order Book Imbalance"),
        (VWAPIndicator, "VWAP"),
        (ATRIndicator, "ATR"),
        (BollingerBandsIndicator, "Bollinger Bands"),
        (SupportResistanceIndicator, "Support/Resistance"),
    ]
    
    # Track results
    results = {}
    
    # Test each indicator
    for indicator_class, name in indicators_to_test:
        success = await test_indicator(indicator_class, name, symbols, iterations)
        results[name] = success
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed
    
    for name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    # Return overall success
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)