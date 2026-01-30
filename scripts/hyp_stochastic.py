#!/usr/bin/env python
"""
Stochastic Oscillator Indicator.

Shows %K, %D, crossovers, and overbought/oversold zones.

USAGE:
  python hyp_stochastic.py <ticker> [timeframe] [k_period] [d_period]

EXAMPLES:
  python hyp_stochastic.py BTC              # Stochastic for BTC (14/3, 1h)
  python hyp_stochastic.py ETH 4h           # Stochastic for ETH, 4h
  python hyp_stochastic.py SOL 1d 14 3      # Custom settings
"""

import os
import sys
import asyncio
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from hyperliquid.info import Info
from hyperliquid.utils import constants


def calculate_stochastic(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                         k_period: int = 14, d_period: int = 3) -> dict:
    """Calculate Stochastic Oscillator."""
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

    current_k = k_values[-1] if k_values else 50
    current_d = np.mean(k_values[-d_period:]) if len(k_values) >= d_period else current_k

    # Previous values for crossover detection
    prev_k = k_values[-2] if len(k_values) >= 2 else current_k
    prev_d = np.mean(k_values[-d_period-1:-1]) if len(k_values) > d_period else current_d

    # Detect crossover
    crossover = None
    if prev_k <= prev_d and current_k > current_d:
        crossover = "bullish"
    elif prev_k >= prev_d and current_k < current_d:
        crossover = "bearish"

    # Zone classification
    if current_k >= 80:
        zone = "overbought"
    elif current_k <= 20:
        zone = "oversold"
    else:
        zone = "neutral"

    return {
        "k": current_k,
        "d": current_d,
        "prev_k": prev_k,
        "prev_d": prev_d,
        "crossover": crossover,
        "zone": zone,
        "k_history": k_values[-20:]
    }


def get_stochastic_signal(stoch_data: dict) -> dict:
    """Get trading signal from Stochastic data."""
    if not stoch_data:
        return {"signal": "INSUFFICIENT DATA", "strength": 0}

    crossover = stoch_data.get("crossover")
    zone = stoch_data.get("zone")
    k = stoch_data.get("k", 50)

    if crossover == "bullish" and zone == "oversold":
        return {"signal": "STRONG BUY - Bullish cross in oversold", "strength": 95}
    elif crossover == "bearish" and zone == "overbought":
        return {"signal": "STRONG SELL - Bearish cross in overbought", "strength": 95}
    elif crossover == "bullish":
        return {"signal": "BUY - Bullish crossover", "strength": 70}
    elif crossover == "bearish":
        return {"signal": "SELL - Bearish crossover", "strength": 70}
    elif zone == "overbought":
        return {"signal": "OVERBOUGHT - Watch for reversal", "strength": 60}
    elif zone == "oversold":
        return {"signal": "OVERSOLD - Watch for reversal", "strength": 60}
    else:
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
            return None, None, None

        candles = candles[-num_bars:] if len(candles) > num_bars else candles
        highs = np.array([float(c['h']) for c in candles])
        lows = np.array([float(c['l']) for c in candles])
        closes = np.array([float(c['c']) for c in candles])
        return highs, lows, closes
    except Exception as e:
        print(f"[ERROR] Failed to fetch candles: {e}")
        return None, None, None


async def main(ticker: str, timeframe: str = "1h", k_period: int = 14, d_period: int = 3):
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
    print(f"STOCHASTIC OSCILLATOR - {ticker}")
    print("=" * 65)
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  Timeframe:     {timeframe}")
    print(f"  Settings:      %K Period={k_period}, %D Period={d_period}")
    print()

    # Calculate Stochastic
    highs, lows, closes = await fetch_candles(info, ticker, timeframe, num_bars=(k_period + d_period) * 3)

    if highs is None or len(highs) < k_period + d_period:
        print("[ERROR] Insufficient data for Stochastic calculation")
        return

    stoch_data = calculate_stochastic(highs, lows, closes, k_period, d_period)

    if not stoch_data:
        print("[ERROR] Failed to calculate Stochastic")
        return

    signal = get_stochastic_signal(stoch_data)

    print("STOCHASTIC ANALYSIS:")
    print("-" * 65)
    print(f"  %K Value:      {stoch_data['k']:>8.2f}")
    print(f"  %D Value:      {stoch_data['d']:>8.2f}")
    print(f"  Zone:          {stoch_data['zone'].upper()}")
    print()

    if stoch_data['crossover']:
        cross_type = "BULLISH CROSSOVER" if stoch_data['crossover'] == 'bullish' else "BEARISH CROSSOVER"
        print(f"  ** {cross_type} DETECTED **")
        print()

    print(f"  Signal:        {signal['signal']}")
    print(f"  Strength:      {signal['strength']}%")
    print()

    # Visual gauge
    print("STOCHASTIC GAUGE:")
    print("-" * 65)

    gauge_width = 50
    k_pos = int(stoch_data['k'] / 100 * gauge_width)
    d_pos = int(stoch_data['d'] / 100 * gauge_width)

    k_pos = max(0, min(gauge_width, k_pos))
    d_pos = max(0, min(gauge_width, d_pos))

    # Create gauge lines
    k_line = ["-"] * (gauge_width + 1)
    d_line = ["-"] * (gauge_width + 1)

    # Mark zones
    oversold_mark = int(20 / 100 * gauge_width)
    overbought_mark = int(80 / 100 * gauge_width)

    for line in [k_line, d_line]:
        line[oversold_mark] = "|"
        line[overbought_mark] = "|"

    k_line[k_pos] = "K"
    d_line[d_pos] = "D"

    print(f"  0       20                    80      100")
    print(f"  [{''.join(k_line)}]  %K = {stoch_data['k']:.1f}")
    print(f"  [{''.join(d_line)}]  %D = {stoch_data['d']:.1f}")
    print(f"  {'OVERSOLD':<15}{'':^20}{'OVERBOUGHT':>15}")
    print()

    # K-D relationship
    print("K-D ANALYSIS:")
    print("-" * 65)
    k_above_d = stoch_data['k'] > stoch_data['d']
    print(f"  %K {'above' if k_above_d else 'below'} %D -> {'Bullish momentum' if k_above_d else 'Bearish momentum'}")
    print(f"  Spread: {abs(stoch_data['k'] - stoch_data['d']):.2f}")
    print()

    # Multi-timeframe Stochastic
    print("MULTI-TIMEFRAME STOCHASTIC:")
    print("-" * 65)
    print(f"  {'TF':>4}  {'%K':>8}  {'%D':>8}  {'Zone':>12}  {'Status'}")
    print("-" * 65)

    timeframes = ["15m", "1h", "4h", "1d"]
    for tf in timeframes:
        tf_highs, tf_lows, tf_closes = await fetch_candles(info, ticker, tf, num_bars=(k_period + d_period) * 3)
        if tf_highs is not None and len(tf_highs) >= k_period + d_period:
            tf_stoch = calculate_stochastic(tf_highs, tf_lows, tf_closes, k_period, d_period)
            if tf_stoch:
                status = ""
                if tf_stoch['crossover']:
                    status = f"** {tf_stoch['crossover'].upper()} CROSS **"
                elif tf_stoch['k'] > tf_stoch['d']:
                    status = "Bullish"
                else:
                    status = "Bearish"
                print(f"  {tf:>4}  {tf_stoch['k']:>8.2f}  {tf_stoch['d']:>8.2f}  {tf_stoch['zone']:>12}  {status}")

    print("=" * 65)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"
    k_period = int(sys.argv[3]) if len(sys.argv) > 3 else 14
    d_period = int(sys.argv[4]) if len(sys.argv) > 4 else 3

    asyncio.run(main(ticker, timeframe, k_period, d_period))
