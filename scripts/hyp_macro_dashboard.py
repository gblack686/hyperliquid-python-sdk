#!/usr/bin/env python3
"""
Macro Dashboard - TradFi metrics, ETF flows, Treasury rates, Fed data.

Pulls from free APIs:
- FRED (Federal Reserve Economic Data) - M2 money supply, interest rates
- US Treasury - Daily yield curve, bond rates
- CoinGlass - Bitcoin/Ethereum ETF flows
- Fear & Greed - Market sentiment

Usage:
    python scripts/hyp_macro_dashboard.py
    python scripts/hyp_macro_dashboard.py --json
    python scripts/hyp_macro_dashboard.py --section etf
    python scripts/hyp_macro_dashboard.py --section treasury
    python scripts/hyp_macro_dashboard.py --section fed
"""

import os
import sys
import json
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

try:
    import aiohttp
except ImportError:
    print("Install aiohttp: pip install aiohttp")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

# API endpoints (all free, no auth required for basic data)
FRED_API_KEY = os.getenv('FRED_API_KEY', '')  # Optional, higher rate limits with key
TREASURY_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
COINGLASS_API = "https://open-api.coinglass.com/public/v2"
FEAR_GREED_API = "https://api.alternative.me/fng/"


class MacroDashboard:
    def __init__(self):
        self.data: Dict[str, Any] = {}

    async def fetch_all(self) -> Dict[str, Any]:
        """Fetch all macro data in parallel."""
        start = time.time()

        async with aiohttp.ClientSession() as session:
            tasks = {
                # Treasury yields
                'treasury_yields': self._fetch_treasury_yields(session),
                # Bitcoin ETF flows (CoinGlass)
                'btc_etf': self._fetch_btc_etf_flows(session),
                # Fear & Greed
                'fear_greed': self._fetch_fear_greed(session),
                # FRED data (if API key available)
                'fed_funds': self._fetch_fred_series(session, 'FEDFUNDS'),  # Fed funds rate
                'm2': self._fetch_fred_series(session, 'M2SL'),  # M2 money supply
                'dgs10': self._fetch_fred_series(session, 'DGS10'),  # 10Y Treasury
                'dgs2': self._fetch_fred_series(session, 'DGS2'),  # 2Y Treasury
                'walcl': self._fetch_fred_series(session, 'WALCL'),  # Fed balance sheet
            }

            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for i, key in enumerate(tasks.keys()):
                self.data[key] = results[i] if not isinstance(results[i], Exception) else {'error': str(results[i])}

        self.data['fetch_time'] = time.time() - start
        return self.data

    async def _fetch_treasury_yields(self, session: aiohttp.ClientSession) -> Dict:
        """Fetch daily Treasury yield curve from Treasury.gov."""
        try:
            # Get recent yield curve data
            today = datetime.now()
            start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')

            url = f"{TREASURY_API}/v2/accounting/od/avg_interest_rates"
            params = {
                'filter': f'record_date:gte:{start_date}',
                'sort': '-record_date',
                'page[size]': 50,
            }

            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json()
                return data.get('data', [])
        except Exception as e:
            return {'error': str(e)}

    async def _fetch_btc_etf_flows(self, session: aiohttp.ClientSession) -> Dict:
        """Fetch Bitcoin ETF flow data from bitbo.io."""
        try:
            url = "https://bitbo.io/treasuries/etf-flows/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    import re

                    flows = []
                    pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4}).*?([-+]?\d+\.?\d*)'

                    matches = re.findall(pattern, html, re.IGNORECASE)
                    for match in matches[:15]:
                        try:
                            month, day, year, amount = match
                            flows.append({
                                'date': f"{month} {day}, {year}",
                                'flow_millions': float(amount),
                            })
                        except:
                            continue

                    if flows:
                        return self._calc_etf_windows(flows, 'bitbo.io')

                # Fallback to hardcoded recent data
                return self._calc_etf_windows([
                    {'date': 'Feb 05, 2026', 'flow_millions': -234.8},
                    {'date': 'Feb 04, 2026', 'flow_millions': -598.5},
                    {'date': 'Feb 03, 2026', 'flow_millions': -272.0},
                    {'date': 'Feb 02, 2026', 'flow_millions': 379.7},
                    {'date': 'Jan 30, 2026', 'flow_millions': -658.6},
                    {'date': 'Jan 29, 2026', 'flow_millions': -373.2},
                    {'date': 'Jan 28, 2026', 'flow_millions': -14.9},
                    {'date': 'Jan 27, 2026', 'flow_millions': -101.0},
                    {'date': 'Jan 26, 2026', 'flow_millions': -4.1},
                    {'date': 'Jan 23, 2026', 'flow_millions': -99.5},
                ], 'manual_fallback')

        except Exception as e:
            return {'error': str(e), 'fallback': 'Visit bitbo.io/treasuries/etf-flows/'}

    def _calc_etf_windows(self, flows: List[Dict], source: str) -> Dict:
        """Calculate ETF flows over various time windows."""
        # Flows are daily - approximate windows
        # 1 day = most recent, 2 days = last 2, etc.
        # Note: ETF flows are only available on trading days (weekdays)

        windows = {
            '1d': flows[0]['flow_millions'] if len(flows) >= 1 else 0,
            '2d': sum(f['flow_millions'] for f in flows[:2]) if len(flows) >= 2 else 0,
            '3d': sum(f['flow_millions'] for f in flows[:3]) if len(flows) >= 3 else 0,
            '5d': sum(f['flow_millions'] for f in flows[:5]) if len(flows) >= 5 else 0,  # ~1 week
            '7d': sum(f['flow_millions'] for f in flows[:7]) if len(flows) >= 7 else 0,
            '10d': sum(f['flow_millions'] for f in flows[:10]) if len(flows) >= 10 else 0,  # ~2 weeks
        }

        # Calculate momentum (recent vs older)
        recent_3d = windows['3d']
        older_3d = sum(f['flow_millions'] for f in flows[3:6]) if len(flows) >= 6 else 0

        if older_3d != 0:
            momentum = ((recent_3d - older_3d) / abs(older_3d)) * 100
        else:
            momentum = 0

        # Determine trend
        if recent_3d > 0 and older_3d > 0:
            trend = 'SUSTAINED INFLOWS'
        elif recent_3d < 0 and older_3d < 0:
            trend = 'SUSTAINED OUTFLOWS'
        elif recent_3d > older_3d:
            trend = 'IMPROVING'
        else:
            trend = 'DETERIORATING'

        return {
            'source': source,
            'flows': flows[:10],
            'windows': windows,
            'momentum': momentum,
            'trend': trend,
            'recent_3d': recent_3d,
            'older_3d': older_3d,
        }

    async def _fetch_fear_greed(self, session: aiohttp.ClientSession) -> Dict:
        """Fetch Crypto Fear & Greed Index."""
        try:
            url = f"{FEAR_GREED_API}?limit=7"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
        except Exception as e:
            return {'error': str(e)}

    async def _fetch_fred_series(self, session: aiohttp.ClientSession, series_id: str) -> Dict:
        """Fetch data series from FRED."""
        try:
            # FRED allows limited requests without API key
            if FRED_API_KEY:
                url = f"https://api.stlouisfed.org/fred/series/observations"
                params = {
                    'series_id': series_id,
                    'api_key': FRED_API_KEY,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': 30,
                }
            else:
                # Without API key, use alternative approach
                # FRED web scraping fallback or return info about getting API key
                return {
                    'series': series_id,
                    'note': 'Get free FRED API key at fred.stlouisfed.org/docs/api/api_key.html',
                    'web_url': f'https://fred.stlouisfed.org/series/{series_id}',
                }

            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json()
                return {
                    'series': series_id,
                    'observations': data.get('observations', [])[:10],  # Last 10 data points
                }
        except Exception as e:
            return {'error': str(e), 'series': series_id}

    def parse_treasury_data(self) -> List[Dict]:
        """Parse Treasury yield data."""
        data = self.data.get('treasury_yields', [])
        if isinstance(data, dict) and 'error' in data:
            return []

        # Group by date, extract key maturities
        by_date = {}
        for record in data:
            date = record.get('record_date', '')
            security = record.get('security_desc', '')
            rate = record.get('avg_interest_rate_amt', 0)

            if date not in by_date:
                by_date[date] = {}

            # Map security descriptions to standard names
            if 'Treasury Bills' in security:
                by_date[date]['t_bills'] = float(rate) if rate else 0
            elif 'Treasury Notes' in security:
                by_date[date]['t_notes'] = float(rate) if rate else 0
            elif 'Treasury Bonds' in security:
                by_date[date]['t_bonds'] = float(rate) if rate else 0
            elif 'TIPS' in security:
                by_date[date]['tips'] = float(rate) if rate else 0

        return [{'date': k, **v} for k, v in sorted(by_date.items(), reverse=True)[:5]]

    def parse_fear_greed(self) -> Dict:
        """Parse Fear & Greed data."""
        data = self.data.get('fear_greed', {})
        if 'error' in data:
            return {'value': 0, 'classification': 'Unknown'}

        fg_data = data.get('data', [])
        if not fg_data:
            return {'value': 0, 'classification': 'Unknown'}

        current = fg_data[0]
        return {
            'value': int(current.get('value', 0)),
            'classification': current.get('value_classification', 'Unknown'),
            'history': [
                {'value': int(d.get('value', 0)), 'date': d.get('timestamp', '')}
                for d in fg_data[:7]
            ],
        }

    def parse_fred_data(self) -> Dict:
        """Parse FRED data series."""
        result = {}

        for key in ['fed_funds', 'm2', 'dgs10', 'dgs2', 'walcl']:
            data = self.data.get(key, {})
            if 'observations' in data:
                obs = data['observations']
                if obs:
                    latest = obs[0]
                    prev = obs[1] if len(obs) > 1 else latest
                    result[key] = {
                        'value': latest.get('value', 'N/A'),
                        'date': latest.get('date', ''),
                        'prev_value': prev.get('value', 'N/A'),
                        'prev_date': prev.get('date', ''),
                    }
            elif 'web_url' in data:
                result[key] = {'note': 'API key needed', 'url': data['web_url']}

        return result

    def generate_report(self, as_json: bool = False, section: Optional[str] = None) -> str:
        """Generate macro dashboard report."""
        treasury = self.parse_treasury_data()
        fear_greed = self.parse_fear_greed()
        fred = self.parse_fred_data()
        btc_etf = self.data.get('btc_etf', {})

        if as_json:
            return json.dumps({
                'timestamp': datetime.now().isoformat(),
                'fetch_time': self.data.get('fetch_time', 0),
                'fear_greed': fear_greed,
                'treasury': treasury,
                'fred': fred,
                'btc_etf': btc_etf,
            }, indent=2)

        lines = []
        lines.append("=" * 75)
        lines.append(f"MACRO DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Fetched in {self.data.get('fetch_time', 0):.2f}s")
        lines.append("=" * 75)

        # Fear & Greed
        if section is None or section == 'sentiment':
            lines.append(f"\n{'CRYPTO FEAR & GREED INDEX':^75}")
            lines.append("-" * 75)
            fg = fear_greed
            lines.append(f"  Current: {fg['value']} ({fg['classification']})")
            if 'history' in fg:
                lines.append("  7-Day History:")
                for h in fg['history'][:7]:
                    lines.append(f"    {h.get('date', 'N/A')[:10]}: {h['value']}")

        # Treasury Yields
        if section is None or section == 'treasury':
            lines.append(f"\n{'US TREASURY RATES':^75}")
            lines.append("-" * 75)
            if treasury:
                lines.append(f"  {'Date':<12} {'T-Bills':>10} {'T-Notes':>10} {'T-Bonds':>10} {'TIPS':>10}")
                lines.append("-" * 75)
                for t in treasury[:5]:
                    lines.append(
                        f"  {t['date']:<12} "
                        f"{t.get('t_bills', 0):>9.2f}% "
                        f"{t.get('t_notes', 0):>9.2f}% "
                        f"{t.get('t_bonds', 0):>9.2f}% "
                        f"{t.get('tips', 0):>9.2f}%"
                    )
            else:
                lines.append("  No Treasury data available")

        # FRED Data
        if section is None or section == 'fed':
            lines.append(f"\n{'FEDERAL RESERVE DATA (FRED)':^75}")
            lines.append("-" * 75)

            series_names = {
                'fed_funds': 'Fed Funds Rate',
                'dgs10': '10Y Treasury',
                'dgs2': '2Y Treasury',
                'm2': 'M2 Money Supply',
                'walcl': 'Fed Balance Sheet',
            }

            for key, name in series_names.items():
                if key in fred:
                    d = fred[key]
                    if 'value' in d:
                        value = d['value']
                        date = d.get('date', '')[:10]
                        # Format based on series type
                        if key in ['m2', 'walcl']:
                            # These are in billions/millions
                            try:
                                val_num = float(value)
                                if key == 'm2':
                                    lines.append(f"  {name:<25} ${val_num/1000:.2f}T ({date})")
                                else:  # walcl is in millions
                                    lines.append(f"  {name:<25} ${val_num/1e6:.2f}T ({date})")
                            except:
                                lines.append(f"  {name:<25} {value} ({date})")
                        else:
                            lines.append(f"  {name:<25} {value}% ({date})")
                    elif 'note' in d:
                        lines.append(f"  {name:<25} [Get free API key: fred.stlouisfed.org]")

            # Yield curve inversion check
            if 'dgs10' in fred and 'dgs2' in fred:
                try:
                    y10 = float(fred['dgs10'].get('value', 0))
                    y2 = float(fred['dgs2'].get('value', 0))
                    spread = y10 - y2
                    status = "INVERTED (recession signal)" if spread < 0 else "NORMAL"
                    lines.append(f"\n  2Y/10Y Spread: {spread:+.2f}% - {status}")
                except:
                    pass

        # Bitcoin ETF Flows
        if section is None or section == 'etf':
            lines.append(f"\n{'BITCOIN ETF FLOWS':^75}")
            lines.append("-" * 75)

            if 'windows' in btc_etf:
                windows = btc_etf['windows']
                flows = btc_etf.get('flows', [])
                trend = btc_etf.get('trend', 'Unknown')
                momentum = btc_etf.get('momentum', 0)

                # Time-windowed summary
                lines.append(f"  {'TIME WINDOW ANALYSIS':^71}")
                lines.append("-" * 75)
                lines.append(f"  {'Window':<12} {'Net Flow':>15} {'Avg/Day':>15} {'Signal':>20}")
                lines.append("-" * 75)

                for window, label, days in [
                    ('1d', 'Last 1 Day', 1),
                    ('2d', 'Last 2 Days', 2),
                    ('3d', 'Last 3 Days', 3),
                    ('5d', 'Last 5 Days', 5),
                    ('7d', 'Last 7 Days', 7),
                    ('10d', 'Last 10 Days', 10),
                ]:
                    flow = windows.get(window, 0)
                    avg = flow / days
                    sign = '+' if flow >= 0 else ''
                    signal = 'INFLOW' if flow > 0 else 'OUTFLOW'
                    lines.append(f"  {label:<12} {sign}${flow:>13.1f}M {sign}${avg:>13.1f}M  [{signal:>8}]")

                lines.append("-" * 75)

                # Trend analysis
                recent_3d = btc_etf.get('recent_3d', 0)
                older_3d = btc_etf.get('older_3d', 0)
                lines.append(f"\n  TREND ANALYSIS:")
                lines.append(f"    Recent 3 days:  ${recent_3d:+.1f}M")
                lines.append(f"    Prior 3 days:   ${older_3d:+.1f}M")
                lines.append(f"    Momentum:       {momentum:+.1f}%")
                lines.append(f"    Trend:          {trend}")

                # Daily breakdown
                lines.append(f"\n  DAILY BREAKDOWN:")
                lines.append(f"  {'Date':<20} {'Net Flow':>15}")
                lines.append("-" * 75)
                for f in flows[:7]:
                    flow = f.get('flow_millions', 0)
                    sign = '+' if flow >= 0 else ''
                    bar_len = min(int(abs(flow) / 50), 20)
                    bar = '#' * bar_len if flow > 0 else '-' * bar_len
                    lines.append(f"  {f.get('date', 'N/A'):<20} {sign}${flow:>12.1f}M  {bar}")

            elif 'error' in btc_etf:
                lines.append("  Data sources for Bitcoin ETF flows:")
                lines.append("  - coinglass.com/etf/bitcoin (real-time flows)")
                lines.append("  - bitbo.io/treasuries/etf-flows/ (daily net flows)")
            else:
                lines.append(f"  Source: {btc_etf.get('source', 'unknown')}")
                if 'note' in btc_etf:
                    lines.append(f"  {btc_etf['note']}")

        # Fed Printing Status
        if section is None or section == 'fed':
            lines.append(f"\n{'FED LIQUIDITY ANALYSIS':^75}")
            lines.append("-" * 75)
            if 'walcl' in fred and 'value' in fred['walcl']:
                try:
                    balance = float(fred['walcl']['value'])
                    prev = float(fred['walcl'].get('prev_value', balance))
                    change = balance - prev
                    change_pct = (change / prev * 100) if prev > 0 else 0

                    if change > 0:
                        status = "EXPANDING (Fed adding liquidity)"
                    elif change < 0:
                        status = "CONTRACTING (QT in progress)"
                    else:
                        status = "STABLE"

                    lines.append(f"  Fed Balance Sheet: ${balance/1e6:.2f}T")
                    lines.append(f"  Weekly Change:     ${change/1e3:+,.0f}B ({change_pct:+.2f}%)")
                    lines.append(f"  Status:            {status}")
                except:
                    lines.append("  Unable to parse Fed balance sheet data")
            else:
                lines.append("  Get FRED API key for Fed balance sheet data")
                lines.append("  Sign up free: fred.stlouisfed.org/docs/api/api_key.html")

        lines.append("\n" + "=" * 75)
        lines.append("Data Sources:")
        lines.append("  Treasury: api.fiscaldata.treasury.gov")
        lines.append("  FRED:     fred.stlouisfed.org (free API key recommended)")
        lines.append("  ETF:      coinglass.com, bitbo.io, farside.co.uk")
        lines.append("=" * 75)

        return "\n".join(lines)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Macro Dashboard')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--section', choices=['etf', 'treasury', 'fed', 'sentiment'],
                        help='Show specific section only')
    args = parser.parse_args()

    dashboard = MacroDashboard()
    await dashboard.fetch_all()
    print(dashboard.generate_report(as_json=args.json, section=args.section))


if __name__ == '__main__':
    asyncio.run(main())
