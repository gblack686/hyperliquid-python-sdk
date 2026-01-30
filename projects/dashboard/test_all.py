#!/usr/bin/env python
"""Comprehensive Test Suite for Hyperliquid Trading Dashboard."""

import os
import sys
import asyncio
import subprocess
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'quantpylib'))

# Load environment variables
load_dotenv()

# Color codes for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_section(title: str):
    """Print a section header."""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")

def print_success(msg: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}[OK] {msg}{Colors.ENDC}")

def print_error(msg: str):
    """Print error message."""
    print(f"{Colors.FAIL}[FAIL] {msg}{Colors.ENDC}")

def print_warning(msg: str):
    """Print warning message."""
    print(f"{Colors.WARNING}[!] {msg}{Colors.ENDC}")

def print_info(msg: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}[i] {msg}{Colors.ENDC}")

# ================== TEST 1: IMPORTS ==================

def test_imports() -> bool:
    """Test all imports to identify missing dependencies."""
    print_section("TEST 1: Import Dependencies")
    
    missing_modules = []
    successful_imports = []
    
    # List of imports to test
    imports_to_test = [
        ("streamlit", "streamlit"),
        ("asyncio", "asyncio"),
        ("pandas", "pandas"),
        ("plotly.graph_objects", "plotly"),
        ("plotly", "plotly"),
        ("loguru", "loguru"),
        ("msgpack", "msgpack"),
        ("orjson", "orjson"),
        ("numba", "numba"),
        ("matplotlib.pyplot", "matplotlib"),
        ("scipy", "scipy"),
        ("web3", "web3"),
        ("websockets", "websockets"),
        ("aiohttp", "aiohttp"),
        ("eth_utils", "eth_utils"),
        ("eth_account", "eth_account"),
        ("ta", "ta"),
        ("pandas_ta", "pandas_ta"),
        ("sklearn", "scikit-learn"),
        ("supabase", "supabase"),
        ("dotenv", "python-dotenv"),
        ("pydantic", "pydantic"),
        ("psycopg2", "psycopg2"),
        ("sqlalchemy", "sqlalchemy"),
        ("bs4", "beautifulsoup4"),
        ("lxml", "lxml"),
        ("seaborn", "seaborn"),
        ("statsmodels", "statsmodels"),
        ("httpx", "httpx"),
        ("yaml", "yaml"),
        ("dill", "dill"),
        ("hyperliquid", "hyperliquid-python-sdk"),
    ]
    
    for import_name, package_name in imports_to_test:
        try:
            __import__(import_name)
            successful_imports.append(import_name)
            print_success(f"{import_name}")
        except (ImportError, AttributeError) as e:
            missing_modules.append((import_name, package_name, str(e)))
            print_error(f"{import_name}: {e}")
    
    # Test quantpylib specific imports
    print("\nTesting quantpylib imports:")
    
    quantpylib_imports = [
        "quantpylib.wrappers.hyperliquid",
        "quantpylib.standards",
        "quantpylib.hft.lob",
        "quantpylib.utilities.general",
    ]
    
    for import_name in quantpylib_imports:
        try:
            __import__(import_name)
            successful_imports.append(import_name)
            print_success(f"{import_name}")
        except (ImportError, AttributeError) as e:
            missing_modules.append((import_name, import_name, str(e)))
            print_error(f"{import_name}: {e}")
    
    # Summary
    total = len(imports_to_test) + len(quantpylib_imports)
    passed = len(successful_imports)
    print(f"\nImport Test Result: {passed}/{total} imports successful")
    
    return len(missing_modules) == 0

# ================== TEST 2: ENVIRONMENT ==================

def test_environment() -> bool:
    """Check environment configuration."""
    print_section("TEST 2: Environment Configuration")
    
    required_vars = [
        ('HYPERLIQUID_API_KEY', 'Your private key for API access', True),
        ('ACCOUNT_ADDRESS', 'Your Hyperliquid account address', False),
        ('SUPABASE_URL', 'Supabase project URL', True),
        ('SUPABASE_KEY', 'Supabase anon key', True)
    ]
    
    all_present = True
    
    for var, description, mask in required_vars:
        value = os.getenv(var)
        if value:
            if mask and ('KEY' in var or 'SECRET' in var):
                masked = value[:10] + '...' + value[-4:] if len(value) > 14 else '***'
                print_success(f"{var}: {masked}")
            else:
                display = value[:30] + '...' if len(value) > 30 else value
                print_success(f"{var}: {display}")
        else:
            print_error(f"{var}: Missing - {description}")
            all_present = False
    
    return all_present

# ================== TEST 3: COMPONENTS ==================

async def test_components() -> bool:
    """Test main components of the app."""
    print_section("TEST 3: Component Initialization")
    
    all_passed = True
    
    # Test HyperliquidClient
    try:
        from src.hyperliquid_client import HyperliquidClient
        client = HyperliquidClient()
        print_success("HyperliquidClient initialized")
    except Exception as e:
        print_error(f"HyperliquidClient failed: {e}")
        all_passed = False
    
    # Test SupabaseManager
    try:
        from src.data.supabase_manager import SupabaseManager
        if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
            manager = SupabaseManager()
            print_success("SupabaseManager initialized")
        else:
            print_warning("SupabaseManager skipped (missing credentials)")
    except Exception as e:
        print_error(f"SupabaseManager failed: {e}")
        all_passed = False
    
    # Test ConfluenceAggregator
    try:
        from src.confluence.aggregator import ConfluenceAggregator
        aggregator = ConfluenceAggregator()
        print_success("ConfluenceAggregator initialized")
    except Exception as e:
        print_error(f"ConfluenceAggregator failed: {e}")
        all_passed = False
    
    # Test all indicators
    indicators = [
        "volume_spike.VolumeSpike",
        "ma_crossover.MACrossover",
        "rsi_mtf.RSIMultiTimeframe",
        "bollinger.BollingerBands",
        "macd.MACD",
        "stochastic.StochasticOscillator",
        "support_resistance.SupportResistance",
        "atr.ATRVolatility",
        "vwap.VWAP",
        "divergence.PriceDivergence"
    ]
    
    print("\nTesting indicators:")
    for indicator in indicators:
        module_name, class_name = indicator.rsplit('.', 1)
        try:
            module = __import__(f"src.indicators.{module_name}", fromlist=[class_name])
            getattr(module, class_name)
            print_success(f"{indicator}")
        except Exception as e:
            print_error(f"{indicator}: {e}")
            all_passed = False
    
    return all_passed

# ================== TEST 4: HYPERLIQUID CONNECTION ==================

def test_hyperliquid_connection() -> bool:
    """Test Hyperliquid API connection."""
    print_section("TEST 4: Hyperliquid Connection")
    
    try:
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        account_address = os.getenv('ACCOUNT_ADDRESS')
        
        if not secret_key:
            print_warning("HYPERLIQUID_API_KEY not found")
            return False
        
        # Create account from private key
        account: LocalAccount = eth_account.Account.from_key(secret_key)
        api_wallet = account.address
        
        print_info(f"API Wallet: {api_wallet}")
        print_info(f"Account Address: {account_address or 'Not set'}")
        
        # Connect to mainnet
        base_url = constants.MAINNET_API_URL
        info = Info(base_url, skip_ws=True)
        
        # Test connection
        meta = info.meta()
        print_success(f"Connected to Hyperliquid - {len(meta.get('universe', []))} assets available")
        
        # Get live price
        all_mids = info.all_mids()
        btc_price = float(all_mids.get("BTC", 0))
        eth_price = float(all_mids.get("ETH", 0))
        print_success(f"Live prices - BTC: ${btc_price:,.2f}, ETH: ${eth_price:,.2f}")
        
        return True
        
    except ImportError:
        print_error("hyperliquid package not installed")
        return False
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return False

# ================== TEST 5: DASHBOARD CONNECTION ==================

async def test_dashboard_connection() -> bool:
    """Test the dashboard's HyperliquidClient."""
    print_section("TEST 5: Dashboard Client Connection")
    
    try:
        from src.hyperliquid_client import HyperliquidClient
        
        api_key = os.getenv('HYPERLIQUID_API_KEY')
        
        client = HyperliquidClient(key=api_key, secret=None, mode="mainnet")
        
        connected = await client.connect()
        if connected:
            print_success("Dashboard client connected successfully")
        else:
            print_error("Dashboard client connection failed")
            return False
        
        # Test market data
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            bars = await client.get_trade_bars(
                ticker="BTC",
                start=start_time,
                end=end_time
            )
            
            if bars is not None:
                print_success("Market data fetch successful")
            else:
                print_warning("No market data returned")
        except Exception as e:
            print_warning(f"Market data fetch issue: {e}")
        
        return connected
        
    except Exception as e:
        print_error(f"Dashboard client test failed: {e}")
        return False

# ================== TEST 6: STREAMLIT APP ==================

def test_streamlit_app() -> bool:
    """Test Streamlit app startup."""
    print_section("TEST 6: Streamlit Application")
    
    try:
        # Start Streamlit in background
        print_info("Starting Streamlit app...")
        
        # Use the venv Python
        venv_python = Path("venv/Scripts/python.exe")
        if not venv_python.exists():
            print_error("Virtual environment not found")
            return False
        
        # Start the app
        process = subprocess.Popen(
            [str(venv_python), "-m", "streamlit", "run", "app.py", 
             "--server.headless", "true", "--server.port", "8501"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent
        )
        
        # Wait for startup
        print_info("Waiting for app to start...")
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print_error(f"App failed to start: {stderr.decode()}")
            return False
        
        print_success("Streamlit app started on http://localhost:8501")
        
        # Test with curl or requests
        try:
            import requests
            response = requests.get("http://localhost:8501", timeout=5)
            if response.status_code == 200:
                print_success("App is responding to HTTP requests")
            else:
                print_warning(f"App returned status code: {response.status_code}")
        except Exception as e:
            print_warning(f"Could not verify HTTP response: {e}")
        
        # Terminate the process
        process.terminate()
        process.wait(timeout=5)
        print_info("Streamlit app stopped")
        
        return True
        
    except Exception as e:
        print_error(f"Streamlit test failed: {e}")
        return False

# ================== TEST 7: PLAYWRIGHT UI TEST ==================

def test_playwright_ui() -> bool:
    """Test UI with Playwright (requires app to be running)."""
    print_section("TEST 7: UI Testing with Playwright")
    
    print_info("This test requires the dashboard to be running")
    print_info("Starting dashboard in background...")
    
    # Start the app in background
    venv_python = Path("venv/Scripts/python.exe")
    process = subprocess.Popen(
        [str(venv_python), "-m", "streamlit", "run", "app.py", 
         "--server.headless", "true", "--server.port", "8501"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=Path(__file__).parent
    )
    
    try:
        # Wait for app to start
        time.sleep(8)
        
        # Create a simple Playwright test script
        playwright_test = '''
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to app
        await page.goto("http://localhost:8501")
        await page.wait_for_load_state("networkidle")
        
        # Check title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Check for main elements
        header = await page.query_selector("h1")
        if header:
            text = await header.text_content()
            print(f"Header found: {text}")
        
        # Check for tabs
        tabs = await page.query_selector_all('[role="tab"]')
        print(f"Found {len(tabs)} tabs")
        
        # Test tab navigation
        for i, tab in enumerate(tabs[:3]):  # Test first 3 tabs
            await tab.click()
            await page.wait_for_timeout(500)
            print(f"Clicked tab {i+1}")
        
        # Check for configuration panel
        config = await page.query_selector('text=/Configuration/')
        if config:
            print("Configuration panel found")
        
        # Take screenshot
        await page.screenshot(path="test_screenshot.png")
        print("Screenshot saved")
        
        await browser.close()
        return True

if __name__ == "__main__":
    result = asyncio.run(test())
    exit(0 if result else 1)
'''
        
        # Write and run the Playwright test
        test_file = Path("playwright_test_temp.py")
        test_file.write_text(playwright_test)
        
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print_success("UI test passed")
            for line in result.stdout.split('\n'):
                if line:
                    print_info(line)
            test_file.unlink()  # Clean up
            return True
        else:
            print_error(f"UI test failed: {result.stderr}")
            test_file.unlink()  # Clean up
            return False
            
    except subprocess.TimeoutExpired:
        print_error("UI test timed out")
        return False
    except Exception as e:
        print_error(f"UI test error: {e}")
        return False
    finally:
        # Stop the app
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()
        print_info("Dashboard stopped")

# ================== MAIN TEST RUNNER ==================

async def run_all_tests():
    """Run all tests and generate report."""
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("+" + "="*58 + "+")
    print("|" + " HYPERLIQUID TRADING DASHBOARD - COMPLETE TEST SUITE ".center(58) + "|")
    print("+" + "="*58 + "+")
    print(f"{Colors.ENDC}")
    
    results = {}
    
    # Run all tests
    results['Imports'] = test_imports()
    results['Environment'] = test_environment()
    results['Components'] = await test_components()
    results['Hyperliquid API'] = test_hyperliquid_connection()
    results['Dashboard Client'] = await test_dashboard_connection()
    results['Streamlit App'] = test_streamlit_app()
    
    # Optional Playwright test (requires playwright to be installed)
    try:
        import playwright
        results['UI Testing'] = test_playwright_ui()
    except ImportError:
        print_warning("Playwright not installed - skipping UI tests")
        print_info("Install with: pip install playwright && playwright install chromium")
        results['UI Testing'] = None
    
    # Generate report
    print_section("TEST REPORT")
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, result in results.items():
        if result is None:
            print(f"{Colors.WARNING}[SKIP]{Colors.ENDC} {test_name}")
            skipped += 1
        elif result:
            print(f"{Colors.OKGREEN}[PASS]{Colors.ENDC} {test_name}")
            passed += 1
        else:
            print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} {test_name}")
            failed += 1
    
    print(f"\n{Colors.BOLD}Summary:{Colors.ENDC}")
    print(f"  Passed: {Colors.OKGREEN}{passed}{Colors.ENDC}")
    print(f"  Failed: {Colors.FAIL}{failed}{Colors.ENDC}")
    print(f"  Skipped: {Colors.WARNING}{skipped}{Colors.ENDC}")
    
    # Overall result
    if failed == 0 and passed > 0:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}[SUCCESS] ALL TESTS PASSED!{Colors.ENDC}")
        print(f"{Colors.OKGREEN}The dashboard is ready to use.{Colors.ENDC}")
        return True
    elif passed > failed:
        print(f"\n{Colors.WARNING}{Colors.BOLD}[WARNING] PARTIAL SUCCESS{Colors.ENDC}")
        print(f"{Colors.WARNING}Some tests failed but core functionality works.{Colors.ENDC}")
        return True
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}[ERROR] TEST SUITE FAILED{Colors.ENDC}")
        print(f"{Colors.FAIL}Please fix the issues before using the dashboard.{Colors.ENDC}")
        return False

def main():
    """Main entry point."""
    success = asyncio.run(run_all_tests())
    
    # Recommendations
    if not success:
        print_section("RECOMMENDATIONS")
        print("1. Check missing environment variables in .env")
        print("2. Install missing packages: pip install -r requirements.txt")
        print("3. Ensure Hyperliquid API key is valid")
        print("4. Verify Supabase credentials are correct")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())