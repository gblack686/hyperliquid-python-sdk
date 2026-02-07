"""
Cost Attribution Analyzer
==========================
Wraps quantpylib's cost_statistics() for Sharpe decomposition.
Decomposes strategy Sharpe into costless, costful, and per-component drags.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from quantpylib.simulator.performance import cost_statistics
    HAS_COST_STATS = True
except ImportError:
    HAS_COST_STATS = False

from .visualization import QuantViz


class CostAttributionAnalyzer:
    """
    Sharpe decomposition by cost component.

    Decomposes a strategy's Sharpe ratio into:
    - sharpe_costless: Sharpe before any costs
    - sharpe_costful: Sharpe after all costs
    - sharpe_commful: Sharpe with commission costs only
    - sharpe_execful: Sharpe with execution/slippage costs only
    - sharpe_swapful: Sharpe with swap/funding costs only
    - costdrag: Total Sharpe drag from costs
    - drag_pct: Percentage of Sharpe lost to costs
    """

    # Crypto 24/7 annualization
    PERIODS = {"minute": 525600, "hourly": 8760, "daily": 365}

    def __init__(self, granularity: str = "hourly"):
        self.periods_in_year = self.PERIODS.get(granularity, 8760)

    def analyze(self, portfolio_df: pd.DataFrame) -> Dict[str, float]:
        """
        Run cost attribution on a portfolio DataFrame.

        Args:
            portfolio_df: DataFrame from Alpha.run_simulation() with columns:
                capital_ret, comm_penalty, exec_penalty (optional: swap_penalty)

        Returns:
            Dict with sharpe_costless, sharpe_costful, sharpe_commful,
            sharpe_execful, sharpe_swapful, costdrag, drag_pct
        """
        if HAS_COST_STATS:
            return self._analyze_quantpylib(portfolio_df)
        return self._analyze_builtin(portfolio_df)

    def _analyze_quantpylib(self, portfolio_df: pd.DataFrame) -> Dict[str, float]:
        """Use quantpylib's cost_statistics directly."""
        try:
            result = cost_statistics(portfolio_df, periods_in_year=self.periods_in_year)
            # Ensure all keys exist
            out = {
                "sharpe_costless": float(result.get("sharpe_costless", 0)),
                "sharpe_costful": float(result.get("sharpe_costful", 0)),
                "sharpe_commful": float(result.get("sharpe_commful", 0)),
                "sharpe_execful": float(result.get("sharpe_execful", 0)),
                "sharpe_swapful": float(result.get("sharpe_swapful", 0)),
                "costdrag": float(result.get("costdrag", 0)),
            }
            sl = out["sharpe_costless"]
            out["drag_pct"] = abs(out["costdrag"] / sl * 100) if sl != 0 else 0
            return out
        except Exception as e:
            logger.warning(f"quantpylib cost_statistics failed, using builtin: {e}")
            return self._analyze_builtin(portfolio_df)

    def _analyze_builtin(self, portfolio_df: pd.DataFrame) -> Dict[str, float]:
        """
        Built-in cost attribution from capital_ret and penalty columns.
        """
        df = portfolio_df.copy()
        ann = np.sqrt(self.periods_in_year)

        # gross return (before costs)
        capital_ret = df.get("capital_ret", pd.Series(dtype=float))
        comm = df.get("comm_penalty", pd.Series(0, index=df.index))
        exec_pen = df.get("exec_penalty", pd.Series(0, index=df.index))
        swap = df.get("swap_penalty", pd.Series(0, index=df.index))

        if len(capital_ret) < 2:
            return self._empty()

        total_penalty = comm + exec_pen + swap
        gross_ret = capital_ret + total_penalty  # undo penalties

        def _sharpe(r: pd.Series) -> float:
            std = r.std()
            return float(r.mean() / std * ann) if std > 0 else 0.0

        s_costless = _sharpe(gross_ret)
        s_costful = _sharpe(capital_ret)
        s_commful = _sharpe(gross_ret - comm)
        s_execful = _sharpe(gross_ret - exec_pen)
        s_swapful = _sharpe(gross_ret - swap)
        drag = s_costless - s_costful

        return {
            "sharpe_costless": round(s_costless, 4),
            "sharpe_costful": round(s_costful, 4),
            "sharpe_commful": round(s_commful, 4),
            "sharpe_execful": round(s_execful, 4),
            "sharpe_swapful": round(s_swapful, 4),
            "costdrag": round(drag, 4),
            "drag_pct": round(abs(drag / s_costless * 100), 2) if s_costless != 0 else 0,
        }

    def _empty(self) -> Dict[str, float]:
        return {
            "sharpe_costless": 0, "sharpe_costful": 0,
            "sharpe_commful": 0, "sharpe_execful": 0,
            "sharpe_swapful": 0, "costdrag": 0, "drag_pct": 0,
        }

    def format_report(self, data: Dict[str, float]) -> str:
        """ASCII table of cost attribution."""
        lines = [
            "=== COST ATTRIBUTION ===",
            "",
            f"  Sharpe (costless):     {data['sharpe_costless']:+.4f}",
            f"  Sharpe (costful):      {data['sharpe_costful']:+.4f}",
            f"  Sharpe (comm-only):    {data['sharpe_commful']:+.4f}",
            f"  Sharpe (exec-only):    {data['sharpe_execful']:+.4f}",
            f"  Sharpe (swap-only):    {data['sharpe_swapful']:+.4f}",
            "",
            f"  Total Cost Drag:       {data['costdrag']:+.4f}",
            f"  Drag (%% of gross):    {data['drag_pct']:.1f}%",
        ]
        return "\n".join(lines)

    def plot(self, data: Dict[str, float]) -> Any:
        """Plotly cost attribution chart."""
        return QuantViz.cost_attribution_chart(data)
