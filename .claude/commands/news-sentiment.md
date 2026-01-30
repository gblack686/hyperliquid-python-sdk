# Market Sentiment Command

Get comprehensive crypto market sentiment from multiple sources.

## Usage

```bash
cd $REPO_ROOT
python integrations/news/crypto_news_aggregator.py sentiment
```

JSON output:
```bash
python integrations/news/crypto_news_aggregator.py sentiment --json
```

## Sample Output

```
Fear & Greed: 16 (Extreme Fear)
Reddit Sentiment: Bearish
Trending: ULTIMA, BTC, SOL, DOGE, PEPE
```

## Data Sources Combined

1. **Fear & Greed Index** (Alternative.me)
   - Value: 0-100 scale
   - Classifications: Extreme Fear, Fear, Neutral, Greed, Extreme Greed

2. **Reddit Sentiment** (r/CryptoCurrency)
   - Based on average post scores
   - Bullish (>500), Neutral (100-500), Bearish (<100)

3. **Trending Coins** (CoinGecko)
   - Top 10 trending by search volume
   - Updated every few hours

## JSON Response Structure

```json
{
  "fear_greed_value": 16,
  "fear_greed_classification": "Extreme Fear",
  "reddit_sentiment": "Bearish",
  "trending_coins": ["ULTIMA", "BTC", "SOL", "DOGE", "PEPE"],
  "timestamp": "2026-01-30T12:00:00+00:00"
}
```

## Historical Data

Get 7-day Fear & Greed history:
```bash
python integrations/news/crypto_news_aggregator.py fear-greed
```
