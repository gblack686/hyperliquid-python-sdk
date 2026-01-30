#!/usr/bin/env python3
"""
Test WebSocket connection to Hyperliquid
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add parent directory to path
sys.path.append('..')
from hyperliquid.info import Info
from hyperliquid.utils import constants
import eth_account

def test_websocket():
    """Test WebSocket connection"""
    
    print("\n[WEBSOCKET CONNECTION TEST]")
    print("="*60)
    
    # Get credentials
    account_address = os.getenv('ACCOUNT_ADDRESS')
    private_key = os.getenv('HYPERLIQUID_API_KEY')
    
    if not account_address or not private_key:
        print("[X] Missing credentials in .env")
        return
    
    print(f"Account: {account_address}")
    
    # Initialize connection with WebSocket
    print("\nInitializing connection...")
    info = Info(constants.MAINNET_API_URL, skip_ws=False)
    
    # Track messages
    message_count = 0
    last_price = 0
    
    def handle_trades(data):
        """Handle trade updates"""
        nonlocal message_count, last_price
        message_count += 1
        
        try:
            if isinstance(data, dict):
                if "data" in data:
                    trades = data["data"]
                    if isinstance(trades, list) and len(trades) > 0:
                        trade = trades[0]
                        if "px" in trade:
                            price = float(trade["px"])
                            size = float(trade.get("sz", 0))
                            last_price = price
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Trade: ${price:.4f} x {size:.4f} HYPE (msg #{message_count})")
        except Exception as e:
            print(f"Error processing trade: {e}")
    
    def handle_l2book(data):
        """Handle orderbook updates"""
        nonlocal message_count
        message_count += 1
        
        try:
            if isinstance(data, dict) and "levels" in data:
                levels = data["levels"]
                if len(levels) > 0 and len(levels[0]) >= 2:
                    bid = float(levels[0][0]["px"])
                    ask = float(levels[0][1]["px"])
                    spread = ask - bid
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Book: Bid ${bid:.4f} | Ask ${ask:.4f} | Spread ${spread:.4f} (msg #{message_count})")
        except Exception as e:
            print(f"Error processing book: {e}")
    
    # Subscribe to HYPE trades
    print("\nSubscribing to HYPE market data...")
    
    try:
        # Subscribe to trades
        trade_id = info.subscribe(
            {"type": "trades", "coin": "HYPE"},
            handle_trades
        )
        print(f"[OK] Subscribed to trades (ID: {trade_id})")
        
        # Subscribe to orderbook
        book_id = info.subscribe(
            {"type": "l2Book", "coin": "HYPE"},
            handle_l2book
        )
        print(f"[OK] Subscribed to orderbook (ID: {book_id})")
        
        # Let it run for 30 seconds
        print(f"\nListening for 30 seconds...\n")
        print("-"*60)
        
        start_time = time.time()
        while time.time() - start_time < 30:
            time.sleep(1)
            
            # Show status every 10 seconds
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                print(f"\n[Status] {elapsed}s elapsed, {message_count} messages received")
                if last_price > 0:
                    print(f"         Last HYPE price: ${last_price:.4f}\n")
        
        print("-"*60)
        print(f"\n[RESULTS]")
        print(f"Total messages received: {message_count}")
        print(f"Last HYPE price: ${last_price:.4f}" if last_price > 0 else "No trades received")
        
        if message_count > 0:
            print(f"Average rate: {message_count/30:.1f} messages/second")
            print("\n[OK] WebSocket connection is working!")
        else:
            print("\n[X] No messages received - check connection")
        
        # Unsubscribe
        info.unsubscribe({"type": "trades", "coin": "HYPE"}, trade_id)
        info.unsubscribe({"type": "l2Book", "coin": "HYPE"}, book_id)
        
    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("="*60)

if __name__ == "__main__":
    test_websocket()