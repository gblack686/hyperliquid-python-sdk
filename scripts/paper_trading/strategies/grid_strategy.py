"""
Grid/Box Trading Strategy
=========================
Identifies range-bound markets and generates mean reversion signals.
- Buy at range lows (oversold)
- Sell at range highs (overbought)
"""

import os
import logging
import time
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from hyperliquid.info import Info
from hyperliquid.utils import constants
from dotenv import load_dotenv

load_dotenv()

from ..base_strategy import BaseStrategy, Recommendation

logger = logging.getLogger(__name__)

# Try to import quantpylib for candle data
try:
    from quantpylib.wrappers.hyperliquid import Hyperliquid
    HAS_QUANTPYLIB = True
except ImportError:
    HAS_QUANTPYLIB = False
    logger.warning("quantpylib not available - using basic range detection")


class GridStrategy(BaseStrategy):
    """Grid/range trading strategy"""

    def __init__(
        self,
        lookback_hours: int = 72,        # Hours to calculate range
        min_range_pct: float = 3.0,      # Minimum range size (%)
        max_range_pct: float = 15.0,     # Maximum range size (%)
        entry_threshold_pct: float = 20, # Enter when price is in bottom/top 20% of range
        min_volume: float = 500_000,     # Minimum $500K 24h volume
        expiry_hours: int = 24,          # 24 hour expiry
        position_size: float = 1000.0,   # Paper position size
    ):
        """
        Initialize grid strategy.

        Args:
            lookback_hours: Hours to look back for range calculation
            min_range_pct: Minimum range width as percentage
            max_range_pct: Maximum range width (avoid trending markets)
            entry_threshold_pct: % from range edge to trigger entry
            min_volume: Minimum 24h volume in USD
            expiry_hours: Hours until recommendation expires
            position_size: Paper position size in USD
        """
        super().__init__(name="grid_trading", expiry_hours=expiry_hours)

        self.lookback_hours = lookback_hours
        self.min_range_pct = min_range_pct
        self.max_range_pct = max_range_pct
        self.entry_threshold_pct = entry_threshold_pct
        self.min_volume = min_volume
        self.position_size = position_size

        self._hyp = None

    async def _get_hyp_client(self):
        """Get or create Hyperliquid client for candle data"""
        if not HAS_QUANTPYLIB:
            return None

        if self._hyp is None:
            try:
                self._hyp = Hyperliquid(
                    key=os.getenv("HYP_KEY"),
                    secret=os.getenv("HYP_SECRET"),
                    mode="live"
                )
                await self._hyp.init_client()
            except Exception as e:
                logger.warning(f"Could not initialize Hyperliquid client: {e}")
                return None

        return self._hyp

    async def get_top_symbols(self, limit: int = 10) -> List[str]:
        """Get top symbols by 24h volume"""
        info = Info(constants.MAINNET_API_URL, skip_ws=True)

        try:
            meta_and_ctxs = info.meta_and_asset_ctxs()
            if not meta_and_ctxs or len(meta_and_ctxs) < 2:
                return []

            meta = meta_and_ctxs[0]
            asset_ctxs = meta_and_ctxs[1]
            universe = meta.get("universe", [])

            symbols = []
            for i, asset in enumerate(universe):
                ticker = asset.get("name", f"UNKNOWN_{i}")
                ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}
                volume = float(ctx.get("dayNtlVlm", 0))

                if volume >= self.min_volume:
                    symbols.append((ticker, volume))

            symbols.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in symbols[:limit]]

        except Exception as e:
            logger.error(f"Error getting top symbols: {e}")
            return []

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

    async def _get_range_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get price range data for a symbol"""
        hyp = await self._get_hyp_client()

        if not hyp:
            # Fallback: use simple 24h range from market data
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            meta_and_ctxs = info.meta_and_asset_ctxs()

            if not meta_and_ctxs or len(meta_and_ctxs) < 2:
                return None

            meta = meta_and_ctxs[0]
            asset_ctxs = meta_and_ctxs[1]
            universe = meta.get("universe", [])

            for i, asset in enumerate(universe):
                if asset.get("name") == ticker:
                    ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}
                    mark_price = float(ctx.get("markPx", 0))
                    prev_price = float(ctx.get("prevDayPx", 0))

                    if mark_price > 0 and prev_price > 0:
                        # Estimate range as +/- 3% from current price
                        range_high = mark_price * 1.03
                        range_low = mark_price * 0.97
                        range_pct = 6.0

                        return {
                            "range_low": range_low,
                            "range_high": range_high,
                            "range_pct": range_pct,
                            "current_price": mark_price,
                            "rsi": None,
                            "closes": None,
                        }
            return None

        try:
            now = int(time.time() * 1000)
            start = now - (self.lookback_hours * 60 * 60 * 1000)

            candles = await hyp.candle_historical(
                ticker=ticker,
                interval="1h",
                start=start,
                end=now
            )

            if not candles or len(candles) < 24:
                return None

            # Extract OHLC data
            highs = np.array([float(c["h"]) for c in candles])
            lows = np.array([float(c["l"]) for c in candles])
            closes = np.array([float(c["c"]) for c in candles])

            range_high = np.max(highs)
            range_low = np.min(lows)
            current_price = closes[-1]

            range_pct = ((range_high - range_low) / range_low) * 100

            # Calculate RSI
            rsi = self._calculate_rsi(closes)

            return {
                "range_low": range_low,
                "range_high": range_high,
                "range_pct": range_pct,
                "current_price": current_price,
                "rsi": rsi,
                "closes": closes,
            }

        except Exception as e:
            logger.error(f"Error getting range data for {ticker}: {e}")
            return None

    async def generate_recommendations(self) -> List[Recommendation]:
        """Generate grid trading recommendations"""
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        recommendations = []

        try:
            logger.info("[GRID] Fetching market data...")
            meta_and_ctxs = info.meta_and_asset_ctxs()

            if not meta_and_ctxs or len(meta_and_ctxs) < 2:
                logger.error("[GRID] Could not fetch market data")
                return []

            meta = meta_and_ctxs[0]
            asset_ctxs = meta_and_ctxs[1]
            universe = meta.get("universe", [])

            # Get top symbols by volume
            top_symbols = await self.get_top_symbols(limit=20)
            logger.info(f"[GRID] Analyzing {len(top_symbols)} top symbols...")

            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(hours=self.expiry_hours)

            for ticker in top_symbols:
                range_data = await self._get_range_data(ticker)

                if not range_data:
                    continue

                range_low = range_data["range_low"]
                range_high = range_data["range_high"]
                range_pct = range_data["range_pct"]
                current_price = range_data["current_price"]
                rsi = range_data["rsi"]

                # Check range is within acceptable bounds
                if range_pct < self.min_range_pct or range_pct > self.max_range_pct:
                    continue

                # Calculate position in range (0% = at low, 100% = at high)
                position_in_range = ((current_price - range_low) / (range_high - range_low)) * 100

                # Check if price is near range edges
                direction = None
                confidence = 50

                if position_in_range <= self.entry_threshold_pct:
                    # Price at range low - BUY
                    direction = "LONG"
                    # Higher confidence if RSI confirms oversold
                    if rsi and rsi < 30:
                        confidence = 80
                    elif rsi and rsi < 40:
                        confidence = 70
                    else:
                        confidence = 60

                elif position_in_range >= (100 - self.entry_threshold_pct):
                    # Price at range high - SELL
                    direction = "SHORT"
                    if rsi and rsi > 70:
                        confidence = 80
                    elif rsi and rsi > 60:
                        confidence = 70
                    else:
                        confidence = 60

                if direction:
                    # Calculate target (range mid) and stop (beyond range)
                    range_mid = (range_high + range_low) / 2

                    if direction == "LONG":
                        target = range_mid
                        stop = range_low * 0.98  # 2% below range low
                    else:
                        target = range_mid
                        stop = range_high * 1.02  # 2% above range high

                    rec = Recommendation(
                        strategy_name=self.name,
                        symbol=ticker,
                        direction=direction,
                        entry_price=current_price,
                        target_price_1=target,
                        stop_loss_price=stop,
                        confidence_score=confidence,
                        expires_at=expires_at,
                        position_size=self.position_size,
                        strategy_params={
                            "range_low": round(range_low, 4),
                            "range_high": round(range_high, 4),
                            "range_pct": round(range_pct, 2),
                            "position_in_range": round(position_in_range, 1),
                            "rsi": round(rsi, 1) if rsi else None,
                        },
                    )
                    recommendations.append(rec)
                    rsi_str = f"{rsi:.1f}" if rsi else "N/A"
                    logger.info(
                        f"[GRID] {direction} {ticker}: "
                        f"pos={position_in_range:.1f}%, rsi={rsi_str}, conf={confidence}"
                    )

            logger.info(f"[GRID] Generated {len(recommendations)} recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"[GRID] Error generating recommendations: {e}")
            raise

        finally:
            # Cleanup Hyperliquid client
            if self._hyp:
                try:
                    await self._hyp.cleanup()
                except Exception:
                    pass
                self._hyp = None
