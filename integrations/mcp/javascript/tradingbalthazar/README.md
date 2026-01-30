# TradingBalthazar Hyperliquid MCP Server v9

Full-featured MCP server with complete trading support for spot and futures.

## Features

- **Complete API Coverage** - All Hyperliquid endpoints
- **Spot & Futures Trading** - Full order management
- **Account Management** - Balances, positions, transfers
- **Vault Operations** - Vault management and delegation
- **WebSocket Support** - Real-time data streaming
- **Error Validation** - Comprehensive error handling
- **Multi-Account** - Sub-account support

## Installation

### Clone and Install
```bash
git clone https://github.com/MCP-Mirror/TradingBalthazar_hyperliquid-mcp-server-v9.git
cd TradingBalthazar_hyperliquid-mcp-server-v9
npm install
```

## Configuration

Create `config.json`:
```json
{
  "api": {
    "key": "your_api_key",
    "secret": "your_secret_key",
    "network": "mainnet"
  },
  "server": {
    "port": 8005,
    "host": "127.0.0.1"
  },
  "features": {
    "spot": true,
    "futures": true,
    "vaults": true,
    "subaccounts": true,
    "websocket": true
  },
  "limits": {
    "maxOrders": 100,
    "maxPositions": 50,
    "maxLeverage": 20
  }
}
```

## Available Tools (Complete List)

### Market Data
- `get_all_mids` - All mid prices
- `get_l2_snapshot` - Order book snapshot
- `get_candles` - Historical OHLCV
- `get_trades` - Recent trades
- `get_funding_rates` - Funding rates
- `get_open_interest` - Open interest
- `get_metadata` - Exchange metadata

### Spot Trading
- `spot_place_order` - Place spot order
- `spot_cancel_order` - Cancel spot order
- `spot_modify_order` - Modify spot order
- `spot_get_orders` - Get spot orders
- `spot_get_fills` - Get spot fills
- `spot_get_balances` - Get spot balances

### Futures Trading
- `place_order` - Place futures order
- `cancel_order` - Cancel order
- `cancel_all_orders` - Cancel all orders
- `modify_order` - Modify order
- `close_position` - Close position
- `close_all_positions` - Close all positions
- `set_leverage` - Set leverage
- `get_positions` - Get positions
- `get_open_orders` - Get open orders

### Account Management
- `get_account_info` - Account overview
- `get_balances` - All balances
- `get_margin_info` - Margin details
- `get_pnl` - P&L information
- `get_trade_history` - Historical trades
- `get_funding_history` - Funding payments
- `get_deposit_address` - Deposit addresses
- `withdraw` - Withdraw funds
- `transfer` - Internal transfers

### Vault Operations
- `create_vault` - Create new vault
- `deposit_to_vault` - Deposit funds
- `withdraw_from_vault` - Withdraw funds
- `delegate_to_vault` - Delegate trading
- `undelegate_from_vault` - Remove delegation
- `get_vault_info` - Vault details
- `get_vault_positions` - Vault positions
- `get_vault_pnl` - Vault P&L

### Sub-Accounts
- `create_subaccount` - Create sub-account
- `get_subaccounts` - List sub-accounts
- `transfer_between_subaccounts` - Transfer funds
- `get_subaccount_info` - Sub-account details
- `switch_subaccount` - Switch active account

### Advanced Features
- `get_referral_info` - Referral statistics
- `get_rewards` - Staking rewards
- `get_leaderboard` - Trading leaderboard
- `batch_orders` - Batch order operations
- `get_exchange_status` - System status

## Usage Examples

### Place Order with Risk Checks
```javascript
const client = require('./client');

async function placeOrderWithChecks(symbol, side, size, price) {
  // Check account balance
  const account = await client.execute('get_account_info');
  const availableBalance = account.result.available_balance;
  
  // Check margin requirements
  const marginReq = await client.execute('get_margin_info', {
    symbol, size, leverage: 5
  });
  
  if (marginReq.result.required_margin > availableBalance) {
    throw new Error('Insufficient balance for margin');
  }
  
  // Place order
  const order = await client.execute('place_order', {
    symbol,
    side,
    size,
    price,
    order_type: 'LIMIT',
    reduce_only: false,
    post_only: true
  });
  
  return order.result;
}
```

### Vault Management
```javascript
async function manageVault(vaultId) {
  // Get vault info
  const info = await client.execute('get_vault_info', { vault_id: vaultId });
  
  // Check performance
  const pnl = await client.execute('get_vault_pnl', { vault_id: vaultId });
  
  // Deposit if profitable
  if (pnl.result.total_pnl > 0) {
    await client.execute('deposit_to_vault', {
      vault_id: vaultId,
      amount: 1000
    });
  }
  
  // Get positions
  const positions = await client.execute('get_vault_positions', {
    vault_id: vaultId
  });
  
  return {
    info: info.result,
    pnl: pnl.result,
    positions: positions.result
  };
}
```

### WebSocket Streaming
```javascript
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8005/ws');

ws.on('open', () => {
  // Subscribe to trades
  ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'trades',
    symbols: ['BTC', 'ETH']
  }));
  
  // Subscribe to orderbook
  ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'orderbook',
    symbols: ['HYPE']
  }));
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  console.log('Update:', msg);
});
```

### Batch Operations
```javascript
async function batchOperations() {
  // Cancel all orders and place new ones atomically
  const batch = await client.execute('batch_orders', {
    cancel_all: true,
    new_orders: [
      {
        symbol: 'BTC',
        side: 'BUY',
        size: 0.1,
        price: 64000,
        order_type: 'LIMIT'
      },
      {
        symbol: 'ETH',
        side: 'BUY',
        size: 1,
        price: 3400,
        order_type: 'LIMIT'
      }
    ]
  });
  
  return batch.result;
}
```

## Error Handling

```javascript
try {
  const result = await client.execute('place_order', params);
} catch (error) {
  if (error.code === 'INSUFFICIENT_BALANCE') {
    console.error('Not enough funds');
  } else if (error.code === 'INVALID_LEVERAGE') {
    console.error('Leverage too high');
  } else if (error.code === 'RATE_LIMIT') {
    console.error('Rate limited, retry after:', error.retry_after);
  } else {
    console.error('Unknown error:', error);
  }
}
```

## Performance Features

- Connection pooling for API calls
- Request batching for efficiency
- Response caching (configurable TTL)
- Automatic retry with exponential backoff
- Circuit breaker for failing endpoints

## Security

- API keys encrypted at rest
- Request signing for authentication
- IP whitelist support
- Rate limiting per endpoint
- Audit logging with rotation

## Testing

```bash
# Unit tests
npm test

# Integration tests
npm run test:integration

# Load testing
npm run test:load
```

## Deployment

### Docker Compose
```yaml
version: '3.8'
services:
  mcp-server:
    image: tradingbalthazar/hyperliquid-mcp:v9
    ports:
      - "8005:8005"
    environment:
      - API_KEY=${HYPERLIQUID_API_KEY}
      - SECRET_KEY=${HYPERLIQUID_SECRET_KEY}
    volumes:
      - ./config.json:/app/config.json
    restart: unless-stopped
```

## Support

- Repository: https://github.com/MCP-Mirror/TradingBalthazar_hyperliquid-mcp-server-v9
- Documentation: Full API reference in `/docs`