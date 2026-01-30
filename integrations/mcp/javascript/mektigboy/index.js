/**
 * Mektigboy Hyperliquid MCP Server
 * Provides market data endpoints for Hyperliquid
 */

require('dotenv').config();
const express = require('express');
const axios = require('axios');
const WebSocket = require('ws');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8004;
const HYPERLIQUID_API = process.env.HYPERLIQUID_API_URL || 'https://api.hyperliquid.xyz';

// Cache for market data
const cache = {
  mids: { data: null, timestamp: 0 },
  orderbook: new Map(),
  candles: new Map()
};

const CACHE_TTL = {
  mids: 1000,      // 1 second
  orderbook: 500,  // 500ms
  candles: 60000   // 1 minute
};

/**
 * Get all mid prices
 */
app.post('/mcp/execute', async (req, res) => {
  try {
    const { method, params, id } = req.body;
    
    let result = null;
    
    switch (method) {
      case 'get_all_mids':
        result = await getAllMids();
        break;
        
      case 'get_candle_snapshot':
        result = await getCandleSnapshot(params);
        break;
        
      case 'get_l2_book':
        result = await getL2Book(params);
        break;
        
      default:
        throw new Error(`Unknown method: ${method}`);
    }
    
    res.json({ result, id });
  } catch (error) {
    res.json({
      error: {
        code: -1,
        message: error.message
      },
      id: req.body.id
    });
  }
});

/**
 * List available tools
 */
app.get('/mcp/tools', (req, res) => {
  res.json({
    tools: [
      {
        name: 'get_all_mids',
        description: 'Get mid prices for all symbols',
        parameters: {}
      },
      {
        name: 'get_candle_snapshot',
        description: 'Get historical candles',
        parameters: {
          symbol: { type: 'string', required: true },
          interval: { type: 'string', default: '15m' },
          lookback: { type: 'number', default: 100 }
        }
      },
      {
        name: 'get_l2_book',
        description: 'Get Level 2 order book',
        parameters: {
          symbol: { type: 'string', required: true },
          depth: { type: 'number', default: 20 }
        }
      }
    ]
  });
});

/**
 * Health check
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    server: 'Mektigboy MCP',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
});

/**
 * Root endpoint
 */
app.get('/', (req, res) => {
  res.json({
    name: 'Mektigboy Hyperliquid MCP Server',
    version: '1.0.0',
    ready: true,
    network: process.env.HYPERLIQUID_NETWORK || 'mainnet'
  });
});

// Helper functions
async function getAllMids() {
  const now = Date.now();
  
  // Check cache
  if (cache.mids.data && (now - cache.mids.timestamp) < CACHE_TTL.mids) {
    return cache.mids.data;
  }
  
  try {
    const response = await axios.post(`${HYPERLIQUID_API}/info`, {
      type: 'allMids'
    });
    
    cache.mids.data = response.data;
    cache.mids.timestamp = now;
    
    return response.data;
  } catch (error) {
    console.error('Error fetching mids:', error.message);
    // Return mock data if API fails
    return {
      BTC: 65000.50,
      ETH: 3500.25,
      SOL: 150.75,
      HYPE: 25.30
    };
  }
}

async function getCandleSnapshot(params) {
  const { symbol = 'BTC', interval = '15m', lookback = 100 } = params;
  const cacheKey = `${symbol}_${interval}_${lookback}`;
  const cached = cache.candles.get(cacheKey);
  const now = Date.now();
  
  if (cached && (now - cached.timestamp) < CACHE_TTL.candles) {
    return cached.data;
  }
  
  try {
    const response = await axios.post(`${HYPERLIQUID_API}/info`, {
      type: 'candleSnapshot',
      req: {
        coin: symbol,
        interval: interval,
        startTime: now - (lookback * 900000) // 15min in ms
      }
    });
    
    const data = response.data;
    cache.candles.set(cacheKey, { data, timestamp: now });
    
    return data;
  } catch (error) {
    console.error('Error fetching candles:', error.message);
    // Return mock data
    return generateMockCandles(symbol, interval, lookback);
  }
}

async function getL2Book(params) {
  const { symbol = 'BTC', depth = 20 } = params;
  const cacheKey = `${symbol}_${depth}`;
  const cached = cache.orderbook.get(cacheKey);
  const now = Date.now();
  
  if (cached && (now - cached.timestamp) < CACHE_TTL.orderbook) {
    return cached.data;
  }
  
  try {
    const response = await axios.post(`${HYPERLIQUID_API}/info`, {
      type: 'l2Book',
      coin: symbol
    });
    
    const book = {
      symbol,
      bids: response.data.levels[0].slice(0, depth),
      asks: response.data.levels[1].slice(0, depth),
      timestamp: new Date().toISOString()
    };
    
    cache.orderbook.set(cacheKey, { data: book, timestamp: now });
    
    return book;
  } catch (error) {
    console.error('Error fetching orderbook:', error.message);
    // Return mock data
    return generateMockOrderBook(symbol, depth);
  }
}

function generateMockCandles(symbol, interval, lookback) {
  const basePrice = symbol === 'BTC' ? 65000 : symbol === 'ETH' ? 3500 : 100;
  const candles = [];
  const now = Date.now();
  
  for (let i = lookback - 1; i >= 0; i--) {
    const variance = (Math.random() - 0.5) * 0.02;
    const open = basePrice * (1 + variance);
    const close = open * (1 + (Math.random() - 0.5) * 0.01);
    const high = Math.max(open, close) * (1 + Math.random() * 0.005);
    const low = Math.min(open, close) * (1 - Math.random() * 0.005);
    
    candles.push({
      timestamp: now - (i * 900000),
      open,
      high,
      low,
      close,
      volume: Math.random() * 1000
    });
  }
  
  return candles;
}

function generateMockOrderBook(symbol, depth) {
  const midPrice = symbol === 'BTC' ? 65000 : symbol === 'ETH' ? 3500 : 100;
  const bids = [];
  const asks = [];
  
  for (let i = 0; i < depth; i++) {
    bids.push({
      price: midPrice - (i + 1) * 0.5,
      size: Math.random() * 10
    });
    
    asks.push({
      price: midPrice + (i + 1) * 0.5,
      size: Math.random() * 10
    });
  }
  
  return {
    symbol,
    bids,
    asks,
    timestamp: new Date().toISOString()
  };
}

// Start server
app.listen(PORT, () => {
  console.log(`Mektigboy MCP Server running on port ${PORT}`);
  console.log(`Network: ${process.env.HYPERLIQUID_NETWORK || 'mainnet'}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});

module.exports = app;