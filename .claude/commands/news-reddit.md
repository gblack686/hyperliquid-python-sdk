# Reddit Crypto News Command

Fetch hot posts from crypto subreddits (r/CryptoCurrency, r/Bitcoin, etc.).

## Usage

Get hot posts from r/CryptoCurrency:
```bash
cd $REPO_ROOT
python integrations/news/crypto_news_aggregator.py reddit --limit 10
```

Specify a different subreddit:
```bash
python integrations/news/crypto_news_aggregator.py reddit --subreddit Bitcoin --limit 10
```

JSON output:
```bash
python integrations/news/crypto_news_aggregator.py reddit --limit 10 --json
```

## Sample Output

```
[Score: 2847] Bitcoin just broke $150k - here's why this time is different
  https://reddit.com/r/CryptoCurrency/comments/abc123/...

[Score: 1523] Daily Crypto Discussion - January 30, 2026
  https://reddit.com/r/CryptoCurrency/comments/def456/...

[Score: 892] Ethereum L2s now processing more transactions than mainnet
  https://reddit.com/r/CryptoCurrency/comments/ghi789/...
```

## Available Subreddits

- `CryptoCurrency` (10M+ members) - General crypto discussion
- `Bitcoin` - Bitcoin-specific news
- `ethereum` - Ethereum ecosystem
- `altcoin` - Altcoin discussion

## Data Fields

- `title`: Post title
- `url`: Reddit permalink
- `score`: Upvotes
- `source`: Subreddit name
- `published_at`: Post timestamp
- `body`: Self-text preview (500 chars)
- `tags`: Post flair

## Rate Limits

- No auth required for public data
- ~60 requests/minute
