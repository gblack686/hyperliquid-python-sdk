"""
Support/Resistance Levels Indicator for Hyperliquid
Identifies and tracks key support and resistance levels
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
from scipy.signal import find_peaks

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


class SupportResistanceIndicator:
    """
    Tracks Support/Resistance metrics:
    - Key S/R levels from price pivots
    - Volume-based S/R levels
    - Dynamic S/R from moving averages
    - Distance from nearest S/R
    - S/R strength scoring
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Price history for S/R calculation
        self.price_history = defaultdict(lambda: {
            '1h': deque(maxlen=500),   # ~20 days
            '4h': deque(maxlen=200),   # ~33 days
            '1d': deque(maxlen=100)    # ~100 days
        })
        
        # S/R levels storage
        self.support_levels = defaultdict(list)
        self.resistance_levels = defaultdict(list)
        self.pivot_points = defaultdict(dict)
        
        # Dynamic S/R from MAs
        self.ma_levels = defaultdict(dict)
        
        # Current prices
        self.current_prices = defaultdict(float)
        
        # Level strength scores
        self.level_strength = defaultdict(lambda: defaultdict(float))
        
        # Timing
        self.last_update = time.time()
        self.last_snapshot = time.time()
        
    async def fetch_candles(self, symbol: str, interval: str, limit: int = 200):
        """Fetch candle data for S/R calculation"""
        try:
            # Map interval to Hyperliquid format
            interval_map = {
                '1h': '60m',
                '4h': '240m',
                '1d': '1d'
            }
            
            hl_interval = interval_map.get(interval, '60m')
            
            # Get candles
            end_time = int(time.time() * 1000)
            start_time = end_time - (limit * self.get_interval_ms(interval))
            
            candles = self.info.candles_snapshot(
                symbol,
                hl_interval,
                start_time,
                end_time
            )
            
            if candles:
                # Store candle data
                candle_data = []
                for candle in candles:
                    data = {
                        'time': candle.get('t', 0),
                        'open': float(candle.get('o', 0)),
                        'high': float(candle.get('h', 0)),
                        'low': float(candle.get('l', 0)),
                        'close': float(candle.get('c', 0)),
                        'volume': float(candle.get('v', 0))
                    }
                    candle_data.append(data)
                
                self.price_history[symbol][interval] = deque(candle_data, maxlen=500)
                
                # Update current price
                if candle_data:
                    self.current_prices[symbol] = candle_data[-1]['close']
                
                return True
            return False
            
        except Exception as e:
            print(f"[S/R] Error fetching candles for {symbol} {interval}: {e}")
            return False
    
    def get_interval_ms(self, interval: str) -> int:
        """Get interval duration in milliseconds"""
        intervals = {
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        return intervals.get(interval, 60 * 60 * 1000)
    
    def find_pivot_levels(self, symbol: str, interval: str) -> Tuple[List[float], List[float]]:
        """Find pivot highs and lows that form S/R levels"""
        candles = list(self.price_history[symbol][interval])
        
        if len(candles) < 20:
            return [], []
        
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        # Find peaks (resistance) and troughs (support)
        # Using prominence to filter out minor peaks
        min_prominence = np.std(highs) * 0.5
        
        peak_indices, peak_props = find_peaks(highs, prominence=min_prominence, distance=5)
        trough_indices, trough_props = find_peaks([-l for l in lows], prominence=min_prominence, distance=5)
        
        # Get peak and trough values
        resistance_levels = [highs[i] for i in peak_indices[-10:]]  # Last 10 peaks
        support_levels = [lows[i] for i in trough_indices[-10:]]  # Last 10 troughs
        
        return support_levels, resistance_levels
    
    def cluster_levels(self, levels: List[float], threshold_pct: float = 0.5) -> List[Dict]:
        """Cluster nearby levels and score their strength"""
        if not levels:
            return []
        
        # Sort levels
        sorted_levels = sorted(levels)
        
        # Cluster nearby levels
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Check if level is within threshold of cluster average
            cluster_avg = np.mean(current_cluster)
            if abs(level - cluster_avg) / cluster_avg * 100 <= threshold_pct:
                current_cluster.append(level)
            else:
                # Start new cluster
                clusters.append(current_cluster)
                current_cluster = [level]
        
        # Add last cluster
        if current_cluster:
            clusters.append(current_cluster)
        
        # Score clusters by touch count and recency
        scored_levels = []
        for cluster in clusters:
            level = np.mean(cluster)
            strength = len(cluster)  # More touches = stronger level
            
            scored_levels.append({
                'level': level,
                'strength': strength,
                'touches': len(cluster)
            })
        
        # Sort by strength
        scored_levels.sort(key=lambda x: x['strength'], reverse=True)
        
        return scored_levels[:5]  # Top 5 levels
    
    def calculate_pivot_points(self, symbol: str) -> Dict:
        """Calculate classic pivot points"""
        candles_1d = list(self.price_history[symbol]['1d'])
        
        if not candles_1d:
            return {}
        
        # Get previous day's data
        prev_candle = candles_1d[-2] if len(candles_1d) > 1 else candles_1d[-1]
        
        high = prev_candle['high']
        low = prev_candle['low']
        close = prev_candle['close']
        
        # Calculate pivot point
        pivot = (high + low + close) / 3
        
        # Calculate support and resistance levels
        r1 = (2 * pivot) - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        
        s1 = (2 * pivot) - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)
        
        return {
            'pivot': pivot,
            'r1': r1,
            'r2': r2,
            'r3': r3,
            's1': s1,
            's2': s2,
            's3': s3
        }
    
    def calculate_ma_levels(self, symbol: str) -> Dict:
        """Calculate moving average based S/R levels"""
        candles_1h = list(self.price_history[symbol]['1h'])
        
        if len(candles_1h) < 200:
            return {}
        
        closes = [c['close'] for c in candles_1h]
        
        # Calculate key MAs
        ma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else 0
        ma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else 0
        ma_100 = np.mean(closes[-100:]) if len(closes) >= 100 else 0
        ma_200 = np.mean(closes[-200:]) if len(closes) >= 200 else 0
        
        return {
            'ma_20': ma_20,
            'ma_50': ma_50,
            'ma_100': ma_100,
            'ma_200': ma_200
        }
    
    def calculate_sr_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate comprehensive S/R metrics"""
        # Find pivot-based S/R levels
        support_1h, resistance_1h = self.find_pivot_levels(symbol, '1h')
        support_4h, resistance_4h = self.find_pivot_levels(symbol, '4h')
        
        # Combine and cluster levels
        all_support = support_1h + support_4h
        all_resistance = resistance_1h + resistance_4h
        
        clustered_support = self.cluster_levels(all_support)
        clustered_resistance = self.cluster_levels(all_resistance)
        
        # Extract top levels
        top_support = [s['level'] for s in clustered_support[:3]]
        top_resistance = [r['level'] for r in clustered_resistance[:3]]
        
        # Calculate pivot points
        pivots = self.calculate_pivot_points(symbol)
        
        # Calculate MA levels
        ma_levels = self.calculate_ma_levels(symbol)
        
        # Store levels
        self.support_levels[symbol] = top_support
        self.resistance_levels[symbol] = top_resistance
        self.pivot_points[symbol] = pivots
        self.ma_levels[symbol] = ma_levels
        
        # Calculate distances
        current_price = self.current_prices.get(symbol, 0)
        
        # Find nearest S/R
        nearest_support = 0
        nearest_resistance = 0
        support_distance = 0
        resistance_distance = 0
        
        if top_support and current_price > 0:
            valid_support = [s for s in top_support if s < current_price]
            if valid_support:
                nearest_support = max(valid_support)
                support_distance = ((current_price - nearest_support) / current_price) * 100
        
        if top_resistance and current_price > 0:
            valid_resistance = [r for r in top_resistance if r > current_price]
            if valid_resistance:
                nearest_resistance = min(valid_resistance)
                resistance_distance = ((nearest_resistance - current_price) / current_price) * 100
        
        # Determine position
        if support_distance > 0 and support_distance < 0.5:
            position = 'at_support'
        elif resistance_distance > 0 and resistance_distance < 0.5:
            position = 'at_resistance'
        elif support_distance < 2:
            position = 'near_support'
        elif resistance_distance < 2:
            position = 'near_resistance'
        else:
            position = 'neutral'
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'support_1': top_support[0] if len(top_support) > 0 else 0,
            'support_2': top_support[1] if len(top_support) > 1 else 0,
            'support_3': top_support[2] if len(top_support) > 2 else 0,
            'resistance_1': top_resistance[0] if len(top_resistance) > 0 else 0,
            'resistance_2': top_resistance[1] if len(top_resistance) > 1 else 0,
            'resistance_3': top_resistance[2] if len(top_resistance) > 2 else 0,
            'pivot': pivots.get('pivot', 0),
            'pivot_r1': pivots.get('r1', 0),
            'pivot_s1': pivots.get('s1', 0),
            'ma_20': ma_levels.get('ma_20', 0),
            'ma_50': ma_levels.get('ma_50', 0),
            'ma_200': ma_levels.get('ma_200', 0),
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'support_distance_pct': support_distance,
            'resistance_distance_pct': resistance_distance,
            'position': position,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Update S/R data for all symbols"""
        for symbol in self.symbols:
            for interval in ['1h', '4h', '1d']:
                await self.fetch_candles(symbol, interval)
    
    async def save_to_supabase(self):
        """Save S/R data to Supabase"""
        for symbol in self.symbols:
            metrics = self.calculate_sr_metrics(symbol)
            
            # Update current table
            try:
                self.supabase.table('hl_sr_current').upsert({
                    'symbol': symbol,
                    **metrics
                }).execute()
            except Exception as e:
                print(f"[S/R] Error saving current data: {e}")
            
            # Save snapshots every 30 minutes
            current_time = time.time()
            if current_time - self.last_snapshot >= 1800:
                try:
                    self.supabase.table('hl_sr_snapshots').insert({
                        'symbol': symbol,
                        'price': metrics['current_price'],
                        'nearest_support': metrics['nearest_support'],
                        'nearest_resistance': metrics['nearest_resistance'],
                        'position': metrics['position'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[S/R] Error saving snapshot: {e}")
        
        if time.time() - self.last_snapshot >= 1800:
            self.last_snapshot = time.time()
            print(f"[S/R] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 60):
        """Run the S/R tracker"""
        print(f"[S/R] Starting Support/Resistance tracker")
        print(f"[S/R] Tracking: {', '.join(self.symbols)}")
        print(f"[S/R] Update interval: {update_interval} seconds")
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
                print(f"\n[S/R Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    metrics = self.calculate_sr_metrics(symbol)
                    if metrics['current_price'] > 0:
                        print(f"  {symbol}: S=${metrics['nearest_support']:.2f} ({metrics['support_distance_pct']:.1f}%), "
                              f"R=${metrics['nearest_resistance']:.2f} ({metrics['resistance_distance_pct']:.1f}%), "
                              f"{metrics['position']}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[S/R] Error in main loop: {e}")
                await asyncio.sleep(10)


async def main():
    """Run S/R indicator"""
    indicator = SupportResistanceIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=60)  # Update every minute
    except KeyboardInterrupt:
        print("\n[S/R] Stopped by user")
    except Exception as e:
        print(f"[S/R] Fatal error: {e}")


if __name__ == "__main__":
    print("Support/Resistance Indicator for Hyperliquid")
    print("Updates every 60 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())