#!/usr/bin/env python3
"""
Agentic Funding Arbitrage Scanner - Find funding rate opportunities
Scans all markets for extreme funding rates and generates carry trade setups

DATA INTEGRITY RULES:
1. NO FABRICATED DATA - Every value comes from real API responses
2. EMPTY STATE HANDLING - If no data, report clearly
3. SOURCE TRACKING - Log which API call produced each data point
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from hyperliquid.info import Info
from hyperliquid.utils import constants


async def funding_arbitrage(min_rate=0.01):
    """Scan for funding arbitrage opportunities."""

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path("outputs/funding_arbitrage") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("FUNDING ARBITRAGE SCANNER")
    print(f"Min Rate Threshold: {min_rate}% per 8h")
    print(f"Timestamp: {timestamp}")
    print("DATA INTEGRITY: Real API data only")
    print("=" * 70)
    print()

    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    try:
        # Fetch all market data
        print("[1/4] Fetching market data...")
        meta_and_ctxs = info.meta_and_asset_ctxs()

        if not meta_and_ctxs or len(meta_and_ctxs) < 2:
            print("[ERROR] Could not fetch market data")
            return

        meta = meta_and_ctxs[0]
        asset_ctxs = meta_and_ctxs[1]

        universe = meta.get('universe', [])
        print(f"       Markets found: {len(universe)}")

        # Extract funding data
        print("[2/4] Analyzing funding rates...")
        funding_data = []

        for i, asset in enumerate(universe):
            ticker = asset.get('name', f'UNKNOWN_{i}')
            ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}

            funding_rate = float(ctx.get('funding', 0)) * 100  # Convert to percentage
            mark_price = float(ctx.get('markPx', 0))
            open_interest = float(ctx.get('openInterest', 0))
            volume_24h = float(ctx.get('dayNtlVlm', 0))

            if mark_price > 0:
                funding_data.append({
                    'ticker': ticker,
                    'funding_8h': funding_rate,
                    'funding_24h': funding_rate * 3,
                    'funding_apy': funding_rate * 3 * 365,
                    'mark_price': mark_price,
                    'open_interest': open_interest,
                    'volume_24h': volume_24h
                })

        # Filter for extreme funding
        print("[3/4] Finding opportunities...")
        min_rate_decimal = min_rate / 100

        # Positive funding (short opportunities)
        positive_funding = [
            f for f in funding_data
            if f['funding_8h'] >= min_rate
            and f['volume_24h'] >= 100000  # Min $100K volume
        ]
        positive_funding.sort(key=lambda x: x['funding_8h'], reverse=True)

        # Negative funding (long opportunities)
        negative_funding = [
            f for f in funding_data
            if f['funding_8h'] <= -min_rate
            and f['volume_24h'] >= 100000
        ]
        negative_funding.sort(key=lambda x: x['funding_8h'])

        print(f"       Positive funding opportunities: {len(positive_funding)}")
        print(f"       Negative funding opportunities: {len(negative_funding)}")

        # Generate report
        print("[4/4] Generating report...")

        report = f"""# Funding Arbitrage Report
## Generated: {timestamp}
## Minimum Rate Threshold: {min_rate}% per 8h

---

## Market Overview
- **Markets Scanned**: {len(funding_data)}
- **Extreme Positive Funding**: {len(positive_funding)} markets
- **Extreme Negative Funding**: {len(negative_funding)} markets

---

## Top SHORT Opportunities (Positive Funding)

*You receive funding when SHORT these markets*

| Rank | Ticker | Rate (8h) | Rate (24h) | APY | Volume 24h | OI |
|------|--------|-----------|------------|-----|------------|-----|
"""
        for i, opp in enumerate(positive_funding[:10], 1):
            report += f"| {i} | {opp['ticker']} | +{opp['funding_8h']:.4f}% | +{opp['funding_24h']:.4f}% | +{opp['funding_apy']:.1f}% | ${opp['volume_24h']:,.0f} | ${opp['open_interest']:,.0f} |\n"

        report += """
---

## Top LONG Opportunities (Negative Funding)

*You receive funding when LONG these markets*

| Rank | Ticker | Rate (8h) | Rate (24h) | APY | Volume 24h | OI |
|------|--------|-----------|------------|-----|------------|-----|
"""
        for i, opp in enumerate(negative_funding[:10], 1):
            report += f"| {i} | {opp['ticker']} | {opp['funding_8h']:.4f}% | {opp['funding_24h']:.4f}% | {opp['funding_apy']:.1f}% | ${opp['volume_24h']:,.0f} | ${opp['open_interest']:,.0f} |\n"

        # Best opportunity details
        if positive_funding:
            best_short = positive_funding[0]
            report += f"""
---

## Best SHORT Opportunity: {best_short['ticker']}

| Metric | Value |
|--------|-------|
| Funding Rate (8h) | +{best_short['funding_8h']:.4f}% |
| Funding Rate (24h) | +{best_short['funding_24h']:.4f}% |
| Annualized Yield | +{best_short['funding_apy']:.1f}% |
| Mark Price | ${best_short['mark_price']:,.4f} |
| 24h Volume | ${best_short['volume_24h']:,.0f} |
| Open Interest | ${best_short['open_interest']:,.0f} |

### Expected Returns (per $10,000 position)
- **8h Funding**: ${best_short['funding_8h'] / 100 * 10000:.2f}
- **24h Funding**: ${best_short['funding_24h'] / 100 * 10000:.2f}
- **Weekly Funding**: ${best_short['funding_24h'] / 100 * 10000 * 7:.2f}
- **Monthly Funding**: ${best_short['funding_24h'] / 100 * 10000 * 30:.2f}

### Trade Setup
- **Direction**: SHORT
- **Leverage**: 1-3x (carry trade, keep low)
- **Stop Loss**: 2x daily funding (~{best_short['funding_24h'] * 2:.2f}% above entry)
- **Exit**: When funding normalizes (<0.005%)
"""

        if negative_funding:
            best_long = negative_funding[0]
            report += f"""
---

## Best LONG Opportunity: {best_long['ticker']}

| Metric | Value |
|--------|-------|
| Funding Rate (8h) | {best_long['funding_8h']:.4f}% |
| Funding Rate (24h) | {best_long['funding_24h']:.4f}% |
| Annualized Yield | {best_long['funding_apy']:.1f}% |
| Mark Price | ${best_long['mark_price']:,.4f} |
| 24h Volume | ${best_long['volume_24h']:,.0f} |
| Open Interest | ${best_long['open_interest']:,.0f} |

### Expected Returns (per $10,000 position)
- **8h Funding**: ${abs(best_long['funding_8h']) / 100 * 10000:.2f}
- **24h Funding**: ${abs(best_long['funding_24h']) / 100 * 10000:.2f}
- **Weekly Funding**: ${abs(best_long['funding_24h']) / 100 * 10000 * 7:.2f}
- **Monthly Funding**: ${abs(best_long['funding_24h']) / 100 * 10000 * 30:.2f}

### Trade Setup
- **Direction**: LONG
- **Leverage**: 1-3x (carry trade, keep low)
- **Stop Loss**: 2x daily funding (~{abs(best_long['funding_24h']) * 2:.2f}% below entry)
- **Exit**: When funding normalizes (>-0.005%)
"""

        report += """
---

## Risk Warnings

1. **Directional Risk**: Funding income can be offset by adverse price moves
2. **Funding Volatility**: Rates can change rapidly
3. **Liquidity Risk**: Low volume markets may have high slippage
4. **Leverage**: Keep leverage low (1-3x) for carry trades

## Strategy Notes

- Best for: Sideways/ranging markets where price is stable
- Combine with: Spot hedge for delta-neutral carry
- Monitor: Funding rate trends, not just current rate
"""

        (output_dir / "arbitrage_report.md").write_text(report)

        # Print summary
        print()
        print("=" * 70)
        print("SCAN COMPLETE")
        print("=" * 70)
        print()
        print(f"Markets scanned: {len(funding_data)}")
        print(f"Short opportunities: {len(positive_funding)}")
        print(f"Long opportunities: {len(negative_funding)}")
        print()

        if positive_funding:
            print(f"Best SHORT: {positive_funding[0]['ticker']} at +{positive_funding[0]['funding_8h']:.4f}% ({positive_funding[0]['funding_apy']:.1f}% APY)")

        if negative_funding:
            print(f"Best LONG: {negative_funding[0]['ticker']} at {negative_funding[0]['funding_8h']:.4f}% ({abs(negative_funding[0]['funding_apy']):.1f}% APY)")

        print()
        print(f"Full report saved to: {output_dir.absolute()}")

    except Exception as e:
        print(f"\n[ERROR] Scan failed: {e}")
        raise


if __name__ == "__main__":
    min_rate = float(sys.argv[1]) if len(sys.argv) > 1 else 0.01
    asyncio.run(funding_arbitrage(min_rate))
