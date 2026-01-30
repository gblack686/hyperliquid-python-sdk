import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import BaseIndicator

class StochasticOscillator(BaseIndicator):
    def __init__(self, symbol: str, timeframe: str, k_period: int = 14, d_period: int = 3, overbought: float = 80, oversold: float = 20):
        super().__init__(symbol, timeframe)
        self.k_period = k_period
        self.d_period = d_period
        self.overbought = overbought
        self.oversold = oversold
        self.k_value = None
        self.d_value = None
        self.k_history = []
        
    async def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        if len(data) < self.k_period + self.d_period:
            return {"error": "Insufficient data"}
        
        highs = data['high'].values
        lows = data['low'].values
        closes = data['close'].values
        
        k_values = []
        for i in range(self.k_period - 1, len(closes)):
            period_high = np.max(highs[i - self.k_period + 1:i + 1])
            period_low = np.min(lows[i - self.k_period + 1:i + 1])
            
            if period_high == period_low:
                k = 50
            else:
                k = ((closes[i] - period_low) / (period_high - period_low)) * 100
            
            k_values.append(k)
        
        self.k_value = k_values[-1] if k_values else 50
        
        self.k_history = k_values[-self.d_period:] if len(k_values) >= self.d_period else k_values
        self.d_value = np.mean(self.k_history) if self.k_history else self.k_value
        
        prev_k = k_values[-2] if len(k_values) >= 2 else self.k_value
        prev_d = np.mean(k_values[-self.d_period-1:-1]) if len(k_values) > self.d_period else self.d_value
        
        signal = None
        crossover = None
        
        if prev_k <= prev_d and self.k_value > self.d_value:
            if self.k_value < self.oversold:
                signal = "BULLISH_CROSSOVER_OVERSOLD"
                crossover = "bullish_oversold"
            else:
                signal = "BULLISH_CROSSOVER"
                crossover = "bullish"
        elif prev_k >= prev_d and self.k_value < self.d_value:
            if self.k_value > self.overbought:
                signal = "BEARISH_CROSSOVER_OVERBOUGHT"
                crossover = "bearish_overbought"
            else:
                signal = "BEARISH_CROSSOVER"
                crossover = "bearish"
        elif self.k_value >= self.overbought and self.d_value >= self.overbought:
            signal = "OVERBOUGHT"
        elif self.k_value <= self.oversold and self.d_value <= self.oversold:
            signal = "OVERSOLD"
        else:
            signal = "NEUTRAL"
        
        self.update_value({
            "k": self.k_value,
            "d": self.d_value,
            "crossover": crossover,
            "zone": self._get_zone()
        }, signal)
        
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": "Stochastic",
            "value": self.last_value,
            "signal": signal
        }
    
    def _get_zone(self) -> str:
        if self.k_value >= self.overbought:
            return "overbought"
        elif self.k_value <= self.oversold:
            return "oversold"
        else:
            return "neutral"
    
    def get_signal(self) -> Dict[str, Any]:
        if not self.last_value:
            return {"signal": None, "strength": 0}
        
        crossover = self.last_value.get("crossover")
        
        if crossover == "bullish_oversold":
            return {"signal": "BUY", "strength": 95}
        elif crossover == "bearish_overbought":
            return {"signal": "SELL", "strength": 95}
        elif crossover == "bullish":
            return {"signal": "BUY", "strength": 70}
        elif crossover == "bearish":
            return {"signal": "SELL", "strength": 70}
        elif self.last_signal == "OVERBOUGHT":
            return {"signal": "SELL", "strength": 60}
        elif self.last_signal == "OVERSOLD":
            return {"signal": "BUY", "strength": 60}
        
        return {"signal": "NEUTRAL", "strength": 0}
    
    def get_confluence_weight(self) -> float:
        if self.last_value:
            crossover = self.last_value.get("crossover")
            if crossover in ["bullish_oversold", "bearish_overbought"]:
                return 2.2
            elif crossover:
                return 1.5
        return 1.0