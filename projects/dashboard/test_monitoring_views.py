"""
Test script to verify monitoring views in Supabase
Run this after applying the SQL views to confirm they work
"""

import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

def test_monitoring_views():
    """Test the monitoring views if they exist"""
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("[ERROR] Missing Supabase credentials")
        return False
    
    try:
        supabase = create_client(url, key)
        print("[OK] Connected to Supabase")
        print("=" * 70)
        
        # Test 1: Try to query hl_monitoring_dashboard view
        print("\nTEST 1: Query hl_monitoring_dashboard view")
        print("-" * 40)
        
        try:
            response = supabase.table('hl_monitoring_dashboard').select('*').execute()
            
            if response.data:
                print(f"[SUCCESS] View returned {len(response.data)} indicators")
                print("\nIndicator Status:")
                for row in response.data[:5]:  # Show first 5
                    indicator = row.get('indicator_type', 'Unknown')
                    symbol = row.get('symbol', 'N/A')
                    value = row.get('value', 0)
                    signal = row.get('signal', 'N/A')
                    minutes = row.get('minutes_ago', 0)
                    
                    if minutes < 5:
                        status = "ACTIVE"
                    elif minutes < 60:
                        status = "RECENT"
                    elif minutes < 1440:
                        status = "STALE"
                    else:
                        status = "INACTIVE"
                    
                    print(f"  {indicator:20} {symbol:6} Value: {value:10.2f} Signal: {signal:10} [{status}]")
            else:
                print("[INFO] View exists but returned no data")
                
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg:
                print("[WARNING] View 'hl_monitoring_dashboard' does not exist yet")
                print("Please apply the SQL migration from sql/create_monitoring_view.sql")
            else:
                print(f"[ERROR] {error_msg}")
        
        # Test 2: Try to query hl_table_summary view
        print("\n" + "=" * 70)
        print("TEST 2: Query hl_table_summary view")
        print("-" * 40)
        
        try:
            response = supabase.table('hl_table_summary').select('*').execute()
            
            if response.data:
                print(f"[SUCCESS] View returned {len(response.data)} tables")
                print("\nTable Summary:")
                
                active_count = 0
                total_records = 0
                
                for row in response.data:
                    table = row.get('table_name', 'Unknown')
                    count = row.get('record_count', 0)
                    status = row.get('status', 'Unknown')
                    minutes = row.get('minutes_since_update', 0)
                    
                    if status == 'Active':
                        active_count += 1
                    total_records += count
                    
                    print(f"  {table:30} Records: {count:6} Status: {status:10} Age: {minutes:.1f} min")
                
                print(f"\nSummary:")
                print(f"  Active Tables: {active_count}/{len(response.data)}")
                print(f"  Total Records: {total_records:,}")
            else:
                print("[INFO] View exists but returned no data")
                
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg:
                print("[WARNING] View 'hl_table_summary' does not exist yet")
                print("Please apply the SQL migration from sql/create_monitoring_view.sql")
            else:
                print(f"[ERROR] {error_msg}")
        
        print("\n" + "=" * 70)
        print("MONITORING VIEWS TEST COMPLETE")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to connect to Supabase: {e}")
        return False

if __name__ == "__main__":
    test_monitoring_views()