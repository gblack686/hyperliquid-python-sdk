"""
Comprehensive test suite for Hyperliquid Trading Dashboard
"""

import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
from supabase import create_client
from dotenv import load_dotenv
import subprocess
import requests

load_dotenv()

class DashboardTestSuite:
    def __init__(self):
        self.test_results = {}
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.supabase = None
        
        if self.supabase_url and self.supabase_key:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
    
    def print_header(self, title):
        print("\n" + "=" * 70)
        print(f" {title}")
        print("=" * 70)
    
    def print_result(self, test_name, passed, details=""):
        status = "[PASS]" if passed else "[FAIL]"
        self.test_results[test_name] = passed
        print(f"  {status} {test_name}")
        if details:
            print(f"        {details}")
    
    def test_environment(self):
        """Test 1: Environment and Dependencies"""
        self.print_header("TEST 1: ENVIRONMENT CHECK")
        
        # Check Python version
        python_version = sys.version.split()[0]
        self.print_result(
            "Python Version", 
            sys.version_info >= (3, 8),
            f"Version: {python_version}"
        )
        
        # Check required environment variables
        env_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
        for var in env_vars:
            value = os.getenv(var)
            self.print_result(
                f"Environment: {var}",
                value is not None,
                "Set" if value else "Missing"
            )
        
        # Check required packages
        packages = ['streamlit', 'supabase', 'pandas', 'plotly', 'websockets']
        for package in packages:
            try:
                __import__(package)
                self.print_result(f"Package: {package}", True, "Installed")
            except ImportError:
                self.print_result(f"Package: {package}", False, "Not installed")
    
    def test_supabase_connection(self):
        """Test 2: Supabase Connection and Tables"""
        self.print_header("TEST 2: SUPABASE CONNECTION")
        
        if not self.supabase:
            self.print_result("Supabase Client", False, "Failed to initialize")
            return
        
        self.print_result("Supabase Client", True, "Initialized")
        
        # Test tables
        tables = [
            'hl_cvd_current',
            'hl_cvd_snapshots',
            'hl_oi_current',
            'hl_oi_snapshots',
            'trading_dash_indicators'
        ]
        
        for table in tables:
            try:
                response = self.supabase.table(table).select("*").limit(1).execute()
                has_data = len(response.data) > 0 if response.data else False
                self.print_result(
                    f"Table: {table}",
                    True,
                    f"{'Has data' if has_data else 'Empty but accessible'}"
                )
            except Exception as e:
                error_msg = str(e)
                if "does not exist" in error_msg:
                    self.print_result(f"Table: {table}", False, "Does not exist")
                else:
                    self.print_result(f"Table: {table}", False, f"Error: {error_msg[:50]}")
    
    def test_cvd_data(self):
        """Test 3: CVD Data Verification"""
        self.print_header("TEST 3: CVD DATA VERIFICATION")
        
        if not self.supabase:
            self.print_result("CVD Data Check", False, "No Supabase connection")
            return
        
        # Check CVD snapshots
        try:
            response = self.supabase.table('hl_cvd_snapshots')\
                .select("*")\
                .order('timestamp', desc=True)\
                .limit(10)\
                .execute()
            
            if response.data:
                latest = response.data[0]
                cvd_value = latest.get('cvd', 0)
                symbol = latest.get('symbol', 'Unknown')
                timestamp = latest.get('timestamp', '')
                
                self.print_result(
                    "CVD Snapshots",
                    True,
                    f"Latest: {symbol} CVD={cvd_value:.2f}"
                )
                
                # Check data freshness
                if timestamp:
                    ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    age = datetime.now() - ts.replace(tzinfo=None)
                    is_fresh = age < timedelta(hours=24)
                    self.print_result(
                        "CVD Data Freshness",
                        is_fresh,
                        f"Age: {age.total_seconds() / 3600:.1f} hours"
                    )
            else:
                self.print_result("CVD Snapshots", False, "No data found")
                
        except Exception as e:
            self.print_result("CVD Data Check", False, str(e)[:100])
    
    def test_dashboard_endpoints(self):
        """Test 4: Dashboard HTTP Endpoints"""
        self.print_header("TEST 4: DASHBOARD ENDPOINTS")
        
        endpoints = [
            ("Enhanced Dashboard", "http://localhost:8501"),
            ("Simplified Dashboard", "http://localhost:8502"),
            ("Charts Dashboard", "http://localhost:8503")
        ]
        
        for name, url in endpoints:
            try:
                response = requests.get(url, timeout=5)
                self.print_result(
                    name,
                    response.status_code == 200,
                    f"Status: {response.status_code}"
                )
            except requests.exceptions.ConnectionError:
                self.print_result(name, False, "Not running")
            except requests.exceptions.Timeout:
                self.print_result(name, False, "Timeout")
            except Exception as e:
                self.print_result(name, False, str(e)[:50])
    
    def test_indicator_files(self):
        """Test 5: Indicator Files"""
        self.print_header("TEST 5: INDICATOR FILES")
        
        indicator_files = [
            'indicators/cvd.py',
            'indicators/open_interest.py',
            'indicators/funding_rate.py',
            'indicators/vwap.py',
            'indicators/bollinger_bands.py',
            'indicators/volume_profile.py',
            'indicators/atr.py',
            'indicators/liquidations.py'
        ]
        
        for file in indicator_files:
            exists = os.path.exists(file)
            if exists:
                size = os.path.getsize(file)
                self.print_result(
                    f"File: {file}",
                    True,
                    f"Size: {size} bytes"
                )
            else:
                self.print_result(f"File: {file}", False, "Not found")
    
    def test_cvd_integration(self):
        """Test 6: CVD Integration in Manager"""
        self.print_header("TEST 6: CVD INTEGRATION")
        
        # Check if CVD is in indicator_manager.py
        manager_file = "indicator_manager.py"
        if os.path.exists(manager_file):
            with open(manager_file, 'r') as f:
                content = f.read()
                
            checks = [
                ("CVD Import", "from indicators.cvd import CVDIndicator" in content),
                ("CVD in defaults", "'cvd'" in content),
                ("CVD Initialization", "CVDIndicator" in content)
            ]
            
            for check_name, passed in checks:
                self.print_result(check_name, passed)
        else:
            self.print_result("Indicator Manager File", False, "Not found")
    
    def test_real_time_data(self):
        """Test 7: Real-time Data Flow"""
        self.print_header("TEST 7: REAL-TIME DATA FLOW")
        
        if not self.supabase:
            self.print_result("Real-time Test", False, "No Supabase connection")
            return
        
        # Insert test record
        test_record = {
            "symbol": "TEST_RT",
            "timeframe": "1m",
            "indicator_name": "test_realtime",
            "indicator_value": {"value": 999.99, "timestamp": datetime.now().isoformat()},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Insert
            insert_response = self.supabase.table("trading_dash_indicators")\
                .insert(test_record).execute()
            
            if insert_response.data:
                self.print_result("Insert Test Data", True, "Record inserted")
                
                # Read back
                read_response = self.supabase.table("trading_dash_indicators")\
                    .select("*")\
                    .eq("symbol", "TEST_RT")\
                    .execute()
                
                if read_response.data:
                    self.print_result("Read Test Data", True, f"Found {len(read_response.data)} records")
                    
                    # Clean up
                    delete_response = self.supabase.table("trading_dash_indicators")\
                        .delete()\
                        .eq("symbol", "TEST_RT")\
                        .execute()
                    
                    self.print_result("Cleanup Test Data", True, "Deleted")
                else:
                    self.print_result("Read Test Data", False, "Could not read back")
            else:
                self.print_result("Insert Test Data", False, "Insert failed")
                
        except Exception as e:
            self.print_result("Real-time Test", False, str(e)[:100])
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 70)
        print(" HYPERLIQUID TRADING DASHBOARD - COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        print(f" Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Run tests
        self.test_environment()
        self.test_supabase_connection()
        self.test_cvd_data()
        self.test_dashboard_endpoints()
        self.test_indicator_files()
        self.test_cvd_integration()
        self.test_real_time_data()
        
        # Summary
        self.print_header("TEST SUMMARY")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for v in self.test_results.values() if v)
        failed_tests = total_tests - passed_tests
        
        print(f"\n  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n  Failed Tests:")
            for test, passed in self.test_results.items():
                if not passed:
                    print(f"    - {test}")
        
        overall_status = "PASS" if passed_tests/total_tests >= 0.8 else "FAIL"
        print(f"\n  Overall Status: [{overall_status}]")
        
        print("\n" + "=" * 70)
        print(" TEST SUITE COMPLETE")
        print("=" * 70)
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = DashboardTestSuite()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)