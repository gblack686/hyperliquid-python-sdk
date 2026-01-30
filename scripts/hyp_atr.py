#!/usr/bin/env python
"""
ATR (Average True Range) Volatility Indicator.

Shows volatility levels, suggested stop loss, and position sizing.

USAGE:
  python hyp_atr.py <ticker> [timeframe] [period]

EXAMPLES:
  python hyp_atr.py BTC              # ATR for BTC (14 period, 1h)
  python hyp_atr.py ETH 4h           # ATR for ETH, 4h timeframe
  python hyp_atr.py SOL 1d 21        # ATR for SOL, daily, 21 period
"""

import os
import sys
import asyncio
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from hyperliquid.info import Info
from hyperliquid.utils import constants


def calculate_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> dict:
    """Calculate ATR and volatility metrics."""
    if len(highs) < period + 1:
        return None

    # Calculate True Range
    true_ranges = []
    for i in range(1, len(highs)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i-1])
        low_close = abs(lows[i] - closes[i-1])
        true_range = max(high_low, high_close, low_close)
        true_ranges.append(true_range)

    if len(true_ranges) < period:
        return None

    # Calculate ATR using Wilder's smoothing
    atr_values = []
    atr = np.mean(true_ranges[:period])
    atr_values.append(atr)

    for i in range(period, len(true_ranges)):
        atr = ((atr * (period - 1)) + true_ranges[i]) / period
        atr_values.append(atr)

    current_atr = atr_values[-1]
    current_price = closes[-1]
    atr_pct = (current_atr / current_price * 100) if current_price > 0 else 0

    # Historical ATR percentage for comparison
    historical_atr_pct = []
    for i in range(max(0, len(atr_values) - 50), len(atr_values)):
        idx = len(true_ranges) - len(atr_values) + i + 1
        if idx < len(closes):
            pct = (atr_values[i] / closes[idx] * 100) if closes[idx] > 0 else 0
            historical_atr_pct.append(pct)

    avg_atr_pct = np.mean(historical_atr_pct) if historical_atr_pct else atr_pct

    # Volatility classification
    if atr_pct > avg_atr_pct * 1.5:
        volatility = "HIGH"
    elif atr_pct > avg_atr_pct * 1.2:
        volatility = "INCREASING"
    elif atr_pct < avg_atr_pct * 0.7:
        volatility = "LOW"
    else:
        volatility = "NORMAL"

    return {
        "atr": current_atr,
        "atr_pct": atr_pct,
        "avg_atr_pct": avg_atr_pct,
        "volatility": volatility,
        "current_price": current_price,
        "suggested_stop_1x": current_atr,
        "suggested_stop_2x": current_atr * 2,
        "suggested_stop_3x": current_atr * 3,
        "atr_history": atr_values[-20:]
    }


def get_atr_signal(atr_data: dict) -> dict:
    """Get trading guidance from ATR data."""
    if not atr_data:
        return {"signal": "INSUFFICIENT DATA", "strength": 0}

    volatility = atr_data["volatility"]

    if volatility == "HIGH":
        return {"signal": "REDUCE SIZE - High Volatility", "strength": 70}
    elif volatility == "INCREASING":
        return {"signal": "CAUTION - Volatility Rising", "strength": 50}
    elif volatility == "LOW":
        return {"signal": "PREPARE - Breakout Potential", "strength": 40}
    else:
        return {"signal": "NORMAL CONDITIONS", "strength": 0}


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
            return None, None, None

        candles = candles[-num_bars:] if len(candles) > num_bars else candles
        highs = np.array([float(c['h']) for c in candles])
        lows = np.array([float(c['l']) for c in candles])
        closes = np.array([float(c['c']) for c in candles])
        return highs, lows, closes
    except Exception as e:
        print(f"[ERROR] Failed to fetch candles: {e}")
        return None, None, None


async def main(ticker: str, timeframe: str = "1h", period: int = 14):
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
    print(f"ATR VOLATILITY - {ticker}")
    print("=" * 65)
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  Timeframe:     {timeframe}")
    print(f"  Period:        {period}")
    print()

    # Calculate ATR
    highs, lows, closes = await fetch_candles(info, ticker, timeframe, num_bars=period * 5)

    if highs is None or len(highs) < period + 1:
        print("[ERROR] Insufficient data for ATR calculation")
        return

    atr_data = calculate_atr(highs, lows, closes, period)

    if not atr_data:
        print("[ERROR] Failed to calculate ATR")
        return

    signal = get_atr_signal(atr_data)

    print("ATR ANALYSIS:")
    print("-" * 65)
    print(f"  ATR Value:     ${atr_data['atr']:>12,.2f}")
    print(f"  ATR %:         {atr_data['atr_pct']:>12.2f}%")
    print(f"  Avg ATR %:     {atr_data['avg_atr_pct']:>12.2f}%")
    print(f"  Volatility:    {atr_data['volatility']}")
    print()
    print(f"  Signal:        {signal['signal']}")
    print()

    # Stop loss suggestions
    print("STOP LOSS SUGGESTIONS:")
    print("-" * 65)
    print(f"  1x ATR Stop:   ${atr_data['suggested_stop_1x']:,.2f}")
    print(f"                 Long: ${current_price - atr_data['suggested_stop_1x']:,.2f}")
    print(f"                 Short: ${current_price + atr_data['suggested_stop_1x']:,.2f}")
    print()
    print(f"  2x ATR Stop:   ${atr_data['suggested_stop_2x']:,.2f}")
    print(f"                 Long: ${current_price - atr_data['suggested_stop_2x']:,.2f}")
    print(f"                 Short: ${current_price + atr_data['suggested_stop_2x']:,.2f}")
    print()
    print(f"  3x ATR Stop:   ${atr_data['suggested_stop_3x']:,.2f}")
    print(f"                 Long: ${current_price - atr_data['suggested_stop_3x']:,.2f}")
    print(f"                 Short: ${current_price + atr_data['suggested_stop_3x']:,.2f}")
    print()

    # Position sizing suggestion
    print("POSITION SIZING (Risk-Based):")
    print("-" * 65)
    risk_amounts = [100, 500, 1000]
    for risk in risk_amounts:
        size = risk / atr_data['suggested_stop_2x'] if atr_data['suggested_stop_2x'] > 0 else 0
        notional = size * current_price
        print(f"  ${risk:>4} risk -> {size:.6f} {ticker} (${notional:,.2f} notional)")
    print()

    # Volatility gauge
    print("VOLATILITY GAUGE:")
    print("-" * 65)
    ratio = atr_data['atr_pct'] / atr_data['avg_atr_pct'] if atr_data['avg_atr_pct'] > 0 else 1
    gauge_pos = int(min(ratio, 2) / 2 * 40)
    gauge = ["-"] * 41
    gauge[20] = "|"  # Average line
    gauge[gauge_pos] = "*"

    print(f"  Low           Average           High")
    print(f"  [{''.join(gauge)}]")
    print(f"  Current: {ratio:.2f}x average ATR")
    print()

    # Multi-timeframe ATR
    print("MULTI-TIMEFRAME ATR:")
    print("-" * 65)
    print(f"  {'TF':>4}  {'ATR':>12}  {'ATR %':>8}  {'Volatility':>12}")
    print("-" * 65)

    timeframes = ["15m", "1h", "4h", "1d"]
    for tf in timeframes:
        tf_highs, tf_lows, tf_closes = await fetch_candles(info, ticker, tf, num_bars=period * 5)
        if tf_highs is not None and len(tf_highs) >= period + 1:
            tf_atr = calculate_atr(tf_highs, tf_lows, tf_closes, period)
            if tf_atr:
                print(f"  {tf:>4}  ${tf_atr['atr']:>10,.2f}  {tf_atr['atr_pct']:>7.2f}%  {tf_atr['volatility']:>12}")

    print("=" * 65)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"
    period = int(sys.argv[3]) if len(sys.argv) > 3 else 14

    asyncio.run(main(ticker, timeframe, period))
