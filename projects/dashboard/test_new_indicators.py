#!/usr/bin/env python
"""Test new indicators"""

import asyncio
import sys
sys.path.append('./indicators')

from indicators.volume_profile import VolumeProfileIndicator
from indicators.basis_premium import BasisPremiumIndicator
from indicators.mtf_aggregator import MTFAggregatorIndicator

async def test():
    print("Testing new indicators...")
    
    symbols = ['BTC', 'ETH']
    
    print("\n1. Testing Volume Profile...")
    try:
        vp = VolumeProfileIndicator(symbols)
        await vp.update()
        for symbol in symbols:
            metrics = vp.calculate_vp_metrics(symbol)
            print(f"  {symbol}: POC={metrics['poc_session']:.2f}, VA Position={metrics['position_relative_to_va']}")
        print("  ✓ Volume Profile OK")
    except Exception as e:
        print(f"  ✗ Volume Profile failed: {e}")
    
    print("\n2. Testing Basis/Premium...")
    try:
        bp = BasisPremiumIndicator(symbols)
        await bp.update()
        for symbol in symbols:
            metrics = bp.calculate_basis(symbol)
            if metrics:
                print(f"  {symbol}: Basis={metrics['basis_pct']:.3f}%, State={metrics['state']}")
        print("  ✓ Basis/Premium OK")
    except Exception as e:
        print(f"  ✗ Basis/Premium failed: {e}")
    
    print("\n3. Testing MTF Aggregator...")
    try:
        mtf = MTFAggregatorIndicator(symbols)
        await mtf.update()
        for symbol in symbols:
            metrics = mtf.calculate_mtf_metrics(symbol)
            print(f"  {symbol}: Score={metrics['confluence_score']:.1f}, Bias={metrics['market_bias']}")
        print("  ✓ MTF Aggregator OK")
    except Exception as e:
        print(f"  ✗ MTF Aggregator failed: {e}")
    
    print("\n✅ All new indicators tested!")

if __name__ == "__main__":
    asyncio.run(test())