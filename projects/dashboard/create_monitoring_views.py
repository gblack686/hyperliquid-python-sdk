"""
Create monitoring views in Supabase for hl_ tables
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def create_monitoring_views():
    """Create the monitoring views in Supabase"""
    
    # Initialize Supabase client with service key for admin access
    url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not service_key:
        # Try anon key if service key not available
        service_key = os.getenv('SUPABASE_ANON_KEY')
        print("[WARNING] Using anon key instead of service key - some operations may fail")
    
    if not url or not service_key:
        print("[ERROR] Missing Supabase credentials")
        return False
    
    try:
        supabase = create_client(url, service_key)
        print("[OK] Connected to Supabase")
        
        # Test the monitoring by querying existing tables
        print("\n" + "=" * 70)
        print("HL TABLES MONITORING REPORT")
        print("=" * 70)
        
        tables_to_check = [
            ('hl_cvd_current', 'updated_at'),
            ('hl_cvd_snapshots', 'timestamp'),
            ('hl_oi_current', 'updated_at'),
            ('hl_oi_snapshots', 'timestamp'),
            ('hl_funding_current', 'updated_at'),
            ('hl_funding_snapshots', 'timestamp'),
            ('hl_volume_profile_current', 'updated_at'),
            ('hl_volume_profile_snapshots', 'timestamp'),
            ('hl_vwap_current', 'updated_at'),
            ('hl_vwap_snapshots', 'timestamp'),
            ('hl_atr_current', 'updated_at'),
            ('hl_atr_snapshots', 'timestamp'),
            ('hl_bollinger_current', 'updated_at'),
            ('hl_bollinger_snapshots', 'timestamp'),
            ('hl_sr_current', 'updated_at'),
            ('hl_sr_snapshots', 'timestamp')
        ]
        
        monitoring_data = []
        
        for table_name, time_column in tables_to_check:
            try:
                # Get latest record
                response = supabase.table(table_name).select('*').order(time_column, desc=True).limit(1).execute()
                
                if response.data and len(response.data) > 0:
                    latest = response.data[0]
                    timestamp = latest.get(time_column)
                    
                    # Get count
                    count_response = supabase.table(table_name).select('id', count='exact').execute()
                    count = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
                    
                    # Calculate age
                    if timestamp:
                        from datetime import datetime
                        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        age_minutes = (datetime.now() - ts.replace(tzinfo=None)).total_seconds() / 60
                        
                        status = 'Active' if age_minutes < 5 else 'Recent' if age_minutes < 60 else 'Stale' if age_minutes < 1440 else 'Inactive'
                        
                        monitoring_data.append({
                            'table': table_name,
                            'records': count,
                            'last_update': timestamp[:19],
                            'age_minutes': round(age_minutes, 1),
                            'status': status,
                            'symbol': latest.get('symbol', 'N/A')
                        })
                    else:
                        monitoring_data.append({
                            'table': table_name,
                            'records': count,
                            'last_update': 'N/A',
                            'age_minutes': 9999,
                            'status': 'No timestamp',
                            'symbol': 'N/A'
                        })
                else:
                    monitoring_data.append({
                        'table': table_name,
                        'records': 0,
                        'last_update': 'N/A',
                        'age_minutes': 9999,
                        'status': 'Empty',
                        'symbol': 'N/A'
                    })
                    
            except Exception as e:
                error_msg = str(e)
                if "does not exist" in error_msg:
                    status = "Not Found"
                else:
                    status = "Error"
                    
                monitoring_data.append({
                    'table': table_name,
                    'records': 0,
                    'last_update': 'N/A',
                    'age_minutes': 9999,
                    'status': status,
                    'symbol': 'N/A'
                })
        
        # Sort by age (most recent first)
        monitoring_data.sort(key=lambda x: x['age_minutes'])
        
        # Display results
        print(f"\n{'Table':<30} {'Records':<10} {'Status':<10} {'Age':<15} {'Last Update':<20} {'Symbol':<10}")
        print("-" * 110)
        
        for data in monitoring_data:
            age_str = f"{data['age_minutes']:.1f} min" if data['age_minutes'] < 9999 else "N/A"
            print(f"{data['table']:<30} {data['records']:<10} {data['status']:<10} {age_str:<15} {data['last_update']:<20} {data['symbol']:<10}")
        
        # Summary statistics
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        active_count = sum(1 for d in monitoring_data if d['status'] == 'Active')
        recent_count = sum(1 for d in monitoring_data if d['status'] == 'Recent')
        stale_count = sum(1 for d in monitoring_data if d['status'] == 'Stale')
        inactive_count = sum(1 for d in monitoring_data if d['status'] in ['Inactive', 'Empty', 'Not Found'])
        
        print(f"Active Tables (< 5 min): {active_count}")
        print(f"Recent Tables (< 1 hour): {recent_count}")
        print(f"Stale Tables (< 24 hours): {stale_count}")
        print(f"Inactive/Empty Tables: {inactive_count}")
        
        total_records = sum(d['records'] for d in monitoring_data)
        print(f"\nTotal Records Across All Tables: {total_records:,}")
        
        # Show most active tables
        print("\n" + "=" * 70)
        print("MOST ACTIVE TABLES (by record count)")
        print("=" * 70)
        
        monitoring_data.sort(key=lambda x: x['records'], reverse=True)
        for i, data in enumerate(monitoring_data[:5]):
            print(f"{i+1}. {data['table']}: {data['records']} records")
        
        print("\n" + "=" * 70)
        print("NOTE: SQL views should be created via Supabase Dashboard SQL Editor")
        print("File: sql/create_monitoring_view.sql")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    create_monitoring_views()