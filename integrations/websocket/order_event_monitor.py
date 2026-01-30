"""
Order Event Monitor for Hyperliquid
====================================
This script monitors order events in real-time using WebSocket subscriptions.
It logs all order fills, closures, and updates to help track trading activity.

Available WebSocket Event Types:
- userEvents: General user events including liquidations
- userFills: Order fills with PnL information  
- orderUpdates: Order status changes
- userFundings: Funding payments
- userNonFundingLedgerUpdates: Other ledger updates
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('order_events.log'),
        logging.StreamHandler()
    ]
)

load_dotenv()

class OrderEventMonitor:
    def __init__(self):
        # Get configuration
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        
        if not secret_key or not self.account_address:
            logging.error("Missing configuration in .env file")
            sys.exit(1)
            
        # Initialize clients
        self.account: LocalAccount = eth_account.Account.from_key(secret_key)
        base_url = constants.MAINNET_API_URL
        
        self.info = Info(base_url, skip_ws=False)  # WebSocket enabled
        self.exchange = Exchange(self.account, base_url, account_address=self.account_address)
        
        # Track positions and orders
        self.positions = {}
        self.open_orders = {}
        self.fills_log = []
        
        logging.info(f"Order Event Monitor initialized for account: {self.account_address}")
    
    def on_user_events(self, event):
        """
        Handle general user events (liquidations, etc.)
        """
        logging.info(f"USER EVENT: {json.dumps(event, indent=2)}")
        
        if 'data' in event:
            data = event['data']
            # Check for liquidations
            if 'liquidations' in data:
                for liq in data['liquidations']:
                    logging.warning(f"LIQUIDATION: {liq}")
                    self.handle_liquidation(liq)
    
    def on_user_fills(self, fill_event):
        """
        Handle order fills - THIS IS THE MAIN EVENT FOR CLOSED ORDERS
        
        Fill data includes:
        - coin: Trading pair
        - px: Fill price
        - sz: Fill size
        - side: Buy/sell
        - closedPnl: Realized PnL when closing position
        - hash: Transaction hash
        - oid: Order ID
        - crossed: Whether it crossed the spread
        """
        logging.info(f"FILL EVENT: {json.dumps(fill_event, indent=2)}")
        
        if 'data' in fill_event and 'fills' in fill_event['data']:
            for fill in fill_event['data']['fills']:
                self.process_fill(fill)
    
    def process_fill(self, fill):
        """
        Process individual fill and determine if position was closed
        """
        coin = fill.get('coin', 'Unknown')
        px = float(fill.get('px', 0))
        sz = float(fill.get('sz', 0))
        side = fill.get('side', '')
        closed_pnl = fill.get('closedPnl')
        oid = fill.get('oid')
        timestamp = fill.get('time', datetime.now().isoformat())
        
        # Log the fill
        fill_record = {
            'timestamp': timestamp,
            'coin': coin,
            'side': side,
            'price': px,
            'size': sz,
            'oid': oid,
            'closed_pnl': closed_pnl
        }
        self.fills_log.append(fill_record)
        
        # Check if this is a position closure (has closedPnl)
        if closed_pnl is not None and closed_pnl != '0':
            pnl_value = float(closed_pnl)
            logging.warning(f"🔔 POSITION CLOSED - {coin}")
            logging.warning(f"   Side: {side}, Size: {sz}, Price: ${px:,.2f}")
            logging.warning(f"   Realized PnL: ${pnl_value:,.2f}")
            
            # Trigger any actions needed on position closure
            self.on_position_closed(coin, side, sz, px, pnl_value, oid)
        else:
            logging.info(f"📈 Position Opened/Increased - {coin}: {side} {sz} @ ${px:,.2f}")
    
    def on_position_closed(self, coin, side, size, price, pnl, order_id):
        """
        Webhook-like function called when a position is closed
        This is where you can trigger external actions
        """
        closure_data = {
            'event': 'POSITION_CLOSED',
            'timestamp': datetime.now().isoformat(),
            'coin': coin,
            'side': side,
            'size': size,
            'price': price,
            'realized_pnl': pnl,
            'order_id': order_id,
            'account': self.account_address
        }
        
        # Log to file
        with open('position_closures.json', 'a') as f:
            f.write(json.dumps(closure_data) + '\n')
        
        # Here you can add webhook calls, database updates, etc.
        # Example: Send to external webhook
        # self.send_webhook(closure_data)
        
        # Example: Update trading strategy based on PnL
        if pnl > 0:
            logging.info(f"✅ Profitable trade! Consider similar setups for {coin}")
        else:
            logging.info(f"❌ Loss on trade. Review strategy for {coin}")
    
    def on_order_updates(self, update):
        """
        Handle order status updates (new, cancelled, modified)
        """
        logging.info(f"ORDER UPDATE: {json.dumps(update, indent=2)}")
        
        if 'data' in update:
            data = update['data']
            # Process order updates
            if 'orders' in data:
                for order in data['orders']:
                    self.process_order_update(order)
    
    def process_order_update(self, order):
        """
        Process order status changes
        """
        oid = order.get('oid')
        status = order.get('status', '')
        coin = order.get('coin', '')
        
        if status == 'cancelled':
            logging.info(f"ORDER CANCELLED: {coin} - Order ID: {oid}")
            if oid in self.open_orders:
                del self.open_orders[oid]
        elif status == 'filled':
            logging.info(f"ORDER FILLED: {coin} - Order ID: {oid}")
            if oid in self.open_orders:
                del self.open_orders[oid]
        elif status == 'open':
            self.open_orders[oid] = order
            logging.info(f"ORDER OPENED: {coin} - Order ID: {oid}")
    
    def handle_liquidation(self, liquidation):
        """
        Handle liquidation events
        """
        coin = liquidation.get('coin', 'Unknown')
        size = liquidation.get('sz', 0)
        px = liquidation.get('px', 0)
        
        logging.critical(f"⚠️ LIQUIDATION ALERT!")
        logging.critical(f"   Coin: {coin}")
        logging.critical(f"   Size: {size}")
        logging.critical(f"   Price: ${px:,.2f}")
        
        # Emergency actions on liquidation
        # Could trigger stop-all trading, send alerts, etc.
    
    def get_fills_summary(self):
        """
        Get summary of recent fills
        """
        if not self.fills_log:
            return "No fills recorded yet"
        
        total_pnl = sum(float(f['closed_pnl']) for f in self.fills_log if f['closed_pnl'])
        
        summary = f"\n{'='*50}\n"
        summary += f"FILLS SUMMARY (Last {len(self.fills_log)} fills)\n"
        summary += f"Total Realized PnL: ${total_pnl:,.2f}\n"
        summary += f"{'='*50}\n"
        
        for fill in self.fills_log[-10:]:  # Last 10 fills
            summary += f"{fill['timestamp']}: {fill['coin']} {fill['side']} {fill['size']} @ ${fill['price']:,.2f}"
            if fill['closed_pnl']:
                summary += f" (PnL: ${float(fill['closed_pnl']):,.2f})"
            summary += "\n"
        
        return summary
    
    def start_monitoring(self):
        """
        Start WebSocket subscriptions for order events
        """
        logging.info("Starting WebSocket event monitoring...")
        
        # Subscribe to different event types
        self.info.subscribe({
            "type": "userFills",
            "user": self.account_address
        }, self.on_user_fills)
        
        self.info.subscribe({
            "type": "userEvents", 
            "user": self.account_address
        }, self.on_user_events)
        
        self.info.subscribe({
            "type": "orderUpdates",
            "user": self.account_address
        }, self.on_order_updates)
        
        logging.info("✅ Monitoring started. Listening for order events...")
        logging.info("Press Ctrl+C to stop monitoring")
        
        # Keep the script running
        try:
            import time
            while True:
                time.sleep(60)
                # Print summary every minute
                print(self.get_fills_summary())
        except KeyboardInterrupt:
            logging.info("Stopping monitor...")
            self.cleanup()
    
    def cleanup(self):
        """
        Clean up resources
        """
        # Save final state
        with open('final_fills_log.json', 'w') as f:
            json.dump(self.fills_log, f, indent=2)
        
        logging.info(f"Saved {len(self.fills_log)} fills to final_fills_log.json")
        logging.info("Monitor stopped")
    
    def send_webhook(self, data):
        """
        Example webhook sender (implement as needed)
        """
        # import requests
        # webhook_url = os.getenv('WEBHOOK_URL')
        # if webhook_url:
        #     try:
        #         response = requests.post(webhook_url, json=data, timeout=5)
        #         logging.info(f"Webhook sent: {response.status_code}")
        #     except Exception as e:
        #         logging.error(f"Webhook failed: {e}")
        pass

def main():
    """
    Main entry point
    """
    monitor = OrderEventMonitor()
    
    # You can also check recent fills historically
    logging.info("Fetching recent fills...")
    recent_fills = monitor.info.user_fills(monitor.account_address)
    
    if recent_fills:
        logging.info(f"Found {len(recent_fills)} recent fills")
        for fill in recent_fills[:5]:  # Show last 5
            monitor.process_fill(fill)
    
    # Start real-time monitoring
    monitor.start_monitoring()

if __name__ == "__main__":
    main()