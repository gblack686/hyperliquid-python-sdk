"""
Amalgapha - Multi-Strategy Portfolio Optimizer
================================================
Reimplements the commented-out Amalgapha from quantpylib's alpha.py
in the integration layer.

Uses cvxopt quadratic programming with Ledoit-Wolf covariance
shrinkage to compute optimal strategy allocations.

The optimizer minimizes: -r'w + (lambda/2) * w'Sigma*w
subject to: sum(w) = 1, w >= 0

Where:
    r = expected strategy returns
    w = strategy allocation weights
    Sigma = strategy return covariance matrix
    lambda = risk aversion coefficient
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from cvxopt import matrix, solvers
    solvers.options["show_progress"] = False
    HAS_CVXOPT = True
except ImportError:
    HAS_CVXOPT = False

try:
    from quantpylib.simulator.quant_popt import est_returns, est_covariance, ledoitwolf_cc
    HAS_QUANT_POPT = True
except ImportError:
    HAS_QUANT_POPT = False

from .visualization import QuantViz
from .alpha_correlation import AlphaCorrelationAnalyzer


class Amalgapha:
    """
    Multi-strategy portfolio optimizer using quadratic programming.

    Combines multiple backtested strategies into an optimal portfolio
    by solving a mean-variance optimization problem with:
    - Ledoit-Wolf shrinkage for robust covariance estimation
    - Configurable risk aversion
    - Rolling window optimization for time-varying allocations
    - Budget and non-negativity constraints

    Usage:
        # From backtest results
        amalg = Amalgapha.from_backtest_results(
            results_list=[result1, result2, result3],
            strategy_names=["momentum", "funding", "grid"],
        )
        output = amalg.optimize()

        # From Alpha instances
        amalg = Amalgapha(
            strategy_returns={"momentum": ret1, "funding": ret2},
            risk_aversion=0.5,
        )
        output = amalg.optimize()
    """

    def __init__(
        self,
        strategy_returns: Dict[str, pd.Series],
        risk_aversion: float = 1.0,
        return_estimator: str = "simple_mean",
        covariance_estimator: str = "ledwol_cc",
        rolling_window: Optional[int] = None,
        min_observations: int = 30,
    ):
        """
        Args:
            strategy_returns: Dict of strategy_name -> return series
            risk_aversion: Higher = more conservative (0.1-10.0 typical)
            return_estimator: "constant" or "simple_mean"
            covariance_estimator: "sample" or "ledwol_cc" (Ledoit-Wolf)
            rolling_window: If set, compute time-varying allocations
            min_observations: Minimum data points before optimization
        """
        self.strategy_returns = strategy_returns
        self.risk_aversion = risk_aversion
        self.return_estimator = return_estimator
        self.covariance_estimator = covariance_estimator
        self.rolling_window = rolling_window
        self.min_observations = min_observations
        self.strategy_names = list(strategy_returns.keys())
        self.n_strategies = len(self.strategy_names)

    @classmethod
    def from_backtest_results(
        cls,
        results_list: List[Dict[str, Any]],
        strategy_names: Optional[List[str]] = None,
        risk_aversion: float = 1.0,
        **kwargs,
    ) -> "Amalgapha":
        """
        Factory from QuantBacktester result dicts.

        Args:
            results_list: List of dicts from QuantBacktester.run_*()
            strategy_names: Optional names (otherwise uses formula/strategy_name)
            risk_aversion: Risk aversion coefficient
        """
        returns_dict = {}
        for i, result in enumerate(results_list):
            name = None
            if strategy_names and i < len(strategy_names):
                name = strategy_names[i]
            if not name:
                name = result.get("formula") or result.get("strategy_name") or f"strategy_{i}"

            pdf = result.get("portfolio_df")
            if pdf is not None and "capital_ret" in pdf.columns:
                returns_dict[name] = pdf["capital_ret"].dropna()
            elif pdf is not None and "capital" in pdf.columns:
                cap = pdf["capital"]
                returns_dict[name] = cap.pct_change().dropna()

        return cls(strategy_returns=returns_dict, risk_aversion=risk_aversion, **kwargs)

    @classmethod
    def from_alphas(
        cls,
        alpha_instances: List[Any],
        strategy_names: Optional[List[str]] = None,
        risk_aversion: float = 1.0,
        **kwargs,
    ) -> "Amalgapha":
        """
        Factory from backtested Alpha instances.

        Args:
            alpha_instances: List of backtested Alpha/QuantStrategy instances
            strategy_names: Optional names
            risk_aversion: Risk aversion coefficient
        """
        returns_dict = {}
        for i, alpha in enumerate(alpha_instances):
            name = strategy_names[i] if strategy_names and i < len(strategy_names) else f"alpha_{i}"
            if hasattr(alpha, "portfolio_df") and alpha.portfolio_df is not None:
                if "capital_ret" in alpha.portfolio_df.columns:
                    returns_dict[name] = alpha.portfolio_df["capital_ret"].dropna()
                elif "capital" in alpha.portfolio_df.columns:
                    cap = alpha.portfolio_df["capital"]
                    returns_dict[name] = cap.pct_change().dropna()

        return cls(strategy_returns=returns_dict, risk_aversion=risk_aversion, **kwargs)

    def optimize(self) -> Dict[str, Any]:
        """
        Run the portfolio optimization.

        Returns:
            Dict with:
            - strat_allocations: Dict of strategy -> weight
            - combined_returns: pd.Series of combined portfolio returns
            - combined_metrics: Dict of portfolio-level metrics
            - correlation_matrix: pd.DataFrame
            - allocations_over_time: pd.DataFrame (if rolling_window set)
        """
        if self.n_strategies < 2:
            return self._single_strategy()

        # Align returns
        ret_df = pd.DataFrame(self.strategy_returns)
        ret_df = ret_df.dropna(how="all").fillna(0)

        if len(ret_df) < self.min_observations:
            return self._equal_weight(ret_df)

        if self.rolling_window:
            return self._optimize_rolling(ret_df)
        return self._optimize_static(ret_df)

    def _optimize_static(self, ret_df: pd.DataFrame) -> Dict[str, Any]:
        """Single-period optimization over entire history."""
        weights = self._qp_solve(ret_df)

        if weights is None:
            return self._equal_weight(ret_df)

        alloc = {name: round(float(w), 4) for name, w in zip(self.strategy_names, weights)}
        combined_ret = (ret_df * weights).sum(axis=1)

        # Correlation analysis
        corr_analyzer = AlphaCorrelationAnalyzer()
        corr_result = corr_analyzer.compute(self.strategy_returns)

        return {
            "strat_allocations": alloc,
            "combined_returns": combined_ret,
            "combined_metrics": self._compute_metrics(combined_ret),
            "correlation_matrix": corr_result["corr_matrix"],
            "diversification_ratio": corr_result["diversification_ratio"],
            "individual_metrics": {
                name: self._compute_metrics(ret_df[name])
                for name in self.strategy_names
            },
            "risk_aversion": self.risk_aversion,
            "method": "qp_static",
        }

    def _optimize_rolling(self, ret_df: pd.DataFrame) -> Dict[str, Any]:
        """Rolling window optimization for time-varying allocations."""
        window = self.rolling_window
        n = len(ret_df)
        allocations = []

        for t in range(window, n):
            window_df = ret_df.iloc[t - window:t]
            # Filter strategies with too much missing data
            valid_frac = window_df.notna().mean()
            valid_cols = valid_frac[valid_frac > 0.5].index.tolist()

            if len(valid_cols) < 2:
                # Equal weight fallback
                w = np.ones(self.n_strategies) / self.n_strategies
            else:
                sub_df = window_df[valid_cols].fillna(0)
                w_sub = self._qp_solve(sub_df)

                if w_sub is None:
                    w_sub = np.ones(len(valid_cols)) / len(valid_cols)

                # Map back to full strategy vector
                w = np.zeros(self.n_strategies)
                for i, col in enumerate(valid_cols):
                    idx = self.strategy_names.index(col)
                    w[idx] = w_sub[i]

            allocations.append(w)

        alloc_df = pd.DataFrame(
            allocations,
            columns=self.strategy_names,
            index=ret_df.index[window:],
        )

        # Combined returns using time-varying weights
        combined_ret = (ret_df.iloc[window:] * alloc_df.values).sum(axis=1)

        # Final (latest) allocation
        final_alloc = {
            name: round(float(alloc_df[name].iloc[-1]), 4)
            for name in self.strategy_names
        }

        corr_analyzer = AlphaCorrelationAnalyzer()
        corr_result = corr_analyzer.compute(self.strategy_returns)

        return {
            "strat_allocations": final_alloc,
            "combined_returns": combined_ret,
            "combined_metrics": self._compute_metrics(combined_ret),
            "correlation_matrix": corr_result["corr_matrix"],
            "diversification_ratio": corr_result["diversification_ratio"],
            "allocations_over_time": alloc_df,
            "individual_metrics": {
                name: self._compute_metrics(ret_df[name])
                for name in self.strategy_names
            },
            "risk_aversion": self.risk_aversion,
            "method": "qp_rolling",
        }

    def _qp_solve(self, ret_df: pd.DataFrame) -> Optional[np.ndarray]:
        """
        Solve the QP optimization problem.

        Minimize: -r'w + (lambda/2) * w'Sigma*w
        Subject to: sum(w) = 1, w >= 0

        Standard form for cvxopt:
            min  (1/2) x'Px + q'x
            s.t. Gx <= h, Ax = b

        P = lambda * Sigma
        q = -r
        G = -I (non-negativity)
        h = 0
        A = 1' (budget)
        b = 1
        """
        n = ret_df.shape[1]
        returns_arr = ret_df.values  # T x N

        # Estimate returns and covariance
        r = self._estimate_returns(returns_arr)
        sigma = self._estimate_covariance(returns_arr)

        if r is None or sigma is None:
            return None

        if HAS_CVXOPT:
            return self._solve_cvxopt(r, sigma, n)
        return self._solve_analytical(r, sigma, n)

    def _solve_cvxopt(self, r: np.ndarray, sigma: np.ndarray, n: int) -> Optional[np.ndarray]:
        """Solve QP using cvxopt."""
        try:
            # Regularize covariance for numerical stability
            sigma = sigma + np.eye(n) * 1e-8

            P = matrix(self.risk_aversion * sigma, tc="d")
            q = matrix(-r, tc="d")

            # Inequality: -w <= 0 (non-negativity)
            G = matrix(-np.eye(n), tc="d")
            h = matrix(np.zeros(n), tc="d")

            # Equality: sum(w) = 1
            A = matrix(np.ones((1, n)), tc="d")
            b = matrix([1.0], tc="d")

            sol = solvers.qp(P, q, G, h, A, b)

            if sol["status"] != "optimal":
                logger.warning(f"QP solver status: {sol['status']}")
                return None

            weights = np.array(sol["x"]).flatten()
            # Clip numerical noise
            weights = np.maximum(weights, 0)
            weights = weights / weights.sum()
            return weights

        except Exception as e:
            logger.error(f"CVXOPT QP solve failed: {e}")
            return None

    def _solve_analytical(self, r: np.ndarray, sigma: np.ndarray, n: int) -> Optional[np.ndarray]:
        """
        Analytical fallback when cvxopt unavailable.
        Uses inverse-variance weighting (risk parity approximation).
        """
        try:
            var = np.diag(sigma)
            inv_var = 1.0 / np.maximum(var, 1e-10)
            weights = inv_var / inv_var.sum()
            return weights
        except Exception as e:
            logger.error(f"Analytical solve failed: {e}")
            return None

    def _estimate_returns(self, returns: np.ndarray) -> Optional[np.ndarray]:
        """Estimate expected returns."""
        if HAS_QUANT_POPT:
            try:
                ret_df = pd.DataFrame(returns)
                settings = {"type": self.return_estimator}
                return est_returns(ret_df, settings).values
            except Exception as e:
                logger.debug(f"quantpylib est_returns failed: {e}")

        # Builtin
        if self.return_estimator == "constant":
            mean_all = np.mean(returns)
            return np.full(returns.shape[1], mean_all)
        else:
            return np.mean(returns, axis=0)

    def _estimate_covariance(self, returns: np.ndarray) -> Optional[np.ndarray]:
        """Estimate covariance matrix (with optional Ledoit-Wolf shrinkage)."""
        if HAS_QUANT_POPT and self.covariance_estimator == "ledwol_cc":
            try:
                return ledoitwolf_cc(returns)
            except Exception as e:
                logger.debug(f"Ledoit-Wolf failed, using sample cov: {e}")

        # Builtin sample covariance
        try:
            return np.cov(returns.T)
        except Exception:
            return None

    def _single_strategy(self) -> Dict[str, Any]:
        """Handle single-strategy case (no optimization needed)."""
        name = self.strategy_names[0]
        ret = self.strategy_returns[name]
        return {
            "strat_allocations": {name: 1.0},
            "combined_returns": ret,
            "combined_metrics": self._compute_metrics(ret),
            "correlation_matrix": pd.DataFrame([[1.0]], index=[name], columns=[name]),
            "diversification_ratio": 1.0,
            "individual_metrics": {name: self._compute_metrics(ret)},
            "risk_aversion": self.risk_aversion,
            "method": "single",
        }

    def _equal_weight(self, ret_df: pd.DataFrame) -> Dict[str, Any]:
        """Fallback to equal-weight allocation."""
        n = self.n_strategies
        weights = np.ones(n) / n
        alloc = {name: round(1.0 / n, 4) for name in self.strategy_names}
        combined_ret = (ret_df * weights).sum(axis=1)

        return {
            "strat_allocations": alloc,
            "combined_returns": combined_ret,
            "combined_metrics": self._compute_metrics(combined_ret),
            "correlation_matrix": ret_df.corr(),
            "diversification_ratio": 1.0,
            "individual_metrics": {
                name: self._compute_metrics(ret_df[name])
                for name in self.strategy_names
            },
            "risk_aversion": self.risk_aversion,
            "method": "equal_weight_fallback",
        }

    @staticmethod
    def _compute_metrics(returns: pd.Series, periods: int = 8760) -> Dict[str, float]:
        """Compute basic metrics for a return series."""
        r = returns.dropna()
        if len(r) < 2:
            return {"sharpe": 0, "sortino": 0, "max_dd": 0, "cagr": 0, "total_return": 0}

        ann = np.sqrt(periods)
        mean_r = float(r.mean())
        std_r = float(r.std())
        sharpe = mean_r / std_r * ann if std_r > 0 else 0

        downside = r[r < 0]
        ds_std = float(downside.std()) if len(downside) > 0 else 0
        sortino = mean_r / ds_std * ann if ds_std > 0 else 0

        cum = (1 + r).cumprod()
        peak = cum.cummax()
        dd = (cum - peak) / peak
        max_dd = float(dd.min())

        total_return = float(cum.iloc[-1] - 1)
        years = len(r) / periods
        cagr = float((cum.iloc[-1]) ** (1 / years) - 1) if years > 0 and cum.iloc[-1] > 0 else 0

        return {
            "sharpe": round(sharpe, 4),
            "sortino": round(sortino, 4),
            "max_dd": round(max_dd, 4),
            "cagr": round(cagr, 4),
            "total_return": round(total_return, 4),
        }

    def format_report(self, results: Dict[str, Any]) -> str:
        """ASCII report of optimization results."""
        lines = [
            "=== AMALGAPHA PORTFOLIO OPTIMIZATION ===",
            f"  Method: {results.get('method', 'unknown')}",
            f"  Risk Aversion: {results['risk_aversion']}",
            "",
            "  Strategy Allocations:",
        ]

        for name, weight in results["strat_allocations"].items():
            bar = "#" * int(weight * 40)
            lines.append(f"    {name:<20} {weight:6.1%}  {bar}")

        lines.append("")
        lines.append("  Individual Performance:")
        lines.append(f"    {'Strategy':<20} {'Sharpe':>8} {'Sortino':>8} {'MaxDD':>8} {'Return':>8}")
        lines.append(f"    {'-'*56}")

        for name, metrics in results.get("individual_metrics", {}).items():
            lines.append(
                f"    {name:<20} {metrics.get('sharpe', 0):8.4f} "
                f"{metrics.get('sortino', 0):8.4f} "
                f"{metrics.get('max_dd', 0):8.2%} "
                f"{metrics.get('total_return', 0):8.2%}"
            )

        combined = results.get("combined_metrics", {})
        lines.append(f"    {'-'*56}")
        lines.append(
            f"    {'COMBINED':<20} {combined.get('sharpe', 0):8.4f} "
            f"{combined.get('sortino', 0):8.4f} "
            f"{combined.get('max_dd', 0):8.2%} "
            f"{combined.get('total_return', 0):8.2%}"
        )

        div = results.get("diversification_ratio", 0)
        lines.append("")
        lines.append(f"  Diversification Ratio: {div:.4f}")

        return "\n".join(lines)

    def plot(self, results: Dict[str, Any]) -> Any:
        """Plot allocation chart. Returns list of figures if rolling."""
        figs = []

        # Allocation chart
        if "allocations_over_time" in results:
            figs.append(QuantViz.amalgapha_allocation_chart(results["allocations_over_time"]))
        else:
            # Static allocation as single-row DataFrame
            alloc_df = pd.DataFrame(
                [results["strat_allocations"]],
                index=[pd.Timestamp.now()],
            )
            figs.append(QuantViz.amalgapha_allocation_chart(alloc_df))

        # Combined equity curve
        combined_ret = results.get("combined_returns")
        if combined_ret is not None:
            cum = (1 + combined_ret).cumprod() * 10000
            eq_df = pd.DataFrame({"capital": cum})
            figs.append(QuantViz.equity_curve(eq_df, title="Combined Portfolio Equity"))

        # Correlation heatmap
        corr = results.get("correlation_matrix")
        if corr is not None and len(corr) > 1:
            figs.append(QuantViz.correlation_heatmap(corr, title="Strategy Correlations"))

        return figs
