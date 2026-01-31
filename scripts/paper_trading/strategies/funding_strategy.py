"""
Funding Arbitrage Strategy
==========================
Generates signals based on extreme funding rates.

Logic:
- High positive funding -> SHORT (collect funding)
- High negative funding -> LONG (collect funding)

This is a carry trade strategy that profits from funding rate payments
while hedging or accepting directional risk.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio

from loguru import logger
from dotenv import load_dotenv

from hyperliquid.info import Info
from hyperliquid.utils import constants

from ..base_strategy import BaseStrategy, Recommendation, Direction

load_dotenv()


class FundingStrategy(BaseStrategy):
    """Funding arbitrage strategy - trade based on extreme funding rates"""

    def __init__(
        self,
        min_funding_rate: float = 0.01,  # 0.01% per 8h
        min_volume_24h: float = 100000,  # $100K minimum
        max_signals_per_run: int = 3,
        stop_loss_multiple: float = 2.0,  # 2x daily funding as stop
        position_size_usd: float = 1000.0
    ):
        """
        Initialize funding strategy.

        Args:
            min_funding_rate: Minimum funding rate (%) per 8h to generate signal
            min_volume_24h: Minimum 24h volume in USD
            max_signals_per_run: Maximum signals to generate per run
            stop_loss_multiple: Stop loss as multiple of daily funding rate
            position_size_usd: Default position size
        """
        super().__init__(
            name="funding_arbitrage",
            default_expiry_hours=8,  # Funding trades are short duration
            min_confidence=60,
            position_size_usd=position_size_usd
        )

        self.min_funding_rate = min_funding_rate
        self.min_volume_24h = min_volume_24h
        self.max_signals_per_run = max_signals_per_run
        self.stop_loss_multiple = stop_loss_multiple

        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

    async def generate_signals(self) -> List[Recommendation]:
        """
        Generate signals based on funding rate extremes.

        Returns:
            List of recommendations for high funding rate opportunities
        """
        logger.info(f"[{self.name}] Scanning for funding opportunities...")

        try:
            # Fetch market data
            meta_and_ctxs = self.info.meta_and_asset_ctxs()

            if not meta_and_ctxs or len(meta_and_ctxs) < 2:
                logger.error("Could not fetch market data")
                return []

            meta = meta_and_ctxs[0]
            asset_ctxs = meta_and_ctxs[1]
            universe = meta.get("universe", [])

            logger.info(f"[{self.name}] Analyzing {len(universe)} markets")

            # Get active recommendations to avoid duplicates
            active_recs = self.get_active_recommendations()
            active_symbols = {r.symbol for r in active_recs}

            # Extract funding data
            funding_data = []

            for i, asset in enumerate(universe):
                ticker = asset.get("name", f"UNKNOWN_{i}")
                ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}

                funding_rate = float(ctx.get("funding", 0)) * 100  # Convert to percentage
                mark_price = float(ctx.get("markPx", 0))
                volume_24h = float(ctx.get("dayNtlVlm", 0))
                open_interest = float(ctx.get("openInterest", 0))

                if mark_price > 0 and volume_24h >= self.min_volume_24h:
                    funding_data.append({
                        "ticker": ticker,
                        "funding_8h": funding_rate,
                        "funding_24h": funding_rate * 3,
                        "funding_apy": funding_rate * 3 * 365,
                        "mark_price": mark_price,
                        "open_interest": open_interest,
                        "volume_24h": volume_24h
                    })

            # Find extreme funding rates
            positive_funding = sorted(
                [f for f in funding_data if f["funding_8h"] >= self.min_funding_rate],
                key=lambda x: x["funding_8h"],
                reverse=True
            )

            negative_funding = sorted(
                [f for f in funding_data if f["funding_8h"] <= -self.min_funding_rate],
                key=lambda x: x["funding_8h"]
            )

            logger.info(f"[{self.name}] Found {len(positive_funding)} positive, {len(negative_funding)} negative opportunities")

            recommendations = []

            # Generate SHORT signals for high positive funding
            for opp in positive_funding[:self.max_signals_per_run]:
                if opp["ticker"] in active_symbols:
                    logger.debug(f"Skipping {opp['ticker']} - already has active signal")
                    continue

                # Calculate confidence based on funding rate and volume
                base_confidence = min(60 + int(opp["funding_8h"] * 1000), 95)

                # Volume bonus
                if opp["volume_24h"] > 1000000:
                    base_confidence = min(base_confidence + 10, 95)

                # Calculate stop loss (2x daily funding above entry)
                stop_loss_pct = opp["funding_24h"] * self.stop_loss_multiple
                stop_loss_price = opp["mark_price"] * (1 + stop_loss_pct / 100)

                # Target is just collecting funding - small price target
                # Exit when funding normalizes (conservatively, just aim for 0.5% price move)
                target_price = opp["mark_price"] * 0.995  # 0.5% below entry for shorts

                rec = self.create_recommendation(
                    symbol=opp["ticker"],
                    direction=Direction.SHORT,
                    entry_price=opp["mark_price"],
                    confidence_score=base_confidence,
                    target_price_1=target_price,
                    stop_loss_price=stop_loss_price,
                    strategy_params={
                        "funding_8h": opp["funding_8h"],
                        "funding_24h": opp["funding_24h"],
                        "funding_apy": opp["funding_apy"],
                        "volume_24h": opp["volume_24h"],
                        "open_interest": opp["open_interest"]
                    },
                    notes=f"Funding: +{opp['funding_8h']:.4f}% (8h), APY: +{opp['funding_apy']:.1f}%",
                    expiry_hours=8  # Short expiry for funding trades
                )

                recommendations.append(rec)
                active_symbols.add(opp["ticker"])

            # Generate LONG signals for high negative funding
            for opp in negative_funding[:self.max_signals_per_run]:
                if opp["ticker"] in active_symbols:
                    logger.debug(f"Skipping {opp['ticker']} - already has active signal")
                    continue

                # Calculate confidence
                base_confidence = min(60 + int(abs(opp["funding_8h"]) * 1000), 95)

                if opp["volume_24h"] > 1000000:
                    base_confidence = min(base_confidence + 10, 95)

                # Stop loss below entry
                stop_loss_pct = abs(opp["funding_24h"]) * self.stop_loss_multiple
                stop_loss_price = opp["mark_price"] * (1 - stop_loss_pct / 100)

                # Target
                target_price = opp["mark_price"] * 1.005  # 0.5% above entry for longs

                rec = self.create_recommendation(
                    symbol=opp["ticker"],
                    direction=Direction.LONG,
                    entry_price=opp["mark_price"],
                    confidence_score=base_confidence,
                    target_price_1=target_price,
                    stop_loss_price=stop_loss_price,
                    strategy_params={
                        "funding_8h": opp["funding_8h"],
                        "funding_24h": opp["funding_24h"],
                        "funding_apy": opp["funding_apy"],
                        "volume_24h": opp["volume_24h"],
                        "open_interest": opp["open_interest"]
                    },
                    notes=f"Funding: {opp['funding_8h']:.4f}% (8h), APY: {opp['funding_apy']:.1f}%",
                    expiry_hours=8
                )

                recommendations.append(rec)
                active_symbols.add(opp["ticker"])

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


async def test_funding_strategy():
    """Test the funding strategy"""
    strategy = FundingStrategy(
        min_funding_rate=0.005,  # Lower threshold for testing
        max_signals_per_run=5
    )

    print("Testing Funding Strategy...")
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
    asyncio.run(test_funding_strategy())
