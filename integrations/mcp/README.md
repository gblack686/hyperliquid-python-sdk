# Hyperliquid MCP Servers Collection

This directory contains configurations and setup instructions for various Hyperliquid MCP (Model Context Protocol) servers.

## Available MCP Servers

### 1. TypeScript/JavaScript Servers

#### mektigboy/server-hyperliquid
- **Language**: TypeScript/JavaScript
- **Features**: Market data (mids, candles, L2 book)
- **Repository**: https://github.com/mektigboy/server-hyperliquid
- **Setup**: See `typescript/mektigboy/README.md`

#### TradingBalthazar_hyperliquid-mcp-server-v9
- **Language**: JavaScript
- **Features**: Full trading support (spot, futures, accounts)
- **Repository**: https://github.com/MCP-Mirror/TradingBalthazar_hyperliquid-mcp-server-v9
- **Setup**: See `javascript/tradingbalthazar/README.md`

#### 6rz6/HYPERLIQUID-MCP-Server
- **Language**: JavaScript
- **Features**: Market & account data, WebSocket, analytics
- **Repository**: https://github.com/6rz6/HYPERLIQUID-MCP-Server
- **Setup**: See `javascript/6rz6/README.md`

### 2. Python Servers

#### kukapay/hyperliquid-info-mcp
- **Language**: Python
- **Features**: User/account insights + analytics prompts
- **Repository**: https://github.com/kukapay/hyperliquid-info-mcp
- **Setup**: See `python/kukapay-info/README.md`

#### kukapay/hyperliquid-whalealert-mcp
- **Language**: Python
- **Features**: Whale trade alerts and summaries
- **Repository**: https://github.com/kukapay/hyperliquid-whalealert-mcp
- **Setup**: See `python/kukapay-whale/README.md`

#### midodimori/hyperliquid-mcp
- **Language**: Python
- **Features**: 29 trading tools with Pydantic validation
- **Package**: https://pypi.org/project/hyperliquid-mcp/
- **Setup**: See `python/midodimori/README.md`

### 3. Official SDK

#### hyperliquid-python-sdk
- **Language**: Python
- **Features**: Official Hyperliquid API SDK (non-MCP)
- **Repository**: https://github.com/hyperliquid-dex/hyperliquid-python-sdk
- **Note**: Already installed in parent directory

## Quick Start

### For Python MCP Servers
```bash
cd python
pip install -r requirements.txt
```

### For JavaScript/TypeScript MCP Servers
```bash
cd javascript
npm install
```

## Environment Setup

Create a `.env` file in the mcp directory:
```env
# Hyperliquid API Keys (keep these secret!)
HYPERLIQUID_API_KEY=your_api_key_here
HYPERLIQUID_SECRET_KEY=your_secret_key_here

# Network Configuration
HYPERLIQUID_NETWORK=mainnet  # or testnet
HYPERLIQUID_API_URL=https://api.hyperliquid.xyz

# MCP Server Ports
MCP_PYTHON_PORT=8001
MCP_TYPESCRIPT_PORT=8002
MCP_JAVASCRIPT_PORT=8003

# Optional: Supabase for data storage
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
```

## Testing

Use the mock server for testing without API keys:
```bash
cd ../hyperliquid-trading-dashboard
python mcp_test_server.py
```

## Production Deployment

See `DEPLOYMENT.md` for production deployment instructions.

## Security Notes

- **NEVER** commit API keys to version control
- Use environment variables for all sensitive data
- Test thoroughly with mock servers before using real APIs
- Implement rate limiting in production
- Use separate API keys for test/production

## Support

For issues with specific MCP servers, check their respective GitHub repositories.