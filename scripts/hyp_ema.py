#!/usr/bin/env python
"""
EMA/MA Crossover Indicator.

Shows moving average crossovers, golden/death cross, and trend direction.

USAGE:
  python hyp_ema.py <ticker> [timeframe] [fast] [slow]

EXAMPLES:
  python hyp_ema.py BTC              # EMA for BTC (20/50, 1h)
  python hyp_ema.py ETH 4h           # EMA for ETH, 4h timeframe
  python hyp_ema.py SOL 1d 50 200    # Classic 50/200 golden cross
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


def calculate_ema(closes: np.ndarray, period: int) -> float:
    """Calculate single EMA value."""
    if len(closes) < period:
        return closes[-1] if len(closes) > 0 else 0

    multiplier = 2 / (period + 1)
    ema = np.mean(closes[:period])

    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def calculate_sma(closes: np.ndarray, period: int) -> float:
    """Calculate simple moving average."""
    if len(closes) < period:
        return np.mean(closes) if len(closes) > 0 else 0
    return np.mean(closes[-period:])


def calculate_ma_crossover(closes: np.ndarray, fast: int = 20, slow: int = 50, use_ema: bool = True) -> dict:
    """Calculate MA crossover data."""
    if len(closes) < slow:
        return None

    calc_func = calculate_ema if use_ema else calculate_sma

    current_fast = calc_func(closes, fast)
    current_slow = calc_func(closes, slow)

    # Previous values
    prev_fast = calc_func(closes[:-1], fast)
    prev_slow = calc_func(closes[:-1], slow)

    # Current price
    current_price = closes[-1]

    # Crossover detection
    crossover = None
    crossover_name = None
    if prev_fast <= prev_slow and current_fast > current_slow:
        crossover = "bullish"
        crossover_name = "Golden Cross" if fast == 50 and slow == 200 else "Bullish Crossover"
    elif prev_fast >= prev_slow and current_fast < current_slow:
        crossover = "bearish"
        crossover_name = "Death Cross" if fast == 50 and slow == 200 else "Bearish Crossover"

    # Trend determination
    if current_fast > current_slow:
        trend = "BULLISH"
    else:
        trend = "BEARISH"

    # Price position relative to MAs
    if current_price > current_fast and current_price > current_slow:
        price_position = "above_both"
    elif current_price < current_fast and current_price < current_slow:
        price_position = "below_both"
    elif current_price > current_fast:
        price_position = "between_above_fast"
    else:
        price_position = "between_below_fast"

    spread = current_fast - current_slow
    spread_pct = (spread / current_slow * 100) if current_slow > 0 else 0

    return {
        "fast_ma": current_fast,
        "slow_ma": current_slow,
        "current_price": current_price,
        "crossover": crossover,
        "crossover_name": crossover_name,
        "trend": trend,
        "price_position": price_position,
        "spread": spread,
        "spread_pct": spread_pct
    }


def get_ma_signal(ma_data: dict) -> dict:
    """Get trading signal from MA data."""
    if not ma_data:
        return {"signal": "INSUFFICIENT DATA", "strength": 0}

    crossover = ma_data.get("crossover")
    trend = ma_data.get("trend")
    price_pos = ma_data.get("price_position")

    if crossover == "bullish":
        return {"signal": f"BUY - {ma_data['crossover_name']}", "strength": 90}
    elif crossover == "bearish":
        return {"signal": f"SELL - {ma_data['crossover_name']}", "strength": 90}
    elif price_pos == "above_both" and trend == "BULLISH":
        return {"signal": "BULLISH - Price above both MAs", "strength": 70}
    elif price_pos == "below_both" and trend == "BEARISH":
        return {"signal": "BEARISH - Price below both MAs", "strength": 70}
    elif trend == "BULLISH":
        return {"signal": "BULLISH TREND", "strength": 50}
    elif trend == "BEARISH":
        return {"signal": "BEARISH TREND", "strength": 50}

    return {"signal": "NEUTRAL", "strength": 0}


TIMEFRAME_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "8h": "8h", "12h": "12h",
    "1d": "1d", "3d": "3d", "1w": "1w"
}


async def fetch_candles(hyp: Hyperliquid, ticker: str, timeframe: str, num_bars: int = 300):
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


async def main(ticker: str, timeframe: str = "1h", fast: int = 20, slow: int = 50):
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
    print(f"EMA CROSSOVER - {ticker}")
    print("=" * 65)
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  Timeframe:     {timeframe}")
    print(f"  Settings:      Fast EMA={fast}, Slow EMA={slow}")
    print()

    # Calculate MA crossover
    closes = await fetch_candles(hyp, ticker, timeframe, num_bars=slow * 3)

    if closes is None or len(closes) < slow:
        await hyp.cleanup()
        print("[ERROR] Insufficient data for MA calculation")
        return

    ma_data = calculate_ma_crossover(closes, fast, slow)

    if not ma_data:
        print("[ERROR] Failed to calculate MAs")
        return

    signal = get_ma_signal(ma_data)

    print("MOVING AVERAGE ANALYSIS:")
    print("-" * 65)
    print(f"  Fast EMA ({fast}):  ${ma_data['fast_ma']:>12,.2f}")
    print(f"  Slow EMA ({slow}):  ${ma_data['slow_ma']:>12,.2f}")
    print(f"  Spread:        ${ma_data['spread']:>12,.2f} ({ma_data['spread_pct']:+.2f}%)")
    print()
    print(f"  Trend:         {ma_data['trend']}")
    print(f"  Price Position: {ma_data['price_position'].replace('_', ' ').title()}")
    print()

    if ma_data['crossover']:
        print(f"  ** {ma_data['crossover_name'].upper()} DETECTED **")
        print()

    print(f"  Signal:        {signal['signal']}")
    print(f"  Strength:      {signal['strength']}%")
    print()

    # Visual representation
    print("PRICE vs MAs:")
    print("-" * 65)

    prices = [ma_data['slow_ma'], ma_data['fast_ma'], ma_data['current_price']]
    min_p = min(prices)
    max_p = max(prices)
    range_p = max_p - min_p if max_p > min_p else 1

    def pos(p):
        return int((p - min_p) / range_p * 40)

    line = [" "] * 41
    slow_pos = pos(ma_data['slow_ma'])
    fast_pos = pos(ma_data['fast_ma'])
    price_pos = pos(ma_data['current_price'])

    line[slow_pos] = "S"
    line[fast_pos] = "F"
    line[price_pos] = "*"

    print(f"  [{''.join(line)}]")
    print(f"  S=Slow EMA  F=Fast EMA  *=Price")
    print()

    # Multi-period EMAs
    print("MULTIPLE EMAs:")
    print("-" * 65)
    periods = [9, 20, 50, 100, 200]
    print(f"  {'Period':>6}  {'EMA':>14}  {'vs Price':>10}  {'Status'}")
    print("-" * 65)

    for period in periods:
        if len(closes) >= period:
            ema = calculate_ema(closes, period)
            diff_pct = (current_price - ema) / ema * 100 if ema > 0 else 0
            status = "Above" if current_price > ema else "Below"
            print(f"  {period:>6}  ${ema:>12,.2f}  {diff_pct:>+9.2f}%  {status}")

    print()

    # Multi-timeframe MA
    print("MULTI-TIMEFRAME TREND:")
    print("-" * 65)
    print(f"  {'TF':>4}  {'Fast EMA':>12}  {'Slow EMA':>12}  {'Trend':>10}  {'Cross'}")
    print("-" * 65)

    timeframes = ["15m", "1h", "4h", "1d"]
    for tf in timeframes:
        tf_closes = await fetch_candles(hyp, ticker, tf, num_bars=slow * 3)
        if tf_closes is not None and len(tf_closes) >= slow:
            tf_ma = calculate_ma_crossover(tf_closes, fast, slow)
            if tf_ma:
                cross_str = tf_ma['crossover_name'] if tf_ma['crossover'] else "-"
                print(f"  {tf:>4}  ${tf_ma['fast_ma']:>10,.2f}  ${tf_ma['slow_ma']:>10,.2f}  {tf_ma['trend']:>10}  {cross_str}")

    print("=" * 65)
    await hyp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"
    fast = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    slow = int(sys.argv[4]) if len(sys.argv) > 4 else 50

    asyncio.run(main(ticker, timeframe, fast, slow))
