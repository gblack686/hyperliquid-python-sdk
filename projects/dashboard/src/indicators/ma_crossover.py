import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import BaseIndicator

class MACrossover(BaseIndicator):
    def __init__(self, symbol: str, timeframe: str, fast_period: int = 50, slow_period: int = 200):
        super().__init__(symbol, timeframe)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.fast_ma = None
        self.slow_ma = None
        self.crossover_type = None
        
    async def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        if len(data) < self.slow_period:
            return {"error": "Insufficient data"}
        
        closes = data['close'].values
        
        self.fast_ma = np.mean(closes[-self.fast_period:])
        self.slow_ma = np.mean(closes[-self.slow_period:])
        
        prev_fast_ma = np.mean(closes[-self.fast_period-1:-1])
        prev_slow_ma = np.mean(closes[-self.slow_period-1:-1])
        
        signal = None
        self.crossover_type = None
        
        if prev_fast_ma <= prev_slow_ma and self.fast_ma > self.slow_ma:
            signal = "BULLISH_CROSSOVER"
            self.crossover_type = "golden_cross"
        elif prev_fast_ma >= prev_slow_ma and self.fast_ma < self.slow_ma:
            signal = "BEARISH_CROSSOVER"
            self.crossover_type = "death_cross"
        elif self.fast_ma > self.slow_ma:
            signal = "BULLISH_TREND"
        else:
            signal = "BEARISH_TREND"
        
        self.update_value({
            "fast_ma": self.fast_ma,
            "slow_ma": self.slow_ma,
            "crossover": self.crossover_type,
            "spread": self.fast_ma - self.slow_ma,
            "spread_pct": ((self.fast_ma - self.slow_ma) / self.slow_ma * 100) if self.slow_ma > 0 else 0
        }, signal)
        
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": "MACrossover",
            "value": self.last_value,
            "signal": signal
        }
    
    def get_signal(self) -> Dict[str, Any]:
        if not self.last_value:
            return {"signal": None, "strength": 0}
        
        if self.crossover_type == "golden_cross":
            return {"signal": "BUY", "strength": 90}
        elif self.crossover_type == "death_cross":
            return {"signal": "SELL", "strength": 90}
        elif self.last_signal == "BULLISH_TREND":
            spread_pct = abs(self.last_value.get("spread_pct", 0))
            return {"signal": "BULLISH", "strength": min(70, 30 + spread_pct * 2)}
        elif self.last_signal == "BEARISH_TREND":
            spread_pct = abs(self.last_value.get("spread_pct", 0))
            return {"signal": "BEARISH", "strength": min(70, 30 + spread_pct * 2)}
        
        return {"signal": "NEUTRAL", "strength": 0}
    
    def get_confluence_weight(self) -> float:
        return 2.0 if self.crossover_type else 1.0