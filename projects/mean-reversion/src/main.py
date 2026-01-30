"""
HYPE Mean Reversion Trading System
Main application orchestrator that coordinates WebSocket, Strategy, and Order Execution
"""

import os
import sys
import asyncio
import signal
from datetime import datetime, timedelta
from typing import Optional, Dict
import json

from dotenv import load_dotenv
from loguru import logger
from supabase import create_client, Client

# Import our components
from websocket_manager import WebSocketManager
from strategy_engine import StrategyEngine, TradingSignal, SignalType
from order_executor import OrderExecutor

# Load environment variables
load_dotenv()


class TradingSystem:
    """
    Main trading system orchestrator
    Coordinates WebSocket data, strategy decisions, and order execution
    """
    
    def __init__(self, dry_run: bool = True):
        """
        Initialize trading system
        
        Args:
            dry_run: If True, simulate trades without executing
        """
        
        self.dry_run = dry_run
        self.running = False
        
        # Initialize Supabase
        self.supabase_client = self.init_supabase()
        
        # Initialize components
        logger.info("Initializing trading system components...")
        
        self.websocket_manager = WebSocketManager(self.supabase_client)
        self.strategy_engine = StrategyEngine()
        self.order_executor = OrderExecutor(dry_run=dry_run)
        
        # State tracking
        self.last_signal_time = None
        self.signal_cooldown = 60  # Minimum seconds between signals
        self.consecutive_errors = 0
        self.max_errors = 10
        
        # Performance tracking
        self.system_stats = {
            "start_time": datetime.utcnow(),
            "signals_generated": 0,
            "orders_placed": 0,
            "errors": 0,
            "last_health_check": None
        }
        
        logger.info(f"Trading System initialized (dry_run={dry_run})")
    
    def init_supabase(self) -> Optional[Client]:
        """Initialize Supabase client"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if supabase_url and supabase_key:
                client = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialized")
                return client
            else:
                logger.warning("Supabase credentials not found, logging disabled")
                return None
                
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
            return None
    
    async def process_price_update(self, price_data: Dict):
        """
        Process price update from WebSocket
        
        Args:
            price_data: Price data from WebSocket
        """
        try:
            price = float(price_data.get("price", 0))
            volume = float(price_data.get("volume", 0))
            
            if price <= 0:
                return
            
            # Update strategy engine
            self.strategy_engine.update_price(price, volume)
            
            # Check if we should generate signal
            if self.should_generate_signal():
                signal = self.strategy_engine.generate_signal()
                
                if signal.action != SignalType.HOLD:
                    await self.process_signal(signal)
                    
        except Exception as e:
            logger.error(f"Error processing price update: {e}")
            self.consecutive_errors += 1
    
    def should_generate_signal(self) -> bool:
        """Check if we should generate a new signal"""
        
        # Check if we have enough data
        if len(self.strategy_engine.price_buffer) < self.strategy_engine.lookback_period:
            return False
        
        # Check cooldown
        if self.last_signal_time:
            time_since = (datetime.utcnow() - self.last_signal_time).total_seconds()
            if time_since < self.signal_cooldown:
                return False
        
        # Check error threshold
        if self.consecutive_errors >= self.max_errors:
            logger.error("Max errors reached, halting signal generation")
            return False
        
        return True
    
    async def process_signal(self, signal: TradingSignal):
        """
        Process trading signal and execute orders
        
        Args:
            signal: Trading signal from strategy engine
        """
        try:
            logger.info(f"Processing signal: {signal.action.value} @ ${signal.price:.4f}")
            
            self.system_stats["signals_generated"] += 1
            self.last_signal_time = datetime.utcnow()
            
            # Calculate position size
            position_size = self.strategy_engine.calculate_position_size(signal)
            
            # Execute order
            result = await self.order_executor.execute_signal(signal, position_size)
            
            if result.get("status") in ["success", "simulated"]:
                self.system_stats["orders_placed"] += 1
                
                # Update strategy position tracking
                if signal.action == SignalType.BUY:
                    size = position_size / signal.price
                    self.strategy_engine.update_position(size, signal.price, "long")
                    
                elif signal.action == SignalType.SELL:
                    size = -position_size / signal.price
                    self.strategy_engine.update_position(size, signal.price, "short")
                    
                elif signal.action == SignalType.EXIT:
                    pnl = self.strategy_engine.close_position(signal.price)
                    logger.info(f"Position closed, P&L: ${pnl:.2f}")
                
                # Log to Supabase
                await self.log_trade_signal(signal, result)
                
                # Reset error counter on success
                self.consecutive_errors = 0
                
            else:
                logger.warning(f"Order execution failed: {result}")
                self.consecutive_errors += 1
                
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            self.system_stats["errors"] += 1
            self.consecutive_errors += 1
    
    async def log_trade_signal(self, signal: TradingSignal, result: Dict):
        """Log trade signal to Supabase"""
        try:
            if self.supabase_client:
                data = {
                    "timestamp": signal.timestamp.isoformat(),
                    "action": signal.action.value,
                    "price": signal.price,
                    "z_score": signal.z_score,
                    "confidence": signal.confidence,
                    "reason": signal.reason,
                    "order_result": result,
                    "strategy": "mean_reversion",
                    "account": os.getenv('ACCOUNT_ADDRESS')
                }
                
                self.supabase_client.table("hl_signals").insert(data).execute()
                
        except Exception as e:
            logger.error(f"Failed to log signal: {e}")
    
    async def websocket_message_handler(self):
        """Handle messages from WebSocket manager"""
        
        while self.running:
            try:
                # Check for new messages in WebSocket manager's price buffer
                if self.websocket_manager.price_buffer:
                    # Get latest price
                    latest = self.websocket_manager.price_buffer[-1]
                    await self.process_price_update({
                        "price": latest["price"],
                        "volume": latest.get("size", 0)
                    })
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"WebSocket handler error: {e}")
                await asyncio.sleep(5)
    
    async def health_monitor(self):
        """Monitor system health and performance"""
        
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Get system statistics
                strategy_stats = self.strategy_engine.get_statistics()
                executor_stats = self.order_executor.get_statistics()
                ws_stats = self.websocket_manager.stats
                
                # Combine stats
                health_report = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "uptime_hours": (datetime.utcnow() - self.system_stats["start_time"]).total_seconds() / 3600,
                    "system": self.system_stats,
                    "strategy": strategy_stats,
                    "executor": executor_stats,
                    "websocket": ws_stats,
                    "status": "HEALTHY" if self.consecutive_errors < 5 else "WARNING"
                }
                
                # Log health
                logger.info(f"System Health: {health_report['status']}")
                logger.info(f"P&L: ${strategy_stats['total_pnl']:.2f} | Trades: {strategy_stats['total_trades']} | Win Rate: {strategy_stats['win_rate']:.1f}%")
                
                # Save to Supabase
                if self.supabase_client:
                    self.supabase_client.table("hl_system_health").insert({
                        "component": "trading_system",
                        "status": health_report["status"],
                        "details": health_report,
                        "checked_at": datetime.utcnow().isoformat()
                    }).execute()
                
                self.system_stats["last_health_check"] = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    async def emergency_shutdown(self):
        """Emergency shutdown procedure"""
        logger.warning("Initiating emergency shutdown...")
        
        try:
            # Cancel all orders
            cancelled = await self.order_executor.cancel_all_orders()
            logger.info(f"Cancelled {cancelled} orders")
            
            # Close any open positions (optional)
            if self.strategy_engine.current_position.size != 0:
                logger.warning("Open position detected during shutdown")
                # Could implement forced position closing here
            
            # Log shutdown
            if self.supabase_client:
                self.supabase_client.table("hl_system_health").insert({
                    "component": "trading_system",
                    "status": "SHUTDOWN",
                    "details": {
                        "reason": "emergency_shutdown",
                        "stats": self.system_stats
                    },
                    "checked_at": datetime.utcnow().isoformat()
                }).execute()
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def run(self):
        """Main execution loop"""
        logger.info("Starting HYPE Trading System...")
        self.running = True
        
        # Create tasks
        tasks = []
        
        # Start WebSocket manager
        tasks.append(asyncio.create_task(self.websocket_manager.run()))
        
        # Wait for WebSocket to connect
        await asyncio.sleep(5)
        
        # Start other components
        tasks.append(asyncio.create_task(self.websocket_message_handler()))
        tasks.append(asyncio.create_task(self.health_monitor()))
        
        # Add message processors from WebSocket manager
        for _ in range(3):  # 3 parallel processors
            tasks.append(asyncio.create_task(self.websocket_manager.message_processor()))
        
        try:
            # Log startup
            if self.supabase_client:
                self.supabase_client.table("hl_system_health").insert({
                    "component": "trading_system",
                    "status": "STARTED",
                    "details": {
                        "dry_run": self.dry_run,
                        "strategy": "mean_reversion",
                        "parameters": {
                            "lookback": self.strategy_engine.lookback_period,
                            "entry_z": self.strategy_engine.entry_z_score,
                            "exit_z": self.strategy_engine.exit_z_score
                        }
                    },
                    "checked_at": datetime.utcnow().isoformat()
                }).execute()
            
            logger.success(f"Trading System started (dry_run={self.dry_run})")
            
            # Run until interrupted
            await asyncio.gather(*tasks)
            
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        except Exception as e:
            logger.error(f"System error: {e}")
        finally:
            self.running = False
            await self.emergency_shutdown()
            
            # Cancel all tasks
            for task in tasks:
                task.cancel()
            
            logger.info("Trading System stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    raise KeyboardInterrupt


async def main():
    """Main entry point"""
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='HYPE Mean Reversion Trading System')
    parser.add_argument('--live', action='store_true', help='Run in live mode (real trades)')
    parser.add_argument('--test', action='store_true', help='Run test mode with sample data')
    args = parser.parse_args()
    
    # Determine mode
    dry_run = not args.live
    
    if args.live:
        logger.warning("RUNNING IN LIVE MODE - REAL TRADES WILL BE EXECUTED")
        response = input("Are you sure you want to run in LIVE mode? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Aborting live mode")
            return
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configure logging
    logger.add(
        f"logs/trading_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO"
    )
    
    # Create and run trading system
    system = TradingSystem(dry_run=dry_run)
    
    if args.test:
        # Run test mode
        logger.info("Running in test mode...")
        await test_system(system)
    else:
        # Run production mode
        await system.run()


async def test_system(system: TradingSystem):
    """Test the trading system with simulated data"""
    
    logger.info("Starting test mode with simulated data...")
    
    # Simulate price updates
    import numpy as np
    np.random.seed(42)
    
    base_price = 44.0
    for i in range(100):
        # Generate realistic price movement
        noise = np.random.normal(0, 0.5)
        trend = np.sin(i / 10) * 2  # Add cyclical pattern
        price = base_price + noise + trend
        volume = np.random.uniform(1000, 5000)
        
        # Update strategy
        system.strategy_engine.update_price(price, volume)
        
        # Generate signal every 5 iterations
        if i > system.strategy_engine.lookback_period and i % 5 == 0:
            signal = system.strategy_engine.generate_signal()
            
            if signal.action != SignalType.HOLD:
                await system.process_signal(signal)
        
        await asyncio.sleep(0.1)  # Small delay for testing
    
    # Print results
    stats = system.strategy_engine.get_statistics()
    logger.info("Test Complete:")
    logger.info(f"Total P&L: ${stats['total_pnl']:.2f}")
    logger.info(f"Total Trades: {stats['total_trades']}")
    logger.info(f"Win Rate: {stats['win_rate']:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())