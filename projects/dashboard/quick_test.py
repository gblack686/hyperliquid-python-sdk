#!/usr/bin/env python
"""Quick test of fixed indicators"""

import sys
import asyncio
sys.path.append('./indicators')

from indicators.vwap import VWAPIndicator
from indicators.orderbook_imbalance import OrderBookImbalanceIndicator
from indicators.liquidations import LiquidationsIndicator

async def test():
    print("Testing fixed indicators...")
    
    # Test VWAP
    i1 = VWAPIndicator(['BTC'])
    await i1.update()
    print('✓ VWAP: OK')
    
    # Test OrderBook
    i2 = OrderBookImbalanceIndicator(['BTC'])
    await i2.update()
    print('✓ OrderBook: OK')
    
    # Test Liquidations
    i3 = LiquidationsIndicator(['BTC'])
    await i3.update()
    print('✓ Liquidations: OK')
    
    print("\nAll fixed indicators working!")

if __name__ == "__main__":
    asyncio.run(test())