#!/usr/bin/env python
"""Watch live trades (trade tape) on Hyperliquid."""
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def watch_trades(ticker, duration=30):
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    ticker = ticker.upper()
    print("=" * 60)
    print(f"LIVE TRADES: {ticker} (press Ctrl+C to stop)")
    print("=" * 60)
    print(f"{'Time':12} {'Side':6} {'Price':>14} {'Size':>12} {'Value':>14}")
    print("-" * 62)

    trade_count = 0
    buy_volume = 0
    sell_volume = 0

    async def trade_handler(msg):
        nonlocal trade_count, buy_volume, sell_volume
        try:
            if 'data' in msg:
                trades = msg['data']
                if isinstance(trades, list):
                    for trade in trades:
                        if trade.get('coin', '').upper() == ticker:
                            side = 'BUY' if trade.get('side') == 'B' else 'SELL'
                            price = float(trade.get('px', 0))
                            size = float(trade.get('sz', 0))
                            value = price * size
                            now = datetime.now().strftime('%H:%M:%S.%f')[:12]

                            # Track volume
                            if side == 'BUY':
                                buy_volume += value
                            else:
                                sell_volume += value
                            trade_count += 1

                            # Color indicator
                            indicator = '+' if side == 'BUY' else '-'
                            print(f"{now} {indicator}{side:5} ${price:>12,.2f} {size:>12.4f} ${value:>12,.2f}")
        except Exception as e:
            pass

    await hyp.trades_subscribe(ticker=ticker, handler=trade_handler)

    try:
        await asyncio.sleep(duration)
    except asyncio.CancelledError:
        pass

    await hyp.trades_unsubscribe(ticker=ticker)

    # Summary
    print("-" * 62)
    print(f"Trades: {trade_count} | Buy Vol: ${buy_volume:,.0f} | Sell Vol: ${sell_volume:,.0f}")
    delta = buy_volume - sell_volume
    print(f"Delta: ${delta:+,.0f} ({'buyers' if delta > 0 else 'sellers'} dominant)")
    print("=" * 60)
    await hyp.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hyp_trades.py <ticker> [seconds]")
        sys.exit(1)

    ticker = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    asyncio.run(watch_trades(ticker, duration))
