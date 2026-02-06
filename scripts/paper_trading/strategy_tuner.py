"""
Strategy Auto-Tuner
====================
Analyzes recent performance and automatically adjusts strategy parameters.

The tuner runs on a schedule (default: daily) and:
1. Pulls 7-day performance metrics from Supabase
2. Evaluates each strategy against configurable thresholds
3. Proposes parameter adjustments with reasoning
4. Logs adjustments to paper_strategy_adjustments table
5. Optionally auto-applies or waits for review

Tuning Rules:
- Win rate < 30% -> Tighten entry criteria (raise min thresholds)
- Win rate > 70% -> Loosen entry criteria slightly (capture more signals)
- Avg P&L negative for 7d -> Widen stops, raise confidence threshold
- High signal count + low win rate -> Reduce signal frequency
- Consistently profitable -> Slightly increase position sizing

Usage:
    tuner = StrategyTuner(auto_apply=False)  # Require manual review
    adjustments = await tuner.evaluate_all()
    await tuner.log_adjustments(adjustments)

    # Review pending adjustments
    pending = await tuner.get_pending_adjustments()

    # Apply approved adjustments
    await tuner.apply_approved()
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class Adjustment:
    """A proposed parameter adjustment."""
    strategy_name: str
    parameter_name: str
    old_value: float
    new_value: float
    reason: str
    metric_trigger: str
    metric_value: float
    # Performance context
    win_rate_7d: Optional[float] = None
    total_pnl_7d: Optional[float] = None
    total_signals_7d: Optional[int] = None
    avg_pnl_pct_7d: Optional[float] = None


# Default parameter bounds - prevents tuning from going to extremes
PARAMETER_BOUNDS = {
    "funding_arbitrage": {
        "min_funding_rate": (0.002, 0.05),   # 0.002% to 0.05%
        "min_volume": (50_000, 500_000),
        "expiry_hours": (4, 24),
    },
    "grid_trading": {
        "min_range_pct": (1.5, 8.0),
        "max_range_pct": (8.0, 25.0),
        "entry_threshold_pct": (10, 40),
        "min_volume": (100_000, 2_000_000),
        "lookback_hours": (24, 168),
        "expiry_hours": (8, 72),
    },
    "directional_momentum": {
        "min_change_pct": (1.0, 8.0),
        "min_volume": (100_000, 2_000_000),
        "min_score": (30, 80),
        "expiry_hours": (8, 72),
    },
}

# Tuning thresholds
THRESHOLDS = {
    "win_rate_low": 0.30,        # Below 30% = tighten
    "win_rate_high": 0.70,       # Above 70% = loosen slightly
    "avg_pnl_negative_days": 7,  # 7 days of negative avg P&L = widen stops
    "min_signals_for_eval": 5,   # Need at least 5 signals to evaluate
    "max_adjustment_pct": 0.25,  # Max 25% change per adjustment
}


class StrategyTuner:
    """
    Evaluates strategy performance and proposes parameter adjustments.

    Attributes:
        auto_apply: If True, apply adjustments immediately. If False, log as 'pending'.
    """

    def __init__(self, auto_apply: bool = False):
        self.auto_apply = auto_apply
        self.supabase = self._init_supabase()

    def _init_supabase(self) -> Optional[Client]:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            logger.warning("Supabase credentials not found - tuner disabled")
            return None
        return create_client(url, key)

    async def evaluate_all(self) -> List[Adjustment]:
        """
        Evaluate all strategies and return proposed adjustments.

        Returns:
            List of Adjustment objects with proposed changes
        """
        if not self.supabase:
            return []

        adjustments = []
        strategies = ["funding_arbitrage", "grid_trading", "directional_momentum"]

        for strategy_name in strategies:
            try:
                metrics = await self._get_strategy_metrics(strategy_name)
                if not metrics:
                    logger.info(f"No metrics for {strategy_name} - skipping")
                    continue

                current_params = await self._get_current_params(strategy_name)
                strategy_adjustments = self._evaluate_strategy(
                    strategy_name, metrics, current_params
                )
                adjustments.extend(strategy_adjustments)

            except Exception as e:
                logger.error(f"Error evaluating {strategy_name}: {e}")

        return adjustments

    async def _get_strategy_metrics(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get 7-day performance metrics for a strategy."""
        if not self.supabase:
            return None

        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        try:
            # Get outcomes in the last 7 days
            outcomes = self.supabase.table("paper_recommendation_outcomes").select(
                "outcome_type, pnl_pct, pnl_usd, hold_duration_minutes, "
                "paper_recommendations!inner(strategy_name, confidence_score)"
            ).gte("outcome_time", seven_days_ago).execute()

            if not outcomes.data:
                return None

            # Filter to this strategy
            strategy_outcomes = [
                o for o in outcomes.data
                if o.get("paper_recommendations", {}).get("strategy_name") == strategy_name
            ]

            if len(strategy_outcomes) < THRESHOLDS["min_signals_for_eval"]:
                logger.info(
                    f"{strategy_name}: Only {len(strategy_outcomes)} outcomes "
                    f"(need {THRESHOLDS['min_signals_for_eval']})"
                )
                return None

            # Compute metrics
            total = len(strategy_outcomes)
            wins = sum(1 for o in strategy_outcomes if o["outcome_type"] == "TARGET_HIT")
            losses = sum(1 for o in strategy_outcomes if o["outcome_type"] == "STOPPED")
            expired = sum(1 for o in strategy_outcomes if o["outcome_type"] == "EXPIRED")

            pnl_values = [float(o.get("pnl_pct", 0)) for o in strategy_outcomes]
            avg_pnl = sum(pnl_values) / len(pnl_values) if pnl_values else 0
            total_pnl = sum(pnl_values)

            pnl_usd_values = [float(o.get("pnl_usd", 0)) for o in strategy_outcomes]
            total_pnl_usd = sum(pnl_usd_values)

            durations = [
                int(o.get("hold_duration_minutes", 0))
                for o in strategy_outcomes if o.get("hold_duration_minutes")
            ]
            avg_duration = sum(durations) / len(durations) if durations else 0

            confidences = [
                int(o.get("paper_recommendations", {}).get("confidence_score", 0))
                for o in strategy_outcomes
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Win/loss streak
            outcomes_sorted = sorted(
                strategy_outcomes,
                key=lambda x: x.get("outcome_time", ""),
                reverse=True,
            )
            streak = 0
            streak_type = None
            for o in outcomes_sorted:
                ot = o["outcome_type"]
                if streak_type is None:
                    streak_type = ot
                    streak = 1
                elif ot == streak_type:
                    streak += 1
                else:
                    break

            decided = wins + losses
            win_rate = wins / decided if decided > 0 else 0

            return {
                "total_signals": total,
                "wins": wins,
                "losses": losses,
                "expired": expired,
                "win_rate": win_rate,
                "avg_pnl_pct": avg_pnl,
                "total_pnl_pct": total_pnl,
                "total_pnl_usd": total_pnl_usd,
                "avg_duration_min": avg_duration,
                "avg_confidence": avg_confidence,
                "current_streak": streak,
                "streak_type": streak_type,
                "expiry_rate": expired / total if total > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Error fetching metrics for {strategy_name}: {e}")
            return None

    async def _get_current_params(self, strategy_name: str) -> Dict[str, float]:
        """
        Get current effective parameters for a strategy.

        Checks if there are previously applied adjustments, otherwise
        returns defaults from the scheduler config.
        """
        defaults = {
            "funding_arbitrage": {
                "min_funding_rate": 0.01,
                "min_volume": 100_000,
                "expiry_hours": 8,
            },
            "grid_trading": {
                "lookback_hours": 72,
                "min_range_pct": 3.0,
                "max_range_pct": 15.0,
                "entry_threshold_pct": 20,
                "min_volume": 500_000,
                "expiry_hours": 24,
            },
            "directional_momentum": {
                "min_change_pct": 3.0,
                "min_volume": 500_000,
                "min_score": 50,
                "expiry_hours": 24,
            },
        }

        params = defaults.get(strategy_name, {}).copy()

        # Override with latest applied adjustments
        if self.supabase:
            try:
                result = self.supabase.table("paper_strategy_adjustments").select(
                    "parameter_name, new_value"
                ).eq("strategy_name", strategy_name).eq(
                    "status", "applied"
                ).order("created_at", desc=True).execute()

                if result.data:
                    # Apply most recent adjustment for each parameter
                    seen = set()
                    for adj in result.data:
                        param = adj["parameter_name"]
                        if param not in seen:
                            params[param] = adj["new_value"]
                            seen.add(param)

            except Exception as e:
                logger.warning(f"Error fetching applied adjustments: {e}")

        return params

    def _evaluate_strategy(
        self,
        strategy_name: str,
        metrics: Dict[str, Any],
        current_params: Dict[str, float],
    ) -> List[Adjustment]:
        """
        Evaluate a strategy's performance and propose adjustments.

        Tuning rules:
        1. Low win rate -> raise entry thresholds
        2. High win rate -> slightly lower entry thresholds
        3. Negative avg P&L -> widen stops (increase expiry, tighten entry)
        4. High expiry rate -> shorten expiry or tighten entry
        5. Low signal count -> loosen filters to get more data
        """
        adjustments = []
        win_rate = metrics["win_rate"]
        avg_pnl = metrics["avg_pnl_pct"]
        total_signals = metrics["total_signals"]
        expiry_rate = metrics["expiry_rate"]
        bounds = PARAMETER_BOUNDS.get(strategy_name, {})

        context = {
            "win_rate_7d": win_rate,
            "total_pnl_7d": metrics["total_pnl_pct"],
            "total_signals_7d": total_signals,
            "avg_pnl_pct_7d": avg_pnl,
        }

        # Rule 1: Low win rate - tighten entry criteria
        if win_rate < THRESHOLDS["win_rate_low"]:
            # Raise minimum thresholds
            if strategy_name == "funding_arbitrage":
                adj = self._propose_adjustment(
                    strategy_name, "min_funding_rate",
                    current_params.get("min_funding_rate", 0.01),
                    direction="up", step_pct=0.15, bounds=bounds,
                    reason=f"Win rate {win_rate:.0%} below 30% threshold - raising funding rate minimum",
                    metric_trigger="win_rate", metric_value=win_rate, **context
                )
                if adj:
                    adjustments.append(adj)

            elif strategy_name == "grid_trading":
                adj = self._propose_adjustment(
                    strategy_name, "entry_threshold_pct",
                    current_params.get("entry_threshold_pct", 20),
                    direction="down", step_pct=0.15, bounds=bounds,
                    reason=f"Win rate {win_rate:.0%} below 30% - tightening entry zone (closer to range edges)",
                    metric_trigger="win_rate", metric_value=win_rate, **context
                )
                if adj:
                    adjustments.append(adj)

            elif strategy_name == "directional_momentum":
                adj = self._propose_adjustment(
                    strategy_name, "min_score",
                    current_params.get("min_score", 50),
                    direction="up", step_pct=0.10, bounds=bounds,
                    reason=f"Win rate {win_rate:.0%} below 30% - raising minimum momentum score",
                    metric_trigger="win_rate", metric_value=win_rate, **context
                )
                if adj:
                    adjustments.append(adj)

        # Rule 2: High win rate - slightly loosen to capture more signals
        elif win_rate > THRESHOLDS["win_rate_high"]:
            if strategy_name == "directional_momentum":
                adj = self._propose_adjustment(
                    strategy_name, "min_score",
                    current_params.get("min_score", 50),
                    direction="down", step_pct=0.05, bounds=bounds,
                    reason=f"Win rate {win_rate:.0%} above 70% - slightly lowering min score to capture more signals",
                    metric_trigger="win_rate", metric_value=win_rate, **context
                )
                if adj:
                    adjustments.append(adj)

            elif strategy_name == "grid_trading":
                adj = self._propose_adjustment(
                    strategy_name, "entry_threshold_pct",
                    current_params.get("entry_threshold_pct", 20),
                    direction="up", step_pct=0.05, bounds=bounds,
                    reason=f"Win rate {win_rate:.0%} above 70% - widening entry zone for more signals",
                    metric_trigger="win_rate", metric_value=win_rate, **context
                )
                if adj:
                    adjustments.append(adj)

        # Rule 3: Negative avg P&L - defensive adjustments
        if avg_pnl < -1.0:  # Losing more than 1% average per signal
            if "min_volume" in current_params:
                adj = self._propose_adjustment(
                    strategy_name, "min_volume",
                    current_params["min_volume"],
                    direction="up", step_pct=0.20, bounds=bounds,
                    reason=f"Avg P&L {avg_pnl:+.2f}% - raising volume filter to focus on liquid markets",
                    metric_trigger="avg_pnl_pct", metric_value=avg_pnl, **context
                )
                if adj:
                    adjustments.append(adj)

        # Rule 4: High expiry rate - signals expiring before resolution
        if expiry_rate > 0.50:  # More than 50% expiring
            if "expiry_hours" in current_params:
                adj = self._propose_adjustment(
                    strategy_name, "expiry_hours",
                    current_params["expiry_hours"],
                    direction="up", step_pct=0.20, bounds=bounds,
                    reason=f"Expiry rate {expiry_rate:.0%} - extending signal duration",
                    metric_trigger="expiry_rate", metric_value=expiry_rate, **context
                )
                if adj:
                    adjustments.append(adj)

        # Rule 5: Very few signals - loosen filters
        if total_signals < 10 and win_rate >= 0.40:
            if strategy_name == "directional_momentum" and "min_change_pct" in current_params:
                adj = self._propose_adjustment(
                    strategy_name, "min_change_pct",
                    current_params["min_change_pct"],
                    direction="down", step_pct=0.10, bounds=bounds,
                    reason=f"Only {total_signals} signals in 7d with {win_rate:.0%} win rate - lowering change threshold",
                    metric_trigger="total_signals", metric_value=total_signals, **context
                )
                if adj:
                    adjustments.append(adj)

            elif strategy_name == "funding_arbitrage" and "min_funding_rate" in current_params:
                adj = self._propose_adjustment(
                    strategy_name, "min_funding_rate",
                    current_params["min_funding_rate"],
                    direction="down", step_pct=0.10, bounds=bounds,
                    reason=f"Only {total_signals} signals in 7d with {win_rate:.0%} win rate - lowering funding threshold",
                    metric_trigger="total_signals", metric_value=total_signals, **context
                )
                if adj:
                    adjustments.append(adj)

        return adjustments

    def _propose_adjustment(
        self,
        strategy_name: str,
        parameter_name: str,
        current_value: float,
        direction: str,
        step_pct: float,
        bounds: Dict[str, Tuple[float, float]],
        reason: str,
        metric_trigger: str,
        metric_value: float,
        **context,
    ) -> Optional[Adjustment]:
        """
        Propose a single parameter adjustment.

        Args:
            direction: "up" or "down"
            step_pct: Percentage to adjust (0.10 = 10%)
            bounds: Min/max bounds for the parameter

        Returns:
            Adjustment if the proposed change is meaningful, None otherwise
        """
        # Cap step at max allowed
        step_pct = min(step_pct, THRESHOLDS["max_adjustment_pct"])

        if direction == "up":
            new_value = current_value * (1 + step_pct)
        else:
            new_value = current_value * (1 - step_pct)

        # Enforce bounds
        param_bounds = bounds.get(parameter_name)
        if param_bounds:
            new_value = max(param_bounds[0], min(param_bounds[1], new_value))

        # Round appropriately
        if parameter_name in ("expiry_hours", "lookback_hours", "min_score", "entry_threshold_pct"):
            new_value = round(new_value)
        elif parameter_name == "min_volume":
            new_value = round(new_value / 10_000) * 10_000  # Round to nearest $10K
        else:
            new_value = round(new_value, 6)

        # Skip if no meaningful change
        if abs(new_value - current_value) < 0.001 * abs(current_value):
            return None

        return Adjustment(
            strategy_name=strategy_name,
            parameter_name=parameter_name,
            old_value=current_value,
            new_value=new_value,
            reason=reason,
            metric_trigger=metric_trigger,
            metric_value=metric_value,
            win_rate_7d=context.get("win_rate_7d"),
            total_pnl_7d=context.get("total_pnl_7d"),
            total_signals_7d=context.get("total_signals_7d"),
            avg_pnl_pct_7d=context.get("avg_pnl_pct_7d"),
        )

    async def log_adjustments(self, adjustments: List[Adjustment]) -> List[str]:
        """
        Save proposed adjustments to Supabase.

        Returns:
            List of record IDs
        """
        if not self.supabase or not adjustments:
            return []

        ids = []
        status = "applied" if self.auto_apply else "pending"

        for adj in adjustments:
            try:
                data = {
                    "strategy_name": adj.strategy_name,
                    "parameter_name": adj.parameter_name,
                    "old_value": adj.old_value,
                    "new_value": adj.new_value,
                    "reason": adj.reason,
                    "metric_trigger": adj.metric_trigger,
                    "metric_value": adj.metric_value,
                    "win_rate_7d": adj.win_rate_7d,
                    "total_pnl_7d": adj.total_pnl_7d,
                    "total_signals_7d": adj.total_signals_7d,
                    "avg_pnl_pct_7d": adj.avg_pnl_pct_7d,
                    "status": status,
                }

                result = self.supabase.table("paper_strategy_adjustments").insert(data).execute()
                if result.data:
                    record_id = result.data[0]["id"]
                    ids.append(record_id)
                    logger.info(
                        f"[TUNER] {adj.strategy_name}.{adj.parameter_name}: "
                        f"{adj.old_value} -> {adj.new_value} ({status}) | {adj.reason}"
                    )

            except Exception as e:
                logger.error(f"Error logging adjustment: {e}")

        return ids

    async def get_pending_adjustments(self) -> List[Dict[str, Any]]:
        """Get all pending adjustments awaiting review."""
        if not self.supabase:
            return []

        try:
            result = self.supabase.table("paper_strategy_adjustments").select(
                "*"
            ).eq("status", "pending").order("created_at", desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error fetching pending adjustments: {e}")
            return []

    async def approve_adjustment(self, adjustment_id: str, notes: str = "") -> bool:
        """Approve a pending adjustment for application."""
        if not self.supabase:
            return False

        try:
            self.supabase.table("paper_strategy_adjustments").update({
                "status": "approved",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "review_notes": notes,
            }).eq("id", adjustment_id).execute()
            logger.info(f"Adjustment {adjustment_id} approved")
            return True
        except Exception as e:
            logger.error(f"Error approving adjustment: {e}")
            return False

    async def revert_adjustment(self, adjustment_id: str, notes: str = "") -> bool:
        """Revert a pending or applied adjustment."""
        if not self.supabase:
            return False

        try:
            self.supabase.table("paper_strategy_adjustments").update({
                "status": "reverted",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "review_notes": notes,
            }).eq("id", adjustment_id).execute()
            logger.info(f"Adjustment {adjustment_id} reverted")
            return True
        except Exception as e:
            logger.error(f"Error reverting adjustment: {e}")
            return False

    async def apply_approved(self) -> int:
        """
        Apply all approved adjustments to strategy instances.

        Returns the number of adjustments applied.
        """
        if not self.supabase:
            return 0

        try:
            result = self.supabase.table("paper_strategy_adjustments").select(
                "*"
            ).eq("status", "approved").execute()

            if not result.data:
                return 0

            count = 0
            for adj in result.data:
                # Mark as applied
                self.supabase.table("paper_strategy_adjustments").update({
                    "status": "applied",
                }).eq("id", adj["id"]).execute()
                count += 1

                logger.info(
                    f"[TUNER] Applied: {adj['strategy_name']}.{adj['parameter_name']}: "
                    f"{adj['old_value']} -> {adj['new_value']}"
                )

            return count

        except Exception as e:
            logger.error(f"Error applying adjustments: {e}")
            return 0

    def get_effective_params(
        self, strategy_name: str, applied_adjustments: List[Dict]
    ) -> Dict[str, float]:
        """
        Compute effective parameters after applying adjustments.

        Args:
            strategy_name: Strategy to get params for
            applied_adjustments: List of applied adjustment records

        Returns:
            Dict of parameter_name -> effective_value
        """
        defaults = {
            "funding_arbitrage": {
                "min_funding_rate": 0.01,
                "min_volume": 100_000,
                "expiry_hours": 8,
            },
            "grid_trading": {
                "lookback_hours": 72,
                "min_range_pct": 3.0,
                "max_range_pct": 15.0,
                "entry_threshold_pct": 20,
                "min_volume": 500_000,
                "expiry_hours": 24,
            },
            "directional_momentum": {
                "min_change_pct": 3.0,
                "min_volume": 500_000,
                "min_score": 50,
                "expiry_hours": 24,
            },
        }

        params = defaults.get(strategy_name, {}).copy()

        # Apply adjustments in chronological order
        relevant = [
            a for a in applied_adjustments
            if a["strategy_name"] == strategy_name and a["status"] == "applied"
        ]
        relevant.sort(key=lambda x: x.get("created_at", ""))

        for adj in relevant:
            params[adj["parameter_name"]] = adj["new_value"]

        return params

    def format_report(self, adjustments: List[Adjustment]) -> str:
        """Format adjustments as a readable report."""
        if not adjustments:
            return "No adjustments proposed - all strategies within acceptable ranges."

        lines = [
            "=" * 60,
            " STRATEGY AUTO-TUNER REPORT",
            "=" * 60,
            f" Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f" Mode: {'Auto-apply' if self.auto_apply else 'Pending review'}",
            f" Proposed: {len(adjustments)} adjustment(s)",
            "",
        ]

        # Group by strategy
        by_strategy: Dict[str, List[Adjustment]] = {}
        for adj in adjustments:
            by_strategy.setdefault(adj.strategy_name, []).append(adj)

        for strategy_name, adjs in by_strategy.items():
            lines.append(f"--- {strategy_name.upper()} ---")
            if adjs[0].win_rate_7d is not None:
                lines.append(
                    f"  7d: {adjs[0].total_signals_7d} signals | "
                    f"Win rate: {adjs[0].win_rate_7d:.0%} | "
                    f"Avg P&L: {adjs[0].avg_pnl_pct_7d:+.2f}%"
                )

            for adj in adjs:
                # Format values
                if adj.parameter_name == "min_volume":
                    old_fmt = f"${adj.old_value:,.0f}"
                    new_fmt = f"${adj.new_value:,.0f}"
                elif adj.parameter_name in ("expiry_hours", "lookback_hours", "min_score", "entry_threshold_pct"):
                    old_fmt = f"{adj.old_value:.0f}"
                    new_fmt = f"{adj.new_value:.0f}"
                else:
                    old_fmt = f"{adj.old_value:.4f}"
                    new_fmt = f"{adj.new_value:.4f}"

                arrow = ">>>" if adj.new_value > adj.old_value else "<<<"
                lines.append(f"  {adj.parameter_name}: {old_fmt} {arrow} {new_fmt}")
                lines.append(f"    Reason: {adj.reason}")

            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)
