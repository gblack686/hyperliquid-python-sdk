"""
Enhanced HyperLiquid Stats Integration
Uses the official Hyperliquid API to fetch statistics and analytics
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
from dataclasses import dataclass
import os
from dotenv import load_dotenv
import sys
import requests

# Add parent directory to path
sys.path.append('..')
sys.path.append(os.path.dirname(__file__))

try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
except ImportError:
    print("[ERROR] hyperliquid SDK not found. Please install: pip install hyperliquid")
    sys.exit(1)

from src.data.supabase_manager import SupabaseManager

load_dotenv()


class EnhancedStatsAPI:
    """
    Enhanced stats using the official Hyperliquid API
    Fetches funding rates, open interest, volume, and other metrics
    """
    
    def __init__(self, testnet: bool = False):
        """Initialize the enhanced stats client"""
        self.api_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        self.info = Info(self.api_url, skip_ws=True)
        self.db_manager = SupabaseManager()
        self.testnet = testnet
        
        # Common symbols to track
        self.symbols = ['BTC', 'ETH', 'SOL', 'HYPE', 'ARB', 'OP', 'MATIC', 'AVAX', 'INJ', 'SUI']
    
    def get_funding_rates(self) -> List[Dict]:
        """
        Fetch current funding rates for all symbols
        
        Returns:
            List of funding rate data
        """
        try:
            # Get metadata for all symbols
            meta = self.info.meta()
            universe = meta.get('universe', [])
            
            funding_data = []
            timestamp = datetime.now()
            
            for asset in universe:
                symbol = asset.get('name', '')
                if symbol not in self.symbols:
                    continue
                
                # Get funding info
                funding_info = self.info.funding(symbol)
                if funding_info:
                    funding_rate = float(funding_info.get('fundingRate', 0))
                    
                    # Get open interest
                    oi_info = self.info.open_interest(symbol)
                    open_interest = float(oi_info) if oi_info else 0
                    
                    funding_data.append({
                        'symbol': symbol,
                        'funding_rate': funding_rate,
                        'open_interest': open_interest,
                        'timestamp': timestamp.isoformat()
                    })
            
            print(f"[SUCCESS] Fetched funding rates for {len(funding_data)} symbols")
            return funding_data
            
        except Exception as e:
            print(f"[ERROR] Failed to get funding rates: {e}")
            return []
    
    def get_volume_stats(self) -> List[Dict]:
        """
        Fetch 24h volume statistics
        
        Returns:
            List of volume data
        """
        try:
            # Get all mids for price data
            all_mids = self.info.all_mids()
            
            volume_data = []
            timestamp = datetime.now()
            
            for symbol in self.symbols:
                if symbol in all_mids:
                    mid_data = all_mids[symbol]
                    
                    # Get 24h volume from recent trades
                    recent_trades = self.info.user_fills_by_time(
                        user=None,  # All users
                        startTime=int((timestamp - timedelta(hours=24)).timestamp() * 1000),
                        endTime=int(timestamp.timestamp() * 1000)
                    )
                    
                    # Calculate volume for this symbol
                    symbol_volume = 0
                    if recent_trades:
                        for trade in recent_trades:
                            if trade.get('coin') == symbol:
                                symbol_volume += abs(float(trade.get('px', 0)) * float(trade.get('sz', 0)))
                    
                    volume_data.append({
                        'symbol': symbol,
                        'price': float(mid_data),
                        'volume_24h': symbol_volume,
                        'timestamp': timestamp.isoformat()
                    })
            
            print(f"[SUCCESS] Fetched volume stats for {len(volume_data)} symbols")
            return volume_data
            
        except Exception as e:
            print(f"[ERROR] Failed to get volume stats: {e}")
            return []
    
    def get_leaderboard(self) -> List[Dict]:
        """
        Fetch top traders by PnL
        
        Returns:
            List of top traders
        """
        try:
            # Get snapshot of all users (this is limited)
            snapshot = self.info.snapshot()
            
            leaderboard = []
            
            if snapshot and 'users' in snapshot:
                users = snapshot['users']
                
                # Sort by cumulative PnL
                sorted_users = sorted(
                    users.items(),
                    key=lambda x: float(x[1].get('cumulativePnl', 0)),
                    reverse=True
                )[:20]  # Top 20
                
                for rank, (address, data) in enumerate(sorted_users, 1):
                    leaderboard.append({
                        'rank': rank,
                        'address': address[:8] + '...' + address[-4:],  # Truncate for privacy
                        'pnl': float(data.get('cumulativePnl', 0)),
                        'volume': float(data.get('volume', 0)),
                        'timestamp': datetime.now().isoformat()
                    })
            
            print(f"[SUCCESS] Fetched top {len(leaderboard)} traders")
            return leaderboard
            
        except Exception as e:
            print(f"[ERROR] Failed to get leaderboard: {e}")
            return []
    
    def get_liquidations(self, hours: int = 1) -> List[Dict]:
        """
        Fetch recent liquidations (approximated from large trades)
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of potential liquidation events
        """
        try:
            liquidations = []
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Get recent large trades that might be liquidations
            for symbol in self.symbols:
                trades = self.info.user_fills_by_time(
                    user=None,
                    startTime=int(start_time.timestamp() * 1000),
                    endTime=int(end_time.timestamp() * 1000)
                )
                
                if trades:
                    for trade in trades:
                        if trade.get('coin') == symbol:
                            size = abs(float(trade.get('sz', 0)))
                            price = float(trade.get('px', 0))
                            value = size * price
                            
                            # Consider large trades as potential liquidations
                            if value > 50000:  # $50k threshold
                                liquidations.append({
                                    'symbol': symbol,
                                    'side': 'long' if trade.get('side') == 'B' else 'short',
                                    'size': size,
                                    'price': price,
                                    'value': value,
                                    'timestamp': datetime.fromtimestamp(trade.get('time', 0) / 1000).isoformat()
                                })
            
            print(f"[SUCCESS] Found {len(liquidations)} potential liquidations in last {hours}h")
            return liquidations
            
        except Exception as e:
            print(f"[ERROR] Failed to get liquidations: {e}")
            return []
    
    def get_market_metrics(self) -> Dict:
        """
        Get overall market metrics
        
        Returns:
            Dictionary with market metrics
        """
        try:
            # Get all mids for market overview
            all_mids = self.info.all_mids()
            
            # Calculate total market metrics
            total_symbols = len(all_mids)
            
            # Get funding rates
            positive_funding = 0
            negative_funding = 0
            
            for symbol in self.symbols:
                funding_info = self.info.funding(symbol)
                if funding_info:
                    rate = float(funding_info.get('fundingRate', 0))
                    if rate > 0:
                        positive_funding += 1
                    elif rate < 0:
                        negative_funding += 1
            
            metrics = {
                'total_symbols': total_symbols,
                'tracked_symbols': len(self.symbols),
                'positive_funding': positive_funding,
                'negative_funding': negative_funding,
                'neutral_funding': len(self.symbols) - positive_funding - negative_funding,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"[SUCCESS] Fetched market metrics")
            return metrics
            
        except Exception as e:
            print(f"[ERROR] Failed to get market metrics: {e}")
            return {}
    
    async def save_to_supabase(self, data_type: str, data: Any):
        """
        Save stats data to Supabase
        
        Args:
            data_type: Type of data ('funding', 'volume', 'leaderboard', etc.)
            data: Data to save
        """
        try:
            table_name = f"hl_stats_{data_type}"
            
            if isinstance(data, list) and data:
                # Batch insert for lists
                self.db_manager.batch_upsert(table_name, data, ['symbol', 'timestamp'])
                print(f"[SUCCESS] Saved {len(data)} {data_type} records to Supabase")
            elif isinstance(data, dict) and data:
                # Single record insert
                self.db_manager.upsert(table_name, data)
                print(f"[SUCCESS] Saved {data_type} data to Supabase")
                
        except Exception as e:
            print(f"[ERROR] Failed to save {data_type} to Supabase: {e}")
    
    async def run_stats_update(self):
        """
        Run a single update cycle for all stats
        """
        print(f"\n[UPDATE] Fetching stats at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Fetch all data types
        funding = self.get_funding_rates()
        volume = self.get_volume_stats()
        leaderboard = self.get_leaderboard()
        liquidations = self.get_liquidations(1)
        metrics = self.get_market_metrics()
        
        # Save to Supabase
        if funding:
            await self.save_to_supabase('funding', funding)
        if volume:
            await self.save_to_supabase('volume', volume)
        if leaderboard:
            await self.save_to_supabase('leaderboard', leaderboard)
        if liquidations:
            await self.save_to_supabase('liquidations', liquidations)
        if metrics:
            await self.save_to_supabase('metrics', metrics)
        
        return {
            'funding': funding,
            'volume': volume,
            'leaderboard': leaderboard,
            'liquidations': liquidations,
            'metrics': metrics
        }


async def main():
    """Main function to demonstrate enhanced stats usage"""
    print("="*70)
    print("ENHANCED HYPERLIQUID STATS")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Initialize enhanced API
    stats_api = EnhancedStatsAPI(testnet=False)
    
    # Run stats update
    results = await stats_api.run_stats_update()
    
    # Display summary
    print("\n" + "="*70)
    print("STATS SUMMARY")
    print("="*70)
    
    if results['funding']:
        print(f"Funding Rates: {len(results['funding'])} symbols tracked")
        for item in results['funding'][:3]:
            print(f"  - {item['symbol']}: {item['funding_rate']:.4%}")
    
    if results['volume']:
        print(f"\nVolume Stats: {len(results['volume'])} symbols")
        for item in results['volume'][:3]:
            print(f"  - {item['symbol']}: ${item['volume_24h']:,.0f}")
    
    if results['metrics']:
        m = results['metrics']
        print(f"\nMarket Metrics:")
        print(f"  - Total Symbols: {m['total_symbols']}")
        print(f"  - Positive Funding: {m['positive_funding']}")
        print(f"  - Negative Funding: {m['negative_funding']}")
    
    print("\n" + "="*70)
    print("Enhanced stats integration complete!")


if __name__ == "__main__":
    asyncio.run(main())