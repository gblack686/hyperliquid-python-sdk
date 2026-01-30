# Hyperliquid Trading Indicators Module
"""
Modular indicator system for Hyperliquid trading.
Each indicator runs independently and stores data in Supabase.
"""

from typing import Dict, List, Any

class IndicatorBase:
    """Base class for all indicators"""
    
    def __init__(self, symbols: List[str], supabase_client):
        self.symbols = symbols
        self.supabase = supabase_client
        self.data = {}
        
    async def initialize(self):
        """Initialize the indicator"""
        pass
        
    async def update(self, market_data: Dict[str, Any]):
        """Update indicator with new market data"""
        raise NotImplementedError
        
    async def save_to_supabase(self):
        """Save current state to Supabase"""
        raise NotImplementedError
        
    def get_current_value(self, symbol: str) -> Any:
        """Get current indicator value for a symbol"""
        return self.data.get(symbol)

# Available indicators
INDICATORS = {
    'cvd': 'indicators.cvd.CVDIndicator',
    'open_interest': 'indicators.open_interest.OpenInterestIndicator',
    'funding_rate': 'indicators.funding_rate.FundingRateIndicator',
    'liquidations': 'indicators.liquidations.LiquidationsIndicator',
    'order_book': 'indicators.order_book.OrderBookIndicator',
    'price_metrics': 'indicators.price_metrics.PriceMetricsIndicator',
    'volume_metrics': 'indicators.volume_metrics.VolumeMetricsIndicator',
}