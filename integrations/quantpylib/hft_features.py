"""
HFT Feature Extractor
=======================
Wraps quantpylib.hft.features for microstructure signal enhancement.
Computes rolling volatility, trade imbalance, and flow PnL.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

try:
    from quantpylib.hft.features import rolling_vol, trade_imbalance, flow_pnl
    HAS_HFT = True
except ImportError:
    HAS_HFT = False

from .visualization import QuantViz


class HFTFeatureExtractor:
    """
    Microstructure feature extraction for enhanced signal generation.

    Wraps quantpylib HFT features:
    - Rolling volatility (standard + exponential)
    - Trade imbalance (directional flow bias)
    - Flow PnL (market maker perspective)

    Can enrich existing candle DataFrames with HFT-derived columns.
    """

    def compute_rolling_vol(
        self,
        mids: np.ndarray,
        window: int = 100,
        exponential: bool = False,
    ) -> np.ndarray:
        """
        Compute rolling volatility of mid prices.

        Args:
            mids: Array of mid prices
            window: Rolling window size
            exponential: Use exponential weighting (more recent = more weight)

        Returns:
            Array of rolling volatility values
        """
        if HAS_HFT:
            try:
                return rolling_vol(mids, window, exp=exponential)
            except Exception as e:
                logger.debug(f"quantpylib rolling_vol failed: {e}")

        # Builtin fallback
        diffs = np.diff(mids)
        if len(diffs) < window:
            return np.full(len(mids), np.nan)

        if exponential:
            alpha = 2.0 / (window + 1)
            result = np.full(len(mids), np.nan)
            var = np.var(diffs[:window])
            result[window] = np.sqrt(var)
            for i in range(window + 1, len(mids)):
                var = alpha * diffs[i - 1] ** 2 + (1 - alpha) * var
                result[i] = np.sqrt(var)
            return result
        else:
            result = np.full(len(mids), np.nan)
            for i in range(window, len(mids)):
                result[i] = np.std(diffs[i - window:i])
            return result

    def compute_trade_imbalance(
        self,
        trades: np.ndarray,
        decay_half_life: int = 50,
    ) -> float:
        """
        Compute signed volume imbalance with exponential decay.

        Args:
            trades: Array of shape (N, 4): [timestamp, price, size, direction]
                    direction: +1 = buyer-initiated, -1 = seller-initiated
            decay_half_life: Half-life for exponential decay weighting

        Returns:
            Imbalance value in [-1, 1]. Positive = buy pressure.
        """
        if len(trades) == 0:
            return 0.0

        if HAS_HFT:
            try:
                decay_fn = lambda n: np.exp(-np.log(2) / decay_half_life * np.arange(n)[::-1])
                return float(trade_imbalance(trades, decay_fn))
            except Exception as e:
                logger.debug(f"quantpylib trade_imbalance failed: {e}")

        # Builtin
        n = len(trades)
        weights = np.exp(-np.log(2) / decay_half_life * np.arange(n)[::-1])
        sizes = trades[:, 2]
        directions = trades[:, 3]
        signed_vol = sizes * directions

        denom = np.sum(weights * sizes)
        if denom == 0:
            return 0.0
        return float(np.sum(weights * signed_vol) / denom)

    def compute_flow_pnl(
        self,
        trades: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Calculate running PnL from trade flow (market maker perspective).

        Args:
            trades: Array of shape (N, 4): [timestamp, price, size, direction]

        Returns:
            Dict with timestamps, running_pnls, cumulative_volume
        """
        if len(trades) == 0:
            return {"timestamps": [], "values": [], "cumulative_volume": []}

        if HAS_HFT:
            try:
                ts, pnls, cum_vol = flow_pnl(trades)
                return {
                    "timestamps": ts.tolist() if isinstance(ts, np.ndarray) else ts,
                    "values": pnls.tolist() if isinstance(pnls, np.ndarray) else pnls,
                    "cumulative_volume": cum_vol.tolist() if isinstance(cum_vol, np.ndarray) else cum_vol,
                }
            except Exception as e:
                logger.debug(f"quantpylib flow_pnl failed: {e}")

        # Builtin
        timestamps = trades[:, 0]
        prices = trades[:, 1]
        sizes = trades[:, 2]
        directions = trades[:, 3]

        # Inventory = negative cumulative signed volume (market maker is counterparty)
        signed_vol = sizes * directions
        inventory = -np.cumsum(signed_vol)

        # Running PnL: sum of (price_change * inventory_before)
        pnls = np.zeros(len(trades))
        for i in range(1, len(trades)):
            pnls[i] = pnls[i - 1] + inventory[i - 1] * (prices[i] - prices[i - 1])

        return {
            "timestamps": timestamps.tolist(),
            "values": pnls.tolist(),
            "cumulative_volume": np.cumsum(sizes).tolist(),
        }

    def enrich_candle_df(
        self,
        df: pd.DataFrame,
        vol_window: int = 20,
        vol_exp: bool = False,
    ) -> pd.DataFrame:
        """
        Add HFT-derived feature columns to an existing candle DataFrame.

        Adds columns:
        - hft_vol: Rolling volatility of close prices
        - hft_vol_ratio: Current vol / average vol
        - hft_vol_zscore: Z-score of current vol
        - hft_microstructure_signal: Combined microstructure signal

        Args:
            df: DataFrame with at least 'close' column
            vol_window: Window for rolling volatility
            vol_exp: Use exponential volatility

        Returns:
            DataFrame with additional columns
        """
        result = df.copy()
        mids = result["close"].values.astype(float)

        # Rolling volatility
        vol = self.compute_rolling_vol(mids, window=vol_window, exponential=vol_exp)
        result["hft_vol"] = vol

        # Vol ratio and z-score
        vol_series = pd.Series(vol, index=result.index)
        vol_mean = vol_series.rolling(vol_window * 5, min_periods=vol_window).mean()
        vol_std = vol_series.rolling(vol_window * 5, min_periods=vol_window).std()

        result["hft_vol_ratio"] = vol_series / vol_mean
        result["hft_vol_zscore"] = (vol_series - vol_mean) / vol_std.replace(0, np.nan)

        # Simple microstructure signal:
        # High vol + price momentum = trend, high vol + no momentum = mean reversion
        returns = result["close"].pct_change()
        mom = returns.rolling(vol_window).mean()
        result["hft_microstructure_signal"] = mom / vol_series.replace(0, np.nan)

        return result

    def format_report(self, features: Dict[str, Any]) -> str:
        """ASCII report of HFT features."""
        lines = ["=== HFT MICROSTRUCTURE FEATURES ===", ""]

        if "rolling_vol" in features:
            rv = features["rolling_vol"]
            if isinstance(rv, pd.Series):
                lines.append(f"  Rolling Vol: last={rv.iloc[-1]:.6f}, mean={rv.mean():.6f}")
            elif isinstance(rv, np.ndarray):
                valid = rv[~np.isnan(rv)]
                if len(valid) > 0:
                    lines.append(f"  Rolling Vol: last={valid[-1]:.6f}, mean={valid.mean():.6f}")

        if "trade_imbalance" in features:
            ti = features["trade_imbalance"]
            if isinstance(ti, (int, float)):
                direction = "BUY pressure" if ti > 0 else "SELL pressure" if ti < 0 else "NEUTRAL"
                lines.append(f"  Trade Imbalance: {ti:.4f} ({direction})")

        if "flow_pnl" in features:
            fp = features["flow_pnl"]
            if isinstance(fp, dict) and "values" in fp:
                vals = fp["values"]
                if vals:
                    lines.append(f"  Flow PnL: final={vals[-1]:.4f}")

        return "\n".join(lines)

    def plot(self, features: Dict[str, Any]) -> Any:
        """Plotly HFT features dashboard."""
        return QuantViz.hft_features_dashboard(features)
