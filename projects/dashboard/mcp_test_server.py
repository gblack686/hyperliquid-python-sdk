"""
Mock MCP Server for Testing
Provides a test environment for MCP integration without real API keys
"""

import json
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============= Data Models =============

class MCPRequest(BaseModel):
    """Standard MCP request format"""
    method: str
    params: Dict[str, Any] = {}
    id: Optional[str] = None


class MCPResponse(BaseModel):
    """Standard MCP response format"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


# ============= Mock Data Generator =============

class MockDataGenerator:
    """Generates realistic mock data for testing"""
    
    def __init__(self):
        self.symbols = ['BTC', 'ETH', 'SOL', 'HYPE', 'ARB', 'OP', 'MATIC']
        self.base_prices = {
            'BTC': 65000.0,
            'ETH': 3500.0,
            'SOL': 150.0,
            'HYPE': 25.0,
            'ARB': 1.2,
            'OP': 2.5,
            'MATIC': 0.8
        }
    
    def get_all_mids(self) -> Dict[str, float]:
        """Generate mock mid prices"""
        mids = {}
        for symbol, base_price in self.base_prices.items():
            # Add some random variance (±2%)
            variance = random.uniform(-0.02, 0.02)
            mids[symbol] = base_price * (1 + variance)
        return mids
    
    def get_l2_book(self, symbol: str) -> Dict:
        """Generate mock L2 order book"""
        if symbol not in self.base_prices:
            return {}
        
        mid_price = self.base_prices[symbol]
        
        # Generate bids and asks
        bids = []
        asks = []
        
        for i in range(10):
            bid_price = mid_price * (1 - 0.001 * (i + 1))
            ask_price = mid_price * (1 + 0.001 * (i + 1))
            
            bid_size = random.uniform(0.1, 10.0)
            ask_size = random.uniform(0.1, 10.0)
            
            bids.append({'price': bid_price, 'size': bid_size})
            asks.append({'price': ask_price, 'size': ask_size})
        
        return {
            'symbol': symbol,
            'bids': bids,
            'asks': asks,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_candle_snapshot(self, symbol: str, interval: str = '15m', 
                           lookback: int = 100) -> List[Dict]:
        """Generate mock candle data"""
        if symbol not in self.base_prices:
            return []
        
        candles = []
        base_price = self.base_prices[symbol]
        
        # Interval to minutes mapping
        interval_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        
        minutes = interval_minutes.get(interval, 15)
        current_time = datetime.now()
        
        for i in range(lookback):
            timestamp = current_time - timedelta(minutes=minutes * i)
            
            # Generate OHLCV data with some trend
            trend = random.uniform(-0.001, 0.001) * i
            open_price = base_price * (1 + trend + random.uniform(-0.005, 0.005))
            high = open_price * (1 + random.uniform(0, 0.01))
            low = open_price * (1 - random.uniform(0, 0.01))
            close = random.uniform(low, high)
            volume = random.uniform(100, 10000)
            
            candles.append({
                'timestamp': int(timestamp.timestamp() * 1000),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return list(reversed(candles))
    
    def get_user_state(self, address: str) -> Dict:
        """Generate mock user state"""
        return {
            'address': address,
            'account_value': random.uniform(10000, 100000),
            'balance': random.uniform(5000, 50000),
            'margin_used': random.uniform(1000, 10000),
            'positions': self._generate_positions(),
            'open_orders': self._generate_orders(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_funding_rates(self) -> Dict[str, float]:
        """Generate mock funding rates"""
        rates = {}
        for symbol in self.symbols:
            # Funding rates typically range from -0.01% to 0.01% per hour
            rates[symbol] = random.uniform(-0.0001, 0.0001)
        return rates
    
    def get_whale_alerts(self, min_value: float = 1000000) -> List[Dict]:
        """Generate mock whale trade alerts"""
        alerts = []
        
        for _ in range(random.randint(0, 5)):
            symbol = random.choice(self.symbols)
            side = random.choice(['BUY', 'SELL'])
            size = random.uniform(min_value / self.base_prices[symbol], 
                                 min_value * 3 / self.base_prices[symbol])
            
            alerts.append({
                'symbol': symbol,
                'side': side,
                'size': size,
                'value': size * self.base_prices[symbol],
                'price': self.base_prices[symbol],
                'timestamp': datetime.now().isoformat(),
                'address': f"0x{''.join(random.choices('0123456789abcdef', k=40))}"
            })
        
        return alerts
    
    def _generate_positions(self) -> List[Dict]:
        """Generate mock positions"""
        positions = []
        
        for _ in range(random.randint(0, 3)):
            symbol = random.choice(self.symbols)
            side = random.choice(['LONG', 'SHORT'])
            size = random.uniform(0.1, 10.0)
            entry_price = self.base_prices[symbol] * random.uniform(0.95, 1.05)
            
            positions.append({
                'symbol': symbol,
                'side': side,
                'size': size,
                'entry_price': entry_price,
                'mark_price': self.base_prices[symbol],
                'pnl': (self.base_prices[symbol] - entry_price) * size * (1 if side == 'LONG' else -1)
            })
        
        return positions
    
    def _generate_orders(self) -> List[Dict]:
        """Generate mock orders"""
        orders = []
        
        for _ in range(random.randint(0, 5)):
            symbol = random.choice(self.symbols)
            side = random.choice(['BUY', 'SELL'])
            order_type = random.choice(['LIMIT', 'STOP_MARKET', 'STOP_LIMIT'])
            size = random.uniform(0.1, 5.0)
            
            if side == 'BUY':
                price = self.base_prices[symbol] * random.uniform(0.95, 0.99)
            else:
                price = self.base_prices[symbol] * random.uniform(1.01, 1.05)
            
            orders.append({
                'id': f"order_{random.randint(1000, 9999)}",
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'size': size,
                'price': price,
                'status': 'OPEN',
                'timestamp': datetime.now().isoformat()
            })
        
        return orders


# ============= MCP Server Implementation =============

app = FastAPI(title="Mock Hyperliquid MCP Server", version="1.0.0")
data_generator = MockDataGenerator()


@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "Mock Hyperliquid MCP Server",
        "version": "1.0.0",
        "description": "Test server for MCP integration without real API keys",
        "endpoints": [
            "/mcp/tools",
            "/mcp/execute"
        ]
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
                "name": "get_l2_book",
                "description": "Get Level 2 order book",
                "parameters": {
                    "symbol": {"type": "string", "required": True}
                }
            },
            {
                "name": "get_candle_snapshot",
                "description": "Get historical candles",
                "parameters": {
                    "symbol": {"type": "string", "required": True},
                    "interval": {"type": "string", "default": "15m"},
                    "lookback": {"type": "integer", "default": 100}
                }
            },
            {
                "name": "get_user_state",
                "description": "Get user account state",
                "parameters": {
                    "address": {"type": "string", "required": True}
                }
            },
            {
                "name": "get_funding_rates",
                "description": "Get current funding rates",
                "parameters": {}
            },
            {
                "name": "get_whale_alerts",
                "description": "Get whale trade alerts",
                "parameters": {
                    "min_value": {"type": "number", "default": 1000000}
                }
            },
            {
                "name": "place_order",
                "description": "Place a mock order",
                "parameters": {
                    "symbol": {"type": "string", "required": True},
                    "side": {"type": "string", "required": True},
                    "size": {"type": "number", "required": True},
                    "price": {"type": "number"},
                    "order_type": {"type": "string", "default": "LIMIT"}
                }
            },
            {
                "name": "cancel_order",
                "description": "Cancel a mock order",
                "parameters": {
                    "order_id": {"type": "string", "required": True}
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
        
        logger.info(f"Executing method: {method} with params: {params}")
        
        # Route to appropriate handler
        if method == "get_all_mids":
            result = data_generator.get_all_mids()
        
        elif method == "get_l2_book":
            symbol = params.get('symbol', 'BTC')
            result = data_generator.get_l2_book(symbol)
        
        elif method == "get_candle_snapshot":
            symbol = params.get('symbol', 'BTC')
            interval = params.get('interval', '15m')
            lookback = params.get('lookback', 100)
            result = data_generator.get_candle_snapshot(symbol, interval, lookback)
        
        elif method == "get_user_state":
            address = params.get('address', '0x' + '0' * 40)
            result = data_generator.get_user_state(address)
        
        elif method == "get_funding_rates":
            result = data_generator.get_funding_rates()
        
        elif method == "get_whale_alerts":
            min_value = params.get('min_value', 1000000)
            result = data_generator.get_whale_alerts(min_value)
        
        elif method == "place_order":
            # Mock order placement
            result = {
                'success': True,
                'order_id': f"order_{random.randint(10000, 99999)}",
                'message': 'Mock order placed successfully',
                'params': params
            }
        
        elif method == "cancel_order":
            # Mock order cancellation
            result = {
                'success': True,
                'message': f"Mock order {params.get('order_id')} cancelled",
                'params': params
            }
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return MCPResponse(result=result, id=request.id)
    
    except Exception as e:
        logger.error(f"Error executing method: {e}")
        return MCPResponse(
            error={"code": -1, "message": str(e)},
            id=request.id
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ============= WebSocket Support (Optional) =============

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time mock data"""
    await websocket.accept()
    
    try:
        while True:
            # Send mock price updates every second
            await asyncio.sleep(1)
            
            mids = data_generator.get_all_mids()
            await websocket.send_json({
                "type": "price_update",
                "data": mids,
                "timestamp": datetime.now().isoformat()
            })
            
            # Occasionally send whale alerts
            if random.random() < 0.1:  # 10% chance
                alerts = data_generator.get_whale_alerts()
                if alerts:
                    await websocket.send_json({
                        "type": "whale_alert",
                        "data": alerts[0],
                        "timestamp": datetime.now().isoformat()
                    })
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


def run_server(host: str = "127.0.0.1", port: int = 8888):
    """Run the mock MCP server"""
    print("="*70)
    print("MOCK HYPERLIQUID MCP SERVER")
    print("="*70)
    print(f"Starting server at http://{host}:{port}")
    print("Available endpoints:")
    print(f"  - http://{host}:{port}/")
    print(f"  - http://{host}:{port}/mcp/tools")
    print(f"  - http://{host}:{port}/mcp/execute")
    print(f"  - ws://{host}:{port}/ws")
    print("="*70)
    print("Press Ctrl+C to stop")
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()