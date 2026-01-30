"""
Order Book Imbalance Indicator for Hyperliquid
Tracks bid/ask imbalance and order book dynamics
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque
import os
from dotenv import load_dotenv
import sys
import numpy as np
import functools

# Try to import hyperliquid - works both locally and in Docker
try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
except ImportError:
    sys.path.append('..')
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
from supabase import create_client, Client

# Import RateSemaphore for rate limiting
try:
    # Try to import from quantpylib if available
    sys.path.append('C:/Users/gblac/OneDrive/Desktop/hyperliquid-python-sdk/quantpylib')
    from quantpylib.throttler.rate_semaphore import AsyncRateSemaphore
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    # Fall back to custom implementation if needed
    RATE_LIMITING_AVAILABLE = False
    
    # Simple async rate limiter fallback
    class AsyncRateSemaphore:
        def __init__(self, credits=1, greedy_entry=False, greedy_exit=True):
            self.credits = credits
            self.lock = asyncio.Lock()
            self.last_call = 0
            self.min_interval = 0.2  # 200ms minimum between calls
            
        async def transact(self, coroutine, credits, refund_time, transaction_id=None, verbose=False):
            async with self.lock:
                # Simple rate limiting - ensure minimum interval between calls
                now = time.time()
                elapsed = now - self.last_call
                if elapsed < self.min_interval:
                    await asyncio.sleep(self.min_interval - elapsed)
                
                self.last_call = time.time()
                return await coroutine

load_dotenv()


class OrderBookImbalanceIndicator:
    """
    Tracks Order Book Imbalance metrics:
    - Bid/Ask ratio at different depths
    - Order book pressure (bid vs ask volume)
    - Large order detection
    - Support/Resistance levels from order book
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Initialize rate limiter
        # Hyperliquid allows 20 requests per second, but we'll be conservative
        # Using 10 credits with 1 second refund time = ~10 requests/second max
        self.rate_limiter = AsyncRateSemaphore(credits=10, greedy_exit=True)
        print(f"[OrderBook] Rate limiting {'enabled' if RATE_LIMITING_AVAILABLE else 'using fallback'}")
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Data storage
        self.orderbooks = defaultdict(dict)
        self.imbalance_history = defaultdict(lambda: deque(maxlen=300))  # 5 min of data
        self.support_levels = defaultdict(list)
        self.resistance_levels = defaultdict(list)
        
        # Metrics
        self.bid_ask_ratio = defaultdict(float)
        self.bid_volume = defaultdict(float)
        self.ask_volume = defaultdict(float)
        self.order_book_pressure = defaultdict(float)
        self.large_bid_orders = defaultdict(int)
        self.large_ask_orders = defaultdict(int)
        
        # WebSocket subscriptions
        self.subscriptions = {}
        
        # Timing
        self.last_update = time.time()
        self.last_snapshot = time.time()
        
    def subscribe_to_orderbooks(self):
        """Subscribe to order book updates via WebSocket"""
        # WebSocket disabled for now due to module conflicts
        print("[OrderBook] Using polling mode (WebSocket disabled)")
        return
    
    def process_orderbook_data(self, symbol: str, data: Any):
        """Process incoming order book data"""
        try:
            if isinstance(data, dict) and 'data' in data:
                book = data['data']
                
                if 'levels' in book:
                    # Full order book snapshot
                    self.orderbooks[symbol] = {
                        'bids': book['levels'][0],  # [[price, size], ...]
                        'asks': book['levels'][1],
                        'time': time.time()
                    }
                else:
                    # Incremental update
                    if symbol in self.orderbooks:
                        self.apply_orderbook_update(symbol, book)
                
                # Calculate metrics after update
                self.calculate_imbalance(symbol)
                
        except Exception as e:
            print(f"[OrderBook] Error processing data for {symbol}: {e}")
    
    def apply_orderbook_update(self, symbol: str, update: Dict):
        """Apply incremental order book update"""
        # This would handle incremental updates to the order book
        # For simplicity, we'll fetch the full book periodically
        pass
    
    async def fetch_orderbook(self, symbol: str):
        """Fetch order book snapshot from API with rate limiting"""
        try:
            # Wrap the API call in rate limiter
            async def fetch_coroutine():
                return self.info.l2_snapshot(symbol)
            
            # Use rate limiter with 1 credit per request, 1 second refund time
            book = await self.rate_limiter.transact(
                fetch_coroutine(),
                credits=1,
                refund_time=1.0,
                transaction_id=f"orderbook_{symbol}",
                verbose=False
            )
            
            if book and 'levels' in book:
                self.orderbooks[symbol] = {
                    'bids': book['levels'][0][:50],  # Top 50 bids
                    'asks': book['levels'][1][:50],  # Top 50 asks
                    'time': time.time()
                }
                return True
            return False
            
        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg:
                print(f"[OrderBook] Rate limited for {symbol}, will retry later")
            else:
                print(f"[OrderBook] Error fetching book for {symbol}: {e}")
            return False
    
    def calculate_imbalance(self, symbol: str):
        """Calculate order book imbalance metrics"""
        if symbol not in self.orderbooks:
            return
            
        book = self.orderbooks[symbol]
        bids = book.get('bids', [])
        asks = book.get('asks', [])
        
        if not bids or not asks:
            return
        
        # Calculate volumes at different depths
        depths = [5, 10, 20, 50]
        
        for depth in depths:
            # Handle both formats: dict with 'px'/'sz' or list [price, size]
            if bids and isinstance(bids[0], dict):
                bid_vol = sum(float(bid['sz']) * float(bid['px']) for bid in bids[:depth])
            else:
                bid_vol = sum(float(bid[1]) * float(bid[0]) for bid in bids[:depth])
            
            if asks and isinstance(asks[0], dict):
                ask_vol = sum(float(ask['sz']) * float(ask['px']) for ask in asks[:depth])
            else:
                ask_vol = sum(float(ask[1]) * float(ask[0]) for ask in asks[:depth])
            
            if depth == 10:  # Use depth 10 as primary metric
                self.bid_volume[symbol] = bid_vol
                self.ask_volume[symbol] = ask_vol
                
                # Calculate ratio (0-100 scale, 50 is balanced)
                total_vol = bid_vol + ask_vol
                if total_vol > 0:
                    self.bid_ask_ratio[symbol] = (bid_vol / total_vol) * 100
                else:
                    self.bid_ask_ratio[symbol] = 50
                
                # Calculate pressure (-100 to +100, positive is bullish)
                if total_vol > 0:
                    self.order_book_pressure[symbol] = ((bid_vol - ask_vol) / total_vol) * 100
                else:
                    self.order_book_pressure[symbol] = 0
        
        # Detect large orders (orders > 2x average size)
        if len(bids) > 5:
            if isinstance(bids[0], dict):
                avg_bid_size = np.mean([float(bid['sz']) for bid in bids[:20]])
                self.large_bid_orders[symbol] = sum(
                    1 for bid in bids[:20] if float(bid['sz']) > avg_bid_size * 2
                )
            else:
                avg_bid_size = np.mean([float(bid[1]) for bid in bids[:20]])
                self.large_bid_orders[symbol] = sum(
                    1 for bid in bids[:20] if float(bid[1]) > avg_bid_size * 2
                )
        
        if len(asks) > 5:
            if isinstance(asks[0], dict):
                avg_ask_size = np.mean([float(ask['sz']) for ask in asks[:20]])
                self.large_ask_orders[symbol] = sum(
                    1 for ask in asks[:20] if float(ask['sz']) > avg_ask_size * 2
                )
            else:
                avg_ask_size = np.mean([float(ask[1]) for ask in asks[:20]])
                self.large_ask_orders[symbol] = sum(
                    1 for ask in asks[:20] if float(ask[1]) > avg_ask_size * 2
                )
        
        # Identify support/resistance from large orders
        self.identify_sr_levels(symbol, bids, asks)
        
        # Add to history
        self.imbalance_history[symbol].append({
            'time': time.time(),
            'ratio': self.bid_ask_ratio[symbol],
            'pressure': self.order_book_pressure[symbol]
        })
    
    def identify_sr_levels(self, symbol: str, bids: List, asks: List):
        """Identify support and resistance levels from order book"""
        # Find clusters of large orders
        support_levels = []
        resistance_levels = []
        
        if bids:
            # Group bids by price clusters
            if isinstance(bids[0], dict):
                bid_sizes = [(float(bid['px']), float(bid['sz'])) for bid in bids[:20]]
            else:
                bid_sizes = [(float(bid[0]), float(bid[1])) for bid in bids[:20]]
            bid_sizes.sort(key=lambda x: x[1], reverse=True)  # Sort by size
            
            # Top 3 large bid levels are support
            for price, size in bid_sizes[:3]:
                support_levels.append(price)
        
        if asks:
            # Group asks by price clusters
            if isinstance(asks[0], dict):
                ask_sizes = [(float(ask['px']), float(ask['sz'])) for ask in asks[:20]]
            else:
                ask_sizes = [(float(ask[0]), float(ask[1])) for ask in asks[:20]]
            ask_sizes.sort(key=lambda x: x[1], reverse=True)  # Sort by size
            
            # Top 3 large ask levels are resistance
            for price, size in ask_sizes[:3]:
                resistance_levels.append(price)
        
        self.support_levels[symbol] = sorted(support_levels, reverse=True)[:3]
        self.resistance_levels[symbol] = sorted(resistance_levels)[:3]
    
    def calculate_orderbook_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate comprehensive order book metrics"""
        history = list(self.imbalance_history[symbol])
        
        # Calculate trend
        if len(history) >= 10:
            recent_pressure = [h['pressure'] for h in history[-10:]]
            older_pressure = [h['pressure'] for h in history[-20:-10]] if len(history) >= 20 else recent_pressure
            
            recent_avg = np.mean(recent_pressure)
            older_avg = np.mean(older_pressure)
            
            if recent_avg > older_avg + 10:
                trend = 'bullish'
            elif recent_avg < older_avg - 10:
                trend = 'bearish'
            else:
                trend = 'neutral'
        else:
            trend = 'neutral'
        
        # Determine market state
        current_ratio = self.bid_ask_ratio.get(symbol, 50)
        if current_ratio > 65:
            state = 'strong_bid'
        elif current_ratio < 35:
            state = 'strong_ask'
        elif 55 < current_ratio < 65:
            state = 'bid_pressure'
        elif 35 < current_ratio < 45:
            state = 'ask_pressure'
        else:
            state = 'balanced'
        
        # Get spread if we have order book data
        spread = 0
        spread_pct = 0
        if symbol in self.orderbooks:
            book = self.orderbooks[symbol]
            if book.get('bids') and book.get('asks'):
                # Handle both formats
                if isinstance(book['bids'][0], dict):
                    best_bid = float(book['bids'][0]['px'])
                    best_ask = float(book['asks'][0]['px'])
                else:
                    best_bid = float(book['bids'][0][0])
                    best_ask = float(book['asks'][0][0])
                spread = best_ask - best_bid
                mid_price = (best_bid + best_ask) / 2
                spread_pct = (spread / mid_price) * 100 if mid_price > 0 else 0
        
        return {
            'symbol': symbol,
            'bid_ask_ratio': self.bid_ask_ratio.get(symbol, 50),
            'bid_volume': self.bid_volume.get(symbol, 0),
            'ask_volume': self.ask_volume.get(symbol, 0),
            'order_book_pressure': self.order_book_pressure.get(symbol, 0),
            'large_bid_orders': self.large_bid_orders.get(symbol, 0),
            'large_ask_orders': self.large_ask_orders.get(symbol, 0),
            'support_levels': self.support_levels.get(symbol, []),
            'resistance_levels': self.resistance_levels.get(symbol, []),
            'spread': spread,
            'spread_pct': spread_pct,
            'trend': trend,
            'state': state,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Update order book data for all symbols with rate limiting"""
        # Create tasks for parallel fetching with rate limiting
        tasks = []
        for symbol in self.symbols:
            if symbol not in self.orderbooks or \
               time.time() - self.orderbooks.get(symbol, {}).get('time', 0) > 5:
                # Add to task list for rate-limited parallel execution
                tasks.append(self.fetch_orderbook(symbol))
        
        # Execute all fetches with rate limiting
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Calculate imbalance for successfully fetched symbols
            for i, symbol in enumerate(self.symbols):
                if i < len(results) and results[i] is not False and not isinstance(results[i], Exception):
                    self.calculate_imbalance(symbol)
    
    async def save_to_supabase(self):
        """Save order book metrics to Supabase"""
        for symbol in self.symbols:
            metrics = self.calculate_orderbook_metrics(symbol)
            
            # Update current table
            try:
                # Convert lists to JSON strings for storage
                metrics_copy = metrics.copy()
                metrics_copy['support_levels'] = json.dumps(metrics['support_levels'])
                metrics_copy['resistance_levels'] = json.dumps(metrics['resistance_levels'])
                
                self.supabase.table('hl_orderbook_current').upsert({
                    'symbol': symbol,
                    **metrics_copy
                }).execute()
            except Exception as e:
                print(f"[OrderBook] Error saving current data: {e}")
            
            # Save snapshots every 5 minutes
            current_time = time.time()
            if current_time - self.last_snapshot >= 300:
                try:
                    self.supabase.table('hl_orderbook_snapshots').insert({
                        'symbol': symbol,
                        'bid_ask_ratio': metrics['bid_ask_ratio'],
                        'order_book_pressure': metrics['order_book_pressure'],
                        'bid_volume': metrics['bid_volume'],
                        'ask_volume': metrics['ask_volume'],
                        'spread_pct': metrics['spread_pct'],
                        'state': metrics['state'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[OrderBook] Error saving snapshot: {e}")
        
        if time.time() - self.last_snapshot >= 300:
            self.last_snapshot = time.time()
            print(f"[OrderBook] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 5):
        """Run the order book imbalance tracker"""
        print(f"[OrderBook] Starting Order Book Imbalance tracker")
        print(f"[OrderBook] Tracking: {', '.join(self.symbols)}")
        print(f"[OrderBook] Update interval: {update_interval} seconds")
        print("=" * 60)
        
        # Subscribe to WebSocket feeds
        self.subscribe_to_orderbooks()
        
        # Give WebSocket time to connect (though WebSocket is disabled)
        await asyncio.sleep(2)
        
        print(f"[OrderBook] Rate limiting configured: max 10 requests/second")
        
        while True:
            try:
                # Update order books if needed
                await self.update()
                
                # Save to Supabase
                await self.save_to_supabase()
                
                # Display current metrics
                print(f"\n[OrderBook Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    metrics = self.calculate_orderbook_metrics(symbol)
                    print(f"  {symbol}: Ratio={metrics['bid_ask_ratio']:.1f}%, "
                          f"Pressure={metrics['order_book_pressure']:+.1f}, "
                          f"Spread={metrics['spread_pct']:.3f}%, "
                          f"{metrics['state']}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[OrderBook] Error in main loop: {e}")
                await asyncio.sleep(5)


async def main():
    """Run Order Book Imbalance indicator"""
    indicator = OrderBookImbalanceIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=5)  # Update every 5 seconds
    except KeyboardInterrupt:
        print("\n[OrderBook] Stopped by user")
    except Exception as e:
        print(f"[OrderBook] Fatal error: {e}")


if __name__ == "__main__":
    print("Order Book Imbalance Indicator for Hyperliquid")
    print("Updates every 5 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())