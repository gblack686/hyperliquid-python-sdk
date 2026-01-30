"""
Combined script to start monitoring and place a trade
"""
import os
import sys
import json
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
import eth_account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()

class MonitorAndTrade:
    def __init__(self):
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        
        # Initialize clients
        account = eth_account.Account.from_key(secret_key)
        base_url = constants.MAINNET_API_URL
        
        self.info = Info(base_url, skip_ws=False)
        self.exchange = Exchange(account, base_url, account_address=self.account_address)
        
        self.fills_log = []
        print(f"Initialized for account: {self.account_address}")
    
    def on_user_fills(self, event):
        """Handle fill events"""
        if 'data' in event and 'fills' in event['data']:
            for fill in event['data']['fills']:
                timestamp = datetime.now().strftime("%H:%M:%S")
                coin = fill.get('coin', 'Unknown')
                side = fill.get('side', '')
                px = float(fill.get('px', 0))
                sz = float(fill.get('sz', 0))
                closed_pnl = fill.get('closedPnl')
                
                self.fills_log.append(fill)
                
                if closed_pnl and closed_pnl != '0':
                    print(f"\n[{timestamp}] 🔔 POSITION CLOSED - {coin}")
                    print(f"  Side: {side}, Size: {sz}, Price: ${px:,.2f}")
                    print(f"  Realized PnL: ${float(closed_pnl):,.2f}")
                else:
                    print(f"\n[{timestamp}] 📈 FILL - {coin}: {side} {sz} @ ${px:,.2f}")
    
    def start_monitoring(self):
        """Start WebSocket monitoring in background"""
        print("\n✅ Starting WebSocket monitoring...")
        self.info.subscribe({
            "type": "userFills",
            "user": self.account_address
        }, self.on_user_fills)
        
        self.info.subscribe({
            "type": "orderUpdates",
            "user": self.account_address
        }, lambda x: print(f"\n📋 Order Update: {x.get('data', {})}"))
        
        print("✅ Monitoring active - will show fills in real-time\n")
    
    def place_hype_order(self, usd_amount):
        """Place a HYPE buy order"""
        print(f"\n{'='*60}")
        print(f"Placing ${usd_amount} HYPE order...")
        print(f"{'='*60}")
        
        # Get current price
        all_mids = self.info.all_mids()
        hype_price = float(all_mids.get("HYPE", 0))
        
        if hype_price == 0:
            print("Error: Could not get HYPE price")
            return
        
        # Calculate order details
        hype_quantity = round(usd_amount / hype_price, 2)
        limit_price = round(hype_price * 1.001, 2)  # 0.1% above market
        
        print(f"Current HYPE Price: ${hype_price:,.2f}")
        print(f"Order Quantity: {hype_quantity} HYPE")
        print(f"Limit Price: ${limit_price:,.2f}")
        
        # Place the order
        try:
            order_result = self.exchange.order(
                "HYPE",
                True,  # is_buy
                hype_quantity,
                limit_price,
                {"limit": {"tif": "Ioc"}},  # Immediate or Cancel
                False  # reduce_only
            )
            
            if order_result.get("status") == "ok":
                print(f"\n✅ Order placed successfully!")
                statuses = order_result.get("response", {}).get("data", {}).get("statuses", [])
                for status in statuses:
                    filled = status.get("filled", {})
                    if filled:
                        total_sz = float(filled.get("totalSz", 0))
                        avg_px = float(filled.get("avgPx", 0))
                        if total_sz > 0:
                            print(f"Filled: {total_sz} HYPE @ ${avg_px:,.2f}")
                            print(f"Total Cost: ${total_sz * avg_px:,.2f}")
            else:
                print(f"Order failed: {order_result}")
                
        except Exception as e:
            print(f"Error placing order: {e}")

def main():
    # Create monitor instance
    monitor = MonitorAndTrade()
    
    # Start monitoring in background
    monitor.start_monitoring()
    
    # Wait a moment for WebSocket to connect
    print("Waiting for WebSocket connection...")
    time.sleep(2)
    
    # Place the $50 HYPE order
    monitor.place_hype_order(50)
    
    # Keep monitoring running
    print(f"\n{'='*60}")
    print("Monitor running - Press Ctrl+C to stop")
    print("Will show any fills or order updates in real-time")
    print(f"{'='*60}\n")
    
    try:
        while True:
            time.sleep(30)
            if monitor.fills_log:
                print(f"\n[Status] Total fills recorded: {len(monitor.fills_log)}")
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        print(f"Total fills during session: {len(monitor.fills_log)}")
        if monitor.fills_log:
            print("\nLast 5 fills:")
            for fill in monitor.fills_log[-5:]:
                print(f"  {fill.get('coin')} {fill.get('side')} {fill.get('sz')} @ {fill.get('px')}")

if __name__ == "__main__":
    main()