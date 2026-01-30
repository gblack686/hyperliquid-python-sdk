# Trending Coins Command

Get trending cryptocurrencies from CoinGecko search data.

## Usage

```bash
cd $REPO_ROOT
python integrations/news/crypto_news_aggregator.py trending
```

JSON output:
```bash
python integrations/news/crypto_news_aggregator.py trending --json
```

## Sample Output

```
Trending Coins:
  ULTIMA - Ultima (Rank #287)
  BTC - Bitcoin (Rank #1)
  SOL - Solana (Rank #5)
  DOGE - Dogecoin (Rank #8)
  PEPE - Pepe (Rank #23)
  WIF - dogwifhat (Rank #56)
  BONK - Bonk (Rank #62)
```

## Data Fields

- `symbol`: Token symbol
- `name`: Full name
- `market_cap_rank`: Current rank by market cap
- `price_btc`: Price in BTC
- `score`: Trending score (0 = highest)

## JSON Response

```json
[
  {
    "name": "Ultima",
    "symbol": "ULTIMA",
    "market_cap_rank": 287,
    "price_btc": 0.0598,
    "score": 0
  },
  {
    "name": "Bitcoin",
    "symbol": "BTC",
    "market_cap_rank": 1,
    "price_btc": 1.0,
    "score": 1
  }
]
```

## Rate Limits

- CoinGecko free tier: 10-30 calls/minute
- No API key required
