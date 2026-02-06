#!/usr/bin/env python3
"""
Price Chart for Hyperliquid

Generates a price chart with optional indicators (EMA, Bollinger Bands).

USAGE:
  python hyp_chart_price.py <ticker> [timeframe] [bars]

EXAMPLES:
  python hyp_chart_price.py BTC              # BTC 1h, 100 bars
  python hyp_chart_price.py ETH 4h           # ETH 4h, 100 bars
  python hyp_chart_price.py SOL 1d 200       # SOL daily, 200 bars
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
    setup_dark_style, COLORS, CHART_DIR, save_chart,
    calculate_ema, calculate_bollinger, format_price
)

INTERVAL_MS = {
    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000, '1h': 60 * 60 * 1000, '2h': 2 * 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000, '8h': 8 * 60 * 60 * 1000, '12h': 12 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000, '3d': 3 * 24 * 60 * 60 * 1000, '1w': 7 * 24 * 60 * 60 * 1000,
}


async def chart_price(ticker: str, timeframe: str = "1h", num_bars: int = 100):
    """Generate price chart with EMAs and Bollinger Bands."""

    ticker = ticker.upper()
    print(f"Generating price chart for {ticker} ({timeframe}, {num_bars} bars)...")

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

        if not candles or len(candles) < 20:
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
        ema20 = calculate_ema(closes, 20)
        ema50 = calculate_ema(closes, 50) if len(closes) >= 50 else None
        bb_upper, bb_middle, bb_lower = calculate_bollinger(closes, 20, 2)

        # Create chart
        setup_dark_style()
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), height_ratios=[3, 1], sharex=True)
        fig.suptitle(f'{ticker} - {timeframe}', fontsize=14, fontweight='bold')

        # Price chart
        ax1.fill_between(dates, bb_lower, bb_upper, alpha=0.1, color=COLORS['blue'], label='Bollinger Bands')
        ax1.plot(dates, closes, color=COLORS['text'], linewidth=1.5, label='Price')
        ax1.plot(dates, ema20, color=COLORS['orange'], linewidth=1, label='EMA 20', alpha=0.8)

        if ema50 is not None:
            ax1.plot(dates, ema50, color=COLORS['purple'], linewidth=1, label='EMA 50', alpha=0.8)

        ax1.plot(dates, bb_middle, color=COLORS['blue'], linewidth=0.8, linestyle='--', alpha=0.5)

        # Color code candles
        for i in range(len(dates)):
            color = COLORS['green'] if closes[i] >= opens[i] else COLORS['red']
            ax1.plot([dates[i], dates[i]], [lows[i], highs[i]], color=color, linewidth=0.5, alpha=0.5)

        ax1.set_ylabel('Price')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)

        # Current price annotation
        current_price = closes[-1]
        ax1.axhline(y=current_price, color=COLORS['text'], linestyle=':', alpha=0.5)
        ax1.annotate(
            format_price(current_price),
            xy=(dates[-1], current_price),
            xytext=(10, 0),
            textcoords='offset points',
            fontsize=10,
            color=COLORS['text'],
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['background'], edgecolor=COLORS['grid'])
        )

        # Volume chart
        colors = [COLORS['green'] if closes[i] >= opens[i] else COLORS['red'] for i in range(len(closes))]
        ax2.bar(dates, volumes, color=colors, alpha=0.7, width=interval_ms / (24 * 60 * 60 * 1000))
        ax2.set_ylabel('Volume')
        ax2.grid(True, alpha=0.3)

        # Volume average
        vol_ma = np.convolve(volumes, np.ones(20)/20, mode='valid')
        vol_ma = np.concatenate([np.full(19, np.nan), vol_ma])
        ax2.plot(dates, vol_ma, color=COLORS['orange'], linewidth=1, label='Vol MA(20)')

        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45)

        plt.tight_layout()

        # Save chart
        filepath = save_chart(fig, f"price_{timeframe}", ticker)
        print(f"Chart saved: {filepath}")

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

    asyncio.run(chart_price(ticker, timeframe, num_bars))
