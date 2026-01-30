"""
Bollinger Bands Indicator for Hyperliquid
Tracks price position relative to Bollinger Bands across multiple timeframes
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


class BollingerBandsIndicator:
    """
    Tracks Bollinger Bands metrics:
    - Upper, Middle (SMA), Lower bands
    - Band position (0-1 scale)
    - Band width and squeeze detection
    - Multi-timeframe bands (5m, 15m, 1h, 4h, 1d)
    - Band breaks and walks
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Price data storage
        self.price_history = defaultdict(lambda: {
            '5m': deque(maxlen=100),
            '15m': deque(maxlen=100),
            '1h': deque(maxlen=100),
            '4h': deque(maxlen=100),
            '1d': deque(maxlen=100)
        })
        
        # Bollinger Bands values
        self.bands = defaultdict(lambda: {
            '5m': {'upper': 0, 'middle': 0, 'lower': 0, 'width': 0},
            '15m': {'upper': 0, 'middle': 0, 'lower': 0, 'width': 0},
            '1h': {'upper': 0, 'middle': 0, 'lower': 0, 'width': 0},
            '4h': {'upper': 0, 'middle': 0, 'lower': 0, 'width': 0},
            '1d': {'upper': 0, 'middle': 0, 'lower': 0, 'width': 0}
        })
        
        # Band position (0 = at lower band, 0.5 = at middle, 1 = at upper band)
        self.band_position = defaultdict(lambda: {
            '5m': 0.5,
            '15m': 0.5,
            '1h': 0.5,
            '4h': 0.5,
            '1d': 0.5
        })
        
        # Squeeze detection
        self.squeeze_state = defaultdict(lambda: {
            '5m': False,
            '15m': False,
            '1h': False,
            '4h': False,
            '1d': False
        })
        
        # Current prices
        self.current_prices = defaultdict(float)
        
        # Band walk tracking (consecutive candles at bands)
        self.upper_walk_count = defaultdict(lambda: defaultdict(int))
        self.lower_walk_count = defaultdict(lambda: defaultdict(int))
        
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
        """Fetch candle data for Bollinger Bands calculation"""
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
            
            candles = self.info.candles_snapshot(
                symbol,  # coin
                hl_interval,  # interval
                start_time,  # startTime
                end_time  # endTime
            )
            
            if candles:
                # Extract closing prices
                prices = []
                for candle in candles:
                    close_price = float(candle.get('c', 0))
                    prices.append(close_price)
                
                # Store price history
                self.price_history[symbol][interval] = deque(prices, maxlen=100)
                
                # Update current price
                if prices:
                    self.current_prices[symbol] = prices[-1]
                
                return True
            return False
            
        except Exception as e:
            print(f"[BB] Error fetching candles for {symbol} {interval}: {e}")
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
    
    def calculate_bands(self, symbol: str, interval: str, period: int = 20, std_dev: float = 2.0):
        """Calculate Bollinger Bands for given symbol and interval"""
        prices = list(self.price_history[symbol][interval])
        
        if len(prices) < period:
            return None
        
        # Get recent prices for calculation
        recent_prices = prices[-period:]
        
        # Calculate SMA (middle band)
        sma = np.mean(recent_prices)
        
        # Calculate standard deviation
        std = np.std(recent_prices)
        
        # Calculate bands
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        width = upper - lower
        
        # Store bands
        self.bands[symbol][interval] = {
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'width': width,
            'std': std
        }
        
        # Calculate position (0-1 scale)
        current_price = self.current_prices.get(symbol, sma)
        if width > 0:
            position = (current_price - lower) / width
            position = max(0, min(1, position))  # Clamp to 0-1
        else:
            position = 0.5
        
        self.band_position[symbol][interval] = position
        
        # Detect squeeze (low volatility)
        # Squeeze when bandwidth is below 20th percentile of recent history
        if len(prices) >= 50:
            recent_widths = []
            for i in range(len(prices) - period, len(prices)):
                if i >= period:
                    window = prices[i-period:i]
                    w_std = np.std(window)
                    recent_widths.append(w_std * std_dev * 2)
            
            if recent_widths:
                percentile_20 = np.percentile(recent_widths, 20)
                self.squeeze_state[symbol][interval] = width < percentile_20
        
        # Track band walks
        if position > 0.95:  # At upper band
            self.upper_walk_count[symbol][interval] += 1
            self.lower_walk_count[symbol][interval] = 0
        elif position < 0.05:  # At lower band
            self.lower_walk_count[symbol][interval] += 1
            self.upper_walk_count[symbol][interval] = 0
        else:
            self.upper_walk_count[symbol][interval] = 0
            self.lower_walk_count[symbol][interval] = 0
        
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'width': width,
            'position': position
        }
    
    def determine_band_signal(self, symbol: str) -> str:
        """Determine trading signal based on band position"""
        # Use 1h as primary timeframe
        position_1h = self.band_position[symbol].get('1h', 0.5)
        position_15m = self.band_position[symbol].get('15m', 0.5)
        squeeze_1h = self.squeeze_state[symbol].get('1h', False)
        
        # Check for band walks
        upper_walk = self.upper_walk_count[symbol]['1h'] >= 3
        lower_walk = self.lower_walk_count[symbol]['1h'] >= 3
        
        if squeeze_1h:
            # During squeeze, prepare for breakout
            if position_15m > 0.7:
                return 'squeeze_bullish'
            elif position_15m < 0.3:
                return 'squeeze_bearish'
            else:
                return 'squeeze_neutral'
        elif upper_walk:
            return 'strong_uptrend'  # Walking the upper band
        elif lower_walk:
            return 'strong_downtrend'  # Walking the lower band
        elif position_1h > 0.8:
            return 'overbought'
        elif position_1h < 0.2:
            return 'oversold'
        elif 0.4 <= position_1h <= 0.6:
            return 'neutral'
        elif position_1h > 0.6:
            return 'bullish'
        else:
            return 'bearish'
    
    def calculate_bb_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate comprehensive Bollinger Bands metrics"""
        # Update bands for all timeframes
        for interval in ['5m', '15m', '1h', '4h', '1d']:
            self.calculate_bands(symbol, interval)
        
        # Get primary metrics (1h timeframe)
        bands_1h = self.bands[symbol]['1h']
        position_1h = self.band_position[symbol]['1h']
        
        # Calculate bandwidth percentage (volatility measure)
        bandwidth_pct = 0
        if bands_1h['middle'] > 0:
            bandwidth_pct = (bands_1h['width'] / bands_1h['middle']) * 100
        
        # Determine market state
        signal = self.determine_band_signal(symbol)
        
        return {
            'symbol': symbol,
            'current_price': self.current_prices.get(symbol, 0),
            'bb_upper_5m': self.bands[symbol]['5m']['upper'],
            'bb_middle_5m': self.bands[symbol]['5m']['middle'],
            'bb_lower_5m': self.bands[symbol]['5m']['lower'],
            'bb_position_5m': self.band_position[symbol]['5m'],
            'bb_upper_15m': self.bands[symbol]['15m']['upper'],
            'bb_middle_15m': self.bands[symbol]['15m']['middle'],
            'bb_lower_15m': self.bands[symbol]['15m']['lower'],
            'bb_position_15m': self.band_position[symbol]['15m'],
            'bb_upper_1h': bands_1h['upper'],
            'bb_middle_1h': bands_1h['middle'],
            'bb_lower_1h': bands_1h['lower'],
            'bb_position_1h': position_1h,
            'bb_width_1h': bands_1h['width'],
            'bandwidth_pct': bandwidth_pct,
            'squeeze_5m': bool(self.squeeze_state[symbol]['5m']),  # Convert numpy bool to Python bool
            'squeeze_15m': bool(self.squeeze_state[symbol]['15m']),  # Convert numpy bool to Python bool
            'squeeze_1h': bool(self.squeeze_state[symbol]['1h']),  # Convert numpy bool to Python bool
            'upper_walk_count': self.upper_walk_count[symbol]['1h'],
            'lower_walk_count': self.lower_walk_count[symbol]['1h'],
            'signal': signal,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Update Bollinger Bands data for all symbols and timeframes"""
        current_time = time.time()
        
        for symbol in self.symbols:
            for interval in ['5m', '15m', '1h', '4h', '1d']:
                # Check if we need to update this interval
                interval_seconds = self.get_interval_ms(interval) / 1000
                if current_time - self.last_update[symbol][interval] >= interval_seconds / 2:
                    await self.fetch_candles(symbol, interval)
                    self.last_update[symbol][interval] = current_time
    
    async def save_to_supabase(self):
        """Save Bollinger Bands data to Supabase"""
        for symbol in self.symbols:
            metrics = self.calculate_bb_metrics(symbol)
            
            # Update current table
            try:
                self.supabase.table('hl_bollinger_current').upsert({
                    'symbol': symbol,
                    **metrics
                }).execute()
            except Exception as e:
                print(f"[BB] Error saving current data: {e}")
            
            # Save snapshots every 15 minutes
            current_time = time.time()
            if current_time - self.last_snapshot >= 900:
                try:
                    self.supabase.table('hl_bollinger_snapshots').insert({
                        'symbol': symbol,
                        'price': metrics['current_price'],
                        'bb_position_1h': metrics['bb_position_1h'],
                        'bandwidth_pct': metrics['bandwidth_pct'],
                        'squeeze_1h': bool(metrics['squeeze_1h']),  # Ensure it's a Python bool
                        'signal': metrics['signal'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[BB] Error saving snapshot: {e}")
        
        if time.time() - self.last_snapshot >= 900:
            self.last_snapshot = time.time()
            print(f"[BB] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 30):
        """Run the Bollinger Bands tracker"""
        print(f"[BB] Starting Bollinger Bands tracker")
        print(f"[BB] Tracking: {', '.join(self.symbols)}")
        print(f"[BB] Update interval: {update_interval} seconds")
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
                print(f"\n[BB Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    metrics = self.calculate_bb_metrics(symbol)
                    if metrics['current_price'] > 0:
                        print(f"  {symbol}: Pos={metrics['bb_position_1h']:.2f}, "
                              f"Width={metrics['bandwidth_pct']:.1f}%, "
                              f"Squeeze={metrics['squeeze_1h']}, "
                              f"Signal={metrics['signal']}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[BB] Error in main loop: {e}")
                await asyncio.sleep(10)


async def main():
    """Run Bollinger Bands indicator"""
    indicator = BollingerBandsIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=30)  # Update every 30 seconds
    except KeyboardInterrupt:
        print("\n[BB] Stopped by user")
    except Exception as e:
        print(f"[BB] Fatal error: {e}")


if __name__ == "__main__":
    print("Bollinger Bands Indicator for Hyperliquid")
    print("Updates every 30 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())