"""
Quick MCP Test
Tests basic MCP functionality without WebSocket
"""

import asyncio
import aiohttp
import json
from datetime import datetime


async def quick_test():
    """Quick test of MCP server"""
    base_url = "http://127.0.0.1:8888"
    
    print("Testing MCP Server...")
    print("="*40)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Check server is running
        try:
            async with session.get(f"{base_url}/") as response:
                data = await response.json()
                print(f"[OK] Server: {data['name']} v{data['version']}")
        except Exception as e:
            print(f"[FAIL] Server not reachable: {e}")
            return
        
        # Test 2: List tools
        async with session.get(f"{base_url}/mcp/tools") as response:
            tools = await response.json()
            print(f"[OK] Found {len(tools['tools'])} tools")
        
        # Test 3: Get mid prices
        payload = {
            "method": "get_all_mids",
            "params": {},
            "id": "test1"
        }
        async with session.post(f"{base_url}/mcp/execute", json=payload) as response:
            result = await response.json()
            mids = result['result']
            print(f"[OK] Mid prices: BTC=${mids['BTC']:.2f}, ETH=${mids['ETH']:.2f}")
        
        # Test 4: Get L2 book
        payload = {
            "method": "get_l2_book",
            "params": {"symbol": "HYPE"},
            "id": "test2"
        }
        async with session.post(f"{base_url}/mcp/execute", json=payload) as response:
            result = await response.json()
            book = result['result']
            print(f"[OK] L2 Book for {book['symbol']}: {len(book['bids'])} bids, {len(book['asks'])} asks")
        
        # Test 5: Get funding rates
        payload = {
            "method": "get_funding_rates",
            "params": {},
            "id": "test3"
        }
        async with session.post(f"{base_url}/mcp/execute", json=payload) as response:
            result = await response.json()
            funding = result['result']
            hype_rate = funding.get('HYPE', 0)
            print(f"[OK] HYPE funding rate: {hype_rate:.4%}/hour")
        
        # Test 6: Place mock order
        payload = {
            "method": "place_order",
            "params": {
                "symbol": "HYPE",
                "side": "BUY",
                "size": 10,
                "price": 24.50,
                "order_type": "LIMIT"
            },
            "id": "test4"
        }
        async with session.post(f"{base_url}/mcp/execute", json=payload) as response:
            result = await response.json()
            order = result['result']
            print(f"[OK] Order placed: {order['order_id']}")
    
    print("="*40)
    print("All tests passed! Mock MCP server is working.")


if __name__ == "__main__":
    asyncio.run(quick_test())