#!/usr/bin/env python
"""
Bollinger Bands Indicator.

Shows upper/lower bands, squeeze detection, and breakout signals.

USAGE:
  python hyp_bollinger.py <ticker> [timeframe] [period] [std_dev]

EXAMPLES:
  python hyp_bollinger.py BTC               # BB for BTC (20 period, 2 std, 1h)
  python hyp_bollinger.py ETH 4h            # BB for ETH, 4h timeframe
  python hyp_bollinger.py SOL 1d 20 2.5     # Custom BB settings
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


def calculate_bollinger(closes: np.ndarray, period: int = 20, std_dev: float = 2.0) -> dict:
    """Calculate Bollinger Bands."""
    if len(closes) < period:
        return None

    recent = closes[-period:]
    current_price = closes[-1]

    middle_band = np.mean(recent)
    std = np.std(recent)

    upper_band = middle_band + (std_dev * std)
    lower_band = middle_band - (std_dev * std)
    band_width = upper_band - lower_band
    band_width_pct = (band_width / middle_band * 100) if middle_band > 0 else 0

    # Calculate historical band widths for squeeze detection
    historical_widths = []
    for i in range(max(0, len(closes) - 50), len(closes) - period + 1):
        window = closes[i:i+period]
        w_std = np.std(window)
        w_width = 2 * std_dev * w_std
        historical_widths.append(w_width)

    avg_width = np.mean(historical_widths) if historical_widths else band_width
    squeeze = band_width < avg_width * 0.7

    # Price position within bands
    if band_width > 0:
        position_pct = (current_price - lower_band) / band_width * 100
    else:
        position_pct = 50

    return {
        "upper": upper_band,
        "middle": middle_band,
        "lower": lower_band,
        "width": band_width,
        "width_pct": band_width_pct,
        "squeeze": squeeze,
        "current_price": current_price,
        "position_pct": position_pct,
        "avg_width": avg_width
    }


def get_bb_signal(bb_data: dict) -> dict:
    """Get trading signal from Bollinger Bands."""
    if not bb_data:
        return {"signal": "INSUFFICIENT DATA", "strength": 0}

    price = bb_data["current_price"]
    upper = bb_data["upper"]
    lower = bb_data["lower"]
    position = bb_data["position_pct"]
    squeeze = bb_data["squeeze"]

    if price > upper:
        return {"signal": "BREAKOUT UP - Overbought", "strength": 85, "zone": "above_upper"}
    elif price < lower:
        return {"signal": "BREAKOUT DOWN - Oversold", "strength": 85, "zone": "below_lower"}
    elif squeeze:
        return {"signal": "SQUEEZE - Prepare for breakout", "strength": 60, "zone": "squeeze"}
    elif position > 80:
        return {"signal": "NEAR UPPER - Caution", "strength": 50, "zone": "upper_zone"}
    elif position < 20:
        return {"signal": "NEAR LOWER - Caution", "strength": 50, "zone": "lower_zone"}
    else:
        return {"signal": "NEUTRAL", "strength": 0, "zone": "middle"}


TIMEFRAME_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "8h": "8h", "12h": "12h",
    "1d": "1d", "3d": "3d", "1w": "1w"
}


async def fetch_candles(hyp: Hyperliquid, ticker: str, timeframe: str, num_bars: int = 200):
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
            return None

        candles = candles[-num_bars:] if len(candles) > num_bars else candles
        closes = np.array([float(c['c']) for c in candles])
        return closes
    except Exception as e:
        print(f"[ERROR] Failed to fetch candles: {e}")
        return None


async def main(ticker: str, timeframe: str = "1h", period: int = 20, std_dev: float = 2.0):
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
    print(f"BOLLINGER BANDS - {ticker}")
    print("=" * 65)
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  Timeframe:     {timeframe}")
    print(f"  Settings:      Period={period}, Std Dev={std_dev}")
    print()

    # Calculate Bollinger Bands
    closes = await fetch_candles(hyp, ticker, timeframe, num_bars=period * 3)

    if closes is None or len(closes) < period:
        await hyp.cleanup()
        print("[ERROR] Insufficient data for Bollinger Bands calculation")
        return

    bb_data = calculate_bollinger(closes, period, std_dev)

    if not bb_data:
        print("[ERROR] Failed to calculate Bollinger Bands")
        return

    signal = get_bb_signal(bb_data)

    print("BOLLINGER BANDS:")
    print("-" * 65)
    print(f"  Upper Band:    ${bb_data['upper']:>12,.2f}")
    print(f"  Middle Band:   ${bb_data['middle']:>12,.2f}")
    print(f"  Lower Band:    ${bb_data['lower']:>12,.2f}")
    print(f"  Band Width:    ${bb_data['width']:>12,.2f} ({bb_data['width_pct']:.2f}%)")
    print()
    print(f"  Price Position: {bb_data['position_pct']:.1f}% within bands")
    print(f"  Squeeze:        {'YES - Low volatility!' if bb_data['squeeze'] else 'No'}")
    print()
    print(f"  Signal:        {signal['signal']}")
    print(f"  Strength:      {signal['strength']}%")
    print()

    # Visual band representation
    print("BAND VISUALIZATION:")
    print("-" * 65)

    upper = bb_data['upper']
    middle = bb_data['middle']
    lower = bb_data['lower']
    price = bb_data['current_price']

    # Normalize to 0-50 scale
    band_range = upper - lower
    if band_range > 0:
        price_pos = int((price - lower) / band_range * 50)
        middle_pos = int((middle - lower) / band_range * 50)
    else:
        price_pos = 25
        middle_pos = 25

    price_pos = max(0, min(50, price_pos))
    middle_pos = max(0, min(50, middle_pos))

    line = ["-"] * 51
    line[0] = "L"
    line[50] = "U"
    line[middle_pos] = "M"
    line[price_pos] = "*"

    print(f"  Lower                  Middle                   Upper")
    print(f"  ${''.join(line)}$")
    print(f"  {lower:<,.0f}{' ' * 20}{middle:^,.0f}{' ' * 20}{upper:>,.0f}")
    print(f"  {'':20}Price: ${price:,.2f} (*)")
    print()

    # Multi-timeframe Bollinger Bands
    print("MULTI-TIMEFRAME BOLLINGER BANDS:")
    print("-" * 65)
    print(f"  {'TF':>4}  {'Upper':>12}  {'Middle':>12}  {'Lower':>12}  {'Pos %':>6}  {'Status'}")
    print("-" * 65)

    timeframes = ["15m", "1h", "4h", "1d"]
    for tf in timeframes:
        tf_closes = await fetch_candles(hyp, ticker, tf, num_bars=period * 3)
        if tf_closes is not None and len(tf_closes) >= period:
            tf_bb = calculate_bollinger(tf_closes, period, std_dev)
            if tf_bb:
                tf_signal = get_bb_signal(tf_bb)
                squeeze_flag = " [SQ]" if tf_bb['squeeze'] else ""
                print(f"  {tf:>4}  ${tf_bb['upper']:>10,.2f}  ${tf_bb['middle']:>10,.2f}  ${tf_bb['lower']:>10,.2f}  {tf_bb['position_pct']:>5.1f}%  {tf_signal['zone']}{squeeze_flag}")

    print("=" * 65)
    await hyp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"
    period = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    std_dev = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0

    asyncio.run(main(ticker, timeframe, period, std_dev))
