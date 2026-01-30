"""
Volume Profile (VPVR) Indicator for Hyperliquid
Tracks volume distribution across price levels
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
import json

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


class VolumeProfileIndicator:
    """
    Tracks Volume Profile metrics:
    - Volume at Price (VAP) levels
    - Point of Control (POC) - highest volume price
    - Value Area (VA) - 70% of volume concentration
    - High Volume Nodes (HVN) and Low Volume Nodes (LVN)
    - Volume-weighted support/resistance
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Volume profile data
        self.price_levels = defaultdict(lambda: defaultdict(float))  # symbol -> price -> volume
        self.trade_history = defaultdict(lambda: deque(maxlen=10000))  # Last 10k trades
        
        # Profile metrics
        self.poc = defaultdict(float)  # Point of Control
        self.value_area_high = defaultdict(float)
        self.value_area_low = defaultdict(float)
        self.hvn_levels = defaultdict(list)  # High Volume Nodes
        self.lvn_levels = defaultdict(list)  # Low Volume Nodes
        
        # Current prices
        self.current_prices = defaultdict(float)
        
        # Profile periods
        self.profile_periods = {
            'session': 4 * 3600,  # 4 hours
            'daily': 24 * 3600,    # 24 hours
            'weekly': 7 * 24 * 3600  # 7 days
        }
        
        # Timing
        self.last_update = time.time()
        self.last_snapshot = time.time()
    
    async def fetch_recent_trades(self, symbol: str):
        """Fetch recent trades for volume profile calculation"""
        try:
            # Get recent trades (last 1000)
            trades = self.info.user_fills_by_time(symbol)
            
            if trades:
                for trade in trades:
                    trade_data = {
                        'time': trade.get('time', 0),
                        'price': float(trade.get('px', 0)),
                        'size': float(trade.get('sz', 0)),
                        'side': trade.get('side', 'unknown')
                    }
                    
                    # Add to history
                    self.trade_history[symbol].append(trade_data)
                    
                    # Update current price
                    if trade_data['price'] > 0:
                        self.current_prices[symbol] = trade_data['price']
                
                return True
            return False
            
        except Exception as e:
            # If user_fills fails, try getting from candles volume
            try:
                # Use candles as fallback for volume data
                end_time = int(time.time() * 1000)
                start_time = end_time - (4 * 60 * 60 * 1000)  # 4 hours
                
                candles = self.info.candles_snapshot(
                    symbol,
                    '15m',
                    start_time,
                    end_time
                )
                
                if candles:
                    for candle in candles:
                        # Simulate trades from candle data
                        avg_price = (float(candle.get('h', 0)) + float(candle.get('l', 0))) / 2
                        volume = float(candle.get('v', 0))
                        
                        if avg_price > 0 and volume > 0:
                            trade_data = {
                                'time': candle.get('t', 0),
                                'price': avg_price,
                                'size': volume / 10,  # Approximate trade size
                                'side': 'buy' if float(candle.get('c', 0)) > float(candle.get('o', 0)) else 'sell'
                            }
                            self.trade_history[symbol].append(trade_data)
                    
                    # Update current price
                    if candles:
                        self.current_prices[symbol] = float(candles[-1].get('c', 0))
                    
                    return True
                    
            except Exception as e2:
                print(f"[VolumeProfile] Error fetching data for {symbol}: {e2}")
            
            return False
    
    def calculate_volume_profile(self, symbol: str, period: str = 'session'):
        """Calculate volume profile for given period"""
        trades = list(self.trade_history[symbol])
        
        if not trades:
            return None
        
        # Filter trades by period
        current_time = time.time()
        period_seconds = self.profile_periods.get(period, 4 * 3600)
        cutoff_time = (current_time - period_seconds) * 1000
        
        period_trades = [t for t in trades if t['time'] >= cutoff_time]
        
        if not period_trades:
            return None
        
        # Find price range
        prices = [t['price'] for t in period_trades]
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        
        if price_range <= 0:
            return None
        
        # Create price buckets (50 levels)
        num_levels = 50
        bucket_size = price_range / num_levels
        
        # Calculate volume at each price level
        volume_profile = defaultdict(float)
        
        for trade in period_trades:
            bucket = int((trade['price'] - min_price) / bucket_size)
            bucket_price = min_price + (bucket * bucket_size) + (bucket_size / 2)
            volume_profile[bucket_price] += trade['size']
        
        # Sort by price
        sorted_profile = sorted(volume_profile.items())
        
        if not sorted_profile:
            return None
        
        # Find Point of Control (highest volume level)
        poc_price = max(sorted_profile, key=lambda x: x[1])[0]
        
        # Calculate Value Area (70% of volume)
        total_volume = sum(v for _, v in sorted_profile)
        value_area_volume = total_volume * 0.7
        
        # Find value area bounds
        va_high = poc_price
        va_low = poc_price
        accumulated_volume = volume_profile[poc_price]
        
        # Expand from POC until we have 70% of volume
        poc_index = next(i for i, (p, _) in enumerate(sorted_profile) if p == poc_price)
        upper_index = poc_index
        lower_index = poc_index
        
        while accumulated_volume < value_area_volume:
            # Check which side to expand
            can_go_up = upper_index < len(sorted_profile) - 1
            can_go_down = lower_index > 0
            
            if can_go_up and can_go_down:
                # Expand to side with more volume
                up_volume = sorted_profile[upper_index + 1][1] if can_go_up else 0
                down_volume = sorted_profile[lower_index - 1][1] if can_go_down else 0
                
                if up_volume >= down_volume:
                    upper_index += 1
                    accumulated_volume += sorted_profile[upper_index][1]
                    va_high = sorted_profile[upper_index][0]
                else:
                    lower_index -= 1
                    accumulated_volume += sorted_profile[lower_index][1]
                    va_low = sorted_profile[lower_index][0]
            elif can_go_up:
                upper_index += 1
                accumulated_volume += sorted_profile[upper_index][1]
                va_high = sorted_profile[upper_index][0]
            elif can_go_down:
                lower_index -= 1
                accumulated_volume += sorted_profile[lower_index][1]
                va_low = sorted_profile[lower_index][0]
            else:
                break
        
        # Identify HVN and LVN
        avg_volume = total_volume / len(sorted_profile)
        hvn_levels = [price for price, vol in sorted_profile if vol > avg_volume * 1.5]
        lvn_levels = [price for price, vol in sorted_profile if vol < avg_volume * 0.5]
        
        return {
            'poc': poc_price,
            'value_area_high': va_high,
            'value_area_low': va_low,
            'hvn_levels': hvn_levels[:5],  # Top 5 HVN
            'lvn_levels': lvn_levels[:5],  # Top 5 LVN
            'total_volume': total_volume,
            'profile': dict(sorted_profile)
        }
    
    def calculate_vp_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate comprehensive volume profile metrics"""
        # Calculate profiles for different periods
        session_profile = self.calculate_volume_profile(symbol, 'session')
        daily_profile = self.calculate_volume_profile(symbol, 'daily')
        
        if not session_profile:
            # Return empty metrics if no data
            return {
                'symbol': symbol,
                'current_price': self.current_prices.get(symbol, 0),
                'poc_session': 0,
                'poc_daily': 0,
                'value_area_high': 0,
                'value_area_low': 0,
                'hvn_levels': [],
                'lvn_levels': [],
                'volume_distribution': {},
                'position_relative_to_poc': 'unknown',
                'position_relative_to_va': 'unknown',
                'updated_at': datetime.utcnow().isoformat()
            }
        
        current_price = self.current_prices.get(symbol, 0)
        
        # Determine position relative to POC
        if current_price > session_profile['poc']:
            poc_position = 'above'
        elif current_price < session_profile['poc']:
            poc_position = 'below'
        else:
            poc_position = 'at'
        
        # Determine position relative to Value Area
        if current_price > session_profile['value_area_high']:
            va_position = 'above'
        elif current_price < session_profile['value_area_low']:
            va_position = 'below'
        else:
            va_position = 'inside'
        
        # Calculate volume distribution percentages
        if session_profile['profile']:
            sorted_prices = sorted(session_profile['profile'].keys())
            mid_index = len(sorted_prices) // 2
            
            upper_volume = sum(session_profile['profile'][p] for p in sorted_prices[mid_index:])
            lower_volume = sum(session_profile['profile'][p] for p in sorted_prices[:mid_index])
            total = upper_volume + lower_volume
            
            if total > 0:
                upper_pct = (upper_volume / total) * 100
                lower_pct = (lower_volume / total) * 100
            else:
                upper_pct = lower_pct = 50
        else:
            upper_pct = lower_pct = 50
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'poc_session': session_profile['poc'],
            'poc_daily': daily_profile['poc'] if daily_profile else session_profile['poc'],
            'value_area_high': session_profile['value_area_high'],
            'value_area_low': session_profile['value_area_low'],
            'hvn_levels': session_profile['hvn_levels'],
            'lvn_levels': session_profile['lvn_levels'],
            'total_volume': session_profile['total_volume'],
            'upper_volume_pct': upper_pct,
            'lower_volume_pct': lower_pct,
            'position_relative_to_poc': poc_position,
            'position_relative_to_va': va_position,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Update volume profile data for all symbols"""
        for symbol in self.symbols:
            await self.fetch_recent_trades(symbol)
    
    async def save_to_supabase(self):
        """Save volume profile data to Supabase"""
        for symbol in self.symbols:
            metrics = self.calculate_vp_metrics(symbol)
            
            # Update current table
            try:
                # Convert lists to JSON for storage
                metrics_copy = metrics.copy()
                metrics_copy['hvn_levels'] = json.dumps(metrics['hvn_levels'])
                metrics_copy['lvn_levels'] = json.dumps(metrics['lvn_levels'])
                
                self.supabase.table('hl_volume_profile_current').upsert({
                    'symbol': symbol,
                    **metrics_copy
                }).execute()
            except Exception as e:
                print(f"[VolumeProfile] Error saving current data: {e}")
            
            # Save snapshots every 30 minutes
            current_time = time.time()
            if current_time - self.last_snapshot >= 1800:
                try:
                    self.supabase.table('hl_volume_profile_snapshots').insert({
                        'symbol': symbol,
                        'price': metrics['current_price'],
                        'poc': metrics['poc_session'],
                        'value_area_high': metrics['value_area_high'],
                        'value_area_low': metrics['value_area_low'],
                        'position_va': metrics['position_relative_to_va'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[VolumeProfile] Error saving snapshot: {e}")
        
        if time.time() - self.last_snapshot >= 1800:
            self.last_snapshot = time.time()
            print(f"[VolumeProfile] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 60):
        """Run the volume profile tracker"""
        print(f"[VolumeProfile] Starting Volume Profile tracker")
        print(f"[VolumeProfile] Tracking: {', '.join(self.symbols)}")
        print(f"[VolumeProfile] Update interval: {update_interval} seconds")
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
                print(f"\n[VolumeProfile Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    metrics = self.calculate_vp_metrics(symbol)
                    if metrics['current_price'] > 0:
                        print(f"  {symbol}: POC=${metrics['poc_session']:.2f}, "
                              f"VA=[${metrics['value_area_low']:.2f}-${metrics['value_area_high']:.2f}], "
                              f"Position: {metrics['position_relative_to_va']}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[VolumeProfile] Error in main loop: {e}")
                await asyncio.sleep(10)


async def main():
    """Run Volume Profile indicator"""
    indicator = VolumeProfileIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=60)  # Update every minute
    except KeyboardInterrupt:
        print("\n[VolumeProfile] Stopped by user")
    except Exception as e:
        print(f"[VolumeProfile] Fatal error: {e}")


if __name__ == "__main__":
    print("Volume Profile Indicator for Hyperliquid")
    print("Updates every 60 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())