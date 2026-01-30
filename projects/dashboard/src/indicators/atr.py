import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import BaseIndicator

class ATRVolatility(BaseIndicator):
    def __init__(self, symbol: str, timeframe: str, period: int = 14):
        super().__init__(symbol, timeframe)
        self.period = period
        self.atr_value = None
        self.atr_percentage = None
        self.volatility_level = None
        
    async def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        if len(data) < self.period + 1:
            return {"error": "Insufficient data"}
        
        highs = data['high'].values
        lows = data['low'].values
        closes = data['close'].values
        
        true_ranges = []
        for i in range(1, len(highs)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)
        
        if len(true_ranges) < self.period:
            return {"error": "Insufficient data for ATR calculation"}
        
        atr_values = []
        atr = np.mean(true_ranges[:self.period])
        atr_values.append(atr)
        
        for i in range(self.period, len(true_ranges)):
            atr = ((atr * (self.period - 1)) + true_ranges[i]) / self.period
            atr_values.append(atr)
        
        self.atr_value = atr_values[-1] if atr_values else 0
        current_price = closes[-1]
        self.atr_percentage = (self.atr_value / current_price * 100) if current_price > 0 else 0
        
        historical_atr_pct = []
        for i in range(max(0, len(atr_values) - 50), len(atr_values)):
            idx = len(true_ranges) - len(atr_values) + i + 1
            if idx < len(closes):
                pct = (atr_values[i] / closes[idx] * 100) if closes[idx] > 0 else 0
                historical_atr_pct.append(pct)
        
        avg_atr_pct = np.mean(historical_atr_pct) if historical_atr_pct else self.atr_percentage
        
        signal = None
        if self.atr_percentage > avg_atr_pct * 1.5:
            signal = "HIGH_VOLATILITY"
            self.volatility_level = "high"
        elif self.atr_percentage > avg_atr_pct * 1.2:
            signal = "INCREASING_VOLATILITY"
            self.volatility_level = "increasing"
        elif self.atr_percentage < avg_atr_pct * 0.7:
            signal = "LOW_VOLATILITY"
            self.volatility_level = "low"
        else:
            signal = "NORMAL_VOLATILITY"
            self.volatility_level = "normal"
        
        self.update_value({
            "atr": self.atr_value,
            "atr_percentage": self.atr_percentage,
            "average_atr_percentage": avg_atr_pct,
            "volatility_level": self.volatility_level,
            "suggested_stop_loss": self.atr_value * 2,
            "suggested_position_size_multiplier": 1 / (self.atr_percentage / 2) if self.atr_percentage > 0 else 1
        }, signal)
        
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": "ATR",
            "value": self.last_value,
            "signal": signal
        }
    
    def get_signal(self) -> Dict[str, Any]:
        if not self.last_value:
            return {"signal": None, "strength": 0}
        
        if self.last_signal == "HIGH_VOLATILITY":
            return {"signal": "REDUCE_SIZE", "strength": 70}
        elif self.last_signal == "INCREASING_VOLATILITY":
            return {"signal": "CAUTION", "strength": 50}
        elif self.last_signal == "LOW_VOLATILITY":
            return {"signal": "PREPARE_BREAKOUT", "strength": 40}
        
        return {"signal": "NEUTRAL", "strength": 0}
    
    def get_confluence_weight(self) -> float:
        if self.volatility_level == "high":
            return 1.3
        elif self.volatility_level == "low":
            return 1.2
        return 1.0