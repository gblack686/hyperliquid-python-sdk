import os
import sys
import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from loguru import logger

# Add quantpylib to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'quantpylib'))

from quantpylib.wrappers.hyperliquid import Hyperliquid
from quantpylib.standards import Period

class HyperliquidClient:
    def __init__(self, key: Optional[str] = None, secret: Optional[str] = None, mode: str = "mainnet"):
        self.key = key
        self.secret = secret
        self.mode = mode
        self.client: Optional[Hyperliquid] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_interval = 5
        self.subscriptions = {}
        
    async def connect(self):
        try:
            # Quantpylib expects:
            # - key: public address (optional)
            # - secret: private key (optional)
            # If secret is provided, it will derive the address from it
            self.client = Hyperliquid(
                key=None,  # Let quantpylib derive this from secret
                secret=self.key,  # This is actually the private key
                mode=self.mode
            )
            await self.client.init_client()
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("Successfully connected to Hyperliquid")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Hyperliquid: {e}")
            self.is_connected = False
            return False
    
    async def ensure_connected(self):
        if not self.is_connected:
            return await self.connect()
        return True
    
    async def reconnect(self):
        while self.reconnect_attempts < self.max_reconnect_attempts:
            logger.info(f"Attempting to reconnect... (Attempt {self.reconnect_attempts + 1}/{self.max_reconnect_attempts})")
            if await self.connect():
                await self.resubscribe()
                return True
            self.reconnect_attempts += 1
            await asyncio.sleep(self.reconnect_interval)
        logger.error("Max reconnection attempts reached")
        return False
    
    async def resubscribe(self):
        for sub_type, params in self.subscriptions.items():
            try:
                if sub_type == "all_mids":
                    await self.client.all_mids_subscribe(**params)
                elif sub_type == "l2_book":
                    await self.client.l2_book_subscribe(**params)
                elif sub_type == "account_fill":
                    await self.client.account_fill_subscribe(**params)
                elif sub_type == "order_updates":
                    await self.client.order_updates_subscribe(**params)
                logger.info(f"Resubscribed to {sub_type}")
            except Exception as e:
                logger.error(f"Failed to resubscribe to {sub_type}: {e}")
    
    async def get_account_balance(self) -> Optional[Dict]:
        if not await self.ensure_connected():
            return None
        try:
            return await self.client.account_balance()
        except Exception as e:
            # Completely avoid any string conversion of the exception
            logger.debug("Account balance fetch failed - likely using read-only API key")
            return None
    
    async def get_positions(self, is_perpetuals: bool = True) -> Optional[List]:
        if not await self.ensure_connected():
            return None
        try:
            return await self.client.positions_get(is_perpetuals=is_perpetuals)
        except Exception as e:
            logger.debug("Positions fetch failed - likely using read-only API key")
            return None
    
    async def get_open_orders(self, as_canonical: bool = False) -> Optional[List]:
        if not await self.ensure_connected():
            return None
        try:
            return await self.client.orders_get(as_canonical=as_canonical)
        except Exception as e:
            logger.error(f"Error fetching open orders: {str(e)[:200]}")
            return None
    
    async def get_l2_book(self, ticker: str, depth: int = 20) -> Optional[Dict]:
        if not await self.ensure_connected():
            return None
        try:
            return await self.client.l2_book_get(ticker=ticker)
        except Exception as e:
            logger.error(f"Error fetching L2 book for {ticker}: {str(e)[:200]}")
            return None
    
    async def get_all_mids(self) -> Optional[Dict]:
        if not await self.ensure_connected():
            return None
        try:
            return await self.client.get_all_mids()
        except Exception as e:
            logger.error(f"Error fetching mid prices: {str(e)[:200]}")
            return None
    
    async def get_historical_candles(
        self, 
        ticker: str, 
        interval: str, 
        start: int, 
        end: int
    ) -> Optional[List]:
        if not await self.ensure_connected():
            return None
        try:
            # Use the correct quantpylib method name
            result = await self.client.candle_historical(
                ticker=ticker,
                interval=interval,
                start=start,
                end=end
            )
            return result if result else None
        except Exception as e:
            logger.error(f"Error fetching historical candles: {str(e)[:200]}")
            return None
    
    async def get_trade_bars(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
        granularity: Period = Period.MINUTE,
        granularity_multiplier: int = 15
    ) -> Optional[Any]:
        if not await self.ensure_connected():
            return None
        try:
            # get_trade_bars returns a DataFrame
            df = await self.client.get_trade_bars(
                ticker=ticker,
                start=start,
                end=end,
                granularity=granularity,
                granularity_multiplier=granularity_multiplier
            )
            # Check if DataFrame is empty
            if df is not None and not df.empty:
                return df
            return None
        except Exception as e:
            logger.error(f"Error fetching trade bars: {str(e)[:200]}")
            return None
    
    async def subscribe_all_mids(self, handler: Callable, as_canonical: bool = False):
        if not await self.ensure_connected():
            return False
        try:
            await self.client.all_mids_subscribe(handler=handler, as_canonical=as_canonical)
            self.subscriptions["all_mids"] = {"handler": handler, "as_canonical": as_canonical}
            logger.info("Subscribed to all mid prices")
            return True
        except Exception as e:
            logger.error(f"Error subscribing to all mids: {str(e)[:200]}")
            return False
    
    async def subscribe_l2_book(self, ticker: str, handler: Callable, depth: int = 20):
        if not await self.ensure_connected():
            return False
        try:
            await self.client.l2_book_subscribe(ticker, handler=handler)
            self.subscriptions[f"l2_book_{ticker}"] = {"ticker": ticker, "handler": handler}
            logger.info(f"Subscribed to L2 book for {ticker}")
            return True
        except Exception as e:
            logger.error(f"Error subscribing to L2 book: {str(e)[:200]}")
            return False
    
    async def subscribe_account_fills(self, handler: Callable):
        if not await self.ensure_connected():
            return False
        try:
            await self.client.account_fill_subscribe(handler=handler)
            self.subscriptions["account_fill"] = {"handler": handler}
            logger.info("Subscribed to account fills")
            return True
        except Exception as e:
            logger.error(f"Error subscribing to account fills: {str(e)[:200]}")
            return False
    
    async def subscribe_order_updates(self, handler: Callable):
        if not await self.ensure_connected():
            return False
        try:
            await self.client.order_updates_subscribe(handler=handler)
            self.subscriptions["order_updates"] = {"handler": handler}
            logger.info("Subscribed to order updates")
            return True
        except Exception as e:
            logger.error(f"Error subscribing to order updates: {str(e)[:200]}")
            return False
    
    async def place_limit_order(
        self,
        ticker: str,
        amount: float,
        price: float,
        tp: Optional[float] = None,
        sl: Optional[float] = None
    ) -> Optional[Dict]:
        if not await self.ensure_connected():
            return None
        try:
            return await self.client.limit_order(
                ticker=ticker,
                amount=amount,
                price=price,
                tp=tp,
                sl=sl
            )
        except Exception as e:
            logger.error(f"Error placing limit order: {str(e)[:200]}")
            return None
    
    async def place_market_order(self, ticker: str, amount: float) -> Optional[Dict]:
        if not await self.ensure_connected():
            return None
        try:
            return await self.client.market_order(ticker=ticker, amount=amount)
        except Exception as e:
            logger.error(f"Error placing market order: {str(e)[:200]}")
            return None
    
    async def cancel_order(self, ticker: str, oid: int, is_canonical: bool = False) -> Optional[Dict]:
        if not await self.ensure_connected():
            return None
        try:
            return await self.client.cancel_order(ticker, oid=oid, is_canonical=is_canonical)
        except Exception as e:
            logger.error(f"Error canceling order: {str(e)[:200]}")
            return None
    
    async def cancel_all_orders(self, ticker: str, is_canonical: bool = False) -> Optional[Dict]:
        if not await self.ensure_connected():
            return None
        try:
            return await self.client.cancel_open_orders(ticker=ticker, is_canonical=is_canonical)
        except Exception as e:
            logger.error(f"Error canceling all orders: {str(e)[:200]}")
            return None
    
    async def cleanup(self):
        if self.client:
            try:
                await self.client.cleanup()
                logger.info("Hyperliquid client cleaned up")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)[:200]}")
        self.is_connected = False