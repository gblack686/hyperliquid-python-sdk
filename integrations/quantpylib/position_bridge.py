"""
Position Bridge
=================
Translates backtest positions into live trading targets.
Wraps BaseAlpha.get_positions_for_capital() for capital deployment.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

try:
    from quantpylib.simulator.alpha import BaseAlpha
    HAS_BASE_ALPHA = True
except ImportError:
    HAS_BASE_ALPHA = False

from .visualization import QuantViz


class LivePositionBridge:
    """
    Converts backtest Alpha positions into actionable live trading targets.

    Handles:
    - Capital-scaled position sizing from Alpha weights
    - Inertia filtering (skip small rebalances)
    - Leverage ratio tracking
    - Order generation for execution

    Usage:
        bridge = LivePositionBridge()
        targets = bridge.compute_targets(
            alpha_instance=my_alpha,
            capital=50000,
            current_holdings={"BTC": 0.5, "ETH": 3.0},
        )
        orders = bridge.generate_orders(targets, {"BTC": 95000, "ETH": 3200})
    """

    def __init__(self, inertia_threshold: float = 0.02):
        """
        Args:
            inertia_threshold: Min position change (as fraction of capital)
                              below which rebalance is skipped.
        """
        self.inertia_threshold = inertia_threshold

    def compute_targets(
        self,
        alpha_instance: Any,
        capital: float,
        current_holdings: Optional[Dict[str, float]] = None,
        current_prices: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Compute target positions from a backtested Alpha.

        Args:
            alpha_instance: A backtested Alpha/QuantStrategy instance
            capital: Available capital for deployment
            current_holdings: Dict of instrument -> current units held
            current_prices: Dict of instrument -> current price

        Returns:
            Dict with targets, changes, dollar_exposure, inertia_filtered,
            leverage_ratio, instruments, target_units, current_units
        """
        if current_holdings is None:
            current_holdings = {}

        instruments = []
        weights = []

        # Extract final-period weights from the Alpha
        if HAS_BASE_ALPHA and hasattr(alpha_instance, "portfolio_df") and alpha_instance.portfolio_df is not None:
            pdf = alpha_instance.portfolio_df
            instruments = list(alpha_instance.instruments)

            # Get last row weights
            weight_cols = [c for c in pdf.columns if c.startswith("w_")]
            if weight_cols:
                last_weights = pdf[weight_cols].iloc[-1]
                weights = [float(last_weights.get(f"w_{inst}", 0)) for inst in instruments]
            else:
                weights = [0.0] * len(instruments)
        elif hasattr(alpha_instance, "instruments") and hasattr(alpha_instance, "weights"):
            instruments = list(alpha_instance.instruments)
            if isinstance(alpha_instance.weights, pd.DataFrame):
                weights = alpha_instance.weights.iloc[-1].tolist()
            else:
                weights = list(alpha_instance.weights)
        else:
            return {"error": "Cannot extract positions from alpha instance"}

        # Compute target units
        target_units = []
        current_units = []
        changes = []
        dollar_exposures = []
        inertia_filtered = []

        for i, inst in enumerate(instruments):
            w = weights[i] if i < len(weights) else 0
            price = 1.0
            if current_prices and inst in current_prices:
                price = current_prices[inst]
            elif hasattr(alpha_instance, "dfs") and inst in alpha_instance.dfs:
                price = float(alpha_instance.dfs[inst]["close"].iloc[-1])

            dollar_target = capital * w
            unit_target = dollar_target / price if price > 0 else 0
            curr = current_holdings.get(inst, 0)
            change = unit_target - curr
            dollar_exp = abs(unit_target * price)

            # Inertia filter
            is_filtered = abs(change * price) < (capital * self.inertia_threshold)

            target_units.append(round(unit_target, 6))
            current_units.append(curr)
            changes.append(round(change, 6))
            dollar_exposures.append(round(dollar_exp, 2))
            inertia_filtered.append(is_filtered)

        # Leverage ratio
        total_exposure = sum(dollar_exposures)
        leverage_ratio = total_exposure / capital if capital > 0 else 0

        return {
            "instruments": instruments,
            "target_units": target_units,
            "current_units": current_units,
            "changes": changes,
            "dollar_exposure": dollar_exposures,
            "inertia_filtered": inertia_filtered,
            "leverage_ratio": round(leverage_ratio, 4),
            "total_exposure": round(total_exposure, 2),
            "capital": capital,
        }

    def generate_orders(
        self,
        targets: Dict[str, Any],
        current_prices: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        Generate order list from computed targets.

        Args:
            targets: Output from compute_targets()
            current_prices: Dict of instrument -> current price

        Returns:
            List of order dicts: {instrument, side, size, type, reason, dollar_value}
        """
        orders = []
        instruments = targets.get("instruments", [])
        changes = targets.get("changes", [])
        filtered = targets.get("inertia_filtered", [])

        for i, inst in enumerate(instruments):
            if i >= len(changes):
                break

            change = changes[i]
            is_filtered = filtered[i] if i < len(filtered) else False

            if is_filtered or abs(change) < 1e-10:
                continue

            price = current_prices.get(inst, 0)
            side = "buy" if change > 0 else "sell"
            size = abs(change)

            orders.append({
                "instrument": inst,
                "side": side,
                "size": round(size, 6),
                "type": "limit",
                "reason": "rebalance",
                "dollar_value": round(size * price, 2),
            })

        return orders

    def format_report(self, targets: Dict[str, Any]) -> str:
        """ASCII position report."""
        lines = [
            "=== POSITION TARGETS ===",
            f"  Capital: ${targets['capital']:,.2f}",
            f"  Leverage: {targets['leverage_ratio']:.2f}x",
            f"  Total Exposure: ${targets['total_exposure']:,.2f}",
            "",
            f"  {'Instrument':<12} {'Current':>10} {'Target':>10} {'Change':>10} {'Exposure':>12} {'Skip':>6}",
            f"  {'-'*62}",
        ]

        for i, inst in enumerate(targets["instruments"]):
            curr = targets["current_units"][i]
            tgt = targets["target_units"][i]
            chg = targets["changes"][i]
            exp = targets["dollar_exposure"][i]
            skip = "YES" if targets["inertia_filtered"][i] else ""
            lines.append(
                f"  {inst:<12} {curr:10.4f} {tgt:10.4f} {chg:+10.4f} ${exp:>10,.2f} {skip:>6}"
            )

        return "\n".join(lines)

    def plot(self, targets: Dict[str, Any]) -> Any:
        """Plotly position sizing chart."""
        return QuantViz.position_sizing_chart(targets)
