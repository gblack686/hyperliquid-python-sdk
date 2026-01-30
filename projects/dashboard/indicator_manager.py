"""
Unified Indicator Manager for Hyperliquid Trading System
Manages and coordinates all indicators
"""

import asyncio
import sys
import os
from typing import Dict, List, Any
from datetime import datetime
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client

# Add indicators to path
sys.path.append('./indicators')

# Import indicators
from indicators.open_interest import OpenInterestIndicator
from indicators.funding_rate import FundingRateIndicator
from indicators.liquidations import LiquidationsIndicator
from indicators.orderbook_imbalance import OrderBookImbalanceIndicator
from indicators.vwap import VWAPIndicator
from indicators.atr import ATRIndicator
from indicators.bollinger_bands import BollingerBandsIndicator
from indicators.support_resistance import SupportResistanceIndicator
from indicators.volume_profile import VolumeProfileIndicator
from indicators.basis_premium import BasisPremiumIndicator
from indicators.mtf_aggregator import MTFAggregatorIndicator
from indicators.cvd import CVDIndicator

# Try to import hyperliquid - works both locally and in Docker
try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
except ImportError:
    sys.path.append('..')
    from hyperliquid.info import Info
    from hyperliquid.utils import constants

load_dotenv()


class IndicatorManager:
    """
    Manages multiple indicators running concurrently
    """
    
    def __init__(self, symbols: List[str] = None, indicators: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.indicators_to_run = indicators or ['open_interest', 'funding_rate', 'liquidations', 'orderbook', 'vwap', 'atr', 'bollinger', 'sr', 'volume_profile', 'basis', 'mtf', 'cvd']
        self.indicators = {}
        self.tasks = []
        
        # Supabase setup for health checks
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize selected indicators
        self._initialize_indicators()
        
    def _initialize_indicators(self):
        """Initialize the selected indicators"""
        
        if 'open_interest' in self.indicators_to_run:
            self.indicators['open_interest'] = OpenInterestIndicator(self.symbols)
            print("[Manager] Initialized Open Interest indicator")
            
        if 'funding_rate' in self.indicators_to_run:
            self.indicators['funding_rate'] = FundingRateIndicator(self.symbols)
            print("[Manager] Initialized Funding Rate indicator")
            
        if 'liquidations' in self.indicators_to_run:
            self.indicators['liquidations'] = LiquidationsIndicator(self.symbols)
            print("[Manager] Initialized Liquidations indicator")
            
        if 'orderbook' in self.indicators_to_run:
            self.indicators['orderbook'] = OrderBookImbalanceIndicator(self.symbols)
            print("[Manager] Initialized Order Book Imbalance indicator")
            
        if 'vwap' in self.indicators_to_run:
            self.indicators['vwap'] = VWAPIndicator(self.symbols)
            print("[Manager] Initialized VWAP indicator")
            
        if 'atr' in self.indicators_to_run:
            self.indicators['atr'] = ATRIndicator(self.symbols)
            print("[Manager] Initialized ATR indicator")
            
        if 'bollinger' in self.indicators_to_run:
            self.indicators['bollinger'] = BollingerBandsIndicator(self.symbols)
            print("[Manager] Initialized Bollinger Bands indicator")
            
        if 'sr' in self.indicators_to_run:
            self.indicators['sr'] = SupportResistanceIndicator(self.symbols)
            print("[Manager] Initialized Support/Resistance indicator")
            
        if 'volume_profile' in self.indicators_to_run:
            self.indicators['volume_profile'] = VolumeProfileIndicator(self.symbols)
            print("[Manager] Initialized Volume Profile indicator")
            
        if 'basis' in self.indicators_to_run:
            self.indicators['basis'] = BasisPremiumIndicator(self.symbols)
            print("[Manager] Initialized Basis/Premium indicator")
            
        if 'mtf' in self.indicators_to_run:
            self.indicators['mtf'] = MTFAggregatorIndicator(self.symbols)
            print("[Manager] Initialized MTF Aggregator indicator")
            
        if 'cvd' in self.indicators_to_run:
            self.indicators['cvd'] = CVDIndicator(self.symbols)
            print("[Manager] Initialized CVD (Cumulative Volume Delta) indicator")
    
    async def start_indicator(self, name: str, indicator: Any, interval: int):
        """Start a single indicator"""
        try:
            print(f"[Manager] Starting {name} with {interval}s interval")
            await indicator.run(update_interval=interval)
        except Exception as e:
            print(f"[Manager] Error in {name}: {e}")
    
    async def run_startup_tests(self) -> bool:
        """Run startup tests to verify system health"""
        print("\n" + "=" * 60)
        print("RUNNING STARTUP TESTS")
        print("=" * 60)
        
        all_passed = True
        
        # Test 1: Supabase connection
        try:
            result = self.supabase.table('hl_oi_current').select("symbol").limit(1).execute()
            print("[PASS] Supabase connection")
        except Exception as e:
            print(f"[FAIL] Supabase connection: {e}")
            all_passed = False
        
        # Test 2: Hyperliquid API
        try:
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            response = info.meta_and_asset_ctxs()
            if isinstance(response, list) and len(response) == 2:
                print("[PASS] Hyperliquid API connection")
            else:
                print("[FAIL] Hyperliquid API: Unexpected response")
                all_passed = False
        except Exception as e:
            print(f"[FAIL] Hyperliquid API: {e}")
            all_passed = False
        
        # Test 3: Check if indicators can initialize
        try:
            test_oi = OpenInterestIndicator(['BTC'])
            print("[PASS] Open Interest indicator initialized")
        except Exception as e:
            print(f"[FAIL] Open Interest indicator: {e}")
            all_passed = False
        
        try:
            test_funding = FundingRateIndicator(['BTC'])
            print("[PASS] Funding Rate indicator initialized")
        except Exception as e:
            print(f"[FAIL] Funding Rate indicator: {e}")
            all_passed = False
        
        print("=" * 60)
        if all_passed:
            print("All startup tests PASSED")
            return True
        else:
            print("Some startup tests FAILED")
            print("Please check your configuration and connections")
            return False
    
    async def run(self):
        """Run all indicators concurrently"""
        # Run startup tests first
        if not await self.run_startup_tests():
            print("\n[Manager] Startup tests failed. Please fix issues before continuing.")
            print("[Manager] Continuing anyway in 5 seconds...")
            await asyncio.sleep(5)
        
        print("\n" + "=" * 60)
        print("HYPERLIQUID INDICATOR MANAGER")
        print("=" * 60)
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Indicators: {', '.join(self.indicators_to_run)}")
        print("=" * 60 + "\n")
        
        # Create tasks for each indicator
        tasks = []
        
        if 'open_interest' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'open_interest', 
                    self.indicators['open_interest'],
                    30  # 30 second updates
                )
            ))
            
        if 'funding_rate' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'funding_rate',
                    self.indicators['funding_rate'], 
                    300  # 5 minute updates
                )
            ))
            
        if 'liquidations' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'liquidations',
                    self.indicators['liquidations'], 
                    10  # 10 second updates
                )
            ))
            
        if 'orderbook' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'orderbook',
                    self.indicators['orderbook'], 
                    5  # 5 second updates
                )
            ))
            
        if 'vwap' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'vwap',
                    self.indicators['vwap'], 
                    10  # 10 second updates
                )
            ))
            
        if 'atr' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'atr',
                    self.indicators['atr'], 
                    30  # 30 second updates
                )
            ))
            
        if 'bollinger' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'bollinger',
                    self.indicators['bollinger'], 
                    30  # 30 second updates
                )
            ))
            
        if 'sr' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'sr',
                    self.indicators['sr'], 
                    60  # 60 second updates
                )
            ))
            
        if 'volume_profile' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'volume_profile',
                    self.indicators['volume_profile'], 
                    60  # 60 second updates
                )
            ))
            
        if 'basis' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'basis',
                    self.indicators['basis'], 
                    30  # 30 second updates
                )
            ))
            
        if 'mtf' in self.indicators:
            tasks.append(asyncio.create_task(
                self.start_indicator(
                    'mtf',
                    self.indicators['mtf'], 
                    30  # 30 second updates
                )
            ))
        
        # Wait for all tasks (they should run forever)
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n[Manager] Shutting down all indicators...")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            print("[Manager] All indicators stopped")
    
    def status(self) -> Dict[str, Any]:
        """Get status of all indicators"""
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'symbols': self.symbols,
            'indicators': {}
        }
        
        for name, indicator in self.indicators.items():
            if hasattr(indicator, 'get_current_value'):
                status['indicators'][name] = {
                    symbol: indicator.get_current_value(symbol)
                    for symbol in self.symbols
                }
        
        return status


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Hyperliquid Indicator Manager')
    parser.add_argument(
        '--symbols', 
        nargs='+', 
        default=['BTC', 'ETH', 'SOL', 'HYPE'],
        help='Symbols to track'
    )
    parser.add_argument(
        '--indicators',
        nargs='+', 
        default=['open_interest', 'funding_rate'],
        help='Indicators to run'
    )
    
    args = parser.parse_args()
    
    # Create and run manager
    manager = IndicatorManager(
        symbols=args.symbols,
        indicators=args.indicators
    )
    
    try:
        await manager.run()
    except KeyboardInterrupt:
        print("\n[Manager] Stopped by user")
    except Exception as e:
        print(f"[Manager] Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())