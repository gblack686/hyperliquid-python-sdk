"""
Enhanced WebSocket Monitor with Full Data Display
Shows all available fields including timestamps, fees, and position details
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
from collections import defaultdict

load_dotenv()

class EnhancedMonitor:
    def __init__(self):
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        
        account = eth_account.Account.from_key(secret_key)
        base_url = constants.MAINNET_API_URL
        self.info = Info(base_url, skip_ws=False)
        
        # Track statistics
        self.positions = defaultdict(lambda: {'size': 0, 'total_cost': 0, 'realized_pnl': 0})
        self.session_stats = {
            'total_fills': 0,
            'buy_fills': 0,
            'sell_fills': 0,
            'total_volume': 0,
            'total_fees': 0,
            'realized_pnl': 0,
            'positions_closed': 0
        }
        
        print("="*80)
        print("ENHANCED HYPERLIQUID WEBSOCKET MONITOR")
        print("="*80)
        print(f"Account: {self.account_address}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
    
    def on_user_fills(self, event):
        """Handle fill events with all available data"""
        if 'data' in event and 'fills' in event['data']:
            fills = event['data']['fills']
            is_snapshot = event['data'].get('isSnapshot', False)
            
            if is_snapshot:
                print("\n[SNAPSHOT] Initial fills data received")
                return
            
            for fill in fills:
                self.process_fill(fill)
    
    def process_fill(self, fill):
        """Process a single fill with all fields"""
        # Extract all available fields
        coin = fill.get('coin', 'Unknown')
        px = float(fill.get('px', 0))
        sz = float(fill.get('sz', 0))
        side = fill.get('side', '')  # 'B' for Buy, 'A' for Ask/Sell
        timestamp = fill.get('time', 0)  # Unix timestamp in milliseconds
        start_position = fill.get('startPosition', '')
        direction = fill.get('dir', '')  # 'Open Long', 'Close Long', etc.
        closed_pnl = fill.get('closedPnl', '')
        tx_hash = fill.get('hash', '')
        order_id = fill.get('oid', '')
        crossed = fill.get('crossed', False)
        fee = float(fill.get('fee', 0))
        trade_id = fill.get('tid', '')
        fee_token = fill.get('feeToken', 'USDC')  # For spot trades
        
        # Convert timestamp to readable format
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)  # Convert ms to seconds
            time_str = dt.strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds
            date_str = dt.strftime('%Y-%m-%d')
        else:
            time_str = "No timestamp"
            date_str = ""
        
        # Update statistics
        self.session_stats['total_fills'] += 1
        self.session_stats['total_volume'] += sz * px
        self.session_stats['total_fees'] += fee
        
        if side == 'B':
            self.session_stats['buy_fills'] += 1
            side_display = "BUY"
        else:
            self.session_stats['sell_fills'] += 1
            side_display = "SELL"
        
        # Print detailed fill information
        print(f"\n{'='*80}")
        print(f"FILL #{self.session_stats['total_fills']} - {time_str}")
        print(f"{'='*80}")
        print(f"Coin:           {coin}")
        print(f"Side:           {side_display} ({side})")
        print(f"Price:          ${px:,.4f}")
        print(f"Size:           {sz:,.4f}")
        print(f"Value:          ${sz * px:,.2f}")
        print(f"Direction:      {direction if direction else 'N/A'}")
        print(f"Start Position: {start_position if start_position else 'N/A'}")
        
        if fee > 0:
            print(f"Fee:            ${fee:,.6f} {fee_token if fee_token else ''}")
            fee_rate = (fee / (sz * px)) * 100 if sz * px > 0 else 0
            print(f"Fee Rate:       {fee_rate:.4f}%")
        
        if closed_pnl and closed_pnl != '0':
            pnl_value = float(closed_pnl)
            self.session_stats['realized_pnl'] += pnl_value
            self.session_stats['positions_closed'] += 1
            self.positions[coin]['realized_pnl'] += pnl_value
            
            print(f"**POSITION CLOSED**")
            print(f"Realized PnL:   ${pnl_value:,.2f}")
            print(f"Session PnL:    ${self.session_stats['realized_pnl']:,.2f}")
            
            # Calculate return percentage if we have position data
            if self.positions[coin]['total_cost'] > 0:
                roi = (pnl_value / self.positions[coin]['total_cost']) * 100
                print(f"ROI:            {roi:.2f}%")
        
        print(f"Crossed:        {'Yes' if crossed else 'No'}")
        print(f"Order ID:       {order_id}")
        print(f"Trade ID:       {trade_id}")
        print(f"Timestamp:      {timestamp} ({date_str} {time_str})")
        print(f"TX Hash:        {tx_hash[:16]}..." if tx_hash else "TX Hash:        N/A")
        
        # Update position tracking
        if side == 'B':  # Buy - increase position
            self.positions[coin]['size'] += sz
            self.positions[coin]['total_cost'] += sz * px
        else:  # Sell - decrease position
            self.positions[coin]['size'] -= sz
            self.positions[coin]['total_cost'] -= sz * px
        
        # Log to file with full data
        with open('enhanced_fills.json', 'a') as f:
            fill_data = {
                'timestamp': timestamp,
                'datetime': f"{date_str} {time_str}",
                'coin': coin,
                'side': side,
                'price': px,
                'size': sz,
                'value': sz * px,
                'direction': direction,
                'start_position': start_position,
                'closed_pnl': float(closed_pnl) if closed_pnl else 0,
                'fee': fee,
                'fee_token': fee_token,
                'crossed': crossed,
                'order_id': order_id,
                'trade_id': trade_id,
                'hash': tx_hash
            }
            f.write(json.dumps(fill_data) + '\n')
    
    def on_order_updates(self, event):
        """Handle order updates"""
        if 'data' in event:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{timestamp}] ORDER UPDATE")
            print(json.dumps(event['data'], indent=2))
    
    def show_summary(self):
        """Display session summary"""
        print(f"\n{'='*80}")
        print("SESSION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Fills:        {self.session_stats['total_fills']}")
        print(f"Buy Orders:         {self.session_stats['buy_fills']}")
        print(f"Sell Orders:        {self.session_stats['sell_fills']}")
        print(f"Total Volume:       ${self.session_stats['total_volume']:,.2f}")
        print(f"Total Fees Paid:    ${self.session_stats['total_fees']:,.4f}")
        print(f"Positions Closed:   {self.session_stats['positions_closed']}")
        print(f"Realized PnL:       ${self.session_stats['realized_pnl']:,.2f}")
        
        if self.session_stats['total_volume'] > 0:
            avg_fee_rate = (self.session_stats['total_fees'] / self.session_stats['total_volume']) * 100
            print(f"Avg Fee Rate:       {avg_fee_rate:.4f}%")
        
        print(f"\nOpen Positions:")
        for coin, data in self.positions.items():
            if abs(data['size']) > 0.0001:  # Only show non-zero positions
                avg_price = data['total_cost'] / data['size'] if data['size'] != 0 else 0
                print(f"  {coin}: {data['size']:.4f} @ avg ${avg_price:.4f}")
        print(f"{'='*80}")
    
    def start(self):
        """Start monitoring"""
        print("\nStarting WebSocket subscriptions...")
        
        # Subscribe to fills with full data
        self.info.subscribe({
            "type": "userFills",
            "user": self.account_address
        }, self.on_user_fills)
        
        self.info.subscribe({
            "type": "orderUpdates",
            "user": self.account_address
        }, self.on_order_updates)
        
        print("Monitoring active! Full fill data will be displayed.")
        print("-"*80)
        
        try:
            last_summary = time.time()
            while True:
                time.sleep(1)
                # Show summary every 60 seconds
                if time.time() - last_summary > 60:
                    self.show_summary()
                    last_summary = time.time()
                    
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.show_summary()
            print("\nFull data saved to: enhanced_fills.json")

if __name__ == "__main__":
    monitor = EnhancedMonitor()
    monitor.start()