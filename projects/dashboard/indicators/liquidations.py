"""
Liquidations Tracker for Hyperliquid
Tracks liquidation events and calculates liquidation intensity
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import os
from dotenv import load_dotenv
import sys
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


class LiquidationsIndicator:
    """
    Tracks Liquidation metrics:
    - Recent liquidation events
    - Liquidation volume (long vs short)
    - Liquidation intensity score
    - Liquidation clusters/levels
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Data storage
        self.liquidations_5m = defaultdict(lambda: deque(maxlen=100))  # Last 100 liquidations
        self.liquidations_1h = defaultdict(lambda: deque(maxlen=500))
        self.liquidations_24h = defaultdict(list)
        
        # Aggregated metrics
        self.liq_volume_long = defaultdict(float)
        self.liq_volume_short = defaultdict(float)
        self.liq_intensity = defaultdict(float)
        self.liq_count = defaultdict(int)
        
        # WebSocket subscriptions
        self.subscriptions = {}
        
        # Timing
        self.last_update = time.time()
        self.last_cleanup = time.time()
        
    def subscribe_to_liquidations(self):
        """Subscribe to liquidation events via WebSocket"""
        # WebSocket disabled for now due to module conflicts
        print("[Liquidations] Using polling mode (WebSocket disabled)")
        return
    
    def process_liquidation_data(self, symbol: str, data: Any):
        """Process incoming trade data to detect liquidations"""
        try:
            if isinstance(data, dict) and 'data' in data:
                trades = data['data']
                
                for trade in trades:
                    # Check if trade is a liquidation
                    # In Hyperliquid, liquidations are marked in trade data
                    if trade.get('liquidation') or trade.get('liq'):
                        self.add_liquidation(symbol, trade)
                        
        except Exception as e:
            print(f"[Liquidations] Error processing data for {symbol}: {e}")
    
    def add_liquidation(self, symbol: str, trade: Dict):
        """Add a liquidation event"""
        try:
            liq_event = {
                'time': time.time(),
                'price': float(trade.get('px', 0)),
                'size': float(trade.get('sz', 0)),
                'side': 'long' if trade.get('side') == 'B' else 'short',
                'value': float(trade.get('px', 0)) * float(trade.get('sz', 0))
            }
            
            # Add to time-based storage
            self.liquidations_5m[symbol].append(liq_event)
            self.liquidations_1h[symbol].append(liq_event)
            self.liquidations_24h[symbol].append(liq_event)
            
            # Update aggregated metrics
            if liq_event['side'] == 'long':
                self.liq_volume_long[symbol] += liq_event['value']
            else:
                self.liq_volume_short[symbol] += liq_event['value']
                
            self.liq_count[symbol] += 1
            
            # Print alert for large liquidations
            if liq_event['value'] > 100000:  # $100k+
                print(f"\n[LIQUIDATION ALERT] {symbol}")
                print(f"  Side: {liq_event['side'].upper()}")
                print(f"  Size: ${liq_event['value']:,.0f}")
                print(f"  Price: ${liq_event['price']:,.2f}")
                
        except Exception as e:
            print(f"[Liquidations] Error adding liquidation: {e}")
    
    async def fetch_recent_liquidations(self):
        """Fetch recent liquidation data from API if needed"""
        # This can be used as fallback if WebSocket misses events
        # Hyperliquid doesn't have a direct liquidations endpoint,
        # but we can analyze trades for liquidation patterns
        pass
    
    def calculate_liquidation_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate liquidation metrics for a symbol"""
        current_time = time.time()
        
        # Clean old data
        self.clean_old_liquidations(symbol)
        
        # Get liquidations for different timeframes
        liq_5m = [l for l in self.liquidations_5m[symbol] 
                  if current_time - l['time'] <= 300]
        liq_1h = [l for l in self.liquidations_1h[symbol] 
                  if current_time - l['time'] <= 3600]
        liq_24h = [l for l in self.liquidations_24h[symbol] 
                   if current_time - l['time'] <= 86400]
        
        # Calculate volumes
        volume_5m_long = sum(l['value'] for l in liq_5m if l['side'] == 'long')
        volume_5m_short = sum(l['value'] for l in liq_5m if l['side'] == 'short')
        volume_1h_long = sum(l['value'] for l in liq_1h if l['side'] == 'long')
        volume_1h_short = sum(l['value'] for l in liq_1h if l['side'] == 'short')
        volume_24h_long = sum(l['value'] for l in liq_24h if l['side'] == 'long')
        volume_24h_short = sum(l['value'] for l in liq_24h if l['side'] == 'short')
        
        # Calculate intensity (normalized by time)
        intensity_5m = (len(liq_5m) / 5) if liq_5m else 0  # Per minute
        intensity_1h = (len(liq_1h) / 60) if liq_1h else 0
        intensity_24h = (len(liq_24h) / 1440) if liq_24h else 0
        
        # Calculate ratio
        total_5m = volume_5m_long + volume_5m_short
        ratio_5m = (volume_5m_long / total_5m * 100) if total_5m > 0 else 50
        
        total_1h = volume_1h_long + volume_1h_short
        ratio_1h = (volume_1h_long / total_1h * 100) if total_1h > 0 else 50
        
        # Determine trend
        if intensity_5m > intensity_1h * 2:
            trend = 'accelerating'
        elif intensity_5m < intensity_1h * 0.5:
            trend = 'decelerating'
        else:
            trend = 'stable'
        
        # Determine bias
        if ratio_5m > 70:
            bias = 'long_squeeze'  # Many longs liquidated
        elif ratio_5m < 30:
            bias = 'short_squeeze'  # Many shorts liquidated
        else:
            bias = 'balanced'
        
        return {
            'symbol': symbol,
            'count_5m': len(liq_5m),
            'count_1h': len(liq_1h),
            'count_24h': len(liq_24h),
            'volume_5m_long': volume_5m_long,
            'volume_5m_short': volume_5m_short,
            'volume_1h_long': volume_1h_long,
            'volume_1h_short': volume_1h_short,
            'volume_24h_long': volume_24h_long,
            'volume_24h_short': volume_24h_short,
            'intensity_score': intensity_5m * 10,  # Normalized score
            'long_ratio_5m': ratio_5m,
            'long_ratio_1h': ratio_1h,
            'trend': trend,
            'bias': bias,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    def clean_old_liquidations(self, symbol: str):
        """Remove old liquidation data"""
        current_time = time.time()
        
        # Clean 24h data
        self.liquidations_24h[symbol] = [
            l for l in self.liquidations_24h[symbol]
            if current_time - l['time'] <= 86400
        ]
    
    async def update(self):
        """Update liquidation data for all symbols (stub for polling mode)"""
        # In polling mode, we don't actively update - data comes from WebSocket or external source
        # This is just a placeholder to satisfy the interface
        pass
    
    async def save_to_supabase(self):
        """Save liquidation data to Supabase"""
        for symbol in self.symbols:
            metrics = self.calculate_liquidation_metrics(symbol)
            
            # Update current table
            try:
                self.supabase.table('hl_liquidations_current').upsert({
                    'symbol': symbol,
                    **metrics
                }).execute()
            except Exception as e:
                print(f"[Liquidations] Error saving current data: {e}")
            
            # Save snapshots every 5 minutes if there's activity
            current_time = time.time()
            if current_time - self.last_update >= 300 and metrics['count_5m'] > 0:
                try:
                    self.supabase.table('hl_liquidations_snapshots').insert({
                        'symbol': symbol,
                        'count': metrics['count_5m'],
                        'volume_long': metrics['volume_5m_long'],
                        'volume_short': metrics['volume_5m_short'],
                        'intensity': metrics['intensity_score'],
                        'bias': metrics['bias'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[Liquidations] Error saving snapshot: {e}")
        
        if current_time - self.last_update >= 300:
            self.last_update = current_time
            print(f"[Liquidations] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 10):
        """Run the liquidations tracker"""
        print(f"[Liquidations] Starting Liquidations tracker")
        print(f"[Liquidations] Tracking: {', '.join(self.symbols)}")
        print(f"[Liquidations] Update interval: {update_interval} seconds")
        print("=" * 60)
        
        # Subscribe to WebSocket feeds
        self.subscribe_to_liquidations()
        
        while True:
            try:
                # Save to Supabase
                await self.save_to_supabase()
                
                # Display current metrics
                print(f"\n[Liquidations Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    metrics = self.calculate_liquidation_metrics(symbol)
                    if metrics['count_5m'] > 0:
                        print(f"  {symbol}: 5m={metrics['count_5m']} liqs, "
                              f"L/S=${metrics['volume_5m_long']:.0f}/${metrics['volume_5m_short']:.0f}, "
                              f"Intensity={metrics['intensity_score']:.1f}, "
                              f"{metrics['bias']}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[Liquidations] Error in main loop: {e}")
                await asyncio.sleep(5)


async def main():
    """Run Liquidations indicator"""
    indicator = LiquidationsIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=10)  # Update every 10 seconds
    except KeyboardInterrupt:
        print("\n[Liquidations] Stopped by user")
    except Exception as e:
        print(f"[Liquidations] Fatal error: {e}")


if __name__ == "__main__":
    print("Liquidations Indicator for Hyperliquid")
    print("Updates every 10 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())