"""
Simple script to buy $50 of HYPE and monitor the fill
"""
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
import eth_account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()

def main():
    # Initialize
    secret_key = os.getenv('HYPERLIQUID_API_KEY')
    account_address = os.getenv('ACCOUNT_ADDRESS')
    
    account = eth_account.Account.from_key(secret_key)
    base_url = constants.MAINNET_API_URL
    
    info = Info(base_url, skip_ws=False)
    exchange = Exchange(account, base_url, account_address=account_address)
    
    print(f"Account: {account_address}")
    
    # Monitor fills
    fills_received = []
    
    def on_fill(event):
        if 'data' in event and 'fills' in event['data']:
            for fill in event['data']['fills']:
                fills_received.append(fill)
                coin = fill.get('coin', '')
                side = fill.get('side', '')
                px = float(fill.get('px', 0))
                sz = float(fill.get('sz', 0))
                print(f"\n[FILL] {coin}: {side} {sz} @ ${px:,.2f}")
                if fill.get('closedPnl'):
                    print(f"  Closed PnL: ${float(fill['closedPnl']):,.2f}")
    
    # Subscribe to fills
    info.subscribe({"type": "userFills", "user": account_address}, on_fill)
    print("WebSocket monitoring started")
    
    # Wait for connection
    time.sleep(2)
    
    # Get HYPE price
    all_mids = info.all_mids()
    hype_price = float(all_mids.get("HYPE", 0))
    
    if hype_price == 0:
        print("Error: Could not get HYPE price")
        return
    
    # Calculate order
    usd_amount = 50
    hype_quantity = round(usd_amount / hype_price, 2)
    limit_price = round(hype_price * 1.001, 2)
    
    print(f"\n{'='*50}")
    print(f"PLACING $50 HYPE ORDER")
    print(f"{'='*50}")
    print(f"Current Price: ${hype_price:,.2f}")
    print(f"Quantity: {hype_quantity} HYPE")
    print(f"Limit Price: ${limit_price:,.2f}")
    print(f"{'='*50}")
    
    # Place order
    try:
        order_result = exchange.order(
            "HYPE",
            True,  # buy
            hype_quantity,
            limit_price,
            {"limit": {"tif": "Ioc"}},
            False
        )
        
        if order_result.get("status") == "ok":
            print("\nORDER PLACED SUCCESSFULLY!")
            
            # Check immediate fill
            statuses = order_result.get("response", {}).get("data", {}).get("statuses", [])
            for status in statuses:
                filled = status.get("filled", {})
                if filled:
                    total_sz = float(filled.get("totalSz", 0))
                    avg_px = float(filled.get("avgPx", 0))
                    if total_sz > 0:
                        print(f"Immediately Filled: {total_sz} HYPE @ ${avg_px:,.2f}")
                        print(f"Total Cost: ${total_sz * avg_px:,.2f}")
        else:
            print(f"Order failed: {order_result}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Wait for WebSocket fills
    print("\nWaiting 5 seconds for WebSocket confirmation...")
    time.sleep(5)
    
    if fills_received:
        print(f"\nReceived {len(fills_received)} fill(s) via WebSocket")
    
    # Check position
    print("\nChecking updated position...")
    user_state = info.user_state(account_address)
    for pos in user_state.get('assetPositions', []):
        position = pos.get('position', {})
        if position.get('coin') == 'HYPE':
            size = float(position.get('szi', 0))
            entry = float(position.get('entryPx', 0))
            value = size * entry
            print(f"HYPE Position: {size} @ ${entry:,.2f} = ${value:,.2f}")
            break
    
    print("\nDone!")

if __name__ == "__main__":
    main()