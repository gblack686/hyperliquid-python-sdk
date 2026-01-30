# Kukapay Hyperliquid Whale Alert MCP Server

Real-time whale trade monitoring and alerting system for Hyperliquid.

## Features

- Monitor trades over $1 million in real-time
- Track whale wallets and their positions
- Generate summaries of whale activity
- Customizable alert thresholds
- WebSocket streaming for instant notifications

## Installation

### Option 1: Clone and Install
```bash
python setup.py
```

### Option 2: Manual Setup
```bash
git clone https://github.com/kukapay/hyperliquid-whalealert-mcp.git
cd hyperliquid-whalealert-mcp
pip install -r requirements.txt
```

## Configuration

Create a `config.json` file:
```json
{
  "api_key": "your_api_key",
  "secret_key": "your_secret_key",
  "network": "mainnet",
  "port": 8002,
  "alert_threshold": 1000000,
  "symbols": ["BTC", "ETH", "SOL", "HYPE"],
  "webhook_url": "optional_discord_or_slack_webhook"
}
```

## Available Tools

### Alert Tools
- `get_whale_alerts` - Get recent whale trades
  - Parameters:
    - `min_value`: Minimum trade value (default: $1M)
    - `hours`: Look back period (default: 24)
    - `symbol`: Filter by symbol (optional)

- `get_whale_positions` - Track large position holders
  - Parameters:
    - `min_position_value`: Minimum position size
    - `top_n`: Number of whales to track

### Analysis Tools
- `summarize_whale_activity` - AI prompt for whale activity summary
- `analyze_whale_patterns` - Identify trading patterns
- `get_whale_statistics` - Statistical analysis of whale trades

### Monitoring Tools
- `start_monitoring` - Begin real-time monitoring
- `stop_monitoring` - Stop monitoring
- `get_monitoring_status` - Check monitoring status

## Usage

### Start the Server
```bash
python server.py
```

### Example Client Usage
```python
import requests
import asyncio
import websockets

# Get recent whale alerts
payload = {
    "method": "get_whale_alerts",
    "params": {
        "min_value": 500000,  # $500k minimum
        "hours": 12
    },
    "id": "1"
}
response = requests.post("http://localhost:8002/mcp/execute", json=payload)
alerts = response.json()

# WebSocket streaming
async def stream_whales():
    async with websockets.connect("ws://localhost:8002/ws") as ws:
        while True:
            alert = await ws.recv()
            print(f"🐋 WHALE ALERT: {alert}")

asyncio.run(stream_whales())
```

## Alert Format

```json
{
  "timestamp": "2025-01-06T10:30:00Z",
  "symbol": "BTC",
  "side": "BUY",
  "size": 15.5,
  "price": 65000,
  "value": 1007500,
  "address": "0x1234...5678",
  "exchange": "hyperliquid",
  "alert_type": "trade",
  "significance": "high"
}
```

## WebSocket Events

The server broadcasts the following events via WebSocket:

- `whale_trade` - Large trade executed
- `whale_position_opened` - New whale position
- `whale_position_closed` - Whale exits position
- `whale_liquidation` - Large liquidation event
- `market_impact` - Trade causing significant price movement

## Notification Integrations

### Discord Webhook
```python
config = {
    "webhook_url": "https://discord.com/api/webhooks/...",
    "alert_format": "discord"
}
```

### Telegram Bot
```python
config = {
    "telegram_bot_token": "your_bot_token",
    "telegram_chat_id": "your_chat_id",
    "alert_format": "telegram"
}
```

### Custom Webhook
```python
config = {
    "custom_webhook": "https://your-api.com/whale-alert",
    "webhook_headers": {"Authorization": "Bearer token"}
}
```

## Testing

Use the mock server to test whale alerts:
```bash
cd ../../../hyperliquid-trading-dashboard
python mcp_test_server.py
```

## Performance Optimization

- Filters trades client-side to reduce processing
- Caches whale addresses for faster lookups
- Batches database writes for efficiency
- Uses WebSocket for real-time updates

## Security Notes

- Monitor public trade data only (no private keys needed for basic monitoring)
- API keys required only for detailed wallet analysis
- Rate limiting implemented to prevent API abuse
- Whale addresses are pseudonymized in public alerts

## Support

Repository: https://github.com/kukapay/hyperliquid-whalealert-mcp