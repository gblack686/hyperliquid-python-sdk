"""
Simple CVD Calculator using Hyperliquid WebSocket directly
No authentication needed for public trade data
"""

import json
import asyncio
import websockets
from datetime import datetime
from collections import deque, defaultdict
from typing import Dict, List, Optional
import time


class SimpleCVDCalculator:
    """
    Real-time CVD calculator using direct WebSocket connection
    """
    
    def __init__(self, symbols: List[str] = None):
        """
        Initialize CVD calculator
        
        Args:
            symbols: List of symbols to track (e.g., ['BTC', 'ETH', 'SOL'])
        """
        self.symbols = symbols or ['BTC', 'ETH', 'SOL']
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        
        # CVD tracking
        self.cvd = defaultdict(float)
        self.trades_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.stats = defaultdict(lambda: {
            'total_trades': 0,
            'buy_volume': 0.0,
            'sell_volume': 0.0,
            'last_price': 0.0,
            'start_time': time.time()
        })
        
        self.running = False
        
    async def handle_message(self, message: str):
        """Process WebSocket message"""
        try:
            data = json.loads(message)
            
            # Check if it's a trade message
            if 'channel' in data and data['channel'] == 'trades':
                if 'data' in data:
                    for trade in data['data']:
                        await self.process_trade(trade)
            elif 'data' in data and isinstance(data['data'], list):
                # Handle array of trades
                for trade in data['data']:
                    if 'coin' in trade and 'px' in trade:
                        await self.process_trade(trade)
                        
        except Exception as e:
            print(f"[CVD] Error handling message: {e}")
            
    async def process_trade(self, trade: dict):
        """Process individual trade"""
        try:
            symbol = trade.get('coin', '')
            if symbol not in self.symbols:
                return
                
            price = float(trade.get('px', 0))
            size = float(trade.get('sz', 0))
            side = trade.get('side', '')
            timestamp = trade.get('time', int(time.time() * 1000))
            
            # Update CVD
            if side == 'B':
                self.cvd[symbol] += size
                self.stats[symbol]['buy_volume'] += size * price
            else:  # side == 'A' or 'S'
                self.cvd[symbol] -= size
                self.stats[symbol]['sell_volume'] += size * price
                
            # Update stats
            self.stats[symbol]['total_trades'] += 1
            self.stats[symbol]['last_price'] = price
            
            # Store trade
            self.trades_buffer[symbol].append({
                'time': timestamp,
                'price': price,
                'size': size,
                'side': side,
                'cvd': self.cvd[symbol]
            })
            
            # Print update every 10 trades
            if self.stats[symbol]['total_trades'] % 10 == 0:
                self.print_status(symbol)
                
        except Exception as e:
            print(f"[CVD] Error processing trade: {e}")
            
    def print_status(self, symbol: str):
        """Print current CVD status"""
        cvd_value = self.cvd[symbol]
        stats = self.stats[symbol]
        
        total_volume = stats['buy_volume'] + stats['sell_volume']
        buy_ratio = (stats['buy_volume'] / total_volume * 100) if total_volume > 0 else 50
        
        # Calculate CVD per minute
        elapsed_minutes = (time.time() - stats['start_time']) / 60
        cvd_per_minute = cvd_value / elapsed_minutes if elapsed_minutes > 0 else 0
        
        print(f"[{symbol}] CVD: {cvd_value:+.2f} | Price: ${stats['last_price']:.2f} | "
              f"Trades: {stats['total_trades']} | Buy%: {buy_ratio:.1f} | "
              f"CVD/min: {cvd_per_minute:+.2f}")
              
    async def run(self, duration_seconds: Optional[int] = None):
        """
        Run the CVD calculator
        
        Args:
            duration_seconds: How long to run (None = forever)
        """
        self.running = True
        start_time = time.time()
        
        print(f"[CVD] Connecting to {self.ws_url}")
        print(f"[CVD] Tracking symbols: {', '.join(self.symbols)}")
        print("=" * 60)
        
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    print("[CVD] Connected to WebSocket")
                    
                    # Subscribe to trades for each symbol
                    for symbol in self.symbols:
                        subscribe_msg = {
                            "method": "subscribe",
                            "subscription": {
                                "type": "trades",
                                "coin": symbol
                            }
                        }
                        await ws.send(json.dumps(subscribe_msg))
                        print(f"[CVD] Subscribed to {symbol} trades")
                    
                    # Main message loop
                    while self.running:
                        try:
                            # Set timeout for receiving messages
                            message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            await self.handle_message(message)
                            
                        except asyncio.TimeoutError:
                            # Check if duration exceeded
                            if duration_seconds and (time.time() - start_time) > duration_seconds:
                                print(f"\n[CVD] Duration limit reached")
                                self.running = False
                                break
                                
                        except websockets.ConnectionClosed:
                            print("[CVD] WebSocket connection closed")
                            break
                            
            except Exception as e:
                print(f"[CVD] Connection error: {e}")
                if self.running:
                    print("[CVD] Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
                    
        print("\n[CVD] Stopped")
        self.print_final_summary()
        
    def print_final_summary(self):
        """Print final CVD summary"""
        print("\n" + "=" * 60)
        print("FINAL CVD SUMMARY")
        print("=" * 60)
        
        for symbol in self.symbols:
            if self.stats[symbol]['total_trades'] > 0:
                cvd_value = self.cvd[symbol]
                stats = self.stats[symbol]
                
                total_volume = stats['buy_volume'] + stats['sell_volume']
                buy_ratio = (stats['buy_volume'] / total_volume * 100) if total_volume > 0 else 50
                
                print(f"\n{symbol}:")
                print(f"  Final CVD: {cvd_value:+.2f}")
                print(f"  Last Price: ${stats['last_price']:.2f}")
                print(f"  Total Trades: {stats['total_trades']:,}")
                print(f"  Buy Volume: ${stats['buy_volume']:,.0f}")
                print(f"  Sell Volume: ${stats['sell_volume']:,.0f}")
                print(f"  Buy Ratio: {buy_ratio:.1f}%")
                
                # Trend determination
                if cvd_value > 0:
                    trend = "BULLISH" if cvd_value > stats['total_trades'] * 0.01 else "SLIGHTLY BULLISH"
                elif cvd_value < 0:
                    trend = "BEARISH" if abs(cvd_value) > stats['total_trades'] * 0.01 else "SLIGHTLY BEARISH"
                else:
                    trend = "NEUTRAL"
                print(f"  Trend: {trend}")
                
    def get_cvd_data(self, symbol: str) -> Dict:
        """Get CVD data for a symbol"""
        return {
            'cvd': self.cvd[symbol],
            'stats': self.stats[symbol],
            'recent_trades': list(self.trades_buffer[symbol])[-100:]  # Last 100 trades
        }


async def main():
    """Run CVD calculator example"""
    
    # Create calculator
    calculator = SimpleCVDCalculator(symbols=['BTC', 'ETH', 'SOL'])
    
    # Run for 30 seconds
    try:
        await calculator.run(duration_seconds=30)
    except KeyboardInterrupt:
        calculator.running = False
        print("\n[CVD] Interrupted by user")
        
    # Get final data
    for symbol in calculator.symbols:
        data = calculator.get_cvd_data(symbol)
        if data['stats']['total_trades'] > 0:
            print(f"\n{symbol} CVD Data Available: {len(data['recent_trades'])} recent trades")


if __name__ == "__main__":
    print("Starting Simple CVD Calculator")
    print("This will track real-time trades and calculate CVD")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())