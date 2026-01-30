# Mektigboy Hyperliquid MCP Server

TypeScript/JavaScript MCP server for Hyperliquid market data.

## Features

- Real-time mid prices for all symbols
- Historical candle data (OHLCV)
- Level 2 order book snapshots
- TypeScript type safety
- Easy integration with Claude Desktop

## Installation

### Option 1: NPX (Recommended for Claude Desktop)
```bash
npx -y @mektigboy/server-hyperliquid
```

### Option 2: Clone and Install
```bash
# Run setup script
bash setup.sh

# Or manually
git clone https://github.com/mektigboy/server-hyperliquid.git
cd server-hyperliquid
npm install
```

## Configuration

### For Claude Desktop
Add to your Claude Desktop config:
```json
{
  "mcpServers": {
    "hyperliquid": {
      "command": "npx",
      "args": ["-y", "@mektigboy/server-hyperliquid"]
    }
  }
}
```

### Standalone Configuration
Create `.env` file:
```env
HYPERLIQUID_API_KEY=your_api_key
HYPERLIQUID_SECRET_KEY=your_secret_key
HYPERLIQUID_NETWORK=mainnet
PORT=8004
```

## Available Tools

### `get_all_mids`
Get mid prices for all trading pairs.

**Parameters:** None

**Response:**
```json
{
  "BTC": 65000.50,
  "ETH": 3500.25,
  "SOL": 150.75,
  ...
}
```

### `get_candle_snapshot`
Get historical OHLCV candle data.

**Parameters:**
- `symbol` (string): Trading symbol (e.g., "BTC")
- `interval` (string): Candle interval ("1m", "5m", "15m", "1h", "4h", "1d")
- `lookback` (number): Number of candles to fetch

**Response:**
```json
[
  {
    "timestamp": 1704067200000,
    "open": 65000,
    "high": 65500,
    "low": 64500,
    "close": 65250,
    "volume": 1234.56
  },
  ...
]
```

### `get_l2_book`
Get Level 2 order book data.

**Parameters:**
- `symbol` (string): Trading symbol (e.g., "BTC")
- `depth` (number): Book depth (default: 20)

**Response:**
```json
{
  "symbol": "BTC",
  "bids": [
    {"price": 64999.50, "size": 1.5},
    {"price": 64999.00, "size": 2.3},
    ...
  ],
  "asks": [
    {"price": 65000.50, "size": 1.2},
    {"price": 65001.00, "size": 2.1},
    ...
  ],
  "timestamp": "2024-01-06T10:30:00Z"
}
```

## Usage Examples

### JavaScript Client
```javascript
const axios = require('axios');

// Get all mid prices
async function getMidPrices() {
  const response = await axios.post('http://localhost:8004/mcp/execute', {
    method: 'get_all_mids',
    params: {},
    id: '1'
  });
  return response.data.result;
}

// Get BTC candles
async function getBTCCandles() {
  const response = await axios.post('http://localhost:8004/mcp/execute', {
    method: 'get_candle_snapshot',
    params: {
      symbol: 'BTC',
      interval: '15m',
      lookback: 100
    },
    id: '2'
  });
  return response.data.result;
}

// Get order book
async function getOrderBook(symbol) {
  const response = await axios.post('http://localhost:8004/mcp/execute', {
    method: 'get_l2_book',
    params: {
      symbol: symbol,
      depth: 10
    },
    id: '3'
  });
  return response.data.result;
}
```

### TypeScript Client
```typescript
interface MidPrices {
  [symbol: string]: number;
}

interface Candle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface OrderBook {
  symbol: string;
  bids: Array<{price: number; size: number}>;
  asks: Array<{price: number; size: number}>;
  timestamp: string;
}

async function fetchMarketData(): Promise<void> {
  const mids: MidPrices = await getMidPrices();
  const candles: Candle[] = await getBTCCandles();
  const book: OrderBook = await getOrderBook('ETH');
  
  console.log(`BTC Price: $${mids.BTC}`);
  console.log(`Latest candle close: $${candles[candles.length - 1].close}`);
  console.log(`ETH Best bid: $${book.bids[0].price}`);
}
```

## Testing

```bash
cd server-hyperliquid
npm test
```

## Performance

- Caches mid prices for 1 second
- Caches order book for 500ms
- Automatic reconnection on WebSocket disconnect
- Rate limiting: 100 requests per minute

## Deployment

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 8004
CMD ["npm", "start"]
```

### PM2
```bash
pm2 start server.js --name hyperliquid-mcp
pm2 save
pm2 startup
```

## Support

- Repository: https://github.com/mektigboy/server-hyperliquid
- NPM Package: https://www.npmjs.com/package/@mektigboy/server-hyperliquid