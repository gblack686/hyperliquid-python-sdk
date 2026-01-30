import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from .base import BaseIndicator
from scipy.signal import argrelextrema

class SupportResistance(BaseIndicator):
    def __init__(self, symbol: str, timeframe: str, lookback: int = 100, min_touches: int = 2, tolerance: float = 0.002):
        super().__init__(symbol, timeframe)
        self.lookback = lookback
        self.min_touches = min_touches
        self.tolerance = tolerance
        self.support_levels = []
        self.resistance_levels = []
        self.current_price = None
        
    def find_pivot_points(self, data: np.ndarray, order: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        highs = argrelextrema(data, np.greater, order=order)[0]
        lows = argrelextrema(data, np.less, order=order)[0]
        return highs, lows
    
    def cluster_levels(self, levels: List[float], tolerance: float) -> List[Dict]:
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] <= tolerance:
                current_cluster.append(level)
            else:
                clusters.append({
                    "level": np.mean(current_cluster),
                    "strength": len(current_cluster),
                    "touches": len(current_cluster)
                })
                current_cluster = [level]
        
        if current_cluster:
            clusters.append({
                "level": np.mean(current_cluster),
                "strength": len(current_cluster),
                "touches": len(current_cluster)
            })
        
        return [c for c in clusters if c["touches"] >= self.min_touches]
    
    async def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        if len(data) < self.lookback:
            return {"error": "Insufficient data"}
        
        highs = data['high'].values[-self.lookback:]
        lows = data['low'].values[-self.lookback:]
        closes = data['close'].values[-self.lookback:]
        self.current_price = closes[-1]
        
        high_pivots, low_pivots = self.find_pivot_points(highs, order=5)
        
        resistance_candidates = [highs[i] for i in high_pivots]
        support_candidates = [lows[i] for i in low_pivots]
        
        self.resistance_levels = self.cluster_levels(resistance_candidates, self.tolerance)
        self.support_levels = self.cluster_levels(support_candidates, self.tolerance)
        
        self.resistance_levels = sorted(self.resistance_levels, key=lambda x: x["level"], reverse=True)[:5]
        self.support_levels = sorted(self.support_levels, key=lambda x: x["level"], reverse=True)[:5]
        
        nearest_support = None
        nearest_resistance = None
        
        for support in self.support_levels:
            if support["level"] < self.current_price:
                nearest_support = support
                break
        
        for resistance in reversed(self.resistance_levels):
            if resistance["level"] > self.current_price:
                nearest_resistance = resistance
                break
        
        signal = None
        position_info = {}
        
        if nearest_resistance and nearest_support:
            range_size = nearest_resistance["level"] - nearest_support["level"]
            position_in_range = (self.current_price - nearest_support["level"]) / range_size if range_size > 0 else 0.5
            
            distance_to_resistance = (nearest_resistance["level"] - self.current_price) / self.current_price
            distance_to_support = (self.current_price - nearest_support["level"]) / self.current_price
            
            position_info = {
                "position_in_range": position_in_range,
                "distance_to_resistance": distance_to_resistance,
                "distance_to_support": distance_to_support
            }
            
            if distance_to_resistance < 0.005:
                signal = "AT_RESISTANCE"
            elif distance_to_support < 0.005:
                signal = "AT_SUPPORT"
            elif position_in_range > 0.8:
                signal = "NEAR_RESISTANCE"
            elif position_in_range < 0.2:
                signal = "NEAR_SUPPORT"
            else:
                signal = "NEUTRAL"
        
        self.update_value({
            "support_levels": self.support_levels,
            "resistance_levels": self.resistance_levels,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "current_price": self.current_price,
            **position_info
        }, signal)
        
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": "SupportResistance",
            "value": self.last_value,
            "signal": signal
        }
    
    def get_signal(self) -> Dict[str, Any]:
        if not self.last_value:
            return {"signal": None, "strength": 0}
        
        nearest_support = self.last_value.get("nearest_support")
        nearest_resistance = self.last_value.get("nearest_resistance")
        
        if self.last_signal == "AT_RESISTANCE":
            strength = 70
            if nearest_resistance and nearest_resistance.get("strength", 0) > 3:
                strength = 85
            return {"signal": "SELL", "strength": strength}
        elif self.last_signal == "AT_SUPPORT":
            strength = 70
            if nearest_support and nearest_support.get("strength", 0) > 3:
                strength = 85
            return {"signal": "BUY", "strength": strength}
        elif self.last_signal == "NEAR_RESISTANCE":
            return {"signal": "CAUTION_SELL", "strength": 40}
        elif self.last_signal == "NEAR_SUPPORT":
            return {"signal": "CAUTION_BUY", "strength": 40}
        
        return {"signal": "NEUTRAL", "strength": 0}
    
    def get_confluence_weight(self) -> float:
        if self.last_signal in ["AT_RESISTANCE", "AT_SUPPORT"]:
            if self.last_value:
                nearest = self.last_value.get("nearest_support" if "SUPPORT" in self.last_signal else "nearest_resistance")
                if nearest and nearest.get("strength", 0) > 3:
                    return 2.0
            return 1.5
        return 1.0