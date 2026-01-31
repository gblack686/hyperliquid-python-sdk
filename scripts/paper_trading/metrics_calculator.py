"""
Metrics Calculator Module
=========================
Calculates and stores performance metrics for paper trading strategies.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate and store strategy performance metrics"""

    PERIODS = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "all_time": None,  # No time filter
    }

    def __init__(self):
        """Initialize metrics calculator"""
        self.supabase = self._init_supabase()

    def _init_supabase(self) -> Optional[Client]:
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            logger.warning("Supabase credentials not found")
            return None

        return create_client(url, key)

    async def calculate_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate metrics for all strategies and periods.

        Returns:
            Dict of {strategy_name: {period: metrics}}
        """
        if not self.supabase:
            return {}

        strategies = await self._get_strategy_names()
        results = {}

        for strategy in strategies:
            results[strategy] = {}
            for period_name, period_delta in self.PERIODS.items():
                metrics = await self.calculate_metrics(strategy, period_name, period_delta)
                if metrics:
                    results[strategy][period_name] = metrics
                    await self._save_metrics(strategy, period_name, metrics)

        return results

    async def _get_strategy_names(self) -> List[str]:
        """Get unique strategy names from recommendations"""
        if not self.supabase:
            return []

        try:
            result = self.supabase.table("paper_recommendations").select(
                "strategy_name"
            ).execute()

            strategies = set(r["strategy_name"] for r in result.data) if result.data else set()
            return list(strategies)

        except Exception as e:
            logger.error(f"Error getting strategy names: {e}")
            return []

    async def calculate_metrics(
        self,
        strategy_name: str,
        period_name: str,
        period_delta: Optional[timedelta]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate metrics for a specific strategy and period.

        Args:
            strategy_name: Name of the strategy
            period_name: Period identifier (24h, 7d, etc.)
            period_delta: Time delta for the period (None for all_time)

        Returns:
            Dict of calculated metrics
        """
        if not self.supabase:
            return None

        try:
            # Build query for recommendations
            query = self.supabase.table("paper_recommendations").select("*").eq(
                "strategy_name", strategy_name
            )

            if period_delta:
                start_time = datetime.now(timezone.utc) - period_delta
                query = query.gte("created_at", start_time.isoformat())

            recs_result = query.execute()
            recommendations = recs_result.data or []

            if not recommendations:
                return None

            # Get outcomes for these recommendations
            rec_ids = [r["id"] for r in recommendations]
            outcomes_result = self.supabase.table("paper_recommendation_outcomes").select(
                "*"
            ).in_("recommendation_id", rec_ids).execute()
            outcomes = outcomes_result.data or []

            # Calculate metrics
            total_signals = len(recommendations)
            active = sum(1 for r in recommendations if r["status"] == "ACTIVE")
            completed = [o for o in outcomes]

            wins = sum(1 for o in completed if o["outcome_type"] == "TARGET_HIT")
            losses = sum(1 for o in completed if o["outcome_type"] in ["STOPPED", "EXPIRED"])

            # PnL calculations
            total_pnl_pct = sum(float(o.get("pnl_pct", 0)) for o in completed)
            total_pnl_amount = sum(float(o.get("pnl_usd", 0)) for o in completed)

            # Win rate
            completed_count = wins + losses
            win_rate = (wins / completed_count * 100) if completed_count > 0 else 0

            # Average PnL
            avg_pnl_pct = total_pnl_pct / completed_count if completed_count > 0 else 0

            # Best and worst trades
            pnl_values = [float(o.get("pnl_pct", 0)) for o in completed]
            best_trade = max(pnl_values) if pnl_values else 0
            worst_trade = min(pnl_values) if pnl_values else 0

            # Profit factor (gross profit / gross loss)
            gross_profit = sum(float(o.get("pnl_usd", 0)) for o in completed if float(o.get("pnl_usd", 0)) > 0)
            gross_loss = abs(sum(float(o.get("pnl_usd", 0)) for o in completed if float(o.get("pnl_usd", 0)) < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit if gross_profit > 0 else 0

            # Average hold duration
            hold_durations = [int(o.get("hold_duration_minutes", 0)) for o in completed]
            avg_hold_duration = sum(hold_durations) / len(hold_durations) if hold_durations else 0

            return {
                "total_signals": total_signals,
                "wins": wins,
                "losses": losses,
                "active": active,
                "win_rate": round(win_rate, 2),
                "total_pnl_pct": round(total_pnl_pct, 4),
                "total_pnl_amount": round(total_pnl_amount, 2),
                "avg_pnl_pct": round(avg_pnl_pct, 4),
                "best_trade_pnl": round(best_trade, 4),
                "worst_trade_pnl": round(worst_trade, 4),
                "profit_factor": round(profit_factor, 2),
                "avg_hold_duration_minutes": int(avg_hold_duration),
            }

        except Exception as e:
            logger.error(f"Error calculating metrics for {strategy_name}/{period_name}: {e}")
            return None

    async def _save_metrics(
        self,
        strategy_name: str,
        period: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """Save or update metrics in database"""
        if not self.supabase:
            return False

        try:
            now = datetime.now(timezone.utc)
            period_delta = self.PERIODS.get(period)
            period_start = (now - period_delta) if period_delta else datetime(2020, 1, 1, tzinfo=timezone.utc)

            # Map our metrics to existing schema
            data = {
                "strategy_name": strategy_name,
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "total_recommendations": metrics.get("total_signals", 0),
                "winning_trades": metrics.get("wins", 0),
                "losing_trades": metrics.get("losses", 0),
                "total_pnl_pct": metrics.get("total_pnl_pct", 0),
                "avg_pnl_pct": metrics.get("avg_pnl_pct", 0),
                "max_win_pct": metrics.get("best_trade_pnl", 0),
                "max_loss_pct": metrics.get("worst_trade_pnl", 0),
                "avg_hold_duration_minutes": metrics.get("avg_hold_duration_minutes", 0),
                "win_rate": metrics.get("win_rate", 0),
                "profit_factor": metrics.get("profit_factor", 0),
            }

            # Insert new record (existing schema doesn't have unique constraint)
            self.supabase.table("paper_strategy_metrics").insert(data).execute()

            logger.debug(f"Saved metrics for {strategy_name}/{period}")
            return True

        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
            return False

    async def get_daily_review(self) -> Dict[str, Any]:
        """
        Generate 24-hour review report.

        Returns:
            Dict with review data for all strategies
        """
        if not self.supabase:
            return {"error": "Database not configured"}

        try:
            now = datetime.now(timezone.utc)
            yesterday = now - timedelta(hours=24)

            # Get recommendations from last 24h
            result = self.supabase.table("paper_recommendations").select("*").gte(
                "created_at", yesterday.isoformat()
            ).order("strategy_name").order("created_at", desc=True).execute()

            recommendations = result.data or []

            if not recommendations:
                return {
                    "period_start": yesterday.isoformat(),
                    "period_end": now.isoformat(),
                    "strategies": {},
                    "combined": {"total_signals": 0},
                }

            # Get outcomes
            rec_ids = [r["id"] for r in recommendations]
            outcomes_result = self.supabase.table("paper_recommendation_outcomes").select(
                "*"
            ).in_("recommendation_id", rec_ids).execute()
            outcomes = outcomes_result.data or []

            # Map outcomes to recommendation IDs
            outcome_map = {o["recommendation_id"]: o for o in outcomes}

            # Group by strategy
            strategies = {}
            for rec in recommendations:
                strategy = rec["strategy_name"]
                if strategy not in strategies:
                    strategies[strategy] = {
                        "signals": 0,
                        "wins": 0,
                        "losses": 0,
                        "active": 0,
                        "total_pnl_pct": 0,
                        "total_pnl_amount": 0,
                        "best_trade": None,
                        "worst_trade": None,
                        "recommendations": [],
                    }

                strategies[strategy]["signals"] += 1

                if rec["status"] == "ACTIVE":
                    strategies[strategy]["active"] += 1
                else:
                    outcome = outcome_map.get(rec["id"])
                    if outcome:
                        pnl_pct = float(outcome.get("pnl_pct", 0))
                        pnl_amount = float(outcome.get("pnl_usd", 0))

                        strategies[strategy]["total_pnl_pct"] += pnl_pct
                        strategies[strategy]["total_pnl_amount"] += pnl_amount

                        if outcome["outcome_type"] == "TARGET_HIT":
                            strategies[strategy]["wins"] += 1
                        else:
                            strategies[strategy]["losses"] += 1

                        # Track best/worst
                        if strategies[strategy]["best_trade"] is None or pnl_pct > strategies[strategy]["best_trade"]["pnl_pct"]:
                            strategies[strategy]["best_trade"] = {
                                "symbol": rec["symbol"],
                                "direction": rec["direction"],
                                "pnl_pct": pnl_pct,
                            }

                        if strategies[strategy]["worst_trade"] is None or pnl_pct < strategies[strategy]["worst_trade"]["pnl_pct"]:
                            strategies[strategy]["worst_trade"] = {
                                "symbol": rec["symbol"],
                                "direction": rec["direction"],
                                "pnl_pct": pnl_pct,
                            }

                strategies[strategy]["recommendations"].append(rec)

            # Calculate win rates and averages
            for strategy in strategies.values():
                completed = strategy["wins"] + strategy["losses"]
                strategy["win_rate"] = (strategy["wins"] / completed * 100) if completed > 0 else 0
                strategy["avg_pnl_pct"] = (strategy["total_pnl_pct"] / completed) if completed > 0 else 0

            # Combined stats
            combined = {
                "total_signals": sum(s["signals"] for s in strategies.values()),
                "total_wins": sum(s["wins"] for s in strategies.values()),
                "total_losses": sum(s["losses"] for s in strategies.values()),
                "total_active": sum(s["active"] for s in strategies.values()),
                "total_pnl_amount": sum(s["total_pnl_amount"] for s in strategies.values()),
            }
            combined_completed = combined["total_wins"] + combined["total_losses"]
            combined["overall_win_rate"] = (combined["total_wins"] / combined_completed * 100) if combined_completed > 0 else 0

            # Find best strategy
            if strategies:
                best_strategy = max(strategies.items(), key=lambda x: x[1]["total_pnl_amount"])
                combined["best_strategy"] = best_strategy[0]
            else:
                combined["best_strategy"] = None

            return {
                "period_start": yesterday.isoformat(),
                "period_end": now.isoformat(),
                "strategies": strategies,
                "combined": combined,
            }

        except Exception as e:
            logger.error(f"Error generating daily review: {e}")
            return {"error": str(e)}

    def format_review_report(self, review: Dict[str, Any]) -> str:
        """Format review data as text report (ASCII only)"""
        if "error" in review:
            return f"Error: {review['error']}"

        lines = [
            "=== PAPER TRADING 24H REVIEW ===",
            f"Period: {review['period_start'][:16]} to {review['period_end'][:16]}",
            "",
        ]

        strategies = review.get("strategies", {})

        for name, data in strategies.items():
            display_name = name.upper().replace("_", " ")
            completed = data["wins"] + data["losses"]

            lines.extend([
                display_name,
                f"+-- Signals: {data['signals']}",
                f"+-- Wins: {data['wins']} ({data['win_rate']:.1f}%)" if completed > 0 else f"+-- Wins: 0",
                f"+-- Losses: {data['losses']}",
                f"+-- Active: {data['active']}",
                f"+-- Avg P&L: {data['avg_pnl_pct']:+.2f}%" if completed > 0 else "+-- Avg P&L: N/A",
            ])

            if data["best_trade"]:
                lines.append(f"+-- Best: {data['best_trade']['symbol']} {data['best_trade']['direction']} {data['best_trade']['pnl_pct']:+.1f}%")

            lines.append("")

        # Combined stats
        combined = review.get("combined", {})
        lines.extend([
            "COMBINED",
            f"+-- Total Signals: {combined.get('total_signals', 0)}",
            f"+-- Overall Win Rate: {combined.get('overall_win_rate', 0):.0f}%",
            f"+-- Total P&L: ${combined.get('total_pnl_amount', 0):+.2f}",
            f"+-- Best Strategy: {combined.get('best_strategy', 'N/A')}",
        ])

        return "\n".join(lines)
