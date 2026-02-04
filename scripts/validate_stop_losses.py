#!/usr/bin/env python3
"""
Stop Loss & Take Profit Validation Script

Validates that all open positions have:
- Stop loss orders covering 100% of position size (across up to 5 levels)
- Take profit orders covering 100% of position size (across up to 5 levels)

Reports violations and can auto-fix by placing missing orders.

Usage:
    python scripts/validate_stop_losses.py              # Validate only
    python scripts/validate_stop_losses.py --fix        # Show suggestions (dry run)
    python scripts/validate_stop_losses.py --auto-fix   # Automatically place missing orders
"""

import sys
import argparse
from datetime import datetime
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from dotenv import dotenv_values
import eth_account
import time


class StopLossValidator:
    def __init__(self):
        config = dotenv_values('.env')
        self.address = config.get('ACCOUNT_ADDRESS')
        secret_key = config.get('HYP_SECRET')

        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        account = eth_account.Account.from_key(secret_key)
        self.exchange = Exchange(account, constants.MAINNET_API_URL)

        # Configuration - 5 levels each for SL and TP
        self.config = {
            'num_levels': 5,
            'atr_period': 14,
            'atr_timeframe': '15m',
            # Stop loss: closer levels first (1x, 1.5x, 2x, 2.5x, 3x ATR from entry)
            'stop_atr_multipliers': [1.0, 1.5, 2.0, 2.5, 3.0],
            # Take profit: closer levels first
            'tp_atr_multipliers': [1.0, 1.5, 2.0, 2.5, 3.0],
            # Equal distribution across all levels
            'size_distribution': [0.20, 0.20, 0.20, 0.20, 0.20],
        }

    def get_positions(self):
        """Get all open positions"""
        state = self.info.user_state(self.address)
        positions = []

        for pos in state.get('assetPositions', []):
            p = pos['position']
            size = float(p['szi'])
            if size != 0:
                positions.append({
                    'coin': p['coin'],
                    'size': size,
                    'abs_size': abs(size),
                    'entry': float(p['entryPx']),
                    'direction': 'SHORT' if size < 0 else 'LONG',
                    'unrealized_pnl': float(p['unrealizedPnl']),
                    'liq_px': p.get('liquidationPx')
                })

        return positions

    def get_open_orders(self, coin=None):
        """Get open orders, optionally filtered by coin"""
        orders = self.info.open_orders(self.address)
        if coin:
            orders = [o for o in orders if o['coin'] == coin]
        return orders

    def classify_orders(self, orders, position):
        """Classify orders as stop loss or take profit based on position direction"""
        stop_losses = []
        take_profits = []
        other_orders = []

        direction = position['direction']
        entry = position['entry']

        for order in orders:
            order_side = 'BUY' if order['side'] == 'B' else 'SELL'
            trigger_px = float(order.get('triggerPx', 0))
            limit_px = float(order.get('limitPx', 0))
            size = float(order['sz'])
            oid = order.get('oid', 'unknown')

            # Determine if this is a closing order
            is_closing_order = (direction == 'SHORT' and order_side == 'BUY') or \
                              (direction == 'LONG' and order_side == 'SELL')

            if not is_closing_order:
                other_orders.append(order)
                continue

            price = trigger_px if trigger_px > 0 else limit_px

            if direction == 'SHORT':
                # For short: SL is above entry (buy to close at loss), TP is below entry
                if price > entry:
                    stop_losses.append({'price': price, 'size': size, 'oid': oid, 'order': order})
                else:
                    take_profits.append({'price': price, 'size': size, 'oid': oid, 'order': order})
            else:  # LONG
                # For long: SL is below entry (sell to close at loss), TP is above entry
                if price < entry:
                    stop_losses.append({'price': price, 'size': size, 'oid': oid, 'order': order})
                else:
                    take_profits.append({'price': price, 'size': size, 'oid': oid, 'order': order})

        return stop_losses, take_profits, other_orders

    def calculate_atr(self, coin):
        """Calculate ATR for a coin"""
        end_time = int(time.time() * 1000)
        tf_ms = {'15m': 15*60*1000, '1h': 60*60*1000}
        interval_ms = tf_ms.get(self.config['atr_timeframe'], 15*60*1000)

        start_time = end_time - (self.config['atr_period'] + 10) * interval_ms
        candles = self.info.candles_snapshot(coin, self.config['atr_timeframe'], start_time, end_time)

        if len(candles) < self.config['atr_period'] + 1:
            return None

        highs = [float(c['h']) for c in candles]
        lows = [float(c['l']) for c in candles]
        closes = [float(c['c']) for c in candles]

        tr = []
        for i in range(1, len(candles)):
            tr.append(max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            ))

        atr = sum(tr[-self.config['atr_period']:]) / self.config['atr_period']
        return atr

    def get_sz_decimals(self, coin):
        """Get size decimals for a coin"""
        meta = self.info.meta()
        for asset in meta['universe']:
            if asset['name'] == coin:
                return asset['szDecimals']
        return 0

    def validate_position(self, position):
        """Validate a single position for stop loss and take profit coverage"""
        coin = position['coin']
        abs_size = position['abs_size']
        direction = position['direction']
        entry = position['entry']

        orders = self.get_open_orders(coin)
        stop_losses, take_profits, other_orders = self.classify_orders(orders, position)

        # Calculate coverage
        sl_coverage = sum(sl['size'] for sl in stop_losses)
        tp_coverage = sum(tp['size'] for tp in take_profits)

        sl_pct = (sl_coverage / abs_size * 100) if abs_size > 0 else 0
        tp_pct = (tp_coverage / abs_size * 100) if abs_size > 0 else 0

        violations = []

        if sl_pct < 99.9:  # Allow tiny rounding differences
            violations.append({
                'type': 'STOP_LOSS_INCOMPLETE',
                'coverage': sl_pct,
                'missing': abs_size - sl_coverage,
                'message': f'Stop loss covers {sl_pct:.1f}% ({sl_coverage:,.0f} / {abs_size:,.0f})'
            })

        if tp_pct < 99.9:
            violations.append({
                'type': 'TAKE_PROFIT_INCOMPLETE',
                'coverage': tp_pct,
                'missing': abs_size - tp_coverage,
                'message': f'Take profit covers {tp_pct:.1f}% ({tp_coverage:,.0f} / {abs_size:,.0f})'
            })

        return {
            'coin': coin,
            'direction': direction,
            'size': abs_size,
            'entry': entry,
            'liq_px': position.get('liq_px'),
            'stop_losses': stop_losses,
            'take_profits': take_profits,
            'other_orders': other_orders,
            'sl_coverage': sl_pct,
            'tp_coverage': tp_pct,
            'sl_count': len(stop_losses),
            'tp_count': len(take_profits),
            'violations': violations,
            'is_valid': len(violations) == 0
        }

    def suggest_fixes(self, validation_result):
        """Generate suggested orders to fix violations"""
        suggestions = []
        coin = validation_result['coin']
        direction = validation_result['direction']
        entry = validation_result['entry']
        abs_size = validation_result['size']

        atr = self.calculate_atr(coin)
        if not atr:
            print(f"  [WARN] Could not calculate ATR for {coin}")
            return suggestions

        current_price = float(self.info.all_mids().get(coin, entry))
        sz_decimals = self.get_sz_decimals(coin)

        # Handle stop loss violations
        for v in validation_result['violations']:
            if v['type'] == 'STOP_LOSS_INCOMPLETE':
                missing_size = v['missing']
                existing_prices = {sl['price'] for sl in validation_result['stop_losses']}

                # How many levels do we need?
                num_existing = len(validation_result['stop_losses'])
                num_needed = self.config['num_levels'] - num_existing

                if num_needed <= 0:
                    # Have 5 levels but not enough size - add to one level
                    size_per_level = missing_size
                    multiplier = self.config['stop_atr_multipliers'][0]

                    if direction == 'SHORT':
                        price = entry + (atr * multiplier)
                    else:
                        price = entry - (atr * multiplier)

                    suggestions.append({
                        'type': 'STOP_LOSS',
                        'coin': coin,
                        'direction': direction,
                        'price': round(price, 4),
                        'size': round(missing_size, sz_decimals),
                        'multiplier': multiplier,
                        'is_buy': direction == 'SHORT'
                    })
                else:
                    # Need to add more levels
                    size_per_level = missing_size / num_needed

                    for i, multiplier in enumerate(self.config['stop_atr_multipliers']):
                        if direction == 'SHORT':
                            price = entry + (atr * multiplier)
                        else:
                            price = entry - (atr * multiplier)

                        # Skip if already have order near this price
                        if any(abs(p - price) / price < 0.01 for p in existing_prices):
                            continue

                        suggestions.append({
                            'type': 'STOP_LOSS',
                            'coin': coin,
                            'direction': direction,
                            'price': round(price, 4),
                            'size': round(size_per_level, sz_decimals),
                            'multiplier': multiplier,
                            'is_buy': direction == 'SHORT'
                        })

                        if len([s for s in suggestions if s['type'] == 'STOP_LOSS' and s['coin'] == coin]) >= num_needed:
                            break

            elif v['type'] == 'TAKE_PROFIT_INCOMPLETE':
                missing_size = v['missing']
                existing_prices = {tp['price'] for tp in validation_result['take_profits']}

                num_existing = len(validation_result['take_profits'])
                num_needed = self.config['num_levels'] - num_existing

                if num_needed <= 0:
                    size_per_level = missing_size
                    multiplier = self.config['tp_atr_multipliers'][0]

                    if direction == 'SHORT':
                        price = entry - (atr * multiplier)
                    else:
                        price = entry + (atr * multiplier)

                    suggestions.append({
                        'type': 'TAKE_PROFIT',
                        'coin': coin,
                        'direction': direction,
                        'price': round(price, 4),
                        'size': round(missing_size, sz_decimals),
                        'multiplier': multiplier,
                        'is_buy': direction == 'SHORT'
                    })
                else:
                    size_per_level = missing_size / num_needed

                    for i, multiplier in enumerate(self.config['tp_atr_multipliers']):
                        if direction == 'SHORT':
                            price = entry - (atr * multiplier)
                        else:
                            price = entry + (atr * multiplier)

                        if any(abs(p - price) / price < 0.01 for p in existing_prices):
                            continue

                        suggestions.append({
                            'type': 'TAKE_PROFIT',
                            'coin': coin,
                            'direction': direction,
                            'price': round(price, 4),
                            'size': round(size_per_level, sz_decimals),
                            'multiplier': multiplier,
                            'is_buy': direction == 'SHORT'
                        })

                        if len([s for s in suggestions if s['type'] == 'TAKE_PROFIT' and s['coin'] == coin]) >= num_needed:
                            break

        return suggestions

    def place_suggested_orders(self, suggestions, dry_run=True):
        """Place the suggested orders"""
        results = []

        for suggestion in suggestions:
            coin = suggestion['coin']
            is_buy = suggestion['is_buy']
            size = suggestion['size']
            price = suggestion['price']
            order_type = suggestion['type']

            if size <= 0:
                continue

            if dry_run:
                print(f"  [DRY RUN] {order_type}: {'BUY' if is_buy else 'SELL'} {size:,.0f} {coin} @ ${price:.4f}")
                results.append({'suggestion': suggestion, 'status': 'dry_run'})
                continue

            try:
                tpsl = 'sl' if order_type == 'STOP_LOSS' else 'tp'

                result = self.exchange.order(
                    coin,
                    is_buy,
                    size,
                    price,
                    {
                        'trigger': {
                            'triggerPx': price,
                            'isMarket': True,
                            'tpsl': tpsl
                        }
                    }
                )

                if result.get('status') == 'ok':
                    print(f"  [OK] {order_type}: {'BUY' if is_buy else 'SELL'} {size:,.0f} {coin} @ ${price:.4f}")
                    results.append({'suggestion': suggestion, 'status': 'success', 'result': result})
                else:
                    error_msg = result.get('response', {}).get('data', {}).get('statuses', [{}])[0].get('error', 'Unknown error')
                    print(f"  [FAILED] {order_type} {coin}: {error_msg}")
                    results.append({'suggestion': suggestion, 'status': 'failed', 'result': result})

                time.sleep(0.2)  # Rate limiting

            except Exception as e:
                print(f"  [ERROR] {order_type} {coin}: {e}")
                results.append({'suggestion': suggestion, 'status': 'error', 'error': str(e)})

        return results

    def run(self, fix=False, auto_fix=False):
        """Run the validation"""
        print("=" * 70)
        print("STOP LOSS & TAKE PROFIT VALIDATION")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Standard: 5 Stop Losses + 5 Take Profits = 100% Coverage Each")
        print("=" * 70)
        print()

        positions = self.get_positions()

        if not positions:
            print("No open positions found.")
            return True

        print(f"Found {len(positions)} open position(s)")
        print()

        all_valid = True
        all_suggestions = []
        total_violations = 0

        for position in positions:
            result = self.validate_position(position)
            mids = self.info.all_mids()
            current_price = float(mids.get(result['coin'], 0))

            # Position Header
            print("-" * 70)
            status_icon = "[OK]" if result['is_valid'] else "[!!]"
            print(f"{status_icon} {result['coin']} {result['direction']}")
            print("-" * 70)
            print(f"  Position Size: {result['size']:,.0f}")
            print(f"  Entry: ${result['entry']:.4f} | Current: ${current_price:.4f}")
            if result.get('liq_px'):
                print(f"  Liquidation: ${float(result['liq_px']):.4f}")
            print()

            # Stop Loss Coverage
            sl_status = "[OK]" if result['sl_coverage'] >= 99.9 else "[X]"
            print(f"  {sl_status} STOP LOSS: {result['sl_coverage']:.1f}% covered ({result['sl_count']} orders)")
            if result['stop_losses']:
                for sl in sorted(result['stop_losses'], key=lambda x: x['price'], reverse=(result['direction']=='SHORT')):
                    pct = sl['size'] / result['size'] * 100
                    print(f"       ${sl['price']:.4f}: {sl['size']:,.0f} ({pct:.1f}%)")
            else:
                print(f"       NO STOP LOSSES SET!")
            print()

            # Take Profit Coverage
            tp_status = "[OK]" if result['tp_coverage'] >= 99.9 else "[X]"
            print(f"  {tp_status} TAKE PROFIT: {result['tp_coverage']:.1f}% covered ({result['tp_count']} orders)")
            if result['take_profits']:
                for tp in sorted(result['take_profits'], key=lambda x: x['price'], reverse=(result['direction']=='LONG')):
                    pct = tp['size'] / result['size'] * 100
                    print(f"       ${tp['price']:.4f}: {tp['size']:,.0f} ({pct:.1f}%)")
            else:
                print(f"       NO TAKE PROFITS SET!")
            print()

            # Violations
            if not result['is_valid']:
                all_valid = False
                total_violations += len(result['violations'])

                print("  VIOLATIONS:")
                for v in result['violations']:
                    print(f"    - {v['message']}")

                # Generate suggestions
                suggestions = self.suggest_fixes(result)
                all_suggestions.extend(suggestions)

                if suggestions and (fix or auto_fix):
                    print()
                    print("  SUGGESTED FIXES:")
                    for s in suggestions:
                        action = 'BUY' if s['is_buy'] else 'SELL'
                        print(f"    - {s['type']}: {action} {s['size']:,.0f} @ ${s['price']:.4f} ({s['multiplier']}x ATR)")

            print()

        # Summary
        print("=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print()

        if all_valid:
            print("[PASS] All positions have 100% stop loss and take profit coverage")
            print()
        else:
            print(f"[FAIL] {total_violations} violation(s) found")
            print()
            print(f"Suggested orders to fix:")
            sl_count = len([s for s in all_suggestions if s['type'] == 'STOP_LOSS'])
            tp_count = len([s for s in all_suggestions if s['type'] == 'TAKE_PROFIT'])
            print(f"  - Stop Losses: {sl_count}")
            print(f"  - Take Profits: {tp_count}")
            print()

            if all_suggestions:
                if auto_fix:
                    print("-" * 70)
                    print("PLACING ORDERS")
                    print("-" * 70)
                    print()
                    self.place_suggested_orders(all_suggestions, dry_run=False)
                    print()

                    # Re-validate
                    print("Re-validating...")
                    print()
                    return self.run(fix=False, auto_fix=False)

                elif fix:
                    print("-" * 70)
                    print("SUGGESTED ORDERS (dry run)")
                    print("-" * 70)
                    print()
                    self.place_suggested_orders(all_suggestions, dry_run=True)
                    print()
                    print("Run with --auto-fix to place these orders")
                    print()

        print("=" * 70)
        return all_valid


def main():
    parser = argparse.ArgumentParser(description='Validate Stop Loss & Take Profit Coverage')
    parser.add_argument('--fix', action='store_true', help='Show suggested fixes (dry run)')
    parser.add_argument('--auto-fix', action='store_true', help='Automatically place missing orders')

    args = parser.parse_args()

    validator = StopLossValidator()
    is_valid = validator.run(fix=args.fix, auto_fix=args.auto_fix)

    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
