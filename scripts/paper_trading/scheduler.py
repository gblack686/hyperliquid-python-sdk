"""
Paper Trading Scheduler
=======================
Runs paper trading strategies on a schedule using APScheduler.

Usage:
    python -m scripts.paper_trading.scheduler

Or programmatically:
    from scripts.paper_trading.scheduler import PaperTradingScheduler
    scheduler = PaperTradingScheduler()
    scheduler.start()
"""

import os
import sys
import asyncio
import signal
from datetime import datetime, timedelta
from typing import List, Optional

from loguru import logger
from dotenv import load_dotenv

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    logger.warning("APScheduler not installed - run: pip install apscheduler")

from .base_strategy import BaseStrategy, Recommendation
from .metrics_calculator import MetricsCalculator
from .strategies import FundingStrategy, GridStrategy, DirectionalStrategy

# Optional Telegram integration
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from integrations.telegram.alerts import TelegramAlerts, AlertPriority
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    logger.info("Telegram integration not available")

load_dotenv()


class PaperTradingScheduler:
    """
    Scheduler for paper trading strategies.

    Runs strategies every 15 minutes, checks outcomes hourly,
    and generates daily review reports.
    """

    STRATEGY_NAMES = [
        "funding_arbitrage",
        "grid_trading",
        "directional_momentum"
    ]

    def __init__(
        self,
        signal_interval_minutes: int = 15,
        outcome_check_minutes: int = 15,
        metrics_update_minutes: int = 60,
        daily_review_hour: int = 0,  # UTC hour for daily review
        enable_telegram: bool = True
    ):
        """
        Initialize scheduler.

        Args:
            signal_interval_minutes: How often to run strategies
            outcome_check_minutes: How often to check for outcomes
            metrics_update_minutes: How often to update metrics
            daily_review_hour: UTC hour for daily review (0-23)
            enable_telegram: Whether to send Telegram alerts
        """
        if not HAS_APSCHEDULER:
            raise ImportError("APScheduler required - run: pip install apscheduler")

        self.signal_interval = signal_interval_minutes
        self.outcome_check_interval = outcome_check_minutes
        self.metrics_update_interval = metrics_update_minutes
        self.daily_review_hour = daily_review_hour

        # Initialize strategies
        self.strategies: List[BaseStrategy] = [
            FundingStrategy(
                min_funding_rate=0.01,
                max_signals_per_run=3
            ),
            GridStrategy(
                lookback_hours=24,
                max_signals_per_run=3
            ),
            DirectionalStrategy(
                min_score=60,
                max_signals_per_run=3
            )
        ]

        self.metrics_calculator = MetricsCalculator()
        self.scheduler = AsyncIOScheduler()

        # Telegram
        self.telegram: Optional[TelegramAlerts] = None
        if enable_telegram and HAS_TELEGRAM:
            self.telegram = TelegramAlerts()
            if not self.telegram.config.is_valid:
                logger.warning("Telegram not configured - alerts disabled")
                self.telegram = None

        self._running = False

    async def _run_strategies(self):
        """Run all strategies and generate signals"""
        logger.info("Running paper trading strategies...")

        for strategy in self.strategies:
            try:
                signals = await strategy.generate_signals()

                for signal in signals:
                    # Save to database
                    rec_id = strategy.save_recommendation(signal)

                    if rec_id:
                        signal.id = rec_id
                        logger.info(f"Saved signal: {signal.symbol} {signal.direction.value} (ID: {rec_id})")

                        # Send Telegram alert
                        if self.telegram:
                            try:
                                msg = signal.format_telegram_signal()
                                await self.telegram.send(msg, AlertPriority.MEDIUM)
                            except Exception as e:
                                logger.error(f"Telegram error: {e}")

            except Exception as e:
                logger.error(f"Error running {strategy.name}: {e}")

        logger.info("Strategy run complete")

    async def _check_outcomes(self):
        """Check active recommendations for outcomes"""
        logger.info("Checking for signal outcomes...")

        for strategy in self.strategies:
            try:
                outcomes = await strategy.check_outcomes()

                for outcome in outcomes:
                    rec = outcome["recommendation"]

                    logger.info(
                        f"Outcome: {rec.symbol} {outcome['outcome_type']} "
                        f"{outcome['pnl_pct']:+.2f}%"
                    )

                    # Send Telegram alert
                    if self.telegram:
                        try:
                            msg = rec.format_telegram_outcome(
                                outcome_type=outcome["outcome_type"],
                                exit_price=outcome["exit_price"],
                                pnl_pct=outcome["pnl_pct"],
                                duration_minutes=outcome["duration_minutes"]
                            )
                            priority = (
                                AlertPriority.HIGH
                                if abs(outcome["pnl_pct"]) > 2
                                else AlertPriority.MEDIUM
                            )
                            await self.telegram.send(msg, priority)
                        except Exception as e:
                            logger.error(f"Telegram error: {e}")

            except Exception as e:
                logger.error(f"Error checking outcomes for {strategy.name}: {e}")

        logger.info("Outcome check complete")

    async def _update_metrics(self):
        """Update strategy metrics"""
        logger.info("Updating strategy metrics...")

        try:
            self.metrics_calculator.update_all_metrics(self.STRATEGY_NAMES)
            logger.info("Metrics updated")
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    async def _daily_review(self):
        """Generate and send daily review"""
        logger.info("Generating daily review...")

        try:
            # Generate report
            report = self.metrics_calculator.format_review_report(
                self.STRATEGY_NAMES,
                period="24h"
            )

            logger.info(f"\n{report}")

            # Send to Telegram
            if self.telegram:
                telegram_summary = self.metrics_calculator.format_telegram_summary(
                    self.STRATEGY_NAMES,
                    period="24h"
                )
                await self.telegram.send(telegram_summary, AlertPriority.LOW)

        except Exception as e:
            logger.error(f"Error generating daily review: {e}")

    def start(self):
        """Start the scheduler"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting Paper Trading Scheduler")
        logger.info(f"  Signal generation: every {self.signal_interval} minutes")
        logger.info(f"  Outcome checks: every {self.outcome_check_interval} minutes")
        logger.info(f"  Metrics update: every {self.metrics_update_interval} minutes")
        logger.info(f"  Daily review: {self.daily_review_hour}:00 UTC")
        logger.info(f"  Telegram alerts: {'enabled' if self.telegram else 'disabled'}")

        # Schedule jobs
        self.scheduler.add_job(
            self._run_strategies,
            IntervalTrigger(minutes=self.signal_interval),
            id="run_strategies",
            name="Generate trading signals"
        )

        self.scheduler.add_job(
            self._check_outcomes,
            IntervalTrigger(minutes=self.outcome_check_interval),
            id="check_outcomes",
            name="Check signal outcomes"
        )

        self.scheduler.add_job(
            self._update_metrics,
            IntervalTrigger(minutes=self.metrics_update_interval),
            id="update_metrics",
            name="Update strategy metrics"
        )

        self.scheduler.add_job(
            self._daily_review,
            CronTrigger(hour=self.daily_review_hour, minute=0),
            id="daily_review",
            name="Daily performance review"
        )

        self._running = True
        self.scheduler.start()

    def stop(self):
        """Stop the scheduler"""
        if not self._running:
            return

        logger.info("Stopping Paper Trading Scheduler")
        self.scheduler.shutdown(wait=False)
        self._running = False

    async def run_once(self):
        """Run a single iteration (for testing)"""
        logger.info("Running single paper trading iteration...")

        await self._run_strategies()
        await self._check_outcomes()
        await self._update_metrics()

        logger.info("Single iteration complete")

    async def run_review(self, period: str = "24h"):
        """Run review report (for testing or on-demand)"""
        report = self.metrics_calculator.format_review_report(
            self.STRATEGY_NAMES,
            period=period
        )
        print(report)

        if self.telegram:
            telegram_summary = self.metrics_calculator.format_telegram_summary(
                self.STRATEGY_NAMES,
                period=period
            )
            await self.telegram.send(telegram_summary, AlertPriority.LOW)


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Paper Trading Scheduler")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single iteration and exit"
    )
    parser.add_argument(
        "--review",
        type=str,
        choices=["24h", "7d", "30d", "all_time"],
        help="Generate review report for period"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Signal generation interval in minutes (default: 15)"
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Disable Telegram alerts"
    )
    args = parser.parse_args()

    scheduler = PaperTradingScheduler(
        signal_interval_minutes=args.interval,
        enable_telegram=not args.no_telegram
    )

    if args.review:
        await scheduler.run_review(args.review)
        return

    if args.once:
        await scheduler.run_once()
        return

    # Run continuously
    scheduler.start()

    # Handle shutdown
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        logger.info("Shutdown signal received")
        scheduler.stop()
        loop.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    try:
        # Keep running
        while scheduler._running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
