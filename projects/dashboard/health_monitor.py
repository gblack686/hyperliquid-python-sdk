"""
Health Monitor Service for all indicators
Provides unified health endpoint for Docker containers
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
from datetime import datetime
import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client
import requests
import asyncio

sys.path.append('..')
load_dotenv()

app = FastAPI(title="Indicator Health Monitor", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase setup
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase_client: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None


@app.get("/")
async def root():
    """Root endpoint with dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Indicator Health Monitor</title>
        <style>
            body {
                font-family: 'Segoe UI', system-ui, sans-serif;
                background: #0a0e27;
                color: #fff;
                margin: 0;
                padding: 20px;
            }
            h1 { 
                text-align: center; 
                color: #00d4ff;
                margin-bottom: 30px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .card {
                background: #1a1f3a;
                border-radius: 10px;
                padding: 20px;
                border: 1px solid #2a3f5f;
            }
            .card h3 {
                color: #00d4ff;
                margin-top: 0;
            }
            .status {
                padding: 5px 10px;
                border-radius: 5px;
                display: inline-block;
                font-weight: bold;
            }
            .status.healthy { background: #00ff41; color: #000; }
            .status.warning { background: #ffb700; color: #000; }
            .status.error { background: #ff0040; color: #fff; }
            .metric {
                display: flex;
                justify-content: space-between;
                margin: 10px 0;
                padding: 10px;
                background: #0a0e27;
                border-radius: 5px;
            }
            .metric-label { color: #8892b0; }
            .metric-value { color: #64ffda; font-weight: bold; }
            .refresh-btn {
                background: #00d4ff;
                color: #000;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                margin: 20px auto;
                display: block;
            }
            .refresh-btn:hover { background: #00a8cc; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Hyperliquid Indicator Health Monitor</h1>
            <button class="refresh-btn" onclick="location.reload()">Refresh Status</button>
            <div id="status" class="grid">Loading...</div>
        </div>
        
        <script>
            async function fetchStatus() {
                try {
                    const response = await fetch('/health/detailed');
                    const data = await response.json();
                    displayStatus(data);
                } catch (error) {
                    document.getElementById('status').innerHTML = '<div class="card"><h3>Error</h3><p>Failed to fetch status</p></div>';
                }
            }
            
            function displayStatus(data) {
                const container = document.getElementById('status');
                let html = '';
                
                // Overall Status Card
                html += `<div class="card">
                    <h3>System Status</h3>
                    <div class="metric">
                        <span class="metric-label">Overall Health</span>
                        <span class="status ${data.status}">${data.status.toUpperCase()}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Timestamp</span>
                        <span class="metric-value">${new Date(data.timestamp).toLocaleTimeString()}</span>
                    </div>
                </div>`;
                
                // CVD Card
                if (data.indicators.cvd) {
                    const cvd = data.indicators.cvd;
                    html += `<div class="card">
                        <h3>CVD Monitor</h3>
                        <div class="metric">
                            <span class="metric-label">Status</span>
                            <span class="status ${cvd.healthy ? 'healthy' : 'error'}">${cvd.healthy ? 'RUNNING' : 'OFFLINE'}</span>
                        </div>
                        ${cvd.data ? cvd.data.map(d => `
                            <div class="metric">
                                <span class="metric-label">${d.symbol}</span>
                                <span class="metric-value">CVD: ${d.cvd.toFixed(2)} | Buy: ${d.buy_ratio.toFixed(1)}%</span>
                            </div>
                        `).join('') : ''}
                    </div>`;
                }
                
                // Open Interest Card
                if (data.indicators.open_interest) {
                    const oi = data.indicators.open_interest;
                    html += `<div class="card">
                        <h3>Open Interest</h3>
                        <div class="metric">
                            <span class="metric-label">Status</span>
                            <span class="status ${oi.healthy ? 'healthy' : 'error'}">${oi.healthy ? 'ACTIVE' : 'STALE'}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Last Update</span>
                            <span class="metric-value">${oi.last_update_seconds}s ago</span>
                        </div>
                        ${oi.data ? oi.data.map(d => `
                            <div class="metric">
                                <span class="metric-label">${d.symbol}</span>
                                <span class="metric-value">$${d.oi_current.toFixed(2)}M</span>
                            </div>
                        `).join('') : ''}
                    </div>`;
                }
                
                // Funding Rate Card
                if (data.indicators.funding_rate) {
                    const funding = data.indicators.funding_rate;
                    html += `<div class="card">
                        <h3>Funding Rates</h3>
                        <div class="metric">
                            <span class="metric-label">Status</span>
                            <span class="status ${funding.healthy ? 'healthy' : 'error'}">${funding.healthy ? 'ACTIVE' : 'STALE'}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Last Update</span>
                            <span class="metric-value">${funding.last_update_seconds}s ago</span>
                        </div>
                        ${funding.data ? funding.data.map(d => `
                            <div class="metric">
                                <span class="metric-label">${d.symbol}</span>
                                <span class="metric-value">${d.funding_current.toFixed(4)} bp</span>
                            </div>
                        `).join('') : ''}
                    </div>`;
                }
                
                container.innerHTML = html;
            }
            
            // Fetch status on load and every 10 seconds
            fetchStatus();
            setInterval(fetchStatus, 10000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "indicator-health-monitor"
    }


@app.get("/health/detailed")
async def detailed_health():
    """Detailed health status of all indicators"""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "indicators": {}
    }
    
    # Check CVD Monitor
    try:
        response = requests.get('http://cvd-monitor:8001/health', timeout=2)
        if response.status_code == 200:
            cvd_data = requests.get('http://cvd-monitor:8001/api/cvd/current', timeout=2).json()
            status["indicators"]["cvd"] = {
                "healthy": True,
                "endpoint": "http://cvd-monitor:8001",
                "data": cvd_data[:4] if cvd_data else []
            }
        else:
            status["indicators"]["cvd"] = {"healthy": False, "error": "Unhealthy response"}
    except Exception as e:
        status["indicators"]["cvd"] = {"healthy": False, "error": str(e)}
        # Try localhost as fallback
        try:
            response = requests.get('http://localhost:8001/health', timeout=2)
            if response.status_code == 200:
                cvd_data = requests.get('http://localhost:8001/api/cvd/current', timeout=2).json()
                status["indicators"]["cvd"] = {
                    "healthy": True,
                    "endpoint": "http://localhost:8001",
                    "data": cvd_data[:4] if cvd_data else []
                }
        except:
            pass
    
    # Check Open Interest
    if supabase_client:
        try:
            result = supabase_client.table('hl_oi_current').select("*").order("symbol").execute()
            if result.data:
                # Check freshness
                last_update = max([datetime.fromisoformat(d['updated_at'].replace('+00:00', '')) for d in result.data])
                age_seconds = (datetime.utcnow() - last_update).total_seconds()
                
                status["indicators"]["open_interest"] = {
                    "healthy": age_seconds < 120,  # Healthy if updated within 2 minutes
                    "last_update_seconds": int(age_seconds),
                    "data": result.data
                }
            else:
                status["indicators"]["open_interest"] = {"healthy": False, "error": "No data"}
        except Exception as e:
            status["indicators"]["open_interest"] = {"healthy": False, "error": str(e)}
    
    # Check Funding Rate
    if supabase_client:
        try:
            result = supabase_client.table('hl_funding_current').select("*").order("symbol").execute()
            if result.data:
                # Check freshness
                last_update = max([datetime.fromisoformat(d['updated_at'].replace('+00:00', '')) for d in result.data])
                age_seconds = (datetime.utcnow() - last_update).total_seconds()
                
                status["indicators"]["funding_rate"] = {
                    "healthy": age_seconds < 600,  # Healthy if updated within 10 minutes
                    "last_update_seconds": int(age_seconds),
                    "data": result.data
                }
            else:
                status["indicators"]["funding_rate"] = {"healthy": False, "error": "No data"}
        except Exception as e:
            status["indicators"]["funding_rate"] = {"healthy": False, "error": str(e)}
    
    # Set overall status
    all_healthy = all(ind.get("healthy", False) for ind in status["indicators"].values())
    status["status"] = "healthy" if all_healthy else "degraded"
    
    return status


@app.get("/api/indicators/summary")
async def indicators_summary():
    """Get summary of all indicators"""
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "symbols": ["BTC", "ETH", "SOL", "HYPE"],
        "indicators": {}
    }
    
    # Get all indicator data
    if supabase_client:
        try:
            # OI data
            oi_result = supabase_client.table('hl_oi_current').select("*").execute()
            summary["indicators"]["open_interest"] = oi_result.data if oi_result else []
            
            # Funding data
            funding_result = supabase_client.table('hl_funding_current').select("*").execute()
            summary["indicators"]["funding_rate"] = funding_result.data if funding_result else []
            
            # CVD data
            cvd_result = supabase_client.table('hl_cvd_current').select("*").execute()
            summary["indicators"]["cvd"] = cvd_result.data if cvd_result else []
        except Exception as e:
            summary["error"] = str(e)
    
    return summary


if __name__ == "__main__":
    print("=" * 60)
    print("Indicator Health Monitor")
    print("=" * 60)
    print("Dashboard: http://localhost:8002")
    print("Health: http://localhost:8002/health")
    print("Detailed: http://localhost:8002/health/detailed")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)