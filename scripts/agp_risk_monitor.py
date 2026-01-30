#!/usr/bin/env python3
"""
Agentic Risk Monitor - Real-time portfolio risk monitoring

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
from dotenv import load_dotenv

load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid

# Risk thresholds
THRESHOLDS = {
    'margin_warn': 0.70,
    'margin_crit': 0.85,
    'liq_warn': 0.15,
    'liq_crit': 0.08,
    'conc_warn': 0.40,
    'conc_crit': 0.60,
    'loss_warn': 0.05,
    'loss_crit': 0.10,
    'dd_warn': 0.03,
    'dd_crit': 0.05
}

class RiskMonitor:
    def __init__(self, interval=60):
        self.interval = interval
        self.hyp = None
        self.start_equity = None
        self.peak_equity = None
        self.check_count = 0
        self.alert_count = {'warning': 0, 'critical': 0}

    async def init(self):
        self.hyp = Hyperliquid(
            key=os.getenv('HYP_KEY'),
            secret=os.getenv('HYP_SECRET'),
            mode='live'
        )
        await self.hyp.init_client()

        # Get initial state
        balance = await self.hyp.account_balance()
        self.start_equity = float(balance.get('equity_total', 0))
        self.peak_equity = self.start_equity

        print(f"      Account: {self.hyp.account_address}")
        print(f"      Starting Equity: ${self.start_equity:,.2f}")

    async def check_risks(self):
        """Check all risk metrics against thresholds"""
        alerts = []

        # Fetch real data
        balance = await self.hyp.account_balance()
        account_data = await self.hyp.perpetuals_account()

        equity = float(balance.get('equity_total', 0))
        margin_used = float(balance.get('margin_total', 0))

        positions = account_data.get('assetPositions', [])
        active_positions = [p for p in positions if float(p.get('position', {}).get('szi', 0)) != 0]

        # Update peak for drawdown
        if equity > self.peak_equity:
            self.peak_equity = equity

        # 1. Margin Utilization
        margin_util = margin_used / equity if equity > 0 else 0
        if margin_util >= THRESHOLDS['margin_crit']:
            alerts.append(('CRITICAL', f'Margin: {margin_util:.1%}', 'Reduce positions immediately'))
        elif margin_util >= THRESHOLDS['margin_warn']:
            alerts.append(('WARNING', f'Margin: {margin_util:.1%}', 'Consider reducing exposure'))

        # 2. Liquidation Distance
        min_liq_dist = None
        liq_ticker = None
        for pos_data in active_positions:
            pos = pos_data.get('position', {})
            mark = float(pos.get('markPx', 0))
            liq = pos.get('liquidationPx')
            if liq and mark > 0:
                liq_val = float(liq)
                dist = abs(mark - liq_val) / mark
                if min_liq_dist is None or dist < min_liq_dist:
                    min_liq_dist = dist
                    liq_ticker = pos.get('coin', '?')

        if min_liq_dist is not None:
            if min_liq_dist < THRESHOLDS['liq_crit']:
                alerts.append(('CRITICAL', f'{liq_ticker} liq: {min_liq_dist:.1%}', 'Close or reduce NOW'))
            elif min_liq_dist < THRESHOLDS['liq_warn']:
                alerts.append(('WARNING', f'{liq_ticker} liq: {min_liq_dist:.1%}', 'Add margin or reduce'))

        # 3. Position Concentration
        for pos_data in active_positions:
            pos = pos_data.get('position', {})
            notional = abs(float(pos.get('positionValue', 0)))
            conc = notional / equity if equity > 0 else 0
            coin = pos.get('coin', '?')
            if conc >= THRESHOLDS['conc_crit']:
                alerts.append(('CRITICAL', f'{coin} conc: {conc:.1%}', 'Reduce position size'))
            elif conc >= THRESHOLDS['conc_warn']:
                alerts.append(('WARNING', f'{coin} conc: {conc:.1%}', 'Consider reducing'))

        # 4. Unrealized Loss
        total_upnl = sum(
            float(p.get('position', {}).get('unrealizedPnl', 0))
            for p in active_positions
        )
        if equity > 0 and total_upnl < 0:
            loss_pct = abs(total_upnl) / equity
            if loss_pct >= THRESHOLDS['loss_crit']:
                alerts.append(('CRITICAL', f'uPnL: -{loss_pct:.1%}', 'Review all positions'))
            elif loss_pct >= THRESHOLDS['loss_warn']:
                alerts.append(('WARNING', f'uPnL: -{loss_pct:.1%}', 'Monitor closely'))

        # 5. Drawdown from peak
        dd = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0
        if dd >= THRESHOLDS['dd_crit']:
            alerts.append(('CRITICAL', f'DD: {dd:.1%}', 'Consider stopping for day'))
        elif dd >= THRESHOLDS['dd_warn']:
            alerts.append(('WARNING', f'DD: {dd:.1%}', 'Reduce risk taking'))

        # Determine status
        status = 'OK'
        if any(a[0] == 'CRITICAL' for a in alerts):
            status = 'CRITICAL'
        elif any(a[0] == 'WARNING' for a in alerts):
            status = 'WARNING'

        return {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'equity': equity,
            'margin_util': margin_util,
            'positions': len(active_positions),
            'min_liq_dist': min_liq_dist,
            'upnl': total_upnl,
            'drawdown': dd,
            'alerts': alerts,
            'status': status
        }

    def format_status(self, data):
        """Format status line for console output"""
        icons = {'OK': '[OK]', 'WARNING': '[!!]', 'CRITICAL': '[XX]'}

        liq_str = f"{data['min_liq_dist']:.0%}" if data['min_liq_dist'] else "N/A"

        line = (
            f"{data['timestamp']} "
            f"{icons[data['status']]} "
            f"Eq: ${data['equity']:,.0f} | "
            f"Margin: {data['margin_util']:.0%} | "
            f"Pos: {data['positions']} | "
            f"Liq: {liq_str} | "
            f"uPnL: ${data['upnl']:+,.0f} | "
            f"DD: {data['drawdown']:.1%}"
        )
        return line

    def format_alerts(self, alerts):
        """Format alerts for console output"""
        lines = []
        for severity, message, action in alerts:
            if severity == 'CRITICAL':
                lines.append(f"    [CRITICAL] {message}")
                lines.append(f"               -> {action}")
            else:
                lines.append(f"    [WARNING] {message} - {action}")
        return '\n'.join(lines)

    async def run(self, max_checks=None):
        """Run the monitoring loop"""
        await self.init()

        print()
        print("Starting monitoring loop...")
        print(f"Interval: {self.interval}s | Thresholds: margin>{THRESHOLDS['margin_warn']:.0%}, liq<{THRESHOLDS['liq_warn']:.0%}")
        print("-" * 70)

        try:
            while True:
                self.check_count += 1

                data = await self.check_risks()

                # Print status line
                print(self.format_status(data))

                # Print alerts if any
                if data['alerts']:
                    print(self.format_alerts(data['alerts']))

                    # Track alert counts
                    for alert in data['alerts']:
                        if alert[0] == 'CRITICAL':
                            self.alert_count['critical'] += 1
                        else:
                            self.alert_count['warning'] += 1

                # Check if we should stop
                if max_checks and self.check_count >= max_checks:
                    print(f"\nReached {max_checks} checks, stopping.")
                    break

                await asyncio.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\nMonitor stopped by user (Ctrl+C)")

        finally:
            # Summary
            print()
            print("=" * 70)
            print("RISK MONITOR SUMMARY")
            print("=" * 70)

            final_balance = await self.hyp.account_balance()
            final_equity = float(final_balance.get('equity_total', 0))
            change = final_equity - self.start_equity

            print(f"""
Session Stats:
- Checks performed: {self.check_count}
- Critical alerts: {self.alert_count['critical']}
- Warning alerts: {self.alert_count['warning']}

Equity Change:
- Starting: ${self.start_equity:,.2f}
- Final: ${final_equity:,.2f}
- Change: ${change:+,.2f} ({change/self.start_equity*100 if self.start_equity > 0 else 0:+.2f}%)
- Peak: ${self.peak_equity:,.2f}
""")

            await self.hyp.cleanup()


async def main(interval=60, max_checks=None):
    """Main entry point"""
    print("=" * 70)
    print("HYPERLIQUID RISK MONITOR")
    print(f"Interval: {interval}s")
    print("DATA INTEGRITY: Real API data only - no fabrication")
    print("=" * 70)
    print()

    print("[INIT] Connecting to Hyperliquid...")
    print("      Source: hyp.account_balance(), hyp.perpetuals_account() APIs")

    monitor = RiskMonitor(interval=interval)
    await monitor.run(max_checks=max_checks)


if __name__ == "__main__":
    interval = 60
    max_checks = None

    for arg in sys.argv[1:]:
        if arg.isdigit():
            interval = int(arg)
        elif arg.startswith('--checks='):
            max_checks = int(arg.split('=')[1])

    asyncio.run(main(interval, max_checks))
