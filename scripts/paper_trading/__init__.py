"""
Paper Trading System
====================
A paper trading system with multiple strategy agents that run every 15 minutes,
generate trade recommendations, and track accuracy over time.

Strategies:
- Funding Arbitrage: High funding = SHORT (collect), Low funding = LONG
- Grid Trading: Range detection, buy low/sell high in range
- Directional Momentum: RSI, EMA crossover, volume confirmation

Usage:
    # Run the scheduler
    python -m scripts.paper_trading.scheduler

    # Check status
    python -m scripts.paper_trading.scheduler --status

    # Run once manually
    python -m scripts.paper_trading.scheduler --once
"""

from .base_strategy import Recommendation, BaseStrategy, RecommendationStatus
from .metrics_calculator import MetricsCalculator

__all__ = [
    "Recommendation",
    "BaseStrategy",
    "RecommendationStatus",
    "MetricsCalculator",
]
