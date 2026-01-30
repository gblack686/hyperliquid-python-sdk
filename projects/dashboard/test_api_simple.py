#!/usr/bin/env python3

import subprocess
import time
import sys
import os
import json
from pathlib import Path

# Test without external dependencies first
def test_data_validation():
    """Test the mock data validation"""
    print("\n=== Testing Data Validation ===")
    cmd = [sys.executable, "scripts/load_and_validate.py"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        if result.returncode == 0:
            print("[PASS] Data validation succeeded")
            print(result.stdout)
            return True
        else:
            print("[FAIL] Data validation failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"[ERROR] Could not run validation: {e}")
        return False

def test_api_import():
    """Test if the API module can be imported"""
    print("\n=== Testing API Import ===")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from src.api.mtf_data_feed import app, MTFDataFeedService
        print("[PASS] API module imported successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] Could not import API module: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

def start_api_server():
    """Start the API server"""
    print("\n=== Starting API Server ===")
    cmd = [sys.executable, "run_mtf_api.py"]
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent
        )
        print("API server process started, waiting for initialization...")
        time.sleep(5)  # Give it time to start
        
        # Check if process is still running
        if process.poll() is None:
            print("[PASS] API server is running")
            return process
        else:
            stdout, stderr = process.communicate(timeout=1)
            print("[FAIL] API server exited immediately")
            print(f"STDOUT: {stdout.decode() if stdout else 'None'}")
            print(f"STDERR: {stderr.decode() if stderr else 'None'}")
            return None
    except Exception as e:
        print(f"[ERROR] Could not start API server: {e}")
        return None

def test_api_endpoints(base_url="http://localhost:8000"):
    """Test basic API endpoints"""
    print("\n=== Testing API Endpoints ===")
    try:
        import requests
        
        # Test health endpoint
        print("Testing /api/health...")
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print(f"[PASS] Health endpoint: {response.json()}")
        else:
            print(f"[FAIL] Health endpoint returned {response.status_code}")
            return False
        
        # Test symbols endpoint
        print("Testing /api/symbols...")
        response = requests.get(f"{base_url}/api/symbols", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Symbols endpoint: {len(data.get('symbols', []))} symbols")
        else:
            print(f"[FAIL] Symbols endpoint returned {response.status_code}")
            return False
        
        # Test timeframes endpoint
        print("Testing /api/timeframes...")
        response = requests.get(f"{base_url}/api/timeframes", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Timeframes endpoint: {len(data.get('timeframes', []))} timeframes")
        else:
            print(f"[FAIL] Timeframes endpoint returned {response.status_code}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("[FAIL] Could not connect to API server")
        return False
    except ImportError:
        print("[SKIP] requests module not installed, skipping API tests")
        return None
    except Exception as e:
        print(f"[ERROR] API test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("MTF API Test Suite (Simple)")
    print("=" * 60)
    
    results = {
        "data_validation": False,
        "api_import": False,
        "api_server": False,
        "api_endpoints": False
    }
    
    # Test data validation
    results["data_validation"] = test_data_validation()
    
    # Test API import
    results["api_import"] = test_api_import()
    
    # Try to start API server
    api_process = None
    if results["api_import"]:
        api_process = start_api_server()
        results["api_server"] = api_process is not None
        
        # Test endpoints if server is running
        if api_process:
            time.sleep(3)  # Extra time for server to be ready
            endpoint_result = test_api_endpoints()
            if endpoint_result is not None:
                results["api_endpoints"] = endpoint_result
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # Cleanup
    if api_process:
        print("\nStopping API server...")
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
        print("API server stopped")
    
    # Save results
    results_file = Path(__file__).parent / "test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
            "passed": passed,
            "total": total
        }, f, indent=2)
    print(f"\nResults saved to {results_file}")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())