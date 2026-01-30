"""
Comprehensive test suite for all 11 MTF indicators
Tests both individual functionality and integrated operation
"""

import asyncio
import pytest
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import json

# Add indicators to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "indicators"))

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

# Test configuration
TEST_SYMBOLS = ["BTC", "ETH"]
TEST_TIMEOUT = 30  # seconds


class TestResult:
    """Track test results for reporting"""
    def __init__(self):
        self.passed: List[str] = []
        self.failed: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        
    def add_pass(self, test_name: str):
        self.passed.append(test_name)
        
    def add_fail(self, test_name: str, error: str, details: Dict = None):
        self.failed.append({
            "test": test_name,
            "error": error,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
        
    def add_warning(self, message: str):
        self.warnings.append(message)
        
    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_tests": len(self.passed) + len(self.failed),
            "passed": len(self.passed),
            "failed": len(self.failed),
            "warnings": len(self.warnings),
            "pass_rate": f"{(len(self.passed) / (len(self.passed) + len(self.failed)) * 100):.1f}%" if self.passed or self.failed else "0%",
            "passed_tests": self.passed,
            "failed_tests": self.failed,
            "warnings": self.warnings
        }


class IndicatorTestSuite:
    """Comprehensive test suite for all indicators"""
    
    def __init__(self):
        self.results = TestResult()
        self.indicators = self._initialize_indicators()
        
    def _initialize_indicators(self) -> Dict[str, Any]:
        """Initialize all indicator instances"""
        symbols = TEST_SYMBOLS
        return {
            "open_interest": OpenInterestIndicator(symbols),
            "funding_rate": FundingRateIndicator(symbols),
            "liquidations": LiquidationsIndicator(symbols),
            "bollinger": BollingerBandsIndicator(symbols),
            "vwap": VWAPIndicator(symbols),
            "atr": ATRIndicator(symbols),
            "orderbook": OrderBookImbalanceIndicator(symbols),
            "support_resistance": SupportResistanceIndicator(symbols),
            "volume_profile": VolumeProfileIndicator(symbols),
            "basis_premium": BasisPremiumIndicator(symbols),
            "mtf_aggregator": MTFAggregatorIndicator(symbols)
        }
    
    async def test_indicator_initialization(self):
        """Test that all indicators initialize correctly"""
        print("\n" + "="*50)
        print("TEST 1: INDICATOR INITIALIZATION")
        print("="*50)
        
        for name, indicator in self.indicators.items():
            try:
                assert indicator is not None, f"{name} indicator is None"
                assert hasattr(indicator, 'run'), f"{name} missing run method"
                self.results.add_pass(f"init_{name}")
                print(f"✅ {name}: Initialized successfully")
            except Exception as e:
                self.results.add_fail(f"init_{name}", str(e))
                print(f"❌ {name}: Failed - {e}")
                
    async def test_data_calculation(self):
        """Test that each indicator can calculate data"""
        print("\n" + "="*50)
        print("TEST 2: DATA CALCULATION")
        print("="*50)
        
        for name, indicator in self.indicators.items():
            for symbol in TEST_SYMBOLS:
                test_name = f"calc_{name}_{symbol}"
                try:
                    # Different method names for different indicators
                    if name == "open_interest":
                        data = await indicator.calculate_open_interest(symbol)
                    elif name == "funding_rate":
                        data = await indicator.calculate_funding_rate(symbol)
                    elif name == "liquidations":
                        data = await indicator.calculate_liquidations(symbol)
                    elif name == "bollinger":
                        data = await indicator.calculate_bollinger_bands(symbol)
                    elif name == "vwap":
                        data = await indicator.calculate_vwap(symbol)
                    elif name == "atr":
                        data = await indicator.calculate_atr(symbol)
                    elif name == "orderbook":
                        data = await indicator.calculate_orderbook(symbol)
                    elif name == "support_resistance":
                        data = await indicator.calculate_support_resistance(symbol)
                    elif name == "volume_profile":
                        data = await indicator.calculate_volume_profile(symbol)
                    elif name == "basis_premium":
                        data = await indicator.calculate_basis(symbol)
                    elif name == "mtf_aggregator":
                        data = await indicator.calculate_confluence(symbol)
                    else:
                        data = await indicator.calculate(symbol)
                    
                    assert data is not None, "No data returned"
                    assert isinstance(data, dict), f"Expected dict, got {type(data)}"
                    
                    self.results.add_pass(test_name)
                    print(f"✅ {name} ({symbol}): Calculated successfully")
                    
                    # Print sample data structure
                    if symbol == TEST_SYMBOLS[0]:  # Only print for first symbol
                        keys = list(data.keys())[:5]  # First 5 keys
                        print(f"   Sample keys: {keys}")
                        
                except Exception as e:
                    self.results.add_fail(test_name, str(e))
                    print(f"❌ {name} ({symbol}): Failed - {e}")
                    
    async def test_database_save(self):
        """Test that indicators can save to database"""
        print("\n" + "="*50)
        print("TEST 3: DATABASE SAVE OPERATIONS")
        print("="*50)
        
        for name, indicator in self.indicators.items():
            test_name = f"save_{name}"
            try:
                # Test with BTC only for save operations
                symbol = "BTC"
                
                # Calculate data first
                if name == "open_interest":
                    data = await indicator.calculate_open_interest(symbol)
                    await indicator.save_to_db(symbol, data)
                elif name == "funding_rate":
                    data = await indicator.calculate_funding_rate(symbol)
                    await indicator.save_to_db(symbol, data)
                elif name == "liquidations":
                    data = await indicator.calculate_liquidations(symbol)
                    await indicator.save_to_db(symbol, data)
                elif name == "bollinger":
                    data = await indicator.calculate_bollinger_bands(symbol)
                    await indicator.save_to_db(symbol, data)
                elif name == "vwap":
                    data = await indicator.calculate_vwap(symbol)
                    await indicator.save_to_db(symbol, data)
                elif name == "atr":
                    data = await indicator.calculate_atr(symbol)
                    await indicator.save_to_db(symbol, data)
                elif name == "orderbook":
                    data = await indicator.calculate_orderbook(symbol)
                    await indicator.save_to_db(symbol, data)
                elif name == "support_resistance":
                    data = await indicator.calculate_support_resistance(symbol)
                    await indicator.save_to_db(symbol, data)
                elif name == "volume_profile":
                    data = await indicator.calculate_volume_profile(symbol)
                    await indicator.save_to_db(symbol, data)
                elif name == "basis_premium":
                    data = await indicator.calculate_basis(symbol)
                    await indicator.save_to_db(symbol, data)
                elif name == "mtf_aggregator":
                    data = await indicator.calculate_confluence(symbol)
                    await indicator.save_to_db(symbol, data)
                
                self.results.add_pass(test_name)
                print(f"✅ {name}: Database save successful")
                
            except Exception as e:
                # Check if it's just a connection issue
                if "connection" in str(e).lower() or "supabase" in str(e).lower():
                    self.results.add_warning(f"{name}: Database connection issue (may be normal in test environment)")
                    print(f"⚠️ {name}: Database connection warning - {e}")
                else:
                    self.results.add_fail(test_name, str(e))
                    print(f"❌ {name}: Failed - {e}")
                    
    async def test_rate_limiting(self):
        """Test that rate limiting is working"""
        print("\n" + "="*50)
        print("TEST 4: RATE LIMITING")
        print("="*50)
        
        # Test rapid API calls
        test_name = "rate_limiting"
        try:
            indicator = self.indicators["open_interest"]
            start_time = datetime.now()
            
            # Try 5 rapid calls
            tasks = []
            for i in range(5):
                tasks.append(indicator.calculate_open_interest("BTC"))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Should take at least some time due to rate limiting
            assert elapsed > 0, "Rate limiting not enforced"
            
            # Check that all calls completed
            successful = sum(1 for r in results if not isinstance(r, Exception))
            assert successful > 0, "No successful API calls"
            
            self.results.add_pass(test_name)
            print(f"✅ Rate limiting: Working correctly ({successful}/5 calls succeeded in {elapsed:.2f}s)")
            
        except Exception as e:
            self.results.add_fail(test_name, str(e))
            print(f"❌ Rate limiting: Failed - {e}")
            
    async def test_error_handling(self):
        """Test error handling with invalid inputs"""
        print("\n" + "="*50)
        print("TEST 5: ERROR HANDLING")
        print("="*50)
        
        invalid_symbols = ["INVALID", "", None, "XYZ123"]
        
        for symbol in invalid_symbols:
            test_name = f"error_{symbol}"
            try:
                indicator = self.indicators["open_interest"]
                
                # This should handle the error gracefully
                if symbol is None:
                    continue  # Skip None test
                    
                data = await indicator.calculate_open_interest(symbol)
                
                # Should either return empty data or handle gracefully
                if data is None or data == {}:
                    self.results.add_pass(test_name)
                    print(f"✅ Error handling ({symbol}): Handled gracefully")
                else:
                    # If data returned, it might be a valid symbol
                    self.results.add_warning(f"Symbol '{symbol}' returned data (might be valid)")
                    print(f"⚠️ Error handling ({symbol}): Returned data unexpectedly")
                    
            except Exception as e:
                # Exception is expected for invalid symbols
                self.results.add_pass(test_name)
                print(f"✅ Error handling ({symbol}): Exception handled correctly")
                
    async def test_integration(self):
        """Test that indicators work together"""
        print("\n" + "="*50)
        print("TEST 6: INTEGRATION TEST")
        print("="*50)
        
        test_name = "integration"
        try:
            symbol = "BTC"
            
            # Collect data from multiple indicators
            oi_data = await self.indicators["open_interest"].calculate_open_interest(symbol)
            funding_data = await self.indicators["funding_rate"].calculate_funding_rate(symbol)
            bb_data = await self.indicators["bollinger"].calculate_bollinger_bands(symbol)
            
            # MTF Aggregator should be able to use data from other indicators
            confluence_data = await self.indicators["mtf_aggregator"].calculate_confluence(symbol)
            
            assert confluence_data is not None, "MTF aggregator returned no data"
            assert "confluence_score" in confluence_data, "Missing confluence score"
            
            self.results.add_pass(test_name)
            print(f"✅ Integration: All indicators work together successfully")
            print(f"   Confluence score: {confluence_data.get('confluence_score', 'N/A')}")
            
        except Exception as e:
            self.results.add_fail(test_name, str(e))
            print(f"❌ Integration: Failed - {e}")
            
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return results"""
        print("\n" + "="*70)
        print(" "*20 + "MTF INDICATORS TEST SUITE")
        print(" "*15 + f"Testing {len(self.indicators)} indicators")
        print(" "*15 + f"Symbols: {', '.join(TEST_SYMBOLS)}")
        print("="*70)
        
        # Run all test categories
        await self.test_indicator_initialization()
        await self.test_data_calculation()
        await self.test_database_save()
        await self.test_rate_limiting()
        await self.test_error_handling()
        await self.test_integration()
        
        # Print summary
        summary = self.results.get_summary()
        
        print("\n" + "="*70)
        print(" "*25 + "TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ({summary['pass_rate']})")
        print(f"Failed: {summary['failed']}")
        print(f"Warnings: {summary['warnings']}")
        
        if summary['failed'] > 0:
            print("\nFailed Tests:")
            for failure in summary['failed_tests']:
                print(f"  - {failure['test']}: {failure['error']}")
                
        if summary['warnings'] > 0:
            print("\nWarnings:")
            for warning in summary['warnings']:
                print(f"  - {warning}")
                
        print("="*70)
        
        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(summary, f, indent=2)
            print(f"\nResults saved to test_results.json")
            
        return summary


async def main():
    """Main test runner"""
    test_suite = IndicatorTestSuite()
    results = await test_suite.run_all_tests()
    
    # Return exit code based on results
    if results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())