"""
Hyperliquid Account Dashboard V2
Improved version with correct margin calculations and better data display
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
        
        # Cache for prices
        self.all_mids = {}
    
    def format_number(self, value: float, decimals: int = 2, is_currency: bool = True) -> str:
        """Format numbers with proper comma separation"""
        if is_currency:
            return f"${value:,.{decimals}f}"
        return f"{value:,.{decimals}f}"
    
    def get_current_prices(self):
        """Get current mid prices for all assets"""
        try:
            self.all_mids = self.info.all_mids()
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not fetch current prices: {e}")
    
    def get_mark_price(self, coin: str) -> float:
        """Get current mark price for an asset"""
        if coin in self.all_mids:
            return float(self.all_mids[coin])
        return 0.0
    
    def calculate_liquidation_details(self, position: Dict) -> Dict:
        """Calculate detailed liquidation information"""
        pos = position.get("position", {})
        coin = pos.get("coin", "Unknown")
        szi = float(pos.get("szi", 0))
        entry_px = float(pos.get("entryPx", 0))
        liq_px = float(pos.get("liquidationPx", 0))
        position_value = float(pos.get("positionValue", 0))
        margin_used = float(pos.get("marginUsed", 0))
        leverage_info = pos.get("leverage", {})
        
        # Get current mark price
        mark_px = self.get_mark_price(coin)
        if mark_px == 0:
            mark_px = position_value / abs(szi) if szi != 0 else 0
        
        # Calculate distance to liquidation
        if liq_px > 0 and mark_px > 0:
            if szi > 0:  # Long position
                liq_distance_pct = ((mark_px - liq_px) / mark_px) * 100
            else:  # Short position
                liq_distance_pct = ((liq_px - mark_px) / mark_px) * 100
        else:
            liq_distance_pct = 0
        
        return {
            "coin": coin,
            "side": "LONG" if szi > 0 else "SHORT",
            "size": abs(szi),
            "entry_price": entry_px,
            "mark_price": mark_px,
            "liquidation_price": liq_px,
            "position_value": position_value,
            "margin_used": margin_used,
            "leverage_type": leverage_info.get("type", "cross"),
            "leverage_setting": leverage_info.get("value", 1),
            "liquidation_distance_pct": liq_distance_pct
        }
    
    def display_header(self):
        """Display dashboard header"""
        print("\n" + "=" * 100)
        print(f"{Fore.CYAN}{Style.BRIGHT}HYPERLIQUID ACCOUNT DASHBOARD V2")
        print("=" * 100)
        print(f"Network: {Fore.GREEN}{self.network.replace('_API_URL', '')}")
        print(f"Account: {Fore.YELLOW}{self.account_address}")
        print(f"API Wallet: {Fore.YELLOW}{self.api_wallet_address}")
        print(f"Last Update: {Fore.WHITE}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
    
    def display_account_summary(self):
        """Display account summary with correct calculations"""
        user_state = self.info.user_state(self.account_address)
        
        # Get margin summaries
        margin_summary = user_state.get("marginSummary", {})
        cross_margin = user_state.get("crossMarginSummary", {})
        
        # Parse values
        account_value = float(margin_summary.get("accountValue", 0))
        total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
        total_ntl_pos = float(margin_summary.get("totalNtlPos", 0))
        total_raw_usd = float(margin_summary.get("totalRawUsd", 0))
        withdrawable = float(user_state.get("withdrawable", 0))
        maintenance_margin = float(user_state.get("crossMaintenanceMarginUsed", 0))
        
        # Calculate metrics
        actual_leverage = total_ntl_pos / account_value if account_value > 0 else 0
        margin_usage_pct = (total_margin_used / account_value * 100) if account_value > 0 else 0
        free_margin = account_value - total_margin_used
        margin_level = (account_value / total_margin_used * 100) if total_margin_used > 0 else 0
        
        # Calculate distance to liquidation based on maintenance margin
        if maintenance_margin > 0:
            liquidation_buffer = account_value - maintenance_margin
            liquidation_pct = (liquidation_buffer / account_value * 100) if account_value > 0 else 0
        else:
            liquidation_pct = 100
        
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[ACCOUNT SUMMARY]")
        print("-" * 80)
        
        # Main metrics
        print(f"{Fore.GREEN}Account Value:        {self.format_number(account_value)}")
        print(f"{Fore.CYAN}Free Margin:          {self.format_number(free_margin)}")
        print(f"{Fore.CYAN}Withdrawable:         {self.format_number(withdrawable)}")
        print(f"{Fore.YELLOW}Margin Used:          {self.format_number(total_margin_used)} ({margin_usage_pct:.1f}% of account)")
        print(f"{Fore.YELLOW}Maintenance Margin:   {self.format_number(maintenance_margin)}")
        print(f"{Fore.MAGENTA}Notional Position:    {self.format_number(total_ntl_pos)}")
        print(f"{Fore.BLUE}Raw USD Balance:      {self.format_number(total_raw_usd)}")
        
        # Leverage and risk metrics
        print(f"\n{Fore.WHITE}Risk Metrics:")
        print(f"{Fore.RED}Actual Leverage:      {actual_leverage:.2f}x")
        print(f"{Fore.YELLOW}Margin Level:         {margin_level:.1f}%")
        print(f"{Fore.CYAN}Buffer to Liquidation: {liquidation_pct:.1f}%")
        
        # Risk warnings
        if margin_usage_pct > 80:
            print(f"\n{Back.RED}{Fore.WHITE}[!!!] CRITICAL RISK: Margin usage above 80% - Consider reducing position!")
        elif margin_usage_pct > 60:
            print(f"\n{Back.YELLOW}{Fore.BLACK}[!!] HIGH RISK: Margin usage above 60% - Monitor closely!")
        elif margin_usage_pct > 40:
            print(f"\n{Fore.YELLOW}[!] MODERATE RISK: Margin usage above 40%")
        
        if liquidation_pct < 20:
            print(f"{Back.RED}{Fore.WHITE}[!!!] LIQUIDATION RISK: Buffer below 20%!")
        
        return user_state
    
    def display_positions(self, user_state: Dict):
        """Display open positions with improved information"""
        positions = user_state.get("assetPositions", [])
        
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[OPEN POSITIONS]")
        print("-" * 120)
        
        if not positions:
            print(f"{Fore.YELLOW}No open positions")
            return
        
        # Get current prices
        self.get_current_prices()
        
        # Header
        print(f"{'Asset':<8} {'Side':<6} {'Size':<12} {'Entry':<10} {'Mark':<10} {'Liq Price':<10} "
              f"{'Notional':<14} {'PnL':<12} {'PnL%':<8} {'Leverage':<10} {'Liq Dist':<10}")
        print("-" * 120)
        
        total_pnl = 0
        for pos_data in positions:
            position = pos_data.get("position", {})
            szi = float(position.get("szi", 0))
            
            if szi == 0:
                continue
            
            # Get position details
            details = self.calculate_liquidation_details(pos_data)
            
            # Get additional data
            unrealized_pnl = float(position.get("unrealizedPnl", 0))
            return_on_equity = float(position.get("returnOnEquity", 0)) * 100
            
            # Determine colors
            side_color = Fore.GREEN if szi > 0 else Fore.RED
            pnl_color = Fore.GREEN if unrealized_pnl >= 0 else Fore.RED
            
            # Liquidation distance color
            liq_dist = details["liquidation_distance_pct"]
            if liq_dist < 5:
                liq_color = Back.RED + Fore.WHITE
            elif liq_dist < 10:
                liq_color = Fore.RED
            elif liq_dist < 20:
                liq_color = Fore.YELLOW
            else:
                liq_color = Fore.WHITE
            
            # Format leverage display
            leverage_display = f"{details['leverage_type'][:1].upper()}{details['leverage_setting']}x"
            
            print(f"{details['coin']:<8} {side_color}{details['side']:<6}{Style.RESET_ALL} "
                  f"{details['size']:<12.4f} ${details['entry_price']:<9.2f} "
                  f"${details['mark_price']:<9.2f} ${details['liquidation_price']:<9.2f} "
                  f"{self.format_number(details['position_value']):<14} "
                  f"{pnl_color}{self.format_number(unrealized_pnl, 2, True):<12}{Style.RESET_ALL} "
                  f"{pnl_color}{return_on_equity:<7.2f}%{Style.RESET_ALL} "
                  f"{leverage_display:<10} "
                  f"{liq_color}{liq_dist:<9.1f}%{Style.RESET_ALL}")
            
            # Add funding information
            cum_funding = position.get("cumFunding", {})
            if cum_funding:
                since_open = float(cum_funding.get("sinceOpen", 0))
                all_time = float(cum_funding.get("allTime", 0))
                if since_open != 0:
                    funding_color = Fore.GREEN if since_open > 0 else Fore.RED
                    print(f"  Funding - Since Open: {funding_color}${since_open:.2f}{Style.RESET_ALL}, "
                          f"All Time: ${all_time:.2f}")
            
            total_pnl += unrealized_pnl
        
        print("-" * 120)
        pnl_color = Fore.GREEN if total_pnl >= 0 else Fore.RED
        print(f"Total Unrealized PnL: {pnl_color}{self.format_number(total_pnl)}")
    
    def display_open_orders(self):
        """Display all open orders"""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[OPEN ORDERS]")
        print("-" * 100)
        
        try:
            open_orders = self.info.open_orders(self.account_address)
            
            if not open_orders:
                print(f"{Fore.YELLOW}No open orders")
                return
            
            # Get current prices for reference
            self.get_current_prices()
            
            print(f"{'Asset':<8} {'Side':<6} {'Type':<8} {'Size':<12} {'Price':<12} "
                  f"{'Distance':<12} {'Filled':<10} {'Status':<10} {'Order ID':<15}")
            print("-" * 100)
            
            for order in open_orders:
                coin = order.get("coin", "Unknown")
                side = order.get("side", "")
                order_type = order.get("orderType", "Limit")
                sz = float(order.get("sz", 0))
                limit_px = float(order.get("limitPx", 0))
                filled = float(order.get("filled", 0))
                oid = str(order.get("oid", ""))[:15]
                
                # Calculate distance from current price
                current_px = self.get_mark_price(coin)
                if current_px > 0 and limit_px > 0:
                    distance_pct = ((limit_px - current_px) / current_px) * 100
                    distance_str = f"{distance_pct:+.2f}%"
                else:
                    distance_str = "N/A"
                
                # Determine status
                if filled > 0:
                    fill_pct = (filled / sz * 100) if sz > 0 else 0
                    status = f"Partial({fill_pct:.0f}%)"
                    status_color = Fore.YELLOW
                else:
                    status = "Open"
                    status_color = Fore.WHITE
                
                side_color = Fore.GREEN if side == "B" else Fore.RED
                
                print(f"{coin:<8} {side_color}{side:<6}{Style.RESET_ALL} "
                      f"{order_type:<8} {sz:<12.4f} ${limit_px:<11.2f} "
                      f"{distance_str:<12} {filled:<10.4f} "
                      f"{status_color}{status:<10}{Style.RESET_ALL} {oid}")
                
        except Exception as e:
            print(f"{Fore.RED}Error fetching orders: {str(e)}")
    
    def display_recent_fills(self):
        """Display recent filled orders with improved formatting"""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[RECENT FILLS (Last 24h)]")
        print("-" * 100)
        
        try:
            fills = self.info.user_fills(self.account_address)
            
            if not fills:
                print(f"{Fore.YELLOW}No recent fills")
                return
            
            # Filter last 24 hours
            current_time = int(time.time() * 1000)
            day_ago = current_time - (24 * 60 * 60 * 1000)
            
            recent_fills = [f for f in fills if int(f.get("time", 0)) > day_ago][:20]
            
            if not recent_fills:
                print(f"{Fore.YELLOW}No fills in the last 24 hours")
                return
            
            print(f"{'Time':<20} {'Asset':<8} {'Side':<6} {'Size':<12} {'Price':<12} "
                  f"{'Value':<14} {'Fee':<10} {'Type':<8}")
            print("-" * 100)
            
            total_volume = 0
            total_fees = 0
            
            for fill in recent_fills:
                fill_time = datetime.fromtimestamp(int(fill.get("time", 0)) / 1000)
                time_str = fill_time.strftime("%Y-%m-%d %H:%M:%S")
                coin = fill.get("coin", "Unknown")
                side = fill.get("side", "")
                sz = float(fill.get("sz", 0))
                px = float(fill.get("px", 0))
                fee = float(fill.get("fee", 0))
                start_position = fill.get("startPosition", False)
                
                value = sz * px
                total_volume += value
                total_fees += fee
                
                side_color = Fore.GREEN if side == "B" else Fore.RED
                fill_type = "Open" if start_position else "Close"
                
                print(f"{time_str:<20} {coin:<8} {side_color}{side:<6}{Style.RESET_ALL} "
                      f"{sz:<12.4f} ${px:<11.2f} {self.format_number(value):<14} "
                      f"{fee:<10.6f} {fill_type:<8}")
            
            print("-" * 100)
            print(f"24h Volume: {Fore.CYAN}{self.format_number(total_volume)}")
            print(f"24h Fees Paid: {Fore.YELLOW}{self.format_number(total_fees)}")
            
            if total_volume > 0:
                fee_rate = (total_fees / total_volume) * 100
                print(f"Effective Fee Rate: {Fore.GREEN}{fee_rate:.4f}%")
            
        except Exception as e:
            print(f"{Fore.RED}Error fetching fills: {str(e)}")
    
    def display_account_health(self):
        """Display account health metrics and recommendations"""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}[ACCOUNT HEALTH & RECOMMENDATIONS]")
        print("-" * 80)
        
        user_state = self.info.user_state(self.account_address)
        margin_summary = user_state.get("marginSummary", {})
        
        account_value = float(margin_summary.get("accountValue", 0))
        total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
        total_ntl_pos = float(margin_summary.get("totalNtlPos", 0))
        maintenance_margin = float(user_state.get("crossMaintenanceMarginUsed", 0))
        
        # Calculate health metrics
        margin_usage = (total_margin_used / account_value * 100) if account_value > 0 else 0
        actual_leverage = total_ntl_pos / account_value if account_value > 0 else 0
        
        # Health score (0-100)
        health_score = 100
        recommendations = []
        
        # Deduct points for high margin usage
        if margin_usage > 80:
            health_score -= 40
            recommendations.append(f"{Fore.RED}[CRITICAL] Reduce position size immediately - margin usage at {margin_usage:.1f}%")
        elif margin_usage > 60:
            health_score -= 25
            recommendations.append(f"{Fore.YELLOW}[WARNING] Consider reducing position - margin usage at {margin_usage:.1f}%")
        elif margin_usage > 40:
            health_score -= 10
            recommendations.append(f"{Fore.CYAN}[INFO] Monitor margin usage - currently at {margin_usage:.1f}%")
        
        # Deduct points for high leverage
        if actual_leverage > 10:
            health_score -= 30
            recommendations.append(f"{Fore.RED}[CRITICAL] Extremely high leverage at {actual_leverage:.1f}x")
        elif actual_leverage > 5:
            health_score -= 15
            recommendations.append(f"{Fore.YELLOW}[WARNING] High leverage at {actual_leverage:.1f}x")
        elif actual_leverage > 3:
            health_score -= 5
            recommendations.append(f"{Fore.CYAN}[INFO] Moderate leverage at {actual_leverage:.1f}x")
        
        # Display health score with color
        if health_score >= 80:
            score_color = Fore.GREEN
            status = "EXCELLENT"
        elif health_score >= 60:
            score_color = Fore.YELLOW
            status = "GOOD"
        elif health_score >= 40:
            score_color = Fore.YELLOW
            status = "FAIR"
        else:
            score_color = Fore.RED
            status = "POOR"
        
        print(f"Account Health Score: {score_color}{health_score}/100 - {status}{Style.RESET_ALL}")
        
        if recommendations:
            print(f"\nRecommendations:")
            for rec in recommendations:
                print(f"  - {rec}")
        else:
            print(f"\n{Fore.GREEN}No issues detected - account is healthy!")
    
    def run_dashboard(self, refresh_interval: int = 0):
        """Run the dashboard with optional auto-refresh"""
        try:
            while True:
                # Clear screen
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # Display all sections
                self.display_header()
                user_state = self.display_account_summary()
                self.display_positions(user_state)
                self.display_open_orders()
                self.display_recent_fills()
                self.display_account_health()
                
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
    
    parser = argparse.ArgumentParser(description='Hyperliquid Account Dashboard V2')
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