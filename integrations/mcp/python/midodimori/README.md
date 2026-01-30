# Midodimori Hyperliquid MCP Server

Comprehensive MCP server with 29 trading tools, Pydantic validation, and risk management.

## Features

- **29 Trading Tools** - Complete coverage of Hyperliquid API
- **Type Safety** - Pydantic models for all data structures
- **Risk Management** - Built-in position sizing and leverage checks
- **Error Handling** - Robust error handling and logging
- **WebSocket Support** - Real-time data streaming
- **Simulation Mode** - Test strategies without real trades

## Installation

### From PyPI
```bash
pip install hyperliquid-mcp>=0.1.5
```

### Or run setup script
```bash
python setup.py
```

## Quick Start

### Command Line
```bash
# Start server with default config
hyperliquid-mcp serve

# Start with custom port
hyperliquid-mcp serve --port 8003

# Start in testnet mode
hyperliquid-mcp serve --network testnet

# Start with risk limits
hyperliquid-mcp serve --max-position 10000 --max-leverage 5
```

### Python Library
```python
from hyperliquid_mcp import HyperliquidMCP, MCPConfig

# Configure
config = MCPConfig(
    api_key="your_api_key",
    secret_key="your_secret_key",
    network="mainnet",
    port=8003
)

# Initialize
mcp = HyperliquidMCP(config)

# Use as library
account = mcp.execute_tool("get_account_info", {})
print(f"Balance: ${account['balance']}")

# Or start as server
mcp.run()
```

## Available Tools (29 Total)

### Account Management
- `get_account_info` - Complete account state
- `get_positions` - Current positions
- `get_open_orders` - Active orders
- `get_balance` - Account balances
- `get_leverage` - Current leverage
- `get_margin_info` - Margin requirements

### Trading Operations
- `place_order` - Place new order
- `cancel_order` - Cancel existing order
- `cancel_all_orders` - Cancel all orders
- `modify_order` - Modify existing order
- `close_position` - Close position
- `close_all_positions` - Close all positions

### Market Data
- `get_all_mids` - Mid prices for all symbols
- `get_orderbook` - L2 order book
- `get_trades` - Recent trades
- `get_candles` - OHLCV data
- `get_funding_rates` - Current funding
- `get_open_interest` - OI data

### Risk Management
- `calculate_position_size` - Risk-based sizing
- `check_risk_limits` - Validate trade risk
- `get_risk_metrics` - Portfolio risk metrics
- `simulate_trade` - Simulate trade impact

### Analytics
- `get_pnl_history` - Historical P&L
- `get_trade_statistics` - Trading stats
- `analyze_performance` - Performance metrics
- `get_funding_history` - Historical funding

### Utilities
- `get_server_time` - Server timestamp
- `get_exchange_info` - Exchange metadata
- `validate_order` - Pre-validate order

## Configuration Options

```python
class MCPConfig(BaseModel):
    # API Configuration
    api_key: str
    secret_key: str
    network: str = "mainnet"  # or "testnet"
    
    # Server Configuration
    port: int = 8003
    host: str = "127.0.0.1"
    
    # Features
    enable_websocket: bool = True
    enable_risk_checks: bool = True
    enable_simulation: bool = False
    
    # Risk Limits
    max_position_size: float = 10000  # USD
    max_leverage: float = 10.0
    max_orders: int = 50
    allowed_symbols: List[str] = None  # None = all
    
    # Performance
    cache_ttl: int = 60  # seconds
    rate_limit: int = 100  # requests per minute
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "mcp.log"
```

## WebSocket Streaming

```python
# Subscribe to real-time data
async def stream_data():
    async with mcp.websocket() as ws:
        # Subscribe to trades
        await ws.subscribe("trades", ["BTC", "ETH"])
        
        # Subscribe to orderbook
        await ws.subscribe("orderbook", ["HYPE"])
        
        # Receive updates
        async for msg in ws:
            print(f"Update: {msg}")
```

## Risk Management

The server includes built-in risk checks:

```python
# Position sizing based on risk
size = mcp.execute_tool(
    "calculate_position_size",
    {
        "symbol": "BTC",
        "risk_percent": 1.0,  # Risk 1% of account
        "stop_loss": 64000    # Stop loss price
    }
)

# Validate trade before execution
validation = mcp.execute_tool(
    "check_risk_limits",
    {
        "symbol": "BTC",
        "side": "BUY",
        "size": size,
        "leverage": 3
    }
)

if validation["approved"]:
    # Place order
    order = mcp.execute_tool("place_order", {...})
```

## Simulation Mode

Test strategies without real trades:

```python
config = MCPConfig(
    api_key="test",
    secret_key="test",
    enable_simulation=True
)

mcp = HyperliquidMCP(config)

# All trades are simulated
result = mcp.execute_tool(
    "place_order",
    {
        "symbol": "BTC",
        "side": "BUY",
        "size": 0.1,
        "price": 65000
    }
)
print(f"Simulated order: {result}")
```

## Error Handling

```python
from hyperliquid_mcp.exceptions import (
    MCPError,
    AuthenticationError,
    InsufficientBalanceError,
    RiskLimitExceededError,
    OrderValidationError
)

try:
    result = mcp.execute_tool("place_order", params)
except InsufficientBalanceError as e:
    print(f"Not enough balance: {e}")
except RiskLimitExceededError as e:
    print(f"Risk limit exceeded: {e}")
except MCPError as e:
    print(f"MCP error: {e}")
```

## Testing

Run tests with mock data:
```bash
# Unit tests
pytest tests/

# Integration tests with mock server
python tests/test_integration.py

# Load testing
python tests/test_performance.py
```

## Performance Optimization

- Response caching for market data
- Connection pooling for API calls
- Batch order operations
- WebSocket for real-time updates
- Async/await for concurrent operations

## Security Notes

- API keys stored in environment variables
- All sensitive data encrypted in transit
- Rate limiting to prevent abuse
- IP whitelist support
- Audit logging for all operations

## Support

- PyPI Package: https://pypi.org/project/hyperliquid-mcp/
- Documentation: https://hyperliquid-mcp.readthedocs.io/
- Issues: https://github.com/midodimori/hyperliquid-mcp/issues