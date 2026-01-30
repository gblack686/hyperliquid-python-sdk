"""
Hyperliquid to Supabase Data Sync System
Collects account data, orders, positions, and fills from Hyperliquid
and syncs them to Supabase database for tracking and analysis
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount
from typing import Dict, List, Optional
from supabase import create_client, Client
from decimal import Decimal

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Load environment variables
load_dotenv()

class HyperliquidSupabaseSync:
    def __init__(self):
        """Initialize sync system with API credentials"""
        # Hyperliquid credentials
        self.hl_secret = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        self.network = os.getenv('NETWORK', 'MAINNET_API_URL')
        
        # Supabase credentials - hardcoded for now, should be in .env
        self.supabase_url = "https://lfxlrxwxnvtrzwsohojz.supabase.co"
        self.supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxmeGxyeHd4bnZ0cnp3c29ob2p6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2NTk0MDIsImV4cCI6MjA2MDIzNTQwMn0.kBCpCkkfxcHWhycF6-ClE_o_AUmfBzJi6dnU5vDJUKI"
        
        if not self.hl_secret or not self.account_address:
            print("Error: Missing Hyperliquid configuration in .env file")
            sys.exit(1)
        
        # Initialize Hyperliquid
        self.account: LocalAccount = eth_account.Account.from_key(self.hl_secret)
        self.base_url = getattr(constants, self.network)
        self.info = Info(self.base_url, skip_ws=True)
        self.exchange = Exchange(self.account, self.base_url)
        
        # Initialize Supabase
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Cache for prices
        self.all_mids = {}
        
        print(f"[INIT] Sync system initialized")
        print(f"[INIT] Hyperliquid Account: {self.account_address}")
        print(f"[INIT] Supabase URL: {self.supabase_url}")
    
    def get_current_prices(self):
        """Get current mid prices for all assets"""
        try:
            self.all_mids = self.info.all_mids()
        except Exception as e:
            print(f"[WARNING] Could not fetch current prices: {e}")
    
    def get_mark_price(self, coin: str) -> float:
        """Get current mark price for an asset"""
        if coin in self.all_mids:
            return float(self.all_mids[coin])
        return 0.0
    
    def calculate_health_score(self, margin_usage: float, leverage: float) -> tuple:
        """Calculate account health score"""
        health_score = 100
        
        # Deduct for margin usage
        if margin_usage > 80:
            health_score -= 40
            status = "CRITICAL"
        elif margin_usage > 60:
            health_score -= 25
            status = "WARNING"
        elif margin_usage > 40:
            health_score -= 10
            status = "MODERATE"
        else:
            status = "GOOD"
        
        # Deduct for leverage
        if leverage > 10:
            health_score -= 30
        elif leverage > 5:
            health_score -= 15
        elif leverage > 3:
            health_score -= 5
        
        # Final status
        if health_score >= 80:
            status = "EXCELLENT"
        elif health_score >= 60 and status not in ["CRITICAL", "WARNING"]:
            status = "GOOD"
        elif health_score >= 40 and status not in ["CRITICAL"]:
            status = "FAIR"
        else:
            status = "POOR"
        
        return health_score, status
    
    async def sync_dashboard_data(self):
        """Sync account dashboard data to Supabase"""
        try:
            print(f"\n[SYNC] Fetching dashboard data...")
            
            # Get user state
            user_state = self.info.user_state(self.account_address)
            
            # Parse values
            margin_summary = user_state.get("marginSummary", {})
            account_value = float(margin_summary.get("accountValue", 0))
            total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
            total_ntl_pos = float(margin_summary.get("totalNtlPos", 0))
            total_raw_usd = float(margin_summary.get("totalRawUsd", 0))
            withdrawable = float(user_state.get("withdrawable", 0))
            maintenance_margin = float(user_state.get("crossMaintenanceMarginUsed", 0))
            
            # Calculate metrics
            actual_leverage = total_ntl_pos / account_value if account_value > 0 else 0
            margin_usage_pct = (total_margin_used / account_value * 100) if account_value > 0 else 0
            free_margin = account_value - total_margin_used
            margin_level = (account_value / total_margin_used * 100) if total_margin_used > 0 else 0
            liquidation_buffer_pct = ((account_value - maintenance_margin) / account_value * 100) if account_value > 0 else 0
            
            # Calculate total PnL from positions
            positions = user_state.get("assetPositions", [])
            total_positions = 0
            total_unrealized_pnl = 0
            
            for pos_data in positions:
                position = pos_data.get("position", {})
                szi = float(position.get("szi", 0))
                if szi != 0:
                    total_positions += 1
                    total_unrealized_pnl += float(position.get("unrealizedPnl", 0))
            
            # Calculate health score
            health_score, health_status = self.calculate_health_score(margin_usage_pct, actual_leverage)
            
            # Prepare data for insertion
            dashboard_data = {
                "account_address": self.account_address,
                "account_value": str(account_value),
                "withdrawable": str(withdrawable),
                "total_margin_used": str(total_margin_used),
                "total_notional_position": str(total_ntl_pos),
                "total_raw_usd": str(total_raw_usd),
                "maintenance_margin": str(maintenance_margin),
                "actual_leverage": str(actual_leverage),
                "margin_usage_pct": str(margin_usage_pct),
                "free_margin": str(free_margin),
                "margin_level": str(margin_level),
                "liquidation_buffer_pct": str(liquidation_buffer_pct),
                "total_positions": total_positions,
                "total_unrealized_pnl": str(total_unrealized_pnl),
                "health_score": health_score,
                "health_status": health_status,
                "raw_user_state": user_state
            }
            
            # Insert into Supabase
            result = self.supabase.table('hl_dashboard').insert(dashboard_data).execute()
            print(f"[SUCCESS] Dashboard data synced - Health: {health_status} ({health_score}/100)")
            
            return user_state
            
        except Exception as e:
            print(f"[ERROR] Failed to sync dashboard data: {e}")
            return None
    
    async def sync_positions(self, user_state: Dict):
        """Sync position data to Supabase"""
        try:
            print(f"[SYNC] Fetching position data...")
            
            # Get current prices
            self.get_current_prices()
            
            positions = user_state.get("assetPositions", [])
            synced_count = 0
            
            for pos_data in positions:
                position = pos_data.get("position", {})
                szi = float(position.get("szi", 0))
                
                if szi == 0:
                    continue
                
                coin = position.get("coin", "Unknown")
                entry_px = float(position.get("entryPx", 0))
                liq_px = float(position.get("liquidationPx", 0))
                position_value = float(position.get("positionValue", 0))
                margin_used = float(position.get("marginUsed", 0))
                unrealized_pnl = float(position.get("unrealizedPnl", 0))
                return_on_equity = float(position.get("returnOnEquity", 0))
                
                leverage_info = position.get("leverage", {})
                leverage_type = leverage_info.get("type", "cross")
                leverage_value = leverage_info.get("value", 1)
                max_leverage = position.get("maxLeverage", 10)
                
                # Get current mark price
                mark_px = self.get_mark_price(coin)
                if mark_px == 0:
                    mark_px = position_value / abs(szi) if szi != 0 else 0
                
                # Calculate liquidation distance
                if liq_px > 0 and mark_px > 0:
                    if szi > 0:  # Long
                        liq_distance_pct = ((mark_px - liq_px) / mark_px) * 100
                    else:  # Short
                        liq_distance_pct = ((liq_px - mark_px) / mark_px) * 100
                else:
                    liq_distance_pct = 0
                
                # Get funding info
                cum_funding = position.get("cumFunding", {})
                funding_since_open = float(cum_funding.get("sinceOpen", 0))
                funding_all_time = float(cum_funding.get("allTime", 0))
                
                # Prepare position data
                position_data = {
                    "account_address": self.account_address,
                    "coin": coin,
                    "side": "LONG" if szi > 0 else "SHORT",
                    "size": str(abs(szi)),
                    "entry_price": str(entry_px),
                    "mark_price": str(mark_px),
                    "liquidation_price": str(liq_px),
                    "position_value": str(position_value),
                    "margin_used": str(margin_used),
                    "unrealized_pnl": str(unrealized_pnl),
                    "return_on_equity": str(return_on_equity),
                    "leverage_type": leverage_type,
                    "leverage_value": str(leverage_value),
                    "max_leverage": str(max_leverage),
                    "liquidation_distance_pct": str(liq_distance_pct),
                    "funding_since_open": str(funding_since_open),
                    "funding_all_time": str(funding_all_time),
                    "raw_position": position
                }
                
                # Insert into Supabase
                result = self.supabase.table('hl_positions').insert(position_data).execute()
                synced_count += 1
            
            print(f"[SUCCESS] {synced_count} positions synced")
            
        except Exception as e:
            print(f"[ERROR] Failed to sync positions: {e}")
    
    async def sync_orders(self):
        """Sync open orders to Supabase"""
        try:
            print(f"[SYNC] Fetching open orders...")
            
            open_orders = self.info.open_orders(self.account_address)
            
            if not open_orders:
                print(f"[INFO] No open orders to sync")
                return
            
            synced_count = 0
            
            for order in open_orders:
                order_id = str(order.get("oid", ""))
                
                # Check if order already exists
                existing = self.supabase.table('hl_orders').select("*").eq('order_id', order_id).execute()
                
                coin = order.get("coin", "Unknown")
                side = order.get("side", "")
                order_type = order.get("orderType", "Limit")
                sz = float(order.get("sz", 0))
                limit_px = float(order.get("limitPx", 0))
                filled = float(order.get("filled", 0))
                cloid = order.get("cloid", "")
                
                # Calculate fill percentage
                fill_pct = (filled / sz * 100) if sz > 0 else 0
                
                # Determine status
                if filled >= sz:
                    status = "Filled"
                elif filled > 0:
                    status = "Partial"
                else:
                    status = "Open"
                
                order_data = {
                    "account_address": self.account_address,
                    "order_id": order_id,
                    "coin": coin,
                    "side": side,
                    "order_type": order_type,
                    "size": str(sz),
                    "limit_price": str(limit_px),
                    "filled": str(filled),
                    "status": status,
                    "fill_percentage": str(fill_pct),
                    "cloid": cloid,
                    "raw_order": order
                }
                
                if existing.data:
                    # Update existing order
                    result = self.supabase.table('hl_orders').update(order_data).eq('order_id', order_id).execute()
                else:
                    # Insert new order
                    result = self.supabase.table('hl_orders').insert(order_data).execute()
                
                synced_count += 1
            
            print(f"[SUCCESS] {synced_count} orders synced")
            
        except Exception as e:
            print(f"[ERROR] Failed to sync orders: {e}")
    
    async def sync_recent_fills(self):
        """Sync recent fills to Supabase"""
        try:
            print(f"[SYNC] Fetching recent fills...")
            
            fills = self.info.user_fills(self.account_address)
            
            if not fills:
                print(f"[INFO] No fills to sync")
                return
            
            # Get last 100 fills
            recent_fills = fills[:100]
            synced_count = 0
            skipped_count = 0
            
            for fill in recent_fills:
                fill_time = datetime.fromtimestamp(int(fill.get("time", 0)) / 1000)
                coin = fill.get("coin", "Unknown")
                side = fill.get("side", "")
                sz = float(fill.get("sz", 0))
                px = float(fill.get("px", 0))
                fee = float(fill.get("fee", 0))
                fee_token = fill.get("feeToken", "USDC")
                start_position = fill.get("startPosition", False)
                
                value = sz * px
                
                fill_data = {
                    "account_address": self.account_address,
                    "fill_time": fill_time.isoformat(),
                    "coin": coin,
                    "side": side,
                    "size": str(sz),
                    "price": str(px),
                    "value": str(value),
                    "fee": str(fee),
                    "fee_token": fee_token,
                    "start_position": str(start_position) if start_position else "0",
                    "raw_fill": fill
                }
                
                try:
                    # Insert with conflict handling
                    result = self.supabase.table('hl_fills').insert(fill_data).execute()
                    synced_count += 1
                except Exception as e:
                    if "duplicate" in str(e).lower():
                        skipped_count += 1
                    else:
                        print(f"[WARNING] Failed to insert fill: {e}")
            
            print(f"[SUCCESS] {synced_count} fills synced, {skipped_count} duplicates skipped")
            
        except Exception as e:
            print(f"[ERROR] Failed to sync fills: {e}")
    
    async def update_order_status(self):
        """Check and update status of existing orders"""
        try:
            print(f"[SYNC] Updating order statuses...")
            
            # Get open/partial orders from database
            db_orders = self.supabase.table('hl_orders').select("*").in_('status', ['Open', 'Partial']).execute()
            
            if not db_orders.data:
                print(f"[INFO] No orders to update")
                return
            
            # Get current open orders from Hyperliquid
            current_orders = self.info.open_orders(self.account_address)
            current_order_ids = {str(o.get("oid", "")) for o in current_orders}
            
            updated_count = 0
            
            for db_order in db_orders.data:
                order_id = db_order['order_id']
                
                if order_id not in current_order_ids:
                    # Order is no longer open, mark as filled or cancelled
                    # Check fills to determine if it was filled
                    fills = self.info.user_fills(self.account_address)
                    order_fills = [f for f in fills if str(f.get("oid", "")) == order_id]
                    
                    if order_fills:
                        status = "Filled"
                    else:
                        status = "Cancelled"
                    
                    # Update status in database
                    update_data = {
                        "status": status,
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    result = self.supabase.table('hl_orders').update(update_data).eq('order_id', order_id).execute()
                    updated_count += 1
                    print(f"[UPDATE] Order {order_id[:8]}... marked as {status}")
            
            print(f"[SUCCESS] {updated_count} order statuses updated")
            
        except Exception as e:
            print(f"[ERROR] Failed to update order statuses: {e}")
    
    async def run_sync_cycle(self):
        """Run a complete sync cycle"""
        print(f"\n{'='*60}")
        print(f"[SYNC] Starting sync cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # Sync dashboard data
        user_state = await self.sync_dashboard_data()
        
        if user_state:
            # Sync positions
            await self.sync_positions(user_state)
        
        # Sync orders
        await self.sync_orders()
        
        # Sync recent fills
        await self.sync_recent_fills()
        
        # Update order statuses
        await self.update_order_status()
        
        print(f"[SYNC] Cycle completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async def run_continuous_sync(self, interval_seconds: int = 60):
        """Run continuous sync with specified interval"""
        print(f"[SYNC] Starting continuous sync with {interval_seconds}s interval")
        print(f"[SYNC] Press Ctrl+C to stop")
        
        try:
            while True:
                await self.run_sync_cycle()
                print(f"\n[SYNC] Next sync in {interval_seconds} seconds...")
                await asyncio.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print(f"\n[SYNC] Stopped by user")
        except Exception as e:
            print(f"\n[ERROR] Sync failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hyperliquid to Supabase Sync')
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Sync interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run sync once and exit'
    )
    
    args = parser.parse_args()
    
    # Initialize sync system
    sync = HyperliquidSupabaseSync()
    
    if args.once:
        # Run once
        await sync.run_sync_cycle()
    else:
        # Run continuously
        await sync.run_continuous_sync(interval_seconds=args.interval)


if __name__ == "__main__":
    asyncio.run(main())