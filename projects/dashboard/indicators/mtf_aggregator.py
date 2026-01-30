"""
Multi-Timeframe Aggregator for Hyperliquid
Aggregates signals from multiple timeframes and indicators
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque
import os
from dotenv import load_dotenv
import sys
import numpy as np
import json

# Try to import hyperliquid - works both locally and in Docker
try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
except ImportError:
    sys.path.append('..')
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
from supabase import create_client, Client

load_dotenv()


class MTFAggregatorIndicator:
    """
    Aggregates signals across multiple timeframes:
    - Trend alignment across timeframes
    - Signal confluence scoring
    - Divergence detection
    - Momentum synchronization
    - Overall market bias calculation
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Timeframe data
        self.timeframes = ['5m', '15m', '1h', '4h', '1d']
        self.price_data = defaultdict(lambda: defaultdict(dict))  # symbol -> timeframe -> data
        
        # Signal storage
        self.trend_signals = defaultdict(lambda: defaultdict(str))  # symbol -> timeframe -> signal
        self.momentum_signals = defaultdict(lambda: defaultdict(float))
        self.volume_signals = defaultdict(lambda: defaultdict(float))
        
        # Aggregate scores
        self.confluence_scores = defaultdict(float)
        self.trend_alignment = defaultdict(str)
        self.market_bias = defaultdict(str)
        
        # Moving averages for each timeframe
        self.ma_periods = {'5m': 20, '15m': 20, '1h': 20, '4h': 20, '1d': 20}
        
        # Current prices
        self.current_prices = defaultdict(float)
        
        # Timing
        self.last_update = defaultdict(lambda: defaultdict(float))
        self.last_snapshot = time.time()
    
    def get_interval_ms(self, interval: str) -> int:
        """Get interval duration in milliseconds"""
        intervals = {
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        return intervals.get(interval, 5 * 60 * 1000)
    
    async def fetch_timeframe_data(self, symbol: str, timeframe: str):
        """Fetch data for a specific timeframe"""
        try:
            # Map timeframe to Hyperliquid format
            interval_map = {
                '5m': '5m',
                '15m': '15m',
                '1h': '60m',
                '4h': '240m',
                '1d': '1d'
            }
            
            hl_interval = interval_map.get(timeframe, '5m')
            
            # Get candles
            end_time = int(time.time() * 1000)
            start_time = end_time - (50 * self.get_interval_ms(timeframe))  # 50 candles
            
            candles = self.info.candles_snapshot(
                symbol,
                hl_interval,
                start_time,
                end_time
            )
            
            if candles:
                # Process candle data
                closes = [float(c.get('c', 0)) for c in candles]
                highs = [float(c.get('h', 0)) for c in candles]
                lows = [float(c.get('l', 0)) for c in candles]
                volumes = [float(c.get('v', 0)) for c in candles]
                
                if closes:
                    # Calculate indicators for this timeframe
                    ma_period = self.ma_periods[timeframe]
                    
                    # Simple moving average
                    sma = np.mean(closes[-ma_period:]) if len(closes) >= ma_period else np.mean(closes)
                    
                    # EMA
                    ema = self.calculate_ema(closes, ma_period)
                    
                    # RSI
                    rsi = self.calculate_rsi(closes, 14)
                    
                    # MACD
                    macd, signal, histogram = self.calculate_macd(closes)
                    
                    # Store data
                    self.price_data[symbol][timeframe] = {
                        'close': closes[-1],
                        'sma': sma,
                        'ema': ema,
                        'rsi': rsi,
                        'macd': macd,
                        'macd_signal': signal,
                        'macd_histogram': histogram,
                        'volume': volumes[-1] if volumes else 0,
                        'high': highs[-1] if highs else 0,
                        'low': lows[-1] if lows else 0
                    }
                    
                    # Update current price
                    self.current_prices[symbol] = closes[-1]
                    
                    # Determine trend signal for this timeframe
                    if closes[-1] > sma and closes[-1] > ema:
                        trend = 'bullish'
                    elif closes[-1] < sma and closes[-1] < ema:
                        trend = 'bearish'
                    else:
                        trend = 'neutral'
                    
                    self.trend_signals[symbol][timeframe] = trend
                    
                    # Momentum signal (RSI-based)
                    if rsi > 70:
                        momentum = 1.0  # Overbought
                    elif rsi < 30:
                        momentum = -1.0  # Oversold
                    else:
                        momentum = (rsi - 50) / 50  # Normalized
                    
                    self.momentum_signals[symbol][timeframe] = momentum
                    
                    # Volume signal
                    avg_volume = np.mean(volumes) if volumes else 0
                    current_volume = volumes[-1] if volumes else 0
                    volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 1
                    self.volume_signals[symbol][timeframe] = volume_ratio
                    
                    return True
            
            return False
            
        except Exception as e:
            # Silently handle 422 errors for unsupported intervals
            if '422' not in str(e):
                print(f"[MTF] Error fetching {timeframe} data for {symbol}: {e}")
            return False
    
    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if not prices:
            return 0
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices)
        gains = deltas.copy()
        losses = deltas.copy()
        
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """Calculate MACD"""
        if len(prices) < slow:
            return 0, 0, 0
        
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # For simplicity, using current MACD as signal
        signal_line = macd_line * 0.9  # Simplified
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_confluence(self, symbol: str) -> Dict[str, Any]:
        """Calculate signal confluence across timeframes"""
        
        # Count bullish/bearish signals
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        
        # Weight by timeframe (higher timeframes have more weight)
        timeframe_weights = {'5m': 1, '15m': 2, '1h': 3, '4h': 4, '1d': 5}
        weighted_score = 0
        total_weight = 0
        
        for tf in self.timeframes:
            if tf in self.trend_signals[symbol]:
                signal = self.trend_signals[symbol][tf]
                weight = timeframe_weights[tf]
                
                if signal == 'bullish':
                    bullish_count += 1
                    weighted_score += weight
                elif signal == 'bearish':
                    bearish_count += 1
                    weighted_score -= weight
                else:
                    neutral_count += 1
                
                total_weight += weight
        
        # Calculate confluence score (-100 to +100)
        if total_weight > 0:
            confluence_score = (weighted_score / total_weight) * 20  # Scale to -100 to +100
        else:
            confluence_score = 0
        
        # Determine trend alignment
        if bullish_count >= 4:
            alignment = 'strong_bullish'
        elif bullish_count >= 3:
            alignment = 'bullish'
        elif bearish_count >= 4:
            alignment = 'strong_bearish'
        elif bearish_count >= 3:
            alignment = 'bearish'
        else:
            alignment = 'mixed'
        
        # Calculate momentum confluence
        momentum_sum = sum(self.momentum_signals[symbol].values())
        momentum_avg = momentum_sum / len(self.momentum_signals[symbol]) if self.momentum_signals[symbol] else 0
        
        # Determine market bias
        if confluence_score > 50 and momentum_avg > 0.3:
            bias = 'strong_buy'
        elif confluence_score > 25 and momentum_avg > 0:
            bias = 'buy'
        elif confluence_score < -50 and momentum_avg < -0.3:
            bias = 'strong_sell'
        elif confluence_score < -25 and momentum_avg < 0:
            bias = 'sell'
        else:
            bias = 'neutral'
        
        return {
            'confluence_score': confluence_score,
            'trend_alignment': alignment,
            'market_bias': bias,
            'bullish_timeframes': bullish_count,
            'bearish_timeframes': bearish_count,
            'momentum_score': momentum_avg * 100
        }
    
    def calculate_mtf_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate comprehensive MTF metrics"""
        confluence = self.calculate_confluence(symbol)
        
        # Get individual timeframe signals
        tf_signals = {}
        for tf in self.timeframes:
            if tf in self.trend_signals[symbol]:
                tf_data = self.price_data[symbol].get(tf, {})
                tf_signals[f'signal_{tf}'] = self.trend_signals[symbol][tf]
                tf_signals[f'rsi_{tf}'] = tf_data.get('rsi', 50)
                tf_signals[f'momentum_{tf}'] = self.momentum_signals[symbol].get(tf, 0)
        
        return {
            'symbol': symbol,
            'current_price': self.current_prices.get(symbol, 0),
            'confluence_score': confluence['confluence_score'],
            'trend_alignment': confluence['trend_alignment'],
            'market_bias': confluence['market_bias'],
            'bullish_timeframes': confluence['bullish_timeframes'],
            'bearish_timeframes': confluence['bearish_timeframes'],
            'momentum_score': confluence['momentum_score'],
            **tf_signals,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Update MTF data for all symbols"""
        current_time = time.time()
        
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                # Update based on timeframe interval
                interval_seconds = self.get_interval_ms(timeframe) / 1000
                
                # Update less frequently for higher timeframes
                update_frequency = min(interval_seconds / 4, 300)  # Max 5 minutes
                
                if current_time - self.last_update[symbol][timeframe] >= update_frequency:
                    await self.fetch_timeframe_data(symbol, timeframe)
                    self.last_update[symbol][timeframe] = current_time
    
    async def save_to_supabase(self):
        """Save MTF data to Supabase"""
        for symbol in self.symbols:
            metrics = self.calculate_mtf_metrics(symbol)
            
            # Update current table
            try:
                self.supabase.table('hl_mtf_current').upsert({
                    'symbol': symbol,
                    **metrics
                }).execute()
            except Exception as e:
                print(f"[MTF] Error saving current data: {e}")
            
            # Save snapshots every 30 minutes
            current_time = time.time()
            if current_time - self.last_snapshot >= 1800:
                try:
                    self.supabase.table('hl_mtf_snapshots').insert({
                        'symbol': symbol,
                        'price': metrics['current_price'],
                        'confluence_score': metrics['confluence_score'],
                        'trend_alignment': metrics['trend_alignment'],
                        'market_bias': metrics['market_bias'],
                        'momentum_score': metrics['momentum_score'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[MTF] Error saving snapshot: {e}")
        
        if time.time() - self.last_snapshot >= 1800:
            self.last_snapshot = time.time()
            print(f"[MTF] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 30):
        """Run the MTF aggregator"""
        print(f"[MTF] Starting Multi-Timeframe Aggregator")
        print(f"[MTF] Tracking: {', '.join(self.symbols)}")
        print(f"[MTF] Timeframes: {', '.join(self.timeframes)}")
        print(f"[MTF] Update interval: {update_interval} seconds")
        print("=" * 60)
        
        # Initial fetch
        await self.update()
        
        while True:
            try:
                # Update data
                await self.update()
                
                # Save to Supabase
                await self.save_to_supabase()
                
                # Display current metrics
                print(f"\n[MTF Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    metrics = self.calculate_mtf_metrics(symbol)
                    print(f"  {symbol}: Score={metrics['confluence_score']:.1f}, "
                          f"Alignment={metrics['trend_alignment']}, "
                          f"Bias={metrics['market_bias']}, "
                          f"Momentum={metrics['momentum_score']:.1f}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[MTF] Error in main loop: {e}")
                await asyncio.sleep(10)


async def main():
    """Run MTF Aggregator"""
    indicator = MTFAggregatorIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=30)  # Update every 30 seconds
    except KeyboardInterrupt:
        print("\n[MTF] Stopped by user")
    except Exception as e:
        print(f"[MTF] Fatal error: {e}")


if __name__ == "__main__":
    print("Multi-Timeframe Aggregator for Hyperliquid")
    print("Updates every 30 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())