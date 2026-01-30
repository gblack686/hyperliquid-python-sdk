"""
Mock MCP Server Launcher
Start the mock server for testing without API keys
"""

import sys
import os
sys.path.append("../hyperliquid-trading-dashboard")

from mcp_test_server import run_server

if __name__ == "__main__":
    print("Starting Mock MCP Server on port 8888...")
    print("Use this for testing without real API keys")
    run_server(host="127.0.0.1", port=8888)
