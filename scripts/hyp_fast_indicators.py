#!/usr/bin/env python3
"""
Fast Technical Indicators - Parallel API fetching.

Fetches all timeframes in parallel for speed.
Target: <5 seconds vs 2+ minutes sequential.

Usage:
    python scripts/hyp_fast_indicators.py BTC
    python scripts/hyp_fast_indicators.py SOL --json
"""

import os
import sys
import json
import asyncio
import math
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    import aiohttp
except ImportError:
    print("Install aiohttp: pip install aiohttp")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"
TIMEFRAMES = ['15m', '1h', '4h', '1d']
TF_MS = {'5m': 5*60*1000, '15m': 15*60*1000, '1h': 60*60*1000, '4h': 4*60*60*1000, '1d': 24*60*60*1000}


class FastIndicators:
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.data: Dict[str, Any] = {}
        self.candles: Dict[str, List] = {}

    async def fetch_all(self) -> Dict[str, Any]:
        """Fetch all candle data in parallel."""
        start = time.time()
        now_ms = int(time.time() * 1000)

        async with aiohttp.ClientSession() as session:
            tasks = {}

            # Fetch candles for all timeframes in parallel
            for tf in TIMEFRAMES:
                interval_ms = TF_MS.get(tf, 60*60*1000)
                lookback = 100  # candles needed for indicators
                start_time = now_ms - (lookback * interval_ms)

                tasks[tf] = self._post(session, HYPERLIQUID_API, {
                    'type': 'candleSnapshot',
                    'req': {
                        'coin': self.ticker,
                        'interval': tf,
                        'startTime': start_time,
                        'endTime': now_ms,
                    }
                })

            # Also get current price
            tasks['meta'] = self._post(session, HYPERLIQUID_API, {'type': 'metaAndAssetCtxs'})

            results = await asyncio.gather(*[tasks[k] for k in tasks], return_exceptions=True)

            for i, key in enumerate(tasks.keys()):
                self.data[key] = results[i]

        # Parse candles
        for tf in TIMEFRAMES:
            raw = self.data.get(tf, [])
            if isinstance(raw, list):
                self.candles[tf] = raw

        self.data['fetch_time'] = time.time() - start
        return self.data

    async def _post(self, session: aiohttp.ClientSession, url: str, data: dict):
        try:
            async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                return await resp.json()
        except Exception as e:
            return {'error': str(e)}

    def get_current_price(self) -> float:
        """Get current price from meta."""
        meta = self.data.get('meta', [])
        if isinstance(meta, list) and len(meta) > 1:
            universe = meta[0].get('universe', [])
            ctxs = meta[1]
            for i, asset in enumerate(universe):
                if asset.get('name') == self.ticker and i < len(ctxs):
                    return float(ctxs[i].get('markPx', 0))
        return 0

    def calc_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI."""
        if len(closes) < period + 1:
            return 50.0

        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(change, 0))
            losses.append(abs(min(change, 0)))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def calc_macd(self, closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Calculate MACD."""
        if len(closes) < slow + signal:
            return {'macd': 0, 'signal': 0, 'histogram': 0}

        def ema(data, period):
            if len(data) < period:
                return data[-1] if data else 0
            multiplier = 2 / (period + 1)
            ema_val = sum(data[:period]) / period
            for price in data[period:]:
                ema_val = (price * multiplier) + (ema_val * (1 - multiplier))
            return ema_val

        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)
        macd_line = ema_fast - ema_slow

        # Calculate signal line from MACD history
        macd_history = []
        for i in range(slow, len(closes)):
            ef = ema(closes[:i+1], fast)
            es = ema(closes[:i+1], slow)
            macd_history.append(ef - es)

        signal_line = ema(macd_history, signal) if len(macd_history) >= signal else macd_line
        histogram = macd_line - signal_line

        return {'macd': macd_line, 'signal': signal_line, 'histogram': histogram}

    def calc_stochastic(self, highs: List[float], lows: List[float], closes: List[float],
                        k_period: int = 14, d_period: int = 3) -> Dict:
        """Calculate Stochastic."""
        if len(closes) < k_period:
            return {'k': 50, 'd': 50}

        lowest_low = min(lows[-k_period:])
        highest_high = max(highs[-k_period:])

        if highest_high == lowest_low:
            k = 50
        else:
            k = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100

        # Smooth K to get D
        k_values = []
        for i in range(k_period, len(closes) + 1):
            ll = min(lows[i-k_period:i])
            hh = max(highs[i-k_period:i])
            if hh != ll:
                k_values.append(((closes[i-1] - ll) / (hh - ll)) * 100)
            else:
                k_values.append(50)

        d = sum(k_values[-d_period:]) / d_period if len(k_values) >= d_period else k

        return {'k': k, 'd': d}

    def calc_bollinger(self, closes: List[float], period: int = 20, std_dev: float = 2.0) -> Dict:
        """Calculate Bollinger Bands."""
        if len(closes) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0, 'position': 0.5, 'bandwidth': 0}

        sma = sum(closes[-period:]) / period
        variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
        std = math.sqrt(variance)

        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        current = closes[-1]

        band_width = upper - lower
        position = (current - lower) / band_width if band_width > 0 else 0.5
        bandwidth_pct = (band_width / sma * 100) if sma > 0 else 0

        return {
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'position': min(max(position, 0), 1),
            'bandwidth': bandwidth_pct
        }

    def calc_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Calculate ATR."""
        if len(closes) < period + 1:
            return 0

        tr = []
        for i in range(1, len(closes)):
            tr.append(max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            ))

        return sum(tr[-period:]) / period

    def calc_ema(self, closes: List[float], period: int) -> float:
        """Calculate EMA."""
        if len(closes) < period:
            return closes[-1] if closes else 0

        multiplier = 2 / (period + 1)
        ema_val = sum(closes[:period]) / period
        for price in closes[period:]:
            ema_val = (price * multiplier) + (ema_val * (1 - multiplier))
        return ema_val

    def generate_report(self, as_json: bool = False) -> str:
        """Generate indicator report."""
        current_price = self.get_current_price()

        # Use 1h timeframe as primary
        candles_1h = self.candles.get('1h', [])
        if not candles_1h:
            return f"No candle data for {self.ticker}"

        closes = [float(c['c']) for c in candles_1h]
        highs = [float(c['h']) for c in candles_1h]
        lows = [float(c['l']) for c in candles_1h]

        # Calculate all indicators
        rsi = self.calc_rsi(closes)
        macd = self.calc_macd(closes)
        stoch = self.calc_stochastic(highs, lows, closes)
        bb = self.calc_bollinger(closes)
        atr = self.calc_atr(highs, lows, closes)
        ema20 = self.calc_ema(closes, 20)
        ema50 = self.calc_ema(closes, 50)

        # Multi-timeframe RSI
        mtf_rsi = {}
        for tf in TIMEFRAMES:
            tf_candles = self.candles.get(tf, [])
            if tf_candles:
                tf_closes = [float(c['c']) for c in tf_candles]
                mtf_rsi[tf] = self.calc_rsi(tf_closes)

        if as_json:
            return json.dumps({
                'ticker': self.ticker,
                'price': current_price,
                'fetch_time': self.data.get('fetch_time', 0),
                'rsi': rsi,
                'macd': macd,
                'stochastic': stoch,
                'bollinger': bb,
                'atr': atr,
                'ema20': ema20,
                'ema50': ema50,
                'mtf_rsi': mtf_rsi,
            }, indent=2)

        # Text report
        lines = []
        lines.append("=" * 75)
        lines.append(f"FAST INDICATORS - {self.ticker}")
        lines.append(f"Fetched in {self.data.get('fetch_time', 0):.2f}s")
        lines.append("=" * 75)
        lines.append(f"  Current Price: ${current_price:,.2f}")
        lines.append(f"  Timeframe:     1h (primary)")

        # Indicator summary
        lines.append(f"\n{'INDICATOR SUMMARY':^75}")
        lines.append("-" * 75)
        lines.append(f"  {'Indicator':<20} {'Value':<20} {'Zone':<15} {'Signal':<10}")
        lines.append("-" * 75)

        # RSI
        rsi_zone = 'OVERSOLD' if rsi < 30 else 'OVERBOUGHT' if rsi > 70 else 'NEUTRAL'
        rsi_signal = 'BUY' if rsi < 30 else 'SELL' if rsi > 70 else '-'
        lines.append(f"  {'RSI (14)':<20} {rsi:<20.2f} {rsi_zone:<15} {rsi_signal:<10}")

        # MACD
        macd_zone = 'BULLISH' if macd['histogram'] > 0 else 'BEARISH'
        macd_signal = 'BUY' if macd['histogram'] > 0 and macd['macd'] > macd['signal'] else 'SELL' if macd['histogram'] < 0 else '-'
        lines.append(f"  {'MACD Histogram':<20} {macd['histogram']:<20.4f} {macd_zone:<15} {macd_signal:<10}")

        # Stochastic
        stoch_zone = 'OVERSOLD' if stoch['k'] < 20 else 'OVERBOUGHT' if stoch['k'] > 80 else 'NEUTRAL'
        stoch_signal = 'BUY' if stoch['k'] < 20 and stoch['k'] > stoch['d'] else 'SELL' if stoch['k'] > 80 else '-'
        stoch_val = f"{stoch['k']:.1f}/{stoch['d']:.1f}"
        lines.append(f"  {'Stochastic K/D':<20} {stoch_val:<20} {stoch_zone:<15} {stoch_signal:<10}")

        # Bollinger
        bb_zone = 'LOWER' if bb['position'] < 0.2 else 'UPPER' if bb['position'] > 0.8 else 'MIDDLE'
        lines.append(f"  {'Bollinger Pos':<20} {bb['position']*100:<20.1f}% {bb_zone:<15} {'-':<10}")

        # ATR
        atr_pct = (atr / current_price * 100) if current_price > 0 else 0
        atr_zone = 'HIGH' if atr_pct > 3 else 'LOW' if atr_pct < 1 else 'NORMAL'
        lines.append(f"  {'ATR (14)':<20} ${atr:<18.2f} {atr_zone:<15} {'-':<10}")

        # Trend
        trend = 'BULLISH' if ema20 > ema50 else 'BEARISH'
        trend_strength = 'STRONG' if abs(ema20 - ema50) / ema50 > 0.02 else 'WEAK'
        lines.append(f"  {'Trend EMA 20/50':<20} {trend_strength + ' ' + trend:<20} {trend:<15} {'-':<10}")

        # Price levels
        lines.append(f"\n{'KEY PRICE LEVELS':^75}")
        lines.append("-" * 75)
        lines.append(f"  Bollinger Upper:   ${bb['upper']:>12,.2f}  ({(bb['upper']/current_price-1)*100:+.2f}%)")
        lines.append(f"  Bollinger Middle:  ${bb['middle']:>12,.2f}  ({(bb['middle']/current_price-1)*100:+.2f}%)")
        lines.append(f"  Bollinger Lower:   ${bb['lower']:>12,.2f}  ({(bb['lower']/current_price-1)*100:+.2f}%)")
        lines.append(f"  EMA 20:            ${ema20:>12,.2f}  ({(ema20/current_price-1)*100:+.2f}%)")
        lines.append(f"  EMA 50:            ${ema50:>12,.2f}  ({(ema50/current_price-1)*100:+.2f}%)")

        # ATR stops
        lines.append(f"\n{'ATR-BASED STOPS':^75}")
        lines.append("-" * 75)
        lines.append(f"  1x ATR Stop:       Long: ${current_price - atr:>10,.2f}  |  Short: ${current_price + atr:>10,.2f}")
        lines.append(f"  2x ATR Stop:       Long: ${current_price - 2*atr:>10,.2f}  |  Short: ${current_price + 2*atr:>10,.2f}")

        # MTF RSI
        lines.append(f"\n{'MULTI-TIMEFRAME RSI':^75}")
        lines.append("-" * 75)
        for tf in TIMEFRAMES:
            if tf in mtf_rsi:
                r = mtf_rsi[tf]
                zone = 'OVERSOLD' if r < 30 else 'OVERBOUGHT' if r > 70 else 'NEUTRAL'
                bar = int(r / 100 * 40)
                lines.append(f"  {tf:>4}:  [{'#' * bar}{'-' * (40-bar)}] {r:>5.1f} {zone}")

        # Overall bias
        lines.append(f"\n{'OVERALL BIAS':^75}")
        lines.append("-" * 75)
        buy_signals = sum([
            rsi < 30,
            macd['histogram'] > 0,
            stoch['k'] < 20 and stoch['k'] > stoch['d'],
            bb['position'] < 0.2,
        ])
        sell_signals = sum([
            rsi > 70,
            macd['histogram'] < 0,
            stoch['k'] > 80,
            bb['position'] > 0.8,
        ])
        bias = 'BULLISH' if buy_signals > sell_signals else 'BEARISH' if sell_signals > buy_signals else 'NEUTRAL'
        lines.append(f"  Buy Signals:   {buy_signals}/4")
        lines.append(f"  Sell Signals:  {sell_signals}/4")
        lines.append(f"  Overall Bias:  {bias}")

        lines.append("=" * 75)
        return "\n".join(lines)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fast Technical Indicators')
    parser.add_argument('ticker', help='Ticker symbol (e.g., BTC, SOL)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    indicators = FastIndicators(args.ticker)
    await indicators.fetch_all()
    print(indicators.generate_report(as_json=args.json))


if __name__ == '__main__':
    asyncio.run(main())
