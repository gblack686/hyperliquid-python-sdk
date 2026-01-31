"""
Base Strategy Module
====================
Provides base classes and utilities for paper trading strategies.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
import json

from dotenv import load_dotenv
from loguru import logger
from supabase import create_client, Client

load_dotenv()


class RecommendationStatus(Enum):
    """Status of a paper trading recommendation"""
    ACTIVE = "ACTIVE"
    TARGET_HIT = "TARGET_HIT"
    STOPPED = "STOPPED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Direction(Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"
    HOLD = "HOLD"


@dataclass
class Recommendation:
    """Paper trading recommendation"""
    strategy_name: str
    symbol: str
    direction: Direction
    entry_price: float
    confidence_score: int  # 0-100

    # Optional price targets
    target_price_1: Optional[float] = None
    target_price_2: Optional[float] = None
    stop_loss_price: Optional[float] = None

    # Metadata
    expires_at: Optional[datetime] = None
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None

    # Set on save
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    status: RecommendationStatus = RecommendationStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insert"""
        data = {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "direction": self.direction.value if isinstance(self.direction, Direction) else self.direction,
            "entry_price": self.entry_price,
            "confidence_score": self.confidence_score,
            "target_price_1": self.target_price_1,
            "target_price_2": self.target_price_2,
            "stop_loss_price": self.stop_loss_price,
            "strategy_params": self.strategy_params,
            "notes": self.notes,
            "status": self.status.value if isinstance(self.status, RecommendationStatus) else self.status,
        }

        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recommendation":
        """Create from database row"""
        return cls(
            id=data.get("id"),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None,
            strategy_name=data["strategy_name"],
            symbol=data["symbol"],
            direction=Direction(data["direction"]),
            entry_price=float(data["entry_price"]),
            confidence_score=int(data["confidence_score"]),
            target_price_1=float(data["target_price_1"]) if data.get("target_price_1") else None,
            target_price_2=float(data["target_price_2"]) if data.get("target_price_2") else None,
            stop_loss_price=float(data["stop_loss_price"]) if data.get("stop_loss_price") else None,
            expires_at=datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")) if data.get("expires_at") else None,
            strategy_params=data.get("strategy_params", {}),
            notes=data.get("notes"),
            status=RecommendationStatus(data["status"]),
        )

    def calculate_pnl_pct(self, current_price: float) -> float:
        """Calculate unrealized P&L percentage"""
        if self.direction == Direction.LONG:
            return ((current_price - self.entry_price) / self.entry_price) * 100
        elif self.direction == Direction.SHORT:
            return ((self.entry_price - current_price) / self.entry_price) * 100
        return 0.0

    def format_telegram_signal(self) -> str:
        """Format recommendation for Telegram alert"""
        direction_str = self.direction.value

        # Calculate R:R ratio if we have target and stop
        rr_str = ""
        if self.target_price_1 and self.stop_loss_price:
            if self.direction == Direction.LONG:
                risk = self.entry_price - self.stop_loss_price
                reward = self.target_price_1 - self.entry_price
            else:
                risk = self.stop_loss_price - self.entry_price
                reward = self.entry_price - self.target_price_1

            if risk > 0:
                rr = reward / risk
                rr_str = f"\nR:R: {rr:.1f}x"

        # Calculate target and stop percentages
        target_pct = ""
        stop_pct = ""
        if self.target_price_1:
            pct = ((self.target_price_1 - self.entry_price) / self.entry_price) * 100
            if self.direction == Direction.SHORT:
                pct = -pct
            sign = "+" if pct > 0 else ""
            target_pct = f" ({sign}{pct:.1f}%)"

        if self.stop_loss_price:
            pct = ((self.stop_loss_price - self.entry_price) / self.entry_price) * 100
            if self.direction == Direction.SHORT:
                pct = -pct
            sign = "+" if pct > 0 else ""
            stop_pct = f" ({sign}{pct:.1f}%)"

        msg = f"*PAPER SIGNAL*: {self.symbol} {direction_str}\n"
        msg += f"Strategy: {self.strategy_name}\n"
        msg += f"Entry: ${self.entry_price:,.4f}\n"

        if self.target_price_1:
            msg += f"Target: ${self.target_price_1:,.4f}{target_pct}\n"
        if self.stop_loss_price:
            msg += f"Stop: ${self.stop_loss_price:,.4f}{stop_pct}\n"

        msg += f"Confidence: {self.confidence_score}/100{rr_str}"

        return msg

    def format_telegram_outcome(self, outcome_type: str, exit_price: float, pnl_pct: float, duration_minutes: int) -> str:
        """Format outcome for Telegram alert"""
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"

        pnl_usd = pnl_pct / 100 * 1000  # Assuming $1000 position
        sign = "+" if pnl_pct >= 0 else ""

        msg = f"*SIGNAL RESULT*: {self.symbol} {self.direction.value}\n"
        msg += f"Outcome: {outcome_type.replace('_', ' ')}\n"
        msg += f"P&L: {sign}{pnl_pct:.2f}% (${pnl_usd:+.2f})\n"
        msg += f"Duration: {duration_str}"

        return msg


class SupabasePaperTrading:
    """Supabase client for paper trading operations"""

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            logger.warning("Supabase credentials not set - paper trading will not persist to database")
            self.client = None
        else:
            self.client: Client = create_client(self.url, self.key)
            logger.info("Supabase paper trading client initialized")

    def save_recommendation(self, rec: Recommendation) -> Optional[str]:
        """Save a recommendation to Supabase, returns ID"""
        if not self.client:
            logger.warning("Supabase not configured - recommendation not saved")
            return None

        try:
            data = rec.to_dict()
            result = self.client.table("paper_recommendations").insert(data).execute()

            if result.data:
                rec_id = result.data[0]["id"]
                logger.info(f"Saved recommendation {rec_id}: {rec.symbol} {rec.direction.value}")
                return rec_id
            return None
        except Exception as e:
            logger.error(f"Error saving recommendation: {e}")
            return None

    def get_active_recommendations(self, strategy_name: Optional[str] = None) -> List[Recommendation]:
        """Get all active recommendations, optionally filtered by strategy"""
        if not self.client:
            return []

        try:
            query = self.client.table("paper_recommendations").select("*").eq("status", "ACTIVE")

            if strategy_name:
                query = query.eq("strategy_name", strategy_name)

            result = query.order("created_at", desc=True).execute()

            return [Recommendation.from_dict(row) for row in result.data]
        except Exception as e:
            logger.error(f"Error fetching active recommendations: {e}")
            return []

    def get_recommendations_since(self, since: datetime, strategy_name: Optional[str] = None) -> List[Recommendation]:
        """Get recommendations since a given time"""
        if not self.client:
            return []

        try:
            query = self.client.table("paper_recommendations").select("*").gte("created_at", since.isoformat())

            if strategy_name:
                query = query.eq("strategy_name", strategy_name)

            result = query.order("created_at", desc=True).execute()

            return [Recommendation.from_dict(row) for row in result.data]
        except Exception as e:
            logger.error(f"Error fetching recommendations: {e}")
            return []

    def update_recommendation_status(self, rec_id: str, status: RecommendationStatus) -> bool:
        """Update recommendation status"""
        if not self.client:
            return False

        try:
            self.client.table("paper_recommendations").update(
                {"status": status.value}
            ).eq("id", rec_id).execute()

            logger.info(f"Updated recommendation {rec_id} to {status.value}")
            return True
        except Exception as e:
            logger.error(f"Error updating recommendation status: {e}")
            return False

    def save_outcome(
        self,
        recommendation_id: str,
        outcome_type: str,
        exit_price: float,
        pnl_pct: float,
        hold_duration_minutes: int,
        pnl_usd: Optional[float] = None,
        peak_pnl_pct: Optional[float] = None,
        trough_pnl_pct: Optional[float] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Save outcome for a recommendation"""
        if not self.client:
            return False

        try:
            data = {
                "recommendation_id": recommendation_id,
                "outcome_type": outcome_type,
                "exit_price": exit_price,
                "pnl_pct": pnl_pct,
                "hold_duration_minutes": hold_duration_minutes,
            }

            if pnl_usd is not None:
                data["pnl_usd"] = pnl_usd
            if peak_pnl_pct is not None:
                data["peak_pnl_pct"] = peak_pnl_pct
            if trough_pnl_pct is not None:
                data["trough_pnl_pct"] = trough_pnl_pct
            if notes:
                data["notes"] = notes

            self.client.table("paper_recommendation_outcomes").insert(data).execute()

            logger.info(f"Saved outcome for {recommendation_id}: {outcome_type} {pnl_pct:+.2f}%")
            return True
        except Exception as e:
            logger.error(f"Error saving outcome: {e}")
            return False

    def save_price_snapshot(self, recommendation_id: str, price: float, unrealized_pnl_pct: float) -> bool:
        """Save price snapshot for tracking"""
        if not self.client:
            return False

        try:
            self.client.table("paper_price_snapshots").insert({
                "recommendation_id": recommendation_id,
                "price": price,
                "unrealized_pnl_pct": unrealized_pnl_pct
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error saving price snapshot: {e}")
            return False

    def get_outcomes_since(self, since: datetime, strategy_name: Optional[str] = None) -> List[Dict]:
        """Get outcomes since a given time"""
        if not self.client:
            return []

        try:
            query = self.client.table("paper_recommendation_outcomes").select(
                "*, paper_recommendations!inner(strategy_name, symbol, direction, entry_price, confidence_score)"
            ).gte("outcome_time", since.isoformat())

            if strategy_name:
                query = query.eq("paper_recommendations.strategy_name", strategy_name)

            result = query.order("outcome_time", desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching outcomes: {e}")
            return []

    def upsert_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Upsert strategy metrics"""
        if not self.client:
            return False

        try:
            self.client.table("paper_strategy_metrics").upsert(
                metrics,
                on_conflict="strategy_name,period"
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error upserting metrics: {e}")
            return False

    def get_metrics(self, strategy_name: Optional[str] = None, period: Optional[str] = None) -> List[Dict]:
        """Get strategy metrics"""
        if not self.client:
            return []

        try:
            query = self.client.table("paper_strategy_metrics").select("*")

            if strategy_name:
                query = query.eq("strategy_name", strategy_name)
            if period:
                query = query.eq("period", period)

            result = query.order("updated_at", desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            return []


class BaseStrategy(ABC):
    """Base class for paper trading strategies"""

    def __init__(
        self,
        name: str,
        default_expiry_hours: int = 24,
        min_confidence: int = 50,
        position_size_usd: float = 1000.0
    ):
        self.name = name
        self.default_expiry_hours = default_expiry_hours
        self.min_confidence = min_confidence
        self.position_size_usd = position_size_usd
        self.db = SupabasePaperTrading()

        logger.info(f"Strategy initialized: {name}")

    @abstractmethod
    async def generate_signals(self) -> List[Recommendation]:
        """
        Generate trading signals.

        Returns:
            List of Recommendation objects for symbols that meet criteria.
            Should return empty list if no opportunities found.
        """
        pass

    @abstractmethod
    async def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get current prices for symbols.

        Args:
            symbols: List of symbols to get prices for

        Returns:
            Dict mapping symbol to current price
        """
        pass

    def save_recommendation(self, rec: Recommendation) -> Optional[str]:
        """Save recommendation to database"""
        return self.db.save_recommendation(rec)

    def get_active_recommendations(self) -> List[Recommendation]:
        """Get active recommendations for this strategy"""
        return self.db.get_active_recommendations(self.name)

    async def check_outcomes(self) -> List[Dict]:
        """
        Check active recommendations for outcomes (target hit, stopped, expired).

        Returns:
            List of outcome dictionaries
        """
        active_recs = self.get_active_recommendations()

        if not active_recs:
            return []

        # Get current prices
        symbols = list(set(r.symbol for r in active_recs))
        prices = await self.get_current_prices(symbols)

        outcomes = []
        now = datetime.utcnow()

        for rec in active_recs:
            if not rec.id:
                continue

            current_price = prices.get(rec.symbol)
            if not current_price:
                continue

            pnl_pct = rec.calculate_pnl_pct(current_price)
            created_at = rec.created_at or now
            duration_minutes = int((now - created_at).total_seconds() / 60)

            outcome_type = None

            # Check expiry first
            if rec.expires_at and now >= rec.expires_at:
                outcome_type = "EXPIRED"

            # Check stop loss
            elif rec.stop_loss_price:
                if rec.direction == Direction.LONG and current_price <= rec.stop_loss_price:
                    outcome_type = "STOPPED"
                elif rec.direction == Direction.SHORT and current_price >= rec.stop_loss_price:
                    outcome_type = "STOPPED"

            # Check target
            if not outcome_type and rec.target_price_1:
                if rec.direction == Direction.LONG and current_price >= rec.target_price_1:
                    outcome_type = "TARGET_HIT"
                elif rec.direction == Direction.SHORT and current_price <= rec.target_price_1:
                    outcome_type = "TARGET_HIT"

            if outcome_type:
                # Update status
                self.db.update_recommendation_status(rec.id, RecommendationStatus(outcome_type))

                # Save outcome
                pnl_usd = (pnl_pct / 100) * self.position_size_usd
                self.db.save_outcome(
                    recommendation_id=rec.id,
                    outcome_type=outcome_type,
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                    hold_duration_minutes=duration_minutes,
                    pnl_usd=pnl_usd
                )

                outcomes.append({
                    "recommendation": rec,
                    "outcome_type": outcome_type,
                    "exit_price": current_price,
                    "pnl_pct": pnl_pct,
                    "pnl_usd": pnl_usd,
                    "duration_minutes": duration_minutes
                })

                logger.info(f"Outcome recorded: {rec.symbol} {outcome_type} {pnl_pct:+.2f}%")
            else:
                # Save price snapshot for tracking
                self.db.save_price_snapshot(rec.id, current_price, pnl_pct)

        return outcomes

    def create_recommendation(
        self,
        symbol: str,
        direction: Direction,
        entry_price: float,
        confidence_score: int,
        target_price_1: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        strategy_params: Optional[Dict] = None,
        notes: Optional[str] = None,
        expiry_hours: Optional[int] = None
    ) -> Recommendation:
        """Helper to create a recommendation with defaults"""

        expiry_hours = expiry_hours or self.default_expiry_hours
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)

        return Recommendation(
            strategy_name=self.name,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            confidence_score=confidence_score,
            target_price_1=target_price_1,
            stop_loss_price=stop_loss_price,
            expires_at=expires_at,
            strategy_params=strategy_params or {},
            notes=notes
        )
