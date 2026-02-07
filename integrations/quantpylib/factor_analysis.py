"""
Factor Analysis
================
CAPM regression: R_strategy = alpha + beta * R_market + epsilon.
Quantifies systematic vs idiosyncratic risk contribution.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

from .visualization import QuantViz


class FactorAnalyzer:
    """
    Single-factor (CAPM) regression for strategy returns.

    Decomposes strategy returns into:
    - alpha: Excess return not explained by market
    - beta: Sensitivity to market returns
    - r_squared: Fraction of variance explained by market
    - information_ratio: alpha / residual_std (annualized)
    """

    PERIODS = {"minute": 525600, "hourly": 8760, "daily": 365}

    def __init__(self, granularity: str = "hourly"):
        self.periods_in_year = self.PERIODS.get(granularity, 8760)

    def analyze(
        self,
        strategy_returns: pd.Series,
        market_returns: pd.Series,
    ) -> Dict[str, Any]:
        """
        Run CAPM regression.

        Args:
            strategy_returns: Period returns of the strategy
            market_returns: Period returns of the market (benchmark)

        Returns:
            Dict with alpha, beta, r_squared, alpha_tstat, alpha_pvalue,
            information_ratio, residual_std, strategy_returns, market_returns
        """
        # Align on common index
        common = strategy_returns.dropna().index.intersection(market_returns.dropna().index)
        if len(common) < 10:
            return self._empty(strategy_returns, market_returns)

        y = strategy_returns.loc[common].values
        x = market_returns.loc[common].values

        if HAS_STATSMODELS:
            return self._ols_statsmodels(y, x, strategy_returns.loc[common], market_returns.loc[common])
        return self._ols_builtin(y, x, strategy_returns.loc[common], market_returns.loc[common])

    def _ols_statsmodels(
        self, y: np.ndarray, x: np.ndarray,
        strat_s: pd.Series, mkt_s: pd.Series,
    ) -> Dict[str, Any]:
        """OLS via statsmodels."""
        X = sm.add_constant(x)
        model = sm.OLS(y, X).fit()

        alpha = float(model.params[0])
        beta = float(model.params[1])
        residual_std = float(model.resid.std())
        ann = np.sqrt(self.periods_in_year)

        return {
            "alpha": alpha,
            "alpha_annualized": alpha * self.periods_in_year,
            "beta": beta,
            "r_squared": float(model.rsquared),
            "adj_r_squared": float(model.rsquared_adj),
            "alpha_tstat": float(model.tvalues[0]),
            "alpha_pvalue": float(model.pvalues[0]),
            "beta_tstat": float(model.tvalues[1]),
            "beta_pvalue": float(model.pvalues[1]),
            "residual_std": residual_std,
            "information_ratio": round(alpha / residual_std * ann, 4) if residual_std > 0 else 0,
            "f_statistic": float(model.fvalue) if model.fvalue is not None else 0,
            "f_pvalue": float(model.f_pvalue) if model.f_pvalue is not None else 1,
            "nobs": int(model.nobs),
            "strategy_returns": strat_s,
            "market_returns": mkt_s,
        }

    def _ols_builtin(
        self, y: np.ndarray, x: np.ndarray,
        strat_s: pd.Series, mkt_s: pd.Series,
    ) -> Dict[str, Any]:
        """Manual OLS when statsmodels unavailable."""
        n = len(y)
        x_mean = x.mean()
        y_mean = y.mean()

        beta = float(np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2))
        alpha = float(y_mean - beta * x_mean)

        y_hat = alpha + beta * x
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0

        residual_std = float(np.sqrt(ss_res / max(n - 2, 1)))
        ann = np.sqrt(self.periods_in_year)

        # t-statistics
        se_alpha = residual_std * np.sqrt(1 / n + x_mean ** 2 / np.sum((x - x_mean) ** 2))
        se_beta = residual_std / np.sqrt(np.sum((x - x_mean) ** 2))
        t_alpha = alpha / se_alpha if se_alpha > 0 else 0
        t_beta = beta / se_beta if se_beta > 0 else 0

        return {
            "alpha": alpha,
            "alpha_annualized": alpha * self.periods_in_year,
            "beta": beta,
            "r_squared": r_squared,
            "adj_r_squared": 1 - (1 - r_squared) * (n - 1) / max(n - 2, 1),
            "alpha_tstat": float(t_alpha),
            "alpha_pvalue": None,  # would need scipy
            "beta_tstat": float(t_beta),
            "beta_pvalue": None,
            "residual_std": residual_std,
            "information_ratio": round(alpha / residual_std * ann, 4) if residual_std > 0 else 0,
            "f_statistic": float(t_beta ** 2),
            "f_pvalue": None,
            "nobs": n,
            "strategy_returns": strat_s,
            "market_returns": mkt_s,
        }

    def _empty(self, strat_s, mkt_s) -> Dict[str, Any]:
        return {
            "alpha": 0, "alpha_annualized": 0, "beta": 0,
            "r_squared": 0, "adj_r_squared": 0,
            "alpha_tstat": 0, "alpha_pvalue": 1,
            "beta_tstat": 0, "beta_pvalue": 1,
            "residual_std": 0, "information_ratio": 0,
            "f_statistic": 0, "f_pvalue": 1, "nobs": 0,
            "strategy_returns": strat_s, "market_returns": mkt_s,
        }

    def format_report(self, data: Dict[str, Any]) -> str:
        """ASCII report."""
        lines = [
            "=== FACTOR ANALYSIS (CAPM) ===",
            "",
            f"  Alpha (per period):   {data['alpha']:.6f}",
            f"  Alpha (annualized):   {data['alpha_annualized']:.4f}",
            f"  Beta:                 {data['beta']:.4f}",
            f"  R-squared:            {data['r_squared']:.4f}",
            f"  Adj R-squared:        {data['adj_r_squared']:.4f}",
            "",
            f"  Alpha t-stat:         {data['alpha_tstat']:.3f}",
            f"  Alpha p-value:        {data.get('alpha_pvalue', 'N/A')}",
            f"  Information Ratio:    {data['information_ratio']:.4f}",
            "",
            f"  Observations:         {data['nobs']}",
        ]
        return "\n".join(lines)

    def plot(self, results: Dict[str, Any]) -> Any:
        """Plotly factor exposure chart."""
        return QuantViz.factor_exposure_chart(results)
