"""
Real Data MCP Server for Hyperliquid
Uses actual Hyperliquid API for real market data
No API key needed for public endpoints
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

# FastAPI imports
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Pydantic for validation
from pydantic import BaseModel, Field

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

# Import Hyperliquid SDK
try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
    HAS_SDK = True
except ImportError:
    HAS_SDK = False
    print("Warning: Hyperliquid SDK not found in parent directory")

# Direct API calls as fallback
import requests


class MCPRequest(BaseModel):
    """MCP request model"""
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[str] = None


class MCPResponse(BaseModel):
    """MCP response model"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class RealDataMCPServer:
    """Real Data MCP Server using Hyperliquid API"""
    
    def __init__(self):
        self.app = FastAPI(title="Real Data Hyperliquid MCP Server", version="1.0.0")
        self.setup_routes()
        
        # Initialize Hyperliquid Info client if SDK available
        if HAS_SDK:
            self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
            print("Using Hyperliquid SDK for real data")
        else:
            self.info = None
            print("Using direct API calls for real data")
        
        # Direct API endpoint
        self.api_url = "https://api.hyperliquid.xyz/info"
        
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/")
        async def root():
            return {
                "name": "Real Data Hyperliquid MCP Server",
                "version": "1.0.0",
                "data_source": "REAL - Hyperliquid Mainnet API",
                "ready": True,
                "network": "mainnet",
                "api_url": "https://api.hyperliquid.xyz"
            }
        
        @self.app.get("/health")
        async def health():
            # Test API connection
            try:
                result = await self.get_all_mids({})
                is_healthy = result is not None and len(result) > 0
            except:
                is_healthy = False
                
            return {
                "status": "healthy" if is_healthy else "degraded",
                "data_source": "real",
                "api_connected": is_healthy,
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/mcp/tools")
        async def list_tools():
            return {
                "tools": self.get_available_tools()
            }
        
        @self.app.post("/mcp/execute")
        async def execute_tool(request: MCPRequest):
            try:
                result = await self.execute_method(request.method, request.params)
                return MCPResponse(result=result, id=request.id)
            except Exception as e:
                return MCPResponse(
                    error={"code": -1, "message": str(e)},
                    id=request.id
                )
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    # Send real price updates every 2 seconds
                    prices = await self.get_all_mids({})
                    await websocket.send_json({
                        "type": "price_update",
                        "data": prices,
                        "timestamp": datetime.now().isoformat(),
                        "source": "real"
                    })
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"WebSocket error: {e}")
            finally:
                await websocket.close()
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return [
            {
                "name": "get_all_mids",
                "description": "Get REAL mid prices for all symbols",
                "parameters": {},
                "data_source": "real"
            },
            {
                "name": "get_l2_book",
                "description": "Get REAL Level 2 order book",
                "parameters": {
                    "coin": {"type": "string", "required": True, "example": "BTC"},
                },
                "data_source": "real"
            },
            {
                "name": "get_recent_trades",
                "description": "Get REAL recent trades",
                "parameters": {
                    "coin": {"type": "string", "required": True, "example": "BTC"},
                },
                "data_source": "real"
            },
            {
                "name": "get_meta",
                "description": "Get REAL exchange metadata and asset info",
                "parameters": {},
                "data_source": "real"
            },
            {
                "name": "get_open_interest",
                "description": "Get REAL open interest for a coin",
                "parameters": {
                    "coin": {"type": "string", "required": True, "example": "BTC"}
                },
                "data_source": "real"
            },
            {
                "name": "get_funding_history",
                "description": "Get REAL funding rate history",
                "parameters": {
                    "coin": {"type": "string", "required": True, "example": "BTC"},
                    "lookback_days": {"type": "number", "default": 7}
                },
                "data_source": "real"
            },
            {
                "name": "get_perps_metadata",
                "description": "Get REAL perpetuals metadata",
                "parameters": {},
                "data_source": "real"
            },
            {
                "name": "get_spot_metadata",
                "description": "Get REAL spot trading pairs metadata",
                "parameters": {},
                "data_source": "real"
            },
            {
                "name": "get_candles",
                "description": "Get REAL historical candles",
                "parameters": {
                    "coin": {"type": "string", "required": True, "example": "BTC"},
                    "interval": {"type": "string", "default": "1h", "options": ["1m", "5m", "15m", "1h", "4h", "1d"]},
                    "lookback": {"type": "number", "default": 100}
                },
                "data_source": "real"
            },
            {
                "name": "get_volume_24h",
                "description": "Get REAL 24-hour trading volume",
                "parameters": {},
                "data_source": "real"
            }
        ]
    
    async def execute_method(self, method: str, params: Dict[str, Any]) -> Any:
        """Execute a method with given parameters"""
        
        method_map = {
            "get_all_mids": self.get_all_mids,
            "get_l2_book": self.get_l2_book,
            "get_recent_trades": self.get_recent_trades,
            "get_meta": self.get_meta,
            "get_open_interest": self.get_open_interest,
            "get_funding_history": self.get_funding_history,
            "get_perps_metadata": self.get_perps_metadata,
            "get_spot_metadata": self.get_spot_metadata,
            "get_candles": self.get_candles,
            "get_volume_24h": self.get_volume_24h
        }
        
        if method not in method_map:
            raise ValueError(f"Unknown method: {method}")
        
        return await method_map[method](params)
    
    async def get_all_mids(self, params: Dict[str, Any]) -> Dict[str, float]:
        """Get REAL mid prices for all symbols"""
        try:
            if self.info:
                # Use SDK if available
                result = self.info.all_mids()
                return result if result else {}
            else:
                # Direct API call
                response = requests.post(
                    self.api_url,
                    json={"type": "allMids"},
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json()
                return {}
        except Exception as e:
            print(f"Error fetching real mids: {e}")
            return {}
    
    async def get_l2_book(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get REAL Level 2 order book"""
        coin = params.get("coin", "BTC")
        
        try:
            if self.info:
                # Use SDK if available
                result = self.info.l2_snapshot(coin)
                if result:
                    return {
                        "coin": coin,
                        "levels": result.get("levels", [[], []]),
                        "timestamp": datetime.now().isoformat(),
                        "source": "real"
                    }
            else:
                # Direct API call
                response = requests.post(
                    self.api_url,
                    json={"type": "l2Book", "coin": coin},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "coin": coin,
                        "levels": data.get("levels", [[], []]),
                        "timestamp": datetime.now().isoformat(),
                        "source": "real"
                    }
            return {"coin": coin, "levels": [[], []], "error": "No data"}
        except Exception as e:
            print(f"Error fetching real L2 book: {e}")
            return {"coin": coin, "levels": [[], []], "error": str(e)}
    
    async def get_recent_trades(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get REAL recent trades"""
        coin = params.get("coin", "BTC")
        
        try:
            if self.info:
                # Use SDK if available - get recent trades from user fills
                # Note: This would need a user address, so we'll use direct API
                pass
            
            # Direct API call for recent trades
            response = requests.post(
                self.api_url,
                json={"type": "recentTrades", "coin": coin},
                timeout=10
            )
            if response.status_code == 200:
                trades = response.json()
                return trades if isinstance(trades, list) else []
            return []
        except Exception as e:
            print(f"Error fetching real recent trades: {e}")
            return []
    
    async def get_meta(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get REAL exchange metadata"""
        try:
            if self.info:
                # Use SDK if available
                result = self.info.meta()
                return result if result else {}
            else:
                # Direct API call
                response = requests.post(
                    self.api_url,
                    json={"type": "meta"},
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json()
            return {}
        except Exception as e:
            print(f"Error fetching real meta: {e}")
            return {}
    
    async def get_open_interest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get REAL open interest"""
        coin = params.get("coin", "BTC")
        
        try:
            # Direct API call
            response = requests.post(
                self.api_url,
                json={"type": "openInterest", "coin": coin},
                timeout=10
            )
            if response.status_code == 200:
                return {
                    "coin": coin,
                    "data": response.json(),
                    "timestamp": datetime.now().isoformat(),
                    "source": "real"
                }
            return {"coin": coin, "data": None}
        except Exception as e:
            print(f"Error fetching real open interest: {e}")
            return {"coin": coin, "error": str(e)}
    
    async def get_funding_history(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get REAL funding rate history"""
        coin = params.get("coin", "BTC")
        lookback_days = params.get("lookback_days", 7)
        
        try:
            if self.info:
                # Use SDK if available
                end_time = int(datetime.now().timestamp() * 1000)
                start_time = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)
                
                result = self.info.funding_history(coin, start_time, end_time)
                if result:
                    return result
            
            # Direct API call
            response = requests.post(
                self.api_url,
                json={
                    "type": "fundingHistory",
                    "coin": coin,
                    "startTime": int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching real funding history: {e}")
            return []
    
    async def get_perps_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get REAL perpetuals metadata"""
        try:
            # Direct API call
            response = requests.post(
                self.api_url,
                json={"type": "perpsMetaAndAssetCtxs"},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"Error fetching real perps metadata: {e}")
            return {}
    
    async def get_spot_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get REAL spot metadata"""
        try:
            # Direct API call
            response = requests.post(
                self.api_url,
                json={"type": "spotMetaAndAssetCtxs"},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"Error fetching real spot metadata: {e}")
            return {}
    
    async def get_candles(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get REAL historical candles"""
        coin = params.get("coin", "BTC")
        interval = params.get("interval", "1h")
        lookback = params.get("lookback", 100)
        
        try:
            if self.info:
                # Use SDK if available
                result = self.info.candles_snapshot(coin, interval, lookback)
                if result:
                    return result
            
            # Direct API call
            response = requests.post(
                self.api_url,
                json={
                    "type": "candleSnapshot",
                    "req": {
                        "coin": coin,
                        "interval": interval,
                        "startTime": int((datetime.now() - timedelta(hours=lookback)).timestamp() * 1000),
                        "endTime": int(datetime.now().timestamp() * 1000)
                    }
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching real candles: {e}")
            return []
    
    async def get_volume_24h(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get REAL 24-hour trading volume"""
        try:
            # Get all mids first to get list of coins
            mids = await self.get_all_mids({})
            
            # Direct API call for volume data
            response = requests.post(
                self.api_url,
                json={"type": "metaAndAssetCtxs"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Extract volume data from the response
                volumes = {}
                if isinstance(data, list) and len(data) > 1:
                    asset_ctxs = data[1] if len(data) > 1 else []
                    for i, ctx in enumerate(asset_ctxs):
                        if isinstance(ctx, dict) and "dayNtlVlm" in ctx:
                            # Map index to coin name if possible
                            coin = list(mids.keys())[i] if i < len(mids) else f"Asset_{i}"
                            volumes[coin] = ctx.get("dayNtlVlm", 0)
                
                return {
                    "volumes": volumes,
                    "total": sum(volumes.values()),
                    "timestamp": datetime.now().isoformat(),
                    "source": "real"
                }
            return {"volumes": {}, "total": 0}
        except Exception as e:
            print(f"Error fetching real volume: {e}")
            return {"volumes": {}, "error": str(e)}


def create_app() -> FastAPI:
    """Create and configure the FastAPI app"""
    server = RealDataMCPServer()
    return server.app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", "8889"))
    
    print("="*60)
    print("REAL DATA HYPERLIQUID MCP SERVER")
    print("="*60)
    print(f"Starting on port {port}")
    print(f"Data Source: REAL - Hyperliquid Mainnet API")
    print(f"API URL: https://api.hyperliquid.xyz")
    print(f"Health check: http://localhost:{port}/health")
    print(f"Tools list: http://localhost:{port}/mcp/tools")
    print("="*60)
    print("No API key required for public market data!")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=port)