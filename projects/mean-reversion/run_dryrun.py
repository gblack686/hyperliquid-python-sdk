#!/usr/bin/env python3
"""
Simplified dry-run trading system
Shows real-time signals without the complexity
"""

import os
import sys
import time
from datetime import datetime
from collections import deque
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add paths
sys.path.append('..')
sys.path.append('src')

from hyperliquid.info import Info
from hyperliquid.utils import constants
from strategy_engine import StrategyEngine, SignalType
from order_executor import OrderExecutor
from loguru import logger

# Configure simple logging
logger.remove()
logger.add(sys.stdout, format="{time:HH:mm:ss} | {level} | {message}", level="INFO")


class SimpleTradingSystem:
    """Simplified trading system for dry-run"""
    
    def __init__(self):
        """Initialize system"""
        
        # Components
        self.strategy = StrategyEngine()
        self.executor = OrderExecutor(dry_run=True)
        
        # WebSocket
        self.info = Info(constants.MAINNET_API_URL, skip_ws=False)
        
        # Tracking
        self.trade_count = 0
        self.signal_count = 0
        self.last_price = 0
        self.start_time = datetime.now()
        self.position_value = 0
        
        # Performance
        self.signals_history = []
        
    def handle_trades(self, data):
        """Process trade updates"""
        
        try:
            # Extract trades
            if isinstance(data, dict) and "data" in data:
                trades = data["data"]
            elif isinstance(data, list):
                trades = data
            else:
                trades = [data] if data else []
            
            for trade in trades:
                if isinstance(trade, dict) and "px" in trade:
                    price = float(trade["px"])
                    size = float(trade.get("sz", 0))
                    
                    self.trade_count += 1
                    self.last_price = price
                    
                    # Update strategy
                    self.strategy.update_price(price, size * price)
                    
                    # Check for signals (after warmup)
                    if len(self.strategy.price_buffer) >= self.strategy.lookback_period:
                        signal = self.strategy.generate_signal()
                        
                        if signal.action != SignalType.HOLD:
                            self.process_signal(signal, price)
                    
                    # Display every 10th trade
                    if self.trade_count % 10 == 0:
                        self.display_status()
                        
        except Exception as e:
            logger.error(f"Error handling trade: {e}")
    
    def process_signal(self, signal, price):
        """Process trading signal"""
        
        self.signal_count += 1
        
        # Calculate position size
        position_size = self.strategy.calculate_position_size(signal)
        
        # Log signal
        logger.info(f"SIGNAL #{self.signal_count}: {signal.action.value} @ ${price:.4f}")
        logger.info(f"  Reason: {signal.reason}")
        logger.info(f"  Z-Score: {signal.z_score:.2f} | Confidence: {signal.confidence:.1%}")
        logger.info(f"  Position Size: ${position_size:.2f}")
        
        # Simulate execution
        if signal.action == SignalType.BUY:
            self.position_value = position_size
            self.strategy.update_position(position_size/price, price, "long")
            logger.success(f"  [DRY-RUN] Bought {position_size/price:.4f} HYPE")
            
        elif signal.action == SignalType.SELL:
            self.position_value = -position_size
            self.strategy.update_position(-position_size/price, price, "short")
            logger.success(f"  [DRY-RUN] Shorted {position_size/price:.4f} HYPE")
            
        elif signal.action == SignalType.EXIT:
            pnl = self.strategy.close_position(price)
            self.position_value = 0
            logger.success(f"  [DRY-RUN] Closed position, P&L: ${pnl:.2f}")
        
        # Store signal
        self.signals_history.append({
            "time": datetime.now(),
            "action": signal.action.value,
            "price": price,
            "z_score": signal.z_score,
            "confidence": signal.confidence,
            "position_size": position_size
        })
        
        print("-" * 60)
    
    def display_status(self):
        """Display current status"""
        
        runtime = (datetime.now() - self.start_time).total_seconds() / 60
        
        # Get stats
        stats = self.strategy.get_statistics()
        indicators = stats['current_indicators']
        
        # Display inline status
        status = f"[{datetime.now().strftime('%H:%M:%S')}] "
        status += f"Price: ${self.last_price:.4f} | "
        status += f"Z-Score: {indicators['z_score']:+.2f} | "
        status += f"Trades: {self.trade_count} | "
        status += f"Signals: {self.signal_count} | "
        
        if stats['current_position']['side'] != 'flat':
            status += f"Pos: {stats['current_position']['side'].upper()} | "
            unrealized = self.strategy.calculate_unrealized_pnl(self.last_price)
            status += f"Unrealized P&L: ${unrealized:+.2f}"
        else:
            status += f"Position: FLAT"
        
        print(status)
    
    def run(self):
        """Main execution"""
        
        print("\n" + "="*70)
        print("HYPE TRADING SYSTEM - DRY RUN MODE")
        print("="*70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Strategy: Mean Reversion (Entry Z: {self.strategy.entry_z_score}, Exit Z: {self.strategy.exit_z_score})")
        print(f"Max Position: ${self.strategy.max_position_size}")
        print(f"Stop Loss: {self.strategy.stop_loss_pct*100:.0f}%")
        print("\nConnecting to Hyperliquid...")
        
        try:
            # Subscribe to trades
            trade_id = self.info.subscribe(
                {"type": "trades", "coin": "HYPE"},
                self.handle_trades
            )
            print(f"[OK] Connected! Subscribed to HYPE trades (ID: {trade_id})")
            
            print("\nMonitoring for signals... (Press Ctrl+C to stop)")
            print("Note: First signal requires 12+ hours of price data")
            print("-"*70)
            
            # Keep running
            while True:
                time.sleep(10)
                
                # Show periodic updates
                if self.trade_count > 0 and self.trade_count % 50 == 0:
                    self.show_summary()
                    
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            
            # Unsubscribe
            try:
                self.info.unsubscribe({"type": "trades", "coin": "HYPE"}, trade_id)
            except:
                pass
            
            # Show final summary
            self.show_summary()
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    def show_summary(self):
        """Show performance summary"""
        
        runtime = (datetime.now() - self.start_time).total_seconds() / 60
        stats = self.strategy.get_statistics()
        
        print("\n" + "="*70)
        print("PERFORMANCE SUMMARY")
        print("="*70)
        print(f"Runtime: {runtime:.1f} minutes")
        print(f"Trades Processed: {self.trade_count}")
        print(f"Signals Generated: {self.signal_count}")
        
        if self.signal_count > 0:
            print(f"Signal Rate: {self.signal_count/runtime:.2f} per minute")
            print(f"\nSignal History:")
            for i, sig in enumerate(self.signals_history[-5:], 1):  # Last 5 signals
                print(f"  {i}. {sig['time'].strftime('%H:%M:%S')} - {sig['action']} @ ${sig['price']:.4f} (Z: {sig['z_score']:+.2f})")
        
        print(f"\nStrategy Performance:")
        print(f"  Total P&L: ${stats['total_pnl']:.2f}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Total Trades: {stats['total_trades']}")
        
        print(f"\nCurrent Market:")
        print(f"  Last Price: ${self.last_price:.4f}")
        print(f"  Z-Score: {self.strategy.z_score:+.2f}")
        print(f"  Position: {stats['current_position']['side'].upper()}")
        
        if stats['current_position']['side'] != 'flat':
            unrealized = self.strategy.calculate_unrealized_pnl(self.last_price)
            print(f"  Unrealized P&L: ${unrealized:+.2f}")
        
        print("="*70)


def main():
    """Main entry point"""
    
    system = SimpleTradingSystem()
    system.run()


if __name__ == "__main__":
    main()