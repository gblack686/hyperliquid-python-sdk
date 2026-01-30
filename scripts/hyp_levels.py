#!/usr/bin/env python
"""
Support and Resistance Levels Indicator.

Identifies key price levels based on pivot points and price clustering.

USAGE:
  python hyp_levels.py <ticker> [timeframe] [lookback]

EXAMPLES:
  python hyp_levels.py BTC              # S/R for BTC (100 bars, 1h)
  python hyp_levels.py ETH 4h           # S/R for ETH, 4h timeframe
  python hyp_levels.py SOL 1d 200       # S/R for SOL, daily, 200 bar lookback
"""

import os
import sys
import asyncio
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from hyperliquid.info import Info
from hyperliquid.utils import constants


def find_pivot_points(data: np.ndarray, order: int = 5) -> tuple:
    """Find local highs and lows (pivot points)."""
    highs = []
    lows = []

    for i in range(order, len(data) - order):
        # Check if local maximum
        if all(data[i] >= data[i-j] for j in range(1, order+1)) and \
           all(data[i] >= data[i+j] for j in range(1, order+1)):
            highs.append(i)

        # Check if local minimum
        if all(data[i] <= data[i-j] for j in range(1, order+1)) and \
           all(data[i] <= data[i+j] for j in range(1, order+1)):
            lows.append(i)

    return np.array(highs), np.array(lows)


def cluster_levels(levels: list, tolerance: float = 0.002, min_touches: int = 2) -> list:
    """Cluster similar price levels together."""
    if not levels:
        return []

    sorted_levels = sorted(levels)
    clusters = []
    current_cluster = [sorted_levels[0]]

    for level in sorted_levels[1:]:
        if abs(level - current_cluster[-1]) / current_cluster[-1] <= tolerance:
            current_cluster.append(level)
        else:
            if len(current_cluster) >= min_touches:
                clusters.append({
                    "level": np.mean(current_cluster),
                    "strength": len(current_cluster),
                    "touches": len(current_cluster)
                })
            current_cluster = [level]

    if len(current_cluster) >= min_touches:
        clusters.append({
            "level": np.mean(current_cluster),
            "strength": len(current_cluster),
            "touches": len(current_cluster)
        })

    return clusters


def calculate_support_resistance(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                                  lookback: int = 100, tolerance: float = 0.005) -> dict:
    """Calculate support and resistance levels."""
    if len(highs) < lookback:
        lookback = len(highs)

    highs = highs[-lookback:]
    lows = lows[-lookback:]
    closes = closes[-lookback:]
    current_price = closes[-1]

    # Find pivot points
    high_pivots, low_pivots = find_pivot_points(highs, order=3)

    resistance_candidates = [highs[i] for i in high_pivots]
    support_candidates = [lows[i] for i in low_pivots]

    # Cluster levels
    resistance_levels = cluster_levels(resistance_candidates, tolerance, min_touches=1)
    support_levels = cluster_levels(support_candidates, tolerance, min_touches=1)

    # Sort and limit
    resistance_levels = sorted(resistance_levels, key=lambda x: x["level"], reverse=True)[:5]
    support_levels = sorted(support_levels, key=lambda x: x["level"], reverse=True)[:5]

    # Find nearest levels
    nearest_support = None
    nearest_resistance = None

    for support in support_levels:
        if support["level"] < current_price:
            nearest_support = support
            break

    for resistance in reversed(resistance_levels):
        if resistance["level"] > current_price:
            nearest_resistance = resistance
            break

    # Calculate position info
    position_info = {}
    if nearest_resistance and nearest_support:
        range_size = nearest_resistance["level"] - nearest_support["level"]
        if range_size > 0:
            position_in_range = (current_price - nearest_support["level"]) / range_size
        else:
            position_in_range = 0.5

        position_info = {
            "position_in_range": position_in_range,
            "distance_to_resistance": (nearest_resistance["level"] - current_price) / current_price,
            "distance_to_support": (current_price - nearest_support["level"]) / current_price
        }

    return {
        "support_levels": support_levels,
        "resistance_levels": resistance_levels,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "current_price": current_price,
        **position_info
    }


def get_sr_signal(sr_data: dict) -> dict:
    """Get trading signal from S/R data."""
    if not sr_data:
        return {"signal": "INSUFFICIENT DATA", "strength": 0}

    dist_res = sr_data.get("distance_to_resistance", 1)
    dist_sup = sr_data.get("distance_to_support", 1)

    if dist_res is not None and dist_res < 0.005:
        strength = 70
        if sr_data.get("nearest_resistance", {}).get("strength", 0) > 3:
            strength = 85
        return {"signal": "AT RESISTANCE - Watch for rejection", "strength": strength}
    elif dist_sup is not None and dist_sup < 0.005:
        strength = 70
        if sr_data.get("nearest_support", {}).get("strength", 0) > 3:
            strength = 85
        return {"signal": "AT SUPPORT - Watch for bounce", "strength": strength}
    elif sr_data.get("position_in_range", 0.5) > 0.8:
        return {"signal": "NEAR RESISTANCE", "strength": 40}
    elif sr_data.get("position_in_range", 0.5) < 0.2:
        return {"signal": "NEAR SUPPORT", "strength": 40}

    return {"signal": "NEUTRAL - Mid-range", "strength": 0}


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


async def main(ticker: str, timeframe: str = "1h", lookback: int = 100):
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

    print("=" * 70)
    print(f"SUPPORT & RESISTANCE - {ticker}")
    print("=" * 70)
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  Timeframe:     {timeframe}")
    print(f"  Lookback:      {lookback} bars")
    print()

    # Calculate S/R levels
    highs, lows, closes = await fetch_candles(info, ticker, timeframe, num_bars=lookback)

    if highs is None or len(highs) < 20:
        print("[ERROR] Insufficient data for S/R calculation")
        return

    sr_data = calculate_support_resistance(highs, lows, closes, lookback)

    if not sr_data:
        print("[ERROR] Failed to calculate S/R levels")
        return

    signal = get_sr_signal(sr_data)

    # Display resistance levels
    print("RESISTANCE LEVELS:")
    print("-" * 70)
    for i, res in enumerate(sr_data['resistance_levels'][:5]):
        dist = (res['level'] - current_price) / current_price * 100
        nearest = " <-- NEAREST" if sr_data['nearest_resistance'] and res['level'] == sr_data['nearest_resistance']['level'] else ""
        print(f"  R{i+1}: ${res['level']:>12,.2f}  ({dist:>+6.2f}%)  Strength: {res['strength']}{nearest}")

    print()

    # Display current price
    print(f"  *** PRICE: ${current_price:>10,.2f} ***")
    print()

    # Display support levels
    print("SUPPORT LEVELS:")
    print("-" * 70)
    for i, sup in enumerate(sr_data['support_levels'][:5]):
        dist = (sup['level'] - current_price) / current_price * 100
        nearest = " <-- NEAREST" if sr_data['nearest_support'] and sup['level'] == sr_data['nearest_support']['level'] else ""
        print(f"  S{i+1}: ${sup['level']:>12,.2f}  ({dist:>+6.2f}%)  Strength: {sup['strength']}{nearest}")

    print()

    # Position analysis
    if sr_data.get('position_in_range') is not None:
        print("POSITION ANALYSIS:")
        print("-" * 70)
        print(f"  Position in range: {sr_data['position_in_range']*100:.1f}%")
        if sr_data.get('distance_to_resistance') is not None:
            print(f"  Distance to resistance: {sr_data['distance_to_resistance']*100:.2f}%")
        if sr_data.get('distance_to_support') is not None:
            print(f"  Distance to support: {sr_data['distance_to_support']*100:.2f}%")
        print()

    print(f"  Signal:        {signal['signal']}")
    print(f"  Strength:      {signal['strength']}%")
    print()

    # Visual price ladder
    print("PRICE LADDER:")
    print("-" * 70)

    all_levels = []
    for res in sr_data['resistance_levels'][:3]:
        all_levels.append(('R', res['level'], res['strength']))
    all_levels.append(('P', current_price, 0))
    for sup in sr_data['support_levels'][:3]:
        all_levels.append(('S', sup['level'], sup['strength']))

    all_levels.sort(key=lambda x: x[1], reverse=True)

    for level_type, price, strength in all_levels:
        if level_type == 'R':
            print(f"  R  ${price:>12,.2f}  {'=' * strength}  (resistance)")
        elif level_type == 'S':
            print(f"  S  ${price:>12,.2f}  {'=' * strength}  (support)")
        else:
            print(f"  *  ${price:>12,.2f}  <-- CURRENT PRICE")

    print()

    # Multi-timeframe S/R
    print("MULTI-TIMEFRAME KEY LEVELS:")
    print("-" * 70)
    print(f"  {'TF':>4}  {'Nearest Res':>14}  {'Nearest Sup':>14}  {'Range %':>8}")
    print("-" * 70)

    timeframes = ["15m", "1h", "4h", "1d"]
    for tf in timeframes:
        tf_highs, tf_lows, tf_closes = await fetch_candles(info, ticker, tf, num_bars=lookback)
        if tf_highs is not None and len(tf_highs) >= 20:
            tf_sr = calculate_support_resistance(tf_highs, tf_lows, tf_closes, lookback)
            if tf_sr:
                res_str = f"${tf_sr['nearest_resistance']['level']:,.2f}" if tf_sr['nearest_resistance'] else "N/A"
                sup_str = f"${tf_sr['nearest_support']['level']:,.2f}" if tf_sr['nearest_support'] else "N/A"
                range_pct = f"{tf_sr.get('position_in_range', 0)*100:.1f}%" if tf_sr.get('position_in_range') else "N/A"
                print(f"  {tf:>4}  {res_str:>14}  {sup_str:>14}  {range_pct:>8}")

    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"
    lookback = int(sys.argv[3]) if len(sys.argv) > 3 else 100

    asyncio.run(main(ticker, timeframe, lookback))
