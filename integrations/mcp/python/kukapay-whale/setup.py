"""
Kukapay Hyperliquid Whale Alert MCP Server Setup
Monitors and alerts on whale trades ($1M+)
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_kukapay_whale_mcp():
    """Set up the kukapay hyperliquid-whalealert-mcp server"""
    
    print("="*60)
    print("Setting up Kukapay Hyperliquid Whale Alert MCP Server")
    print("="*60)
    
    # Clone repository
    repo_url = "https://github.com/kukapay/hyperliquid-whalealert-mcp.git"
    
    if not Path("hyperliquid-whalealert-mcp").exists():
        print(f"Cloning repository from {repo_url}...")
        subprocess.run(["git", "clone", repo_url], check=True)
        print("Repository cloned successfully!")
    else:
        print("Repository already exists, pulling latest changes...")
        subprocess.run(["git", "-C", "hyperliquid-whalealert-mcp", "pull"], check=True)
    
    # Install dependencies
    print("\nInstalling dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "hyperliquid-whalealert-mcp/requirements.txt"], check=True)
    
    print("\n✅ Kukapay Whale Alert MCP Server setup complete!")
    print("\nFeatures:")
    print("  - Real-time whale trade monitoring")
    print("  - Alerts for positions over $1 million")
    print("  - get_whale_alerts tool")
    print("  - summarize_whale_activity prompt")
    print("  - Customizable alert thresholds")
    
    return True


if __name__ == "__main__":
    setup_kukapay_whale_mcp()