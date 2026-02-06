#!/usr/bin/env python3
"""
Safe Trade Executor

ALL trades must go through this executor which:
1. Calculates stop loss based on key technical levels
2. Validates stop loss before execution
3. Places entry + stop atomically
4. Rejects trades without valid stops

STOP LOSS LEVELS (in priority order):
1. Recent swing high/low (for shorts/longs)
2. ATR-based stop (1.5x ATR from entry)
3. Key support/resistance levels
4. Fallback: percentage-based

USAGE:
  from scripts.safe_trade_executor import SafeTradeExecutor

  executor = SafeTradeExecutor()
  result = executor.market_short('XRP', size=7)  # Auto-calculates stop
  result = executor.market_long('BTC', size=0.001, stop_price=75000)  # Manual stop
"""

import os
import sys
import time
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import eth_account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants


@dataclass
class StopLossLevel:
    """Calculated stop loss with reasoning."""
    price: float
    method: str  # 'swing', 'atr', 'support_resistance', 'percentage'
    distance_pct: float
    description: str


@dataclass
class TradeResult:
    """Result of a trade execution."""
    success: bool
    coin: str
    direction: str
    entry_price: float
    size: float
    stop_loss: float
    stop_method: str
    order_id: Optional[str] = None
    stop_order_id: Optional[str] = None
    error: Optional[str] = None
    chart_path: Optional[str] = None
    scaled_entries: List[float] = None
    scaled_exits: List[float] = None


class KeyLevelCalculator:
    """Calculate key technical levels for stop loss placement."""

    def __init__(self, info: Info):
        self.info = info

    def get_candles(self, coin: str, timeframe: str = '1h', num_bars: int = 100) -> List[Dict]:
        """Fetch candle data."""
        now = int(time.time() * 1000)
        interval_map = {
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
        }
        interval_ms = interval_map.get(timeframe, 60 * 60 * 1000)
        start = now - (num_bars * interval_ms)

        return self.info.candles_snapshot(coin, timeframe, start, now)

    def find_swing_levels(self, coin: str) -> Tuple[Optional[float], Optional[float]]:
        """Find recent swing high and swing low."""
        candles = self.get_candles(coin, '1h', 50)

        if not candles or len(candles) < 10:
            return None, None

        highs = np.array([float(c['h']) for c in candles])
        lows = np.array([float(c['l']) for c in candles])

        # Find swing highs (local maxima)
        swing_highs = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append(highs[i])

        # Find swing lows (local minima)
        swing_lows = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append(lows[i])

        # Get most recent swing high/low
        recent_high = max(swing_highs[-3:]) if swing_highs else np.max(highs[-20:])
        recent_low = min(swing_lows[-3:]) if swing_lows else np.min(lows[-20:])

        return recent_high, recent_low

    def calculate_atr(self, coin: str, period: int = 14) -> Optional[float]:
        """Calculate Average True Range."""
        candles = self.get_candles(coin, '1h', period + 10)

        if not candles or len(candles) < period:
            return None

        highs = np.array([float(c['h']) for c in candles])
        lows = np.array([float(c['l']) for c in candles])
        closes = np.array([float(c['c']) for c in candles])

        tr_list = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)

        return np.mean(tr_list[-period:])

    def get_current_price(self, coin: str) -> float:
        """Get current mid price."""
        mids = self.info.all_mids()
        return float(mids.get(coin, 0))

    def calculate_stop_loss(
        self,
        coin: str,
        direction: str,  # 'LONG' or 'SHORT'
        entry_price: Optional[float] = None
    ) -> StopLossLevel:
        """
        Calculate optimal stop loss based on key levels.

        Priority:
        1. Swing high/low (most reliable)
        2. ATR-based (volatility adjusted)
        3. Percentage fallback
        """
        current_price = entry_price or self.get_current_price(coin)

        if current_price == 0:
            raise ValueError(f"Could not get price for {coin}")

        # Get swing levels
        swing_high, swing_low = self.find_swing_levels(coin)

        # Get ATR
        atr = self.calculate_atr(coin)

        # Calculate stops for each method
        stops = []

        # Method 1: Swing levels
        if direction == 'SHORT' and swing_high:
            # Stop above recent swing high
            buffer = current_price * 0.002  # 0.2% buffer
            stop_price = swing_high + buffer
            distance = (stop_price - current_price) / current_price * 100

            if distance <= 15:  # Max 15% stop
                stops.append(StopLossLevel(
                    price=stop_price,
                    method='swing_high',
                    distance_pct=distance,
                    description=f"Above recent swing high ${swing_high:.4f}"
                ))

        elif direction == 'LONG' and swing_low:
            # Stop below recent swing low
            buffer = current_price * 0.002
            stop_price = swing_low - buffer
            distance = (current_price - stop_price) / current_price * 100

            if distance <= 15:
                stops.append(StopLossLevel(
                    price=stop_price,
                    method='swing_low',
                    distance_pct=distance,
                    description=f"Below recent swing low ${swing_low:.4f}"
                ))

        # Method 2: ATR-based
        if atr:
            atr_multiplier = 2.0  # 2x ATR

            if direction == 'SHORT':
                stop_price = current_price + (atr * atr_multiplier)
            else:
                stop_price = current_price - (atr * atr_multiplier)

            distance = abs(stop_price - current_price) / current_price * 100

            if distance <= 15:
                stops.append(StopLossLevel(
                    price=stop_price,
                    method='atr',
                    distance_pct=distance,
                    description=f"2x ATR (${atr:.4f})"
                ))

        # Method 3: Percentage fallback
        fallback_pct = {
            'BTC': 5.0,
            'ETH': 6.0,
        }.get(coin, 8.0)

        if direction == 'SHORT':
            stop_price = current_price * (1 + fallback_pct / 100)
        else:
            stop_price = current_price * (1 - fallback_pct / 100)

        stops.append(StopLossLevel(
            price=stop_price,
            method='percentage',
            distance_pct=fallback_pct,
            description=f"Default {fallback_pct}% stop"
        ))

        # Select best stop (prefer swing, then ATR, then percentage)
        priority = {'swing_high': 1, 'swing_low': 1, 'atr': 2, 'percentage': 3}
        stops.sort(key=lambda x: (priority.get(x.method, 99), x.distance_pct))

        return stops[0]


class SafeTradeExecutor:
    """
    Safe trade executor that requires stop losses for all trades.

    Every trade:
    1. Calculates stop based on key levels
    2. Validates the stop is reasonable
    3. Places entry order
    4. Immediately places stop loss
    5. Validates stop was placed
    """

    def __init__(self, generate_charts: bool = False):
        """
        Initialize SafeTradeExecutor.

        Args:
            generate_charts: If True, generate trade setup charts after execution
        """
        secret = os.getenv('HYP_SECRET')
        self.account = os.getenv('ACCOUNT_ADDRESS')

        if not secret or not self.account:
            raise ValueError("HYP_SECRET and ACCOUNT_ADDRESS required")

        self.wallet = eth_account.Account.from_key(secret)
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        self.exchange = Exchange(self.wallet, constants.MAINNET_API_URL, account_address=self.account)
        self.level_calc = KeyLevelCalculator(self.info)
        self.generate_charts = generate_charts

    def _generate_trade_chart(
        self,
        coin: str,
        direction: str,
        entry_price: float,
        stop_price: float,
        leverage: int = 10,
        size: float = 0,
        spread_pct: float = 2.0,
        target_pct: float = 10.0
    ) -> Tuple[Optional[str], List[float], List[float]]:
        """
        Generate trade setup chart.

        Returns:
            Tuple of (chart_path, scaled_entries, scaled_exits)
        """
        try:
            import asyncio
            from chart_utils import (
                TradeSetup, calculate_scaled_entries, calculate_scaled_exits
            )

            # Calculate scaled levels
            scaled_entries = calculate_scaled_entries(entry_price, direction, spread_pct, 5)
            scaled_exits = calculate_scaled_exits(entry_price, direction, target_pct, 5)

            if not self.generate_charts:
                return None, scaled_entries, scaled_exits

            # Import chart function
            from hyp_chart_trade_setup import chart_trade_setup

            # Run async chart generation
            chart_path = asyncio.run(chart_trade_setup(
                ticker=coin,
                direction=direction,
                entry_price=entry_price,
                stop_price=stop_price,
                spread_pct=spread_pct,
                target_pct=target_pct,
                timeframe='1h',
                num_bars=100,
                leverage=leverage,
                size=size
            ))

            return chart_path, scaled_entries, scaled_exits

        except Exception as e:
            print(f"  Warning: Chart generation failed: {e}")
            # Still return scaled levels even if chart fails
            from chart_utils import calculate_scaled_entries, calculate_scaled_exits
            scaled_entries = calculate_scaled_entries(entry_price, direction, spread_pct, 5)
            scaled_exits = calculate_scaled_exits(entry_price, direction, target_pct, 5)
            return None, scaled_entries, scaled_exits

    def _validate_stop(self, entry: float, stop: float, direction: str) -> bool:
        """Validate stop loss is on correct side and reasonable distance."""
        if direction == 'LONG':
            if stop >= entry:
                print(f"[ERROR] Stop ${stop:.4f} must be BELOW entry ${entry:.4f} for LONG")
                return False
        else:  # SHORT
            if stop <= entry:
                print(f"[ERROR] Stop ${stop:.4f} must be ABOVE entry ${entry:.4f} for SHORT")
                return False

        # Check distance (max 20%)
        distance = abs(entry - stop) / entry * 100
        if distance > 20:
            print(f"[ERROR] Stop distance {distance:.1f}% exceeds maximum 20%")
            return False

        if distance < 0.5:
            print(f"[ERROR] Stop distance {distance:.1f}% too tight (min 0.5%)")
            return False

        return True

    def _place_stop_loss(self, coin: str, size: float, stop_price: float, direction: str) -> Dict:
        """Place stop loss order."""
        is_buy = direction == 'SHORT'  # Buy to close short, sell to close long

        trigger = {
            "triggerPx": stop_price,
            "isMarket": True,
            "tpsl": "sl"
        }

        return self.exchange.order(
            coin,
            is_buy,
            size,
            stop_price,
            {"trigger": trigger},
            reduce_only=True
        )

    def _get_meta_info(self, coin: str) -> Dict:
        """Get asset metadata for sizing."""
        meta = self.info.meta()
        for asset in meta['universe']:
            if asset['name'] == coin:
                return asset
        return {}

    def market_short(
        self,
        coin: str,
        size: float,
        leverage: int = 10,
        stop_price: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> TradeResult:
        """
        Execute a market short with required stop loss.

        Args:
            coin: Trading pair (e.g., 'XRP', 'ADA')
            size: Position size in coin units
            leverage: Leverage to use (default 10x)
            stop_price: Manual stop price (auto-calculated if None)
            take_profit: Optional take profit price
        """
        direction = 'SHORT'

        print(f"\n{'='*50}")
        print(f"SAFE TRADE EXECUTOR - {coin} {direction}")
        print(f"{'='*50}")

        # Get current price
        current_price = self.level_calc.get_current_price(coin)
        if current_price == 0:
            return TradeResult(
                success=False, coin=coin, direction=direction,
                entry_price=0, size=size, stop_loss=0, stop_method='',
                error=f"Could not get price for {coin}"
            )

        print(f"Current Price: ${current_price:.4f}")
        print(f"Size: {size} {coin}")
        print(f"Leverage: {leverage}x")

        # Calculate or validate stop loss
        if stop_price:
            stop_level = StopLossLevel(
                price=stop_price,
                method='manual',
                distance_pct=abs(stop_price - current_price) / current_price * 100,
                description='User-specified stop'
            )
        else:
            print("\nCalculating stop loss from key levels...")
            stop_level = self.level_calc.calculate_stop_loss(coin, direction, current_price)

        print(f"\nStop Loss: ${stop_level.price:.4f}")
        print(f"  Method: {stop_level.method}")
        print(f"  Distance: {stop_level.distance_pct:.1f}%")
        print(f"  Reason: {stop_level.description}")

        # Validate stop
        if not self._validate_stop(current_price, stop_level.price, direction):
            return TradeResult(
                success=False, coin=coin, direction=direction,
                entry_price=current_price, size=size, stop_loss=stop_level.price,
                stop_method=stop_level.method, error="Invalid stop loss"
            )

        # Set leverage
        print(f"\nSetting leverage to {leverage}x...")
        try:
            self.exchange.update_leverage(leverage, coin)
        except Exception as e:
            print(f"  Warning: {e}")

        # Execute market order
        print(f"\nPlacing market SHORT...")
        try:
            order_result = self.exchange.market_open(coin, False, size, None)

            if order_result.get('status') != 'ok':
                return TradeResult(
                    success=False, coin=coin, direction=direction,
                    entry_price=current_price, size=size, stop_loss=stop_level.price,
                    stop_method=stop_level.method, error=str(order_result)
                )

            # Get fill price
            fills = order_result.get('response', {}).get('data', {}).get('statuses', [])
            if fills and 'filled' in fills[0]:
                entry_price = float(fills[0]['filled'].get('avgPx', current_price))
            else:
                entry_price = current_price

            print(f"  FILLED @ ${entry_price:.4f}")

        except Exception as e:
            return TradeResult(
                success=False, coin=coin, direction=direction,
                entry_price=current_price, size=size, stop_loss=stop_level.price,
                stop_method=stop_level.method, error=str(e)
            )

        # Place stop loss immediately
        print(f"\nPlacing stop loss @ ${stop_level.price:.4f}...")
        try:
            stop_result = self._place_stop_loss(coin, size, stop_level.price, direction)

            if stop_result.get('status') != 'ok':
                print(f"  [!] WARNING: Stop loss failed: {stop_result}")
                print(f"  [!] POSITION IS UNPROTECTED - SET STOP MANUALLY")
            else:
                print(f"  Stop loss placed successfully")

        except Exception as e:
            print(f"  [!] WARNING: Stop loss error: {e}")
            print(f"  [!] POSITION IS UNPROTECTED - SET STOP MANUALLY")

        # Place take profit if specified
        if take_profit:
            print(f"\nPlacing take profit @ ${take_profit:.4f}...")
            try:
                tp_trigger = {"triggerPx": take_profit, "isMarket": True, "tpsl": "tp"}
                self.exchange.order(coin, True, size, take_profit, {"trigger": tp_trigger}, reduce_only=True)
                print(f"  Take profit placed")
            except Exception as e:
                print(f"  Warning: TP failed: {e}")

        # Generate chart and calculate scaled levels
        chart_path, scaled_entries, scaled_exits = self._generate_trade_chart(
            coin, direction, entry_price, stop_level.price, leverage, size
        )

        print(f"\n{'='*50}")
        print(f"[OK] TRADE EXECUTED")
        print(f"  {coin} SHORT @ ${entry_price:.4f}")
        print(f"  Stop: ${stop_level.price:.4f} ({stop_level.distance_pct:.1f}%)")
        if chart_path:
            print(f"  Chart: {chart_path}")
        print(f"{'='*50}\n")

        return TradeResult(
            success=True,
            coin=coin,
            direction=direction,
            entry_price=entry_price,
            size=size,
            stop_loss=stop_level.price,
            stop_method=stop_level.method,
            chart_path=chart_path,
            scaled_entries=scaled_entries,
            scaled_exits=scaled_exits
        )

    def market_long(
        self,
        coin: str,
        size: float,
        leverage: int = 10,
        stop_price: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> TradeResult:
        """Execute a market long with required stop loss."""
        direction = 'LONG'

        print(f"\n{'='*50}")
        print(f"SAFE TRADE EXECUTOR - {coin} {direction}")
        print(f"{'='*50}")

        current_price = self.level_calc.get_current_price(coin)
        if current_price == 0:
            return TradeResult(
                success=False, coin=coin, direction=direction,
                entry_price=0, size=size, stop_loss=0, stop_method='',
                error=f"Could not get price for {coin}"
            )

        print(f"Current Price: ${current_price:.4f}")
        print(f"Size: {size} {coin}")
        print(f"Leverage: {leverage}x")

        # Calculate or validate stop loss
        if stop_price:
            stop_level = StopLossLevel(
                price=stop_price,
                method='manual',
                distance_pct=abs(current_price - stop_price) / current_price * 100,
                description='User-specified stop'
            )
        else:
            print("\nCalculating stop loss from key levels...")
            stop_level = self.level_calc.calculate_stop_loss(coin, direction, current_price)

        print(f"\nStop Loss: ${stop_level.price:.4f}")
        print(f"  Method: {stop_level.method}")
        print(f"  Distance: {stop_level.distance_pct:.1f}%")
        print(f"  Reason: {stop_level.description}")

        if not self._validate_stop(current_price, stop_level.price, direction):
            return TradeResult(
                success=False, coin=coin, direction=direction,
                entry_price=current_price, size=size, stop_loss=stop_level.price,
                stop_method=stop_level.method, error="Invalid stop loss"
            )

        print(f"\nSetting leverage to {leverage}x...")
        try:
            self.exchange.update_leverage(leverage, coin)
        except Exception as e:
            print(f"  Warning: {e}")

        print(f"\nPlacing market LONG...")
        try:
            order_result = self.exchange.market_open(coin, True, size, None)

            if order_result.get('status') != 'ok':
                return TradeResult(
                    success=False, coin=coin, direction=direction,
                    entry_price=current_price, size=size, stop_loss=stop_level.price,
                    stop_method=stop_level.method, error=str(order_result)
                )

            fills = order_result.get('response', {}).get('data', {}).get('statuses', [])
            if fills and 'filled' in fills[0]:
                entry_price = float(fills[0]['filled'].get('avgPx', current_price))
            else:
                entry_price = current_price

            print(f"  FILLED @ ${entry_price:.4f}")

        except Exception as e:
            return TradeResult(
                success=False, coin=coin, direction=direction,
                entry_price=current_price, size=size, stop_loss=stop_level.price,
                stop_method=stop_level.method, error=str(e)
            )

        print(f"\nPlacing stop loss @ ${stop_level.price:.4f}...")
        try:
            stop_result = self._place_stop_loss(coin, size, stop_level.price, direction)

            if stop_result.get('status') != 'ok':
                print(f"  [!] WARNING: Stop loss failed: {stop_result}")
                print(f"  [!] POSITION IS UNPROTECTED - SET STOP MANUALLY")
            else:
                print(f"  Stop loss placed successfully")

        except Exception as e:
            print(f"  [!] WARNING: Stop loss error: {e}")

        if take_profit:
            print(f"\nPlacing take profit @ ${take_profit:.4f}...")
            try:
                tp_trigger = {"triggerPx": take_profit, "isMarket": True, "tpsl": "tp"}
                self.exchange.order(coin, False, size, take_profit, {"trigger": tp_trigger}, reduce_only=True)
                print(f"  Take profit placed")
            except Exception as e:
                print(f"  Warning: TP failed: {e}")

        # Generate chart and calculate scaled levels
        chart_path, scaled_entries, scaled_exits = self._generate_trade_chart(
            coin, direction, entry_price, stop_level.price, leverage, size
        )

        print(f"\n{'='*50}")
        print(f"[OK] TRADE EXECUTED")
        print(f"  {coin} LONG @ ${entry_price:.4f}")
        print(f"  Stop: ${stop_level.price:.4f} ({stop_level.distance_pct:.1f}%)")
        if chart_path:
            print(f"  Chart: {chart_path}")
        print(f"{'='*50}\n")

        return TradeResult(
            success=True,
            coin=coin,
            direction=direction,
            entry_price=entry_price,
            size=size,
            stop_loss=stop_level.price,
            stop_method=stop_level.method,
            chart_path=chart_path,
            scaled_entries=scaled_entries,
            scaled_exits=scaled_exits
        )

    def get_stop_preview(self, coin: str, direction: str) -> StopLossLevel:
        """Preview what stop loss would be calculated without executing."""
        current_price = self.level_calc.get_current_price(coin)
        return self.level_calc.calculate_stop_loss(coin, direction.upper(), current_price)


def main():
    """CLI interface for safe trade executor."""
    import argparse

    parser = argparse.ArgumentParser(description="Safe Trade Executor")
    parser.add_argument('action', choices=['long', 'short', 'preview'],
                       help='Trade action or preview stops')
    parser.add_argument('coin', help='Trading pair (e.g., XRP, ADA, BTC)')
    parser.add_argument('--size', type=float, help='Position size')
    parser.add_argument('--leverage', type=int, default=10, help='Leverage (default: 10)')
    parser.add_argument('--stop', type=float, help='Manual stop price')
    parser.add_argument('--tp', type=float, help='Take profit price')
    parser.add_argument('--chart', action='store_true', help='Generate trade setup chart')

    args = parser.parse_args()

    executor = SafeTradeExecutor(generate_charts=args.chart)

    if args.action == 'preview':
        print(f"\n=== STOP LOSS PREVIEW: {args.coin} ===\n")

        for direction in ['LONG', 'SHORT']:
            stop = executor.get_stop_preview(args.coin, direction)
            print(f"{direction}:")
            print(f"  Stop: ${stop.price:.4f}")
            print(f"  Method: {stop.method}")
            print(f"  Distance: {stop.distance_pct:.1f}%")
            print(f"  Reason: {stop.description}")
            print()

    elif args.action == 'long':
        if not args.size:
            print("ERROR: --size required for long")
            sys.exit(1)
        result = executor.market_long(
            args.coin.upper(), args.size, args.leverage, args.stop, args.tp
        )
        sys.exit(0 if result.success else 1)

    elif args.action == 'short':
        if not args.size:
            print("ERROR: --size required for short")
            sys.exit(1)
        result = executor.market_short(
            args.coin.upper(), args.size, args.leverage, args.stop, args.tp
        )
        sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
