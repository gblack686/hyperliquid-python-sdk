# MCP Server Testing Guide

## Overview
This guide explains how to test MCP (Model Context Protocol) servers for Hyperliquid without using real API keys. We've created a complete mock testing environment that simulates the Hyperliquid API.

## Components

### 1. Mock MCP Server (`mcp_test_server.py`)
A FastAPI-based server that simulates Hyperliquid MCP endpoints:
- **Port**: 8888
- **Endpoints**:
  - `/` - Server info
  - `/mcp/tools` - List available tools
  - `/mcp/execute` - Execute MCP tools
  - `/ws` - WebSocket for real-time data

### 2. MCP Client Test (`mcp_client_test.py`)
Comprehensive test suite for MCP functionality:
- Lists available tools
- Tests all major endpoints
- WebSocket streaming test
- Error handling validation

### 3. Quick Test (`test_mcp_quick.py`)
Lightweight test script for rapid validation without WebSocket.

## Available Mock Tools

The mock server provides these MCP tools:

1. **get_all_mids** - Get mid prices for all symbols
2. **get_l2_book** - Get Level 2 order book data
3. **get_candle_snapshot** - Get historical OHLCV candles
4. **get_user_state** - Get user account state
5. **get_funding_rates** - Get current funding rates
6. **get_whale_alerts** - Get whale trade alerts ($1M+)
7. **place_order** - Place a mock order
8. **cancel_order** - Cancel a mock order

## Testing Without Real API Keys

### Step 1: Start the Mock Server
```bash
cd hyperliquid-trading-dashboard
python mcp_test_server.py
```

Server will start at `http://127.0.0.1:8888`

### Step 2: Run Tests

#### Quick Test (No WebSocket)
```bash
python test_mcp_quick.py
```

Expected output:
```
Testing MCP Server...
========================================
[OK] Server: Mock Hyperliquid MCP Server v1.0.0
[OK] Found 8 tools
[OK] Mid prices: BTC=$64386.78, ETH=$3566.85
[OK] L2 Book for HYPE: 10 bids, 10 asks
[OK] HYPE funding rate: -0.0019%/hour
[OK] Order placed: order_45422
========================================
All tests passed! Mock MCP server is working.
```

#### Full Test Suite (With WebSocket)
```bash
python mcp_client_test.py
```

This runs 10 comprehensive tests including WebSocket streaming.

## Mock Data Generation

The server generates realistic mock data:
- **Prices**: Base prices with ±2% random variance
- **Order Books**: 10 levels of bids/asks
- **Candles**: Historical OHLCV with realistic patterns
- **Funding Rates**: -0.01% to 0.01% per hour range
- **Whale Alerts**: Random large trades over $1M

## WebSocket Streaming

The mock server provides real-time data via WebSocket:
- Price updates every second
- Occasional whale alerts (10% probability)
- Connection URL: `ws://127.0.0.1:8888/ws`

## Integration with Real MCP Servers

Once testing is complete, you can switch to real MCP servers:

### Python MCP Options:
1. **hyperliquid-mcp** (PyPI) - 29 trading tools
2. **hyperliquid-info-mcp** - Read-only data access
3. **hyperliquid-whalealert-mcp** - Whale monitoring

### Installation:
```bash
pip install hyperliquid-mcp
# or
pip install hyperliquid-info-mcp
```

### Configuration:
Replace the mock server URL with the real MCP server endpoint and add your API credentials.

## Docker Integration

Add to `docker-compose.yml`:
```yaml
mcp-server:
  build:
    context: .
    target: mcp-server
  container_name: hl-mcp
  ports:
    - "8888:8888"
  environment:
    - MCP_MODE=mock  # or 'production' with real keys
```

## Security Notes

1. **Never commit real API keys** - Use environment variables
2. **Test thoroughly with mock data** before using real APIs
3. **Implement rate limiting** in production
4. **Use separate test/production configurations**

## Troubleshooting

### Server won't start
- Check port 8888 is not in use: `netstat -an | grep 8888`
- Kill existing process: `taskkill /F /PID <pid>` (Windows) or `kill -9 <pid>` (Linux/Mac)

### Connection refused
- Ensure server is running: `curl http://127.0.0.1:8888/`
- Check firewall settings

### WebSocket errors
- Update websockets library: `pip install --upgrade websockets`
- Check browser/client WebSocket support

## Next Steps

1. **Extend mock data** - Add more symbols, custom scenarios
2. **Add authentication** - Implement API key validation
3. **Create test scenarios** - Specific trading conditions
4. **Performance testing** - Load testing with multiple clients
5. **Switch to production** - Migrate to real MCP servers

## Related Files

- `mcp_test_server.py` - Mock server implementation
- `mcp_client_test.py` - Full test suite
- `test_mcp_quick.py` - Quick validation test
- `hyperliquid_stats_api.py` - Stats API integration
- `hyperliquid_stats_enhanced.py` - Enhanced stats using SDK

## Summary

This testing environment allows complete MCP server testing without real API keys, providing:
- Realistic mock data generation
- All major endpoint coverage
- WebSocket streaming support
- Easy transition to production
- No risk of accidental trades or API costs