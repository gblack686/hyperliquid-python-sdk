#!/usr/bin/env python3
"""
Technical Analysis Chart for Hyperliquid

Generates a multi-panel chart with Price, RSI, MACD, and Volume.

USAGE:
  python hyp_chart_ta.py <ticker> [timeframe] [bars]

EXAMPLES:
  python hyp_chart_ta.py BTC              # BTC 1h, 100 bars
  python hyp_chart_ta.py ETH 4h           # ETH 4h, 100 bars
  python hyp_chart_ta.py SOL 1d 200       # SOL daily, 200 bars
"""

import os
import sys
import asyncio
import time
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from quantpylib.wrappers.hyperliquid import Hyperliquid
from chart_utils import (
    setup_dark_style, COLORS, save_chart,
    calculate_rsi, calculate_macd, calculate_ema, calculate_bollinger, format_price,
    TradeSetup, draw_trade_setup
)

INTERVAL_MS = {
    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000, '1h': 60 * 60 * 1000, '2h': 2 * 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000, '8h': 8 * 60 * 60 * 1000, '12h': 12 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000, '3d': 3 * 24 * 60 * 60 * 1000, '1w': 7 * 24 * 60 * 60 * 1000,
}


async def chart_ta(ticker: str, timeframe: str = "1h", num_bars: int = 100, trade_setup: TradeSetup = None):
    """Generate technical analysis multi-panel chart.

    Args:
        ticker: Trading pair symbol (e.g., 'BTC', 'ETH')
        timeframe: Chart timeframe (e.g., '1h', '4h', '1d')
        num_bars: Number of candles to fetch
        trade_setup: Optional TradeSetup for overlay visualization
    """

    ticker = ticker.upper()
    print(f"Generating TA chart for {ticker} ({timeframe}, {num_bars} bars)...")

    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    try:
        # Fetch candles
        now = int(time.time() * 1000)
        interval_ms = INTERVAL_MS.get(timeframe, 60 * 60 * 1000)
        start = now - (num_bars * interval_ms)

        candles = await hyp.candle_historical(
            ticker=ticker,
            interval=timeframe,
            start=start,
            end=now
        )

        if not candles or len(candles) < 30:
            print(f"[ERROR] Insufficient data for {ticker}")
            return None

        # Extract data
        dates = [datetime.fromtimestamp(c['t'] / 1000) for c in candles]
        opens = np.array([float(c['o']) for c in candles])
        highs = np.array([float(c['h']) for c in candles])
        lows = np.array([float(c['l']) for c in candles])
        closes = np.array([float(c['c']) for c in candles])
        volumes = np.array([float(c['v']) for c in candles])

        # Calculate indicators
        rsi = calculate_rsi(closes, 14)
        macd_line, signal_line, histogram = calculate_macd(closes)
        ema20 = calculate_ema(closes, 20)
        ema50 = calculate_ema(closes, 50) if len(closes) >= 50 else None
        bb_upper, bb_middle, bb_lower = calculate_bollinger(closes, 20, 2)

        # Create chart
        setup_dark_style()
        fig, axes = plt.subplots(4, 1, figsize=(14, 12), height_ratios=[3, 1, 1, 1], sharex=True)
        fig.suptitle(f'{ticker} Technical Analysis - {timeframe}', fontsize=14, fontweight='bold')

        # Panel 1: Price with EMAs and Bollinger Bands
        ax1 = axes[0]
        ax1.fill_between(dates, bb_lower, bb_upper, alpha=0.1, color=COLORS['blue'])
        ax1.plot(dates, closes, color=COLORS['text'], linewidth=1.5, label='Price')
        ax1.plot(dates, ema20, color=COLORS['orange'], linewidth=1, label='EMA 20')
        if ema50 is not None:
            ax1.plot(dates, ema50, color=COLORS['purple'], linewidth=1, label='EMA 50')
        ax1.plot(dates, bb_middle, color=COLORS['blue'], linewidth=0.8, linestyle='--', alpha=0.5)

        # Highlight candles
        for i in range(len(dates)):
            color = COLORS['green'] if closes[i] >= opens[i] else COLORS['red']
            ax1.plot([dates[i], dates[i]], [lows[i], highs[i]], color=color, linewidth=0.5, alpha=0.5)

        ax1.set_ylabel('Price')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)

        # Current price
        current = closes[-1]
        ax1.axhline(y=current, color=COLORS['text'], linestyle=':', alpha=0.5)
        ax1.annotate(format_price(current), xy=(1.01, current), xycoords=('axes fraction', 'data'),
                    fontsize=9, color=COLORS['text'])

        # Trade setup overlay (if provided)
        if trade_setup:
            # Draw setup on last 40% of chart
            setup_start_idx = int(len(dates) * 0.6)
            x_start = dates[setup_start_idx]
            x_end = dates[-1]
            draw_trade_setup(ax1, trade_setup, x_start, x_end, show_boxes=True, show_levels=True, show_labels=True)

            # Extend y-axis to include all trade levels
            all_prices = list(highs) + list(lows)
            if trade_setup.stop_loss:
                all_prices.append(trade_setup.stop_loss)
            if trade_setup.scaled_exits:
                all_prices.extend(trade_setup.scaled_exits)
            if trade_setup.entry_price:
                all_prices.append(trade_setup.entry_price)
            ax1.set_ylim(min(all_prices) * 0.98, max(all_prices) * 1.02)

        # Panel 2: RSI
        ax2 = axes[1]
        ax2.plot(dates, rsi, color=COLORS['purple'], linewidth=1)
        ax2.axhline(y=70, color=COLORS['red'], linestyle='--', alpha=0.5)
        ax2.axhline(y=30, color=COLORS['green'], linestyle='--', alpha=0.5)
        ax2.axhline(y=50, color=COLORS['gray'], linestyle=':', alpha=0.3)
        ax2.fill_between(dates, 70, 100, alpha=0.1, color=COLORS['red'])
        ax2.fill_between(dates, 0, 30, alpha=0.1, color=COLORS['green'])
        ax2.set_ylabel('RSI')
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)

        # RSI value annotation
        current_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50
        ax2.annotate(f'{current_rsi:.1f}', xy=(1.01, current_rsi), xycoords=('axes fraction', 'data'),
                    fontsize=9, color=COLORS['text'])

        # Panel 3: MACD
        ax3 = axes[2]
        ax3.plot(dates, macd_line, color=COLORS['blue'], linewidth=1, label='MACD')
        ax3.plot(dates, signal_line, color=COLORS['orange'], linewidth=1, label='Signal')
        ax3.axhline(y=0, color=COLORS['gray'], linestyle='-', alpha=0.3)

        # Histogram
        hist_colors = [COLORS['green'] if h >= 0 else COLORS['red'] for h in histogram]
        ax3.bar(dates, histogram, color=hist_colors, alpha=0.5, width=interval_ms / (24 * 60 * 60 * 1000))
        ax3.set_ylabel('MACD')
        ax3.legend(loc='upper left', fontsize=8)
        ax3.grid(True, alpha=0.3)

        # Panel 4: Volume
        ax4 = axes[3]
        vol_colors = [COLORS['green'] if closes[i] >= opens[i] else COLORS['red'] for i in range(len(closes))]
        ax4.bar(dates, volumes, color=vol_colors, alpha=0.7, width=interval_ms / (24 * 60 * 60 * 1000))

        # Volume MA
        vol_ma = np.convolve(volumes, np.ones(20)/20, mode='valid')
        vol_ma = np.concatenate([np.full(19, np.nan), vol_ma])
        ax4.plot(dates, vol_ma, color=COLORS['orange'], linewidth=1, label='Vol MA(20)')

        ax4.set_ylabel('Volume')
        ax4.set_xlabel('Time')
        ax4.grid(True, alpha=0.3)

        # Format x-axis
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax4.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45)

        plt.tight_layout()

        # Save chart
        filepath = save_chart(fig, f"ta_{timeframe}", ticker)
        print(f"Chart saved: {filepath}")

        # Print summary
        print()
        print(f"=== {ticker} Summary ===")
        print(f"Price: {format_price(current)}")
        print(f"RSI: {current_rsi:.1f} {'(Overbought)' if current_rsi > 70 else '(Oversold)' if current_rsi < 30 else ''}")
        print(f"MACD: {'Bullish' if macd_line[-1] > signal_line[-1] else 'Bearish'}")
        print(f"Trend: {'Bullish' if ema20[-1] > (ema50[-1] if ema50 is not None else ema20[-1]) else 'Bearish'}")

        return filepath

    except Exception as e:
        print(f"[ERROR] Chart generation failed: {e}")
        return None

    finally:
        await hyp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"
    num_bars = int(sys.argv[3]) if len(sys.argv) > 3 else 100

    asyncio.run(chart_ta(ticker, timeframe, num_bars))
