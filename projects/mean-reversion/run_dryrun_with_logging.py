#!/usr/bin/env python3
"""
Dry-run trading system with full Supabase logging
Shows real-time signals and saves all data to database
"""

import os
import sys
import time
from datetime import datetime
from collections import deque
from dotenv import load_dotenv
import json

# Load environment
load_dotenv()

# Add paths
sys.path.append('..')
sys.path.append('src')

from hyperliquid.info import Info
from hyperliquid.utils import constants
from strategy_engine import StrategyEngine, SignalType
from order_executor import OrderExecutor
from supabase import create_client, Client
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stdout, format="{time:HH:mm:ss} | {level} | {message}", level="INFO")


class TradingSystemWithLogging:
    """Trading system with full Supabase integration"""
    
    def __init__(self):
        """Initialize system with database"""
        
        # Initialize Supabase
        self.supabase = self.init_supabase()
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        
        # Components
        self.strategy = StrategyEngine()
        self.executor = OrderExecutor(dry_run=True)
        
        # WebSocket
        self.info = Info(constants.MAINNET_API_URL, skip_ws=False)
        
        # Tracking
        self.trade_count = 0
        self.signal_count = 0
        self.last_price = 0
        self.start_time = datetime.utcnow()
        
        # Performance
        self.signals_history = []
        
        # Log system startup
        self.log_system_health("STARTED", {"mode": "dry_run"})
        
    def init_supabase(self) -> Client:
        """Initialize Supabase client"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.warning("Supabase not configured - logging disabled")
            return None
            
        client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")
        return client
    
    def log_system_health(self, status: str, details: dict = None):
        """Log system health to Supabase"""
        if not self.supabase:
            return
            
        try:
            data = {
                "component": "trading_system_dryrun",
                "status": status,
                "details": details or {},
                "checked_at": datetime.utcnow().isoformat()
            }
            
            self.supabase.table("hl_system_health").insert(data).execute()
            logger.debug(f"Logged health: {status}")
            
        except Exception as e:
            logger.error(f"Failed to log health: {e}")
    
    def log_signal(self, signal, price, position_size, order_result):
        """Log trading signal to Supabase"""
        if not self.supabase:
            return
            
        try:
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "account_address": self.account_address,
                "strategy": "mean_reversion",
                "action": signal.action.value,
                "price": float(price),
                "z_score": float(signal.z_score),
                "confidence": float(signal.confidence),
                "reason": signal.reason,
                "position_size": float(position_size),
                "order_result": order_result,
                "metadata": signal.metadata
            }
            
            self.supabase.table("hl_signals").insert(data).execute()
            logger.debug(f"Logged signal: {signal.action.value}")
            
        except Exception as e:
            logger.error(f"Failed to log signal: {e}")
    
    def log_trade(self, price, size, side=None):
        """Log trade to Supabase"""
        if not self.supabase:
            return
            
        try:
            data = {
                "trade_time": datetime.utcnow().isoformat(),
                "coin": "HYPE",
                "price": float(price),
                "size": float(size),
                "side": side,
                "value": float(price * size)
            }
            
            # Only log significant trades
            if data["value"] > 100:  # Log trades > $100
                self.supabase.table("hl_trades_log").insert(data).execute()
                
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
    
    def log_performance_snapshot(self):
        """Log performance metrics to Supabase"""
        if not self.supabase:
            return
            
        try:
            stats = self.strategy.get_statistics()
            
            data = {
                "account_address": self.account_address,
                "strategy": "mean_reversion",
                "period_start": self.start_time.isoformat(),
                "period_end": datetime.utcnow().isoformat(),
                "total_pnl": float(stats['total_pnl']),
                "daily_pnl": float(stats['daily_pnl']),
                "total_trades": stats['total_trades'],
                "win_count": self.strategy.win_count,
                "loss_count": self.strategy.loss_count,
                "win_rate": float(stats['win_rate']),
                "metrics": {
                    "signals_generated": self.signal_count,
                    "trades_processed": self.trade_count,
                    "current_z_score": float(self.strategy.z_score),
                    "current_position": stats['current_position']['side']
                }
            }
            
            self.supabase.table("hl_performance").insert(data).execute()
            logger.info("Logged performance snapshot")
            
        except Exception as e:
            logger.error(f"Failed to log performance: {e}")
    
    def log_account_snapshot(self):
        """Log account snapshot"""
        if not self.supabase:
            return
            
        try:
            stats = self.strategy.get_statistics()
            
            data = {
                "account_address": self.account_address,
                "snapshot_time": datetime.utcnow().isoformat(),
                "account_value": 10000.0,  # Simulated
                "margin_used": abs(self.strategy.current_position.size * self.last_price) if self.strategy.current_position.size else 0,
                "positions": [stats['current_position']] if stats['current_position']['side'] != 'flat' else [],
                "raw_data": stats
            }
            
            self.supabase.table("hl_account_snapshots").insert(data).execute()
            
        except Exception as e:
            logger.error(f"Failed to log account snapshot: {e}")
    
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
                    side = trade.get("side", "")
                    
                    self.trade_count += 1
                    self.last_price = price
                    
                    # Log significant trades
                    if size * price > 1000:  # Trade > $1000
                        self.log_trade(price, size, side)
                    
                    # Update strategy
                    self.strategy.update_price(price, size * price)
                    
                    # Check for signals (after warmup)
                    if len(self.strategy.price_buffer) >= self.strategy.lookback_period:
                        signal = self.strategy.generate_signal()
                        
                        if signal.action != SignalType.HOLD:
                            self.process_signal(signal, price)
                    
                    # Display status every 10 trades
                    if self.trade_count % 10 == 0:
                        self.display_status()
                        
        except Exception as e:
            logger.error(f"Error handling trade: {e}")
    
    def process_signal(self, signal, price):
        """Process trading signal with logging"""
        
        self.signal_count += 1
        
        # Calculate position size
        position_size = self.strategy.calculate_position_size(signal)
        
        # Log signal
        logger.info(f"SIGNAL #{self.signal_count}: {signal.action.value} @ ${price:.4f}")
        logger.info(f"  Z-Score: {signal.z_score:.2f} | Confidence: {signal.confidence:.1%}")
        
        # Simulate execution
        order_result = {"status": "simulated", "mode": "dry_run"}
        
        if signal.action == SignalType.BUY:
            self.strategy.update_position(position_size/price, price, "long")
            logger.success(f"  [DRY-RUN] Bought {position_size/price:.4f} HYPE for ${position_size:.2f}")
            order_result["action"] = "buy"
            order_result["size"] = position_size/price
            
        elif signal.action == SignalType.SELL:
            self.strategy.update_position(-position_size/price, price, "short")
            logger.success(f"  [DRY-RUN] Shorted {position_size/price:.4f} HYPE for ${position_size:.2f}")
            order_result["action"] = "sell"
            order_result["size"] = position_size/price
            
        elif signal.action == SignalType.EXIT:
            pnl = self.strategy.close_position(price)
            logger.success(f"  [DRY-RUN] Closed position, P&L: ${pnl:.2f}")
            order_result["action"] = "exit"
            order_result["pnl"] = pnl
        
        # Log to Supabase
        self.log_signal(signal, price, position_size, order_result)
        
        # Store signal
        self.signals_history.append({
            "time": datetime.utcnow(),
            "action": signal.action.value,
            "price": price,
            "z_score": signal.z_score,
            "confidence": signal.confidence,
            "position_size": position_size
        })
        
        print("-" * 60)
    
    def display_status(self):
        """Display current status"""
        
        stats = self.strategy.get_statistics()
        indicators = stats['current_indicators']
        
        status = f"[{datetime.utcnow().strftime('%H:%M:%S')}] "
        status += f"Price: ${self.last_price:.4f} | "
        status += f"Z: {indicators['z_score']:+.2f} | "
        status += f"Signals: {self.signal_count} | "
        
        if stats['current_position']['side'] != 'flat':
            unrealized = self.strategy.calculate_unrealized_pnl(self.last_price)
            status += f"Pos: {stats['current_position']['side'].upper()} | P&L: ${unrealized:+.2f}"
        else:
            status += f"Position: FLAT"
        
        if self.supabase:
            status += " | [DB: Connected]"
        
        print(status)
    
    def run(self):
        """Main execution"""
        
        print("\n" + "="*70)
        print("HYPE TRADING SYSTEM - DRY RUN WITH SUPABASE LOGGING")
        print("="*70)
        print(f"Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Account: {self.account_address}")
        print(f"Database: {'Connected' if self.supabase else 'Not configured'}")
        print(f"Strategy: Mean Reversion (Entry: {self.strategy.entry_z_score}, Exit: {self.strategy.exit_z_score})")
        print("\nConnecting to Hyperliquid WebSocket...")
        
        try:
            # Subscribe to trades
            trade_id = self.info.subscribe(
                {"type": "trades", "coin": "HYPE"},
                self.handle_trades
            )
            print(f"[OK] Connected! Monitoring HYPE trades...")
            
            if self.supabase:
                print("[OK] Supabase logging active - all signals will be saved")
            
            print("\nMonitoring for signals... (Press Ctrl+C to stop)")
            print("-"*70)
            
            # Periodic tasks
            last_health_check = time.time()
            last_performance_log = time.time()
            last_account_snapshot = time.time()
            
            while True:
                current_time = time.time()
                
                # Health check every 60 seconds
                if current_time - last_health_check > 60:
                    self.log_system_health("HEALTHY", {
                        "trades_processed": self.trade_count,
                        "signals_generated": self.signal_count,
                        "uptime_minutes": (datetime.utcnow() - self.start_time).total_seconds() / 60
                    })
                    last_health_check = current_time
                
                # Performance snapshot every 5 minutes
                if current_time - last_performance_log > 300:
                    self.log_performance_snapshot()
                    last_performance_log = current_time
                
                # Account snapshot every 10 minutes
                if current_time - last_account_snapshot > 600:
                    self.log_account_snapshot()
                    last_account_snapshot = current_time
                
                time.sleep(10)
                    
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            
            # Log shutdown
            self.log_system_health("STOPPED", {
                "reason": "user_shutdown",
                "total_runtime_minutes": (datetime.utcnow() - self.start_time).total_seconds() / 60,
                "total_signals": self.signal_count
            })
            
            # Final performance log
            self.log_performance_snapshot()
            
            # Unsubscribe
            try:
                self.info.unsubscribe({"type": "trades", "coin": "HYPE"}, trade_id)
            except:
                pass
            
            # Show summary
            self.show_summary()
            
        except Exception as e:
            logger.error(f"Error: {e}")
            self.log_system_health("ERROR", {"error": str(e)})
            import traceback
            traceback.print_exc()
    
    def show_summary(self):
        """Show performance summary"""
        
        runtime = (datetime.utcnow() - self.start_time).total_seconds() / 60
        stats = self.strategy.get_statistics()
        
        print("\n" + "="*70)
        print("SESSION SUMMARY")
        print("="*70)
        print(f"Runtime: {runtime:.1f} minutes")
        print(f"Trades Processed: {self.trade_count}")
        print(f"Signals Generated: {self.signal_count}")
        
        if self.signal_count > 0:
            print(f"\nLast 5 Signals:")
            for sig in self.signals_history[-5:]:
                print(f"  {sig['time'].strftime('%H:%M:%S')} - {sig['action']} @ ${sig['price']:.4f} (Z: {sig['z_score']:+.2f})")
        
        print(f"\nPerformance:")
        print(f"  Total P&L: ${stats['total_pnl']:.2f}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Total Trades: {stats['total_trades']}")
        
        if self.supabase:
            print(f"\nDatabase:")
            print(f"  Signals logged: {self.signal_count}")
            print(f"  Health checks: {int(runtime / 1) + 1}")
            print(f"  Performance snapshots: {int(runtime / 5) + 1}")
        
        print("="*70)


def main():
    """Main entry point"""
    
    print("\nInitializing trading system with Supabase logging...")
    system = TradingSystemWithLogging()
    system.run()


if __name__ == "__main__":
    main()