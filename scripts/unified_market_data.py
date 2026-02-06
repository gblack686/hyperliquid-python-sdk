#!/usr/bin/env python3
"""
Unified Market Data - Binance + Hyperliquid side by side.

Fetches and compares data from both exchanges in parallel:
- Prices
- Funding rates
- Open interest
- CVD (taker ratio)
- Long/Short ratio
- Liquidations
- Orderbook depth

Usage:
    python scripts/unified_market_data.py                    # All majors
    python scripts/unified_market_data.py BTC SOL            # Specific tickers
    python scripts/unified_market_data.py --json             # JSON output
    python scripts/unified_market_data.py --liquidations     # Include recent liqs
"""

import os
import sys
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    import aiohttp
except ImportError:
    print("Install aiohttp: pip install aiohttp")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

# API Endpoints
HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"
BINANCE_FAPI = "https://fapi.binance.com"
BINANCE_DATA = "https://fapi.binance.com/futures/data"

# Symbol mapping
SYMBOL_MAP = {
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT',
    'SOL': 'SOLUSDT',
    'XRP': 'XRPUSDT',
    'DOGE': 'DOGEUSDT',
    'ADA': 'ADAUSDT',
    'AVAX': 'AVAXUSDT',
    'LINK': 'LINKUSDT',
    'SUI': 'SUIUSDT',
    'PEPE': '1000PEPEUSDT',  # Binance uses 1000PEPE
    'WIF': 'WIFUSDT',
}

DEFAULT_SYMBOLS = ['BTC', 'ETH', 'SOL', 'XRP']


class UnifiedMarketData:
    """Fetch and compare market data from Binance and Hyperliquid."""

    def __init__(self, symbols: List[str] = None):
        self.symbols = [s.upper() for s in (symbols or DEFAULT_SYMBOLS)]
        self.data: Dict[str, Any] = {}
        self.hl_meta: Dict = {}
        self.hl_universe_map: Dict[str, int] = {}

    async def fetch_all(self, include_liquidations: bool = False) -> Dict[str, Any]:
        """Fetch all data from both exchanges in parallel."""
        start = time.time()

        async with aiohttp.ClientSession() as session:
            tasks = {}

            # Hyperliquid: meta (prices, funding, OI)
            tasks['hl_meta'] = self._post(session, HYPERLIQUID_API, {'type': 'metaAndAssetCtxs'})

            # Binance data for each symbol
            for sym in self.symbols:
                bn_sym = SYMBOL_MAP.get(sym, f'{sym}USDT')

                # Price
                tasks[f'bn_price_{sym}'] = self._get(session,
                    f"{BINANCE_FAPI}/fapi/v1/ticker/price", {'symbol': bn_sym})

                # Funding
                tasks[f'bn_funding_{sym}'] = self._get(session,
                    f"{BINANCE_FAPI}/fapi/v1/fundingRate", {'symbol': bn_sym, 'limit': 1})

                # OI
                tasks[f'bn_oi_{sym}'] = self._get(session,
                    f"{BINANCE_FAPI}/fapi/v1/openInterest", {'symbol': bn_sym})

                # OI history (for change %)
                tasks[f'bn_oi_hist_{sym}'] = self._get(session,
                    f"{BINANCE_DATA}/openInterestHist",
                    {'symbol': bn_sym, 'period': '1h', 'limit': 2})

                # Taker buy/sell (CVD proxy)
                tasks[f'bn_cvd_{sym}'] = self._get(session,
                    f"{BINANCE_DATA}/takerlongshortRatio",
                    {'symbol': bn_sym, 'period': '1h', 'limit': 3})

                # Long/Short ratio
                tasks[f'bn_ls_{sym}'] = self._get(session,
                    f"{BINANCE_DATA}/globalLongShortAccountRatio",
                    {'symbol': bn_sym, 'period': '1h', 'limit': 1})

                # Recent liquidations
                if include_liquidations:
                    tasks[f'bn_liq_{sym}'] = self._get(session,
                        f"{BINANCE_FAPI}/fapi/v1/allForceOrders",
                        {'symbol': bn_sym, 'limit': 50})

            # Execute all in parallel
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            for i, key in enumerate(tasks.keys()):
                result = results[i]
                if isinstance(result, Exception):
                    self.data[key] = {'error': str(result)}
                else:
                    self.data[key] = result

        # Parse HL meta
        self._parse_hl_meta()

        self.data['fetch_time'] = time.time() - start
        return self.data

    async def _get(self, session: aiohttp.ClientSession, url: str, params: dict = None):
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

    def _parse_hl_meta(self):
        """Parse Hyperliquid meta for quick lookups."""
        meta = self.data.get('hl_meta', [])
        if isinstance(meta, list) and len(meta) > 1:
            self.hl_meta = meta
            universe = meta[0].get('universe', [])
            for i, asset in enumerate(universe):
                self.hl_universe_map[asset.get('name', '')] = i

    def get_hl_data(self, symbol: str) -> Dict:
        """Get Hyperliquid data for a symbol."""
        if not self.hl_meta or len(self.hl_meta) < 2:
            return {}

        idx = self.hl_universe_map.get(symbol)
        if idx is None or idx >= len(self.hl_meta[1]):
            return {}

        ctx = self.hl_meta[1][idx]
        return {
            'price': float(ctx.get('markPx', 0)),
            'funding': float(ctx.get('funding', 0)),
            'oi': float(ctx.get('openInterest', 0)),
            'oi_usd': float(ctx.get('openInterest', 0)) * float(ctx.get('markPx', 0)),
            'volume_24h': float(ctx.get('dayNtlVlm', 0)),
        }

    def get_bn_data(self, symbol: str) -> Dict:
        """Get Binance data for a symbol."""
        # Price
        price_data = self.data.get(f'bn_price_{symbol}', {})
        price = float(price_data.get('price', 0)) if isinstance(price_data, dict) and 'price' in price_data else 0

        # Funding
        funding_data = self.data.get(f'bn_funding_{symbol}', [])
        funding = 0
        if isinstance(funding_data, list) and len(funding_data) > 0:
            funding = float(funding_data[0].get('fundingRate', 0))

        # OI
        oi_data = self.data.get(f'bn_oi_{symbol}', {})
        oi = float(oi_data.get('openInterest', 0)) if isinstance(oi_data, dict) else 0
        oi_usd = oi * price

        # OI change
        oi_hist = self.data.get(f'bn_oi_hist_{symbol}', [])
        oi_change_pct = 0
        if isinstance(oi_hist, list) and len(oi_hist) >= 2:
            now_oi = float(oi_hist[-1].get('sumOpenInterestValue', 0))
            prev_oi = float(oi_hist[0].get('sumOpenInterestValue', 0))
            if prev_oi > 0:
                oi_change_pct = (now_oi - prev_oi) / prev_oi * 100

        # CVD (taker ratio)
        cvd_data = self.data.get(f'bn_cvd_{symbol}', [])
        cvd_ratio = 1.0
        cvd_trend = 'NEUTRAL'
        if isinstance(cvd_data, list) and len(cvd_data) > 0:
            cvd_ratio = float(cvd_data[-1].get('buySellRatio', 1))
            if len(cvd_data) > 1:
                prev_ratio = float(cvd_data[-2].get('buySellRatio', 1))
                cvd_trend = 'UP' if cvd_ratio > prev_ratio else 'DOWN'

        # L/S ratio
        ls_data = self.data.get(f'bn_ls_{symbol}', [])
        ls_ratio = 1.0
        long_pct = 50.0
        if isinstance(ls_data, list) and len(ls_data) > 0:
            ls_ratio = float(ls_data[0].get('longShortRatio', 1))
            long_pct = ls_ratio / (1 + ls_ratio) * 100

        return {
            'price': price,
            'funding': funding,
            'oi': oi,
            'oi_usd': oi_usd,
            'oi_change_pct': oi_change_pct,
            'cvd_ratio': cvd_ratio,
            'cvd_bias': 'BUYING' if cvd_ratio > 1 else 'SELLING',
            'cvd_trend': cvd_trend,
            'ls_ratio': ls_ratio,
            'long_pct': long_pct,
        }

    def get_bn_liquidations(self, symbol: str) -> List[Dict]:
        """Get recent Binance liquidations for a symbol."""
        liq_data = self.data.get(f'bn_liq_{symbol}', [])
        if not isinstance(liq_data, list):
            return []

        liqs = []
        for l in liq_data:
            try:
                side = l.get('side', '')
                # SELL = long liquidation, BUY = short liquidation
                liq_type = 'LONG_LIQ' if side == 'SELL' else 'SHORT_LIQ'
                price = float(l.get('price', 0))
                qty = float(l.get('origQty', 0))
                liqs.append({
                    'time': datetime.fromtimestamp(l.get('time', 0) / 1000),
                    'type': liq_type,
                    'price': price,
                    'qty': qty,
                    'value_usd': price * qty,
                })
            except (KeyError, ValueError):
                continue

        return sorted(liqs, key=lambda x: x['time'], reverse=True)

    def generate_report(self, include_liquidations: bool = False, as_json: bool = False) -> str:
        """Generate unified market report."""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'fetch_time': self.data.get('fetch_time', 0),
            'symbols': {},
        }

        for sym in self.symbols:
            hl = self.get_hl_data(sym)
            bn = self.get_bn_data(sym)

            report_data['symbols'][sym] = {
                'hyperliquid': hl,
                'binance': bn,
            }

            if include_liquidations:
                report_data['symbols'][sym]['liquidations'] = self.get_bn_liquidations(sym)[:10]

        if as_json:
            return json.dumps(report_data, indent=2, default=str)

        # Text report
        lines = []
        lines.append("=" * 90)
        lines.append(f"UNIFIED MARKET DATA - Binance + Hyperliquid")
        lines.append(f"Fetched in {self.data.get('fetch_time', 0):.2f}s | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 90)

        # Prices comparison
        lines.append(f"\n{'PRICES':^90}")
        lines.append("-" * 90)
        lines.append(f"{'Symbol':<8} {'Hyperliquid':>15} {'Binance':>15} {'Diff':>10} {'Funding HL':>12} {'Funding BN':>12}")
        lines.append("-" * 90)

        for sym in self.symbols:
            hl = self.get_hl_data(sym)
            bn = self.get_bn_data(sym)

            hl_price = hl.get('price', 0)
            bn_price = bn.get('price', 0)
            diff_pct = ((hl_price - bn_price) / bn_price * 100) if bn_price > 0 else 0

            hl_funding = hl.get('funding', 0) * 100
            bn_funding = bn.get('funding', 0) * 100

            lines.append(
                f"{sym:<8} ${hl_price:>14,.4f} ${bn_price:>14,.4f} {diff_pct:>+9.3f}% "
                f"{hl_funding:>+11.4f}% {bn_funding:>+11.4f}%"
            )

        # Open Interest
        lines.append(f"\n{'OPEN INTEREST':^90}")
        lines.append("-" * 90)
        lines.append(f"{'Symbol':<8} {'HL OI (USD)':>18} {'BN OI (USD)':>18} {'BN OI Chg 1h':>14} {'BN Volume':>20}")
        lines.append("-" * 90)

        for sym in self.symbols:
            hl = self.get_hl_data(sym)
            bn = self.get_bn_data(sym)

            hl_oi = hl.get('oi_usd', 0)
            bn_oi = bn.get('oi_usd', 0)
            bn_oi_chg = bn.get('oi_change_pct', 0)
            hl_vol = hl.get('volume_24h', 0)

            lines.append(
                f"{sym:<8} ${hl_oi/1e6:>16,.1f}M ${bn_oi/1e9:>16,.2f}B {bn_oi_chg:>+13.1f}% ${hl_vol/1e6:>18,.1f}M"
            )

        # CVD and L/S
        lines.append(f"\n{'CVD & LONG/SHORT RATIO (Binance)':^90}")
        lines.append("-" * 90)
        lines.append(f"{'Symbol':<8} {'CVD Ratio':>12} {'CVD Bias':>12} {'Trend':>8} {'Long %':>10} {'Short %':>10}")
        lines.append("-" * 90)

        for sym in self.symbols:
            bn = self.get_bn_data(sym)

            cvd = bn.get('cvd_ratio', 1)
            cvd_bias = bn.get('cvd_bias', 'NEUTRAL')
            cvd_trend = bn.get('cvd_trend', '-')
            long_pct = bn.get('long_pct', 50)
            short_pct = 100 - long_pct

            lines.append(
                f"{sym:<8} {cvd:>12.3f} {cvd_bias:>12} {cvd_trend:>8} {long_pct:>9.1f}% {short_pct:>9.1f}%"
            )

        # Liquidations
        if include_liquidations:
            lines.append(f"\n{'RECENT LIQUIDATIONS (Binance)':^90}")
            lines.append("-" * 90)

            for sym in self.symbols:
                liqs = self.get_bn_liquidations(sym)[:5]
                if liqs:
                    lines.append(f"\n  {sym}:")
                    for l in liqs:
                        lines.append(
                            f"    {l['time'].strftime('%H:%M:%S')} {l['type']:<10} "
                            f"${l['price']:>12,.4f} x {l['qty']:>12,.4f} = ${l['value_usd']:>12,.2f}"
                        )
                else:
                    lines.append(f"\n  {sym}: No recent liquidations")

        # Summary
        lines.append(f"\n{'SUMMARY':^90}")
        lines.append("-" * 90)

        # Count biases
        buying = sum(1 for s in self.symbols if self.get_bn_data(s).get('cvd_bias') == 'BUYING')
        selling = len(self.symbols) - buying

        oi_falling = sum(1 for s in self.symbols if self.get_bn_data(s).get('oi_change_pct', 0) < 0)

        avg_long = sum(self.get_bn_data(s).get('long_pct', 50) for s in self.symbols) / len(self.symbols)

        neg_funding_hl = sum(1 for s in self.symbols if self.get_hl_data(s).get('funding', 0) < 0)
        neg_funding_bn = sum(1 for s in self.symbols if self.get_bn_data(s).get('funding', 0) < 0)

        lines.append(f"  CVD Bias:     {buying} BUYING / {selling} SELLING")
        lines.append(f"  OI Change:    {oi_falling}/{len(self.symbols)} falling (deleveraging)")
        lines.append(f"  Avg Long %:   {avg_long:.1f}%")
        lines.append(f"  Neg Funding:  HL: {neg_funding_hl}/{len(self.symbols)} | BN: {neg_funding_bn}/{len(self.symbols)}")

        lines.append("=" * 90)
        return "\n".join(lines)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Unified Market Data - Binance + Hyperliquid')
    parser.add_argument('symbols', nargs='*', help='Symbols to fetch (default: BTC ETH SOL XRP)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--liquidations', '-l', action='store_true', help='Include recent liquidations')
    args = parser.parse_args()

    symbols = args.symbols if args.symbols else DEFAULT_SYMBOLS

    umd = UnifiedMarketData(symbols)
    await umd.fetch_all(include_liquidations=args.liquidations)
    print(umd.generate_report(include_liquidations=args.liquidations, as_json=args.json))


if __name__ == '__main__':
    asyncio.run(main())
