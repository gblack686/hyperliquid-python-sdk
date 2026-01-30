"""
Funding Rate Indicator for Hyperliquid
Tracks funding rates and predicted funding
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


class FundingRateIndicator:
    """
    Tracks Funding Rate metrics:
    - Current funding rate
    - Predicted funding rate  
    - Funding history (8h, 24h)
    - Cumulative funding
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Data storage
        self.funding_current = defaultdict(float)
        self.funding_predicted = defaultdict(float)
        self.funding_history = defaultdict(lambda: deque(maxlen=24))  # 24 hours of hourly data
        self.cumulative_funding = defaultdict(float)
        
        # Timing
        self.last_update = time.time()
        self.last_snapshot = time.time()
        
    async def fetch_funding_rates(self):
        """Fetch current funding rates from Hyperliquid"""
        try:
            # Get metadata and asset contexts once
            response = self.info.meta_and_asset_ctxs()
            
            if not isinstance(response, list) or len(response) != 2:
                print("[Funding] Unexpected API response format")
                return {}
            
            meta = response[0]
            ctxs = response[1]
            universe = meta.get('universe', [])
            
            funding_data = {}
            
            # Find our symbols in the universe
            for i, asset_meta in enumerate(universe):
                coin = asset_meta.get('name', '')
                if coin in self.symbols and i < len(ctxs):
                    try:
                        ctx = ctxs[i]
                        
                        # Get current funding rate from asset context
                        funding_rate = float(ctx.get('funding', 0)) * 10000  # Convert to basis points
                        
                        # Get predicted funding (use premium if available)
                        premium = float(ctx.get('premium', 0)) * 10000 if ctx.get('premium') else funding_rate
                        
                        funding_data[coin] = {
                            'current': funding_rate,
                            'predicted': premium,
                            'time': int(time.time() * 1000)
                        }
                        
                        # Initialize history with current value if empty
                        if coin not in self.funding_history or not self.funding_history[coin]:
                            self.funding_history[coin] = deque([{
                                'rate': funding_rate,
                                'time': int(time.time())
                            }], maxlen=24)
                        else:
                            # Add to history
                            self.funding_history[coin].append({
                                'rate': funding_rate,
                                'time': int(time.time())
                            })
                            
                    except Exception as e:
                        print(f"[Funding] Error processing {coin}: {e}")
                    
            return funding_data
        except Exception as e:
            print(f"[Funding] Error fetching funding rates: {e}")
            return {}
    
    def calculate_funding_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate funding metrics for a symbol"""
        current = self.funding_current.get(symbol, 0)
        predicted = self.funding_predicted.get(symbol, 0)
        history = list(self.funding_history[symbol])
        
        # Calculate cumulative funding (8h and 24h)
        cumulative_8h = sum(h['rate'] for h in history[-8:]) if len(history) >= 8 else 0
        cumulative_24h = sum(h['rate'] for h in history) if history else 0
        
        # Calculate average funding
        avg_funding = cumulative_24h / len(history) if history else 0
        
        # Determine trend
        if len(history) >= 3:
            recent_avg = sum(h['rate'] for h in history[-3:]) / 3
            older_avg = sum(h['rate'] for h in history[-6:-3]) / 3 if len(history) >= 6 else avg_funding
            
            if recent_avg > older_avg + 1:  # More than 1bp increase
                trend = 'increasing'
            elif recent_avg < older_avg - 1:  # More than 1bp decrease
                trend = 'decreasing'
            else:
                trend = 'neutral'
        else:
            trend = 'neutral'
        
        # Funding sentiment
        if current > 10:  # > 10 basis points
            sentiment = 'very_bullish'
        elif current > 5:
            sentiment = 'bullish'
        elif current < -10:
            sentiment = 'very_bearish'
        elif current < -5:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'
        
        return {
            'symbol': symbol,
            'funding_current': current,
            'funding_predicted': predicted,
            'funding_8h_cumulative': cumulative_8h,
            'funding_24h_cumulative': cumulative_24h,
            'funding_avg_24h': avg_funding,
            'trend': trend,
            'sentiment': sentiment,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Update funding data"""
        funding_data = await self.fetch_funding_rates()
        
        for symbol, data in funding_data.items():
            # Update current funding
            self.funding_current[symbol] = data['current']
            self.funding_predicted[symbol] = data['predicted']
            
            # Update cumulative
            self.cumulative_funding[symbol] += data['current'] / 3  # Funding every 8 hours
    
    async def save_to_supabase(self):
        """Save funding data to Supabase"""
        current_time = time.time()
        
        for symbol in self.symbols:
            if symbol not in self.funding_current:
                continue
                
            metrics = self.calculate_funding_metrics(symbol)
            
            # Update current table
            try:
                self.supabase.table('hl_funding_current').upsert({
                    'symbol': symbol,
                    **metrics
                }).execute()
            except Exception as e:
                print(f"[Funding] Error saving current data: {e}")
            
            # Save snapshots every hour
            if current_time - self.last_snapshot >= 3600:
                try:
                    self.supabase.table('hl_funding_snapshots').insert({
                        'symbol': symbol,
                        'funding_rate': self.funding_current[symbol],
                        'funding_predicted': self.funding_predicted[symbol],
                        'cumulative_24h': metrics['funding_24h_cumulative'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[Funding] Error saving snapshot: {e}")
        
        if current_time - self.last_snapshot >= 3600:
            self.last_snapshot = current_time
            print(f"[Funding] Saved hourly snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 300):
        """Run the funding rate tracker"""
        print(f"[Funding] Starting Funding Rate tracker")
        print(f"[Funding] Tracking: {', '.join(self.symbols)}")
        print(f"[Funding] Update interval: {update_interval} seconds")
        print("=" * 60)
        
        while True:
            try:
                # Update funding data
                await self.update()
                
                # Save to Supabase
                await self.save_to_supabase()
                
                # Display current metrics
                print(f"\n[Funding Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    if symbol in self.funding_current:
                        metrics = self.calculate_funding_metrics(symbol)
                        print(f"  {symbol}: Rate={metrics['funding_current']:+.2f}bp, "
                              f"Pred={metrics['funding_predicted']:+.2f}bp, "
                              f"24h={metrics['funding_24h_cumulative']:+.1f}bp, "
                              f"{metrics['sentiment']}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[Funding] Error in main loop: {e}")
                await asyncio.sleep(30)


async def main():
    """Run Funding Rate indicator"""
    indicator = FundingRateIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=300)  # Update every 5 minutes
    except KeyboardInterrupt:
        print("\n[Funding] Stopped by user")
    except Exception as e:
        print(f"[Funding] Fatal error: {e}")


if __name__ == "__main__":
    print("Funding Rate Indicator for Hyperliquid")
    print("Updates every 5 minutes")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())