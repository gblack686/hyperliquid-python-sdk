"""
Apply SQL migration to create monitoring views in Supabase
This script applies the monitoring views directly using Supabase Admin API
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

def apply_monitoring_views():
    """Apply the monitoring views using Supabase Admin API"""
    
    # Get credentials
    url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not service_key:
        print("[WARNING] SUPABASE_SERVICE_KEY not found. You'll need to apply the SQL manually.")
        print("\nTo apply the views manually:")
        print("1. Open your Supabase Dashboard")
        print("2. Go to SQL Editor")
        print("3. Copy and paste the contents of sql/create_monitoring_view.sql")
        print("4. Click 'Run' to execute the SQL")
        return False
    
    if not url:
        print("[ERROR] SUPABASE_URL not found")
        return False
    
    # Read the SQL file
    sql_file = "sql/create_monitoring_view.sql"
    if not os.path.exists(sql_file):
        print(f"[ERROR] SQL file not found: {sql_file}")
        return False
    
    with open(sql_file, 'r') as f:
        sql_content = f.read()
    
    # Parse the project ID from the URL
    # URL format: https://[project_id].supabase.co
    project_id = url.split('//')[1].split('.')[0]
    
    # Construct the Admin API endpoint
    admin_api_url = f"https://api.supabase.com/v1/projects/{project_id}/database/query"
    
    # Set up headers
    headers = {
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    # Prepare the request body
    body = {
        'query': sql_content
    }
    
    print(f"[INFO] Attempting to apply migration to project: {project_id}")
    
    try:
        response = requests.post(admin_api_url, headers=headers, json=body)
        
        if response.status_code == 200:
            print("[SUCCESS] Monitoring views created successfully!")
            return True
        else:
            print(f"[ERROR] Failed to apply migration. Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            # If Admin API fails, provide manual instructions
            print("\n" + "=" * 70)
            print("MANUAL APPLICATION REQUIRED")
            print("=" * 70)
            print("\nThe automated migration failed. Please apply manually:")
            print("\n1. Open Supabase Dashboard: https://app.supabase.com")
            print(f"2. Select your project: {project_id}")
            print("3. Navigate to SQL Editor (left sidebar)")
            print("4. Click 'New query'")
            print("5. Copy the contents of: sql/create_monitoring_view.sql")
            print("6. Paste into the SQL editor")
            print("7. Click 'Run' to execute")
            print("\nThe SQL file creates two views:")
            print("  - hl_monitoring_dashboard: Shows latest record from each hl_ table")
            print("  - hl_table_summary: Shows table statistics and status")
            print("=" * 70)
            
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request failed: {e}")
        return False

if __name__ == "__main__":
    success = apply_monitoring_views()
    
    if success:
        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("\n1. Test the views by running:")
        print("   python test_monitoring_views.py")
        print("\n2. View the monitoring dashboard:")
        print("   streamlit run app_monitoring.py")
        print("\n3. Check the simplified dashboard:")
        print("   streamlit run app_simplified.py")
        print("=" * 70)