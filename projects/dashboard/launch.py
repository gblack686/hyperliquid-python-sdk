#!/usr/bin/env python
"""Launch script for Hyperliquid Trading Dashboard."""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def check_venv():
    """Check if running in virtual environment."""
    return hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )

def activate_venv():
    """Activate virtual environment if not already active."""
    if not check_venv():
        venv_python = Path("venv/Scripts/python.exe")
        if venv_python.exists():
            # Re-run this script with venv Python
            subprocess.run([str(venv_python), __file__])
            sys.exit(0)
        else:
            print("Virtual environment not found. Creating...")
            subprocess.run([sys.executable, "-m", "venv", "venv"])
            print("Virtual environment created. Please run this script again.")
            sys.exit(0)

def check_dependencies():
    """Check and install missing dependencies."""
    print("Checking dependencies...")
    
    required_packages = [
        "streamlit", "pandas", "plotly", "supabase", "loguru",
        "msgpack", "orjson", "numba", "matplotlib", "ta", "pandas_ta"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing)
    
    print("All dependencies installed!")

def launch_app():
    """Launch the Streamlit app."""
    print("\n" + "="*50)
    print(" Hyperliquid Trading Dashboard")
    print("="*50)
    print("\nStarting dashboard...")
    print("Dashboard URL: http://localhost:8501")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Wait a moment then open browser
    def open_browser():
        time.sleep(3)
        webbrowser.open("http://localhost:8501")
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run Streamlit
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")

if __name__ == "__main__":
    activate_venv()
    check_dependencies()
    launch_app()