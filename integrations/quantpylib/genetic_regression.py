"""
Genetic Regression Engine
===========================
Wraps quantpylib's GeneticRegression for factor research.
Uses gene formula syntax for flexible factor construction and OLS regression.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

try:
    from quantpylib.simulator.models import GeneticRegression
    HAS_GENETIC_REG = True
except ImportError:
    HAS_GENETIC_REG = False

from .visualization import QuantViz


class FactorResearchEngine:
    """
    Factor research using gene-expression formulas and OLS regression.

    Formula syntax (gene expressions):
        dependent ~ independent1 + independent2 + ...

    Gene operations:
        logret_N()       - N-period log returns
        volatility_N()   - N-period rolling volatility
        mean_N()         - N-period rolling mean
        forward_N()      - N-period forward returns (target)
        div(a, b)        - Division
        mult(a, b)       - Multiplication
        plus(a, b)       - Addition
        minus(a, b)      - Subtraction
        abs(a)           - Absolute value
        sign(a)          - Sign function
        cs_rank()        - Cross-sectional rank
        ts_rank_N()      - Time-series rank
        tsargmax_N()     - Time-series argmax

    Example:
        engine = FactorResearchEngine()
        results = engine.run_regression(
            formula="forward_1(logret_1()) ~ div(logret_25(),volatility_25())",
            candle_dfs={"BTC": btc_df, "ETH": eth_df},
            instruments=["BTC", "ETH"],
        )
    """

    def run_regression(
        self,
        formula: str,
        candle_dfs: Dict[str, pd.DataFrame],
        instruments: List[str],
        axis: str = "flatten",
        bins: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run a gene-formula regression.

        Args:
            formula: Gene expression formula (e.g. "forward_1(logret_1()) ~ volatility_25()")
            candle_dfs: Dict of instrument -> DataFrame with OHLCV columns
            instruments: List of instrument names
            axis: OLS axis - "flatten" (pool all), "xs" (cross-section), "ts" (time-series)
            bins: Optional binning for nonlinear analysis

        Returns:
            Dict with r_squared, adj_r_squared, f_statistic, f_pvalue,
            coefficients, diagnostics, summary, y_actual, y_predicted
        """
        if not HAS_GENETIC_REG:
            return self._not_available(formula)

        try:
            gr = GeneticRegression(
                formula=formula,
                dfs=candle_dfs,
                instruments=instruments,
                build=True,
            )

            # Run OLS
            ols_result = gr.ols(axis=axis, bins=bins)

            # Extract results
            coefficients = {}
            for i, name in enumerate(ols_result.params.index):
                coefficients[name] = {
                    "value": float(ols_result.params[i]),
                    "std_err": float(ols_result.bse[i]),
                    "t_stat": float(ols_result.tvalues[i]),
                    "p_value": float(ols_result.pvalues[i]),
                }

            # Diagnostics
            diagnostics = {}
            try:
                diag = gr.diagnose()
                diagnostics = {
                    "condition_number": float(diag.get("condition_number", 0))
                        if "condition_number" in diag else None,
                    "vif": diag.get("vif", {}),
                }
            except Exception as e:
                logger.debug(f"Diagnostics failed: {e}")

            y_actual = ols_result.model.endog.tolist()
            y_predicted = ols_result.fittedvalues.tolist()

            return {
                "formula": formula,
                "instruments": instruments,
                "axis": axis,
                "r_squared": float(ols_result.rsquared),
                "adj_r_squared": float(ols_result.rsquared_adj),
                "f_statistic": float(ols_result.fvalue) if ols_result.fvalue is not None else 0,
                "f_pvalue": float(ols_result.f_pvalue) if ols_result.f_pvalue is not None else 1,
                "nobs": int(ols_result.nobs),
                "coefficients": coefficients,
                "diagnostics": diagnostics,
                "summary": str(ols_result.summary()),
                "y_actual": y_actual,
                "y_predicted": y_predicted,
            }

        except Exception as e:
            logger.error(f"GeneticRegression failed: {e}")
            return {"error": str(e), "formula": formula}

    def _not_available(self, formula: str) -> Dict[str, Any]:
        return {
            "error": "GeneticRegression requires quantpylib. Install with: pip install quantpylib",
            "formula": formula,
        }

    def format_report(self, results: Dict[str, Any]) -> str:
        """ASCII report."""
        if "error" in results:
            return f"[ERROR] {results['error']}"

        lines = [
            "=== FACTOR RESEARCH ===",
            f"  Formula: {results['formula']}",
            f"  Instruments: {', '.join(results.get('instruments', []))}",
            f"  Axis: {results.get('axis', 'flatten')}",
            "",
            f"  R-squared:     {results['r_squared']:.6f}",
            f"  Adj R-squared: {results['adj_r_squared']:.6f}",
            f"  F-statistic:   {results['f_statistic']:.4f}",
            f"  F p-value:     {results['f_pvalue']:.6f}",
            f"  Observations:  {results['nobs']}",
            "",
            "  Coefficients:",
        ]

        for name, info in results.get("coefficients", {}).items():
            sig = "*" if info["p_value"] < 0.05 else ""
            lines.append(
                f"    {name:<20} {info['value']:+.6f}  "
                f"(t={info['t_stat']:.3f}, p={info['p_value']:.4f}) {sig}"
            )

        diag = results.get("diagnostics", {})
        if diag:
            lines.append("")
            lines.append("  Diagnostics:")
            if diag.get("condition_number") is not None:
                cn = diag["condition_number"]
                warn = " [!] HIGH" if cn > 30 else ""
                lines.append(f"    Condition Number: {cn:.1f}{warn}")

        return "\n".join(lines)

    def plot(self, results: Dict[str, Any]) -> Any:
        """Plotly regression plot."""
        return QuantViz.regression_plot(results)
