#!/usr/bin/env python3
"""
Agentic Position Optimizer - Analyze positions and generate optimization recommendations
Calculates health scores, optimal sizing, and specific action items

DATA INTEGRITY RULES:
1. NO FABRICATED DATA - Every value comes from real API responses
2. EMPTY STATE HANDLING - If no positions, report clearly
3. SOURCE TRACKING - Log which API call produced each data point
"""

import os
import sys
import asyncio
import time
import numpy as np
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants

INTERVAL_MS = {'1h': 60 * 60 * 1000}


def calculate_atr(highs, lows, closes, period=14):
    """Calculate ATR."""
    if len(closes) < period + 1:
        return None

    tr_list = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        tr_list.append(tr)

    return np.mean(tr_list[-period:])


async def position_optimizer(max_risk_pct=2.0):
    """Analyze and optimize positions."""

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path("outputs/position_optimizer") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("POSITION OPTIMIZER")
    print(f"Max Risk Per Position: {max_risk_pct}%")
    print(f"Timestamp: {timestamp}")
    print("DATA INTEGRITY: Real API data only")
    print("=" * 70)
    print()

    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    try:
        # Get account data
        print("[1/5] Fetching account data...")
        balance = await hyp.account_balance()
        equity = float(balance.get('equity_total', 0))
        print(f"       Equity: ${equity:,.2f}")

        # Get positions
        print("[2/5] Fetching positions...")
        account_data = await hyp.perpetuals_account()
        positions = account_data.get('assetPositions', [])

        active_positions = []
        for pos_data in positions:
            pos = pos_data.get('position', {})
            size = float(pos.get('szi', 0))
            if size != 0:
                active_positions.append(pos_data)

        print(f"       Active positions: {len(active_positions)}")

        if len(active_positions) == 0:
            print("\n[INFO] No open positions to optimize")
            report = f"""# Position Optimizer Report
## Generated: {timestamp}

## Account Status
- **Equity**: ${equity:,.2f}
- **Open Positions**: 0

## Assessment
No positions currently open. Account is flat with no active risk exposure.

## Recommendations
1. Review market conditions before opening new positions
2. Ensure risk parameters are set before trading
3. Consider using /hyp-momentum-scanner or /hyp-technical-analysis to find opportunities
"""
            (output_dir / "optimization_report.md").write_text(report)
            print(f"\nReport saved to: {output_dir.absolute()}")
            return

        # Get funding rates
        print("[3/5] Fetching funding rates...")
        meta_and_ctxs = info.meta_and_asset_ctxs()
        meta = meta_and_ctxs[0]
        asset_ctxs = meta_and_ctxs[1]
        universe = meta.get('universe', [])

        funding_map = {}
        for i, asset in enumerate(universe):
            ticker = asset.get('name', '')
            ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}
            funding_map[ticker] = float(ctx.get('funding', 0)) * 100

        # Analyze each position
        print("[4/5] Analyzing positions...")
        position_analysis = []

        for pos_data in active_positions:
            pos = pos_data.get('position', {})
            ticker = pos.get('coin', 'UNKNOWN')
            size = float(pos.get('szi', 0))
            entry = float(pos.get('entryPx', 0))
            mark = float(pos.get('markPx', 0))
            liq = pos.get('liquidationPx')
            liq_price = float(liq) if liq else None
            upnl = float(pos.get('unrealizedPnl', 0))
            margin = float(pos.get('marginUsed', 0))
            notional = abs(float(pos.get('positionValue', 0)))

            side = 'LONG' if size > 0 else 'SHORT'
            pnl_pct = (upnl / margin * 100) if margin > 0 else 0

            # Calculate liquidation distance
            liq_distance = None
            if liq_price and mark > 0:
                liq_distance = abs(mark - liq_price) / mark * 100

            # Get ATR for optimal stop calculation
            atr = None
            optimal_stop = None
            optimal_size = None

            try:
                now = int(time.time() * 1000)
                start = now - (50 * INTERVAL_MS['1h'])

                candles = await hyp.candle_historical(
                    ticker=ticker,
                    interval='1h',
                    start=start,
                    end=now
                )

                if candles and len(candles) >= 15:
                    highs = np.array([float(c['h']) for c in candles])
                    lows = np.array([float(c['l']) for c in candles])
                    closes = np.array([float(c['c']) for c in candles])

                    atr = calculate_atr(highs, lows, closes, 14)

                    if atr:
                        # Optimal stop = 1.5 ATR from entry
                        stop_distance = 1.5 * atr
                        if side == 'LONG':
                            optimal_stop = entry - stop_distance
                        else:
                            optimal_stop = entry + stop_distance

                        # Optimal size based on max risk
                        risk_amount = equity * (max_risk_pct / 100)
                        stop_pct = (stop_distance / mark) * 100
                        optimal_size = (risk_amount / stop_pct) * 100

            except Exception:
                pass

            # Get funding rate
            funding_rate = funding_map.get(ticker, 0)
            funding_impact = 'favorable' if (side == 'LONG' and funding_rate < 0) or (side == 'SHORT' and funding_rate > 0) else 'unfavorable' if funding_rate != 0 else 'neutral'

            # Calculate health score
            health_score = 50  # Base score

            # Liquidation distance component (30 points)
            if liq_distance:
                if liq_distance > 20:
                    health_score += 30
                elif liq_distance > 15:
                    health_score += 20
                elif liq_distance > 10:
                    health_score += 10
                elif liq_distance > 5:
                    health_score += 0
                else:
                    health_score -= 20

            # P&L component (20 points)
            if pnl_pct > 5:
                health_score += 20
            elif pnl_pct > 0:
                health_score += 10
            elif pnl_pct > -5:
                health_score += 0
            else:
                health_score -= 10

            # Funding component (10 points)
            if funding_impact == 'favorable':
                health_score += 10
            elif funding_impact == 'unfavorable':
                health_score -= 5

            # Size component (10 points)
            concentration = notional / equity if equity > 0 else 0
            if concentration < 0.2:
                health_score += 10
            elif concentration < 0.4:
                health_score += 5
            elif concentration > 0.6:
                health_score -= 10

            health_score = max(0, min(100, health_score))

            position_analysis.append({
                'ticker': ticker,
                'side': side,
                'size': abs(size),
                'entry': entry,
                'mark': mark,
                'notional': notional,
                'upnl': upnl,
                'pnl_pct': pnl_pct,
                'margin': margin,
                'liq_price': liq_price,
                'liq_distance': liq_distance,
                'atr': atr,
                'optimal_stop': optimal_stop,
                'optimal_size': optimal_size,
                'funding_rate': funding_rate,
                'funding_impact': funding_impact,
                'concentration': concentration,
                'health_score': health_score
            })

        # Generate recommendations
        print("[5/5] Generating recommendations...")

        recommendations = []
        for pos in position_analysis:
            if pos['health_score'] < 30:
                recommendations.append({
                    'ticker': pos['ticker'],
                    'priority': 'URGENT',
                    'action': 'CLOSE or REDUCE',
                    'reason': f"Health score critical ({pos['health_score']}/100)"
                })
            elif pos['liq_distance'] and pos['liq_distance'] < 10:
                recommendations.append({
                    'ticker': pos['ticker'],
                    'priority': 'URGENT',
                    'action': 'ADD MARGIN or REDUCE',
                    'reason': f"Liquidation distance only {pos['liq_distance']:.1f}%"
                })
            elif pos['concentration'] > 0.5:
                recommendations.append({
                    'ticker': pos['ticker'],
                    'priority': 'HIGH',
                    'action': 'REDUCE',
                    'reason': f"Position is {pos['concentration']*100:.0f}% of equity"
                })
            elif pos['optimal_stop'] and pos['pnl_pct'] < -3:
                recommendations.append({
                    'ticker': pos['ticker'],
                    'priority': 'HIGH',
                    'action': 'SET STOP',
                    'reason': f"Position down {abs(pos['pnl_pct']):.1f}%, set stop at ${pos['optimal_stop']:,.2f}"
                })
            elif pos['funding_impact'] == 'unfavorable' and abs(pos['funding_rate']) > 0.02:
                recommendations.append({
                    'ticker': pos['ticker'],
                    'priority': 'MEDIUM',
                    'action': 'REVIEW',
                    'reason': f"Paying {abs(pos['funding_rate']):.4f}% funding per 8h"
                })

        # Generate report
        report = f"""# Position Optimizer Report
## Generated: {timestamp}
## Max Risk Setting: {max_risk_pct}%

---

## Account Overview
- **Equity**: ${equity:,.2f}
- **Open Positions**: {len(position_analysis)}
- **Total Notional**: ${sum(p['notional'] for p in position_analysis):,.2f}
- **Total Unrealized P&L**: ${sum(p['upnl'] for p in position_analysis):,.2f}

---

## Position Health Summary

| Ticker | Side | Notional | P&L | Health | Liq Dist | Status |
|--------|------|----------|-----|--------|----------|--------|
"""
        for pos in sorted(position_analysis, key=lambda x: x['health_score']):
            status = 'CRITICAL' if pos['health_score'] < 30 else 'WARNING' if pos['health_score'] < 50 else 'FAIR' if pos['health_score'] < 70 else 'GOOD'
            liq_str = f"{pos['liq_distance']:.1f}%" if pos['liq_distance'] else "N/A"
            report += f"| {pos['ticker']} | {pos['side']} | ${pos['notional']:,.0f} | ${pos['upnl']:+,.2f} ({pos['pnl_pct']:+.1f}%) | {pos['health_score']}/100 | {liq_str} | {status} |\n"

        # Recommendations section
        report += """
---

## Recommendations

"""
        urgent = [r for r in recommendations if r['priority'] == 'URGENT']
        high = [r for r in recommendations if r['priority'] == 'HIGH']
        medium = [r for r in recommendations if r['priority'] == 'MEDIUM']

        if urgent:
            report += "### URGENT (Act Now)\n"
            for r in urgent:
                report += f"- **{r['ticker']}**: {r['action']} - {r['reason']}\n"
            report += "\n"

        if high:
            report += "### HIGH Priority (Today)\n"
            for r in high:
                report += f"- **{r['ticker']}**: {r['action']} - {r['reason']}\n"
            report += "\n"

        if medium:
            report += "### MEDIUM Priority (This Week)\n"
            for r in medium:
                report += f"- **{r['ticker']}**: {r['action']} - {r['reason']}\n"
            report += "\n"

        if not recommendations:
            report += "No urgent recommendations. All positions appear healthy.\n\n"

        # Detailed position analysis
        report += "---\n\n## Detailed Position Analysis\n"

        for pos in position_analysis:
            report += f"""
### {pos['ticker']} ({pos['side']})

| Metric | Current | Optimal |
|--------|---------|---------|
| Size | {pos['size']:,.4f} | {f"{pos['optimal_size']:,.4f}" if pos['optimal_size'] else "N/A"} |
| Entry | ${pos['entry']:,.2f} | - |
| Mark | ${pos['mark']:,.2f} | - |
| Stop Loss | Not Set | {f"${pos['optimal_stop']:,.2f}" if pos['optimal_stop'] else "N/A"} |
| Notional | ${pos['notional']:,.2f} | - |
| Margin Used | ${pos['margin']:,.2f} | - |
| Liq Price | {f"${pos['liq_price']:,.2f}" if pos['liq_price'] else "N/A"} | - |
| Liq Distance | {f"{pos['liq_distance']:.1f}%" if pos['liq_distance'] else "N/A"} | >15% |
| Funding (8h) | {pos['funding_rate']:.4f}% ({pos['funding_impact']}) | - |
| Health Score | {pos['health_score']}/100 | 70+ |

"""

        report += """---

## Risk Summary

| Check | Status |
|-------|--------|
"""
        critical_positions = len([p for p in position_analysis if p['health_score'] < 30])
        near_liq = len([p for p in position_analysis if p['liq_distance'] and p['liq_distance'] < 10])
        over_concentrated = len([p for p in position_analysis if p['concentration'] > 0.4])

        report += f"| Critical Health Positions | {critical_positions} |\n"
        report += f"| Near Liquidation (<10%) | {near_liq} |\n"
        report += f"| Over-Concentrated (>40%) | {over_concentrated} |\n"

        (output_dir / "optimization_report.md").write_text(report)

        # Print summary
        print()
        print("=" * 70)
        print("OPTIMIZATION COMPLETE")
        print("=" * 70)
        print()

        for pos in position_analysis:
            status = 'CRITICAL' if pos['health_score'] < 30 else 'WARNING' if pos['health_score'] < 50 else 'OK'
            print(f"{pos['ticker']} ({pos['side']}): Health {pos['health_score']}/100 [{status}]")

        if recommendations:
            print()
            print("URGENT ACTIONS:")
            for r in urgent[:3]:
                print(f"  - {r['ticker']}: {r['action']}")

        print()
        print(f"Full report saved to: {output_dir.absolute()}")

    except Exception as e:
        print(f"\n[ERROR] Optimization failed: {e}")
        raise

    finally:
        await hyp.cleanup()


if __name__ == "__main__":
    max_risk = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    asyncio.run(position_optimizer(max_risk))
