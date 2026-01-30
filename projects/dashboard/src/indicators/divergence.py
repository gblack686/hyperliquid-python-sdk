import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from .base import BaseIndicator
from scipy.signal import argrelextrema

class PriceDivergence(BaseIndicator):
    def __init__(self, symbol: str, timeframe: str, lookback: int = 50, min_swing_strength: int = 3):
        super().__init__(symbol, timeframe)
        self.lookback = lookback
        self.min_swing_strength = min_swing_strength
        self.rsi_divergence = None
        self.macd_divergence = None
        self.current_divergences = []
        
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> np.ndarray:
        closes = data['close'].values
        deltas = np.diff(closes)
        
        gains = deltas.copy()
        gains[gains < 0] = 0
        losses = -deltas.copy()
        losses[losses < 0] = 0
        
        rsi_values = []
        
        for i in range(period, len(closes)):
            avg_gain = np.mean(gains[i-period:i])
            avg_loss = np.mean(losses[i-period:i])
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return np.array(rsi_values)
    
    def calculate_macd(self, data: pd.DataFrame) -> np.ndarray:
        closes = data['close'].values
        
        def ema(data, period):
            multiplier = 2 / (period + 1)
            ema_val = data[0]
            for price in data[1:]:
                ema_val = (price - ema_val) * multiplier + ema_val
            return ema_val
        
        macd_values = []
        for i in range(26, len(closes)):
            fast_ema = ema(closes[i-12:i+1], 12)
            slow_ema = ema(closes[i-26:i+1], 26)
            macd_values.append(fast_ema - slow_ema)
        
        return np.array(macd_values)
    
    def find_divergence(self, prices: np.ndarray, indicator: np.ndarray, divergence_type: str = "both") -> List[Dict]:
        divergences = []
        
        price_highs = argrelextrema(prices, np.greater, order=self.min_swing_strength)[0]
        price_lows = argrelextrema(prices, np.less, order=self.min_swing_strength)[0]
        
        if len(indicator) < len(prices):
            offset = len(prices) - len(indicator)
            indicator_highs = argrelextrema(indicator, np.greater, order=self.min_swing_strength)[0]
            indicator_lows = argrelextrema(indicator, np.less, order=self.min_swing_strength)[0]
            
            indicator_highs = indicator_highs[indicator_highs < len(indicator)]
            indicator_lows = indicator_lows[indicator_lows < len(indicator)]
            
            indicator_highs += offset
            indicator_lows += offset
        else:
            indicator_highs = argrelextrema(indicator, np.greater, order=self.min_swing_strength)[0]
            indicator_lows = argrelextrema(indicator, np.less, order=self.min_swing_strength)[0]
        
        if divergence_type in ["bearish", "both"] and len(price_highs) >= 2:
            for i in range(1, len(price_highs)):
                current_high = price_highs[i]
                prev_high = price_highs[i-1]
                
                matching_indicator_highs = [ih for ih in indicator_highs 
                                           if abs(ih - current_high) <= 2 or abs(ih - prev_high) <= 2]
                
                if len(matching_indicator_highs) >= 2:
                    ind_current = matching_indicator_highs[-1]
                    ind_prev = matching_indicator_highs[-2]
                    
                    if ind_current - offset >= 0 and ind_prev - offset >= 0:
                        if (prices[current_high] > prices[prev_high] and 
                            indicator[ind_current - offset] < indicator[ind_prev - offset]):
                            divergences.append({
                                "type": "bearish",
                                "strength": "regular",
                                "price_points": [prev_high, current_high],
                                "indicator_points": [ind_prev, ind_current]
                            })
        
        if divergence_type in ["bullish", "both"] and len(price_lows) >= 2:
            for i in range(1, len(price_lows)):
                current_low = price_lows[i]
                prev_low = price_lows[i-1]
                
                matching_indicator_lows = [il for il in indicator_lows 
                                          if abs(il - current_low) <= 2 or abs(il - prev_low) <= 2]
                
                if len(matching_indicator_lows) >= 2:
                    ind_current = matching_indicator_lows[-1]
                    ind_prev = matching_indicator_lows[-2]
                    
                    if ind_current - offset >= 0 and ind_prev - offset >= 0:
                        if (prices[current_low] < prices[prev_low] and 
                            indicator[ind_current - offset] > indicator[ind_prev - offset]):
                            divergences.append({
                                "type": "bullish",
                                "strength": "regular",
                                "price_points": [prev_low, current_low],
                                "indicator_points": [ind_prev, ind_current]
                            })
        
        return divergences
    
    async def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        if len(data) < self.lookback:
            return {"error": "Insufficient data"}
        
        data = data.iloc[-self.lookback:].copy()
        prices = data['close'].values
        
        rsi_values = self.calculate_rsi(data)
        macd_values = self.calculate_macd(data)
        
        self.current_divergences = []
        
        if len(rsi_values) > self.min_swing_strength * 2:
            rsi_divergences = self.find_divergence(prices, rsi_values)
            for div in rsi_divergences:
                div["indicator"] = "RSI"
                self.current_divergences.append(div)
        
        if len(macd_values) > self.min_swing_strength * 2:
            macd_divergences = self.find_divergence(prices, macd_values)
            for div in macd_divergences:
                div["indicator"] = "MACD"
                self.current_divergences.append(div)
        
        recent_divergences = [d for d in self.current_divergences 
                             if max(d["price_points"]) >= len(prices) - 10]
        
        signal = None
        if recent_divergences:
            bullish_count = sum(1 for d in recent_divergences if d["type"] == "bullish")
            bearish_count = sum(1 for d in recent_divergences if d["type"] == "bearish")
            
            if bullish_count > bearish_count:
                if bullish_count >= 2:
                    signal = "STRONG_BULLISH_DIVERGENCE"
                else:
                    signal = "BULLISH_DIVERGENCE"
            elif bearish_count > bullish_count:
                if bearish_count >= 2:
                    signal = "STRONG_BEARISH_DIVERGENCE"
                else:
                    signal = "BEARISH_DIVERGENCE"
            else:
                signal = "MIXED_DIVERGENCE"
        else:
            signal = "NO_DIVERGENCE"
        
        self.update_value({
            "divergences": recent_divergences,
            "total_divergences": len(recent_divergences),
            "bullish_count": sum(1 for d in recent_divergences if d["type"] == "bullish"),
            "bearish_count": sum(1 for d in recent_divergences if d["type"] == "bearish")
        }, signal)
        
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": "Divergence",
            "value": self.last_value,
            "signal": signal
        }
    
    def get_signal(self) -> Dict[str, Any]:
        if not self.last_value:
            return {"signal": None, "strength": 0}
        
        if self.last_signal == "STRONG_BULLISH_DIVERGENCE":
            return {"signal": "BUY", "strength": 90}
        elif self.last_signal == "STRONG_BEARISH_DIVERGENCE":
            return {"signal": "SELL", "strength": 90}
        elif self.last_signal == "BULLISH_DIVERGENCE":
            return {"signal": "BUY", "strength": 70}
        elif self.last_signal == "BEARISH_DIVERGENCE":
            return {"signal": "SELL", "strength": 70}
        elif self.last_signal == "MIXED_DIVERGENCE":
            return {"signal": "CAUTION", "strength": 30}
        
        return {"signal": "NEUTRAL", "strength": 0}
    
    def get_confluence_weight(self) -> float:
        if self.last_signal in ["STRONG_BULLISH_DIVERGENCE", "STRONG_BEARISH_DIVERGENCE"]:
            return 2.5
        elif self.last_signal in ["BULLISH_DIVERGENCE", "BEARISH_DIVERGENCE"]:
            return 2.0
        return 1.0