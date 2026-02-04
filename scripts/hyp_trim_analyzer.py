#!/usr/bin/env python3
"""
Trim Analyzer - Multi-timeframe analysis for position trimming decisions.

Analyzes positions across 15M, 1H, and 4H timeframes to generate
trim recommendations based on EMA, RSI, MACD, and volume signals.

Usage:
    python scripts/hyp_trim_analyzer.py              # Analyze all positions
    python scripts/hyp_trim_analyzer.py XRP          # Analyze specific ticker
    python scripts/hyp_trim_analyzer.py --json       # Output as JSON
"""

import sys
import json
import time
from datetime import datetime
from hyperliquid.info import Info
from hyperliquid.utils import constants
from dotenv import dotenv_values


class TrimAnalyzer:
    def __init__(self):
        config = dotenv_values('.env')
        self.address = config.get('ACCOUNT_ADDRESS')
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

    def get_positions(self, ticker=None):
        """Get open positions, optionally filtered by ticker"""
        state = self.info.user_state(self.address)
        positions = []

        for pos in state.get('assetPositions', []):
            p = pos['position']
            size = float(p['szi'])
            if size == 0:
                continue

            coin = p['coin']
            if ticker and coin.upper() != ticker.upper():
                continue

            positions.append({
                'coin': coin,
                'size': size,
                'abs_size': abs(size),
                'entry': float(p['entryPx']),
                'direction': 'SHORT' if size < 0 else 'LONG',
                'unrealized_pnl': float(p['unrealizedPnl'])
            })

        return positions

    def get_candles(self, coin, timeframe, count=100):
        """Get candle data for analysis"""
        end_time = int(time.time() * 1000)

        tf_ms = {
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000
        }

        interval_ms = tf_ms.get(timeframe, 60 * 60 * 1000)
        start_time = end_time - (count * interval_ms)

        return self.info.candles_snapshot(coin, timeframe, start_time, end_time)

    def calculate_ema(self, data, period):
        """Calculate EMA"""
        k = 2 / (period + 1)
        ema_vals = [data[0]]
        for i in range(1, len(data)):
            ema_vals.append(data[i] * k + ema_vals[-1] * (1 - k))
        return ema_vals

    def calculate_rsi(self, closes, period=14):
        """Calculate RSI"""
        if len(closes) < period + 1:
            return 50

        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def analyze_timeframe(self, coin, timeframe):
        """Analyze a single timeframe"""
        candles = self.get_candles(coin, timeframe)

        if len(candles) < 50:
            return None

        closes = [float(c['c']) for c in candles]
        highs = [float(c['h']) for c in candles]
        lows = [float(c['l']) for c in candles]
        volumes = [float(c['v']) for c in candles]

        current = closes[-1]

        # EMAs
        ema9 = self.calculate_ema(closes, 9)[-1]
        ema20 = self.calculate_ema(closes, 20)[-1]
        ema50 = self.calculate_ema(closes, 50)[-1]

        # RSI
        rsi = self.calculate_rsi(closes)

        # RSI trend (compare current to 5 periods ago)
        rsi_prev = self.calculate_rsi(closes[:-5]) if len(closes) > 19 else rsi
        rsi_trend = 'RISING' if rsi > rsi_prev + 2 else 'FALLING' if rsi < rsi_prev - 2 else 'FLAT'

        # MACD
        ema12 = self.calculate_ema(closes, 12)
        ema26 = self.calculate_ema(closes, 26)
        macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
        signal_line = self.calculate_ema(macd_line, 9)

        histogram = macd_line[-1] - signal_line[-1]
        prev_histogram = macd_line[-2] - signal_line[-2]

        macd_side = 'BULLISH' if histogram > 0 else 'BEARISH'
        macd_momentum = 'STRENGTHENING' if abs(histogram) > abs(prev_histogram) else 'WEAKENING'

        # Volume
        avg_vol = sum(volumes[-20:-1]) / 19 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        current_vol = volumes[-1]
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1

        # Volume trend
        recent_vol = sum(volumes[-5:]) / 5
        prev_vol = sum(volumes[-10:-5]) / 5 if len(volumes) >= 10 else recent_vol
        vol_trend = 'INCREASING' if recent_vol > prev_vol * 1.1 else 'DECREASING' if recent_vol < prev_vol * 0.9 else 'FLAT'

        # Last candle color (for volume context)
        last_candle_green = closes[-1] > float(candles[-1]['o'])

        # Trend
        if current > ema9 > ema20:
            trend = 'BULLISH'
        elif current < ema9 < ema20:
            trend = 'BEARISH'
        else:
            trend = 'MIXED'

        return {
            'timeframe': timeframe,
            'price': current,
            'ema9': ema9,
            'ema20': ema20,
            'ema50': ema50,
            'rsi': rsi,
            'rsi_trend': rsi_trend,
            'macd_histogram': histogram,
            'macd_side': macd_side,
            'macd_momentum': macd_momentum,
            'vol_ratio': vol_ratio,
            'vol_trend': vol_trend,
            'last_candle_green': last_candle_green,
            'trend': trend
        }

    def score_signals(self, analysis, direction):
        """Score signals for trim decision"""
        score = 0
        breakdown = []

        # Invert logic for LONG positions
        is_short = direction == 'SHORT'

        # Price vs EMA9
        price = analysis['1h']['price']
        ema9 = analysis['1h']['ema9']
        ema20 = analysis['1h']['ema20']

        if is_short:
            if price < ema9:
                score += 2
                breakdown.append(('Price < EMA9', '+2', 'HOLD'))
            elif price > ema9:
                score -= 2
                breakdown.append(('Price > EMA9', '-2', 'TRIM'))
        else:
            if price > ema9:
                score += 2
                breakdown.append(('Price > EMA9', '+2', 'HOLD'))
            elif price < ema9:
                score -= 2
                breakdown.append(('Price < EMA9', '-2', 'TRIM'))

        # Price vs EMA20
        if is_short:
            if price < ema20:
                score += 2
                breakdown.append(('Price < EMA20', '+2', 'HOLD'))
            elif price > ema20:
                score -= 3
                breakdown.append(('Price > EMA20', '-3', 'TRIM'))
        else:
            if price > ema20:
                score += 2
                breakdown.append(('Price > EMA20', '+2', 'HOLD'))
            elif price < ema20:
                score -= 3
                breakdown.append(('Price < EMA20', '-3', 'TRIM'))

        # RSI level (1H)
        rsi = analysis['1h']['rsi']
        if is_short:
            if rsi < 45:
                score += 2
                breakdown.append((f'RSI {rsi:.1f} < 45', '+2', 'HOLD'))
            elif rsi > 55:
                score -= 2
                breakdown.append((f'RSI {rsi:.1f} > 55', '-2', 'TRIM'))
            else:
                breakdown.append((f'RSI {rsi:.1f} neutral', '0', 'NEUTRAL'))
        else:
            if rsi > 55:
                score += 2
                breakdown.append((f'RSI {rsi:.1f} > 55', '+2', 'HOLD'))
            elif rsi < 45:
                score -= 2
                breakdown.append((f'RSI {rsi:.1f} < 45', '-2', 'TRIM'))
            else:
                breakdown.append((f'RSI {rsi:.1f} neutral', '0', 'NEUTRAL'))

        # RSI Trend
        rsi_trend = analysis['1h']['rsi_trend']
        if is_short:
            if rsi_trend == 'FALLING':
                score += 1
                breakdown.append(('RSI falling', '+1', 'HOLD'))
            elif rsi_trend == 'RISING':
                score -= 1
                breakdown.append(('RSI rising', '-1', 'TRIM'))
        else:
            if rsi_trend == 'RISING':
                score += 1
                breakdown.append(('RSI rising', '+1', 'HOLD'))
            elif rsi_trend == 'FALLING':
                score -= 1
                breakdown.append(('RSI falling', '-1', 'TRIM'))

        # MACD Histogram
        histogram = analysis['1h']['macd_histogram']
        if is_short:
            if histogram < 0:
                score += 2
                breakdown.append(('MACD histogram negative', '+2', 'HOLD'))
            elif histogram > 0:
                score -= 2
                breakdown.append(('MACD histogram positive', '-2', 'TRIM'))
        else:
            if histogram > 0:
                score += 2
                breakdown.append(('MACD histogram positive', '+2', 'HOLD'))
            elif histogram < 0:
                score -= 2
                breakdown.append(('MACD histogram negative', '-2', 'TRIM'))

        # MACD Momentum
        momentum = analysis['1h']['macd_momentum']
        macd_side = analysis['1h']['macd_side']
        if is_short:
            if macd_side == 'BEARISH' and momentum == 'STRENGTHENING':
                score += 1
                breakdown.append(('MACD bearish strengthening', '+1', 'HOLD'))
            elif macd_side == 'BULLISH' or momentum == 'WEAKENING':
                score -= 1
                breakdown.append(('MACD weakening/bullish', '-1', 'TRIM'))
        else:
            if macd_side == 'BULLISH' and momentum == 'STRENGTHENING':
                score += 1
                breakdown.append(('MACD bullish strengthening', '+1', 'HOLD'))
            elif macd_side == 'BEARISH' or momentum == 'WEAKENING':
                score -= 1
                breakdown.append(('MACD weakening/bearish', '-1', 'TRIM'))

        # Volume on counter-trend candle
        vol_ratio = analysis['1h']['vol_ratio']
        last_green = analysis['1h']['last_candle_green']

        if is_short:
            if last_green and vol_ratio >= 2.0:
                score -= 2
                breakdown.append((f'Volume spike on green ({vol_ratio:.1f}x)', '-2', 'TRIM'))
            elif not last_green or vol_ratio < 1.0:
                score += 1
                breakdown.append((f'Low/red volume ({vol_ratio:.1f}x)', '+1', 'HOLD'))
        else:
            if not last_green and vol_ratio >= 2.0:
                score -= 2
                breakdown.append((f'Volume spike on red ({vol_ratio:.1f}x)', '-2', 'TRIM'))
            elif last_green or vol_ratio < 1.0:
                score += 1
                breakdown.append((f'Low/green volume ({vol_ratio:.1f}x)', '+1', 'HOLD'))

        # 4H momentum shift check
        if analysis.get('4h'):
            tf4h = analysis['4h']
            if is_short:
                if tf4h['trend'] == 'BULLISH':
                    score -= 2
                    breakdown.append(('4H trend BULLISH', '-2', 'TRIM'))
                elif tf4h['trend'] == 'BEARISH':
                    score += 1
                    breakdown.append(('4H trend BEARISH', '+1', 'HOLD'))
            else:
                if tf4h['trend'] == 'BEARISH':
                    score -= 2
                    breakdown.append(('4H trend BEARISH', '-2', 'TRIM'))
                elif tf4h['trend'] == 'BULLISH':
                    score += 1
                    breakdown.append(('4H trend BULLISH', '+1', 'HOLD'))

        return score, breakdown

    def get_recommendation(self, score):
        """Get trim recommendation based on score"""
        if score >= 6:
            return 'HOLD', 0, 'Strong trend continuation signals'
        elif score >= 1:
            return 'HOLD', 0, 'Trend intact, minor caution'
        elif score >= -4:
            return 'TRIM 25-33%', 0.30, 'Early reversal signals detected'
        elif score >= -7:
            return 'TRIM 50%', 0.50, 'Multiple reversal signals'
        else:
            return 'EXIT 75%+', 0.75, 'Strong reversal signals - protect capital'

    def analyze_position(self, position):
        """Full analysis for a single position"""
        coin = position['coin']
        direction = position['direction']
        entry = position['entry']

        # Get current price
        mids = self.info.all_mids()
        current_price = float(mids.get(coin, 0))

        # Calculate P&L
        if direction == 'SHORT':
            pnl_pct = ((entry - current_price) / entry) * 100
        else:
            pnl_pct = ((current_price - entry) / entry) * 100

        # Analyze each timeframe
        analysis = {}
        for tf in ['15m', '1h', '4h']:
            tf_analysis = self.analyze_timeframe(coin, tf)
            if tf_analysis:
                analysis[tf] = tf_analysis

        if '1h' not in analysis:
            return None

        # Score signals
        score, breakdown = self.score_signals(analysis, direction)

        # Get recommendation
        action, trim_pct, reason = self.get_recommendation(score)

        # Calculate key levels
        key_levels = {
            'ema9_1h': analysis['1h']['ema9'],
            'ema20_1h': analysis['1h']['ema20'],
            'ema9_4h': analysis['4h']['ema9'] if '4h' in analysis else None
        }

        return {
            'coin': coin,
            'direction': direction,
            'size': position['abs_size'],
            'entry': entry,
            'current_price': current_price,
            'pnl_pct': pnl_pct,
            'unrealized_pnl': position['unrealized_pnl'],
            'analysis': analysis,
            'score': score,
            'breakdown': breakdown,
            'recommendation': action,
            'trim_pct': trim_pct,
            'trim_size': int(position['abs_size'] * trim_pct),
            'reason': reason,
            'key_levels': key_levels
        }

    def print_report(self, result):
        """Print formatted report"""
        print()
        print("=" * 70)
        print(f"TRIM ANALYSIS: {result['coin']}")
        print("=" * 70)
        print()
        print(f"Position: {result['direction']} {result['size']:,.0f}")
        print(f"Entry: ${result['entry']:.4f} | Current: ${result['current_price']:.4f}")
        print(f"P&L: {result['pnl_pct']:+.2f}% (${result['unrealized_pnl']:+,.2f})")
        print()

        # Multi-timeframe summary
        print("-" * 70)
        print("MULTI-TIMEFRAME SUMMARY")
        print("-" * 70)
        print(f"{'TF':<6} {'Trend':<10} {'RSI':<12} {'MACD':<20} {'Volume':<15}")
        print("-" * 70)

        for tf in ['15m', '1h', '4h']:
            if tf in result['analysis']:
                a = result['analysis'][tf]
                rsi_str = f"{a['rsi']:.1f} ({a['rsi_trend']})"
                macd_str = f"{a['macd_side']} {a['macd_momentum']}"
                vol_str = f"{a['vol_ratio']:.2f}x ({a['vol_trend']})"
                print(f"{tf.upper():<6} {a['trend']:<10} {rsi_str:<12} {macd_str:<20} {vol_str:<15}")

        print()

        # Signal breakdown
        print("-" * 70)
        print("SIGNAL BREAKDOWN")
        print("-" * 70)
        for signal, pts, action in result['breakdown']:
            print(f"  {signal:<35} {pts:>5}  [{action}]")

        print("-" * 70)
        print(f"  {'TOTAL SCORE':<35} {result['score']:>+5}")
        print()

        # Recommendation
        print("=" * 70)
        rec = result['recommendation']
        if 'HOLD' in rec:
            print(f"RECOMMENDATION: [{rec}]")
        elif 'TRIM' in rec:
            print(f"RECOMMENDATION: [{rec}] - {result['trim_size']:,} units")
        else:
            print(f"RECOMMENDATION: [{rec}]")

        print(f"Reason: {result['reason']}")
        print()

        # Key levels
        print("KEY LEVELS TO WATCH:")
        kl = result['key_levels']
        direction = result['direction']

        if direction == 'SHORT':
            print(f"  Trim trigger (EMA9 1H):  ${kl['ema9_1h']:.4f}")
            print(f"  Major trigger (EMA20 1H): ${kl['ema20_1h']:.4f}")
            if kl['ema9_4h']:
                print(f"  Exit trigger (EMA9 4H):  ${kl['ema9_4h']:.4f}")
        else:
            print(f"  Trim trigger (EMA9 1H):  ${kl['ema9_1h']:.4f}")
            print(f"  Major trigger (EMA20 1H): ${kl['ema20_1h']:.4f}")
            if kl['ema9_4h']:
                print(f"  Exit trigger (EMA9 4H):  ${kl['ema9_4h']:.4f}")

        print("=" * 70)

    def run(self, ticker=None, output_json=False):
        """Run the analyzer"""
        positions = self.get_positions(ticker)

        if not positions:
            print("No open positions found.")
            return []

        results = []
        for position in positions:
            result = self.analyze_position(position)
            if result:
                results.append(result)
                if not output_json:
                    self.print_report(result)

        if output_json:
            print(json.dumps(results, indent=2, default=str))

        return results


def main():
    ticker = None
    output_json = False

    for arg in sys.argv[1:]:
        if arg == '--json':
            output_json = True
        elif not arg.startswith('-'):
            ticker = arg

    analyzer = TrimAnalyzer()
    analyzer.run(ticker=ticker, output_json=output_json)


if __name__ == '__main__':
    main()
