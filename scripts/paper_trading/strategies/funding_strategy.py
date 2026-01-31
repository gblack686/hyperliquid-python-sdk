"""
Funding Arbitrage Strategy
==========================
Identifies funding rate arbitrage opportunities.
- High positive funding -> SHORT (collect funding)
- High negative funding -> LONG (collect funding)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from hyperliquid.info import Info
from hyperliquid.utils import constants

from ..base_strategy import BaseStrategy, Recommendation

logger = logging.getLogger(__name__)


class FundingStrategy(BaseStrategy):
    """Funding rate arbitrage strategy"""

    def __init__(
        self,
        min_funding_rate: float = 0.01,  # Minimum 0.01% per 8h
        min_volume: float = 100_000,     # Minimum $100K 24h volume
        expiry_hours: int = 8,           # 8 hour expiry (one funding period)
        position_size: float = 1000.0,   # Paper position size
    ):
        """
        Initialize funding strategy.

        Args:
            min_funding_rate: Minimum funding rate (%) to trigger signal
            min_volume: Minimum 24h volume in USD
            expiry_hours: Hours until recommendation expires
            position_size: Paper position size in USD
        """
        super().__init__(name="funding_arbitrage", expiry_hours=expiry_hours)

        self.min_funding_rate = min_funding_rate
        self.min_volume = min_volume
        self.position_size = position_size

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

            # Build list with volume data
            symbols = []
            for i, asset in enumerate(universe):
                ticker = asset.get("name", f"UNKNOWN_{i}")
                ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}
                volume = float(ctx.get("dayNtlVlm", 0))

                if volume >= self.min_volume:
                    symbols.append((ticker, volume))

            # Sort by volume and return top N
            symbols.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in symbols[:limit]]

        except Exception as e:
            logger.error(f"Error getting top symbols: {e}")
            return []

    async def generate_recommendations(self) -> List[Recommendation]:
        """Generate funding arbitrage recommendations"""
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        recommendations = []

        try:
            logger.info("[FUNDING] Fetching market data...")
            meta_and_ctxs = info.meta_and_asset_ctxs()

            if not meta_and_ctxs or len(meta_and_ctxs) < 2:
                logger.error("[FUNDING] Could not fetch market data")
                return []

            meta = meta_and_ctxs[0]
            asset_ctxs = meta_and_ctxs[1]
            universe = meta.get("universe", [])

            logger.info(f"[FUNDING] Analyzing {len(universe)} markets...")

            # Extract funding data
            funding_data = []
            for i, asset in enumerate(universe):
                ticker = asset.get("name", f"UNKNOWN_{i}")
                ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}

                funding_rate = float(ctx.get("funding", 0)) * 100  # Convert to %
                mark_price = float(ctx.get("markPx", 0))
                open_interest = float(ctx.get("openInterest", 0))
                volume_24h = float(ctx.get("dayNtlVlm", 0))

                if mark_price > 0 and volume_24h >= self.min_volume:
                    funding_data.append({
                        "ticker": ticker,
                        "funding_8h": funding_rate,
                        "funding_apy": funding_rate * 3 * 365,
                        "mark_price": mark_price,
                        "open_interest": open_interest * mark_price,  # OI in USD
                        "volume_24h": volume_24h,
                    })

            # Find positive funding opportunities (SHORT)
            positive_funding = [
                f for f in funding_data
                if f["funding_8h"] >= self.min_funding_rate
            ]
            positive_funding.sort(key=lambda x: x["funding_8h"], reverse=True)

            # Find negative funding opportunities (LONG)
            negative_funding = [
                f for f in funding_data
                if f["funding_8h"] <= -self.min_funding_rate
            ]
            negative_funding.sort(key=lambda x: x["funding_8h"])

            logger.info(f"[FUNDING] Found {len(positive_funding)} SHORT opportunities")
            logger.info(f"[FUNDING] Found {len(negative_funding)} LONG opportunities")

            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(hours=self.expiry_hours)

            # Generate SHORT recommendations (positive funding)
            for opp in positive_funding[:5]:
                # For shorts: target is below entry, stop is above
                entry = opp["mark_price"]
                target = entry * 0.995  # 0.5% profit target (conservative for carry)
                stop = entry * (1 + abs(opp["funding_8h"]) * 2 / 100)  # 2x funding as stop

                # Confidence based on funding rate magnitude and volume
                confidence = min(95, int(50 + abs(opp["funding_8h"]) * 500 + opp["volume_24h"] / 1e8))

                rec = Recommendation(
                    strategy_name=self.name,
                    symbol=opp["ticker"],
                    direction="SHORT",
                    entry_price=entry,
                    target_price_1=target,
                    stop_loss_price=stop,
                    confidence_score=confidence,
                    expires_at=expires_at,
                    position_size=self.position_size,
                    strategy_params={
                        "funding_8h": opp["funding_8h"],
                        "funding_apy": opp["funding_apy"],
                        "open_interest": opp["open_interest"],
                        "volume_24h": opp["volume_24h"],
                    },
                )
                recommendations.append(rec)
                logger.info(
                    f"[FUNDING] SHORT {opp['ticker']}: "
                    f"funding={opp['funding_8h']:+.4f}%, conf={confidence}"
                )

            # Generate LONG recommendations (negative funding)
            for opp in negative_funding[:5]:
                # For longs: target is above entry, stop is below
                entry = opp["mark_price"]
                target = entry * 1.005  # 0.5% profit target
                stop = entry * (1 - abs(opp["funding_8h"]) * 2 / 100)  # 2x funding as stop

                confidence = min(95, int(50 + abs(opp["funding_8h"]) * 500 + opp["volume_24h"] / 1e8))

                rec = Recommendation(
                    strategy_name=self.name,
                    symbol=opp["ticker"],
                    direction="LONG",
                    entry_price=entry,
                    target_price_1=target,
                    stop_loss_price=stop,
                    confidence_score=confidence,
                    expires_at=expires_at,
                    position_size=self.position_size,
                    strategy_params={
                        "funding_8h": opp["funding_8h"],
                        "funding_apy": opp["funding_apy"],
                        "open_interest": opp["open_interest"],
                        "volume_24h": opp["volume_24h"],
                    },
                )
                recommendations.append(rec)
                logger.info(
                    f"[FUNDING] LONG {opp['ticker']}: "
                    f"funding={opp['funding_8h']:+.4f}%, conf={confidence}"
                )

            return recommendations

        except Exception as e:
            logger.error(f"[FUNDING] Error generating recommendations: {e}")
            raise
