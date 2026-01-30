"""
Test CVD System Components
"""
import asyncio
import time
import os
import json
import websockets
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def test_supabase_connection():
    """Test Supabase connection"""
    print("\n[TEST 1] Testing Supabase Connection...")
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            print("  ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
            return False
            
        supabase = create_client(supabase_url, supabase_key)
        
        # Test query
        result = supabase.table('hl_cvd_current').select("*").execute()
        print(f"  SUCCESS: Connected to Supabase")
        print(f"  Found {len(result.data)} records in hl_cvd_current")
        
        for record in result.data:
            print(f"    - {record['symbol']}: CVD={record['cvd']}, Last Update={record['updated_at']}")
        
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

async def test_websocket_connection():
    """Test WebSocket connection to Hyperliquid"""
    print("\n[TEST 2] Testing WebSocket Connection...")
    try:
        ws_url = "wss://api.hyperliquid.xyz/ws"
        trades_received = 0
        
        async with websockets.connect(ws_url) as ws:
            print(f"  SUCCESS: Connected to {ws_url}")
            
            # Subscribe to BTC trades
            subscribe_msg = {
                "method": "subscribe",
                "subscription": {"type": "trades", "coin": "BTC"}
            }
            await ws.send(json.dumps(subscribe_msg))
            print("  Subscribed to BTC trades")
            
            # Listen for 3 seconds
            start = time.time()
            while time.time() - start < 3:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    data = json.loads(message)
                    if 'data' in data:
                        trades_received += len(data.get('data', []))
                except asyncio.TimeoutError:
                    continue
            
            print(f"  Received {trades_received} trades in 3 seconds")
            return trades_received > 0
            
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def test_cvd_calculator_import():
    """Test if CVD calculator can be imported"""
    print("\n[TEST 3] Testing CVD Calculator Import...")
    try:
        from cvd_supabase_integration import CVDSupabaseCalculator
        calc = CVDSupabaseCalculator(symbols=['BTC'])
        print("  SUCCESS: CVD Calculator initialized")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def test_monitor_server_import():
    """Test if monitor server can be imported"""
    print("\n[TEST 4] Testing Monitor Server Import...")
    try:
        from cvd_monitor_server import app
        print("  SUCCESS: Monitor server app created")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

async def test_cvd_calculation():
    """Test actual CVD calculation"""
    print("\n[TEST 5] Testing CVD Calculation (5 seconds)...")
    try:
        from cvd_supabase_integration import CVDSupabaseCalculator
        
        calc = CVDSupabaseCalculator(symbols=['BTC'])
        calc.running = True
        
        # Run tasks
        listen_task = asyncio.create_task(calc.listen_to_trades())
        save_task = asyncio.create_task(calc.periodic_save())
        
        # Wait 5 seconds
        await asyncio.sleep(5)
        
        # Stop
        calc.running = False
        
        # Cancel tasks
        listen_task.cancel()
        save_task.cancel()
        
        try:
            await listen_task
            await save_task
        except asyncio.CancelledError:
            pass
        
        # Check results
        data = calc.get_latest_data()
        
        if 'BTC' in data:
            cvd = data['BTC']['cvd']
            trades = data['BTC']['trade_count']
            print(f"  SUCCESS: CVD calculated")
            print(f"  BTC: {trades} trades, CVD={cvd:.2f}")
            return True
        else:
            print("  WARNING: No trades received in 5 seconds")
            return False
            
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_in_supabase():
    """Check if new data is in Supabase"""
    print("\n[TEST 6] Checking Latest Data in Supabase...")
    try:
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        
        # Get latest snapshots
        result = supabase.table('hl_cvd_snapshots')\
            .select("*")\
            .order('timestamp', desc=True)\
            .limit(5)\
            .execute()
            
        print(f"  Found {len(result.data)} recent snapshots")
        
        if result.data:
            latest = result.data[0]
            print(f"  Latest: {latest['symbol']} at {latest['timestamp']}")
            print(f"    CVD={latest['cvd']}, Trades={latest['trade_count']}")
            
        return len(result.data) > 0
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

async def main():
    print("="*60)
    print("CVD SYSTEM DIAGNOSTIC TESTS")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Run tests
    results.append(("Supabase Connection", test_supabase_connection()))
    results.append(("WebSocket Connection", await test_websocket_connection()))
    results.append(("CVD Calculator Import", test_cvd_calculator_import()))
    results.append(("Monitor Server Import", test_monitor_server_import()))
    results.append(("CVD Calculation", await test_cvd_calculation()))
    results.append(("Data in Supabase", test_data_in_supabase()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED - System is ready to run!")
        print("\nTo start the system:")
        print("  1. Run: python cvd_supabase_integration.py")
        print("  2. Run: python cvd_monitor_server.py")
        print("  3. Open: http://localhost:8001")
    else:
        print("SOME TESTS FAILED - Check the errors above")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())