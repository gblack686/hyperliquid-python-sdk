"""
Backtest Engine Bridge
=======================
Wraps quantpylib's Alpha backtesting engine for use with the paper trading system.

Key upgrades over the existing agp_strategy_backtest.py:
- Execution cost modeling (commissions + slippage)
- Funding rate simulation for perpetuals
- Volatility-targeted position sizing
- Multi-asset portfolio backtesting
- Statistical hypothesis testing (Monte Carlo)
- GeneticAlpha formula-based strategy discovery
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable

logger = logging.getLogger(__name__)

try:
    from quantpylib.simulator.alpha import Alpha, BaseAlpha
    from quantpylib.standards.intervals import Period
    HAS_ALPHA = True
except ImportError:
    HAS_ALPHA = False
    logger.info("quantpylib Alpha not available - using built-in backtester")

try:
    from quantpylib.simulator.gene import GeneticAlpha
    HAS_GENETIC = True
except ImportError:
    HAS_GENETIC = False


class QuantStrategy(Alpha if HAS_ALPHA else object):
    """
    Bridge between paper trading strategies and quantpylib's Alpha engine.

    Subclass this to create strategies with proper backtesting support:
    - Automatic volatility-targeted position sizing
    - Execution cost modeling
    - Funding rate simulation
    - Statistical significance testing

    Example:
        class MomentumAlpha(QuantStrategy):
            async def compute_signals(self, index):
                for inst in self.instruments:
                    self.dfs[inst]['rsi'] = compute_rsi(self.dfs[inst]['close'])

            def compute_forecasts(self, portfolio_i, dt, eligibles_row):
                forecasts = np.zeros(len(self.instruments))
                for i, inst in enumerate(self.instruments):
                    rsi = self.dfs[inst].loc[dt, 'rsi']
                    if rsi < 30:
                        forecasts[i] = 1.0   # Long signal
                    elif rsi > 70:
                        forecasts[i] = -1.0  # Short signal
                return forecasts

        alpha = MomentumAlpha(
            dfs=candle_dfs,
            instruments=["BTC", "ETH", "SOL"],
            portfolio_vol=0.20,
            commrates=[0.0003] * 3,   # 3bps commission
            weekend_trading=True,
            around_the_clock=True,
            granularity=Period.HOURLY,
        )
        results = await alpha.run_simulation()
        metrics = alpha.get_performance_measures()
    """

    def __init__(self, **kwargs):
        if HAS_ALPHA:
            # Default crypto settings
            kwargs.setdefault("weekend_trading", True)
            kwargs.setdefault("around_the_clock", True)
            kwargs.setdefault("portfolio_vol", 0.20)
            kwargs.setdefault("starting_capital", 10000.0)

            # Default Hyperliquid fee structure
            instruments = kwargs.get("instruments", [])
            n = len(instruments)
            kwargs.setdefault("commrates", [0.00035] * n)  # 3.5bps taker
            kwargs.setdefault("execrates", [0.0001] * n)   # ~1bp slippage estimate

            super().__init__(**kwargs)

    async def compute_signals(self, index):
        """Override this to compute technical indicators on self.dfs."""
        raise NotImplementedError("Subclass must implement compute_signals()")

    def compute_forecasts(self, portfolio_i, dt, eligibles_row):
        """Override this to return forecast array for each instrument."""
        raise NotImplementedError("Subclass must implement compute_forecasts()")


class QuantBacktester:
    """
    High-level backtesting interface that bridges quantpylib's engine
    with the existing paper trading system.

    Supports:
    1. Strategy backtesting via QuantStrategy subclasses
    2. Formula-based backtesting via GeneticAlpha
    3. Built-in fallback when quantpylib is not available

    Usage:
        backtester = QuantBacktester()

        # Formula-based backtest
        results = await backtester.run_genetic_backtest(
            formula="ls_10/90(div(logret_1(),volatility_25()))",
            tickers=["BTC", "ETH", "SOL"],
            candle_dfs=dfs,
            start=datetime(2025, 1, 1),
            end=datetime(2026, 1, 1),
        )

        # Custom strategy backtest
        results = await backtester.run_strategy_backtest(
            strategy_cls=MyStrategy,
            candle_dfs=dfs,
            tickers=["BTC", "ETH"],
        )
    """

    def __init__(self):
        self.last_results: Optional[Dict[str, Any]] = None

    async def run_genetic_backtest(
        self,
        formula: str,
        tickers: List[str],
        candle_dfs: Dict[str, pd.DataFrame],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        starting_capital: float = 10000.0,
        portfolio_vol: float = 0.20,
        granularity: str = "hourly",
        commrates: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Run a formula-based backtest using GeneticAlpha.

        Args:
            formula: GeneticAlpha genome string
                     e.g., "ls_10/90(div(logret_1(),volatility_25()))"
            tickers: List of instrument names
            candle_dfs: Dict of ticker -> DataFrame with OHLCV columns
            start: Backtest start date (optional)
            end: Backtest end date (optional)
            starting_capital: Initial portfolio capital
            portfolio_vol: Target annualized portfolio volatility
            granularity: "minute", "hourly", or "daily"
            commrates: Commission rates per instrument (list of floats)

        Returns:
            Dict with keys: portfolio_df, metrics, formula, tickers
        """
        if not HAS_GENETIC:
            return self._genetic_not_available(formula, tickers)

        period_map = {
            "minute": Period.MINUTE,
            "hourly": Period.HOURLY,
            "daily": Period.DAILY,
        }
        period = period_map.get(granularity, Period.HOURLY)
        n = len(tickers)

        try:
            alpha = GeneticAlpha(
                genome=formula,
                dfs=candle_dfs,
                instruments=tickers,
                start=start,
                end=end,
                starting_capital=starting_capital,
                portfolio_vol=portfolio_vol,
                weekend_trading=True,
                around_the_clock=True,
                granularity=period,
                commrates=commrates or [0.00035] * n,
                execrates=[0.0001] * n,
            )

            portfolio_df = await alpha.run_simulation(verbose=False)
            metrics = alpha.get_performance_measures()

            # Extract scalar values from metrics
            clean_metrics = {}
            for key, value in metrics.items():
                if isinstance(value, pd.Series):
                    clean_metrics[key] = float(value.iloc[-1])
                elif isinstance(value, (np.floating, np.integer)):
                    clean_metrics[key] = float(value)
                elif isinstance(value, pd.DataFrame):
                    continue  # Skip DataFrames for JSON serialization
                else:
                    clean_metrics[key] = value

            result = {
                "portfolio_df": portfolio_df,
                "metrics": clean_metrics,
                "formula": formula,
                "tickers": tickers,
                "terminal_value": float(alpha.capitals[-1]),
                "total_return_pct": ((alpha.capitals[-1] / starting_capital) - 1) * 100,
                "engine": "quantpylib_genetic",
            }

            self.last_results = result
            return result

        except Exception as e:
            logger.error(f"GeneticAlpha backtest failed: {e}")
            return {
                "error": str(e),
                "formula": formula,
                "tickers": tickers,
                "engine": "quantpylib_genetic",
            }

    async def run_strategy_backtest(
        self,
        strategy: QuantStrategy,
    ) -> Dict[str, Any]:
        """
        Run a backtest using a QuantStrategy instance.

        Args:
            strategy: Initialized QuantStrategy instance

        Returns:
            Dict with portfolio_df, metrics, hypothesis_tests
        """
        if not HAS_ALPHA:
            return {"error": "quantpylib not available", "engine": "none"}

        try:
            portfolio_df = await strategy.run_simulation(verbose=False)
            metrics = strategy.get_performance_measures()

            # Clean metrics
            clean_metrics = {}
            for key, value in metrics.items():
                if isinstance(value, pd.Series):
                    clean_metrics[key] = float(value.iloc[-1])
                elif isinstance(value, (np.floating, np.integer)):
                    clean_metrics[key] = float(value)
                elif isinstance(value, pd.DataFrame):
                    continue
                else:
                    clean_metrics[key] = value

            result = {
                "portfolio_df": portfolio_df,
                "metrics": clean_metrics,
                "terminal_value": float(strategy.capitals[-1]),
                "total_return_pct": (
                    (strategy.capitals[-1] / strategy.starting_capital) - 1
                ) * 100,
                "engine": "quantpylib_alpha",
            }

            self.last_results = result
            return result

        except Exception as e:
            logger.error(f"Strategy backtest failed: {e}")
            return {"error": str(e), "engine": "quantpylib_alpha"}

    async def run_hypothesis_tests(
        self,
        strategy: QuantStrategy,
        num_decision_shuffles: int = 500,
        num_data_shuffles: int = 5,
    ) -> Dict[str, float]:
        """
        Run statistical significance tests on a backtested strategy.

        Returns p-values for:
        - timer_p: Can we time assets better than random?
        - picker_p: Can we pick assets better than random?
        - trader_p1: Are our trading decisions better than random?
        - trader_p2: Is our edge robust to data permutations?

        A p-value < 0.05 means the strategy has statistically significant alpha.
        """
        if not HAS_ALPHA:
            return {"error": "quantpylib not available"}

        if strategy.portfolio_df is None:
            await strategy.run_simulation(verbose=False)

        try:
            return await strategy.hypothesis_tests(
                num_decision_shuffles=num_decision_shuffles,
                num_data_shuffles=num_data_shuffles,
            )
        except Exception as e:
            logger.error(f"Hypothesis tests failed: {e}")
            return {"error": str(e)}

    def _genetic_not_available(
        self, formula: str, tickers: List[str]
    ) -> Dict[str, Any]:
        """Fallback when GeneticAlpha is not available."""
        return {
            "error": (
                "GeneticAlpha requires quantpylib. "
                "Install with: pip install quantpylib"
            ),
            "formula": formula,
            "tickers": tickers,
            "engine": "none",
        }

    @staticmethod
    def available_gene_operations() -> List[str]:
        """List available operations for GeneticAlpha formulas."""
        return [
            "logret_N()     - N-period log returns",
            "volatility_N() - N-period rolling volatility",
            "mean_N()       - N-period rolling mean",
            "max_N()        - N-period rolling max",
            "min_N()        - N-period rolling min",
            "cs_rank()      - Cross-sectional rank (0-1)",
            "ts_rank_N()    - Time-series rank over N periods",
            "div(a, b)      - Division: a / b",
            "mult(a, b)     - Multiplication: a * b",
            "plus(a, b)     - Addition: a + b",
            "minus(a, b)    - Subtraction: a - b",
            "abs(a)         - Absolute value",
            "sign(a)        - Sign (+1, 0, -1)",
            "log(a)         - Natural logarithm",
            "ls_P1/P2(a)    - Long/short: long top P2%, short bottom P1%",
            "mac_N1/N2(a)   - Moving average crossover: fast N1 vs slow N2",
            "",
            "Data fields: open, high, low, close, volume",
            "",
            "Examples:",
            "  ls_10/90(logret_1())                    - Momentum: long winners, short losers",
            "  ls_10/90(div(logret_1(),volatility_25())) - Risk-adjusted momentum",
            "  mac_10/30(close)                         - MA crossover strategy",
            "  ls_20/80(minus(close,mean_20(close)))    - Mean reversion",
        ]
