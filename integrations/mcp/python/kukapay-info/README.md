# Kukapay Hyperliquid Info MCP Server

Read-only data access MCP server with analytics prompts for Hyperliquid.

## Features

- User account state and positions
- Open orders and trade history
- Funding history and fees
- Market data (mids, L2 snapshots, candles)
- AI analysis prompts for position summaries

## Installation

### Option 1: Clone and Install
```bash
python setup.py
```

### Option 2: Manual Setup
```bash
git clone https://github.com/kukapay/hyperliquid-info-mcp.git
cd hyperliquid-info-mcp
pip install -r requirements.txt
```

## Configuration

Create a `config.json` file:
```json
{
  "api_key": "your_api_key",
  "secret_key": "your_secret_key",
  "network": "mainnet",
  "port": 8001
}
```

## Available Tools

### User Data Tools
- `get_user_state` - Get complete user account state
- `get_user_open_orders` - List all open orders
- `get_user_trade_history` - Get historical trades
- `get_user_funding_history` - Get funding payments
- `get_user_fees` - Get fee statistics

### Market Data Tools
- `get_all_mids` - Get mid prices for all symbols
- `get_l2_snapshot` - Get Level 2 order book
- `get_candles_snapshot` - Get historical OHLCV data
- `get_funding_history` - Get funding rate history
- `get_meta` - Get market metadata

### Analysis Tools
- `analyze_positions` - AI prompt for position analysis
- `summarize_trading_activity` - Generate trading summary

## Usage

### Start the Server
```bash
python server.py
```

### Example Client Usage
```python
import requests

# List available tools
response = requests.get("http://localhost:8001/mcp/tools")
tools = response.json()

# Execute a tool
payload = {
    "method": "get_user_state",
    "params": {"address": "0x..."},
    "id": "1"
}
response = requests.post("http://localhost:8001/mcp/execute", json=payload)
result = response.json()
```

## Testing

Use the mock server for testing without API keys:
```bash
cd ../../../hyperliquid-trading-dashboard
python mcp_test_server.py
```

## API Documentation

### GET /mcp/tools
Returns list of available MCP tools with their parameters.

### POST /mcp/execute
Execute an MCP tool with specified parameters.

Request body:
```json
{
  "method": "tool_name",
  "params": {
    "param1": "value1"
  },
  "id": "request_id"
}
```

Response:
```json
{
  "result": {...},
  "error": null,
  "id": "request_id"
}
```

## Security Notes

- This is a READ-ONLY server - no trading operations
- API keys are only needed for private user data
- Public market data can be accessed without authentication
- Never expose your API keys in client-side code

## Support

Repository: https://github.com/kukapay/hyperliquid-info-mcp