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
- Interactive Plotly visualization with hover tooltips
- Cost attribution (Sharpe decomposition by cost component)
- Factor analysis (CAPM alpha/beta regression)
- Alpha correlation (cross-strategy diversification analysis)
- Genetic regression (factor research with gene formulas)
- Position bridge (backtest-to-live position sizing)
- Advanced hypothesis testing (bar permutation, marginal family tests)
- HFT feature extraction (microstructure signals)
- Amalgapha (multi-strategy QP portfolio optimizer)
"""

from .data_pipeline import HyperliquidDataPipeline
from .backtest_engine import QuantBacktester, QuantStrategy
from .performance_bridge import PerformanceAnalyzer
from .rate_limiter import RateLimiter
from .enhanced_metrics import EnhancedMetricsCalculator
from .visualization import QuantViz
from .cost_attribution import CostAttributionAnalyzer
from .factor_analysis import FactorAnalyzer
from .alpha_correlation import AlphaCorrelationAnalyzer
from .genetic_regression import FactorResearchEngine
from .position_bridge import LivePositionBridge
from .advanced_hypothesis import AdvancedHypothesisTester
from .hft_features import HFTFeatureExtractor
from .amalgapha import Amalgapha

__all__ = [
    # Core
    "HyperliquidDataPipeline",
    "QuantBacktester",
    "QuantStrategy",
    "PerformanceAnalyzer",
    "RateLimiter",
    "EnhancedMetricsCalculator",
    # Visualization
    "QuantViz",
    # Analytics
    "CostAttributionAnalyzer",
    "FactorAnalyzer",
    "AlphaCorrelationAnalyzer",
    "FactorResearchEngine",
    "LivePositionBridge",
    "AdvancedHypothesisTester",
    "HFTFeatureExtractor",
    # Portfolio optimization
    "Amalgapha",
]
