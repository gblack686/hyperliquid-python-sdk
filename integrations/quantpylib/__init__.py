"""
QuantPyLib Integration Bridge
==============================
Bridges the quantpylib library into the hyperliquid-python-sdk ecosystem.

Provides:
- Enhanced backtesting via quantpylib.simulator.Alpha
- Async data pipeline via quantpylib DataPoller
- Rate limiting via quantpylib Throttler
- Performance metrics (Sharpe, drawdown, hypothesis testing)
- GeneticAlpha formula-based strategy discovery
- Enhanced metrics calculator with quantpylib analytics
"""

from .data_pipeline import HyperliquidDataPipeline
from .backtest_engine import QuantBacktester, QuantStrategy
from .performance_bridge import PerformanceAnalyzer
from .rate_limiter import RateLimiter
from .enhanced_metrics import EnhancedMetricsCalculator

__all__ = [
    "HyperliquidDataPipeline",
    "QuantBacktester",
    "QuantStrategy",
    "PerformanceAnalyzer",
    "RateLimiter",
    "EnhancedMetricsCalculator",
]
