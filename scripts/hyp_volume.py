#!/usr/bin/env python
"""
Volume Analysis Indicator.

Shows volume spikes, volume trends, and volume-price relationships.

USAGE:
  python hyp_volume.py <ticker> [timeframe] [lookback]

EXAMPLES:
  python hyp_volume.py BTC              # Volume for BTC (20 bar MA, 1h)
  python hyp_volume.py ETH 4h           # Volume for ETH, 4h timeframe
  python hyp_volume.py SOL 1d 50        # Volume for SOL, daily, 50 bar lookback
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

INTERVAL_MS = {
    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000, '1h': 60 * 60 * 1000, '2h': 2 * 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000, '8h': 8 * 60 * 60 * 1000, '12h': 12 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000, '3d': 3 * 24 * 60 * 60 * 1000, '1w': 7 * 24 * 60 * 60 * 1000,
}


def calculate_volume_analysis(volumes: np.ndarray, closes: np.ndarray, lookback: int = 20) -> dict:
    """Calculate volume analysis metrics."""
    if len(volumes) < lookback:
        return None

    current_volume = volumes[-1]
    volume_ma = np.mean(volumes[-lookback:])
    spike_ratio = current_volume / volume_ma if volume_ma > 0 else 0

    # Volume trend
    recent_avg = np.mean(volumes[-5:]) if len(volumes) >= 5 else current_volume
    older_avg = np.mean(volumes[-lookback:-5]) if len(volumes) > 5 else volume_ma
    volume_trend = "INCREASING" if recent_avg > older_avg * 1.2 else "DECREASING" if recent_avg < older_avg * 0.8 else "STABLE"

    # Volume-price relationship
    price_change = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 else 0
    volume_change = (volumes[-1] - volumes[-2]) / volumes[-2] * 100 if len(volumes) >= 2 and volumes[-2] > 0 else 0

    if price_change > 0 and volume_change > 0:
        vp_relationship = "BULLISH_CONFIRMATION"
    elif price_change < 0 and volume_change > 0:
        vp_relationship = "BEARISH_CONFIRMATION"
    elif price_change > 0 and volume_change < 0:
        vp_relationship = "BULLISH_DIVERGENCE"
    elif price_change < 0 and volume_change < 0:
        vp_relationship = "BEARISH_DIVERGENCE"
    else:
        vp_relationship = "NEUTRAL"

    # Classify volume level
    if spike_ratio >= 2.0:
        volume_level = "EXTREME"
    elif spike_ratio >= 1.5:
        volume_level = "HIGH"
    elif spike_ratio >= 1.0:
        volume_level = "ABOVE_AVERAGE"
    elif spike_ratio >= 0.5:
        volume_level = "BELOW_AVERAGE"
    else:
        volume_level = "LOW"

    # Volume history for visualization
    volume_history = volumes[-15:] if len(volumes) >= 15 else volumes

    return {
        "current_volume": current_volume,
        "volume_ma": volume_ma,
        "spike_ratio": spike_ratio,
        "volume_level": volume_level,
        "volume_trend": volume_trend,
        "price_change": price_change,
        "volume_change": volume_change,
        "vp_relationship": vp_relationship,
        "volume_history": volume_history,
        "max_volume": np.max(volumes[-lookback:]),
        "min_volume": np.min(volumes[-lookback:])
    }


def get_volume_signal(vol_data: dict) -> dict:
    """Get trading signal from volume data."""
    if not vol_data:
        return {"signal": "INSUFFICIENT DATA", "strength": 0}

    level = vol_data["volume_level"]
    vp_rel = vol_data["vp_relationship"]

    if level in ["EXTREME", "HIGH"]:
        if vp_rel == "BULLISH_CONFIRMATION":
            return {"signal": "STRONG BULLISH - High volume up move", "strength": 85}
        elif vp_rel == "BEARISH_CONFIRMATION":
            return {"signal": "STRONG BEARISH - High volume down move", "strength": 85}
        elif vp_rel == "BULLISH_DIVERGENCE":
            return {"signal": "WARNING - Rising on low volume", "strength": 50}
        elif vp_rel == "BEARISH_DIVERGENCE":
            return {"signal": "WARNING - Falling on low volume", "strength": 50}
        else:
            return {"signal": "HIGH VOLUME ALERT", "strength": 70}
    elif level == "LOW":
        return {"signal": "LOW VOLUME - Weak conviction", "strength": 30}

    return {"signal": "NORMAL VOLUME", "strength": 0}


TIMEFRAME_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "8h": "8h", "12h": "12h",
    "1d": "1d", "3d": "3d", "1w": "1w"
}


async def fetch_candles(hyp: Hyperliquid, ticker: str, timeframe: str, num_bars: int = 100):
    """Fetch candle data from Hyperliquid."""
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

        if not candles:
            return None, None

        candles = candles[-num_bars:] if len(candles) > num_bars else candles
        volumes = np.array([float(c['v']) for c in candles])
        closes = np.array([float(c['c']) for c in candles])
        return volumes, closes
    except Exception as e:
        print(f"[ERROR] Failed to fetch candles: {e}")
        return None, None


def format_volume(vol: float) -> str:
    """Format volume with K/M/B suffixes."""
    if vol >= 1_000_000_000:
        return f"{vol/1_000_000_000:.2f}B"
    elif vol >= 1_000_000:
        return f"{vol/1_000_000:.2f}M"
    elif vol >= 1_000:
        return f"{vol/1_000:.2f}K"
    else:
        return f"{vol:.2f}"


async def main(ticker: str, timeframe: str = "1h", lookback: int = 20):
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

    print("=" * 65)
    print(f"VOLUME ANALYSIS - {ticker}")
    print("=" * 65)
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  Timeframe:     {timeframe}")
    print(f"  MA Period:     {lookback}")
    print()

    # Calculate volume analysis
    volumes, closes = await fetch_candles(hyp, ticker, timeframe, num_bars=lookback * 3)

    if volumes is None or len(volumes) < lookback:
        await hyp.cleanup()
        print("[ERROR] Insufficient data for volume calculation")
        return

    vol_data = calculate_volume_analysis(volumes, closes, lookback)

    if not vol_data:
        print("[ERROR] Failed to calculate volume metrics")
        return

    signal = get_volume_signal(vol_data)

    print("VOLUME METRICS:")
    print("-" * 65)
    print(f"  Current Volume:   {format_volume(vol_data['current_volume']):>12}")
    print(f"  Volume MA ({lookback}):   {format_volume(vol_data['volume_ma']):>12}")
    print(f"  Spike Ratio:      {vol_data['spike_ratio']:>12.2f}x")
    print(f"  Volume Level:     {vol_data['volume_level']:>12}")
    print(f"  Volume Trend:     {vol_data['volume_trend']:>12}")
    print()
    print(f"  Max Volume ({lookback}):  {format_volume(vol_data['max_volume']):>12}")
    print(f"  Min Volume ({lookback}):  {format_volume(vol_data['min_volume']):>12}")
    print()

    print("VOLUME-PRICE RELATIONSHIP:")
    print("-" * 65)
    print(f"  Price Change:     {vol_data['price_change']:>+12.2f}%")
    print(f"  Volume Change:    {vol_data['volume_change']:>+12.2f}%")
    print(f"  Relationship:     {vol_data['vp_relationship'].replace('_', ' ')}")
    print()

    print(f"  Signal:        {signal['signal']}")
    print(f"  Strength:      {signal['strength']}%")
    print()

    # Volume bar chart
    print("VOLUME HISTORY (Last 15 bars):")
    print("-" * 65)

    vol_hist = vol_data['volume_history']
    max_vol = np.max(vol_hist)

    for i, v in enumerate(vol_hist):
        bar_len = int(v / max_vol * 30) if max_vol > 0 else 0
        bar = "#" * bar_len

        # Mark if above/below average
        marker = "+" if v > vol_data['volume_ma'] else "-" if v < vol_data['volume_ma'] * 0.5 else " "
        print(f"  {i+1:>2} {marker} {bar:<30} {format_volume(v):>10}")

    print()
    print(f"  Legend: + = Above MA, - = Below 50% MA, # = Volume bar")
    print()

    # Multi-timeframe volume
    print("MULTI-TIMEFRAME VOLUME:")
    print("-" * 65)
    print(f"  {'TF':>4}  {'Volume':>12}  {'vs MA':>8}  {'Level':>12}  {'Trend'}")
    print("-" * 65)

    timeframes = ["15m", "1h", "4h", "1d"]
    for tf in timeframes:
        tf_volumes, tf_closes = await fetch_candles(hyp, ticker, tf, num_bars=lookback * 3)
        if tf_volumes is not None and len(tf_volumes) >= lookback:
            tf_vol = calculate_volume_analysis(tf_volumes, tf_closes, lookback)
            if tf_vol:
                print(f"  {tf:>4}  {format_volume(tf_vol['current_volume']):>12}  {tf_vol['spike_ratio']:>7.2f}x  {tf_vol['volume_level']:>12}  {tf_vol['volume_trend']}")

    print("=" * 65)
    await hyp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"
    lookback = int(sys.argv[3]) if len(sys.argv) > 3 else 20

    asyncio.run(main(ticker, timeframe, lookback))
