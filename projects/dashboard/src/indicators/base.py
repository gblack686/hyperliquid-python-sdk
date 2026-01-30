from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger

class BaseIndicator(ABC):
    def __init__(self, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.last_value = None
        self.last_signal = None
        self.last_update = None
        
    @abstractmethod
    async def calculate(self, data: pd.DataFrame) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_signal(self) -> Dict[str, Any]:
        pass
    
    def update_value(self, value: Any, signal: Optional[str] = None):
        self.last_value = value
        self.last_signal = signal
        self.last_update = datetime.now()
        
    def get_confluence_weight(self) -> float:
        return 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicator": self.__class__.__name__,
            "value": self.last_value,
            "signal": self.last_signal,
            "updated": self.last_update.isoformat() if self.last_update else None,
            "weight": self.get_confluence_weight()
        }