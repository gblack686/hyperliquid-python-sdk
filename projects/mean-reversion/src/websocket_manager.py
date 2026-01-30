"""
Production WebSocket Manager with Supabase Integration
Handles real-time data streaming from Hyperliquid with automatic reconnection
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from collections import deque
import time

import eth_account
from eth_account.signers.local import LocalAccount
from dotenv import load_dotenv
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from supabase import create_client, Client

# Add parent directory to path
sys.path.append('..')
from hyperliquid.info import Info
from hyperliquid.utils import constants

# Load environment variables
load_dotenv()


class WebSocketManager:
    """
    Production-ready WebSocket manager with automatic reconnection and Supabase logging
    """
    
    def __init__(self, supabase_client: Optional[Client] = None):
        """Initialize WebSocket manager"""
        
        # Configuration
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        self.private_key = os.getenv('HYPERLIQUID_API_KEY')
        self.network = os.getenv('NETWORK', 'MAINNET_API_URL')
        
        if not self.account_address or not self.private_key:
            logger.error("Missing Hyperliquid credentials in .env")
            raise ValueError("Missing required credentials")
        
        # Initialize Hyperliquid
        self.account: LocalAccount = eth_account.Account.from_key(self.private_key)
        self.base_url = getattr(constants, self.network)
        self.info: Optional[Info] = None
        
        # Supabase client
        self.supabase = supabase_client
        if not self.supabase:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            if supabase_url and supabase_key:
                self.supabase = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialized")
        
        # State management
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_delay = 60
        self.subscriptions = {}
        self.message_queue = asyncio.Queue(maxsize=10000)
        
        # Performance tracking
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "errors": 0,
            "last_message_time": None,
            "connection_start": None
        }
        
        # Price tracking for candle generation
        self.price_buffer = deque(maxlen=60)  # Keep last 60 prices
        self.last_candle_time = None
        
        logger.info(f"WebSocket Manager initialized for {self.account_address}")
    
    async def connect(self) -> bool:
        """Establish WebSocket connection"""
        try:
            logger.info("Connecting to Hyperliquid WebSocket...")
            
            # Initialize with WebSocket enabled
            self.info = Info(self.base_url, skip_ws=False)
            
            self.is_connected = True
            self.reconnect_attempts = 0
            self.stats["connection_start"] = datetime.utcnow()
            
            logger.success("WebSocket connection established")
            
            # Log connection to Supabase
            await self.log_system_event("websocket_connected", {
                "account": self.account_address,
                "network": self.network
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.is_connected = False
            return False
    
    async def setup_subscriptions(self):
        """Setup all WebSocket subscriptions"""
        
        subscriptions = [
            # Market data
            {"type": "trades", "coin": "HYPE"},
            {"type": "l2Book", "coin": "HYPE"},
            {"type": "candle", "coin": "HYPE", "interval": "1h"},
            
            # Account data
            {"type": "orderUpdates", "user": self.account_address},
            {"type": "userFills", "user": self.account_address},
            {"type": "userEvents", "user": self.account_address},
            {"type": "webData2", "user": self.account_address}
        ]
        
        for sub in subscriptions:
            try:
                channel = sub.get("type")
                
                # Create specific handler for each channel
                if channel == "trades":
                    handler = self.handle_trades
                elif channel == "l2Book":
                    handler = self.handle_orderbook
                elif channel == "candle":
                    handler = self.handle_candles
                elif channel == "orderUpdates":
                    handler = self.handle_order_updates
                elif channel == "userFills":
                    handler = self.handle_fills
                elif channel == "userEvents":
                    handler = self.handle_user_events
                elif channel == "webData2":
                    handler = self.handle_web_data
                else:
                    handler = self.handle_generic_message
                
                # Subscribe with wrapper to catch errors
                subscription_id = self.info.subscribe(
                    sub, 
                    lambda data, ch=channel: asyncio.create_task(
                        self.process_message(ch, data)
                    )
                )
                
                self.subscriptions[channel] = {"subscription": sub, "id": subscription_id}
                logger.info(f"Subscribed to {channel} (ID: {subscription_id})")
                
            except Exception as e:
                logger.error(f"Failed to subscribe to {sub}: {e}")
    
    async def process_message(self, channel: str, data: Any):
        """Process incoming WebSocket message"""
        try:
            # Update stats
            self.stats["messages_received"] += 1
            self.stats["last_message_time"] = datetime.utcnow()
            
            # Create message object
            message = {
                "channel": channel,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
                "account": self.account_address
            }
            
            # Add to queue for async processing
            if self.message_queue.full():
                # Remove oldest message if queue is full
                try:
                    self.message_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            
            await self.message_queue.put(message)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.stats["errors"] += 1
    
    async def message_processor(self):
        """Process messages from queue"""
        while True:
            try:
                # Get message with timeout
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=5.0
                )
                
                channel = message["channel"]
                data = message["data"]
                
                # Route to specific handler
                if channel == "trades":
                    await self.handle_trades(data)
                elif channel == "l2Book":
                    await self.handle_orderbook(data)
                elif channel == "candle":
                    await self.handle_candles(data)
                elif channel == "orderUpdates":
                    await self.handle_order_updates(data)
                elif channel == "userFills":
                    await self.handle_fills(data)
                elif channel == "userEvents":
                    await self.handle_user_events(data)
                elif channel == "webData2":
                    await self.handle_web_data(data)
                
                self.stats["messages_processed"] += 1
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message processor error: {e}")
                self.stats["errors"] += 1
    
    async def handle_trades(self, data: Dict):
        """Handle trade updates"""
        try:
            # Extract trade data
            if isinstance(data, dict):
                trades = data.get("data", [data])
            elif isinstance(data, list):
                trades = data
            else:
                trades = [data]
            
            for trade in trades:
                if isinstance(trade, dict):
                    price = float(trade.get("px", 0))
                    size = float(trade.get("sz", 0))
                    side = trade.get("side", "")
                    
                    if price > 0:
                        # Update price buffer
                        self.price_buffer.append({
                            "price": price,
                            "size": size,
                            "side": side,
                            "time": datetime.utcnow()
                        })
                        
                        # Log significant trades
                        if size > 1000:  # Log trades > $1000
                            logger.info(f"Large trade: {side} {size:.2f} HYPE @ ${price:.4f}")
                            
                            if self.supabase:
                                await self.log_trade(trade)
            
        except Exception as e:
            logger.error(f"Error handling trades: {e}")
    
    async def handle_orderbook(self, data: Dict):
        """Handle orderbook updates"""
        try:
            # Extract best bid/ask for monitoring
            if isinstance(data, dict) and "levels" in data:
                levels = data["levels"]
                if len(levels) > 0:
                    best_bid = levels[0][0].get("px") if levels[0] else None
                    best_ask = levels[0][1].get("px") if len(levels[0]) > 1 else None
                    
                    # Could store in Redis for quick access
                    # await self.redis.set("hype:best_bid", best_bid)
                    # await self.redis.set("hype:best_ask", best_ask)
                    
        except Exception as e:
            logger.error(f"Error handling orderbook: {e}")
    
    async def handle_candles(self, data: Dict):
        """Handle candle updates"""
        try:
            # Process candle data for strategy
            if isinstance(data, dict):
                candle = {
                    "open": float(data.get("o", 0)),
                    "high": float(data.get("h", 0)),
                    "low": float(data.get("l", 0)),
                    "close": float(data.get("c", 0)),
                    "volume": float(data.get("v", 0)),
                    "time": datetime.fromtimestamp(data.get("t", 0) / 1000)
                }
                
                # Trigger strategy update
                logger.debug(f"New candle: O:{candle['open']:.4f} H:{candle['high']:.4f} L:{candle['low']:.4f} C:{candle['close']:.4f}")
                
                # This will be picked up by strategy engine
                # await self.strategy_callback(candle)
                
        except Exception as e:
            logger.error(f"Error handling candles: {e}")
    
    async def handle_order_updates(self, data: Dict):
        """Handle order updates"""
        try:
            orders = self.parse_data_format(data)
            
            for order in orders:
                if isinstance(order, dict):
                    order_id = order.get("oid")
                    status = order.get("order_status", order.get("status"))
                    
                    logger.info(f"Order update: {order_id} - {status}")
                    
                    # Save to Supabase
                    if self.supabase and order_id:
                        await self.save_order_update(order)
                        
        except Exception as e:
            logger.error(f"Error handling order updates: {e}")
    
    async def handle_fills(self, data: Dict):
        """Handle fill updates"""
        try:
            fills = self.parse_data_format(data)
            
            for fill in fills:
                if isinstance(fill, dict):
                    size = float(fill.get("sz", 0))
                    price = float(fill.get("px", 0))
                    side = fill.get("side", "")
                    fee = float(fill.get("fee", 0))
                    
                    logger.info(f"Fill: {side} {size:.4f} HYPE @ ${price:.4f} (fee: ${fee:.6f})")
                    
                    # Save to Supabase
                    if self.supabase:
                        await self.save_fill(fill)
                        
        except Exception as e:
            logger.error(f"Error handling fills: {e}")
    
    async def handle_user_events(self, data: Dict):
        """Handle user events"""
        try:
            events = self.parse_data_format(data)
            
            for event in events:
                if isinstance(event, dict):
                    event_type = event.get("type", "unknown")
                    logger.info(f"User event: {event_type}")
                    
                    # Log important events
                    if event_type in ["liquidation", "margin_call", "funding"]:
                        logger.warning(f"Important event: {event_type} - {event}")
                        await self.send_alert(f"Event: {event_type}", event)
                        
        except Exception as e:
            logger.error(f"Error handling user events: {e}")
    
    async def handle_web_data(self, data: Dict):
        """Handle web data (positions, margin, etc)"""
        try:
            if isinstance(data, dict):
                # Extract account state
                margin_summary = data.get("marginSummary", {})
                positions = data.get("assetPositions", [])
                
                # Log account health
                if margin_summary:
                    account_value = float(margin_summary.get("accountValue", 0))
                    margin_used = float(margin_summary.get("marginUsed", 0))
                    
                    logger.debug(f"Account: Value=${account_value:.2f}, Margin=${margin_used:.2f}")
                    
                    # Save snapshot
                    if self.supabase:
                        await self.save_account_snapshot(data)
                        
        except Exception as e:
            logger.error(f"Error handling web data: {e}")
    
    async def handle_generic_message(self, data: Dict):
        """Handle generic messages"""
        logger.debug(f"Generic message: {data}")
    
    def parse_data_format(self, data: Any) -> list:
        """Parse various data formats into list"""
        if isinstance(data, dict):
            if "data" in data:
                return data["data"] if isinstance(data["data"], list) else [data["data"]]
            return [data]
        elif isinstance(data, list):
            return data
        return []
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
    async def reconnect(self):
        """Reconnect with exponential backoff"""
        self.reconnect_attempts += 1
        logger.warning(f"Reconnection attempt {self.reconnect_attempts}")
        
        # Close existing connection
        self.is_connected = False
        self.info = None
        
        # Wait before reconnecting
        delay = min(2 ** self.reconnect_attempts, self.max_reconnect_delay)
        await asyncio.sleep(delay)
        
        # Try to connect
        if await self.connect():
            await self.setup_subscriptions()
            return True
        
        raise Exception("Reconnection failed")
    
    async def heartbeat_monitor(self):
        """Monitor connection health"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Check last message time
                if self.stats["last_message_time"]:
                    time_since = datetime.utcnow() - self.stats["last_message_time"]
                    
                    if time_since > timedelta(minutes=2):
                        logger.warning("No messages for 2 minutes, reconnecting...")
                        await self.reconnect()
                
                # Log stats
                logger.debug(f"WebSocket stats: {self.stats}")
                
                # Save health check
                if self.supabase:
                    await self.log_health_check()
                    
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
    
    # Supabase integration methods
    async def save_order_update(self, order: Dict):
        """Save order update to Supabase"""
        try:
            data = {
                "account_address": self.account_address,
                "order_id": order.get("oid"),
                "coin": order.get("coin", "HYPE"),
                "side": order.get("side"),
                "order_type": order.get("orderType"),
                "size": float(order.get("sz", 0)),
                "limit_price": float(order.get("limitPx", 0)) if order.get("limitPx") else None,
                "filled": float(order.get("filled", 0)),
                "status": order.get("order_status", order.get("status")),
                "order_time": datetime.utcnow().isoformat(),
                "raw_order": order
            }
            
            # Upsert to handle updates
            self.supabase.table("hl_orders").upsert(
                data, 
                on_conflict="order_id"
            ).execute()
            
        except Exception as e:
            logger.error(f"Failed to save order: {e}")
    
    async def save_fill(self, fill: Dict):
        """Save fill to Supabase"""
        try:
            data = {
                "account_address": self.account_address,
                "fill_id": fill.get("tid", f"{fill.get('oid')}_{int(time.time())}"),
                "order_id": fill.get("oid"),
                "coin": fill.get("coin", "HYPE"),
                "side": fill.get("side"),
                "size": float(fill.get("sz", 0)),
                "price": float(fill.get("px", 0)),
                "fee": float(fill.get("fee", 0)),
                "fill_time": datetime.utcnow().isoformat(),
                "raw_fill": fill
            }
            
            self.supabase.table("hl_fills").insert(data).execute()
            
        except Exception as e:
            if "duplicate" not in str(e).lower():
                logger.error(f"Failed to save fill: {e}")
    
    async def save_account_snapshot(self, data: Dict):
        """Save account snapshot to Supabase"""
        try:
            snapshot = {
                "account_address": self.account_address,
                "snapshot_time": datetime.utcnow().isoformat(),
                "account_value": float(data.get("marginSummary", {}).get("accountValue", 0)),
                "margin_used": float(data.get("marginSummary", {}).get("marginUsed", 0)),
                "positions": data.get("assetPositions", []),
                "raw_data": data
            }
            
            self.supabase.table("hl_dashboard").insert(snapshot).execute()
            
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
    
    async def log_trade(self, trade: Dict):
        """Log significant trade"""
        # Could implement trade logging logic
        pass
    
    async def log_system_event(self, event_type: str, details: Dict):
        """Log system events"""
        try:
            if self.supabase:
                self.supabase.table("hl_system_health").insert({
                    "component": "websocket_manager",
                    "status": event_type,
                    "details": details,
                    "checked_at": datetime.utcnow().isoformat()
                }).execute()
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
    
    async def log_health_check(self):
        """Log health check to Supabase"""
        try:
            if self.supabase:
                self.supabase.table("hl_system_health").insert({
                    "component": "websocket_manager",
                    "status": "HEALTHY" if self.is_connected else "ERROR",
                    "latency_ms": 0,  # Could calculate actual latency
                    "details": self.stats,
                    "checked_at": datetime.utcnow().isoformat()
                }).execute()
        except Exception as e:
            logger.error(f"Failed to log health check: {e}")
    
    async def send_alert(self, title: str, message: Dict):
        """Send alert for critical events"""
        logger.warning(f"ALERT: {title} - {message}")
        # Implement Discord/Telegram alerts here
    
    async def run(self):
        """Main execution loop"""
        logger.info("Starting WebSocket Manager...")
        
        # Connect and setup subscriptions
        if not await self.connect():
            logger.error("Failed to establish initial connection")
            return
        
        await self.setup_subscriptions()
        
        # Start concurrent tasks
        tasks = [
            asyncio.create_task(self.message_processor()),
            asyncio.create_task(self.heartbeat_monitor())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down WebSocket Manager...")
        except Exception as e:
            logger.error(f"WebSocket Manager error: {e}")
        finally:
            self.is_connected = False
            logger.info("WebSocket Manager stopped")


async def main():
    """Test WebSocket manager"""
    manager = WebSocketManager()
    await manager.run()


if __name__ == "__main__":
    # Configure logging
    logger.add(
        "logs/websocket_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    asyncio.run(main())