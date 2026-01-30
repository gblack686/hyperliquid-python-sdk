"""
Standalone WebSocket Monitor for Hyperliquid
Runs continuously and logs all order events
"""
import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import eth_account
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

class WebSocketMonitor:
    def __init__(self):
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        
        if not secret_key or not self.account_address:
            print("ERROR: Missing HYPERLIQUID_API_KEY or ACCOUNT_ADDRESS in .env")
            sys.exit(1)
        
        account = eth_account.Account.from_key(secret_key)
        base_url = constants.MAINNET_API_URL
        self.info = Info(base_url, skip_ws=False)
        
        self.fills_count = 0
        self.positions_closed = 0
        self.total_pnl = 0.0
        
        print("="*60)
        print("HYPERLIQUID WEBSOCKET MONITOR")
        print("="*60)
        print(f"Account: {self.account_address}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        print("\nMonitoring for:")
        print("  - Order fills")
        print("  - Position closures")
        print("  - Order updates")
        print("  - User events")
        print("\n" + "="*60)
    
    def on_user_fills(self, event):
        """Handle fill events"""
        if 'data' in event and 'fills' in event['data']:
            for fill in event['data']['fills']:
                self.fills_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                coin = fill.get('coin', 'Unknown')
                side = fill.get('side', '')
                px = float(fill.get('px', 0))
                sz = float(fill.get('sz', 0))
                closed_pnl = fill.get('closedPnl')
                oid = fill.get('oid', '')
                
                # Log fill to file
                with open('fills.log', 'a') as f:
                    f.write(f"{datetime.now().isoformat()} | {json.dumps(fill)}\n")
                
                if closed_pnl and closed_pnl != '0':
                    # Position closed
                    pnl_value = float(closed_pnl)
                    self.positions_closed += 1
                    self.total_pnl += pnl_value
                    
                    print(f"\n[{timestamp}] >>> POSITION CLOSED <<<")
                    print(f"  Coin: {coin}")
                    print(f"  Side: {side}")
                    print(f"  Size: {sz}")
                    print(f"  Price: ${px:,.2f}")
                    print(f"  Realized PnL: ${pnl_value:,.2f}")
                    print(f"  Order ID: {oid}")
                    print(f"  Total PnL Today: ${self.total_pnl:,.2f}")
                    print("-"*40)
                    
                    # Log closure separately
                    with open('closures.log', 'a') as f:
                        closure_data = {
                            'timestamp': datetime.now().isoformat(),
                            'coin': coin,
                            'side': side,
                            'size': sz,
                            'price': px,
                            'pnl': pnl_value,
                            'total_pnl': self.total_pnl
                        }
                        f.write(json.dumps(closure_data) + '\n')
                else:
                    # Position opened/modified
                    print(f"\n[{timestamp}] FILL EXECUTED")
                    print(f"  {coin}: {side} {sz} @ ${px:,.2f}")
                    print(f"  Order ID: {oid}")
    
    def on_order_updates(self, event):
        """Handle order status updates"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if 'data' in event:
            print(f"\n[{timestamp}] ORDER UPDATE")
            data = event.get('data', {})
            print(f"  Data: {json.dumps(data, indent=2)}")
    
    def on_user_events(self, event):
        """Handle general user events"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if 'data' in event:
            data = event.get('data', {})
            # Check for liquidations
            if 'liquidations' in data and data['liquidations']:
                print(f"\n[{timestamp}] !!! LIQUIDATION ALERT !!!")
                print(f"  Data: {json.dumps(data['liquidations'], indent=2)}")
            elif data:  # Other events
                print(f"\n[{timestamp}] USER EVENT")
                print(f"  Data: {json.dumps(data, indent=2)}")
    
    def start(self):
        """Start monitoring"""
        print("\nStarting WebSocket subscriptions...")
        
        # Subscribe to different event types
        self.info.subscribe({
            "type": "userFills",
            "user": self.account_address
        }, self.on_user_fills)
        
        self.info.subscribe({
            "type": "orderUpdates", 
            "user": self.account_address
        }, self.on_order_updates)
        
        self.info.subscribe({
            "type": "userEvents",
            "user": self.account_address
        }, self.on_user_events)
        
        print("WebSocket subscriptions active!")
        print("\nMonitoring... (Press Ctrl+C to stop)")
        print("-"*60)
        
        # Keep running and show periodic status
        try:
            last_status = time.time()
            while True:
                time.sleep(1)
                # Show status every 30 seconds
                if time.time() - last_status > 30:
                    print(f"\n[STATUS] {datetime.now().strftime('%H:%M:%S')}")
                    print(f"  Fills: {self.fills_count}")
                    print(f"  Positions Closed: {self.positions_closed}")
                    print(f"  Total PnL: ${self.total_pnl:,.2f}")
                    print("-"*40)
                    last_status = time.time()
                    
        except KeyboardInterrupt:
            print("\n\nShutting down monitor...")
            print(f"\nSession Summary:")
            print(f"  Total Fills: {self.fills_count}")
            print(f"  Positions Closed: {self.positions_closed}")
            print(f"  Total PnL: ${self.total_pnl:,.2f}")
            print(f"  Logs saved to: fills.log, closures.log")

if __name__ == "__main__":
    monitor = WebSocketMonitor()
    monitor.start()