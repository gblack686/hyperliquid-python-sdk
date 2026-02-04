#!/usr/bin/env python3
"""
Auto Stop Manager - 15-Minute Adaptive Stop Loss System

Analyzes volume trends, ATR, and price action to dynamically adjust
stop loss and take profit orders every 15 minutes.

Usage:
    python scripts/auto_stop_manager.py              # Run once
    python scripts/auto_stop_manager.py --watch      # Run continuously every 15 min
    python scripts/auto_stop_manager.py --dry-run    # Analyze without placing orders
"""

import sys
import time
import argparse
from datetime import datetime
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from dotenv import dotenv_values
import eth_account


class AutoStopManager:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        config = dotenv_values('.env')
        self.address = config.get('ACCOUNT_ADDRESS')
        secret_key = config.get('HYP_SECRET')

        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

        if not dry_run:
            account = eth_account.Account.from_key(secret_key)
            self.exchange = Exchange(account, constants.MAINNET_API_URL)
        else:
            self.exchange = None

        # Configuration
        self.config = {
            'atr_multiplier_stop': 1.5,      # Stop loss = ATR * this
            'atr_multiplier_tp1': 2.0,       # TP1 = ATR * this
            'atr_multiplier_tp2': 3.0,       # TP2 = ATR * this
            'trail_activation_pct': 1.5,     # Start trailing after X% profit
            'trail_distance_atr': 1.0,       # Trail distance in ATR
            'volume_spike_threshold': 2.0,   # Volume spike = X * average
            'tighten_on_volume_spike': 0.5,  # Tighten stop by this ATR on volume spike
            'min_rr_ratio': 1.5,             # Minimum risk/reward for new stops
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
                    'entry': float(p['entryPx']),
                    'unrealized_pnl': float(p['unrealizedPnl']),
                    'direction': 'LONG' if size > 0 else 'SHORT'
                })

        return positions

    def get_open_orders(self, coin):
        """Get open orders for a coin"""
        orders = self.info.open_orders(self.address)
        return [o for o in orders if o['coin'] == coin]

    def calculate_atr(self, coin, period=14, timeframe='15m'):
        """Calculate ATR for a coin"""
        end_time = int(time.time() * 1000)

        # Map timeframe to milliseconds
        tf_ms = {'15m': 15*60*1000, '1h': 60*60*1000, '4h': 4*60*60*1000}
        interval_ms = tf_ms.get(timeframe, 15*60*1000)

        start_time = end_time - (period + 10) * interval_ms
        candles = self.info.candles_snapshot(coin, timeframe, start_time, end_time)

        if len(candles) < period + 1:
            return None

        highs = [float(c['h']) for c in candles]
        lows = [float(c['l']) for c in candles]
        closes = [float(c['c']) for c in candles]

        # Calculate True Range
        tr = []
        for i in range(1, len(candles)):
            tr.append(max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            ))

        # Calculate ATR (SMA of TR)
        atr = sum(tr[-period:]) / period
        return atr

    def analyze_volume(self, coin, lookback=20, timeframe='15m'):
        """Analyze volume trends"""
        end_time = int(time.time() * 1000)
        tf_ms = {'15m': 15*60*1000, '1h': 60*60*1000}
        interval_ms = tf_ms.get(timeframe, 15*60*1000)

        start_time = end_time - (lookback + 5) * interval_ms
        candles = self.info.candles_snapshot(coin, timeframe, start_time, end_time)

        if len(candles) < lookback:
            return {'current': 0, 'average': 0, 'ratio': 1, 'trend': 'NEUTRAL', 'spike': False}

        volumes = [float(c['v']) for c in candles]

        current_vol = volumes[-1]
        avg_vol = sum(volumes[-lookback:-1]) / (lookback - 1)

        # Volume trend (compare recent 5 vs previous 5)
        recent_avg = sum(volumes[-5:]) / 5
        prev_avg = sum(volumes[-10:-5]) / 5

        if recent_avg > prev_avg * 1.2:
            trend = 'INCREASING'
        elif recent_avg < prev_avg * 0.8:
            trend = 'DECREASING'
        else:
            trend = 'NEUTRAL'

        ratio = current_vol / avg_vol if avg_vol > 0 else 1
        spike = ratio >= self.config['volume_spike_threshold']

        return {
            'current': current_vol,
            'average': avg_vol,
            'ratio': ratio,
            'trend': trend,
            'spike': spike
        }

    def get_current_price(self, coin):
        """Get current mid price"""
        mids = self.info.all_mids()
        return float(mids.get(coin, 0))

    def calculate_optimal_stops(self, position, atr, volume_analysis, current_price):
        """Calculate optimal stop loss and take profit levels"""
        entry = position['entry']
        direction = position['direction']

        # Base stop distance
        stop_distance = atr * self.config['atr_multiplier_stop']

        # Tighten stop on volume spike (potential reversal)
        if volume_analysis['spike']:
            stop_distance -= atr * self.config['tighten_on_volume_spike']

        # Calculate current P&L %
        if direction == 'LONG':
            pnl_pct = ((current_price - entry) / entry) * 100
        else:
            pnl_pct = ((entry - current_price) / entry) * 100

        # Determine if we should trail
        trailing = pnl_pct >= self.config['trail_activation_pct']

        if direction == 'LONG':
            if trailing:
                # Trail from current price
                stop_loss = current_price - (atr * self.config['trail_distance_atr'])
                # Don't let stop go below entry (lock in breakeven minimum)
                stop_loss = max(stop_loss, entry)
            else:
                # Fixed stop below entry
                stop_loss = entry - stop_distance

            tp1 = entry + (atr * self.config['atr_multiplier_tp1'])
            tp2 = entry + (atr * self.config['atr_multiplier_tp2'])

        else:  # SHORT
            if trailing:
                # Trail from current price
                stop_loss = current_price + (atr * self.config['trail_distance_atr'])
                # Don't let stop go above entry (lock in breakeven minimum)
                stop_loss = min(stop_loss, entry)
            else:
                # Fixed stop above entry
                stop_loss = entry + stop_distance

            tp1 = entry - (atr * self.config['atr_multiplier_tp1'])
            tp2 = entry - (atr * self.config['atr_multiplier_tp2'])

        return {
            'stop_loss': stop_loss,
            'tp1': tp1,
            'tp2': tp2,
            'trailing': trailing,
            'stop_distance': stop_distance,
            'pnl_pct': pnl_pct
        }

    def cancel_existing_orders(self, coin):
        """Cancel all existing orders for a coin"""
        if self.dry_run:
            print(f"  [DRY RUN] Would cancel all {coin} orders")
            return

        orders = self.get_open_orders(coin)
        for order in orders:
            try:
                self.exchange.cancel(coin, order['oid'])
                print(f"  Cancelled order {order['oid']}")
            except Exception as e:
                print(f"  Error cancelling order: {e}")

    def place_stop_order(self, coin, is_buy, size, trigger_price, limit_price=None):
        """Place a stop loss order"""
        if self.dry_run:
            print(f"  [DRY RUN] Would place STOP {'BUY' if is_buy else 'SELL'} {abs(size)} {coin} @ trigger {trigger_price:.4f}")
            return None

        # Use trigger order for stop loss
        try:
            result = self.exchange.order(
                coin,
                is_buy,
                abs(size),
                limit_price or trigger_price,
                {
                    'trigger': {
                        'triggerPx': trigger_price,
                        'isMarket': limit_price is None,
                        'tpsl': 'sl'
                    }
                }
            )
            return result
        except Exception as e:
            print(f"  Error placing stop order: {e}")
            return None

    def place_tp_order(self, coin, is_buy, size, trigger_price):
        """Place a take profit order"""
        if self.dry_run:
            print(f"  [DRY RUN] Would place TP {'BUY' if is_buy else 'SELL'} {abs(size)} {coin} @ {trigger_price:.4f}")
            return None

        try:
            result = self.exchange.order(
                coin,
                is_buy,
                abs(size),
                trigger_price,
                {
                    'trigger': {
                        'triggerPx': trigger_price,
                        'isMarket': True,
                        'tpsl': 'tp'
                    }
                }
            )
            return result
        except Exception as e:
            print(f"  Error placing TP order: {e}")
            return None

    def manage_position(self, position):
        """Analyze and manage stops for a single position"""
        coin = position['coin']
        direction = position['direction']
        size = position['size']
        entry = position['entry']

        print(f"\n{'='*50}")
        print(f"Managing {coin} {direction}")
        print(f"{'='*50}")
        print(f"Size: {size:,.0f} | Entry: ${entry:.4f}")

        # Get current price
        current_price = self.get_current_price(coin)
        print(f"Current Price: ${current_price:.4f}")

        # Calculate ATR
        atr = self.calculate_atr(coin, period=14, timeframe='15m')
        if not atr:
            print("  ERROR: Could not calculate ATR")
            return
        print(f"ATR (14, 15m): ${atr:.4f} ({atr/current_price*100:.2f}%)")

        # Analyze volume
        vol = self.analyze_volume(coin, lookback=20, timeframe='15m')
        print(f"Volume: {vol['ratio']:.2f}x avg | Trend: {vol['trend']} | Spike: {vol['spike']}")

        # Calculate optimal stops
        stops = self.calculate_optimal_stops(position, atr, vol, current_price)

        print(f"\nCurrent P&L: {stops['pnl_pct']:+.2f}%")
        print(f"Trailing Mode: {'YES' if stops['trailing'] else 'NO'}")

        print(f"\nCalculated Levels:")
        print(f"  Stop Loss: ${stops['stop_loss']:.4f}")
        print(f"  TP1 (33%): ${stops['tp1']:.4f}")
        print(f"  TP2 (33%): ${stops['tp2']:.4f}")

        # Get existing orders
        existing_orders = self.get_open_orders(coin)
        print(f"\nExisting orders: {len(existing_orders)}")

        # Cancel existing orders and place new ones
        print("\nUpdating orders...")
        self.cancel_existing_orders(coin)

        # Place stop loss for full position
        is_buy_to_close = direction == 'SHORT'

        print(f"\nPlacing new orders:")

        # Stop loss
        sl_result = self.place_stop_order(
            coin,
            is_buy_to_close,
            abs(size),
            stops['stop_loss']
        )
        if sl_result:
            print(f"  Stop Loss placed @ ${stops['stop_loss']:.4f}")

        # Take profit 1 (33% of position)
        tp1_size = abs(size) * 0.33
        # Round to integer for XRP
        meta = self.info.meta()
        sz_decimals = 0
        for asset in meta['universe']:
            if asset['name'] == coin:
                sz_decimals = asset['szDecimals']
                break
        tp1_size = round(tp1_size, sz_decimals)

        if tp1_size > 0:
            tp1_result = self.place_tp_order(
                coin,
                is_buy_to_close,
                tp1_size,
                stops['tp1']
            )
            if tp1_result:
                print(f"  TP1 placed: {tp1_size} @ ${stops['tp1']:.4f}")

        # Take profit 2 (33% of position)
        tp2_size = round(abs(size) * 0.33, sz_decimals)
        if tp2_size > 0:
            tp2_result = self.place_tp_order(
                coin,
                is_buy_to_close,
                tp2_size,
                stops['tp2']
            )
            if tp2_result:
                print(f"  TP2 placed: {tp2_size} @ ${stops['tp2']:.4f}")

        # Summary
        if direction == 'SHORT':
            risk = (stops['stop_loss'] - current_price) / current_price * 100
            reward1 = (current_price - stops['tp1']) / current_price * 100
        else:
            risk = (current_price - stops['stop_loss']) / current_price * 100
            reward1 = (stops['tp1'] - current_price) / current_price * 100

        print(f"\nRisk/Reward Summary:")
        print(f"  Risk to Stop: {risk:.2f}%")
        print(f"  Reward to TP1: {reward1:.2f}%")
        print(f"  R:R Ratio: {abs(reward1/risk):.2f}" if risk != 0 else "  R:R Ratio: N/A")

        return {
            'coin': coin,
            'direction': direction,
            'stop_loss': stops['stop_loss'],
            'tp1': stops['tp1'],
            'tp2': stops['tp2'],
            'trailing': stops['trailing'],
            'volume_spike': vol['spike'],
            'pnl_pct': stops['pnl_pct']
        }

    def run(self):
        """Run the stop manager for all positions"""
        print("\n" + "="*60)
        print(f"AUTO STOP MANAGER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        if self.dry_run:
            print("[DRY RUN MODE - No orders will be placed]")

        positions = self.get_positions()

        if not positions:
            print("\nNo open positions found.")
            return []

        print(f"\nFound {len(positions)} open position(s)")

        results = []
        for position in positions:
            result = self.manage_position(position)
            if result:
                results.append(result)

        print("\n" + "="*60)
        print("STOP MANAGER COMPLETE")
        print("="*60)

        return results


def main():
    parser = argparse.ArgumentParser(description='Auto Stop Manager')
    parser.add_argument('--watch', action='store_true', help='Run continuously every 15 minutes')
    parser.add_argument('--dry-run', action='store_true', help='Analyze without placing orders')
    parser.add_argument('--interval', type=int, default=15, help='Interval in minutes (default: 15)')

    args = parser.parse_args()

    manager = AutoStopManager(dry_run=args.dry_run)

    if args.watch:
        print(f"Starting continuous monitoring (every {args.interval} minutes)")
        print("Press Ctrl+C to stop\n")

        while True:
            try:
                manager.run()
                print(f"\nNext run in {args.interval} minutes...")
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                print("\nStopping auto stop manager...")
                break
            except Exception as e:
                print(f"\nError: {e}")
                print(f"Retrying in {args.interval} minutes...")
                time.sleep(args.interval * 60)
    else:
        manager.run()


if __name__ == '__main__':
    main()
