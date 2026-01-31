"""
Directional Momentum Strategy
=============================
Identifies high-momentum opportunities using:
- RSI
- EMA crossovers
- Volume confirmation
- 24h price change
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
    logger.warning("quantpylib not available - using basic momentum detection")


class DirectionalStrategy(BaseStrategy):
    """Directional momentum strategy"""

    def __init__(
        self,
        min_change_pct: float = 3.0,     # Minimum 3% 24h change
        min_volume: float = 500_000,     # Minimum $500K 24h volume
        min_score: int = 50,             # Minimum momentum score (0-100)
        expiry_hours: int = 24,          # 24 hour expiry
        position_size: float = 1000.0,   # Paper position size
    ):
        """
        Initialize directional strategy.

        Args:
            min_change_pct: Minimum 24h price change to consider
            min_volume: Minimum 24h volume in USD
            min_score: Minimum momentum score to generate signal
            expiry_hours: Hours until recommendation expires
            position_size: Paper position size in USD
        """
        super().__init__(name="directional_momentum", expiry_hours=expiry_hours)

        self.min_change_pct = min_change_pct
        self.min_volume = min_volume
        self.min_score = min_score
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

    def _calculate_ema(self, closes: np.ndarray, period: int) -> float:
        """Calculate EMA"""
        if len(closes) < period:
            return closes[-1] if len(closes) > 0 else 0

        multiplier = 2 / (period + 1)
        ema = np.mean(closes[:period])

        for price in closes[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    async def _get_technical_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get technical indicator data for a symbol"""
        hyp = await self._get_hyp_client()

        if not hyp:
            # Return None - will use basic momentum detection
            return None

        try:
            now = int(time.time() * 1000)
            start = now - (100 * 60 * 60 * 1000)  # 100 hours of 1h candles

            candles = await hyp.candle_historical(
                ticker=ticker,
                interval="1h",
                start=start,
                end=now
            )

            if not candles or len(candles) < 20:
                return None

            closes = np.array([float(c["c"]) for c in candles])
            volumes = np.array([float(c["v"]) for c in candles])

            current_price = closes[-1]
            rsi = self._calculate_rsi(closes)
            ema20 = self._calculate_ema(closes, 20)
            ema50 = self._calculate_ema(closes, 50) if len(closes) >= 50 else ema20

            avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

            return {
                "current_price": current_price,
                "rsi": rsi,
                "ema20": ema20,
                "ema50": ema50,
                "volume_ratio": volume_ratio,
            }

        except Exception as e:
            logger.error(f"Error getting technical data for {ticker}: {e}")
            return None

    def _calculate_momentum_score(
        self,
        change_24h: float,
        is_long: bool,
        rsi: Optional[float],
        current_price: float,
        ema20: Optional[float],
        ema50: Optional[float],
        volume_ratio: Optional[float]
    ) -> int:
        """
        Calculate momentum score (0-100).

        Components:
        - Price change (30 points)
        - Volume (20 points)
        - EMA alignment (25 points)
        - RSI (25 points)
        """
        score = 0

        # Price change component (30 points)
        change_score = min(abs(change_24h) * 3, 30)
        score += change_score

        # Volume component (20 points)
        if volume_ratio:
            if volume_ratio > 2:
                score += 20
            elif volume_ratio > 1.5:
                score += 15
            elif volume_ratio > 1:
                score += 10

        # EMA alignment (25 points)
        if ema20 and ema50:
            if is_long:
                if current_price > ema20 and current_price > ema50:
                    score += 25
                elif current_price > ema20:
                    score += 15
            else:
                if current_price < ema20 and current_price < ema50:
                    score += 25
                elif current_price < ema20:
                    score += 15

        # RSI component (25 points)
        if rsi:
            if is_long:
                if 40 <= rsi <= 70:  # Not overbought, room to run
                    score += 25
                elif 30 <= rsi < 40:  # Recovering
                    score += 20
                elif rsi > 70:  # Overbought - reduce score
                    score += 5
            else:
                if 30 <= rsi <= 60:  # Not oversold, room to fall
                    score += 25
                elif 60 < rsi <= 70:  # Starting to weaken
                    score += 20
                elif rsi < 30:  # Oversold - reduce score
                    score += 5

        return min(100, int(score))

    def _get_ema_status(
        self,
        current_price: float,
        ema20: Optional[float],
        ema50: Optional[float]
    ) -> str:
        """Get human-readable EMA status"""
        if not ema20 or not ema50:
            return "N/A"

        if current_price > ema20 > ema50:
            return "Price > EMA20 > EMA50"
        elif current_price > ema20:
            return "Price > EMA20"
        elif current_price < ema20 < ema50:
            return "Price < EMA20 < EMA50"
        elif current_price < ema20:
            return "Price < EMA20"
        else:
            return "Mixed"

    async def generate_recommendations(self) -> List[Recommendation]:
        """Generate directional momentum recommendations"""
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        recommendations = []

        try:
            logger.info("[MOMENTUM] Fetching market data...")
            meta_and_ctxs = info.meta_and_asset_ctxs()

            if not meta_and_ctxs or len(meta_and_ctxs) < 2:
                logger.error("[MOMENTUM] Could not fetch market data")
                return []

            meta = meta_and_ctxs[0]
            asset_ctxs = meta_and_ctxs[1]
            universe = meta.get("universe", [])

            logger.info(f"[MOMENTUM] Analyzing {len(universe)} markets...")

            # Extract market data with 24h changes
            market_data = []
            for i, asset in enumerate(universe):
                ticker = asset.get("name", f"UNKNOWN_{i}")
                ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}

                mark_price = float(ctx.get("markPx", 0))
                prev_price = float(ctx.get("prevDayPx", 0))
                volume_24h = float(ctx.get("dayNtlVlm", 0))
                open_interest = float(ctx.get("openInterest", 0))

                if mark_price > 0 and prev_price > 0 and volume_24h >= self.min_volume:
                    change_24h = ((mark_price - prev_price) / prev_price) * 100

                    # Only consider markets with significant movement
                    if abs(change_24h) >= self.min_change_pct:
                        market_data.append({
                            "ticker": ticker,
                            "price": mark_price,
                            "change_24h": change_24h,
                            "volume_24h": volume_24h,
                            "open_interest": open_interest * mark_price,
                        })

            # Sort by absolute change
            market_data.sort(key=lambda x: abs(x["change_24h"]), reverse=True)

            logger.info(f"[MOMENTUM] Found {len(market_data)} candidates with >{self.min_change_pct}% change")

            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(hours=self.expiry_hours)

            # Analyze top movers
            for market in market_data[:10]:
                ticker = market["ticker"]
                is_long = market["change_24h"] > 0

                # Get technical data
                tech_data = await self._get_technical_data(ticker)

                rsi = tech_data["rsi"] if tech_data else None
                ema20 = tech_data["ema20"] if tech_data else None
                ema50 = tech_data["ema50"] if tech_data else None
                volume_ratio = tech_data["volume_ratio"] if tech_data else None
                current_price = tech_data["current_price"] if tech_data else market["price"]

                # Calculate momentum score
                score = self._calculate_momentum_score(
                    market["change_24h"],
                    is_long,
                    rsi,
                    current_price,
                    ema20,
                    ema50,
                    volume_ratio
                )

                if score < self.min_score:
                    continue

                direction = "LONG" if is_long else "SHORT"

                # Calculate targets and stops
                if is_long:
                    # For longs: target above, stop below
                    target = current_price * 1.02  # 2% target
                    stop = current_price * 0.982   # 1.8% stop
                else:
                    # For shorts: target below, stop above
                    target = current_price * 0.98   # 2% target
                    stop = current_price * 1.018    # 1.8% stop

                ema_status = self._get_ema_status(current_price, ema20, ema50)

                rec = Recommendation(
                    strategy_name=self.name,
                    symbol=ticker,
                    direction=direction,
                    entry_price=current_price,
                    target_price_1=target,
                    stop_loss_price=stop,
                    confidence_score=score,
                    expires_at=expires_at,
                    position_size=self.position_size,
                    strategy_params={
                        "change_24h": round(market["change_24h"], 2),
                        "score": score,
                        "rsi": round(rsi, 1) if rsi else None,
                        "ema_status": ema_status,
                        "volume_ratio": round(volume_ratio, 2) if volume_ratio else None,
                        "volume_24h": market["volume_24h"],
                    },
                )
                recommendations.append(rec)
                rsi_str = f"{rsi:.1f}" if rsi else "N/A"
                logger.info(
                    f"[MOMENTUM] {direction} {ticker}: "
                    f"change={market['change_24h']:+.1f}%, score={score}, rsi={rsi_str}"
                )

            logger.info(f"[MOMENTUM] Generated {len(recommendations)} recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"[MOMENTUM] Error generating recommendations: {e}")
            raise

        finally:
            # Cleanup Hyperliquid client
            if self._hyp:
                try:
                    await self._hyp.cleanup()
                except Exception:
                    pass
                self._hyp = None
