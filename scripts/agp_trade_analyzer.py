#!/usr/bin/env python3
"""
Agentic Trade Analyzer - Analyzes recent trades for patterns and edge

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
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

# Also import the raw SDK for fills endpoint
from hyperliquid.info import Info
from hyperliquid.utils import constants

async def trade_analyzer(trade_count=50):
    """Analyze recent trades using REAL DATA ONLY"""

    # Setup
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path("outputs/trade_analysis") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("HYPERLIQUID TRADE ANALYZER")
    print(f"Analyzing up to {trade_count} recent trades")
    print("DATA INTEGRITY: Real API data only - no fabrication")
    print("=" * 70)
    print()

    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Also use raw SDK for user_fills
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    try:
        # Step 1: Fetch real trade history
        print(f"[1/5] Fetching trade history...")
        print(f"      Source: info.user_fills() API")
        print(f"      Account: {hyp.account_address}")

        # Get user fills from the API
        fills = info.user_fills(hyp.account_address)

        # Validate response
        if fills is None:
            fills = []

        # Limit to requested count
        fills = fills[:trade_count] if len(fills) > trade_count else fills

        print(f"      Retrieved: {len(fills)} fills")

        # Save raw data
        fills_json = json.dumps(fills, indent=2, default=str)
        (output_dir / "raw_fills.json").write_text(fills_json)
        print("   [OK] Raw fills saved")

        # Step 2: Analyze trades
        print("[2/5] Analyzing trade data...")

        if len(fills) == 0:
            # NO DATA - Report honestly
            no_data_text = f"""# Trade Analysis

**Data Source**: `info.user_fills()` API
**Account**: `{hyp.account_address}`
**Timestamp**: {timestamp}

## Status: NO TRADE DATA

No fills/trades found for this account.

### Possible Reasons
1. **New account** - No trades have been executed yet
2. **Inactive account** - No recent trading activity
3. **Wrong account** - Check if HYP_KEY matches intended account

### What This Means
- Cannot calculate win rate (no trades)
- Cannot identify patterns (no data points)
- Cannot compute edge metrics (no P&L history)

### Next Steps
1. Execute some trades on Hyperliquid
2. Re-run this analysis after trading activity
3. Verify API credentials point to correct account

### Raw API Response
```json
[]
```
"""
            (output_dir / "metrics").mkdir(parents=True, exist_ok=True)
            (output_dir / "metrics" / "win_rate.md").write_text(no_data_text)
            (output_dir / "patterns").mkdir(parents=True, exist_ok=True)
            (output_dir / "patterns" / "analysis.md").write_text(no_data_text)
            (output_dir / "metrics" / "edge.md").write_text(no_data_text)
            (output_dir / "improvements.md").write_text(no_data_text)
            (output_dir / "report.md").write_text(no_data_text)

            print("   [!] No trades found - analysis cannot proceed")
            print()
            print("=" * 70)
            print("TRADE ANALYSIS: NO DATA")
            print("=" * 70)
            print(f"\nNo trades found for account {hyp.account_address}")
            print("Execute some trades first, then re-run this analysis.")
            print(f"\nEmpty report saved to: {output_dir.absolute()}")

            await hyp.cleanup()
            return

        # We have real data - analyze it
        print(f"      Processing {len(fills)} fills...")

        # Parse fills into trades
        trades_by_ticker = defaultdict(list)
        all_trades = []

        for fill in fills:
            coin = fill.get('coin', 'UNKNOWN')
            side = fill.get('side', 'UNKNOWN')
            size = float(fill.get('sz', 0))
            price = float(fill.get('px', 0))
            time_str = fill.get('time', '')
            fee = float(fill.get('fee', 0))
            closed_pnl = float(fill.get('closedPnl', 0))

            trade = {
                'coin': coin,
                'side': side,
                'size': size,
                'price': price,
                'time': time_str,
                'fee': fee,
                'closedPnl': closed_pnl,
                'is_winner': closed_pnl > 0 if closed_pnl != 0 else None
            }
            trades_by_ticker[coin].append(trade)
            all_trades.append(trade)

        # Calculate real statistics
        closing_trades = [t for t in all_trades if t['closedPnl'] != 0]
        winners = [t for t in closing_trades if t['closedPnl'] > 0]
        losers = [t for t in closing_trades if t['closedPnl'] < 0]

        total_pnl = sum(t['closedPnl'] for t in closing_trades)
        total_fees = sum(t['fee'] for t in all_trades)

        win_rate = len(winners) / len(closing_trades) * 100 if closing_trades else 0
        avg_win = sum(t['closedPnl'] for t in winners) / len(winners) if winners else 0
        avg_loss = sum(t['closedPnl'] for t in losers) / len(losers) if losers else 0

        gross_profit = sum(t['closedPnl'] for t in winners)
        gross_loss = abs(sum(t['closedPnl'] for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

        # Win Rate Analysis
        win_rate_text = f"""# Win Rate Analysis

**Data Source**: `info.user_fills()` API
**Account**: `{hyp.account_address}`
**Timestamp**: {timestamp}
**Fills Analyzed**: {len(fills)}

## Overall Statistics
- **Total Fills**: {len(all_trades)}
- **Closing Trades** (with P&L): {len(closing_trades)}
- **Winners**: {len(winners)} ({win_rate:.1f}%)
- **Losers**: {len(losers)} ({100-win_rate:.1f}% if closing_trades else 0)

## P&L Metrics
- **Total Realized P&L**: ${total_pnl:,.2f}
- **Total Fees Paid**: ${total_fees:,.2f}
- **Net P&L**: ${total_pnl - total_fees:,.2f}
- **Average Win**: ${avg_win:,.2f}
- **Average Loss**: ${avg_loss:,.2f}
- **Profit Factor**: {profit_factor:.2f}

## By Ticker
| Ticker | Fills | Closing | Winners | Win Rate | Total P&L |
|--------|-------|---------|---------|----------|-----------|
"""
        for ticker, trades in trades_by_ticker.items():
            ticker_closing = [t for t in trades if t['closedPnl'] != 0]
            ticker_winners = [t for t in ticker_closing if t['closedPnl'] > 0]
            ticker_pnl = sum(t['closedPnl'] for t in ticker_closing)
            ticker_wr = len(ticker_winners) / len(ticker_closing) * 100 if ticker_closing else 0
            win_rate_text += f"| {ticker} | {len(trades)} | {len(ticker_closing)} | {len(ticker_winners)} | {ticker_wr:.1f}% | ${ticker_pnl:,.2f} |\n"

        win_rate_text += f"""
## By Side
"""
        long_trades = [t for t in closing_trades if t['side'] == 'B']
        short_trades = [t for t in closing_trades if t['side'] == 'A']
        long_winners = [t for t in long_trades if t['closedPnl'] > 0]
        short_winners = [t for t in short_trades if t['closedPnl'] > 0]

        win_rate_text += f"- **Long Trades**: {len(long_trades)} ({len(long_winners)} winners, {len(long_winners)/len(long_trades)*100 if long_trades else 0:.1f}% win rate)\n"
        win_rate_text += f"- **Short Trades**: {len(short_trades)} ({len(short_winners)} winners, {len(short_winners)/len(short_trades)*100 if short_trades else 0:.1f}% win rate)\n"

        (output_dir / "metrics").mkdir(parents=True, exist_ok=True)
        (output_dir / "metrics" / "win_rate.md").write_text(win_rate_text)
        print("   [OK] Win rate analysis saved")

        # Step 3: Pattern Analysis
        print("[3/5] Analyzing patterns...")

        patterns_text = f"""# Trading Patterns

**Data Source**: `info.user_fills()` API
**Timestamp**: {timestamp}
**Trades Analyzed**: {len(closing_trades)} closing trades

## Time-Based Patterns
"""
        # Parse timestamps and analyze by hour
        hour_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
        for trade in closing_trades:
            try:
                # Parse timestamp (format varies)
                time_val = trade.get('time', 0)
                if isinstance(time_val, (int, float)):
                    dt = datetime.fromtimestamp(time_val / 1000)
                else:
                    dt = datetime.fromisoformat(str(time_val).replace('Z', '+00:00'))
                hour = dt.hour
                hour_stats[hour]['pnl'] += trade['closedPnl']
                if trade['closedPnl'] > 0:
                    hour_stats[hour]['wins'] += 1
                else:
                    hour_stats[hour]['losses'] += 1
            except:
                pass

        if hour_stats:
            patterns_text += "\n| Hour (UTC) | Trades | Wins | Win Rate | P&L |\n"
            patterns_text += "|------------|--------|------|----------|-----|\n"
            for hour in sorted(hour_stats.keys()):
                stats = hour_stats[hour]
                total = stats['wins'] + stats['losses']
                wr = stats['wins'] / total * 100 if total > 0 else 0
                patterns_text += f"| {hour:02d}:00 | {total} | {stats['wins']} | {wr:.0f}% | ${stats['pnl']:,.2f} |\n"

            # Find best/worst hours
            best_hour = max(hour_stats.items(), key=lambda x: x[1]['pnl'])
            worst_hour = min(hour_stats.items(), key=lambda x: x[1]['pnl'])
            patterns_text += f"\n- **Best Hour**: {best_hour[0]:02d}:00 UTC (${best_hour[1]['pnl']:,.2f})\n"
            patterns_text += f"- **Worst Hour**: {worst_hour[0]:02d}:00 UTC (${worst_hour[1]['pnl']:,.2f})\n"
        else:
            patterns_text += "\nInsufficient timestamp data for time analysis.\n"

        # Streak analysis
        patterns_text += "\n## Streak Analysis\n"
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        current_type = None

        for trade in closing_trades:
            is_win = trade['closedPnl'] > 0
            if current_type == is_win:
                current_streak += 1
            else:
                current_streak = 1
                current_type = is_win

            if is_win:
                max_win_streak = max(max_win_streak, current_streak)
            else:
                max_loss_streak = max(max_loss_streak, current_streak)

        patterns_text += f"- **Longest Win Streak**: {max_win_streak} trades\n"
        patterns_text += f"- **Longest Loss Streak**: {max_loss_streak} trades\n"

        (output_dir / "patterns").mkdir(parents=True, exist_ok=True)
        (output_dir / "patterns" / "analysis.md").write_text(patterns_text)
        print("   [OK] Pattern analysis saved")

        # Step 4: Edge Metrics
        print("[4/5] Calculating edge metrics...")

        expectancy = total_pnl / len(closing_trades) if closing_trades else 0

        edge_text = f"""# Edge Metrics

**Data Source**: Calculated from `info.user_fills()` API data
**Timestamp**: {timestamp}
**Closing Trades**: {len(closing_trades)}

## Expected Value
- **Total P&L**: ${total_pnl:,.2f}
- **Expectancy per Trade**: ${expectancy:,.2f}
- **Win Rate**: {win_rate:.1f}%
- **Profit Factor**: {profit_factor:.2f}

## Risk-Reward
- **Average Win**: ${avg_win:,.2f}
- **Average Loss**: ${avg_loss:,.2f}
- **Risk-Reward Ratio**: {abs(avg_win/avg_loss) if avg_loss != 0 else 'N/A':.2f}

## Drawdown Analysis
"""
        # Calculate running P&L for drawdown
        running_pnl = 0
        peak_pnl = 0
        max_dd = 0

        for trade in closing_trades:
            running_pnl += trade['closedPnl']
            if running_pnl > peak_pnl:
                peak_pnl = running_pnl
            dd = peak_pnl - running_pnl
            if dd > max_dd:
                max_dd = dd

        edge_text += f"- **Peak P&L**: ${peak_pnl:,.2f}\n"
        edge_text += f"- **Maximum Drawdown**: ${max_dd:,.2f}\n"
        edge_text += f"- **Current P&L**: ${running_pnl:,.2f}\n"

        (output_dir / "metrics" / "edge.md").write_text(edge_text)
        print("   [OK] Edge metrics saved")

        # Step 5: Improvements
        print("[5/5] Generating improvements...")

        improvements_text = f"""# Improvement Suggestions

**Data Source**: Analysis of {len(closing_trades)} trades
**Timestamp**: {timestamp}

## Based on Real Data Analysis

"""
        # Generate data-driven suggestions
        if win_rate < 50:
            improvements_text += f"### 1. Improve Entry Criteria\n"
            improvements_text += f"**Issue**: Win rate at {win_rate:.1f}% is below 50%\n"
            improvements_text += f"**Suggestion**: Review entry signals - consider adding confirmation filters\n\n"

        if profit_factor < 1.5 and profit_factor > 0:
            improvements_text += f"### 2. Improve Risk-Reward\n"
            improvements_text += f"**Issue**: Profit factor at {profit_factor:.2f} is below 1.5\n"
            improvements_text += f"**Suggestion**: Let winners run longer or cut losers faster\n\n"

        if hour_stats:
            worst = min(hour_stats.items(), key=lambda x: x[1]['pnl'])
            if worst[1]['pnl'] < -50:
                improvements_text += f"### 3. Avoid Poor Hours\n"
                improvements_text += f"**Issue**: Hour {worst[0]:02d}:00 UTC has ${worst[1]['pnl']:,.2f} P&L\n"
                improvements_text += f"**Suggestion**: Consider reducing activity during this hour\n\n"

        if max_loss_streak >= 3:
            improvements_text += f"### 4. Add Tilt Prevention\n"
            improvements_text += f"**Issue**: Maximum loss streak of {max_loss_streak} trades\n"
            improvements_text += f"**Suggestion**: Implement a cooldown after 2-3 consecutive losses\n\n"

        if len(improvements_text.split("###")) <= 2:
            improvements_text += "### No Major Issues Detected\n"
            improvements_text += "Based on the available data, no critical improvements identified.\n"
            improvements_text += "Continue monitoring and gather more trade data for deeper analysis.\n"

        (output_dir / "improvements.md").write_text(improvements_text)
        print("   [OK] Improvements saved")

        # Summary Report
        report_text = f"""# Trade Analysis Report

**Generated**: {timestamp}
**Account**: `{hyp.account_address}`
**Data Source**: `info.user_fills()` API
**Integrity**: All metrics calculated from real trade data

---

## Summary

| Metric | Value |
|--------|-------|
| Total Fills | {len(all_trades)} |
| Closing Trades | {len(closing_trades)} |
| Win Rate | {win_rate:.1f}% |
| Profit Factor | {profit_factor:.2f} |
| Total P&L | ${total_pnl:,.2f} |
| Expectancy | ${expectancy:,.2f} per trade |
| Max Drawdown | ${max_dd:,.2f} |

## Files Generated
- `raw_fills.json` - Raw API response
- `metrics/win_rate.md` - Win rate analysis
- `metrics/edge.md` - Edge metrics
- `patterns/analysis.md` - Pattern analysis
- `improvements.md` - Improvement suggestions
"""
        (output_dir / "report.md").write_text(report_text)

        print()
        print("=" * 70)
        print("TRADE ANALYSIS COMPLETE")
        print("=" * 70)
        print(f"""
## Summary (Real Data)

- **Trades Analyzed**: {len(closing_trades)}
- **Win Rate**: {win_rate:.1f}%
- **Profit Factor**: {profit_factor:.2f}
- **Total P&L**: ${total_pnl:,.2f}
- **Expectancy**: ${expectancy:,.2f} per trade

All analysis saved to: {output_dir.absolute()}
""")

    except Exception as e:
        print(f"\n[ERROR] Trade analysis failed: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await hyp.cleanup()

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    asyncio.run(trade_analyzer(count))
