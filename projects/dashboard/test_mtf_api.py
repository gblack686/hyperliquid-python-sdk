#!/usr/bin/env python3

import requests
import json
import time
from datetime import datetime
from loguru import logger

BASE_URL = "http://localhost:8000"

def test_health():
    logger.info("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200
    data = response.json()
    logger.success(f"Health check: {data}")
    return True

def test_symbols():
    logger.info("Testing symbols endpoint...")
    response = requests.get(f"{BASE_URL}/api/symbols")
    assert response.status_code == 200
    data = response.json()
    logger.success(f"Available symbols: {data['symbols']}")
    return True

def test_timeframes():
    logger.info("Testing timeframes endpoint...")
    response = requests.get(f"{BASE_URL}/api/timeframes")
    assert response.status_code == 200
    data = response.json()
    logger.success(f"Timeframes: {data['descriptions']}")
    return True

def test_mtf_context(symbol="BTC-USD"):
    logger.info(f"Testing MTF context for {symbol}...")
    response = requests.get(f"{BASE_URL}/api/mtf/context/{symbol}?exec_tf=5")
    
    if response.status_code == 200:
        data = response.json()
        logger.success(f"MTF Context received for {symbol}")
        logger.info(f"  Price: ${data['p']:,.2f}")
        logger.info(f"  Timeframes: {data['TF']}")
        logger.info(f"  Support: ${data['L_sup']:,.2f}")
        logger.info(f"  Resistance: ${data['L_res']:,.2f}")
        return data
    else:
        logger.error(f"Failed to get MTF context: {response.text}")
        return None

def test_batch_context():
    logger.info("Testing batch MTF context...")
    response = requests.get(f"{BASE_URL}/api/mtf/batch?symbols=BTC-USD,ETH-USD,SOL-USD&exec_tf=5")
    
    if response.status_code == 200:
        data = response.json()
        logger.success(f"Batch context received for {len(data)} symbols")
        for item in data:
            logger.info(f"  Symbol {item['sym']}: ${item['p']:,.2f}")
        return data
    else:
        logger.error(f"Failed to get batch context: {response.text}")
        return None

def test_process_mtf(context_data):
    if not context_data:
        logger.warning("No context data to process")
        return None
        
    logger.info("Testing MTF processing...")
    response = requests.post(f"{BASE_URL}/api/mtf/process", json=context_data)
    
    if response.status_code == 200:
        data = response.json()
        logger.success("MTF data processed successfully")
        logger.info(f"  Signal Average: {data['sA']}")
        logger.info(f"  Confidence: {data['confA']}%")
        logger.info(f"  Probability of Continuation: {data['prob_cont']}%")
        logger.info(f"  Hold Signal: {data['hold']}")
        logger.info(f"  TP ATR: {data['tp_atr']}")
        logger.info(f"  SL ATR: {data['sl_atr']}")
        return data
    else:
        logger.error(f"Failed to process MTF: {response.text}")
        return None

def test_historical(symbol="BTC-USD"):
    logger.info(f"Testing historical data for {symbol}...")
    response = requests.get(f"{BASE_URL}/api/mtf/historical/{symbol}?limit=10")
    
    if response.status_code == 200:
        data = response.json()
        logger.success(f"Historical data received: {data['count']} records")
        return data
    else:
        logger.error(f"Failed to get historical data: {response.text}")
        return None

def test_stream(symbol="BTC-USD", duration=10):
    logger.info(f"Testing streaming for {symbol} (running for {duration} seconds)...")
    
    try:
        import sseclient
        
        response = requests.get(
            f"{BASE_URL}/api/mtf/stream/{symbol}?exec_tf=5&interval=5",
            stream=True
        )
        
        client = sseclient.SSEClient(response)
        start_time = time.time()
        event_count = 0
        
        for event in client.events():
            if time.time() - start_time > duration:
                break
                
            event_count += 1
            data = json.loads(event.data)
            logger.info(f"Stream event {event_count}: {data.get('timestamp', 'N/A')}")
            
            if 'error' in data:
                logger.error(f"Stream error: {data['error']}")
            else:
                context = data.get('context', {})
                output = data.get('output', {})
                logger.info(f"  Price: ${context.get('p', 0):,.2f}")
                logger.info(f"  Confidence: {output.get('confA', 0)}%")
        
        logger.success(f"Streaming test completed: {event_count} events received")
        return True
        
    except ImportError:
        logger.warning("sseclient not installed, skipping streaming test")
        logger.info("Install with: pip install sseclient-py")
        return None
    except Exception as e:
        logger.error(f"Streaming test failed: {e}")
        return False

def run_all_tests():
    logger.info("=" * 50)
    logger.info("Starting MTF API Tests")
    logger.info("=" * 50)
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        if test_health():
            tests_passed += 1
    except Exception as e:
        logger.error(f"Health test failed: {e}")
        tests_failed += 1
    
    time.sleep(1)
    
    try:
        if test_symbols():
            tests_passed += 1
    except Exception as e:
        logger.error(f"Symbols test failed: {e}")
        tests_failed += 1
    
    time.sleep(1)
    
    try:
        if test_timeframes():
            tests_passed += 1
    except Exception as e:
        logger.error(f"Timeframes test failed: {e}")
        tests_failed += 1
    
    time.sleep(1)
    
    try:
        context = test_mtf_context("BTC-USD")
        if context:
            tests_passed += 1
            
            output = test_process_mtf(context)
            if output:
                tests_passed += 1
        else:
            tests_failed += 2
    except Exception as e:
        logger.error(f"MTF context/process test failed: {e}")
        tests_failed += 2
    
    time.sleep(1)
    
    try:
        if test_batch_context():
            tests_passed += 1
    except Exception as e:
        logger.error(f"Batch context test failed: {e}")
        tests_failed += 1
    
    time.sleep(1)
    
    try:
        if test_historical():
            tests_passed += 1
    except Exception as e:
        logger.error(f"Historical test failed: {e}")
        tests_failed += 1
    
    logger.info("=" * 50)
    logger.info(f"Tests completed: {tests_passed} passed, {tests_failed} failed")
    logger.info("=" * 50)
    
    return tests_failed == 0

if __name__ == "__main__":
    import sys
    
    logger.info("Make sure the API server is running:")
    logger.info("  python run_mtf_api.py")
    logger.info("")
    
    time.sleep(2)
    
    success = run_all_tests()
    
    if not success:
        sys.exit(1)