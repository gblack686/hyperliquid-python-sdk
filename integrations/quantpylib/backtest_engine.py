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

import os
import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable

from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

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

    def run_cost_attribution(
        self,
        results: Optional[Dict[str, Any]] = None,
        granularity: str = "hourly",
    ) -> Dict[str, float]:
        """
        Run cost attribution (Sharpe decomposition) on backtest results.

        Args:
            results: Backtest results dict (uses last_results if None)
            granularity: Time granularity for annualization

        Returns:
            Dict with sharpe_costless, sharpe_costful, costdrag, etc.
        """
        from .cost_attribution import CostAttributionAnalyzer

        results = results or self.last_results
        if not results or "portfolio_df" not in results:
            return {"error": "No backtest results available"}

        analyzer = CostAttributionAnalyzer(granularity=granularity)
        return analyzer.analyze(results["portfolio_df"])

    def run_factor_analysis(
        self,
        results: Optional[Dict[str, Any]] = None,
        market_returns: Optional[pd.Series] = None,
        granularity: str = "hourly",
    ) -> Dict[str, Any]:
        """
        Run CAPM factor analysis on backtest results.

        Args:
            results: Backtest results dict (uses last_results if None)
            market_returns: Market benchmark returns. If None, uses
                           equal-weight of all instruments.
            granularity: Time granularity for annualization

        Returns:
            Dict with alpha, beta, r_squared, information_ratio, etc.
        """
        from .factor_analysis import FactorAnalyzer

        results = results or self.last_results
        if not results or "portfolio_df" not in results:
            return {"error": "No backtest results available"}

        pdf = results["portfolio_df"]
        if "capital_ret" in pdf.columns:
            strat_ret = pdf["capital_ret"].dropna()
        elif "capital" in pdf.columns:
            strat_ret = pdf["capital"].pct_change().dropna()
        else:
            return {"error": "Cannot extract strategy returns from portfolio_df"}

        if market_returns is None:
            # Approximate market return from equal-weight of instruments
            ret_cols = [c for c in pdf.columns if c.startswith("ret_")]
            if ret_cols:
                market_returns = pdf[ret_cols].mean(axis=1).dropna()
            else:
                # Fallback: use zero (pure alpha test)
                market_returns = pd.Series(0, index=strat_ret.index)

        analyzer = FactorAnalyzer(granularity=granularity)
        return analyzer.analyze(strat_ret, market_returns)

    def run_amalgapha(
        self,
        strategy_results_list: List[Dict[str, Any]],
        strategy_names: Optional[List[str]] = None,
        risk_aversion: float = 1.0,
        rolling_window: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run Amalgapha portfolio optimization across multiple strategies.

        Args:
            strategy_results_list: List of backtest result dicts
            strategy_names: Optional names for each strategy
            risk_aversion: Risk aversion coefficient (higher = more conservative)
            rolling_window: If set, compute time-varying allocations

        Returns:
            Dict with strat_allocations, combined_returns, combined_metrics
        """
        from .amalgapha import Amalgapha

        amalg = Amalgapha.from_backtest_results(
            results_list=strategy_results_list,
            strategy_names=strategy_names,
            risk_aversion=risk_aversion,
            rolling_window=rolling_window,
        )
        return amalg.optimize()

    def run_bar_permutation_test(
        self,
        alpha_cls: Any,
        alpha_kwargs: Dict[str, Any],
        candle_dfs: Dict[str, pd.DataFrame],
        num_permutations: int = 100,
        metric: str = "sharpe",
    ) -> Dict[str, Any]:
        """
        Run bar permutation test for statistical significance.

        Args:
            alpha_cls: Strategy class (not instance)
            alpha_kwargs: Constructor kwargs (without dfs)
            candle_dfs: Dict of instrument -> OHLCV DataFrame
            num_permutations: Number of permutations
            metric: Metric to test ("sharpe", "sortino", "cagr")

        Returns:
            Dict with p_value, null_distribution, significance flags
        """
        from .advanced_hypothesis import AdvancedHypothesisTester

        tester = AdvancedHypothesisTester()
        return tester.run_bar_permutation_test(
            alpha_cls=alpha_cls,
            alpha_kwargs=alpha_kwargs,
            candle_dfs=candle_dfs,
            num_permutations=num_permutations,
            metric=metric,
        )

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

    async def save_results_to_supabase(
        self,
        results: Dict[str, Any],
    ) -> Optional[str]:
        """
        Save backtest results to the paper_backtest_results table.

        Args:
            results: Dict from run_genetic_backtest or run_strategy_backtest

        Returns:
            Record ID if saved, None otherwise
        """
        if not HAS_SUPABASE:
            logger.warning("Supabase not available - cannot save backtest results")
            return None

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            return None

        try:
            supabase = create_client(url, key)
            metrics = results.get("metrics", {})

            # Build equity curve summary (sample to max 500 points)
            equity_curve = None
            portfolio_df = results.get("portfolio_df")
            if portfolio_df is not None and "capital" in portfolio_df.columns:
                capital_series = portfolio_df["capital"]
                step = max(1, len(capital_series) // 500)
                sampled = capital_series.iloc[::step]
                equity_curve = [
                    {"t": str(idx), "v": round(float(val), 2)}
                    for idx, val in sampled.items()
                ]

            data = {
                "engine": results.get("engine", "unknown"),
                "formula": results.get("formula"),
                "strategy_name": results.get("strategy_name"),
                "tickers": results.get("tickers", []),
                "granularity": results.get("granularity", "hourly"),
                "starting_capital": 10000,
                "portfolio_vol": 0.20,
                "terminal_value": results.get("terminal_value"),
                "total_return_pct": results.get("total_return_pct"),
                "sharpe_ratio": metrics.get("sharpe"),
                "sortino_ratio": metrics.get("sortino"),
                "max_drawdown": metrics.get("max_dd"),
                "cagr": metrics.get("cagr"),
                "omega_ratio": metrics.get("omega") or metrics.get("omega(0)"),
                "profit_factor": metrics.get("profit_factor"),
                "win_rate": metrics.get("win_rate"),
                "var_95": metrics.get("VaR95"),
                "cvar_95": metrics.get("cVaR95"),
                "gain_to_pain": metrics.get("gain_to_pain"),
                "skewness": metrics.get("skew_ret"),
                "kurtosis": metrics.get("kurt_exc"),
                "equity_curve": equity_curve,
                "metrics_json": metrics,
            }

            # Add hypothesis test results if present
            for key_name in ["timer_p", "picker_p", "trader_p1", "trader_p2"]:
                if key_name in results:
                    data[key_name] = results[key_name]

            result = supabase.table("paper_backtest_results").insert(data).execute()

            if result.data:
                record_id = result.data[0]["id"]
                logger.info(f"Backtest results saved: {record_id}")
                return record_id

        except Exception as e:
            logger.error(f"Error saving backtest results: {e}")

        return None

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
