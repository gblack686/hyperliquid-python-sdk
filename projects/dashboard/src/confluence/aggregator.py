from typing import Dict, List, Any, Optional
from datetime import datetime
import numpy as np
from loguru import logger
from ..indicators.base import BaseIndicator

class ConfluenceAggregator:
    def __init__(self, threshold: float = 70.0):
        self.indicators: Dict[str, BaseIndicator] = {}
        self.threshold = threshold
        self.last_confluence_score = 0
        self.last_signals = {}
        self.last_update = None
        
    def add_indicator(self, name: str, indicator: BaseIndicator):
        self.indicators[name] = indicator
        logger.info(f"Added indicator: {name}")
    
    def remove_indicator(self, name: str):
        if name in self.indicators:
            del self.indicators[name]
            logger.info(f"Removed indicator: {name}")
    
    def calculate_confluence(self) -> Dict[str, Any]:
        if not self.indicators:
            return {
                "score": 0,
                "signal": "NO_INDICATORS",
                "strength": "none",
                "indicators_triggered": [],
                "action": "WAIT"
            }
        
        bullish_score = 0
        bearish_score = 0
        neutral_count = 0
        triggered_indicators = []
        
        for name, indicator in self.indicators.items():
            signal_data = indicator.get_signal()
            weight = indicator.get_confluence_weight()
            
            if signal_data["signal"] in ["BUY", "BULLISH", "STRONG_OVERSOLD"]:
                bullish_score += signal_data["strength"] * weight
                triggered_indicators.append({
                    "name": name,
                    "signal": signal_data["signal"],
                    "strength": signal_data["strength"],
                    "weight": weight
                })
            elif signal_data["signal"] in ["SELL", "BEARISH", "STRONG_OVERBOUGHT"]:
                bearish_score += signal_data["strength"] * weight
                triggered_indicators.append({
                    "name": name,
                    "signal": signal_data["signal"],
                    "strength": signal_data["strength"],
                    "weight": weight
                })
            elif signal_data["signal"] in ["CAUTION_BUY"]:
                bullish_score += signal_data["strength"] * weight * 0.5
                triggered_indicators.append({
                    "name": name,
                    "signal": signal_data["signal"],
                    "strength": signal_data["strength"],
                    "weight": weight
                })
            elif signal_data["signal"] in ["CAUTION_SELL"]:
                bearish_score += signal_data["strength"] * weight * 0.5
                triggered_indicators.append({
                    "name": name,
                    "signal": signal_data["signal"],
                    "strength": signal_data["strength"],
                    "weight": weight
                })
            else:
                neutral_count += 1
        
        total_weight = sum(ind.get_confluence_weight() for ind in self.indicators.values())
        max_possible_score = 100 * total_weight
        
        bullish_normalized = (bullish_score / max_possible_score * 100) if max_possible_score > 0 else 0
        bearish_normalized = (bearish_score / max_possible_score * 100) if max_possible_score > 0 else 0
        
        if bullish_normalized > bearish_normalized:
            confluence_score = bullish_normalized
            direction = "BULLISH"
        else:
            confluence_score = bearish_normalized
            direction = "BEARISH"
        
        self.last_confluence_score = confluence_score
        
        strength = self._get_strength_level(confluence_score)
        action = self._get_action_suggestion(confluence_score, direction, triggered_indicators)
        
        self.last_signals = {
            "bullish_score": bullish_normalized,
            "bearish_score": bearish_normalized,
            "neutral_count": neutral_count
        }
        self.last_update = datetime.now()
        
        return {
            "score": confluence_score,
            "direction": direction,
            "strength": strength,
            "indicators_triggered": triggered_indicators,
            "action": action,
            "bullish_score": bullish_normalized,
            "bearish_score": bearish_normalized,
            "threshold_met": confluence_score >= self.threshold,
            "timestamp": self.last_update
        }
    
    def _get_strength_level(self, score: float) -> str:
        if score >= 90:
            return "EXTREME"
        elif score >= 75:
            return "STRONG"
        elif score >= 60:
            return "MODERATE"
        elif score >= 40:
            return "WEAK"
        else:
            return "VERY_WEAK"
    
    def _get_action_suggestion(self, score: float, direction: str, triggered: List[Dict]) -> str:
        high_priority_signals = ["BULLISH_CROSSOVER", "BEARISH_CROSSOVER", 
                                "STRONG_OVERBOUGHT", "STRONG_OVERSOLD",
                                "BREAKOUT_UP", "BREAKOUT_DOWN"]
        
        has_high_priority = any(
            ind["signal"] in high_priority_signals 
            for ind in triggered
        )
        
        if score >= self.threshold:
            if direction == "BULLISH":
                if has_high_priority:
                    return "STRONG_BUY"
                return "BUY"
            else:
                if has_high_priority:
                    return "STRONG_SELL"
                return "SELL"
        elif score >= self.threshold * 0.7:
            if direction == "BULLISH":
                return "CONSIDER_BUY"
            else:
                return "CONSIDER_SELL"
        elif score >= self.threshold * 0.5:
            return "PREPARE"
        else:
            return "WAIT"
    
    def get_summary(self) -> Dict[str, Any]:
        if not self.last_update:
            return {"status": "No data available"}
        
        indicator_statuses = {}
        for name, indicator in self.indicators.items():
            signal_data = indicator.get_signal()
            indicator_statuses[name] = {
                "signal": signal_data["signal"],
                "strength": signal_data["strength"],
                "last_update": indicator.last_update.isoformat() if indicator.last_update else None
            }
        
        return {
            "last_score": self.last_confluence_score,
            "last_signals": self.last_signals,
            "last_update": self.last_update.isoformat(),
            "threshold": self.threshold,
            "total_indicators": len(self.indicators),
            "indicator_statuses": indicator_statuses
        }
    
    def reset(self):
        self.last_confluence_score = 0
        self.last_signals = {}
        self.last_update = None
        for indicator in self.indicators.values():
            indicator.last_value = None
            indicator.last_signal = None
            indicator.last_update = None