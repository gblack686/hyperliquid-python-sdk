"""
Analyze Hyperliquid API efficiency and data retention strategy
"""
import os
import sys
import json
import asyncio
import time
from datetime import datetime, timedelta
from collections import deque
import numpy as np
from dotenv import load_dotenv
import eth_account

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

class DataEfficiencyAnalyzer:
    def __init__(self):
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account = eth_account.Account.from_key(secret_key)
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Track API call costs
        self.api_calls = {
            'candles': {'count': 0, 'total_time': 0, 'data_size': 0},
            'l2_book': {'count': 0, 'total_time': 0, 'data_size': 0},
            'trades': {'count': 0, 'total_time': 0, 'data_size': 0},
            'meta': {'count': 0, 'total_time': 0, 'data_size': 0}
        }
        
        # CVD calculation buffers
        self.trade_buffer = deque(maxlen=10000)  # Keep last 10k trades
        self.cvd_cache = {}  # CVD values per timeframe
        
    def measure_api_call(self, endpoint: str, func, *args, **kwargs):
        """Measure API call performance"""
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        
        # Estimate data size
        data_size = len(json.dumps(result)) if result else 0
        
        self.api_calls[endpoint]['count'] += 1
        self.api_calls[endpoint]['total_time'] += elapsed
        self.api_calls[endpoint]['data_size'] += data_size
        
        return result, elapsed, data_size
    
    def analyze_candle_efficiency(self, symbol: str = "BTC"):
        """Analyze candle data fetching efficiency"""
        print(f"\n=== Analyzing Candle Data Efficiency for {symbol} ===")
        
        intervals = ["5m", "15m", "1h", "4h", "1d"]
        results = []
        
        for interval in intervals:
            # Fetch 100 candles
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (100 * 60 * 1000)  # Adjust based on interval
            
            result, elapsed, size = self.measure_api_call(
                'candles',
                self.info.candles_snapshot,
                symbol, interval, start_time, end_time
            )
            
            candle_count = len(result) if result else 0
            
            results.append({
                'interval': interval,
                'candles': candle_count,
                'time_ms': elapsed * 1000,
                'size_kb': size / 1024,
                'ms_per_candle': (elapsed * 1000 / candle_count) if candle_count > 0 else 0
            })
            
            print(f"  {interval}: {candle_count} candles, {elapsed*1000:.1f}ms, {size/1024:.1f}KB")
        
        return results
    
    def analyze_trades_for_cvd(self, symbol: str = "BTC"):
        """Analyze trades data requirements for CVD calculation"""
        print(f"\n=== Analyzing Trades for CVD Calculation ===")
        
        # Note: Hyperliquid doesn't have a direct trades endpoint in REST API
        # We need to use WebSocket for real-time trades or user fills for historical
        
        print("Trade Data Options:")
        print("1. WebSocket subscription (Real-time):")
        print("   - Most efficient for live CVD")
        print("   - Minimal latency")
        print("   - Requires persistent connection")
        
        print("\n2. User fills endpoint (Historical):")
        print("   - Only shows YOUR trades")
        print("   - Not suitable for market-wide CVD")
        
        print("\n3. Calculated from L2 changes:")
        print("   - Approximate CVD from order book changes")
        print("   - Less accurate but feasible")
        
        # Try to get user fills as example
        try:
            fills = self.info.user_fills(self.account.address)
            if fills:
                print(f"\n  Found {len(fills)} user fills (not market-wide)")
                # Calculate simple CVD from user fills
                buy_volume = sum(float(f['sz']) for f in fills if f['side'] == 'B')
                sell_volume = sum(float(f['sz']) for f in fills if f['side'] == 'A')
                cvd = buy_volume - sell_volume
                print(f"  User CVD: {cvd:.2f}")
        except:
            print("  No user fills available")
        
        return {
            'recommendation': 'Use WebSocket for real-time CVD',
            'alternative': 'Store L2 snapshots and calculate approximate CVD',
            'storage_needed': 'Rolling buffer of ~10k trades (< 10MB RAM)'
        }
    
    def calculate_storage_requirements(self):
        """Calculate storage requirements for different strategies"""
        print("\n=== Storage Requirements Analysis ===")
        
        strategies = {
            'Minimal (REST only)': {
                'candles': '5 TFs × 100 candles × 100 bytes = 50KB per symbol',
                'l2_snapshot': '20 levels × 50 bytes = 1KB per symbol',
                'total_ram': '~100KB per symbol',
                'database': 'Store only latest values'
            },
            'Balanced (With CVD)': {
                'candles': 'Same as minimal',
                'trades_buffer': '10k trades × 100 bytes = 1MB per symbol',
                'cvd_cache': '6 TFs × 100 points = 5KB per symbol',
                'total_ram': '~1.5MB per symbol',
                'database': 'Store hourly aggregates'
            },
            'Comprehensive (Full history)': {
                'candles': 'All TFs, 1000 candles each = 500KB',
                'trades': '100k trades buffer = 10MB',
                'orderbook_snapshots': '1 per minute = 1.5MB/hour',
                'total_ram': '~15MB per symbol',
                'database': 'Store all raw data'
            }
        }
        
        for name, reqs in strategies.items():
            print(f"\n{name}:")
            for key, value in reqs.items():
                print(f"  {key}: {value}")
        
        return strategies
    
    def recommend_efficient_approach(self):
        """Recommend the most efficient approach"""
        print("\n=== RECOMMENDED EFFICIENT APPROACH ===")
        
        recommendations = """
1. **For Real-time CVD**:
   - Use WebSocket subscription for trades
   - Maintain rolling buffer (last 1000-5000 trades)
   - Calculate CVD incrementally, don't recalculate from scratch
   - Cache CVD values per timeframe

2. **For Historical Data**:
   - Fetch candles once per minute (not every request)
   - Store in local cache/Redis with TTL
   - Only fetch new candles since last fetch

3. **For Order Book**:
   - Subscribe to L2 WebSocket for real-time
   - Calculate liquidity metrics on-demand
   - Don't store full orderbook history

4. **Database Strategy**:
   - Store aggregated metrics, not raw data
   - Use time-series compression (1min → 5min → 1h)
   - Keep only recent raw data (last 24h)

5. **API Efficiency**:
   - Batch requests where possible
   - Use WebSocket for frequently changing data
   - Cache static data (symbol info, etc.)
   - Implement exponential backoff for retries
"""
        print(recommendations)
        
        return {
            'websocket_priority': ['trades', 'l2_book'],
            'cache_ttl': {'candles': 60, 'meta': 300, 'l2_snapshot': 5},
            'buffer_sizes': {'trades': 5000, 'candles': 200, 'orderbook': 20}
        }

async def main():
    analyzer = DataEfficiencyAnalyzer()
    
    # Analyze candle efficiency
    candle_results = analyzer.analyze_candle_efficiency("BTC")
    
    # Analyze trades for CVD
    cvd_analysis = analyzer.analyze_trades_for_cvd("BTC")
    
    # Calculate storage requirements
    storage_reqs = analyzer.calculate_storage_requirements()
    
    # Get recommendations
    recommendations = analyzer.recommend_efficient_approach()
    
    # Print summary
    print("\n=== EFFICIENCY SUMMARY ===")
    print(f"Total API calls made: {sum(v['count'] for v in analyzer.api_calls.values())}")
    print(f"Total time spent: {sum(v['total_time'] for v in analyzer.api_calls.values()):.2f}s")
    print(f"Total data transferred: {sum(v['data_size'] for v in analyzer.api_calls.values())/1024:.1f}KB")
    
    print("\n=== KEY FINDINGS ===")
    print("1. CVD cannot be accurately calculated from REST API alone")
    print("2. WebSocket is required for real-time trade data")
    print("3. Current approach wastes resources by not caching")
    print("4. Should implement incremental updates, not full refetches")
    
    return {
        'candle_results': candle_results,
        'cvd_analysis': cvd_analysis,
        'storage_reqs': storage_reqs,
        'recommendations': recommendations
    }

if __name__ == "__main__":
    results = asyncio.run(main())