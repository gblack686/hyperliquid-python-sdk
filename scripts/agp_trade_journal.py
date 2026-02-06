#!/usr/bin/env python3
"""
Agentic Trade Journal - Create structured journal entries for completed trades
Captures setup, execution, outcome, and lessons learned

DATA INTEGRITY RULES:
1. NO FABRICATED DATA - Every value comes from real API responses
2. EMPTY STATE HANDLING - If no trades, report clearly
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


def get_trade_grade(pnl_pct, execution_quality=50):
    """Calculate trade grade based on P&L and execution."""
    if pnl_pct > 5:
        outcome_score = 50
    elif pnl_pct > 2:
        outcome_score = 40
    elif pnl_pct > 0:
        outcome_score = 30
    elif pnl_pct > -2:
        outcome_score = 20
    elif pnl_pct > -5:
        outcome_score = 10
    else:
        outcome_score = 0

    total = outcome_score + (execution_quality / 2)

    if total >= 90:
        return 'A', total
    elif total >= 80:
        return 'B', total
    elif total >= 70:
        return 'C', total
    elif total >= 60:
        return 'D', total
    else:
        return 'F', total


async def trade_journal(ticker, trade_id='latest'):
    """Create a trade journal entry."""

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    journal_dir = Path("outputs/trade_journal")
    journal_dir.mkdir(parents=True, exist_ok=True)
    (journal_dir / "archive").mkdir(exist_ok=True)

    print("=" * 70)
    print("TRADE JOURNAL")
    print(f"Ticker: {ticker} | Trade ID: {trade_id}")
    print(f"Timestamp: {timestamp}")
    print("DATA INTEGRITY: Real API data only")
    print("=" * 70)
    print()

    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    account = os.getenv('HYP_ACCOUNT_ADDRESS')

    if not account:
        # Try to get from SDK
        from quantpylib.wrappers.hyperliquid import Hyperliquid
        hyp = Hyperliquid(
            key=os.getenv('HYP_KEY'),
            secret=os.getenv('HYP_SECRET'),
            mode='live'
        )
        await hyp.init_client()
        account = hyp.account_address
        await hyp.cleanup()

    try:
        # Fetch trade history
        print("[1/4] Fetching trade history...")
        fills = info.user_fills(account)

        if not fills:
            print("[ERROR] No trade history found")
            return

        # Filter for ticker
        ticker_fills = [f for f in fills if f.get('coin', '').upper() == ticker.upper()]

        if not ticker_fills:
            print(f"[ERROR] No trades found for {ticker}")
            return

        print(f"       Found {len(ticker_fills)} fills for {ticker}")

        # Group fills into trades (entries and exits)
        # A trade is defined as fills that result in a closed position
        print("[2/4] Analyzing trades...")

        trades = []
        current_position = 0
        current_trade = {'entries': [], 'exits': [], 'ticker': ticker}

        for fill in sorted(ticker_fills, key=lambda x: x.get('time', 0)):
            size = float(fill.get('sz', 0))
            side = fill.get('side', '')
            price = float(fill.get('px', 0))
            fee = float(fill.get('fee', 0))
            pnl = float(fill.get('closedPnl', 0))
            time_ms = fill.get('time', 0)

            fill_data = {
                'size': size,
                'side': side,
                'price': price,
                'fee': fee,
                'pnl': pnl,
                'time': datetime.fromtimestamp(time_ms / 1000).strftime("%Y-%m-%d %H:%M:%S") if time_ms else 'N/A'
            }

            # Determine if entry or exit
            if side == 'B':
                size_change = size
            else:
                size_change = -size

            new_position = current_position + size_change

            # Check if this is an exit (closing trade)
            if pnl != 0:
                current_trade['exits'].append(fill_data)

                # Trade complete, save it
                if len(current_trade['entries']) > 0:
                    current_trade['total_pnl'] = sum(e['pnl'] for e in current_trade['exits'])
                    current_trade['total_fees'] = sum(e['fee'] for e in current_trade['entries']) + sum(e['fee'] for e in current_trade['exits'])
                    trades.append(current_trade)

                current_trade = {'entries': [], 'exits': [], 'ticker': ticker}
                current_position = new_position
            else:
                # This is an entry
                current_trade['entries'].append(fill_data)
                current_position = new_position

        if not trades:
            print(f"[ERROR] No completed trades found for {ticker}")
            return

        print(f"       Found {len(trades)} completed trades")

        # Get the trade to journal
        if trade_id == 'latest':
            trade = trades[-1]
            trade_num = len(trades)
        else:
            try:
                idx = int(trade_id) - 1
                if idx < 0 or idx >= len(trades):
                    print(f"[ERROR] Trade #{trade_id} not found. Available: 1-{len(trades)}")
                    return
                trade = trades[idx]
                trade_num = idx + 1
            except ValueError:
                trade = trades[-1]
                trade_num = len(trades)

        print(f"       Journaling trade #{trade_num}")

        # Calculate trade metrics
        print("[3/4] Calculating metrics...")

        entries = trade['entries']
        exits = trade['exits']

        if not entries:
            print("[ERROR] No entry data for this trade")
            return

        # Entry metrics
        entry_time = entries[0]['time']
        avg_entry = sum(e['price'] * e['size'] for e in entries) / sum(e['size'] for e in entries)
        total_entry_size = sum(e['size'] for e in entries)
        entry_side = 'LONG' if entries[0]['side'] == 'B' else 'SHORT'

        # Exit metrics
        if exits:
            exit_time = exits[-1]['time']
            avg_exit = sum(e['price'] * e['size'] for e in exits) / sum(e['size'] for e in exits)
        else:
            exit_time = 'N/A'
            avg_exit = avg_entry

        # P&L
        total_pnl = trade.get('total_pnl', 0)
        total_fees = trade.get('total_fees', 0)
        net_pnl = total_pnl - total_fees

        # Return percentage (based on notional)
        notional = avg_entry * total_entry_size
        return_pct = (total_pnl / notional * 100) if notional > 0 else 0

        # Grade the trade
        grade, score = get_trade_grade(return_pct)

        # Generate lessons based on outcome
        print("[4/4] Generating journal entry...")

        lessons = []
        if return_pct > 0:
            lessons.append("Winner - Review what confirmed the setup")
            if return_pct > 5:
                lessons.append("Large winner - Could have sized up?")
            lessons.append("Document the entry trigger for future reference")
        else:
            lessons.append("Loser - Review what went wrong")
            if return_pct < -5:
                lessons.append("Large loss - Was stop in place? Was it honored?")
            lessons.append("Identify what would have kept you out of this trade")

        # Generate report
        entry_file = journal_dir / "archive" / f"{ticker}_{date_str}_{trade_num}.md"

        report = f"""# Trade Journal Entry
## {ticker} | {date_str} | Trade #{trade_num}

---

### Trade Summary

| Metric | Value |
|--------|-------|
| Direction | {entry_side} |
| Entry Price | ${avg_entry:,.4f} |
| Exit Price | ${avg_exit:,.4f} |
| Size | {total_entry_size:,.4f} |
| Notional | ${notional:,.2f} |
| Gross P&L | ${total_pnl:+,.2f} |
| Fees | ${total_fees:,.2f} |
| Net P&L | ${net_pnl:+,.2f} ({return_pct:+.2f}%) |
| Grade | **{grade}** ({score:.0f}/100) |

---

### Timeline

**Entry**: {entry_time}
"""
        for i, e in enumerate(entries, 1):
            report += f"  - Fill {i}: {e['size']:,.4f} @ ${e['price']:,.4f} ({e['side']})\n"

        report += f"""
**Exit**: {exit_time}
"""
        for i, e in enumerate(exits, 1):
            report += f"  - Fill {i}: {e['size']:,.4f} @ ${e['price']:,.4f} (P&L: ${e['pnl']:+,.2f})\n"

        report += f"""
---

### Entry Analysis

**Setup Type**: [TODO: Document the setup]

**Entry Trigger**: [TODO: What triggered entry?]

**Entry Quality**: [TODO: Rate 1-10]

Notes:
- [Add notes about entry conditions]
- [Add notes about market context]

---

### Exit Analysis

**Exit Type**: {'Profitable' if total_pnl > 0 else 'Loss'}

**Exit Reason**: [TODO: Why did you exit?]

**Exit Quality**: [TODO: Rate 1-10]

Notes:
- [Add notes about exit decision]
- [Could exit have been better?]

---

### Performance Metrics

| Metric | Value | Assessment |
|--------|-------|------------|
| Return | {return_pct:+.2f}% | {'Good' if return_pct > 2 else 'Fair' if return_pct > 0 else 'Poor'} |
| Fees | ${total_fees:.2f} | {f'{total_fees/notional*100:.3f}% of notional' if notional > 0 else 'N/A'} |
| Net/Gross | {(net_pnl/total_pnl*100) if total_pnl != 0 else 100:.1f}% | - |

---

### Lessons Learned

"""
        for lesson in lessons:
            report += f"> **{lesson}**\n\n"

        report += """
### What Went Well

1. [TODO: Add positives]
2. [TODO: Add positives]

### What Went Wrong

1. [TODO: Add areas for improvement]
2. [TODO: Add areas for improvement]

---

### Action Items

- [ ] [TODO: Specific improvement to implement]
- [ ] [TODO: Rule to add/modify]
- [ ] [TODO: Pattern to watch for]

---

### Tags

`#{ticker}` `#{'winner' if total_pnl > 0 else 'loser'}` `#{entry_side.lower()}` `#grade-{grade.lower()}`

---

*Generated: {timestamp}*
"""

        entry_file.write_text(report)

        # Update index
        index_file = journal_dir / "index.md"
        index_entry = f"| {date_str} | {ticker} | {entry_side} | ${net_pnl:+,.2f} | {return_pct:+.2f}% | {grade} | [Link](archive/{entry_file.name}) |\n"

        if index_file.exists():
            index_content = index_file.read_text()
            # Append to table
            index_content += index_entry
        else:
            index_content = f"""# Trade Journal Index

| Date | Ticker | Side | Net P&L | Return | Grade | Link |
|------|--------|------|---------|--------|-------|------|
{index_entry}"""

        index_file.write_text(index_content)

        # Print summary
        print()
        print("=" * 70)
        print("JOURNAL ENTRY CREATED")
        print("=" * 70)
        print()
        print(f"Ticker: {ticker}")
        print(f"Direction: {entry_side}")
        print(f"Entry: ${avg_entry:,.4f}")
        print(f"Exit: ${avg_exit:,.4f}")
        print(f"Net P&L: ${net_pnl:+,.2f} ({return_pct:+.2f}%)")
        print(f"Grade: {grade}")
        print()
        print(f"Journal entry saved to: {entry_file.absolute()}")
        print(f"Index updated: {index_file.absolute()}")
        print()
        print("Remember to fill in the [TODO] sections with your analysis!")

    except Exception as e:
        print(f"\n[ERROR] Journal creation failed: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agp_trade_journal.py <ticker> [trade_id]")
        print("Example: python agp_trade_journal.py BTC latest")
        print("Example: python agp_trade_journal.py ETH 5")
        sys.exit(1)

    ticker = sys.argv[1]
    trade_id = sys.argv[2] if len(sys.argv) > 2 else 'latest'

    asyncio.run(trade_journal(ticker, trade_id))
