"""
Non-blocking CVD Calculator with proper timeout and async handling
"""

import json
import asyncio
import websockets
from datetime import datetime
from collections import deque, defaultdict
from typing import Dict, List, Optional
import time


class NonBlockingCVDCalculator:
    """
    Non-blocking CVD calculator with proper timeout handling
    """
    
    def __init__(self, symbols: List[str] = None):
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
        self.ws = None
        
    async def process_trade(self, trade: dict):
        """Process individual trade"""
        try:
            symbol = trade.get('coin', '')
            if symbol not in self.symbols:
                return
                
            price = float(trade.get('px', 0))
            size = float(trade.get('sz', 0))
            side = trade.get('side', '')
            
            # Update CVD
            if side == 'B':
                self.cvd[symbol] += size
                self.stats[symbol]['buy_volume'] += size * price
            else:
                self.cvd[symbol] -= size
                self.stats[symbol]['sell_volume'] += size * price
                
            self.stats[symbol]['total_trades'] += 1
            self.stats[symbol]['last_price'] = price
            
            # Store trade
            self.trades_buffer[symbol].append({
                'time': time.time(),
                'price': price,
                'size': size,
                'side': side,
                'cvd': self.cvd[symbol]
            })
                
        except Exception as e:
            print(f"[CVD] Error processing trade: {e}")
    
    async def listen_to_trades(self):
        """Listen to WebSocket trades (non-blocking)"""
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
                
                # Process messages without blocking
                while self.running:
                    try:
                        # Use wait_for with a short timeout to make it non-blocking
                        message = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        
                        # Process message asynchronously
                        data = json.loads(message)
                        if 'data' in data:
                            for trade in data.get('data', []):
                                if 'coin' in trade:
                                    await self.process_trade(trade)
                                    
                    except asyncio.TimeoutError:
                        # No message received, continue
                        continue
                    except websockets.ConnectionClosed:
                        print("[CVD] Connection closed")
                        break
                        
        except Exception as e:
            print(f"[CVD] WebSocket error: {e}")
    
    async def print_status_periodically(self):
        """Print status updates (runs in parallel with trade listening)"""
        while self.running:
            await asyncio.sleep(5)  # Update every 5 seconds
            
            print(f"\n[Status Update] {datetime.now().strftime('%H:%M:%S')}")
            for symbol in self.symbols:
                if self.stats[symbol]['total_trades'] > 0:
                    stats = self.stats[symbol]
                    total_vol = stats['buy_volume'] + stats['sell_volume']
                    buy_pct = (stats['buy_volume'] / total_vol * 100) if total_vol > 0 else 50
                    
                    print(f"  {symbol}: CVD={self.cvd[symbol]:+.2f}, "
                          f"Trades={stats['total_trades']}, "
                          f"Buy%={buy_pct:.1f}, "
                          f"Price=${stats['last_price']:.2f}")
    
    async def run_for_duration(self, duration_seconds: int):
        """Run calculator for specific duration (non-blocking)"""
        self.running = True
        print(f"[CVD] Starting for {duration_seconds} seconds...")
        print("=" * 60)
        
        # Create tasks that run in parallel
        tasks = [
            asyncio.create_task(self.listen_to_trades()),
            asyncio.create_task(self.print_status_periodically())
        ]
        
        # Wait for duration
        await asyncio.sleep(duration_seconds)
        
        # Stop running
        self.running = False
        print(f"\n[CVD] Stopping after {duration_seconds} seconds...")
        
        # Cancel tasks
        for task in tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Close WebSocket if still open
        if self.ws:
            await self.ws.close()
            
        self.print_final_summary()
        
    def print_final_summary(self):
        """Print final summary"""
        print("\n" + "=" * 60)
        print("FINAL CVD SUMMARY")
        print("=" * 60)
        
        for symbol in self.symbols:
            if self.stats[symbol]['total_trades'] > 0:
                cvd_value = self.cvd[symbol]
                stats = self.stats[symbol]
                
                total_volume = stats['buy_volume'] + stats['sell_volume']
                buy_ratio = (stats['buy_volume'] / total_volume * 100) if total_volume > 0 else 50
                
                # Determine signal
                if cvd_value > stats['total_trades'] * 0.1:
                    signal = "STRONG BUY PRESSURE"
                elif cvd_value > 0:
                    signal = "MODERATE BUY"
                elif cvd_value < -stats['total_trades'] * 0.1:
                    signal = "STRONG SELL PRESSURE"
                else:
                    signal = "MODERATE SELL"
                
                print(f"\n{symbol}:")
                print(f"  Final CVD: {cvd_value:+.2f}")
                print(f"  Total Trades: {stats['total_trades']:,}")
                print(f"  Buy Ratio: {buy_ratio:.1f}%")
                print(f"  Signal: {signal}")
    
    def get_results(self) -> Dict:
        """Get CVD results"""
        results = {}
        for symbol in self.symbols:
            if self.stats[symbol]['total_trades'] > 0:
                results[symbol] = {
                    'cvd': self.cvd[symbol],
                    'stats': dict(self.stats[symbol]),
                    'recent_trades': list(self.trades_buffer[symbol])[-100:]
                }
        return results


async def main():
    """Test non-blocking CVD calculator"""
    
    # Create calculator
    calculator = NonBlockingCVDCalculator(symbols=['BTC', 'ETH', 'SOL'])
    
    # Run for exactly 15 seconds (will not block/hang)
    await calculator.run_for_duration(15)
    
    # Get results
    results = calculator.get_results()
    
    # Save results
    import json
    with open('cvd_results_nonblocking.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SUCCESS] Results saved to cvd_results_nonblocking.json")
    print("[SUCCESS] Script completed successfully without blocking!")
    
    return results


if __name__ == "__main__":
    print("Non-Blocking CVD Calculator")
    print("This will run for exactly 15 seconds and then exit cleanly\n")
    
    results = asyncio.run(main())
    
    print("\n[SUCCESS] Done! Script exited normally.")