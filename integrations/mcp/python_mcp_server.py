"""
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
