# Connecting Hyperliquid MCP Servers to Claude Desktop

## Quick Setup (Windows)

### 1. Find Your Claude Config File
The Claude Desktop config is located at:
```
%APPDATA%\Claude\claude_desktop_config.json
```
Or full path:
```
C:\Users\gblac\AppData\Roaming\Claude\claude_desktop_config.json
```

### 2. Add MCP Server Configuration

Edit the `claude_desktop_config.json` file and add the following under `mcpServers`:

```json
{
  "mcpServers": {
    "hyperliquid-real": {
      "command": "python",
      "args": ["C:\\Users\\gblac\\OneDrive\\Desktop\\hyperliquid-python-sdk\\mcp\\real_data_mcp_server.py"],
      "env": {}
    },
    "hyperliquid-mock": {
      "command": "python",
      "args": ["C:\\Users\\gblac\\OneDrive\\Desktop\\hyperliquid-python-sdk\\mcp\\start_mock_server.py"],
      "env": {}
    }
  }
}
```

### 3. Restart Claude Desktop
After saving the config, restart Claude Desktop for the changes to take effect.

## Available MCP Servers

### 1. **Real Data Server** (Recommended)
- **Purpose**: Get real-time Hyperliquid market data
- **Port**: 8889
- **API Key**: Not required for public data
- **Features**:
  - Real prices for 426+ trading pairs
  - Live order books
  - Recent trades
  - Funding rates
  - Historical candles

### 2. **Mock Server** (For Testing)
- **Purpose**: Test strategies without real data
- **Port**: 8888
- **API Key**: Not required
- **Features**:
  - Simulated price movements
  - Fake order books
  - Test trading functions

### 3. **Python SDK Server**
- **Purpose**: Full SDK integration
- **Port**: 8001
- **API Key**: Required for user-specific data
- **Features**:
  - User account data
  - Open orders
  - User fills
  - Position management

## Docker Setup (Optional)

### Build and Run All Servers
```bash
cd mcp

# Build Docker images
docker-compose build

# Start all servers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop all servers
docker-compose down
```

### Run Individual Servers
```bash
# Real data server only
docker-compose up -d mcp-real

# Mock server only
docker-compose up -d mcp-mock
```

## Manual Testing (Without Claude)

### Test Real Data Server
```bash
# Start server
python real_data_mcp_server.py

# In another terminal, test it
python test_real_data.py
```

### Test Mock Server
```bash
# Start server
python start_mock_server.py

# In another terminal, test it
python test_mcp_client.py
```

## Using in Claude Desktop

Once configured, you can use these commands in Claude:

### Example Commands
```
"Get the current price of BTC"
"Show me the ETH order book"
"What are the recent trades for SOL?"
"Get funding rates for the last 24 hours"
"Show me all available trading pairs"
```

### MCP Tools Available in Claude

1. **Market Data Tools**
   - `get_all_mids` - Get all current prices
   - `get_l2_book` - Get order book for a symbol
   - `get_recent_trades` - Get recent trades
   - `get_candles` - Get historical price candles

2. **Analytics Tools**
   - `get_funding_history` - Get funding rate history
   - `get_open_interest` - Get open interest data
   - `get_volume_24h` - Get 24-hour volumes

3. **Metadata Tools**
   - `get_meta` - Get exchange metadata
   - `get_perps_metadata` - Get perpetuals info
   - `get_spot_metadata` - Get spot pairs info

## Troubleshooting

### Server Won't Start
```bash
# Check if port is in use
netstat -an | findstr :8889

# Kill process using port
taskkill /F /PID <process_id>
```

### Claude Can't Connect
1. Ensure Python is in your PATH
2. Check the file paths in claude_desktop_config.json
3. Restart Claude Desktop after config changes
4. Check Windows Firewall settings

### No Data Returned
1. Check server logs: `python real_data_mcp_server.py`
2. Test manually: `python test_real_data.py`
3. Verify internet connection to api.hyperliquid.xyz

## Security Notes

- Real Data Server: Read-only, no trading capabilities
- Mock Server: Completely simulated, safe for testing
- No API keys stored in Claude config
- All servers run locally on your machine

## Advanced Configuration

### Custom Ports
Edit the server files to change ports:
```python
port = int(os.getenv("PORT", "8889"))  # Change 8889 to your port
```

### Add Authentication
For production use with real API keys:
1. Create `.env` file with your keys
2. Never commit `.env` to git
3. Use environment variables in Docker

### Rate Limiting
The real data server respects Hyperliquid's rate limits automatically.

## Support

- Server code: `/mcp/` directory
- Test scripts: `test_real_data.py`, `test_mcp_client.py`
- Logs: Check terminal output when running servers