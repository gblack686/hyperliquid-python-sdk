"""
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
    print("\n1. Testing Mock Server (port 8888)...")
    async with MCPTestClient("http://127.0.0.1:8888") as client:
        await client.test_server()
    
    # Test Python MCP server
    print("\n2. Testing Python MCP Server (port 8001)...")
    async with MCPTestClient("http://127.0.0.1:8001") as client:
        await client.test_server()


if __name__ == "__main__":
    asyncio.run(main())
