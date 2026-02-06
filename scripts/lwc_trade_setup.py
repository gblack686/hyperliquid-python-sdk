#!/usr/bin/env python3
"""
Lightweight Charts - Trade Setup Visualization

Creates a TradingView-style chart with trade setup:
- Entry, Stop Loss, Take Profit horizontal lines
- Entry marker
- Dark theme

USAGE:
  python lwc_trade_setup.py BTC SHORT --entry 98000 --stop 102000
  python lwc_trade_setup.py ETH LONG --entry 3200 --stop 3000 --target 15
"""

import os
import sys
import asyncio
import time
import argparse
import pandas as pd
from datetime import datetime
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


def calculate_scaled_exits(entry: float, direction: str, target_pct: float = 10.0, num_levels: int = 5):
    """Calculate take profit levels."""
    step = (target_pct / 100) / num_levels
    if direction.upper() == 'LONG':
        return [entry * (1 + step * (i + 1)) for i in range(num_levels)]
    else:
        return [entry * (1 - step * (i + 1)) for i in range(num_levels)]


def format_price(price: float) -> str:
    """Format price for display."""
    if price >= 1000:
        return f"${price:,.0f}"
    elif price >= 1:
        return f"${price:.2f}"
    else:
        return f"${price:.4f}"


async def create_trade_chart(
    ticker: str,
    direction: str,
    entry_price: float,
    stop_loss: float,
    target_pct: float = 10.0,
    timeframe: str = "1h",
    num_bars: int = 100
):
    """Create trade setup chart using lightweight-charts."""

    ticker = ticker.upper()
    direction = direction.upper()

    print(f"\nFetching {ticker} {timeframe} data ({num_bars} bars)...")
    df = await fetch_candles(ticker, timeframe, num_bars)

    if df is None:
        print("[ERROR] Failed to fetch data")
        return None

    print(f"Got {len(df)} candles")
    current_price = df['close'].iloc[-1]
    print(f"Current price: {format_price(current_price)}")

    # Calculate TPs
    take_profits = calculate_scaled_exits(entry_price, direction, target_pct, 5)

    # Calculate R:R
    risk = abs(entry_price - stop_loss)
    reward = abs(take_profits[-1] - entry_price)
    rr = reward / risk if risk > 0 else 0

    print(f"\nTrade Setup: {ticker} {direction}")
    print(f"  Entry: {format_price(entry_price)}")
    print(f"  Stop Loss: {format_price(stop_loss)} ({abs(entry_price - stop_loss) / entry_price * 100:.1f}%)")
    print(f"  Take Profits:")
    for i, tp in enumerate(take_profits):
        print(f"    TP{i+1}: {format_price(tp)}")
    print(f"  Risk:Reward = {rr:.1f}:1")

    # Create chart
    print("\nCreating chart...")

    chart = Chart(
        width=1400,
        height=900,
        title=f'{ticker} {direction} Trade Setup - {timeframe}'
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

    # Candlestick colors
    chart.candle_style(
        up_color='#00C853',
        down_color='#FF5252',
        wick_up_color='#00C853',
        wick_down_color='#FF5252'
    )

    # Set data
    chart.set(df)

    # Legend with R:R info
    chart.legend(visible=True, font_size=12)

    # Watermark
    chart.watermark(f'{direction} | R:R {rr:.1f}:1', color='rgba(255, 255, 255, 0.1)')

    # ===== HORIZONTAL LINES =====

    # Entry line (white, bold)
    entry_line = chart.horizontal_line(
        price=entry_price,
        color='#FFFFFF',
        width=3,
        style='solid',
        text=f'ENTRY {format_price(entry_price)}',
        axis_label_visible=True
    )

    # Stop loss line (red)
    sl_line = chart.horizontal_line(
        price=stop_loss,
        color='#FF5252',
        width=2,
        style='solid',
        text=f'SL {format_price(stop_loss)}',
        axis_label_visible=True
    )

    # Take profit lines (green, dashed)
    for i, tp in enumerate(take_profits):
        chart.horizontal_line(
            price=tp,
            color='#00C853',
            width=1,
            style='dashed',
            text=f'TP{i+1} {format_price(tp)}',
            axis_label_visible=True
        )

    # ===== MARKERS =====

    # Entry marker at current time
    current_time = df['time'].iloc[-1]
    marker_position = 'below' if direction == 'LONG' else 'above'
    marker_shape = 'arrowUp' if direction == 'LONG' else 'arrowDown'
    marker_color = '#00C853' if direction == 'LONG' else '#FF5252'

    try:
        chart.marker(
            time=current_time,
            position=marker_position,
            shape=marker_shape,
            color=marker_color,
            text=f'{direction} Entry'
        )
    except Exception as e:
        print(f"  Marker note: {e}")

    # ===== PRICE SCALE =====
    chart.price_scale(auto_scale=True)
    chart.time_scale(right_offset=20)

    print("\n" + "=" * 50)
    print("Chart window opening...")
    print("Press Ctrl+S in the chart window to save screenshot")
    print("Close window when done")
    print("=" * 50)

    # Show chart (use async version since we're in async context)
    await chart.show_async()

    return chart


def main():
    parser = argparse.ArgumentParser(
        description="Lightweight Charts Trade Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('ticker', help='Trading pair (e.g., BTC, ETH)')
    parser.add_argument('direction', choices=['LONG', 'SHORT', 'long', 'short'])
    parser.add_argument('--entry', type=float, required=True, help='Entry price')
    parser.add_argument('--stop', type=float, required=True, help='Stop loss price')
    parser.add_argument('--target', type=float, default=10.0, help='Target %% for TPs (default: 10)')
    parser.add_argument('--timeframe', '-t', default='1h',
                       choices=['1m', '5m', '15m', '1h', '4h', '1d'])
    parser.add_argument('--bars', '-b', type=int, default=100)

    args = parser.parse_args()

    # Validate stop
    if args.direction.upper() == 'LONG' and args.stop >= args.entry:
        print("[ERROR] For LONG: Stop must be BELOW entry")
        sys.exit(1)
    if args.direction.upper() == 'SHORT' and args.stop <= args.entry:
        print("[ERROR] For SHORT: Stop must be ABOVE entry")
        sys.exit(1)

    asyncio.run(create_trade_chart(
        ticker=args.ticker,
        direction=args.direction,
        entry_price=args.entry,
        stop_loss=args.stop,
        target_pct=args.target,
        timeframe=args.timeframe,
        num_bars=args.bars
    ))


if __name__ == "__main__":
    main()
