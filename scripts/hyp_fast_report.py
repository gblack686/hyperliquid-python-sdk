#!/usr/bin/env python3
"""
Fast Market Report - Parallel API fetching for speed.

Fetches positions, prices, funding, CVD, OI, L/S ratios all in parallel.
Target: <3 seconds for full report.

Usage:
    python scripts/hyp_fast_report.py
    python scripts/hyp_fast_report.py --json
"""

import os
import sys
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Use aiohttp for parallel requests
try:
    import aiohttp
except ImportError:
    print("Install aiohttp: pip install aiohttp")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

BINANCE_FUTURES = "https://fapi.binance.com/futures/data"
HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"
TRACKED_SYMBOLS = ['BTC', 'ETH', 'SOL', 'XRP']
BINANCE_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']


class FastMarketReport:
    def __init__(self):
        self.address = os.getenv('ACCOUNT_ADDRESS', '')
        self.data: Dict[str, Any] = {}

    async def fetch_all(self) -> Dict[str, Any]:
        """Fetch all data in parallel."""
        start = time.time()

        async with aiohttp.ClientSession() as session:
            tasks = {}

            # Hyperliquid: positions + market data (single call gets both)
            tasks['hl_state'] = self._post(session, HYPERLIQUID_API,
                {'type': 'clearinghouseState', 'user': self.address})
            tasks['hl_meta'] = self._post(session, HYPERLIQUID_API,
                {'type': 'metaAndAssetCtxs'})

            # Binance: CVD, OI, L/S for each symbol
            for i, sym in enumerate(BINANCE_SYMBOLS):
                tasks[f'cvd_{sym}'] = self._get(session,
                    f"{BINANCE_FUTURES}/takerlongshortRatio",
                    {'symbol': sym, 'period': '1h', 'limit': 3})
                tasks[f'oi_{sym}'] = self._get(session,
                    f"{BINANCE_FUTURES}/openInterestHist",
                    {'symbol': sym, 'period': '1h', 'limit': 2})
                tasks[f'ls_{sym}'] = self._get(session,
                    f"{BINANCE_FUTURES}/globalLongShortAccountRatio",
                    {'symbol': sym, 'period': '1h', 'limit': 1})

            # Execute all in parallel
            results = await asyncio.gather(
                *[tasks[k] for k in tasks],
                return_exceptions=True
            )

            # Map results back to keys
            for i, key in enumerate(tasks.keys()):
                self.data[key] = results[i]

        self.data['fetch_time'] = time.time() - start
        return self.data

    async def _get(self, session: aiohttp.ClientSession, url: str, params: dict):
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
        except Exception as e:
            return {'error': str(e)}

    async def _post(self, session: aiohttp.ClientSession, url: str, data: dict):
        try:
            async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
        except Exception as e:
            return {'error': str(e)}

    def parse_positions(self) -> List[Dict]:
        """Parse position data from Hyperliquid response."""
        state = self.data.get('hl_state', {})
        if isinstance(state, Exception) or 'error' in state:
            return []

        positions = []
        for pos in state.get('assetPositions', []):
            p = pos.get('position', {})
            size = float(p.get('szi', 0))
            if size == 0:
                continue

            entry = float(p.get('entryPx', 0))
            upnl = float(p.get('unrealizedPnl', 0))
            coin = p.get('coin', '')

            # Get mark price from meta
            mark = entry  # fallback
            meta = self.data.get('hl_meta', [])
            if isinstance(meta, list) and len(meta) > 1:
                universe = meta[0].get('universe', [])
                ctxs = meta[1]
                for i, asset in enumerate(universe):
                    if asset.get('name') == coin and i < len(ctxs):
                        mark = float(ctxs[i].get('markPx', entry))
                        break

            margin = float(p.get('marginUsed', 0))
            roe = (upnl / margin * 100) if margin > 0 else 0

            positions.append({
                'coin': coin,
                'side': 'LONG' if size > 0 else 'SHORT',
                'size': abs(size),
                'entry': entry,
                'mark': mark,
                'upnl': upnl,
                'roe': roe,
            })

        return positions

    def parse_account(self) -> Dict:
        """Parse account value from Hyperliquid response."""
        state = self.data.get('hl_state', {})
        if isinstance(state, Exception) or 'error' in state:
            return {}

        return {
            'account_value': float(state.get('marginSummary', {}).get('accountValue', 0)),
            'total_margin': float(state.get('marginSummary', {}).get('totalMarginUsed', 0)),
            'total_upnl': sum(
                float(p['position'].get('unrealizedPnl', 0))
                for p in state.get('assetPositions', [])
            ),
        }

    def parse_funding(self) -> Dict[str, float]:
        """Parse funding rates from Hyperliquid meta."""
        meta = self.data.get('hl_meta', [])
        if not isinstance(meta, list) or len(meta) < 2:
            return {}

        universe = meta[0].get('universe', [])
        ctxs = meta[1]

        funding = {}
        for i, asset in enumerate(universe):
            name = asset.get('name', '')
            if name in TRACKED_SYMBOLS and i < len(ctxs):
                rate = float(ctxs[i].get('funding', 0))
                funding[name] = rate

        return funding

    def parse_prices(self) -> Dict[str, float]:
        """Parse current prices from Hyperliquid meta."""
        meta = self.data.get('hl_meta', [])
        if not isinstance(meta, list) or len(meta) < 2:
            return {}

        universe = meta[0].get('universe', [])
        ctxs = meta[1]

        prices = {}
        for i, asset in enumerate(universe):
            name = asset.get('name', '')
            if name in TRACKED_SYMBOLS and i < len(ctxs):
                prices[name] = float(ctxs[i].get('markPx', 0))

        return prices

    def parse_cvd(self) -> Dict[str, Dict]:
        """Parse CVD (taker buy/sell ratio) from Binance."""
        cvd = {}
        for sym in BINANCE_SYMBOLS:
            data = self.data.get(f'cvd_{sym}', [])
            if isinstance(data, list) and len(data) > 0:
                latest = float(data[-1].get('buySellRatio', 1))
                prev = float(data[-2].get('buySellRatio', 1)) if len(data) > 1 else latest
                coin = sym.replace('USDT', '')
                cvd[coin] = {
                    'ratio': latest,
                    'prev': prev,
                    'bias': 'BUYING' if latest > 1.0 else 'SELLING',
                    'direction': 'UP' if latest > prev else 'DOWN',
                }
        return cvd

    def parse_oi(self) -> Dict[str, Dict]:
        """Parse OI changes from Binance."""
        oi = {}
        for sym in BINANCE_SYMBOLS:
            data = self.data.get(f'oi_{sym}', [])
            if isinstance(data, list) and len(data) >= 2:
                now = float(data[-1].get('sumOpenInterestValue', 0))
                prev = float(data[0].get('sumOpenInterestValue', 0))
                change_pct = ((now - prev) / prev * 100) if prev > 0 else 0
                coin = sym.replace('USDT', '')
                oi[coin] = {
                    'value': now,
                    'change_pct': change_pct,
                }
        return oi

    def parse_ls_ratio(self) -> Dict[str, Dict]:
        """Parse long/short account ratio from Binance."""
        ls = {}
        for sym in BINANCE_SYMBOLS:
            data = self.data.get(f'ls_{sym}', [])
            if isinstance(data, list) and len(data) > 0:
                ratio = float(data[0].get('longShortRatio', 1))
                long_pct = ratio / (1 + ratio) * 100
                coin = sym.replace('USDT', '')
                ls[coin] = {
                    'ratio': ratio,
                    'long_pct': long_pct,
                    'short_pct': 100 - long_pct,
                }
        return ls

    def generate_report(self, as_json: bool = False) -> str:
        """Generate the full report."""
        positions = self.parse_positions()
        account = self.parse_account()
        funding = self.parse_funding()
        prices = self.parse_prices()
        cvd = self.parse_cvd()
        oi = self.parse_oi()
        ls = self.parse_ls_ratio()

        if as_json:
            return json.dumps({
                'timestamp': datetime.now().isoformat(),
                'fetch_time': self.data.get('fetch_time', 0),
                'account': account,
                'positions': positions,
                'prices': prices,
                'funding': funding,
                'cvd': cvd,
                'oi': oi,
                'ls_ratio': ls,
            }, indent=2)

        # Text report
        lines = []
        lines.append("=" * 70)
        lines.append(f"FAST MARKET REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Fetched in {self.data.get('fetch_time', 0):.2f}s")
        lines.append("=" * 70)

        # Account
        lines.append(f"\nAccount Value: ${account.get('account_value', 0):,.2f}")
        lines.append(f"Total uPnL:    ${account.get('total_upnl', 0):+,.2f}")

        # Positions
        if positions:
            lines.append(f"\n{'POSITIONS':^70}")
            lines.append("-" * 70)
            lines.append(f"{'Ticker':<8} {'Side':<6} {'Entry':>12} {'Mark':>12} {'uPnL':>12} {'ROE':>8}")
            lines.append("-" * 70)
            for p in positions:
                lines.append(
                    f"{p['coin']:<8} {p['side']:<6} ${p['entry']:>10,.2f} ${p['mark']:>10,.2f} "
                    f"${p['upnl']:>+10,.2f} {p['roe']:>+7.1f}%"
                )

        # CVD
        lines.append(f"\n{'CVD (Taker Buy/Sell)':^70}")
        lines.append("-" * 70)
        for coin in TRACKED_SYMBOLS:
            if coin in cvd:
                c = cvd[coin]
                lines.append(f"{coin:<8} {c['ratio']:.3f} [{c['bias']:^8}] {c['direction']}")

        # OI Changes
        lines.append(f"\n{'OI CHANGE (1h)':^70}")
        lines.append("-" * 70)
        for coin in TRACKED_SYMBOLS:
            if coin in oi:
                o = oi[coin]
                lines.append(f"{coin:<8} ${o['value']/1e9:.2f}B  ({o['change_pct']:+.1f}%)")

        # L/S Ratio
        lines.append(f"\n{'LONG/SHORT RATIO':^70}")
        lines.append("-" * 70)
        for coin in TRACKED_SYMBOLS:
            if coin in ls:
                l = ls[coin]
                lines.append(f"{coin:<8} {l['long_pct']:.1f}% Long / {l['short_pct']:.1f}% Short")

        # Funding
        lines.append(f"\n{'FUNDING RATES':^70}")
        lines.append("-" * 70)
        for coin in TRACKED_SYMBOLS:
            if coin in funding:
                rate = funding[coin]
                apr = rate * 24 * 365 * 100
                lines.append(f"{coin:<8} {rate*100:.4f}% ({apr:+.1f}% APR)")

        # Summary signals
        lines.append(f"\n{'SIGNALS':^70}")
        lines.append("-" * 70)

        cvd_selling = sum(1 for c in cvd.values() if c['bias'] == 'SELLING')
        cvd_buying = len(cvd) - cvd_selling
        lines.append(f"CVD: {cvd_buying} BUYING / {cvd_selling} SELLING")

        oi_falling = sum(1 for o in oi.values() if o['change_pct'] < 0)
        lines.append(f"OI:  {oi_falling}/{len(oi)} falling (deleveraging)")

        avg_long = sum(l['long_pct'] for l in ls.values()) / len(ls) if ls else 50
        lines.append(f"L/S: {avg_long:.1f}% accounts long")

        neg_funding = sum(1 for f in funding.values() if f < 0)
        lines.append(f"Funding: {neg_funding}/{len(funding)} negative (shorts paid)")

        lines.append("=" * 70)

        return "\n".join(lines)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fast Market Report')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    report = FastMarketReport()
    await report.fetch_all()
    print(report.generate_report(as_json=args.json))


if __name__ == '__main__':
    asyncio.run(main())
