#!/usr/bin/env python
"""Update Archon with completed tasks"""

import requests
import json
from datetime import datetime

# Archon API endpoint
ARCHON_URL = "http://localhost:8181/api/tasks"

# Task data
task_data = {
    "project_id": "hyperliquid-dashboard",
    "title": "MTF Indicators Suite Complete",
    "description": """Successfully implemented and deployed 11 MTF trading indicators:
    
Core Indicators (8):
- Open Interest (30s updates)
- Funding Rate (5m updates) 
- Liquidations Tracker (10s updates)
- Order Book Imbalance with rate limiting (5s updates)
- VWAP multi-timeframe (10s updates)
- ATR volatility (30s updates)
- Bollinger Bands (30s updates)
- Support/Resistance levels (60s updates)

Advanced Analytics (3):
- Volume Profile (VPVR) with POC and Value Area
- Basis/Premium Tracker with arbitrage detection
- Multi-Timeframe Aggregator with confluence scoring

Technical Implementation:
- Rate limiting using quantpylib AsyncRateSemaphore (10 req/s)
- All indicators saving to Supabase (200/201 OK)
- Production Docker deployment
- Tracking: BTC, ETH, SOL, HYPE
""",
    "status": "completed",
    "priority": "high",
    "tags": ["hyperliquid", "indicators", "mtf", "trading", "production"],
    "metadata": {
        "indicators_count": 11,
        "rate_limiting": "implemented", 
        "database": "supabase",
        "deployment": "docker",
        "symbols": ["BTC", "ETH", "SOL", "HYPE"]
    },
    "completed_at": datetime.utcnow().isoformat()
}

try:
    # Send POST request
    response = requests.post(ARCHON_URL, json=task_data)
    
    if response.status_code in [200, 201]:
        print("Successfully updated Archon with completed task")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Failed to update Archon: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"Error connecting to Archon: {e}")
    print("Archon might not be running or accessible")