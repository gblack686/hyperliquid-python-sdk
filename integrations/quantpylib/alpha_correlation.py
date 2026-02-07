"""
Alpha Correlation Analyzer
============================
Cross-strategy correlation analysis for portfolio diversification.
Wraps quantpylib's alpha_correlation() with Plotly rendering.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from quantpylib.simulator.performance import alpha_correlation as qpl_alpha_corr
    HAS_ALPHA_CORR = True
except ImportError:
    HAS_ALPHA_CORR = False

from .visualization import QuantViz


class AlphaCorrelationAnalyzer:
    """
    Cross-strategy correlation and diversification analysis.

    Computes:
    - Pairwise return correlation matrix
    - Eigenvalue decomposition for factor structure
    - Diversification ratio
    - Identification of redundant strategy pairs
    """

    def compute(
        self,
        strategy_returns: Dict[str, pd.Series],
    ) -> Dict[str, Any]:
        """
        Compute correlation analysis across strategies.

        Args:
            strategy_returns: Dict of strategy_name -> return series

        Returns:
            Dict with corr_matrix, eigenvalues, diversification_ratio, clustered_pairs
        """
        names = list(strategy_returns.keys())
        if len(names) < 2:
            return {
                "corr_matrix": pd.DataFrame(),
                "eigenvalues": [],
                "diversification_ratio": 1.0,
                "clustered_pairs": [],
                "strategy_names": names,
            }

        # Align all series on common index
        aligned = pd.DataFrame(strategy_returns)
        aligned = aligned.dropna(how="all")

        # Fill NaN with 0 (strategy not trading = 0 return)
        aligned = aligned.fillna(0)

        if len(aligned) < 10:
            return {
                "corr_matrix": pd.DataFrame(np.eye(len(names)), index=names, columns=names),
                "eigenvalues": [1.0] * len(names),
                "diversification_ratio": 1.0,
                "clustered_pairs": [],
                "strategy_names": names,
            }

        corr_matrix = aligned.corr()

        # Eigenvalue decomposition
        try:
            eigenvalues = np.linalg.eigvalsh(corr_matrix.values)
            eigenvalues = sorted(eigenvalues, reverse=True)
        except np.linalg.LinAlgError:
            eigenvalues = [1.0] * len(names)

        # Diversification ratio: ratio of weighted avg vol to portfolio vol
        # Higher = more diversified. Equal weight assumed.
        cov_matrix = aligned.cov()
        n = len(names)
        w = np.ones(n) / n
        individual_vols = np.sqrt(np.diag(cov_matrix.values))
        weighted_avg_vol = float(np.dot(w, individual_vols))
        portfolio_vol = float(np.sqrt(w @ cov_matrix.values @ w))
        div_ratio = weighted_avg_vol / portfolio_vol if portfolio_vol > 0 else 1.0

        # Find clustered (redundant) pairs
        clustered = self.identify_redundant(corr_matrix, threshold=0.7)

        return {
            "corr_matrix": corr_matrix,
            "eigenvalues": [float(e) for e in eigenvalues],
            "diversification_ratio": round(div_ratio, 4),
            "clustered_pairs": clustered,
            "strategy_names": names,
            "cov_matrix": cov_matrix,
        }

    def identify_redundant(
        self,
        corr_matrix: pd.DataFrame,
        threshold: float = 0.7,
    ) -> List[Tuple[str, str, float]]:
        """
        Identify strategy pairs with correlation above threshold.

        Returns:
            List of (strat_a, strat_b, correlation) tuples
        """
        pairs = []
        names = list(corr_matrix.columns)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                corr = abs(float(corr_matrix.iloc[i, j]))
                if corr >= threshold:
                    pairs.append((names[i], names[j], round(corr, 4)))

        return sorted(pairs, key=lambda x: -x[2])

    def format_report(self, results: Dict[str, Any]) -> str:
        """ASCII report."""
        lines = [
            "=== ALPHA CORRELATION ANALYSIS ===",
            "",
            f"  Strategies:           {len(results['strategy_names'])}",
            f"  Diversification Ratio: {results['diversification_ratio']:.4f}",
            f"  (>1.0 = diversified, 1.0 = perfectly correlated)",
            "",
        ]

        # Eigenvalues
        eigs = results["eigenvalues"]
        total = sum(eigs)
        lines.append("  Eigenvalues (variance explained):")
        for i, e in enumerate(eigs[:5]):
            pct = e / total * 100 if total > 0 else 0
            lines.append(f"    Factor {i+1}: {e:.4f} ({pct:.1f}%)")

        # Redundant pairs
        clustered = results["clustered_pairs"]
        if clustered:
            lines.append("")
            lines.append("  [!] Redundant pairs (corr > 0.7):")
            for a, b, corr in clustered:
                lines.append(f"    {a} <-> {b}: {corr:.3f}")
        else:
            lines.append("")
            lines.append("  [OK] No redundant pairs found")

        return "\n".join(lines)

    def plot(self, results: Dict[str, Any]) -> Any:
        """Plotly correlation heatmap."""
        return QuantViz.correlation_heatmap(
            results["corr_matrix"],
            names=results.get("strategy_names"),
        )
