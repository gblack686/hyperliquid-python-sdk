#!/usr/bin/env python
"""Detailed PnL analysis for Hyperliquid."""
import os
import sys
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def analyze_pnl(period='all'):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Get all fills
    endpoint = hyp._add_to_request('order_fills', data={'user': hyp.account_address})
    fills = await hyp.http_client.request(**endpoint)

    print("=" * 70)
    print("PNL ANALYSIS")
    print("=" * 70)

    if not fills:
        print("No trade history found.")
        await hyp.cleanup()
        return

    # Filter by period
    now = datetime.now()
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_name = "Today"
    elif period == 'week':
        start_date = now - timedelta(days=7)
        period_name = "Last 7 Days"
    elif period == 'month':
        start_date = now - timedelta(days=30)
        period_name = "Last 30 Days"
    else:
        start_date = datetime(2020, 1, 1)
        period_name = "All Time"

    start_ts = start_date.timestamp() * 1000

    filtered_fills = [f for f in fills if f.get('time', 0) >= start_ts]

    if not filtered_fills:
        print(f"No trades found for period: {period_name}")
        await hyp.cleanup()
        return

    # Aggregate by ticker
    ticker_stats = defaultdict(lambda: {'pnl': 0, 'fees': 0, 'volume': 0, 'trades': 0, 'wins': 0, 'losses': 0})
    daily_pnl = defaultdict(float)

    for fill in filtered_fills:
        ticker = fill.get('coin', 'UNKNOWN')
        pnl = float(fill.get('closedPnl', 0))
        fee = float(fill.get('fee', 0))
        size = float(fill.get('sz', 0))
        price = float(fill.get('px', 0))
        ts = fill.get('time', 0)

        ticker_stats[ticker]['pnl'] += pnl
        ticker_stats[ticker]['fees'] += fee
        ticker_stats[ticker]['volume'] += size * price
        ticker_stats[ticker]['trades'] += 1
        if pnl > 0:
            ticker_stats[ticker]['wins'] += 1
        elif pnl < 0:
            ticker_stats[ticker]['losses'] += 1

        # Daily aggregation
        try:
            day = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d')
            daily_pnl[day] += pnl
        except:
            pass

    # Summary
    total_pnl = sum(s['pnl'] for s in ticker_stats.values())
    total_fees = sum(s['fees'] for s in ticker_stats.values())
    total_volume = sum(s['volume'] for s in ticker_stats.values())
    total_trades = sum(s['trades'] for s in ticker_stats.values())
    total_wins = sum(s['wins'] for s in ticker_stats.values())
    total_losses = sum(s['losses'] for s in ticker_stats.values())

    net_pnl = total_pnl - total_fees
    win_rate = (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) > 0 else 0

    print(f"\nPeriod: {period_name}")
    print(f"Trades: {total_trades}")
    print()

    print("SUMMARY:")
    print(f"  Gross PnL:    ${total_pnl:>12,.2f}")
    print(f"  Fees:         ${total_fees:>12,.2f}")
    print(f"  Net PnL:      ${net_pnl:>12,.2f}")
    print(f"  Volume:       ${total_volume:>12,.0f}")
    print(f"  Win Rate:     {win_rate:>12.1f}%")
    print()

    # By ticker
    print("BY TICKER:")
    print(f"  {'Ticker':10} {'PnL':>12} {'Fees':>10} {'Trades':>8} {'Win%':>8}")
    print("-" * 55)

    sorted_tickers = sorted(ticker_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)
    for ticker, stats in sorted_tickers:
        if stats['trades'] > 0:
            wr = (stats['wins'] / (stats['wins'] + stats['losses']) * 100) if (stats['wins'] + stats['losses']) > 0 else 0
            print(f"  {ticker:10} ${stats['pnl']:>10,.2f} ${stats['fees']:>8,.2f} {stats['trades']:>8} {wr:>7.1f}%")

    # Daily breakdown (last 7 days)
    if daily_pnl:
        print()
        print("DAILY PNL (Recent):")
        sorted_days = sorted(daily_pnl.items(), reverse=True)[:7]
        for day, pnl in sorted_days:
            print(f"  {day}: ${pnl:>10,.2f}")

    print("=" * 70)
    await hyp.cleanup()

if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else 'all'
    asyncio.run(analyze_pnl(period))
