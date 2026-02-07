"""
Performance Analytics Bridge
==============================
Wraps quantpylib's performance metrics and hypothesis testing
for use with the paper trading system.

Replaces hand-rolled Sharpe/drawdown calculations with
battle-tested implementations from quantpylib.simulator.performance.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

try:
    from quantpylib.simulator.performance import performance_measures, cost_statistics
    from quantpylib.standards.intervals import Period
    HAS_QUANTPYLIB_PERF = True
except ImportError:
    HAS_QUANTPYLIB_PERF = False
    logger.info("quantpylib performance module not available - using built-in metrics")


class PerformanceAnalyzer:
    """
    Performance analytics using quantpylib's battle-tested metrics.

    Provides:
    - Sharpe ratio, Sortino ratio
    - Maximum drawdown, rolling drawdown
    - CAGR, Calmar ratio
    - VaR, CVaR (95%)
    - Omega ratio, Ulcer index
    - Gain-to-pain ratio
    - Skewness, kurtosis

    Falls back to built-in calculations when quantpylib is not available.
    """

    # Periods for crypto (24/7, 365 days)
    CRYPTO_PERIODS_HOURLY = 365 * 24   # 8760
    CRYPTO_PERIODS_DAILY = 365
    CRYPTO_PERIODS_MINUTE = 365 * 24 * 60

    def __init__(self, granularity: str = "hourly"):
        """
        Args:
            granularity: "minute", "hourly", or "daily"
        """
        self.granularity = granularity
        self.periods_in_year = {
            "minute": self.CRYPTO_PERIODS_MINUTE,
            "hourly": self.CRYPTO_PERIODS_HOURLY,
            "daily": self.CRYPTO_PERIODS_DAILY,
        }.get(granularity, self.CRYPTO_PERIODS_DAILY)

    def analyze_returns(
        self,
        returns: pd.Series,
        weights: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Compute comprehensive performance metrics from a return series.

        Args:
            returns: Time series of period returns (not cumulative)
            weights: Optional portfolio weights DataFrame

        Returns:
            Dict with all performance metrics
        """
        if HAS_QUANTPYLIB_PERF and weights is not None:
            return self._analyze_quantpylib(returns, weights)
        return self._analyze_builtin(returns)

    def _analyze_quantpylib(
        self, returns: pd.Series, weights: pd.DataFrame
    ) -> Dict[str, Any]:
        """Full analysis using quantpylib."""
        try:
            metrics = performance_measures(
                r=returns,
                w=weights,
                periods_in_year=self.periods_in_year,
                plot=False
            )
            # Extract scalar values from any Series in the result
            result = {}
            for key, value in metrics.items():
                if isinstance(value, pd.Series):
                    result[key] = float(value.iloc[-1])
                elif isinstance(value, (np.floating, np.integer)):
                    result[key] = float(value)
                elif isinstance(value, pd.DataFrame):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
            return result
        except Exception as e:
            logger.warning(f"quantpylib analysis failed, falling back: {e}")
            return self._analyze_builtin(returns)

    def _analyze_builtin(self, returns: pd.Series) -> Dict[str, Any]:
        """Built-in performance analysis (no quantpylib dependency)."""
        r = returns.dropna()

        if len(r) < 2:
            return self._empty_metrics()

        # Cumulative returns
        cum_ret = (1 + r).cumprod()
        log_ret = np.log(cum_ret)

        # Drawdown
        rolling_max = cum_ret.cummax()
        drawdown = (cum_ret - rolling_max) / rolling_max
        max_dd = float(drawdown.min())

        # Sharpe ratio
        mean_ret = float(r.mean())
        std_ret = float(r.std())
        sharpe = (mean_ret / std_ret * np.sqrt(self.periods_in_year)) if std_ret > 0 else 0

        # Sortino ratio
        downside = r[r < 0]
        downside_std = float(downside.std()) if len(downside) > 0 else 0
        sortino = (mean_ret / downside_std * np.sqrt(self.periods_in_year)) if downside_std > 0 else 0

        # CAGR
        total_periods = len(r)
        years = total_periods / self.periods_in_year
        total_return = float(cum_ret.iloc[-1])
        cagr = (total_return ** (1 / years) - 1) if years > 0 and total_return > 0 else 0

        # VaR and CVaR (95%)
        var_95 = float(np.percentile(r, 5))
        cvar_95 = float(r[r <= var_95].mean()) if len(r[r <= var_95]) > 0 else var_95

        # Omega ratio
        threshold = 0
        gains = r[r > threshold].sum()
        losses = abs(r[r <= threshold].sum())
        omega = float(gains / losses) if losses > 0 else float(gains) if gains > 0 else 0

        # Gain-to-pain ratio
        total_gain = float(r[r > 0].sum())
        total_loss = float(abs(r[r < 0].sum()))
        gain_to_pain = total_gain / total_loss if total_loss > 0 else total_gain

        # Win rate
        wins = (r > 0).sum()
        total = (r != 0).sum()
        win_rate = float(wins / total) if total > 0 else 0

        # Profit factor
        gross_profit = float(r[r > 0].sum())
        gross_loss = float(abs(r[r < 0].sum()))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit

        return {
            "cum_ret": float(cum_ret.iloc[-1]),
            "log_ret": float(log_ret.iloc[-1]) if len(log_ret) > 0 else 0,
            "max_dd": max_dd,
            "sharpe": round(sharpe, 4),
            "sortino": round(sortino, 4),
            "mean_ret": round(mean_ret * self.periods_in_year, 4),
            "stdev_ret": round(std_ret * np.sqrt(self.periods_in_year), 4),
            "skew_ret": round(float(r.skew()), 4),
            "kurt_exc": round(float(r.kurtosis()), 4),
            "cagr": round(cagr, 4),
            "omega": round(omega, 4),
            "VaR95": round(var_95, 6),
            "cVaR95": round(cvar_95, 6),
            "gain_to_pain": round(gain_to_pain, 4),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "total_trades": int(total),
            "total_periods": len(r),
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics dict."""
        return {
            "cum_ret": 1.0, "log_ret": 0, "max_dd": 0,
            "sharpe": 0, "sortino": 0, "mean_ret": 0,
            "stdev_ret": 0, "skew_ret": 0, "kurt_exc": 0,
            "cagr": 0, "omega": 0, "VaR95": 0, "cVaR95": 0,
            "gain_to_pain": 0, "win_rate": 0, "profit_factor": 0,
            "total_trades": 0, "total_periods": 0,
        }

    def compare_strategies(
        self,
        strategy_returns: Dict[str, pd.Series],
    ) -> pd.DataFrame:
        """
        Compare multiple strategies side-by-side.

        Args:
            strategy_returns: Dict of strategy_name -> return series

        Returns:
            DataFrame with metrics as rows, strategies as columns
        """
        results = {}
        for name, returns in strategy_returns.items():
            results[name] = self.analyze_returns(returns)

        df = pd.DataFrame(results)
        return df

    def cost_attribution(
        self,
        portfolio_df: pd.DataFrame,
    ) -> Dict[str, float]:
        """
        Shortcut to CostAttributionAnalyzer for Sharpe decomposition.

        Args:
            portfolio_df: DataFrame with capital_ret, comm_penalty, exec_penalty columns

        Returns:
            Dict with sharpe_costless, sharpe_costful, costdrag, etc.
        """
        from .cost_attribution import CostAttributionAnalyzer
        analyzer = CostAttributionAnalyzer(granularity=self.granularity)
        return analyzer.analyze(portfolio_df)

    def alpha_correlation(
        self,
        strategy_returns: Dict[str, pd.Series],
    ) -> Dict[str, Any]:
        """
        Shortcut to AlphaCorrelationAnalyzer for cross-strategy analysis.

        Args:
            strategy_returns: Dict of strategy_name -> return series

        Returns:
            Dict with corr_matrix, eigenvalues, diversification_ratio, clustered_pairs
        """
        from .alpha_correlation import AlphaCorrelationAnalyzer
        analyzer = AlphaCorrelationAnalyzer()
        return analyzer.compute(strategy_returns)

    @staticmethod
    def returns_from_pnl_records(
        records: List[Dict[str, Any]],
        position_size: float = 1000.0,
    ) -> pd.Series:
        """
        Convert paper trading outcome records into a return series.

        Args:
            records: List of outcome dicts with pnl_pct and outcome_time
            position_size: Base position size for weighting

        Returns:
            pd.Series of returns indexed by time
        """
        if not records:
            return pd.Series(dtype=float)

        data = []
        for r in records:
            pnl_pct = float(r.get("pnl_pct", 0)) / 100  # Convert from % to decimal
            timestamp = r.get("outcome_time") or r.get("created_at")
            if timestamp and pnl_pct != 0:
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp, utc=True)
                data.append({"time": timestamp, "return": pnl_pct})

        if not data:
            return pd.Series(dtype=float)

        df = pd.DataFrame(data).set_index("time").sort_index()
        return df["return"]
