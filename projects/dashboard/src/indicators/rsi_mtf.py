import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .base import BaseIndicator

class RSIMultiTimeframe(BaseIndicator):
    def __init__(self, symbol: str, timeframes: List[str], period: int = 14, overbought: float = 70, oversold: float = 30):
        super().__init__(symbol, timeframes[0])
        self.timeframes = timeframes
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.rsi_values = {}
        
    def calculate_rsi(self, data: pd.DataFrame) -> float:
        if len(data) < self.period + 1:
            return 50.0
        
        closes = data['close'].values
        deltas = np.diff(closes)
        
        gains = deltas.copy()
        gains[gains < 0] = 0
        losses = -deltas.copy()
        losses[losses < 0] = 0
        
        avg_gain = np.mean(gains[:self.period])
        avg_loss = np.mean(losses[:self.period])
        
        for i in range(self.period, len(gains)):
            avg_gain = (avg_gain * (self.period - 1) + gains[i]) / self.period
            avg_loss = (avg_loss * (self.period - 1) + losses[i]) / self.period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    async def calculate(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        self.rsi_values = {}
        signals = []
        
        for tf in self.timeframes:
            if tf in data:
                rsi = self.calculate_rsi(data[tf])
                self.rsi_values[tf] = rsi
                
                if rsi >= self.overbought:
                    signals.append(f"OVERBOUGHT_{tf}")
                elif rsi <= self.oversold:
                    signals.append(f"OVERSOLD_{tf}")
        
        avg_rsi = np.mean(list(self.rsi_values.values())) if self.rsi_values else 50
        
        signal = None
        if all(rsi >= self.overbought for rsi in self.rsi_values.values()):
            signal = "STRONG_OVERBOUGHT"
        elif all(rsi <= self.oversold for rsi in self.rsi_values.values()):
            signal = "STRONG_OVERSOLD"
        elif avg_rsi >= self.overbought:
            signal = "OVERBOUGHT"
        elif avg_rsi <= self.oversold:
            signal = "OVERSOLD"
        else:
            signal = "NEUTRAL"
        
        self.update_value({
            "rsi_values": self.rsi_values,
            "average_rsi": avg_rsi,
            "signals": signals
        }, signal)
        
        return {
            "symbol": self.symbol,
            "timeframes": self.timeframes,
            "indicator": "RSI_MTF",
            "value": self.last_value,
            "signal": signal
        }
    
    def get_signal(self) -> Dict[str, Any]:
        if not self.last_value:
            return {"signal": None, "strength": 0}
        
        avg_rsi = self.last_value.get("average_rsi", 50)
        
        if self.last_signal == "STRONG_OVERBOUGHT":
            return {"signal": "SELL", "strength": 95}
        elif self.last_signal == "STRONG_OVERSOLD":
            return {"signal": "BUY", "strength": 95}
        elif self.last_signal == "OVERBOUGHT":
            deviation = avg_rsi - self.overbought
            return {"signal": "SELL", "strength": min(80, 60 + deviation)}
        elif self.last_signal == "OVERSOLD":
            deviation = self.oversold - avg_rsi
            return {"signal": "BUY", "strength": min(80, 60 + deviation)}
        
        return {"signal": "NEUTRAL", "strength": 0}
    
    def get_confluence_weight(self) -> float:
        if self.last_signal in ["STRONG_OVERBOUGHT", "STRONG_OVERSOLD"]:
            return 2.5
        return 1.5