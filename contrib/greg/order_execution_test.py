"""
Hyperliquid Order Execution Testing Script
WARNING: This script can place REAL orders on MAINNET
Use with caution and start with small sizes
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from colorama import init, Fore, Back, Style

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Initialize colorama for Windows
init(autoreset=True)

# Load environment variables
load_dotenv()

class OrderExecutionTester:
    def __init__(self, testnet: bool = False):
        """Initialize order execution tester
        
        Args:
            testnet: If True, use testnet. If False, use mainnet (CAREFUL!)
        """
        self.secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        
        if not self.secret_key or not self.account_address:
            print(f"{Fore.RED}Error: Missing configuration in .env file")
            sys.exit(1)
        
        # Network selection
        if testnet:
            self.network = "TESTNET_API_URL"
            print(f"{Fore.YELLOW}[TESTNET MODE] Using testnet for safety")
        else:
            self.network = os.getenv('NETWORK', 'MAINNET_API_URL')
            print(f"{Fore.RED}[MAINNET MODE] REAL MONEY AT RISK!")
        
        # Initialize connection
        self.account: LocalAccount = eth_account.Account.from_key(self.secret_key)
        self.base_url = getattr(constants, self.network)
        self.info = Info(self.base_url, skip_ws=True)
        self.exchange = Exchange(self.account, self.base_url)
        
        # Safety limits
        self.max_order_size = 10  # Maximum size per order
        self.max_orders = 5  # Maximum number of orders at once
        
        print(f"{Fore.GREEN}[INIT] Order Execution Tester Initialized")
        print(f"[INIT] Account: {self.account_address}")
        print(f"[INIT] Network: {self.network.replace('_API_URL', '')}")
        print(f"[INIT] Max Order Size: {self.max_order_size}")
        print(f"[INIT] Max Orders: {self.max_orders}")
    
    def get_current_price(self, coin: str) -> float:
        """Get current mid price for a coin"""
        try:
            all_mids = self.info.all_mids()
            if coin in all_mids:
                return float(all_mids[coin])
            else:
                print(f"{Fore.RED}[ERROR] Could not find price for {coin}")
                return 0.0
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to get price: {e}")
            return 0.0
    
    def get_price_decimals(self, coin: str) -> int:
        """Get number of decimal places for price"""
        try:
            meta = self.info.meta()
            universe = meta.get("universe", [])
            for asset in universe:
                if asset.get("name") == coin:
                    # Hyperliquid uses specific price formats
                    # This is a simplified version
                    return 2
            return 2
        except:
            return 2
    
    def round_price(self, price: float, coin: str) -> float:
        """Round price to appropriate decimals"""
        decimals = self.get_price_decimals(coin)
        return round(price, decimals)
    
    def display_open_orders(self):
        """Display all current open orders"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}CURRENT OPEN ORDERS")
        print(f"{Fore.CYAN}{'='*60}")
        
        try:
            open_orders = self.info.open_orders(self.account_address)
            
            if not open_orders:
                print(f"{Fore.YELLOW}No open orders")
                return []
            
            print(f"{'#':<3} {'Coin':<8} {'Side':<5} {'Size':<12} {'Price':<12} {'Filled':<10} {'Order ID':<20}")
            print("-" * 60)
            
            for i, order in enumerate(open_orders, 1):
                coin = order.get("coin", "Unknown")
                side = "BUY" if order.get("side") == "B" else "SELL"
                sz = float(order.get("sz", 0))
                limit_px = float(order.get("limitPx", 0))
                filled = float(order.get("filled", 0))
                oid = str(order.get("oid", ""))[:20]
                
                side_color = Fore.GREEN if side == "BUY" else Fore.RED
                
                print(f"{i:<3} {coin:<8} {side_color}{side:<5}{Style.RESET_ALL} "
                      f"{sz:<12.4f} ${limit_px:<11.2f} {filled:<10.4f} {oid}")
            
            return open_orders
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to get open orders: {e}")
            return []
    
    def place_limit_order(self, coin: str, is_buy: bool, size: float, price: float, 
                         reduce_only: bool = False, post_only: bool = False):
        """Place a limit order"""
        try:
            # Safety check
            if size > self.max_order_size:
                print(f"{Fore.RED}[SAFETY] Order size {size} exceeds max {self.max_order_size}")
                return None
            
            # Round price
            price = self.round_price(price, coin)
            
            # Prepare order
            side = "Buy" if is_buy else "Sell"
            
            print(f"\n{Fore.YELLOW}[ORDER] Placing {side} Limit Order:")
            print(f"  Coin: {coin}")
            print(f"  Size: {size}")
            print(f"  Price: ${price}")
            print(f"  Reduce Only: {reduce_only}")
            print(f"  Post Only: {post_only}")
            
            # Place order
            order_result = self.exchange.order(
                name=coin,
                is_buy=is_buy,
                sz=size,
                limit_px=price,
                order_type={"limit": {"tif": "Gtc"}},
                reduce_only=reduce_only
            )
            
            if order_result.get("status") == "ok":
                order_data = order_result.get("response", {}).get("data", {})
                statuses = order_data.get("statuses", [])
                
                if statuses and statuses[0].get("filled"):
                    print(f"{Fore.GREEN}[SUCCESS] Order placed successfully!")
                    print(f"  Order ID: {statuses[0].get('oid')}")
                    return statuses[0]
                else:
                    print(f"{Fore.GREEN}[SUCCESS] Order placed!")
                    return order_result
            else:
                print(f"{Fore.RED}[FAILED] Order failed: {order_result}")
                return None
                
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to place order: {e}")
            return None
    
    def place_market_order(self, coin: str, is_buy: bool, size: float):
        """Place a market order"""
        try:
            # Safety check
            if size > self.max_order_size:
                print(f"{Fore.RED}[SAFETY] Order size {size} exceeds max {self.max_order_size}")
                return None
            
            side = "Buy" if is_buy else "Sell"
            
            print(f"\n{Fore.YELLOW}[ORDER] Placing {side} Market Order:")
            print(f"  Coin: {coin}")
            print(f"  Size: {size}")
            
            # Confirm market order
            confirm = input(f"{Fore.RED}[CONFIRM] Execute MARKET order? (yes/no): ")
            if confirm.lower() != 'yes':
                print(f"{Fore.YELLOW}[CANCELLED] Market order cancelled by user")
                return None
            
            # Place market order
            order_result = self.exchange.market_open(
                name=coin,
                is_buy=is_buy,
                sz=size
            )
            
            if order_result.get("status") == "ok":
                print(f"{Fore.GREEN}[SUCCESS] Market order executed!")
                return order_result
            else:
                print(f"{Fore.RED}[FAILED] Market order failed: {order_result}")
                return None
                
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to place market order: {e}")
            return None
    
    def modify_order(self, oid: int, coin: str, is_buy: bool, size: float, price: float):
        """Modify an existing order"""
        try:
            price = self.round_price(price, coin)
            
            print(f"\n{Fore.YELLOW}[MODIFY] Modifying Order {oid}:")
            print(f"  New Size: {size}")
            print(f"  New Price: ${price}")
            
            # Modify order
            modify_result = self.exchange.order(
                name=coin,
                is_buy=is_buy,
                sz=size,
                limit_px=price,
                order_type={"limit": {"tif": "Gtc"}},
                oid=oid  # Passing OID modifies existing order
            )
            
            if modify_result.get("status") == "ok":
                print(f"{Fore.GREEN}[SUCCESS] Order modified successfully!")
                return modify_result
            else:
                print(f"{Fore.RED}[FAILED] Modify failed: {modify_result}")
                return None
                
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to modify order: {e}")
            return None
    
    def cancel_order(self, coin: str, oid: int):
        """Cancel a specific order"""
        try:
            print(f"\n{Fore.YELLOW}[CANCEL] Cancelling Order {oid} for {coin}")
            
            # Cancel order
            cancel_result = self.exchange.cancel(name=coin, oid=oid)
            
            if cancel_result.get("status") == "ok":
                print(f"{Fore.GREEN}[SUCCESS] Order cancelled!")
                return cancel_result
            else:
                print(f"{Fore.RED}[FAILED] Cancel failed: {cancel_result}")
                return None
                
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to cancel order: {e}")
            return None
    
    def cancel_all_orders(self, coin: Optional[str] = None):
        """Cancel all open orders (optionally for specific coin)"""
        try:
            if coin:
                print(f"\n{Fore.YELLOW}[CANCEL ALL] Cancelling all {coin} orders...")
            else:
                print(f"\n{Fore.RED}[CANCEL ALL] Cancelling ALL orders...")
            
            # Get open orders
            open_orders = self.info.open_orders(self.account_address)
            
            if not open_orders:
                print(f"{Fore.YELLOW}No orders to cancel")
                return
            
            # Filter by coin if specified
            if coin:
                orders_to_cancel = [o for o in open_orders if o.get("coin") == coin]
            else:
                orders_to_cancel = open_orders
            
            if not orders_to_cancel:
                print(f"{Fore.YELLOW}No matching orders to cancel")
                return
            
            print(f"Found {len(orders_to_cancel)} orders to cancel")
            
            # Confirm cancellation
            confirm = input(f"{Fore.RED}[CONFIRM] Cancel {len(orders_to_cancel)} orders? (yes/no): ")
            if confirm.lower() != 'yes':
                print(f"{Fore.YELLOW}[CANCELLED] Cancellation aborted by user")
                return
            
            # Cancel orders
            cancelled_count = 0
            failed_count = 0
            
            for order in orders_to_cancel:
                order_coin = order.get("coin")
                order_oid = order.get("oid")
                
                try:
                    cancel_result = self.exchange.cancel(name=order_coin, oid=order_oid)
                    
                    if cancel_result.get("status") == "ok":
                        cancelled_count += 1
                        print(f"  {Fore.GREEN}✓ Cancelled {order_coin} order {order_oid}")
                    else:
                        failed_count += 1
                        print(f"  {Fore.RED}✗ Failed to cancel {order_coin} order {order_oid}")
                except Exception as e:
                    failed_count += 1
                    print(f"  {Fore.RED}✗ Error cancelling {order_coin} order {order_oid}: {e}")
                
                # Small delay to avoid rate limits
                time.sleep(0.1)
            
            print(f"\n{Fore.CYAN}[SUMMARY] Cancelled: {cancelled_count}, Failed: {failed_count}")
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to cancel all orders: {e}")
    
    def place_bracket_order(self, coin: str, is_buy: bool, size: float, 
                           entry_price: float, tp_price: float, sl_price: float):
        """Place a bracket order (entry + take profit + stop loss)"""
        try:
            print(f"\n{Fore.CYAN}[BRACKET] Placing Bracket Order:")
            print(f"  Coin: {coin}")
            print(f"  Side: {'Buy' if is_buy else 'Sell'}")
            print(f"  Size: {size}")
            print(f"  Entry: ${entry_price}")
            print(f"  Take Profit: ${tp_price}")
            print(f"  Stop Loss: ${sl_price}")
            
            # Place entry order
            entry_order = self.place_limit_order(coin, is_buy, size, entry_price)
            
            if entry_order:
                print(f"{Fore.GREEN}[BRACKET] Entry order placed")
                
                # Note: Hyperliquid's TP/SL implementation may vary
                # This is a simplified example
                print(f"{Fore.YELLOW}[INFO] TP/SL orders should be placed after entry fills")
                print(f"[INFO] Use reduce_only=True for TP/SL orders")
                
            return entry_order
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to place bracket order: {e}")
            return None
    
    def place_scaled_orders(self, coin: str, is_buy: bool, total_size: float, 
                           num_orders: int, price_start: float, price_end: float):
        """Place multiple scaled orders across a price range"""
        try:
            if num_orders > self.max_orders:
                print(f"{Fore.RED}[SAFETY] Number of orders {num_orders} exceeds max {self.max_orders}")
                return
            
            size_per_order = total_size / num_orders
            
            if size_per_order > self.max_order_size:
                print(f"{Fore.RED}[SAFETY] Size per order {size_per_order} exceeds max {self.max_order_size}")
                return
            
            print(f"\n{Fore.CYAN}[SCALED] Placing {num_orders} Scaled Orders:")
            print(f"  Coin: {coin}")
            print(f"  Side: {'Buy' if is_buy else 'Sell'}")
            print(f"  Total Size: {total_size}")
            print(f"  Price Range: ${price_start} - ${price_end}")
            
            # Confirm
            confirm = input(f"{Fore.YELLOW}[CONFIRM] Place {num_orders} orders? (yes/no): ")
            if confirm.lower() != 'yes':
                print(f"{Fore.YELLOW}[CANCELLED] Scaled orders cancelled by user")
                return
            
            # Calculate price steps
            price_step = (price_end - price_start) / (num_orders - 1) if num_orders > 1 else 0
            
            placed_orders = []
            for i in range(num_orders):
                price = price_start + (price_step * i)
                price = self.round_price(price, coin)
                
                print(f"\n  Order {i+1}/{num_orders}: {size_per_order} @ ${price}")
                
                order = self.place_limit_order(coin, is_buy, size_per_order, price)
                if order:
                    placed_orders.append(order)
                
                # Small delay to avoid rate limits
                time.sleep(0.5)
            
            print(f"\n{Fore.GREEN}[SCALED] Placed {len(placed_orders)}/{num_orders} orders successfully")
            return placed_orders
            
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to place scaled orders: {e}")
            return None
    
    def test_order_lifecycle(self):
        """Test complete order lifecycle: place, modify, cancel"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}TESTING ORDER LIFECYCLE")
        print(f"{Fore.CYAN}{'='*60}")
        
        # Get test parameters
        coin = input("Enter coin symbol (e.g., BTC, ETH): ").upper()
        
        # Get current price
        current_price = self.get_current_price(coin)
        if current_price == 0:
            print(f"{Fore.RED}Could not get price for {coin}")
            return
        
        print(f"Current {coin} price: ${current_price}")
        
        # Place a test limit order far from market
        test_size = 0.001  # Very small size
        test_price = current_price * 0.8  # 20% below market
        
        print(f"\n1. PLACING TEST ORDER")
        order = self.place_limit_order(coin, True, test_size, test_price)
        
        if order:
            # Wait a bit
            time.sleep(2)
            
            # Display orders
            self.display_open_orders()
            
            # Modify order
            if 'oid' in order:
                oid = order['oid']
                print(f"\n2. MODIFYING ORDER")
                new_price = test_price * 1.01  # Increase price by 1%
                self.modify_order(oid, coin, True, test_size, new_price)
                
                # Wait and display
                time.sleep(2)
                self.display_open_orders()
                
                # Cancel order
                print(f"\n3. CANCELLING ORDER")
                self.cancel_order(coin, oid)
                
                # Final display
                time.sleep(2)
                self.display_open_orders()
    
    def interactive_menu(self):
        """Interactive menu for testing orders"""
        while True:
            print(f"\n{Fore.CYAN}{'='*60}")
            print(f"{Fore.CYAN}ORDER EXECUTION TESTER")
            print(f"{Fore.CYAN}Network: {self.network.replace('_API_URL', '')}")
            print(f"{Fore.CYAN}{'='*60}")
            print(f"1. Display Open Orders")
            print(f"2. Place Limit Order")
            print(f"3. Place Market Order")
            print(f"4. Modify Order")
            print(f"5. Cancel Specific Order")
            print(f"6. Cancel All Orders")
            print(f"7. Cancel All Orders for Coin")
            print(f"8. Place Scaled Orders")
            print(f"9. Test Order Lifecycle")
            print(f"0. Exit")
            print(f"{Fore.CYAN}{'='*60}")
            
            choice = input(f"{Fore.YELLOW}Enter choice: ")
            
            if choice == '1':
                self.display_open_orders()
                
            elif choice == '2':
                coin = input("Coin: ").upper()
                side = input("Side (buy/sell): ").lower()
                size = float(input("Size: "))
                price = float(input("Price: "))
                self.place_limit_order(coin, side == 'buy', size, price)
                
            elif choice == '3':
                coin = input("Coin: ").upper()
                side = input("Side (buy/sell): ").lower()
                size = float(input("Size: "))
                self.place_market_order(coin, side == 'buy', size)
                
            elif choice == '4':
                orders = self.display_open_orders()
                if orders:
                    idx = int(input("Order number to modify: ")) - 1
                    if 0 <= idx < len(orders):
                        order = orders[idx]
                        new_size = float(input("New size: "))
                        new_price = float(input("New price: "))
                        self.modify_order(
                            order['oid'],
                            order['coin'],
                            order['side'] == 'B',
                            new_size,
                            new_price
                        )
                
            elif choice == '5':
                orders = self.display_open_orders()
                if orders:
                    idx = int(input("Order number to cancel: ")) - 1
                    if 0 <= idx < len(orders):
                        order = orders[idx]
                        self.cancel_order(order['coin'], order['oid'])
                
            elif choice == '6':
                self.cancel_all_orders()
                
            elif choice == '7':
                coin = input("Coin to cancel all orders: ").upper()
                self.cancel_all_orders(coin)
                
            elif choice == '8':
                coin = input("Coin: ").upper()
                side = input("Side (buy/sell): ").lower()
                total_size = float(input("Total size: "))
                num_orders = int(input("Number of orders: "))
                price_start = float(input("Start price: "))
                price_end = float(input("End price: "))
                self.place_scaled_orders(
                    coin, side == 'buy', total_size, 
                    num_orders, price_start, price_end
                )
                
            elif choice == '9':
                self.test_order_lifecycle()
                
            elif choice == '0':
                print(f"{Fore.YELLOW}Exiting...")
                break
            else:
                print(f"{Fore.RED}Invalid choice")
            
            input(f"\n{Fore.CYAN}Press Enter to continue...")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hyperliquid Order Execution Tester')
    parser.add_argument(
        '--testnet',
        action='store_true',
        help='Use testnet instead of mainnet'
    )
    parser.add_argument(
        '--menu',
        action='store_true',
        default=True,
        help='Show interactive menu (default)'
    )
    
    args = parser.parse_args()
    
    # Safety warning
    if not args.testnet:
        print(f"\n{Back.RED}{Fore.WHITE}")
        print("="*60)
        print("WARNING: MAINNET MODE - REAL MONEY AT RISK!")
        print("="*60)
        print(f"{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}This script will place REAL orders on MAINNET")
        print(f"Consider using --testnet flag for testing")
        
        confirm = input(f"\n{Fore.RED}Continue with MAINNET? (type 'MAINNET' to confirm): ")
        if confirm != 'MAINNET':
            print(f"{Fore.GREEN}Good choice! Exiting for safety.")
            sys.exit(0)
    
    # Initialize tester
    tester = OrderExecutionTester(testnet=args.testnet)
    
    if args.menu:
        tester.interactive_menu()
    else:
        # Run specific test
        tester.display_open_orders()


if __name__ == "__main__":
    main()