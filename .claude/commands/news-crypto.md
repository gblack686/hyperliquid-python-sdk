# Crypto News Command

Fetch latest crypto news from CryptoCompare (50+ sources).

## Usage

Run the news aggregator to get the latest crypto headlines:

```bash
cd $REPO_ROOT
python integrations/news/crypto_news_aggregator.py news --limit 10
```

Or with JSON output:
```bash
python integrations/news/crypto_news_aggregator.py news --limit 10 --json
```

## Sample Output

```
[cryptopolitan] Aptos price prediction for 2026 - Will APT token hold bullish hopes?
  URL: https://www.cryptopolitan.com/aptos-price-prediction/
  Time: 2026-01-30T12:34:00+00:00

[cointelegraph] Bitcoin ETF inflows surge as institutional demand grows
  URL: https://cointelegraph.com/news/bitcoin-etf-inflows
  Time: 2026-01-30T11:22:00+00:00
```

## Data Fields

- `title`: Article headline
- `url`: Link to full article
- `source`: News outlet name
- `published_at`: ISO timestamp
- `body`: First 500 chars of content
- `tags`: Coin tags (BTC, ETH, etc.)
- `categories`: Topic categories
- `image_url`: Thumbnail image

## Rate Limits

- Free tier: ~50 requests/minute
- With API key: Higher limits available
