"""
Metrics Calculator
==================
Calculates performance metrics for paper trading strategies.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np

from loguru import logger

from .base_strategy import SupabasePaperTrading, RecommendationStatus


class MetricsCalculator:
    """Calculate and store strategy performance metrics"""

    PERIODS = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "all_time": timedelta(days=3650)  # ~10 years
    }

    def __init__(self):
        self.db = SupabasePaperTrading()

    def calculate_metrics_for_strategy(self, strategy_name: str, period: str) -> Dict[str, Any]:
        """
        Calculate metrics for a strategy over a given period.

        Args:
            strategy_name: Name of the strategy
            period: One of '24h', '7d', '30d', 'all_time'

        Returns:
            Dictionary of metrics
        """
        delta = self.PERIODS.get(period, timedelta(hours=24))
        since = datetime.utcnow() - delta

        # Get recommendations for this period
        recs = self.db.get_recommendations_since(since, strategy_name)

        # Get outcomes for this period
        outcomes = self.db.get_outcomes_since(since, strategy_name)

        # Calculate metrics
        total_signals = len(recs)
        still_active = sum(1 for r in recs if r.status == RecommendationStatus.ACTIVE)

        wins = 0
        losses = 0
        pnls = []
        win_pnls = []
        loss_pnls = []
        durations = []
        best_pnl = None
        worst_pnl = None

        for outcome in outcomes:
            pnl = float(outcome.get("pnl_pct", 0))
            pnls.append(pnl)
            durations.append(outcome.get("hold_duration_minutes", 0))

            if pnl >= 0:
                wins += 1
                win_pnls.append(pnl)
            else:
                losses += 1
                loss_pnls.append(pnl)

            if best_pnl is None or pnl > best_pnl:
                best_pnl = pnl
            if worst_pnl is None or pnl < worst_pnl:
                worst_pnl = pnl

        # Calculate derived metrics
        completed = wins + losses
        win_rate = (wins / completed * 100) if completed > 0 else None
        avg_pnl = np.mean(pnls) if pnls else None
        total_pnl = sum(pnls) if pnls else 0

        # Profit factor
        gross_profit = sum(win_pnls) if win_pnls else 0
        gross_loss = abs(sum(loss_pnls)) if loss_pnls else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

        # Sharpe ratio (simplified, using 0 as risk-free rate)
        if pnls and len(pnls) >= 2:
            returns = np.array(pnls)
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(365) if np.std(returns) > 0 else None
        else:
            sharpe = None

        # Max drawdown
        max_drawdown = None
        if pnls:
            cumulative = np.cumsum(pnls)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = cumulative - running_max
            max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else None

        # Average hold duration
        avg_duration = np.mean(durations) if durations else None

        # Position size assumed $1000
        total_pnl_usd = (total_pnl / 100) * 1000 if total_pnl else 0

        metrics = {
            "strategy_name": strategy_name,
            "period": period,
            "updated_at": datetime.utcnow().isoformat(),
            "total_signals": total_signals,
            "wins": wins,
            "losses": losses,
            "still_active": still_active,
            "win_rate": round(win_rate, 2) if win_rate is not None else None,
            "avg_pnl_pct": round(avg_pnl, 4) if avg_pnl is not None else None,
            "total_pnl_pct": round(total_pnl, 4) if total_pnl else 0,
            "total_pnl_usd": round(total_pnl_usd, 2),
            "profit_factor": round(profit_factor, 4) if profit_factor is not None else None,
            "sharpe_ratio": round(sharpe, 4) if sharpe is not None else None,
            "max_drawdown_pct": round(max_drawdown, 4) if max_drawdown is not None else None,
            "avg_hold_duration_minutes": round(avg_duration, 2) if avg_duration is not None else None,
            "best_trade_pnl_pct": round(best_pnl, 4) if best_pnl is not None else None,
            "worst_trade_pnl_pct": round(worst_pnl, 4) if worst_pnl is not None else None,
        }

        return metrics

    def update_all_metrics(self, strategy_names: List[str]) -> Dict[str, List[Dict]]:
        """
        Update metrics for all strategies across all periods.

        Args:
            strategy_names: List of strategy names to update

        Returns:
            Dictionary of strategy_name -> list of period metrics
        """
        results = {}

        for strategy in strategy_names:
            results[strategy] = []
            for period in self.PERIODS.keys():
                try:
                    metrics = self.calculate_metrics_for_strategy(strategy, period)
                    self.db.upsert_metrics(metrics)
                    results[strategy].append(metrics)
                    logger.info(f"Updated metrics: {strategy} {period}")
                except Exception as e:
                    logger.error(f"Error calculating metrics for {strategy} {period}: {e}")

        return results

    def get_combined_metrics(self, strategy_names: List[str], period: str = "24h") -> Dict[str, Any]:
        """Get combined metrics across all strategies"""
        all_metrics = []

        for strategy in strategy_names:
            metrics = self.calculate_metrics_for_strategy(strategy, period)
            all_metrics.append(metrics)

        if not all_metrics:
            return {}

        # Aggregate
        total_signals = sum(m["total_signals"] for m in all_metrics)
        total_wins = sum(m["wins"] for m in all_metrics)
        total_losses = sum(m["losses"] for m in all_metrics)
        total_active = sum(m["still_active"] for m in all_metrics)
        total_pnl = sum(m["total_pnl_pct"] or 0 for m in all_metrics)
        total_pnl_usd = sum(m["total_pnl_usd"] or 0 for m in all_metrics)

        completed = total_wins + total_losses
        overall_win_rate = (total_wins / completed * 100) if completed > 0 else None

        # Find best strategy
        best_strategy = max(all_metrics, key=lambda m: m["total_pnl_pct"] or 0)

        return {
            "period": period,
            "total_signals": total_signals,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "total_active": total_active,
            "overall_win_rate": round(overall_win_rate, 1) if overall_win_rate else None,
            "total_pnl_pct": round(total_pnl, 2),
            "total_pnl_usd": round(total_pnl_usd, 2),
            "best_strategy": best_strategy["strategy_name"],
            "strategy_metrics": all_metrics
        }

    def format_review_report(self, strategy_names: List[str], period: str = "24h") -> str:
        """Generate a formatted review report"""

        combined = self.get_combined_metrics(strategy_names, period)

        if not combined:
            return "No data available for review."

        delta = self.PERIODS.get(period, timedelta(hours=24))
        since = datetime.utcnow() - delta
        now = datetime.utcnow()

        lines = [
            "=== PAPER TRADING REVIEW ===",
            f"Period: {since.strftime('%Y-%m-%d %H:%M')} to {now.strftime('%Y-%m-%d %H:%M')} ({period})",
            ""
        ]

        # Per-strategy metrics
        for metrics in combined.get("strategy_metrics", []):
            strategy = metrics["strategy_name"]
            lines.append(strategy.upper())

            win_rate_str = f"{metrics['win_rate']:.1f}%" if metrics['win_rate'] else "N/A"
            avg_pnl_str = f"{metrics['avg_pnl_pct']:+.2f}%" if metrics['avg_pnl_pct'] else "N/A"

            lines.append(f"  Signals: {metrics['total_signals']}")
            lines.append(f"  Wins: {metrics['wins']} ({win_rate_str})")
            lines.append(f"  Losses: {metrics['losses']}")
            lines.append(f"  Active: {metrics['still_active']}")
            lines.append(f"  Avg P&L: {avg_pnl_str}")

            if metrics['best_trade_pnl_pct'] is not None:
                lines.append(f"  Best: {metrics['best_trade_pnl_pct']:+.2f}%")
            if metrics['worst_trade_pnl_pct'] is not None:
                lines.append(f"  Worst: {metrics['worst_trade_pnl_pct']:+.2f}%")

            lines.append("")

        # Combined metrics
        lines.append("COMBINED")
        lines.append(f"  Total Signals: {combined['total_signals']}")
        overall_wr = f"{combined['overall_win_rate']:.1f}%" if combined['overall_win_rate'] else "N/A"
        lines.append(f"  Overall Win Rate: {overall_wr}")
        lines.append(f"  Total P&L: {combined['total_pnl_pct']:+.2f}% (${combined['total_pnl_usd']:+.2f})")
        lines.append(f"  Best Strategy: {combined['best_strategy']}")

        return "\n".join(lines)

    def format_telegram_summary(self, strategy_names: List[str], period: str = "24h") -> str:
        """Generate Telegram-formatted summary"""

        combined = self.get_combined_metrics(strategy_names, period)

        if not combined:
            return "*PAPER TRADING*: No data available"

        lines = [f"*PAPER TRADING SUMMARY* ({period})", ""]

        for metrics in combined.get("strategy_metrics", []):
            strategy = metrics["strategy_name"].replace("_", " ").title()
            win_rate = f"{metrics['win_rate']:.0f}%" if metrics['win_rate'] else "-"
            pnl = metrics['total_pnl_pct'] or 0

            lines.append(f"*{strategy}*")
            lines.append(f"  {metrics['wins']}W/{metrics['losses']}L ({win_rate}) | {pnl:+.1f}%")

        lines.append("")
        lines.append(f"*Combined*: {combined['total_pnl_pct']:+.1f}% (${combined['total_pnl_usd']:+.0f})")

        return "\n".join(lines)
