"""
Test All 84xx MCP Servers
Tests the new MCP servers on ports 8401-8403
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any


class MCP84xxTester:
    def __init__(self):
        self.servers = {
            "Kukapay Info (8401)": {
                "url": "http://localhost:8401",
                "tests": ["get_market_summary", "analyze_positions"]
            },
            "Whale Tracker (8402)": {
                "url": "http://localhost:8402", 
                "tests": ["get_whale_trades", "get_flow_analysis"]
            },
            "Advanced Trading (8403)": {
                "url": "http://localhost:8403",
                "tests": ["get_market_prices", "get_technical_indicators", "get_trade_signals"]
            }
        }
    
    async def test_server(self, name: str, config: Dict[str, Any], session: aiohttp.ClientSession):
        """Test a single server"""
        url = config["url"]
        print(f"\n{'='*60}")
        print(f"Testing {name}")
        print(f"URL: {url}")
        print('='*60)
        
        # Check health
        try:
            async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print(f"[OK] Server healthy: {health.get('status')}")
                else:
                    print(f"[FAIL] Server unhealthy: HTTP {resp.status}")
                    return
        except Exception as e:
            print(f"[FAIL] Cannot connect: {e}")
            print(f"      Start server with: python python/{name.split()[0].lower()}_server.py")
            return
        
        # Get server info
        try:
            async with session.get(f"{url}/", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    info = await resp.json()
                    print(f"[OK] Server: {info.get('name')}")
                    print(f"     Features: {', '.join(info.get('features', []))}")
                    print(f"     Data Source: {info.get('data_source')}")
        except Exception as e:
            print(f"[WARNING] Cannot get server info: {e}")
        
        # Test specific endpoints
        for test_method in config["tests"]:
            await self.test_endpoint(url, test_method, session)
    
    async def test_endpoint(self, url: str, method: str, session: aiohttp.ClientSession):
        """Test a specific endpoint"""
        print(f"\nTesting {method}...")
        
        # Prepare parameters based on method
        params = {}
        if method == "analyze_positions":
            params = {"address": "0x1234567890abcdef1234567890abcdef12345678"}
        elif method == "get_whale_trades":
            params = {"min_usd": 50000, "lookback_minutes": 60}
        elif method == "get_flow_analysis":
            params = {"coin": "BTC", "lookback_hours": 24}
        elif method == "get_technical_indicators":
            params = {"coin": "ETH", "indicators": ["RSI", "MACD"]}
        elif method == "get_trade_signals":
            params = {"coin": "SOL", "strategy": "trend_following"}
        
        payload = {
            "method": method,
            "params": params,
            "id": f"test_{method}"
        }
        
        try:
            async with session.post(
                f"{url}/mcp/execute",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "result" in data:
                        result = data["result"]
                        print(f"  [OK] {method} successful")
                        
                        # Show sample of results
                        if isinstance(result, dict):
                            if "prices" in result and isinstance(result["prices"], dict):
                                # Show some prices
                                prices = result["prices"]
                                sample_coins = ["BTC", "ETH", "SOL", "HYPE"]
                                for coin in sample_coins:
                                    if coin in prices:
                                        price = prices[coin]
                                        try:
                                            print(f"       {coin}: ${float(price):,.2f}")
                                        except:
                                            print(f"       {coin}: {price}")
                            elif "whale_trades" in result:
                                trades = result["whale_trades"]
                                print(f"       Found {len(trades)} whale trades")
                                if trades:
                                    t = trades[0]
                                    print(f"       Example: {t.get('coin')} {t.get('side')} ${t.get('value_usd', 0):,.0f}")
                            elif "indicators" in result:
                                indicators = result["indicators"]
                                for ind_name, ind_data in indicators.items():
                                    if isinstance(ind_data, dict):
                                        print(f"       {ind_name}: {ind_data.get('value', ind_data.get('signal', 'N/A'))}")
                            elif "signals" in result:
                                signals = result["signals"]
                                if signals:
                                    s = signals[0]
                                    print(f"       Signal: {s.get('type')} - {s.get('reason', 'N/A')}")
                            elif "flow_ratio" in result:
                                print(f"       Buy/Sell Ratio: {result.get('flow_ratio', 0):.2f}")
                                print(f"       Sentiment: {result.get('sentiment', 'neutral')}")
                            elif "total_coins" in result:
                                print(f"       Total Coins: {result.get('total_coins', 0)}")
                                print(f"       Market Status: {result.get('market_status', 'unknown')}")
                            else:
                                # Show first few keys
                                keys = list(result.keys())[:3]
                                for key in keys:
                                    print(f"       {key}: {result[key]}")
                    else:
                        error = data.get("error", {})
                        print(f"  [FAIL] {method}: {error.get('message', 'Unknown error')}")
                else:
                    print(f"  [FAIL] HTTP {resp.status}")
        except Exception as e:
            print(f"  [FAIL] {method}: {e}")


async def start_servers():
    """Start all servers in background"""
    import subprocess
    import sys
    
    servers = [
        ("kukapay_info_server.py", 8401),
        ("whale_tracker_server.py", 8402),
        ("advanced_trading_server.py", 8403)
    ]
    
    print("Starting servers...")
    processes = []
    
    for server_file, port in servers:
        try:
            # Start server in background
            cmd = [sys.executable, f"python/{server_file}"]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            processes.append((server_file, process))
            print(f"  Started {server_file} on port {port}")
        except Exception as e:
            print(f"  Failed to start {server_file}: {e}")
    
    # Wait for servers to initialize
    await asyncio.sleep(3)
    return processes


async def main():
    """Main test function"""
    print("="*60)
    print("MCP 84xx SERVERS TEST")
    print("="*60)
    print("Testing new MCP servers on ports 8401-8403")
    print("These servers use REAL Hyperliquid data")
    
    # Option to start servers
    print("\nDo you want to start the servers automatically? (y/n)")
    # For automated testing, assume no
    auto_start = False
    
    if auto_start:
        processes = await start_servers()
    else:
        print("\nMake sure servers are running:")
        print("  python python/kukapay_info_server.py")
        print("  python python/whale_tracker_server.py")
        print("  python python/advanced_trading_server.py")
    
    # Run tests
    tester = MCP84xxTester()
    
    async with aiohttp.ClientSession() as session:
        for name, config in tester.servers.items():
            await tester.test_server(name, config, session)
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("\nAll 84xx series MCP servers have been created:")
    print("  - Kukapay Info (8401): User analytics and positions")
    print("  - Whale Tracker (8402): Large trade monitoring")
    print("  - Advanced Trading (8403): Full trading toolkit")
    print("\nThese servers use REAL Hyperliquid market data!")
    print("No API key required for public market data.")
    print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed: {e}")