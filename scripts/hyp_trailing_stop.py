#!/usr/bin/env python
"""
Trailing Stop - Follows price movement to lock in profits.

HOW IT WORKS:
- For LONG positions: Stop trails below the highest price reached
- For SHORT positions: Stop trails above the lowest price reached
- When price reverses by trail_pct, position is closed at market

USAGE:
  python hyp_trailing_stop.py <ticker> <trail_pct> [--interval=5]

EXAMPLES:
  python hyp_trailing_stop.py BTC 2.0           # 2% trailing stop
  python hyp_trailing_stop.py ETH 1.5 --interval=3  # 1.5% trail, check every 3s
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants


class TrailingStop:
    def __init__(self, ticker, trail_pct, interval=5):
        self.ticker = ticker.upper()
        self.trail_pct = float(trail_pct) / 100  # Convert to decimal
        self.interval = interval
        self.hyp = None
        self.info = None

        # Tracking
        self.position_side = None  # 'long' or 'short'
        self.position_size = 0
        self.entry_price = 0
        self.best_price = None  # Highest for long, lowest for short
        self.stop_price = None
        self.triggered = False

    async def init(self):
        self.hyp = Hyperliquid(
            key=os.getenv('HYP_KEY'),
            secret=os.getenv('HYP_SECRET'),
            mode='live'
        )
        await self.hyp.init_client()
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

    async def get_position(self):
        """Get current position for ticker."""
        user_state = self.info.user_state(self.hyp.account_address)
        positions = user_state.get('assetPositions', [])

        for pos_data in positions:
            pos = pos_data.get('position', {})
            if pos.get('coin') == self.ticker:
                size = float(pos.get('szi', 0))
                if size != 0:
                    return {
                        'size': size,
                        'side': 'long' if size > 0 else 'short',
                        'entry_price': float(pos.get('entryPx', 0)),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0))
                    }
        return None

    async def get_current_price(self):
        """Get current mark price."""
        mids = self.info.all_mids()
        return float(mids.get(self.ticker, 0))

    def calculate_stop(self, current_price):
        """Calculate trailing stop price."""
        if self.position_side == 'long':
            # For longs, stop is below best price
            if self.best_price is None or current_price > self.best_price:
                self.best_price = current_price
            self.stop_price = self.best_price * (1 - self.trail_pct)
        else:
            # For shorts, stop is above best (lowest) price
            if self.best_price is None or current_price < self.best_price:
                self.best_price = current_price
            self.stop_price = self.best_price * (1 + self.trail_pct)

    def should_trigger(self, current_price):
        """Check if stop should trigger."""
        if self.position_side == 'long':
            return current_price <= self.stop_price
        else:
            return current_price >= self.stop_price

    async def close_position(self):
        """Close position at market."""
        try:
            close_amount = -self.position_size  # Opposite direction
            result = await self.hyp.market_order(
                ticker=self.ticker,
                amount=close_amount,
                reduce_only=True,
                round_size=True
            )
            return result
        except Exception as e:
            print(f"[ERROR] Close failed: {e}")
            return None

    async def run(self):
        """Main trailing stop loop."""
        await self.init()

        print("=" * 70)
        print("TRAILING STOP MONITOR")
        print("=" * 70)
        print(f"  Ticker:     {self.ticker}")
        print(f"  Trail %:    {self.trail_pct * 100:.2f}%")
        print(f"  Interval:   {self.interval}s")
        print()

        # Check for existing position
        position = await self.get_position()
        if not position:
            print(f"[ERROR] No open position for {self.ticker}")
            await self.hyp.cleanup()
            return

        self.position_side = position['side']
        self.position_size = position['size']
        self.entry_price = position['entry_price']

        print(f"  Position:   {self.position_side.upper()} {abs(self.position_size)}")
        print(f"  Entry:      ${self.entry_price:,.2f}")
        print()
        print("Starting trailing stop monitor...")
        print("-" * 70)

        try:
            while not self.triggered:
                current_price = await self.get_current_price()

                # Calculate/update trailing stop
                self.calculate_stop(current_price)

                # Calculate P&L
                if self.position_side == 'long':
                    pnl = (current_price - self.entry_price) * abs(self.position_size)
                    distance = (current_price - self.stop_price) / current_price * 100
                else:
                    pnl = (self.entry_price - current_price) * abs(self.position_size)
                    distance = (self.stop_price - current_price) / current_price * 100

                # Status line
                now = datetime.now().strftime('%H:%M:%S')
                print(f"{now} | Price: ${current_price:,.2f} | Best: ${self.best_price:,.2f} | "
                      f"Stop: ${self.stop_price:,.2f} | Dist: {distance:.2f}% | PnL: ${pnl:+,.2f}")

                # Check trigger
                if self.should_trigger(current_price):
                    print()
                    print("=" * 70)
                    print("[TRIGGERED] Trailing stop hit!")
                    print("=" * 70)
                    print(f"  Trigger Price: ${current_price:,.2f}")
                    print(f"  Stop Price:    ${self.stop_price:,.2f}")
                    print(f"  Best Price:    ${self.best_price:,.2f}")
                    print()
                    print("Closing position at market...")

                    result = await self.close_position()
                    if result and result.get('status') == 'ok':
                        print("[SUCCESS] Position closed!")

                        # Get fill info
                        response = result.get('response', {})
                        data = response.get('data', {})
                        statuses = data.get('statuses', [])
                        for s in statuses:
                            if 'filled' in s:
                                filled = s['filled']
                                print(f"  Fill Price: ${float(filled.get('avgPx', 0)):,.2f}")
                                print(f"  Fill Size:  {filled.get('totalSz', 'N/A')}")
                    else:
                        print(f"[ERROR] Close result: {result}")

                    self.triggered = True
                    break

                await asyncio.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\n[STOPPED] Trailing stop monitor stopped by user")
            print("Position remains open - manage manually!")

        finally:
            await self.hyp.cleanup()
            print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    trail_pct = float(sys.argv[2])
    interval = 5

    for arg in sys.argv[3:]:
        if arg.startswith('--interval='):
            interval = int(arg.split('=')[1])

    ts = TrailingStop(ticker, trail_pct, interval)
    asyncio.run(ts.run())
