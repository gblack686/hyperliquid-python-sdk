#!/usr/bin/env python3
"""
Run Paper Trading - Single Iteration
====================================
Run all strategies once and output results.

Usage:
    python -m scripts.paper_trading.run_once
    python -m scripts.paper_trading.run_once --strategy funding
    python -m scripts.paper_trading.run_once --dry-run
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime

from loguru import logger
from dotenv import load_dotenv

from .strategies import FundingStrategy, GridStrategy, DirectionalStrategy
from .base_strategy import Recommendation

load_dotenv()


async def run_strategy(strategy, dry_run: bool = False):
    """Run a single strategy"""
    print(f"\n{'='*60}")
    print(f"Running: {strategy.name}")
    print(f"{'='*60}")

    signals = await strategy.generate_signals()

    if not signals:
        print("No signals generated")
        return []

    print(f"\nGenerated {len(signals)} signals:\n")

    for signal in signals:
        print(f"  {signal.symbol} {signal.direction.value}")
        print(f"    Entry: ${signal.entry_price:,.4f}")
        if signal.target_price_1:
            pct = ((signal.target_price_1 - signal.entry_price) / signal.entry_price) * 100
            if signal.direction.value == "SHORT":
                pct = -pct
            print(f"    Target: ${signal.target_price_1:,.4f} ({pct:+.1f}%)")
        if signal.stop_loss_price:
            pct = ((signal.stop_loss_price - signal.entry_price) / signal.entry_price) * 100
            if signal.direction.value == "SHORT":
                pct = -pct
            print(f"    Stop: ${signal.stop_loss_price:,.4f} ({pct:+.1f}%)")
        print(f"    Confidence: {signal.confidence_score}/100")
        if signal.notes:
            print(f"    Notes: {signal.notes}")
        print()

        if not dry_run:
            rec_id = strategy.save_recommendation(signal)
            if rec_id:
                print(f"    Saved to DB: {rec_id}")
            else:
                print("    (Not saved - Supabase not configured)")

    return signals


async def main():
    parser = argparse.ArgumentParser(description="Run paper trading strategies")
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["funding", "grid", "directional", "all"],
        default="all",
        help="Strategy to run (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate signals without saving to database"
    )
    args = parser.parse_args()

    print(f"Paper Trading - Single Run")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'Dry Run' if args.dry_run else 'Live (saves to DB)'}")

    strategies = []

    if args.strategy in ["funding", "all"]:
        strategies.append(FundingStrategy(
            min_funding_rate=0.01,
            max_signals_per_run=3
        ))

    if args.strategy in ["grid", "all"]:
        strategies.append(GridStrategy(
            lookback_hours=24,
            max_signals_per_run=3
        ))

    if args.strategy in ["directional", "all"]:
        strategies.append(DirectionalStrategy(
            min_score=60,
            max_signals_per_run=3
        ))

    all_signals = []
    for strategy in strategies:
        try:
            signals = await run_strategy(strategy, args.dry_run)
            all_signals.extend(signals)
        except Exception as e:
            logger.error(f"Error running {strategy.name}: {e}")

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total signals generated: {len(all_signals)}")

    by_direction = {"LONG": 0, "SHORT": 0}
    for signal in all_signals:
        by_direction[signal.direction.value] = by_direction.get(signal.direction.value, 0) + 1

    print(f"  LONG: {by_direction.get('LONG', 0)}")
    print(f"  SHORT: {by_direction.get('SHORT', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
