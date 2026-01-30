import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import BaseIndicator

class MACD(BaseIndicator):
    def __init__(self, symbol: str, timeframe: str, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(symbol, timeframe)
        self.fast_period = fast
        self.slow_period = slow
        self.signal_period = signal
        self.macd_line = None
        self.signal_line = None
        self.histogram = None
        
    def calculate_ema(self, data: np.ndarray, period: int) -> float:
        if len(data) < period:
            return data[-1] if len(data) > 0 else 0
        
        multiplier = 2 / (period + 1)
        ema = np.mean(data[:period])
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    async def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        if len(data) < self.slow_period + self.signal_period:
            return {"error": "Insufficient data"}
        
        closes = data['close'].values
        
        fast_ema = self.calculate_ema(closes, self.fast_period)
        slow_ema = self.calculate_ema(closes, self.slow_period)
        
        self.macd_line = fast_ema - slow_ema
        
        macd_values = []
        for i in range(self.slow_period, len(closes) + 1):
            window = closes[:i]
            f_ema = self.calculate_ema(window, self.fast_period)
            s_ema = self.calculate_ema(window, self.slow_period)
            macd_values.append(f_ema - s_ema)
        
        if len(macd_values) >= self.signal_period:
            self.signal_line = self.calculate_ema(np.array(macd_values), self.signal_period)
        else:
            self.signal_line = self.macd_line
        
        self.histogram = self.macd_line - self.signal_line
        
        prev_histogram = None
        if len(macd_values) >= 2:
            prev_macd = macd_values[-2]
            prev_signal = self.calculate_ema(np.array(macd_values[:-1]), self.signal_period) if len(macd_values[:-1]) >= self.signal_period else prev_macd
            prev_histogram = prev_macd - prev_signal
        
        signal = None
        crossover = None
        
        if prev_histogram is not None:
            if prev_histogram <= 0 and self.histogram > 0:
                signal = "BULLISH_CROSSOVER"
                crossover = "bullish"
            elif prev_histogram >= 0 and self.histogram < 0:
                signal = "BEARISH_CROSSOVER"
                crossover = "bearish"
            elif self.histogram > 0:
                signal = "BULLISH"
            else:
                signal = "BEARISH"
        else:
            signal = "BULLISH" if self.histogram > 0 else "BEARISH"
        
        self.update_value({
            "macd": self.macd_line,
            "signal": self.signal_line,
            "histogram": self.histogram,
            "crossover": crossover
        }, signal)
        
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": "MACD",
            "value": self.last_value,
            "signal": signal
        }
    
    def get_signal(self) -> Dict[str, Any]:
        if not self.last_value:
            return {"signal": None, "strength": 0}
        
        crossover = self.last_value.get("crossover")
        histogram = self.last_value.get("histogram", 0)
        
        if crossover == "bullish":
            return {"signal": "BUY", "strength": 85}
        elif crossover == "bearish":
            return {"signal": "SELL", "strength": 85}
        elif self.last_signal == "BULLISH":
            strength = min(60, 30 + abs(histogram) * 100)
            return {"signal": "BULLISH", "strength": strength}
        elif self.last_signal == "BEARISH":
            strength = min(60, 30 + abs(histogram) * 100)
            return {"signal": "BEARISH", "strength": strength}
        
        return {"signal": "NEUTRAL", "strength": 0}
    
    def get_confluence_weight(self) -> float:
        if self.last_value and self.last_value.get("crossover"):
            return 2.0
        return 1.2