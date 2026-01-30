#!/usr/bin/env python3
"""
Quick status check for both HYPE Trading Systems
"""

import requests
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import subprocess

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

def check_service(url, name):
    """Check if a service is running"""
    try:
        response = requests.get(url, timeout=2)
        return f"✅ {name}: Running (Status: {response.status_code})"
    except:
        return f"❌ {name}: Not accessible"

def check_docker():
    """Check Docker containers"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        containers = result.stdout.strip().split('\n')
        hl_containers = [c for c in containers if 'hl-' in c]
        return f"🐳 Docker: {len(hl_containers)} HL containers running"
    except:
        return "🐳 Docker: Unable to check"

def check_supabase():
    """Check Supabase connection"""
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url:
            return "📊 Supabase: Not configured"
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Check paper trading account
        result = supabase.table('hl_paper_accounts').select("current_balance, total_pnl").eq(
            'account_name', 'hype_paper_trader'
        ).execute()
        
        if result.data:
            balance = result.data[0]['current_balance']
            pnl = result.data[0]['total_pnl']
            return f"📊 Paper Trading: Balance ${balance:,.2f} | P&L: ${pnl:,.2f}"
        else:
            return "📊 Paper Trading: No data"
    except:
        return "📊 Supabase: Connection error"

def main():
    print("=" * 70)
    print("🚀 HYPE TRADING SYSTEMS STATUS CHECK")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    print("📈 SYSTEM 1: HYPERLIQUID TRADING CONFLUENCE DASHBOARD")
    print("-" * 50)
    print(check_service("http://localhost:8501", "Streamlit Dashboard"))
    print(check_service("http://localhost:8000/health", "Trigger Analyzer"))
    print(check_service("http://localhost:8181", "Paper Trading API"))
    print(check_docker())
    print(check_supabase())
    print()
    
    print("📊 SYSTEM 2: HYPE MEAN REVERSION SYSTEM")
    print("-" * 50)
    
    # Check if Mean Reversion process is running
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "mean_reversion" in result.stdout.lower() or "start.py" in result.stdout:
            print("✅ Mean Reversion: Process running")
        else:
            print("⏸️ Mean Reversion: Not running")
            print("   To start: python run_mean_reversion.py")
    except:
        # Windows version
        try:
            result = subprocess.run(
                ["wmic", "process", "get", "description"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            if "python" in result.stdout:
                # Check for python processes
                print("🔍 Python processes detected (check if Mean Reversion is running)")
            else:
                print("⏸️ Mean Reversion: Not running")
                print("   To start: python run_mean_reversion.py")
        except:
            print("⚠️ Unable to check process status")
    
    # Check Mean Reversion signals in Supabase
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if supabase_url:
            supabase = create_client(supabase_url, supabase_key)
            
            # Get recent signals
            result = supabase.table('hl_signals').select("created_at, action, price").order(
                'created_at', desc=True
            ).limit(1).execute()
            
            if result.data:
                last_signal = result.data[0]
                signal_time = last_signal['created_at']
                print(f"📡 Last Signal: {last_signal['action']} at ${last_signal['price']:.2f}")
            else:
                print("📡 No signals yet")
    except:
        pass
    
    print()
    print("=" * 70)
    print("💡 QUICK COMMANDS:")
    print("-" * 50)
    print("View Dashboard:        http://localhost:8501")
    print("Start Mean Reversion:  python run_mean_reversion.py")
    print("Monitor Both:          python monitor_both_systems.py")
    print("=" * 70)

if __name__ == "__main__":
    main()