---
model: haiku
description: Quick 60-second news scan - headlines, sentiment, trending
argument-hint: none
allowed-tools: Bash(python:*), Bash(curl:*), Read
---

# Quick News Scan

## Purpose

Fast 60-second market pulse check. Get headlines, sentiment, and trending coins without deep analysis.

## Instructions

Run all data fetches in parallel, output concise summary directly to user.

## Workflow

### Parallel Data Fetch

Run these **simultaneously**:

#### 1. Fear & Greed
```bash
curl -s "https://api.alternative.me/fng/?limit=1" | python -c "
import sys, json
data = json.load(sys.stdin)
item = data.get('data', [{}])[0]
print(f\"Fear & Greed: {item.get('value', 'N/A')} ({item.get('value_classification', 'N/A')})\")"
```

#### 2. Trending
```bash
curl -s "https://api.coingecko.com/api/v3/search/trending" | python -c "
import sys, json
data = json.load(sys.stdin)
coins = [item['item']['symbol'] for item in data.get('coins', [])[:7]]
print(f\"Trending: {', '.join(coins)}\")"
```

#### 3. Top 5 Headlines
```bash
curl -s "https://min-api.cryptocompare.com/data/v2/news/?limit=5" | python -c "
import sys, json
data = json.load(sys.stdin)
print('Headlines:')
for item in data.get('Data', [])[:5]:
    print(f\"  [{item['source'][:12]}] {item['title'][:65]}...\")"
```

#### 4. Reddit Top Post
```bash
curl -s "https://old.reddit.com/r/CryptoCurrency/hot.json?limit=3" -H "User-Agent: Bot/1.0" | python -c "
import sys, json
data = json.load(sys.stdin)
posts = [c['data'] for c in data.get('data', {}).get('children', []) if not c['data'].get('stickied')]
if posts:
    top = posts[0]
    print(f\"Reddit Hot: [{top.get('score', 0)} pts] {top.get('title', '')[:60]}...\")"
```

## Output Format

```
================== QUICK NEWS SCAN ==================

Fear & Greed: XX (Classification)
Trending: BTC, ETH, SOL, DOGE, ...

Headlines:
  [source] Headline text...
  [source] Headline text...
  [source] Headline text...
  [source] Headline text...
  [source] Headline text...

Reddit Hot: [XXX pts] Post title...

=====================================================
```

## Example

```bash
/news-scan
```
