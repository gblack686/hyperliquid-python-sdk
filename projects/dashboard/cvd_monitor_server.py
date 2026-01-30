"""
CVD Monitoring Server
Provides REST API and real-time view of CVD data from Supabase
"""

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json

load_dotenv()

app = FastAPI(title="CVD Monitor", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)


@app.get("/")
async def root():
    """Serve monitoring dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CVD Monitor</title>
        <style>
            body { 
                font-family: 'Courier New', monospace; 
                background: #1a1a1a; 
                color: #00ff00;
                padding: 20px;
            }
            h1 { color: #00ff00; }
            .container { max-width: 1200px; margin: 0 auto; }
            .symbol-card {
                background: #2a2a2a;
                border: 1px solid #00ff00;
                border-radius: 5px;
                padding: 15px;
                margin: 10px 0;
                display: inline-block;
                width: 30%;
                margin-right: 3%;
            }
            .symbol { font-size: 24px; font-weight: bold; }
            .cvd { font-size: 20px; margin: 10px 0; }
            .positive { color: #00ff00; }
            .negative { color: #ff0000; }
            .neutral { color: #ffff00; }
            .metric { margin: 5px 0; font-size: 14px; }
            .timestamp { color: #888; font-size: 12px; }
            #status { 
                background: #2a2a2a;
                border: 1px solid #00ff00;
                padding: 10px;
                margin: 20px 0;
            }
            .chart {
                width: 100%;
                height: 200px;
                margin: 10px 0;
            }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <div class="container">
            <h1>🔥 CVD Real-Time Monitor</h1>
            <div id="status">Connecting...</div>
            <div id="symbols"></div>
            <div id="charts" style="margin-top: 30px;">
                <canvas id="cvdChart"></canvas>
            </div>
        </div>
        
        <script>
            const symbolsDiv = document.getElementById('symbols');
            const statusDiv = document.getElementById('status');
            
            // Chart setup
            const ctx = document.getElementById('cvdChart').getContext('2d');
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: false },
                        x: { display: false }
                    },
                    plugins: {
                        legend: { display: true }
                    }
                }
            });
            
            const colors = {
                'BTC': '#f7931a',
                'ETH': '#627eea',
                'SOL': '#00ffa3'
            };
            
            const chartData = {
                'BTC': [],
                'ETH': [],
                'SOL': []
            };
            
            async function fetchCVD() {
                try {
                    const response = await fetch('/api/cvd/current');
                    const data = await response.json();
                    
                    statusDiv.innerHTML = `✓ Connected | Updated: ${new Date().toLocaleTimeString()}`;
                    statusDiv.style.borderColor = '#00ff00';
                    
                    let html = '';
                    
                    data.forEach(item => {
                        const cvdClass = item.cvd > 0 ? 'positive' : 'negative';
                        const trendIcon = item.trend === 'bullish' ? '↑' : 
                                        item.trend === 'bearish' ? '↓' : '→';
                        
                        html += `
                            <div class="symbol-card">
                                <div class="symbol">${item.symbol}</div>
                                <div class="cvd ${cvdClass}">
                                    CVD: ${item.cvd.toFixed(2)} ${trendIcon}
                                </div>
                                <div class="metric">Price: $${item.last_price.toFixed(2)}</div>
                                <div class="metric">Buy Ratio: ${item.buy_ratio.toFixed(1)}%</div>
                                <div class="metric">Trades: ${item.trade_count}</div>
                                <div class="metric">1m Change: ${item.cvd_1m.toFixed(2)}</div>
                                <div class="metric">5m Change: ${item.cvd_5m.toFixed(2)}</div>
                                <div class="timestamp">${item.updated_at}</div>
                            </div>
                        `;
                        
                        // Update chart data
                        if (!chartData[item.symbol]) {
                            chartData[item.symbol] = [];
                        }
                        chartData[item.symbol].push(item.cvd);
                        if (chartData[item.symbol].length > 50) {
                            chartData[item.symbol].shift();
                        }
                    });
                    
                    symbolsDiv.innerHTML = html;
                    
                    // Update chart
                    updateChart();
                    
                } catch (error) {
                    statusDiv.innerHTML = `✗ Error: ${error.message}`;
                    statusDiv.style.borderColor = '#ff0000';
                }
            }
            
            function updateChart() {
                const labels = Array.from({length: Math.max(...Object.values(chartData).map(d => d.length))}, (_, i) => i);
                
                chart.data.labels = labels;
                chart.data.datasets = Object.keys(chartData).map(symbol => ({
                    label: symbol,
                    data: chartData[symbol],
                    borderColor: colors[symbol],
                    backgroundColor: colors[symbol] + '20',
                    tension: 0.4,
                    fill: false
                }));
                
                chart.update('none');
            }
            
            // Fetch every 2 seconds
            setInterval(fetchCVD, 2000);
            fetchCVD();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/cvd/current")
async def get_current_cvd():
    """Get current CVD values for all symbols"""
    try:
        result = supabase.table('hl_cvd_current').select("*").execute()
        return result.data
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/cvd/snapshots/{symbol}")
async def get_cvd_snapshots(symbol: str, minutes: int = 60):
    """Get historical CVD snapshots for a symbol"""
    try:
        time_ago = datetime.now() - timedelta(minutes=minutes)
        
        result = supabase.table('hl_cvd_snapshots')\
            .select("*")\
            .eq('symbol', symbol)\
            .gte('timestamp', time_ago.isoformat())\
            .order('timestamp', desc=True)\
            .limit(500)\
            .execute()
        
        return result.data
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/cvd/stats")
async def get_cvd_stats():
    """Get CVD statistics"""
    try:
        # Get current CVD
        current = supabase.table('hl_cvd_current').select("*").execute()
        
        # Get snapshot count
        snapshots = supabase.table('hl_cvd_snapshots')\
            .select("symbol, count")\
            .execute()
        
        stats = {
            "current_cvd": current.data,
            "total_snapshots": len(snapshots.data) if snapshots.data else 0,
            "last_update": datetime.now().isoformat()
        }
        
        return stats
    except Exception as e:
        return {"error": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time CVD updates"""
    await websocket.accept()
    
    try:
        while True:
            # Get current CVD
            result = supabase.table('hl_cvd_current').select("*").execute()
            
            # Send to client
            await websocket.send_json({
                "type": "cvd_update",
                "data": result.data,
                "timestamp": datetime.now().isoformat()
            })
            
            # Wait 2 seconds
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Supabase connection
        result = supabase.table('hl_cvd_current').select("symbol").limit(1).execute()
        
        return {
            "status": "healthy",
            "supabase": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("CVD Monitoring Server")
    print("=" * 60)
    print("Dashboard: http://localhost:8001")
    print("API Docs: http://localhost:8001/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")