# MCP Server Examples Documentation

## Overview
Created a comprehensive dashboard showing live examples from all 5 MCP servers with real Hyperliquid data.

## 🎯 Archon Task Created
- **Task ID**: 33b9e2ab-5ceb-40bb-aa32-57db90ce2a14
- **Project**: Hyperliquid Trading Confluence Dashboard
- **Title**: Add MCP Server Examples Dashboard with Live Data
- **Status**: TODO → In Progress → Completed

## 📊 Dashboard Features

### Access Point
- **URL**: http://localhost:8504
- **File**: `hyperliquid-trading-dashboard/app_mcp_examples.py`
- **Menu Option**: #5 in Dashboard Launcher

### Available MCP Servers & Examples

## 1. 📊 Real Data Server (Port 8889)
**Live Examples:**
- **All Mid Prices**: 426+ coins with real-time prices
  - BTC: $110,161.50
  - ETH: $4,275.75
  - SOL: $200.59
  - HYPE: $45.94
- **Order Book**: BTC Level 2 with bid/ask visualization
- **Historical Candles**: ETH 1-hour candles (24 hours)

**Tools Demonstrated:**
```python
get_all_mids()          # All market prices
get_l2_book(coin="BTC") # Order book depth
get_candles(coin="ETH", interval="1h", lookback=24)
```

## 2. 🎭 Mock Server (Port 8888)
**Simulated Examples:**
- **Mock Prices**: Test data for development
- **User State**: Simulated account information
  - Account Value: $125,000.50
  - Available Balance: $80,000.25
  - PnL: $5,250.75

**Tools Demonstrated:**
```python
get_all_mids()                           # Simulated prices
get_user_state(address="0xMockAddress") # Mock user data
```

## 3. 📈 Kukapay Info Server (Port 8401)
**Analytics Examples:**
- **Market Summary**: 
  - Total Coins: 426
  - Market Status: Open
  - Top prices display
- **Position Analysis**: Empty positions for zero address

**Tools Demonstrated:**
```python
get_market_summary()                    # Overall market stats
analyze_positions(address="0x0000...")  # Position analytics
```

## 4. 🐋 Whale Tracker (Port 8402)
**Whale Activity Examples:**
- **Recent Whale Trades**: Large trades above $50k
  - Total Volume tracking
  - Buy/Sell sides
- **BTC Flow Analysis**:
  - Flow Ratio: Buy/Sell pressure
  - Net Flow: Dollar volume
  - Sentiment: Bullish/Bearish/Neutral
- **Unusual Activity Detection**: Alerts for anomalies

**Tools Demonstrated:**
```python
get_whale_trades(min_usd=50000, lookback_minutes=60)
get_flow_analysis(coin="BTC", lookback_hours=24)
get_unusual_activity(sensitivity="medium")
```

## 5. 🤖 Advanced Trading Server (Port 8403)
**Trading Intelligence Examples:**
- **Technical Indicators (BTC)**:
  - RSI: Current value with overbought/oversold zones
  - MACD: Signal and histogram
  - Bollinger Bands: Upper/Lower bands
- **Trade Signals (ETH)**:
  - Buy/Sell/Hold recommendations
  - Confidence levels
  - Signal reasons
- **Position Sizing (SOL)**:
  - Recommended size based on risk
  - Stop loss calculation
  - Maximum loss limits

**Tools Demonstrated:**
```python
get_technical_indicators(coin="BTC", indicators=["RSI", "MACD", "BB"])
get_trade_signals(coin="ETH", strategy="trend_following")
calculate_position_size(coin="SOL", account_balance=10000, 
                       risk_percent=2, stop_loss_price=195)
```

## 📱 Dashboard Interface

### Features
- **Server Selection**: Radio buttons to switch between servers
- **Live Status Indicators**: Shows which servers are online
- **Auto-Refresh**: Optional 5-second auto-refresh
- **Raw Data View**: Expandable JSON viewer
- **Visual Components**:
  - Price tables with formatting
  - Order book depth charts (Plotly)
  - Metric cards with color coding
  - Progress bars for confidence levels

### Server Status Bar
Bottom of dashboard shows real-time status:
- ✅ Green: Server online
- ❌ Red: Server offline
- ⚠️ Yellow: Connection issue

## 🚀 How to Use

### Start All MCP Servers
```bash
# Terminal 1: Real Data
python mcp/real_data_mcp_server.py

# Terminal 2: Mock Server
python mcp/start_mock_server.py

# Terminal 3: Info Server
python mcp/python/kukapay_info_server.py

# Terminal 4: Whale Tracker
python mcp/python/whale_tracker_server.py

# Terminal 5: Advanced Trading
python mcp/python/advanced_trading_server.py
```

### Launch Dashboard
```bash
# Option 1: Direct launch
cd hyperliquid-trading-dashboard
streamlit run app_mcp_examples.py --server.port 8504

# Option 2: Via launcher
python dashboard_launcher.py
# Select option 5
```

## 📝 Code Structure

### Main Components
```python
# Server configuration
MCP_SERVERS = {
    "Real Data Server": {"url": "http://localhost:8889", ...},
    "Mock Server": {"url": "http://localhost:8888", ...},
    # ... etc
}

# Async data fetching
async def call_mcp_tool(session, server_url, method, params={})
async def get_server_examples(server_name, server_config)

# Display functions for each server
display_real_data_examples(examples)
display_whale_tracker_examples(examples)
display_advanced_trading_examples(examples)
# ... etc
```

## 🎯 Benefits

1. **Educational**: Users can see what data each MCP server provides
2. **Testing**: Verify servers are working correctly
3. **Development**: Understand data structures for integration
4. **Monitoring**: Real-time status of all MCP servers
5. **Documentation**: Live examples better than static docs

## 📊 Data Flow

```
User → Streamlit Dashboard → MCP Server → Hyperliquid API
                ↓                ↓              ↓
            Display ← Process ← Response ← Real Data
```

## 🔧 Troubleshooting

### Server Not Available
- Check server is running: `netstat -an | findstr :PORT`
- Start missing server from mcp/ directory
- Verify no firewall blocking ports

### No Data Displayed
- Check server health endpoint: http://localhost:PORT/health
- Verify Hyperliquid API is accessible
- Check for rate limiting

### Auto-refresh Issues
- Disable if causing performance problems
- Manual refresh with button always available

## 📈 Future Enhancements

1. **WebSocket Integration**: Real-time streaming updates
2. **Historical Charts**: Time series visualizations
3. **Comparison View**: Side-by-side server comparisons
4. **Export Functionality**: Save data snapshots
5. **Alert Configuration**: Set thresholds for notifications

## ✅ Summary

Successfully created and integrated MCP Server Examples Dashboard:
- ✅ Created Archon task for tracking
- ✅ Built comprehensive Streamlit dashboard
- ✅ Integrated all 5 MCP servers
- ✅ Display live, real data examples
- ✅ Added to dashboard launcher menu
- ✅ Visual components for better understanding
- ✅ Server status monitoring
- ✅ Auto-refresh capability

The dashboard is now available at **http://localhost:8504** and provides a complete view of all MCP server capabilities with real Hyperliquid data!