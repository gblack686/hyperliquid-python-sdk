"""
Base Strategy Module
====================
Provides the base class and data structures for paper trading strategies.
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional, Dict, Any

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RecommendationStatus(Enum):
    """Status of a trading recommendation"""
    ACTIVE = "ACTIVE"
    TARGET_HIT = "TARGET_HIT"
    STOPPED = "STOPPED"
    EXPIRED = "EXPIRED"


# Strategy display names (ASCII only, no emoji)
STRATEGY_DISPLAY = {
    "funding_arbitrage": "FUNDING ARBITRAGE",
    "grid_trading": "GRID TRADING",
    "directional_momentum": "MOMENTUM SIGNAL",
}


@dataclass
class Recommendation:
    """Trading recommendation from a strategy agent"""
    strategy_name: str
    symbol: str
    direction: str  # LONG, SHORT, HOLD
    entry_price: float
    target_price_1: float
    stop_loss_price: float
    confidence_score: int  # 0-100
    expires_at: datetime
    position_size: float = 1000.0
    strategy_params: Dict[str, Any] = field(default_factory=dict)

    # Set after saving
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    status: str = "ACTIVE"

    @property
    def target_pct(self) -> float:
        """Calculate target percentage from entry"""
        if self.entry_price == 0:
            return 0
        return ((self.target_price_1 - self.entry_price) / self.entry_price) * 100

    @property
    def stop_pct(self) -> float:
        """Calculate stop loss percentage from entry"""
        if self.entry_price == 0:
            return 0
        return ((self.stop_loss_price - self.entry_price) / self.entry_price) * 100

    @property
    def risk_reward(self) -> float:
        """Calculate risk/reward ratio"""
        risk = abs(self.stop_pct)
        reward = abs(self.target_pct)
        if risk == 0:
            return 0
        return reward / risk

    def format_telegram_signal(self) -> str:
        """Format recommendation as enhanced Telegram message (ASCII only)"""
        display_name = STRATEGY_DISPLAY.get(self.strategy_name, self.strategy_name.upper())

        # Basic info
        target_pct = self.target_pct
        stop_pct = self.stop_pct
        rr = self.risk_reward

        # Calculate expiry hours
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        expiry_hours = max(0, (expires - now).total_seconds() / 3600)

        # Base message
        lines = [
            f"[PAPER] {display_name}",
            "-" * 20,
            f"{self.symbol} {self.direction} | Confidence: {self.confidence_score}/100",
            "",
            f"Entry: ${self.entry_price:,.4f}",
            f"Target: ${self.target_price_1:,.4f} ({target_pct:+.1f}%)",
            f"Stop: ${self.stop_loss_price:,.4f} ({stop_pct:+.1f}%)",
            f"R:R: {rr:.1f}x",
        ]

        # Strategy-specific data
        params = self.strategy_params

        if self.strategy_name == "funding_arbitrage":
            funding_8h = params.get("funding_8h", 0)
            funding_apy = params.get("funding_apy", 0)
            open_interest = params.get("open_interest", 0)

            lines.extend([
                "",
                "FUNDING DATA:",
                f"  8h Rate: {funding_8h:+.4f}%",
                f"  APY: {funding_apy:+.1f}%",
                f"  OI: ${open_interest/1e6:.1f}M" if open_interest > 0 else "  OI: N/A",
                "",
                "Strategy: Collect funding payments",
            ])

        elif self.strategy_name == "grid_trading":
            range_low = params.get("range_low", 0)
            range_high = params.get("range_high", 0)
            range_pct = params.get("range_pct", 0)
            position_in_range = params.get("position_in_range", 50)
            rsi = params.get("rsi")

            lines.extend([
                "",
                "RANGE DATA:",
                f"  Range: ${range_low:,.2f} - ${range_high:,.2f} ({range_pct:.1f}%)",
                f"  Position: {'At range LOW' if position_in_range < 30 else 'At range HIGH' if position_in_range > 70 else 'Mid range'} ({position_in_range:.0f}%)",
                f"  RSI(14): {rsi:.0f}" + (" (oversold)" if rsi and rsi < 30 else " (overbought)" if rsi and rsi > 70 else "") if rsi else "  RSI: N/A",
                "",
                "Strategy: Mean reversion to range mid",
            ])

        elif self.strategy_name == "directional_momentum":
            change_24h = params.get("change_24h", 0)
            score = params.get("score", 0)
            rsi = params.get("rsi")
            ema_status = params.get("ema_status", "N/A")
            volume_ratio = params.get("volume_ratio")

            lines.extend([
                "",
                "MOMENTUM DATA:",
                f"  24h Change: {change_24h:+.1f}%",
                f"  Score: {score}/100",
                f"  RSI(14): {rsi:.0f}" if rsi else "  RSI: N/A",
                f"  EMA: {ema_status}",
                f"  Volume: {volume_ratio:.1f}x avg" if volume_ratio else "  Volume: N/A",
                "",
                "Strategy: Trend following",
            ])

        lines.append(f"Expires: {expiry_hours:.0f}h")

        return "\n".join(lines)

    def format_telegram_outcome(self, outcome_type: str, exit_price: float,
                                 pnl_pct: float, pnl_amount: float,
                                 hold_duration_minutes: int) -> str:
        """Format outcome as enhanced Telegram message (ASCII only)"""
        display_name = STRATEGY_DISPLAY.get(self.strategy_name, self.strategy_name.upper())

        # Outcome icons (ASCII only)
        outcome_icons = {
            "TARGET_HIT": "[OK]",
            "STOPPED": "[-]",
            "EXPIRED": "[!]",
        }
        icon = outcome_icons.get(outcome_type, "[?]")

        # Duration formatting
        hours = hold_duration_minutes // 60
        minutes = hold_duration_minutes % 60
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        # Base message
        lines = [
            f"[RESULT] {display_name}",
            "-" * 20,
            f"{self.symbol} {self.direction} -> {outcome_type.replace('_', ' ')} {icon}",
            "",
            f"P&L: {pnl_pct:+.2f}% (${pnl_amount:+.2f})",
            f"Duration: {duration_str}",
            f"Exit: ${exit_price:,.4f}",
        ]

        # Original setup from strategy_params
        params = self.strategy_params
        lines.append("")
        lines.append("Original Setup:")

        if self.strategy_name == "funding_arbitrage":
            funding_8h = params.get("funding_8h", 0)
            lines.extend([
                f"  8h Funding: {funding_8h:+.4f}%",
                f"  Entry: ${self.entry_price:,.4f}",
            ])

        elif self.strategy_name == "grid_trading":
            range_low = params.get("range_low", 0)
            range_high = params.get("range_high", 0)
            position_in_range = params.get("position_in_range", 50)
            rsi = params.get("rsi")
            lines.extend([
                f"  Range: ${range_low:,.2f} - ${range_high:,.2f}",
                f"  Position: {position_in_range:.0f}% of range",
                f"  RSI: {rsi:.0f}" if rsi else "  RSI: N/A",
            ])

        elif self.strategy_name == "directional_momentum":
            change_24h = params.get("change_24h", 0)
            score = params.get("score", 0)
            rsi = params.get("rsi")
            lines.extend([
                f"  24h Change: {change_24h:+.1f}%",
                f"  Score: {score}/100",
                f"  RSI: {rsi:.0f}" if rsi else "  RSI: N/A",
            ])

        # Contextual note based on outcome
        lines.append("")
        if outcome_type == "TARGET_HIT":
            lines.append("Target reached successfully")
        elif outcome_type == "STOPPED":
            if self.strategy_name == "grid_trading":
                lines.append("Range broke down - trend shift?")
            else:
                lines.append("Stop loss triggered")
        elif outcome_type == "EXPIRED":
            lines.append("Signal expired without hitting target or stop")

        return "\n".join(lines)


class BaseStrategy(ABC):
    """Base class for all paper trading strategies"""

    def __init__(self, name: str, expiry_hours: int = 24):
        """
        Initialize strategy.

        Args:
            name: Strategy name (e.g., 'funding_arbitrage')
            expiry_hours: Hours until recommendations expire
        """
        self.name = name
        self.expiry_hours = expiry_hours
        self.supabase = self._init_supabase()

    def _init_supabase(self) -> Optional[Client]:
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            logger.warning("Supabase credentials not found - database features disabled")
            return None

        return create_client(url, key)

    @abstractmethod
    async def generate_recommendations(self) -> List[Recommendation]:
        """
        Generate trading recommendations.
        Must be implemented by each strategy.

        Returns:
            List of Recommendation objects
        """
        pass

    @abstractmethod
    async def get_top_symbols(self, limit: int = 10) -> List[str]:
        """
        Get top symbols to analyze.

        Args:
            limit: Number of symbols to return

        Returns:
            List of symbol names
        """
        pass

    async def run(self) -> List[Recommendation]:
        """
        Run the strategy and save recommendations.

        Returns:
            List of saved recommendations
        """
        logger.info(f"[{self.name}] Running strategy...")

        try:
            recommendations = await self.generate_recommendations()

            if not recommendations:
                logger.info(f"[{self.name}] No recommendations generated")
                return []

            # Save to database
            saved = []
            for rec in recommendations:
                saved_rec = await self.save_recommendation(rec)
                if saved_rec:
                    saved.append(saved_rec)

            logger.info(f"[{self.name}] Saved {len(saved)} recommendations")
            return saved

        except Exception as e:
            logger.error(f"[{self.name}] Strategy error: {e}")
            raise

    async def save_recommendation(self, rec: Recommendation) -> Optional[Recommendation]:
        """Save recommendation to Supabase"""
        if not self.supabase:
            logger.warning("Cannot save - Supabase not configured")
            return rec

        try:
            data = {
                "strategy_name": rec.strategy_name,
                "symbol": rec.symbol,
                "direction": rec.direction,
                "entry_price": float(rec.entry_price),
                "target_price_1": float(rec.target_price_1),
                "stop_loss_price": float(rec.stop_loss_price),
                "confidence_score": rec.confidence_score,
                "expires_at": rec.expires_at.isoformat(),
                "position_size": float(rec.position_size),
                "strategy_params": rec.strategy_params,
                "status": "ACTIVE",
            }

            result = self.supabase.table("paper_recommendations").insert(data).execute()

            if result.data:
                rec.id = result.data[0]["id"]
                rec.created_at = datetime.fromisoformat(
                    result.data[0]["created_at"].replace("Z", "+00:00")
                )
                logger.debug(f"Saved recommendation {rec.id} for {rec.symbol}")
                return rec

        except Exception as e:
            logger.error(f"Error saving recommendation: {e}")

        return None

    async def get_active_recommendations(self) -> List[Dict[str, Any]]:
        """Get all active recommendations for this strategy"""
        if not self.supabase:
            return []

        try:
            result = self.supabase.table("paper_recommendations").select("*").eq(
                "strategy_name", self.name
            ).eq("status", "ACTIVE").execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Error fetching active recommendations: {e}")
            return []

    async def check_outcomes(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Check if any active recommendations have hit target or stop.

        Args:
            current_prices: Dict of symbol -> current price

        Returns:
            List of outcome records
        """
        if not self.supabase:
            return []

        outcomes = []
        active = await self.get_active_recommendations()
        now = datetime.now(timezone.utc)

        for rec in active:
            symbol = rec["symbol"]
            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            entry_price = float(rec["entry_price"])
            target_price = float(rec["target_price_1"])
            stop_price = float(rec["stop_loss_price"])
            direction = rec["direction"]
            position_size = float(rec.get("position_size", 1000))

            # Parse expiry
            expires_at = rec["expires_at"]
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

            # Parse created_at
            created_at = rec["created_at"]
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

            outcome_type = None
            exit_price = current_price

            # Check for target/stop hit based on direction
            if direction == "LONG":
                if current_price >= target_price:
                    outcome_type = "TARGET_HIT"
                elif current_price <= stop_price:
                    outcome_type = "STOPPED"
            elif direction == "SHORT":
                if current_price <= target_price:
                    outcome_type = "TARGET_HIT"
                elif current_price >= stop_price:
                    outcome_type = "STOPPED"

            # Check for expiry
            if not outcome_type and now >= expires_at:
                outcome_type = "EXPIRED"

            if outcome_type:
                # Calculate PnL
                if direction == "LONG":
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                else:
                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100

                pnl_amount = (pnl_pct / 100) * position_size
                hold_duration = int((now - created_at).total_seconds() / 60)

                outcome = await self._save_outcome(
                    rec["id"], outcome_type, exit_price, pnl_pct, pnl_amount, hold_duration
                )

                if outcome:
                    # Add recommendation data for Telegram formatting
                    outcome["recommendation"] = rec
                    outcomes.append(outcome)

        return outcomes

    async def _save_outcome(
        self,
        recommendation_id: str,
        outcome_type: str,
        exit_price: float,
        pnl_pct: float,
        pnl_amount: float,
        hold_duration_minutes: int
    ) -> Optional[Dict[str, Any]]:
        """Save outcome and update recommendation status"""
        if not self.supabase:
            return None

        try:
            # Save outcome
            outcome_data = {
                "recommendation_id": recommendation_id,
                "outcome_type": outcome_type,
                "exit_price": float(exit_price),
                "pnl_pct": float(pnl_pct),
                "pnl_usd": float(pnl_amount),
                "hold_duration_minutes": hold_duration_minutes,
            }

            result = self.supabase.table("paper_recommendation_outcomes").insert(
                outcome_data
            ).execute()

            # Update recommendation status
            self.supabase.table("paper_recommendations").update({
                "status": outcome_type
            }).eq("id", recommendation_id).execute()

            logger.info(
                f"Outcome saved: {recommendation_id} -> {outcome_type} "
                f"({pnl_pct:+.2f}%)"
            )

            return result.data[0] if result.data else outcome_data

        except Exception as e:
            logger.error(f"Error saving outcome: {e}")
            return None
