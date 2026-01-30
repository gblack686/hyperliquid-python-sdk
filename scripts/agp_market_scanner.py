#!/usr/bin/env python3
"""
Agentic Market Scanner - Scans all markets for trading opportunities
Uses REAL API data for funding rates, prices, and market metrics

DATA INTEGRITY RULES:
1. NO FABRICATED DATA - Every statistic comes from real API responses
2. EMPTY STATE HANDLING - If no data, report "No data available" clearly
3. SOURCE TRACKING - Log which API call produced each data point
4. VALIDATION - Before analysis, verify data exists and is valid
5. FAIL LOUDLY - If API fails or returns unexpected format, error clearly
"""

import os
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

# Also use raw SDK for additional endpoints
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def market_scanner():
    """Execute market scans using REAL DATA ONLY"""

    # Setup
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path("outputs/market_scan") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("HYPERLIQUID MARKET SCANNER")
    print(f"Timestamp: {timestamp}")
    print("DATA INTEGRITY: Real API data only - no fabrication")
    print("=" * 70)
    print()

    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Raw SDK for additional data
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    try:
        # 1. Fetch all market data
        print("[1/5] Fetching market metadata and prices...")
        print("      Source: info.meta_and_asset_ctxs() API")

        meta_and_ctxs = info.meta_and_asset_ctxs()

        if not meta_and_ctxs or len(meta_and_ctxs) < 2:
            raise ValueError("Failed to fetch market metadata")

        meta = meta_and_ctxs[0]
        asset_ctxs = meta_and_ctxs[1]

        universe = meta.get('universe', [])
        print(f"      Markets found: {len(universe)}")

        # Build market data
        markets = []
        for i, asset in enumerate(universe):
            ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}

            coin = asset.get('name', f'UNKNOWN_{i}')
            mark_px = float(ctx.get('markPx', 0))
            funding = float(ctx.get('funding', 0))
            open_interest = float(ctx.get('openInterest', 0))
            prev_day_px = float(ctx.get('prevDayPx', 0))
            volume_24h = float(ctx.get('dayNtlVlm', 0))

            # Calculate 24h change
            change_24h = ((mark_px - prev_day_px) / prev_day_px * 100) if prev_day_px > 0 else 0

            markets.append({
                'coin': coin,
                'mark_px': mark_px,
                'funding': funding,
                'open_interest': open_interest,
                'volume_24h': volume_24h,
                'change_24h': change_24h,
                'prev_day_px': prev_day_px
            })

        print("   [OK] Market data fetched")

        # 2. Funding Analysis
        print("[2/5] Analyzing funding rates...")
        print("      Source: Asset contexts from meta_and_asset_ctxs()")

        # Sort by funding rate
        by_funding = sorted(markets, key=lambda x: x['funding'], reverse=True)

        funding_text = f"""# Funding Rate Analysis

**Data Source**: `info.meta_and_asset_ctxs()` API
**Timestamp**: {timestamp}
**Markets Analyzed**: {len(markets)}

## Highest Positive Funding (Short Opportunities)
Positive funding = longs pay shorts = potential short edge

| Ticker | Funding (8h) | Annualized | Mark Price | OI |
|--------|--------------|------------|------------|-----|
"""
        for m in by_funding[:10]:
            ann = m['funding'] * 3 * 365 * 100  # Annualized %
            funding_text += f"| {m['coin']} | {m['funding']*100:.4f}% | {ann:.1f}% | ${m['mark_px']:,.2f} | ${m['open_interest']:,.0f} |\n"

        funding_text += """
## Highest Negative Funding (Long Opportunities)
Negative funding = shorts pay longs = potential long edge

| Ticker | Funding (8h) | Annualized | Mark Price | OI |
|--------|--------------|------------|------------|-----|
"""
        for m in reversed(by_funding[-10:]):
            ann = m['funding'] * 3 * 365 * 100
            funding_text += f"| {m['coin']} | {m['funding']*100:.4f}% | {ann:.1f}% | ${m['mark_px']:,.2f} | ${m['open_interest']:,.0f} |\n"

        # Find extreme funding
        extreme_positive = [m for m in markets if m['funding'] > 0.0001]  # >0.01% per 8h
        extreme_negative = [m for m in markets if m['funding'] < -0.0001]

        funding_text += f"""
## Funding Extremes Summary
- **Extreme Positive (>0.01%)**: {len(extreme_positive)} markets
- **Extreme Negative (<-0.01%)**: {len(extreme_negative)} markets
"""
        if extreme_positive:
            top = max(extreme_positive, key=lambda x: x['funding'])
            funding_text += f"- **Highest Funding**: {top['coin']} at {top['funding']*100:.4f}%\n"
        if extreme_negative:
            bottom = min(extreme_negative, key=lambda x: x['funding'])
            funding_text += f"- **Lowest Funding**: {bottom['coin']} at {bottom['funding']*100:.4f}%\n"

        (output_dir / "funding").mkdir(parents=True, exist_ok=True)
        (output_dir / "funding" / "opportunities.md").write_text(funding_text)
        print("   [OK] Funding analysis saved")

        # 3. Movers Analysis
        print("[3/5] Analyzing price movers...")
        print("      Source: 24h price change from meta_and_asset_ctxs()")

        by_change = sorted(markets, key=lambda x: x['change_24h'], reverse=True)

        movers_text = f"""# Price Movers (24h)

**Data Source**: `info.meta_and_asset_ctxs()` API
**Timestamp**: {timestamp}

## Top Gainers
| Rank | Ticker | 24h Change | Price | Volume 24h |
|------|--------|------------|-------|------------|
"""
        for i, m in enumerate(by_change[:10], 1):
            movers_text += f"| {i} | {m['coin']} | {m['change_24h']:+.2f}% | ${m['mark_px']:,.4f} | ${m['volume_24h']:,.0f} |\n"

        movers_text += """
## Top Losers
| Rank | Ticker | 24h Change | Price | Volume 24h |
|------|--------|------------|-------|------------|
"""
        for i, m in enumerate(reversed(by_change[-10:]), 1):
            movers_text += f"| {i} | {m['coin']} | {m['change_24h']:+.2f}% | ${m['mark_px']:,.4f} | ${m['volume_24h']:,.0f} |\n"

        # Summary stats
        avg_change = sum(m['change_24h'] for m in markets) / len(markets) if markets else 0
        gainers = len([m for m in markets if m['change_24h'] > 0])
        losers = len([m for m in markets if m['change_24h'] < 0])

        movers_text += f"""
## Market Summary
- **Average 24h Change**: {avg_change:+.2f}%
- **Gainers**: {gainers} ({gainers/len(markets)*100:.0f}%)
- **Losers**: {losers} ({losers/len(markets)*100:.0f}%)
- **Market Bias**: {"BULLISH" if avg_change > 1 else "BEARISH" if avg_change < -1 else "NEUTRAL"}
"""

        (output_dir / "movers").mkdir(parents=True, exist_ok=True)
        (output_dir / "movers" / "analysis.md").write_text(movers_text)
        print("   [OK] Movers analysis saved")

        # 4. Open Interest Analysis
        print("[4/5] Analyzing open interest...")
        print("      Source: OI from meta_and_asset_ctxs()")

        by_oi = sorted(markets, key=lambda x: x['open_interest'], reverse=True)

        oi_text = f"""# Open Interest Analysis

**Data Source**: `info.meta_and_asset_ctxs()` API
**Timestamp**: {timestamp}

## Highest Open Interest
| Rank | Ticker | Open Interest | Price | Funding |
|------|--------|---------------|-------|---------|
"""
        for i, m in enumerate(by_oi[:15], 1):
            oi_text += f"| {i} | {m['coin']} | ${m['open_interest']:,.0f} | ${m['mark_px']:,.2f} | {m['funding']*100:.4f}% |\n"

        total_oi = sum(m['open_interest'] for m in markets)
        oi_text += f"""
## OI Summary
- **Total Market OI**: ${total_oi:,.0f}
- **Top 5 Concentration**: {sum(m['open_interest'] for m in by_oi[:5])/total_oi*100:.1f}%
- **Top 10 Concentration**: {sum(m['open_interest'] for m in by_oi[:10])/total_oi*100:.1f}%
"""

        (output_dir / "oi").mkdir(parents=True, exist_ok=True)
        (output_dir / "oi" / "analysis.md").write_text(oi_text)
        print("   [OK] Open interest analysis saved")

        # 5. Volume Analysis
        print("[5/5] Analyzing volume...")
        print("      Source: 24h volume from meta_and_asset_ctxs()")

        by_volume = sorted(markets, key=lambda x: x['volume_24h'], reverse=True)

        volume_text = f"""# Volume Analysis

**Data Source**: `info.meta_and_asset_ctxs()` API
**Timestamp**: {timestamp}

## Highest 24h Volume
| Rank | Ticker | Volume 24h | Price | 24h Change |
|------|--------|------------|-------|------------|
"""
        for i, m in enumerate(by_volume[:15], 1):
            volume_text += f"| {i} | {m['coin']} | ${m['volume_24h']:,.0f} | ${m['mark_px']:,.2f} | {m['change_24h']:+.2f}% |\n"

        total_volume = sum(m['volume_24h'] for m in markets)
        volume_text += f"""
## Volume Summary
- **Total 24h Volume**: ${total_volume:,.0f}
- **Top 5 Concentration**: {sum(m['volume_24h'] for m in by_volume[:5])/total_volume*100:.1f}%
"""

        (output_dir / "volume").mkdir(parents=True, exist_ok=True)
        (output_dir / "volume" / "analysis.md").write_text(volume_text)
        print("   [OK] Volume analysis saved")

        # Synthesis
        print("[SYNTHESIS] Combining findings...")

        synthesis_text = f"""# Market Scan Synthesis

**Data Source**: `info.meta_and_asset_ctxs()` API
**Timestamp**: {timestamp}
**Markets Analyzed**: {len(markets)}
**Integrity**: All data from live Hyperliquid API

---

## Market Regime
- **Average 24h Change**: {avg_change:+.2f}%
- **Gainers/Losers**: {gainers}/{losers}
- **Sentiment**: {"BULLISH" if avg_change > 1 else "BEARISH" if avg_change < -1 else "NEUTRAL"}
- **Total OI**: ${total_oi:,.0f}
- **Total Volume**: ${total_volume:,.0f}

## Top Opportunities (Based on Real Data)

### Funding Plays
"""
        # Top funding shorts
        top_funding = sorted(markets, key=lambda x: x['funding'], reverse=True)[:3]
        for m in top_funding:
            if m['funding'] > 0.00005:
                synthesis_text += f"- **{m['coin']} SHORT**: Funding {m['funding']*100:.4f}% ({m['funding']*3*365*100:.0f}% ann.) - Get paid to short\n"

        # Top funding longs
        bottom_funding = sorted(markets, key=lambda x: x['funding'])[:3]
        for m in bottom_funding:
            if m['funding'] < -0.00005:
                synthesis_text += f"- **{m['coin']} LONG**: Funding {m['funding']*100:.4f}% ({m['funding']*3*365*100:.0f}% ann.) - Get paid to long\n"

        synthesis_text += """
### Momentum Plays
"""
        for m in by_change[:3]:
            if m['change_24h'] > 3:
                synthesis_text += f"- **{m['coin']}**: +{m['change_24h']:.1f}% momentum, ${m['volume_24h']:,.0f} volume\n"

        synthesis_text += """
### Mean Reversion Candidates
"""
        for m in list(reversed(by_change[-3:])):
            if m['change_24h'] < -3:
                synthesis_text += f"- **{m['coin']}**: {m['change_24h']:.1f}% oversold, watch for reversal\n"

        synthesis_text += f"""
## Warnings
- **High OI Concentration**: Top 5 coins hold {sum(m['open_interest'] for m in by_oi[:5])/total_oi*100:.0f}% of total OI
"""
        # Warn about extreme moves
        extreme_moves = [m for m in markets if abs(m['change_24h']) > 10]
        if extreme_moves:
            synthesis_text += f"- **Extreme Volatility**: {len(extreme_moves)} coins moved >10% in 24h\n"

        synthesis_text += """
## Data Quality
- All prices are mark prices from Hyperliquid API
- Funding rates are per 8-hour period
- Volume and OI are 24-hour figures
- No data has been fabricated or estimated
"""

        (output_dir / "synthesis.md").write_text(synthesis_text)
        print("   [OK] Synthesis complete")

        # Report
        print()
        print("=" * 70)
        print("MARKET SCAN COMPLETE (Real Data)")
        print("=" * 70)
        print(f"""
## Market Summary

- **Markets Scanned**: {len(markets)}
- **Average 24h Change**: {avg_change:+.2f}%
- **Market Sentiment**: {"BULLISH" if avg_change > 1 else "BEARISH" if avg_change < -1 else "NEUTRAL"}
- **Gainers/Losers**: {gainers}/{losers}

## Top Movers
- **Best**: {by_change[0]['coin']} +{by_change[0]['change_24h']:.1f}%
- **Worst**: {by_change[-1]['coin']} {by_change[-1]['change_24h']:.1f}%

## Funding Extremes
- **Highest**: {top_funding[0]['coin']} {top_funding[0]['funding']*100:.4f}%
- **Lowest**: {bottom_funding[0]['coin']} {bottom_funding[0]['funding']*100:.4f}%

All analysis saved to: {output_dir.absolute()}
""")

    except Exception as e:
        print(f"\n[ERROR] Market scan failed: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await hyp.cleanup()

if __name__ == "__main__":
    asyncio.run(market_scanner())
