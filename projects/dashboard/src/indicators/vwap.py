import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import BaseIndicator

class VWAP(BaseIndicator):
    def __init__(self, symbol: str, timeframe: str):
        super().__init__(symbol, timeframe)
        self.vwap_value = None
        self.current_price = None
        self.deviation = None
        self.upper_band = None
        self.lower_band = None
        
    async def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        if len(data) < 1:
            return {"error": "Insufficient data"}
        
        data = data.copy()
        
        data['date'] = pd.to_datetime(data.index if isinstance(data.index, pd.DatetimeIndex) else data.get('timestamp', data.index))
        data['day'] = data['date'].dt.date
        
        current_day = data['day'].iloc[-1]
        day_data = data[data['day'] == current_day].copy()
        
        if len(day_data) < 1:
            return {"error": "No data for current day"}
        
        day_data['typical_price'] = (day_data['high'] + day_data['low'] + day_data['close']) / 3
        day_data['pv'] = day_data['typical_price'] * day_data['volume']
        
        cumulative_pv = day_data['pv'].cumsum()
        cumulative_volume = day_data['volume'].cumsum()
        
        day_data['vwap'] = cumulative_pv / cumulative_volume
        
        self.vwap_value = day_data['vwap'].iloc[-1]
        self.current_price = day_data['close'].iloc[-1]
        
        day_data['squared_diff'] = ((day_data['typical_price'] - day_data['vwap']) ** 2) * day_data['volume']
        variance = day_data['squared_diff'].sum() / cumulative_volume.iloc[-1] if cumulative_volume.iloc[-1] > 0 else 0
        std_dev = np.sqrt(variance)
        
        self.upper_band = self.vwap_value + (2 * std_dev)
        self.lower_band = self.vwap_value - (2 * std_dev)
        
        self.deviation = ((self.current_price - self.vwap_value) / self.vwap_value * 100) if self.vwap_value > 0 else 0
        
        signal = None
        position = None
        
        if self.current_price > self.upper_band:
            signal = "ABOVE_UPPER_BAND"
            position = "extended_up"
        elif self.current_price < self.lower_band:
            signal = "BELOW_LOWER_BAND"
            position = "extended_down"
        elif self.current_price > self.vwap_value:
            if self.deviation > 1:
                signal = "ABOVE_VWAP_STRONG"
            else:
                signal = "ABOVE_VWAP"
            position = "above"
        elif self.current_price < self.vwap_value:
            if self.deviation < -1:
                signal = "BELOW_VWAP_STRONG"
            else:
                signal = "BELOW_VWAP"
            position = "below"
        else:
            signal = "AT_VWAP"
            position = "at"
        
        self.update_value({
            "vwap": self.vwap_value,
            "current_price": self.current_price,
            "deviation_pct": self.deviation,
            "upper_band": self.upper_band,
            "lower_band": self.lower_band,
            "position": position,
            "cumulative_volume": cumulative_volume.iloc[-1] if not cumulative_volume.empty else 0
        }, signal)
        
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": "VWAP",
            "value": self.last_value,
            "signal": signal
        }
    
    def get_signal(self) -> Dict[str, Any]:
        if not self.last_value:
            return {"signal": None, "strength": 0}
        
        if self.last_signal == "ABOVE_UPPER_BAND":
            return {"signal": "SELL", "strength": 80}
        elif self.last_signal == "BELOW_LOWER_BAND":
            return {"signal": "BUY", "strength": 80}
        elif self.last_signal == "ABOVE_VWAP_STRONG":
            return {"signal": "BULLISH", "strength": 60}
        elif self.last_signal == "BELOW_VWAP_STRONG":
            return {"signal": "BEARISH", "strength": 60}
        elif self.last_signal == "ABOVE_VWAP":
            return {"signal": "BULLISH", "strength": 40}
        elif self.last_signal == "BELOW_VWAP":
            return {"signal": "BEARISH", "strength": 40}
        
        return {"signal": "NEUTRAL", "strength": 0}
    
    def get_confluence_weight(self) -> float:
        if self.last_signal in ["ABOVE_UPPER_BAND", "BELOW_LOWER_BAND"]:
            return 1.8
        elif self.last_signal in ["ABOVE_VWAP_STRONG", "BELOW_VWAP_STRONG"]:
            return 1.4
        return 1.0