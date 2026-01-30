"""
Hyperliquid + Supabase Integration
===================================
Monitors Hyperliquid events via WebSocket and stores them in Supabase.
Can be run locally, on a VPS, or as a Docker container.

Requirements:
pip install supabase python-dotenv
"""

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import eth_account
from supabase import create_client, Client
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class HyperliquidSupabaseMonitor:
    def __init__(self):
        # Hyperliquid setup
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        
        # Supabase setup
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not all([secret_key, self.account_address, supabase_url, supabase_key]):
            raise ValueError("Missing required environment variables")
        
        # Initialize Supabase client
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Initialize Hyperliquid
        account = eth_account.Account.from_key(secret_key)
        base_url = constants.MAINNET_API_URL
        self.info = Info(base_url, skip_ws=False)
        self.exchange = Exchange(account, base_url, account_address=self.account_address)
        
        logging.info(f"Monitor initialized for account: {self.account_address}")
        
        # Create tables if needed (run once)
        self.setup_database()
    
    def setup_database(self):
        """
        SQL to create tables in Supabase (run in Supabase SQL editor)
        
        -- Fills table
        CREATE TABLE IF NOT EXISTS fills (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT NOW(),
            account_address TEXT NOT NULL,
            coin TEXT NOT NULL,
            side TEXT NOT NULL,
            price DECIMAL(20, 8) NOT NULL,
            size DECIMAL(20, 8) NOT NULL,
            order_id TEXT,
            closed_pnl DECIMAL(20, 8),
            is_position_close BOOLEAN DEFAULT FALSE,
            tx_hash TEXT,
            metadata JSONB
        );
        
        -- Positions table
        CREATE TABLE IF NOT EXISTS positions (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT NOW(),
            account_address TEXT NOT NULL,
            coin TEXT NOT NULL,
            size DECIMAL(20, 8) NOT NULL,
            entry_price DECIMAL(20, 8),
            mark_price DECIMAL(20, 8),
            unrealized_pnl DECIMAL(20, 8),
            margin_used DECIMAL(20, 8),
            is_open BOOLEAN DEFAULT TRUE,
            closed_at TIMESTAMP,
            realized_pnl DECIMAL(20, 8),
            metadata JSONB
        );
        
        -- Order events table
        CREATE TABLE IF NOT EXISTS order_events (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT NOW(),
            account_address TEXT NOT NULL,
            event_type TEXT NOT NULL,
            coin TEXT,
            order_id TEXT,
            data JSONB NOT NULL
        );
        
        -- Create indexes
        CREATE INDEX idx_fills_account ON fills(account_address);
        CREATE INDEX idx_fills_coin ON fills(coin);
        CREATE INDEX idx_fills_created ON fills(created_at DESC);
        CREATE INDEX idx_positions_account ON positions(account_address);
        CREATE INDEX idx_positions_open ON positions(is_open);
        
        -- Enable Row Level Security (optional)
        ALTER TABLE fills ENABLE ROW LEVEL SECURITY;
        ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE order_events ENABLE ROW LEVEL SECURITY;
        """
        logging.info("Database tables should be created in Supabase SQL editor")
    
    def on_user_fills(self, event):
        """
        Handle fill events and store in Supabase
        """
        try:
            if 'data' in event and 'fills' in event['data']:
                for fill in event['data']['fills']:
                    fill_data = {
                        'account_address': self.account_address,
                        'coin': fill.get('coin'),
                        'side': fill.get('side'),
                        'price': float(fill.get('px', 0)),
                        'size': float(fill.get('sz', 0)),
                        'order_id': str(fill.get('oid', '')),
                        'closed_pnl': float(fill.get('closedPnl', 0)) if fill.get('closedPnl') else None,
                        'is_position_close': bool(fill.get('closedPnl') and fill['closedPnl'] != '0'),
                        'tx_hash': fill.get('hash', ''),
                        'metadata': {
                            'crossed': fill.get('crossed', False),
                            'fee': fill.get('fee', 0),
                            'timestamp': fill.get('time', datetime.now().isoformat())
                        }
                    }
                    
                    # Insert into Supabase
                    result = self.supabase.table('fills').insert(fill_data).execute()
                    
                    if fill_data['is_position_close']:
                        logging.warning(f"🔔 Position CLOSED: {fill_data['coin']} - PnL: ${fill_data['closed_pnl']:,.2f}")
                        
                        # Update position record
                        self.close_position_record(fill_data)
                        
                        # Trigger edge function (optional)
                        self.trigger_edge_function('position_closed', fill_data)
                    else:
                        logging.info(f"📈 Fill: {fill_data['coin']} {fill_data['side']} {fill_data['size']} @ ${fill_data['price']:,.2f}")
                    
        except Exception as e:
            logging.error(f"Error processing fill: {e}")
            # Store error in order_events table
            self.log_event('error', {'error': str(e), 'event': str(event)})
    
    def on_order_updates(self, event):
        """
        Handle order updates and store in Supabase
        """
        try:
            if 'data' in event:
                order_data = {
                    'account_address': self.account_address,
                    'event_type': 'order_update',
                    'data': event['data']
                }
                
                self.supabase.table('order_events').insert(order_data).execute()
                logging.info(f"Order update logged")
                
        except Exception as e:
            logging.error(f"Error processing order update: {e}")
    
    def close_position_record(self, fill_data):
        """
        Update position record when closed
        """
        try:
            # Find open position for this coin
            result = self.supabase.table('positions').select('*').eq(
                'account_address', self.account_address
            ).eq(
                'coin', fill_data['coin']
            ).eq(
                'is_open', True
            ).execute()
            
            if result.data and len(result.data) > 0:
                position_id = result.data[0]['id']
                
                # Update position as closed
                update_data = {
                    'is_open': False,
                    'closed_at': datetime.now().isoformat(),
                    'realized_pnl': fill_data['closed_pnl']
                }
                
                self.supabase.table('positions').update(update_data).eq(
                    'id', position_id
                ).execute()
                
                logging.info(f"Position record {position_id} marked as closed")
                
        except Exception as e:
            logging.error(f"Error updating position record: {e}")
    
    def sync_current_positions(self):
        """
        Sync current positions from Hyperliquid to Supabase
        """
        try:
            user_state = self.info.user_state(self.account_address)
            
            for pos in user_state.get('assetPositions', []):
                position = pos.get('position', {})
                coin = position.get('coin')
                size = float(position.get('szi', 0))
                
                if size != 0:  # Has open position
                    position_data = {
                        'account_address': self.account_address,
                        'coin': coin,
                        'size': size,
                        'entry_price': float(position.get('entryPx', 0)),
                        'mark_price': float(position.get('markPx', 0)),
                        'unrealized_pnl': float(position.get('unrealizedPnl', 0)),
                        'margin_used': float(position.get('marginUsed', 0)),
                        'is_open': True,
                        'metadata': position
                    }
                    
                    # Check if position exists
                    existing = self.supabase.table('positions').select('id').eq(
                        'account_address', self.account_address
                    ).eq('coin', coin).eq('is_open', True).execute()
                    
                    if not existing.data:
                        # Insert new position
                        self.supabase.table('positions').insert(position_data).execute()
                        logging.info(f"New position tracked: {coin}")
                    else:
                        # Update existing position
                        self.supabase.table('positions').update(position_data).eq(
                            'id', existing.data[0]['id']
                        ).execute()
                        logging.info(f"Position updated: {coin}")
                        
        except Exception as e:
            logging.error(f"Error syncing positions: {e}")
    
    def log_event(self, event_type, data, coin=None):
        """
        Log general events to Supabase
        """
        try:
            event_data = {
                'account_address': self.account_address,
                'event_type': event_type,
                'coin': coin,
                'data': data
            }
            
            self.supabase.table('order_events').insert(event_data).execute()
            
        except Exception as e:
            logging.error(f"Error logging event: {e}")
    
    def trigger_edge_function(self, function_name, data):
        """
        Trigger a Supabase Edge Function
        """
        try:
            # Supabase Edge Functions are triggered via HTTP
            # You would call them like:
            # response = self.supabase.functions.invoke(function_name, data)
            
            logging.info(f"Would trigger edge function: {function_name}")
            # Uncomment when edge function is deployed:
            # response = self.supabase.functions.invoke(function_name, invoke_options={'body': data})
            # logging.info(f"Edge function response: {response}")
            
        except Exception as e:
            logging.error(f"Error triggering edge function: {e}")
    
    def start_monitoring(self):
        """
        Start WebSocket monitoring
        """
        logging.info("Starting WebSocket monitoring...")
        
        # Initial position sync
        self.sync_current_positions()
        
        # Subscribe to events
        self.info.subscribe({
            "type": "userFills",
            "user": self.account_address
        }, self.on_user_fills)
        
        self.info.subscribe({
            "type": "orderUpdates",
            "user": self.account_address
        }, self.on_order_updates)
        
        logging.info("✅ Monitoring started. Events will be stored in Supabase.")
        
        # Keep running
        try:
            import time
            while True:
                time.sleep(60)
                # Periodic position sync
                self.sync_current_positions()
                
        except KeyboardInterrupt:
            logging.info("Monitoring stopped")

def main():
    # Add to .env file:
    # SUPABASE_URL=https://your-project.supabase.co
    # SUPABASE_ANON_KEY=your-anon-key
    
    monitor = HyperliquidSupabaseMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main()