"""
HYPE-specific paper trading runner
Monitors HYPE and executes trades based on triggers
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from paper_trader import PaperTradingAccount, PaperOrder
from config_hype import CONFIG, get_position_size, should_trade
import websockets
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [HYPE-TRADER] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class HYPEPaperTrader:
    """HYPE-focused paper trading system"""
    
    def __init__(self):
        self.config = CONFIG
        self.account: Optional[PaperTradingAccount] = None
        self.symbol = "HYPE"
        self.last_price = CONFIG["hype"]["typical_price"]
        self.position_count = 0
        self.daily_trades = 0
        self.last_trade_time = 0
        self.running = True
        
    async def initialize(self):
        """Initialize the paper trading account"""
        self.account = PaperTradingAccount(
            CONFIG["trading"]["account_name"],
            CONFIG["trading"]["initial_balance"]
        )
        await self.account.initialize()
        logger.info(f"Initialized HYPE paper trader with ${CONFIG['trading']['initial_balance']:,.2f}")
        
    async def connect_websocket(self):
        """Connect to Hyperliquid WebSocket for HYPE data"""
        ws_url = "wss://api.hyperliquid.xyz/ws"
        
        try:
            async with websockets.connect(ws_url, ping_interval=20) as ws:
                # Subscribe to HYPE data
                subscribe_msg = {
                    "method": "subscribe",
                    "subscription": {
                        "type": "trades",
                        "coin": "HYPE"
                    }
                }
                await ws.send(json.dumps(subscribe_msg))
                
                # Also subscribe to order book
                book_msg = {
                    "method": "subscribe",
                    "subscription": {
                        "type": "l2Book",
                        "coin": "HYPE"
                    }
                }
                await ws.send(json.dumps(book_msg))
                
                logger.info("Connected to Hyperliquid WebSocket for HYPE")
                
                # Process messages
                while self.running:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(msg)
                        await self.process_market_data(data)
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            await asyncio.sleep(5)
            
    async def process_market_data(self, data: dict):
        """Process incoming market data"""
        if data.get("channel") == "trades":
            trades = data.get("data", [])
            if trades:
                # Update last price
                for trade in trades:
                    if trade.get("coin") == "HYPE":
                        self.last_price = float(trade["px"])
                        
        elif data.get("channel") == "l2Book":
            book = data.get("data", {})
            if book.get("coin") == "HYPE":
                # Process order book data
                levels = book.get("levels", [])
                if levels:
                    # Best bid/ask
                    best_bid = float(levels[0][0]["px"]) if levels[0] else self.last_price
                    best_ask = float(levels[1][0]["px"]) if len(levels) > 1 and levels[1] else self.last_price
                    self.last_price = (best_bid + best_ask) / 2
                    
        # Update account prices
        await self.account.update_prices({"HYPE": self.last_price})
        
    async def simulate_triggers(self):
        """Simulate trigger signals for HYPE trading"""
        while self.running:
            try:
                # Generate simulated trigger based on market conditions
                trigger_signal = await self.evaluate_market_conditions()
                
                if trigger_signal:
                    await self.execute_trade(trigger_signal)
                
                # Check account status periodically
                if self.config["monitoring"]["print_summary"]:
                    summary = self.account.get_account_summary()
                    logger.info(f"Balance: ${summary['balance']:.2f}, P&L: ${summary['total_pnl']:.2f} "
                              f"({summary['total_pnl_pct']:.2f}%), Positions: {summary['open_positions']}")
                
                await asyncio.sleep(self.config["monitoring"]["update_interval"])
                
            except Exception as e:
                logger.error(f"Error in trigger simulation: {e}")
                await asyncio.sleep(5)
                
    async def evaluate_market_conditions(self) -> Optional[dict]:
        """Evaluate market conditions and generate trading signals"""
        # Simple momentum-based trigger simulation
        import random
        
        # Simulate trigger confidence
        confidence = random.uniform(0.4, 0.9)
        
        # Determine signal type based on simulated market conditions
        signal_types = [
            ("momentum_long", "buy"),
            ("momentum_short", "sell"),
            ("breakout_up", "buy"),
            ("breakout_down", "sell"),
            ("funding_arbitrage", "buy"),
            ("volume_spike_up", "buy"),
            ("volume_spike_down", "sell")
        ]
        
        trigger_name, side = random.choice(signal_types)
        
        # Check if we should trade
        features = {
            "last_px": self.last_price,
            "funding_bp": random.uniform(-50, 50),  # Simulated funding
            "volume_spike": random.uniform(0.5, 3.0)  # Simulated volume
        }
        
        if should_trade(trigger_name, confidence, features):
            # Check cooldown
            current_time = time.time()
            if current_time - self.last_trade_time < 30:  # 30 second cooldown
                return None
                
            # Check position limits
            positions = self.account.get_open_positions()
            hype_positions = [p for p in positions if p["symbol"] == "HYPE"]
            
            if len(hype_positions) >= self.config["risk"]["max_positions"]:
                logger.info(f"Max positions reached ({len(hype_positions)}), skipping signal")
                return None
                
            return {
                "trigger_name": trigger_name,
                "side": side,
                "confidence": confidence,
                "features": features
            }
            
        return None
        
    async def execute_trade(self, signal: dict):
        """Execute a trade based on signal"""
        try:
            # Calculate position size
            position_size = get_position_size(signal["confidence"])
            
            if position_size == 0:
                logger.debug(f"Position size is 0 for confidence {signal['confidence']:.2f}")
                return
                
            # Create order
            order = PaperOrder(
                symbol="HYPE",
                side=signal["side"],
                order_type="market",
                size=position_size,
                trigger_name=signal["trigger_name"],
                trigger_confidence=signal["confidence"],
                notes=f"HYPE trader signal at ${self.last_price:.2f}"
            )
            
            # Place order
            order_id = await self.account.place_order(order)
            
            if order_id:
                self.last_trade_time = time.time()
                self.daily_trades += 1
                logger.info(f"Executed {signal['side']} {position_size} HYPE @ ${self.last_price:.2f} "
                          f"(Trigger: {signal['trigger_name']}, Confidence: {signal['confidence']:.2%})")
                
                # Save performance metrics
                if self.config["monitoring"]["save_trades_to_db"]:
                    await self.account.save_performance_metrics()
                    
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            
    async def run(self):
        """Main run loop"""
        await self.initialize()
        
        # Create tasks for concurrent operation
        tasks = [
            asyncio.create_task(self.connect_websocket()),
            asyncio.create_task(self.simulate_triggers()),
            asyncio.create_task(self.monitor_performance())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down HYPE trader...")
            self.running = False
            
    async def monitor_performance(self):
        """Monitor and save performance metrics"""
        while self.running:
            try:
                await asyncio.sleep(self.config["monitoring"]["performance_save_interval"])
                
                # Save performance
                await self.account.save_performance_metrics()
                
                # Get summary
                summary = self.account.get_account_summary()
                
                # Log performance
                logger.info(f"Performance Update - Balance: ${summary['balance']:.2f}, "
                          f"P&L: ${summary['total_pnl']:.2f} ({summary['total_pnl_pct']:.2f}%), "
                          f"Win Rate: {summary['win_rate']:.1f}%, "
                          f"Max Drawdown: {summary['max_drawdown']:.2f}%")
                
                # Check daily loss limit
                if summary['total_pnl_pct'] / 100 < -self.config["risk"]["max_daily_loss"]:
                    logger.warning(f"Daily loss limit reached ({self.config['risk']['max_daily_loss']:.1%})")
                    # Could implement trade suspension here
                    
            except Exception as e:
                logger.error(f"Error monitoring performance: {e}")


async def main():
    """Main entry point"""
    print("="*60)
    print("HYPE Paper Trading System")
    print(f"Account: {CONFIG['trading']['account_name']}")
    print(f"Initial Balance: ${CONFIG['trading']['initial_balance']:,.2f}")
    print(f"Base Position Size: {CONFIG['trading']['base_position_size']} HYPE")
    print(f"Max Positions: {CONFIG['risk']['max_positions']}")
    print(f"Min Confidence: {CONFIG['triggers']['confidence_min']:.1%}")
    print("="*60)
    print("Starting HYPE paper trader...")
    print("Press Ctrl+C to stop\n")
    
    trader = HYPEPaperTrader()
    await trader.run()


if __name__ == "__main__":
    asyncio.run(main())