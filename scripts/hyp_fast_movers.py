#!/usr/bin/env python3
"""
Fast Market Movers - Single API call for all data.

Gets all asset data in one request instead of per-asset.
Target: <3 seconds vs 60+ seconds sequential.

Usage:
    python scripts/hyp_fast_movers.py
    python scripts/hyp_fast_movers.py --top 10
    python scripts/hyp_fast_movers.py --json
"""

import os
import sys
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any

try:
    import aiohttp
except ImportError:
    print("Install aiohttp: pip install aiohttp")
    sys.exit(1)

HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"


class FastMovers:
    def __init__(self, top_n: int = 10):
        self.top_n = top_n
        self.data: Dict[str, Any] = {}
        self.assets: List[Dict] = []

    async def fetch_all(self) -> Dict[str, Any]:
        """Fetch all market data in single request."""
        start = time.time()

        async with aiohttp.ClientSession() as session:
            # Single request gets ALL assets
            async with session.post(
                HYPERLIQUID_API,
                json={'type': 'metaAndAssetCtxs'},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                self.data['meta'] = await resp.json()

        self.data['fetch_time'] = time.time() - start
        self._parse_assets()
        return self.data

    def _parse_assets(self):
        """Parse asset data from meta response."""
        meta = self.data.get('meta', [])
        if not isinstance(meta, list) or len(meta) < 2:
            return

        universe = meta[0].get('universe', [])
        ctxs = meta[1]

        for i, asset in enumerate(universe):
            if i >= len(ctxs):
                break

            ctx = ctxs[i]
            name = asset.get('name', '')
            mark_px = float(ctx.get('markPx', 0))
            prev_day_px = float(ctx.get('prevDayPx', 0))
            day_ntl_vlm = float(ctx.get('dayNtlVlm', 0))
            oi = float(ctx.get('openInterest', 0))
            funding = float(ctx.get('funding', 0))

            if mark_px == 0 or prev_day_px == 0:
                continue

            change_pct = ((mark_px - prev_day_px) / prev_day_px) * 100

            self.assets.append({
                'name': name,
                'price': mark_px,
                'prev_price': prev_day_px,
                'change_pct': change_pct,
                'volume': day_ntl_vlm,
                'oi': oi * mark_px,  # OI in USD
                'funding': funding,
            })

    def get_gainers(self) -> List[Dict]:
        """Get top gainers."""
        return sorted(self.assets, key=lambda x: x['change_pct'], reverse=True)[:self.top_n]

    def get_losers(self) -> List[Dict]:
        """Get top losers."""
        return sorted(self.assets, key=lambda x: x['change_pct'])[:self.top_n]

    def get_volume_leaders(self) -> List[Dict]:
        """Get top by volume."""
        return sorted(self.assets, key=lambda x: x['volume'], reverse=True)[:self.top_n]

    def get_summary(self) -> Dict:
        """Get market summary."""
        total_volume = sum(a['volume'] for a in self.assets)
        avg_change = sum(a['change_pct'] for a in self.assets) / len(self.assets) if self.assets else 0
        gainers = sum(1 for a in self.assets if a['change_pct'] > 0)
        losers = len(self.assets) - gainers

        return {
            'total_volume': total_volume,
            'avg_change': avg_change,
            'gainers': gainers,
            'losers': losers,
            'total_assets': len(self.assets),
        }

    def generate_report(self, as_json: bool = False) -> str:
        """Generate movers report."""
        gainers = self.get_gainers()
        losers = self.get_losers()
        volume_leaders = self.get_volume_leaders()
        summary = self.get_summary()

        if as_json:
            return json.dumps({
                'timestamp': datetime.now().isoformat(),
                'fetch_time': self.data.get('fetch_time', 0),
                'summary': summary,
                'gainers': gainers,
                'losers': losers,
                'volume_leaders': volume_leaders,
            }, indent=2)

        lines = []
        lines.append("=" * 70)
        lines.append(f"FAST MARKET MOVERS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Fetched in {self.data.get('fetch_time', 0):.2f}s")
        lines.append("=" * 70)

        # Gainers
        lines.append(f"\nTOP {self.top_n} GAINERS:")
        lines.append(f"  {'Ticker':<12} {'Price':>14} {'Change':>10} {'Volume':>16}")
        lines.append("-" * 70)
        for a in gainers:
            lines.append(f"  {a['name']:<12} ${a['price']:>12,.4f} {a['change_pct']:>+9.2f}% ${a['volume']:>14,.0f}")

        # Losers
        lines.append(f"\nTOP {self.top_n} LOSERS:")
        lines.append(f"  {'Ticker':<12} {'Price':>14} {'Change':>10} {'Volume':>16}")
        lines.append("-" * 70)
        for a in losers:
            lines.append(f"  {a['name']:<12} ${a['price']:>12,.4f} {a['change_pct']:>+9.2f}% ${a['volume']:>14,.0f}")

        # Volume leaders
        lines.append(f"\nTOP {self.top_n} BY VOLUME:")
        lines.append(f"  {'Ticker':<12} {'Price':>14} {'Change':>10} {'Volume':>16}")
        lines.append("-" * 70)
        for a in volume_leaders:
            lines.append(f"  {a['name']:<12} ${a['price']:>12,.4f} {a['change_pct']:>+9.2f}% ${a['volume']:>14,.0f}")

        # Summary
        lines.append(f"\nMARKET SUMMARY:")
        lines.append("-" * 70)
        lines.append(f"  Total 24h Volume: ${summary['total_volume']:>18,.0f}")
        lines.append(f"  Average Change:   {summary['avg_change']:>18.2f}%")
        lines.append(f"  Gainers/Losers:   {summary['gainers']:>8}/{summary['losers']}")
        lines.append("=" * 70)

        return "\n".join(lines)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fast Market Movers')
    parser.add_argument('--top', type=int, default=10, help='Number of top movers to show')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    movers = FastMovers(top_n=args.top)
    await movers.fetch_all()
    print(movers.generate_report(as_json=args.json))


if __name__ == '__main__':
    asyncio.run(main())
