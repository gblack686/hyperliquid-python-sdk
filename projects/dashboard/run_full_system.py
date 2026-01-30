"""
Run the full CVD system with monitoring
"""
import subprocess
import time
import webbrowser
import asyncio
from datetime import datetime

def check_supabase_data():
    """Check if data is flowing to Supabase"""
    from supabase import create_client
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_KEY')
    )
    
    # Get current CVD
    result = supabase.table('hl_cvd_current').select("*").execute()
    
    print("\n" + "="*60)
    print("CURRENT CVD DATA IN SUPABASE")
    print("="*60)
    
    for item in result.data:
        print(f"\n{item['symbol']}:")
        print(f"  CVD: {float(item['cvd']):+.2f}")
        print(f"  Buy Ratio: {float(item['buy_ratio']):.1f}%")
        print(f"  Price: ${float(item['last_price']):,.2f}")
        print(f"  Trend: {item['trend']}")
        print(f"  Updated: {item['updated_at']}")
    
    # Get snapshot count
    snapshots = supabase.table('hl_cvd_snapshots').select("symbol", count='exact').execute()
    print(f"\nTotal Snapshots: {snapshots.count if hasattr(snapshots, 'count') else 'Unknown'}")
    
    return True

def main():
    print("="*60)
    print("STARTING FULL CVD SYSTEM")
    print("="*60)
    
    # Check initial data
    print("\nChecking existing Supabase data...")
    check_supabase_data()
    
    print("\n" + "="*60)
    print("LAUNCHING COMPONENTS")
    print("="*60)
    
    # Start CVD Calculator
    print("\n[1] Starting CVD Calculator...")
    calc_process = subprocess.Popen(
        ["python", "cvd_supabase_integration.py"],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    print("    CVD Calculator PID:", calc_process.pid)
    
    # Wait a moment
    time.sleep(3)
    
    # Start Monitor Server
    print("\n[2] Starting Monitor Server...")
    server_process = subprocess.Popen(
        ["python", "cvd_monitor_server.py"],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    print("    Monitor Server PID:", server_process.pid)
    
    # Wait for server to start
    time.sleep(3)
    
    print("\n" + "="*60)
    print("SYSTEM RUNNING!")
    print("="*60)
    print("\nDashboard: http://localhost:8001")
    print("API Docs:  http://localhost:8001/docs")
    print("\nOpening dashboard in browser...")
    
    # Open browser
    webbrowser.open("http://localhost:8001")
    
    print("\n" + "="*60)
    print("MONITORING ACTIVE")
    print("="*60)
    print("\nPress Ctrl+C to stop all components")
    print("\nLive Updates:")
    
    try:
        # Monitor loop
        while True:
            time.sleep(10)
            
            # Check if processes are still running
            calc_running = calc_process.poll() is None
            server_running = server_process.poll() is None
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Status Check:")
            print(f"  Calculator: {'Running' if calc_running else 'STOPPED'}")
            print(f"  Server: {'Running' if server_running else 'STOPPED'}")
            
            if not calc_running or not server_running:
                print("\n[WARNING] One or more components stopped!")
                break
                
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        
    finally:
        # Terminate processes
        if calc_process.poll() is None:
            calc_process.terminate()
            print("Stopped CVD Calculator")
            
        if server_process.poll() is None:
            server_process.terminate()
            print("Stopped Monitor Server")
        
        # Final data check
        print("\nFinal data check...")
        check_supabase_data()
        
        print("\nSystem stopped.")

if __name__ == "__main__":
    main()