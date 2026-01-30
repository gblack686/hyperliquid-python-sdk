#!/usr/bin/env python3
"""
Live monitoring script - shows real-time HYPE data and signals
Connects to WebSocket and displays market activity
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from loguru import logger
from dotenv import load_dotenv
from websocket_manager import WebSocketManager
from strategy_engine import StrategyEngine, SignalType
from supabase import create_client

# Load environment
load_dotenv()


class LiveMonitor:
    """Monitor live HYPE market data"""
    
    def __init__(self):
        """Initialize monitor"""
        
        # Setup Supabase (optional)
        self.supabase = None
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        if supabase_url and supabase_key:
            self.supabase = create_client(supabase_url, supabase_key)
        
        # Initialize components
        self.websocket = WebSocketManager(self.supabase)
        self.strategy = StrategyEngine()
        
        # Tracking
        self.trade_count = 0
        self.signal_count = 0
        self.last_price = 0
        self.start_time = datetime.utcnow()
        
    async def process_trades(self):
        """Process trade updates from WebSocket"""
        
        print("\n[LIVE MARKET DATA STREAM]")
        print("-" * 70)
        print(f"{'Time':<12} {'Price':<10} {'Size':<10} {'Z-Score':<8} {'Signal':<10} {'Notes':<20}")
        print("-" * 70)
        
        while True:
            try:
                # Check for messages in queue
                if not self.websocket.message_queue.empty():
                    message = await self.websocket.message_queue.get()
                    
                    if message["channel"] == "trades":
                        data = message["data"]
                        
                        # Process trade data
                        if isinstance(data, dict) and "data" in data:
                            trades = data["data"]
                        elif isinstance(data, list):
                            trades = data
                        else:
                            trades = [data]
                        
                        for trade in trades:
                            if isinstance(trade, dict) and "px" in trade:
                                price = float(trade["px"])
                                size = float(trade.get("sz", 0))
                                side = trade.get("side", "")
                                
                                self.trade_count += 1
                                self.last_price = price
                                
                                # Update strategy
                                self.strategy.update_price(price, size * price)
                                
                                # Check for signals
                                signal_str = ""
                                if len(self.strategy.price_buffer) >= self.strategy.lookback_period:
                                    signal = self.strategy.generate_signal()
                                    
                                    if signal.action != SignalType.HOLD:
                                        self.signal_count += 1
                                        signal_str = f"[{signal.action.value}]"
                                        
                                        # Display signal details
                                        print(f"\n  >>> SIGNAL: {signal.action.value} @ ${price:.4f}")
                                        print(f"      Reason: {signal.reason}")
                                        print(f"      Confidence: {signal.confidence:.1%}\n")
                                
                                # Display trade
                                time_str = datetime.utcnow().strftime("%H:%M:%S")
                                price_str = f"${price:.4f}"
                                size_str = f"${size*price:.0f}"
                                z_score_str = f"{self.strategy.z_score:+.2f}"
                                
                                # Note large trades
                                note = ""
                                if size * price > 10000:
                                    note = "LARGE TRADE"
                                elif abs(self.strategy.z_score) > 1.5:
                                    note = "HIGH Z-SCORE"
                                
                                print(f"{time_str:<12} {price_str:<10} {size_str:<10} {z_score_str:<8} {signal_str:<10} {note:<20}")
                
                # Small delay
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error processing trades: {e}")
                await asyncio.sleep(1)
    
    async def display_stats(self):
        """Display periodic statistics"""
        
        while True:
            await asyncio.sleep(30)  # Update every 30 seconds
            
            runtime = (datetime.utcnow() - self.start_time).total_seconds() / 60
            
            print("\n" + "="*70)
            print(f"[STATISTICS UPDATE - {datetime.utcnow().strftime('%H:%M:%S')}]")
            print(f"  Runtime: {runtime:.1f} minutes")
            print(f"  Trades Processed: {self.trade_count}")
            print(f"  Signals Generated: {self.signal_count}")
            print(f"  Last Price: ${self.last_price:.4f}")
            
            if self.strategy.sma > 0:
                print(f"  SMA: ${self.strategy.sma:.4f}")
                print(f"  Std Dev: ${self.strategy.std:.4f}")
                print(f"  Current Z-Score: {self.strategy.z_score:+.2f}")
                print(f"  RSI: {self.strategy.rsi:.1f}")
                print(f"  Volatility: {self.strategy.volatility*100:.1f}%")
            
            stats = self.strategy.get_statistics()
            if stats['total_trades'] > 0:
                print(f"  Win Rate: {stats['win_rate']:.1f}%")
                print(f"  Total P&L: ${stats['total_pnl']:.2f}")
            
            print("="*70 + "\n")
    
    async def run(self):
        """Main execution"""
        
        print("\n" + "="*70)
        print("HYPE LIVE MARKET MONITOR")
        print("="*70)
        print(f"Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Account: {self.websocket.account_address}")
        print(f"Strategy: Mean Reversion (Entry Z: {self.strategy.entry_z_score}, Exit Z: {self.strategy.exit_z_score})")
        print("\nConnecting to Hyperliquid WebSocket...")
        
        # Connect WebSocket
        if not await self.websocket.connect():
            print("Failed to connect to WebSocket")
            return
        
        print("Connected! Setting up subscriptions...")
        await self.websocket.setup_subscriptions()
        
        print("Monitoring live market data... (Press Ctrl+C to stop)\n")
        
        # Create tasks
        tasks = [
            asyncio.create_task(self.websocket.message_processor()),
            asyncio.create_task(self.websocket.heartbeat_monitor()),
            asyncio.create_task(self.process_trades()),
            asyncio.create_task(self.display_stats())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
        finally:
            # Summary
            runtime = (datetime.utcnow() - self.start_time).total_seconds() / 60
            print("\n" + "="*70)
            print("SESSION SUMMARY")
            print("="*70)
            print(f"  Total Runtime: {runtime:.1f} minutes")
            print(f"  Trades Processed: {self.trade_count}")
            print(f"  Signals Generated: {self.signal_count}")
            
            if self.signal_count > 0:
                print(f"  Signal Rate: {self.signal_count / runtime:.2f} per minute")
            
            print(f"  Final Price: ${self.last_price:.4f}")
            print("="*70)


async def main():
    """Main entry point"""
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Run monitor
    monitor = LiveMonitor()
    await monitor.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")