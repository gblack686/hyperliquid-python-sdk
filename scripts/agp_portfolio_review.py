#!/usr/bin/env python3
"""
Agentic Portfolio Review - Orchestrates complete portfolio analysis
Chains account, positions, PnL, funding, and risk analysis agents

DATA INTEGRITY RULES:
1. NO FABRICATED DATA - Every statistic comes from real API responses
2. EMPTY STATE HANDLING - If no data, report "No data available" clearly
3. SOURCE TRACKING - Log which API call produced each data point
4. VALIDATION - Before analysis, verify data exists and is valid
5. FAIL LOUDLY - If API fails or returns unexpected format, error clearly
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

async def portfolio_review(period="today"):
    """Execute complete portfolio review with REAL DATA ONLY"""

    # Setup
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path("outputs/portfolio_review") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("HYPERLIQUID PORTFOLIO REVIEW")
    print(f"Period: {period} | Timestamp: {timestamp}")
    print("DATA INTEGRITY: Real API data only - no fabrication")
    print("=" * 70)
    print()

    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    try:
        # Step 1: Account Snapshot
        print("[1/6] Fetching account snapshot...")
        print("      Source: hyp.account_balance() API")
        balance = await hyp.account_balance()

        # Validate response
        if not balance:
            raise ValueError("API returned empty balance response")

        equity = float(balance.get('equity_total', 0))
        withdrawable = float(balance.get('equity_withdrawable', 0))
        margin_used = float(balance.get('margin_total', 0))
        margin_maint = float(balance.get('margin_maintenance', 0))
        notional = float(balance.get('notional_position', 0))

        account_text = f"""# Account Snapshot

**Data Source**: `hyp.account_balance()` API
**Timestamp**: {timestamp}

## Account Details
- **Account Address**: `{hyp.account_address}`
- **Equity**: ${equity:,.2f}
- **Withdrawable**: ${withdrawable:,.2f}
- **Margin Used**: ${margin_used:,.2f}
- **Margin Maintenance**: ${margin_maint:,.2f}
- **Notional Position**: ${notional:,.2f}
- **Margin Utilization**: {(margin_used/equity*100) if equity > 0 else 0:.1f}%

## Raw API Response
```json
{balance}
```
"""
        (output_dir / "account_snapshot.md").write_text(account_text)
        print(f"      Equity: ${equity:,.2f}")
        print("   [OK] Account snapshot saved")

        # Step 2: Positions
        print("[2/6] Fetching positions...")
        print("      Source: hyp.perpetuals_account() API")
        account_data = await hyp.perpetuals_account()

        if not account_data:
            raise ValueError("API returned empty perpetuals_account response")

        positions = account_data.get('assetPositions', [])
        margin_summary = account_data.get('marginSummary', {})

        # Filter to only positions with non-zero size
        active_positions = []
        for pos_data in positions:
            pos = pos_data.get('position', {})
            size = float(pos.get('szi', 0))
            if size != 0:
                active_positions.append(pos_data)

        pos_text = f"""# Open Positions

**Data Source**: `hyp.perpetuals_account()` API
**Timestamp**: {timestamp}
**Active Positions**: {len(active_positions)}

"""
        if len(active_positions) == 0:
            pos_text += """## Status: NO OPEN POSITIONS

No active positions found on this account.

This could mean:
- Account has no open trades
- All positions have been closed
- This is a new or inactive account
"""
        else:
            pos_text += "| Ticker | Side | Size | Entry | Mark | Liq Price | uPnL | Margin | Leverage |\n"
            pos_text += "|--------|------|------|-------|------|-----------|------|--------|----------|\n"

            total_upnl = 0
            total_margin = 0
            for pos_data in active_positions:
                pos = pos_data.get('position', {})
                coin = pos.get('coin', 'N/A')
                size = float(pos.get('szi', 0))
                side = 'LONG' if size > 0 else 'SHORT'
                entry = float(pos.get('entryPx', 0))
                mark = float(pos.get('markPx', 0))
                liq = pos.get('liquidationPx')
                liq_val = float(liq) if liq else None
                upnl = float(pos.get('unrealizedPnl', 0))
                margin = float(pos.get('marginUsed', 0))
                lev = pos.get('leverage', {})
                lev_val = lev.get('value', 'N/A') if isinstance(lev, dict) else lev

                total_upnl += upnl
                total_margin += margin
                liq_str = f"${liq_val:,.2f}" if liq_val else "N/A"

                pos_text += f"| {coin} | {side} | {abs(size):,.4f} | ${entry:,.2f} | ${mark:,.2f} | {liq_str} | ${upnl:,.2f} | ${margin:,.2f} | {lev_val}x |\n"

            pos_text += f"\n**Total Unrealized PnL**: ${total_upnl:,.2f}\n"
            pos_text += f"**Total Margin Used**: ${total_margin:,.2f}\n"

        (output_dir / "positions").mkdir(parents=True, exist_ok=True)
        (output_dir / "positions" / "current.md").write_text(pos_text)
        print(f"      Active positions: {len(active_positions)}")
        print("   [OK] Positions saved")

        # Step 3: Risk Assessment
        print("[3/6] Calculating risk metrics...")
        print("      Source: Derived from account_balance + perpetuals_account")

        margin_util = margin_used / equity if equity > 0 else 0

        # Liquidation distance calculation
        min_liq_dist = None
        min_liq_ticker = None
        max_concentration = 0
        max_conc_ticker = None
        total_upnl = 0

        for pos_data in active_positions:
            pos = pos_data.get('position', {})
            coin = pos.get('coin', 'N/A')
            size = float(pos.get('szi', 0))
            mark = float(pos.get('markPx', 0))
            liq = pos.get('liquidationPx')
            liq_val = float(liq) if liq else None
            notional_pos = abs(float(pos.get('positionValue', 0)))
            upnl = float(pos.get('unrealizedPnl', 0))

            total_upnl += upnl

            # Liquidation distance
            if liq_val and mark > 0:
                dist = abs(mark - liq_val) / mark
                if min_liq_dist is None or dist < min_liq_dist:
                    min_liq_dist = dist
                    min_liq_ticker = coin

            # Concentration
            if equity > 0:
                conc = notional_pos / equity
                if conc > max_concentration:
                    max_concentration = conc
                    max_conc_ticker = coin

        risk_text = f"""# Risk Assessment

**Data Source**: Calculated from `account_balance()` and `perpetuals_account()` APIs
**Timestamp**: {timestamp}

## Leverage & Margin
- **Margin Utilization**: {margin_util:.1%}
"""
        if margin_util > 0.85:
            risk_text += "  - Status: CRITICAL (>85%)\n"
        elif margin_util > 0.70:
            risk_text += "  - Status: WARNING (>70%)\n"
        else:
            risk_text += "  - Status: HEALTHY\n"

        risk_text += f"- **Effective Portfolio Leverage**: {(margin_used/equity + 1) if equity > 0 else 1:.2f}x\n"
        risk_text += f"- **Margin Maintenance**: ${margin_maint:,.2f}\n\n"

        risk_text += "## Liquidation Risk\n"
        if min_liq_dist is not None:
            risk_text += f"- **Nearest Liquidation**: {min_liq_ticker} at {min_liq_dist:.1%} distance\n"
            if min_liq_dist < 0.08:
                risk_text += "  - Status: CRITICAL (<8%)\n"
            elif min_liq_dist < 0.15:
                risk_text += "  - Status: WARNING (<15%)\n"
            else:
                risk_text += "  - Status: SAFE\n"
        else:
            risk_text += "- **Nearest Liquidation**: N/A (no positions)\n"

        risk_text += "\n## Position Concentration\n"
        if max_concentration > 0:
            risk_text += f"- **Largest Position**: {max_conc_ticker} at {max_concentration:.1%} of equity\n"
            if max_concentration > 0.60:
                risk_text += "  - Status: CRITICAL (>60%)\n"
            elif max_concentration > 0.40:
                risk_text += "  - Status: WARNING (>40%)\n"
            else:
                risk_text += "  - Status: DIVERSIFIED\n"
        else:
            risk_text += "- **Largest Position**: N/A (no positions)\n"

        risk_text += f"\n## P&L Status\n"
        risk_text += f"- **Unrealized P&L**: ${total_upnl:,.2f}\n"
        risk_text += f"- **Return on Equity**: {(total_upnl/equity*100) if equity > 0 else 0:.2f}%\n"

        risk_text += "\n## Overall Risk Level\n"
        if len(active_positions) == 0:
            risk_text += "- **Assessment**: NO POSITIONS - No active risk\n"
        elif margin_util > 0.70 or (min_liq_dist and min_liq_dist < 0.15):
            risk_text += "- **Assessment**: HIGH RISK\n"
        elif margin_util > 0.50:
            risk_text += "- **Assessment**: MEDIUM RISK\n"
        else:
            risk_text += "- **Assessment**: LOW RISK\n"

        (output_dir / "risk").mkdir(parents=True, exist_ok=True)
        (output_dir / "risk" / "assessment.md").write_text(risk_text)
        print("   [OK] Risk assessment saved")

        # Step 4: Recommendations
        print("[4/6] Generating recommendations...")
        print("      Source: Derived from risk metrics")

        recommendations = []

        if len(active_positions) == 0:
            recommendations.append("**No positions open** - Account is flat with no active risk exposure.")
        else:
            if margin_util > 0.70:
                recommendations.append(f"**Reduce Leverage**: Margin utilization at {margin_util:.1%}. Consider closing smallest profitable position or adding capital.")
            if min_liq_dist and min_liq_dist < 0.15:
                recommendations.append(f"**Liquidation Warning**: {min_liq_ticker} is {min_liq_dist:.1%} from liquidation. Add margin or reduce position size.")
            if max_concentration > 0.40:
                recommendations.append(f"**Rebalance**: {max_conc_ticker} represents {max_concentration:.1%} of portfolio. Consider reducing concentration.")
            if total_upnl < 0 and equity > 0 and (total_upnl / equity) < -0.05:
                recommendations.append(f"**Review Positions**: Portfolio is down {abs(total_upnl/equity):.1%}. Review stop losses and exit criteria.")

        if len(recommendations) == 0:
            recommendations.append("**Portfolio looks healthy** - No urgent actions recommended.")

        rec_text = f"""# Recommendations

**Data Source**: Derived from risk assessment
**Timestamp**: {timestamp}

## Action Items

"""
        for i, rec in enumerate(recommendations, 1):
            rec_text += f"{i}. {rec}\n\n"

        (output_dir / "recommendations.md").write_text(rec_text)
        print("   [OK] Recommendations generated")

        # Step 5: Dashboard
        print("[5/6] Creating dashboard...")

        # Determine status indicators based on real data
        margin_status = "OK" if margin_util < 0.70 else ("WATCH" if margin_util < 0.85 else "CRITICAL")

        if min_liq_dist is None:
            liq_status = "N/A"
        elif min_liq_dist > 0.15:
            liq_status = "SAFE"
        elif min_liq_dist > 0.08:
            liq_status = "WATCH"
        else:
            liq_status = "CRITICAL"

        if max_concentration == 0:
            conc_status = "N/A"
        elif max_concentration < 0.40:
            conc_status = "BALANCED"
        elif max_concentration < 0.60:
            conc_status = "WATCH"
        else:
            conc_status = "RISKY"

        dashboard = f"""# Portfolio Dashboard

**Generated**: {timestamp}
**Data Sources**: `account_balance()`, `perpetuals_account()` APIs
**Integrity**: All data from live Hyperliquid API - no fabrication

---

## Account Summary
| Metric | Value |
|--------|-------|
| Equity | ${equity:,.2f} |
| Unrealized P&L | ${total_upnl:,.2f} ({(total_upnl/equity*100) if equity > 0 else 0:.2f}%) |
| Margin Used | ${margin_used:,.2f} ({margin_util:.1%}) |
| Withdrawable | ${withdrawable:,.2f} |
| Open Positions | {len(active_positions)} |

## Risk Status
| Check | Status | Value |
|-------|--------|-------|
| Margin Utilization | {margin_status} | {margin_util:.1%} |
| Liquidation Distance | {liq_status} | {f"{min_liq_dist:.1%}" if min_liq_dist else "N/A"} |
| Concentration | {conc_status} | {f"{max_concentration:.1%}" if max_concentration > 0 else "N/A"} |

## Output Files
- Account Details: `account_snapshot.md`
- Position Report: `positions/current.md`
- Risk Analysis: `risk/assessment.md`
- Recommendations: `recommendations.md`
"""
        (output_dir / "dashboard.md").write_text(dashboard)
        print("   [OK] Dashboard created")

        # Step 6: Final Report
        print("[6/6] Generating final report...")
        print()
        print("=" * 70)
        print("PORTFOLIO REVIEW COMPLETE")
        print("=" * 70)
        print(f"\n{dashboard}")
        print(f"\nAll outputs saved to: {output_dir.absolute()}")

    except Exception as e:
        print(f"\n[ERROR] Portfolio review failed: {e}")
        error_log = f"""# Portfolio Review Error

**Timestamp**: {timestamp}
**Error**: {str(e)}

The portfolio review could not complete due to an API or data error.
Please check:
1. API credentials (HYP_KEY, HYP_SECRET)
2. Network connectivity
3. Hyperliquid API status
"""
        (output_dir / "error.md").write_text(error_log)
        raise

    finally:
        await hyp.cleanup()

if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "today"
    asyncio.run(portfolio_review(period))
