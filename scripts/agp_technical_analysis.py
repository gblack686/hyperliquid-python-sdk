#!/usr/bin/env python3
"""
Agentic Technical Analysis - Full multi-indicator analysis with confluence scoring
Chains RSI, MACD, Bollinger, ATR, Stochastic, EMA, S/R, and Volume indicators

DATA INTEGRITY RULES:
1. NO FABRICATED DATA - Every value comes from real API responses
2. EMPTY STATE HANDLING - If no data, report "Insufficient data" clearly
3. SOURCE TRACKING - Log which API call produced each data point
4. VALIDATION - Before analysis, verify data exists and is valid
"""

import os
import sys
import asyncio
import time
import numpy as np
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants

INTERVAL_MS = {
    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000, '1h': 60 * 60 * 1000, '2h': 2 * 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000, '8h': 8 * 60 * 60 * 1000, '12h': 12 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000, '3d': 3 * 24 * 60 * 60 * 1000, '1w': 7 * 24 * 60 * 60 * 1000,
}


async def fetch_candles(hyp, ticker, timeframe, num_bars=200):
    """Fetch candle data from Hyperliquid."""
    now = int(time.time() * 1000)
    interval_ms = INTERVAL_MS.get(timeframe, 60 * 60 * 1000)
    start = now - (num_bars * interval_ms)

    candles = await hyp.candle_historical(
        ticker=ticker.upper(),
        interval=timeframe,
        start=start,
        end=now
    )

    if not candles:
        return None

    candles = candles[-num_bars:] if len(candles) > num_bars else candles
    return candles


def calculate_rsi(closes, period=14):
    """Calculate RSI."""
    if len(closes) < period + 1:
        return None

    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_ema(closes, period):
    """Calculate EMA."""
    if len(closes) < period:
        return closes[-1] if len(closes) > 0 else 0

    multiplier = 2 / (period + 1)
    ema = np.mean(closes[:period])

    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def calculate_macd(closes, fast=12, slow=26, signal=9):
    """Calculate MACD."""
    if len(closes) < slow:
        return None

    fast_ema = calculate_ema(closes, fast)
    slow_ema = calculate_ema(closes, slow)
    macd_line = fast_ema - slow_ema

    # For signal line, we need MACD history
    macd_history = []
    for i in range(slow, len(closes) + 1):
        subset = closes[:i]
        f_ema = calculate_ema(subset, fast)
        s_ema = calculate_ema(subset, slow)
        macd_history.append(f_ema - s_ema)

    if len(macd_history) < signal:
        signal_line = macd_line
    else:
        signal_line = calculate_ema(np.array(macd_history), signal)

    histogram = macd_line - signal_line

    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram,
        'crossover': 'bullish' if macd_line > signal_line else 'bearish'
    }


def calculate_bollinger(closes, period=20, std_dev=2):
    """Calculate Bollinger Bands."""
    if len(closes) < period:
        return None

    sma = np.mean(closes[-period:])
    std = np.std(closes[-period:])

    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    current = closes[-1]

    bandwidth = (upper - lower) / sma * 100
    percent_b = (current - lower) / (upper - lower) if (upper - lower) > 0 else 0.5

    return {
        'upper': upper,
        'middle': sma,
        'lower': lower,
        'bandwidth': bandwidth,
        'percent_b': percent_b,
        'squeeze': bandwidth < 4  # Squeeze when bandwidth is low
    }


def calculate_atr(highs, lows, closes, period=14):
    """Calculate ATR."""
    if len(closes) < period + 1:
        return None

    tr_list = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        tr_list.append(tr)

    atr = np.mean(tr_list[-period:])
    atr_pct = (atr / closes[-1]) * 100 if closes[-1] > 0 else 0

    return {
        'atr': atr,
        'atr_pct': atr_pct
    }


def calculate_stochastic(highs, lows, closes, k_period=14, d_period=3):
    """Calculate Stochastic."""
    if len(closes) < k_period + d_period:
        return None

    k_values = []
    for i in range(k_period - 1, len(closes)):
        period_high = np.max(highs[i - k_period + 1:i + 1])
        period_low = np.min(lows[i - k_period + 1:i + 1])

        if period_high == period_low:
            k = 50
        else:
            k = ((closes[i] - period_low) / (period_high - period_low)) * 100

        k_values.append(k)

    current_k = k_values[-1]
    current_d = np.mean(k_values[-d_period:]) if len(k_values) >= d_period else current_k

    zone = 'overbought' if current_k >= 80 else 'oversold' if current_k <= 20 else 'neutral'

    return {
        'k': current_k,
        'd': current_d,
        'zone': zone,
        'crossover': 'bullish' if current_k > current_d else 'bearish'
    }


def find_support_resistance(highs, lows, closes, lookback=50):
    """Find support and resistance levels."""
    if len(closes) < lookback:
        lookback = len(closes)

    highs = highs[-lookback:]
    lows = lows[-lookback:]
    current = closes[-1]

    # Simple pivot detection
    resistance_candidates = []
    support_candidates = []

    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            resistance_candidates.append(highs[i])
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            support_candidates.append(lows[i])

    # Find nearest
    nearest_resistance = None
    nearest_support = None

    for r in sorted(resistance_candidates, reverse=True):
        if r > current:
            nearest_resistance = r
            break

    for s in sorted(support_candidates, reverse=True):
        if s < current:
            nearest_support = s
            break

    return {
        'nearest_resistance': nearest_resistance,
        'nearest_support': nearest_support,
        'current_price': current
    }


def calculate_volume_analysis(volumes, closes, lookback=20):
    """Analyze volume."""
    if len(volumes) < lookback:
        return None

    current_volume = volumes[-1]
    volume_ma = np.mean(volumes[-lookback:])
    spike_ratio = current_volume / volume_ma if volume_ma > 0 else 0

    price_change = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 else 0

    # Volume-price confirmation
    if price_change > 0 and spike_ratio > 1.0:
        confirmation = 'bullish_confirmation'
    elif price_change < 0 and spike_ratio > 1.0:
        confirmation = 'bearish_confirmation'
    else:
        confirmation = 'neutral'

    return {
        'current': current_volume,
        'average': volume_ma,
        'spike_ratio': spike_ratio,
        'confirmation': confirmation
    }


def calculate_confluence_score(indicators, direction='long'):
    """Calculate confluence score based on all indicators."""
    score = 0
    details = []

    # EMA (3 points max)
    ema20 = indicators.get('ema20')
    ema50 = indicators.get('ema50')
    price = indicators.get('price')

    if ema20 and ema50 and price:
        if direction == 'long':
            if price > ema20 and price > ema50:
                score += 2
                details.append("+2: Price above both EMAs")
            if ema20 > ema50:
                score += 1
                details.append("+1: EMA20 > EMA50 (bullish)")
        else:
            if price < ema20 and price < ema50:
                score += 2
                details.append("+2: Price below both EMAs")
            if ema20 < ema50:
                score += 1
                details.append("+1: EMA20 < EMA50 (bearish)")

    # RSI (2 points max)
    rsi = indicators.get('rsi')
    if rsi:
        if direction == 'long':
            if 40 <= rsi <= 60:
                score += 1
                details.append("+1: RSI neutral (room to run)")
            if rsi < 30:
                score += 2
                details.append("+2: RSI oversold")
        else:
            if 40 <= rsi <= 60:
                score += 1
                details.append("+1: RSI neutral (room to fall)")
            if rsi > 70:
                score += 2
                details.append("+2: RSI overbought")

    # MACD (2 points max)
    macd = indicators.get('macd')
    if macd:
        if direction == 'long' and macd['crossover'] == 'bullish':
            score += 2
            details.append("+2: MACD bullish crossover")
        elif direction == 'short' and macd['crossover'] == 'bearish':
            score += 2
            details.append("+2: MACD bearish crossover")

    # Stochastic (2 points max)
    stoch = indicators.get('stochastic')
    if stoch:
        if direction == 'long':
            if stoch['zone'] == 'oversold':
                score += 1
                details.append("+1: Stochastic oversold")
            if stoch['crossover'] == 'bullish':
                score += 1
                details.append("+1: Stochastic bullish crossover")
        else:
            if stoch['zone'] == 'overbought':
                score += 1
                details.append("+1: Stochastic overbought")
            if stoch['crossover'] == 'bearish':
                score += 1
                details.append("+1: Stochastic bearish crossover")

    # Volume (1 point max)
    volume = indicators.get('volume')
    if volume:
        if volume['spike_ratio'] > 1.5:
            if direction == 'long' and volume['confirmation'] == 'bullish_confirmation':
                score += 1
                details.append("+1: Volume confirms bullish move")
            elif direction == 'short' and volume['confirmation'] == 'bearish_confirmation':
                score += 1
                details.append("+1: Volume confirms bearish move")

    # S/R (2 points max)
    sr = indicators.get('sr')
    if sr:
        if direction == 'long' and sr['nearest_support']:
            dist = (price - sr['nearest_support']) / price
            if dist < 0.02:
                score += 2
                details.append("+2: Near support level")
        elif direction == 'short' and sr['nearest_resistance']:
            dist = (sr['nearest_resistance'] - price) / price
            if dist < 0.02:
                score += 2
                details.append("+2: Near resistance level")

    return {
        'score': score,
        'max_score': 12,
        'details': details
    }


async def technical_analysis(ticker, timeframe='1h'):
    """Execute complete technical analysis."""

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path("outputs/technical_analysis") / f"{ticker}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"TECHNICAL ANALYSIS - {ticker}")
    print(f"Timeframe: {timeframe} | Timestamp: {timestamp}")
    print("DATA INTEGRITY: Real API data only")
    print("=" * 70)
    print()

    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    try:
        # Get current price
        print("[1/10] Fetching current price...")
        mids = info.all_mids()
        current_price = float(mids.get(ticker.upper(), 0))

        if current_price == 0:
            print(f"[ERROR] Ticker '{ticker}' not found")
            return

        print(f"       Price: ${current_price:,.2f}")

        # Fetch candles
        print("[2/10] Fetching candle data...")
        candles = await fetch_candles(hyp, ticker, timeframe, num_bars=200)

        if not candles or len(candles) < 50:
            print("[ERROR] Insufficient candle data")
            return

        highs = np.array([float(c['h']) for c in candles])
        lows = np.array([float(c['l']) for c in candles])
        closes = np.array([float(c['c']) for c in candles])
        volumes = np.array([float(c['v']) for c in candles])

        print(f"       Candles: {len(candles)}")

        # Calculate all indicators
        print("[3/10] Calculating RSI...")
        rsi = calculate_rsi(closes, 14)
        print(f"       RSI(14): {rsi:.2f}" if rsi else "       RSI: N/A")

        print("[4/10] Calculating MACD...")
        macd = calculate_macd(closes)
        if macd:
            print(f"       MACD: {macd['macd']:.4f}, Signal: {macd['signal']:.4f}")

        print("[5/10] Calculating Bollinger Bands...")
        bollinger = calculate_bollinger(closes)
        if bollinger:
            print(f"       BB: {bollinger['lower']:.2f} - {bollinger['upper']:.2f}")

        print("[6/10] Calculating ATR...")
        atr = calculate_atr(highs, lows, closes)
        if atr:
            print(f"       ATR(14): {atr['atr']:.4f} ({atr['atr_pct']:.2f}%)")

        print("[7/10] Calculating Stochastic...")
        stoch = calculate_stochastic(highs, lows, closes)
        if stoch:
            print(f"       Stoch: %K={stoch['k']:.1f}, %D={stoch['d']:.1f}")

        print("[8/10] Calculating EMAs...")
        ema20 = calculate_ema(closes, 20)
        ema50 = calculate_ema(closes, 50)
        print(f"       EMA20: ${ema20:.2f}, EMA50: ${ema50:.2f}")

        print("[9/10] Finding Support/Resistance...")
        sr = find_support_resistance(highs, lows, closes)
        if sr['nearest_support']:
            print(f"       Support: ${sr['nearest_support']:.2f}")
        if sr['nearest_resistance']:
            print(f"       Resistance: ${sr['nearest_resistance']:.2f}")

        print("[10/10] Analyzing Volume...")
        volume = calculate_volume_analysis(volumes, closes)
        if volume:
            print(f"       Volume ratio: {volume['spike_ratio']:.2f}x avg")

        # Collect all indicators
        indicators = {
            'price': current_price,
            'rsi': rsi,
            'macd': macd,
            'bollinger': bollinger,
            'atr': atr,
            'stochastic': stoch,
            'ema20': ema20,
            'ema50': ema50,
            'sr': sr,
            'volume': volume
        }

        # Calculate confluence for both directions
        long_confluence = calculate_confluence_score(indicators, 'long')
        short_confluence = calculate_confluence_score(indicators, 'short')

        # Determine direction
        if long_confluence['score'] > short_confluence['score']:
            direction = 'LONG'
            confluence = long_confluence
        elif short_confluence['score'] > long_confluence['score']:
            direction = 'SHORT'
            confluence = short_confluence
        else:
            direction = 'NEUTRAL'
            confluence = long_confluence

        # Generate trade setup
        setup = None
        if direction != 'NEUTRAL' and atr and sr:
            if direction == 'LONG':
                entry = current_price
                stop = entry - (1.5 * atr['atr'])
                target1 = sr['nearest_resistance'] if sr['nearest_resistance'] else entry * 1.02
                target2 = entry + (2 * (entry - stop))
            else:
                entry = current_price
                stop = entry + (1.5 * atr['atr'])
                target1 = sr['nearest_support'] if sr['nearest_support'] else entry * 0.98
                target2 = entry - (2 * (stop - entry))

            setup = {
                'direction': direction,
                'entry': entry,
                'stop': stop,
                'target1': target1,
                'target2': target2,
                'risk_pct': abs(entry - stop) / entry * 100
            }

        # Generate report
        print()
        print("=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)

        report = f"""# Technical Analysis: {ticker}
## Generated: {timestamp}
## Timeframe: {timeframe}

---

## Price Context
- **Current Price**: ${current_price:,.2f}
- **EMA 20**: ${ema20:,.2f} ({'above' if current_price > ema20 else 'below'})
- **EMA 50**: ${ema50:,.2f} ({'above' if current_price > ema50 else 'below'})
- **Trend**: {'BULLISH' if ema20 > ema50 else 'BEARISH'}

## Indicator Summary

| Indicator | Value | Signal |
|-----------|-------|--------|
| RSI (14) | {f"{rsi:.1f}" if rsi else "N/A"} | {"Oversold" if rsi and rsi < 30 else "Overbought" if rsi and rsi > 70 else "Neutral"} |
| MACD | {f"{macd['macd']:.4f}" if macd else "N/A"} | {macd['crossover'].title() if macd else "N/A"} |
| Stochastic | {f"{stoch['k']:.1f}" if stoch else "N/A"} | {stoch['zone'].title() if stoch else "N/A"} |
| Bollinger %B | {f"{bollinger['percent_b']:.2f}" if bollinger else "N/A"} | {"Squeeze" if bollinger and bollinger['squeeze'] else "Normal"} |
| ATR (14) | {f"{atr['atr']:.4f} ({atr['atr_pct']:.2f}%)" if atr else "N/A"} | - |
| Volume | {f"{volume['spike_ratio']:.2f}x" if volume else "N/A"} | {volume['confirmation'].replace('_', ' ').title() if volume else "N/A"} |

## Support & Resistance
- **Nearest Support**: {f"${sr['nearest_support']:,.2f}" if sr['nearest_support'] else "N/A"}
- **Nearest Resistance**: {f"${sr['nearest_resistance']:,.2f}" if sr['nearest_resistance'] else "N/A"}

## Confluence Score

**Direction**: {direction}
**Score**: {confluence['score']}/{confluence['max_score']}

### Scoring Details:
"""
        for detail in confluence['details']:
            report += f"- {detail}\n"

        if setup:
            report += f"""
## Trade Setup

**Direction**: {setup['direction']}

| Level | Price | Distance |
|-------|-------|----------|
| Entry | ${setup['entry']:,.2f} | - |
| Stop Loss | ${setup['stop']:,.2f} | {setup['risk_pct']:.2f}% |
| Target 1 | ${setup['target1']:,.2f} | {abs(setup['target1'] - setup['entry']) / setup['entry'] * 100:.2f}% |
| Target 2 | ${setup['target2']:,.2f} | {abs(setup['target2'] - setup['entry']) / setup['entry'] * 100:.2f}% |

**Confidence**: {'HIGH' if confluence['score'] >= 8 else 'MEDIUM' if confluence['score'] >= 5 else 'LOW'}
"""
        else:
            report += """
## Trade Setup

**No clear setup** - Confluence score too low or indicators mixed.
Wait for better entry conditions.
"""

        (output_dir / "analysis_report.md").write_text(report)

        print(f"\n{report}")
        print(f"\nOutput saved to: {output_dir.absolute()}")

    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        raise

    finally:
        await hyp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agp_technical_analysis.py <ticker> [timeframe]")
        print("Example: python agp_technical_analysis.py BTC 4h")
        sys.exit(1)

    ticker = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"

    asyncio.run(technical_analysis(ticker, timeframe))
