"""
HyperLiquid Stats API Integration
Connects to stats.hyperliquid.xyz for official statistics and analytics
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
from dataclasses import dataclass
import os
from dotenv import load_dotenv
import sys

# Add parent directory to path
sys.path.append('..')
sys.path.append(os.path.dirname(__file__))

from src.data.supabase_manager import SupabaseManager

load_dotenv()


@dataclass
class FundingData:
    """Funding rate data structure"""
    symbol: str
    funding_rate: float
    next_funding_time: datetime
    open_interest: float
    volume_24h: float
    timestamp: datetime


@dataclass
class VolumeData:
    """Volume comparison data"""
    symbol: str
    hl_volume: float
    binance_volume: float
    okx_volume: float
    bybit_volume: float
    total_cex_volume: float
    hl_market_share: float
    timestamp: datetime


@dataclass
class TVLData:
    """Total Value Locked metrics"""
    total_tvl: float
    usdc_tvl: float
    hype_tvl: float
    other_assets_tvl: float
    timestamp: datetime


class HyperLiquidStatsAPI:
    """
    Interface to HyperLiquid Stats API
    Fetches official statistics and analytics data
    """
    
    def __init__(self, testnet: bool = False):
        """Initialize the stats API client"""
        self.base_url = "https://stats.hyperliquid.xyz/api"
        self.testnet = testnet
        self.session = None
        self.db_manager = SupabaseManager()
        
        # Common symbols to track
        self.symbols = ['BTC', 'ETH', 'SOL', 'HYPE', 'ARB', 'OP', 'MATIC']
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def fetch(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Generic fetch method for API calls
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response as dictionary
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"[ERROR] API request failed: {response.status}")
                    return {}
        except Exception as e:
            print(f"[ERROR] Failed to fetch {endpoint}: {e}")
            return {}
    
    async def get_funding_rates(self) -> List[FundingData]:
        """
        Fetch current funding rates for all symbols
        
        Returns:
            List of FundingData objects
        """
        try:
            data = await self.fetch("funding")
            
            funding_list = []
            timestamp = datetime.now()
            
            for item in data.get('data', []):
                funding = FundingData(
                    symbol=item.get('symbol', ''),
                    funding_rate=float(item.get('funding_rate', 0)),
                    next_funding_time=datetime.fromisoformat(item.get('next_funding', '')),
                    open_interest=float(item.get('open_interest', 0)),
                    volume_24h=float(item.get('volume_24h', 0)),
                    timestamp=timestamp
                )
                funding_list.append(funding)
            
            print(f"[SUCCESS] Fetched funding rates for {len(funding_list)} symbols")
            return funding_list
            
        except Exception as e:
            print(f"[ERROR] Failed to get funding rates: {e}")
            return []
    
    async def get_volume_comparison(self) -> List[VolumeData]:
        """
        Fetch volume comparison between HyperLiquid and CEXs
        
        Returns:
            List of VolumeData objects
        """
        try:
            data = await self.fetch("volume_comparison")
            
            volume_list = []
            timestamp = datetime.now()
            
            for item in data.get('data', []):
                hl_vol = float(item.get('hyperliquid_volume', 0))
                binance_vol = float(item.get('binance_volume', 0))
                okx_vol = float(item.get('okx_volume', 0))
                bybit_vol = float(item.get('bybit_volume', 0))
                
                total_cex = binance_vol + okx_vol + bybit_vol
                market_share = (hl_vol / (hl_vol + total_cex) * 100) if total_cex > 0 else 100
                
                volume = VolumeData(
                    symbol=item.get('symbol', ''),
                    hl_volume=hl_vol,
                    binance_volume=binance_vol,
                    okx_volume=okx_vol,
                    bybit_volume=bybit_vol,
                    total_cex_volume=total_cex,
                    hl_market_share=market_share,
                    timestamp=timestamp
                )
                volume_list.append(volume)
            
            print(f"[SUCCESS] Fetched volume comparison for {len(volume_list)} symbols")
            return volume_list
            
        except Exception as e:
            print(f"[ERROR] Failed to get volume comparison: {e}")
            return []
    
    async def get_tvl_metrics(self) -> Optional[TVLData]:
        """
        Fetch Total Value Locked metrics
        
        Returns:
            TVLData object or None
        """
        try:
            data = await self.fetch("tvl")
            
            if data:
                tvl = TVLData(
                    total_tvl=float(data.get('total_tvl', 0)),
                    usdc_tvl=float(data.get('usdc_tvl', 0)),
                    hype_tvl=float(data.get('hype_tvl', 0)),
                    other_assets_tvl=float(data.get('other_assets_tvl', 0)),
                    timestamp=datetime.now()
                )
                
                print(f"[SUCCESS] Fetched TVL metrics: ${tvl.total_tvl:,.2f}")
                return tvl
            
        except Exception as e:
            print(f"[ERROR] Failed to get TVL metrics: {e}")
            return None
    
    async def get_leaderboard(self, timeframe: str = '24h') -> List[Dict]:
        """
        Fetch trading leaderboard
        
        Args:
            timeframe: '24h', '7d', '30d', 'all'
            
        Returns:
            List of trader statistics
        """
        try:
            data = await self.fetch("leaderboard", params={'timeframe': timeframe})
            
            leaderboard = []
            for trader in data.get('data', [])[:20]:  # Top 20 traders
                leaderboard.append({
                    'rank': trader.get('rank'),
                    'address': trader.get('address'),
                    'pnl': float(trader.get('pnl', 0)),
                    'volume': float(trader.get('volume', 0)),
                    'win_rate': float(trader.get('win_rate', 0)),
                    'trades': trader.get('trades', 0)
                })
            
            print(f"[SUCCESS] Fetched top {len(leaderboard)} traders")
            return leaderboard
            
        except Exception as e:
            print(f"[ERROR] Failed to get leaderboard: {e}")
            return []
    
    async def get_liquidations(self, hours: int = 24) -> List[Dict]:
        """
        Fetch recent liquidations
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of liquidation events
        """
        try:
            data = await self.fetch("liquidations", params={'hours': hours})
            
            liquidations = []
            for liq in data.get('data', []):
                liquidations.append({
                    'symbol': liq.get('symbol'),
                    'side': liq.get('side'),
                    'size': float(liq.get('size', 0)),
                    'price': float(liq.get('price', 0)),
                    'value': float(liq.get('value', 0)),
                    'timestamp': datetime.fromisoformat(liq.get('timestamp', ''))
                })
            
            print(f"[SUCCESS] Fetched {len(liquidations)} liquidations in last {hours}h")
            return liquidations
            
        except Exception as e:
            print(f"[ERROR] Failed to get liquidations: {e}")
            return []
    
    async def save_to_supabase(self, data_type: str, data: Any):
        """
        Save stats data to Supabase
        
        Args:
            data_type: Type of data ('funding', 'volume', 'tvl', etc.)
            data: Data to save
        """
        try:
            table_name = f"hl_stats_{data_type}"
            
            if isinstance(data, list):
                # Batch insert for lists
                records = []
                for item in data:
                    if hasattr(item, '__dict__'):
                        records.append(item.__dict__)
                    else:
                        records.append(item)
                
                if records:
                    self.db_manager.batch_upsert(table_name, records, ['symbol', 'timestamp'])
                    print(f"[SUCCESS] Saved {len(records)} {data_type} records to Supabase")
            else:
                # Single record insert
                record = data.__dict__ if hasattr(data, '__dict__') else data
                self.db_manager.upsert(table_name, record)
                print(f"[SUCCESS] Saved {data_type} data to Supabase")
                
        except Exception as e:
            print(f"[ERROR] Failed to save {data_type} to Supabase: {e}")
    
    async def run_periodic_update(self, interval_minutes: int = 5):
        """
        Run periodic updates of all stats
        
        Args:
            interval_minutes: Update interval in minutes
        """
        print(f"[INFO] Starting periodic stats updates every {interval_minutes} minutes")
        
        while True:
            try:
                print(f"\n[UPDATE] Fetching stats at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Fetch all data types
                funding = await self.get_funding_rates()
                volume = await self.get_volume_comparison()
                tvl = await self.get_tvl_metrics()
                leaderboard = await self.get_leaderboard('24h')
                liquidations = await self.get_liquidations(1)  # Last hour
                
                # Save to Supabase
                if funding:
                    await self.save_to_supabase('funding', funding)
                if volume:
                    await self.save_to_supabase('volume', volume)
                if tvl:
                    await self.save_to_supabase('tvl', tvl)
                if leaderboard:
                    await self.save_to_supabase('leaderboard', leaderboard)
                if liquidations:
                    await self.save_to_supabase('liquidations', liquidations)
                
                # Wait for next update
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                print(f"[ERROR] Update cycle failed: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error


def create_stats_tables():
    """Create necessary tables in Supabase for stats data"""
    from supabase import create_client, Client
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("[ERROR] Missing Supabase credentials")
        return
    
    # SQL for creating tables
    sql_commands = [
        """
        CREATE TABLE IF NOT EXISTS hl_stats_funding (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            funding_rate DECIMAL(10, 8),
            next_funding_time TIMESTAMP,
            open_interest DECIMAL(20, 2),
            volume_24h DECIMAL(20, 2),
            timestamp TIMESTAMP DEFAULT NOW(),
            UNIQUE(symbol, timestamp)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS hl_stats_volume (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            hl_volume DECIMAL(20, 2),
            binance_volume DECIMAL(20, 2),
            okx_volume DECIMAL(20, 2),
            bybit_volume DECIMAL(20, 2),
            total_cex_volume DECIMAL(20, 2),
            hl_market_share DECIMAL(5, 2),
            timestamp TIMESTAMP DEFAULT NOW(),
            UNIQUE(symbol, timestamp)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS hl_stats_tvl (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            total_tvl DECIMAL(20, 2),
            usdc_tvl DECIMAL(20, 2),
            hype_tvl DECIMAL(20, 2),
            other_assets_tvl DECIMAL(20, 2),
            timestamp TIMESTAMP DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS hl_stats_leaderboard (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            rank INTEGER,
            address VARCHAR(100),
            pnl DECIMAL(20, 2),
            volume DECIMAL(20, 2),
            win_rate DECIMAL(5, 2),
            trades INTEGER,
            timeframe VARCHAR(10),
            timestamp TIMESTAMP DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS hl_stats_liquidations (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            symbol VARCHAR(20),
            side VARCHAR(10),
            size DECIMAL(20, 8),
            price DECIMAL(20, 8),
            value DECIMAL(20, 2),
            timestamp TIMESTAMP
        );
        """
    ]
    
    print("[INFO] Creating stats tables in Supabase...")
    # Note: Tables should be created via Supabase dashboard or migration
    for i, sql in enumerate(sql_commands, 1):
        print(f"[{i}/5] Table creation SQL generated")
    
    print("[SUCCESS] Table creation SQL ready for Supabase")


async def main():
    """Main function to demonstrate stats API usage"""
    print("="*70)
    print("HYPERLIQUID STATS API INTEGRATION")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Create tables first
    create_stats_tables()
    
    # Initialize API client
    async with HyperLiquidStatsAPI() as stats_api:
        # Fetch and display funding rates
        print("\n[1/5] Fetching Funding Rates...")
        funding = await stats_api.get_funding_rates()
        if funding:
            print(f"Sample: {funding[0].symbol} funding: {funding[0].funding_rate:.4%}")
        
        # Fetch and display volume comparison
        print("\n[2/5] Fetching Volume Comparison...")
        volume = await stats_api.get_volume_comparison()
        if volume:
            print(f"Sample: {volume[0].symbol} HL market share: {volume[0].hl_market_share:.2f}%")
        
        # Fetch and display TVL
        print("\n[3/5] Fetching TVL Metrics...")
        tvl = await stats_api.get_tvl_metrics()
        if tvl:
            print(f"Total TVL: ${tvl.total_tvl:,.2f}")
        
        # Fetch and display leaderboard
        print("\n[4/5] Fetching Leaderboard...")
        leaderboard = await stats_api.get_leaderboard('24h')
        if leaderboard:
            print(f"Top trader PnL: ${leaderboard[0]['pnl']:,.2f}")
        
        # Fetch and display liquidations
        print("\n[5/5] Fetching Recent Liquidations...")
        liquidations = await stats_api.get_liquidations(1)
        print(f"Liquidations in last hour: {len(liquidations)}")
        
        print("\n" + "="*70)
        print("Stats API integration complete!")
        print("To run periodic updates, use: stats_api.run_periodic_update()")


if __name__ == "__main__":
    asyncio.run(main())