#!/usr/bin/env python3
"""
P&L Chart for Hyperliquid

Generates charts showing P&L history, equity curve, and trade distribution.

USAGE:
  python hyp_chart_pnl.py [num_trades]

EXAMPLES:
  python hyp_chart_pnl.py           # Last 100 trades
  python hyp_chart_pnl.py 200       # Last 200 trades
"""

import os
import sys
import asyncio
import numpy as np
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from hyperliquid.info import Info
from hyperliquid.utils import constants
from chart_utils import setup_dark_style, COLORS, save_chart


async def chart_pnl(num_trades: int = 100):
    """Generate P&L analysis charts."""

    print(f"Generating P&L charts (last {num_trades} trades)...")

    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    # Get account address
    account = os.getenv('HYP_ACCOUNT_ADDRESS')
    if not account:
        from quantpylib.wrappers.hyperliquid import Hyperliquid
        hyp = Hyperliquid(
            key=os.getenv('HYP_KEY'),
            secret=os.getenv('HYP_SECRET'),
            mode='live'
        )
        await hyp.init_client()
        account = hyp.account_address
        await hyp.cleanup()

    try:
        # Fetch fills
        fills = info.user_fills(account)

        if not fills:
            print("[ERROR] No trade history found")
            return None

        # Filter fills with closed PnL
        trades_with_pnl = [
            f for f in fills
            if float(f.get('closedPnl', 0)) != 0
        ][:num_trades]

        if len(trades_with_pnl) < 5:
            print("[ERROR] Insufficient trade history for charts")
            return None

        # Extract data
        pnls = [float(f['closedPnl']) for f in trades_with_pnl]
        timestamps = [datetime.fromtimestamp(f['time'] / 1000) for f in trades_with_pnl]
        tickers = [f.get('coin', 'UNKNOWN') for f in trades_with_pnl]

        # Calculate cumulative P&L (reverse order for chronological)
        pnls_chrono = pnls[::-1]
        timestamps_chrono = timestamps[::-1]
        cumulative = np.cumsum(pnls_chrono)

        # Stats by ticker
        pnl_by_ticker = defaultdict(float)
        trades_by_ticker = defaultdict(int)
        for f in trades_with_pnl:
            ticker = f.get('coin', 'UNKNOWN')
            pnl = float(f.get('closedPnl', 0))
            pnl_by_ticker[ticker] += pnl
            trades_by_ticker[ticker] += 1

        # Sort by absolute P&L
        sorted_tickers = sorted(pnl_by_ticker.keys(), key=lambda x: abs(pnl_by_ticker[x]), reverse=True)[:10]

        # Create charts
        setup_dark_style()
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'P&L Analysis - Last {len(trades_with_pnl)} Trades', fontsize=14, fontweight='bold')

        # Chart 1: Cumulative P&L (Equity Curve)
        ax1 = axes[0, 0]
        ax1.fill_between(timestamps_chrono, 0, cumulative,
                        where=(cumulative >= 0), alpha=0.3, color=COLORS['green'])
        ax1.fill_between(timestamps_chrono, 0, cumulative,
                        where=(cumulative < 0), alpha=0.3, color=COLORS['red'])
        ax1.plot(timestamps_chrono, cumulative, color=COLORS['text'], linewidth=1.5)
        ax1.axhline(y=0, color=COLORS['gray'], linestyle='-', linewidth=0.5)
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Cumulative P&L ($)')
        ax1.set_title('Equity Curve')
        ax1.grid(True, alpha=0.3)

        # Annotate final value
        final_pnl = cumulative[-1]
        ax1.annotate(f'${final_pnl:+,.2f}', xy=(timestamps_chrono[-1], final_pnl),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=10, color=COLORS['green'] if final_pnl >= 0 else COLORS['red'],
                    fontweight='bold')

        # Chart 2: Trade Distribution
        ax2 = axes[0, 1]
        colors = [COLORS['green'] if p >= 0 else COLORS['red'] for p in pnls_chrono]
        ax2.bar(range(len(pnls_chrono)), pnls_chrono, color=colors, alpha=0.7)
        ax2.axhline(y=0, color=COLORS['gray'], linestyle='-', linewidth=0.5)
        ax2.set_xlabel('Trade #')
        ax2.set_ylabel('P&L ($)')
        ax2.set_title('Individual Trade P&L')
        ax2.grid(True, alpha=0.3)

        # Win rate annotation
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)
        win_rate = wins / len(pnls) * 100 if pnls else 0
        ax2.text(0.02, 0.98, f'Win Rate: {win_rate:.1f}%\nWins: {wins} | Losses: {losses}',
                transform=ax2.transAxes, va='top', fontsize=10,
                bbox=dict(boxstyle='round', facecolor=COLORS['background'], edgecolor=COLORS['grid']))

        # Chart 3: P&L by Ticker
        ax3 = axes[1, 0]
        ticker_pnls = [pnl_by_ticker[t] for t in sorted_tickers]
        colors = [COLORS['green'] if p >= 0 else COLORS['red'] for p in ticker_pnls]

        y_pos = np.arange(len(sorted_tickers))
        ax3.barh(y_pos, ticker_pnls, color=colors, alpha=0.7)
        ax3.set_yticks(y_pos)
        ax3.set_yticklabels(sorted_tickers)
        ax3.axvline(x=0, color=COLORS['gray'], linestyle='-', linewidth=0.5)
        ax3.set_xlabel('Total P&L ($)')
        ax3.set_title('P&L by Ticker')
        ax3.grid(True, alpha=0.3, axis='x')

        for i, v in enumerate(ticker_pnls):
            ax3.text(v + (max(abs(min(ticker_pnls)), max(ticker_pnls)) * 0.02 if v >= 0 else -max(abs(min(ticker_pnls)), max(ticker_pnls)) * 0.02),
                    i, f'${v:+,.0f}', va='center', ha='left' if v >= 0 else 'right', fontsize=8)

        # Chart 4: P&L Histogram
        ax4 = axes[1, 1]
        bins = np.linspace(min(pnls), max(pnls), 30)
        ax4.hist(pnls, bins=bins, color=COLORS['blue'], alpha=0.7, edgecolor=COLORS['text'])
        ax4.axvline(x=0, color=COLORS['gray'], linestyle='-', linewidth=1)
        ax4.axvline(x=np.mean(pnls), color=COLORS['orange'], linestyle='--', linewidth=1, label=f'Mean: ${np.mean(pnls):.2f}')
        ax4.axvline(x=np.median(pnls), color=COLORS['purple'], linestyle='--', linewidth=1, label=f'Median: ${np.median(pnls):.2f}')
        ax4.set_xlabel('P&L ($)')
        ax4.set_ylabel('Frequency')
        ax4.set_title('P&L Distribution')
        ax4.legend(loc='upper right', fontsize=8)
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save chart
        filepath = save_chart(fig, "pnl_analysis")
        print(f"Chart saved: {filepath}")

        # Print summary
        print()
        print("=== P&L Summary ===")
        print(f"Total Trades: {len(pnls)}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Total P&L: ${sum(pnls):+,.2f}")
        print(f"Average Trade: ${np.mean(pnls):+,.2f}")
        print(f"Best Trade: ${max(pnls):+,.2f}")
        print(f"Worst Trade: ${min(pnls):+,.2f}")
        print(f"Profit Factor: {abs(sum(p for p in pnls if p > 0) / sum(p for p in pnls if p < 0)):.2f}" if sum(p for p in pnls if p < 0) != 0 else "N/A")

        return filepath

    except Exception as e:
        print(f"[ERROR] Chart generation failed: {e}")
        return None


if __name__ == "__main__":
    num_trades = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    asyncio.run(chart_pnl(num_trades))
