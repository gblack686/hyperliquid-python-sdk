#!/usr/bin/env python3
"""
Binance Liquidation Stream - Real-time liquidations via WebSocket.

Streams all liquidation events from Binance Futures and:
- Shows real-time liquidation feed
- Aggregates liquidation data by price level
- Tracks cumulative liquidations by direction

Usage:
    python scripts/binance_liq_stream.py                  # Stream all
    python scripts/binance_liq_stream.py --symbols BTC SOL  # Filter symbols
    python scripts/binance_liq_stream.py --duration 300   # Run for 5 min
    python scripts/binance_liq_stream.py --aggregate      # Show aggregated view
    python scripts/binance_liq_stream.py --min-value 10000  # Min $10k liquidations
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

BINANCE_WS = "wss://fstream.binance.com/ws"
LIQUIDATION_STREAM = "!forceOrder@arr"

# Symbol mapping for filtering
WATCH_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT']


class LiquidationAggregator:
    """Aggregates liquidation data for analysis."""

    def __init__(self):
        self.liquidations: List[Dict] = []
        self.by_symbol: Dict[str, Dict] = defaultdict(lambda: {
            'long_count': 0, 'long_value': 0,
            'short_count': 0, 'short_value': 0,
        })
        self.by_price_level: Dict[str, Dict[float, float]] = defaultdict(lambda: defaultdict(float))
        self.start_time = time.time()

    def add(self, liq: Dict):
        """Add a liquidation event."""
        self.liquidations.append(liq)

        symbol = liq['symbol']
        value = liq['value_usd']
        liq_type = liq['type']

        # Aggregate by symbol
        if liq_type == 'LONG_LIQ':
            self.by_symbol[symbol]['long_count'] += 1
            self.by_symbol[symbol]['long_value'] += value
        else:
            self.by_symbol[symbol]['short_count'] += 1
            self.by_symbol[symbol]['short_value'] += value

        # Aggregate by price level (bucket to nearest 0.5%)
        price = liq['price']
        bucket = round(price, -int(len(str(int(price))) - 2))  # Round to significant figures
        self.by_price_level[symbol][bucket] += value

    def summary(self) -> str:
        """Generate summary report."""
        duration = time.time() - self.start_time
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append(f"LIQUIDATION SUMMARY ({duration:.0f}s)")
        lines.append("=" * 70)

        total_long = sum(s['long_value'] for s in self.by_symbol.values())
        total_short = sum(s['short_value'] for s in self.by_symbol.values())

        lines.append(f"\n  Total Long Liquidations:  ${total_long:>15,.2f}")
        lines.append(f"  Total Short Liquidations: ${total_short:>15,.2f}")
        lines.append(f"  Net (Long - Short):       ${total_long - total_short:>+15,.2f}")

        if self.by_symbol:
            lines.append(f"\n  BY SYMBOL:")
            lines.append(f"  {'Symbol':<12} {'Long Liqs':>12} {'Long $':>15} {'Short Liqs':>12} {'Short $':>15}")
            lines.append("  " + "-" * 66)

            for symbol, data in sorted(self.by_symbol.items(), key=lambda x: x[1]['long_value'] + x[1]['short_value'], reverse=True):
                lines.append(
                    f"  {symbol:<12} {data['long_count']:>12} ${data['long_value']:>14,.0f} "
                    f"{data['short_count']:>12} ${data['short_value']:>14,.0f}"
                )

        lines.append("=" * 70)
        return "\n".join(lines)


class BinanceLiquidationStream:
    """Stream real-time liquidations from Binance."""

    def __init__(self, symbols: List[str] = None, min_value: float = 0, aggregate: bool = False):
        self.filter_symbols = [s.upper() if s.upper().endswith('USDT') else f'{s.upper()}USDT'
                              for s in (symbols or [])]
        self.min_value = min_value
        self.aggregate = aggregate
        self.aggregator = LiquidationAggregator() if aggregate else None
        self.running = True
        self.count = 0

    def parse_liquidation(self, data: Dict) -> Optional[Dict]:
        """Parse liquidation order from websocket message."""
        try:
            order = data.get('o', {})
            symbol = order.get('s', '')
            side = order.get('S', '')  # SELL = long liq, BUY = short liq
            price = float(order.get('p', 0))
            qty = float(order.get('q', 0))
            value_usd = price * qty

            # Filter by symbol if specified
            if self.filter_symbols and symbol not in self.filter_symbols:
                return None

            # Filter by minimum value
            if value_usd < self.min_value:
                return None

            liq_type = 'LONG_LIQ' if side == 'SELL' else 'SHORT_LIQ'

            return {
                'time': datetime.fromtimestamp(order.get('T', 0) / 1000),
                'symbol': symbol,
                'type': liq_type,
                'side': side,
                'price': price,
                'qty': qty,
                'value_usd': value_usd,
            }
        except Exception as e:
            return None

    def format_liquidation(self, liq: Dict) -> str:
        """Format liquidation for display."""
        # Color coding (ANSI) - red for long liqs, green for short liqs
        if liq['type'] == 'LONG_LIQ':
            color = '\033[91m'  # Red
            direction = 'LONG'
        else:
            color = '\033[92m'  # Green
            direction = 'SHORT'
        reset = '\033[0m'

        symbol = liq['symbol'].replace('USDT', '').replace('1000', '')

        # Size indicator
        value = liq['value_usd']
        if value >= 1000000:
            size_indicator = ' [WHALE]'
        elif value >= 100000:
            size_indicator = ' [LARGE]'
        elif value >= 10000:
            size_indicator = ''
        else:
            size_indicator = ''

        return (
            f"{color}{liq['time'].strftime('%H:%M:%S')} "
            f"{symbol:<6} {direction:<5} "
            f"${liq['price']:>12,.4f} x {liq['qty']:>12,.4f} = "
            f"${value:>12,.2f}{size_indicator}{reset}"
        )

    async def stream(self, duration: int = None):
        """Start streaming liquidations."""
        uri = f"{BINANCE_WS}/{LIQUIDATION_STREAM}"
        start_time = time.time()

        print("=" * 70)
        print(f"BINANCE LIQUIDATION STREAM")
        print(f"Filters: {self.filter_symbols if self.filter_symbols else 'ALL'}")
        print(f"Min Value: ${self.min_value:,.0f}" if self.min_value > 0 else "Min Value: None")
        print(f"Duration: {duration}s" if duration else "Duration: Until stopped (Ctrl+C)")
        print("=" * 70)
        print(f"{'Time':<10} {'Symbol':<6} {'Type':<5} {'Price':>14} {'Qty':>14} {'Value':>14}")
        print("-" * 70)

        try:
            async with websockets.connect(uri) as ws:
                while self.running:
                    # Check duration
                    if duration and (time.time() - start_time) >= duration:
                        break

                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)

                        liq = self.parse_liquidation(data)
                        if liq:
                            self.count += 1
                            print(self.format_liquidation(liq))

                            if self.aggregator:
                                self.aggregator.add(liq)

                    except asyncio.TimeoutError:
                        # No liquidation in last 5s, continue
                        continue

        except websockets.exceptions.ConnectionClosed:
            print("\nConnection closed")
        except KeyboardInterrupt:
            print("\nStopped by user")
        finally:
            self.running = False

        # Print summary
        print(f"\n{'-' * 70}")
        print(f"Total liquidations received: {self.count}")

        if self.aggregator:
            print(self.aggregator.summary())

    def stop(self):
        """Stop the stream."""
        self.running = False


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Binance Liquidation Stream')
    parser.add_argument('--symbols', '-s', nargs='*', help='Filter by symbols (e.g., BTC SOL)')
    parser.add_argument('--duration', '-d', type=int, help='Run for N seconds')
    parser.add_argument('--min-value', '-m', type=float, default=0, help='Minimum liquidation value USD')
    parser.add_argument('--aggregate', '-a', action='store_true', help='Show aggregated summary at end')
    args = parser.parse_args()

    stream = BinanceLiquidationStream(
        symbols=args.symbols,
        min_value=args.min_value,
        aggregate=args.aggregate,
    )

    await stream.stream(duration=args.duration)


if __name__ == '__main__':
    asyncio.run(main())
