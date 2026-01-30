import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import BaseIndicator

class BollingerBands(BaseIndicator):
    def __init__(self, symbol: str, timeframe: str, period: int = 20, std_dev: float = 2.0):
        super().__init__(symbol, timeframe)
        self.period = period
        self.std_dev = std_dev
        self.upper_band = None
        self.middle_band = None
        self.lower_band = None
        self.band_width = None
        self.squeeze = False
        
    async def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        if len(data) < self.period:
            return {"error": "Insufficient data"}
        
        closes = data['close'].values[-self.period:]
        current_price = closes[-1]
        
        self.middle_band = np.mean(closes)
        std = np.std(closes)
        
        self.upper_band = self.middle_band + (self.std_dev * std)
        self.lower_band = self.middle_band - (self.std_dev * std)
        self.band_width = self.upper_band - self.lower_band
        
        band_width_pct = (self.band_width / self.middle_band * 100) if self.middle_band > 0 else 0
        
        historical_widths = []
        for i in range(max(0, len(data) - 50), len(data) - self.period + 1):
            window = data['close'].values[i:i+self.period]
            w_std = np.std(window)
            w_width = 2 * self.std_dev * w_std
            historical_widths.append(w_width)
        
        avg_width = np.mean(historical_widths) if historical_widths else self.band_width
        self.squeeze = self.band_width < avg_width * 0.7
        
        signal = None
        position = None
        
        if current_price > self.upper_band:
            signal = "BREAKOUT_UP"
            position = "ABOVE_UPPER"
        elif current_price < self.lower_band:
            signal = "BREAKOUT_DOWN"
            position = "BELOW_LOWER"
        elif self.squeeze:
            signal = "SQUEEZE"
            position = "INSIDE"
        else:
            price_position = (current_price - self.lower_band) / self.band_width if self.band_width > 0 else 0.5
            if price_position > 0.8:
                signal = "NEAR_UPPER"
            elif price_position < 0.2:
                signal = "NEAR_LOWER"
            else:
                signal = "NEUTRAL"
            position = "INSIDE"
        
        self.update_value({
            "upper_band": self.upper_band,
            "middle_band": self.middle_band,
            "lower_band": self.lower_band,
            "band_width": self.band_width,
            "band_width_pct": band_width_pct,
            "squeeze": self.squeeze,
            "current_price": current_price,
            "position": position
        }, signal)
        
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": "BollingerBands",
            "value": self.last_value,
            "signal": signal
        }
    
    def get_signal(self) -> Dict[str, Any]:
        if not self.last_value:
            return {"signal": None, "strength": 0}
        
        if self.last_signal == "BREAKOUT_UP":
            return {"signal": "BUY", "strength": 85}
        elif self.last_signal == "BREAKOUT_DOWN":
            return {"signal": "SELL", "strength": 85}
        elif self.last_signal == "SQUEEZE":
            return {"signal": "PREPARE", "strength": 60}
        elif self.last_signal == "NEAR_UPPER":
            return {"signal": "SELL", "strength": 40}
        elif self.last_signal == "NEAR_LOWER":
            return {"signal": "BUY", "strength": 40}
        
        return {"signal": "NEUTRAL", "strength": 0}
    
    def get_confluence_weight(self) -> float:
        if self.squeeze:
            return 2.0
        elif self.last_signal in ["BREAKOUT_UP", "BREAKOUT_DOWN"]:
            return 1.8
        return 1.0