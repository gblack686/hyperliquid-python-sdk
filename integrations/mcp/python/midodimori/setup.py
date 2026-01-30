"""
Midodimori Hyperliquid MCP Server Setup
Comprehensive trading tools with Pydantic validation
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_midodimori_mcp():
    """Set up the midodimori hyperliquid-mcp server from PyPI"""
    
    print("="*60)
    print("Setting up Midodimori Hyperliquid MCP Server")
    print("="*60)
    
    # Install from PyPI
    print("Installing hyperliquid-mcp from PyPI...")
    subprocess.run([sys.executable, "-m", "pip", "install", "hyperliquid-mcp>=0.1.5"], check=True)
    
    print("\n✅ Midodimori MCP Server installed successfully!")
    print("\nFeatures:")
    print("  - 29 comprehensive trading tools")
    print("  - Full account management")
    print("  - Market data access")
    print("  - Risk simulation and validation")
    print("  - Pydantic type safety")
    print("  - Robust error handling")
    
    print("\nTo start the server:")
    print("  hyperliquid-mcp serve --port 8003")
    print("\nOr use as a library:")
    print("  from hyperliquid_mcp import HyperliquidMCP")
    
    return True


def create_example_config():
    """Create an example configuration file"""
    
    config = """# Midodimori Hyperliquid MCP Configuration

from hyperliquid_mcp import HyperliquidMCP, MCPConfig
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
config = MCPConfig(
    api_key=os.getenv("HYPERLIQUID_API_KEY"),
    secret_key=os.getenv("HYPERLIQUID_SECRET_KEY"),
    network="mainnet",  # or "testnet"
    port=8003,
    enable_websocket=True,
    enable_risk_checks=True,
    max_position_size=10000,  # USD
    max_leverage=5.0,
    allowed_symbols=["BTC", "ETH", "SOL", "HYPE"],
)

# Initialize MCP server
mcp = HyperliquidMCP(config)

# Example: Get all available tools
tools = mcp.list_tools()
print(f"Available tools: {len(tools)}")

# Example: Execute a tool
result = mcp.execute_tool(
    method="get_account_info",
    params={}
)
print(f"Account info: {result}")

# Start the server
if __name__ == "__main__":
    mcp.run()
"""
    
    with open("example_server.py", "w") as f:
        f.write(config)
    
    print("\n📄 Created example_server.py with configuration template")


if __name__ == "__main__":
    setup_midodimori_mcp()
    create_example_config()