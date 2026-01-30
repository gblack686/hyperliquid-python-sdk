"""
CVD Calculator with Supabase Integration
Saves snapshots every 5 seconds instead of individual trades
"""

import json
import asyncio
import websockets
from datetime import datetime, timedelta
from collections import deque, defaultdict
from typing import Dict, List, Optional
import time
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


class CVDSupabaseCalculator:
    """
    CVD Calculator that saves aggregated data to Supabase
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        
        # Initialize Supabase
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # CVD tracking
        self.cvd = defaultdict(float)
        self.cvd_history = defaultdict(lambda: deque(maxlen=1200))  # 5 min of 1-sec data
        self.trades_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.stats = defaultdict(lambda: {
            'total_trades': 0,
            'buy_volume': 0.0,
            'sell_volume': 0.0,
            'last_price': 0.0,
            'start_time': time.time(),
            'last_snapshot': time.time()
        })
        
        self.running = False
        self.ws = None
        self.last_save_time = time.time()
        
    async def process_trade(self, trade: dict):
        """Process individual trade and update CVD"""
        try:
            symbol = trade.get('coin', '')
            if symbol not in self.symbols:
                return
                
            price = float(trade.get('px', 0))
            size = float(trade.get('sz', 0))
            side = trade.get('side', '')
            timestamp = time.time()
            
            # Update CVD
            if side == 'B':
                self.cvd[symbol] += size
                self.stats[symbol]['buy_volume'] += size * price
            else:
                self.cvd[symbol] -= size
                self.stats[symbol]['sell_volume'] += size * price
                
            self.stats[symbol]['total_trades'] += 1
            self.stats[symbol]['last_price'] = price
            
            # Store in history for calculating changes
            self.cvd_history[symbol].append({
                'time': timestamp,
                'cvd': self.cvd[symbol]
            })
            
            # Store trade (in memory only)
            self.trades_buffer[symbol].append({
                'time': timestamp,
                'price': price,
                'size': size,
                'side': side
            })
                
        except Exception as e:
            print(f"[CVD] Error processing trade: {e}")
    
    def calculate_cvd_metrics(self, symbol: str) -> Dict:
        """Calculate CVD metrics for a symbol"""
        history = list(self.cvd_history[symbol])
        if len(history) < 2:
            return None
            
        current_time = time.time()
        current_cvd = self.cvd[symbol]
        
        # Find CVD values at different time points
        cvd_1m_ago = current_cvd
        cvd_5m_ago = current_cvd
        
        for entry in reversed(history):
            time_diff = current_time - entry['time']
            if time_diff >= 60 and cvd_1m_ago == current_cvd:
                cvd_1m_ago = entry['cvd']
            if time_diff >= 300:
                cvd_5m_ago = entry['cvd']
                break
        
        # Calculate changes
        cvd_change_1m = current_cvd - cvd_1m_ago
        cvd_change_5m = current_cvd - cvd_5m_ago
        
        # Calculate velocity (CVD change per minute)
        elapsed = current_time - self.stats[symbol]['start_time']
        cvd_velocity = (current_cvd / (elapsed / 60)) if elapsed > 0 else 0
        
        # Calculate buy ratio
        total_volume = self.stats[symbol]['buy_volume'] + self.stats[symbol]['sell_volume']
        buy_ratio = (self.stats[symbol]['buy_volume'] / total_volume * 100) if total_volume > 0 else 50
        
        # Determine trend
        if cvd_change_1m > 0 and cvd_change_5m > 0:
            trend = 'bullish'
        elif cvd_change_1m < 0 and cvd_change_5m < 0:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        return {
            'cvd': current_cvd,
            'cvd_change_1m': cvd_change_1m,
            'cvd_change_5m': cvd_change_5m,
            'cvd_velocity': cvd_velocity,
            'buy_volume': self.stats[symbol]['buy_volume'],
            'sell_volume': self.stats[symbol]['sell_volume'],
            'trade_count': self.stats[symbol]['total_trades'],
            'last_price': self.stats[symbol]['last_price'],
            'buy_ratio': buy_ratio,
            'trend': trend
        }
    
    async def save_to_supabase(self):
        """Save CVD snapshots to Supabase"""
        try:
            current_time = time.time()
            
            for symbol in self.symbols:
                if self.stats[symbol]['total_trades'] == 0:
                    continue
                    
                metrics = self.calculate_cvd_metrics(symbol)
                if not metrics:
                    continue
                
                # Update current CVD table (upsert)
                current_data = {
                    'symbol': symbol,
                    'cvd': float(metrics['cvd']),
                    'cvd_1m': float(metrics['cvd_change_1m']),
                    'cvd_5m': float(metrics['cvd_change_5m']),
                    'buy_volume': float(metrics['buy_volume']),
                    'sell_volume': float(metrics['sell_volume']),
                    'trade_count': metrics['trade_count'],
                    'last_price': float(metrics['last_price']),
                    'buy_ratio': float(metrics['buy_ratio']),
                    'trend': metrics['trend'],
                    'updated_at': datetime.now().isoformat()
                }
                
                # Upsert to current table
                self.supabase.table('hl_cvd_current').upsert(current_data).execute()
                
                # Only save snapshot if 5 seconds have passed
                if current_time - self.stats[symbol]['last_snapshot'] >= 5:
                    snapshot_data = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'cvd': float(metrics['cvd']),
                        'cvd_change_1m': float(metrics['cvd_change_1m']),
                        'cvd_change_5m': float(metrics['cvd_change_5m']),
                        'cvd_velocity': float(metrics['cvd_velocity']),
                        'buy_volume': float(metrics['buy_volume']),
                        'sell_volume': float(metrics['sell_volume']),
                        'trade_count': metrics['trade_count'],
                        'last_price': float(metrics['last_price']),
                        'buy_ratio': float(metrics['buy_ratio'])
                    }
                    
                    # Insert snapshot
                    self.supabase.table('hl_cvd_snapshots').insert(snapshot_data).execute()
                    self.stats[symbol]['last_snapshot'] = current_time
                    
            print(f"[CVD] Saved snapshots to Supabase at {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"[CVD] Error saving to Supabase: {e}")
    
    async def listen_to_trades(self):
        """Listen to WebSocket trades"""
        try:
            async with websockets.connect(self.ws_url) as ws:
                self.ws = ws
                print("[CVD] Connected to WebSocket")
                
                # Subscribe to all symbols
                for symbol in self.symbols:
                    subscribe_msg = {
                        "method": "subscribe",
                        "subscription": {"type": "trades", "coin": symbol}
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    print(f"[CVD] Subscribed to {symbol}")
                
                # Process messages
                while self.running:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        data = json.loads(message)
                        
                        if 'data' in data:
                            for trade in data.get('data', []):
                                if 'coin' in trade:
                                    await self.process_trade(trade)
                                    
                    except asyncio.TimeoutError:
                        continue
                    except websockets.ConnectionClosed:
                        print("[CVD] Connection closed, reconnecting...")
                        break
                        
        except Exception as e:
            print(f"[CVD] WebSocket error: {e}")
            if self.running:
                await asyncio.sleep(5)  # Wait before reconnecting
    
    async def periodic_save(self):
        """Save data to Supabase every 5 seconds"""
        while self.running:
            await asyncio.sleep(5)
            await self.save_to_supabase()
    
    async def print_status(self):
        """Print status updates"""
        while self.running:
            await asyncio.sleep(10)  # Status every 10 seconds
            
            print(f"\n[Status] {datetime.now().strftime('%H:%M:%S')}")
            for symbol in self.symbols:
                if self.stats[symbol]['total_trades'] > 0:
                    metrics = self.calculate_cvd_metrics(symbol)
                    if metrics:
                        print(f"  {symbol}: CVD={metrics['cvd']:+.2f}, "
                              f"Trades={metrics['trade_count']}, "
                              f"Buy%={metrics['buy_ratio']:.1f}, "
                              f"Trend={metrics['trend']}")
    
    async def run(self):
        """Run the CVD calculator continuously"""
        self.running = True
        print(f"[CVD] Starting CVD Calculator with Supabase integration")
        print(f"[CVD] Tracking: {', '.join(self.symbols)}")
        print(f"[CVD] Saving snapshots every 5 seconds")
        print("=" * 60)
        
        # Run all tasks in parallel
        tasks = [
            asyncio.create_task(self.listen_to_trades()),
            asyncio.create_task(self.periodic_save()),
            asyncio.create_task(self.print_status())
        ]
        
        try:
            # Run until interrupted
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n[CVD] Shutting down...")
        finally:
            self.running = False
            
            # Final save
            await self.save_to_supabase()
            
            # Cancel tasks
            for task in tasks:
                task.cancel()
            
            # Close WebSocket
            if self.ws:
                await self.ws.close()
            
            print("[CVD] Shutdown complete")
    
    def get_latest_data(self) -> Dict:
        """Get latest CVD data for all symbols"""
        result = {}
        for symbol in self.symbols:
            if self.stats[symbol]['total_trades'] > 0:
                metrics = self.calculate_cvd_metrics(symbol)
                if metrics:
                    result[symbol] = metrics
        return result


async def main():
    """Run CVD calculator with Supabase integration"""
    calculator = CVDSupabaseCalculator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await calculator.run()
    except KeyboardInterrupt:
        print("\n[CVD] Interrupted by user")
    except Exception as e:
        print(f"[CVD] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("CVD Calculator with Supabase Integration")
    print("Data will be saved to Supabase every 5 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())