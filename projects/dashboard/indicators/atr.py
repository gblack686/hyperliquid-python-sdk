"""
ATR (Average True Range) Indicator for Hyperliquid
Tracks volatility using ATR across multiple timeframes
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque
import os
from dotenv import load_dotenv
import sys
import numpy as np

# Try to import hyperliquid - works both locally and in Docker
try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
except ImportError:
    sys.path.append('..')
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
from supabase import create_client, Client

load_dotenv()


class ATRIndicator:
    """
    Tracks ATR (Average True Range) metrics:
    - Standard ATR calculation
    - Multi-timeframe ATR (5m, 15m, 1h, 4h, 1d)
    - ATR percentile levels
    - Volatility regime classification
    - ATR-based stop loss levels
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # ATR data storage
        self.candles = defaultdict(lambda: {
            '5m': deque(maxlen=100),
            '15m': deque(maxlen=100),
            '1h': deque(maxlen=100),
            '4h': deque(maxlen=100),
            '1d': deque(maxlen=100)
        })
        
        # Current ATR values
        self.atr_values = defaultdict(lambda: {
            '5m': 0,
            '15m': 0,
            '1h': 0,
            '4h': 0,
            '1d': 0
        })
        
        # ATR normalized (as percentage of price)
        self.atr_percentages = defaultdict(lambda: {
            '5m': 0,
            '15m': 0,
            '1h': 0,
            '4h': 0,
            '1d': 0
        })
        
        # Historical ATR for percentile calculation
        self.atr_history = defaultdict(lambda: deque(maxlen=500))
        
        # Current price cache
        self.current_prices = defaultdict(float)
        
        # Timing
        self.last_update = defaultdict(lambda: {
            '5m': 0,
            '15m': 0,
            '1h': 0,
            '4h': 0,
            '1d': 0
        })
        self.last_snapshot = time.time()
        
    async def fetch_candles(self, symbol: str, interval: str, limit: int = 50):
        """Fetch candle data for ATR calculation"""
        try:
            # Map interval to Hyperliquid format
            interval_map = {
                '5m': '5m',
                '15m': '15m',
                '1h': '60m',
                '4h': '240m',
                '1d': '1d'
            }
            
            hl_interval = interval_map.get(interval, '5m')
            
            # Get candles
            end_time = int(time.time() * 1000)
            start_time = end_time - (limit * self.get_interval_ms(interval))
            
            # Use the correct API method
            candles = self.info.candles_snapshot(
                symbol,  # coin parameter
                hl_interval,  # interval
                start_time,  # startTime
                end_time  # endTime
            )
            
            if candles:
                # Process candles
                for candle in candles:
                    candle_data = {
                        'time': candle.get('t', 0),
                        'open': float(candle.get('o', 0)),
                        'high': float(candle.get('h', 0)),
                        'low': float(candle.get('l', 0)),
                        'close': float(candle.get('c', 0)),
                        'volume': float(candle.get('v', 0))
                    }
                    self.candles[symbol][interval].append(candle_data)
                
                # Update current price
                if candles:
                    self.current_prices[symbol] = float(candles[-1].get('c', 0))
                
                return True
            return False
            
        except Exception as e:
            print(f"[ATR] Error fetching candles for {symbol} {interval}: {e}")
            return False
    
    def get_interval_ms(self, interval: str) -> int:
        """Get interval duration in milliseconds"""
        intervals = {
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        return intervals.get(interval, 5 * 60 * 1000)
    
    def calculate_true_range(self, current: Dict, previous: Dict) -> float:
        """Calculate True Range for a single period"""
        high = current['high']
        low = current['low']
        prev_close = previous['close'] if previous else current['open']
        
        # True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        return max(tr1, tr2, tr3)
    
    def calculate_atr(self, symbol: str, interval: str, period: int = 14) -> float:
        """Calculate ATR for given symbol and interval"""
        candles = list(self.candles[symbol][interval])
        
        if len(candles) < period + 1:
            return 0
        
        # Calculate True Ranges
        true_ranges = []
        for i in range(1, len(candles)):
            tr = self.calculate_true_range(candles[i], candles[i-1])
            true_ranges.append(tr)
        
        if len(true_ranges) < period:
            return 0
        
        # Calculate ATR using exponential smoothing
        atr = np.mean(true_ranges[:period])  # Initial ATR
        alpha = 1.0 / period
        
        for i in range(period, len(true_ranges)):
            atr = (true_ranges[i] * alpha) + (atr * (1 - alpha))
        
        return atr
    
    def classify_volatility(self, symbol: str) -> str:
        """Classify current volatility regime"""
        current_atr = self.atr_values[symbol].get('1h', 0)
        history = list(self.atr_history[symbol])
        
        if not history or current_atr == 0:
            return 'normal'
        
        # Calculate percentile
        percentile = np.percentile(history, [20, 40, 60, 80])
        
        if current_atr < percentile[0]:
            return 'very_low'
        elif current_atr < percentile[1]:
            return 'low'
        elif current_atr < percentile[2]:
            return 'normal'
        elif current_atr < percentile[3]:
            return 'high'
        else:
            return 'very_high'
    
    def calculate_atr_stops(self, symbol: str, multiplier: float = 2.0) -> Dict[str, float]:
        """Calculate ATR-based stop loss levels"""
        current_price = self.current_prices.get(symbol, 0)
        atr_1h = self.atr_values[symbol].get('1h', 0)
        
        if current_price == 0 or atr_1h == 0:
            return {'long_stop': 0, 'short_stop': 0}
        
        return {
            'long_stop': current_price - (atr_1h * multiplier),
            'short_stop': current_price + (atr_1h * multiplier)
        }
    
    def calculate_atr_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate comprehensive ATR metrics"""
        # Update ATR for all timeframes
        for interval in ['5m', '15m', '1h', '4h', '1d']:
            atr = self.calculate_atr(symbol, interval)
            self.atr_values[symbol][interval] = atr
            
            # Calculate as percentage of price
            current_price = self.current_prices.get(symbol, 0)
            if current_price > 0:
                self.atr_percentages[symbol][interval] = (atr / current_price) * 100
        
        # Add to history for percentile calculation
        if self.atr_values[symbol]['1h'] > 0:
            self.atr_history[symbol].append(self.atr_values[symbol]['1h'])
        
        # Get ATR stops
        stops = self.calculate_atr_stops(symbol)
        
        # Determine trend based on ATR expansion/contraction
        atr_5m = self.atr_values[symbol]['5m']
        atr_15m = self.atr_values[symbol]['15m']
        atr_1h = self.atr_values[symbol]['1h']
        
        if atr_5m > atr_15m > atr_1h:
            atr_trend = 'expanding'  # Volatility increasing
        elif atr_5m < atr_15m < atr_1h:
            atr_trend = 'contracting'  # Volatility decreasing
        else:
            atr_trend = 'stable'
        
        return {
            'symbol': symbol,
            'current_price': self.current_prices.get(symbol, 0),
            'atr_5m': self.atr_values[symbol]['5m'],
            'atr_15m': self.atr_values[symbol]['15m'],
            'atr_1h': self.atr_values[symbol]['1h'],
            'atr_4h': self.atr_values[symbol]['4h'],
            'atr_1d': self.atr_values[symbol]['1d'],
            'atr_pct_5m': self.atr_percentages[symbol]['5m'],
            'atr_pct_15m': self.atr_percentages[symbol]['15m'],
            'atr_pct_1h': self.atr_percentages[symbol]['1h'],
            'atr_pct_4h': self.atr_percentages[symbol]['4h'],
            'atr_pct_1d': self.atr_percentages[symbol]['1d'],
            'volatility_regime': self.classify_volatility(symbol),
            'atr_trend': atr_trend,
            'long_stop': stops['long_stop'],
            'short_stop': stops['short_stop'],
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Update ATR data for all symbols and timeframes"""
        current_time = time.time()
        
        for symbol in self.symbols:
            for interval in ['5m', '15m', '1h', '4h', '1d']:
                # Check if we need to update this interval
                interval_seconds = self.get_interval_ms(interval) / 1000
                if current_time - self.last_update[symbol][interval] >= interval_seconds / 2:
                    await self.fetch_candles(symbol, interval)
                    self.last_update[symbol][interval] = current_time
    
    async def save_to_supabase(self):
        """Save ATR data to Supabase"""
        for symbol in self.symbols:
            metrics = self.calculate_atr_metrics(symbol)
            
            # Update current table
            try:
                self.supabase.table('hl_atr_current').upsert({
                    'symbol': symbol,
                    **metrics
                }).execute()
            except Exception as e:
                print(f"[ATR] Error saving current data: {e}")
            
            # Save snapshots every 15 minutes
            current_time = time.time()
            if current_time - self.last_snapshot >= 900:
                try:
                    self.supabase.table('hl_atr_snapshots').insert({
                        'symbol': symbol,
                        'price': metrics['current_price'],
                        'atr_1h': metrics['atr_1h'],
                        'atr_pct_1h': metrics['atr_pct_1h'],
                        'volatility_regime': metrics['volatility_regime'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[ATR] Error saving snapshot: {e}")
        
        if time.time() - self.last_snapshot >= 900:
            self.last_snapshot = time.time()
            print(f"[ATR] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 30):
        """Run the ATR tracker"""
        print(f"[ATR] Starting ATR tracker")
        print(f"[ATR] Tracking: {', '.join(self.symbols)}")
        print(f"[ATR] Update interval: {update_interval} seconds")
        print("=" * 60)
        
        # Initial fetch
        await self.update()
        
        while True:
            try:
                # Update data
                await self.update()
                
                # Save to Supabase
                await self.save_to_supabase()
                
                # Display current metrics
                print(f"\n[ATR Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    metrics = self.calculate_atr_metrics(symbol)
                    if metrics['current_price'] > 0:
                        print(f"  {symbol}: ATR(1h)={metrics['atr_1h']:.2f} ({metrics['atr_pct_1h']:.2f}%), "
                              f"Volatility={metrics['volatility_regime']}, "
                              f"Trend={metrics['atr_trend']}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[ATR] Error in main loop: {e}")
                await asyncio.sleep(10)


async def main():
    """Run ATR indicator"""
    indicator = ATRIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=30)  # Update every 30 seconds
    except KeyboardInterrupt:
        print("\n[ATR] Stopped by user")
    except Exception as e:
        print(f"[ATR] Fatal error: {e}")


if __name__ == "__main__":
    print("ATR Indicator for Hyperliquid")
    print("Updates every 30 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())