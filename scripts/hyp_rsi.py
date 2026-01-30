#!/usr/bin/env python
"""
RSI (Relative Strength Index) Indicator.

Shows RSI across multiple timeframes with overbought/oversold signals.

USAGE:
  python hyp_rsi.py <ticker> [period] [timeframe]

EXAMPLES:
  python hyp_rsi.py BTC              # RSI for BTC (default 14 period, 1h)
  python hyp_rsi.py ETH 14 4h        # RSI for ETH, 14 period, 4h timeframe
  python hyp_rsi.py SOL 21 1d        # RSI for SOL, 21 period, daily
"""

import os
import sys
import asyncio
import time
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants

# Interval to milliseconds mapping
INTERVAL_MS = {
    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000, '1h': 60 * 60 * 1000, '2h': 2 * 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000, '8h': 8 * 60 * 60 * 1000, '12h': 12 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000, '3d': 3 * 24 * 60 * 60 * 1000, '1w': 7 * 24 * 60 * 60 * 1000,
}


def calculate_rsi(closes: np.ndarray, period: int = 14) -> float:
    """Calculate RSI from closing prices."""
    if len(closes) < period + 1:
        return 50.0

    deltas = np.diff(closes)

    gains = deltas.copy()
    gains[gains < 0] = 0
    losses = -deltas.copy()
    losses[losses < 0] = 0

    # Wilder's smoothing
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def get_rsi_signal(rsi: float, overbought: float = 70, oversold: float = 30) -> dict:
    """Get signal from RSI value."""
    if rsi >= 80:
        return {"signal": "STRONG SELL", "strength": 95, "zone": "extreme_overbought"}
    elif rsi >= overbought:
        return {"signal": "SELL", "strength": 70, "zone": "overbought"}
    elif rsi <= 20:
        return {"signal": "STRONG BUY", "strength": 95, "zone": "extreme_oversold"}
    elif rsi <= oversold:
        return {"signal": "BUY", "strength": 70, "zone": "oversold"}
    elif rsi > 50:
        return {"signal": "BULLISH", "strength": 40, "zone": "bullish"}
    elif rsi < 50:
        return {"signal": "BEARISH", "strength": 40, "zone": "bearish"}
    else:
        return {"signal": "NEUTRAL", "strength": 0, "zone": "neutral"}


TIMEFRAME_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "8h": "8h", "12h": "12h",
    "1d": "1d", "3d": "3d", "1w": "1w"
}


async def fetch_candles(hyp: Hyperliquid, ticker: str, timeframe: str, num_bars: int = 200):
    """Fetch candle data from Hyperliquid using quantpylib."""
    try:
        now = int(time.time() * 1000)
        interval_ms = INTERVAL_MS.get(timeframe, 60 * 60 * 1000)
        start = now - (num_bars * interval_ms)

        candles = await hyp.candle_historical(
            ticker=ticker.upper(),
            interval=timeframe,
            start=start,
            end=now
        )

        if not candles or len(candles) == 0:
            return None

        closes = np.array([float(c['c']) for c in candles])
        return closes
    except Exception as e:
        print(f"[ERROR] Failed to fetch candles: {e}")
        return None


async def main(ticker: str, period: int = 14, timeframe: str = "1h"):
    ticker = ticker.upper()

    if timeframe not in TIMEFRAME_MAP:
        print(f"[ERROR] Invalid timeframe '{timeframe}'. Valid: {list(TIMEFRAME_MAP.keys())}")
        return

    # Initialize quantpylib
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    # Get current price
    mids = info.all_mids()
    current_price = float(mids.get(ticker, 0))

    if current_price == 0:
        print(f"[ERROR] Ticker '{ticker}' not found")
        await hyp.cleanup()
        return

    print("=" * 60)
    print(f"RSI INDICATOR - {ticker}")
    print("=" * 60)
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  Period:        {period}")
    print(f"  Timeframe:     {timeframe}")
    print()

    # Calculate RSI
    closes = await fetch_candles(hyp, ticker, timeframe, num_bars=period * 3)

    if closes is None or len(closes) < period + 1:
        print("[ERROR] Insufficient data for RSI calculation")
        await hyp.cleanup()
        return

    rsi = calculate_rsi(closes, period)
    signal = get_rsi_signal(rsi)

    print("RSI ANALYSIS:")
    print("-" * 60)
    print(f"  RSI Value:     {rsi:.2f}")
    print(f"  Zone:          {signal['zone'].upper()}")
    print(f"  Signal:        {signal['signal']}")
    print(f"  Strength:      {signal['strength']}%")
    print()

    # Visual RSI gauge
    print("RSI GAUGE:")
    print("-" * 60)
    gauge_width = 50
    position = int((rsi / 100) * gauge_width)

    gauge = ""
    for i in range(gauge_width + 1):
        if i == int(20 / 100 * gauge_width):
            gauge += "|"  # Oversold line
        elif i == int(30 / 100 * gauge_width):
            gauge += "|"  # Oversold threshold
        elif i == int(70 / 100 * gauge_width):
            gauge += "|"  # Overbought threshold
        elif i == int(80 / 100 * gauge_width):
            gauge += "|"  # Overbought line
        elif i == position:
            gauge += "*"
        else:
            gauge += "-"

    print(f"  0   20  30           50           70  80  100")
    print(f"  [{gauge}]")
    print(f"  {'OVERSOLD':<20}{'NEUTRAL':^20}{'OVERBOUGHT':>20}")
    print()

    # Multi-timeframe RSI
    print("MULTI-TIMEFRAME RSI:")
    print("-" * 60)

    timeframes = ["15m", "1h", "4h", "1d"]
    for tf in timeframes:
        tf_closes = await fetch_candles(hyp, ticker, tf, num_bars=period * 3)
        if tf_closes is not None and len(tf_closes) >= period + 1:
            tf_rsi = calculate_rsi(tf_closes, period)
            tf_signal = get_rsi_signal(tf_rsi)
            print(f"  {tf:>4}: RSI {tf_rsi:>6.2f} | {tf_signal['zone']:>18} | {tf_signal['signal']}")

    print("=" * 60)
    await hyp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    period = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    timeframe = sys.argv[3] if len(sys.argv) > 3 else "1h"

    asyncio.run(main(ticker, period, timeframe))
