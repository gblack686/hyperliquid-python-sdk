"""
Directional Momentum Strategy
=============================
Generates signals based on momentum indicators.

Logic:
- RSI extremes with EMA alignment
- Volume confirmation
- Multi-indicator confluence

This is a trend-following strategy that catches momentum moves.
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

from ..base_strategy import BaseStrategy, Recommendation, Direction

load_dotenv()


class DirectionalStrategy(BaseStrategy):
    """Directional momentum strategy - trend following"""

    def __init__(
        self,
        min_score: int = 60,  # Minimum momentum score
        min_volume_24h: float = 500000,
        min_change_24h: float = 2.0,  # Minimum 24h change %
        max_signals_per_run: int = 3,
        risk_reward_ratio: float = 1.5,
        position_size_usd: float = 1000.0
    ):
        """
        Initialize directional strategy.

        Args:
            min_score: Minimum momentum score (0-100) to generate signal
            min_volume_24h: Minimum 24h volume in USD
            min_change_24h: Minimum 24h price change % to consider
            max_signals_per_run: Maximum signals to generate per run
            risk_reward_ratio: Target R:R ratio for entries
            position_size_usd: Default position size
        """
        super().__init__(
            name="directional_momentum",
            default_expiry_hours=24,
            min_confidence=60,
            position_size_usd=position_size_usd
        )

        self.min_score = min_score
        self.min_volume_24h = min_volume_24h
        self.min_change_24h = min_change_24h
        self.max_signals_per_run = max_signals_per_run
        self.risk_reward_ratio = risk_reward_ratio

        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

    def _get_candles(self, symbol: str, interval: str, start_time: int, end_time: int) -> List[Dict]:
        """
        Get candle data using the built-in Hyperliquid SDK.

        Args:
            symbol: Trading pair symbol (e.g., "BTC")
            interval: Candle interval (e.g., "1h", "15m")
            start_time: Start time in milliseconds
            end_time: End time in milliseconds

        Returns:
            List of candle dictionaries with o, h, l, c, v keys
        """
        try:
            raw_candles = self.info.candles_snapshot(symbol, interval, start_time, end_time)

            if not raw_candles:
                return []

            # Convert SDK format to our expected format
            candles = []
            for c in raw_candles:
                candles.append({
                    "t": c.get("t", 0),  # timestamp
                    "o": c.get("o", 0),  # open
                    "h": c.get("h", 0),  # high
                    "l": c.get("l", 0),  # low
                    "c": c.get("c", 0),  # close
                    "v": c.get("v", 0),  # volume
                })

            return candles

        except Exception as e:
            logger.debug(f"Error fetching candles for {symbol}: {e}")
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

    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> Optional[float]:
        """Calculate Average True Range"""
        if len(candles) < period + 1:
            return None

        trs = []
        for i in range(1, len(candles)):
            high = float(candles[i]["h"])
            low = float(candles[i]["l"])
            prev_close = float(candles[i-1]["c"])

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)

        if len(trs) < period:
            return None

        return np.mean(trs[-period:])

    def _calculate_momentum_score(
        self,
        is_long: bool,
        change_24h: float,
        rsi: Optional[float],
        ema20: float,
        ema50: float,
        current_price: float,
        volume_ratio: float
    ) -> int:
        """
        Calculate momentum score (0-100).

        Components:
        - Price change: 30 points
        - RSI alignment: 25 points
        - EMA alignment: 25 points
        - Volume confirmation: 20 points
        """
        score = 0

        # Price change component (30 points)
        change_score = min(abs(change_24h) * 5, 30)
        score += change_score

        # Volume component (20 points)
        if volume_ratio > 2.0:
            score += 20
        elif volume_ratio > 1.5:
            score += 15
        elif volume_ratio > 1.0:
            score += 10

        # EMA alignment (25 points)
        if is_long:
            if current_price > ema20 and ema20 > ema50:
                score += 25  # Strong bullish alignment
            elif current_price > ema20:
                score += 15
            elif current_price > ema50:
                score += 10
        else:
            if current_price < ema20 and ema20 < ema50:
                score += 25  # Strong bearish alignment
            elif current_price < ema20:
                score += 15
            elif current_price < ema50:
                score += 10

        # RSI component (25 points)
        if rsi:
            if is_long:
                # For longs: want RSI 40-70 (room to run, not overbought)
                if 40 <= rsi <= 65:
                    score += 25
                elif 30 <= rsi < 40:  # Recovering
                    score += 20
                elif 65 < rsi <= 75:  # Getting hot but still ok
                    score += 15
            else:
                # For shorts: want RSI 30-60 (room to fall, not oversold)
                if 35 <= rsi <= 60:
                    score += 25
                elif 60 < rsi <= 70:  # Weakening
                    score += 20
                elif 25 <= rsi < 35:
                    score += 15

        return min(score, 100)

    async def generate_signals(self) -> List[Recommendation]:
        """
        Generate signals based on momentum indicators.

        Returns:
            List of recommendations for high momentum opportunities
        """
        logger.info(f"[{self.name}] Scanning for momentum opportunities...")

        try:

            # Get market data
            meta_and_ctxs = self.info.meta_and_asset_ctxs()

            if not meta_and_ctxs or len(meta_and_ctxs) < 2:
                logger.error("Could not fetch market data")
                return []

            meta = meta_and_ctxs[0]
            asset_ctxs = meta_and_ctxs[1]
            universe = meta.get("universe", [])

            # Filter and sort candidates
            candidates = []
            for i, asset in enumerate(universe):
                ticker = asset.get("name", "")
                ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}

                mark_price = float(ctx.get("markPx", 0))
                prev_price = float(ctx.get("prevDayPx", 0))
                volume_24h = float(ctx.get("dayNtlVlm", 0))

                if mark_price > 0 and prev_price > 0 and volume_24h >= self.min_volume_24h:
                    change_24h = ((mark_price - prev_price) / prev_price) * 100

                    if abs(change_24h) >= self.min_change_24h:
                        candidates.append({
                            "ticker": ticker,
                            "mark_price": mark_price,
                            "change_24h": change_24h,
                            "volume_24h": volume_24h,
                            "is_long": change_24h > 0
                        })

            # Sort by absolute change
            candidates.sort(key=lambda x: abs(x["change_24h"]), reverse=True)
            candidates = candidates[:15]  # Top 15 movers

            logger.info(f"[{self.name}] Analyzing {len(candidates)} momentum candidates")

            # Get active recommendations
            active_recs = self.get_active_recommendations()
            active_symbols = {r.symbol for r in active_recs}

            recommendations = []
            now = int(time.time() * 1000)
            start = now - (100 * 60 * 60 * 1000)  # 100 hours for EMA calculation

            for candidate in candidates:
                ticker = candidate["ticker"]

                if ticker in active_symbols:
                    continue

                if len(recommendations) >= self.max_signals_per_run:
                    break

                try:
                    # Fetch candle data using built-in SDK
                    candles = self._get_candles(ticker, "1h", start, now)

                    if not candles or len(candles) < 50:
                        continue

                    closes = np.array([float(c["c"]) for c in candles])
                    volumes = np.array([float(c["v"]) for c in candles])

                    # Calculate indicators
                    rsi = self._calculate_rsi(closes, 14)
                    ema20 = self._calculate_ema(closes, 20)
                    ema50 = self._calculate_ema(closes, 50)
                    atr = self._calculate_atr(candles, 14)

                    current_price = closes[-1]
                    avg_volume = np.mean(volumes[-20:])
                    recent_volume = np.mean(volumes[-3:])
                    volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

                    # Calculate momentum score
                    is_long = candidate["is_long"]
                    score = self._calculate_momentum_score(
                        is_long=is_long,
                        change_24h=candidate["change_24h"],
                        rsi=rsi,
                        ema20=ema20,
                        ema50=ema50,
                        current_price=current_price,
                        volume_ratio=volume_ratio
                    )

                    if score < self.min_score:
                        continue

                    # Calculate entry, target, stop
                    direction = Direction.LONG if is_long else Direction.SHORT

                    if atr:
                        # ATR-based stops
                        if is_long:
                            stop_loss = current_price - (atr * 2)
                            risk = current_price - stop_loss
                            target = current_price + (risk * self.risk_reward_ratio)
                        else:
                            stop_loss = current_price + (atr * 2)
                            risk = stop_loss - current_price
                            target = current_price - (risk * self.risk_reward_ratio)
                    else:
                        # Percentage-based fallback
                        stop_pct = 0.02  # 2%
                        if is_long:
                            stop_loss = current_price * (1 - stop_pct)
                            target = current_price * (1 + stop_pct * self.risk_reward_ratio)
                        else:
                            stop_loss = current_price * (1 + stop_pct)
                            target = current_price * (1 - stop_pct * self.risk_reward_ratio)

                    # Confidence is based on score
                    confidence = max(55, min(score, 95))

                    rec = self.create_recommendation(
                        symbol=ticker,
                        direction=direction,
                        entry_price=current_price,
                        confidence_score=confidence,
                        target_price_1=target,
                        stop_loss_price=stop_loss,
                        strategy_params={
                            "change_24h": candidate["change_24h"],
                            "momentum_score": score,
                            "rsi": rsi,
                            "ema20": ema20,
                            "ema50": ema50,
                            "atr": atr,
                            "volume_ratio": volume_ratio,
                            "volume_24h": candidate["volume_24h"]
                        },
                        notes=f"Score: {score}/100, 24h: {candidate['change_24h']:+.1f}%, RSI: {rsi:.0f}" if rsi else f"Score: {score}/100, 24h: {candidate['change_24h']:+.1f}%"
                    )

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


async def test_directional_strategy():
    """Test the directional strategy"""
    strategy = DirectionalStrategy(
        min_score=50,  # Lower for testing
        min_change_24h=1.0,
        max_signals_per_run=5
    )

    print("Testing Directional Strategy...")
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
    asyncio.run(test_directional_strategy())
