"""
Comprehensive Test Script for All MCP Servers
Tests Python and JavaScript MCP servers
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))


class MCPServerTester:
    def __init__(self):
        self.servers = {
            "Mock Server": "http://127.0.0.1:8888",
            "Python Info": "http://127.0.0.1:8001",
            "Python Whale": "http://127.0.0.1:8002",
            "Python Midodimori": "http://127.0.0.1:8003",
            "JS Mektigboy": "http://127.0.0.1:8004",
            "JS Balthazar": "http://127.0.0.1:8005",
            "JS 6rz6": "http://127.0.0.1:8006"
        }
        self.results = {}
        
    async def test_server(self, name: str, url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test a single MCP server"""
        result = {
            "name": name,
            "url": url,
            "status": "offline",
            "health": None,
            "tools": None,
            "test_results": [],
            "error": None
        }
        
        try:
            # Test root endpoint
            print(f"\nTesting {name} at {url}...")
            
            async with session.get(f"{url}/", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["status"] = "online"
                    result["health"] = data
                    print(f"  [OK] Server online: {data.get('name', 'Unknown')}")
                else:
                    result["error"] = f"HTTP {resp.status}"
                    print(f"  [FAIL] HTTP {resp.status}")
                    return result
                    
        except asyncio.TimeoutError:
            result["error"] = "Connection timeout"
            print(f"  [FAIL] Connection timeout")
            return result
        except Exception as e:
            result["error"] = str(e)
            print(f"  [FAIL] Connection error: {e}")
            return result
        
        # Test tools endpoint
        try:
            async with session.get(f"{url}/mcp/tools", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    tools = await resp.json()
                    result["tools"] = tools.get("tools", [])
                    print(f"  [OK] Found {len(result['tools'])} tools")
                    
                    # Display first 3 tools
                    for i, tool in enumerate(result["tools"][:3]):
                        print(f"    - {tool.get('name', 'unknown')}: {tool.get('description', 'No description')}")
                    if len(result["tools"]) > 3:
                        print(f"    ... and {len(result['tools']) - 3} more")
        except Exception as e:
            print(f"  [WARNING] Could not fetch tools: {e}")
        
        # Test get_all_mids if available
        try:
            payload = {
                "method": "get_all_mids",
                "params": {},
                "id": "test_1"
            }
            
            async with session.post(
                f"{url}/mcp/execute",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "result" in data and data["result"]:
                        mids = data["result"]
                        if isinstance(mids, dict) and mids:
                            # Show first few prices
                            symbols = list(mids.keys())[:3]
                            prices = [f"{sym}=${mids[sym]:.2f}" for sym in symbols if sym in mids]
                            print(f"  [OK] Mid prices: {', '.join(prices)}")
                            result["test_results"].append({
                                "test": "get_all_mids",
                                "success": True,
                                "sample": prices
                            })
                        else:
                            print(f"  [OK] get_all_mids endpoint working (no data)")
                            result["test_results"].append({
                                "test": "get_all_mids",
                                "success": True,
                                "note": "No data returned"
                            })
                    elif "error" in data:
                        print(f"  [WARNING] get_all_mids error: {data['error'].get('message', 'Unknown')}")
                        result["test_results"].append({
                            "test": "get_all_mids",
                            "success": False,
                            "error": data['error'].get('message', 'Unknown')
                        })
        except Exception as e:
            print(f"  [WARNING] Could not test get_all_mids: {e}")
        
        return result
    
    async def test_all_servers(self):
        """Test all configured MCP servers"""
        print("="*60)
        print("MCP SERVERS COMPREHENSIVE TEST")
        print("="*60)
        print(f"Testing {len(self.servers)} servers...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for name, url in self.servers.items():
                tasks.append(self.test_server(name, url, session))
            
            results = await asyncio.gather(*tasks)
            
            for i, (name, _) in enumerate(self.servers.items()):
                self.results[name] = results[i]
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        online_count = sum(1 for r in self.results.values() if r["status"] == "online")
        total_count = len(self.results)
        
        print(f"\nServers Online: {online_count}/{total_count}")
        print("\nServer Status:")
        
        for name, result in self.results.items():
            status_symbol = "[OK]" if result["status"] == "online" else "[FAIL]"
            tools_count = len(result["tools"]) if result["tools"] else 0
            
            print(f"  {status_symbol} {name:20} - ", end="")
            
            if result["status"] == "online":
                print(f"Online ({tools_count} tools)")
            else:
                print(f"Offline - {result['error']}")
        
        # Recommendations
        print("\n" + "="*60)
        print("RECOMMENDATIONS")
        print("="*60)
        
        if online_count == 0:
            print("\n[!] No servers are running. Start them with:")
            print("    1. Python servers: cd mcp && venv\\Scripts\\python.exe python_mcp_server.py")
            print("    2. Mock server: cd mcp && venv\\Scripts\\python.exe start_mock_server.py")
            print("    3. JavaScript servers: cd mcp/javascript/mektigboy && npm start")
        elif online_count < total_count:
            print("\n[!] Some servers are offline. To start missing servers:")
            for name, result in self.results.items():
                if result["status"] == "offline":
                    port = result["url"].split(":")[-1]
                    if "Python" in name:
                        print(f"    {name}: Check Python server on port {port}")
                    elif "JS" in name:
                        print(f"    {name}: Check JavaScript server on port {port}")
                    elif "Mock" in name:
                        print(f"    {name}: cd mcp && venv\\Scripts\\python.exe start_mock_server.py")
        else:
            print("\n[OK] All servers are online and operational!")
            print("\nYou can now:")
            print("  1. Use the mock server (port 8888) for testing without API keys")
            print("  2. Configure real API keys in mcp/.env for production servers")
            print("  3. Integrate these servers with your trading applications")
        
        # Save results to file
        self.save_results()
    
    def save_results(self):
        """Save test results to JSON file"""
        output = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(self.results),
                "online": sum(1 for r in self.results.values() if r["status"] == "online"),
                "offline": sum(1 for r in self.results.values() if r["status"] == "offline")
            },
            "servers": self.results
        }
        
        with open("mcp_test_results.json", "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\n[OK] Test results saved to mcp_test_results.json")


async def main():
    """Main test function"""
    tester = MCPServerTester()
    await tester.test_all_servers()


if __name__ == "__main__":
    print("Starting MCP Server Tests...")
    print("Make sure servers are running before testing.")
    print("To start mock server: cd mcp && venv\\Scripts\\python.exe start_mock_server.py")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()