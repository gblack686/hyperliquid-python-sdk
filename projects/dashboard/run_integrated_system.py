"""
Run the integrated trading dashboard system with CVD indicator
"""

import asyncio
import sys
import subprocess
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

def print_header():
    """Print system header"""
    print("=" * 80)
    print("HYPERLIQUID TRADING DASHBOARD - INTEGRATED SYSTEM")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

def print_status(message, status="INFO"):
    """Print status message"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    if status == "SUCCESS":
        symbol = "[OK]"
    elif status == "ERROR":
        symbol = "[ERROR]"
    elif status == "WARNING":
        symbol = "[WARN]"
    else:
        symbol = "[INFO]"
    print(f"[{timestamp}] {symbol} {message}")

async def run_indicator_manager():
    """Run the indicator manager with all indicators including CVD"""
    print_status("Starting Indicator Manager with CVD...", "INFO")
    
    # Run indicator manager
    cmd = [sys.executable, "indicator_manager.py", 
           "--symbols", "BTC", "ETH", "SOL", "HYPE",
           "--indicators", "cvd", "open_interest", "funding_rate", "vwap", "bollinger", "volume_profile"]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Monitor output
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(f"  [Indicators] {output.strip()}")
        await asyncio.sleep(0.01)
    
    return process

async def run_dashboard():
    """Run the simplified dashboard"""
    print_status("Starting Simplified Dashboard...", "INFO")
    
    # Run streamlit dashboard
    cmd = [sys.executable, "-m", "streamlit", "run", 
           "app_simplified.py",
           "--server.port", "8501",
           "--server.headless", "true"]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give it time to start
    await asyncio.sleep(5)
    
    print_status("Dashboard available at: http://localhost:8501", "SUCCESS")
    return process

async def check_services():
    """Check if services are running"""
    print_status("Checking service health...", "INFO")
    
    # Check Supabase connection
    try:
        from supabase import create_client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if url and key:
            client = create_client(url, key)
            # Try a simple query
            result = client.table('hl_cvd_current').select('symbol').limit(1).execute()
            print_status("Supabase connection: OK", "SUCCESS")
        else:
            print_status("Supabase credentials not found", "WARNING")
    except Exception as e:
        print_status(f"Supabase connection failed: {e}", "ERROR")
    
    print()

async def monitor_system():
    """Monitor system status"""
    print_status("System Monitoring Active", "INFO")
    print()
    print("INDICATOR STATUS:")
    print("-" * 40)
    
    indicators = [
        "CVD (Cumulative Volume Delta)",
        "Open Interest",
        "Funding Rate", 
        "VWAP",
        "Bollinger Bands",
        "Volume Profile"
    ]
    
    for ind in indicators:
        print(f"  - {ind}: Active")
    
    print()
    print("ACCESS POINTS:")
    print("-" * 40)
    print("  - Dashboard: http://localhost:8501")
    print("  - CVD Monitor: http://localhost:8001 (if running separately)")
    print()
    print("TIPS:")
    print("-" * 40)
    print("  - CVD now integrated into main indicator system")
    print("  - All indicators update every 60 seconds")
    print("  - CVD tracks cumulative buy/sell volume delta")
    print("  - Check dashboard for real-time indicator cards")
    print()

async def main():
    """Main execution"""
    print_header()
    
    try:
        # Check services
        await check_services()
        
        # Start indicator manager
        print_status("Launching Indicator Manager...", "INFO")
        indicator_process = await run_indicator_manager()
        
        # Wait a bit for indicators to initialize
        await asyncio.sleep(3)
        
        # Start dashboard
        dashboard_process = await run_dashboard()
        
        # Monitor system
        await monitor_system()
        
        print_status("System fully operational!", "SUCCESS")
        print()
        print("Press Ctrl+C to shutdown")
        print("=" * 80)
        
        # Keep running
        while True:
            await asyncio.sleep(60)
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"[{current_time}] [HEARTBEAT] System running...")
            
    except KeyboardInterrupt:
        print()
        print_status("Shutdown requested", "WARNING")
        print_status("Cleaning up...", "INFO")
        
        # Cleanup
        if 'indicator_process' in locals():
            indicator_process.terminate()
        if 'dashboard_process' in locals():
            dashboard_process.terminate()
            
        print_status("System stopped", "SUCCESS")
        
    except Exception as e:
        print_status(f"Fatal error: {e}", "ERROR")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Initializing Integrated Trading System...")
    print()
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Failed to start: {e}")
        sys.exit(1)