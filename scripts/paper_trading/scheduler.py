#!/usr/bin/env python3
"""
Paper Trading Scheduler
=======================
Runs paper trading strategies on a schedule using APScheduler.

Usage:
    # Run continuously (every 15 minutes)
    python -m scripts.paper_trading.scheduler

    # Run once and exit
    python -m scripts.paper_trading.scheduler --once

    # Check status
    python -m scripts.paper_trading.scheduler --status

    # Generate review report
    python -m scripts.paper_trading.scheduler --review
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from hyperliquid.info import Info
from hyperliquid.utils import constants

from scripts.paper_trading.base_strategy import Recommendation
from scripts.paper_trading.metrics_calculator import MetricsCalculator
from scripts.paper_trading.strategies import (
    FundingStrategy,
    GridStrategy,
    DirectionalStrategy,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Try to import APScheduler
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    logger.warning("APScheduler not installed - continuous mode disabled")

# Try to import Telegram alerts
try:
    from integrations.telegram.alerts import TelegramAlerts, AlertPriority
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    logger.warning("Telegram integration not available")


class PaperTradingScheduler:
    """Scheduler for paper trading strategies"""

    # Strategies that should send Telegram alerts
    # Set to empty list to disable all alerts, or list specific strategy names
    ALERT_ENABLED_STRATEGIES = [
        # "funding_arbitrage",  # Disabled - not effective
        "grid_trading",
        "directional_momentum",
    ]

    def __init__(
        self,
        enable_telegram: bool = True,
        signal_interval_minutes: int = 15,
        outcome_check_interval_minutes: int = 5,
        metrics_interval_minutes: int = 60,
    ):
        """
        Initialize scheduler.

        Args:
            enable_telegram: Send alerts to Telegram
            signal_interval_minutes: Minutes between signal generation runs
            outcome_check_interval_minutes: Minutes between outcome checks
            metrics_interval_minutes: Minutes between metrics updates
        """
        self.enable_telegram = enable_telegram and HAS_TELEGRAM
        self.signal_interval = signal_interval_minutes
        self.outcome_check_interval = outcome_check_interval_minutes
        self.metrics_interval = metrics_interval_minutes

        # Initialize strategies
        self.strategies = [
            FundingStrategy(
                min_funding_rate=0.01,
                min_volume=100_000,
                expiry_hours=8,
            ),
            GridStrategy(
                lookback_hours=72,
                min_range_pct=3.0,
                max_range_pct=15.0,
                entry_threshold_pct=20,
                min_volume=500_000,
                expiry_hours=24,
            ),
            DirectionalStrategy(
                min_change_pct=3.0,
                min_volume=500_000,
                min_score=50,
                expiry_hours=24,
            ),
        ]

        self.metrics_calculator = MetricsCalculator()
        self.telegram = TelegramAlerts() if self.enable_telegram else None
        self.scheduler = None

    async def run_all_strategies(self) -> List[Recommendation]:
        """Run all strategies and return recommendations"""
        all_recommendations = []

        logger.info("=" * 60)
        logger.info("PAPER TRADING - SIGNAL GENERATION")
        logger.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
        logger.info("=" * 60)

        for strategy in self.strategies:
            try:
                logger.info(f"Running {strategy.name}...")
                recommendations = await strategy.run()
                all_recommendations.extend(recommendations)

                # Send Telegram alerts for each recommendation (if strategy is enabled for alerts)
                if self.telegram and recommendations and strategy.name in self.ALERT_ENABLED_STRATEGIES:
                    for rec in recommendations:
                        message = rec.format_telegram_signal()
                        await self.telegram.send(message, AlertPriority.MEDIUM)
                        logger.info(f"Sent Telegram alert for {rec.symbol}")
                elif recommendations and strategy.name not in self.ALERT_ENABLED_STRATEGIES:
                    logger.info(f"Skipping Telegram alerts for {strategy.name} (disabled)")

            except Exception as e:
                logger.error(f"Error running {strategy.name}: {e}")

        logger.info(f"Total recommendations: {len(all_recommendations)}")
        return all_recommendations

    async def check_all_outcomes(self) -> List[Dict]:
        """Check outcomes for all strategies"""
        all_outcomes = []

        # Get current prices
        prices = await self._get_current_prices()
        if not prices:
            logger.warning("Could not fetch current prices")
            return []

        for strategy in self.strategies:
            try:
                outcomes = await strategy.check_outcomes(prices)
                all_outcomes.extend(outcomes)

                # Send Telegram alerts for outcomes (if strategy is enabled for alerts)
                if self.telegram and outcomes and strategy.name in self.ALERT_ENABLED_STRATEGIES:
                    for outcome in outcomes:
                        rec_data = outcome.get("recommendation", {})

                        # Reconstruct Recommendation for formatting
                        rec = Recommendation(
                            strategy_name=rec_data.get("strategy_name", ""),
                            symbol=rec_data.get("symbol", ""),
                            direction=rec_data.get("direction", ""),
                            entry_price=float(rec_data.get("entry_price", 0)),
                            target_price_1=float(rec_data.get("target_price_1", 0)),
                            stop_loss_price=float(rec_data.get("stop_loss_price", 0)),
                            confidence_score=int(rec_data.get("confidence_score", 0)),
                            expires_at=datetime.now(timezone.utc),
                            strategy_params=rec_data.get("strategy_params", {}),
                        )

                        message = rec.format_telegram_outcome(
                            outcome_type=outcome.get("outcome_type", ""),
                            exit_price=float(outcome.get("exit_price", 0)),
                            pnl_pct=float(outcome.get("pnl_pct", 0)),
                            pnl_amount=float(outcome.get("pnl_usd", 0)),
                            hold_duration_minutes=int(outcome.get("hold_duration_minutes", 0)),
                        )
                        await self.telegram.send(message, AlertPriority.HIGH)
                        logger.info(
                            f"Outcome: {rec_data.get('symbol')} -> {outcome.get('outcome_type')} "
                            f"({outcome.get('pnl_pct', 0):+.2f}%)"
                        )

            except Exception as e:
                logger.error(f"Error checking outcomes for {strategy.name}: {e}")

        return all_outcomes

    async def update_metrics(self):
        """Update strategy performance metrics"""
        try:
            logger.info("Updating metrics...")
            await self.metrics_calculator.calculate_all_metrics()
            logger.info("Metrics updated")
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    async def _get_current_prices(self) -> Dict[str, float]:
        """Get current prices for all symbols"""
        try:
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            meta_and_ctxs = info.meta_and_asset_ctxs()

            if not meta_and_ctxs or len(meta_and_ctxs) < 2:
                return {}

            meta = meta_and_ctxs[0]
            asset_ctxs = meta_and_ctxs[1]
            universe = meta.get("universe", [])

            prices = {}
            for i, asset in enumerate(universe):
                ticker = asset.get("name", f"UNKNOWN_{i}")
                ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}
                mark_price = float(ctx.get("markPx", 0))
                if mark_price > 0:
                    prices[ticker] = mark_price

            return prices

        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return {}

    async def run_once(self):
        """Run all tasks once"""
        await self.run_all_strategies()
        await self.check_all_outcomes()
        await self.update_metrics()

    async def get_status(self) -> Dict:
        """Get current status"""
        status = {
            "strategies": [],
            "telegram_enabled": self.enable_telegram,
            "scheduler_running": self.scheduler is not None and self.scheduler.running if self.scheduler else False,
        }

        for strategy in self.strategies:
            active = await strategy.get_active_recommendations()
            status["strategies"].append({
                "name": strategy.name,
                "active_recommendations": len(active),
            })

        return status

    async def generate_review(self) -> str:
        """Generate 24h review report"""
        review = await self.metrics_calculator.get_daily_review()
        return self.metrics_calculator.format_review_report(review)

    async def send_daily_review(self):
        """Send daily review to Telegram"""
        if not self.telegram:
            return

        try:
            report = await self.generate_review()
            await self.telegram.send(report, AlertPriority.LOW)
            logger.info("Daily review sent to Telegram")
        except Exception as e:
            logger.error(f"Error sending daily review: {e}")

    def start(self):
        """Start the scheduler"""
        if not HAS_APSCHEDULER:
            logger.error("APScheduler not installed. Install with: pip install apscheduler")
            return

        self.scheduler = AsyncIOScheduler()

        # Schedule signal generation every 15 minutes
        self.scheduler.add_job(
            self.run_all_strategies,
            IntervalTrigger(minutes=self.signal_interval),
            id="signal_generation",
            name="Generate trading signals",
            replace_existing=True,
        )

        # Schedule outcome checking every 5 minutes
        self.scheduler.add_job(
            self.check_all_outcomes,
            IntervalTrigger(minutes=self.outcome_check_interval),
            id="outcome_check",
            name="Check trade outcomes",
            replace_existing=True,
        )

        # Schedule metrics update every hour
        self.scheduler.add_job(
            self.update_metrics,
            IntervalTrigger(minutes=self.metrics_interval),
            id="metrics_update",
            name="Update metrics",
            replace_existing=True,
        )

        # Schedule daily review at midnight UTC
        self.scheduler.add_job(
            self.send_daily_review,
            "cron",
            hour=0,
            minute=0,
            id="daily_review",
            name="Send daily review",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Paper trading scheduler started")
        logger.info(f"  - Signals: every {self.signal_interval} minutes")
        logger.info(f"  - Outcomes: every {self.outcome_check_interval} minutes")
        logger.info(f"  - Metrics: every {self.metrics_interval} minutes")
        logger.info(f"  - Daily review: 00:00 UTC")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Paper Trading Scheduler")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--review", action="store_true", help="Generate 24h review and exit")
    parser.add_argument("--no-telegram", action="store_true", help="Disable Telegram alerts")
    args = parser.parse_args()

    scheduler = PaperTradingScheduler(
        enable_telegram=not args.no_telegram,
    )

    if args.status:
        status = await scheduler.get_status()
        print("\n=== PAPER TRADING STATUS ===")
        print(f"Telegram: {'Enabled' if status['telegram_enabled'] else 'Disabled'}")
        print(f"Scheduler: {'Running' if status['scheduler_running'] else 'Stopped'}")
        print("\nStrategies:")
        for s in status["strategies"]:
            print(f"  - {s['name']}: {s['active_recommendations']} active")
        return

    if args.review:
        report = await scheduler.generate_review()
        print("\n" + report)
        return

    if args.once:
        print("\nRunning paper trading cycle once...")
        await scheduler.run_once()
        print("\nDone!")
        return

    # Continuous mode
    if not HAS_APSCHEDULER:
        print("ERROR: APScheduler not installed")
        print("Install with: pip install apscheduler")
        sys.exit(1)

    print("\n=== PAPER TRADING SCHEDULER ===")
    print("Starting continuous operation...")
    print("Press Ctrl+C to stop\n")

    # Run initial cycle
    await scheduler.run_once()

    # Start scheduler
    scheduler.start()

    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
