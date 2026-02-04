#!/usr/bin/env python3
"""
Hyperliquid Indicator Streaming to Supabase

Streams real-time trading indicators from Hyperliquid websocket to Supabase
for dashboard visualization and trim signal monitoring.

Features:
- Real-time price updates via allMids websocket
- Multi-timeframe indicator calculation (15M, 1H, 4H)
- EMA, RSI, MACD, Volume, Bollinger Bands
- Position trim signal monitoring
- Supabase realtime integration

Usage:
    python scripts/hyp_indicator_stream.py --tickers BTC,ETH,XRP
    python scripts/hyp_indicator_stream.py --test
    python scripts/hyp_indicator_stream.py --all

Requirements:
    pip install supabase websockets python-dotenv
"""

import os
import sys
import json
import time
import math
import logging
import argparse
import threading
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional, Any

from dotenv import dotenv_values
from hyperliquid.info import Info
from hyperliquid.utils import constants

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """Calculate technical indicators from candle data"""

    @staticmethod
    def ema(data: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if not data or len(data) < period:
            return []
        k = 2 / (period + 1)
        ema_vals = [data[0]]
        for i in range(1, len(data)):
            ema_vals.append(data[i] * k + ema_vals[-1] * (1 - k))
        return ema_vals

    @staticmethod
    def sma(data: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average"""
        if len(data) < period:
            return []
        return [
            sum(data[i - period:i]) / period
            for i in range(period, len(data) + 1)
        ]

    @staticmethod
    def rsi(closes: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(closes) < period + 1:
            return 50.0

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
        """Calculate MACD indicator"""
        if len(closes) < slow + signal:
            return {'line': 0, 'signal': 0, 'histogram': 0}

        ema_fast = IndicatorCalculator.ema(closes, fast)
        ema_slow = IndicatorCalculator.ema(closes, slow)

        macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
        signal_line = IndicatorCalculator.ema(macd_line, signal)

        return {
            'line': macd_line[-1],
            'signal': signal_line[-1],
            'histogram': macd_line[-1] - signal_line[-1]
        }

    @staticmethod
    def bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(closes) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0, 'position': 0.5}

        sma = sum(closes[-period:]) / period
        variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
        std = math.sqrt(variance)

        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        current = closes[-1]

        # Position within bands (0 = at lower, 1 = at upper)
        band_width = upper - lower
        position = (current - lower) / band_width if band_width > 0 else 0.5

        return {
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'position': min(max(position, 0), 1)
        }

    @staticmethod
    def volume_analysis(volumes: List[float], period: int = 20) -> Dict[str, Any]:
        """Analyze volume patterns"""
        if len(volumes) < period:
            avg = sum(volumes) / len(volumes) if volumes else 0
            return {'avg': avg, 'ratio': 1.0, 'trend': 'FLAT'}

        avg = sum(volumes[-period:-1]) / (period - 1) if period > 1 else volumes[-1]
        current = volumes[-1]
        ratio = current / avg if avg > 0 else 1.0

        # Volume trend
        recent = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else current
        prev = sum(volumes[-10:-5]) / 5 if len(volumes) >= 10 else recent

        if recent > prev * 1.1:
            trend = 'INCREASING'
        elif recent < prev * 0.9:
            trend = 'DECREASING'
        else:
            trend = 'FLAT'

        return {'avg': avg, 'ratio': ratio, 'trend': trend}


class HyperliquidIndicatorStream:
    """Stream Hyperliquid indicators to Supabase"""

    def __init__(self, tickers: List[str] = None):
        self.config = dotenv_values('.env')
        self.address = self.config.get('ACCOUNT_ADDRESS')
        self.info = Info(constants.MAINNET_API_URL, skip_ws=False)

        # Supabase setup
        self.supabase = None
        self.supabase_url = self.config.get('SUPABASE_URL')
        self.supabase_key = self.config.get('SUPABASE_KEY') or self.config.get('SUPABASE_ANON_KEY')

        if self.supabase_url and self.supabase_key:
            try:
                from supabase import create_client
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                logger.info("Supabase connected successfully")
            except ImportError:
                logger.warning("Supabase package not installed. Run: pip install supabase")
            except Exception as e:
                logger.error(f"Supabase connection failed: {e}")
        else:
            logger.warning("Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_KEY in .env")

        # Tickers to track
        self.tickers = tickers or ['BTC', 'ETH', 'XRP']
        self.timeframes = ['15m', '1h', '4h']

        # Candle cache
        self.candle_cache: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
        self.cache_lock = threading.Lock()

        # Price tracking
        self.current_prices: Dict[str, float] = {}
        self.price_lock = threading.Lock()

        # Streaming state
        self.running = False
        self.last_indicator_push: Dict[str, float] = {}

        # Calculator
        self.calc = IndicatorCalculator()

    def get_candles(self, ticker: str, timeframe: str, count: int = 100) -> List[Dict]:
        """Fetch candle data from Hyperliquid"""
        end_time = int(time.time() * 1000)

        tf_ms = {
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000
        }

        interval_ms = tf_ms.get(timeframe, 60 * 60 * 1000)
        start_time = end_time - (count * interval_ms)

        try:
            return self.info.candles_snapshot(ticker, timeframe, start_time, end_time)
        except Exception as e:
            logger.error(f"Error fetching candles for {ticker} {timeframe}: {e}")
            return []

    def calculate_indicators(self, ticker: str, timeframe: str) -> Optional[Dict]:
        """Calculate all indicators for a ticker/timeframe"""
        candles = self.get_candles(ticker, timeframe)

        if len(candles) < 50:
            logger.warning(f"Insufficient candles for {ticker} {timeframe}: {len(candles)}")
            return None

        closes = [float(c['c']) for c in candles]
        highs = [float(c['h']) for c in candles]
        lows = [float(c['l']) for c in candles]
        volumes = [float(c['v']) for c in candles]

        current_price = closes[-1]

        # EMAs
        ema9_vals = self.calc.ema(closes, 9)
        ema20_vals = self.calc.ema(closes, 20)
        ema50_vals = self.calc.ema(closes, 50)

        ema9 = ema9_vals[-1] if ema9_vals else None
        ema20 = ema20_vals[-1] if ema20_vals else None
        ema50 = ema50_vals[-1] if ema50_vals else None

        # RSI
        rsi = self.calc.rsi(closes)
        rsi_prev = self.calc.rsi(closes[:-5]) if len(closes) > 19 else rsi
        rsi_trend = 'RISING' if rsi > rsi_prev + 2 else 'FALLING' if rsi < rsi_prev - 2 else 'FLAT'

        # MACD
        macd = self.calc.macd(closes)
        prev_candles = closes[:-1] if len(closes) > 1 else closes
        prev_macd = self.calc.macd(prev_candles)

        macd_side = 'BULLISH' if macd['histogram'] > 0 else 'BEARISH'
        macd_momentum = 'STRENGTHENING' if abs(macd['histogram']) > abs(prev_macd['histogram']) else 'WEAKENING'

        # Volume
        vol_analysis = self.calc.volume_analysis(volumes)

        # Bollinger Bands
        bb = self.calc.bollinger_bands(closes)

        # Trend determination
        if current_price > ema9 > ema20:
            trend = 'BULLISH'
        elif current_price < ema9 < ema20:
            trend = 'BEARISH'
        else:
            trend = 'MIXED'

        return {
            'ticker': ticker,
            'timeframe': timeframe,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'price': current_price,
            'ema9': ema9,
            'ema20': ema20,
            'ema50': ema50,
            'rsi': round(rsi, 2),
            'rsi_trend': rsi_trend,
            'macd_line': macd['line'],
            'macd_signal': macd['signal'],
            'macd_histogram': macd['histogram'],
            'macd_side': macd_side,
            'macd_momentum': macd_momentum,
            'volume': volumes[-1],
            'volume_avg': vol_analysis['avg'],
            'volume_ratio': round(vol_analysis['ratio'], 2),
            'volume_trend': vol_analysis['trend'],
            'bb_upper': bb['upper'],
            'bb_middle': bb['middle'],
            'bb_lower': bb['lower'],
            'bb_position': round(bb['position'], 2),
            'trend': trend
        }

    def push_to_supabase(self, table: str, data: Dict) -> bool:
        """Push data to Supabase table"""
        if not self.supabase:
            return False

        try:
            self.supabase.table(table).insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase insert error ({table}): {e}")
            return False

    def calculate_trim_signal(self, ticker: str, direction: str, entry_price: float,
                              position_size: float, pnl_pct: float) -> Dict:
        """Calculate trim signal for a position"""
        # Get 1H analysis (primary timeframe for trim decisions)
        indicators_1h = self.calculate_indicators(ticker, '1h')
        indicators_4h = self.calculate_indicators(ticker, '4h')

        if not indicators_1h:
            return None

        score = 0
        is_short = direction == 'SHORT'

        price = indicators_1h['price']
        ema9 = indicators_1h['ema9']
        ema20 = indicators_1h['ema20']
        rsi = indicators_1h['rsi']
        histogram = indicators_1h['macd_histogram']
        vol_ratio = indicators_1h['volume_ratio']

        # Score calculation (same as trim_analyzer)
        # Price vs EMA9
        if is_short:
            score += 2 if price < ema9 else -2
        else:
            score += 2 if price > ema9 else -2

        # Price vs EMA20
        if is_short:
            score += 2 if price < ema20 else -3
        else:
            score += 2 if price > ema20 else -3

        # RSI
        if is_short:
            score += 2 if rsi < 45 else (-2 if rsi > 55 else 0)
        else:
            score += 2 if rsi > 55 else (-2 if rsi < 45 else 0)

        # MACD
        if is_short:
            score += 2 if histogram < 0 else -2
        else:
            score += 2 if histogram > 0 else -2

        # Volume on counter-trend
        if vol_ratio >= 2.0:
            score -= 2

        # 4H trend
        if indicators_4h:
            if is_short and indicators_4h['trend'] == 'BULLISH':
                score -= 2
            elif not is_short and indicators_4h['trend'] == 'BEARISH':
                score -= 2

        # Determine recommendation
        if score >= 6:
            recommendation = 'HOLD'
            trim_pct = 0
        elif score >= 1:
            recommendation = 'HOLD'
            trim_pct = 0
        elif score >= -4:
            recommendation = 'TRIM_25'
            trim_pct = 0.25
        elif score >= -7:
            recommendation = 'TRIM_50'
            trim_pct = 0.50
        else:
            recommendation = 'EXIT_75'
            trim_pct = 0.75

        return {
            'ticker': ticker,
            'direction': direction,
            'position_size': position_size,
            'entry_price': entry_price,
            'current_price': price,
            'pnl_percent': round(pnl_pct, 2),
            'trim_score': score,
            'recommendation': recommendation,
            'trim_percent': round(trim_pct * 100, 0),
            'reason': f"Score {score}: {'Trend intact' if score >= 1 else 'Reversal signals detected'}",
            'ema9_1h': ema9,
            'ema20_1h': ema20,
            'ema9_4h': indicators_4h['ema9'] if indicators_4h else None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def get_positions(self) -> List[Dict]:
        """Get current open positions"""
        if not self.address:
            return []

        try:
            state = self.info.user_state(self.address)
            positions = []

            for pos in state.get('assetPositions', []):
                p = pos['position']
                size = float(p['szi'])
                if size == 0:
                    continue

                positions.append({
                    'ticker': p['coin'],
                    'size': abs(size),
                    'direction': 'SHORT' if size < 0 else 'LONG',
                    'entry_price': float(p['entryPx']),
                    'unrealized_pnl': float(p['unrealizedPnl'])
                })

            return positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def on_price_update(self, msg: Dict):
        """Handle price updates from websocket"""
        if 'data' not in msg or 'mids' not in msg['data']:
            return

        mids = msg['data']['mids']
        with self.price_lock:
            for ticker, price in mids.items():
                if ticker in self.tickers or not self.tickers:
                    self.current_prices[ticker] = float(price)

    def stream_indicators(self, interval_seconds: int = 60):
        """Stream indicators at regular intervals"""
        logger.info(f"Starting indicator stream for: {', '.join(self.tickers)}")
        logger.info(f"Push interval: {interval_seconds} seconds")

        while self.running:
            try:
                for ticker in self.tickers:
                    for timeframe in self.timeframes:
                        cache_key = f"{ticker}_{timeframe}"

                        # Check if enough time has passed since last push
                        now = time.time()
                        last_push = self.last_indicator_push.get(cache_key, 0)

                        if now - last_push < interval_seconds:
                            continue

                        # Calculate indicators
                        indicators = self.calculate_indicators(ticker, timeframe)
                        if indicators:
                            # Push to Supabase
                            if self.push_to_supabase('trading_indicators', indicators):
                                self.last_indicator_push[cache_key] = now
                                logger.info(f"Pushed {ticker} {timeframe}: RSI={indicators['rsi']:.1f}, Trend={indicators['trend']}")
                            else:
                                logger.debug(f"Calculated {ticker} {timeframe} (no Supabase)")

                # Check positions for trim signals
                positions = self.get_positions()
                for pos in positions:
                    ticker = pos['ticker']
                    if ticker not in self.tickers:
                        continue

                    # Calculate P&L %
                    with self.price_lock:
                        current_price = self.current_prices.get(ticker, pos['entry_price'])

                    if pos['direction'] == 'SHORT':
                        pnl_pct = ((pos['entry_price'] - current_price) / pos['entry_price']) * 100
                    else:
                        pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100

                    # Generate trim signal
                    trim_signal = self.calculate_trim_signal(
                        ticker, pos['direction'], pos['entry_price'],
                        pos['size'], pnl_pct
                    )

                    if trim_signal:
                        self.push_to_supabase('trim_signals', trim_signal)
                        logger.info(f"Trim signal {ticker}: Score={trim_signal['trim_score']}, Rec={trim_signal['recommendation']}")

                time.sleep(5)  # Check every 5 seconds for interval

            except Exception as e:
                logger.error(f"Stream error: {e}")
                time.sleep(10)

    def start(self, interval: int = 60):
        """Start the streaming service"""
        self.running = True

        # Subscribe to allMids for real-time prices
        logger.info("Subscribing to price updates...")
        self.info.subscribe({"type": "allMids"}, self.on_price_update)

        # Start indicator streaming in a thread
        stream_thread = threading.Thread(target=self.stream_indicators, args=(interval,))
        stream_thread.daemon = True
        stream_thread.start()

        logger.info("=" * 60)
        logger.info("HYPERLIQUID INDICATOR STREAM")
        logger.info("=" * 60)
        logger.info(f"Tickers: {', '.join(self.tickers)}")
        logger.info(f"Timeframes: {', '.join(self.timeframes)}")
        logger.info(f"Interval: {interval}s")
        logger.info(f"Supabase: {'Connected' if self.supabase else 'Not configured'}")
        logger.info("=" * 60)
        logger.info("Streaming... Press Ctrl+C to stop")
        logger.info("")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            self.running = False

    def test_connection(self):
        """Test Supabase connection and indicator calculation"""
        print("=" * 60)
        print("INDICATOR STREAM TEST")
        print("=" * 60)

        # Test Supabase
        print("\n[1] Supabase Connection:")
        if self.supabase:
            print("    Status: Connected")
            print(f"    URL: {self.supabase_url[:40]}...")
        else:
            print("    Status: NOT CONFIGURED")
            print("    Add to .env:")
            print("      SUPABASE_URL=https://your-project.supabase.co")
            print("      SUPABASE_KEY=your-anon-key")

        # Test indicator calculation
        print("\n[2] Indicator Calculation:")
        test_ticker = self.tickers[0] if self.tickers else 'BTC'
        indicators = self.calculate_indicators(test_ticker, '1h')

        if indicators:
            print(f"    Ticker: {test_ticker}")
            print(f"    Price: ${indicators['price']:.2f}")
            print(f"    EMA9: ${indicators['ema9']:.2f}")
            print(f"    EMA20: ${indicators['ema20']:.2f}")
            print(f"    RSI: {indicators['rsi']:.1f} ({indicators['rsi_trend']})")
            print(f"    MACD: {indicators['macd_side']} {indicators['macd_momentum']}")
            print(f"    Volume: {indicators['volume_ratio']:.2f}x ({indicators['volume_trend']})")
            print(f"    Trend: {indicators['trend']}")
        else:
            print("    ERROR: Could not calculate indicators")

        # Test positions
        print("\n[3] Position Detection:")
        if self.address:
            positions = self.get_positions()
            if positions:
                for pos in positions:
                    print(f"    {pos['ticker']}: {pos['direction']} {pos['size']:.2f}")
            else:
                print("    No open positions")
        else:
            print("    Wallet not configured (ACCOUNT_ADDRESS)")

        print("\n" + "=" * 60)
        print("Test complete. Run without --test to start streaming.")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Stream Hyperliquid indicators to Supabase')
    parser.add_argument('--tickers', type=str, help='Comma-separated list of tickers (default: BTC,ETH,XRP)')
    parser.add_argument('--interval', type=int, default=60, help='Push interval in seconds (default: 60)')
    parser.add_argument('--test', action='store_true', help='Test connection and exit')
    parser.add_argument('--all', action='store_true', help='Track all available tickers')

    args = parser.parse_args()

    # Parse tickers
    tickers = None
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(',')]
    elif not args.all:
        tickers = ['BTC', 'ETH', 'XRP']

    # Create streamer
    streamer = HyperliquidIndicatorStream(tickers)

    if args.test:
        streamer.test_connection()
    else:
        streamer.start(interval=args.interval)


if __name__ == '__main__':
    main()
