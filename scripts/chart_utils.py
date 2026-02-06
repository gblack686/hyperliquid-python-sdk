#!/usr/bin/env python3
"""
Chart Utilities for Hyperliquid
Provides common charting functions and styling for consistent visual output
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

# Output directory
CHART_DIR = Path(__file__).parent.parent / "outputs" / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

# Chart styling - TradingView dark theme palette
COLORS = {
    'green': '#26a69a',         # TV teal-green (up candles)
    'red': '#ef5350',           # TV soft red (down candles)
    'blue': '#42a5f5',          # Indicator blue
    'orange': '#ffa726',        # Signal/MA orange
    'purple': '#ab47bc',        # Alt indicators
    'yellow': '#ffee58',        # Highlights
    'gray': '#787b86',          # Muted text / axes
    'background': '#131722',    # TV dark background
    'grid': '#1e222d',          # TV grid lines
    'text': '#d1d4dc',          # TV primary text
    'text_muted': '#787b86',    # TV secondary text
    'candle_up': '#26a69a',     # TV green candle
    'candle_down': '#ef5350',   # TV red candle
    'wick_up': '#26a69a',
    'wick_down': '#ef5350',
    'volume_up': '#26a69a',
    'volume_down': '#ef5350',
    'entry': '#ffffff',         # Entry line white
    'stop_loss': '#ef5350',     # SL red
    'take_profit': '#26a69a',   # TP green
    'rr_badge': '#ffa726',      # R:R badge orange
}

def setup_dark_style():
    """Configure matplotlib for TradingView-style dark theme."""
    plt.style.use('dark_background')
    plt.rcParams.update({
        'figure.facecolor': COLORS['background'],
        'axes.facecolor': COLORS['background'],
        'axes.edgecolor': COLORS['grid'],
        'axes.labelcolor': COLORS['text_muted'],
        'text.color': COLORS['text'],
        'xtick.color': COLORS['text_muted'],
        'ytick.color': COLORS['text_muted'],
        'grid.color': COLORS['grid'],
        'grid.alpha': 0.6,
        'grid.linestyle': '-',
        'grid.linewidth': 0.5,
        'legend.facecolor': COLORS['background'],
        'legend.edgecolor': COLORS['grid'],
        'font.family': 'sans-serif',
        'font.size': 10,
        'axes.titlesize': 13,
        'axes.labelsize': 10,
        'figure.dpi': 150,
    })


def format_price(price):
    """Format price with appropriate decimal places."""
    if price >= 1000:
        return f"${price:,.0f}"
    elif price >= 1:
        return f"${price:,.2f}"
    elif price >= 0.01:
        return f"${price:.4f}"
    else:
        return f"${price:.6f}"


def calculate_rsi(closes, period=14):
    """Calculate RSI from close prices. Returns array of same length as closes."""
    closes = np.array(closes)
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    # Start with period+1 NaN values to account for np.diff reducing length by 1
    rsi_values = [np.nan] * (period + 1)

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

    return np.array(rsi_values)


def calculate_macd(closes, fast=12, slow=26, signal=9):
    """Calculate MACD from close prices."""
    closes = np.array(closes)

    def ema(data, period):
        ema_values = np.zeros(len(data))
        ema_values[:period] = np.nan
        ema_values[period-1] = np.mean(data[:period])

        multiplier = 2 / (period + 1)
        for i in range(period, len(data)):
            ema_values[i] = (data[i] - ema_values[i-1]) * multiplier + ema_values[i-1]

        return ema_values

    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_bollinger(closes, period=20, std_dev=2):
    """Calculate Bollinger Bands from close prices."""
    closes = np.array(closes)

    sma = np.full(len(closes), np.nan)
    upper = np.full(len(closes), np.nan)
    lower = np.full(len(closes), np.nan)

    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        sma[i] = np.mean(window)
        std = np.std(window)
        upper[i] = sma[i] + (std_dev * std)
        lower[i] = sma[i] - (std_dev * std)

    return upper, sma, lower


def calculate_ema(closes, period):
    """Calculate EMA from close prices."""
    closes = np.array(closes)
    ema_values = np.zeros(len(closes))
    ema_values[:period] = np.nan
    ema_values[period-1] = np.mean(closes[:period])

    multiplier = 2 / (period + 1)
    for i in range(period, len(closes)):
        ema_values[i] = (closes[i] - ema_values[i-1]) * multiplier + ema_values[i-1]

    return ema_values


def plot_candlestick(ax, dates, opens, highs, lows, closes, width=0.6):
    """Plot TradingView-style candlestick chart on given axis."""
    for i in range(len(dates)):
        is_up = closes[i] >= opens[i]
        body_color = COLORS['candle_up'] if is_up else COLORS['candle_down']
        wick_color = COLORS['wick_up'] if is_up else COLORS['wick_down']

        # Wick (thin line through full range)
        ax.plot([dates[i], dates[i]], [lows[i], highs[i]],
                color=wick_color, linewidth=0.8, solid_capstyle='round')

        # Body
        body_bottom = min(opens[i], closes[i])
        body_height = abs(closes[i] - opens[i])

        if body_height > 0:
            rect = Rectangle(
                (mdates.date2num(dates[i]) - width/2, body_bottom),
                width, body_height,
                facecolor=body_color if is_up else body_color,
                edgecolor=body_color,
                linewidth=0.5
            )
            ax.add_patch(rect)
        else:
            # Doji
            ax.plot([mdates.date2num(dates[i]) - width/2,
                     mdates.date2num(dates[i]) + width/2],
                    [opens[i], closes[i]],
                    color=wick_color, linewidth=1.0)


def save_chart(fig, filename, ticker=None):
    """Save chart to file with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if ticker:
        subdir = CHART_DIR / ticker.upper()
        subdir.mkdir(parents=True, exist_ok=True)
        filepath = subdir / f"{filename}_{timestamp}.png"
    else:
        filepath = CHART_DIR / f"{filename}_{timestamp}.png"

    fig.savefig(filepath, dpi=150, bbox_inches='tight',
                facecolor=COLORS['background'], pad_inches=0.3)
    plt.close(fig)

    return str(filepath)


def create_subplot_figure(rows, cols, figsize=None):
    """Create figure with subplots using dark theme."""
    setup_dark_style()

    if figsize is None:
        figsize = (12, 4 * rows)

    fig, axes = plt.subplots(rows, cols, figsize=figsize)
    return fig, axes


# =============================================================================
# Trade Setup Visualization
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TradeSetup:
    """Trade setup for chart visualization."""
    ticker: str
    direction: str  # 'LONG' or 'SHORT'

    # Entry zone
    entry_price: float
    entry_zone_top: Optional[float] = None
    entry_zone_bottom: Optional[float] = None

    # Scaled entries (5 levels)
    scaled_entries: List[float] = field(default_factory=list)

    # Stop loss
    stop_loss: float = 0

    # Scaled exits (5 levels)
    scaled_exits: List[float] = field(default_factory=list)

    # Metadata
    leverage: int = 10
    size: float = 0
    timestamp: datetime = None


def calculate_scaled_entries(
    entry_price: float,
    direction: str,
    spread_pct: float = 2.0,
    num_levels: int = 5
) -> List[float]:
    """
    Calculate scaled entry levels.

    For LONG: entries below current price (buying dips)
    For SHORT: entries above current price (selling rallies)
    """
    if num_levels <= 1:
        return [entry_price]

    step = (spread_pct / 100) / (num_levels - 1)

    if direction.upper() == 'LONG':
        return [entry_price * (1 - step * i) for i in range(num_levels)]
    else:  # SHORT
        return [entry_price * (1 + step * i) for i in range(num_levels)]


def calculate_scaled_exits(
    entry_price: float,
    direction: str,
    target_pct: float = 10.0,
    num_levels: int = 5
) -> List[float]:
    """
    Calculate scaled exit (take profit) levels.

    For LONG: exits above entry (selling into strength)
    For SHORT: exits below entry (covering into weakness)
    """
    step = (target_pct / 100) / num_levels

    if direction.upper() == 'LONG':
        return [entry_price * (1 + step * (i + 1)) for i in range(num_levels)]
    else:  # SHORT
        return [entry_price * (1 - step * (i + 1)) for i in range(num_levels)]


def _to_num(x):
    """Convert datetime or numeric x value to matplotlib numeric."""
    if hasattr(x, 'timestamp'):
        return mdates.date2num(x)
    return x


def draw_trade_setup_box(
    ax,
    price_top: float,
    price_bottom: float,
    x_start,
    x_end,
    box_type: str,
    alpha: float = 0.15
):
    """
    Draw a TradingView-style colored zone on the chart.
    Clean fill with thin border - no heavy outlines.
    """
    box_colors = {
        'entry': COLORS['text'],
        'stop_loss': COLORS['stop_loss'],
        'take_profit': COLORS['take_profit'],
    }

    color = box_colors.get(box_type, COLORS['gray'])
    x_start_num = _to_num(x_start)
    x_end_num = _to_num(x_end)
    width = x_end_num - x_start_num

    # Main fill - subtle
    rect = Rectangle(
        (x_start_num, price_bottom),
        width,
        price_top - price_bottom,
        linewidth=0,
        edgecolor='none',
        facecolor=color,
        alpha=alpha
    )
    ax.add_patch(rect)

    # Thin border lines at top and bottom only (TV style)
    ax.hlines(price_top, x_start_num, x_end_num,
              colors=color, linewidth=0.5, alpha=0.4)
    ax.hlines(price_bottom, x_start_num, x_end_num,
              colors=color, linewidth=0.5, alpha=0.4)


def draw_scaled_levels(
    ax,
    levels: List[float],
    x_start,
    x_end,
    level_type: str,
    show_labels: bool = True
):
    """
    Draw TradingView-style horizontal price levels.
    Entry levels: dashed lines with E1-E5 badge labels
    Exit levels: dashed lines with TP1-TP5 badge labels
    """
    level_colors = {
        'entry': COLORS['blue'],
        'exit': COLORS['take_profit'],
    }

    color = level_colors.get(level_type, COLORS['gray'])
    x_start_num = _to_num(x_start)
    x_end_num = _to_num(x_end)

    for i, level in enumerate(levels):
        # Lighter alpha for further levels
        line_alpha = 0.6 - (i * 0.08)
        ax.hlines(
            level, x_start_num, x_end_num,
            colors=color,
            linestyles='--',
            linewidth=0.8,
            alpha=max(line_alpha, 0.25)
        )
        if show_labels:
            label = f"E{i+1}" if level_type == 'entry' else f"TP{i+1}"
            # TV-style right-edge price label badge
            ax.annotate(
                label,
                xy=(x_end_num, level),
                xytext=(4, 0),
                textcoords='offset points',
                fontsize=7,
                color=COLORS['background'],
                weight='bold',
                va='center',
                bbox=dict(
                    boxstyle='round,pad=0.15',
                    facecolor=color,
                    edgecolor='none',
                    alpha=max(line_alpha, 0.4)
                )
            )


def draw_trade_setup(
    ax,
    setup: TradeSetup,
    x_start,
    x_end,
    show_boxes: bool = True,
    show_levels: bool = True,
    show_labels: bool = True
):
    """
    Draw TradingView-style R:R trade setup visualization.

    Uses axhspan/axhline to draw zones ACROSS THE ENTIRE CHART
    (overlaying on candles), exactly like TradingView's R:R tool.
    """
    is_long = setup.direction.upper() == 'LONG'
    x_start_num = _to_num(x_start)
    x_end_num = _to_num(x_end)

    # -- STOP LOSS ZONE (red, full-width overlay on chart) --
    if setup.stop_loss and show_boxes:
        if is_long:
            sl_top, sl_bottom = setup.entry_price, setup.stop_loss
        else:
            sl_top, sl_bottom = setup.stop_loss, setup.entry_price

        # axhspan draws across FULL chart width - overlays on candles
        ax.axhspan(sl_bottom, sl_top,
                    facecolor=COLORS['stop_loss'], alpha=0.08, zorder=0)

        # SL line - full width
        ax.axhline(y=setup.stop_loss, color=COLORS['stop_loss'],
                    linewidth=1.2, alpha=0.8, linestyle='-', zorder=1)

        # SL price badge on right edge
        if show_labels:
            ax.annotate(
                f"SL {format_price(setup.stop_loss)}",
                xy=(1.0, setup.stop_loss),
                xycoords=('axes fraction', 'data'),
                xytext=(6, 0),
                textcoords='offset points',
                fontsize=8,
                color='white',
                weight='bold',
                va='center',
                bbox=dict(
                    boxstyle='round,pad=0.2',
                    facecolor=COLORS['stop_loss'],
                    edgecolor='none',
                    alpha=0.85
                ),
                zorder=5
            )

    # -- TAKE PROFIT ZONE (green, full-width overlay on chart) --
    if setup.scaled_exits and show_boxes:
        if is_long:
            tp_bottom, tp_top = setup.entry_price, setup.scaled_exits[-1]
        else:
            tp_top, tp_bottom = setup.entry_price, setup.scaled_exits[-1]

        ax.axhspan(tp_bottom, tp_top,
                    facecolor=COLORS['take_profit'], alpha=0.06, zorder=0)

    # -- ENTRY LINE (white, full width, prominent) --
    ax.axhline(y=setup.entry_price, color=COLORS['entry'],
                linewidth=1.8, alpha=0.9, zorder=2)

    if show_labels:
        ax.annotate(
            f"ENTRY {format_price(setup.entry_price)}",
            xy=(1.0, setup.entry_price),
            xycoords=('axes fraction', 'data'),
            xytext=(6, 0),
            textcoords='offset points',
            fontsize=8,
            color=COLORS['background'],
            weight='bold',
            va='center',
            bbox=dict(
                boxstyle='round,pad=0.2',
                facecolor=COLORS['entry'],
                edgecolor='none',
                alpha=0.9
            ),
            zorder=5
        )

    # -- SCALED ENTRY LEVELS (dashed, full width) --
    if setup.scaled_entries and show_levels:
        for i, level in enumerate(setup.scaled_entries[1:], start=1):
            alpha = 0.5 - (i * 0.08)
            ax.axhline(y=level, color=COLORS['blue'],
                        linewidth=0.6, alpha=max(alpha, 0.2),
                        linestyle='--', zorder=1)
            if show_labels:
                ax.annotate(
                    f"E{i+1}",
                    xy=(1.0, level),
                    xycoords=('axes fraction', 'data'),
                    xytext=(6, 0),
                    textcoords='offset points',
                    fontsize=7,
                    color=COLORS['background'],
                    weight='bold',
                    va='center',
                    bbox=dict(
                        boxstyle='round,pad=0.15',
                        facecolor=COLORS['blue'],
                        edgecolor='none',
                        alpha=max(alpha, 0.3)
                    ),
                    zorder=5
                )

    # -- SCALED EXIT LEVELS (dashed, full width) --
    if setup.scaled_exits and show_levels:
        for i, level in enumerate(setup.scaled_exits):
            alpha = 0.5 - (i * 0.06)
            ax.axhline(y=level, color=COLORS['take_profit'],
                        linewidth=0.6, alpha=max(alpha, 0.2),
                        linestyle='--', zorder=1)
            if show_labels:
                ax.annotate(
                    f"TP{i+1}",
                    xy=(1.0, level),
                    xycoords=('axes fraction', 'data'),
                    xytext=(6, 0),
                    textcoords='offset points',
                    fontsize=7,
                    color=COLORS['background'],
                    weight='bold',
                    va='center',
                    bbox=dict(
                        boxstyle='round,pad=0.15',
                        facecolor=COLORS['take_profit'],
                        edgecolor='none',
                        alpha=max(alpha, 0.3)
                    ),
                    zorder=5
                )

    # -- R:R BADGE (centered in chart, inside TP zone) --
    if setup.stop_loss and setup.scaled_exits:
        risk = abs(setup.entry_price - setup.stop_loss)
        reward = abs(setup.scaled_exits[-1] - setup.entry_price)
        rr = reward / risk if risk > 0 else 0

        # Place in middle of TP zone, centered horizontally
        if is_long:
            badge_y = setup.entry_price + (setup.scaled_exits[-1] - setup.entry_price) * 0.45
        else:
            badge_y = setup.entry_price - (setup.entry_price - setup.scaled_exits[-1]) * 0.45

        ax.annotate(
            f"R:R {rr:.1f}:1",
            xy=(0.75, badge_y),
            xycoords=('axes fraction', 'data'),
            fontsize=12,
            color=COLORS['rr_badge'],
            weight='bold',
            ha='center',
            va='center',
            bbox=dict(
                boxstyle='round,pad=0.4',
                facecolor=COLORS['background'],
                edgecolor=COLORS['rr_badge'],
                linewidth=1.5,
                alpha=0.92
            ),
            zorder=6
        )

    # -- DIRECTION TAG (centered in SL zone) --
    direction_color = COLORS['take_profit'] if is_long else COLORS['stop_loss']
    if is_long:
        dir_y = setup.entry_price - abs(setup.entry_price - setup.stop_loss) * 0.45
    else:
        dir_y = setup.entry_price + abs(setup.stop_loss - setup.entry_price) * 0.45

    ax.annotate(
        setup.direction.upper(),
        xy=(0.75, dir_y),
        xycoords=('axes fraction', 'data'),
        fontsize=11,
        color=direction_color,
        weight='bold',
        ha='center',
        va='center',
        zorder=6
    )
