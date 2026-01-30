"""
VWAP (Volume Weighted Average Price) Indicator for Hyperliquid
Tracks VWAP across multiple timeframes and calculates z-scores
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


class VWAPIndicator:
    """
    Tracks VWAP metrics:
    - Standard VWAP (session, daily, weekly)
    - Anchored VWAP from key levels
    - VWAP bands (standard deviations)
    - Price deviation from VWAP (z-score)
    - Volume-weighted momentum
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # VWAP calculation storage
        self.trades_buffer = defaultdict(lambda: deque(maxlen=10000))  # Recent trades
        self.vwap_sessions = defaultdict(dict)  # Different VWAP sessions
        
        # Current metrics
        self.current_price = defaultdict(float)
        self.vwap_values = defaultdict(lambda: {
            'session': 0,    # Current session (e.g., since market open)
            'daily': 0,      # Daily VWAP
            'weekly': 0,     # Weekly VWAP
            'hourly': 0      # Hourly VWAP
        })
        self.vwap_z_scores = defaultdict(lambda: {
            'session': 0,
            'daily': 0,
            'weekly': 0,
            'hourly': 0
        })
        self.vwap_std_devs = defaultdict(lambda: {
            'session': 0,
            'daily': 0,
            'weekly': 0,
            'hourly': 0
        })
        
        # WebSocket subscriptions
        self.subscriptions = {}
        
        # Session management
        self.session_start = self.get_session_start()
        self.daily_start = self.get_daily_start()
        self.weekly_start = self.get_weekly_start()
        self.hourly_start = self.get_hourly_start()
        
        # Timing
        self.last_update = time.time()
        self.last_snapshot = time.time()
        
    def get_session_start(self) -> int:
        """Get current trading session start (e.g., 00:00 UTC)"""
        now = datetime.utcnow()
        session_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(session_start.timestamp() * 1000)
    
    def get_daily_start(self) -> int:
        """Get daily start time"""
        return self.get_session_start()
    
    def get_weekly_start(self) -> int:
        """Get weekly start time (Monday 00:00 UTC)"""
        now = datetime.utcnow()
        days_since_monday = now.weekday()
        weekly_start = now - timedelta(days=days_since_monday)
        weekly_start = weekly_start.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(weekly_start.timestamp() * 1000)
    
    def get_hourly_start(self) -> int:
        """Get hourly start time"""
        now = datetime.utcnow()
        hourly_start = now.replace(minute=0, second=0, microsecond=0)
        return int(hourly_start.timestamp() * 1000)
    
    def subscribe_to_trades(self):
        """Subscribe to trade updates via WebSocket"""
        # WebSocket disabled for now due to module conflicts
        print("[VWAP] Using polling mode (WebSocket disabled)")
        return
    
    def process_trade_data(self, symbol: str, data: Any):
        """Process incoming trade data for VWAP calculation"""
        try:
            if isinstance(data, dict) and 'data' in data:
                trades = data['data']
                
                for trade in trades:
                    trade_data = {
                        'time': int(trade.get('time', time.time() * 1000)),
                        'price': float(trade.get('px', 0)),
                        'volume': float(trade.get('sz', 0)),
                        'notional': float(trade.get('px', 0)) * float(trade.get('sz', 0))
                    }
                    
                    # Update current price
                    self.current_price[symbol] = trade_data['price']
                    
                    # Add to buffer
                    self.trades_buffer[symbol].append(trade_data)
                    
                    # Update VWAP calculations
                    self.update_vwap(symbol, trade_data)
                    
        except Exception as e:
            print(f"[VWAP] Error processing trade data for {symbol}: {e}")
    
    def update_vwap(self, symbol: str, trade: Dict):
        """Update VWAP calculations with new trade"""
        # Initialize sessions if needed
        if symbol not in self.vwap_sessions:
            self.vwap_sessions[symbol] = {
                'session': {'volume': 0, 'notional': 0, 'prices': [], 'start': self.session_start},
                'daily': {'volume': 0, 'notional': 0, 'prices': [], 'start': self.daily_start},
                'weekly': {'volume': 0, 'notional': 0, 'prices': [], 'start': self.weekly_start},
                'hourly': {'volume': 0, 'notional': 0, 'prices': [], 'start': self.hourly_start}
            }
        
        # Check if we need to reset any sessions
        current_time = trade['time']
        if current_time >= self.session_start + 86400000:  # 24 hours
            self.session_start = self.get_session_start()
            self.vwap_sessions[symbol]['session'] = {'volume': 0, 'notional': 0, 'prices': [], 'start': self.session_start}
        
        if current_time >= self.hourly_start + 3600000:  # 1 hour
            self.hourly_start = self.get_hourly_start()
            self.vwap_sessions[symbol]['hourly'] = {'volume': 0, 'notional': 0, 'prices': [], 'start': self.hourly_start}
        
        # Update each timeframe
        for timeframe in ['session', 'daily', 'weekly', 'hourly']:
            session = self.vwap_sessions[symbol][timeframe]
            
            # Add trade to session
            session['volume'] += trade['volume']
            session['notional'] += trade['notional']
            session['prices'].append(trade['price'])
            
            # Calculate VWAP
            if session['volume'] > 0:
                vwap = session['notional'] / session['volume']
                self.vwap_values[symbol][timeframe] = vwap
                
                # Calculate standard deviation for bands
                if len(session['prices']) > 1:
                    prices_array = np.array(session['prices'])
                    std_dev = np.std(prices_array)
                    self.vwap_std_devs[symbol][timeframe] = std_dev
                    
                    # Calculate z-score
                    if std_dev > 0:
                        z_score = (trade['price'] - vwap) / std_dev
                        self.vwap_z_scores[symbol][timeframe] = z_score
    
    async def fetch_recent_trades(self, symbol: str):
        """Fetch recent trades to initialize VWAP"""
        try:
            # For initialization, we would fetch recent candle data
            # and approximate VWAP from OHLCV data
            candles = self.info.candles_snapshot(
                coin=symbol,
                interval='1m',
                startTime=self.session_start,
                endTime=int(time.time() * 1000)
            )
            
            if candles:
                for candle in candles[-60:]:  # Last 60 minutes
                    # Approximate trade from candle
                    typical_price = (candle['h'] + candle['l'] + candle['c']) / 3
                    volume = candle['v']
                    
                    trade_data = {
                        'time': candle['t'],
                        'price': typical_price,
                        'volume': volume,
                        'notional': typical_price * volume
                    }
                    
                    self.update_vwap(symbol, trade_data)
                    
        except Exception as e:
            print(f"[VWAP] Error fetching trades for {symbol}: {e}")
    
    def calculate_vwap_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate comprehensive VWAP metrics"""
        current_px = self.current_price.get(symbol, 0)
        
        # Get VWAP values
        vwaps = self.vwap_values.get(symbol, {})
        z_scores = self.vwap_z_scores.get(symbol, {})
        std_devs = self.vwap_std_devs.get(symbol, {})
        
        # Calculate deviations
        session_vwap = vwaps.get('session', current_px)
        daily_vwap = vwaps.get('daily', current_px)
        weekly_vwap = vwaps.get('weekly', current_px)
        hourly_vwap = vwaps.get('hourly', current_px)
        
        # Deviation percentages
        session_dev = ((current_px - session_vwap) / session_vwap * 100) if session_vwap > 0 else 0
        daily_dev = ((current_px - daily_vwap) / daily_vwap * 100) if daily_vwap > 0 else 0
        weekly_dev = ((current_px - weekly_vwap) / weekly_vwap * 100) if weekly_vwap > 0 else 0
        hourly_dev = ((current_px - hourly_vwap) / hourly_vwap * 100) if hourly_vwap > 0 else 0
        
        # Determine position relative to VWAP
        if abs(session_dev) < 0.1:
            position = 'at_vwap'
        elif session_dev > 0:
            position = 'above_vwap'
        else:
            position = 'below_vwap'
        
        # Trend based on multiple timeframes
        above_count = sum([
            1 if current_px > session_vwap else 0,
            1 if current_px > daily_vwap else 0,
            1 if current_px > weekly_vwap else 0
        ])
        
        if above_count >= 3:
            trend = 'strong_bullish'
        elif above_count >= 2:
            trend = 'bullish'
        elif above_count >= 1:
            trend = 'neutral'
        else:
            trend = 'bearish'
        
        # VWAP bands (1 and 2 standard deviations)
        session_std = std_devs.get('session', 0)
        upper_band_1 = session_vwap + session_std
        upper_band_2 = session_vwap + (2 * session_std)
        lower_band_1 = session_vwap - session_std
        lower_band_2 = session_vwap - (2 * session_std)
        
        return {
            'symbol': symbol,
            'current_price': current_px,
            'vwap_session': session_vwap,
            'vwap_daily': daily_vwap,
            'vwap_weekly': weekly_vwap,
            'vwap_hourly': hourly_vwap,
            'z_score_session': z_scores.get('session', 0),
            'z_score_daily': z_scores.get('daily', 0),
            'z_score_weekly': z_scores.get('weekly', 0),
            'deviation_session_pct': session_dev,
            'deviation_daily_pct': daily_dev,
            'deviation_weekly_pct': weekly_dev,
            'std_dev_session': session_std,
            'upper_band_1': upper_band_1,
            'upper_band_2': upper_band_2,
            'lower_band_1': lower_band_1,
            'lower_band_2': lower_band_2,
            'position': position,
            'trend': trend,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Update VWAP data for all symbols"""
        # Fetch latest trades for all symbols
        for symbol in self.symbols:
            await self.fetch_recent_trades(symbol)
    
    async def save_to_supabase(self):
        """Save VWAP data to Supabase"""
        for symbol in self.symbols:
            metrics = self.calculate_vwap_metrics(symbol)
            
            # Update current table
            try:
                self.supabase.table('hl_vwap_current').upsert({
                    'symbol': symbol,
                    **metrics
                }).execute()
            except Exception as e:
                print(f"[VWAP] Error saving current data: {e}")
            
            # Save snapshots every 5 minutes
            current_time = time.time()
            if current_time - self.last_snapshot >= 300:
                try:
                    self.supabase.table('hl_vwap_snapshots').insert({
                        'symbol': symbol,
                        'price': metrics['current_price'],
                        'vwap_session': metrics['vwap_session'],
                        'vwap_daily': metrics['vwap_daily'],
                        'z_score': metrics['z_score_session'],
                        'deviation_pct': metrics['deviation_session_pct'],
                        'position': metrics['position'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[VWAP] Error saving snapshot: {e}")
        
        if time.time() - self.last_snapshot >= 300:
            self.last_snapshot = time.time()
            print(f"[VWAP] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 10):
        """Run the VWAP tracker"""
        print(f"[VWAP] Starting VWAP tracker")
        print(f"[VWAP] Tracking: {', '.join(self.symbols)}")
        print(f"[VWAP] Update interval: {update_interval} seconds")
        print("=" * 60)
        
        # Initialize with recent trades
        for symbol in self.symbols:
            await self.fetch_recent_trades(symbol)
        
        # Subscribe to WebSocket feeds
        self.subscribe_to_trades()
        
        # Give WebSocket time to connect
        await asyncio.sleep(2)
        
        while True:
            try:
                # Save to Supabase
                await self.save_to_supabase()
                
                # Display current metrics
                print(f"\n[VWAP Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    metrics = self.calculate_vwap_metrics(symbol)
                    print(f"  {symbol}: Price=${metrics['current_price']:.2f}, "
                          f"VWAP=${metrics['vwap_session']:.2f}, "
                          f"Dev={metrics['deviation_session_pct']:+.2f}%, "
                          f"Z={metrics['z_score_session']:+.2f}, "
                          f"{metrics['position']}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[VWAP] Error in main loop: {e}")
                await asyncio.sleep(5)


async def main():
    """Run VWAP indicator"""
    indicator = VWAPIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=10)  # Update every 10 seconds
    except KeyboardInterrupt:
        print("\n[VWAP] Stopped by user")
    except Exception as e:
        print(f"[VWAP] Fatal error: {e}")


if __name__ == "__main__":
    print("VWAP Indicator for Hyperliquid")
    print("Updates every 10 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())