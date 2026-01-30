"""
Check current prices for assets
"""

import os
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

def main():
    # Initialize Info client
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    
    # Get all mid prices
    all_mids = info.all_mids()
    
    # Check HYPE price
    if "HYPE" in all_mids:
        print(f"HYPE current price: ${all_mids['HYPE']}")
    
    # Get L2 book for HYPE
    book = info.l2_book("HYPE")
    if book and "levels" in book:
        bids = book["levels"][0]
        asks = book["levels"][1]
        if bids and asks:
            best_bid = bids[0]["px"]
            best_ask = asks[0]["px"]
            mid = (float(best_bid) + float(best_ask)) / 2
            print(f"HYPE Best Bid: ${best_bid}")
            print(f"HYPE Best Ask: ${best_ask}")
            print(f"HYPE Mid Price: ${mid:.4f}")

if __name__ == "__main__":
    main()