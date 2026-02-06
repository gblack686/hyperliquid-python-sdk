#!/usr/bin/env python3
"""
Market Overview Chart for Hyperliquid

Generates charts showing market-wide data: top movers, funding rates, and open interest.

USAGE:
  python hyp_chart_market.py [top_n]

EXAMPLES:
  python hyp_chart_market.py           # Top 10 by default
  python hyp_chart_market.py 20        # Top 20
"""

import os
import sys
import asyncio
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from hyperliquid.info import Info
from hyperliquid.utils import constants
from chart_utils import setup_dark_style, COLORS, save_chart


async def chart_market(top_n: int = 10):
    """Generate market overview charts."""

    print(f"Generating market overview charts (top {top_n})...")

    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    try:
        # Fetch market data
        meta_and_ctxs = info.meta_and_asset_ctxs()

        if not meta_and_ctxs or len(meta_and_ctxs) < 2:
            print("[ERROR] Could not fetch market data")
            return None

        meta = meta_and_ctxs[0]
        asset_ctxs = meta_and_ctxs[1]
        universe = meta.get('universe', [])

        # Extract data
        market_data = []
        for i, asset in enumerate(universe):
            ticker = asset.get('name', f'UNKNOWN_{i}')
            ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}

            mark_price = float(ctx.get('markPx', 0))
            prev_price = float(ctx.get('prevDayPx', 0))
            volume_24h = float(ctx.get('dayNtlVlm', 0))
            funding = float(ctx.get('funding', 0)) * 100
            open_interest = float(ctx.get('openInterest', 0)) * mark_price

            if mark_price > 0 and prev_price > 0 and volume_24h >= 100000:
                change_24h = ((mark_price - prev_price) / prev_price) * 100
                market_data.append({
                    'ticker': ticker,
                    'price': mark_price,
                    'change_24h': change_24h,
                    'volume_24h': volume_24h,
                    'funding': funding,
                    'open_interest': open_interest
                })

        if not market_data:
            print("[ERROR] No market data available")
            return None

        # Sort for different charts
        by_change = sorted(market_data, key=lambda x: x['change_24h'], reverse=True)
        gainers = by_change[:top_n]
        losers = by_change[-top_n:][::-1]

        by_volume = sorted(market_data, key=lambda x: x['volume_24h'], reverse=True)[:top_n]
        by_oi = sorted(market_data, key=lambda x: x['open_interest'], reverse=True)[:top_n]
        by_funding = sorted(market_data, key=lambda x: abs(x['funding']), reverse=True)[:top_n]

        # Create charts
        setup_dark_style()
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Hyperliquid Market Overview - {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                    fontsize=14, fontweight='bold')

        # Chart 1: Top Gainers & Losers
        ax1 = axes[0, 0]
        tickers = [g['ticker'] for g in gainers[:5]] + [''] + [l['ticker'] for l in losers[:5]]
        changes = [g['change_24h'] for g in gainers[:5]] + [0] + [l['change_24h'] for l in losers[:5]]
        colors = [COLORS['green'] if c >= 0 else COLORS['red'] for c in changes]

        y_pos = np.arange(len(tickers))
        ax1.barh(y_pos, changes, color=colors)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(tickers)
        ax1.axvline(x=0, color=COLORS['gray'], linestyle='-', linewidth=0.5)
        ax1.set_xlabel('24h Change %')
        ax1.set_title('Top Gainers & Losers')
        ax1.grid(True, alpha=0.3, axis='x')

        # Add value labels
        for i, v in enumerate(changes):
            if v != 0:
                ax1.text(v + (0.5 if v >= 0 else -0.5), i, f'{v:+.1f}%',
                        va='center', ha='left' if v >= 0 else 'right', fontsize=8)

        # Chart 2: Top Volume
        ax2 = axes[0, 1]
        vol_tickers = [m['ticker'] for m in by_volume]
        vol_values = [m['volume_24h'] / 1e6 for m in by_volume]  # In millions

        y_pos = np.arange(len(vol_tickers))
        colors = [COLORS['green'] if by_volume[i]['change_24h'] >= 0 else COLORS['red']
                 for i in range(len(by_volume))]
        ax2.barh(y_pos, vol_values, color=colors, alpha=0.7)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(vol_tickers)
        ax2.set_xlabel('24h Volume ($ millions)')
        ax2.set_title('Top Volume')
        ax2.grid(True, alpha=0.3, axis='x')

        for i, v in enumerate(vol_values):
            ax2.text(v + max(vol_values) * 0.02, i, f'${v:.1f}M', va='center', fontsize=8)

        # Chart 3: Open Interest
        ax3 = axes[1, 0]
        oi_tickers = [m['ticker'] for m in by_oi]
        oi_values = [m['open_interest'] / 1e6 for m in by_oi]  # In millions

        y_pos = np.arange(len(oi_tickers))
        ax3.barh(y_pos, oi_values, color=COLORS['blue'], alpha=0.7)
        ax3.set_yticks(y_pos)
        ax3.set_yticklabels(oi_tickers)
        ax3.set_xlabel('Open Interest ($ millions)')
        ax3.set_title('Top Open Interest')
        ax3.grid(True, alpha=0.3, axis='x')

        for i, v in enumerate(oi_values):
            ax3.text(v + max(oi_values) * 0.02, i, f'${v:.1f}M', va='center', fontsize=8)

        # Chart 4: Extreme Funding Rates
        ax4 = axes[1, 1]
        fund_tickers = [m['ticker'] for m in by_funding]
        fund_values = [m['funding'] for m in by_funding]
        colors = [COLORS['red'] if f > 0 else COLORS['green'] for f in fund_values]

        y_pos = np.arange(len(fund_tickers))
        ax4.barh(y_pos, fund_values, color=colors, alpha=0.7)
        ax4.set_yticks(y_pos)
        ax4.set_yticklabels(fund_tickers)
        ax4.axvline(x=0, color=COLORS['gray'], linestyle='-', linewidth=0.5)
        ax4.set_xlabel('Funding Rate (% per 8h)')
        ax4.set_title('Extreme Funding Rates')
        ax4.grid(True, alpha=0.3, axis='x')

        for i, v in enumerate(fund_values):
            ax4.text(v + (0.002 if v >= 0 else -0.002), i, f'{v:.4f}%',
                    va='center', ha='left' if v >= 0 else 'right', fontsize=8)

        plt.tight_layout()

        # Save chart
        filepath = save_chart(fig, "market_overview")
        print(f"Chart saved: {filepath}")

        # Print summary
        print()
        print("=== Market Summary ===")
        print(f"Top Gainer: {gainers[0]['ticker']} +{gainers[0]['change_24h']:.1f}%")
        print(f"Top Loser: {losers[0]['ticker']} {losers[0]['change_24h']:.1f}%")
        print(f"Top Volume: {by_volume[0]['ticker']} ${by_volume[0]['volume_24h']/1e6:.1f}M")
        print(f"Top OI: {by_oi[0]['ticker']} ${by_oi[0]['open_interest']/1e6:.1f}M")

        return filepath

    except Exception as e:
        print(f"[ERROR] Chart generation failed: {e}")
        return None


if __name__ == "__main__":
    top_n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    asyncio.run(chart_market(top_n))
