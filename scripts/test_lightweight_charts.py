#!/usr/bin/env python3
"""
Test lightweight-charts-python library for trade setup visualization.

This tests:
1. Basic candlestick chart
2. Horizontal lines (for entry, SL, TP)
3. Markers
4. Screenshot/export capability
"""

import os
import sys
import asyncio
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lightweight_charts import Chart
from quantpylib.wrappers.hyperliquid import Hyperliquid

INTERVAL_MS = {
    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
    '1h': 60 * 60 * 1000, '4h': 4 * 60 * 60 * 1000, '1d': 24 * 60 * 60 * 1000,
}


async def fetch_candles(ticker: str, timeframe: str = "1h", num_bars: int = 100):
    """Fetch candle data from Hyperliquid."""
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    try:
        now = int(time.time() * 1000)
        interval_ms = INTERVAL_MS.get(timeframe, 60 * 60 * 1000)
        start = now - (num_bars * interval_ms)

        candles = await hyp.candle_historical(
            ticker=ticker,
            interval=timeframe,
            start=start,
            end=now
        )

        if not candles:
            print(f"[ERROR] No data for {ticker}")
            return None

        # Convert to DataFrame with required columns
        df = pd.DataFrame(candles)
        df['time'] = pd.to_datetime(df['t'], unit='ms')
        df['open'] = df['o'].astype(float)
        df['high'] = df['h'].astype(float)
        df['low'] = df['l'].astype(float)
        df['close'] = df['c'].astype(float)
        df['volume'] = df['v'].astype(float)

        return df[['time', 'open', 'high', 'low', 'close', 'volume']]

    finally:
        await hyp.cleanup()


def test_basic_chart():
    """Test 1: Basic candlestick chart with horizontal lines."""
    print("Fetching BTC data...")
    df = asyncio.run(fetch_candles('BTC', '1h', 100))

    if df is None:
        print("Failed to fetch data")
        return

    print(f"Got {len(df)} candles")
    print(df.head())

    # Create chart
    print("\nCreating chart...")
    chart = Chart()

    # Set the data
    chart.set(df)

    # Get current price for reference
    current_price = df['close'].iloc[-1]
    print(f"Current price: ${current_price:,.2f}")

    # Add horizontal lines for trade setup
    entry_price = 98000
    stop_loss = 102000
    take_profit_1 = 95000
    take_profit_2 = 92000

    print("\nAdding horizontal lines...")

    # Entry line (white)
    chart.horizontal_line(
        price=entry_price,
        color='white',
        width=2,
        style='solid',
        text='ENTRY $98,000'
    )

    # Stop loss (red)
    chart.horizontal_line(
        price=stop_loss,
        color='#FF5252',
        width=2,
        style='solid',
        text='SL $102,000'
    )

    # Take profit 1 (green)
    chart.horizontal_line(
        price=take_profit_1,
        color='#00C853',
        width=1,
        style='dashed',
        text='TP1 $95,000'
    )

    # Take profit 2 (green)
    chart.horizontal_line(
        price=take_profit_2,
        color='#00C853',
        width=1,
        style='dashed',
        text='TP2 $92,000'
    )

    print("\nShowing chart (close window to continue)...")
    chart.show(block=True)


def test_with_screenshot():
    """Test 2: Chart with screenshot capability."""
    print("Fetching ETH data...")
    df = asyncio.run(fetch_candles('ETH', '4h', 80))

    if df is None:
        print("Failed to fetch data")
        return

    print(f"Got {len(df)} candles")

    # Create chart with screenshot callback
    chart = Chart()
    chart.set(df)

    # Trade setup
    entry = 3200
    sl = 3400
    tp1 = 3000
    tp2 = 2800

    chart.horizontal_line(price=entry, color='white', width=2, text='ENTRY')
    chart.horizontal_line(price=sl, color='#FF5252', width=2, text='SL')
    chart.horizontal_line(price=tp1, color='#00C853', width=1, style='dashed', text='TP1')
    chart.horizontal_line(price=tp2, color='#00C853', width=1, style='dashed', text='TP2')

    # Check if screenshot method exists
    print("\nChart methods available:")
    methods = [m for m in dir(chart) if not m.startswith('_')]
    for m in methods:
        print(f"  - {m}")

    print("\nShowing chart...")
    chart.show(block=True)


def test_markers():
    """Test 3: Chart with markers for trade entry/exit points."""
    print("Fetching SOL data...")
    df = asyncio.run(fetch_candles('SOL', '1h', 60))

    if df is None:
        print("Failed to fetch data")
        return

    print(f"Got {len(df)} candles")

    chart = Chart()
    chart.set(df)

    # Add entry marker at a specific time
    entry_time = df['time'].iloc[-10]
    entry_price = df['close'].iloc[-10]

    print(f"\nAdding marker at {entry_time}, price ${entry_price:.2f}")

    # Try adding a marker
    try:
        chart.marker(
            time=entry_time,
            position='below',
            shape='arrowUp',
            color='#00C853',
            text='LONG Entry'
        )
        print("Marker added successfully")
    except Exception as e:
        print(f"Marker error: {e}")

    # Add horizontal lines
    chart.horizontal_line(price=entry_price, color='white', width=2, text='Entry')
    chart.horizontal_line(price=entry_price * 0.95, color='#FF5252', width=1, text='SL -5%')
    chart.horizontal_line(price=entry_price * 1.10, color='#00C853', width=1, text='TP +10%')

    print("\nShowing chart...")
    chart.show(block=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test lightweight-charts-python")
    parser.add_argument('test', choices=['basic', 'screenshot', 'markers', 'all'],
                       default='basic', nargs='?',
                       help='Which test to run')

    args = parser.parse_args()

    if args.test == 'basic' or args.test == 'all':
        print("=" * 50)
        print("TEST 1: Basic Chart with Horizontal Lines")
        print("=" * 50)
        test_basic_chart()

    if args.test == 'screenshot' or args.test == 'all':
        print("\n" + "=" * 50)
        print("TEST 2: Chart Methods (Screenshot)")
        print("=" * 50)
        test_with_screenshot()

    if args.test == 'markers' or args.test == 'all':
        print("\n" + "=" * 50)
        print("TEST 3: Chart with Markers")
        print("=" * 50)
        test_markers()
