"""
Enhanced Metrics Calculator
=============================
Extends the paper trading MetricsCalculator with quantpylib-powered analytics.

Adds:
- Sharpe ratio, Sortino ratio, CAGR
- Maximum drawdown with rolling analysis
- VaR/CVaR (95%)
- Omega ratio, gain-to-pain
- Strategy comparison matrix
- Statistical significance indicators
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

from .performance_bridge import PerformanceAnalyzer


class EnhancedMetricsCalculator:
    """
    Enhanced metrics calculator that uses quantpylib performance analytics.

    Drop-in upgrade for the existing MetricsCalculator with richer metrics.
    """

    PERIODS = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "all_time": None,
    }

    def __init__(self, granularity: str = "hourly"):
        self.analyzer = PerformanceAnalyzer(granularity=granularity)
        self.supabase = self._init_supabase()

    def _init_supabase(self) -> Optional[Any]:
        if not HAS_SUPABASE:
            return None
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            return None
        return create_client(url, key)

    async def calculate_enhanced_metrics(
        self,
        strategy_name: Optional[str] = None,
        period: str = "all_time",
    ) -> Dict[str, Any]:
        """
        Calculate enhanced metrics for a strategy using quantpylib analytics.

        Args:
            strategy_name: Filter to specific strategy (None = all)
            period: Time period ("24h", "7d", "30d", "all_time")

        Returns:
            Dict with comprehensive performance metrics
        """
        if not self.supabase:
            return {"error": "Database not configured"}

        period_delta = self.PERIODS.get(period)
        outcomes = await self._fetch_outcomes(strategy_name, period_delta)

        if not outcomes:
            return {"strategy": strategy_name, "period": period, "metrics": {}}

        # Convert outcomes to return series
        returns = PerformanceAnalyzer.returns_from_pnl_records(outcomes)

        if len(returns) < 2:
            return {"strategy": strategy_name, "period": period, "metrics": {}}

        # Run full analysis
        metrics = self.analyzer.analyze_returns(returns)

        # Add trade-level stats
        metrics["total_outcomes"] = len(outcomes)
        metrics["wins"] = sum(1 for o in outcomes if o.get("outcome_type") == "TARGET_HIT")
        metrics["losses"] = sum(
            1 for o in outcomes
            if o.get("outcome_type") in ("STOPPED", "EXPIRED")
        )
        metrics["avg_hold_minutes"] = (
            sum(int(o.get("hold_duration_minutes", 0)) for o in outcomes) / len(outcomes)
            if outcomes else 0
        )

        return {
            "strategy": strategy_name or "all",
            "period": period,
            "metrics": metrics,
        }

    async def compare_all_strategies(
        self, period: str = "30d"
    ) -> Dict[str, Any]:
        """
        Compare all strategies side-by-side with quantpylib metrics.

        Returns:
            Dict with strategy comparison data
        """
        if not self.supabase:
            return {"error": "Database not configured"}

        strategies = await self._get_strategy_names()
        comparison = {}

        for name in strategies:
            result = await self.calculate_enhanced_metrics(
                strategy_name=name, period=period
            )
            comparison[name] = result.get("metrics", {})

        return {
            "period": period,
            "strategies": comparison,
            "best_sharpe": max(
                comparison.items(),
                key=lambda x: x[1].get("sharpe", 0),
                default=(None, {})
            )[0],
            "best_win_rate": max(
                comparison.items(),
                key=lambda x: x[1].get("win_rate", 0),
                default=(None, {})
            )[0],
        }

    async def save_enhanced_metrics(
        self,
        strategy_name: str,
        period: str,
        metrics: Dict[str, Any],
    ) -> bool:
        """Save enhanced metrics to Supabase."""
        if not self.supabase:
            return False

        try:
            now = datetime.now(timezone.utc)
            period_delta = self.PERIODS.get(period)
            period_start = (
                (now - period_delta) if period_delta
                else datetime(2020, 1, 1, tzinfo=timezone.utc)
            )

            data = {
                "strategy_name": strategy_name,
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "total_recommendations": metrics.get("total_outcomes", 0),
                "winning_trades": metrics.get("wins", 0),
                "losing_trades": metrics.get("losses", 0),
                "total_pnl_pct": metrics.get("cum_ret", 1.0) * 100 - 100,
                "avg_pnl_pct": metrics.get("mean_ret", 0) * 100,
                "max_win_pct": 0,  # Would need individual trade data
                "max_loss_pct": metrics.get("max_dd", 0) * 100,
                "avg_hold_duration_minutes": int(metrics.get("avg_hold_minutes", 0)),
                "win_rate": metrics.get("win_rate", 0) * 100,
                "profit_factor": metrics.get("profit_factor", 0),
            }

            self.supabase.table("paper_strategy_metrics").insert(data).execute()
            return True

        except Exception as e:
            logger.error(f"Error saving enhanced metrics: {e}")
            return False

    async def _fetch_outcomes(
        self,
        strategy_name: Optional[str],
        period_delta: Optional[timedelta],
    ) -> List[Dict[str, Any]]:
        """Fetch outcome records from Supabase."""
        if not self.supabase:
            return []

        try:
            # First get recommendation IDs for this strategy/period
            query = self.supabase.table("paper_recommendations").select("id")

            if strategy_name:
                query = query.eq("strategy_name", strategy_name)

            if period_delta:
                start_time = datetime.now(timezone.utc) - period_delta
                query = query.gte("created_at", start_time.isoformat())

            recs_result = query.execute()
            if not recs_result.data:
                return []

            rec_ids = [r["id"] for r in recs_result.data]

            # Fetch outcomes
            outcomes_result = self.supabase.table(
                "paper_recommendation_outcomes"
            ).select("*").in_("recommendation_id", rec_ids).execute()

            return outcomes_result.data or []

        except Exception as e:
            logger.error(f"Error fetching outcomes: {e}")
            return []

    async def _get_strategy_names(self) -> List[str]:
        """Get unique strategy names."""
        if not self.supabase:
            return []
        try:
            result = self.supabase.table("paper_recommendations").select(
                "strategy_name"
            ).execute()
            return list(set(r["strategy_name"] for r in result.data)) if result.data else []
        except Exception as e:
            logger.error(f"Error fetching strategy names: {e}")
            return []

    def format_enhanced_report(self, data: Dict[str, Any]) -> str:
        """Format enhanced metrics as ASCII report."""
        metrics = data.get("metrics", {})
        strategy = data.get("strategy", "Unknown")
        period = data.get("period", "all_time")

        if not metrics:
            return f"No data for {strategy} ({period})"

        lines = [
            f"=== ENHANCED METRICS: {strategy.upper()} ({period}) ===",
            "",
            "RETURNS",
            f"  Sharpe Ratio:     {metrics.get('sharpe', 0):.4f}",
            f"  Sortino Ratio:    {metrics.get('sortino', 0):.4f}",
            f"  CAGR:             {metrics.get('cagr', 0):.2%}",
            f"  Mean Return (ann):{metrics.get('mean_ret', 0):.2%}",
            f"  Std Dev (ann):    {metrics.get('stdev_ret', 0):.2%}",
            "",
            "RISK",
            f"  Max Drawdown:     {metrics.get('max_dd', 0):.2%}",
            f"  VaR (95%):        {metrics.get('VaR95', 0):.4%}",
            f"  CVaR (95%):       {metrics.get('cVaR95', 0):.4%}",
            "",
            "QUALITY",
            f"  Win Rate:         {metrics.get('win_rate', 0):.1%}",
            f"  Profit Factor:    {metrics.get('profit_factor', 0):.2f}",
            f"  Omega Ratio:      {metrics.get('omega', 0):.2f}",
            f"  Gain-to-Pain:     {metrics.get('gain_to_pain', 0):.2f}",
            "",
            "DISTRIBUTION",
            f"  Skewness:         {metrics.get('skew_ret', 0):.4f}",
            f"  Excess Kurtosis:  {metrics.get('kurt_exc', 0):.4f}",
            "",
            f"  Total Trades:     {metrics.get('total_outcomes', 0)}",
            f"  W/L:              {metrics.get('wins', 0)}/{metrics.get('losses', 0)}",
            f"  Avg Hold:         {int(metrics.get('avg_hold_minutes', 0))}m",
        ]

        return "\n".join(lines)
