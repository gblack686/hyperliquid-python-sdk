# Kiyotaka Screenshot Service

Automated screenshot capture service for Kiyotaka trading charts using Playwright.

## Features

- Automated login to Kiyotaka platform
- Single and batch screenshot capture
- RESTful API for screenshot management
- Docker containerized service
- Persistent screenshot storage

## Setup

1. Add Kiyotaka credentials to `.env`:
```env
KIYOTAKA_USERNAME=your_email@example.com
KIYOTAKA_PASSWORD=your_password
```

2. Build and run with Docker Compose:
```bash
docker-compose up screenshot-service
```

## API Endpoints

### Health Check
```bash
GET http://localhost:8003/health
```

### Capture Single Screenshot
```bash
POST http://localhost:8003/screenshot
Content-Type: application/json

{
  "chart_id": "YFvw7cHN",
  "symbol": "HYPEUSDT",
  "exchange": "BINANCE.F",
  "timeframe": "1h"
}
```

### Capture Multiple Screenshots
```bash
POST http://localhost:8003/screenshot/batch
Content-Type: application/json

{
  "charts": [
    {"symbol": "HYPEUSDT", "timeframe": "1m"},
    {"symbol": "HYPEUSDT", "timeframe": "1h"},
    {"symbol": "BTCUSDT", "timeframe": "4h"}
  ]
}
```

### List Screenshots
```bash
GET http://localhost:8003/screenshots/list
```

### Get Screenshot
```bash
GET http://localhost:8003/screenshot/{filename}
```

### Delete Screenshot
```bash
DELETE http://localhost:8003/screenshot/{filename}
```

## Directory Structure

```
hyperliquid-trading-dashboard/
├── screenshot_service.py      # Core screenshot service
├── screenshot_api.py          # FastAPI endpoints
├── Dockerfile.screenshot      # Docker configuration
├── docker-compose.yml         # Service orchestration
└── screenshots/              # Screenshot storage (mounted volume)
```

## Screenshots Location

Screenshots are saved to `./screenshots/` directory which is mounted as a Docker volume.

Format: `kiyotaka_{SYMBOL}_{TIMEFRAME}_{TIMESTAMP}.png`

## Testing

Run standalone:
```bash
python screenshot_api.py
```

Test with curl:
```bash
curl -X POST http://localhost:8003/screenshot \
  -H "Content-Type: application/json" \
  -d '{"symbol": "HYPEUSDT", "timeframe": "1h"}'
```