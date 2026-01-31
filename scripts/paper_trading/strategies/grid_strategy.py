"""
Grid/Box Trading Strategy
=========================
Generates signals based on price range detection.

Logic:
- Identify trading ranges using recent high/low
- Buy at lower range boundary
- Sell at upper range boundary
- Mean reversion approach

Best for sideways/consolidating markets.
"""

import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio
import numpy as np

from loguru import logger
from dotenv import load_dotenv

from hyperliquid.info import Info
from hyperliquid.utils import constants

try:
    from quantpylib.wrappers.hyperliquid import Hyperliquid
    HAS_QUANTPY = True
except ImportError:
    HAS_QUANTPY = False
    logger.warning("quantpylib not available - grid strategy will have limited functionality")

from ..base_strategy import BaseStrategy, Recommendation, Direction

load_dotenv()


class GridStrategy(BaseStrategy):
    """Grid/Box trading strategy - range-bound mean reversion"""

    def __init__(
        self,
        lookback_hours: int = 24,
        range_threshold_pct: float = 3.0,  # Min range size
        entry_zone_pct: float = 0.2,  # Entry within 20% of range boundary
        min_volume_24h: float = 500000,
        max_signals_per_run: int = 3,
        position_size_usd: float = 1000.0
    ):
        """
        Initialize grid strategy.

        Args:
            lookback_hours: Hours to look back for range detection
            range_threshold_pct: Minimum range size (%) to consider tradeable
            entry_zone_pct: How close to boundary to trigger (0.2 = 20% of range)
            min_volume_24h: Minimum 24h volume in USD
            max_signals_per_run: Maximum signals to generate per run
            position_size_usd: Default position size
        """
        super().__init__(
            name="grid_trading",
            default_expiry_hours=24,
            min_confidence=55,
            position_size_usd=position_size_usd
        )

        self.lookback_hours = lookback_hours
        self.range_threshold_pct = range_threshold_pct
        self.entry_zone_pct = entry_zone_pct
        self.min_volume_24h = min_volume_24h
        self.max_signals_per_run = max_signals_per_run

        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        self.hyp = None

        if HAS_QUANTPY:
            self.hyp = Hyperliquid(
                key=os.getenv("HYP_KEY"),
                secret=os.getenv("HYP_SECRET"),
                mode="live"
            )

    async def _init_hyp(self):
        """Initialize Hyperliquid client if needed"""
        if self.hyp and not hasattr(self.hyp, "_initialized"):
            await self.hyp.init_client()
            self.hyp._initialized = True

    async def _cleanup_hyp(self):
        """Cleanup Hyperliquid client"""
        if self.hyp and hasattr(self.hyp, "_initialized"):
            await self.hyp.cleanup()

    def _detect_range(self, candles: List[Dict]) -> Optional[Dict]:
        """
        Detect trading range from candle data.

        Args:
            candles: List of candle data with OHLCV

        Returns:
            Dictionary with range info or None if no range detected
        """
        if not candles or len(candles) < 10:
            return None

        highs = np.array([float(c["h"]) for c in candles])
        lows = np.array([float(c["l"]) for c in candles])
        closes = np.array([float(c["c"]) for c in candles])

        # Calculate range
        range_high = np.percentile(highs, 95)  # Use 95th percentile to filter spikes
        range_low = np.percentile(lows, 5)
        current_price = closes[-1]

        # Range size as percentage
        range_size_pct = ((range_high - range_low) / range_low) * 100

        if range_size_pct < self.range_threshold_pct:
            return None  # Range too tight

        if range_size_pct > 15:
            return None  # Range too wide (likely trending)

        # Calculate position within range (0 = at low, 1 = at high)
        position_in_range = (current_price - range_low) / (range_high - range_low)

        # Check for range breakout (price outside range)
        if current_price > range_high * 1.02 or current_price < range_low * 0.98:
            return None  # Outside range, not suitable

        # Calculate average volume
        volumes = np.array([float(c["v"]) for c in candles])
        avg_volume = np.mean(volumes)
        recent_volume = np.mean(volumes[-5:])
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

        # Calculate RSI for mean reversion confirmation
        rsi = self._calculate_rsi(closes, 14)

        return {
            "range_high": range_high,
            "range_low": range_low,
            "range_mid": (range_high + range_low) / 2,
            "range_size_pct": range_size_pct,
            "current_price": current_price,
            "position_in_range": position_in_range,
            "volume_ratio": volume_ratio,
            "rsi": rsi
        }

    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> Optional[float]:
        """Calculate RSI"""
        if len(closes) < period + 1:
            return None

        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    async def generate_signals(self) -> List[Recommendation]:
        """
        Generate signals based on range boundaries.

        Returns:
            List of recommendations at range extremes
        """
        logger.info(f"[{self.name}] Scanning for grid opportunities...")

        if not HAS_QUANTPY:
            logger.warning("quantpylib required for grid strategy - skipping")
            return []

        try:
            await self._init_hyp()

            # Get market data for filtering
            meta_and_ctxs = self.info.meta_and_asset_ctxs()

            if not meta_and_ctxs or len(meta_and_ctxs) < 2:
                logger.error("Could not fetch market data")
                return []

            meta = meta_and_ctxs[0]
            asset_ctxs = meta_and_ctxs[1]
            universe = meta.get("universe", [])

            # Filter markets by volume
            candidates = []
            for i, asset in enumerate(universe):
                ticker = asset.get("name", "")
                ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}
                volume_24h = float(ctx.get("dayNtlVlm", 0))
                mark_price = float(ctx.get("markPx", 0))

                if volume_24h >= self.min_volume_24h and mark_price > 0:
                    candidates.append({
                        "ticker": ticker,
                        "volume_24h": volume_24h,
                        "mark_price": mark_price
                    })

            # Sort by volume and take top 20
            candidates.sort(key=lambda x: x["volume_24h"], reverse=True)
            candidates = candidates[:20]

            logger.info(f"[{self.name}] Analyzing {len(candidates)} candidates")

            # Get active recommendations
            active_recs = self.get_active_recommendations()
            active_symbols = {r.symbol for r in active_recs}

            recommendations = []
            now = int(time.time() * 1000)
            start = now - (self.lookback_hours * 60 * 60 * 1000)

            for candidate in candidates:
                ticker = candidate["ticker"]

                if ticker in active_symbols:
                    continue

                if len(recommendations) >= self.max_signals_per_run:
                    break

                try:
                    # Fetch candle data
                    candles = await self.hyp.candle_historical(
                        ticker=ticker,
                        interval="1h",
                        start=start,
                        end=now
                    )

                    if not candles or len(candles) < 20:
                        continue

                    # Detect range
                    range_info = self._detect_range(candles)

                    if not range_info:
                        continue

                    position = range_info["position_in_range"]
                    rsi = range_info["rsi"]

                    # Generate signal based on position in range
                    rec = None

                    # Near bottom of range (position < 0.2) -> LONG
                    if position <= self.entry_zone_pct:
                        # Confirm with RSI (oversold helps)
                        confidence = 55

                        if rsi and rsi < 35:
                            confidence += 15
                        elif rsi and rsi < 45:
                            confidence += 10

                        if range_info["volume_ratio"] > 1.2:
                            confidence += 5

                        confidence = min(confidence, 90)

                        # Target is range midpoint or upper
                        target_price = range_info["range_mid"]
                        stop_loss = range_info["range_low"] * 0.98  # 2% below range low

                        rec = self.create_recommendation(
                            symbol=ticker,
                            direction=Direction.LONG,
                            entry_price=range_info["current_price"],
                            confidence_score=confidence,
                            target_price_1=target_price,
                            stop_loss_price=stop_loss,
                            strategy_params={
                                "range_high": range_info["range_high"],
                                "range_low": range_info["range_low"],
                                "range_size_pct": range_info["range_size_pct"],
                                "position_in_range": position,
                                "rsi": rsi,
                                "volume_24h": candidate["volume_24h"]
                            },
                            notes=f"At range low ({position*100:.0f}% of range), RSI: {rsi:.0f}" if rsi else f"At range low ({position*100:.0f}% of range)"
                        )

                    # Near top of range (position > 0.8) -> SHORT
                    elif position >= (1 - self.entry_zone_pct):
                        confidence = 55

                        if rsi and rsi > 65:
                            confidence += 15
                        elif rsi and rsi > 55:
                            confidence += 10

                        if range_info["volume_ratio"] > 1.2:
                            confidence += 5

                        confidence = min(confidence, 90)

                        target_price = range_info["range_mid"]
                        stop_loss = range_info["range_high"] * 1.02

                        rec = self.create_recommendation(
                            symbol=ticker,
                            direction=Direction.SHORT,
                            entry_price=range_info["current_price"],
                            confidence_score=confidence,
                            target_price_1=target_price,
                            stop_loss_price=stop_loss,
                            strategy_params={
                                "range_high": range_info["range_high"],
                                "range_low": range_info["range_low"],
                                "range_size_pct": range_info["range_size_pct"],
                                "position_in_range": position,
                                "rsi": rsi,
                                "volume_24h": candidate["volume_24h"]
                            },
                            notes=f"At range high ({position*100:.0f}% of range), RSI: {rsi:.0f}" if rsi else f"At range high ({position*100:.0f}% of range)"
                        )

                    if rec:
                        recommendations.append(rec)
                        active_symbols.add(ticker)

                except Exception as e:
                    logger.debug(f"Error analyzing {ticker}: {e}")
                    continue

            logger.info(f"[{self.name}] Generated {len(recommendations)} signals")
            return recommendations

        except Exception as e:
            logger.error(f"[{self.name}] Error generating signals: {e}")
            return []

    async def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for symbols"""
        prices = {}

        try:
            meta_and_ctxs = self.info.meta_and_asset_ctxs()

            if meta_and_ctxs and len(meta_and_ctxs) >= 2:
                meta = meta_and_ctxs[0]
                asset_ctxs = meta_and_ctxs[1]
                universe = meta.get("universe", [])

                for i, asset in enumerate(universe):
                    ticker = asset.get("name", "")
                    if ticker in symbols:
                        ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}
                        price = float(ctx.get("markPx", 0))
                        if price > 0:
                            prices[ticker] = price

        except Exception as e:
            logger.error(f"Error fetching prices: {e}")

        return prices


async def test_grid_strategy():
    """Test the grid strategy"""
    strategy = GridStrategy(
        lookback_hours=24,
        range_threshold_pct=2.0,  # Lower for testing
        max_signals_per_run=5
    )

    print("Testing Grid Strategy...")
    print("=" * 60)

    signals = await strategy.generate_signals()

    print(f"\nGenerated {len(signals)} signals:\n")

    for signal in signals:
        print(f"  {signal.symbol} {signal.direction.value}")
        print(f"    Entry: ${signal.entry_price:,.4f}")
        print(f"    Target: ${signal.target_price_1:,.4f}" if signal.target_price_1 else "")
        print(f"    Stop: ${signal.stop_loss_price:,.4f}" if signal.stop_loss_price else "")
        print(f"    Confidence: {signal.confidence_score}/100")
        print(f"    Notes: {signal.notes}")
        print()


if __name__ == "__main__":
    asyncio.run(test_grid_strategy())
