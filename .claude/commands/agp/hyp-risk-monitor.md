---
model: haiku
description: Continuous risk monitoring with alerts and threshold warnings
argument-hint: "[interval] - check frequency in seconds (default 60)"
allowed-tools: Bash(date:*), Bash(python:*), Task, Write, Read
---

# Risk Monitor

## Purpose

Monitor portfolio risk in real-time and alert on threshold breaches. Runs continuously, checking positions and risk metrics at specified intervals.

## Variables

- **INTERVAL**: $1 or 60 (check frequency in seconds)
- **MAX_RUNTIME**: 28800 (8 hours max runtime)

## Risk Thresholds

| Threshold | Default | Severity |
|-----------|---------|----------|
| Margin Utilization | 70% | WARNING |
| Margin Utilization | 85% | CRITICAL |
| Liquidation Distance | 15% | WARNING |
| Liquidation Distance | 8% | CRITICAL |
| Position Concentration | 40% | WARNING |
| Position Concentration | 60% | CRITICAL |
| Unrealized Loss | 5% of equity | WARNING |
| Unrealized Loss | 10% of equity | CRITICAL |
| Daily Drawdown | 3% | WARNING |
| Daily Drawdown | 5% | CRITICAL |

## Instructions

- Run monitoring loop at INTERVAL frequency
- Check all risk metrics against thresholds
- Output concise status line each check
- Alert loudly on WARNING or CRITICAL breaches
- Suggest specific risk reduction actions
- Exit on critical conditions or user interrupt

## Monitoring Script

```python
import os
import sys
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

# Thresholds
MARGIN_WARN = 0.70
MARGIN_CRIT = 0.85
LIQ_WARN = 0.15
LIQ_CRIT = 0.08
CONC_WARN = 0.40
CONC_CRIT = 0.60
LOSS_WARN = 0.05
LOSS_CRIT = 0.10
DD_WARN = 0.03
DD_CRIT = 0.05

class RiskMonitor:
    def __init__(self, interval=60):
        self.interval = interval
        self.hyp = None
        self.start_equity = None
        self.peak_equity = None
        self.alerts = []

    async def init(self):
        self.hyp = Hyperliquid(
            key=os.getenv('HYP_KEY'),
            secret=os.getenv('HYP_SECRET'),
            mode='live'
        )
        await self.hyp.init_client()

        # Get initial state
        bal = await self.hyp.account_balance()
        self.start_equity = float(bal['equity_total'])
        self.peak_equity = self.start_equity

    async def check_risks(self):
        alerts = []

        # Get account data
        account = await self.hyp.perpetuals_account()
        margin_summary = account.get('marginSummary', {})
        positions = account.get('assetPositions', [])

        equity = float(margin_summary.get('accountValue', 0))
        margin_used = float(margin_summary.get('totalMarginUsed', 0))

        # Update peak
        if equity > self.peak_equity:
            self.peak_equity = equity

        # 1. Margin Utilization
        margin_util = margin_used / equity if equity > 0 else 0
        if margin_util >= MARGIN_CRIT:
            alerts.append(('CRITICAL', f'Margin: {margin_util:.1%}', 'Reduce positions immediately'))
        elif margin_util >= MARGIN_WARN:
            alerts.append(('WARNING', f'Margin: {margin_util:.1%}', 'Consider reducing exposure'))

        # 2. Liquidation Distance
        min_liq_dist = 1.0
        liq_position = None
        for pos_data in positions:
            pos = pos_data.get('position', {})
            size = float(pos.get('szi', 0))
            if size == 0:
                continue
            mark = float(pos.get('markPx', 0))
            liq = float(pos.get('liquidationPx', 0)) if pos.get('liquidationPx') else 0
            if liq > 0 and mark > 0:
                dist = abs(mark - liq) / mark
                if dist < min_liq_dist:
                    min_liq_dist = dist
                    liq_position = pos.get('coin')

        if min_liq_dist < LIQ_CRIT:
            alerts.append(('CRITICAL', f'{liq_position} liq dist: {min_liq_dist:.1%}', 'Close or reduce position NOW'))
        elif min_liq_dist < LIQ_WARN:
            alerts.append(('WARNING', f'{liq_position} liq dist: {min_liq_dist:.1%}', 'Add margin or reduce size'))

        # 3. Position Concentration
        total_notional = sum(
            abs(float(p.get('position', {}).get('positionValue', 0)))
            for p in positions
        )
        for pos_data in positions:
            pos = pos_data.get('position', {})
            notional = abs(float(pos.get('positionValue', 0)))
            if total_notional > 0:
                conc = notional / equity
                if conc >= CONC_CRIT:
                    alerts.append(('CRITICAL', f'{pos.get("coin")} concentration: {conc:.1%}', 'Reduce position size'))
                elif conc >= CONC_WARN:
                    alerts.append(('WARNING', f'{pos.get("coin")} concentration: {conc:.1%}', 'Consider reducing'))

        # 4. Unrealized Loss
        total_upnl = sum(
            float(p.get('position', {}).get('unrealizedPnl', 0))
            for p in positions
        )
        if equity > 0:
            loss_pct = -total_upnl / equity if total_upnl < 0 else 0
            if loss_pct >= LOSS_CRIT:
                alerts.append(('CRITICAL', f'Unrealized loss: {loss_pct:.1%}', 'Review all positions'))
            elif loss_pct >= LOSS_WARN:
                alerts.append(('WARNING', f'Unrealized loss: {loss_pct:.1%}', 'Monitor closely'))

        # 5. Daily Drawdown
        dd = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0
        if dd >= DD_CRIT:
            alerts.append(('CRITICAL', f'Drawdown: {dd:.1%}', 'Consider stopping for the day'))
        elif dd >= DD_WARN:
            alerts.append(('WARNING', f'Drawdown: {dd:.1%}', 'Reduce risk taking'))

        return {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'equity': equity,
            'margin_util': margin_util,
            'positions': len([p for p in positions if float(p.get('position', {}).get('szi', 0)) != 0]),
            'min_liq_dist': min_liq_dist,
            'upnl': total_upnl,
            'drawdown': dd,
            'alerts': alerts,
            'status': 'CRITICAL' if any(a[0] == 'CRITICAL' for a in alerts) else
                      'WARNING' if any(a[0] == 'WARNING' for a in alerts) else 'OK'
        }

    def format_status(self, data):
        status_icon = {
            'OK': '[OK]',
            'WARNING': '[!!]',
            'CRITICAL': '[XX]'
        }

        line = (
            f"{data['timestamp']} "
            f"{status_icon[data['status']]} "
            f"Equity: ${data['equity']:,.0f} | "
            f"Margin: {data['margin_util']:.0%} | "
            f"Pos: {data['positions']} | "
            f"Liq: {data['min_liq_dist']:.0%} | "
            f"uPnL: ${data['upnl']:+,.0f} | "
            f"DD: {data['drawdown']:.1%}"
        )
        return line

    def format_alerts(self, alerts):
        output = []
        for severity, message, action in alerts:
            if severity == 'CRITICAL':
                output.append(f"  [CRITICAL] {message}")
                output.append(f"             Action: {action}")
            else:
                output.append(f"  [WARNING] {message} - {action}")
        return '\n'.join(output)

    async def run(self, max_runtime=28800):
        await self.init()

        print("=" * 70)
        print("HYPERLIQUID RISK MONITOR")
        print(f"Interval: {self.interval}s | Max Runtime: {max_runtime//3600}h")
        print(f"Starting Equity: ${self.start_equity:,.2f}")
        print("=" * 70)
        print()

        start_time = datetime.now()

        try:
            while (datetime.now() - start_time).seconds < max_runtime:
                data = await self.check_risks()

                # Print status line
                print(self.format_status(data))

                # Print alerts if any
                if data['alerts']:
                    print(self.format_alerts(data['alerts']))
                    print()

                # Exit on critical
                if data['status'] == 'CRITICAL':
                    print("\n[!] CRITICAL ALERT - Review positions immediately")
                    # Don't exit, but flag prominently

                await asyncio.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\nMonitor stopped by user")
        finally:
            await self.hyp.cleanup()
            print("\nMonitor ended")

if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    monitor = RiskMonitor(interval=interval)
    asyncio.run(monitor.run())
```

## Workflow

### Step 1: Initialize Monitor

1. Connect to Hyperliquid via quantpylib
2. Record starting equity for drawdown calculation
3. Set peak equity tracker

### Step 2: Monitoring Loop

Every {INTERVAL} seconds:

1. **Fetch Current State**
   - Account balances and equity
   - All open positions
   - Margin utilization

2. **Check Risk Metrics**
   - Margin utilization vs thresholds
   - Liquidation distance for each position
   - Position concentration
   - Unrealized P&L
   - Drawdown from peak

3. **Generate Status Line**
   ```
   [14:32:15] [OK] Equity: $12,450 | Margin: 45% | Pos: 3 | Liq: 23% | uPnL: +$234 | DD: 1.2%
   ```

4. **Alert on Breaches**
   ```
   [14:32:15] [!!] Equity: $12,450 | Margin: 72% | Pos: 3 | Liq: 12% | uPnL: -$567 | DD: 4.2%
     [WARNING] Margin: 72% - Consider reducing exposure
     [WARNING] BTC liq dist: 12% - Add margin or reduce size
     [WARNING] Drawdown: 4.2% - Reduce risk taking
   ```

5. **Critical Alerts**
   ```
   [14:32:15] [XX] Equity: $11,200 | Margin: 87% | Pos: 3 | Liq: 7% | uPnL: -$1,234 | DD: 6.1%
     [CRITICAL] Margin: 87% - Reduce positions immediately
     [CRITICAL] ETH liq dist: 7% - Close or reduce position NOW
     [CRITICAL] Drawdown: 6.1% - Consider stopping for the day

   [!] CRITICAL ALERT - Review positions immediately
   ```

### Step 3: Exit Conditions

- User interrupt (Ctrl+C)
- Max runtime reached (8 hours default)
- Manual stop

## Alert Actions

| Alert | Suggested Action |
|-------|-----------------|
| High Margin | Close smallest profitable position |
| Near Liquidation | Add margin OR reduce position 50% |
| High Concentration | Scale out 25% of largest position |
| Large Unrealized Loss | Set stop loss if not set |
| Daily Drawdown | Reduce position sizes by 50% |

## Report

When monitor ends, output summary:

```markdown
## Risk Monitor Summary

### Session Info
- Start: {start_time}
- End: {end_time}
- Duration: X hours Y minutes
- Checks: N

### Equity Tracking
- Starting: $X,XXX.XX
- Peak: $X,XXX.XX
- Final: $X,XXX.XX
- Net Change: +/-$X,XXX.XX (X.X%)

### Alert Summary
- Critical Alerts: N
- Warning Alerts: N
- Clean Checks: N (XX%)

### Most Common Alerts
1. [Alert type]: N occurrences
2. [Alert type]: N occurrences
```

## Examples

```bash
# Monitor every 60 seconds (default)
/hyp-risk-monitor

# Monitor every 30 seconds
/hyp-risk-monitor 30

# Monitor every 2 minutes
/hyp-risk-monitor 120
```
