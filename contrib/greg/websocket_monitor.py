"""
Hyperliquid WebSocket Monitor
Real-time monitoring of orders, fills, and account events using WebSocket
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount
from typing import Dict, List, Optional
from supabase import create_client, Client
from colorama import init, Fore, Style

from hyperliquid.info import Info
from hyperliquid.utils import constants

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

class WebSocketMonitor:
    def __init__(self, use_supabase: bool = True):
        """Initialize WebSocket monitor
        
        Args:
            use_supabase: Whether to sync data to Supabase
        """
        # Hyperliquid credentials
        self.secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        self.network = os.getenv('NETWORK', 'MAINNET_API_URL')
        
        if not self.secret_key or not self.account_address:
            print(f"{Fore.RED}Error: Missing Hyperliquid configuration in .env file")
            sys.exit(1)
        
        # Initialize Hyperliquid with WebSocket support
        self.account: LocalAccount = eth_account.Account.from_key(self.secret_key)
        self.base_url = getattr(constants, self.network)
        # IMPORTANT: skip_ws=False to enable WebSocket
        self.info = Info(self.base_url, skip_ws=False)
        
        # Initialize Supabase if enabled
        self.use_supabase = use_supabase
        if self.use_supabase:
            self.supabase_url = "https://lfxlrxwxnvtrzwsohojz.supabase.co"
            self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if self.supabase_key:
                self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
                print(f"{Fore.GREEN}[INIT] Supabase integration enabled")
            else:
                print(f"{Fore.YELLOW}[INIT] Supabase key not found, disabling integration")
                self.use_supabase = False
        
        print(f"{Fore.GREEN}[INIT] WebSocket Monitor Initialized")
        print(f"[INIT] Account: {self.account_address}")
        print(f"[INIT] Network: {self.network.replace('_API_URL', '')}")
        print(f"[INIT] WebSocket: Enabled")
        
        # Statistics
        self.stats = {
            "orders_received": 0,
            "fills_received": 0,
            "events_received": 0,
            "errors": 0
        }
    
    def handle_order_update(self, data):
        """Handle order update from WebSocket"""
        try:
            self.stats["orders_received"] += 1
            
            print(f"\n{Fore.CYAN}[ORDER UPDATE] {datetime.now().strftime('%H:%M:%S')}")
            print(f"  Raw data type: {type(data)}")
            
            # Parse order data - handle different formats
            if isinstance(data, dict):
                # Check if it's a snapshot or update
                if "data" in data:
                    orders = data.get("data", [])
                    for order in orders:
                        if isinstance(order, dict):
                            self.process_order(order)
                else:
                    # Single order update
                    self.process_order(data)
            elif isinstance(data, list):
                for order in data:
                    if isinstance(order, dict):
                        self.process_order(order)
            else:
                print(f"  Unexpected data format: {data}")
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"{Fore.RED}[ERROR] Order update error: {e}")
    
    def process_order(self, order: Dict):
        """Process individual order"""
        try:
            # Extract order details
            order_id = str(order.get("oid", ""))
            coin = order.get("coin", "Unknown")
            side = order.get("side", "")
            sz = float(order.get("sz", 0))
            limit_px = float(order.get("limitPx", 0))
            filled = float(order.get("filled", 0))
            status = order.get("status", "Unknown")
            
            # Determine order status
            if filled >= sz:
                status = "Filled"
            elif filled > 0:
                status = "Partial"
            else:
                status = "Open"
            
            # Display order
            side_color = Fore.GREEN if side == "B" else Fore.RED
            side_text = "BUY" if side == "B" else "SELL"
            
            print(f"  {coin}: {side_color}{side_text}{Style.RESET_ALL} {sz} @ ${limit_px:.2f}")
            print(f"  Status: {status} | Filled: {filled}/{sz}")
            print(f"  Order ID: {order_id[:12]}...")
            
            # Sync to Supabase if enabled
            if self.use_supabase and order_id:
                self.sync_order_to_supabase(order, order_id, status)
                
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Process order error: {e}")
    
    def sync_order_to_supabase(self, order: Dict, order_id: str, status: str):
        """Sync order to Supabase"""
        try:
            order_data = {
                "account_address": self.account_address,
                "order_id": order_id,
                "coin": order.get("coin", "Unknown"),
                "side": order.get("side", ""),
                "order_type": order.get("orderType", "Limit"),
                "size": str(order.get("sz", 0)),
                "limit_price": str(order.get("limitPx", 0)),
                "filled": str(order.get("filled", 0)),
                "status": status,
                "fill_percentage": str((float(order.get("filled", 0)) / float(order.get("sz", 1))) * 100),
                "cloid": order.get("cloid", ""),
                "raw_order": order
            }
            
            # Check if order exists
            existing = self.supabase.table('hl_orders').select("*").eq('order_id', order_id).execute()
            
            if existing.data:
                # Update existing order
                result = self.supabase.table('hl_orders').update(order_data).eq('order_id', order_id).execute()
                print(f"  {Fore.GREEN}[DB] Order updated in Supabase")
            else:
                # Insert new order
                result = self.supabase.table('hl_orders').insert(order_data).execute()
                print(f"  {Fore.GREEN}[DB] Order added to Supabase")
                
        except Exception as e:
            print(f"  {Fore.YELLOW}[DB] Supabase sync failed: {e}")
    
    def handle_user_fill(self, data):
        """Handle user fill from WebSocket"""
        try:
            self.stats["fills_received"] += 1
            
            print(f"\n{Fore.GREEN}[FILL] {datetime.now().strftime('%H:%M:%S')}")
            print(f"  Raw data type: {type(data)}")
            
            # Parse fill data - handle both dict and list formats
            if isinstance(data, dict):
                if "data" in data:
                    fills = data.get("data", [])
                    for fill in fills:
                        if isinstance(fill, dict):
                            self.process_fill(fill)
                else:
                    self.process_fill(data)
            elif isinstance(data, list):
                for fill in data:
                    if isinstance(fill, dict):
                        self.process_fill(fill)
            else:
                print(f"  Unexpected data format: {data}")
                    
        except Exception as e:
            self.stats["errors"] += 1
            print(f"{Fore.RED}[ERROR] Fill error: {e}")
    
    def process_fill(self, fill: Dict):
        """Process individual fill"""
        try:
            # Extract fill details
            coin = fill.get("coin", "Unknown")
            side = fill.get("side", "")
            sz = float(fill.get("sz", 0))
            px = float(fill.get("px", 0))
            fee = float(fill.get("fee", 0))
            
            side_color = Fore.GREEN if side == "B" else Fore.RED
            side_text = "BOUGHT" if side == "B" else "SOLD"
            
            print(f"  {side_color}{side_text}{Style.RESET_ALL} {sz} {coin} @ ${px:.2f}")
            print(f"  Fee: ${fee:.4f} | Value: ${sz * px:.2f}")
            
            # Sync to Supabase if enabled
            if self.use_supabase:
                self.sync_fill_to_supabase(fill)
                
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Process fill error: {e}")
    
    def sync_fill_to_supabase(self, fill: Dict):
        """Sync fill to Supabase"""
        try:
            fill_time = datetime.fromtimestamp(int(fill.get("time", 0)) / 1000)
            
            fill_data = {
                "account_address": self.account_address,
                "fill_time": fill_time.isoformat(),
                "coin": fill.get("coin", "Unknown"),
                "side": fill.get("side", ""),
                "size": str(fill.get("sz", 0)),
                "price": str(fill.get("px", 0)),
                "value": str(float(fill.get("sz", 0)) * float(fill.get("px", 0))),
                "fee": str(fill.get("fee", 0)),
                "fee_token": fill.get("feeToken", "USDC"),
                "start_position": fill.get("startPosition", False),
                "raw_fill": fill
            }
            
            try:
                result = self.supabase.table('hl_fills').insert(fill_data).execute()
                print(f"  {Fore.GREEN}[DB] Fill added to Supabase")
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    print(f"  {Fore.YELLOW}[DB] Fill sync failed: {e}")
                    
        except Exception as e:
            print(f"  {Fore.YELLOW}[DB] Fill sync error: {e}")
    
    def handle_user_event(self, data: Dict):
        """Handle user event from WebSocket"""
        try:
            self.stats["events_received"] += 1
            
            print(f"\n{Fore.YELLOW}[EVENT] {datetime.now().strftime('%H:%M:%S')}")
            print(f"  Type: {data.get('type', 'Unknown')}")
            
            # You can add more specific event handling here
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"{Fore.RED}[ERROR] Event error: {e}")
    
    def handle_web_data(self, data: Dict):
        """Handle web data updates (includes positions, margin, etc.)"""
        try:
            print(f"\n{Fore.MAGENTA}[WEB DATA] {datetime.now().strftime('%H:%M:%S')}")
            
            if isinstance(data, dict) and "data" in data:
                web_data = data.get("data", {})
                
                # Extract key metrics
                margin_summary = web_data.get("marginSummary", {})
                account_value = float(margin_summary.get("accountValue", 0))
                
                if account_value > 0:
                    print(f"  Account Value: ${account_value:,.2f}")
                    
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Web data error: {e}")
    
    def display_stats(self):
        """Display current statistics"""
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.CYAN}STATISTICS")
        print(f"{Fore.CYAN}{'='*50}")
        print(f"Orders Received: {self.stats['orders_received']}")
        print(f"Fills Received: {self.stats['fills_received']}")
        print(f"Events Received: {self.stats['events_received']}")
        print(f"Errors: {self.stats['errors']}")
    
    def start_monitoring(self):
        """Start WebSocket monitoring"""
        print(f"\n{Fore.GREEN}[START] WebSocket monitoring started")
        print(f"[INFO] Subscribing to real-time updates...")
        
        # Subscribe to order updates
        self.info.subscribe(
            {"type": "orderUpdates", "user": self.account_address},
            self.handle_order_update
        )
        print(f"  [OK] Subscribed to order updates")
        
        # Subscribe to user fills
        self.info.subscribe(
            {"type": "userFills", "user": self.account_address},
            self.handle_user_fill
        )
        print(f"  [OK] Subscribed to user fills")
        
        # Subscribe to user events
        self.info.subscribe(
            {"type": "userEvents", "user": self.account_address},
            self.handle_user_event
        )
        print(f"  [OK] Subscribed to user events")
        
        # Subscribe to web data (includes positions, margin, etc.)
        self.info.subscribe(
            {"type": "webData2", "user": self.account_address},
            self.handle_web_data
        )
        print(f"  [OK] Subscribed to web data")
        
        print(f"\n{Fore.CYAN}[READY] Listening for updates...")
        print(f"[INFO] Press Ctrl+C to stop")
        
        # Keep the program running
        try:
            while True:
                # Display stats every 60 seconds
                import time
                time.sleep(60)
                self.display_stats()
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}[STOP] Monitoring stopped by user")
            self.display_stats()


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hyperliquid WebSocket Monitor')
    parser.add_argument(
        '--no-supabase',
        action='store_true',
        help='Disable Supabase integration'
    )
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = WebSocketMonitor(use_supabase=not args.no_supabase)
    
    # Start monitoring
    monitor.start_monitoring()


if __name__ == "__main__":
    main()