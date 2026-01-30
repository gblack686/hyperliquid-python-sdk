"""
Test suite for Hyperliquid indicators
Verifies that all indicators are working correctly
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dotenv import load_dotenv
from supabase import create_client, Client
from colorama import init, Fore, Style

# Initialize colorama for colored output
init()

sys.path.append('..')
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

class IndicatorTester:
    """Test suite for all indicators"""
    
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        self.symbols = ['BTC', 'ETH', 'SOL', 'HYPE']
        self.test_results = []
        
    def print_test(self, name: str, passed: bool, message: str = ""):
        """Print test result with color"""
        if passed:
            print(f"{Fore.GREEN}[PASS]{Style.RESET_ALL} {name}: {message}")
            self.test_results.append({"test": name, "passed": True, "message": message})
        else:
            print(f"{Fore.RED}[FAIL]{Style.RESET_ALL} {name}: {message}")
            self.test_results.append({"test": name, "passed": False, "message": message})
    
    def print_section(self, title: str):
        """Print section header"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    async def test_supabase_connection(self) -> bool:
        """Test Supabase connection"""
        try:
            # Try to query a simple table
            result = self.supabase.table('hl_oi_current').select("symbol").limit(1).execute()
            self.print_test("Supabase Connection", True, "Connected successfully")
            return True
        except Exception as e:
            self.print_test("Supabase Connection", False, f"Failed: {e}")
            return False
    
    async def test_hyperliquid_api(self) -> bool:
        """Test Hyperliquid API connection"""
        try:
            # Try to get meta data
            response = self.info.meta_and_asset_ctxs()
            if isinstance(response, list) and len(response) == 2:
                self.print_test("Hyperliquid API", True, "Connected successfully")
                return True
            else:
                self.print_test("Hyperliquid API", False, "Unexpected response format")
                return False
        except Exception as e:
            self.print_test("Hyperliquid API", False, f"Failed: {e}")
            return False
    
    async def test_open_interest_data(self) -> bool:
        """Test Open Interest data"""
        try:
            # Query OI data from Supabase
            result = self.supabase.table('hl_oi_current').select("*").execute()
            
            if not result.data:
                self.print_test("Open Interest Data", False, "No data found")
                return False
            
            all_passed = True
            for symbol in self.symbols:
                symbol_data = next((d for d in result.data if d['symbol'] == symbol), None)
                
                if symbol_data:
                    oi = symbol_data.get('oi_current', 0)
                    updated = symbol_data.get('updated_at', '')
                    
                    # Check if data is recent (within 5 minutes)
                    if updated:
                        updated_time = datetime.fromisoformat(updated.replace('+00:00', ''))
                        age_seconds = (datetime.utcnow() - updated_time).total_seconds()
                        
                        if age_seconds < 300:  # 5 minutes
                            self.print_test(
                                f"OI {symbol}", 
                                True, 
                                f"${oi:.2f}M (updated {age_seconds:.0f}s ago)"
                            )
                        else:
                            self.print_test(
                                f"OI {symbol}", 
                                False, 
                                f"Data stale ({age_seconds:.0f}s old)"
                            )
                            all_passed = False
                    else:
                        self.print_test(f"OI {symbol}", False, "No timestamp")
                        all_passed = False
                else:
                    self.print_test(f"OI {symbol}", False, "No data")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.print_test("Open Interest Data", False, f"Error: {e}")
            return False
    
    async def test_funding_rate_data(self) -> bool:
        """Test Funding Rate data"""
        try:
            # Query funding data from Supabase
            result = self.supabase.table('hl_funding_current').select("*").execute()
            
            if not result.data:
                self.print_test("Funding Rate Data", False, "No data found")
                return False
            
            all_passed = True
            for symbol in self.symbols:
                symbol_data = next((d for d in result.data if d['symbol'] == symbol), None)
                
                if symbol_data:
                    funding = symbol_data.get('funding_current', 0)
                    predicted = symbol_data.get('funding_predicted', 0)
                    sentiment = symbol_data.get('sentiment', '')
                    updated = symbol_data.get('updated_at', '')
                    
                    # Check if data is recent (within 10 minutes for funding)
                    if updated:
                        updated_time = datetime.fromisoformat(updated.replace('+00:00', ''))
                        age_seconds = (datetime.utcnow() - updated_time).total_seconds()
                        
                        if age_seconds < 600:  # 10 minutes
                            self.print_test(
                                f"Funding {symbol}", 
                                True, 
                                f"{funding:.4f}bp, pred:{predicted:.2f}bp, {sentiment}"
                            )
                        else:
                            self.print_test(
                                f"Funding {symbol}", 
                                False, 
                                f"Data stale ({age_seconds:.0f}s old)"
                            )
                            all_passed = False
                    else:
                        self.print_test(f"Funding {symbol}", False, "No timestamp")
                        all_passed = False
                else:
                    self.print_test(f"Funding {symbol}", False, "No data")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.print_test("Funding Rate Data", False, f"Error: {e}")
            return False
    
    async def test_cvd_data(self) -> bool:
        """Test CVD data (from Docker container)"""
        try:
            # Query CVD data from Supabase
            result = self.supabase.table('hl_cvd_current').select("*").execute()
            
            if not result.data:
                self.print_test("CVD Data", False, "No data found (is Docker running?)")
                return False
            
            all_passed = True
            for symbol in self.symbols:
                symbol_data = next((d for d in result.data if d['symbol'] == symbol), None)
                
                if symbol_data:
                    cvd = symbol_data.get('cvd', 0)
                    buy_ratio = symbol_data.get('buy_ratio', 0)
                    trend = symbol_data.get('trend', '')
                    
                    self.print_test(
                        f"CVD {symbol}", 
                        True, 
                        f"CVD:{cvd:+.2f}, Buy:{buy_ratio:.1f}%, {trend}"
                    )
                else:
                    self.print_test(f"CVD {symbol}", False, "No data")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.print_test("CVD Data", False, f"Error: {e}")
            return False
    
    async def test_data_updates(self) -> bool:
        """Test if data is being updated"""
        try:
            print("\nWaiting 35 seconds to check for updates...")
            
            # Get initial OI values
            result1 = self.supabase.table('hl_oi_current').select("symbol,oi_current,updated_at").execute()
            initial_data = {d['symbol']: d for d in result1.data}
            
            # Wait for update interval
            await asyncio.sleep(35)
            
            # Get new OI values
            result2 = self.supabase.table('hl_oi_current').select("symbol,oi_current,updated_at").execute()
            new_data = {d['symbol']: d for d in result2.data}
            
            updates_found = False
            for symbol in self.symbols:
                if symbol in initial_data and symbol in new_data:
                    old_time = initial_data[symbol]['updated_at']
                    new_time = new_data[symbol]['updated_at']
                    
                    if old_time != new_time:
                        updates_found = True
                        old_oi = initial_data[symbol]['oi_current']
                        new_oi = new_data[symbol]['oi_current']
                        change = new_oi - old_oi
                        
                        self.print_test(
                            f"Update {symbol}", 
                            True, 
                            f"OI changed by ${change:+.2f}M"
                        )
            
            if not updates_found:
                self.print_test("Data Updates", False, "No updates detected")
                return False
            
            return True
            
        except Exception as e:
            self.print_test("Data Updates", False, f"Error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        self.print_section("INDICATOR SYSTEM TESTS")
        print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Connection tests
        self.print_section("1. CONNECTION TESTS")
        await self.test_supabase_connection()
        await self.test_hyperliquid_api()
        
        # Data presence tests
        self.print_section("2. DATA PRESENCE TESTS")
        await self.test_open_interest_data()
        await self.test_funding_rate_data()
        await self.test_cvd_data()
        
        # Update tests (optional, takes time)
        self.print_section("3. UPDATE TESTS")
        await self.test_data_updates()
        
        # Summary
        self.print_section("TEST SUMMARY")
        total = len(self.test_results)
        passed = sum(1 for t in self.test_results if t['passed'])
        failed = total - passed
        
        print(f"Total Tests: {total}")
        print(f"{Fore.GREEN}Passed: {passed}{Style.RESET_ALL}")
        if failed > 0:
            print(f"{Fore.RED}Failed: {failed}{Style.RESET_ALL}")
        
        # List failed tests
        if failed > 0:
            print(f"\n{Fore.YELLOW}Failed Tests:{Style.RESET_ALL}")
            for test in self.test_results:
                if not test['passed']:
                    print(f"  - {test['test']}: {test['message']}")
        
        return passed == total


async def main():
    """Main test runner"""
    tester = IndicatorTester()
    success = await tester.run_all_tests()
    
    if success:
        print(f"\n{Fore.GREEN}[SUCCESS] All tests passed!{Style.RESET_ALL}")
        return 0
    else:
        print(f"\n{Fore.RED}[FAILURE] Some tests failed!{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())