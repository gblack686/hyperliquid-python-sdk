#!/usr/bin/env python
"""Full trade history with statistics."""
import os
import sys
import asyncio
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def get_history(ticker_filter=None, limit=50):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Get all fills
    endpoint = hyp._add_to_request('order_fills', data={'user': hyp.account_address})
    fills = await hyp.http_client.request(**endpoint)

    print("=" * 90)
    print("TRADE HISTORY")
    print("=" * 90)

    if not fills:
        print("No trade history found.")
        await hyp.cleanup()
        return

    # Filter by ticker
    if ticker_filter:
        ticker_filter = ticker_filter.upper()
        fills = [f for f in fills if f.get('coin', '').upper() == ticker_filter]

    if not fills:
        print(f"No trades found for {ticker_filter}")
        await hyp.cleanup()
        return

    # Group fills into trades (round trips)
    trades = []
    position = defaultdict(float)
    entry_prices = defaultdict(list)

    for fill in reversed(fills):  # Process oldest first
        ticker = fill.get('coin', 'UNKNOWN')
        side = 1 if fill.get('side') == 'B' else -1
        size = float(fill.get('sz', 0)) * side
        price = float(fill.get('px', 0))
        pnl = float(fill.get('closedPnl', 0))
        fee = float(fill.get('fee', 0))
        ts = fill.get('time', 0)

        old_pos = position[ticker]
        position[ticker] += size

        # If position closed or reduced
        if pnl != 0:
            trades.append({
                'time': ts,
                'ticker': ticker,
                'side': 'LONG' if old_pos > 0 else 'SHORT',
                'pnl': pnl,
                'fee': fee,
                'exit_price': price,
                'size': abs(size)
            })

    # Statistics
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]

    total_pnl = sum(t['pnl'] for t in trades)
    total_fees = sum(t['fee'] for t in trades)
    avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
    profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)) if losing_trades and sum(t['pnl'] for t in losing_trades) != 0 else 0

    print("\nSTATISTICS:")
    print(f"  Total Trades:   {len(trades)}")
    print(f"  Winning Trades: {len(winning_trades)}")
    print(f"  Losing Trades:  {len(losing_trades)}")
    print(f"  Win Rate:       {win_rate:.1f}%")
    print(f"  Avg Win:        ${avg_win:,.2f}")
    print(f"  Avg Loss:       ${avg_loss:,.2f}")
    print(f"  Profit Factor:  {profit_factor:.2f}")
    print(f"  Total PnL:      ${total_pnl:,.2f}")
    print(f"  Total Fees:     ${total_fees:,.2f}")
    print(f"  Net PnL:        ${total_pnl - total_fees:,.2f}")

    # Recent trades
    print(f"\nRECENT TRADES (last {min(limit, len(trades))}):")
    print(f"  {'Time':19} {'Ticker':8} {'Side':6} {'PnL':>12} {'Fee':>8}")
    print("-" * 60)

    recent_trades = sorted(trades, key=lambda x: x['time'], reverse=True)[:limit]
    for trade in recent_trades:
        try:
            dt = datetime.fromtimestamp(trade['time'] / 1000)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            time_str = 'N/A'

        pnl_color = '+' if trade['pnl'] > 0 else ''
        print(f"  {time_str:19} {trade['ticker']:8} {trade['side']:6} {pnl_color}${trade['pnl']:>10,.2f} ${trade['fee']:>6,.2f}")

    # Best and worst trades
    if trades:
        best = max(trades, key=lambda x: x['pnl'])
        worst = min(trades, key=lambda x: x['pnl'])
        print()
        print(f"  Best Trade:  {best['ticker']} ${best['pnl']:,.2f}")
        print(f"  Worst Trade: {worst['ticker']} ${worst['pnl']:,.2f}")

    print("=" * 90)
    await hyp.cleanup()

if __name__ == "__main__":
    ticker = None
    limit = 50

    for arg in sys.argv[1:]:
        if arg.isdigit():
            limit = int(arg)
        else:
            ticker = arg

    asyncio.run(get_history(ticker, limit))
