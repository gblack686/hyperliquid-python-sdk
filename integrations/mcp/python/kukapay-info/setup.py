"""
Kukapay Hyperliquid Info MCP Server Setup
Read-only data access with analysis prompts
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_kukapay_info_mcp():
    """Set up the kukapay hyperliquid-info-mcp server"""
    
    print("="*60)
    print("Setting up Kukapay Hyperliquid Info MCP Server")
    print("="*60)
    
    # Clone repository
    repo_url = "https://github.com/kukapay/hyperliquid-info-mcp.git"
    
    if not Path("hyperliquid-info-mcp").exists():
        print(f"Cloning repository from {repo_url}...")
        subprocess.run(["git", "clone", repo_url], check=True)
        print("Repository cloned successfully!")
    else:
        print("Repository already exists, pulling latest changes...")
        subprocess.run(["git", "-C", "hyperliquid-info-mcp", "pull"], check=True)
    
    # Install dependencies
    print("\nInstalling dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "hyperliquid-info-mcp/requirements.txt"], check=True)
    
    print("\n✅ Kukapay Info MCP Server setup complete!")
    print("\nAvailable tools:")
    print("  - get_user_state")
    print("  - get_user_open_orders")
    print("  - get_user_trade_history")
    print("  - get_user_funding_history")
    print("  - get_all_mids")
    print("  - get_l2_snapshot")
    print("  - get_candles_snapshot")
    print("  - analyze_positions (AI prompt)")
    
    return True


if __name__ == "__main__":
    setup_kukapay_info_mcp()