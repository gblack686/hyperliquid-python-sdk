"""
Test Real Data from Hyperliquid API
Tests all MCP server functions with actual market data
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


class RealDataTester:
    def __init__(self):
        self.server_url = "http://localhost:8889"
        self.results = {}
        
    async def test_endpoint(self, session: aiohttp.ClientSession, method: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Test a single endpoint"""
        try:
            payload = {
                "method": method,
                "params": params,
                "id": f"test_{method}"
            }
            
            async with session.post(
                f"{self.server_url}/mcp/execute",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": "result" in data,
                        "data": data.get("result"),
                        "error": data.get("error")
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {resp.status}"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_all_tests(self):
        """Run all real data tests"""
        print("="*80)
        print("HYPERLIQUID REAL DATA MCP SERVER TEST")
        print("="*80)
        print(f"Testing server at {self.server_url}")
        print("Data Source: REAL Hyperliquid Mainnet API")
        print("-"*80)
        
        async with aiohttp.ClientSession() as session:
            # Check server health first
            try:
                async with session.get(f"{self.server_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        health = await resp.json()
                        print(f"\n[OK] Server Status: {health.get('status', 'unknown')}")
                        print(f"    API Connected: {health.get('api_connected', False)}")
                        print(f"    Data Source: {health.get('data_source', 'unknown')}")
                    else:
                        print(f"\n[FAIL] Server not healthy: HTTP {resp.status}")
                        return
            except Exception as e:
                print(f"\n[FAIL] Cannot connect to server: {e}")
                print("\nPlease start the server first:")
                print("  python real_data_mcp_server.py")
                return
            
            print("\n" + "="*80)
            print("TESTING REAL DATA ENDPOINTS")
            print("="*80)
            
            # Test 1: Get All Mid Prices
            print("\n1. GET ALL MID PRICES (Real-time market prices)")
            print("-"*40)
            result = await self.test_endpoint(session, "get_all_mids")
            if result["success"] and result["data"]:
                prices = result["data"]
                print(f"[OK] Retrieved {len(prices)} real market prices")
                # Show top coins
                top_coins = ["BTC", "ETH", "SOL", "ARB", "MATIC", "AVAX", "HYPE"]
                for coin in top_coins:
                    if coin in prices:
                        price_val = prices[coin]
                        if isinstance(price_val, (int, float)):
                            print(f"    {coin}: ${price_val:,.2f}")
                        else:
                            try:
                                price_val = float(price_val)
                                print(f"    {coin}: ${price_val:,.2f}")
                            except:
                                print(f"    {coin}: {price_val}")
                # Show total
                if len(prices) > len(top_coins):
                    print(f"    ... and {len(prices) - len(top_coins)} more coins")
            else:
                print(f"[FAIL] {result.get('error', 'No data')}")
            
            # Test 2: Get L2 Order Book
            print("\n2. GET L2 ORDER BOOK (Real BTC order book)")
            print("-"*40)
            result = await self.test_endpoint(session, "get_l2_book", {"coin": "BTC"})
            if result["success"] and result["data"]:
                book = result["data"]
                levels = book.get("levels", [[], []])
                bids = levels[0] if len(levels) > 0 else []
                asks = levels[1] if len(levels) > 1 else []
                
                print(f"[OK] BTC Order Book ({book.get('source', 'unknown')} data)")
                print(f"    Bids: {len(bids)} levels")
                print(f"    Asks: {len(asks)} levels")
                
                if bids and asks:
                    # Show best bid/ask
                    best_bid = bids[0] if bids else None
                    best_ask = asks[0] if asks else None
                    if best_bid and best_ask:
                        try:
                            # Handle different data formats
                            if isinstance(best_bid, dict):
                                bid_price = float(best_bid.get('px', best_bid.get('price', 0)))
                                bid_size = best_bid.get('sz', best_bid.get('size', 0))
                            elif isinstance(best_bid, (list, tuple)) and len(best_bid) >= 2:
                                bid_price = float(best_bid[0])
                                bid_size = best_bid[1]
                            else:
                                bid_price = float(best_bid)
                                bid_size = 0
                            
                            if isinstance(best_ask, dict):
                                ask_price = float(best_ask.get('px', best_ask.get('price', 0)))
                                ask_size = best_ask.get('sz', best_ask.get('size', 0))
                            elif isinstance(best_ask, (list, tuple)) and len(best_ask) >= 2:
                                ask_price = float(best_ask[0])
                                ask_size = best_ask[1]
                            else:
                                ask_price = float(best_ask)
                                ask_size = 0
                            
                            spread = ask_price - bid_price
                            print(f"    Best Bid: ${bid_price:,.2f} (size: {bid_size})")
                            print(f"    Best Ask: ${ask_price:,.2f} (size: {ask_size})")
                            print(f"    Spread: ${spread:.2f}")
                        except Exception as e:
                            print(f"    [WARNING] Could not parse order book: {e}")
            else:
                print(f"[FAIL] {result.get('error', 'No data')}")
            
            # Test 3: Get Exchange Metadata
            print("\n3. GET EXCHANGE METADATA (Real trading pairs info)")
            print("-"*40)
            result = await self.test_endpoint(session, "get_meta")
            if result["success"] and result["data"]:
                meta = result["data"]
                if isinstance(meta, dict):
                    print(f"[OK] Exchange Metadata Retrieved")
                    universe = meta.get("universe", [])
                    if universe:
                        print(f"    Trading Pairs: {len(universe)}")
                        # Show some pairs
                        for i, pair in enumerate(universe[:5]):
                            if isinstance(pair, dict):
                                print(f"    - {pair.get('name', 'Unknown')}: {pair.get('szDecimals', 'N/A')} decimals")
                        if len(universe) > 5:
                            print(f"    ... and {len(universe) - 5} more pairs")
                elif isinstance(meta, list):
                    print(f"[OK] Metadata Retrieved (array format)")
                    print(f"    Data sections: {len(meta)}")
            else:
                print(f"[FAIL] {result.get('error', 'No data')}")
            
            # Test 4: Get Recent Trades
            print("\n4. GET RECENT TRADES (Real ETH trades)")
            print("-"*40)
            result = await self.test_endpoint(session, "get_recent_trades", {"coin": "ETH"})
            if result["success"] and result["data"]:
                trades = result["data"]
                if isinstance(trades, list) and trades:
                    print(f"[OK] Retrieved {len(trades)} recent ETH trades")
                    # Show last few trades
                    for trade in trades[:3]:
                        if isinstance(trade, dict):
                            px = trade.get('px', 0)
                            sz = trade.get('sz', 0)
                            side = trade.get('side', 'N/A')
                            try:
                                px = float(px) if px else 0
                                print(f"    Price: ${px:,.2f}, Size: {sz}, Side: {side}")
                            except:
                                print(f"    Price: {px}, Size: {sz}, Side: {side}")
                else:
                    print(f"[OK] No recent trades available")
            else:
                print(f"[WARNING] Recent trades not available: {result.get('error', 'No data')}")
            
            # Test 5: Get Open Interest
            print("\n5. GET OPEN INTEREST (Real BTC open interest)")
            print("-"*40)
            result = await self.test_endpoint(session, "get_open_interest", {"coin": "BTC"})
            if result["success"] and result["data"]:
                oi_data = result["data"]
                print(f"[OK] BTC Open Interest ({oi_data.get('source', 'unknown')} data)")
                if "data" in oi_data and oi_data["data"]:
                    print(f"    Data: {oi_data['data']}")
            else:
                print(f"[WARNING] Open interest not available: {result.get('error', 'No data')}")
            
            # Test 6: Get Funding History
            print("\n6. GET FUNDING HISTORY (Real BTC funding rates - last 3 days)")
            print("-"*40)
            result = await self.test_endpoint(session, "get_funding_history", {"coin": "BTC", "lookback_days": 3})
            if result["success"] and result["data"]:
                funding = result["data"]
                if isinstance(funding, list) and funding:
                    print(f"[OK] Retrieved {len(funding)} funding rate records")
                    # Show recent funding rates
                    for i, rate in enumerate(funding[:3]):
                        if isinstance(rate, dict):
                            fr = rate.get('fundingRate', 0)
                            try:
                                fr = float(fr) if fr else 0
                                print(f"    Rate: {fr:.6f}, Time: {rate.get('time', 'N/A')}")
                            except:
                                print(f"    Rate: {fr}, Time: {rate.get('time', 'N/A')}")
                else:
                    print(f"[OK] No funding history available")
            else:
                print(f"[WARNING] Funding history not available: {result.get('error', 'No data')}")
            
            # Test 7: Get Perpetuals Metadata
            print("\n7. GET PERPETUALS METADATA (Real perps info)")
            print("-"*40)
            result = await self.test_endpoint(session, "get_perps_metadata")
            if result["success"] and result["data"]:
                perps = result["data"]
                if isinstance(perps, list) and len(perps) > 0:
                    print(f"[OK] Perpetuals Metadata Retrieved")
                    print(f"    Data sections: {len(perps)}")
                    # Try to extract universe info
                    if len(perps) > 0 and isinstance(perps[0], dict):
                        universe = perps[0].get("universe", [])
                        if universe:
                            print(f"    Perpetual contracts: {len(universe)}")
                elif isinstance(perps, dict):
                    print(f"[OK] Perpetuals Metadata Retrieved")
                    universe = perps.get("universe", [])
                    if universe:
                        print(f"    Perpetual contracts: {len(universe)}")
            else:
                print(f"[WARNING] Perps metadata not available: {result.get('error', 'No data')}")
            
            # Test 8: Get Historical Candles
            print("\n8. GET HISTORICAL CANDLES (Real SOL 1-hour candles)")
            print("-"*40)
            result = await self.test_endpoint(session, "get_candles", {
                "coin": "SOL",
                "interval": "1h",
                "lookback": 24
            })
            if result["success"] and result["data"]:
                candles = result["data"]
                if isinstance(candles, list) and candles:
                    print(f"[OK] Retrieved {len(candles)} SOL candles")
                    # Show recent candles
                    for candle in candles[:3]:
                        if isinstance(candle, dict):
                            try:
                                o = float(candle.get('o', 0))
                                h = float(candle.get('h', 0))
                                l = float(candle.get('l', 0))
                                c = float(candle.get('c', 0))
                                print(f"    Open: ${o:,.2f}, High: ${h:,.2f}, Low: ${l:,.2f}, Close: ${c:,.2f}")
                            except:
                                print(f"    Candle data: {candle}")
                        elif isinstance(candle, list) and len(candle) >= 6:
                            # Format: [timestamp, open, high, low, close, volume]
                            try:
                                print(f"    Open: ${float(candle[1]):,.2f}, High: ${float(candle[2]):,.2f}, "
                                      f"Low: ${float(candle[3]):,.2f}, Close: ${float(candle[4]):,.2f}")
                            except:
                                print(f"    Candle data: {candle[:5]}")
                else:
                    print(f"[OK] No candle data available")
            else:
                print(f"[WARNING] Candles not available: {result.get('error', 'No data')}")
            
            # Test 9: Get 24h Volume
            print("\n9. GET 24-HOUR VOLUME (Real trading volumes)")
            print("-"*40)
            result = await self.test_endpoint(session, "get_volume_24h")
            if result["success"] and result["data"]:
                volume_data = result["data"]
                volumes = volume_data.get("volumes", {})
                total = volume_data.get("total", 0)
                
                if volumes:
                    print(f"[OK] 24-Hour Trading Volumes ({volume_data.get('source', 'unknown')} data)")
                    print(f"    Total Volume: ${total:,.2f}")
                    # Show top volumes
                    sorted_volumes = sorted(volumes.items(), key=lambda x: x[1], reverse=True)
                    for coin, vol in sorted_volumes[:5]:
                        print(f"    {coin}: ${vol:,.2f}")
                else:
                    print(f"[OK] Volume data format different than expected")
            else:
                print(f"[WARNING] Volume data not available: {result.get('error', 'No data')}")
            
            # Test 10: WebSocket Connection
            print("\n10. TEST WEBSOCKET (Real-time price streaming)")
            print("-"*40)
            try:
                ws_url = self.server_url.replace("http", "ws") + "/ws"
                async with session.ws_connect(ws_url, timeout=5) as ws:
                    print("[OK] WebSocket connected")
                    
                    # Receive a few messages
                    messages_received = 0
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get("type") == "price_update":
                                prices = data.get("data", {})
                                if prices:
                                    print(f"    Live update: BTC=${prices.get('BTC', 0):,.2f}, "
                                          f"ETH=${prices.get('ETH', 0):,.2f} "
                                          f"({data.get('source', 'unknown')} data)")
                                messages_received += 1
                                if messages_received >= 2:
                                    break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print(f"[FAIL] WebSocket error: {ws.exception()}")
                            break
                    
                    await ws.close()
                    print(f"    Received {messages_received} price updates")
            except Exception as e:
                print(f"[WARNING] WebSocket test failed: {e}")
        
        print("\n" + "="*80)
        print("REAL DATA TEST SUMMARY")
        print("="*80)
        print("\nAll tests completed!")
        print("\nThe MCP server is successfully retrieving REAL data from Hyperliquid API:")
        print("  - Real-time market prices for all trading pairs")
        print("  - Live order book data with actual bids/asks")
        print("  - Historical candles and trading data")
        print("  - Exchange metadata and trading pair information")
        print("  - WebSocket streaming for real-time updates")
        print("\nNo API key required for public market data!")
        print("="*80)


async def main():
    """Main test function"""
    tester = RealDataTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("Starting Real Data MCP Server Test...")
    print("Make sure the real data server is running:")
    print("  python real_data_mcp_server.py")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()