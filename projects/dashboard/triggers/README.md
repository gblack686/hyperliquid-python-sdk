# Real-time Trigger Strategy System

Ultra-low latency (<60s end-to-end) pre-emptive trading system for Hyperliquid.

## Architecture

```
WebSocket Streams (10-250ms)
       ↓
Feature Cache (≤1s updates)
       ↓
Trigger Engine (≤50ms eval)
       ↓
    ┌──┴──┐
    ↓     ↓
Protective   Analysis
Orders       Workflow
(≤1s)        (≤20s)
    ↓     ↓
    └──┬──┘
       ↓
Final Decision
```

## Components

### 1. **Streamer** (`streamer.py`)
- WebSocket connection to Hyperliquid
- Real-time feature calculation
- Trigger evaluation every 5 seconds
- Protective order placement

### 2. **Analyzer** (`analyzer.py`)
- FastAPI service for trigger analysis
- LLM integration for complex decisions
- Local statistical fallback
- n8n webhook support

### 3. **Configuration** (`triggers.yaml`)
- Trigger definitions and thresholds
- Order sizing parameters
- Cooldown periods

## Trigger Types

### Squeeze Triggers
- **squeeze_down**: Shorts trapped, expect violent up move
- **squeeze_up**: Longs trapped, expect violent down move

### Reversion Triggers
- **reversion_fade_up**: Extreme deviation up, fade the move
- **reversion_fade_down**: Extreme deviation down, expect bounce

### Breakout Triggers
- **breakout_continuation_long**: Momentum acceleration up
- **breakout_continuation_short**: Momentum acceleration down

### Liquidation Triggers
- **liquidation_cascade_long**: Potential long liquidations
- **liquidation_cascade_short**: Potential short liquidations

## Features Tracked

- **CVD Slope**: Cumulative Volume Delta momentum (1m, 5m)
- **OI Delta**: Open Interest changes (5m, 15m percentages)
- **L/S Ratio**: Long/Short positioning ratio
- **Funding Rate**: In basis points
- **VWAP Z-score**: Standard deviations from VWAP
- **Basis**: Spot vs Perpetual differential
- **Trade Burst**: Volume spike detection

## Quick Start

### 1. Install Dependencies

```bash
pip install websockets aiohttp pyyaml fastapi uvicorn python-dotenv
```

### 2. Configure Environment

Create `.env` file:
```env
# Optional: For LLM analysis
OPENAI_API_KEY=your_api_key

# Optional: For n8n integration
N8N_WEBHOOK_URL=https://your-n8n-instance/webhook/trigger-analysis

# Hyperliquid (if using authenticated endpoints)
HYPERLIQUID_API_KEY=your_private_key
```

### 3. Run Streamer

```bash
python triggers/streamer.py
```

### 4. Run Analyzer (separate terminal)

```bash
python triggers/analyzer.py
```

## Testing

### Test Individual Components

```python
# Test feature calculation
python -c "from streamer import FeatureCache; cache = FeatureCache(); print(cache.compute_features('BTC'))"

# Test trigger evaluation
python -c "from streamer import TriggerEngine; engine = TriggerEngine(); print(engine.get_default_config())"

# Test analyzer API
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"trigger":"squeeze_up","symbol":"BTC","timestamp":1234567890,"features":{"last_px":100000,"cvd_slope_1m":0.5}}'
```

### Monitor Performance

The system logs key metrics:
- Trigger fire events
- Order placement latency
- Analysis workflow timing
- Feature calculation performance

## Production Deployment

### Docker Setup

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY triggers/ ./triggers/
COPY .env .

# Run both services
CMD ["sh", "-c", "python triggers/analyzer.py & python triggers/streamer.py"]
```

### Monitoring

Key metrics to track:
- **Trigger Rate**: Should be 0-5 per minute max
- **False Positive Rate**: Track cancelled orders
- **Latency**: Stream→Trigger→Order should be <1s
- **Analysis Time**: LLM response should be <20s

### Safety Features

1. **Cooldown Periods**: Prevent duplicate triggers (60s default)
2. **Position Limits**: Max 25% account per trigger
3. **Concurrent Limits**: Max 3 active triggers
4. **Fallback Logic**: Local analysis if LLM fails
5. **Stop Loss**: Always set at 0.7 ATR minimum

## Integration

### With n8n Workflow

1. Set webhook URL in `.env`
2. n8n receives trigger data
3. n8n processes and returns decision
4. System adjusts orders based on decision

### With Trading System

```python
from triggers.streamer import TriggerStreamer

# Custom order handler
class MyOrderManager:
    async def place_protective_order(self, symbol, side, features):
        # Your order logic here
        pass

# Use custom manager
streamer = TriggerStreamer()
streamer.order_manager = MyOrderManager()
await streamer.run()
```

## Customization

### Add New Trigger

Edit `triggers.yaml`:
```yaml
my_custom_trigger:
  description: "My custom signal"
  when_all:
    cvd_slope_1m_gt: 0.5
    trade_burst: true
  actions:
    - protective_long
    - start_analysis
```

### Modify Features

Edit `streamer.py`:
```python
def compute_features(self, symbol: str) -> Dict[str, float]:
    features = super().compute_features(symbol)
    # Add custom feature
    features["my_feature"] = self.calculate_my_feature(symbol)
    return features
```

## Performance Optimization

- **Use PyPy**: 2-3x faster for feature calculation
- **Redis Cache**: Share features across processes
- **Compiled Regex**: For condition matching
- **Numba JIT**: For numerical computations

## Troubleshooting

### Common Issues

1. **No triggers firing**
   - Check WebSocket connection
   - Verify feature calculation
   - Review trigger thresholds

2. **Too many triggers**
   - Increase cooldown periods
   - Tighten trigger conditions
   - Add quorum requirements

3. **High latency**
   - Reduce evaluation interval
   - Optimize feature calculation
   - Use local analysis only

## License

MIT