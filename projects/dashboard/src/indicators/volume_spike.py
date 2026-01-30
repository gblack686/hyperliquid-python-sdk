import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import BaseIndicator

class VolumeSpike(BaseIndicator):
    def __init__(self, symbol: str, timeframe: str, spike_threshold: float = 2.0, lookback: int = 20):
        super().__init__(symbol, timeframe)
        self.spike_threshold = spike_threshold
        self.lookback = lookback
        self.volume_ma = None
        self.current_volume = None
        
    async def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        if len(data) < self.lookback:
            return {"error": "Insufficient data"}
        
        volumes = data['volume'].values
        self.volume_ma = np.mean(volumes[-self.lookback:])
        self.current_volume = volumes[-1]
        
        spike_ratio = self.current_volume / self.volume_ma if self.volume_ma > 0 else 0
        
        signal = None
        if spike_ratio >= self.spike_threshold:
            signal = "HIGH_VOLUME"
        elif spike_ratio >= self.spike_threshold * 0.75:
            signal = "MODERATE_VOLUME"
        else:
            signal = "NORMAL_VOLUME"
        
        self.update_value({
            "current_volume": self.current_volume,
            "average_volume": self.volume_ma,
            "spike_ratio": spike_ratio
        }, signal)
        
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": "VolumeSpike",
            "value": self.last_value,
            "signal": signal,
            "spike_detected": spike_ratio >= self.spike_threshold
        }
    
    def get_signal(self) -> Dict[str, Any]:
        if not self.last_value:
            return {"signal": None, "strength": 0}
        
        spike_ratio = self.last_value.get("spike_ratio", 0)
        
        if spike_ratio >= self.spike_threshold:
            return {"signal": "HIGH_VOLUME", "strength": min(100, spike_ratio * 30)}
        elif spike_ratio >= self.spike_threshold * 0.75:
            return {"signal": "MODERATE_VOLUME", "strength": 50}
        else:
            return {"signal": "NORMAL", "strength": 0}
    
    def get_confluence_weight(self) -> float:
        return 1.5