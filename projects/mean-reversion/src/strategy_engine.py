"""
Mean Reversion Strategy Engine
Implements the optimized mean reversion strategy with real-time indicator updates
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from collections import deque
from dataclasses import dataclass, asdict
from enum import Enum

from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class SignalType(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    EXIT = "EXIT"
    HOLD = "HOLD"


@dataclass
class TradingSignal:
    """Trading signal data structure"""
    timestamp: datetime
    action: SignalType
    price: float
    z_score: float
    confidence: float
    reason: str
    metadata: Dict = None


@dataclass
class Position:
    """Current position tracking"""
    size: float = 0
    entry_price: float = 0
    entry_time: Optional[datetime] = None
    unrealized_pnl: float = 0
    realized_pnl: float = 0
    side: str = "flat"  # long, short, flat


class StrategyEngine:
    """
    Mean reversion strategy implementation with incremental indicator updates
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize strategy engine"""
        
        # Load configuration
        self.config = config or self.load_config()
        
        # Strategy parameters (from optimization)
        self.lookback_period = self.config.get("lookback_period", 12)
        self.entry_z_score = self.config.get("entry_z_score", 0.75)
        self.exit_z_score = self.config.get("exit_z_score", 0.5)
        self.stop_loss_pct = self.config.get("stop_loss_pct", 0.05)
        
        # Position management
        self.max_position_size = self.config.get("max_position_size", 1000)
        self.max_leverage = self.config.get("max_leverage", 3.0)
        self.current_position = Position()
        
        # Data storage (using deque for efficiency)
        self.price_buffer = deque(maxlen=self.lookback_period)
        self.volume_buffer = deque(maxlen=20)
        self.returns_buffer = deque(maxlen=self.lookback_period)
        
        # Indicators
        self.sma = 0
        self.std = 0
        self.z_score = 0
        self.rsi = 50
        self.volume_ratio = 1.0
        self.volatility = 0
        
        # Incremental calculation helpers
        self.price_sum = 0
        self.price_squared_sum = 0
        
        # Signal history
        self.signals_history = deque(maxlen=100)
        self.last_signal = None
        
        # Performance tracking
        self.total_pnl = 0
        self.daily_pnl = 0
        self.win_count = 0
        self.loss_count = 0
        self.last_reset_date = datetime.now().date()
        
        logger.info(f"Strategy Engine initialized: lookback={self.lookback_period}, entry_z={self.entry_z_score}, exit_z={self.exit_z_score}")
    
    def load_config(self) -> Dict:
        """Load configuration from environment"""
        return {
            "lookback_period": int(os.getenv("LOOKBACK_PERIOD", 12)),
            "entry_z_score": float(os.getenv("ENTRY_Z_SCORE", 0.75)),
            "exit_z_score": float(os.getenv("EXIT_Z_SCORE", 0.5)),
            "stop_loss_pct": float(os.getenv("STOP_LOSS_PCT", 0.05)),
            "max_position_size": float(os.getenv("MAX_POSITION_SIZE", 1000)),
            "max_leverage": float(os.getenv("MAX_LEVERAGE", 3.0))
        }
    
    def update_price(self, price: float, volume: float = 0, timestamp: Optional[datetime] = None):
        """
        Update price and recalculate indicators incrementally
        """
        timestamp = timestamp or datetime.utcnow()
        
        # Add to buffer
        old_len = len(self.price_buffer)
        
        # If buffer is full, remove oldest values from sums
        if old_len == self.lookback_period:
            old_price = self.price_buffer[0]
            self.price_sum -= old_price
            self.price_squared_sum -= old_price * old_price
        
        # Add new price
        self.price_buffer.append(price)
        self.price_sum += price
        self.price_squared_sum += price * price
        
        # Update volume
        if volume > 0:
            self.volume_buffer.append(volume)
        
        # Calculate returns
        if old_len > 0:
            returns = (price - self.price_buffer[-2]) / self.price_buffer[-2]
            self.returns_buffer.append(returns)
        
        # Update indicators
        self.calculate_indicators()
        
        logger.debug(f"Price update: ${price:.4f}, Z-score: {self.z_score:.2f}, SMA: ${self.sma:.4f}")
    
    def calculate_indicators(self):
        """Calculate technical indicators incrementally"""
        
        n = len(self.price_buffer)
        if n == 0:
            return
        
        # Calculate SMA (incremental)
        self.sma = self.price_sum / n
        
        # Calculate standard deviation (incremental)
        if n > 1:
            variance = (self.price_squared_sum / n) - (self.sma * self.sma)
            self.std = np.sqrt(max(0, variance))
        else:
            self.std = 0
        
        # Calculate Z-score
        if self.std > 0:
            current_price = self.price_buffer[-1]
            self.z_score = (current_price - self.sma) / self.std
        else:
            self.z_score = 0
        
        # Calculate RSI (simplified)
        if len(self.returns_buffer) >= 14:
            gains = [r for r in self.returns_buffer if r > 0]
            losses = [-r for r in self.returns_buffer if r < 0]
            
            avg_gain = np.mean(gains) if gains else 0
            avg_loss = np.mean(losses) if losses else 0
            
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                self.rsi = 100 - (100 / (1 + rs))
            else:
                self.rsi = 100 if avg_gain > 0 else 50
        
        # Calculate volume ratio
        if len(self.volume_buffer) > 0:
            current_vol = self.volume_buffer[-1] if self.volume_buffer else 0
            avg_vol = np.mean(self.volume_buffer)
            self.volume_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
        
        # Calculate volatility
        if len(self.returns_buffer) > 0:
            self.volatility = np.std(self.returns_buffer) * np.sqrt(24 * 365)  # Annualized
    
    def generate_signal(self) -> TradingSignal:
        """
        Generate trading signal based on current indicators
        """
        
        # Check if we have enough data
        if len(self.price_buffer) < self.lookback_period:
            return TradingSignal(
                timestamp=datetime.utcnow(),
                action=SignalType.HOLD,
                price=self.price_buffer[-1] if self.price_buffer else 0,
                z_score=self.z_score,
                confidence=0,
                reason="Insufficient data"
            )
        
        current_price = self.price_buffer[-1]
        
        # Check risk limits
        if not self.check_risk_limits():
            return TradingSignal(
                timestamp=datetime.utcnow(),
                action=SignalType.HOLD,
                price=current_price,
                z_score=self.z_score,
                confidence=0,
                reason="Risk limits exceeded"
            )
        
        # Generate signal based on position
        if self.current_position.size == 0:
            signal = self.generate_entry_signal(current_price)
        else:
            signal = self.generate_exit_signal(current_price)
        
        # Store signal
        self.signals_history.append(signal)
        self.last_signal = signal
        
        if signal.action != SignalType.HOLD:
            logger.info(f"Signal generated: {signal.action.value} @ ${signal.price:.4f} (Z:{signal.z_score:.2f}, Conf:{signal.confidence:.2f})")
        
        return signal
    
    def generate_entry_signal(self, current_price: float) -> TradingSignal:
        """Generate entry signal when flat"""
        
        action = SignalType.HOLD
        confidence = 0
        reason = ""
        
        # Check for oversold (buy signal)
        if self.z_score < -self.entry_z_score:
            action = SignalType.BUY
            confidence = min(abs(self.z_score) / 2, 1.0)
            reason = f"Oversold: Z-score {self.z_score:.2f}"
            
            # Boost confidence with additional indicators
            if self.rsi < 30:
                confidence = min(confidence * 1.2, 1.0)
                reason += ", RSI oversold"
            if self.volume_ratio > 1.5:
                confidence = min(confidence * 1.1, 1.0)
                reason += ", High volume"
        
        # Check for overbought (sell/short signal)
        elif self.z_score > self.entry_z_score:
            action = SignalType.SELL
            confidence = min(abs(self.z_score) / 2, 1.0)
            reason = f"Overbought: Z-score {self.z_score:.2f}"
            
            # Boost confidence with additional indicators
            if self.rsi > 70:
                confidence = min(confidence * 1.2, 1.0)
                reason += ", RSI overbought"
            if self.volume_ratio > 1.5:
                confidence = min(confidence * 1.1, 1.0)
                reason += ", High volume"
        
        else:
            reason = f"Z-score {self.z_score:.2f} within normal range"
        
        return TradingSignal(
            timestamp=datetime.utcnow(),
            action=action,
            price=current_price,
            z_score=self.z_score,
            confidence=confidence,
            reason=reason,
            metadata={
                "sma": self.sma,
                "std": self.std,
                "rsi": self.rsi,
                "volume_ratio": self.volume_ratio
            }
        )
    
    def generate_exit_signal(self, current_price: float) -> TradingSignal:
        """Generate exit signal when in position"""
        
        action = SignalType.HOLD
        confidence = 1.0
        reason = ""
        
        # Check mean reversion exit
        if abs(self.z_score) < self.exit_z_score:
            action = SignalType.EXIT
            reason = "Mean reversion complete"
        
        # Check stop loss
        elif self.current_position.size > 0:  # Long position
            if current_price < self.current_position.entry_price * (1 - self.stop_loss_pct):
                action = SignalType.EXIT
                reason = "Stop loss triggered"
        
        elif self.current_position.size < 0:  # Short position
            if current_price > self.current_position.entry_price * (1 + self.stop_loss_pct):
                action = SignalType.EXIT
                reason = "Stop loss triggered"
        
        # Check time-based exit (optional)
        if self.current_position.entry_time:
            time_in_position = datetime.utcnow() - self.current_position.entry_time
            if time_in_position > timedelta(hours=48):
                action = SignalType.EXIT
                confidence = 0.8
                reason = "Time limit reached (48h)"
        
        if action == SignalType.HOLD:
            reason = f"Position held, Z-score: {self.z_score:.2f}"
        
        return TradingSignal(
            timestamp=datetime.utcnow(),
            action=action,
            price=current_price,
            z_score=self.z_score,
            confidence=confidence,
            reason=reason,
            metadata={
                "position_size": self.current_position.size,
                "entry_price": self.current_position.entry_price,
                "unrealized_pnl": self.calculate_unrealized_pnl(current_price)
            }
        )
    
    def calculate_position_size(self, signal: TradingSignal) -> float:
        """
        Calculate position size based on signal confidence and risk parameters
        """
        
        base_size = self.max_position_size
        
        # Adjust for confidence
        base_size *= signal.confidence
        
        # Adjust for volatility
        if self.volatility > 0.10:  # High volatility (>10% daily)
            base_size *= 0.5
        elif self.volatility > 0.07:
            base_size *= 0.75
        
        # Check leverage limit
        max_allowed = self.max_position_size * self.max_leverage
        base_size = min(base_size, max_allowed)
        
        # Round to reasonable precision
        base_size = round(base_size, 2)
        
        logger.debug(f"Position size calculated: ${base_size:.2f} (confidence: {signal.confidence:.2f}, volatility: {self.volatility:.4f})")
        
        return base_size
    
    def update_position(self, size: float, entry_price: float, side: str):
        """Update current position"""
        
        self.current_position.size = size
        self.current_position.entry_price = entry_price
        self.current_position.entry_time = datetime.utcnow()
        self.current_position.side = side
        self.current_position.unrealized_pnl = 0
        
        logger.info(f"Position updated: {side} {size:.4f} @ ${entry_price:.4f}")
    
    def close_position(self, exit_price: float) -> float:
        """Close current position and calculate P&L"""
        
        if self.current_position.size == 0:
            return 0
        
        # Calculate P&L
        if self.current_position.size > 0:  # Long
            pnl = (exit_price - self.current_position.entry_price) * self.current_position.size
        else:  # Short
            pnl = (self.current_position.entry_price - exit_price) * abs(self.current_position.size)
        
        # Update tracking
        self.current_position.realized_pnl = pnl
        self.total_pnl += pnl
        self.daily_pnl += pnl
        
        if pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1
        
        logger.info(f"Position closed @ ${exit_price:.4f}, P&L: ${pnl:.2f}")
        
        # Reset position
        self.current_position = Position()
        
        return pnl
    
    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L"""
        
        if self.current_position.size == 0:
            return 0
        
        if self.current_position.size > 0:  # Long
            return (current_price - self.current_position.entry_price) * self.current_position.size
        else:  # Short
            return (self.current_position.entry_price - current_price) * abs(self.current_position.size)
    
    def check_risk_limits(self) -> bool:
        """Check if trading is allowed based on risk limits"""
        
        # Reset daily P&L if new day
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0
            self.last_reset_date = current_date
        
        # Check daily loss limit (10% of max position)
        if self.daily_pnl < -self.max_position_size * 0.10:
            logger.warning("Daily loss limit reached")
            return False
        
        # Check volatility limit
        if self.volatility > 0.15:  # 15% daily volatility
            logger.warning(f"Volatility too high: {self.volatility:.2%}")
            return False
        
        return True
    
    def get_statistics(self) -> Dict:
        """Get current strategy statistics"""
        
        total_trades = self.win_count + self.loss_count
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "total_pnl": self.total_pnl,
            "daily_pnl": self.daily_pnl,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "current_position": asdict(self.current_position),
            "current_indicators": {
                "z_score": self.z_score,
                "sma": self.sma,
                "std": self.std,
                "rsi": self.rsi,
                "volatility": self.volatility,
                "volume_ratio": self.volume_ratio
            },
            "last_signal": asdict(self.last_signal) if self.last_signal else None
        }
    
    def reset(self):
        """Reset strategy state"""
        
        self.price_buffer.clear()
        self.volume_buffer.clear()
        self.returns_buffer.clear()
        self.signals_history.clear()
        
        self.current_position = Position()
        self.price_sum = 0
        self.price_squared_sum = 0
        
        logger.info("Strategy engine reset")


def test_strategy():
    """Test strategy with sample data"""
    
    strategy = StrategyEngine()
    
    # Simulate price updates
    np.random.seed(42)
    base_price = 44.0
    
    for i in range(100):
        # Generate price with mean reversion tendency
        noise = np.random.normal(0, 0.5)
        mean_reversion = (base_price - strategy.sma) * 0.1 if strategy.sma > 0 else 0
        price = base_price + noise + mean_reversion
        
        volume = np.random.uniform(1000, 5000)
        
        # Update strategy
        strategy.update_price(price, volume)
        
        # Generate signal every hour
        if i >= strategy.lookback_period:
            signal = strategy.generate_signal()
            
            if signal.action != SignalType.HOLD:
                print(f"Signal: {signal.action.value} @ ${signal.price:.2f} (Z:{signal.z_score:.2f})")
                
                # Simulate execution
                if signal.action == SignalType.BUY:
                    size = strategy.calculate_position_size(signal) / price
                    strategy.update_position(size, price, "long")
                elif signal.action == SignalType.SELL:
                    size = -strategy.calculate_position_size(signal) / price
                    strategy.update_position(size, price, "short")
                elif signal.action == SignalType.EXIT:
                    pnl = strategy.close_position(price)
                    print(f"Trade closed, P&L: ${pnl:.2f}")
    
    # Print final statistics
    stats = strategy.get_statistics()
    print(f"\nFinal Statistics:")
    print(f"Total P&L: ${stats['total_pnl']:.2f}")
    print(f"Win Rate: {stats['win_rate']:.1f}%")
    print(f"Total Trades: {stats['total_trades']}")


if __name__ == "__main__":
    test_strategy()