#!/usr/bin/env python3
"""
Liquidity Levels Analyzer - Identify key liquidity zones for order placement.

Analyzes orderbook depth, volume profile, and historical price action to find:
- Liquidity pools (where stops/liquidations cluster)
- High volume nodes (HVN) - areas of acceptance
- Low volume nodes (LVN) - areas price moves quickly through
- Suggested TP and SL levels based on liquidity

Usage:
    python scripts/hyp_liquidity_levels.py BTC
    python scripts/hyp_liquidity_levels.py SOL --depth 50
    python scripts/hyp_liquidity_levels.py XRP --json
"""

import os
import sys
import json
import asyncio
import time
import math
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

try:
    import aiohttp
except ImportError:
    print("Install aiohttp: pip install aiohttp")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"


class LiquidityAnalyzer:
    def __init__(self, ticker: str, depth_pct: float = 5.0):
        """
        Args:
            ticker: Asset symbol (e.g., BTC, SOL)
            depth_pct: How far from current price to analyze (default 5%)
        """
        self.ticker = ticker.upper()
        self.depth_pct = depth_pct
        self.data: Dict[str, Any] = {}
        self.current_price: float = 0
        self.orderbook: Dict[str, List] = {'bids': [], 'asks': []}
        self.candles: List[Dict] = []

    async def fetch_all(self) -> Dict[str, Any]:
        """Fetch orderbook and candle data in parallel."""
        start = time.time()

        async with aiohttp.ClientSession() as session:
            tasks = {
                'meta': self._post(session, HYPERLIQUID_API, {'type': 'metaAndAssetCtxs'}),
                'l2': self._post(session, HYPERLIQUID_API, {
                    'type': 'l2Book',
                    'coin': self.ticker,
                    'nSigFigs': 5,
                }),
                'candles_15m': self._fetch_candles(session, '15m', 200),
                'candles_1h': self._fetch_candles(session, '1h', 100),
                'candles_4h': self._fetch_candles(session, '4h', 50),
            }

            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for i, key in enumerate(tasks.keys()):
                self.data[key] = results[i] if not isinstance(results[i], Exception) else {'error': str(results[i])}

        self._parse_data()
        self.data['fetch_time'] = time.time() - start
        return self.data

    async def _post(self, session: aiohttp.ClientSession, url: str, data: dict):
        try:
            async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                return await resp.json()
        except Exception as e:
            return {'error': str(e)}

    async def _fetch_candles(self, session: aiohttp.ClientSession, interval: str, count: int):
        now_ms = int(time.time() * 1000)
        tf_ms = {'15m': 15*60*1000, '1h': 60*60*1000, '4h': 4*60*60*1000}
        interval_ms = tf_ms.get(interval, 60*60*1000)
        start_time = now_ms - (count * interval_ms)

        return await self._post(session, HYPERLIQUID_API, {
            'type': 'candleSnapshot',
            'req': {
                'coin': self.ticker,
                'interval': interval,
                'startTime': start_time,
                'endTime': now_ms,
            }
        })

    def _parse_data(self):
        """Parse fetched data."""
        # Get current price
        meta = self.data.get('meta', [])
        if isinstance(meta, list) and len(meta) > 1:
            universe = meta[0].get('universe', [])
            ctxs = meta[1]
            for i, asset in enumerate(universe):
                if asset.get('name') == self.ticker and i < len(ctxs):
                    self.current_price = float(ctxs[i].get('markPx', 0))
                    break

        # Parse orderbook
        l2 = self.data.get('l2', {})
        if 'levels' in l2:
            levels = l2['levels']
            if len(levels) >= 2:
                self.orderbook['bids'] = [(float(p['px']), float(p['sz'])) for p in levels[0]]
                self.orderbook['asks'] = [(float(p['px']), float(p['sz'])) for p in levels[1]]

        # Aggregate candles for volume profile
        for tf in ['candles_15m', 'candles_1h', 'candles_4h']:
            candles = self.data.get(tf, [])
            if isinstance(candles, list):
                self.candles.extend(candles)

    def analyze_orderbook_liquidity(self) -> Dict[str, Any]:
        """Analyze orderbook for liquidity clusters."""
        if not self.current_price:
            return {'error': 'No price data'}

        # Define price range to analyze
        price_range = self.current_price * (self.depth_pct / 100)
        min_price = self.current_price - price_range
        max_price = self.current_price + price_range

        # Bucket orderbook into price levels
        bucket_size = self.current_price * 0.001  # 0.1% buckets
        bid_buckets = defaultdict(float)
        ask_buckets = defaultdict(float)

        for price, size in self.orderbook['bids']:
            if price >= min_price:
                bucket = round(price / bucket_size) * bucket_size
                bid_buckets[bucket] += size * price  # USD value

        for price, size in self.orderbook['asks']:
            if price <= max_price:
                bucket = round(price / bucket_size) * bucket_size
                ask_buckets[bucket] += size * price  # USD value

        # Find liquidity clusters (top buckets by value)
        bid_levels = sorted(bid_buckets.items(), key=lambda x: x[1], reverse=True)[:10]
        ask_levels = sorted(ask_buckets.items(), key=lambda x: x[1], reverse=True)[:10]

        # Calculate cumulative liquidity at each level
        cumulative_bids = []
        running_total = 0
        for price, size in sorted(self.orderbook['bids'], reverse=True):
            if price >= min_price:
                running_total += size * price
                cumulative_bids.append((price, running_total))

        cumulative_asks = []
        running_total = 0
        for price, size in sorted(self.orderbook['asks']):
            if price <= max_price:
                running_total += size * price
                cumulative_asks.append((price, running_total))

        return {
            'bid_clusters': [(p, v) for p, v in bid_levels if v > 0],
            'ask_clusters': [(p, v) for p, v in ask_levels if v > 0],
            'total_bid_liquidity': sum(v for _, v in bid_levels),
            'total_ask_liquidity': sum(v for _, v in ask_levels),
            'cumulative_bids': cumulative_bids[:20],
            'cumulative_asks': cumulative_asks[:20],
        }

    def analyze_volume_profile(self) -> Dict[str, Any]:
        """Build volume profile from historical candles."""
        if not self.candles or not self.current_price:
            return {'error': 'No candle data'}

        # Build volume profile (price -> volume mapping)
        price_range = self.current_price * (self.depth_pct / 100)
        bucket_size = self.current_price * 0.005  # 0.5% buckets for volume profile

        volume_profile = defaultdict(float)

        for candle in self.candles:
            try:
                high = float(candle['h'])
                low = float(candle['l'])
                close = float(candle['c'])
                volume = float(candle['v'])

                # Distribute volume across price range (simplified)
                # In reality, you'd use tick data, but this approximates
                mid = (high + low) / 2
                bucket = round(mid / bucket_size) * bucket_size

                # Weight by how close to current price
                if abs(bucket - self.current_price) <= price_range:
                    volume_profile[bucket] += volume
            except (KeyError, ValueError):
                continue

        if not volume_profile:
            return {'error': 'Could not build volume profile'}

        # Sort by volume to find HVN and LVN
        sorted_profile = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)

        # High Volume Nodes (top 20%)
        hvn_count = max(1, len(sorted_profile) // 5)
        hvn = sorted_profile[:hvn_count]

        # Low Volume Nodes (bottom 20%)
        lvn = sorted_profile[-hvn_count:] if len(sorted_profile) > hvn_count else []

        # Point of Control (POC) - highest volume price
        poc = sorted_profile[0] if sorted_profile else (self.current_price, 0)

        # Value Area (70% of volume)
        total_volume = sum(v for _, v in sorted_profile)
        target_volume = total_volume * 0.7
        accumulated = 0
        value_area_prices = []

        for price, vol in sorted_profile:
            accumulated += vol
            value_area_prices.append(price)
            if accumulated >= target_volume:
                break

        value_area_high = max(value_area_prices) if value_area_prices else self.current_price
        value_area_low = min(value_area_prices) if value_area_prices else self.current_price

        return {
            'poc': poc[0],
            'poc_volume': poc[1],
            'value_area_high': value_area_high,
            'value_area_low': value_area_low,
            'hvn': hvn[:5],  # Top 5 high volume nodes
            'lvn': lvn[:5],  # Top 5 low volume nodes
            'profile': dict(sorted_profile[:20]),  # Top 20 levels
        }

    def find_liquidation_levels(self) -> Dict[str, Any]:
        """Estimate where liquidations might cluster based on common leverage."""
        if not self.current_price:
            return {'error': 'No price data'}

        # Common leverage levels and their liquidation distances
        # Liquidation price = Entry * (1 - 1/leverage) for longs
        # Liquidation price = Entry * (1 + 1/leverage) for shorts
        leverage_levels = [5, 10, 20, 25, 50, 100]

        long_liquidations = []
        short_liquidations = []

        for lev in leverage_levels:
            # If longs entered at current price, where would they liquidate?
            long_liq = self.current_price * (1 - 1/lev)
            # If shorts entered at current price, where would they liquidate?
            short_liq = self.current_price * (1 + 1/lev)

            long_liquidations.append({
                'leverage': lev,
                'price': long_liq,
                'distance_pct': (self.current_price - long_liq) / self.current_price * 100,
            })
            short_liquidations.append({
                'leverage': lev,
                'price': short_liq,
                'distance_pct': (short_liq - self.current_price) / self.current_price * 100,
            })

        return {
            'long_liquidations': long_liquidations,
            'short_liquidations': short_liquidations,
        }

    def suggest_order_levels(self, position_side: str = 'SHORT') -> Dict[str, Any]:
        """Suggest TP and SL levels based on liquidity analysis."""
        ob_analysis = self.analyze_orderbook_liquidity()
        vp_analysis = self.analyze_volume_profile()
        liq_analysis = self.find_liquidation_levels()

        if 'error' in ob_analysis or 'error' in vp_analysis:
            return {'error': 'Insufficient data for analysis'}

        suggestions = {
            'position_side': position_side,
            'current_price': self.current_price,
            'take_profits': [],
            'stop_losses': [],
            'rationale': [],
        }

        if position_side.upper() == 'SHORT':
            # For shorts: TP is below current price, SL is above

            # TP levels - look for bid liquidity clusters (where buyers are)
            bid_clusters = sorted(ob_analysis['bid_clusters'], key=lambda x: x[0], reverse=True)
            for price, liquidity in bid_clusters[:3]:
                if price < self.current_price:
                    pct_gain = (self.current_price - price) / self.current_price * 100
                    suggestions['take_profits'].append({
                        'price': price,
                        'gain_pct': pct_gain,
                        'liquidity_usd': liquidity,
                        'type': 'bid_cluster',
                    })

            # Add HVN below price as TP targets
            for price, volume in vp_analysis.get('hvn', []):
                if price < self.current_price * 0.99:  # At least 1% below
                    pct_gain = (self.current_price - price) / self.current_price * 100
                    suggestions['take_profits'].append({
                        'price': price,
                        'gain_pct': pct_gain,
                        'volume': volume,
                        'type': 'high_volume_node',
                    })

            # SL levels - look for ask liquidity (resistance) or liquidation clusters
            ask_clusters = sorted(ob_analysis['ask_clusters'], key=lambda x: x[0])
            for price, liquidity in ask_clusters[:2]:
                if price > self.current_price:
                    pct_loss = (price - self.current_price) / self.current_price * 100
                    suggestions['stop_losses'].append({
                        'price': price,
                        'loss_pct': pct_loss,
                        'liquidity_usd': liquidity,
                        'type': 'ask_cluster',
                    })

            # Add VAH as potential SL (price tends to revert from VA)
            vah = vp_analysis.get('value_area_high', 0)
            if vah > self.current_price:
                pct_loss = (vah - self.current_price) / self.current_price * 100
                suggestions['stop_losses'].append({
                    'price': vah,
                    'loss_pct': pct_loss,
                    'type': 'value_area_high',
                })

        else:  # LONG
            # For longs: TP is above current price, SL is below

            # TP levels - look for ask clusters (where sellers are)
            ask_clusters = sorted(ob_analysis['ask_clusters'], key=lambda x: x[0])
            for price, liquidity in ask_clusters[:3]:
                if price > self.current_price:
                    pct_gain = (price - self.current_price) / self.current_price * 100
                    suggestions['take_profits'].append({
                        'price': price,
                        'gain_pct': pct_gain,
                        'liquidity_usd': liquidity,
                        'type': 'ask_cluster',
                    })

            # SL levels - look for bid liquidity or VAL
            bid_clusters = sorted(ob_analysis['bid_clusters'], key=lambda x: x[0], reverse=True)
            for price, liquidity in bid_clusters[:2]:
                if price < self.current_price:
                    pct_loss = (self.current_price - price) / self.current_price * 100
                    suggestions['stop_losses'].append({
                        'price': price,
                        'loss_pct': pct_loss,
                        'liquidity_usd': liquidity,
                        'type': 'bid_cluster',
                    })

            val = vp_analysis.get('value_area_low', 0)
            if val < self.current_price and val > 0:
                pct_loss = (self.current_price - val) / self.current_price * 100
                suggestions['stop_losses'].append({
                    'price': val,
                    'loss_pct': pct_loss,
                    'type': 'value_area_low',
                })

        # Sort and dedupe
        suggestions['take_profits'] = sorted(
            suggestions['take_profits'],
            key=lambda x: x['gain_pct'],
            reverse=True
        )[:5]

        suggestions['stop_losses'] = sorted(
            suggestions['stop_losses'],
            key=lambda x: x['loss_pct']
        )[:3]

        # Add key levels summary
        suggestions['key_levels'] = {
            'poc': vp_analysis.get('poc'),
            'value_area_high': vp_analysis.get('value_area_high'),
            'value_area_low': vp_analysis.get('value_area_low'),
        }

        return suggestions

    def generate_report(self, position_side: str = 'SHORT', as_json: bool = False) -> str:
        """Generate liquidity analysis report."""
        ob = self.analyze_orderbook_liquidity()
        vp = self.analyze_volume_profile()
        liq = self.find_liquidation_levels()
        suggestions = self.suggest_order_levels(position_side)

        # Handle errors
        if not isinstance(ob, dict):
            ob = {'error': 'Failed to analyze orderbook'}
        if not isinstance(vp, dict):
            vp = {'error': 'Failed to analyze volume profile'}
        if not isinstance(liq, dict):
            liq = {'long_liquidations': [], 'short_liquidations': []}
        if not isinstance(suggestions, dict):
            suggestions = {'error': 'Failed to generate suggestions'}

        if as_json:
            return json.dumps({
                'ticker': self.ticker,
                'current_price': self.current_price,
                'fetch_time': self.data.get('fetch_time', 0),
                'orderbook_analysis': ob,
                'volume_profile': vp,
                'liquidation_levels': liq,
                'suggestions': suggestions,
            }, indent=2)

        lines = []
        lines.append("=" * 75)
        lines.append(f"LIQUIDITY LEVELS - {self.ticker}")
        lines.append(f"Current Price: ${self.current_price:,.4f} | Analysis Depth: +/-{self.depth_pct}%")
        lines.append(f"Fetched in {self.data.get('fetch_time', 0):.2f}s")
        lines.append("=" * 75)

        # Volume Profile
        lines.append(f"\n{'VOLUME PROFILE':^75}")
        lines.append("-" * 75)
        if 'error' not in vp:
            poc = vp.get('poc', 0)
            vah = vp.get('value_area_high', 0)
            val = vp.get('value_area_low', 0)

            poc_dist = (poc - self.current_price) / self.current_price * 100
            vah_dist = (vah - self.current_price) / self.current_price * 100
            val_dist = (val - self.current_price) / self.current_price * 100

            lines.append(f"  Point of Control (POC):  ${poc:>12,.4f}  ({poc_dist:+.2f}%)")
            lines.append(f"  Value Area High (VAH):   ${vah:>12,.4f}  ({vah_dist:+.2f}%)")
            lines.append(f"  Value Area Low (VAL):    ${val:>12,.4f}  ({val_dist:+.2f}%)")

            lines.append(f"\n  High Volume Nodes (Support/Resistance):")
            for price, vol in vp.get('hvn', [])[:5]:
                dist = (price - self.current_price) / self.current_price * 100
                lines.append(f"    ${price:>12,.4f}  ({dist:+.2f}%)  Vol: {vol:,.0f}")

        # Orderbook Liquidity
        lines.append(f"\n{'ORDERBOOK LIQUIDITY':^75}")
        lines.append("-" * 75)
        if 'error' not in ob:
            total_bids = ob.get('total_bid_liquidity', 0)
            total_asks = ob.get('total_ask_liquidity', 0)
            imbalance = (total_bids - total_asks) / (total_bids + total_asks) * 100 if (total_bids + total_asks) > 0 else 0

            lines.append(f"  Total Bid Liquidity:  ${total_bids:>15,.0f}")
            lines.append(f"  Total Ask Liquidity:  ${total_asks:>15,.0f}")
            lines.append(f"  Imbalance:            {imbalance:>15.1f}% {'(BID heavy)' if imbalance > 0 else '(ASK heavy)'}")

            lines.append(f"\n  Top Bid Clusters (Support):")
            for price, liquidity in sorted(ob.get('bid_clusters', []), key=lambda x: x[0], reverse=True)[:5]:
                dist = (price - self.current_price) / self.current_price * 100
                lines.append(f"    ${price:>12,.4f}  ({dist:+.2f}%)  Liq: ${liquidity:>12,.0f}")

            lines.append(f"\n  Top Ask Clusters (Resistance):")
            for price, liquidity in sorted(ob.get('ask_clusters', []), key=lambda x: x[0])[:5]:
                dist = (price - self.current_price) / self.current_price * 100
                lines.append(f"    ${price:>12,.4f}  ({dist:+.2f}%)  Liq: ${liquidity:>12,.0f}")

        # Liquidation Estimates
        lines.append(f"\n{'LIQUIDATION ESTIMATES':^75}")
        lines.append("-" * 75)
        lines.append(f"  Long Liquidations (if entered at current price):")
        for l in liq.get('long_liquidations', [])[:4]:
            lines.append(f"    {l['leverage']:>3}x: ${l['price']:>12,.4f}  ({l['distance_pct']:>+.1f}%)")

        lines.append(f"\n  Short Liquidations (if entered at current price):")
        for l in liq.get('short_liquidations', [])[:4]:
            lines.append(f"    {l['leverage']:>3}x: ${l['price']:>12,.4f}  ({l['distance_pct']:>+.1f}%)")

        # Order Suggestions
        lines.append(f"\n{'SUGGESTED ORDER LEVELS':^75}")
        lines.append(f"Position: {position_side}")
        lines.append("-" * 75)

        if 'error' not in suggestions:
            lines.append(f"\n  TAKE PROFIT Levels:")
            for tp in suggestions.get('take_profits', []):
                tp_type = tp.get('type', 'unknown')
                lines.append(f"    ${tp['price']:>12,.4f}  (+{tp['gain_pct']:.2f}%)  [{tp_type}]")

            lines.append(f"\n  STOP LOSS Levels:")
            for sl in suggestions.get('stop_losses', []):
                sl_type = sl.get('type', 'unknown')
                lines.append(f"    ${sl['price']:>12,.4f}  (-{sl['loss_pct']:.2f}%)  [{sl_type}]")

            # Key levels summary
            key = suggestions.get('key_levels', {})
            lines.append(f"\n  KEY LEVELS SUMMARY:")
            lines.append(f"    POC: ${key.get('poc', 0):,.4f}")
            lines.append(f"    VAH: ${key.get('value_area_high', 0):,.4f}")
            lines.append(f"    VAL: ${key.get('value_area_low', 0):,.4f}")

        lines.append("\n" + "=" * 75)
        return "\n".join(lines)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Liquidity Levels Analyzer')
    parser.add_argument('ticker', help='Ticker symbol (e.g., BTC, SOL)')
    parser.add_argument('--depth', type=float, default=5.0, help='Analysis depth in %% (default: 5)')
    parser.add_argument('--side', choices=['LONG', 'SHORT'], default='SHORT', help='Position side for suggestions')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    analyzer = LiquidityAnalyzer(args.ticker, depth_pct=args.depth)
    await analyzer.fetch_all()
    print(analyzer.generate_report(position_side=args.side, as_json=args.json))


if __name__ == '__main__':
    asyncio.run(main())
