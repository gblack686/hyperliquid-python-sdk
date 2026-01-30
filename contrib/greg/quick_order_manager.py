"""
Quick Order Manager for Hyperliquid
Simplified script for common order operations
"""

import os
import sys
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount
from typing import Optional
from colorama import init, Fore, Style

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

class QuickOrderManager:
    def __init__(self):
        """Initialize order manager"""
        self.secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        self.network = os.getenv('NETWORK', 'MAINNET_API_URL')
        
        if not self.secret_key or not self.account_address:
            print(f"{Fore.RED}Error: Missing configuration in .env file")
            sys.exit(1)
        
        # Initialize connection
        self.account: LocalAccount = eth_account.Account.from_key(self.secret_key)
        self.base_url = getattr(constants, self.network)
        self.info = Info(self.base_url, skip_ws=True)
        self.exchange = Exchange(self.account, self.base_url)
        
        print(f"{Fore.GREEN}Quick Order Manager Ready")
        print(f"Account: {self.account_address}")
    
    def show_orders(self):
        """Display all open orders"""
        try:
            orders = self.info.open_orders(self.account_address)
            
            if not orders:
                print(f"{Fore.YELLOW}No open orders")
                return
            
            print(f"\n{Fore.CYAN}Open Orders:")
            print(f"{'#':<3} {'Coin':<8} {'Side':<5} {'Size':<12} {'Price':<12} {'Filled':<10}")
            print("-" * 60)
            
            for i, order in enumerate(orders, 1):
                coin = order.get("coin", "")
                side = "BUY" if order.get("side") == "B" else "SELL"
                size = float(order.get("sz", 0))
                price = float(order.get("limitPx", 0))
                filled = float(order.get("filled", 0))
                
                side_color = Fore.GREEN if side == "BUY" else Fore.RED
                
                print(f"{i:<3} {coin:<8} {side_color}{side:<5}{Style.RESET_ALL} "
                      f"{size:<12.4f} ${price:<11.2f} {filled:<10.4f}")
            
            return orders
            
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")
            return []
    
    def cancel_all(self, coin: Optional[str] = None):
        """Cancel all orders or all orders for a specific coin"""
        try:
            orders = self.info.open_orders(self.account_address)
            
            if not orders:
                print(f"{Fore.YELLOW}No orders to cancel")
                return
            
            # Filter by coin if specified
            if coin:
                orders = [o for o in orders if o.get("coin") == coin]
                if not orders:
                    print(f"{Fore.YELLOW}No {coin} orders to cancel")
                    return
            
            print(f"{Fore.YELLOW}Cancelling {len(orders)} orders...")
            
            cancelled = 0
            for order in orders:
                try:
                    result = self.exchange.cancel(
                        name=order.get("coin"),
                        oid=order.get("oid")
                    )
                    if result.get("status") == "ok":
                        cancelled += 1
                        print(f"  {Fore.GREEN}[OK] Cancelled {order.get('coin')} order")
                except:
                    print(f"  {Fore.RED}[X] Failed to cancel {order.get('coin')} order")
            
            print(f"{Fore.GREEN}Cancelled {cancelled}/{len(orders)} orders")
            
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")
    
    def quick_limit_buy(self, coin: str, size: float, price_offset_pct: float = -0.5):
        """Place a quick limit buy order below current price"""
        try:
            # Get current price
            mids = self.info.all_mids()
            if coin not in mids:
                print(f"{Fore.RED}Could not find price for {coin}")
                return
            
            current_price = float(mids[coin])
            limit_price = round(current_price * (1 + price_offset_pct/100), 2)
            
            print(f"{Fore.CYAN}Placing BUY order:")
            print(f"  {coin}: {size} @ ${limit_price} (current: ${current_price})")
            
            result = self.exchange.order(
                name=coin,
                is_buy=True,
                sz=size,
                limit_px=limit_price,
                order_type={"limit": {"tif": "Gtc"}}
            )
            
            if result.get("status") == "ok":
                print(f"{Fore.GREEN}[OK] Order placed successfully")
                print(f"  Response: {result}")
            else:
                print(f"{Fore.RED}[X] Order failed: {result}")
                
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")
    
    def quick_limit_sell(self, coin: str, size: float, price_offset_pct: float = 0.5):
        """Place a quick limit sell order above current price"""
        try:
            # Get current price
            mids = self.info.all_mids()
            if coin not in mids:
                print(f"{Fore.RED}Could not find price for {coin}")
                return
            
            current_price = float(mids[coin])
            limit_price = round(current_price * (1 + price_offset_pct/100), 2)
            
            print(f"{Fore.CYAN}Placing SELL order:")
            print(f"  {coin}: {size} @ ${limit_price} (current: ${current_price})")
            
            result = self.exchange.order(
                name=coin,
                is_buy=False,
                sz=size,
                limit_px=limit_price,
                order_type={"limit": {"tif": "Gtc"}}
            )
            
            if result.get("status") == "ok":
                print(f"{Fore.GREEN}[OK] Order placed successfully")
                print(f"  Response: {result}")
            else:
                print(f"{Fore.RED}[X] Order failed: {result}")
                
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")
    
    def close_position(self, coin: str, limit: bool = True, offset_pct: float = 0.1):
        """Close an open position"""
        try:
            # Get user state
            user_state = self.info.user_state(self.account_address)
            positions = user_state.get("assetPositions", [])
            
            # Find position for coin
            position = None
            for pos in positions:
                if pos.get("position", {}).get("coin") == coin:
                    position = pos.get("position", {})
                    break
            
            if not position or float(position.get("szi", 0)) == 0:
                print(f"{Fore.YELLOW}No open position for {coin}")
                return
            
            size = float(position.get("szi", 0))
            is_long = size > 0
            close_size = abs(size)
            
            if limit:
                # Get current price
                mids = self.info.all_mids()
                current_price = float(mids.get(coin, 0))
                
                if is_long:
                    # Selling to close long - place slightly below market
                    limit_price = round(current_price * (1 - offset_pct/100), 2)
                else:
                    # Buying to close short - place slightly above market
                    limit_price = round(current_price * (1 + offset_pct/100), 2)
                
                print(f"{Fore.CYAN}Closing {coin} position:")
                print(f"  Side: {'SELL' if is_long else 'BUY'} {close_size} @ ${limit_price}")
                
                result = self.exchange.order(
                    name=coin,
                    is_buy=not is_long,
                    sz=close_size,
                    limit_px=limit_price,
                    order_type={"limit": {"tif": "Gtc"}},
                    reduce_only=True
                )
            else:
                # Market close
                print(f"{Fore.YELLOW}Market closing {coin} position: {close_size}")
                
                result = self.exchange.market_close(
                    name=coin,
                    sz=close_size
                )
            
            if result.get("status") == "ok":
                print(f"{Fore.GREEN}[OK] Close order placed")
            else:
                print(f"{Fore.RED}[X] Close failed: {result}")
                
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")


def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Quick Order Manager')
    parser.add_argument('action', choices=['show', 'cancel', 'cancel-all', 'buy', 'sell', 'close'],
                       help='Action to perform')
    parser.add_argument('--coin', type=str, help='Coin symbol (e.g., BTC, ETH)')
    parser.add_argument('--size', type=float, help='Order size')
    parser.add_argument('--offset', type=float, default=0.5, 
                       help='Price offset percentage from current price')
    parser.add_argument('--market', action='store_true', 
                       help='Use market order for close')
    
    args = parser.parse_args()
    
    manager = QuickOrderManager()
    
    if args.action == 'show':
        manager.show_orders()
        
    elif args.action == 'cancel':
        if args.coin:
            manager.cancel_all(args.coin)
        else:
            print(f"{Fore.YELLOW}Specify --coin or use 'cancel-all'")
            
    elif args.action == 'cancel-all':
        confirm = input(f"{Fore.RED}Cancel ALL orders? (yes/no): ")
        if confirm.lower() == 'yes':
            manager.cancel_all()
            
    elif args.action == 'buy':
        if not args.coin or not args.size:
            print(f"{Fore.RED}Required: --coin and --size")
        else:
            manager.quick_limit_buy(args.coin.upper(), args.size, -abs(args.offset))
            
    elif args.action == 'sell':
        if not args.coin or not args.size:
            print(f"{Fore.RED}Required: --coin and --size")
        else:
            manager.quick_limit_sell(args.coin.upper(), args.size, abs(args.offset))
            
    elif args.action == 'close':
        if not args.coin:
            print(f"{Fore.RED}Required: --coin")
        else:
            manager.close_position(args.coin.upper(), not args.market, abs(args.offset))


if __name__ == "__main__":
    main()