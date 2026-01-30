"""
MCP Client Test
Tests MCP server integration without real API keys
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, Optional
import websockets


class MCPClient:
    """Client for interacting with MCP servers"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8888"):
        self.base_url = base_url
        self.session = None
        self.ws = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        if self.ws:
            await self.ws.close()
    
    async def list_tools(self) -> Dict:
        """List available MCP tools"""
        async with self.session.get(f"{self.base_url}/mcp/tools") as response:
            return await response.json()
    
    async def execute_tool(self, method: str, params: Dict = None) -> Dict:
        """Execute an MCP tool"""
        payload = {
            "method": method,
            "params": params or {},
            "id": f"req_{datetime.now().timestamp()}"
        }
        
        async with self.session.post(
            f"{self.base_url}/mcp/execute",
            json=payload
        ) as response:
            result = await response.json()
            
            if 'error' in result and result['error']:
                raise Exception(f"MCP Error: {result['error']}")
            
            return result.get('result', {})
    
    async def connect_websocket(self):
        """Connect to WebSocket for real-time data"""
        ws_url = self.base_url.replace('http://', 'ws://') + '/ws'
        self.ws = await websockets.connect(ws_url)
        return self.ws
    
    async def stream_prices(self, duration: int = 10):
        """Stream price updates from WebSocket"""
        if not self.ws:
            await self.connect_websocket()
        
        print(f"Streaming prices for {duration} seconds...")
        
        end_time = datetime.now().timestamp() + duration
        
        while datetime.now().timestamp() < end_time:
            try:
                message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                data = json.loads(message)
                
                if data['type'] == 'price_update':
                    print(f"[PRICE] {data['timestamp']}")
                    for symbol, price in data['data'].items():
                        print(f"  {symbol}: ${price:.2f}")
                
                elif data['type'] == 'whale_alert':
                    alert = data['data']
                    print(f"[WHALE] {alert['symbol']} {alert['side']}: "
                          f"${alert['value']:,.0f} @ ${alert['price']:.2f}")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"WebSocket error: {e}")
                break


async def test_mcp_server():
    """Test the MCP server functionality"""
    print("="*70)
    print("MCP CLIENT TEST")
    print("="*70)
    print(f"Testing server at http://127.0.0.1:8888")
    print("="*70)
    
    async with MCPClient() as client:
        # Test 1: List available tools
        print("\n[TEST 1] Listing available tools...")
        tools = await client.list_tools()
        print(f"Found {len(tools['tools'])} tools:")
        for tool in tools['tools'][:3]:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Test 2: Get all mid prices
        print("\n[TEST 2] Getting mid prices...")
        mids = await client.execute_tool("get_all_mids")
        print("Mid prices:")
        for symbol, price in list(mids.items())[:3]:
            print(f"  {symbol}: ${price:.2f}")
        
        # Test 3: Get L2 order book
        print("\n[TEST 3] Getting L2 order book for BTC...")
        l2_book = await client.execute_tool("get_l2_book", {"symbol": "BTC"})
        print(f"Order book for {l2_book['symbol']}:")
        print(f"  Best bid: ${l2_book['bids'][0]['price']:.2f} x {l2_book['bids'][0]['size']:.2f}")
        print(f"  Best ask: ${l2_book['asks'][0]['price']:.2f} x {l2_book['asks'][0]['size']:.2f}")
        
        # Test 4: Get candle data
        print("\n[TEST 4] Getting candle snapshot...")
        candles = await client.execute_tool(
            "get_candle_snapshot",
            {"symbol": "ETH", "interval": "15m", "lookback": 10}
        )
        print(f"Got {len(candles)} candles")
        latest = candles[-1]
        print(f"Latest candle: O:{latest['open']:.2f} H:{latest['high']:.2f} "
              f"L:{latest['low']:.2f} C:{latest['close']:.2f}")
        
        # Test 5: Get user state
        print("\n[TEST 5] Getting user state...")
        user_state = await client.execute_tool(
            "get_user_state",
            {"address": "0x1234567890abcdef1234567890abcdef12345678"}
        )
        print(f"Account value: ${user_state['account_value']:,.2f}")
        print(f"Balance: ${user_state['balance']:,.2f}")
        print(f"Positions: {len(user_state['positions'])}")
        
        # Test 6: Get funding rates
        print("\n[TEST 6] Getting funding rates...")
        funding = await client.execute_tool("get_funding_rates")
        print("Funding rates:")
        for symbol, rate in list(funding.items())[:3]:
            print(f"  {symbol}: {rate:.4%}/hour")
        
        # Test 7: Get whale alerts
        print("\n[TEST 7] Getting whale alerts...")
        alerts = await client.execute_tool("get_whale_alerts", {"min_value": 500000})
        print(f"Found {len(alerts)} whale trades")
        for alert in alerts[:2]:
            print(f"  {alert['symbol']} {alert['side']}: ${alert['value']:,.0f}")
        
        # Test 8: Place mock order
        print("\n[TEST 8] Placing mock order...")
        order_result = await client.execute_tool(
            "place_order",
            {
                "symbol": "BTC",
                "side": "BUY",
                "size": 0.1,
                "price": 64000,
                "order_type": "LIMIT"
            }
        )
        print(f"Order placed: {order_result['order_id']}")
        
        # Test 9: Cancel mock order
        print("\n[TEST 9] Cancelling mock order...")
        cancel_result = await client.execute_tool(
            "cancel_order",
            {"order_id": order_result['order_id']}
        )
        print(f"Order cancelled: {cancel_result['message']}")
        
        # Test 10: WebSocket streaming
        print("\n[TEST 10] Testing WebSocket streaming...")
        await client.stream_prices(duration=5)
    
    print("\n" + "="*70)
    print("MCP CLIENT TEST COMPLETE")
    print("="*70)


async def test_error_handling():
    """Test error handling"""
    print("\n[ERROR TEST] Testing error handling...")
    
    async with MCPClient() as client:
        try:
            # Test with invalid method
            result = await client.execute_tool("invalid_method")
        except Exception as e:
            print(f"✓ Caught expected error: {e}")
        
        try:
            # Test with invalid symbol
            result = await client.execute_tool("get_l2_book", {"symbol": "INVALID"})
            if not result:
                print("✓ Handled invalid symbol gracefully")
        except Exception as e:
            print(f"Error with invalid symbol: {e}")


if __name__ == "__main__":
    # First, make sure the server is running
    print("Make sure the MCP test server is running:")
    print("  python mcp_test_server.py")
    print("\nPress Enter to start testing...")
    input()
    
    # Run tests
    asyncio.run(test_mcp_server())
    asyncio.run(test_error_handling())