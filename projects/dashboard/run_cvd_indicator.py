"""
Standalone CVD (Cumulative Volume Delta) Indicator Runner
Ensures CVD is always running and streaming data to Supabase
"""

import asyncio
import sys
import os
import signal
import time
from datetime import datetime
from dotenv import load_dotenv
import websockets

# Add paths
sys.path.append('.')
sys.path.append(os.path.dirname(__file__))

from indicators.cvd import CVDIndicator

load_dotenv()

class CVDRunner:
    def __init__(self, symbols=None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.cvd_indicator = None
        self.running = False
        self.restart_count = 0
        self.max_restarts = 10
        self.last_save_time = time.time()
        
    async def run_cvd(self):
        """Run CVD indicator with automatic reconnection"""
        print("=" * 70)
        print("CVD INDICATOR RUNNER")
        print("=" * 70)
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        while self.restart_count < self.max_restarts:
            try:
                # Create new indicator instance
                self.cvd_indicator = CVDIndicator(self.symbols)
                self.running = True
                
                print(f"\n[CVD Runner] Starting CVD indicator (attempt {self.restart_count + 1}/{self.max_restarts})")
                
                # Connect to WebSocket
                connected = await self.cvd_indicator.connect_websocket()
                if not connected:
                    print("[CVD Runner] Failed to connect to WebSocket, retrying in 10 seconds...")
                    await asyncio.sleep(10)
                    self.restart_count += 1
                    continue
                
                print("[CVD Runner] WebSocket connected successfully")
                
                # Main loop
                while self.running:
                    try:
                        # Update CVD
                        await self.cvd_indicator.update()
                        
                        # Save to Supabase every 30 seconds
                        current_time = time.time()
                        if current_time - self.last_save_time >= 30:
                            await self.cvd_indicator.save_to_supabase()
                            self.last_save_time = current_time
                            
                            # Print status
                            for symbol in self.symbols:
                                stats = self.cvd_indicator.stats[symbol]
                                cvd = self.cvd_indicator.cvd[symbol]
                                print(f"[CVD] {symbol}: CVD={cvd:.2f}, Trades={stats['total_trades']}, "
                                      f"Buy={stats['buy_trades']}, Sell={stats['sell_trades']}, "
                                      f"Last={stats['last_price']:.2f}")
                            
                            # Reset restart count on successful operation
                            self.restart_count = 0
                            
                    except Exception as e:
                        print(f"[CVD Runner] Error in update loop: {e}")
                        await asyncio.sleep(1)
                        
            except websockets.exceptions.ConnectionClosed:
                print("[CVD Runner] WebSocket connection closed, reconnecting...")
                self.restart_count += 1
                await asyncio.sleep(5)
                    
            except KeyboardInterrupt:
                print("\n[CVD Runner] Shutdown requested")
                self.running = False
                break
                
            except Exception as e:
                print(f"[CVD Runner] Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                self.restart_count += 1
                await asyncio.sleep(10)
        
        if self.restart_count >= self.max_restarts:
            print(f"[CVD Runner] Max restarts ({self.max_restarts}) reached. Exiting.")
        
    def stop(self):
        """Stop the CVD runner"""
        print("[CVD Runner] Stopping...")
        self.running = False
        if self.cvd_indicator:
            self.cvd_indicator.running = False

async def main():
    """Main entry point"""
    runner = CVDRunner()
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        print("\n[CVD Runner] Received shutdown signal")
        runner.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await runner.run_cvd()
    except Exception as e:
        print(f"[CVD Runner] Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Add missing websockets import
    try:
        import websockets
    except ImportError:
        print("[ERROR] websockets not installed. Installing...")
        os.system("pip install websockets")
        import websockets
    
    asyncio.run(main())