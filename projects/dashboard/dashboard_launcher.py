"""
Dashboard Launcher - Choose which dashboard view to run
"""

import sys
import subprocess
import os
from datetime import datetime

def print_header():
    print("=" * 70)
    print(" HYPERLIQUID TRADING DASHBOARD - LAUNCHER")
    print("=" * 70)
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

def print_menu():
    print("SELECT DASHBOARD VIEW:")
    print("-" * 40)
    print("1. Enhanced Dashboard (Advanced Charts)")
    print("2. Simplified Dashboard (Card View)")
    print("3. Charts Dashboard (All Metrics)")
    print("4. CVD Monitor (Standalone)")
    print("5. MCP Server Examples (Live Data)")
    print("6. Run All Indicators Only")
    print("7. Exit")
    print("-" * 40)
    print()

def run_dashboard(dashboard_file, port=8501, name="Dashboard"):
    """Run a specific dashboard"""
    print(f"\n[INFO] Starting {name}...")
    print(f"[INFO] Access at: http://localhost:{port}")
    print("[INFO] Press Ctrl+C to stop\n")
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        dashboard_file,
        "--server.port", str(port),
        "--server.headless", "true"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print(f"\n[INFO] {name} stopped by user")
    except Exception as e:
        print(f"[ERROR] Failed to run {name}: {e}")

def run_indicators():
    """Run the indicator manager"""
    print("\n[INFO] Starting Indicator Manager with CVD...")
    print("[INFO] Press Ctrl+C to stop\n")
    
    cmd = [
        sys.executable, "indicator_manager.py",
        "--symbols", "BTC", "ETH", "SOL", "HYPE",
        "--indicators", "cvd", "open_interest", "funding_rate", 
        "vwap", "bollinger", "volume_profile", "atr", "liquidations"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[INFO] Indicators stopped by user")
    except Exception as e:
        print(f"[ERROR] Failed to run indicators: {e}")

def run_cvd_monitor():
    """Run the CVD monitor server"""
    print("\n[INFO] Starting CVD Monitor Server...")
    print("[INFO] Dashboard at: http://localhost:8001")
    print("[INFO] API Docs at: http://localhost:8001/docs")
    print("[INFO] Press Ctrl+C to stop\n")
    
    cmd = [sys.executable, "cvd_monitor_server.py"]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[INFO] CVD Monitor stopped by user")
    except Exception as e:
        print(f"[ERROR] Failed to run CVD monitor: {e}")

def main():
    print_header()
    
    while True:
        print_menu()
        
        try:
            choice = input("Enter your choice (1-7): ").strip()
            
            if choice == "1":
                run_dashboard("app_enhanced.py", 8501, "Enhanced Dashboard")
                
            elif choice == "2":
                run_dashboard("app_simplified.py", 8502, "Simplified Dashboard")
                
            elif choice == "3":
                run_dashboard("app_charts.py", 8503, "Charts Dashboard")
                
            elif choice == "4":
                run_cvd_monitor()
                
            elif choice == "5":
                run_dashboard("app_mcp_examples.py", 8504, "MCP Server Examples")
                
            elif choice == "6":
                run_indicators()
                
            elif choice == "7":
                print("\n[INFO] Exiting launcher...")
                break
                
            else:
                print("[ERROR] Invalid choice. Please select 1-7.\n")
                continue
            
            # After running a dashboard, ask if they want to run another
            print("\n" + "=" * 70)
            cont = input("\nRun another dashboard? (y/n): ").strip().lower()
            if cont != 'y':
                break
                
        except KeyboardInterrupt:
            print("\n\n[INFO] Launcher interrupted by user")
            break
        except Exception as e:
            print(f"[ERROR] An error occurred: {e}")
            continue
    
    print("\n" + "=" * 70)
    print("Thank you for using Hyperliquid Trading Dashboard!")
    print("=" * 70)

if __name__ == "__main__":
    main()