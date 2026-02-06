#!/usr/bin/env python3
"""
Adaptive Trailing Stop Manager
===============================
Unified trailing stop system with ATR + Volume + Bollinger Bands
for dynamic stop tightening and profit skimming across multiple positions.

Evolves auto_stop_manager.py (15-min ATR stops) and hyp_trailing_stop.py
(single-ticker % trail) into a single multi-position adaptive system.

Usage:
    python scripts/adaptive_trail_manager.py dry-run              # Calculate, print, no orders
    python scripts/adaptive_trail_manager.py live                  # Run once, place orders
    python scripts/adaptive_trail_manager.py watch                 # Continuous 5-min loop
    python scripts/adaptive_trail_manager.py status                # Show current state
    python scripts/adaptive_trail_manager.py watch --interval 3    # Custom interval (minutes)
    python scripts/adaptive_trail_manager.py live --tickers SOL,XRP
    python scripts/adaptive_trail_manager.py dry-run --reset-state # Fresh start
"""

import os
import sys
import json
import math
import time
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv
load_dotenv()

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import eth_account

# Optional: quantpylib for market_order reduce_only
try:
    from quantpylib.wrappers.hyperliquid import Hyperliquid
    HAS_QUANTPYLIB = True
except ImportError:
    HAS_QUANTPYLIB = False

# Optional: Telegram alerts
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from integrations.telegram.alerts import TelegramAlerts, AlertPriority
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-ticker skim configuration
# skim_levels: absolute prices where 33% of remaining position is closed
# For SHORT positions: triggers when price drops BELOW level
# For LONG positions: triggers when price rises ABOVE level
# target: ultimate price target for the remaining runner
# ---------------------------------------------------------------------------
TICKER_CONFIG = {
    'SOL': {'skim_levels': [83.0, 70.0, 60.0], 'target': 55.0},
    'XRP': {'skim_levels': [1.32, 1.16, 1.00], 'target': 1.00},
    'BTC': {'skim_levels': [72000.0, 68000.0], 'target': 67000.0},
    'ADA': {'skim_levels': [0.35, 0.30], 'target': 0.25},
}

STATE_FILE = os.path.join(os.path.dirname(__file__), '..', 'adaptive_trail_state.json')
MAX_RETRIES = 3
RETRY_DELAY = 5


class AdaptiveTrailManager:
    """Adaptive trailing stop manager with profit skimming."""

    def __init__(self, dry_run: bool = False, tickers: Optional[List[str]] = None):
        self.dry_run = dry_run
        self.ticker_filter = [t.upper() for t in tickers] if tickers else None

        # SDK clients
        self.info: Optional[Info] = None
        self.exchange: Optional[Exchange] = None
        self.hyp: Optional[Any] = None  # quantpylib Hyperliquid
        self.alerts: Optional[Any] = None  # TelegramAlerts

        self.address: str = ''
        self.state: Dict[str, Any] = {}  # per-coin state
        self.meta_cache: Optional[Dict] = None

    # ------------------------------------------------------------------
    # Initialization / cleanup
    # ------------------------------------------------------------------

    async def init(self):
        """Initialize SDK clients and load state."""
        self.address = os.getenv('ACCOUNT_ADDRESS', '')
        secret_key = os.getenv('HYP_SECRET', '')

        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

        if not self.dry_run:
            account = eth_account.Account.from_key(secret_key)
            self.exchange = Exchange(account, constants.MAINNET_API_URL)

            if HAS_QUANTPYLIB:
                self.hyp = Hyperliquid(
                    key=os.getenv('HYP_KEY'),
                    secret=secret_key,
                    mode='live'
                )
                await self.hyp.init_client()

        if HAS_TELEGRAM:
            self.alerts = TelegramAlerts()

        self.load_state()

    async def cleanup(self):
        """Clean up async resources."""
        if self.hyp:
            try:
                await self.hyp.cleanup()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def load_state(self):
        """Load state from JSON file."""
        try:
            with open(STATE_FILE, 'r') as f:
                self.state = json.load(f)
            logger.info("Loaded state from %s", STATE_FILE)
        except (FileNotFoundError, json.JSONDecodeError):
            self.state = {}
            logger.info("Starting with fresh state")

    def save_state(self):
        """Save state to JSON file."""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error("Failed to save state: %s", e)

    def init_position_state(self, coin: str, position: Dict) -> Dict:
        """Initialize or update state for a position."""
        existing = self.state.get(coin, {})
        size = position['size']
        entry = position['entry']
        direction = position['direction']

        if existing and existing.get('entry') == entry and existing.get('direction') == direction:
            # Detect external size changes
            if abs(existing.get('current_size', 0) - abs(size)) > 0.001:
                logger.info("%s: External size change detected %.4f -> %.4f",
                            coin, existing['current_size'], abs(size))
                existing['current_size'] = abs(size)
            return existing

        # New position or changed entry -- start fresh
        config = TICKER_CONFIG.get(coin, {})
        skim_levels = config.get('skim_levels', [])

        state = {
            'coin': coin,
            'direction': direction,
            'entry': entry,
            'original_size': abs(size),
            'current_size': abs(size),
            'best_price': None,
            'last_price': None,
            'current_trail_stop': None,
            'trail_active': False,
            'skims_completed': [],
            'skims_pending': list(skim_levels),
            'adjustments': [],
            'last_updated': datetime.now().isoformat(),
        }
        self.state[coin] = state
        return state

    def clean_stale_positions(self, active_coins: List[str]):
        """Remove state for positions that no longer exist."""
        stale = [c for c in list(self.state.keys()) if c not in active_coins]
        for coin in stale:
            logger.info("Position %s no longer open -- cleaning state", coin)
            del self.state[coin]

    # ------------------------------------------------------------------
    # Market data helpers
    # ------------------------------------------------------------------

    def get_positions(self) -> List[Dict]:
        """Get all open positions."""
        user_state = self.info.user_state(self.address)
        positions = []
        for pos in user_state.get('assetPositions', []):
            p = pos['position']
            size = float(p['szi'])
            if size != 0:
                positions.append({
                    'coin': p['coin'],
                    'size': size,
                    'entry': float(p['entryPx']),
                    'unrealized_pnl': float(p['unrealizedPnl']),
                    'direction': 'LONG' if size > 0 else 'SHORT',
                })
        return positions

    def get_current_price(self, coin: str) -> float:
        """Get current mid price."""
        mids = self.info.all_mids()
        return float(mids.get(coin, 0))

    def get_open_orders(self, coin: str) -> List[Dict]:
        """Get open orders for a coin."""
        orders = self.info.open_orders(self.address)
        return [o for o in orders if o['coin'] == coin]

    def get_sz_decimals(self, coin: str) -> int:
        """Get size decimals for a coin from exchange metadata."""
        if self.meta_cache is None:
            self.meta_cache = self.info.meta()
        for asset in self.meta_cache.get('universe', []):
            if asset['name'] == coin:
                return asset['szDecimals']
        return 0

    # ------------------------------------------------------------------
    # Indicator calculations
    # ------------------------------------------------------------------

    def calculate_atr(self, coin: str, period: int = 14, timeframe: str = '15m') -> Optional[float]:
        """Calculate ATR (Average True Range)."""
        end_time = int(time.time() * 1000)
        tf_ms = {'5m': 5*60*1000, '15m': 15*60*1000, '1h': 60*60*1000, '4h': 4*60*60*1000}
        interval_ms = tf_ms.get(timeframe, 15*60*1000)

        start_time = end_time - (period + 10) * interval_ms
        candles = self.info.candles_snapshot(coin, timeframe, start_time, end_time)

        if len(candles) < period + 1:
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

        atr = sum(tr[-period:]) / period
        return atr

    def analyze_volume(self, coin: str, lookback: int = 20, timeframe: str = '15m') -> Dict:
        """Analyze volume trends and detect spikes."""
        end_time = int(time.time() * 1000)
        tf_ms = {'5m': 5*60*1000, '15m': 15*60*1000, '1h': 60*60*1000}
        interval_ms = tf_ms.get(timeframe, 15*60*1000)

        start_time = end_time - (lookback + 5) * interval_ms
        candles = self.info.candles_snapshot(coin, timeframe, start_time, end_time)

        if len(candles) < lookback:
            return {'current': 0, 'average': 0, 'ratio': 1, 'trend': 'NEUTRAL', 'spike': False}

        volumes = [float(c['v']) for c in candles]
        current_vol = volumes[-1]
        avg_vol = sum(volumes[-lookback:-1]) / (lookback - 1) if lookback > 1 else current_vol

        recent_avg = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else current_vol
        prev_avg = sum(volumes[-10:-5]) / 5 if len(volumes) >= 10 else recent_avg

        if recent_avg > prev_avg * 1.2:
            trend = 'INCREASING'
        elif recent_avg < prev_avg * 0.8:
            trend = 'DECREASING'
        else:
            trend = 'NEUTRAL'

        ratio = current_vol / avg_vol if avg_vol > 0 else 1
        spike = ratio >= 2.0

        return {
            'current': current_vol,
            'average': avg_vol,
            'ratio': ratio,
            'trend': trend,
            'spike': spike,
        }

    def calculate_bollinger_bands(self, coin: str, period: int = 20,
                                  std_dev: float = 2.0, timeframe: str = '15m') -> Optional[Dict]:
        """Calculate Bollinger Bands."""
        end_time = int(time.time() * 1000)
        tf_ms = {'5m': 5*60*1000, '15m': 15*60*1000, '1h': 60*60*1000}
        interval_ms = tf_ms.get(timeframe, 15*60*1000)

        start_time = end_time - (period + 5) * interval_ms
        candles = self.info.candles_snapshot(coin, timeframe, start_time, end_time)

        if len(candles) < period:
            return None

        closes = [float(c['c']) for c in candles]
        sma = sum(closes[-period:]) / period
        variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
        std = math.sqrt(variance)

        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        current = closes[-1]

        band_width = upper - lower
        position = (current - lower) / band_width if band_width > 0 else 0.5
        bandwidth_pct = (band_width / sma * 100) if sma > 0 else 0

        return {
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'position': min(max(position, 0), 1),
            'bandwidth_pct': bandwidth_pct,
            'std': std,
        }

    # ------------------------------------------------------------------
    # Core algorithm: calculate_trail_stop
    # ------------------------------------------------------------------

    def calculate_trail_stop(self, coin: str, current_price: float,
                             pos_state: Dict, atr: float,
                             volume: Dict, bb: Optional[Dict]) -> Optional[float]:
        """
        Calculate the adaptive trailing stop level.

        Steps:
        1. Update best price (lowest for SHORT, highest for LONG)
        2. Check trail activation (>= 1% profit from entry)
        3. Base trail = best_price +/- 1.5 * ATR
        4. Favorable move bonus: tighten 0.5 ATR if moved > 0.5 ATR in our favor
        5. Volume spike: tighten additional 0.25 ATR
        6. Bollinger squeeze: widen 0.25 ATR if bandwidth/middle < 3%
        7. BB extreme: tighten 0.25 ATR if price at favorable band extreme
        8. Safety clamp: never worse than entry once trailing
        9. Monotonic constraint: stop can only tighten (except limited BB squeeze)
        10. Deadband handled by caller (only update order if > 0.1% change)
        """
        direction = pos_state['direction']
        entry = pos_state['entry']
        best = pos_state.get('best_price')
        last = pos_state.get('last_price')
        prev_stop = pos_state.get('current_trail_stop')

        # 1. Update best price
        if direction == 'SHORT':
            if best is None or current_price < best:
                best = current_price
        else:  # LONG
            if best is None or current_price > best:
                best = current_price
        pos_state['best_price'] = best

        # 2. Check trail activation (1% profit from entry)
        if direction == 'SHORT':
            pnl_pct = (entry - current_price) / entry * 100
        else:
            pnl_pct = (current_price - entry) / entry * 100

        if pnl_pct < 1.0 and not pos_state.get('trail_active'):
            # Not yet profitable enough to trail -- no stop
            pos_state['last_price'] = current_price
            return prev_stop

        pos_state['trail_active'] = True

        # 3. Base trail
        if direction == 'SHORT':
            stop = best + 1.5 * atr
        else:
            stop = best - 1.5 * atr

        # 4. Favorable move bonus
        if last is not None:
            if direction == 'SHORT':
                move = last - current_price  # positive = favorable
            else:
                move = current_price - last

            if move > 0.5 * atr:
                if direction == 'SHORT':
                    stop -= 0.5 * atr  # tighten = lower for shorts
                else:
                    stop += 0.5 * atr  # tighten = higher for longs

        # 5. Volume spike tightening
        if volume.get('spike'):
            if direction == 'SHORT':
                stop -= 0.25 * atr
            else:
                stop += 0.25 * atr

        # Bollinger Band adjustments
        if bb is not None:
            # 6. BB squeeze -- widen stop (breakout preparation)
            if bb['bandwidth_pct'] < 3.0:
                if direction == 'SHORT':
                    stop += 0.25 * atr  # widen = higher for shorts
                else:
                    stop -= 0.25 * atr  # widen = lower for longs

            # 7. BB extreme in our favor -- tighten (momentum capture)
            if direction == 'SHORT' and bb['position'] < 0.1:
                stop -= 0.25 * atr
            elif direction == 'LONG' and bb['position'] > 0.9:
                stop += 0.25 * atr

        # 8. Safety clamp -- never worse than entry once trailing
        if direction == 'SHORT':
            stop = min(stop, entry)
        else:
            stop = max(stop, entry)

        # 9. Monotonic constraint -- stop can only tighten
        #    Exception: limited BB squeeze widening already applied above
        if prev_stop is not None:
            if direction == 'SHORT':
                # For shorts, tighter = lower stop price
                # Allow limited widening for BB squeeze (max 0.25 ATR)
                max_widen = 0.25 * atr if (bb and bb['bandwidth_pct'] < 3.0) else 0
                stop = min(stop, prev_stop + max_widen)
            else:
                # For longs, tighter = higher stop price
                max_widen = 0.25 * atr if (bb and bb['bandwidth_pct'] < 3.0) else 0
                stop = max(stop, prev_stop - max_widen)

        pos_state['last_price'] = current_price
        return stop

    # ------------------------------------------------------------------
    # Profit skimming
    # ------------------------------------------------------------------

    def check_skim_triggers(self, coin: str, current_price: float,
                            pos_state: Dict) -> List[float]:
        """Check which skim levels have been triggered."""
        direction = pos_state['direction']
        pending = pos_state.get('skims_pending', [])
        triggered = []

        for level in list(pending):
            if direction == 'SHORT' and current_price <= level:
                triggered.append(level)
            elif direction == 'LONG' and current_price >= level:
                triggered.append(level)

        return triggered

    async def execute_skim(self, coin: str, skim_level: float,
                           pos_state: Dict, current_price: float) -> bool:
        """Execute a profit skim: close 33% of remaining position."""
        current_size = pos_state['current_size']
        skim_size = current_size * 0.33
        sz_decimals = self.get_sz_decimals(coin)
        skim_size = round(skim_size, sz_decimals)

        if skim_size <= 0:
            return False

        direction = pos_state['direction']
        print(f"  SKIM: {coin} {direction} -- Closing {skim_size} @ ~${current_price:.4f} "
              f"(level ${skim_level:.4f})")

        if self.dry_run:
            print(f"  [DRY RUN] Would close {skim_size} {coin}")
        else:
            success = await self._execute_market_close(coin, skim_size, direction)
            if not success:
                return False

        # Update state
        new_size = round(current_size - skim_size, sz_decimals)
        pos_state['current_size'] = new_size
        pos_state['skims_pending'].remove(skim_level)
        pos_state['skims_completed'].append({
            'level': skim_level,
            'size': skim_size,
            'price': current_price,
            'time': datetime.now().isoformat(),
        })

        # Send alert
        await self._send_alert(
            f"*SKIM*: {coin} {direction} -- Closed {skim_size} @ ${current_price:.4f}, "
            f"remaining {new_size}",
            AlertPriority.HIGH if HAS_TELEGRAM else None,
        )

        return True

    async def _execute_market_close(self, coin: str, size: float, direction: str) -> bool:
        """Execute market close via quantpylib or raw SDK."""
        if self.hyp and HAS_QUANTPYLIB:
            try:
                close_amount = size if direction == 'SHORT' else -size
                result = await self.hyp.market_order(
                    ticker=coin,
                    amount=close_amount,
                    reduce_only=True,
                    round_size=True,
                )
                if result and result.get('status') == 'ok':
                    logger.info("Skim market close success for %s", coin)
                    return True
                logger.error("Skim market close failed: %s", result)
                return False
            except Exception as e:
                logger.error("Skim market close error: %s", e)
                return False

        # Fallback: use raw SDK limit-as-market
        if self.exchange:
            try:
                is_buy = direction == 'SHORT'
                price = self.get_current_price(coin)
                # Use a wide limit to simulate market
                slippage = 0.005  # 0.5%
                if is_buy:
                    limit_px = price * (1 + slippage)
                else:
                    limit_px = price * (1 - slippage)
                result = self.exchange.order(
                    coin, is_buy, size, limit_px,
                    {'limit': {'tif': 'Ioc'}},
                    reduce_only=True,
                )
                logger.info("Skim IOC close result: %s", result)
                return True
            except Exception as e:
                logger.error("Skim IOC close error: %s", e)
                return False

        logger.error("No execution client available for skim")
        return False

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    def cancel_stop_orders(self, coin: str):
        """Cancel existing stop/TP orders for a coin."""
        if self.dry_run:
            print(f"  [DRY RUN] Would cancel existing {coin} stop orders")
            return

        orders = self.get_open_orders(coin)
        for order in orders:
            try:
                self.exchange.cancel(coin, order['oid'])
                logger.info("Cancelled order %s for %s", order['oid'], coin)
            except Exception as e:
                logger.error("Error cancelling order %s: %s", order.get('oid'), e)

    def place_stop_order(self, coin: str, direction: str, size: float,
                         trigger_price: float) -> Optional[Dict]:
        """Place a trigger stop-loss order."""
        is_buy = direction == 'SHORT'  # buy to close short

        if self.dry_run:
            side = 'BUY' if is_buy else 'SELL'
            print(f"  [DRY RUN] Would place STOP {side} {size} {coin} @ trigger ${trigger_price:.4f}")
            return {'dry_run': True}

        if not self.exchange:
            logger.error("No exchange client -- cannot place stop")
            return None

        for attempt in range(MAX_RETRIES):
            try:
                result = self.exchange.order(
                    coin,
                    is_buy,
                    size,
                    trigger_price,
                    {
                        'trigger': {
                            'triggerPx': trigger_price,
                            'isMarket': True,
                            'tpsl': 'sl',
                        }
                    },
                )
                logger.info("Stop order placed for %s @ %.4f: %s", coin, trigger_price, result)
                return result
            except Exception as e:
                logger.error("Stop order attempt %d failed: %s", attempt + 1, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        # All retries failed
        asyncio.ensure_future(self._send_alert(
            f"*ERROR*: Failed to place stop for {coin} after {MAX_RETRIES} attempts",
            AlertPriority.CRITICAL if HAS_TELEGRAM else None,
        ))
        return None

    # ------------------------------------------------------------------
    # Telegram alerts
    # ------------------------------------------------------------------

    async def _send_alert(self, message: str, priority=None):
        """Send alert via Telegram if available."""
        if self.alerts and HAS_TELEGRAM and priority:
            try:
                await self.alerts.send(message, priority)
            except Exception as e:
                logger.error("Telegram alert error: %s", e)
        # Always log
        logger.info("ALERT: %s", message)

    # ------------------------------------------------------------------
    # Main per-position cycle
    # ------------------------------------------------------------------

    async def manage_position(self, position: Dict):
        """Run full adaptive trail cycle for one position."""
        coin = position['coin']
        direction = position['direction']
        size = position['size']
        entry = position['entry']

        print(f"\n{'='*60}")
        print(f"  {coin} {direction}  |  Size: {abs(size):.4f}  |  Entry: ${entry:.4f}")
        print(f"{'='*60}")

        # Get current price
        current_price = self.get_current_price(coin)
        if current_price <= 0:
            print(f"  ERROR: Could not get price for {coin}")
            return
        print(f"  Current Price: ${current_price:.4f}")

        # Init / load position state
        pos_state = self.init_position_state(coin, position)

        # Calculate indicators
        atr = self.calculate_atr(coin, period=14, timeframe='15m')
        if not atr:
            print(f"  ERROR: Could not calculate ATR for {coin}")
            return
        print(f"  ATR (14, 15m): ${atr:.4f} ({atr/current_price*100:.2f}%)")

        volume = self.analyze_volume(coin, lookback=20, timeframe='15m')
        print(f"  Volume: {volume['ratio']:.2f}x avg | Trend: {volume['trend']} | "
              f"Spike: {'YES' if volume['spike'] else 'no'}")

        bb = self.calculate_bollinger_bands(coin, period=20, timeframe='15m')
        if bb:
            print(f"  BB: [{bb['lower']:.4f} | {bb['middle']:.4f} | {bb['upper']:.4f}] "
                  f"BW: {bb['bandwidth_pct']:.2f}% Pos: {bb['position']:.2f}")

        # P&L
        if direction == 'SHORT':
            pnl_pct = (entry - current_price) / entry * 100
            pnl_usd = (entry - current_price) * abs(size)
        else:
            pnl_pct = (current_price - entry) / entry * 100
            pnl_usd = (current_price - entry) * abs(size)
        print(f"  P&L: {pnl_pct:+.2f}% (${pnl_usd:+,.2f})")

        # -- Check skim triggers --
        triggered_skims = self.check_skim_triggers(coin, current_price, pos_state)
        if triggered_skims:
            print(f"\n  -- Skim levels triggered: {triggered_skims}")
            for level in sorted(triggered_skims, reverse=(direction == 'LONG')):
                await self.execute_skim(coin, level, pos_state, current_price)

        # -- Calculate trail stop --
        new_stop = self.calculate_trail_stop(coin, current_price, pos_state, atr, volume, bb)

        if new_stop is not None:
            old_stop = pos_state.get('current_trail_stop')
            print(f"\n  Trail Active: YES")
            print(f"  Best Price: ${pos_state['best_price']:.4f}")
            if old_stop:
                print(f"  Previous Stop: ${old_stop:.4f}")
            print(f"  New Stop: ${new_stop:.4f}")

            # Deadband: only update on-exchange if > 0.1% change
            should_update = True
            if old_stop is not None:
                change_pct = abs(new_stop - old_stop) / old_stop * 100
                if change_pct < 0.1:
                    print(f"  Stop change {change_pct:.3f}% < 0.1% deadband -- skipping order update")
                    should_update = False

            if should_update:
                pos_state['current_trail_stop'] = new_stop

                # Record adjustment
                pos_state['adjustments'].append({
                    'time': datetime.now().isoformat(),
                    'old_stop': old_stop,
                    'new_stop': new_stop,
                    'price': current_price,
                    'atr': atr,
                    'volume_spike': volume.get('spike', False),
                    'bb_bandwidth': bb['bandwidth_pct'] if bb else None,
                })
                # Keep last 50 adjustments
                if len(pos_state['adjustments']) > 50:
                    pos_state['adjustments'] = pos_state['adjustments'][-50:]

                # Cancel old stops, place new
                self.cancel_stop_orders(coin)
                current_size = pos_state['current_size']
                self.place_stop_order(coin, direction, current_size, new_stop)

                # Alert if stop tightened significantly (> 1 ATR)
                if old_stop is not None:
                    if direction == 'SHORT':
                        tightening = old_stop - new_stop
                    else:
                        tightening = new_stop - old_stop
                    if tightening > atr:
                        await self._send_alert(
                            f"*TRAIL*: {coin} stop moved ${old_stop:.4f} -> ${new_stop:.4f} "
                            f"(price favorable)",
                            AlertPriority.MEDIUM if HAS_TELEGRAM else None,
                        )
        else:
            print(f"\n  Trail Active: NO (waiting for >= 1% profit to activate)")
            print(f"  Current P&L: {pnl_pct:+.2f}%")

        # -- Skim status --
        pending = pos_state.get('skims_pending', [])
        completed = pos_state.get('skims_completed', [])
        if pending or completed:
            print(f"\n  Skim Status:")
            print(f"    Completed: {len(completed)} | Pending: {len(pending)}")
            if pending:
                print(f"    Next levels: {pending}")
            print(f"    Current size: {pos_state['current_size']:.4f}")

        # Save state
        pos_state['last_updated'] = datetime.now().isoformat()
        self.state[coin] = pos_state
        self.save_state()

    # ------------------------------------------------------------------
    # Run modes
    # ------------------------------------------------------------------

    async def run_once(self):
        """Run one full cycle across all positions."""
        print("\n" + "=" * 60)
        print(f"ADAPTIVE TRAIL MANAGER -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        if self.dry_run:
            print("[DRY RUN MODE -- No orders will be placed]")

        positions = self.get_positions()

        # Apply ticker filter
        if self.ticker_filter:
            positions = [p for p in positions if p['coin'] in self.ticker_filter]

        if not positions:
            print("\nNo matching open positions found.")
            return

        print(f"\nFound {len(positions)} position(s)")

        # Clean stale state
        active_coins = [p['coin'] for p in positions]
        stale_coins = [c for c in list(self.state.keys()) if c not in active_coins]
        for coin in stale_coins:
            await self._send_alert(
                f"*CLOSED*: {coin} position no longer open -- removing state",
                AlertPriority.MEDIUM if HAS_TELEGRAM else None,
            )
        self.clean_stale_positions(active_coins)

        for position in positions:
            try:
                await self.manage_position(position)
            except Exception as e:
                logger.error("Error managing %s: %s", position['coin'], e)
                await self._send_alert(
                    f"*ERROR*: Failed to manage {position['coin']}: {e}",
                    AlertPriority.CRITICAL if HAS_TELEGRAM else None,
                )

        print("\n" + "=" * 60)
        print("CYCLE COMPLETE")
        print("=" * 60)

    async def run_watch(self, interval_minutes: int = 5):
        """Continuous monitoring loop."""
        print(f"Starting continuous monitoring (every {interval_minutes} minutes)")
        print("Press Ctrl+C to stop\n")

        while True:
            try:
                await self.run_once()
                print(f"\nNext run in {interval_minutes} minutes...")
                await asyncio.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\nStopping adaptive trail manager...")
                break
            except Exception as e:
                logger.error("Cycle error: %s", e)
                await self._send_alert(
                    f"*ERROR*: Cycle failed: {e}",
                    AlertPriority.CRITICAL if HAS_TELEGRAM else None,
                )
                print(f"Retrying in {interval_minutes} minutes...")
                await asyncio.sleep(interval_minutes * 60)

    def show_status(self):
        """Display current state from file."""
        self.load_state()

        if not self.state:
            print("No state found. Run 'dry-run' or 'live' first.")
            return

        print("\n" + "=" * 60)
        print("ADAPTIVE TRAIL STATE")
        print("=" * 60)

        for coin, s in self.state.items():
            print(f"\n  {coin} {s.get('direction', '?')}")
            print(f"  {'='*40}")
            print(f"    Entry:         ${s.get('entry', 0):.4f}")
            print(f"    Original Size: {s.get('original_size', 0):.4f}")
            print(f"    Current Size:  {s.get('current_size', 0):.4f}")
            print(f"    Best Price:    ${s.get('best_price', 0):.4f}" if s.get('best_price') else
                  "    Best Price:    N/A")
            print(f"    Trail Active:  {'YES' if s.get('trail_active') else 'NO'}")
            stop = s.get('current_trail_stop')
            print(f"    Current Stop:  ${stop:.4f}" if stop else "    Current Stop:  N/A")

            completed = s.get('skims_completed', [])
            pending = s.get('skims_pending', [])
            print(f"    Skims Done:    {len(completed)}")
            if completed:
                for sk in completed:
                    print(f"      - ${sk['level']:.4f}: {sk['size']} @ ${sk.get('price', 0):.4f} "
                          f"({sk.get('time', '')})")
            print(f"    Skims Pending: {pending}")

            adjustments = s.get('adjustments', [])
            if adjustments:
                last = adjustments[-1]
                print(f"    Last Adjust:   ${last.get('old_stop', 0):.4f} -> "
                      f"${last.get('new_stop', 0):.4f} ({last.get('time', '')})")
            print(f"    Last Updated:  {s.get('last_updated', 'N/A')}")


# ======================================================================
# CLI
# ======================================================================

async def async_main():
    parser = argparse.ArgumentParser(
        description='Adaptive Trailing Stop Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  dry-run         Calculate and print, no orders placed
  live            Run once, place/update orders
  watch           Continuous loop (default 5-min interval)
  status          Show current state from file

Examples:
  python scripts/adaptive_trail_manager.py dry-run
  python scripts/adaptive_trail_manager.py live --tickers SOL,XRP
  python scripts/adaptive_trail_manager.py watch --interval 3
  python scripts/adaptive_trail_manager.py dry-run --reset-state
        """,
    )
    parser.add_argument('mode', choices=['dry-run', 'live', 'watch', 'status'],
                        help='Operating mode')
    parser.add_argument('--interval', type=int, default=5,
                        help='Watch interval in minutes (default: 5)')
    parser.add_argument('--tickers', type=str, default=None,
                        help='Comma-separated ticker filter (e.g. SOL,XRP)')
    parser.add_argument('--reset-state', action='store_true',
                        help='Delete state file and start fresh')

    args = parser.parse_args()

    tickers = args.tickers.split(',') if args.tickers else None
    dry_run = args.mode in ('dry-run', 'status')

    if args.reset_state:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print("State file deleted.")

    manager = AdaptiveTrailManager(dry_run=dry_run, tickers=tickers)

    if args.mode == 'status':
        manager.show_status()
        return

    try:
        await manager.init()

        if args.mode == 'dry-run':
            await manager.run_once()
        elif args.mode == 'live':
            await manager.run_once()
        elif args.mode == 'watch':
            await manager.run_watch(interval_minutes=args.interval)
    finally:
        await manager.cleanup()


def main():
    asyncio.run(async_main())


if __name__ == '__main__':
    main()
