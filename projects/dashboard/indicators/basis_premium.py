"""
Basis/Premium Tracker for Hyperliquid
Tracks futures basis, premium, and arbitrage opportunities
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque
import os
from dotenv import load_dotenv
import sys
import numpy as np

# Try to import hyperliquid - works both locally and in Docker
try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
except ImportError:
    sys.path.append('..')
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
from supabase import create_client, Client

load_dotenv()


class BasisPremiumIndicator:
    """
    Tracks Basis/Premium metrics:
    - Spot vs Perp premium/discount
    - Annualized basis
    - Funding arbitrage opportunities
    - Cross-exchange premium (if spot price available)
    - Term structure analysis
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL', 'HYPE']
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Price data
        self.perp_prices = defaultdict(float)
        self.spot_prices = defaultdict(float)
        self.index_prices = defaultdict(float)
        
        # Basis tracking
        self.basis_history = defaultdict(lambda: deque(maxlen=1440))  # 24h at 1min intervals
        self.premium_history = defaultdict(lambda: deque(maxlen=1440))
        
        # Arbitrage tracking
        self.arb_opportunities = defaultdict(dict)
        self.funding_rates = defaultdict(float)
        
        # Statistics
        self.basis_stats = defaultdict(dict)
        
        # Timing
        self.last_update = time.time()
        self.last_snapshot = time.time()
    
    async def fetch_prices(self, symbol: str):
        """Fetch perpetual and spot prices"""
        try:
            # Get all mids for the symbol
            all_mids = self.info.all_mids()
            
            if all_mids and symbol in all_mids:
                self.perp_prices[symbol] = float(all_mids[symbol])
            
            # Try to get spot price (may not be available for all symbols)
            # For now, we'll use the perpetual price as a proxy
            # In a real implementation, you might fetch spot from another source
            self.spot_prices[symbol] = self.perp_prices[symbol]
            
            # Get index price from meta
            try:
                meta_and_ctxs = self.info.meta_and_asset_ctxs()
                if meta_and_ctxs:
                    meta = meta_and_ctxs[0]
                    ctxs = meta_and_ctxs[1]
                    universe = meta.get('universe', [])
                    
                    for i, asset_meta in enumerate(universe):
                        if asset_meta.get('name', '') == symbol and i < len(ctxs):
                            ctx = ctxs[i]
                            # Oracle price can serve as index price
                            oracle_px = float(ctx.get('oraclePx', 0))
                            if oracle_px > 0:
                                self.index_prices[symbol] = oracle_px
                            else:
                                self.index_prices[symbol] = self.perp_prices[symbol]
                            
                            # Get funding rate
                            self.funding_rates[symbol] = float(ctx.get('funding', 0)) * 10000  # Convert to basis points
                            break
            except:
                self.index_prices[symbol] = self.perp_prices[symbol]
            
            return True
            
        except Exception as e:
            print(f"[Basis] Error fetching prices for {symbol}: {e}")
            return False
    
    def calculate_basis(self, symbol: str) -> Dict[str, Any]:
        """Calculate basis and premium metrics"""
        perp_price = self.perp_prices.get(symbol, 0)
        spot_price = self.spot_prices.get(symbol, perp_price)
        index_price = self.index_prices.get(symbol, perp_price)
        
        if perp_price == 0 or spot_price == 0:
            return {}
        
        # Calculate basis (perp - spot)
        basis_absolute = perp_price - spot_price
        basis_pct = (basis_absolute / spot_price) * 100 if spot_price > 0 else 0
        
        # Calculate premium to index
        premium_absolute = perp_price - index_price
        premium_pct = (premium_absolute / index_price) * 100 if index_price > 0 else 0
        
        # Annualized basis (assuming perpetual)
        # Basis * 365 / days_to_expiry (for perps, we use funding rate period)
        annualized_basis = basis_pct * 365  # Simplified calculation
        
        # Store in history
        self.basis_history[symbol].append({
            'time': time.time(),
            'basis': basis_pct,
            'premium': premium_pct
        })
        
        # Calculate statistics
        if len(self.basis_history[symbol]) > 10:
            recent_basis = [h['basis'] for h in list(self.basis_history[symbol])[-60:]]  # Last hour
            recent_premium = [h['premium'] for h in list(self.basis_history[symbol])[-60:]]
            
            basis_mean = np.mean(recent_basis)
            basis_std = np.std(recent_basis)
            basis_max = max(recent_basis)
            basis_min = min(recent_basis)
            
            premium_mean = np.mean(recent_premium)
            premium_std = np.std(recent_premium)
        else:
            basis_mean = basis_pct
            basis_std = 0
            basis_max = basis_pct
            basis_min = basis_pct
            premium_mean = premium_pct
            premium_std = 0
        
        # Determine market state
        if basis_pct > 0.5:
            state = 'contango_strong'
        elif basis_pct > 0.1:
            state = 'contango'
        elif basis_pct < -0.5:
            state = 'backwardation_strong'
        elif basis_pct < -0.1:
            state = 'backwardation'
        else:
            state = 'neutral'
        
        # Check for arbitrage opportunity
        funding_rate = self.funding_rates.get(symbol, 0)
        
        # Simple arb: if basis > funding rate * 8 (8 hour funding periods)
        arb_threshold = funding_rate * 8
        if abs(basis_pct) > abs(arb_threshold) + 0.1:  # 0.1% buffer for fees
            arb_signal = 'long_spot_short_perp' if basis_pct > 0 else 'short_spot_long_perp'
            arb_profit_estimate = abs(basis_pct) - abs(arb_threshold)
        else:
            arb_signal = 'none'
            arb_profit_estimate = 0
        
        return {
            'symbol': symbol,
            'perp_price': perp_price,
            'spot_price': spot_price,
            'index_price': index_price,
            'basis_absolute': basis_absolute,
            'basis_pct': basis_pct,
            'premium_pct': premium_pct,
            'annualized_basis': annualized_basis,
            'basis_1h_mean': basis_mean,
            'basis_1h_std': basis_std,
            'basis_1h_max': basis_max,
            'basis_1h_min': basis_min,
            'premium_1h_mean': premium_mean,
            'premium_1h_std': premium_std,
            'funding_rate': funding_rate,
            'state': state,
            'arb_signal': arb_signal,
            'arb_profit_estimate': arb_profit_estimate,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    async def update(self):
        """Update basis data for all symbols"""
        for symbol in self.symbols:
            await self.fetch_prices(symbol)
    
    async def save_to_supabase(self):
        """Save basis data to Supabase"""
        for symbol in self.symbols:
            metrics = self.calculate_basis(symbol)
            
            if not metrics:
                continue
            
            # Update current table
            try:
                self.supabase.table('hl_basis_current').upsert({
                    'symbol': symbol,
                    **metrics
                }).execute()
            except Exception as e:
                print(f"[Basis] Error saving current data: {e}")
            
            # Save snapshots every 15 minutes
            current_time = time.time()
            if current_time - self.last_snapshot >= 900:
                try:
                    self.supabase.table('hl_basis_snapshots').insert({
                        'symbol': symbol,
                        'perp_price': metrics['perp_price'],
                        'basis_pct': metrics['basis_pct'],
                        'premium_pct': metrics['premium_pct'],
                        'funding_rate': metrics['funding_rate'],
                        'state': metrics['state'],
                        'arb_signal': metrics['arb_signal'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    print(f"[Basis] Error saving snapshot: {e}")
        
        if time.time() - self.last_snapshot >= 900:
            self.last_snapshot = time.time()
            print(f"[Basis] Saved snapshots at {datetime.now().strftime('%H:%M:%S')}")
    
    async def run(self, update_interval: int = 30):
        """Run the basis tracker"""
        print(f"[Basis] Starting Basis/Premium tracker")
        print(f"[Basis] Tracking: {', '.join(self.symbols)}")
        print(f"[Basis] Update interval: {update_interval} seconds")
        print("=" * 60)
        
        # Initial fetch
        await self.update()
        
        while True:
            try:
                # Update data
                await self.update()
                
                # Save to Supabase
                await self.save_to_supabase()
                
                # Display current metrics
                print(f"\n[Basis Status] {datetime.now().strftime('%H:%M:%S')}")
                for symbol in self.symbols:
                    metrics = self.calculate_basis(symbol)
                    if metrics:
                        print(f"  {symbol}: Basis={metrics['basis_pct']:.3f}%, "
                              f"Premium={metrics['premium_pct']:.3f}%, "
                              f"Funding={metrics['funding_rate']:.2f}bp, "
                              f"{metrics['state']}, Arb: {metrics['arb_signal']}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"[Basis] Error in main loop: {e}")
                await asyncio.sleep(10)


async def main():
    """Run Basis/Premium indicator"""
    indicator = BasisPremiumIndicator(symbols=['BTC', 'ETH', 'SOL', 'HYPE'])
    
    try:
        await indicator.run(update_interval=30)  # Update every 30 seconds
    except KeyboardInterrupt:
        print("\n[Basis] Stopped by user")
    except Exception as e:
        print(f"[Basis] Fatal error: {e}")


if __name__ == "__main__":
    print("Basis/Premium Indicator for Hyperliquid")
    print("Updates every 30 seconds")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())