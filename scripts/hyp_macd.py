#!/usr/bin/env python
"""
MACD (Moving Average Convergence Divergence) Indicator.

Shows MACD line, signal line, histogram, and crossover signals.

USAGE:
  python hyp_macd.py <ticker> [timeframe] [fast] [slow] [signal]

EXAMPLES:
  python hyp_macd.py BTC                    # MACD for BTC (12/26/9, 1h)
  python hyp_macd.py ETH 4h                 # MACD for ETH, 4h timeframe
  python hyp_macd.py SOL 1d 12 26 9         # Custom MACD settings
"""

import os
import sys
import asyncio
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from hyperliquid.info import Info
from hyperliquid.utils import constants


def calculate_ema(data: np.ndarray, period: int) -> np.ndarray:
    """Calculate EMA series."""
    if len(data) < period:
        return np.array([data[-1]] if len(data) > 0 else [0])

    multiplier = 2 / (period + 1)
    ema = np.zeros(len(data))
    ema[period - 1] = np.mean(data[:period])

    for i in range(period, len(data)):
        ema[i] = (data[i] - ema[i-1]) * multiplier + ema[i-1]

    return ema


def calculate_macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Calculate MACD, Signal line, and Histogram."""
    if len(closes) < slow + signal:
        return None

    fast_ema = calculate_ema(closes, fast)
    slow_ema = calculate_ema(closes, slow)

    macd_line = fast_ema - slow_ema

    # Only use valid MACD values (after slow period)
    valid_macd = macd_line[slow-1:]
    signal_line = calculate_ema(valid_macd, signal)

    # Align arrays
    current_macd = macd_line[-1]
    current_signal = signal_line[-1]
    histogram = current_macd - current_signal

    # Previous values for crossover detection
    prev_macd = macd_line[-2]
    prev_signal = signal_line[-2] if len(signal_line) > 1 else current_signal
    prev_histogram = prev_macd - prev_signal

    # Detect crossover
    crossover = None
    if prev_histogram <= 0 and histogram > 0:
        crossover = "bullish"
    elif prev_histogram >= 0 and histogram < 0:
        crossover = "bearish"

    return {
        "macd": current_macd,
        "signal": current_signal,
        "histogram": histogram,
        "prev_histogram": prev_histogram,
        "crossover": crossover,
        "macd_history": macd_line[-20:],
        "signal_history": signal_line[-20:] if len(signal_line) >= 20 else signal_line
    }


def get_macd_signal(macd_data: dict) -> dict:
    """Get trading signal from MACD data."""
    if not macd_data:
        return {"signal": "INSUFFICIENT DATA", "strength": 0}

    crossover = macd_data.get("crossover")
    histogram = macd_data.get("histogram", 0)

    if crossover == "bullish":
        return {"signal": "BUY - Bullish Crossover", "strength": 85}
    elif crossover == "bearish":
        return {"signal": "SELL - Bearish Crossover", "strength": 85}
    elif histogram > 0:
        strength = min(60, 30 + abs(histogram) * 1000)
        return {"signal": "BULLISH", "strength": strength}
    elif histogram < 0:
        strength = min(60, 30 + abs(histogram) * 1000)
        return {"signal": "BEARISH", "strength": strength}

    return {"signal": "NEUTRAL", "strength": 0}


TIMEFRAME_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "8h": "8h", "12h": "12h",
    "1d": "1d", "3d": "3d", "1w": "1w"
}


async def fetch_candles(info: Info, ticker: str, timeframe: str, num_bars: int = 200):
    """Fetch candle data from Hyperliquid."""
    try:
        candles = info.candles_snapshot(
            name=ticker.upper(),
            interval=timeframe,
            startTime=None,
            endTime=None
        )

        if not candles:
            return None

        candles = candles[-num_bars:] if len(candles) > num_bars else candles
        closes = np.array([float(c['c']) for c in candles])
        return closes
    except Exception as e:
        print(f"[ERROR] Failed to fetch candles: {e}")
        return None


async def main(ticker: str, timeframe: str = "1h", fast: int = 12, slow: int = 26, signal: int = 9):
    ticker = ticker.upper()

    if timeframe not in TIMEFRAME_MAP:
        print(f"[ERROR] Invalid timeframe '{timeframe}'. Valid: {list(TIMEFRAME_MAP.keys())}")
        return

    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    # Get current price
    mids = info.all_mids()
    current_price = float(mids.get(ticker, 0))

    if current_price == 0:
        print(f"[ERROR] Ticker '{ticker}' not found")
        return

    print("=" * 65)
    print(f"MACD INDICATOR - {ticker}")
    print("=" * 65)
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  Timeframe:     {timeframe}")
    print(f"  Settings:      Fast={fast}, Slow={slow}, Signal={signal}")
    print()

    # Calculate MACD
    closes = await fetch_candles(info, ticker, timeframe, num_bars=slow * 3)

    if closes is None or len(closes) < slow + signal:
        print("[ERROR] Insufficient data for MACD calculation")
        return

    macd_data = calculate_macd(closes, fast, slow, signal)

    if not macd_data:
        print("[ERROR] Failed to calculate MACD")
        return

    signal_info = get_macd_signal(macd_data)

    print("MACD ANALYSIS:")
    print("-" * 65)
    print(f"  MACD Line:     {macd_data['macd']:>12.4f}")
    print(f"  Signal Line:   {macd_data['signal']:>12.4f}")
    print(f"  Histogram:     {macd_data['histogram']:>12.4f}")
    print()

    if macd_data['crossover']:
        cross_type = "BULLISH CROSSOVER" if macd_data['crossover'] == 'bullish' else "BEARISH CROSSOVER"
        print(f"  ** {cross_type} DETECTED **")
        print()

    print(f"  Signal:        {signal_info['signal']}")
    print(f"  Strength:      {signal_info['strength']}%")
    print()

    # Histogram visualization
    print("HISTOGRAM (Last 20 bars):")
    print("-" * 65)

    macd_hist = macd_data['macd_history']
    sig_hist = macd_data['signal_history']

    # Calculate histogram history
    min_len = min(len(macd_hist), len(sig_hist))
    hist_values = macd_hist[-min_len:] - sig_hist[-min_len:]

    max_hist = max(abs(hist_values.max()), abs(hist_values.min()), 0.0001)

    for i, h in enumerate(hist_values[-15:]):
        bar_len = int(abs(h) / max_hist * 20)
        if h >= 0:
            bar = " " * 20 + "|" + "+" * bar_len
        else:
            bar = " " * (20 - bar_len) + "-" * bar_len + "|"
        print(f"  {i+1:>2}: {bar} {h:>8.4f}")

    print()

    # Multi-timeframe MACD
    print("MULTI-TIMEFRAME MACD:")
    print("-" * 65)
    print(f"  {'TF':>4}  {'MACD':>10}  {'Signal':>10}  {'Histogram':>10}  {'Status'}")
    print("-" * 65)

    timeframes = ["15m", "1h", "4h", "1d"]
    for tf in timeframes:
        tf_closes = await fetch_candles(info, ticker, tf, num_bars=slow * 3)
        if tf_closes is not None and len(tf_closes) >= slow + signal:
            tf_macd = calculate_macd(tf_closes, fast, slow, signal)
            if tf_macd:
                status = "BULLISH" if tf_macd['histogram'] > 0 else "BEARISH"
                if tf_macd['crossover']:
                    status = f"** {tf_macd['crossover'].upper()} CROSS **"
                print(f"  {tf:>4}  {tf_macd['macd']:>10.4f}  {tf_macd['signal']:>10.4f}  {tf_macd['histogram']:>10.4f}  {status}")

    print("=" * 65)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"
    fast = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    slow = int(sys.argv[4]) if len(sys.argv) > 4 else 26
    signal = int(sys.argv[5]) if len(sys.argv) > 5 else 9

    asyncio.run(main(ticker, timeframe, fast, slow, signal))
