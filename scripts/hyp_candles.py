#!/usr/bin/env python
"""Get historical candle data from Hyperliquid."""
import os
import sys
import asyncio
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

# Interval to milliseconds mapping
INTERVAL_MS = {
    '1m': 60 * 1000,
    '5m': 5 * 60 * 1000,
    '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000,
    '1h': 60 * 60 * 1000,
    '2h': 2 * 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000,
    '8h': 8 * 60 * 60 * 1000,
    '12h': 12 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000,
    '3d': 3 * 24 * 60 * 60 * 1000,
    '1w': 7 * 24 * 60 * 60 * 1000,
}

async def get_candles(ticker, interval='1h', num_bars=24):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    ticker = ticker.upper()

    # Calculate time range
    now = int(time.time() * 1000)
    interval_ms = INTERVAL_MS.get(interval, 60 * 60 * 1000)
    start = now - (num_bars * interval_ms)

    print("=" * 75)
    print(f"CANDLES: {ticker} ({interval})")
    print("=" * 75)

    try:
        candles = await hyp.candle_historical(
            ticker=ticker,
            interval=interval,
            start=start,
            end=now
        )

        if not candles or len(candles) == 0:
            print("No candle data found.")
            await hyp.cleanup()
            return

        print(f"{'Time':19} {'Open':>12} {'High':>12} {'Low':>12} {'Close':>12} {'Volume':>12}")
        print("-" * 85)

        for candle in candles[-num_bars:]:
            ts = candle.get('t', 0)
            o = float(candle.get('o', 0))
            h = float(candle.get('h', 0))
            l = float(candle.get('l', 0))
            c = float(candle.get('c', 0))
            v = float(candle.get('v', 0))

            try:
                dt = datetime.fromtimestamp(ts / 1000)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                time_str = str(ts)

            print(f"{time_str:19} ${o:>10,.2f} ${h:>10,.2f} ${l:>10,.2f} ${c:>10,.2f} {v:>12,.2f}")

        # Summary
        if len(candles) > 0:
            first_close = float(candles[0].get('c', 0))
            last_close = float(candles[-1].get('c', 0))
            change = ((last_close - first_close) / first_close * 100) if first_close > 0 else 0
            high = max(float(c.get('h', 0)) for c in candles)
            low = min(float(c.get('l', 0)) for c in candles)

            print("-" * 85)
            print(f"Period: {len(candles)} bars | Change: {change:+.2f}% | High: ${high:,.2f} | Low: ${low:,.2f}")

    except Exception as e:
        print(f"Error fetching candles: {e}")

    print("=" * 75)
    await hyp.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hyp_candles.py <ticker> [interval] [num_bars]")
        print("  Intervals: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 3d, 1w")
        sys.exit(1)

    ticker = sys.argv[1]
    interval = sys.argv[2] if len(sys.argv) > 2 else '1h'
    num_bars = int(sys.argv[3]) if len(sys.argv) > 3 else 24

    asyncio.run(get_candles(ticker, interval, num_bars))
