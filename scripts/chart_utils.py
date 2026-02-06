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

# Chart styling
COLORS = {
    'green': '#00C853',
    'red': '#FF5252',
    'blue': '#2196F3',
    'orange': '#FF9800',
    'purple': '#9C27B0',
    'gray': '#9E9E9E',
    'background': '#1a1a2e',
    'grid': '#2a2a4e',
    'text': '#e0e0e0',
}

def setup_dark_style():
    """Configure matplotlib for dark theme charts."""
    plt.style.use('dark_background')
    plt.rcParams.update({
        'figure.facecolor': COLORS['background'],
        'axes.facecolor': COLORS['background'],
        'axes.edgecolor': COLORS['grid'],
        'axes.labelcolor': COLORS['text'],
        'text.color': COLORS['text'],
        'xtick.color': COLORS['text'],
        'ytick.color': COLORS['text'],
        'grid.color': COLORS['grid'],
        'grid.alpha': 0.3,
        'legend.facecolor': COLORS['background'],
        'legend.edgecolor': COLORS['grid'],
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
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
    """Plot candlestick chart on given axis."""
    for i in range(len(dates)):
        color = COLORS['green'] if closes[i] >= opens[i] else COLORS['red']

        # Wick
        ax.plot([dates[i], dates[i]], [lows[i], highs[i]], color=color, linewidth=0.8)

        # Body
        body_bottom = min(opens[i], closes[i])
        body_height = abs(closes[i] - opens[i])

        if body_height > 0:
            rect = Rectangle(
                (mdates.date2num(dates[i]) - width/2, body_bottom),
                width, body_height,
                facecolor=color, edgecolor=color
            )
            ax.add_patch(rect)
        else:
            # Doji - just a line
            ax.plot([dates[i], dates[i]], [opens[i], closes[i]], color=color, linewidth=1.5)


def save_chart(fig, filename, ticker=None):
    """Save chart to file with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if ticker:
        subdir = CHART_DIR / ticker.upper()
        subdir.mkdir(parents=True, exist_ok=True)
        filepath = subdir / f"{filename}_{timestamp}.png"
    else:
        filepath = CHART_DIR / f"{filename}_{timestamp}.png"

    fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=COLORS['background'])
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


def draw_trade_setup_box(
    ax,
    price_top: float,
    price_bottom: float,
    x_start,
    x_end,
    box_type: str,
    alpha: float = 0.3
):
    """
    Draw a colored rectangular zone on the chart.

    Colors:
    - entry: white/neutral with transparency
    - stop_loss: red with transparency
    - take_profit: green with transparency
    """
    box_colors = {
        'entry': '#FFFFFF',           # White for entry zone
        'stop_loss': COLORS['red'],
        'take_profit': COLORS['green'],
    }

    color = box_colors.get(box_type, COLORS['gray'])

    # Convert x_start to numeric if it's a datetime
    if hasattr(x_start, 'timestamp'):
        x_start_num = mdates.date2num(x_start)
    else:
        x_start_num = x_start

    # Convert x_end to numeric if it's a datetime
    if hasattr(x_end, 'timestamp'):
        x_end_num = mdates.date2num(x_end)
    else:
        x_end_num = x_end

    width = x_end_num - x_start_num

    rect = Rectangle(
        (x_start_num, price_bottom),
        width,
        price_top - price_bottom,
        linewidth=2,
        edgecolor=color,
        facecolor=color,
        alpha=alpha
    )
    ax.add_patch(rect)


def draw_scaled_levels(
    ax,
    levels: List[float],
    x_start,
    x_end,
    level_type: str,
    show_labels: bool = True
):
    """
    Draw horizontal lines for scaled entry/exit levels.

    Entry levels: dashed blue lines, numbered E1-E5
    Exit levels: dashed green lines, labeled TP1-TP5
    """
    level_colors = {
        'entry': COLORS['blue'],
        'exit': COLORS['green'],
    }

    color = level_colors.get(level_type, COLORS['gray'])

    # Convert to numeric for hlines
    x_start_num = mdates.date2num(x_start) if hasattr(x_start, 'timestamp') else x_start
    x_end_num = mdates.date2num(x_end) if hasattr(x_end, 'timestamp') else x_end

    for i, level in enumerate(levels):
        ax.hlines(
            level, x_start_num, x_end_num,
            colors=color,
            linestyles='dashed',
            linewidth=1,
            alpha=0.7
        )
        if show_labels:
            label = f"E{i+1}" if level_type == 'entry' else f"TP{i+1}"
            ax.annotate(
                label,
                xy=(x_end_num, level),
                xytext=(5, 0),
                textcoords='offset points',
                fontsize=8,
                color=color,
                va='center'
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
    Draw complete trade setup visualization on price chart.

    Args:
        ax: Matplotlib axis
        setup: TradeSetup dataclass with trade parameters
        x_start: Start x-coordinate (datetime or numeric) - typically current time
        x_end: End x-coordinate (datetime or numeric) - extends into future
        show_boxes: Whether to draw SL/TP zone boxes
        show_levels: Whether to draw scaled entry/exit level lines
        show_labels: Whether to show E1-E5 / TP1-TP5 labels
    """
    is_long = setup.direction.upper() == 'LONG'

    # Convert to numeric for consistent drawing
    x_start_num = mdates.date2num(x_start) if hasattr(x_start, 'timestamp') else x_start
    x_end_num = mdates.date2num(x_end) if hasattr(x_end, 'timestamp') else x_end

    # 0. Draw vertical "NOW" line at trade entry time
    ax.axvline(x=x_start_num, color='white', linestyle='-', linewidth=1.5, alpha=0.6)

    # 1. Draw stop loss zone (red box)
    if setup.stop_loss and show_boxes:
        if is_long:
            sl_top = setup.entry_price
            sl_bottom = setup.stop_loss
        else:  # SHORT
            sl_top = setup.stop_loss
            sl_bottom = setup.entry_price

        draw_trade_setup_box(ax, sl_top, sl_bottom, x_start_num, x_end_num, 'stop_loss', alpha=0.25)

        # Stop loss line
        ax.hlines(
            setup.stop_loss, x_start_num, x_end_num,
            colors=COLORS['red'],
            linestyles='solid',
            linewidth=2,
            alpha=0.9
        )
        if show_labels:
            ax.annotate(
                f"SL {format_price(setup.stop_loss)}",
                xy=(x_end_num, setup.stop_loss),
                xytext=(5, 0),
                textcoords='offset points',
                fontsize=9,
                color=COLORS['red'],
                weight='bold',
                va='center'
            )

    # 2. Draw take profit zones (green boxes with graduated transparency)
    if setup.scaled_exits and show_boxes:
        for i, tp in enumerate(setup.scaled_exits):
            alpha = 0.12 + (i * 0.04)  # Gradually darker: 0.12 -> 0.28
            if is_long:
                tp_bottom = setup.scaled_exits[i-1] if i > 0 else setup.entry_price
                tp_top = tp
            else:  # SHORT
                tp_top = setup.scaled_exits[i-1] if i > 0 else setup.entry_price
                tp_bottom = tp
            draw_trade_setup_box(ax, tp_top, tp_bottom, x_start_num, x_end_num, 'take_profit', alpha=alpha)

    # 3. Draw entry line (bold white)
    ax.hlines(
        setup.entry_price, x_start_num, x_end_num,
        colors='white',
        linewidth=3,
        alpha=1.0
    )
    if show_labels:
        ax.annotate(
            f"ENTRY {format_price(setup.entry_price)}",
            xy=(x_end_num, setup.entry_price),
            xytext=(5, 0),
            textcoords='offset points',
            fontsize=10,
            color='white',
            weight='bold',
            va='center'
        )

    # 4. Draw scaled entry levels (dashed blue lines)
    if setup.scaled_entries and show_levels:
        draw_scaled_levels(ax, setup.scaled_entries, x_start_num, x_end_num, 'entry', show_labels)

    # 5. Draw scaled exit levels (dashed green lines)
    if setup.scaled_exits and show_levels:
        draw_scaled_levels(ax, setup.scaled_exits, x_start_num, x_end_num, 'exit', show_labels)

    # 6. Add R:R annotation
    if setup.stop_loss and setup.scaled_exits:
        risk = abs(setup.entry_price - setup.stop_loss)
        reward = abs(setup.scaled_exits[-1] - setup.entry_price)
        rr = reward / risk if risk > 0 else 0

        # Position annotation near entry
        y_offset = 15 if is_long else -15
        ax.annotate(
            f"R:R {rr:.1f}:1",
            xy=(x_start, setup.entry_price),
            xytext=(10, y_offset),
            textcoords='offset points',
            fontsize=11,
            color=COLORS['orange'],
            weight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['background'], edgecolor=COLORS['orange'], alpha=0.8)
        )

    # 7. Add direction indicator
    direction_color = COLORS['green'] if is_long else COLORS['red']
    ax.annotate(
        setup.direction.upper(),
        xy=(x_start, setup.entry_price),
        xytext=(10, -15 if is_long else 15),
        textcoords='offset points',
        fontsize=12,
        color=direction_color,
        weight='bold'
    )
