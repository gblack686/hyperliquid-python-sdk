"""
Real-time CVD (Cumulative Volume Delta) Calculator using Quantpylib
Streams trades via WebSocket and calculates CVD in real-time
"""

import os
import asyncio
import time
from datetime import datetime, timedelta
from collections import deque, defaultdict
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add path for local imports
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'quantpylib'))

from quantpylib.wrappers.hyperliquid import Hyperliquid


class CVDCalculator:
    """
    Real-time CVD calculator using Quantpylib's Hyperliquid WebSocket
    """
    
    def __init__(self, symbols: List[str] = None):
        """
        Initialize CVD calculator
        
        Args:
            symbols: List of symbols to track (e.g., ['BTC', 'ETH', 'SOL'])
        """
        self.symbols = symbols or ['BTC', 'ETH', 'SOL']
        
        # CVD tracking per symbol
        self.cvd = defaultdict(float)  # Current CVD value
        self.cvd_history = defaultdict(lambda: deque(maxlen=10000))  # Historical CVD
        self.trades_buffer = defaultdict(lambda: deque(maxlen=5000))  # Recent trades
        
        # Timeframe CVD tracking (1m, 5m, 15m, 1h, 4h, 1d)
        self.timeframe_cvd = defaultdict(lambda: defaultdict(list))
        self.timeframe_timestamps = defaultdict(lambda: defaultdict(list))
        
        # Statistics
        self.stats = defaultdict(lambda: {
            'total_trades': 0,
            'buy_volume': 0.0,
            'sell_volume': 0.0,
            'buy_trades': 0,
            'sell_trades': 0,
            'last_update': None
        })
        
        # Hyperliquid client
        self.client = None
        self.running = False
        
    async def init_client(self):
        """Initialize Hyperliquid WebSocket client"""
        # For public data (trades), we don't need authentication
        # But quantpylib requires a key, so we pass None
        self.client = Hyperliquid(
            key=None,  # Not needed for public WebSocket data
            secret=None,  # Not needed for public WebSocket data
            mode="mainnet"
        )
        await self.client.init_client()
        print(f"[CVD] Initialized Hyperliquid client")
        
    async def handle_trade(self, symbol: str, trade_data):
        """
        Process incoming trade and update CVD
        
        Args:
            symbol: Trading symbol
            trade_data: Trade data from WebSocket
        """
        try:
            # Parse trade data based on Quantpylib format
            if isinstance(trade_data, tuple):
                # Standardized format: (timestamp, price, size, direction)
                ts, price, size, direction = trade_data
                side = 'B' if direction > 0 else 'S'
            else:
                # Raw format from WebSocket
                ts = trade_data.get('time', time.time() * 1000)
                price = float(trade_data.get('px', 0))
                size = float(trade_data.get('sz', 0))
                side = trade_data.get('side', '')
            
            # Update CVD
            if side == 'B':
                self.cvd[symbol] += size
                self.stats[symbol]['buy_volume'] += size * price
                self.stats[symbol]['buy_trades'] += 1
            else:
                self.cvd[symbol] -= size
                self.stats[symbol]['sell_volume'] += size * price
                self.stats[symbol]['sell_trades'] += 1
            
            # Store trade
            trade_record = {
                'ts': ts,
                'price': price,
                'size': size,
                'side': side,
                'cvd': self.cvd[symbol]
            }
            self.trades_buffer[symbol].append(trade_record)
            
            # Update statistics
            self.stats[symbol]['total_trades'] += 1
            self.stats[symbol]['last_update'] = datetime.now()
            
            # Update CVD history
            self.cvd_history[symbol].append({
                'ts': ts,
                'cvd': self.cvd[symbol],
                'price': price
            })
            
            # Update timeframe CVD
            self.update_timeframe_cvd(symbol, ts, self.cvd[symbol])
            
            # Print update every 10 trades
            if self.stats[symbol]['total_trades'] % 10 == 0:
                self.print_cvd_status(symbol)
                
        except Exception as e:
            print(f"[CVD] Error processing trade for {symbol}: {e}")
            
    def update_timeframe_cvd(self, symbol: str, timestamp: float, cvd_value: float):
        """Update CVD for different timeframes"""
        current_time = datetime.fromtimestamp(timestamp / 1000)
        
        # Define timeframe buckets
        timeframes = {
            '1m': current_time.replace(second=0, microsecond=0),
            '5m': current_time.replace(minute=current_time.minute // 5 * 5, second=0, microsecond=0),
            '15m': current_time.replace(minute=current_time.minute // 15 * 15, second=0, microsecond=0),
            '1h': current_time.replace(minute=0, second=0, microsecond=0),
            '4h': current_time.replace(hour=current_time.hour // 4 * 4, minute=0, second=0, microsecond=0),
            '1d': current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        }
        
        for tf_name, tf_time in timeframes.items():
            tf_key = tf_time.isoformat()
            
            # If new timeframe bucket, store the CVD value
            if not self.timeframe_timestamps[symbol][tf_name] or \
               self.timeframe_timestamps[symbol][tf_name][-1] != tf_key:
                self.timeframe_timestamps[symbol][tf_name].append(tf_key)
                self.timeframe_cvd[symbol][tf_name].append(cvd_value)
            else:
                # Update the current timeframe bucket
                self.timeframe_cvd[symbol][tf_name][-1] = cvd_value
                
    def print_cvd_status(self, symbol: str):
        """Print current CVD status for a symbol"""
        stats = self.stats[symbol]
        cvd_value = self.cvd[symbol]
        
        # Calculate buy/sell ratio
        total_volume = stats['buy_volume'] + stats['sell_volume']
        buy_ratio = (stats['buy_volume'] / total_volume * 100) if total_volume > 0 else 50
        
        # Get recent price from trades buffer
        recent_price = self.trades_buffer[symbol][-1]['price'] if self.trades_buffer[symbol] else 0
        
        print(f"\n[{symbol}] CVD Status:")
        print(f"  CVD: {cvd_value:,.2f} | Price: ${recent_price:,.2f}")
        print(f"  Trades: {stats['total_trades']:,} | Buy: {stats['buy_trades']:,} | Sell: {stats['sell_trades']:,}")
        print(f"  Buy Ratio: {buy_ratio:.1f}% | Total Volume: ${total_volume:,.0f}")
        
    def get_cvd_metrics(self, symbol: str) -> Dict:
        """
        Get comprehensive CVD metrics for a symbol
        
        Returns:
            Dictionary with CVD metrics
        """
        if symbol not in self.cvd:
            return {}
            
        # Calculate CVD change over different periods
        history = list(self.cvd_history[symbol])
        if len(history) < 2:
            return {'cvd': self.cvd[symbol], 'status': 'insufficient_data'}
            
        current_cvd = self.cvd[symbol]
        
        # Get CVD from different time points
        cvd_1m_ago = history[-60]['cvd'] if len(history) >= 60 else history[0]['cvd']
        cvd_5m_ago = history[-300]['cvd'] if len(history) >= 300 else history[0]['cvd']
        cvd_15m_ago = history[-900]['cvd'] if len(history) >= 900 else history[0]['cvd']
        
        # Calculate changes
        cvd_change_1m = current_cvd - cvd_1m_ago
        cvd_change_5m = current_cvd - cvd_5m_ago
        cvd_change_15m = current_cvd - cvd_15m_ago
        
        # Calculate CVD velocity (rate of change)
        cvd_velocity = cvd_change_1m  # CVD change per minute
        
        # Determine trend
        if cvd_change_5m > 0 and cvd_change_1m > 0:
            trend = 'bullish'
        elif cvd_change_5m < 0 and cvd_change_1m < 0:
            trend = 'bearish'
        else:
            trend = 'neutral'
            
        # Calculate z-score (normalized CVD)
        cvd_values = [h['cvd'] for h in history[-100:]]
        cvd_mean = np.mean(cvd_values)
        cvd_std = np.std(cvd_values)
        cvd_zscore = (current_cvd - cvd_mean) / cvd_std if cvd_std > 0 else 0
        
        return {
            'cvd': current_cvd,
            'cvd_change_1m': cvd_change_1m,
            'cvd_change_5m': cvd_change_5m,
            'cvd_change_15m': cvd_change_15m,
            'cvd_velocity': cvd_velocity,
            'cvd_zscore': cvd_zscore,
            'trend': trend,
            'buy_volume': self.stats[symbol]['buy_volume'],
            'sell_volume': self.stats[symbol]['sell_volume'],
            'total_trades': self.stats[symbol]['total_trades'],
            'last_update': self.stats[symbol]['last_update']
        }
        
    async def subscribe_to_trades(self):
        """Subscribe to trade streams for all symbols"""
        print(f"[CVD] Subscribing to trades for: {self.symbols}")
        
        for symbol in self.symbols:
            # Create handler for this symbol
            async def trade_handler(trade_data, sym=symbol):
                await self.handle_trade(sym, trade_data)
            
            # Subscribe using Quantpylib
            await self.client.trades_subscribe(
                ticker=symbol,
                handler=trade_handler,
                standardize_schema=True  # Get standardized format
            )
            print(f"[CVD] Subscribed to {symbol} trades")
            
    async def run(self, duration_seconds: Optional[int] = None):
        """
        Run the CVD calculator
        
        Args:
            duration_seconds: How long to run (None = forever)
        """
        try:
            # Initialize client
            await self.init_client()
            
            # Subscribe to trades
            await self.subscribe_to_trades()
            
            self.running = True
            start_time = time.time()
            
            print(f"\n[CVD] Calculator running... Press Ctrl+C to stop")
            print("=" * 60)
            
            # Main loop
            while self.running:
                await asyncio.sleep(10)  # Update interval
                
                # Print summary
                print(f"\n[CVD Summary] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    if self.cvd[symbol] != 0:
                        metrics = self.get_cvd_metrics(symbol)
                        print(f"  {symbol}: CVD={metrics['cvd']:,.2f}, Trend={metrics['trend']}, Z-score={metrics['cvd_zscore']:.2f}")
                
                # Check duration
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    print(f"\n[CVD] Duration limit reached ({duration_seconds}s)")
                    break
                    
        except KeyboardInterrupt:
            print("\n[CVD] Stopped by user")
        except Exception as e:
            print(f"\n[CVD] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Clean up WebSocket connections"""
        self.running = False
        print("\n[CVD] Cleaning up...")
        
        # Unsubscribe from all trades
        for symbol in self.symbols:
            try:
                await self.client.trades_unsubscribe(ticker=symbol)
                print(f"[CVD] Unsubscribed from {symbol}")
            except:
                pass
                
        # Clean up client
        if self.client:
            await self.client.cleanup()
            
        print("[CVD] Cleanup complete")
        
    def export_cvd_data(self, symbol: str) -> pd.DataFrame:
        """
        Export CVD data as DataFrame
        
        Args:
            symbol: Symbol to export
            
        Returns:
            DataFrame with CVD history
        """
        if symbol not in self.trades_buffer:
            return pd.DataFrame()
            
        trades = list(self.trades_buffer[symbol])
        if not trades:
            return pd.DataFrame()
            
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['ts'], unit='ms')
        df = df.set_index('timestamp')
        
        # Add additional metrics
        df['cvd_change'] = df['cvd'].diff()
        df['cvd_ma_5'] = df['cvd'].rolling(window=5).mean()
        df['cvd_ma_20'] = df['cvd'].rolling(window=20).mean()
        
        return df


async def main():
    """Example usage of CVD Calculator"""
    
    # Initialize calculator for BTC, ETH, SOL
    calculator = CVDCalculator(symbols=['BTC', 'ETH', 'SOL'])
    
    # Run for 60 seconds as a test
    await calculator.run(duration_seconds=60)
    
    # Export data
    for symbol in calculator.symbols:
        metrics = calculator.get_cvd_metrics(symbol)
        if metrics:
            print(f"\n[Final Metrics] {symbol}:")
            for key, value in metrics.items():
                if key != 'last_update':
                    print(f"  {key}: {value}")
                    
    # Export to DataFrame (optional)
    btc_df = calculator.export_cvd_data('BTC')
    if not btc_df.empty:
        print(f"\n[Export] BTC CVD data shape: {btc_df.shape}")
        print(btc_df.tail())


if __name__ == "__main__":
    asyncio.run(main())