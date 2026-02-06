#!/usr/bin/env python3
"""
Trade Setup Chart for Hyperliquid

Generates a candlestick chart with trade setup visualization:
- Risk/Reward boxes (red stop loss, green take profit zones)
- Scaled entry levels (5 dashed blue lines)
- Scaled exit levels (5 dashed green lines)
- Entry price marker (bold white line)
- R:R ratio annotation

USAGE:
  python hyp_chart_trade_setup.py <ticker> <direction> --entry <price> --stop <price> [options]

EXAMPLES:
  python hyp_chart_trade_setup.py BTC LONG --entry 95000 --stop 92000
  python hyp_chart_trade_setup.py ETH SHORT --entry 3200 --stop 3400 --spread 3 --target 15
  python hyp_chart_trade_setup.py SOL LONG --entry 180 --stop 170 --timeframe 4h --bars 200

OPTIONS:
  --entry      Entry price (required)
  --stop       Stop loss price (required)
  --spread     Entry spread percentage for scaled entries (default: 2%)
  --target     Target percentage for scaled exits (default: 10%)
  --timeframe  Chart timeframe: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)
  --bars       Number of candles to display (default: 100)
  --leverage   Position leverage for display (default: 10)
  --size       Position size for display (optional)
"""

import os
import sys
import asyncio
import time
import argparse
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quantpylib.wrappers.hyperliquid import Hyperliquid
from chart_utils import (
    setup_dark_style, COLORS, save_chart, format_price, plot_candlestick,
    TradeSetup, calculate_scaled_entries, calculate_scaled_exits, draw_trade_setup
)

INTERVAL_MS = {
    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000, '1h': 60 * 60 * 1000, '2h': 2 * 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000, '8h': 8 * 60 * 60 * 1000, '12h': 12 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000, '3d': 3 * 24 * 60 * 60 * 1000, '1w': 7 * 24 * 60 * 60 * 1000,
}


async def chart_trade_setup(
    ticker: str,
    direction: str,
    entry_price: float,
    stop_price: float,
    spread_pct: float = 2.0,
    target_pct: float = 10.0,
    timeframe: str = "1h",
    num_bars: int = 100,
    leverage: int = 10,
    size: float = 0
):
    """Generate trade setup chart with entry/exit visualization."""

    ticker = ticker.upper()
    direction = direction.upper()

    if direction not in ('LONG', 'SHORT'):
        print(f"[ERROR] Direction must be LONG or SHORT, got: {direction}")
        return None

    print(f"Generating trade setup chart for {ticker} {direction}...")
    print(f"  Entry: {format_price(entry_price)}")
    print(f"  Stop: {format_price(stop_price)}")
    print(f"  Spread: {spread_pct}% | Target: {target_pct}%")

    # Calculate scaled levels
    scaled_entries = calculate_scaled_entries(entry_price, direction, spread_pct, 5)
    scaled_exits = calculate_scaled_exits(entry_price, direction, target_pct, 5)

    # Create TradeSetup
    setup = TradeSetup(
        ticker=ticker,
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_price,
        scaled_entries=scaled_entries,
        scaled_exits=scaled_exits,
        leverage=leverage,
        size=size,
        timestamp=datetime.now()
    )

    # Fetch candle data
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

        if not candles or len(candles) < 20:
            print(f"[ERROR] Insufficient data for {ticker}")
            return None

        # Extract data
        dates = [datetime.fromtimestamp(c['t'] / 1000) for c in candles]
        opens = np.array([float(c['o']) for c in candles])
        highs = np.array([float(c['h']) for c in candles])
        lows = np.array([float(c['l']) for c in candles])
        closes = np.array([float(c['c']) for c in candles])

        # Create chart
        setup_dark_style()
        fig, ax = plt.subplots(figsize=(16, 10))
        fig.patch.set_facecolor(COLORS['background'])
        ax.set_facecolor(COLORS['background'])

        # Title - clean, muted
        title = f'{ticker} {direction} Trade Setup - {timeframe}'
        if leverage:
            title += f' ({leverage}x)'
        fig.suptitle(title, fontsize=13, fontweight='bold', color=COLORS['text'])

        # Plot candlesticks
        candle_width = interval_ms / (24 * 60 * 60 * 1000) * 0.8
        plot_candlestick(ax, dates, opens, highs, lows, closes, width=candle_width)

        # Draw trade setup overlay (spans full chart width via axhspan)
        draw_trade_setup(ax, setup, dates[-1], dates[-1],
                         show_boxes=True, show_levels=True, show_labels=True)

        # Y-axis: fit candles + all trade levels
        all_prices = list(highs) + list(lows) + [entry_price, stop_price] + scaled_exits
        price_min = min(all_prices) * 0.98
        price_max = max(all_prices) * 1.02
        ax.set_ylim(price_min, price_max)

        # X-axis: small margin for right-edge badges only
        time_span = mdates.date2num(dates[-1]) - mdates.date2num(dates[0])
        x_margin = time_span * 0.08
        ax.set_xlim(mdates.date2num(dates[0]), mdates.date2num(dates[-1]) + x_margin)

        # Clean axis formatting
        ax.set_ylabel('Price', fontsize=10, color=COLORS['text_muted'])
        ax.set_xlabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=0, fontsize=8)
        ax.tick_params(axis='both', colors=COLORS['text_muted'], length=0)
        ax.grid(True, alpha=0.6, linewidth=0.5)

        # Current price dotted line + right-edge badge
        current_price = closes[-1]
        ax.axhline(y=current_price, color=COLORS['text_muted'],
                    linestyle=':', linewidth=0.7, alpha=0.5)
        ax.annotate(
            f"Current: {format_price(current_price)}",
            xy=(1.01, current_price),
            xycoords=('axes fraction', 'data'),
            fontsize=8,
            color=COLORS['text_muted']
        )

        # Trade info box - position based on direction to avoid overlapping zones
        risk = abs(entry_price - stop_price)
        reward = abs(scaled_exits[-1] - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        risk_pct = risk / entry_price * 100

        info_text = (
            f"Entry: {format_price(entry_price)}\n"
            f"Stop Loss: {format_price(stop_price)} ({risk_pct:.1f}%)\n"
            f"Target 1: {format_price(scaled_exits[0])}\n"
            f"Target 5: {format_price(scaled_exits[-1])}\n"
            f"Risk:Reward: {rr_ratio:.1f}:1"
        )
        if size > 0:
            info_text += f"\nSize: {size}"
        if leverage > 0:
            info_text += f"\nLeverage: {leverage}x"

        # Smart box placement: upper-left for LONG (SL below), lower-left for SHORT (SL above)
        box_y = 0.98 if direction == 'LONG' else 0.02
        box_va = 'top' if direction == 'LONG' else 'bottom'
        ax.text(
            0.02, box_y, info_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment=box_va,
            color=COLORS['text'],
            bbox=dict(
                boxstyle='round,pad=0.5',
                facecolor=COLORS['background'],
                edgecolor=COLORS['grid'],
                alpha=0.92
            )
        )

        plt.tight_layout()

        # Save chart
        filepath = save_chart(fig, f"trade_setup_{direction.lower()}_{timeframe}", ticker)
        print(f"\nChart saved: {filepath}")

        # Print summary
        print(f"\n{'='*50}")
        print(f"TRADE SETUP: {ticker} {direction}")
        print(f"{'='*50}")
        print(f"Entry Price: {format_price(entry_price)}")
        print(f"Stop Loss: {format_price(stop_price)} ({risk_pct:.1f}%)")
        print(f"\nScaled Entries:")
        for i, e in enumerate(scaled_entries):
            print(f"  E{i+1}: {format_price(e)}")
        print(f"\nScaled Exits:")
        for i, tp in enumerate(scaled_exits):
            tp_pct = abs(tp - entry_price) / entry_price * 100
            print(f"  TP{i+1}: {format_price(tp)} (+{tp_pct:.1f}%)")
        print(f"\nRisk:Reward = {rr_ratio:.1f}:1")
        print(f"{'='*50}")

        return filepath

    except Exception as e:
        print(f"[ERROR] Chart generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        await hyp.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="Generate trade setup chart with entry/exit visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('ticker', help='Trading pair (e.g., BTC, ETH, SOL)')
    parser.add_argument('direction', choices=['LONG', 'SHORT', 'long', 'short'],
                       help='Trade direction')
    parser.add_argument('--entry', type=float, required=True,
                       help='Entry price')
    parser.add_argument('--stop', type=float, required=True,
                       help='Stop loss price')
    parser.add_argument('--spread', type=float, default=2.0,
                       help='Entry spread percentage for scaled entries (default: 2%%)')
    parser.add_argument('--target', type=float, default=10.0,
                       help='Target percentage for scaled exits (default: 10%%)')
    parser.add_argument('--timeframe', '-t', default='1h',
                       choices=['1m', '5m', '15m', '30m', '1h', '2h', '4h', '8h', '12h', '1d', '3d', '1w'],
                       help='Chart timeframe (default: 1h)')
    parser.add_argument('--bars', '-b', type=int, default=100,
                       help='Number of candles to display (default: 100)')
    parser.add_argument('--leverage', '-l', type=int, default=10,
                       help='Position leverage for display (default: 10)')
    parser.add_argument('--size', '-s', type=float, default=0,
                       help='Position size for display')

    args = parser.parse_args()

    # Validate stop loss direction
    if args.direction.upper() == 'LONG' and args.stop >= args.entry:
        print("[ERROR] For LONG: Stop loss must be BELOW entry price")
        sys.exit(1)
    if args.direction.upper() == 'SHORT' and args.stop <= args.entry:
        print("[ERROR] For SHORT: Stop loss must be ABOVE entry price")
        sys.exit(1)

    asyncio.run(chart_trade_setup(
        ticker=args.ticker,
        direction=args.direction,
        entry_price=args.entry,
        stop_price=args.stop,
        spread_pct=args.spread,
        target_pct=args.target,
        timeframe=args.timeframe,
        num_bars=args.bars,
        leverage=args.leverage,
        size=args.size
    ))


if __name__ == "__main__":
    main()
