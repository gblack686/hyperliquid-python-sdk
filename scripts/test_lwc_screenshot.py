#!/usr/bin/env python3
"""
Test lightweight-charts-python with screenshot capability.
"""

import os
import sys
import asyncio
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lightweight_charts import Chart
from quantpylib.wrappers.hyperliquid import Hyperliquid

OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "charts" / "lightweight"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
            return None

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


def create_trade_setup_chart(
    ticker: str,
    direction: str,
    entry_price: float,
    stop_loss: float,
    take_profits: list,
    df: pd.DataFrame
) -> Chart:
    """Create a chart with trade setup visualization."""

    chart = Chart(
        width=1200,
        height=800,
        title=f'{ticker} {direction} Trade Setup'
    )

    # Dark theme
    chart.layout(
        background_color='#1a1a2e',
        text_color='#e0e0e0',
        font_size=12
    )

    chart.grid(
        vert_enabled=True,
        horz_enabled=True,
        color='rgba(42, 42, 78, 0.5)'
    )

    # Set candlestick data
    chart.set(df)

    # Candlestick colors
    chart.candle_style(
        up_color='#00C853',
        down_color='#FF5252',
        wick_up_color='#00C853',
        wick_down_color='#FF5252'
    )

    # Entry line (white, bold)
    chart.horizontal_line(
        price=entry_price,
        color='#FFFFFF',
        width=3,
        style='solid',
        text=f'ENTRY ${entry_price:,.0f}',
        axis_label_visible=True
    )

    # Stop loss line (red)
    chart.horizontal_line(
        price=stop_loss,
        color='#FF5252',
        width=2,
        style='solid',
        text=f'SL ${stop_loss:,.0f}',
        axis_label_visible=True
    )

    # Take profit lines (green, graduated)
    for i, tp in enumerate(take_profits):
        chart.horizontal_line(
            price=tp,
            color='#00C853',
            width=1,
            style='dashed',
            text=f'TP{i+1} ${tp:,.0f}',
            axis_label_visible=True
        )

    # Add marker at current price for entry point
    current_time = df['time'].iloc[-1]
    try:
        position = 'below' if direction.upper() == 'LONG' else 'above'
        shape = 'arrowUp' if direction.upper() == 'LONG' else 'arrowDown'
        marker_color = '#00C853' if direction.upper() == 'LONG' else '#FF5252'

        chart.marker(
            time=current_time,
            position=position,
            shape=shape,
            color=marker_color,
            text=direction.upper()
        )
    except Exception as e:
        print(f"Marker warning: {e}")

    # Add vertical span at entry time (highlight current)
    try:
        chart.vertical_span(
            start_time=current_time,
            color='rgba(255, 255, 255, 0.1)'
        )
    except Exception as e:
        print(f"Vertical span warning: {e}")

    # Legend
    chart.legend(visible=True, font_size=12)

    # Price scale configuration
    chart.price_scale(
        auto_scale=True,
        mode='normal'
    )

    return chart


async def take_screenshot_after_delay(chart: Chart, filepath: str, delay: float = 2.0):
    """Take screenshot after chart is rendered."""
    await asyncio.sleep(delay)

    try:
        img_bytes = chart.screenshot()
        with open(filepath, 'wb') as f:
            f.write(img_bytes)
        print(f"Screenshot saved: {filepath}")
        return True
    except Exception as e:
        print(f"Screenshot failed: {e}")
        return False


async def main():
    """Main test function."""
    print("=" * 60)
    print("Lightweight Charts Python - Trade Setup Test")
    print("=" * 60)

    # Fetch BTC data
    print("\nFetching BTC 1h data...")
    df = await fetch_candles('BTC', '1h', 100)

    if df is None:
        print("Failed to fetch data")
        return

    print(f"Got {len(df)} candles")
    current_price = df['close'].iloc[-1]
    print(f"Current price: ${current_price:,.2f}")

    # Trade setup parameters (SHORT example)
    direction = 'SHORT'
    entry = 98000
    sl = 102000
    tps = [96000, 94000, 92000, 90000, 88000]

    print(f"\nTrade Setup: {direction}")
    print(f"  Entry: ${entry:,}")
    print(f"  Stop Loss: ${sl:,}")
    print(f"  Take Profits: {[f'${tp:,}' for tp in tps]}")

    # Calculate R:R
    risk = abs(entry - sl)
    reward = abs(tps[-1] - entry)
    rr = reward / risk
    print(f"  Risk:Reward = {rr:.1f}:1")

    # Create chart
    print("\nCreating chart...")
    chart = create_trade_setup_chart('BTC', direction, entry, sl, tps, df)

    # Output path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"BTC_trade_setup_{timestamp}.png"

    print("\nShowing chart...")
    print("(Chart window will open - screenshot will be taken after 3 seconds)")
    print("(Close window when done)")

    # Show chart and take screenshot
    # We need to use threading or run screenshot after show
    import threading

    def delayed_screenshot():
        time.sleep(3)
        try:
            img_bytes = chart.screenshot()
            with open(output_path, 'wb') as f:
                f.write(img_bytes)
            print(f"\nScreenshot saved: {output_path}")
        except Exception as e:
            print(f"\nScreenshot error: {e}")

    # Start screenshot thread
    screenshot_thread = threading.Thread(target=delayed_screenshot)
    screenshot_thread.start()

    # Show chart (blocking)
    chart.show(block=True)

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
