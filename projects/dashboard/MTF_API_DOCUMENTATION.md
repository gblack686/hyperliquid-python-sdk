# MTF Data Feed API Documentation

## Overview
This API provides Multi-Timeframe (MTF) trading metrics and analysis for Hyperliquid markets. It processes real-time market data across multiple timeframes and generates trading signals with confidence scores.

## Installation & Setup

### Requirements
```bash
pip install fastapi uvicorn hyperliquid-python-sdk pandas numpy loguru python-dotenv
```

### Starting the Server
```bash
python run_mtf_api.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /api/health
```
Returns the API status and timestamp.

### Available Symbols
```
GET /api/symbols
```
Returns list of supported trading symbols and their mappings.

### Timeframes
```
GET /api/timeframes
```
Returns supported timeframes with descriptions.

### MTF Context Data
```
GET /api/mtf/context/{symbol}
```
Retrieves multi-timeframe context metrics for a specific symbol.

**Parameters:**
- `symbol` (path): Trading symbol (e.g., "BTC-USD")
- `exec_tf` (query): Execution timeframe in minutes (default: 5)

**Response Fields:**
- `sym`: Symbol ID
- `t`: Timestamp
- `p`: Current price
- `TF`: Array of timeframes [10080, 1440, 240, 60, 15, 5]
- `px_z`: Price z-scores per timeframe
- `v_z`: Volume z-scores per timeframe
- `vwap_z`: VWAP z-scores per timeframe
- `bb_pos`: Bollinger Band positions (0-1)
- `atr_n`: Normalized ATR values
- `cvd_s`: Cumulative volume delta slopes
- `cvd_lvl`: CVD levels
- `oi_d`: Open interest deltas
- `liq_n`: Liquidity norms
- `reg`: Regression trends (-1, 0, 1, 2)
- `L_sup`: Support level
- `L_res`: Resistance level
- `L_q_bid`: Bid liquidity
- `L_q_ask`: Ask liquidity

### Batch MTF Context
```
GET /api/mtf/batch
```
Retrieves MTF context for multiple symbols simultaneously.

**Parameters:**
- `symbols` (query): Comma-separated symbols (default: "BTC-USD,ETH-USD,SOL-USD")
- `exec_tf` (query): Execution timeframe in minutes (default: 5)

### Process MTF Data
```
POST /api/mtf/process
```
Processes MTF context data and generates trading signals.

**Request Body:** MTFContextData object

**Response Fields:**
- `s`: Structure scores per timeframe
- `c`: Confluence scores per timeframe
- `o`: Order flow scores per timeframe
- `f`: Final scores per timeframe
- `conf`: Confidence levels per timeframe (0-100)
- `sA`: Structure average
- `fA`: Final average
- `confA`: Average confidence
- `prob_cont`: Probability of continuation (%)
- `sc_in`: Entry score
- `sc_out`: Exit score
- `hold`: Hold signal (0 or 1)
- `tp_atr`: Take profit in ATR multiples
- `sl_atr`: Stop loss in ATR multiples
- `hedge`: Hedge percentage
- `reasons`: Array of reason codes

### Streaming Data
```
GET /api/mtf/stream/{symbol}
```
Server-sent events stream for real-time MTF data.

**Parameters:**
- `symbol` (path): Trading symbol
- `exec_tf` (query): Execution timeframe in minutes (default: 5)
- `interval` (query): Update interval in seconds (default: 60)

### Historical Data
```
GET /api/mtf/historical/{symbol}
```
Retrieves historical MTF context data.

**Parameters:**
- `symbol` (path): Trading symbol
- `start_time` (query): Start timestamp (optional)
- `end_time` (query): End timestamp (optional)
- `limit` (query): Maximum records to return (default: 100, max: 1000)

## Example Usage

### Python Client
```python
import requests

# Get MTF context for BTC
response = requests.get("http://localhost:8000/api/mtf/context/BTC-USD?exec_tf=5")
context = response.json()
print(f"BTC Price: ${context['p']:,.2f}")
print(f"Support: ${context['L_sup']:,.2f}")
print(f"Resistance: ${context['L_res']:,.2f}")

# Process the context for signals
response = requests.post("http://localhost:8000/api/mtf/process", json=context)
signals = response.json()
print(f"Confidence: {signals['confA']}%")
print(f"Hold Signal: {signals['hold']}")
```

### JavaScript Client
```javascript
// Fetch MTF context
fetch('http://localhost:8000/api/mtf/context/BTC-USD?exec_tf=5')
  .then(res => res.json())
  .then(context => {
    console.log(`BTC Price: $${context.p.toFixed(2)}`);
    
    // Process for signals
    return fetch('http://localhost:8000/api/mtf/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(context)
    });
  })
  .then(res => res.json())
  .then(signals => {
    console.log(`Confidence: ${signals.confA}%`);
  });
```

### Streaming Client
```javascript
const evtSource = new EventSource('http://localhost:8000/api/mtf/stream/BTC-USD?interval=30');

evtSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Price: $${data.context.p}`);
  console.log(`Confidence: ${data.output.confA}%`);
};
```

## Testing

Run the test suite:
```bash
python test_mtf_api.py
```

## Architecture

The API integrates with the Hyperliquid SDK to:
1. Fetch real-time market data
2. Calculate technical indicators across multiple timeframes
3. Generate z-scores for normalization
4. Compute support/resistance levels
5. Analyze orderbook liquidity
6. Process signals through scoring algorithms
7. Output actionable trading metrics

## Rate Limits

- Default update interval: 60 seconds for streaming
- Maximum historical records: 1000 per request
- Recommended polling interval: 5+ seconds for real-time data

## Error Handling

All endpoints return appropriate HTTP status codes:
- 200: Success
- 404: Symbol or data not found
- 500: Internal server error

Error responses include detail messages:
```json
{
  "detail": "Error description"
}
```