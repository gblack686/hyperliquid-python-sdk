# Fear & Greed Index Command

Get the Crypto Fear & Greed Index with historical data.

## Usage

```bash
cd $REPO_ROOT
python integrations/news/crypto_news_aggregator.py fear-greed
```

JSON output:
```bash
python integrations/news/crypto_news_aggregator.py fear-greed --json
```

## Sample Output

```
Fear & Greed Index: 16 (Extreme Fear)

7-Day History:
  2026-01-30: 16 (Extreme Fear)
  2026-01-29: 26 (Fear)
  2026-01-28: 29 (Fear)
  2026-01-27: 35 (Fear)
  2026-01-26: 42 (Fear)
  2026-01-25: 38 (Fear)
  2026-01-24: 31 (Fear)
```

## Index Scale

| Value Range | Classification |
|-------------|----------------|
| 0-24 | Extreme Fear |
| 25-44 | Fear |
| 45-55 | Neutral |
| 56-75 | Greed |
| 76-100 | Extreme Greed |

## Trading Signals

- **Extreme Fear (0-24)**: Potential buying opportunity - market oversold
- **Fear (25-44)**: Cautious accumulation zone
- **Neutral (45-55)**: Wait for clearer signals
- **Greed (56-75)**: Consider taking profits
- **Extreme Greed (76-100)**: High risk - potential market top

## JSON Response

```json
{
  "current": {
    "value": 16,
    "classification": "Extreme Fear",
    "timestamp": "2026-01-30T00:00:00+00:00"
  },
  "history": [
    {"value": 16, "classification": "Extreme Fear", "timestamp": "2026-01-30"},
    {"value": 26, "classification": "Fear", "timestamp": "2026-01-29"},
    {"value": 29, "classification": "Fear", "timestamp": "2026-01-28"}
  ]
}
```

## Data Source

- Provider: Alternative.me
- Update frequency: Daily
- API: `https://api.alternative.me/fng/`
- Cost: FREE, no authentication required
