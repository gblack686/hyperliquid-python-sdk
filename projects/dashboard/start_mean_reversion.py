#!/usr/bin/env python3
"""
Start HYPE Mean Reversion System from the dashboard directory
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "hype-trading-system" / "src"))
sys.path.insert(0, str(parent_dir / "hype-trading-system"))

# Change to the hype-trading-system directory context
os.chdir(str(parent_dir / "hype-trading-system"))

print("=" * 60)
print("STARTING HYPE MEAN REVERSION SYSTEM")
print("=" * 60)
print()
print("Mode: DRY-RUN")
print("Symbol: HYPE")
print("Strategy: Mean Reversion")
print()

try:
    # Import and run
    from src.websocket_manager import WebSocketManager
    from src.strategy_engine import StrategyEngine, SignalType
    from src.order_executor import OrderExecutor
    from src.config import get_config
    
    import asyncio
    import time
    from datetime import datetime
    
    class SimpleMeanReversion:
        def __init__(self):
            # Get configuration
            self.config = get_config()
            
            # Initialize components
            self.ws_manager = WebSocketManager(
                self.config.hyperliquid.account_address
            )
            
            self.strategy = StrategyEngine(config={
                "lookback_period": 12,
                "entry_z_score": 0.75,
                "exit_z_score": 0.5,
                "stop_loss_pct": 0.05,
                "max_position_size": 1000,
                "max_leverage": 3.0
            })
            
            self.executor = OrderExecutor(
                api_key=self.config.hyperliquid.api_key,
                account_address=self.config.hyperliquid.account_address,
                dry_run=True
            )
            
            self.running = False
            self.last_signal_time = 0
            self.signal_cooldown = 60  # seconds
            
        def run(self):
            """Run the system"""
            print("Starting WebSocket connection...")
            self.ws_manager.start()
            
            # Wait for connection
            time.sleep(3)
            
            if not self.ws_manager.is_connected:
                print("ERROR: WebSocket failed to connect")
                return
            
            print("WebSocket connected!")
            print("Starting main loop...")
            print("-" * 40)
            
            self.running = True
            trades_count = 0
            signals_count = 0
            
            try:
                while self.running:
                    # Get latest trades
                    trades = self.ws_manager.get_trades()
                    
                    if trades:
                        trades_count += len(trades)
                        
                        # Process with strategy
                        for trade in trades[-10:]:  # Last 10 trades
                            signal = self.strategy.process_trade(trade)
                            
                            if signal and signal != SignalType.HOLD:
                                current_time = time.time()
                                
                                # Apply cooldown
                                if current_time - self.last_signal_time >= self.signal_cooldown:
                                    signals_count += 1
                                    
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                                          f"SIGNAL #{signals_count}: {signal.value}")
                                    print(f"  Price: ${self.strategy.current_price:.2f}")
                                    print(f"  Mean: ${self.strategy.mean:.2f}")
                                    print(f"  Z-Score: {self.strategy.z_score:.3f}")
                                    print(f"  Position: {self.strategy.position}")
                                    
                                    # Execute in dry-run
                                    if signal in [SignalType.BUY, SignalType.SELL]:
                                        size = 100  # HYPE tokens
                                        
                                        if signal == SignalType.BUY:
                                            result = self.executor.place_order(
                                                'HYPE', 'buy', size, self.strategy.current_price
                                            )
                                        else:
                                            result = self.executor.place_order(
                                                'HYPE', 'sell', size, self.strategy.current_price
                                            )
                                        
                                        print(f"  Order Result: {result}")
                                    
                                    print("-" * 40)
                                    self.last_signal_time = current_time
                    
                    # Status update every 30 seconds
                    if trades_count % 100 == 0 and trades_count > 0:
                        print(f"[STATUS] Trades: {trades_count} | Signals: {signals_count} | "
                              f"Price: ${self.strategy.current_price:.2f}")
                    
                    time.sleep(0.5)  # Check twice per second
                    
            except KeyboardInterrupt:
                print("\nStopping system...")
            finally:
                self.running = False
                self.ws_manager.stop()
                print("System stopped")
    
    # Run the system
    system = SimpleMeanReversion()
    system.run()
    
except ImportError as e:
    print(f"Import error: {e}")
    print("\nMake sure you have all dependencies installed:")
    print("  pip install hyperliquid-python-sdk")
    print("  pip install pandas numpy loguru")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()