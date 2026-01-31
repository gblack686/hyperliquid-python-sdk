"""
Paper Trading System
====================
Simulated trading with multiple strategy agents for performance tracking.

Strategies:
- Funding Arbitrage: High funding = SHORT, Low funding = LONG
- Grid Trading: Range detection, buy low/sell high in range
- Directional Momentum: RSI, EMA crossover, volume confirmation

Usage:
    from scripts.paper_trading import PaperTradingScheduler
    scheduler = PaperTradingScheduler()
    scheduler.start()
"""

from .base_strategy import BaseStrategy, Recommendation, RecommendationStatus
from .scheduler import PaperTradingScheduler
from .metrics_calculator import MetricsCalculator

__all__ = [
    "BaseStrategy",
    "Recommendation",
    "RecommendationStatus",
    "PaperTradingScheduler",
    "MetricsCalculator",
]
