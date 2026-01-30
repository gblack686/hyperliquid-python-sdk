"""
Quick status check for all indicators
Shows current values from all running systems
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from tabulate import tabulate
from colorama import init, Fore, Style

# Initialize colorama
init()

sys.path.append('..')
load_dotenv()

def check_status():
    """Check status of all indicators"""
    
    # Supabase setup
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    supabase = create_client(supabase_url, supabase_key)
    
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}HYPERLIQUID TRADING SYSTEM STATUS{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    
    # 1. CVD Data (from Docker)
    print(f"\n{Fore.YELLOW}1. CVD (Cumulative Volume Delta) - Real-time from WebSocket{Style.RESET_ALL}")
    try:
        response = requests.get('http://localhost:8001/api/cvd/current', timeout=2)
        if response.status_code == 200:
            cvd_data = response.json()
            cvd_table = []
            for item in cvd_data:
                cvd_table.append([
                    item['symbol'],
                    f"{item['cvd']:+.2f}",
                    f"{item['buy_ratio']:.1f}%",
                    item['trend'],
                    f"{item['trade_count']:,}"
                ])
            print(tabulate(cvd_table, 
                         headers=['Symbol', 'CVD', 'Buy%', 'Trend', 'Trades'],
                         tablefmt='grid'))
        else:
            print(f"{Fore.RED}CVD API not responding (Docker container may not be running){Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}CVD API error: {e}{Style.RESET_ALL}")
    
    # 2. Open Interest Data
    print(f"\n{Fore.YELLOW}2. Open Interest - USD Millions (30s updates){Style.RESET_ALL}")
    try:
        result = supabase.table('hl_oi_current').select("*").order("symbol").execute()
        if result.data:
            oi_table = []
            for item in result.data:
                oi_table.append([
                    item['symbol'],
                    f"${item['oi_current']:.2f}M",
                    f"{item['oi_change_pct_1h']:+.1f}%",
                    f"{item['oi_delta_5m']:+.2f}M",
                    item['trend']
                ])
            print(tabulate(oi_table,
                         headers=['Symbol', 'OI (USD)', '1h Change%', '5m Delta', 'Trend'],
                         tablefmt='grid'))
    except Exception as e:
        print(f"{Fore.RED}OI data error: {e}{Style.RESET_ALL}")
    
    # 3. Funding Rate Data
    print(f"\n{Fore.YELLOW}3. Funding Rates - Basis Points (5min updates){Style.RESET_ALL}")
    try:
        result = supabase.table('hl_funding_current').select("*").order("symbol").execute()
        if result.data:
            funding_table = []
            for item in result.data:
                funding_table.append([
                    item['symbol'],
                    f"{item['funding_current']:.4f}",
                    f"{item['funding_predicted']:.2f}",
                    f"{item['funding_24h_cumulative']:.2f}",
                    item['sentiment']
                ])
            print(tabulate(funding_table,
                         headers=['Symbol', 'Current', 'Predicted', '24h Cumul', 'Sentiment'],
                         tablefmt='grid'))
    except Exception as e:
        print(f"{Fore.RED}Funding data error: {e}{Style.RESET_ALL}")
    
    # 4. System Health
    print(f"\n{Fore.YELLOW}4. System Health{Style.RESET_ALL}")
    health_table = []
    
    # Check CVD Monitor
    try:
        response = requests.get('http://localhost:8001/health', timeout=2)
        if response.status_code == 200:
            health_table.append(["CVD Monitor (Docker)", f"{Fore.GREEN}RUNNING{Style.RESET_ALL}", "http://localhost:8001"])
        else:
            health_table.append(["CVD Monitor (Docker)", f"{Fore.RED}ERROR{Style.RESET_ALL}", "-"])
    except:
        health_table.append(["CVD Monitor (Docker)", f"{Fore.RED}OFFLINE{Style.RESET_ALL}", "-"])
    
    # Check Supabase
    try:
        supabase.table('hl_oi_current').select("symbol").limit(1).execute()
        health_table.append(["Supabase Database", f"{Fore.GREEN}CONNECTED{Style.RESET_ALL}", "lfxlrxwxnvtrzwsohojz"])
    except:
        health_table.append(["Supabase Database", f"{Fore.RED}ERROR{Style.RESET_ALL}", "-"])
    
    # Check data freshness
    try:
        result = supabase.table('hl_oi_current').select("updated_at").order("updated_at", desc=True).limit(1).execute()
        if result.data:
            last_update = datetime.fromisoformat(result.data[0]['updated_at'].replace('+00:00', ''))
            age_seconds = (datetime.utcnow() - last_update).total_seconds()
            if age_seconds < 60:
                health_table.append(["Indicator Manager", f"{Fore.GREEN}RUNNING{Style.RESET_ALL}", f"Updated {age_seconds:.0f}s ago"])
            else:
                health_table.append(["Indicator Manager", f"{Fore.YELLOW}STALE{Style.RESET_ALL}", f"Updated {age_seconds:.0f}s ago"])
    except:
        health_table.append(["Indicator Manager", f"{Fore.RED}NO DATA{Style.RESET_ALL}", "-"])
    
    print(tabulate(health_table,
                 headers=['Component', 'Status', 'Details'],
                 tablefmt='grid'))
    
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Dashboard: http://localhost:8001{Style.RESET_ALL}")
    print(f"{Fore.CYAN}API Docs: http://localhost:8001/docs{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    check_status()