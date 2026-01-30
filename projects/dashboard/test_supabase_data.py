"""
Test Supabase data streaming and verify all tables
"""

import os
import sys
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import json

load_dotenv()

def test_supabase_connection():
    """Test Supabase connection and data flow"""
    
    print("=" * 70)
    print("SUPABASE DATA STREAMING TEST")
    print("=" * 70)
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("[ERROR] Missing Supabase credentials in .env file")
        return False
    
    try:
        supabase = create_client(url, key)
        print("[OK] Supabase client initialized")
    except Exception as e:
        print(f"[ERROR] Failed to create Supabase client: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("CHECKING DATA TABLES")
    print("=" * 70)
    
    # Tables to check
    tables_to_check = [
        ('hl_cvd_current', 'CVD Current Data'),
        ('hl_cvd_snapshots', 'CVD Historical Snapshots'),
        ('hl_oi_current', 'Open Interest Current'),
        ('hl_oi_snapshots', 'Open Interest Snapshots'),
        ('hl_funding_current', 'Funding Rate Current'),
        ('hl_funding_snapshots', 'Funding Rate Snapshots'),
        ('hl_volume_profile_current', 'Volume Profile Current'),
        ('hl_volume_profile_snapshots', 'Volume Profile Snapshots'),
        ('trading_dash_indicators', 'Trading Dashboard Indicators'),
        ('trading_dash_trades', 'Trading Dashboard Trades'),
        ('trading_dash_account', 'Trading Dashboard Account'),
        ('trading_dash_confluence', 'Trading Dashboard Confluence')
    ]
    
    results = {}
    
    for table_name, description in tables_to_check:
        print(f"\nChecking {description} ({table_name})...")
        print("-" * 50)
        
        try:
            # Get recent data
            response = supabase.table(table_name).select("*").limit(5).order('timestamp', desc=True).execute()
            
            if response.data:
                count = len(response.data)
                print(f"  [OK] Found {count} recent records")
                
                # Check if data is recent (within last hour)
                if 'timestamp' in response.data[0]:
                    latest_timestamp = response.data[0]['timestamp']
                    latest_dt = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
                    now = datetime.now()
                    time_diff = now - latest_dt.replace(tzinfo=None)
                    
                    if time_diff < timedelta(hours=1):
                        print(f"  [OK] Latest data is {time_diff.seconds // 60} minutes old")
                    else:
                        print(f"  [WARNING] Latest data is {time_diff.days} days, {time_diff.seconds // 3600} hours old")
                
                # Show sample data for CVD
                if 'cvd' in table_name:
                    sample = response.data[0]
                    print(f"  Sample CVD Data:")
                    print(f"    - Symbol: {sample.get('symbol', 'N/A')}")
                    print(f"    - CVD: {sample.get('cvd', 'N/A')}")
                    print(f"    - Buy Volume: {sample.get('buy_volume', 'N/A')}")
                    print(f"    - Sell Volume: {sample.get('sell_volume', 'N/A')}")
                    print(f"    - Signal: {sample.get('signal', 'N/A')}")
                
                results[table_name] = 'OK'
            else:
                print(f"  [WARNING] No data found in table")
                results[table_name] = 'EMPTY'
                
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                print(f"  [ERROR] Table does not exist")
                results[table_name] = 'NOT_FOUND'
            else:
                print(f"  [ERROR] {e}")
                results[table_name] = 'ERROR'
    
    print("\n" + "=" * 70)
    print("TESTING REAL-TIME DATA INSERTION")
    print("=" * 70)
    
    # Test inserting data into trading_dash_indicators
    try:
        test_data = {
            "symbol": "TEST",
            "timeframe": "1m",
            "indicator_name": "test_indicator",
            "indicator_value": {"value": 123.45, "signal": "TEST"},
            "timestamp": datetime.now().isoformat()
        }
        
        print("\nInserting test data into trading_dash_indicators...")
        response = supabase.table("trading_dash_indicators").insert(test_data).execute()
        
        if response.data:
            print("  [OK] Test data inserted successfully")
            
            # Try to read it back
            read_response = supabase.table("trading_dash_indicators")\
                .select("*")\
                .eq("symbol", "TEST")\
                .execute()
            
            if read_response.data:
                print("  [OK] Test data retrieved successfully")
                
                # Clean up test data
                delete_response = supabase.table("trading_dash_indicators")\
                    .delete()\
                    .eq("symbol", "TEST")\
                    .execute()
                print("  [OK] Test data cleaned up")
            else:
                print("  [WARNING] Could not retrieve test data")
        else:
            print("  [ERROR] Failed to insert test data")
            
    except Exception as e:
        print(f"  [ERROR] Data insertion test failed: {e}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    ok_count = sum(1 for v in results.values() if v == 'OK')
    empty_count = sum(1 for v in results.values() if v == 'EMPTY')
    not_found_count = sum(1 for v in results.values() if v == 'NOT_FOUND')
    error_count = sum(1 for v in results.values() if v == 'ERROR')
    
    print(f"\nTables with data: {ok_count}/{len(results)}")
    print(f"Empty tables: {empty_count}")
    print(f"Missing tables: {not_found_count}")
    print(f"Errors: {error_count}")
    
    if ok_count > 0:
        print("\n[SUCCESS] Supabase is receiving data!")
    else:
        print("\n[WARNING] No data found in Supabase tables")
    
    print("\n" + "=" * 70)
    
    return ok_count > 0

if __name__ == "__main__":
    test_supabase_connection()