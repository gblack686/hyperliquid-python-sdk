"""
Hyperliquid Account Dashboard
Comprehensive view of all account information including:
- Account balances and values
- Open positions with liquidation levels
- Open orders
- PnL tracking
- Funding rates
- Recent trades
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount
from typing import Dict, List, Optional
from colorama import init, Fore, Back, Style

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Initialize colorama for Windows
init(autoreset=True)

# Load environment variables
load_dotenv()

class HyperliquidDashboard:
    def __init__(self):
        """Initialize dashboard with API credentials"""
        self.secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        self.network = os.getenv('NETWORK', 'MAINNET_API_URL')
        
        if not self.secret_key or not self.account_address:
            print(f"{Fore.RED}Error: Missing configuration in .env file")
            sys.exit(1)
        
        # Create account from private key
        self.account: LocalAccount = eth_account.Account.from_key(self.secret_key)
        self.api_wallet_address = self.account.address
        
        # Select network
        self.base_url = getattr(constants, self.network)
        
        # Initialize Info client
        self.info = Info(self.base_url, skip_ws=True)
        
        # Initialize Exchange client for orders
        self.exchange = Exchange(self.account, self.base_url)
    
    def format_number(self, value: float, decimals: int = 2, is_currency: bool = True) -> str:
        """Format numbers with proper comma separation"""
        if is_currency:
            return f"${value:,.{decimals}f}"
        return f"{value:,.{decimals}f}"
    
    def calculate_liquidation_price(self, position: Dict) -> Optional[float]:
        """Calculate liquidation price for a position"""
        try:
            pos = position.get("position", {})
            szi = float(pos.get("szi", 0))
            entry_px = float(pos.get("entryPx", 0))
            mark_px = float(pos.get("markPx", 0))
            margin_used = float(pos.get("marginUsed", 0))
            
            if szi == 0 or margin_used == 0:
                return None
            
            # Simplified liquidation calculation
            # This assumes maintenance margin is 50% of initial margin
            maintenance_margin_ratio = 0.5
            
            if szi > 0:  # Long position
                # Liquidation when: (mark_price - entry_price) * size = -margin * (1 - maintenance_ratio)
                max_loss = margin_used * (1 - maintenance_margin_ratio)
                liq_price = entry_px - (max_loss / abs(szi))
            else:  # Short position
                # Liquidation when: (entry_price - mark_price) * size = -margin * (1 - maintenance_ratio)
                max_loss = margin_used * (1 - maintenance_margin_ratio)
                liq_price = entry_px + (max_loss / abs(szi))
            
            return max(0, liq_price)  # Price can't be negative
        except Exception as e:
            return None
    
    def get_funding_rate(self, coin: str) -> Dict:
        """Get funding rate for a specific coin"""
        try:
            meta = self.info.meta()
            universe = meta.get("universe", [])
            
            for asset in universe:
                if asset.get("name") == coin:
                    funding = float(asset.get("funding", 0))
                    # Convert to hourly rate (funding is 8-hour rate)
                    hourly_rate = funding / 8
                    daily_rate = funding * 3
                    annual_rate = daily_rate * 365
                    
                    return {
                        "8h": funding * 100,
                        "hourly": hourly_rate * 100,
                        "daily": daily_rate * 100,
                        "annual": annual_rate * 100
                    }
        except Exception:
            pass
        return {"8h": 0, "hourly": 0, "daily": 0, "annual": 0}
    
    def display_header(self):
        """Display dashboard header"""
        print("\n" + "=" * 100)
        print(f"{Fore.CYAN}{Style.BRIGHT}HYPERLIQUID ACCOUNT DASHBOARD")
        print("=" * 100)
        print(f"Network: {Fore.GREEN}{self.network.replace('_API_URL', '')}")
        print(f"Account: {Fore.YELLOW}{self.account_address}")
        print(f"API Wallet: {Fore.YELLOW}{self.api_wallet_address}")
        print(f"Last Update: {Fore.WHITE}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
    
    def display_account_summary(self):
        """Display account summary"""
        user_state = self.info.user_state(self.account_address)
        margin_summary = user_state.get("marginSummary", {})
        
        account_value = float(margin_summary.get("accountValue", 0))
        total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
        total_ntl_pos = float(margin_summary.get("totalNtlPos", 0))
        total_raw_usd = float(margin_summary.get("totalRawUsd", 0))
        withdrawable = float(user_state.get("withdrawable", 0))
        
        # Calculate leverage
        leverage = total_ntl_pos / account_value if account_value > 0 else 0
        
        # Calculate margin ratio
        margin_ratio = (total_margin_used / account_value * 100) if account_value > 0 else 0
        
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[ACCOUNT SUMMARY]")
        print("-" * 50)
        
        # Account values in a grid
        print(f"{Fore.GREEN}Account Value:     {self.format_number(account_value)}")
        print(f"{Fore.CYAN}Withdrawable:      {self.format_number(withdrawable)}")
        print(f"{Fore.YELLOW}Margin Used:       {self.format_number(total_margin_used)} ({margin_ratio:.1f}%)")
        print(f"{Fore.MAGENTA}Notional Position: {self.format_number(total_ntl_pos)}")
        print(f"{Fore.BLUE}Raw USD Balance:   {self.format_number(total_raw_usd)}")
        print(f"{Fore.RED}Current Leverage:  {leverage:.2f}x")
        
        # Risk indicators
        if margin_ratio > 80:
            print(f"\n{Back.RED}{Fore.WHITE}[!] HIGH RISK: Margin usage above 80%!")
        elif margin_ratio > 60:
            print(f"\n{Back.YELLOW}{Fore.BLACK}[!] WARNING: Margin usage above 60%")
        
        return user_state
    
    def display_positions(self, user_state: Dict):
        """Display open positions with liquidation levels"""
        positions = user_state.get("assetPositions", [])
        
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[OPEN POSITIONS]")
        print("-" * 100)
        
        if not positions:
            print(f"{Fore.YELLOW}No open positions")
            return
        
        # Header
        print(f"{'Asset':<10} {'Side':<6} {'Size':<15} {'Entry':<12} {'Mark':<12} {'Liq Price':<12} {'PnL':<15} {'PnL%':<10} {'Funding':<10}")
        print("-" * 100)
        
        total_pnl = 0
        for pos_data in positions:
            position = pos_data.get("position", {})
            coin = position.get("coin", "Unknown")
            szi = float(position.get("szi", 0))
            
            if szi == 0:
                continue
            
            entry_px = float(position.get("entryPx", 0))
            mark_px = float(position.get("markPx", 0))
            unrealized_pnl = float(position.get("unrealizedPnl", 0))
            margin_used = float(position.get("marginUsed", 0))
            
            # Calculate liquidation price
            liq_price = self.calculate_liquidation_price(pos_data)
            
            # Calculate PnL percentage
            pnl_pct = (unrealized_pnl / (abs(szi) * entry_px) * 100) if entry_px > 0 else 0
            
            # Get funding rate
            funding = self.get_funding_rate(coin)
            
            # Determine side and color
            side = "LONG" if szi > 0 else "SHORT"
            side_color = Fore.GREEN if szi > 0 else Fore.RED
            pnl_color = Fore.GREEN if unrealized_pnl >= 0 else Fore.RED
            
            # Calculate distance to liquidation
            if liq_price and mark_px > 0:
                liq_distance = abs((mark_px - liq_price) / mark_px * 100)
                liq_color = Fore.RED if liq_distance < 10 else Fore.YELLOW if liq_distance < 25 else Fore.WHITE
            else:
                liq_distance = 0
                liq_color = Fore.WHITE
            
            print(f"{coin:<10} {side_color}{side:<6}{Style.RESET_ALL} "
                  f"{abs(szi):<15.4f} ${entry_px:<11.2f} ${mark_px:<11.2f} "
                  f"{liq_color}${liq_price:<11.2f}{Style.RESET_ALL} "
                  f"{pnl_color}${unrealized_pnl:<14.2f}{Style.RESET_ALL} "
                  f"{pnl_color}{pnl_pct:<9.2f}%{Style.RESET_ALL} "
                  f"{funding['8h']:.4f}%")
            
            if liq_price and liq_distance < 25:
                print(f"  {liq_color}[!] Distance to liquidation: {liq_distance:.1f}%")
            
            total_pnl += unrealized_pnl
        
        print("-" * 100)
        pnl_color = Fore.GREEN if total_pnl >= 0 else Fore.RED
        print(f"Total Unrealized PnL: {pnl_color}{self.format_number(total_pnl)}")
    
    def display_open_orders(self):
        """Display all open orders"""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[OPEN ORDERS]")
        print("-" * 100)
        
        open_orders = self.info.open_orders(self.account_address)
        
        if not open_orders:
            print(f"{Fore.YELLOW}No open orders")
            return
        
        # Group orders by coin
        orders_by_coin = {}
        for order in open_orders:
            coin = order.get("coin", "Unknown")
            if coin not in orders_by_coin:
                orders_by_coin[coin] = []
            orders_by_coin[coin].append(order)
        
        # Display orders
        print(f"{'Asset':<10} {'Side':<6} {'Type':<8} {'Size':<12} {'Price':<12} {'Filled':<12} {'Status':<10} {'Order ID':<20}")
        print("-" * 100)
        
        for coin, coin_orders in orders_by_coin.items():
            for order in coin_orders:
                side = order.get("side", "")
                order_type = order.get("orderType", "Limit")
                sz = float(order.get("sz", 0))
                limit_px = float(order.get("limitPx", 0))
                filled = float(order.get("filled", 0))
                oid = order.get("oid", "")
                
                # Calculate fill percentage
                fill_pct = (filled / sz * 100) if sz > 0 else 0
                
                # Determine colors
                side_color = Fore.GREEN if side == "B" else Fore.RED
                status = "Partial" if filled > 0 else "Open"
                status_color = Fore.YELLOW if filled > 0 else Fore.WHITE
                
                print(f"{coin:<10} {side_color}{side:<6}{Style.RESET_ALL} "
                      f"{order_type:<8} {sz:<12.4f} ${limit_px:<11.2f} "
                      f"{filled:<12.4f} {status_color}{status:<10}{Style.RESET_ALL} "
                      f"{str(oid)[:20]:<20}")
                
                if fill_pct > 0:
                    print(f"  {Fore.CYAN}Filled: {fill_pct:.1f}%")
    
    def display_recent_fills(self):
        """Display recent filled orders"""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[RECENT FILLS (Last 24h)]")
        print("-" * 100)
        
        try:
            # Get user fills
            fills = self.info.user_fills(self.account_address)
            
            if not fills:
                print(f"{Fore.YELLOW}No recent fills")
                return
            
            # Filter last 24 hours
            current_time = int(time.time() * 1000)
            day_ago = current_time - (24 * 60 * 60 * 1000)
            
            recent_fills = [f for f in fills if int(f.get("time", 0)) > day_ago][:10]  # Last 10 fills
            
            if not recent_fills:
                print(f"{Fore.YELLOW}No fills in the last 24 hours")
                return
            
            print(f"{'Time':<20} {'Asset':<10} {'Side':<6} {'Size':<12} {'Price':<12} {'Fee':<10} {'Type':<10}")
            print("-" * 100)
            
            total_fees = 0
            for fill in recent_fills:
                fill_time = datetime.fromtimestamp(int(fill.get("time", 0)) / 1000).strftime("%Y-%m-%d %H:%M:%S")
                coin = fill.get("coin", "Unknown")
                side = fill.get("side", "")
                sz = float(fill.get("sz", 0))
                px = float(fill.get("px", 0))
                fee = float(fill.get("fee", 0))
                fee_token = fill.get("feeToken", "USDC")
                start_position = fill.get("startPosition", False)
                
                side_color = Fore.GREEN if side == "B" else Fore.RED
                fill_type = "Open" if start_position else "Close"
                
                print(f"{fill_time:<20} {coin:<10} {side_color}{side:<6}{Style.RESET_ALL} "
                      f"{sz:<12.4f} ${px:<11.2f} {fee:<10.6f} {fill_type:<10}")
                
                total_fees += fee
            
            print("-" * 100)
            print(f"Total Fees (24h): {Fore.YELLOW}{self.format_number(total_fees)}")
            
        except Exception as e:
            print(f"{Fore.RED}Error fetching fills: {str(e)}")
    
    def display_spot_balances(self):
        """Display spot wallet balances"""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[SPOT BALANCES]")
        print("-" * 50)
        
        spot_state = self.info.spot_user_state(self.account_address)
        balances = spot_state.get("balances", [])
        
        if not balances:
            print(f"{Fore.YELLOW}No spot balances")
            return
        
        print(f"{'Token':<15} {'Total':<15} {'Available':<15} {'On Hold':<15}")
        print("-" * 50)
        
        for balance in balances:
            token = balance.get("token", "Unknown")
            hold = float(balance.get("hold", 0))
            total = float(balance.get("total", 0))
            
            if total > 0:
                available = total - hold
                hold_color = Fore.YELLOW if hold > 0 else Fore.WHITE
                
                print(f"{token:<15} {total:<15.6f} {available:<15.6f} "
                      f"{hold_color}{hold:<15.6f}{Style.RESET_ALL}")
    
    def display_funding_payments(self):
        """Display funding payment information"""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[FUNDING RATES]")
        print("-" * 80)
        
        positions = self.info.user_state(self.account_address).get("assetPositions", [])
        
        if not positions:
            print(f"{Fore.YELLOW}No positions for funding calculation")
            return
        
        print(f"{'Asset':<10} {'Position':<12} {'8h Rate':<12} {'Daily':<12} {'Annual':<12} {'8h Payment':<15}")
        print("-" * 80)
        
        total_daily_funding = 0
        
        for pos_data in positions:
            position = pos_data.get("position", {})
            coin = position.get("coin", "Unknown")
            szi = float(position.get("szi", 0))
            
            if szi == 0:
                continue
            
            mark_px = float(position.get("markPx", 0))
            notional = abs(szi) * mark_px
            
            funding = self.get_funding_rate(coin)
            
            # Calculate funding payment (negative for longs, positive for shorts in positive funding)
            funding_8h = notional * funding["8h"] / 100
            if szi > 0:  # Long pays funding
                funding_8h = -funding_8h
            
            funding_daily = funding_8h * 3
            total_daily_funding += funding_daily
            
            # Color based on payment direction
            payment_color = Fore.GREEN if funding_8h > 0 else Fore.RED
            
            side = "LONG" if szi > 0 else "SHORT"
            
            print(f"{coin:<10} {side:<12} {funding['8h']:<11.4f}% "
                  f"{funding['daily']:<11.2f}% {funding['annual']:<11.0f}% "
                  f"{payment_color}${funding_8h:<14.2f}{Style.RESET_ALL}")
        
        print("-" * 80)
        payment_color = Fore.GREEN if total_daily_funding > 0 else Fore.RED
        print(f"Expected Daily Funding: {payment_color}{self.format_number(total_daily_funding)}/day")
    
    def display_account_limits(self):
        """Display account trading limits and restrictions"""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[ACCOUNT LIMITS & FEES]")
        print("-" * 50)
        
        # Get rate limits
        try:
            limits = self.info.user_rate_limits(self.account_address)
            
            if limits:
                print(f"Rate Limits:")
                for key, value in limits.items():
                    print(f"  {key}: {value}")
        except Exception:
            pass
        
        # Get fee structure
        user_fees = self.info.user_fees(self.account_address)
        if user_fees:
            maker_rate = float(user_fees.get('makerRate', 0)) * 100
            taker_rate = float(user_fees.get('takerRate', 0)) * 100
            fee_schedule = user_fees.get('feeSchedule', {})
            
            print(f"\nFee Structure:")
            print(f"  Maker Fee: {Fore.GREEN}{maker_rate:.4f}%")
            print(f"  Taker Fee: {Fore.YELLOW}{taker_rate:.4f}%")
            
            if isinstance(fee_schedule, dict):
                print(f"  Perp Cross: {float(fee_schedule.get('cross', 0)) * 100:.4f}%")
                print(f"  Perp Add: {float(fee_schedule.get('add', 0)) * 100:.4f}%")
                print(f"  Spot Cross: {float(fee_schedule.get('spotCross', 0)) * 100:.4f}%")
                print(f"  Spot Add: {float(fee_schedule.get('spotAdd', 0)) * 100:.4f}%")
    
    def run_dashboard(self, refresh_interval: int = 0):
        """Run the dashboard with optional auto-refresh"""
        try:
            while True:
                # Clear screen (works on Windows and Unix)
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # Display all sections
                self.display_header()
                user_state = self.display_account_summary()
                self.display_positions(user_state)
                self.display_open_orders()
                self.display_recent_fills()
                self.display_spot_balances()
                self.display_funding_payments()
                self.display_account_limits()
                
                if refresh_interval <= 0:
                    break
                
                print(f"\n{Fore.CYAN}Refreshing in {refresh_interval} seconds... (Press Ctrl+C to exit)")
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Dashboard stopped by user")
        except Exception as e:
            print(f"\n{Fore.RED}Error: {str(e)}")
            import traceback
            traceback.print_exc()


def main():
    """Main function to run the dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hyperliquid Account Dashboard')
    parser.add_argument(
        '--refresh',
        type=int,
        default=0,
        help='Auto-refresh interval in seconds (0 for no refresh)'
    )
    
    args = parser.parse_args()
    
    dashboard = HyperliquidDashboard()
    dashboard.run_dashboard(refresh_interval=args.refresh)


if __name__ == "__main__":
    main()