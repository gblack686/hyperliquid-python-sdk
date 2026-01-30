"""
Order Execution System
Handles order placement, monitoring, and execution with Hyperliquid
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum

import eth_account
from eth_account.signers.local import LocalAccount
from loguru import logger
from dotenv import load_dotenv

sys.path.append('..')
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

from strategy_engine import TradingSignal, SignalType

load_dotenv()


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class OrderExecutor:
    """
    Handles order execution with Hyperliquid exchange
    """
    
    def __init__(self, dry_run: bool = True):
        """
        Initialize order executor
        
        Args:
            dry_run: If True, simulate orders without executing
        """
        
        self.dry_run = dry_run
        
        # Load credentials
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        self.private_key = os.getenv('HYPERLIQUID_API_KEY')
        self.network = os.getenv('NETWORK', 'MAINNET_API_URL')
        
        if not self.account_address or not self.private_key:
            logger.error("Missing Hyperliquid credentials")
            raise ValueError("Missing required credentials")
        
        # Initialize Hyperliquid connections
        self.account: LocalAccount = eth_account.Account.from_key(self.private_key)
        self.base_url = getattr(constants, self.network)
        self.info = Info(self.base_url, skip_ws=True)
        self.exchange = Exchange(self.account, self.base_url)
        
        # Configuration
        self.slippage_tolerance = float(os.getenv('SLIPPAGE_TOLERANCE', '0.002'))  # 0.2%
        self.min_order_size = float(os.getenv('MIN_ORDER_SIZE', '10'))  # $10 minimum
        self.order_timeout = int(os.getenv('ORDER_TIMEOUT', '30'))  # 30 seconds
        
        # Order tracking
        self.active_orders = {}
        self.order_history = []
        
        logger.info(f"Order Executor initialized (dry_run={dry_run})")
    
    async def execute_signal(self, signal: TradingSignal, position_size: float) -> Dict:
        """
        Execute trading signal
        
        Args:
            signal: Trading signal to execute
            position_size: Position size in USD
        
        Returns:
            Order result dictionary
        """
        
        if signal.action == SignalType.HOLD:
            return {"status": "skipped", "reason": "HOLD signal"}
        
        # Check minimum size
        if position_size < self.min_order_size:
            logger.warning(f"Position size ${position_size:.2f} below minimum ${self.min_order_size}")
            return {"status": "skipped", "reason": "Below minimum size"}
        
        # Route to appropriate handler
        if signal.action == SignalType.BUY:
            return await self.execute_buy(signal, position_size)
        elif signal.action == SignalType.SELL:
            return await self.execute_sell(signal, position_size)
        elif signal.action == SignalType.EXIT:
            return await self.execute_exit(signal)
        
        return {"status": "error", "reason": "Unknown signal type"}
    
    async def execute_buy(self, signal: TradingSignal, position_size: float) -> Dict:
        """Execute buy order"""
        
        try:
            # Get current market price
            current_price = await self.get_current_price("HYPE")
            
            # Calculate order details
            size = position_size / current_price  # Convert USD to HYPE
            limit_price = current_price * (1 + self.slippage_tolerance)
            
            logger.info(f"Executing BUY: {size:.4f} HYPE @ ${current_price:.4f} (limit: ${limit_price:.4f})")
            
            if self.dry_run:
                # Simulate order
                result = {
                    "status": "simulated",
                    "order_id": f"sim_{int(datetime.utcnow().timestamp())}",
                    "type": "BUY",
                    "size": size,
                    "price": current_price,
                    "value": position_size
                }
                logger.info(f"DRY RUN: Would buy {size:.4f} HYPE for ${position_size:.2f}")
                
            else:
                # Create order
                order_request = {
                    "coin": "HYPE",
                    "is_buy": True,
                    "sz": size,
                    "limit_px": limit_price,
                    "order_type": {"limit": {"tif": "Ioc"}},  # Immediate or cancel
                    "reduce_only": False
                }
                
                # Place order
                response = self.exchange.order(order_request, None)
                
                if response.get("status") == "ok":
                    order_id = response.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("resting", {}).get("oid")
                    
                    result = {
                        "status": "success",
                        "order_id": order_id,
                        "type": "BUY",
                        "size": size,
                        "price": current_price,
                        "value": position_size,
                        "response": response
                    }
                    
                    # Track order
                    self.active_orders[order_id] = result
                    
                    logger.success(f"Buy order placed: {order_id}")
                    
                else:
                    result = {
                        "status": "failed",
                        "error": response.get("response", "Unknown error"),
                        "type": "BUY"
                    }
                    logger.error(f"Buy order failed: {result['error']}")
            
            # Store in history
            self.order_history.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Error executing buy: {e}")
            return {"status": "error", "error": str(e), "type": "BUY"}
    
    async def execute_sell(self, signal: TradingSignal, position_size: float) -> Dict:
        """Execute sell/short order"""
        
        try:
            current_price = await self.get_current_price("HYPE")
            size = position_size / current_price
            limit_price = current_price * (1 - self.slippage_tolerance)
            
            logger.info(f"Executing SELL: {size:.4f} HYPE @ ${current_price:.4f} (limit: ${limit_price:.4f})")
            
            if self.dry_run:
                result = {
                    "status": "simulated",
                    "order_id": f"sim_{int(datetime.utcnow().timestamp())}",
                    "type": "SELL",
                    "size": size,
                    "price": current_price,
                    "value": position_size
                }
                logger.info(f"DRY RUN: Would sell {size:.4f} HYPE for ${position_size:.2f}")
                
            else:
                order_request = {
                    "coin": "HYPE",
                    "is_buy": False,
                    "sz": size,
                    "limit_px": limit_price,
                    "order_type": {"limit": {"tif": "Ioc"}},
                    "reduce_only": False
                }
                
                response = self.exchange.order(order_request, None)
                
                if response.get("status") == "ok":
                    order_id = response.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("resting", {}).get("oid")
                    
                    result = {
                        "status": "success",
                        "order_id": order_id,
                        "type": "SELL",
                        "size": size,
                        "price": current_price,
                        "value": position_size,
                        "response": response
                    }
                    
                    self.active_orders[order_id] = result
                    logger.success(f"Sell order placed: {order_id}")
                    
                else:
                    result = {
                        "status": "failed",
                        "error": response.get("response", "Unknown error"),
                        "type": "SELL"
                    }
                    logger.error(f"Sell order failed: {result['error']}")
            
            self.order_history.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Error executing sell: {e}")
            return {"status": "error", "error": str(e), "type": "SELL"}
    
    async def execute_exit(self, signal: TradingSignal) -> Dict:
        """Execute exit order (close position)"""
        
        try:
            # Get current position
            position = await self.get_current_position()
            
            if not position or position.get("size", 0) == 0:
                logger.warning("No position to exit")
                return {"status": "skipped", "reason": "No position"}
            
            size = abs(position["size"])
            is_buy = position["size"] < 0  # Buy to close short
            
            current_price = await self.get_current_price("HYPE")
            
            if is_buy:
                limit_price = current_price * (1 + self.slippage_tolerance)
            else:
                limit_price = current_price * (1 - self.slippage_tolerance)
            
            logger.info(f"Executing EXIT: {'BUY' if is_buy else 'SELL'} {size:.4f} HYPE @ ${current_price:.4f}")
            
            if self.dry_run:
                result = {
                    "status": "simulated",
                    "order_id": f"sim_{int(datetime.utcnow().timestamp())}",
                    "type": "EXIT",
                    "side": "BUY" if is_buy else "SELL",
                    "size": size,
                    "price": current_price
                }
                logger.info(f"DRY RUN: Would exit position")
                
            else:
                order_request = {
                    "coin": "HYPE",
                    "is_buy": is_buy,
                    "sz": size,
                    "limit_px": limit_price,
                    "order_type": {"limit": {"tif": "Ioc"}},
                    "reduce_only": True  # Important for exits
                }
                
                response = self.exchange.order(order_request, None)
                
                if response.get("status") == "ok":
                    order_id = response.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("resting", {}).get("oid")
                    
                    result = {
                        "status": "success",
                        "order_id": order_id,
                        "type": "EXIT",
                        "side": "BUY" if is_buy else "SELL",
                        "size": size,
                        "price": current_price,
                        "response": response
                    }
                    
                    logger.success(f"Exit order placed: {order_id}")
                    
                else:
                    result = {
                        "status": "failed",
                        "error": response.get("response", "Unknown error"),
                        "type": "EXIT"
                    }
                    logger.error(f"Exit order failed: {result['error']}")
            
            self.order_history.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Error executing exit: {e}")
            return {"status": "error", "error": str(e), "type": "EXIT"}
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        
        try:
            if self.dry_run:
                logger.info(f"DRY RUN: Would cancel order {order_id}")
                return True
            
            response = self.exchange.cancel({"coin": "HYPE", "oid": order_id})
            
            if response.get("status") == "ok":
                logger.info(f"Order cancelled: {order_id}")
                if order_id in self.active_orders:
                    del self.active_orders[order_id]
                return True
            else:
                logger.error(f"Failed to cancel order: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def cancel_all_orders(self) -> int:
        """Cancel all active orders"""
        
        cancelled_count = 0
        
        for order_id in list(self.active_orders.keys()):
            if await self.cancel_order(order_id):
                cancelled_count += 1
        
        logger.info(f"Cancelled {cancelled_count} orders")
        return cancelled_count
    
    async def get_current_price(self, coin: str = "HYPE") -> float:
        """Get current market price"""
        
        try:
            # Get mid price from orderbook
            l2_data = self.info.l2_snapshot(coin)
            
            if l2_data and "levels" in l2_data:
                levels = l2_data["levels"][0]
                if len(levels) >= 2:
                    best_bid = float(levels[0]["px"])
                    best_ask = float(levels[1]["px"])
                    mid_price = (best_bid + best_ask) / 2
                    return mid_price
            
            # Fallback to last trade price
            trades = self.info.user_trades(self.account_address)
            if trades:
                return float(trades[0]["px"])
            
            # Default fallback
            return 44.0  # Use recent average if no data
            
        except Exception as e:
            logger.error(f"Error getting price: {e}")
            return 44.0
    
    async def get_current_position(self) -> Optional[Dict]:
        """Get current position"""
        
        try:
            # Get user state
            user_state = self.info.user_state(self.account_address)
            
            if user_state and "assetPositions" in user_state:
                positions = user_state["assetPositions"]
                
                # Find HYPE position
                for position in positions:
                    if position.get("position", {}).get("coin") == "HYPE":
                        return {
                            "coin": "HYPE",
                            "size": float(position["position"].get("szi", 0)),
                            "entry_price": float(position["position"].get("entryPx", 0)),
                            "unrealized_pnl": float(position["position"].get("unrealizedPnl", 0)),
                            "margin_used": float(position["position"].get("marginUsed", 0))
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
    
    async def check_order_status(self, order_id: str) -> OrderStatus:
        """Check order status"""
        
        try:
            if self.dry_run:
                return OrderStatus.FILLED
            
            # Get open orders
            open_orders = self.info.open_orders(self.account_address)
            
            for order in open_orders:
                if order.get("oid") == order_id:
                    return OrderStatus.OPEN
            
            # Check if filled (would need to check fills)
            fills = self.info.user_fills(self.account_address)
            for fill in fills:
                if fill.get("oid") == order_id:
                    return OrderStatus.FILLED
            
            return OrderStatus.CANCELLED
            
        except Exception as e:
            logger.error(f"Error checking order status: {e}")
            return OrderStatus.FAILED
    
    async def wait_for_fill(self, order_id: str, timeout: int = None) -> bool:
        """
        Wait for order to be filled
        
        Args:
            order_id: Order ID to monitor
            timeout: Timeout in seconds
        
        Returns:
            True if filled, False if timeout or cancelled
        """
        
        timeout = timeout or self.order_timeout
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).seconds < timeout:
            status = await self.check_order_status(order_id)
            
            if status == OrderStatus.FILLED:
                logger.info(f"Order {order_id} filled")
                return True
            elif status in [OrderStatus.CANCELLED, OrderStatus.FAILED]:
                logger.warning(f"Order {order_id} {status.value}")
                return False
            
            await asyncio.sleep(1)
        
        logger.warning(f"Order {order_id} timeout after {timeout}s")
        return False
    
    def get_statistics(self) -> Dict:
        """Get execution statistics"""
        
        total_orders = len(self.order_history)
        successful = sum(1 for o in self.order_history if o.get("status") == "success")
        failed = sum(1 for o in self.order_history if o.get("status") == "failed")
        
        return {
            "total_orders": total_orders,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total_orders * 100) if total_orders > 0 else 0,
            "active_orders": len(self.active_orders),
            "dry_run": self.dry_run
        }


async def test_executor():
    """Test order executor"""
    
    from strategy_engine import TradingSignal, SignalType
    
    executor = OrderExecutor(dry_run=True)
    
    # Test buy signal
    buy_signal = TradingSignal(
        timestamp=datetime.utcnow(),
        action=SignalType.BUY,
        price=44.0,
        z_score=-1.5,
        confidence=0.8,
        reason="Test buy"
    )
    
    result = await executor.execute_signal(buy_signal, 100)
    print(f"Buy result: {result}")
    
    # Test current price
    price = await executor.get_current_price()
    print(f"Current price: ${price:.4f}")
    
    # Test statistics
    stats = executor.get_statistics()
    print(f"Statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(test_executor())