#!/usr/bin/env python3

import asyncio
import json
import time
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from loguru import logger
import requests
from typing import Dict, List, Optional

# Add the project to path
sys.path.append(os.path.dirname(__file__))

class MTFAPITestSuite:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.api_process = None
        self.test_results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
        self.start_time = None
        
    def start_api_server(self) -> bool:
        """Start the API server in a subprocess"""
        logger.info("Starting MTF API server...")
        try:
            # Check if server is already running
            try:
                response = requests.get(f"{self.base_url}/api/health", timeout=2)
                if response.status_code == 200:
                    logger.info("API server already running")
                    return True
            except:
                pass
            
            # Start the server
            self.api_process = subprocess.Popen(
                [sys.executable, "run_mtf_api.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent
            )
            
            # Wait for server to start
            max_retries = 30
            for i in range(max_retries):
                time.sleep(1)
                try:
                    response = requests.get(f"{self.base_url}/api/health", timeout=2)
                    if response.status_code == 200:
                        logger.success("API server started successfully")
                        return True
                except:
                    if i % 5 == 0:
                        logger.info(f"Waiting for server to start... ({i}/{max_retries})")
                    
            logger.error("Failed to start API server")
            return False
            
        except Exception as e:
            logger.error(f"Error starting API server: {e}")
            return False
    
    def stop_api_server(self):
        """Stop the API server"""
        if self.api_process:
            logger.info("Stopping API server...")
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.api_process.kill()
            logger.info("API server stopped")
    
    def test_health_endpoint(self) -> bool:
        """Test the health check endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
            self.test_results["passed"].append("Health endpoint")
            logger.success("✓ Health endpoint test passed")
            return True
        except Exception as e:
            self.test_results["failed"].append(f"Health endpoint: {str(e)}")
            logger.error(f"✗ Health endpoint test failed: {e}")
            return False
    
    def test_symbols_endpoint(self) -> bool:
        """Test the symbols endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/symbols")
            assert response.status_code == 200
            data = response.json()
            assert "symbols" in data
            assert "symbol_map" in data
            assert len(data["symbols"]) > 0
            self.test_results["passed"].append("Symbols endpoint")
            logger.success(f"✓ Symbols endpoint test passed - Found {len(data['symbols'])} symbols")
            return True
        except Exception as e:
            self.test_results["failed"].append(f"Symbols endpoint: {str(e)}")
            logger.error(f"✗ Symbols endpoint test failed: {e}")
            return False
    
    def test_timeframes_endpoint(self) -> bool:
        """Test the timeframes endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/timeframes")
            assert response.status_code == 200
            data = response.json()
            assert "timeframes" in data
            assert "descriptions" in data
            assert len(data["timeframes"]) == 6
            self.test_results["passed"].append("Timeframes endpoint")
            logger.success("✓ Timeframes endpoint test passed")
            return True
        except Exception as e:
            self.test_results["failed"].append(f"Timeframes endpoint: {str(e)}")
            logger.error(f"✗ Timeframes endpoint test failed: {e}")
            return False
    
    def test_mtf_context(self, symbol: str = "BTC-USD") -> Optional[Dict]:
        """Test MTF context endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/mtf/context/{symbol}?exec_tf=5", timeout=30)
            assert response.status_code == 200
            data = response.json()
            
            # Validate required fields
            required_fields = ["sym", "t", "p", "TF", "px_z", "v_z", "vwap_z", 
                             "bb_pos", "atr_n", "L_sup", "L_res"]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
            
            assert len(data["TF"]) == 6
            assert len(data["px_z"]) == 6
            assert data["p"] > 0
            
            self.test_results["passed"].append(f"MTF context for {symbol}")
            logger.success(f"✓ MTF context test passed - {symbol}: ${data['p']:,.2f}")
            return data
        except Exception as e:
            self.test_results["failed"].append(f"MTF context {symbol}: {str(e)}")
            logger.error(f"✗ MTF context test failed for {symbol}: {e}")
            return None
    
    def test_batch_context(self) -> bool:
        """Test batch MTF context endpoint"""
        try:
            symbols = "BTC-USD,ETH-USD,SOL-USD"
            response = requests.get(
                f"{self.base_url}/api/mtf/batch?symbols={symbols}&exec_tf=5",
                timeout=60
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 3
            
            for item in data:
                assert "sym" in item
                assert "p" in item
                assert item["p"] > 0
            
            self.test_results["passed"].append("Batch MTF context")
            logger.success(f"✓ Batch context test passed - Received {len(data)} results")
            return True
        except Exception as e:
            self.test_results["failed"].append(f"Batch context: {str(e)}")
            logger.error(f"✗ Batch context test failed: {e}")
            return False
    
    def test_process_mtf(self, context_data: Optional[Dict]) -> bool:
        """Test MTF processing endpoint"""
        if not context_data:
            self.test_results["warnings"].append("Skipped MTF processing - no context data")
            logger.warning("⚠ MTF processing test skipped - no context data")
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/api/mtf/process",
                json=context_data,
                timeout=30
            )
            assert response.status_code == 200
            data = response.json()
            
            # Validate output fields
            required_fields = ["sym", "t", "p", "tf", "s", "c", "o", "f", "conf",
                             "sA", "fA", "confA", "prob_cont", "hold", "tp_atr", "sl_atr"]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
            
            assert 0 <= data["confA"] <= 100
            assert data["hold"] in [0, 1]
            assert data["tp_atr"] > 0
            assert data["sl_atr"] > 0
            
            self.test_results["passed"].append("MTF processing")
            logger.success(f"✓ MTF processing test passed - Confidence: {data['confA']}%")
            return True
        except Exception as e:
            self.test_results["failed"].append(f"MTF processing: {str(e)}")
            logger.error(f"✗ MTF processing test failed: {e}")
            return False
    
    def test_historical_data(self) -> bool:
        """Test historical data endpoint"""
        try:
            response = requests.get(
                f"{self.base_url}/api/mtf/historical/BTC-USD?limit=5",
                timeout=30
            )
            assert response.status_code == 200
            data = response.json()
            assert "symbol" in data
            assert "count" in data
            assert "data" in data
            
            self.test_results["passed"].append("Historical data")
            logger.success(f"✓ Historical data test passed - {data['count']} records")
            return True
        except Exception as e:
            self.test_results["failed"].append(f"Historical data: {str(e)}")
            logger.error(f"✗ Historical data test failed: {e}")
            return False
    
    def test_data_validation(self) -> bool:
        """Validate the mock data files"""
        try:
            # Run the validation script
            result = subprocess.run(
                [sys.executable, "scripts/load_and_validate.py"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            
            if result.returncode == 0:
                self.test_results["passed"].append("Data validation")
                logger.success("✓ Data validation passed")
                return True
            else:
                self.test_results["failed"].append(f"Data validation: {result.stderr}")
                logger.error(f"✗ Data validation failed: {result.stderr}")
                return False
        except Exception as e:
            self.test_results["failed"].append(f"Data validation: {str(e)}")
            logger.error(f"✗ Data validation failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests in sequence"""
        self.start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("Starting MTF API Complete Test Suite")
        logger.info("=" * 60)
        
        # Validate data files first
        self.test_data_validation()
        time.sleep(1)
        
        # Start API server
        if not self.start_api_server():
            logger.error("Failed to start API server - aborting tests")
            return False
        
        time.sleep(3)  # Give server time to fully initialize
        
        # Run API tests
        self.test_health_endpoint()
        time.sleep(0.5)
        
        self.test_symbols_endpoint()
        time.sleep(0.5)
        
        self.test_timeframes_endpoint()
        time.sleep(0.5)
        
        # Test MTF context and processing
        context = self.test_mtf_context("BTC-USD")
        time.sleep(1)
        
        if context:
            self.test_process_mtf(context)
            time.sleep(0.5)
        
        # Test batch processing
        self.test_batch_context()
        time.sleep(0.5)
        
        # Test historical data
        self.test_historical_data()
        
        # Calculate results
        total_tests = len(self.test_results["passed"]) + len(self.test_results["failed"])
        success_rate = (len(self.test_results["passed"]) / total_tests * 100) if total_tests > 0 else 0
        
        # Print summary
        logger.info("=" * 60)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        logger.success(f"✓ Passed: {len(self.test_results['passed'])}")
        if self.test_results["failed"]:
            logger.error(f"✗ Failed: {len(self.test_results['failed'])}")
            for failure in self.test_results["failed"]:
                logger.error(f"  - {failure}")
        if self.test_results["warnings"]:
            logger.warning(f"⚠ Warnings: {len(self.test_results['warnings'])}")
            for warning in self.test_results["warnings"]:
                logger.warning(f"  - {warning}")
        
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Duration: {(datetime.now() - self.start_time).total_seconds():.2f} seconds")
        logger.info("=" * 60)
        
        return len(self.test_results["failed"]) == 0
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_api_server()
    
    def generate_report(self) -> Dict:
        """Generate test report for markdown"""
        return {
            "timestamp": datetime.now().isoformat(),
            "duration": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "total_tests": len(self.test_results["passed"]) + len(self.test_results["failed"]),
            "passed": len(self.test_results["passed"]),
            "failed": len(self.test_results["failed"]),
            "warnings": len(self.test_results["warnings"]),
            "success_rate": (len(self.test_results["passed"]) / 
                           (len(self.test_results["passed"]) + len(self.test_results["failed"])) * 100)
                           if (len(self.test_results["passed"]) + len(self.test_results["failed"])) > 0 else 0,
            "details": self.test_results
        }

def main():
    test_suite = MTFAPITestSuite()
    
    try:
        success = test_suite.run_all_tests()
        report = test_suite.generate_report()
        
        # Save report to file
        report_file = Path(__file__).parent / "test_results.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test report saved to {report_file}")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.warning("Tests interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        return 1
    finally:
        test_suite.cleanup()

if __name__ == "__main__":
    sys.exit(main())