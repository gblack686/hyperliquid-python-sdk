"""
Setup Script for Python MCP Servers Only
Focused on Python implementations which are easier to set up
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_python_environment():
    """Set up Python virtual environment and dependencies"""
    print("="*60)
    print("Setting up Python MCP Servers")
    print("="*60)
    
    # Create virtual environment if it doesn't exist
    if not Path("venv").exists():
        print("\nCreating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("[OK] Virtual environment created")
    
    # Determine pip path based on OS
    if sys.platform == "win32":
        pip_path = Path("venv/Scripts/pip.exe")
        python_path = Path("venv/Scripts/python.exe")
    else:
        pip_path = Path("venv/bin/pip")
        python_path = Path("venv/bin/python")
    
    # Upgrade pip
    print("\nUpgrading pip...")
    subprocess.run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    # Install Python MCP dependencies
    print("\nInstalling Python dependencies...")
    requirements = [
        "hyperliquid-python-sdk>=0.17.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "websockets>=11.0",
        "aiohttp>=3.8.0",
        "pydantic>=2.0.0",
        "pandas>=2.0.0",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.0"
    ]
    
    for req in requirements:
        print(f"Installing {req}...")
        subprocess.run([str(pip_path), "install", req], check=True)
    
    print("\n[OK] Python environment ready!")
    return str(python_path), str(pip_path)


def install_midodimori_mcp(pip_path):
    """Install the midodimori MCP server from PyPI"""
    print("\n" + "="*60)
    print("Installing Midodimori Hyperliquid MCP")
    print("="*60)
    
    try:
        subprocess.run([pip_path, "install", "hyperliquid-mcp>=0.1.5"], check=True)
        print("[OK] Midodimori MCP installed successfully!")
        return True
    except:
        print("[WARNING] Midodimori MCP not available on PyPI yet")
        return False


def create_mock_server_launcher():
    """Create a launcher for the mock MCP server"""
    launcher_content = '''"""
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
'''
    
    with open("start_mock_server.py", "w") as f:
        f.write(launcher_content)
    
    print("[OK] Created start_mock_server.py")


def create_python_mcp_server():
    """Create a simple Python MCP server using the SDK"""
    server_content = '''"""
Simple Python MCP Server
Uses the official Hyperliquid SDK with MCP protocol wrapper
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import Hyperliquid SDK
try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
except ImportError:
    print("Please install hyperliquid-python-sdk: pip install hyperliquid-python-sdk")
    exit(1)

load_dotenv()

# Configuration
API_KEY = os.getenv("HYPERLIQUID_API_KEY", "")
SECRET_KEY = os.getenv("HYPERLIQUID_SECRET_KEY", "")
NETWORK = os.getenv("HYPERLIQUID_NETWORK", "mainnet")
PORT = int(os.getenv("MCP_PYTHON_PORT", 8001))

# Initialize FastAPI
app = FastAPI(title="Hyperliquid Python MCP Server")

# Initialize Hyperliquid Info client
api_url = constants.MAINNET_API_URL if NETWORK == "mainnet" else constants.TESTNET_API_URL
info = Info(api_url, skip_ws=True)


class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any] = {}
    id: Optional[str] = None


class MCPResponse(BaseModel):
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@app.get("/")
async def root():
    return {
        "name": "Hyperliquid Python MCP Server",
        "version": "1.0.0",
        "network": NETWORK,
        "ready": True
    }


@app.get("/mcp/tools")
async def list_tools():
    """List available MCP tools"""
    return {
        "tools": [
            {
                "name": "get_all_mids",
                "description": "Get mid prices for all symbols",
                "parameters": {}
            },
            {
                "name": "get_l2_snapshot",
                "description": "Get L2 order book snapshot",
                "parameters": {
                    "coin": {"type": "string", "required": True}
                }
            },
            {
                "name": "get_candles",
                "description": "Get historical candles",
                "parameters": {
                    "coin": {"type": "string", "required": True},
                    "interval": {"type": "string", "default": "15m"},
                    "lookback": {"type": "number", "default": 100}
                }
            },
            {
                "name": "get_meta",
                "description": "Get exchange metadata",
                "parameters": {}
            },
            {
                "name": "get_open_orders",
                "description": "Get user open orders",
                "parameters": {
                    "user": {"type": "string", "required": True}
                }
            },
            {
                "name": "get_user_state",
                "description": "Get user account state",
                "parameters": {
                    "user": {"type": "string", "required": True}
                }
            },
            {
                "name": "get_user_fills",
                "description": "Get user trade fills",
                "parameters": {
                    "user": {"type": "string", "required": True}
                }
            }
        ]
    }


@app.post("/mcp/execute")
async def execute_tool(request: MCPRequest):
    """Execute an MCP tool"""
    try:
        method = request.method
        params = request.params
        
        result = None
        
        if method == "get_all_mids":
            result = info.all_mids()
            
        elif method == "get_l2_snapshot":
            coin = params.get("coin", "BTC")
            result = info.l2_snapshot(coin)
            
        elif method == "get_candles":
            coin = params.get("coin", "BTC")
            interval = params.get("interval", "15m")
            lookback = params.get("lookback", 100)
            result = info.candles_snapshot(coin, interval, lookback)
            
        elif method == "get_meta":
            result = info.meta()
            
        elif method == "get_open_orders":
            user = params.get("user")
            if user:
                result = info.open_orders(user)
            else:
                raise ValueError("User address required")
                
        elif method == "get_user_state":
            user = params.get("user")
            if user:
                result = info.user_state(user)
            else:
                raise ValueError("User address required")
                
        elif method == "get_user_fills":
            user = params.get("user")
            if user:
                result = info.user_fills(user)
            else:
                raise ValueError("User address required")
                
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return MCPResponse(result=result, id=request.id)
        
    except Exception as e:
        return MCPResponse(
            error={"code": -1, "message": str(e)},
            id=request.id
        )


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


def run_server():
    """Run the MCP server"""
    print(f"Starting Hyperliquid Python MCP Server on port {PORT}")
    print(f"Network: {NETWORK}")
    print(f"API URL: {api_url}")
    uvicorn.run(app, host="127.0.0.1", port=PORT)


if __name__ == "__main__":
    run_server()
'''
    
    with open("python_mcp_server.py", "w") as f:
        f.write(server_content)
    
    print("[OK] Created python_mcp_server.py")


def create_test_client():
    """Create a test client for the Python MCP server"""
    client_content = '''"""
Test Client for Python MCP Server
Tests both mock and real MCP servers
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any


class MCPTestClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_server(self):
        """Test MCP server endpoints"""
        print(f"Testing MCP server at {self.base_url}")
        print("="*50)
        
        # Test root endpoint
        try:
            async with self.session.get(f"{self.base_url}/") as resp:
                data = await resp.json()
                print(f"[OK] Server: {data.get('name', 'Unknown')}")
                print(f"  Network: {data.get('network', 'Unknown')}")
        except Exception as e:
            print(f"[FAIL] Server not reachable: {e}")
            return False
        
        # Test tools listing
        async with self.session.get(f"{self.base_url}/mcp/tools") as resp:
            tools = await resp.json()
            print(f"[OK] Available tools: {len(tools.get('tools', []))}")
            for tool in tools.get('tools', [])[:3]:
                print(f"  - {tool['name']}: {tool['description']}")
        
        # Test get_all_mids
        payload = {
            "method": "get_all_mids",
            "params": {},
            "id": "test1"
        }
        async with self.session.post(f"{self.base_url}/mcp/execute", json=payload) as resp:
            result = await resp.json()
            if result.get('result'):
                mids = result['result']
                if isinstance(mids, dict) and mids:
                    btc_price = mids.get('BTC', 0)
                    eth_price = mids.get('ETH', 0)
                    print(f"[OK] Mid prices: BTC=${btc_price:.2f}, ETH=${eth_price:.2f}")
                else:
                    print("[OK] Mid prices endpoint working (no data)")
            else:
                print(f"[WARNING] Mid prices error: {result.get('error', {}).get('message', 'Unknown')}")
        
        print("="*50)
        print("Test complete!")
        return True


async def main():
    # Test mock server
    print("\\n1. Testing Mock Server (port 8888)...")
    async with MCPTestClient("http://127.0.0.1:8888") as client:
        await client.test_server()
    
    # Test Python MCP server
    print("\\n2. Testing Python MCP Server (port 8001)...")
    async with MCPTestClient("http://127.0.0.1:8001") as client:
        await client.test_server()


if __name__ == "__main__":
    asyncio.run(main())
'''
    
    with open("test_mcp_client.py", "w") as f:
        f.write(client_content)
    
    print("[OK] Created test_mcp_client.py")


def create_windows_launcher():
    """Create Windows batch file to start servers"""
    batch_content = """@echo off
echo ============================================================
echo Hyperliquid MCP Servers Launcher
echo ============================================================
echo.

echo Starting servers...
echo.

REM Start Mock Server (for testing)
start "Mock MCP Server" cmd /k "venv\\Scripts\\python.exe start_mock_server.py"
timeout /t 2 >nul

REM Start Python MCP Server
start "Python MCP Server" cmd /k "venv\\Scripts\\python.exe python_mcp_server.py"
timeout /t 2 >nul

echo.
echo Servers are starting...
echo.
echo Available servers:
echo   Mock Server: http://localhost:8888 (for testing without API keys)
echo   Python MCP: http://localhost:8001 (requires API keys in .env)
echo.
echo To test the servers, run:
echo   venv\\Scripts\\python.exe test_mcp_client.py
echo.
pause
"""
    
    with open("start_servers.bat", "w") as f:
        f.write(batch_content)
    
    print("[OK] Created start_servers.bat")


def main():
    """Main setup function"""
    print("\nSetting up Python MCP servers...")
    
    # Change to MCP directory
    os.chdir(Path(__file__).parent)
    
    # Set up Python environment
    python_path, pip_path = setup_python_environment()
    
    # Try to install midodimori MCP
    install_midodimori_mcp(pip_path)
    
    # Create server files
    create_mock_server_launcher()
    create_python_mcp_server()
    create_test_client()
    create_windows_launcher()
    
    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        env_content = """# Hyperliquid MCP Configuration
HYPERLIQUID_API_KEY=your_api_key_here
HYPERLIQUID_SECRET_KEY=your_secret_key_here
HYPERLIQUID_NETWORK=mainnet
MCP_PYTHON_PORT=8001
"""
        with open(".env", "w") as f:
            f.write(env_content)
        print("[OK] Created .env file (please add your API keys)")
    
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Update .env file with your API keys (optional)")
    print("2. Start the servers:")
    print("   Windows: start_servers.bat")
    print("   Or manually:")
    print(f"     {python_path} start_mock_server.py")
    print(f"     {python_path} python_mcp_server.py")
    print("3. Test the servers:")
    print(f"   {python_path} test_mcp_client.py")
    print("\nThe mock server (port 8888) works without API keys!")


if __name__ == "__main__":
    main()