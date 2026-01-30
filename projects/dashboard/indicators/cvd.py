"""
CVD (Cumulative Volume Delta) Indicator for Hyperliquid
Tracks the cumulative difference between buy and sell volume
"""

import asyncio
import json
import time
import websockets
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional
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


class CVDIndicator:
    """
    Tracks Cumulative Volume Delta (CVD) metrics:
    - Real-time CVD calculation from trade flow
    - Buy vs Sell volume tracking
    - CVD rate of change (1min, 5min, 15min)
    - Volume-weighted CVD
    - CVD divergence detection
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # CVD tracking
        self.cvd = defaultdict(float)
        self.cvd_history = defaultdict(lambda: deque(maxlen=1800))  # 30 min of 1-sec data
        self.trades_buffer = defaultdict(lambda: deque(maxlen=1000))
        
        # Volume tracking
        self.buy_volume = defaultdict(float)
        self.sell_volume = defaultdict(float)
        self.total_volume = defaultdict(float)
        
        # Stats
        self.stats = defaultdict(lambda: {
            'total_trades': 0,
            'buy_trades': 0,
            'sell_trades': 0,
            'last_price': 0.0,
            'start_time': time.time(),
            'last_update': time.time()
        })
        
        # WebSocket connection
        self.ws = None
        self.running = False
        self.last_save_time = time.time()
        
        # Timing
        self.last_snapshot = time.time()
    
    async def connect_websocket(self):
        """Connect to Hyperliquid WebSocket for trade data"""
        try:
            self.ws = await websockets.connect(self.ws_url)
            
            # Subscribe to trades for all symbols
            for symbol in self.symbols:
                subscribe_msg = {
                    "method": "subscribe",
                    "subscription": {
                        "type": "trades",
                        "coin": symbol
                    }
                }
                await self.ws.send(json.dumps(subscribe_msg))
                print(f"[CVD] Subscribed to {symbol} trades")
            
            return True
            
        except Exception as e:
            print(f"[CVD] WebSocket connection error: {e}")
            return False
    
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
                self.buy_volume[symbol] += size
                self.stats[symbol]['buy_trades'] += 1
            else:
                self.cvd[symbol] -= size
                self.sell_volume[symbol] += size
                self.stats[symbol]['sell_trades'] += 1
            
            self.total_volume[symbol] += size
            self.stats[symbol]['total_trades'] += 1
            self.stats[symbol]['last_price'] = price
            self.stats[symbol]['last_update'] = timestamp
            
            # Store in history
            self.cvd_history[symbol].append({
                'time': timestamp,
                'cvd': self.cvd[symbol],
                'price': price
            })
            
            # Store trade
            self.trades_buffer[symbol].append({
                'time': timestamp,
                'price': price,
                'size': size,
                'side': side
            })
                
        except Exception as e:
            print(f"[CVD] Error processing trade: {e}")
    
    def calculate_cvd_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate comprehensive CVD metrics"""
        history = list(self.cvd_history[symbol])
        if len(history) < 2:
            return self.get_empty_metrics(symbol)
            
        current_time = time.time()
        current_cvd = self.cvd[symbol]
        current_price = self.stats[symbol]['last_price']
        
        # Calculate rate of change
        cvd_1m = current_cvd
        cvd_5m = current_cvd
        cvd_15m = current_cvd
        
        for h in reversed(history):
            time_diff = current_time - h['time']
            if time_diff <= 60 and time_diff > 0:
                cvd_1m = current_cvd - h['cvd']
            elif time_diff <= 300 and time_diff > 0:
                cvd_5m = current_cvd - h['cvd']
            elif time_diff <= 900 and time_diff > 0:
                cvd_15m = current_cvd - h['cvd']
                break
        
        # Calculate volume imbalance
        total_vol = self.total_volume[symbol]
        buy_pct = (self.buy_volume[symbol] / total_vol * 100) if total_vol > 0 else 50
        sell_pct = (self.sell_volume[symbol] / total_vol * 100) if total_vol > 0 else 50
        
        # Detect divergence (simplified)
        price_change_5m = 0
        cvd_change_5m = cvd_5m
        
        for h in history:
            if current_time - h['time'] >= 300:
                price_change_5m = ((current_price - h['price']) / h['price'] * 100) if h['price'] > 0 else 0
                break
        
        # Determine divergence
        divergence = 'none'
        if abs(price_change_5m) > 0.1 and abs(cvd_change_5m) > 100:
            if price_change_5m > 0 and cvd_change_5m < 0:
                divergence = 'bearish'  # Price up, CVD down
            elif price_change_5m < 0 and cvd_change_5m > 0:
                divergence = 'bullish'  # Price down, CVD up
        
        # Calculate CVD velocity (rate of change)
        cvd_velocity = cvd_1m / 60 if cvd_1m != 0 else 0  # CVD per second
        
        # Calculate buy ratio
        buy_ratio = buy_pct / 100 if total_vol > 0 else 0.5
        
        # Determine signal
        signal = 'NEUTRAL'
        if cvd_1m > 500 and buy_pct > 60:
            signal = 'BUY'
        elif cvd_1m < -500 and sell_pct > 60:
            signal = 'SELL'
        elif divergence == 'bullish':
            signal = 'BUY'
        elif divergence == 'bearish':
            signal = 'SELL'
        
        return {
            'symbol': symbol,
            'cvd': current_cvd,
            'cvd_1m': cvd_1m,
            'cvd_5m': cvd_5m,
            'cvd_15m': cvd_15m,
            'cvd_velocity': cvd_velocity,
            'buy_volume': self.buy_volume[symbol],
            'sell_volume': self.sell_volume[symbol],
            'total_volume': total_vol,
            'buy_percentage': buy_pct,
            'sell_percentage': sell_pct,
            'buy_ratio': buy_ratio,
            'divergence': divergence,
            'signal': signal,
            'last_price': current_price,
            'total_trades': self.stats[symbol]['total_trades'],
            'updated_at': datetime.utcnow().isoformat()
        }
    
    def get_empty_metrics(self, symbol: str) -> Dict[str, Any]:
        """Return empty metrics when no data available"""
        return {
            'symbol': symbol,
            'cvd': 0,
            'cvd_1m': 0,
            'cvd_5m': 0,
            'cvd_15m': 0,
            'cvd_velocity': 0,
            'buy_volume': 0,
            'sell_volume': 0,
            'total_volume': 0,
            'buy_percentage': 50,
            'sell_percentage': 50,
            'buy_ratio': 0.5,
            'divergence': 'none',
            'signal': 'NEUTRAL',
            'last_price': 0,
            'total_trades': 0,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Process WebSocket messages"""
        if not self.ws:
            connected = await self.connect_websocket()
            if not connected:
                return
        
        try:
            # Process messages with timeout
            message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
            data = json.loads(message)
            
            # Debug: print the structure of received data
            if data and self.stats[self.symbols[0]]['total_trades'] < 5:
                print(f"[CVD DEBUG] Received: {json.dumps(data)[:200]}")
            
            # Handle different message formats
            if data.get('channel') == 'trades':
                for trade in data.get('data', []):
                    await self.process_trade(trade)
            elif data.get('channel') == 'trade':
                # Single trade format
                await self.process_trade(data.get('data', {}))
            elif 'data' in data and isinstance(data['data'], list):
                # Array of trades without channel
                for trade in data['data']:
                    await self.process_trade(trade)
            elif 'coin' in data and 'px' in data:
                # Direct trade object
                await self.process_trade(data)
                    
        except asyncio.TimeoutError:
            pass  # Normal timeout, no new messages
        except websockets.exceptions.ConnectionClosed:
            print("[CVD] WebSocket connection closed, reconnecting...")
            self.ws = None
        except Exception as e:
            print(f"[CVD] Error processing message: {e}")
    
    async def save_to_supabase(self):
        """Save CVD data to Supabase"""
        for symbol in self.symbols:
            metrics = self.calculate_cvd_metrics(symbol)
            
            # Update current table with correct columns
            try:
                current_data = {
                    'symbol': symbol,
                    'cvd': metrics['cvd'],
                    'cvd_1m': metrics.get('cvd_1m', 0),
                    'cvd_5m': metrics.get('cvd_5m', 0),
                    'buy_volume': metrics['buy_volume'],
                    'sell_volume': metrics['sell_volume'],
                    'trade_count': self.stats[symbol]['total_trades'],
                    'last_price': self.stats[symbol]['last_price'],
                    'buy_ratio': metrics['buy_ratio'],
                    'trend': metrics.get('signal', 'NEUTRAL'),  # Use trend instead of signal
                    'updated_at': datetime.utcnow().isoformat()
                }
                self.supabase.table('hl_cvd_current').upsert(current_data).execute()
                print(f"[CVD] Saved current data for {symbol}: CVD={metrics['cvd']:.2f}")
            except Exception as e:
                print(f"[CVD] Error saving current data: {e}")
            
            # Save snapshots every 5 minutes
            current_time = time.time()
            if current_time - self.last_snapshot >= 300:
                try:
                    snapshot_data = {
                        'symbol': symbol,
                        'timestamp': datetime.utcnow().isoformat(),
                        'cvd': metrics['cvd'],
                        'cvd_change_1m': metrics.get('cvd_1m', 0),
                        'cvd_change_5m': metrics.get('cvd_5m', 0),
                        'cvd_velocity': metrics.get('cvd_velocity', 0),
                        'buy_volume': metrics['buy_volume'],
                        'sell_volume': metrics['sell_volume'],
                        'trade_count': self.stats[symbol]['total_trades'],
                        'last_price': self.stats[symbol]['last_price'],
                        'buy_ratio': metrics['buy_ratio']
                    }
                    self.supabase.table('hl_cvd_snapshots').insert(snapshot_data).execute()
                except Exception as e:
                    print(f"[CVD] Error saving snapshot: {e}")
        
        if time.time() - self.last_snapshot >= 300:
            self.last_snapshot = time.time()
            print(f"[CVD] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 5):
        """Run the CVD tracker"""
        print(f"[CVD] Starting CVD (Cumulative Volume Delta) tracker")
        print(f"[CVD] Tracking: {', '.join(self.symbols)}")
        print(f"[CVD] Update interval: {update_interval} seconds")
        print("=" * 60)
        
        self.running = True
        
        while self.running:
            try:
                # Update data from WebSocket
                await self.update()
                
                # Save to Supabase periodically
                if time.time() - self.last_save_time >= update_interval:
                    await self.save_to_supabase()
                    self.last_save_time = time.time()
                    
                    # Display current metrics
                    print(f"\n[CVD Status] {datetime.now().strftime('%H:%M:%S')}")
                    for symbol in self.symbols:
                        metrics = self.calculate_cvd_metrics(symbol)
                        if metrics['total_trades'] > 0:
                            print(f"  {symbol}: CVD={metrics['cvd']:.2f}, "
                                  f"1m={metrics['cvd_1m']:+.2f}, "
                                  f"Buy={metrics['buy_percentage']:.1f}%, "
                                  f"Signal={metrics['signal']}")
                
                # Small delay to prevent CPU overload
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"[CVD] Error in main loop: {e}")
                await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the CVD tracker"""
        self.running = False
        if self.ws:
            await self.ws.close()


async def main():
    """Run CVD indicator standalone"""
    indicator = CVDIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=5)  # Update every 5 seconds
    except KeyboardInterrupt:
        print("\n[CVD] Stopped by user")
        await indicator.stop()
    except Exception as e:
        print(f"[CVD] Fatal error: {e}")
        await indicator.stop()


if __name__ == "__main__":
    print("CVD (Cumulative Volume Delta) Indicator for Hyperliquid")
    print("Updates every 5 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())