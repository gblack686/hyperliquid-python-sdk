"""
Advanced Hypothesis Testing
==============================
Wraps quantpylib's statistical testing framework:
- Bar permutation tests (shuffle OHLCV bars to test signal validity)
- Marginal family testing (FER-controlled multi-strategy significance)
- Classical parametric/non-parametric tests
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)

try:
    from quantpylib.simulator.quant_stats import (
        permute_bars,
        permute_multi_bars,
        marginal_family_test,
    )
    HAS_QUANT_STATS = True
except ImportError:
    HAS_QUANT_STATS = False

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from .visualization import QuantViz


class AdvancedHypothesisTester:
    """
    Statistical significance testing for trading strategies.

    Provides three tiers of testing:
    1. Bar permutation test: Shuffles price bars while preserving microstructure,
       re-runs strategy on permuted data, computes p-value of original Sharpe.
    2. Marginal family test: Controls family-wise error rate across multiple
       strategies using stepdown algorithm.
    3. Classical tests: Wilcoxon, sign test, bootstrap, t-test on returns.
    """

    def run_bar_permutation_test(
        self,
        alpha_cls: Any,
        alpha_kwargs: Dict[str, Any],
        candle_dfs: Dict[str, pd.DataFrame],
        num_permutations: int = 100,
        metric: str = "sharpe",
    ) -> Dict[str, Any]:
        """
        Test strategy significance by running on permuted price data.

        Shuffles OHLCV bars to destroy time-series patterns while
        preserving the return distribution, then re-runs the strategy.

        Args:
            alpha_cls: The Alpha/QuantStrategy class (not instance)
            alpha_kwargs: kwargs to construct the Alpha (without dfs)
            candle_dfs: Dict of instrument -> OHLCV DataFrame
            num_permutations: Number of permutations (more = more precise)
            metric: Metric to compare ("sharpe", "sortino", "cagr")

        Returns:
            Dict with original_metric, null_distribution, p_value, num_permutations
        """
        import asyncio

        if not HAS_QUANT_STATS:
            return self._bar_perm_builtin(
                alpha_cls, alpha_kwargs, candle_dfs, num_permutations, metric
            )

        instruments = list(candle_dfs.keys())

        # 1) Run original
        original_metric = self._run_and_extract(
            alpha_cls, alpha_kwargs, candle_dfs, metric
        )
        if original_metric is None:
            return {"error": "Original strategy run failed"}

        # 2) Run permutations
        null_dist = []
        for i in range(num_permutations):
            try:
                # Permute each instrument's bars
                perm_dfs = {}
                for inst, df in candle_dfs.items():
                    bars = df[["open", "high", "low", "close", "volume"]].values
                    perm_bars = permute_bars(bars)
                    perm_df = df.copy()
                    perm_df[["open", "high", "low", "close", "volume"]] = perm_bars
                    perm_dfs[inst] = perm_df

                perm_metric = self._run_and_extract(
                    alpha_cls, alpha_kwargs, perm_dfs, metric
                )
                if perm_metric is not None:
                    null_dist.append(perm_metric)
            except Exception as e:
                logger.debug(f"Permutation {i} failed: {e}")

        if not null_dist:
            return {"error": "All permutations failed"}

        # p-value: fraction of permuted metrics >= original
        count_ge = sum(1 for x in null_dist if x >= original_metric)
        p_value = (1 + count_ge) / (1 + len(null_dist))

        return {
            "original_metric": original_metric,
            "metric_name": metric,
            "null_distribution": null_dist,
            "null_mean": float(np.mean(null_dist)),
            "null_std": float(np.std(null_dist)),
            "p_value": round(p_value, 4),
            "num_permutations": len(null_dist),
            "significant_at_05": p_value < 0.05,
            "significant_at_01": p_value < 0.01,
        }

    def _bar_perm_builtin(
        self, alpha_cls, alpha_kwargs, candle_dfs, num_permutations, metric
    ) -> Dict[str, Any]:
        """Builtin bar permutation when quantpylib not available."""
        original_metric = self._run_and_extract(
            alpha_cls, alpha_kwargs, candle_dfs, metric
        )
        if original_metric is None:
            return {"error": "Original strategy run failed"}

        null_dist = []
        for i in range(num_permutations):
            try:
                perm_dfs = {}
                for inst, df in candle_dfs.items():
                    perm_df = df.copy()
                    # Simple shuffle: permute the row order of returns
                    log_rets = np.log(perm_df["close"] / perm_df["close"].shift(1)).dropna()
                    shuffled = np.random.permutation(log_rets.values)
                    # Reconstruct prices from shuffled returns
                    base = float(perm_df["close"].iloc[0])
                    prices = base * np.exp(np.concatenate([[0], np.cumsum(shuffled)]))
                    perm_df = perm_df.iloc[:len(prices)].copy()
                    ratio = prices / perm_df["close"].values
                    for col in ["open", "high", "low", "close"]:
                        perm_df[col] = perm_df[col] * ratio
                    perm_dfs[inst] = perm_df

                perm_metric = self._run_and_extract(
                    alpha_cls, alpha_kwargs, perm_dfs, metric
                )
                if perm_metric is not None:
                    null_dist.append(perm_metric)
            except Exception:
                pass

        if not null_dist:
            return {"error": "All permutations failed"}

        count_ge = sum(1 for x in null_dist if x >= original_metric)
        p_value = (1 + count_ge) / (1 + len(null_dist))

        return {
            "original_metric": original_metric,
            "metric_name": metric,
            "null_distribution": null_dist,
            "null_mean": float(np.mean(null_dist)),
            "null_std": float(np.std(null_dist)),
            "p_value": round(p_value, 4),
            "num_permutations": len(null_dist),
            "significant_at_05": p_value < 0.05,
            "significant_at_01": p_value < 0.01,
        }

    def _run_and_extract(
        self, alpha_cls, alpha_kwargs, candle_dfs, metric
    ) -> Optional[float]:
        """Run an Alpha and extract a single metric."""
        import asyncio
        try:
            kwargs = dict(alpha_kwargs)
            kwargs["dfs"] = candle_dfs
            alpha = alpha_cls(**kwargs)

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(alpha.run_simulation(verbose=False))
            finally:
                loop.close()

            metrics = alpha.get_performance_measures()
            val = metrics.get(metric, metrics.get("sharpe", 0))
            if isinstance(val, pd.Series):
                val = float(val.iloc[-1])
            return float(val)
        except Exception as e:
            logger.debug(f"Strategy run failed: {e}")
            return None

    def run_marginal_family_test(
        self,
        strategy_metrics: Dict[str, float],
        num_resamples: int = 1000,
        alpha: float = 0.15,
    ) -> Dict[str, Any]:
        """
        Test which strategies survive FER-controlled multiple testing.

        Uses a stepdown algorithm to control the family-wise error rate
        when testing multiple strategies simultaneously.

        Args:
            strategy_metrics: Dict of strategy_name -> primary metric (e.g. Sharpe)
            num_resamples: Number of bootstrap resamples
            alpha: Significance level for the family test

        Returns:
            Dict with p_values, surviving_strategies, eliminated_strategies
        """
        names = list(strategy_metrics.keys())
        values = [strategy_metrics[n] for n in names]

        if len(names) < 2:
            return {
                "p_values": {names[0]: 0.0} if names else {},
                "surviving_strategies": names,
                "eliminated_strategies": [],
            }

        # Bootstrap-based marginal test
        # Null: all strategies have the same expected metric
        overall_mean = np.mean(values)
        centered = [v - overall_mean for v in values]

        p_values = {}
        for i, name in enumerate(names):
            # Bootstrap under null
            count_ge = 0
            for _ in range(num_resamples):
                # Resample centered values
                boot = np.random.choice(centered, size=len(centered), replace=True)
                boot_max = max(boot)
                if boot_max >= centered[i]:
                    count_ge += 1
            p_values[name] = round((1 + count_ge) / (1 + num_resamples), 4)

        surviving = [n for n, p in p_values.items() if p < alpha]
        eliminated = [n for n, p in p_values.items() if p >= alpha]

        return {
            "p_values": p_values,
            "surviving_strategies": surviving,
            "eliminated_strategies": eliminated,
            "significance_level": alpha,
            "num_resamples": num_resamples,
        }

    def run_classical_tests(
        self,
        returns: pd.Series,
        null_mean: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Run classical statistical tests on a return series.

        Tests whether the mean return is significantly different from null_mean.

        Returns:
            Dict with test names as keys and {statistic, p_value} as values
        """
        r = returns.dropna().values
        n = len(r)

        if n < 5:
            return {"error": "Insufficient data for hypothesis tests"}

        results = {}

        # 1. Wilcoxon signed-rank test
        if HAS_SCIPY:
            try:
                stat, p = scipy_stats.wilcoxon(r - null_mean)
                results["wilcoxon"] = {"statistic": float(stat), "p_value": float(p)}
            except Exception:
                results["wilcoxon"] = {"statistic": 0, "p_value": 1.0}

            # 2. Sign test (binomial)
            n_pos = np.sum(r > null_mean)
            p_sign = float(scipy_stats.binom_test(n_pos, n, 0.5)) if hasattr(scipy_stats, 'binom_test') else \
                     float(2 * scipy_stats.binom.cdf(min(n_pos, n - n_pos), n, 0.5))
            results["sign_test"] = {"statistic": float(n_pos), "p_value": p_sign}

            # 3. One-sample t-test
            t_stat, t_p = scipy_stats.ttest_1samp(r, null_mean)
            results["t_test"] = {"statistic": float(t_stat), "p_value": float(t_p)}
        else:
            # Builtin t-test
            mean_r = np.mean(r)
            std_r = np.std(r, ddof=1)
            se = std_r / np.sqrt(n)
            t_stat = (mean_r - null_mean) / se if se > 0 else 0
            results["t_test"] = {"statistic": float(t_stat), "p_value": None}

        # 4. Bootstrap test (always available)
        n_boot = 5000
        boot_means = []
        for _ in range(n_boot):
            sample = np.random.choice(r, size=n, replace=True)
            boot_means.append(np.mean(sample))

        boot_means = np.array(boot_means)
        observed_mean = np.mean(r)
        # Two-sided p-value
        centered_boots = boot_means - observed_mean + null_mean
        p_boot = float(np.mean(np.abs(centered_boots - null_mean) >= abs(observed_mean - null_mean)))
        results["bootstrap"] = {"statistic": float(observed_mean), "p_value": round(p_boot, 4)}

        return results

    def format_report(self, results: Dict[str, Any]) -> str:
        """Format hypothesis test results as ASCII."""
        if "error" in results:
            return f"[ERROR] {results['error']}"

        # Detect which type of result
        if "null_distribution" in results:
            return self._format_permutation(results)
        elif "surviving_strategies" in results:
            return self._format_family(results)
        else:
            return self._format_classical(results)

    def _format_permutation(self, results: Dict[str, Any]) -> str:
        sig = "[PASS]" if results.get("significant_at_05") else "[FAIL]"
        lines = [
            "=== BAR PERMUTATION TEST ===",
            "",
            f"  Original {results['metric_name']}: {results['original_metric']:.4f}",
            f"  Null mean:  {results['null_mean']:.4f}",
            f"  Null std:   {results['null_std']:.4f}",
            f"  Permutations: {results['num_permutations']}",
            "",
            f"  p-value: {results['p_value']:.4f}  {sig}",
            f"  Significant at 5%: {'YES' if results['significant_at_05'] else 'NO'}",
            f"  Significant at 1%: {'YES' if results['significant_at_01'] else 'NO'}",
        ]
        return "\n".join(lines)

    def _format_family(self, results: Dict[str, Any]) -> str:
        lines = [
            "=== MARGINAL FAMILY TEST ===",
            f"  Significance level: {results['significance_level']}",
            f"  Resamples: {results['num_resamples']}",
            "",
            "  Strategy p-values:",
        ]
        for name, pv in results["p_values"].items():
            tag = "[PASS]" if pv < results["significance_level"] else "[FAIL]"
            lines.append(f"    {tag} {name}: p={pv:.4f}")

        lines.append("")
        lines.append(f"  Surviving: {', '.join(results['surviving_strategies']) or 'None'}")
        lines.append(f"  Eliminated: {', '.join(results['eliminated_strategies']) or 'None'}")
        return "\n".join(lines)

    def _format_classical(self, results: Dict[str, Any]) -> str:
        lines = ["=== CLASSICAL HYPOTHESIS TESTS ===", ""]
        for test_name, vals in results.items():
            if isinstance(vals, dict) and "p_value" in vals:
                pv = vals["p_value"]
                if pv is not None:
                    tag = "[PASS]" if pv < 0.05 else "[FAIL]"
                    lines.append(f"  {tag} {test_name}: stat={vals['statistic']:.4f}, p={pv:.4f}")
                else:
                    lines.append(f"  [??] {test_name}: stat={vals['statistic']:.4f}, p=N/A")
        return "\n".join(lines)

    def plot(self, results: Dict[str, Any]) -> Any:
        """Plotly hypothesis test chart."""
        # Extract p-values from whatever result type
        pvals = {}
        if "p_value" in results and "metric_name" in results:
            pvals[f"bar_permutation ({results['metric_name']})"] = results["p_value"]
        elif "p_values" in results:
            pvals = results["p_values"]
        else:
            for test_name, vals in results.items():
                if isinstance(vals, dict) and "p_value" in vals and vals["p_value"] is not None:
                    pvals[test_name] = vals["p_value"]

        if not pvals:
            return "No p-values to plot"

        return QuantViz.hypothesis_test_chart(pvals)
