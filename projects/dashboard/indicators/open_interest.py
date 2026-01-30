"""
Open Interest Indicator for Hyperliquid
Tracks OI changes, delta, and trends
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


class OpenInterestIndicator:
    """
    Tracks Open Interest metrics:
    - Current OI per symbol
    - OI delta (1m, 5m, 15m, 1h)
    - OI/Volume ratio
    - OI percentile levels
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Data storage
        self.oi_current = defaultdict(float)
        self.oi_history = defaultdict(lambda: deque(maxlen=3600))  # 1 hour of data
        self.oi_snapshots = defaultdict(list)
        
        # Timing
        self.last_update = time.time()
        self.last_snapshot = time.time()
        
    async def fetch_open_interest(self):
        """Fetch current open interest from Hyperliquid"""
        try:
            # Get metadata and asset contexts once
            response = self.info.meta_and_asset_ctxs()
            
            if not isinstance(response, list) or len(response) != 2:
                print("[OI] Unexpected API response format")
                return {}
            
            meta = response[0]
            ctxs = response[1]
            universe = meta.get('universe', [])
            
            oi_data = {}
            
            # Find our symbols in the universe
            for i, asset_meta in enumerate(universe):
                coin = asset_meta.get('name', '')
                if coin in self.symbols and i < len(ctxs):
                    ctx = ctxs[i]
                    # OI is in number of contracts, get mark price to calculate USD value
                    oi_contracts = float(ctx.get('openInterest', 0))
                    mark_px = float(ctx.get('markPx', 0))
                    
                    # Calculate OI in USD millions
                    oi_usd_millions = (oi_contracts * mark_px) / 1_000_000
                    oi_data[coin] = oi_usd_millions
                    
            return oi_data
        except Exception as e:
            print(f"[OI] Error fetching open interest: {e}")
            return {}
    
    def calculate_oi_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate OI metrics for a symbol"""
        current_oi = self.oi_current[symbol]
        history = list(self.oi_history[symbol])
        
        if not history:
            return {
                'symbol': symbol,
                'oi_current': current_oi,
                'oi_delta_1m': 0,
                'oi_delta_5m': 0,
                'oi_delta_15m': 0,
                'oi_delta_1h': 0,
                'oi_change_pct_1h': 0,
                'trend': 'neutral'
            }
        
        current_time = time.time()
        
        # Calculate deltas
        oi_1m_ago = current_oi
        oi_5m_ago = current_oi
        oi_15m_ago = current_oi
        oi_1h_ago = current_oi
        
        for entry in reversed(history):
            time_diff = current_time - entry['time']
            
            if time_diff >= 60 and oi_1m_ago == current_oi:
                oi_1m_ago = entry['oi']
            if time_diff >= 300 and oi_5m_ago == current_oi:
                oi_5m_ago = entry['oi']
            if time_diff >= 900 and oi_15m_ago == current_oi:
                oi_15m_ago = entry['oi']
            if time_diff >= 3600:
                oi_1h_ago = entry['oi']
                break
        
        # Calculate changes
        oi_delta_1m = current_oi - oi_1m_ago
        oi_delta_5m = current_oi - oi_5m_ago
        oi_delta_15m = current_oi - oi_15m_ago
        oi_delta_1h = current_oi - oi_1h_ago
        
        # Calculate percentage change
        oi_change_pct_1h = ((current_oi - oi_1h_ago) / oi_1h_ago * 100) if oi_1h_ago > 0 else 0
        
        # Determine trend
        if oi_delta_5m > 0 and oi_delta_15m > 0:
            trend = 'increasing'
        elif oi_delta_5m < 0 and oi_delta_15m < 0:
            trend = 'decreasing'
        else:
            trend = 'neutral'
        
        return {
            'symbol': symbol,
            'oi_current': current_oi,
            'oi_delta_1m': oi_delta_1m,
            'oi_delta_5m': oi_delta_5m,
            'oi_delta_15m': oi_delta_15m,
            'oi_delta_1h': oi_delta_1h,
            'oi_change_pct_1h': oi_change_pct_1h,
            'trend': trend,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Update OI data"""
        oi_data = await self.fetch_open_interest()
        
        for symbol, oi_value in oi_data.items():
            # Update current OI
            self.oi_current[symbol] = oi_value
            
            # Add to history
            self.oi_history[symbol].append({
                'time': time.time(),
                'oi': oi_value
            })
    
    async def save_to_supabase(self):
        """Save OI data to Supabase"""
        current_time = time.time()
        
        for symbol in self.symbols:
            if symbol not in self.oi_current:
                continue
                
            metrics = self.calculate_oi_metrics(symbol)
            
            # Update current table
            try:
                self.supabase.table('hl_oi_current').upsert({
                    'symbol': symbol,
                    **metrics
                }).execute()
            except Exception as e:
                print(f"[OI] Error saving current data: {e}")
            
            # Save snapshots every 5 minutes
            if current_time - self.last_snapshot >= 300:
                try:
                    self.supabase.table('hl_oi_snapshots').insert({
                        'symbol': symbol,
                        'oi': self.oi_current[symbol],
                        'oi_delta_5m': metrics['oi_delta_5m'],
                        'oi_change_pct_1h': metrics['oi_change_pct_1h'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[OI] Error saving snapshot: {e}")
        
        if current_time - self.last_snapshot >= 300:
            self.last_snapshot = current_time
            print(f"[OI] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 30):
        """Run the OI tracker"""
        print(f"[OI] Starting Open Interest tracker")
        print(f"[OI] Tracking: {', '.join(self.symbols)}")
        print(f"[OI] Update interval: {update_interval} seconds")
        print("=" * 60)
        
        while True:
            try:
                # Update OI data
                await self.update()
                
                # Save to Supabase
                await self.save_to_supabase()
                
                # Display current metrics
                print(f"\n[OI Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    if symbol in self.oi_current:
                        metrics = self.calculate_oi_metrics(symbol)
                        print(f"  {symbol}: OI={metrics['oi_current']:.2f}M, "
                              f"Δ5m={metrics['oi_delta_5m']:+.2f}M, "
                              f"Δ1h%={metrics['oi_change_pct_1h']:+.1f}%, "
                              f"Trend={metrics['trend']}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[OI] Error in main loop: {e}")
                await asyncio.sleep(5)


async def main():
    """Run Open Interest indicator"""
    indicator = OpenInterestIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=30)  # Update every 30 seconds
    except KeyboardInterrupt:
        print("\n[OI] Stopped by user")
    except Exception as e:
        print(f"[OI] Fatal error: {e}")


if __name__ == "__main__":
    print("Open Interest Indicator for Hyperliquid")
    print("Updates every 30 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())