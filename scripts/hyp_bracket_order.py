#!/usr/bin/env python
"""
Bracket Order - Entry with automatic Take Profit and Stop Loss.

HOW IT WORKS:
- Places entry order (limit or market)
- Once filled, places TP and SL orders
- Monitors until one side hits, cancels the other

USAGE:
  python hyp_bracket_order.py <ticker> <side> <size> <entry> <tp_pct> <sl_pct> [--execute]

EXAMPLES:
  python hyp_bracket_order.py BTC long 0.001 80000 5 -2           # Preview
  python hyp_bracket_order.py ETH short 0.01 2600 3 -1.5 --execute  # Execute
  python hyp_bracket_order.py SOL long 1 market 4 -2 --execute      # Market entry
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


class BracketOrder:
    def __init__(self, ticker, side, size, entry, tp_pct, sl_pct):
        self.ticker = ticker.upper()
        self.side = side.lower()
        self.size = float(size)
        self.entry = entry  # Can be 'market' or price
        self.tp_pct = float(tp_pct)
        self.sl_pct = float(sl_pct)

        self.is_long = self.side in ['long', 'buy']
        self.hyp = None
        self.info = None

        # Order tracking
        self.entry_oid = None
        self.tp_oid = None
        self.entry_fill_price = None
        self.tp_price = None
        self.sl_price = None

    async def init(self):
        self.hyp = Hyperliquid(
            key=os.getenv('HYP_KEY'),
            secret=os.getenv('HYP_SECRET'),
            mode='live'
        )
        await self.hyp.init_client()
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

    async def get_current_price(self):
        mids = self.info.all_mids()
        return float(mids.get(self.ticker, 0))

    async def get_position(self):
        user_state = self.info.user_state(self.hyp.account_address)
        positions = user_state.get('assetPositions', [])

        for pos_data in positions:
            pos = pos_data.get('position', {})
            if pos.get('coin') == self.ticker:
                size = float(pos.get('szi', 0))
                if size != 0:
                    return {
                        'size': size,
                        'entry_price': float(pos.get('entryPx', 0))
                    }
        return None

    async def place_entry(self):
        """Place entry order."""
        signed_amount = self.size if self.is_long else -self.size

        if self.entry == 'market':
            result = await self.hyp.market_order(
                ticker=self.ticker,
                amount=signed_amount,
                round_size=True
            )
        else:
            result = await self.hyp.limit_order(
                ticker=self.ticker,
                amount=signed_amount,
                price=float(self.entry),
                round_price=True,
                round_size=True
            )

        return result

    async def place_tp(self):
        """Place take profit order."""
        # TP is opposite direction, reduce only
        signed_amount = -self.size if self.is_long else self.size

        result = await self.hyp.limit_order(
            ticker=self.ticker,
            amount=signed_amount,
            price=self.tp_price,
            reduce_only=True,
            round_price=True,
            round_size=True
        )

        return result

    async def close_at_market(self):
        """Close position at market (for SL)."""
        pos = await self.get_position()
        if not pos:
            return None

        signed_amount = -pos['size']

        result = await self.hyp.market_order(
            ticker=self.ticker,
            amount=signed_amount,
            reduce_only=True,
            round_size=True
        )

        return result

    async def cancel_tp(self):
        """Cancel TP order."""
        if self.tp_oid:
            try:
                await self.hyp.cancel_order(ticker=self.ticker, oid=self.tp_oid)
                return True
            except:
                return False
        return False

    async def preview(self):
        """Preview the bracket order."""
        current_price = await self.get_current_price()

        if self.entry == 'market':
            entry_price = current_price
        else:
            entry_price = float(self.entry)

        # Calculate TP and SL prices
        if self.is_long:
            self.tp_price = entry_price * (1 + self.tp_pct / 100)
            self.sl_price = entry_price * (1 + self.sl_pct / 100)  # sl_pct is negative
        else:
            self.tp_price = entry_price * (1 - self.tp_pct / 100)
            self.sl_price = entry_price * (1 - self.sl_pct / 100)

        notional = entry_price * self.size
        tp_pnl = self.size * entry_price * (self.tp_pct / 100)
        sl_pnl = self.size * entry_price * (self.sl_pct / 100)
        rr_ratio = abs(self.tp_pct / self.sl_pct)

        print("=" * 70)
        print("BRACKET ORDER PREVIEW")
        print("=" * 70)
        print(f"  Ticker:        {self.ticker}")
        print(f"  Side:          {'LONG' if self.is_long else 'SHORT'}")
        print(f"  Size:          {self.size}")
        print(f"  Current Price: ${current_price:,.2f}")
        print()
        print("ORDER LEVELS:")
        print("-" * 70)
        print(f"  Entry:    ${entry_price:,.2f} ({'MARKET' if self.entry == 'market' else 'LIMIT'})")
        print(f"  TP:       ${self.tp_price:,.2f} ({self.tp_pct:+.1f}%) -> PnL: ${tp_pnl:,.2f}")
        print(f"  SL:       ${self.sl_price:,.2f} ({self.sl_pct:+.1f}%) -> PnL: ${sl_pnl:,.2f}")
        print("-" * 70)
        print(f"  Notional:     ${notional:,.2f}")
        print(f"  Risk/Reward:  1:{rr_ratio:.2f}")
        print()

        return {
            'entry_price': entry_price,
            'tp_price': self.tp_price,
            'sl_price': self.sl_price
        }

    async def execute(self):
        """Execute the bracket order."""
        prices = await self.preview()

        print("EXECUTING...")
        print("-" * 70)

        # Step 1: Place entry
        print("  [1/2] Placing entry order...")
        result = await self.place_entry()

        if result.get('status') != 'ok':
            print(f"  [ERROR] Entry failed: {result}")
            return False

        response = result.get('response', {})
        data = response.get('data', {})
        statuses = data.get('statuses', [])

        entry_filled = False
        for s in statuses:
            if 'filled' in s:
                filled = s['filled']
                self.entry_fill_price = float(filled.get('avgPx', 0))
                print(f"  [OK] Entry FILLED @ ${self.entry_fill_price:,.2f}")
                entry_filled = True
            elif 'resting' in s:
                self.entry_oid = s['resting']['oid']
                print(f"  [OK] Entry order placed, OID: {self.entry_oid}")
                print(f"       Waiting for fill...")

                # Wait for fill
                while not entry_filled:
                    await asyncio.sleep(2)
                    pos = await self.get_position()
                    if pos:
                        self.entry_fill_price = pos['entry_price']
                        print(f"  [OK] Entry FILLED @ ${self.entry_fill_price:,.2f}")
                        entry_filled = True
                        break

        if not entry_filled:
            print("  [ERROR] Entry not filled")
            return False

        # Recalculate TP/SL based on actual fill
        if self.is_long:
            self.tp_price = self.entry_fill_price * (1 + self.tp_pct / 100)
            self.sl_price = self.entry_fill_price * (1 + self.sl_pct / 100)
        else:
            self.tp_price = self.entry_fill_price * (1 - self.tp_pct / 100)
            self.sl_price = self.entry_fill_price * (1 - self.sl_pct / 100)

        # Step 2: Place TP order
        print(f"  [2/2] Placing TP order @ ${self.tp_price:,.2f}...")
        result = await self.place_tp()

        if result.get('status') == 'ok':
            response = result.get('response', {})
            data = response.get('data', {})
            statuses = data.get('statuses', [])

            for s in statuses:
                if 'resting' in s:
                    self.tp_oid = s['resting']['oid']
                    print(f"  [OK] TP order placed, OID: {self.tp_oid}")
        else:
            print(f"  [WARN] TP order failed: {result}")

        print()
        print("MONITORING FOR TP/SL...")
        print(f"  TP: ${self.tp_price:,.2f} | SL: ${self.sl_price:,.2f}")
        print("-" * 70)

        # Monitor for TP fill or SL trigger
        try:
            while True:
                current_price = await self.get_current_price()
                pos = await self.get_position()

                # Check if position closed (TP hit)
                if not pos:
                    print(f"\n[TP HIT] Position closed @ ~${current_price:,.2f}")
                    pnl = self.size * self.entry_fill_price * (self.tp_pct / 100)
                    print(f"  Estimated PnL: ${pnl:,.2f}")
                    break

                # Check SL trigger
                sl_hit = False
                if self.is_long and current_price <= self.sl_price:
                    sl_hit = True
                elif not self.is_long and current_price >= self.sl_price:
                    sl_hit = True

                if sl_hit:
                    print(f"\n[SL TRIGGERED] Price ${current_price:,.2f}")

                    # Cancel TP order
                    await self.cancel_tp()
                    print("  TP order cancelled")

                    # Close at market
                    result = await self.close_at_market()
                    if result:
                        print("  Position closed at market")
                        pnl = self.size * self.entry_fill_price * (self.sl_pct / 100)
                        print(f"  Estimated PnL: ${pnl:,.2f}")
                    break

                now = datetime.now().strftime('%H:%M:%S')

                # Distance to TP/SL
                if self.is_long:
                    dist_tp = (self.tp_price - current_price) / current_price * 100
                    dist_sl = (current_price - self.sl_price) / current_price * 100
                else:
                    dist_tp = (current_price - self.tp_price) / current_price * 100
                    dist_sl = (self.sl_price - current_price) / current_price * 100

                upnl = pos['size'] * (current_price - self.entry_fill_price)

                print(f"{now} | ${current_price:,.2f} | TP: {dist_tp:+.2f}% | SL: {dist_sl:+.2f}% | uPnL: ${upnl:+,.2f}")

                await asyncio.sleep(5)

        except KeyboardInterrupt:
            print("\n\n[STOPPED] Monitor stopped")
            print("  Position and orders remain active!")

        return True

    async def cleanup(self):
        if self.hyp:
            await self.hyp.cleanup()


async def main(ticker, side, size, entry, tp_pct, sl_pct, execute=False):
    bracket = BracketOrder(ticker, side, size, entry, tp_pct, sl_pct)
    await bracket.init()

    try:
        if execute:
            await bracket.execute()
        else:
            await bracket.preview()
            print("[PREVIEW MODE] Add --execute to place orders")
    finally:
        await bracket.cleanup()
        print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 7:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    side = sys.argv[2]
    size = sys.argv[3]
    entry = sys.argv[4]  # 'market' or price
    tp_pct = float(sys.argv[5])
    sl_pct = float(sys.argv[6])
    execute = '--execute' in sys.argv or '-x' in sys.argv

    if entry.lower() != 'market':
        entry = float(entry)
    else:
        entry = 'market'

    asyncio.run(main(ticker, side, size, entry, tp_pct, sl_pct, execute))
